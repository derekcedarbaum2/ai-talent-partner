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
import urllib.parse
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
    # Tokens may contain spaces or dots (e.g. "Flock Safety", "acme.io"); quote for the URL.
    url = f"https://api.ashbyhq.com/posting-api/job-board/{urllib.parse.quote(tok)}?includeCompensation=false"
    s, b = fetch(url)
    if s == 200 and '"jobs"' in b:
        try:
            if json.loads(b).get("jobs") is not None:
                return url
        except Exception:
            pass
    return None


PROBES = [("greenhouse", gh_ok), ("lever", lever_ok), ("ashby", ashby_ok)]

HTML_PATTERNS = [
    ("greenhouse", re.compile(r'(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9]+)', re.I)),
    ("greenhouse", re.compile(r'greenhouse\.io/embed/job_board\?for=([a-z0-9]+)', re.I)),
    ("lever",      re.compile(r'jobs\.lever\.co/([a-z0-9\-]+)', re.I)),
    # Ashby tokens may contain URL-encoded spaces (%20) and dots, e.g. "Flock%20Safety" or
    # "acme.io". Match any run of non-slash URL characters (mirroring ats_lib.parse_ats),
    # then urldecode, so resolver and parser agree.
    ("ashby",      re.compile(r'(?:jobs\.ashbyhq\.com|ashbyhq\.com/job-board)/([^/\s"\'<>&?#]+)', re.I)),
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
                tok = urllib.parse.unquote(m.group(1))
                if prov != "ashby":
                    tok = tok.lower()      # ashby tokens can be case-/space-sensitive; keep as-is
                if tok.lower() in ("embed", "www", "api"):
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


def _merge_prior(out, cfg):
    """Keep previously verified ats entries when this run resolved a company to ats=None
    (e.g. a transient fetch failure), so a flaky run never clobbers known-good tokens.
    Returns the number of entries carried over."""
    cache_path = companies_lib._resolved_cache_path(cfg)
    if not os.path.exists(cache_path):
        return 0
    try:
        prior = {x["name"].strip().lower(): x.get("ats")
                 for x in json.load(open(cache_path, encoding="utf-8"))}
    except Exception:
        return 0
    kept = 0
    for c in out:
        if not c.get("ats"):
            old = prior.get(c["name"].strip().lower())
            if old:
                c["ats"] = old
                kept += 1
    return kept


def main():
    limit = None
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        if i + 1 >= len(sys.argv):
            sys.exit("resolve_ats: --limit requires a number (usage: resolve_ats.py [--limit N])")
        try:
            limit = int(sys.argv[i + 1])
        except ValueError:
            sys.exit(f"resolve_ats: --limit must be a number, got {sys.argv[i + 1]!r}")
    cfg = C.load()
    comps = companies_lib.load(cfg, use_resolved=False)
    if limit is not None:
        comps = comps[:limit]
    out = [None] * len(comps)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(resolve, c): i for i, c in enumerate(comps)}
        for f in concurrent.futures.as_completed(futs):
            out[futs[f]] = f.result()
    kept = 0 if limit else _merge_prior(out, cfg)
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
        msg = "wrote state/companies.resolved.json with ats fields"
        if kept:
            msg += f" (kept {kept} previously verified entries over null re-resolutions)"
        print(msg)


if __name__ == "__main__":
    main()
