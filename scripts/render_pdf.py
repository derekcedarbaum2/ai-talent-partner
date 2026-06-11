#!/usr/bin/env python3
"""Turn tailored HTML into PDF with headless Chrome/Chromium.

The generator (prompts/apply.md) writes resume.html and cover-letter.html into each job
folder by filling templates/resume.html and templates/cover-letter.html. This script is the
deterministic step that renders those HTML files to PDF afterward, run by the scheduler as
`render_pdf.py --all`. It is standard-library only (subprocess + shutil), never crashes the
cron, and no-ops cleanly when rendering is disabled or no browser is installed.

Config (config[render]):
  engine      "chrome" -> render with headless Chrome/Chromium; "none" -> skip, exit 0.
  chrome_path explicit path to a Chrome/Chromium binary; null -> auto-detect.

CLI:
  render_pdf.py <input.html> [output.pdf]   render one file (output defaults to input.pdf)
  render_pdf.py --all [applications_dir]    walk the dir, render every resume.html and
                                            cover-letter.html lacking an up-to-date .pdf
                                            (applications_dir defaults to config)
"""
import os
import shutil
import subprocess
import sys
from urllib.parse import quote

import config_lib as C

# Common Chrome/Chromium locations to probe when render.chrome_path is not set.
MAC_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
LINUX_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]

# The two HTML files the generator produces per job folder.
RENDER_NAMES = ["resume.html", "cover-letter.html"]


def find_chrome(explicit=None):
    """Return a path to a Chrome/Chromium binary, or None. Honors an explicit path first,
    then probes the common macOS app locations and the usual Linux binary names on PATH."""
    if explicit:
        p = os.path.expanduser(explicit)
        if os.path.exists(p):
            return p
        # An explicit name (not a path) may still resolve on PATH.
        w = shutil.which(explicit)
        if w:
            return w
        return None
    for p in MAC_PATHS:
        if os.path.exists(p):
            return p
    for name in LINUX_NAMES:
        w = shutil.which(name)
        if w:
            return w
    return None


def render_one(chrome, html_path, pdf_path):
    """Render a single HTML file to pdf_path with headless Chrome. Tries the modern
    --headless=new first and falls back to legacy --headless. Returns True on success."""
    html_abs = os.path.abspath(html_path)
    pdf_abs = os.path.abspath(pdf_path)
    # Percent-encode the path so '#'/'%' (and spaces) in folder names survive as a file:// URL.
    file_url = "file://" + quote(html_abs)
    base = [
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf=" + pdf_abs,
        file_url,
    ]
    for headless in ("--headless=new", "--headless"):
        cmd = [chrome, headless] + base
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"  render error ({headless}): {e}")
            continue
        if r.returncode == 0 and os.path.exists(pdf_abs):
            return True
        msg = (r.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        tail = msg[-1] if msg else f"exit {r.returncode}"
        print(f"  {headless} failed: {tail}")
    return False


def _is_stale(pdf_path, html_path):
    """A PDF is up to date when it exists and is at least as new as its HTML source."""
    if not os.path.exists(pdf_path):
        return True
    return os.path.getmtime(pdf_path) < os.path.getmtime(html_path)


def render_all(chrome, applications_dir):
    """Walk applications_dir and render every resume.html / cover-letter.html whose PDF
    sibling is missing or older than the HTML. Returns (rendered, skipped, failed) counts."""
    rendered = skipped = failed = 0
    for root, _dirs, files in os.walk(applications_dir):
        for name in RENDER_NAMES:
            if name not in files:
                continue
            html_path = os.path.join(root, name)
            pdf_path = os.path.splitext(html_path)[0] + ".pdf"
            if not _is_stale(pdf_path, html_path):
                skipped += 1
                continue
            print(f"rendering {html_path}")
            if render_one(chrome, html_path, pdf_path):
                rendered += 1
            else:
                failed += 1
    return rendered, skipped, failed


def main(argv):
    cfg = C.load()
    render = C.get(cfg, "render", {}) or {}
    engine = (render.get("engine") or "chrome").strip().lower()

    if engine == "none":
        print("render: engine is 'none', skipping PDF generation (HTML/markdown kept).")
        return 0

    chrome = find_chrome(render.get("chrome_path"))
    if not chrome:
        print("render: no Chrome/Chromium found. Install Google Chrome or Chromium, set "
              "render.chrome_path in config, or set render.engine='none' to skip PDF.")
        return 0

    args = [a for a in argv if a]

    if args and args[0] == "--all":
        applications_dir = args[1] if len(args) > 1 else C.repo_path(C.get(cfg, "applications_dir"))
        if not applications_dir or not os.path.isdir(applications_dir):
            print(f"render: applications_dir not found: {applications_dir}")
            return 0
        rendered, skipped, failed = render_all(chrome, applications_dir)
        print(f"render: {rendered} rendered, {skipped} up to date, {failed} failed "
              f"(via {os.path.basename(chrome)}).")
        return 0

    if args:
        html_path = args[0]
        if not os.path.isfile(html_path):
            print(f"render: input not found: {html_path}")
            return 1
        pdf_path = args[1] if len(args) > 1 else os.path.splitext(html_path)[0] + ".pdf"
        print(f"rendering {html_path} -> {pdf_path}")
        ok = render_one(chrome, html_path, pdf_path)
        if ok:
            print("render: done.")
            return 0
        print("render: failed.")
        return 1

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
