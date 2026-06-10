#!/usr/bin/env python3
"""Config-driven hard filters. Every threshold is read from config.json's "filters" block,
nothing is hardcoded:

    us_only                          -> is_international gate
    experience_ceiling_years/field   -> years_excluded (primary rule)
    secondary_experience_*           -> years_excluded (optional second rule, e.g. 5+ yrs SaaS)
    salary_floor_usd                 -> salary_excluded
    company_location_rules           -> company_loc_excluded

Set any value to null in config to disable that filter. The functions take an explicit config
so callers can share one loaded config object.
"""
import html as _html
import re
import config_lib as C

# US state/territory codes and US-signalling words, for the international gate.
_US_CODES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
             "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC").split()
_US_WORDS = ("united states", "usa", "u.s.", "u.s ", "remote - us", "us remote", "remote us",
             "remote, us", "anywhere in the us")
_FOREIGN = [
    "united kingdom", "uk", "england", "scotland", "ireland", "canada", "ontario", "quebec",
    "germany", "france", "spain", "portugal", "italy", "netherlands", "belgium", "switzerland",
    "sweden", "norway", "denmark", "finland", "poland", "austria", "israel", "india", "singapore",
    "australia", "new zealand", "japan", "china", "hong kong", "taiwan", "korea", "south korea",
    "brazil", "mexico", "argentina", "chile", "colombia", "uae", "dubai", "saudi", "qatar",
    "emea", "apac", "latam", "europe", "european", " eu ", "remote - eu", "uk/eu",
    "london", "manchester", "dublin", "paris", "berlin", "munich", "hamburg", "amsterdam",
    "zurich", "geneva", "stockholm", "oslo", "copenhagen", "helsinki", "madrid", "barcelona",
    "lisbon", "milan", "rome", "vienna", "warsaw", "tel aviv", "jerusalem", "bangalore",
    "bengaluru", "mumbai", "delhi", "hyderabad", "pune", "sydney", "melbourne",
    "tokyo", "seoul", "shanghai", "beijing", "shenzhen", "taipei", "sao paulo", "toronto",
    "vancouver", "montreal", "mexico city", "bogota", "buenos aires", "abu dhabi",
]


def _f(cfg):
    return C.get(cfg, "filters", {}) or {}


def is_international(loc, cfg):
    """True if the location is clearly foreign with NO US option, and us_only is enabled."""
    if not _f(cfg).get("us_only"):
        return False
    if not loc:
        return False
    low = loc.lower()
    has_us = (any(re.search(r'\b' + c + r'\b', loc) for c in _US_CODES)
              or any(w in low for w in _US_WORDS)
              or re.search(r'\bUS\b', loc) is not None          # bare "US" token, case-sensitive
              or re.search(r'\bU\.S\.?(?=\W|$)', loc) is not None)
    has_foreign = any(re.search(r'\b' + re.escape(x.strip()) + r'\b', low) for x in _FOREIGN)
    return has_foreign and not has_us


def years_excluded(raw, cfg):
    """Return a reason string if the JD demands too-senior experience, else None.

    Primary rule: experience_ceiling_years + experience_ceiling_field (e.g. 10+ yrs product).
    Optional second rule: secondary_experience_ceiling_years + secondary_experience_ceiling_field
    (e.g. 5+ yrs saas). Either rule disables itself when its years value is null."""
    f = _f(cfg)
    rules = []
    if f.get("experience_ceiling_years") is not None:
        rules.append((int(f["experience_ceiling_years"]),
                      (f.get("experience_ceiling_field") or "").lower()))
    if f.get("secondary_experience_ceiling_years") is not None and f.get("secondary_experience_ceiling_field"):
        rules.append((int(f["secondary_experience_ceiling_years"]),
                      (f.get("secondary_experience_ceiling_field") or "").lower()))
    if not rules:
        return None
    t = re.sub(r'<[^>]+>', ' ', _html.unescape(raw or '')).lower()
    t = re.sub(r'\s+', ' ', t)
    for m in re.finditer(r'(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:to\s*\d{1,2}\s*)?years?', t):
        n = int(m.group(1))
        win = t[max(0, m.start() - 35): m.start() + 60]
        for ceiling, field in rules:
            if n >= ceiling and (not field or field in win):
                label = field if field else "experience"
                return f"{ceiling}+yrs {label}"
    return None


def salary_excluded(raw, cfg):
    """If a salary is stated and its TOP figure is under salary_floor_usd, return a reason."""
    floor = _f(cfg).get("salary_floor_usd")
    if floor is None:
        return None
    floor = int(floor)
    t = re.sub(r'<[^>]+>', ' ', _html.unescape(raw or '')).lower()
    amounts = []
    for m in re.finditer(r'\$\s?(\d{1,3}(?:,\d{3})+)', t):     # $85,000 / $180,000 / $1,200,000
        amounts.append(int(m.group(1).replace(",", "")))
    for m in re.finditer(r'\$\s?(\d{2,3}(?:\.\d)?)\s?k\b', t):  # $180k / $92.5k (t is lowercased)
        amounts.append(int(float(m.group(1)) * 1000))
    plausible = [a for a in amounts if 40_000 <= a <= 1_000_000]
    if plausible and max(plausible) < floor:
        return f"salary<{floor//1000}k(${max(plausible):,})"
    return None


def company_loc_excluded(company, location, cfg):
    """Per-company location override. Returns a reason if the company is in
    company_location_rules and the location does not contain one of its allow_only substrings."""
    rules = _f(cfg).get("company_location_rules") or []
    if not rules:
        return None
    c = (company or "").lower()
    loc = (location or "").lower()
    for rule in rules:
        name = (rule.get("company") or "").lower()
        allow = [a.lower() for a in (rule.get("allow_only") or [])]
        if name and name in c and allow and not any(a in loc for a in allow):
            return f"{rule.get('company')}-location-not-allowed"
    return None
