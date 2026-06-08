#!/usr/bin/env python3
"""ATS URL parsing and post-date resolution, shared by check_live.py and backfill_dates.py.

parse_ats(url) -> (provider, token, job_id) recognises Greenhouse, Lever, and Ashby job URLs.
The Ashby pattern deliberately accepts ANY token including URL-encoded spaces (%20) and dots:
it matches [^/]+ for the token and urldecodes it, so boards like "Flock%20Safety" resolve
correctly. This is the parse_ats fix called out as load-bearing; do not narrow it back to a
character class.
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import config_lib as C

_CTX = C.ssl_ctx()


def fetch_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": C.UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def parse_ats(url):
    """Return (provider, token, job_id) for a known ATS job URL, else (None, None, None).

    Greenhouse company-hosted URLs carry the job id via gh_jid= but not the board token; in
    that case token is None and the caller supplies it from the company -> ats map.
    """
    u = url or ""
    m = re.search(r'(?:boards|job-boards)\.greenhouse\.io/([A-Za-z0-9]+)/jobs/(\d+)', u)
    if m:
        return ("greenhouse", m.group(1), m.group(2))
    m = re.search(r'gh_jid=(\d+)', u)
    if m:
        return ("greenhouse", None, m.group(1))            # company-hosted; token from companies map
    m = re.search(r'jobs\.lever\.co/([A-Za-z0-9\-]+)/([0-9a-fA-F\-]{36})', u)
    if m:
        return ("lever", m.group(1), m.group(2))
    # Ashby token may contain URL-encoded spaces (%20) and dots, e.g. "Flock%20Safety" or
    # "acme.io". Match any non-slash run for the token, then urldecode it.
    m = re.search(r'jobs\.ashbyhq\.com/([^/]+)/([0-9a-fA-F\-]{36})', u)
    if m:
        return ("ashby", urllib.parse.unquote(m.group(1)), m.group(2))
    return (None, None, None)


_BOARD_CACHE = {}   # (provider, token) -> {job_id: posted_date}


def board_map(provider, token):
    """job_id -> ISO post date for every listing on a board, cached per (provider, token)."""
    key = (provider, token)
    if key in _BOARD_CACHE:
        return _BOARD_CACHE[key]
    out = {}
    if provider == "greenhouse":
        d = fetch_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
        for j in (d or {}).get("jobs", []):
            if j.get("updated_at"):
                out[str(j["id"])] = j["updated_at"][:10]
    elif provider == "lever":
        d = fetch_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
        for j in (d or []):
            ms = j.get("createdAt")
            if ms:
                out[j["id"]] = datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
    elif provider == "ashby":
        d = fetch_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=false")
        for j in (d or {}).get("jobs", []):
            dt = j.get("publishedAt") or j.get("updatedAt")
            if dt:
                date = dt[:10]
                ju = j.get("jobUrl", "")
                mm = re.search(r'([0-9a-fA-F\-]{36})', ju)
                if mm:
                    out[mm.group(1).lower()] = date
                if j.get("id"):
                    out[str(j["id"]).lower()] = date
    _BOARD_CACHE[key] = out
    return out


def resolve_date(company, url, company_ats):
    """Resolve a posting's date from its ATS board. company_ats maps lowercased company name
    to its ats dict (for company-hosted Greenhouse URLs that omit the token)."""
    provider, token, jid = parse_ats(url)
    if not provider:
        return None
    if token is None:
        ats = company_ats.get((company or "").strip().lower())
        if not ats or ats.get("provider") != "greenhouse":
            return None
        token = ats["token"]
    lookup = jid.lower() if provider != "greenhouse" else jid
    return board_map(provider, token).get(lookup)
