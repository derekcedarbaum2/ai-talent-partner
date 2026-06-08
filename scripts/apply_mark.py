#!/usr/bin/env python3
"""After the generator runs, mark jobs whose materials are fully written. A job counts as done
only if its output folder under config[applications_dir] holds all three required files. Partials
are left unmarked so they retry next run.

Run by the scheduler (not the sandboxed model step), so it can write the state file. Deterministic,
no LLM. The output folder name is "<Company> - <Title>" with filesystem-illegal characters stripped.
"""
import json
import os
import re

import config_lib as C

REQUIRED = ("resume.md", "cover-letter.md", "application-questions.md")


def folder_for(apps_dir, company, title):
    name = f"{company} - {title}"
    name = re.sub(r'[/\\:*?"<>|]', "", name)
    name = re.sub(r'\s+', " ", name).strip()
    return os.path.join(apps_dir, name)


def main():
    cfg = C.load()
    apps_dir = C.repo_path(C.get(cfg, "applications_dir", "./applications"))
    state = os.path.join(C.REPO_ROOT, "state")
    qpath = os.path.join(state, "apply_queue.json")
    if not os.path.exists(qpath):
        print("mark: no queue")
        return
    queue = json.load(open(qpath))
    gen_path = os.path.join(state, "generated.json")
    os.makedirs(state, exist_ok=True)
    done = set(json.load(open(gen_path))) if os.path.exists(gen_path) else set()

    newly = 0
    for j in queue:
        folder = folder_for(apps_dir, j["company"], j["title"])
        if all(os.path.exists(os.path.join(folder, f)) for f in REQUIRED) and j["url"] not in done:
            done.add(j["url"])
            newly += 1

    json.dump(sorted(done), open(gen_path, "w"), indent=2)
    print(f"mark: {newly} job(s) marked complete ({len(done)} total tracked)")


if __name__ == "__main__":
    main()
