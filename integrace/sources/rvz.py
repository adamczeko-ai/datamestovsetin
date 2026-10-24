"""NIPEZ – Registr veřejných zakázek, open data (od 02/2024): opendata-rvz/{KAT}-{MM}-{RRRR}.zip.

Soubor VZ-MM-RRRR.zip ≈ 180 MB → JSON ≈ 1,3 GB {"obdobi_od","obdobi_do","verze","data":[{verejna_zakazka,historie_lhut,zdroj_dat},…]}.
Zpracování je proudové (bez ijson): ZIP se čte po blocích, objekty z pole "data" se vyřezávají podle hloubky závorek.
Zdroje dat (10/2026): VVZ, NEN, Tender arena, TENDERMARKET – ostatní e-nástroje (např. profil vhodne-uverejneni.cz) chybí.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date

from ..http import Http, now_utc
from ..db import upsert

SOURCE_ID = "nipez.rvz"
BASE = "https://isvz.nipez.cz/sites/default/files/content/opendata-rvz/"


# Rok 2024 je zveřejněn jen jako roční soubor (ověřeno 23. 10. 2026: VZ-2024_rocni.zip 200, VZ-MM-2024.zip 404).
ROCNI_ROKY = {2024}
PRVNI_ROK = 2024


def url_for(kat: str, year: int, month: int) -> str:
    if year in ROCNI_ROKY:
        return f"{BASE}{kat}-{year}_rocni.zip"
    return f"{BASE}{kat}-{month:02d}-{year}.zip"


def periods(od_rok: int = PRVNI_ROK, today: date | None = None) -> list[tuple[int, int]]:
    """Období k doplnění zpětně: roční soubory (měsíc 0) a měsíční soubory do posledního publikovaného.
    ISVZ publikuje k 5. dni následujícího měsíce → od 5. dne je k dispozici předchozí měsíc."""
    today = today or date.today()
    y, m = (today.year, today.month - 1) if today.day >= 5 else (today.year, today.month - 2)
    while m < 1:
        y, m = y - 1, m + 12
    out = []
    for rok in range(max(od_rok, PRVNI_ROK), y + 1):
        if rok in ROCNI_ROKY:
            out.append((rok, 0))
            continue
        for mes in range(1, 13):
            if (rok, mes) <= (y, m):
                out.append((rok, mes))
    return out


def iter_records(text_stream, chunk=1 << 20):
    """Vrací dict záznamy z pole "data" bez načtení celého souboru."""
    buf, i, started = "", 0, False
    depth, in_str, esc, start = 0, False, False, -1
    while True:
        block = text_stream.read(chunk)
        if not block:
            break
        # zahodit zpracovanou část bufferu (ponechat rozpracovaný objekt)
        cut = start if start >= 0 else i
        buf, i = buf[cut:] + block, i - cut
        if start >= 0:
            start = 0
        if not started:
            k = buf.find('"data"')
            k = buf.find("[", k) if k >= 0 else -1
            if k < 0:
                i = max(0, len(buf) - 16)
                continue
            started, i = True, k + 1
        n = len(buf)
        while i < n:
            c = buf[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    yield json.loads(buf[start:i + 1])
                    start = -1
            elif c == "]" and depth == 0:
                return  # konec pole "data"
            i += 1


def _icos_zadavatele(vz: dict) -> list[str]:
    out = []
    for zp in vz.get("zadavaci_postupy") or []:
        for z in ((zp.get("zadavatel_zadavaciho_postupu") or {}).get("zadavatele") or []):
            ico = ((z.get("subjekt") or {}).get("ico") or "").strip()
            if ico:
                out.append(ico.zfill(8))
    return out


def _icos_ucastnici(vz: dict) -> list[str]:
    """Účastníci zadávacího postupu (podané nabídky) – i neúspěšní."""
    out = []
    for cast in vz.get("casti_verejne_zakazky") or []:
        for u in ((cast.get("zadavaci_postup_pro_cast") or {}).get("ucastnici")) or []:
            for d in u.get("dodavatele") or []:
                ico = ((d.get("subjekt") or {}).get("ico") or "").strip()
                if ico:
                    out.append(ico.zfill(8))
    return out


def _smlouvy(vz: dict):
    for cast in vz.get("casti_verejne_zakazky") or []:
        zp = cast.get("zadavaci_postup_pro_cast") or {}
        for i, s in enumerate(((zp.get("vysledek") or {}).get("smlouva")) or []):
            dod = [((d.get("subjekt") or {}).get("ico") or "").zfill(8)
                   for d in s.get("dodavatele_se_kterymi_byla_uzavrena_smlouva") or [] if (d.get("subjekt") or {}).get("ico")]
            yield cast.get("identifikator_NIPEZ") or "", i, s, dod


def filter_records(records, icos: set[str], source_file: str):
    ts = now_utc()
    zak, sml = [], []
    for r in records:
        vz = r.get("verejna_zakazka") or {}
        zad = _icos_zadavatele(vz)
        smlouvy = list(_smlouvy(vz))
        dod_all = {d for _, _, _, ds in smlouvy for d in ds}
        uc = set(_icos_ucastnici(vz))
        role = [n for n, hit in (("zadavatel", set(zad) & icos), ("dodavatel", dod_all & icos),
                                 ("ucastnik", uc & icos)) if hit]
        if not role:
            continue
        nid = vz.get("identifikator_NIPEZ")
        zak.append(dict(identifikator_nipez=nid, nazev=vz.get("nazev_verejne_zakazky"), druh=vz.get("druh_verejne_zakazky"),
                        rezim=vz.get("rezim_verejne_zakazky"), predpokladana_hodnota_czk=vz.get("predpokladana_hodnota_bez_DPH_v_CZK"),
                        casova_znacka=vz.get("casova_znacka"), zdroj_dat=r.get("zdroj_dat"), zadavatele_ico=",".join(zad), role_okruhu=",".join(role),
                        raw_json=json.dumps(r, ensure_ascii=False), source_file=source_file, imported_at=ts))
        for cast_id, i, s, dod in smlouvy:
            sml.append(dict(identifikator_nipez=nid, cast_nipez=cast_id, poradi=i, datum_uzavreni=s.get("datum_uzavreni_smlouvy"),
                            cena_bez_dph=s.get("hodnota_smluvni_ceny_bez_DPH"), cena_s_dph=s.get("hodnota_smluvni_ceny_s_DPH"),
                            mena=s.get("hodnota_smluvni_ceny_mena"), dodavatele_ico=",".join(dod)))
    return zak, sml


def upsert_newer(con, zak: list[dict]) -> list[dict]:
    """Novější casova_znacka přepisuje starší; starší verze se nezapíše."""
    keep = []
    for z in zak:
        row = con.execute("SELECT casova_znacka FROM rvz_zakazka WHERE identifikator_nipez=?", (z["identifikator_nipez"],)).fetchone()
        if not row or (z["casova_znacka"] or "") >= (row[0] or ""):
            keep.append(z)
    return keep


def sync_month(con, http: Http, year: int, month: int, icos: set[str], kat: str = "VZ") -> dict:
    url = url_for(kat, year, month)
    f = http.fetch(SOURCE_ID, url)
    if f.status == "error":
        return {"status": "chyba", "http": f.http_status, "url": url}
    if not f.changed:
        return {"status": "beze_zmeny", "url": url}
    with zipfile.ZipFile(f.path) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            zak, sml = filter_records(iter_records(io.TextIOWrapper(fh, encoding="utf-8")), icos, name)
    zak = upsert_newer(con, zak)
    keep_ids = {z["identifikator_nipez"] for z in zak}
    n1 = upsert(con, "rvz_zakazka", zak)
    n2 = upsert(con, "rvz_smlouva", [s for s in sml if s["identifikator_nipez"] in keep_ids])
    con.commit()
    return {"status": "importovano", "url": url, "zakazky": n1, "smlouvy": n2}


def sync_range(con, http: Http, icos: set[str], od_rok: int = PRVNI_ROK, today: date | None = None,
               kat: str = "VZ") -> list[dict]:
    """Zpětné doplnění: soubory se zpracují postupně (ne paralelně); nezměněné (ETag) se nestahují.
    Chyba jednoho období nezastaví ostatní."""
    out = []
    for y, m in periods(od_rok, today):
        obd = f"{y}" if m == 0 else f"{y}-{m:02d}"
        try:
            r = sync_month(con, http, y, m, icos, kat)
        except Exception as e:  # noqa: BLE001 – zaznamenat a pokračovat
            r = {"status": "chyba", "chyba": f"{type(e).__name__}: {e}"[:200]}
        out.append({"obdobi": obd, **r})
    return out
