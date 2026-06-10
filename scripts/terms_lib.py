#!/usr/bin/env python3
"""Parse config/terms.md into the include/exclude term lists that drive title matching.

terms.md structure (see config/terms.example.md):
  - Only lines starting with "##" are section headings. Anything before the first heading
    (title line, explanatory prose) is ignored.
  - Lines under a heading containing "Exclusion"/"Exclude" are EXCLUDE terms: a title is
    dropped if it contains one of them, even when an include term also matched.
  - Lines under a "## Hard filters" heading are documentation for the human. The actual
    hard-filter thresholds (years, salary, us_only, per-company rules) live in config.json
    under "filters".
  - Lines under any other heading are INCLUDE terms: a posting title must contain one of
    them, case-insensitively, to be kept.

The matcher is an include-list gate, plus an exclude-list that overrides it, plus a "strong
match" notion so a title that is unambiguously the target role survives even when it also
contains a generic negative word.

Lines starting with a single # (not ##) are comments, wherever they appear. Blank lines are
ignored.
"""
import os
import config_lib as C

# Words that, alone, do NOT make a title the target role. A title containing only an include
# term plus one of these is treated as a near-miss and dropped, UNLESS it is a strong match.
# This list is only consulted to break ties, never to drop a title that clearly states the
# include term as its own noun phrase.
_GENERIC_NEG = ["designer", "engineer", "marketing", "scientist", "architect", "analyst",
                "researcher", "recruiter", "counsel", "controller", "quality", "security"]


def _is_section_heading(line):
    """Only '##'-prefixed lines with text are section headings; a single '#' is a comment."""
    s = line.strip()
    return s.startswith("##") and bool(s.lstrip("#").strip())


def parse(path):
    """Return (include_terms, exclude_terms) lowercased lists from a terms.md file."""
    include, exclude = [], []
    mode = "skip"   # ignore prose preamble until the first recognized section heading
    with open(path, encoding="utf-8") as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped:
                continue
            if _is_section_heading(stripped):
                low = stripped.lstrip("#").strip().lower()
                if "exclusion" in low or "exclude" in low:
                    mode = "exclude"
                elif "hard filter" in low:
                    mode = "skip"  # documentation block; thresholds come from config
                else:
                    mode = "include"
                continue
            if stripped.startswith("#"):
                # A comment or commented-out term line (e.g. "# Product Marketing Manager").
                continue
            if mode == "include":
                include.append(stripped.lower())
            elif mode == "exclude":
                exclude.append(stripped.lower())
            # mode == "skip": ignore
    return include, exclude


def load(cfg=None):
    if cfg is None:
        cfg = C.load()
    path = C.repo_path(C.get(cfg, "terms_file", "config/terms.md"))
    include, exclude = parse(path)
    return include, exclude


def make_title_matcher(include, exclude):
    """Build a title_match(title) -> bool closure from parsed terms.

    Logic (generic version of poll.py's title_match):
      1. Reject if the title contains any EXCLUDE term.
      2. Reject if no INCLUDE term is present.
      3. If the title is a 'strong' match (an include term appears as its own role noun),
         keep it. Otherwise, drop it if it contains a generic negative word.
    """
    include = [t for t in include if t]
    exclude = [t for t in exclude if t]

    def title_match(title):
        tl = (title or "").lower()
        if any(x in tl for x in exclude):
            return False
        hits = [t for t in include if t in tl]
        if not hits:
            return False
        # Strong match: an include term is present that is not merely a fragment of a longer
        # generic title. We approximate poll.py's "strong" by requiring that at least one of
        # the matched include terms is itself a multi-word role phrase (>= 2 words) or that no
        # generic negative word is present.
        strong = any(len(t.split()) >= 2 for t in hits)
        if not strong and any(n in tl for n in _GENERIC_NEG):
            return False
        return True

    return title_match
