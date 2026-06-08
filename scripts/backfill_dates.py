#!/usr/bin/env python3
"""Backfill blank Posted dates in the tracker. Many web-sourced rows actually point at
Greenhouse/Lever/Ashby boards, so the real post date is available from the ATS API. Resolves
the date per row (board listing cached per token) and fills the Posted column.

Run with --apply to write; default is a dry-run report. No LLM. Reads and writes through
scripts/sheet_io.py, so it works against either backend.
"""
import sys

import config_lib as C
import companies_lib
import sheet_io
from ats_lib import resolve_date


def main():
    apply = "--apply" in sys.argv
    cfg = C.load()
    company_ats = companies_lib.company_ats_map(cfg)

    rows = sheet_io.read_rows()
    blank = [(r["_rownum"], r["Company"], r["Job Title"], r["Job URL"])
             for r in rows
             if not (r.get("Posted") or "").strip() and (r.get("Job URL") or "").strip()]

    updates, still = [], 0
    for rownum, company, title, url in blank:
        date = resolve_date(company, url, company_ats)
        if date:
            updates.append({"rownum": rownum, "col": "Posted", "value": date})
        else:
            still += 1

    print(f"blank Posted rows: {len(blank)} | resolvable from ATS: {len(updates)} | still blank: {still}")
    for up in updates[:200]:
        print(f"  row {up['rownum']} Posted <- {up['value']}")

    if apply and updates:
        sheet_io.update_cells(updates)
        print(f"\nAPPLIED {len(updates)} date fills.")
    elif not apply:
        print("\n(dry run - pass --apply to write)")


if __name__ == "__main__":
    main()
