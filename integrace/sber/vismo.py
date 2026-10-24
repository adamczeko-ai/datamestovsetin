"""Parsery webu města Vsetín (CMS vismo, www.mestovsetin.cz).

Struktura ověřená z předávky (data/inbox handoff, 22.–23. 10. 2026):
- složky dokumentů: /<nazev>/ds-<id>/…  (usnesení ZM ds-1004, RM ds-1006, materiály ZM ds-19121,
  rozpočtová opatření ds-19317 s ročními podsložkami), úřední deska /vismo/zobraz_dok.asp?…
- soubor: /assets/File.ashx?id_org=18676&id_dokumenty=<N>
Výpisy HTML se z cloudu ověřit nepodařilo (web blokován) – parser výpisu je proto tolerantní
(hledá odkazy File.ashx a ds-/stránkování v libovolném HTML) a testuje se na syntetickém vzorku.
"""
from __future__ import annotations

import html
import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin

BASE = "https://www.mestovsetin.cz"
ID_ORG = "18676"
FILE_URL = BASE + "/assets/File.ashx?id_org=" + ID_ORG + "&id_dokumenty={}"

RE_FILE = re.compile(r"""<a\b[^>]*href=["']([^"']*File\.ashx\?[^"']*id_dokumenty=(\d+)[^"']*)["'][^>]*>(.*?)</a>""", re.S | re.I)
RE_LINK = re.compile(r"""<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""", re.S | re.I)
RE_TAG = re.compile(r"<[^>]+>")


def _txt(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(RE_TAG.sub(" ", s))).strip()


def parse_listing(page: str, page_url: str) -> dict:
    """Výpis složky: soubory (id_dokumenty, titul, info, url), podsložky ds-, další stránky výpisu."""
    soubory, videno = [], set()
    matches = list(RE_FILE.finditer(page))
    for i, m in enumerate(matches):
        idd = int(m.group(2))
        titul = _txt(m.group(3))
        if idd in videno:
            continue
        videno.add(idd)
        konec = matches[i + 1].start() if i + 1 < len(matches) else min(len(page), m.end() + 600)
        za = page[m.end():konec]
        za = za.split("</li>")[0] if "</li>" in za else za[:400]
        info = _txt(za)
        soubory.append({"id_dokumenty": idd, "titul": titul, "info": (titul + " " + info).strip(),
                        "url": FILE_URL.format(idd)})
    podslozky, stranky = [], []
    ds_self = re.search(r"/ds-(\d+)", page_url)
    for href, text in RE_LINK.findall(page):
        href = html.unescape(href)
        absu = urljoin(page_url, href)
        if not absu.startswith(BASE):
            continue
        m = re.search(r"/ds-(\d+)", absu)
        if m and (not ds_self or m.group(1) != ds_self.group(1)):
            if absu not in [p["url"] for p in podslozky]:
                podslozky.append({"ds": int(m.group(1)), "titul": _txt(text), "url": absu})
        elif (m or "zobraz_dok.asp" in absu) and re.search(r"(?:stranka|strana|page|pg)=\d+", absu):
            if absu not in stranky and absu != page_url:
                stranky.append(absu)
    detaily = sorted({urljoin(page_url, html.unescape(h)) for h, _ in RE_LINK.findall(page)
                      if "dokumenty2.asp" in h or "/d-" in h and "File.ashx" not in h})
    return {"soubory": soubory, "podslozky": podslozky, "stranky": stranky, "detaily": detaily}


# --- text dokumentu ---

def typ_souboru(data: bytes, content_type: str | None = None) -> str:
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "doc"
    if data[:2] == b"PK":
        return "zip"
    if content_type and "html" in content_type or data.lstrip()[:1] == b"<":
        return "html"
    return "jiny"


def text_dokumentu(data: bytes) -> tuple[str | None, str]:
    """(text, kvalita): kvalita ok | ocr_potreba | nastroj_chybi | nepodporovano."""
    typ = typ_souboru(data)
    if typ == "pdf":
        cmd = ["pdftotext", "-enc", "UTF-8", "-", "-"]
    elif typ == "doc":
        cmd = ["antiword", "-m", "UTF-8.txt", "-"]
    elif typ == "html":
        return _txt(data.decode("utf-8", "replace")), "ok"
    else:
        return None, "nepodporovano"
    if not shutil.which(cmd[0]):
        return None, "nastroj_chybi"
    with tempfile.NamedTemporaryFile(suffix="." + typ) as f:
        f.write(data)
        f.flush()
        cmd[-2 if typ == "pdf" else -1] = f.name
        r = subprocess.run(cmd, capture_output=True, timeout=120)
    t = r.stdout.decode("utf-8", "replace")
    t = re.sub(r"\f", "\n", t)
    if r.returncode != 0:
        return None, "chyba_extrakce"
    return t, ("ok" if len(re.sub(r"\s", "", t)) > 200 else "ocr_potreba")


# --- usnesení ---

RE_CISLO = re.compile(r"(?m)^\s*(\d{1,3}/\d{1,3}/(RMZ|RM|ZM)/(\d{4}))\b[ \t]*(.*)$")
VYROKY = ("schvaluje", "neschvaluje", "bere na vědomí", "ukládá", "souhlasí", "nesouhlasí", "doporučuje",
          "nedoporučuje", "revokuje", "odkládá", "zmocňuje", "jmenuje", "odvolává", "volí", "vydává",
          "rozhodla", "rozhoduje", "deleguje", "pověřuje", "stanovuje", "stanoví", "zřizuje", "ruší",
          "svěřuje", "vyhrazuje si", "projednalo", "projednala", "konstatuje", "určuje", "zamítá", "mění")
