"""MONITOR – FIN 2-12 M (plnění rozpočtu ÚSC), open data.

Formáty (ověřeno 23. 10. 2026):
- od 2026: /data/extrakty/csv/FinM2026/{RRRR}_{MM}_Data_CSUIS_FINM2026.zip
  členy FINM01_UJ_* (řádky ÚJ, sloupec Partner Fin), FINM02_* (rozvaha – tab. 000200)
  → tab. IV (rekapitulace) NENÍ, konsolidace se dopočítává z 413x/534x.
- do 2025: /data/extrakty/csv/FinM/{RRRR}_{MM}_Data_CSUIS_FINM.zip
  členy FINM201 (rozpočet, bez partnera), FINM202 (tab. III financování), FINM203 (tab. IV rekapitulace)…
- katalogové URL distribuce je BEZ přípony .zip (404) → doplňujeme.
- čísla: tečka, koncová mezera, mínus NA KONCI ('12394400.48-').
"""
from __future__ import annotations

import csv
import io
from datetime import date

from ..http import Http, now_utc
from ..rangezip import list_members, read_member
from ..db import upsert

BASE = "https://monitor.statnipokladna.gov.cz"
CATALOG = BASE + "/api/opendata/monitor"
SOURCE_ID = "monitor.finm"


def num(s: str) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    neg = s.endswith("-")
    v = float(s.rstrip("-"))
    return -v if neg else v


def url_for(year: int, month: int) -> str:
    if year >= 2026:
        return f"{BASE}/data/extrakty/csv/FinM{year}/{year}_{month:02d}_Data_CSUIS_FINM{year}.zip"
    return f"{BASE}/data/extrakty/csv/FinM/{year}_{month:02d}_Data_CSUIS_FINM.zip"


def _rows(text: str):
    rd = csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    next(rd, None)  # hlavička
    for rec in rd:
        if rec:
            yield rec


def parse_finm2026_uj(text: str, icos: set[str], obdobi: str, url: str, etag: str | None):
    """FINM01_UJ: vykaz;tab;obdobi;ucjed;ico;kraj;nuts;typ;par;pol;uz;zdroj;nastroj;mimud;partner;schv;upr;vysl;copy"""
    ts = now_utc()
    rows, transfers = [], {}
    for c in _rows(text):
        if len(c) < 18:
            continue
        ico, partner = c[4], c[14]
        if ico not in icos and partner not in icos:
            continue
        r = dict(obdobi=obdobi, vykaz_tab=c[1], ico=ico, ucjed=c[3], typ=c[7], paragraf=c[8], polozka=c[9],
                 uz=c[10], zdroj=c[11], nastroj=c[12], mimud=c[13], partner_ico=partner,
                 schvaleny=num(c[15]), po_zmenach=num(c[16]), vysledek=num(c[17]),
                 source_url=url, etag=etag, imported_at=ts)
        rows.append(r)
        # transfery: výdajové položky 5xxx/6xxx s partnerem = poskytovatel ico → příjemce partner
        if partner and c[7] == "3" and c[9][:1] in ("5", "6"):
            k = (obdobi, ico, partner, c[9])
            transfers[k] = transfers.get(k, 0.0) + num(c[17])
    tr = [dict(obdobi=k[0], poskytovatel_ico=k[1], prijemce_ico=k[2], polozka=k[3], castka=round(v, 2),
               evidence_level="secondary_aggregate", source_url=url, imported_at=ts)
          for k, v in transfers.items() if v]
    return rows, tr


