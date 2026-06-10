#!/usr/bin/env python3
"""Shared config loader for the engine. Reads config/config.json (falling back to
config/config.example.json so the scripts can be imported before setup runs), resolves
every path relative to the repo root, and exposes a few small helpers the other scripts
share (HTTP user-agent, an SSL context that tolerates the odd misconfigured careers site,
and the canonical 8-column sheet header).

No hardcoded sheet IDs and no absolute user paths live anywhere in the engine: everything
flows from config. REPO_ROOT is the parent of this scripts/ directory.
"""
import json, os, ssl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

# Canonical sheet/CSV columns, in order. Every backend reads and writes exactly these.
HEADER = ["Date Found", "Company", "Job Title", "Location", "Posted", "Job URL", "Source", "Will I apply?"]
N_COLS = len(HEADER)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def ssl_ctx(cfg=None):
    """TLS context for all engine HTTP. Verified by default. Set "insecure_tls": true in
    config.json to disable certificate verification for the odd careers site with a broken
    chain (the engine only ever GETs public job data)."""
    if cfg is None:
        cfg = load()
    c = ssl.create_default_context()
    if get(cfg, "insecure_tls", False):
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
    return c


def repo_path(p):
    """Resolve a config-relative path against the repo root. Absolute paths pass through.
    '~' is expanded so tokens and data dirs can live under the user's home if desired."""
    if not p:
        return p
    p = os.path.expanduser(p)
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(REPO_ROOT, p))


_CACHE = None


def load(path=None):
    """Load and cache config/config.json. Falls back to config/config.example.json when the
    real config does not exist yet, so importing engine modules never hard-fails pre-setup."""
    global _CACHE
    if _CACHE is not None and path is None:
        return _CACHE
    if path is None:
        real = os.path.join(REPO_ROOT, "config", "config.json")
        example = os.path.join(REPO_ROOT, "config", "config.example.json")
        path = real if os.path.exists(real) else example
    with open(path) as f:
        cfg = json.load(f)
    # Strip the leading-underscore documentation keys so callers see only live settings.
    cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
    if path.endswith("config.json"):
        _CACHE = cfg
    return cfg


def get(cfg, key, default=None):
    """config.get with the underscore-comment keys already stripped by load()."""
    return cfg.get(key, default)
