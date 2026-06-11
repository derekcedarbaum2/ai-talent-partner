#!/usr/bin/env python3
"""Phase A (deterministic, no LLM): poll resolved ATS boards, extract postings, prefilter titles
against config/terms.md, apply the config-driven hard filters, de-dup ATS candidates against
the tracker, write state/candidates.json. The model step (prompts/finder.md) does the final
judgment, the web-search shard for non-ATS companies, and the append.

Nothing here is hardcoded: companies come from config/companies.txt (via companies_lib), title
matching from config/terms.md (via terms_lib), and the hard filters from config.json's "filters"
block (via filters.py).
"""
import concurrent.futures
import json
import os
import urllib.request
from datetime import datetime, timezone

import config_lib as C
import companies_lib
import sheet_io
import terms_lib
import filters

CTX = C.ssl_ctx()
UA = C.UA


def fetch_json(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def iso_date(s):
    if not s:
        return ""
    try:
        return s[:10]
    except Exception:
        return ""


def poll(company, title_match, cfg):
    ats = company.get("ats")
    if not ats or ats["provider"] == "workday":
        return []
    prov, api = ats["provider"], ats["api"]
    data = fetch_json(api)
    rows = []
    try:
        if prov == "greenhouse":
            for j in (data or {}).get("jobs", []):
                if title_match(j.get("title", "")):
                    c = j.get("content", "")
                    if filters.years_excluded(c, cfg) or filters.salary_excluded(c, cfg):
                        continue
                    rows.append({"title": j["title"],
                                 "location": (j.get("location") or {}).get("name", ""),
                                 "url": j.get("absolute_url", ""),
                                 "posted": iso_date(j.get("updated_at"))})
        elif prov == "lever":
            for j in (data or []):
                if title_match(j.get("text", "")):
                    lists = " ".join((i.get("text", "") + " " + i.get("content", ""))
                                     for i in j.get("lists", []))
                    c = (j.get("descriptionPlain") or j.get("description", "")) + " " + lists
                    if filters.years_excluded(c, cfg) or filters.salary_excluded(c, cfg):
                        continue
                    ms = j.get("createdAt")
                    posted = (datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
                              if ms else "")
                    rows.append({"title": j["text"],
                                 "location": (j.get("categories") or {}).get("location", ""),
                                 "url": j.get("hostedUrl", ""),
                                 "posted": posted})
        elif prov == "ashby":
            for j in (data or {}).get("jobs", []):
                if title_match(j.get("title", "")):
                    c = j.get("descriptionPlain") or j.get("descriptionHtml", "")
                    if filters.years_excluded(c, cfg) or filters.salary_excluded(c, cfg):
                        continue
                    loc = j.get("location") or j.get("locationName") or ""
                    rows.append({"title": j["title"],
                                 "location": loc if isinstance(loc, str) else "",
                                 "url": j.get("jobUrl") or j.get("applyUrl", ""),
                                 "posted": iso_date(j.get("publishedAt"))})
    except Exception:
        return []
    for r in rows:
        r["company"] = company["name"]
        r["sector"] = company.get("sector", "")
        r["source"] = prov
    return [r for r in rows
            if r.get("url")
            and not filters.is_international(r["location"], cfg)
            and not filters.company_loc_excluded(r["company"], r["location"], cfg)]


def main():
    cfg = C.load()
    comps = companies_lib.load(cfg)
    include, exclude = terms_lib.load(cfg)
    title_match = terms_lib.make_title_matcher(include, exclude)

    state = os.path.join(C.REPO_ROOT, "state")
    os.makedirs(state, exist_ok=True)

    pollable = [c for c in comps if c.get("ats") and c["ats"]["provider"] != "workday"]
    cands = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for rows in ex.map(lambda c: poll(c, title_match, cfg), pollable):
            cands.extend(rows)
    seen, uniq = set(), []
    for r in cands:
        if r["url"] not in seen:
            seen.add(r["url"])
            uniq.append(r)
    # Drop candidates already in the tracker, so the model step never re-judges known rows.
    try:
        existing = sheet_io.get_existing_urls()
    except Exception as e:
        existing = set()
        print(f"warning: could not read tracker for de-dup ({e}); keeping all candidates")
    fresh = [r for r in uniq if r["url"] not in existing]
    dropped = len(uniq) - len(fresh)
    json.dump(fresh, open(os.path.join(state, "candidates.json"), "w"), indent=2)
    print(f"polled {len(pollable)} ATS boards -> {len(fresh)} title-matching postings "
          f"({dropped} dropped as already-tracked)")

    # Web-shard: companies with no pollable ATS get checked 1/SHARDS per run (rotating), so each
    # slice stays small enough for the model step. A full cycle of the non-ATS tail takes SHARDS
    # runs. Sized by config web_shard_count.
    SHARDS = int(C.get(cfg, "web_shard_count", 24)) or 24
    idxf = os.path.join(state, "shard_idx")
    try:
        idx = int(open(idxf).read().strip())
    except Exception:
        idx = 0
    non_pollable = [c for c in comps if not (c.get("ats") and c["ats"]["provider"] != "workday")]
    shard = [{"name": c["name"], "url": c["url"], "sector": c.get("sector", "")}
             for c in non_pollable[idx::SHARDS]]
    json.dump(shard, open(os.path.join(state, "web_shard.json"), "w"), indent=2)
    open(idxf, "w").write(str((idx + 1) % SHARDS))
    print(f"web-shard {idx+1}/{SHARDS}: {len(shard)} non-ATS companies to check this run")


if __name__ == "__main__":
    main()
