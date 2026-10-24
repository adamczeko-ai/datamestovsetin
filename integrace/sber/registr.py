"""Registr smluv (smlouvy.gov.cz) – detail verzí smluv Města Vsetín.

Seznam verzí pochází z předávky (4614 záznamů, rs-list-v1) a z první stránky vyhledávání
(nové verze). Číslo v URL /smlouva/<N> je idVerze (viz integrace/sources/registr_smluv.py).
Detail = XML metadata verze (ISRS 1.2), parsuje integrace.sources.registr_smluv.parse;
navíc názvy smluvních stran (FO pseudonymizovány). Limit detailů za běh: 500.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..sources import registr_smluv as rs
from . import pseudo

HLEDANI = "https://smlouvy.gov.cz/vyhledavani?subject_idnum=00304450"
DETAIL_HTML = "https://smlouvy.gov.cz/smlouva/{v}"
LIMIT_DETAILU = 500


def parse_hledani(page: str) -> list[str]:
    """idVerze z HTML výsledků vyhledávání (odkazy /smlouva/<N>), v pořadí výskytu."""
    return list(dict.fromkeys(re.findall(r'href="(?:https://smlouvy\.gov\.cz)?/smlouva/(\d+)"', page)))


def parse_detail(xml_bytes: bytes, id_verze: str) -> dict:
    d = rs.parse(xml_bytes, id_verze)
    root = ET.fromstring(xml_bytes)
    strany = []
    for s in root.iter(f"{{{rs.NS['r']}}}smluvniStrana"):
        g = lambda p: (s.find(p, rs.NS).text if s.find(p, rs.NS) is not None else None)
        ico = g("r:ico")
        strany.append({"ico": ico, "nazev": pseudo.nazev_subjektu(g("r:nazev"))})
    pub = root.find("r:data/r:smlouva/r:subjekt", rs.NS)
    return {
        "id_smlouvy": d["id_smlouvy"], "predmet": pseudo.nazev(d["predmet"]), "datum_uzavreni": d["datum_uzavreni"],
        "cas_zverejneni": d["cas_zverejneni"], "hodnota_bez_dph": d["hodnota_bez_dph"],
        "hodnota_s_dph": d["hodnota_s_dph"], "cizi_hodnota": d["cizi_hodnota"], "cizi_mena": d["cizi_mena"],
        "value_kind": d["value_kind"], "publikujici_ico": d["publikujici_ico"],
        "publikujici_nazev": pub.find("r:nazev", rs.NS).text if pub is not None and pub.find("r:nazev", rs.NS) is not None else None,
        "strany": strany, "platny": d["platny"], "xml_url": d["source_url"],
    }
