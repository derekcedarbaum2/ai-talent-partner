#!/usr/bin/env python3
"""Single abstraction over the spreadsheet backend. Every other script reads and writes the
job tracker through this module, so nothing else knows or cares whether the store is a local
CSV file or a Google Sheet. The backend is chosen by config["backend"] ("csv" | "google_sheets").

Public API (identical for both backends):
    read_rows()            -> list of dicts, one per data row, keyed by HEADER, plus "_rownum"
                              (1-based, header is row 1, so the first data row is _rownum 2).
    get_existing_urls()    -> set of Job URL values already in the store (for de-dup).
    append_rows(rows)      -> append rows. Each row is a list aligned to HEADER, or a dict.
    update_cells(updates)  -> apply [{"rownum": int, "col": "Posted", "value": "2026-06-01"}].
    delete_rows(rownums)   -> delete the given 1-based row numbers.
    sort_by_posted()       -> reorder data rows by the Posted column, newest first.

Row numbering is 1-based with the header at row 1 to match Google Sheets' native numbering,
so the same _rownum values work against either backend.

Google Sheets auth uses an OAuth refresh-token grant. The token file path comes from
config["google_token_path"] (default ~/.config/ai-talent-partner/google_token.json)
and must contain client_id, client_secret, and refresh_token. See docs/SETUP.md.

The CSV backend writes atomically (temp file + os.replace) and serializes read-modify-write
cycles with an fcntl flock on a lockfile next to the CSV, so concurrent finder/apply runs
cannot drop rows. POSIX-only (this project targets macOS/Linux).
"""
import contextlib
import csv
import fcntl
import json
import os
import tempfile
import urllib.parse
import urllib.request

import config_lib as C

HEADER = C.HEADER
N = C.N_COLS
_COL_IDX = {name: i for i, name in enumerate(HEADER)}


# --------------------------------------------------------------------------------------------
# Helpers shared by both backends
# --------------------------------------------------------------------------------------------
def _row_to_list(row):
    """Accept a dict (keyed by HEADER) or a list; return a HEADER-aligned list of strings."""
    if isinstance(row, dict):
        return [str(row.get(h, "") or "") for h in HEADER]
    row = list(row) + [""] * N
    return [str(x or "") for x in row[:N]]


def _list_to_dict(values, rownum):
    values = (list(values) + [""] * N)[:N]
    d = {HEADER[i]: values[i] for i in range(N)}
    d["_rownum"] = rownum
    return d


