#!/usr/bin/env python3
"""Parse config/companies.txt into the company dicts the engine works with.

Accepted line formats (one company per line, blank lines and # comments ignored):

    Name | https://their-careers-or-homepage.com
    Name | ats:greenhouse:token
    Name | ats:lever:token
    Name | ats:ashby:token

The ats: form is preferred: it carries the provider and board token directly, so no
auto-detection is needed. The bare-URL form is resolved by resolve_ats.py, which fills the
ats field in place (writing the resolved cache to state/companies.resolved.json).

A company dict looks like:
    {"name": str, "url": str, "sector": str, "ats": {provider, token, api} | None}

Sector is optional in companies.txt. If a line carries a trailing "| sector:X" segment it is
used, otherwise sector defaults to "" (the engine does not require it).
"""
import json, os, re
import config_lib as C

_API_BUILDERS = {
    "greenhouse": lambda t: f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs?content=true",
    "lever": lambda t: f"https://api.lever.co/v0/postings/{t}?mode=json",
    "ashby": lambda t: f"https://api.ashbyhq.com/posting-api/job-board/{t}?includeCompensation=false",
}


def _domain(url):
    d = re.sub(r'^https?://', '', url or '').split('/')[0].lower()
    return re.sub(r'^www\.', '', d)


def parse_line(line):
    """Parse one companies.txt line into a company dict, or None for blank/comment lines."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "|" not in line:
        return None
    parts = [p.strip() for p in line.split("|")]
    name = parts[0]
    target = parts[1] if len(parts) > 1 else ""
    sector = ""
    for extra in parts[2:]:
        if extra.lower().startswith("sector:"):
            sector = extra.split(":", 1)[1].strip()
    ats = None
    url = ""
    if target.lower().startswith("ats:"):
        bits = target.split(":")
        if len(bits) >= 3:
            provider = bits[1].lower()
            token = bits[2]
            api = _API_BUILDERS.get(provider, lambda t: "")(token)
            ats = {"provider": provider, "token": token, "api": api}
        url = ""
    else:
        url = target
    return {"name": name, "url": url, "sector": sector, "ats": ats}


def _resolved_cache_path(cfg):
    return os.path.join(C.REPO_ROOT, "state", "companies.resolved.json")


def load(cfg=None, use_resolved=True):
    """Load companies from config[companies_file]. If a resolved cache exists (written by
    resolve_ats.py) and use_resolved is True, prefer its ats fields. The cache is keyed by
    company name so re-running resolve_ats.py does not require re-editing companies.txt."""
    if cfg is None:
        cfg = C.load()
    path = C.repo_path(C.get(cfg, "companies_file", "config/companies.txt"))
    out = []
    seen = set()
    with open(path) as f:
        for line in f:
            c = parse_line(line)
            if not c:
                continue
            key = (_domain(c["url"]) or c["name"].lower())
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
    if use_resolved:
        cache_path = _resolved_cache_path(cfg)
        if os.path.exists(cache_path):
            try:
                cache = json.load(open(cache_path))
                by_name = {x["name"].strip().lower(): x.get("ats") for x in cache}
                for c in out:
                    if not c.get("ats"):
                        ats = by_name.get(c["name"].strip().lower())
                        if ats:
                            c["ats"] = ats
            except Exception:
                pass
    return out


def save_resolved(companies, cfg=None):
    """Persist resolved ats fields to state/companies.resolved.json (gitignored)."""
    if cfg is None:
        cfg = C.load()
    cache_path = _resolved_cache_path(cfg)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    slim = [{"name": c["name"], "ats": c.get("ats")} for c in companies]
    json.dump(slim, open(cache_path, "w"), indent=2)


def company_ats_map(cfg=None):
    """name (lowercased) -> ats dict, for date/liveness backfill from a job URL alone."""
    return {c["name"].strip().lower(): c["ats"] for c in load(cfg) if c.get("ats")}
