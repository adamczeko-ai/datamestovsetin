"""Idempotentní stahování veřejných datových souborů – jádro pro VSETÍN OSINT.

Stav: PROTOTYP pro vývojové prostředí. Otestováno pouze proti lokálnímu
mock serveru (tests/test_sync_core.py), nikoli proti produkčním zdrojům.

Princip:
  1. Evidence (SQLite tabulka sync_ledger) drží pro každý zdroj+URL poslední
     ETag, Last-Modified, velikost, SHA-256 a výsledek.
  2. Před stažením se posílá podmíněný GET (If-None-Match / If-Modified-Since).
     HTTP 304 => nic se nestahuje, zapíše se jen kontrola.
  3. Po stažení se počítá SHA-256; shodný hash s posledním úspěchem => „beze změny“
     (chrání i u zdrojů bez ETagu, např. dataor.justice.cz).
  4. HTTP 429 a 5xx se opakují s exponenciální prodlevou (respektuje Retry-After).
  5. Každý pokus se loguje, neúspěchy zůstávají v evidenci (status=error).

Pozor: u MONITORu je hlavička Last-Modified generována při každém požadavku
(aktuální čas), proto se pro rozhodování používá primárně ETag.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

USER_AGENT = "VSETIN-OSINT-sync/0.1 (+https://nasvsetin.cz)"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_ledger (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id     TEXT NOT NULL,          -- např. monitor.finm, ruian.vfr.ob
    url           TEXT NOT NULL,
    checked_at    TEXT NOT NULL,          -- ISO 8601 UTC
    http_status   INTEGER,
    etag          TEXT,
    last_modified TEXT,
    size_bytes    INTEGER,
    sha256        TEXT,
    status        TEXT NOT NULL,          -- downloaded | not_modified | unchanged_hash | error
    local_path    TEXT,
    attempts      INTEGER NOT NULL DEFAULT 1,
    error         TEXT
);
CREATE INDEX IF NOT EXISTS ix_ledger_src_url ON sync_ledger(source_id, url, checked_at);
"""


@dataclass
class SyncResult:
    status: str
    http_status: int | None
    sha256: str | None
    local_path: str | None
    attempts: int


def open_ledger(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def last_success(con: sqlite3.Connection, source_id: str, url: str):
    """Poslední záznam, ve kterém máme platná data (stažení nebo potvrzení beze změny)."""
    return con.execute(
        """SELECT etag, last_modified, sha256, local_path, checked_at FROM sync_ledger
           WHERE source_id=? AND url=? AND status IN ('downloaded','not_modified','unchanged_hash')
             AND sha256 IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (source_id, url),
    ).fetchone()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _record(con, source_id, url, **kw):
    cols = ["source_id", "url", "checked_at"] + list(kw)
    vals = [source_id, url, _now()] + list(kw.values())
    con.execute(
        f"INSERT INTO sync_ledger ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals
    )
    con.commit()


def fetch(
    con: sqlite3.Connection,
    source_id: str,
    url: str,
    dest_dir: str,
    *,
    use_last_modified: bool = True,
    max_attempts: int = 5,
    base_delay: float = 2.0,
    timeout: float = 120.0,
    sleep=time.sleep,
) -> SyncResult:
    """Stáhne URL jen pokud se změnila. Vrací SyncResult a zapisuje do evidence."""
    prev = last_success(con, source_id, url)
    headers = {"User-Agent": USER_AGENT}
    if prev:
        if prev[0]:
            headers["If-None-Match"] = prev[0]
        if prev[1] and use_last_modified:
            headers["If-Modified-Since"] = prev[1]

    attempt = 0
    while True:
        attempt += 1
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                etag = resp.headers.get("ETag")
                lm = resp.headers.get("Last-Modified")
                os.makedirs(dest_dir, exist_ok=True)
                h = hashlib.sha256()
                size = 0
                fd, tmp = tempfile.mkstemp(dir=dest_dir, prefix=".part-")
                with os.fdopen(fd, "wb") as f:
                    for chunk in iter(lambda: resp.read(1 << 20), b""):
                        h.update(chunk)
                        size += len(chunk)
                        f.write(chunk)
                digest = h.hexdigest()
                if prev and prev[2] == digest:
                    os.remove(tmp)
                    _record(con, source_id, url, http_status=resp.status, etag=etag,
                            last_modified=lm, size_bytes=size, sha256=digest,
                            status="unchanged_hash", local_path=prev[3], attempts=attempt)
                    return SyncResult("unchanged_hash", resp.status, digest, prev[3], attempt)
                final = os.path.join(dest_dir, f"{digest[:16]}-{os.path.basename(url.split('?')[0]) or 'data'}")
                os.replace(tmp, final)
                _record(con, source_id, url, http_status=resp.status, etag=etag,
                        last_modified=lm, size_bytes=size, sha256=digest,
                        status="downloaded", local_path=final, attempts=attempt)
                return SyncResult("downloaded", resp.status, digest, final, attempt)
        except urllib.error.HTTPError as e:
            if e.code == 304 and prev:
                _record(con, source_id, url, http_status=304, etag=prev[0], last_modified=prev[1],
                        sha256=prev[2], status="not_modified", local_path=prev[3], attempts=attempt)
                return SyncResult("not_modified", 304, prev[2], prev[3], attempt)
            retryable = e.code == 429 or 500 <= e.code < 600
            if retryable and attempt < max_attempts:
                ra = e.headers.get("Retry-After") if e.headers else None
                delay = float(ra) if ra and ra.isdigit() else base_delay * 2 ** (attempt - 1)
                sleep(min(delay, 300))
                continue
            _record(con, source_id, url, http_status=e.code, status="error",
                    attempts=attempt, error=f"HTTP {e.code}")
            return SyncResult("error", e.code, None, None, attempt)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < max_attempts:
                sleep(min(base_delay * 2 ** (attempt - 1), 300))
                continue
            _record(con, source_id, url, status="error", attempts=attempt, error=str(e)[:500])
            return SyncResult("error", None, None, None, attempt)


if __name__ == "__main__":  # ruční použití: python -m sync_core ledger.db source_id url dest
    import sys

    c = open_ledger(sys.argv[1])
    print(json.dumps(fetch(c, sys.argv[2], sys.argv[3], sys.argv[4]).__dict__, ensure_ascii=False))