def derive_rekapitulace_2026(rows: list[dict], ico: str) -> list[dict]:
    """Odvozená rekapitulace pro výkaz bez tab. IV (od 2026). Konsolidace = 413x (příjmy) / 534x (výdaje)."""
    agg = {k: [0.0, 0.0, 0.0] for k in ("P_celkem", "P_konsolidace", "V_bezne", "V_kapitalove", "V_konsolidace")}
    obdobi = None
    for r in rows:
        if r["ico"] != ico:
            continue
        obdobi = r["obdobi"]
        pol, typ = r["polozka"], r["typ"]
        vals = (r["schvaleny"], r["po_zmenach"], r["vysledek"])
        keys = []
        if typ == "2" and pol[:1] in "1234":
            keys.append("P_celkem")
            if pol.startswith("413"):
                keys.append("P_konsolidace")
        elif typ == "3" and pol[:1] == "5":
            keys.append("V_bezne")
            if pol.startswith("534"):
                keys.append("V_konsolidace")
        elif typ == "3" and pol[:1] == "6":
            keys.append("V_kapitalove")
        for k in keys:
            for i in range(3):
                agg[k][i] += vals[i]
    if obdobi is None:
        return []
    p = [agg["P_celkem"][i] - agg["P_konsolidace"][i] for i in range(3)]
    v = [agg["V_bezne"][i] + agg["V_kapitalove"][i] - agg["V_konsolidace"][i] for i in range(3)]
    out = {"4200_odv": p, "4430_odv": v, "4440_odv": [p[i] - v[i] for i in range(3)],
           "4060_odv": agg["P_konsolidace"], "4250_odv": agg["V_konsolidace"], "4220_odv": agg["V_kapitalove"]}
    ts = now_utc()
    return [dict(obdobi=obdobi, ico=ico, radek=k, schvaleny=round(x[0], 2), po_zmenach=round(x[1], 2),
                 vysledek=round(x[2], 2), odvozeno=1, source_url=None, etag=None, imported_at=ts) for k, x in out.items()]


def parse_legacy_tab(text: str, icos: set[str], obdobi: str, url: str, etag: str | None):
    """FINM202/203 (do 2025): vykaz;tab;obdobi;ucjed;ico;kraj;nuts;radek;schv;upr;vysl;copy"""
    ts = now_utc()
    out = []
    for c in _rows(text):
        if len(c) >= 11 and c[4] in icos:
            out.append(dict(obdobi=obdobi, ico=c[4], radek=c[7], schvaleny=num(c[8]), po_zmenach=num(c[9]),
                            vysledek=num(c[10]), odvozeno=0, source_url=url, etag=etag, imported_at=ts))
    return out


def sync_period(con, http: Http, year: int, month: int, icos: set[str]) -> dict:
    """Stáhne (Range) jen potřebné členy ZIP, pokud se ETag změnil od posledního importu."""
    url = url_for(year, month)
    obdobi = f"{year}-{month:02d}"
    h = http.head(url)
    if h.get("status") != 200:
        http._log(SOURCE_ID, url, http_status=h.get("status"), status="skipped", attempts=1,
                  error="období nepublikováno")
        return {"obdobi": obdobi, "status": "nepublikovano", "http": h.get("status")}
    last = con.execute("SELECT etag FROM sync_ledger WHERE source_id=? AND url=? AND status IN "
                       "('downloaded','not_modified') ORDER BY id DESC LIMIT 1", (SOURCE_ID, url)).fetchone()
    if last and last[0] == h["etag"]:
        http._log(SOURCE_ID, url, http_status=304, etag=h["etag"], status="not_modified", attempts=1)
        return {"obdobi": obdobi, "status": "beze_zmeny", "etag": h["etag"]}
    members = list_members(http, url, h["length"])
    n_rows = n_rek = n_tr = 0
    if year >= 2026:
        m = next(x for x in members if x.name.startswith("FINM01_UJ_"))
        text = read_member(http, url, m).decode("utf-8")
        rows, tr = parse_finm2026_uj(text, icos, obdobi, url, h["etag"])
        n_rows = upsert(con, "monitor_finm_radek", rows)
        n_tr = upsert(con, "observed_transfer", tr)
        for ico in icos:
            n_rek += upsert(con, "monitor_rekapitulace", derive_rekapitulace_2026(rows, ico))
    else:
        for m in members:
            if m.name.startswith(("FINM202_", "FINM203_")):
                text = read_member(http, url, m).decode("utf-8")
                n_rek += upsert(con, "monitor_rekapitulace", parse_legacy_tab(text, icos, obdobi, url, h["etag"]))
    con.commit()
    http._log(SOURCE_ID, url, http_status=200, etag=h["etag"], size_bytes=h["length"], status="downloaded",
              sha256=None, attempts=1)
    return {"obdobi": obdobi, "status": "importovano", "etag": h["etag"], "radky": n_rows,
            "rekapitulace": n_rek, "transfery": n_tr}


def periods(start_year: int, today: date | None = None):
    today = today or date.today()
    for y in range(start_year, today.year + 1):
        for m in range(1, 13):
            if (y, m) <= (today.year, today.month):
                yield y, m
