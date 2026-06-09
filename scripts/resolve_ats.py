#!/usr/bin/env python3
"""Detect each company's ATS (Greenhouse/Lever/Ashby/Workday) plus board token. Deterministic,
no LLM. Only runs for companies given as a bare URL in companies.txt (the ats: form already
carries provider+token). Strategy per company:
  1) Fetch the homepage and a few careers paths; regex for explicit ATS board URLs (authoritative).
  2) Fall back to probing provider APIs with token candidates derived from the domain and name.
Every candidate token is verified against the provider's public API before being accepted.

Writes the resolved ats fields to state/companies.resolved.json (gitignored), keyed by company
name, so poll.py and the liveness/date scripts can use them without editing companies.txt.
Run with --limit N to test a slice without writing.
"""
import concurrent.futures
import json
import os
import re
import sys
import urllib.request

import config_lib as C
import companies_lib

CTX = C.ssl_ctx()
UA = C.UA


def fetch(url, timeout=8, retries=3):
    # Backs off on rate limiting (429) and transient 503s so bulk probing across many companies
    # does not get the run throttled. Other errors return (None, "") as before.
    import time, urllib.error
    delay = 1.0
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.status, r.read(400000).decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries:
                ra = e.headers.get("Retry-After")
                try:
                    wait = float(ra) if ra else delay
                except ValueError:
                    wait = delay
                time.sleep(min(wait, 30.0))
                delay *= 2
                continue
            return e.code, ""
        except Exception:
            return None, ""
    return None, ""


def token_candidates(name, dom):
    slug = dom.split(".")[0]
    n = re.sub(r'[^a-z0-9]+', '', name.lower())
    nd = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    cands = []
    for c in [slug, n, nd, name.lower().replace(' ', '')]:
        if c and c not in cands:
            cands.append(c)
    return cands


def gh_ok(tok):
    s, b = fetch(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs")
    if s == 200 and '"jobs"' in b:
        try:
            if json.loads(b).get("jobs"):
                return f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs?content=true"
        except Exception:
            pass
    return None


def lever_ok(tok):
    s, b = fetch(f"https://api.lever.co/v0/postings/{tok}?mode=json")
    if s == 200 and b.strip().startswith("["):
        try:
            if json.loads(b):
                return f"https://api.lever.co/v0/postings/{tok}?mode=json"
        except Exception:
            pass
    return None


def ashby_ok(tok):
    s, b = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=false")
    if s == 200 and '"jobs"' in b:
        try:
            if json.loads(b).get("jobs") is not None:
                return f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=false"
        except Exception:
            pass
    return None


PROBES = [("greenhouse", gh_ok), ("lever", lever_ok), ("ashby", ashby_ok)]

HTML_PATTERNS = [
    ("greenhouse", re.compile(r'(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9]+)', re.I)),
    ("greenhouse", re.compile(r'greenhouse\.io/embed/job_board\?for=([a-z0-9]+)', re.I)),
    ("lever",      re.compile(r'jobs\.lever\.co/([a-z0-9\-]+)', re.I)),
    ("ashby",      re.compile(r'(?:jobs\.ashbyhq\.com|ashbyhq\.com/job-board)/([a-z0-9\-]+)', re.I)),
]
WORKDAY = re.compile(r'([a-z0-9\-]+)\.(wd\d+)\.myworkdayjobs\.com', re.I)
VERIFY = {"greenhouse": gh_ok, "lever": lever_ok, "ashby": ashby_ok}

CAREERS_PATHS = ["", "/careers", "/careers/", "/jobs", "/company/careers", "/about/careers", "/join-us", "/work-with-us"]


def resolve(company):
    if company.get("ats"):
        return company                         # already known (ats: form in companies.txt)
    if not company.get("url"):
        return {**company, "ats": None}
    name = company["name"]
    dom = re.sub(r'^https?://(www\.)?', '', company["url"]).split('/')[0]
    base = "https://" + dom
    for path in CAREERS_PATHS[:4]:
        s, html = fetch(base + path)
        if not html:
            continue
        for prov, pat in HTML_PATTERNS:
            m = pat.search(html)
            if m:
                tok = m.group(1).lower()
                if tok in ("embed", "www", "api"):
                    continue
                api = VERIFY[prov](tok)
                if api:
                    return {**company, "ats": {"provider": prov, "token": tok, "api": api}}
        wm = WORKDAY.search(html)
        if wm:
            return {**company, "ats": {"provider": "workday", "token": wm.group(1).lower(),
                                       "api": f"https://{wm.group(1).lower()}.{wm.group(2).lower()}.myworkdayjobs.com",
                                       "note": "workday: not JSON-pollable for free; web-path"}}
    for tok in token_candidates(name, dom):
        for prov, fn in PROBES:
            api = fn(tok)
            if api:
                return {**company, "ats": {"provider": prov, "token": tok, "api": api}}
    return {**company, "ats": None}


def main():
    cfg = C.load()
    comps = companies_lib.load(cfg, use_resolved=False)
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
        comps = comps[:limit]
    out = [None] * len(comps)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(resolve, c): i for i, c in enumerate(comps)}
        for f in concurrent.futures.as_completed(futs):
            out[futs[f]] = f.result()
    found = [c for c in out if c["ats"] and c["ats"].get("provider") != "workday"]
    workday = [c for c in out if c["ats"] and c["ats"].get("provider") == "workday"]
    none = [c for c in out if not c["ats"]]
    from collections import Counter
    prov = Counter(c["ats"]["provider"] for c in out if c["ats"])
    print(f"pollable ATS: {len(found)} | workday(web-path): {len(workday)} | "
          f"no-ATS(web-path): {len(none)} | total {len(out)}")
    print("providers:", dict(prov))
    if limit:
        for c in found:
            print("  +", c["ats"]["provider"], c["ats"]["token"], "<-", c["name"])
    else:
        companies_lib.save_resolved(out, cfg)
        print("wrote state/companies.resolved.json with ats fields")


if __name__ == "__main__":
    main()
