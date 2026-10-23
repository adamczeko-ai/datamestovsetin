"""RÚIAN – výměnný formát (VFR), úplná kopie obce: {RRRRMMDD}_OB_{kod}_UKSH.xml.zip (měsíčně k poslednímu dni).

Ověřeno 23. 10. 2026 na 20260930_OB_541630_UKSH (VFR 3.1): 3 778 AM, 6 739 SO, 26 965 parcel, 144 ulic.
Upozornění: RÚIAN neprokazuje vlastnictví. Parcely bez LV a vlastníků.
"""
from __future__ import annotations

import calendar
import io
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from ..http import Http, now_utc
from ..db import upsert

SOURCE_ID = "ruian.vfr"
BASE = "https://vdp.cuzk.gov.cz/vymenny_format/soucasna/"
NS = {
    "vf": "urn:cz:isvs:ruian:schemas:VymennyFormatTypy:v1", "ami": "urn:cz:isvs:ruian:schemas:AdrMistoIntTypy:v1",
    "soi": "urn:cz:isvs:ruian:schemas:StavObjIntTypy:v1", "pai": "urn:cz:isvs:ruian:schemas:ParcelaIntTypy:v1",
    "uli": "urn:cz:isvs:ruian:schemas:UliceIntTypy:v1", "obi": "urn:cz:isvs:ruian:schemas:ObecIntTypy:v1",
    "coi": "urn:cz:isvs:ruian:schemas:CastObceIntTypy:v1", "kui": "urn:cz:isvs:ruian:schemas:KatUzIntTypy:v1",
    "com": "urn:cz:isvs:ruian:schemas:CommonTypy:v1", "gml": "http://www.opengis.net/gml/3.2",
}


def last_publication(today: date | None = None) -> date:
    """Poslední den předchozího měsíce (soubor k aktuálnímu měsíci vzniká až po jeho konci)."""
    today = today or date.today()
    return today.replace(day=1) - timedelta(days=1)


def url_for(obec_kod: int, d: date) -> str:
    assert d.day == calendar.monthrange(d.year, d.month)[1], "VFR úplná kopie je k poslednímu dni měsíce"
    return f"{BASE}{d:%Y%m%d}_OB_{obec_kod}_UKSH.xml.zip"


def _t(el, path):
    x = el.find(path, NS)
    return x.text if x is not None and x.text is not None else None


def _i(el, path):
    v = _t(el, path)
    return int(v) if v not in (None, "") else None


def _pos(el, path):
    v = _t(el, path)
    if not v:
        return None, None
    a, b = v.split()[:2]
    return float(a), float(b)


def parse(stream, source_file: str):
    """Streamové zpracování (iterparse) – paměť konstantní, prvky se po zpracování mažou."""
    ts = now_utc()
    out = {"ruian_adresni_misto": [], "ruian_stavebni_objekt": [], "ruian_parcela": [], "ruian_ulice": []}
    tags = {f"{{{NS['vf']}}}{n}": n for n in ("AdresniMisto", "StavebniObjekt", "Parcela", "Ulice")}
    for ev, el in ET.iterparse(stream, events=("end",)):
        kind = tags.get(el.tag)
        if not kind or el.get(f"{{{NS['gml']}}}id") is None:
            continue  # kontejner (např. <vf:Ulice> obaluje prvky <vf:Ulice gml:id=…>) – reálný VFR 3.1
        if kind == "AdresniMisto":
            x, y = _pos(el, "ami:Geometrie/ami:DefinicniBod/ami:AdresniBod/gml:Point/gml:pos")
            out["ruian_adresni_misto"].append(dict(
                kod=_i(el, "ami:Kod"), cislo_domovni=_i(el, "ami:CisloDomovni"), cislo_orientacni=_i(el, "ami:CisloOrientacni"),
                cislo_orientacni_pismeno=_t(el, "ami:CisloOrientacniPismeno"), psc=_t(el, "ami:Psc"),
                ulice_kod=_i(el, "ami:Ulice/uli:Kod"), stavebni_objekt_kod=_i(el, "ami:StavebniObjekt/soi:Kod"),
                x=x, y=y, plati_od=_t(el, "ami:PlatiOd"), source_file=source_file, imported_at=ts))
        elif kind == "StavebniObjekt":
            x, y = _pos(el, "soi:Geometrie/soi:DefinicniBod/gml:Point/gml:pos")
            out["ruian_stavebni_objekt"].append(dict(
                kod=_i(el, "soi:Kod"), cast_obce_kod=_i(el, "soi:CastObce/coi:Kod"),
                identifikacni_parcela_id=_i(el, "soi:IdentifikacniParcela/pai:Id"),
                typ_kod=_i(el, "soi:TypStavebnihoObjektuKod"), zpusob_vyuziti_kod=_i(el, "soi:ZpusobVyuzitiKod"),
                pocet_bytu=_i(el, "soi:PocetBytu"), pocet_podlazi=_i(el, "soi:PocetPodlazi"),
                zastavena_plocha=_i(el, "soi:ZastavenaPlocha"), isknbudova_id=_i(el, "soi:IsknBudovaId"),
                dokonceni=_t(el, "soi:Dokonceni"), x=x, y=y, plati_od=_t(el, "soi:PlatiOd"),
                source_file=source_file, imported_at=ts))
        elif kind == "Parcela":
            x, y = _pos(el, "pai:Geometrie/pai:DefinicniBod/gml:Point/gml:pos")
            out["ruian_parcela"].append(dict(
                id=_i(el, "pai:Id"), kmenove_cislo=_i(el, "pai:KmenoveCislo"), pododdeleni=_i(el, "pai:PododdeleniCisla"),
                vymera=_i(el, "pai:VymeraParcely"), druh_pozemku_kod=_i(el, "pai:DruhPozemkuKod"),
                druh_cislovani_kod=_i(el, "pai:DruhCislovaniKod"), katastralni_uzemi_kod=_i(el, "pai:KatastralniUzemi/kui:Kod"),
                x=x, y=y, plati_od=_t(el, "pai:PlatiOd"), source_file=source_file, imported_at=ts))
        elif kind == "Ulice":
            out["ruian_ulice"].append(dict(kod=_i(el, "uli:Kod"), nazev=_t(el, "uli:Nazev"), obec_kod=_i(el, "uli:Obec/obi:Kod"),
                                           plati_od=_t(el, "uli:PlatiOd"), source_file=source_file, imported_at=ts))
        el.clear()
    return out


def sync(con, http: Http, obec_kod: int = 541630, d: date | None = None) -> dict:
    d = d or last_publication()
    url = url_for(obec_kod, d)
    f = http.fetch(SOURCE_ID, url)
    if f.status == "error":
        return {"status": "chyba", "http": f.http_status, "url": url}
    if not f.changed:
        return {"status": "beze_zmeny", "url": url}
    with zipfile.ZipFile(f.path) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            data = parse(fh, name)
    counts = {t: upsert(con, t, rows) for t, rows in data.items()}
    con.commit()
    return {"status": "importovano", "url": url, **counts}
