"""Dokumenty města → text po stranách s kontrolním otiskem (vstup pro LLM vrstvu „nesoulady“).

Vstup: seznam URL (soubor, 1 záznam na řádek: "URL" nebo "source_id<TAB>URL"; '#' = komentář).
Pro každý dokument:
  1. stáhne originál přes Http.fetch (podmíněně, evidence v sync_ledger, SHA-256 celého souboru),
  2. vytáhne text po stranách do  <texty_dir>/<sha256>/p<N>.txt  (N od 1),
  3. zapíše  <texty_dir>/<sha256>/meta.json  a řádek tabulky `dokument_text`.
Idempotence: stejný obsah (SHA-256) = stejná složka; existující meta.json se stejnou verzí extrakce se nepřepisuje.
Formáty: PDF (pdftotext, záložně pypdf), HTML (1 strana), ZIP (každý PDF/HTML člen jako samostatný
dokument s URL "<zip_url>#<člen>").
PDF bez textové vrstvy (sken) se označí `textova_vrstva: false` – OCR se NEprovádí (vyžaduje schválení).

Citace v LLM vrstvě: zdroj = "raw/texty/<sha256>/p<N>.txt", strana = N.
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

from ..http import Http, now_utc
from ..db import upsert

SOURCE_ID = "dokumenty.mesto"
EXTRAKCE_VERZE = "texty@1"
MIN_ZNAKU_NA_STRANU = 25  # méně = stránka bez textové vrstvy (sken / obrázek)

SCHEMA = """
CREATE TABLE IF NOT EXISTS dokument_text (
  sha256 TEXT NOT NULL, url TEXT NOT NULL, source_id TEXT, typ TEXT, pocet_stran INTEGER,
  stran_s_textem INTEGER, textova_vrstva INTEGER, extraktor TEXT, extrakce_verze TEXT,
  slozka TEXT, stazeno_utc TEXT, imported_at TEXT NOT NULL,
  PRIMARY KEY (sha256, url)
);
"""


# ------------------------------------------------------------------ extrakce
def _typ(nazev: str, data: bytes) -> str:
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:4] == b"PK\x03\x04":
        return "zip"
    low = nazev.lower()
    head = data[:2048].lower()
    if low.endswith((".html", ".htm")) or b"<html" in head or b"<!doctype html" in head:
        return "html"
    return "jine"


def _pdftotext(data: bytes) -> list[str] | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    r = subprocess.run([exe, "-layout", "-enc", "UTF-8", "-", "-"], input=data, capture_output=True, timeout=300)
    if r.returncode != 0:
        return None
    pages = r.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]  # pdftotext končí form-feedem
    return pages


def _pypdf(data: bytes) -> list[str] | None:
    try:
        from pypdf import PdfReader  # volitelná závislost
    except ImportError:
        return None
    try:
        return [(p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages]
    except Exception:
        return None


def text_pdf(data: bytes) -> tuple[list[str], str]:
    for fn, name in ((_pdftotext, "pdftotext"), (_pypdf, "pypdf")):
        pages = fn(data)
        if pages is not None:
            return pages, name
    raise RuntimeError("Chybí extraktor PDF: nainstalujte poppler-utils (pdftotext) nebo pypdf.")


def text_html(data: bytes) -> list[str]:
    t = data.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = "\n".join(re.sub(r"[ \t ]+", " ", ln).strip() for ln in t.splitlines())
    return [re.sub(r"\n{3,}", "\n\n", t).strip()]


# ------------------------------------------------------------------ zápis
def uloz(texty_dir: str, url: str, data: bytes, *, source_id: str = SOURCE_ID, stazeno_utc: str | None = None,
         nazev: str = "") -> list[dict]:
    """Uloží text dokumentu (nebo členů ZIP). Vrací seznam meta záznamů."""
    typ = _typ(nazev or url, data)
    if typ == "zip":
        out = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for clen in sorted(z.namelist()):
                if clen.endswith("/") or not clen.lower().endswith((".pdf", ".html", ".htm")):
                    continue
                out += uloz(texty_dir, f"{url}#{clen}", z.read(clen), source_id=source_id,
                            stazeno_utc=stazeno_utc, nazev=clen)
        return out
    sha = hashlib.sha256(data).hexdigest()
    slozka = os.path.join(texty_dir, sha)
    meta_p = os.path.join(slozka, "meta.json")
    if os.path.exists(meta_p):
        with open(meta_p, encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("extrakce_verze") == EXTRAKCE_VERZE:
            if url not in meta["url"]:
                meta["url"].append(url)  # stejný obsah publikovaný pod další adresou
                with open(meta_p, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=1)
            return [dict(meta, _nove=False)]
    if typ == "pdf":
        pages, extraktor = text_pdf(data)
    elif typ == "html":
        pages, extraktor = text_html(data), "html"
    else:
        return [{"url": [url], "sha256": sha, "typ": typ, "preskoceno": "nepodporovaný formát", "_nove": False}]
    tmp = slozka + ".part"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    s_textem = 0
    for i, p in enumerate(pages, 1):
        p = p.replace("\r\n", "\n")
        if len(re.sub(r"\s", "", p)) >= MIN_ZNAKU_NA_STRANU:
            s_textem += 1
        with open(os.path.join(tmp, f"p{i}.txt"), "w", encoding="utf-8") as f:
            f.write(p)
    utc = stazeno_utc or now_utc()
    try:
        praha = datetime.fromisoformat(utc).astimezone(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")
    except ValueError:
        praha = None
    meta = {"schema": "vsetin-osint/dokument-text@1", "sha256": sha, "url": [url], "source_id": source_id,
            "typ": typ, "pocet_stran": len(pages), "stran_s_textem": s_textem,
            "textova_vrstva": s_textem > 0 and s_textem >= len(pages) / 2,
            "extraktor": extraktor, "extrakce_verze": EXTRAKCE_VERZE,
            "stazeno_utc": utc, "stazeno_praha": praha, "velikost_bajtu": len(data),
            "poznamka": None if s_textem else "bez textové vrstvy – nutné OCR (neprovádí se bez schválení)"}
    with open(os.path.join(tmp, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    shutil.rmtree(slozka, ignore_errors=True)
    os.replace(tmp, slozka)  # atomicky: buď celá složka, nebo nic
    return [dict(meta, _nove=True)]


def nacti_seznam(path: str) -> list[tuple[str, str]]:
    out = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            sid, _, url = ln.partition("\t") if "\t" in ln else (SOURCE_ID, "", ln)
            out.append((sid.strip() or SOURCE_ID, url.strip()))
    return out


def sync(con, http: Http, seznam: list[tuple[str, str]], texty_dir: str) -> dict:
    con.executescript(SCHEMA)
    os.makedirs(texty_dir, exist_ok=True)
    stat = {"dokumentu": 0, "nove_texty": 0, "beze_zmeny": 0, "bez_textove_vrstvy": [], "chyby": []}
    for sid, url in seznam:
        f = http.fetch(sid, url)
        if f.status == "error" or not f.path:
            stat["chyby"].append({"url": url, "chyba": f.error})
            continue
        with open(f.path, "rb") as fh:
            data = fh.read()
        try:
            metas = uloz(texty_dir, url, data, source_id=sid, nazev=os.path.basename(f.path))
        except Exception as e:  # jeden dokument nesmí zastavit ostatní
            stat["chyby"].append({"url": url, "chyba": f"{type(e).__name__}: {e}"[:300]})
            continue
        rows = []
        for m in metas:
            stat["dokumentu"] += 1
            if m.get("preskoceno"):
                stat["chyby"].append({"url": m["url"][0], "chyba": m["preskoceno"]})
                continue
            stat["nove_texty" if m["_nove"] else "beze_zmeny"] += 1
            if not m["textova_vrstva"]:
                stat["bez_textove_vrstvy"].append(m["url"][-1])
            for u in m["url"]:
                rows.append(dict(sha256=m["sha256"], url=u, source_id=m["source_id"], typ=m["typ"],
                                 pocet_stran=m["pocet_stran"], stran_s_textem=m["stran_s_textem"],
                                 textova_vrstva=int(m["textova_vrstva"]), extraktor=m["extraktor"],
                                 extrakce_verze=m["extrakce_verze"], slozka=os.path.join(texty_dir, m["sha256"]),
                                 stazeno_utc=m["stazeno_utc"], imported_at=now_utc()))
        upsert(con, "dokument_text", rows)
        con.commit()
    return stat
