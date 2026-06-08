#!/usr/bin/env python3
"""Re-sort the tracker by Posted date, newest first, after each finder pass so new jobs surface
at the top instead of piling up at the bottom. Whole rows move together, so the "Will I apply?"
answers stay attached to their row. Blank-Posted rows (web-sourced) sort to the bottom.

Deterministic, no LLM. Delegates to scripts/sheet_io.sort_by_posted(), which uses the Google
Sheets native SortRange request for the sheets backend (a server-side, in-place reorder that
does not overwrite cell values) or an in-memory sort for the CSV backend.
"""
import sheet_io


def main():
    sheet_io.sort_by_posted()
    print("sort: reordered rows by Posted (newest first)")


if __name__ == "__main__":
    main()
