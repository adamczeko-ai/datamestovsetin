"""Profil zadavatele Města Vsetín na vhodne-uverejneni.cz – export XMLdataVZ.

URL: https://www.vhodne-uverejneni.cz/profil/00304450/XMLdataVZ?od=DDMMRRRR&do=DDMMRRRR
Formát ověřen 23. 10. 2026: namespace urn:cz:isvz:mmr:schemas:vz-z-profilu-zadavatele:v100, v jednom
exportu se mísí dvě struktury zakázky:
- starší: zakazka > VZ (kod_vz_na_profilu, stav_vz …) + ucastnik + dodavatel (zakázky zahájené do ~2024),
- nová: zakazka > casti_vz > cast_zakazky > zadavaci_postup_casti > ucastnici / vybrani_dodavatele.
robots.txt hostitele uvádí Crawl-delay: 30 → Http(robots=True) drží 30 s mezi požadavky.
Výstupní pole odpovídají předávce P2f (vsetin_osint_verejne_zakazky_2026-10-23.json).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, timedelta

from . import pseudo

PROFIL = "https://www.vhodne-uverejneni.cz/profil/00304450"
# portál vrací HTTP 400 pro export přes toto datum („Není možné zároveň exportovat zakázky před a po
# 1.7.2024. Rozdělte požadavek na dva“, ověřeno 23. 10. 2026)
HRANICE = (date(2024, 7, 1),)
URL = PROFIL + "/XMLdataVZ?od={od}&do={do}"


def url_interval(od: date, do: date) -> str:
    return URL.format(od=od.strftime("%d%m%Y"), do=do.strftime("%d%m%Y"))


def intervaly(od: date, do: date, max_dni: int = 180):
    """Rozdělí období na intervaly ≤ max_dni (menší odpovědi, méně zátěže), nikdy přes HRANICE."""
    while od <= do:
        konec = min(do, od + timedelta(days=max_dni - 1))
        for h in HRANICE:
            if od < h <= konec:
                konec = h - timedelta(days=1)
        yield od, konec
        od = konec + timedelta(days=1)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el, name):
    if el is None:
        return None
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _children(el, name):
    return [c for c in (el if el is not None else []) if _local(c.tag) == name]


def _iter(el, name):
    return [c for c in el.iter() if _local(c.tag) == name]


def _t(el, name):
    c = _child(el, name)
    return c.text.strip() if c is not None and c.text else None


def _f(x):
    try:
        return round(float(x), 2) if x not in (None, "") else None
    except ValueError:
        return None


def _num(x):
    v = _f(x)
    return int(v) if v is not None and v == int(v) else v


def _subjekt(el):
    s = _child(el, "subjekt")
    ico = _t(s, "ico")
    return ico, pseudo.nazev_subjektu(_t(s, "nazev_subjektu"))


def _parse_stara(z) -> dict:
    """Starší struktura (<VZ>); pole jako v předávce P2f (vz-xml-v1)."""
    vz = _child(z, "VZ")
    ucastnici = [{"ico": _t(u, "ico"), "nazev": pseudo.nazev_subjektu(_t(u, "nazev_ucastnika")),
                  "cena_bez_dph": _num(_t(u, "cena_bez_dph")), "cena_s_dph": _num(_t(u, "cena_s_dph")),
                  "sdruzeni": _t(u, "sdruzeni")} for u in _children(z, "ucastnik")]
    dodavatele = [{"ico": _t(d, "ico"), "nazev": pseudo.nazev_subjektu(_t(d, "nazev_dodavatele")),
                   "cena_smlouva_bez_dph": _num(_t(d, "cena_celkem_dle_smlouvy_bez_DPH")),
                   "cena_smlouva_s_dph": _num(_t(d, "cena_celkem_dle_smlouvy_DPH")),
                   "sdruzeni": _t(d, "sdruzeni_dodavatelu")} for d in _children(z, "dodavatel")]
    for d, el in zip(dodavatele, _children(z, "dodavatel")):
        rozpad = [{"rok": _t(r, "rok_smlouvy"), "cena_bez_dph": _num(_t(r, "cena_za_rok_bez_dph")),
                   "cena_s_dph": _num(_t(r, "cena_za_rok_s_dph"))} for r in _children(el, "rozpad")]
        if rozpad:
            d["plneni_po_letech"] = rozpad
    dok = _children(vz, "dokument")
    return {"kod": _t(vz, "kod_vz_na_profilu"), "nazev": _t(vz, "nazev_vz"), "stav": _t(vz, "stav_vz"),
            "druh_rizeni": _t(vz, "druh_zadavaciho_rizeni"), "delena_na_casti": _t(vz, "delena_na_casti"),
            "ramcova_dohoda": _t(vz, "ramcova_dohoda"), "kod_vvz": _t(vz, "kod_vz_na_vvz"),
            "datum_zverejneni": _t(vz, "datum_cas_zverejneni"), "datum_uzavreni_smlouvy": _t(vz, "datum_uzavreni_smlouvy"),
            "datum_zruseni": _t(vz, "datum_zruseni"), "ucastnici": ucastnici, "dodavatele": dodavatele,
            "pocet_nabidek": len(ucastnici), "dokumenty": len(dok),
            "dokumenty_typy": list(dict.fromkeys(t for t in (_t(d, "typ_dokumentu") for d in dok) if t)),
            "struktura": "VZ"}


def parse(xml_bytes: bytes) -> list[dict]:
    """Zakázky z jednoho XML exportu (bez metadat sběru)."""
    root = ET.fromstring(xml_bytes)
    out = []
    for z in _children(root, "zakazka"):
        if _child(z, "VZ") is not None:
            out.append(_parse_stara(z))
            continue
        casti = _iter(z, "cast_zakazky")
        postupy = [_child(c, "zadavaci_postup_casti") for c in casti]
        postupy = [p for p in postupy if p is not None]
        ucastnici, dodavatele, typy, ndok = [], [], [], 0
        stav = druh = kod_vvz = datum_uzavreni = datum_zruseni = None
        datum_zverejneni = None
        for p in postupy:
            stav = stav or _t(p, "stav_zadavaciho_postupu")
            druh = druh or _t(p, "druh_zadavaciho_postupu")
            kod_vvz = kod_vvz or _t(p, "evidencni_cislo_vvz")
            datum_uzavreni = datum_uzavreni or _t(p, "datum_uzavreni_smlouvy")
            datum_zruseni = datum_zruseni or _t(p, "datum_zruseni_rizeni")
            datum_zverejneni = datum_zverejneni or _t(p, "datum_uverejneni")
            for u in _iter(p, "ucastnik"):
                ico, nazev = _subjekt(u)
                ucastnici.append({"ico": ico, "nazev": nazev,
                                  "cena_bez_dph": _num(_t(u, "nabidkova_cena_bez_dph")),
                                  "cena_s_dph": _num(_t(u, "nabidkova_cena_s_dph")),
                                  "role": _t(u, "role_ucastnika"),
                                  "vyloucen": _t(u, "ucastnik_vyloucen"), "odstoupil": _t(u, "ucastnik_odstoupil")})
            for d in _iter(p, "vybrany_dodavatel"):
                ico, nazev = _subjekt(d)
                plneni = [{"rok": _t(x, "rok_smlouvy"), "cena_bez_dph": _num(_t(x, "cena_za_rok_bez_dph")),
                           "cena_s_dph": _num(_t(x, "cena_za_rok_s_dph"))} for x in _iter(d, "plneni")]
                dodavatele.append({"ico": ico, "nazev": nazev,
                                   "cena_smlouva_bez_dph": _num(_t(d, "smluvni_cena_bez_DPH")),
                                   "cena_smlouva_s_dph": _num(_t(d, "smluvni_cena_s_DPH")),
                                   "plneni_po_letech": plneni or None,
                                   "uzavrena_smlouva": _t(d, "uzavrena_smlouva_nebo_rd"),
                                   "role": _t(d, "role_dodavatele")})
            for dok in _iter(p, "dokument"):
                ndok += 1
                typy.append(_t(dok, "typ_dokumentu"))
        out.append({
            "kod": _t(z, "id_objektu"), "nazev": _t(z, "nazev_vz"), "druh_vz": _t(z, "druh_vz"),
            "rezim_vz": _t(z, "rezim_vz"), "hlavni_cpv": _t(z, "hlavni_cpv"),
            "stav": stav, "druh_rizeni": druh, "delena_na_casti": _t(z, "delena_na_casti"),
            "ramcova_dohoda": _t(postupy[0], "ramcova_dohoda") if postupy else None, "kod_vvz": kod_vvz,
            "datum_zverejneni": datum_zverejneni, "datum_uzavreni_smlouvy": datum_uzavreni,
            "datum_zruseni": datum_zruseni, "pocet_casti": len(casti),
            "ucastnici": ucastnici, "dodavatele": dodavatele,
            "pocet_nabidek": len([u for u in ucastnici if u["vyloucen"] != "1"]),
            "dokumenty": ndok, "dokumenty_typy": sorted({t for t in typy if t}), "struktura": "casti_vz",
        })
    return out