RE_VYROK = re.compile(r"(?m)^\s*(?:Rada města Vsetín\s+|Zastupitelstvo města Vsetín\s+)?(" + "|".join(VYROKY) + r")\b")
RE_ICO = re.compile(r"\bIČO?\s*:?\s*(\d{2,3}[ \u00a0]?\d{2,3}[ \u00a0]?\d{2,3})\b")
RE_CASTKA = re.compile(r"(\d{1,3}(?:[ .\u00a0]\d{3})+|\d+)(?:,(\d{1,2}|-{1,2}))?\s*Kč")
RE_ZAPATI = re.compile(r"(?m)^.*(?:Strana \d+ \(celkem \d+\)|^\s*Stránka \d+).*$")


def ico_z_textu(t: str) -> list[str]:
    out = (re.sub(r"\D", "", x) for x in RE_ICO.findall(t))
    return list(dict.fromkeys(x for x in out if len(x) == 8))


def castky(t: str) -> list[str]:
    out = []
    for m in RE_CASTKA.finditer(t):
        cela = re.sub(r"[ .\u00a0]", "", m.group(1))
        out.append(f"{cela} Kč")
    return out


def parse_usneseni(raw: str, id_dokumenty: int) -> list[dict]:
    """Rozdělí text výpisu usnesení na jednotlivá usnesení (číslo N/S/ORG/RRRR)."""
    t = RE_ZAPATI.sub("", raw.replace("\r", ""))
    hits = list(RE_CISLO.finditer(t))
    out, videno = [], set()
    for i, m in enumerate(hits):
        blok = t[m.end():hits[i + 1].start() if i + 1 < len(hits) else len(t)]
        cislo, org = m.group(1), m.group(2)
        # název = zbytek řádku čísla + následující řádky do prvního výroku
        v = RE_VYROK.search(blok)
        hlava = (m.group(4) + "\n" + (blok[:v.start()] if v else "")).strip()
        telo = blok[v.start():].strip() if v else blok.strip()
        nazev = re.sub(r"\s+", " ", hlava)
        nazev = re.sub(r"\s*(Rada|Zastupitelstvo) města Vsetín\s*$", "", nazev).strip()
        if (cislo, nazev) in videno:
            continue
        videno.add((cislo, nazev))
        out.append({
            "cislo": cislo, "org": org, "id_dokumenty": id_dokumenty, "nazev": nazev, "text": telo,
            "vyroky": list(dict.fromkeys(x.group(1) for x in RE_VYROK.finditer(telo))),
            "ico": ico_z_textu(blok),
            "castky": castky(blok),
        })
    return out


RE_DATUM = re.compile(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})")
MESICE = {"ledna": 1, "února": 2, "března": 3, "dubna": 4, "května": 5, "června": 6, "července": 7,
          "srpna": 8, "září": 9, "října": 10, "listopadu": 11, "prosince": 12}


def datum_iso(s: str | None) -> str | None:
    """„30.3.2017“ / „30. března 2017“ -> 2017-03-30."""
    if not s:
        return None
    m = RE_DATUM.search(s)
    if m:
        d, mo, y = map(int, m.groups())
    else:
        m = re.search(r"(\d{1,2})\.\s*(" + "|".join(MESICE) + r")\s+(\d{4})", s)
        if not m:
            return None
        d, mo, y = int(m.group(1)), MESICE[m.group(2)], int(m.group(3))
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


# --- rozpočtová opatření ---

def parse_ro_titul(titul: str) -> dict:
    """„Rozpočtové opatření č. 18 - RM“ / „1/2017 - Rozpočtové opatření RM“ -> cislo, schvaluje."""
    m = re.search(r"č\.\s*(\d+)", titul) or re.match(r"\s*(\d+)\s*/\s*\d{4}", titul)
    s = re.search(r"\b(RM|ZM)\b", titul)
    return {"cislo": int(m.group(1)) if m else None, "schvaluje": s.group(1) if s else None}


# --- materiály ZM (ZIP s HTML návrhy usnesení) ---

class _Html2Text(HTMLParser):
    BLOK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table", "td"}

    def __init__(self):
        super().__init__()
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOK:
            self.out.append("\n")

    def handle_data(self, data):
        self.out.append(data)

    def text(self):
        return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t\u00a0]+", " ", "".join(self.out))).strip()


def html_text(s: str) -> str:
    p = _Html2Text()
    p.feed(s)
    return p.text()


def parse_material(text: str) -> dict:
    g = lambda rx: (lambda m: m.group(1).strip() if m else None)(re.search(rx, text))
    return {"vec": g(r"Věc:\s*(.+)"), "predklada_funkcionar": g(r"Předkládá:\s*(.+?)(?:\n|Věc:|$)"),
            "datum_zasedani": datum_iso(g(r"Pro zasedání dne\s*([\d. ]+\d{4})")),
            "ma_duvodovou_zpravu": bool(re.search(r"Důvodová zpráva", text, re.I)), "castky": castky(text)}


def parse_balicek_zm(data: bytes) -> list[dict]:
    """ZIP balíček materiálů ZM -> návrhy usnesení (soubor, text, vec, předkládá …)."""
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in sorted(z.namelist()):
            if not re.search(r"navrh[^/]*\.html?$", n, re.I):
                continue
            raw = z.read(n)
            try:
                s = raw.decode("utf-8")
            except UnicodeDecodeError:
                s = raw.decode("cp1250", "replace")
            t = html_text(s)
            out.append({"soubor": n, "text": t, **parse_material(t)})
    return out


def zasedani_z_titulu(titul: str) -> int | None:
    m = re.search(r"(\d+)\.\s*zasedání", titul)
    return int(m.group(1)) if m else None
