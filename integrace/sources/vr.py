"""Veřejný rejstřík přes ARES REST (/ekonomicke-subjekty-vr/{ico}).

Proč ARES a ne dataor CSV: ARES vrací strukturovaný JSON s historií (datumZapisu/datumVymazu,
vznikFunkce/zanikFunkce); dataor CSV má pole 'udaje' v proprietárním formátu. dataor zůstává
pro hromadné objevování subjektů (soud KS Ostrava pro Vsetínsko).

Minimalizace (GDPR): u fyzických osob se ukládá jen jméno, tituly, funkce a data – NIKDY
datum narození ani adresa bydliště (ARES je vrací).
"""
from __future__ import annotations

import hashlib
import json

from ..http import Http, now_utc
from ..db import upsert

SOURCE_ID = "ares.vr"
URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty-vr/{ico}"


def _cur(v):
    if isinstance(v, list):
        c = [x for x in v if not x.get("datumVymazu")]
        return (c or v)[-1].get("hodnota") if v else None
    return v


def _hist(v):
    return [x.get("hodnota") for x in v if x.get("datumVymazu")] if isinstance(v, list) else []


def _osoba(o: dict):
    fo, po = o.get("fyzickaOsoba"), o.get("pravnickaOsoba")
    if fo:
        jm = " ".join(x for x in [fo.get("titulPredJmenem"), (fo.get("jmeno") or "").title(),
                                  (fo.get("prijmeni") or "").title(), fo.get("titulZaJmenem")] if x)
        return "FO", jm, ""
    if po:
        return "PO", po.get("obchodniJmeno") or "", (po.get("ico") or "").zfill(8) if po.get("ico") else ""
    return "?", "", ""


def parse(doc: dict) -> tuple[dict, list[dict]]:
    ts = now_utc()
    zs = doc.get("zaznamy") or []
    z = next((x for x in zs if x.get("primarniZaznam")), zs[0] if zs else {})
    ico = str(_cur(z.get("ico")) or doc.get("icoId") or "").zfill(8)
    sz = [f"{s.get('oddil')} {s.get('vlozka')} {s.get('soud')}" for s in z.get("spisovaZnacka") or [] if not s.get("datumVymazu")]
    subj = dict(ico=ico, nazev=_cur(z.get("obchodniJmeno")), predchozi_nazvy=json.dumps(_hist(z.get("obchodniJmeno")), ensure_ascii=False),
                spisova_znacka=", ".join(sz), pravni_forma=_cur(z.get("pravniForma")) if isinstance(z.get("pravniForma"), list) else z.get("pravniForma"),
                datum_zapisu=z.get("datumZapisu"), datum_vymazu=z.get("datumVymazu"), sidlo_adm_kod=None, imported_at=ts)
    for a in z.get("adresy") or []:
        if not a.get("datumVymazu") and (a.get("adresa") or {}).get("kodAdresnihoMista"):
            subj["sidlo_adm_kod"] = a["adresa"]["kodAdresnihoMista"]
    ang = []
    for key in ("statutarniOrgany", "ostatniOrgany"):
        for org in z.get(key) or []:
            for c in org.get("clenoveOrganu") or []:
                typ, jm, oico = _osoba(c)
                fn = (c.get("clenstvi") or {}).get("funkce") or {}
                ang.append(dict(ico=ico, organ=org.get("nazevOrganu") or key, typ_osoby=typ, jmeno=jm, osoba_ico=oico,
                                funkce=fn.get("nazev") or c.get("nazevAngazma") or "", podil="",
                                vznik_funkce=fn.get("vznikFunkce"), zanik_funkce=fn.get("zanikFunkce"),
                                datum_zapisu=c.get("datumZapisu") or "", datum_vymazu=c.get("datumVymazu"), imported_at=ts))
    for blok in z.get("spolecnici") or []:
        for sp in blok.get("spolecnik") or []:
            typ, jm, oico = _osoba(sp.get("osoba") or {})
            podily = [p for p in sp.get("podil") or [] if not p.get("datumVymazu")]
            podil = ((podily[-1].get("velikostPodilu") or {}).get("hodnota") or "").replace(";", ",") if podily else ""
            ang.append(dict(ico=ico, organ=blok.get("nazevOrganu") or "Společníci", typ_osoby=typ, jmeno=jm, osoba_ico=oico,
                            funkce="Společník", podil=podil, vznik_funkce=None, zanik_funkce=None,
                            datum_zapisu=sp.get("datumZapisu") or "", datum_vymazu=sp.get("datumVymazu"), imported_at=ts))
    return subj, ang


def sync(con, http: Http, icos: list[str]) -> dict:
    ok = err = 0
    for ico in icos:
        url = URL.format(ico=ico)
        try:
            raw = http.get_bytes(url, {"Accept": "application/json"})
        except RuntimeError as e:
            http._log(SOURCE_ID, url, status="error", attempts=1, error=str(e)[:300]); err += 1
            continue
        digest = hashlib.sha256(raw).hexdigest()
        prev = con.execute("SELECT sha256 FROM vr_subjekt WHERE ico=?", (ico.zfill(8),)).fetchone()
        if prev and prev[0] == digest:
            http._log(SOURCE_ID, url, http_status=200, sha256=digest, status="unchanged_hash", attempts=1)
            continue
        subj, ang = parse(json.loads(raw))
        subj.update(source_url=url, sha256=digest)
        upsert(con, "vr_subjekt", [subj])
        con.execute("DELETE FROM vr_angazma WHERE ico=?", (subj["ico"],))  # snapshot nahrazuje předchozí (historie je v datech VR)
        upsert(con, "vr_angazma", ang)
        con.commit()
        http._log(SOURCE_ID, url, http_status=200, sha256=digest, status="downloaded", size_bytes=len(raw), attempts=1)
        ok += 1
    return {"status": "hotovo", "importovano": ok, "chyby": err}
