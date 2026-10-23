"""HTTP vrstva: podmíněné stahování s evidencí, opakování, Range požadavky.

Pravidla (ověřeno 22.–23. 10. 2026):
- MONITOR: ETag spolehlivý (nginx mtime-size), Last-Modified je falešný (aktuální čas) → posílat jen If-None-Match.
- RÚIAN VFR, RVZ: ETag i Last-Modified platné, 304 funguje.
- dataor.justice.cz: bez ETag/Last-Modified → rozhoduje SHA-256.
- 429/5xx: exponenciální prodleva, respektuje Retry-After.
- robots=True: před prvním požadavkem na hostitele načte robots.txt; zakázané URL nestahuje
  a Crawl-delay prodlouží interval mezi požadavky. Nedostupný robots.txt (síť, 5xx) = hostitel
  zakázán (konzervativní pravidlo); 404 = vše povoleno.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone

USER_AGENT = "VSETIN-OSINT-integrace/0.1 (+https://nasvsetin.cz)"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Fetched:
    status: str            # downloaded | not_modified | unchanged_hash | error
    http_status: int | None
    path: str | None       # lokální soubor s obsahem (i u not_modified – poslední verze)
    sha256: str | None
    etag: str | None
    attempts: int
    error: str | None = None

    @property
    def changed(self) -> bool:
        return self.status == "downloaded"


class RobotsDenied(Exception):
    """URL zakázaná v robots.txt (nebo robots.txt nedostupný)."""


class Http:
    def __init__(self, con: sqlite3.Connection | None, cache_dir: str, *, min_interval: float = 1.0,
                 max_attempts: int = 5, base_delay: float = 2.0, timeout: float = 300.0, sleep=time.sleep,
                 opener=None, user_agent: str = USER_AGENT, robots: bool = False):
        self.con = con  # None = bez evidence v SQLite (sběr do JSONL, scripts/sber.py)
        self.user_agent = user_agent
        self.robots = robots
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._interval: dict[str, float] = {}
        self.cache_dir = cache_dir
        self.min_interval = min_interval
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.timeout = timeout
        self.sleep = sleep
        self._last: dict[str, float] = {}
        self.opener = opener or urllib.request.build_opener()
        os.makedirs(cache_dir, exist_ok=True)

    # --- rate limit na hostitele ---
    def _throttle(self, url: str):
        host = url.split("/")[2]
        wait = self._last.get(host, 0) + self._interval.get(host, self.min_interval) - time.monotonic()
        if wait > 0:
            self.sleep(wait)
        self._last[host] = time.monotonic()

    # --- robots.txt ---
    def _robots_for(self, url: str):
        scheme, _, host = url.split("/")[:3]
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{scheme}//{host}/robots.txt"
            try:
                self._throttle(robots_url)
                req = urllib.request.Request(robots_url, headers={"User-Agent": self.user_agent})
                with self.opener.open(req, timeout=min(self.timeout, 60)) as r:
                    rp.parse(r.read().decode("utf-8", "replace").splitlines())
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    rp.parse([])  # robots.txt neexistuje -> vše povoleno
                else:
                    rp = None
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                rp = None
            self._robots[host] = rp
            if rp is not None:
                cd = rp.crawl_delay(self.user_agent)
                if cd:
                    self._interval[host] = max(self.min_interval, float(cd))
        return self._robots[host]

    def check_robots(self, url: str):
        """Vyvolá RobotsDenied, pokud robots.txt URL zakazuje nebo není dostupný."""
        if not self.robots:
            return
        rp = self._robots_for(url)
        if rp is None:
            raise RobotsDenied(f"robots.txt hostitele {url.split('/')[2]} nedostupný – stahování vynecháno")
        if not rp.can_fetch(self.user_agent, url):
            raise RobotsDenied(f"zakázáno v robots.txt: {url}")

    def _open(self, url: str, headers: dict, method: str = "GET"):
        """Otevře URL s opakováním při 429/5xx a síťových chybách. Vrací (resp|HTTPError, attempts)."""
        self.check_robots(url)
        attempt = 0
        while True:
            attempt += 1
            self._throttle(url)
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent, **headers}, method=method)
            try:
                return self.opener.open(req, timeout=self.timeout), attempt
            except urllib.error.HTTPError as e:
                if (e.code == 429 or 500 <= e.code < 600) and attempt < self.max_attempts:
                    ra = e.headers.get("Retry-After") if e.headers else None
                    self.sleep(min(float(ra) if ra and ra.isdigit() else self.base_delay * 2 ** (attempt - 1), 300))
                    continue
                return e, attempt
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                if attempt < self.max_attempts:
                    self.sleep(min(self.base_delay * 2 ** (attempt - 1), 300))
                    continue
                raise

    # --- evidence ---
    def _last_ok(self, source_id: str, url: str):
        if self.con is None:
            return None
        return self.con.execute(
            """SELECT etag, last_modified, sha256, local_path FROM sync_ledger
               WHERE source_id=? AND url=? AND status IN ('downloaded','not_modified','unchanged_hash')
                 AND sha256 IS NOT NULL ORDER BY id DESC LIMIT 1""", (source_id, url)).fetchone()

    def _log(self, source_id, url, **kw):
        if self.con is None:
            return
        cols = ["source_id", "url", "checked_at", *kw]
        self.con.execute(f"INSERT INTO sync_ledger ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                         [source_id, url, now_utc(), *kw.values()])
        self.con.commit()

    def fetch(self, source_id: str, url: str, *, use_etag=True, use_last_modified=True) -> Fetched:
        """Celý soubor, jen pokud se změnil (304 / shodný hash → beze stahování / bez nové kopie)."""
        prev = self._last_ok(source_id, url)
        if prev and prev[3] and not os.path.exists(prev[3]):
            prev = None  # cache smazána → stáhnout znovu
        headers = {}
        if prev:
            if use_etag and prev[0]:
                headers["If-None-Match"] = prev[0]
            if use_last_modified and prev[1]:
                headers["If-Modified-Since"] = prev[1]
        try:
            resp, attempts = self._open(url, headers)
        except Exception as e:  # síť
            self._log(source_id, url, status="error", attempts=self.max_attempts, error=str(e)[:500])
            return Fetched("error", None, None, None, None, self.max_attempts, str(e))
        if isinstance(resp, urllib.error.HTTPError):
            if resp.code == 304 and prev:
                self._log(source_id, url, http_status=304, etag=prev[0], last_modified=prev[1], sha256=prev[2],
                          status="not_modified", local_path=prev[3], attempts=attempts)
                return Fetched("not_modified", 304, prev[3], prev[2], prev[0], attempts)
            self._log(source_id, url, http_status=resp.code, status="error", attempts=attempts, error=f"HTTP {resp.code}")
            return Fetched("error", resp.code, None, None, None, attempts, f"HTTP {resp.code}")
        with resp:
            etag, lm = resp.headers.get("ETag"), resp.headers.get("Last-Modified")
            h, size = hashlib.sha256(), 0
            fd, tmp = tempfile.mkstemp(dir=self.cache_dir, prefix=".part-")
            with os.fdopen(fd, "wb") as f:
                for chunk in iter(lambda: resp.read(1 << 20), b""):
                    h.update(chunk); size += len(chunk); f.write(chunk)
        digest = h.hexdigest()
        if prev and prev[2] == digest:
            os.remove(tmp)
            self._log(source_id, url, http_status=200, etag=etag, last_modified=lm if use_last_modified else None,
                      size_bytes=size, sha256=digest, status="unchanged_hash", local_path=prev[3], attempts=attempts)
            return Fetched("unchanged_hash", 200, prev[3], digest, etag, attempts)
        name = os.path.basename(url.split("?")[0]) or "data"
        final = os.path.join(self.cache_dir, f"{digest[:16]}-{name}")
        os.replace(tmp, final)
        self._log(source_id, url, http_status=200, etag=etag, last_modified=lm if use_last_modified else None,
                  size_bytes=size, sha256=digest, status="downloaded", local_path=final, attempts=attempts)
        return Fetched("downloaded", 200, final, digest, etag, attempts)

    def head(self, url: str) -> dict:
        resp, _ = self._open(url, {}, method="HEAD")
        if isinstance(resp, urllib.error.HTTPError):
            return {"status": resp.code}
        with resp:
            return {"status": resp.status, "etag": resp.headers.get("ETag"),
                    "length": int(resp.headers.get("Content-Length") or 0),
                    "accept_ranges": resp.headers.get("Accept-Ranges")}

    def get_range(self, url: str, start: int, end: int) -> bytes:
        resp, _ = self._open(url, {"Range": f"bytes={start}-{end}"})
        if isinstance(resp, urllib.error.HTTPError):
            raise RuntimeError(f"HTTP {resp.code} pro Range {url}")
        with resp:
            data = resp.read()
            if resp.status == 200 and (end - start + 1) < len(data):
                data = data[start:end + 1]  # server Range ignoroval
            return data

    def get_bytes(self, url: str, headers: dict | None = None) -> bytes:
        resp, _ = self._open(url, headers or {})
        if isinstance(resp, urllib.error.HTTPError):
            raise RuntimeError(f"HTTP {resp.code}: {url}")
        with resp:
            return resp.read()