# --------------------------------------------------------------------------------------------
# CSV backend
# --------------------------------------------------------------------------------------------
class _CsvBackend:
    def __init__(self, cfg):
        self.path = C.repo_path(C.get(cfg, "csv_path", "./data/jobs.csv"))
        self.lock_path = self.path + ".lock"

    @contextlib.contextmanager
    def _locked(self):
        """Exclusive flock on a lockfile next to the CSV, held across each read-modify-write
        cycle so concurrent finder/apply runs cannot interleave and drop rows."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.lock_path, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def _ensure(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(HEADER)

    def _read_all(self):
        """Return the raw list of data rows (lists), header excluded."""
        self._ensure()
        with open(self.path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        return rows[1:] if rows else []

    def _write_all(self, data_rows):
        """Atomic rewrite: write a temp file in the same directory, then os.replace() it over
        the CSV so readers never see a partially written file."""
        self._ensure()
        d = os.path.dirname(self.path) or "."
        fd, tmp = tempfile.mkstemp(prefix=os.path.basename(self.path) + ".", suffix=".tmp", dir=d)
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(HEADER)
                for r in data_rows:
                    w.writerow((list(r) + [""] * N)[:N])
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise

    def read_rows(self):
        return [_list_to_dict(r, i + 2) for i, r in enumerate(self._read_all())]

    def get_existing_urls(self):
        out = set()
        for r in self._read_all():
            r = (list(r) + [""] * N)[:N]
            u = r[_COL_IDX["Job URL"]].strip()
            if u:
                out.add(u)
        return out

    def append_rows(self, rows):
        if not rows:
            return
        with self._locked():
            self._ensure()
            with open(self.path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                for r in rows:
                    w.writerow(_row_to_list(r))

    def update_cells(self, updates):
        if not updates:
            return
        with self._locked():
            data = self._read_all()
            for up in updates:
                idx = up["rownum"] - 2     # rownum 2 -> data index 0
                col = _COL_IDX[up["col"]] if isinstance(up["col"], str) else up["col"]
                if 0 <= idx < len(data):
                    row = (list(data[idx]) + [""] * N)[:N]
                    row[col] = str(up["value"])
                    data[idx] = row
            self._write_all(data)

    def delete_rows(self, rownums):
        if not rownums:
            return
        with self._locked():
            drop = {rn - 2 for rn in rownums}
            data = [r for i, r in enumerate(self._read_all()) if i not in drop]
            self._write_all(data)

    def sort_by_posted(self):
        pi = _COL_IDX["Posted"]

        def key(r):
            r = (list(r) + [""] * N)[:N]
            return r[pi].strip()

        with self._locked():
            data = self._read_all()
            # Newest first; blank Posted sorts to the bottom (empty string sorts last under reverse).
            with_date = [r for r in data if key(r)]
            without = [r for r in data if not key(r)]
            with_date.sort(key=key, reverse=True)
            self._write_all(with_date + without)


# --------------------------------------------------------------------------------------------
# Google Sheets backend (REST API + OAuth refresh-token grant)
# --------------------------------------------------------------------------------------------
class _GoogleSheetsBackend:
    RANGE = "Sheet1!A2:H"
    TAB = "Sheet1"

    def __init__(self, cfg):
        self.sheet_id = C.get(cfg, "google_sheet_id")
        if not self.sheet_id or "PASTE" in str(self.sheet_id):
            raise RuntimeError("google_sheet_id is not set in config.json")
        self.token_path = C.repo_path(
            C.get(cfg, "google_token_path", "~/.config/ai-talent-partner/google_token.json"))
        self._at = None
        self._gid_cache = None

    def _access_token(self):
        if self._at:
            return self._at
        tok = json.load(open(self.token_path))
        # Token file may inline client creds, or nest them under "installed"/"web" (the shape
        # Google's downloaded OAuth client JSON uses). Support both.
        client = tok.get("installed") or tok.get("web") or tok
        data = urllib.parse.urlencode({
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "refresh_token": tok["refresh_token"],
            "grant_type": "refresh_token",
        }).encode()
        r = urllib.request.urlopen(
            urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=20)
        self._at = json.load(r)["access_token"]
        return self._at

    def _base(self):
        return f"https://sheets.googleapis.com/v4/spreadsheets/{self.sheet_id}"

    def _api(self, method, url, body=None):
        at = self._access_token()
        headers = {"Authorization": "Bearer " + at}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            url, method=method, headers=headers,
            data=json.dumps(body).encode() if body is not None else None)
        return json.load(urllib.request.urlopen(req, timeout=60))

    def _gid(self):
        """Resolve (and cache) the sheetId of the tab titled Sheet1. Values calls address the
        tab by name, but batchUpdate (delete/sort) needs the numeric sheetId, which is NOT
        always 0 -- assuming 0 would hit the wrong tab."""
        if self._gid_cache is None:
            meta = self._api("GET", self._base() + "?fields=sheets(properties(sheetId,title))")
            for sh in meta.get("sheets", []):
                props = sh.get("properties", {})
                if props.get("title") == self.TAB:
                    self._gid_cache = props.get("sheetId")
                    break
            if self._gid_cache is None:
                raise RuntimeError(
                    f"no tab titled {self.TAB!r} in spreadsheet {self.sheet_id}; the engine "
                    f"reads and writes the tab named {self.TAB} -- rename your tab or add one")
        return self._gid_cache

    def _values(self):
        url = self._base() + "/values/" + urllib.parse.quote(self.RANGE) + "?majorDimension=ROWS"
        return self._api("GET", url).get("values", [])

    def read_rows(self):
        return [_list_to_dict(r, i + 2) for i, r in enumerate(self._values())]

    def get_existing_urls(self):
        out = set()
        for r in self._values():
            r = (list(r) + [""] * N)[:N]
            u = (r[_COL_IDX["Job URL"]] or "").strip()
            if u:
                out.add(u)
        return out

    def append_rows(self, rows):
        if not rows:
            return
        body = {"values": [_row_to_list(r) for r in rows]}
        url = (self._base() + "/values/" + urllib.parse.quote("Sheet1!A1")
               + ":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS")
        self._api("POST", url, body)

    def update_cells(self, updates):
        if not updates:
            return
        data = []
        for up in updates:
            col = up["col"]
            if not isinstance(col, str):
                col = HEADER[col]
            col_letter = chr(ord("A") + _COL_IDX[col])
            data.append({"range": f"Sheet1!{col_letter}{up['rownum']}", "values": [[str(up["value"])]]})
        body = {"valueInputOption": "RAW", "data": data}
        self._api("POST", self._base() + "/values:batchUpdate", body)

    def delete_rows(self, rownums):
        if not rownums:
            return
        # Delete descending so earlier indices stay valid. rownum is 1-based; API is 0-based.
        gid = self._gid()
        reqs = [{"deleteDimension": {"range": {"sheetId": gid, "dimension": "ROWS",
                 "startIndex": rn - 1, "endIndex": rn}}} for rn in sorted(rownums, reverse=True)]
        self._api("POST", self._base() + ":batchUpdate", {"requests": reqs})

    def sort_by_posted(self):
        # Count data rows via column A, then SortRange server-side (whole rows move together so
        # the "Will I apply?" answers stay attached). Posted is column index 4; sort all 8 cols.
        got = self._api("GET", self._base() + "/values/"
                        + urllib.parse.quote("Sheet1!A:A") + "?majorDimension=COLUMNS")
        vals = got.get("values", [[]])
        n = len(vals[0]) if vals else 0
        if n <= 1:
            return
        body = {"requests": [{"sortRange": {
            "range": {"sheetId": self._gid(), "startRowIndex": 1, "endRowIndex": n,
                      "startColumnIndex": 0, "endColumnIndex": N},
            "sortSpecs": [{"dimensionIndex": _COL_IDX["Posted"], "sortOrder": "DESCENDING"}],
        }}]}
        self._api("POST", self._base() + ":batchUpdate", body)


# --------------------------------------------------------------------------------------------
# Backend factory + module-level convenience functions
# --------------------------------------------------------------------------------------------
_BACKEND = None


def backend(cfg=None):
    global _BACKEND
    if _BACKEND is not None and cfg is None:
        return _BACKEND
    if cfg is None:
        cfg = C.load()
    kind = C.get(cfg, "backend", "csv")
    if kind == "csv":
        b = _CsvBackend(cfg)
    elif kind == "google_sheets":
        b = _GoogleSheetsBackend(cfg)
    else:
        raise RuntimeError(f"unknown backend: {kind!r} (expected 'csv' or 'google_sheets')")
    _BACKEND = b
    return b


def read_rows():
    return backend().read_rows()


def get_existing_urls():
    return backend().get_existing_urls()


def append_rows(rows):
    return backend().append_rows(rows)


def update_cells(updates):
    return backend().update_cells(updates)


def delete_rows(rownums):
    return backend().delete_rows(rownums)


def sort_by_posted():
    return backend().sort_by_posted()
