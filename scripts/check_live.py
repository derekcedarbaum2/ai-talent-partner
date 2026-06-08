#!/usr/bin/env python3
"""Remove tracker rows whose URL no longer points to a live job (closed/delisted). Liveness is
checked at the source, which is the only reliable signal since most ATS pages serve a 200 SPA
shell even for expired jobs:
  - Greenhouse/Lever: single-job API (200 live, 404 dead).
  - Ashby: authoritative SPA GraphQL (jobs.ashbyhq.com/api/non-user-graphql); jobPosting==null
    or isListed==false means dead. Falls back to the public board listing.
  - Workday: the CXS JSON API 404s on dead jobs even though the page is a 200 shell.
  - other (custom): plain HTTP GET, dead only on explicit 404/410, ambiguous -> keep.

Run with --apply to delete; default is a dry-run report. Deterministic, no LLM. Reads and
deletes through scripts/sheet_io.py, so it works against either the CSV or Google Sheets backend.
This liveness logic is the engine's crown jewel; it is preserved verbatim in spirit from the
original.
"""
import concurrent.futures
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

import config_lib as C
import companies_lib
import sheet_io
from ats_lib import parse_ats

CTX = C.ssl_ctx()
UA = C.UA

COMPANY_ATS = {}   # populated in main() from companies_lib


def api_status(url):
    try:
        urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}),
                               timeout=12, context=CTX)
        return 200
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


_ashby = {}   # token -> set(listed uuids)


def ashby_listed(token):
    if token in _ashby:
        return _ashby[token]
    s = set()
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=false",
            headers={"User-Agent": UA}), timeout=15, context=CTX))
        import re
        for j in d.get("jobs", []):
            if j.get("isListed", True):
                m = re.search(r'([0-9a-fA-F\-]{36})', j.get("jobUrl", ""))
                if m:
                    s.add(m.group(1).lower())
                if j.get("id"):
                    s.add(str(j["id"]).lower())
    except Exception:
        return None      # couldn't fetch -> unknown
    _ashby[token] = s
    return s


_GQL = ("query ApiJobPosting($organizationHostedJobsPageName: String!, $jobPostingId: String!) "
        "{ jobPosting(organizationHostedJobsPageName: $organizationHostedJobsPageName, jobPostingId: $jobPostingId) "
        "{ id isListed __typename } }")


def ashby_live(token, jid):
    """Authoritative: Ashby's SPA GraphQL returns jobPosting=null for expired/unlisted jobs, even
    when the public board API is disabled and the page serves a 200 shell.
    True=live, False=dead, None=couldn't determine."""
    body = {"operationName": "ApiJobPosting",
            "variables": {"organizationHostedJobsPageName": token, "jobPostingId": jid},
            "query": _GQL}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting",
            data=json.dumps(body).encode(), method="POST",
            headers={"User-Agent": UA, "Content-Type": "application/json"}), timeout=12, context=CTX)
        jp = json.load(r).get("data", {}).get("jobPosting")
        if jp is None:
            return False
        if jp.get("isListed") is False:
            return False
        return True
    except Exception:
        return None


def workday_live(url):
    """Workday pages are 200 SPA shells even when expired; the CXS JSON API 404s on dead jobs.
    URL: https://{tenant}.{wd}.myworkdayjobs.com/{site}/job/{loc}/{slug}
    CXS: https://{host}/wday/cxs/{tenant}/{site}/job/{loc}/{slug}. True=live, False=dead, None=unknown."""
    p = urllib.parse.urlparse(url)
    host = p.netloc
    tenant = host.split(".")[0]
    parts = [x for x in p.path.split("/") if x]
    if "job" not in parts or not parts:
        return None
    site = parts[0]
    tail = "/".join(parts[parts.index("job"):])
    st = api_status(f"https://{host}/wday/cxs/{tenant}/{site}/{tail}")
    if st == 404:
        return False
    if st == 200:
        return True
    return None


def http_live(url):
    """Custom pages: dead only on explicit 404/410; ambiguous -> keep (True)."""
    try:
        cur = url
        for _ in range(5):
            try:
                urllib.request.urlopen(urllib.request.Request(cur, headers={"User-Agent": UA}),
                                       timeout=12, context=CTX)
                return True
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    loc = e.headers.get("Location")
                    if not loc:
                        return True
                    cur = urllib.parse.urljoin(cur, loc)
                    continue
                return False if e.code in (404, 410) else True
        return True
    except Exception:
        return True


def is_dead(company, url):
    prov, tok, jid = parse_ats(url)
    if prov == "greenhouse":
        if tok is None:
            ats = COMPANY_ATS.get((company or "").strip().lower())
            if not ats or ats.get("provider") != "greenhouse":
                return not http_live(url)
            tok = ats["token"]
        st = api_status(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs/{jid}")
        if st == 404:
            return True
        if st == 200:
            return False
        return not http_live(url)                  # API inconclusive -> verify the page
    if prov == "lever":
        st = api_status(f"https://api.lever.co/v0/postings/{tok}/{jid}?mode=json")
        if st == 404:
            return True
        if st == 200:
            return False
        return not http_live(url)
    if prov == "ashby":
        live = ashby_live(tok, jid)                # authoritative GraphQL check
        if live is True:
            return False
        if live is False:
            return True
        listed = ashby_listed(tok)                 # GraphQL inconclusive -> board listing
        if listed and jid.lower() in listed:
            return False
        return False                               # truly can't tell -> keep (don't false-delete)
    if "myworkdayjobs.com" in url:                 # Workday: page is a 200 shell; CXS API is authoritative
        live = workday_live(url)
        if live is False:
            return True
        if live is True:
            return False
        return not http_live(url)
    return not http_live(url)


def main():
    apply = "--apply" in sys.argv
    cfg = C.load()
    global COMPANY_ATS
    COMPANY_ATS = companies_lib.company_ats_map(cfg)

    rows = sheet_io.read_rows()
    indexed = [(r["_rownum"], r["Company"], r["Job Title"], r["Job URL"])
               for r in rows if (r.get("Job URL") or "").strip()]

    dead = []

    def chk(item):
        rownum, company, title, url = item
        return (item, is_dead(company, url))

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        for item, d in ex.map(chk, indexed):
            if d:
                dead.append(item)

    print(f"rows checked: {len(indexed)} | dead/closed URLs: {len(dead)}")
    for rownum, company, title, url in sorted(dead):
        print(f"  row {rownum}: {company} - {title}")

    if apply and dead:
        sheet_io.delete_rows([rn for rn, *_ in dead])
        print(f"\nDELETED {len(dead)} dead rows.")
    elif not apply:
        print("\n(dry run - pass --apply to delete)")


if __name__ == "__main__":
    main()
