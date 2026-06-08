#!/usr/bin/env python3
"""Scan the tracker for rows marked "Will I apply?" = Yes that do not yet have application
materials, and write state/apply_queue.json for the generator. Deterministic, no LLM. Reads
through scripts/sheet_io.py, so it works against either backend.

A job is considered already handled once its URL appears in state/generated.json (written by
apply_mark.py after its materials are fully generated), so nothing is queued twice.
"""
import json
import os

import config_lib as C
import sheet_io


def main():
    cfg = C.load()
    state = os.path.join(C.REPO_ROOT, "state")
    os.makedirs(state, exist_ok=True)
    gen_path = os.path.join(state, "generated.json")
    done = set(json.load(open(gen_path))) if os.path.exists(gen_path) else set()

    queue = []
    for r in sheet_io.read_rows():
        apply = (r.get("Will I apply?") or "").strip().lower()
        url = (r.get("Job URL") or "").strip()
        if apply.startswith("y") and url and url not in done:
            queue.append({"date_found": r.get("Date Found", ""), "company": r.get("Company", ""),
                          "title": r.get("Job Title", ""), "location": r.get("Location", ""),
                          "posted": r.get("Posted", ""), "url": url, "source": r.get("Source", "")})

    json.dump(queue, open(os.path.join(state, "apply_queue.json"), "w"), indent=2)
    print(f"apply-scan: {len(queue)} job(s) marked Yes needing materials "
          f"({len(done)} already generated)")
    for q in queue:
        print(f"  -> {q['company']} - {q['title']}")


if __name__ == "__main__":
    main()
