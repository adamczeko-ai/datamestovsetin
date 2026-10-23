"""Registr smluv – hodnoty a strany konkrétních verzí z XML metadat záznamu.

URL: https://smlouvy.gov.cz/smlouva/{idVerze}/xml/registr_smluv_smlouva_{idVerze}.xml (ISRS 1.2).
Řeší chybu M-01: importovat hodnotaBezDph I hodnotaVcetneDph I ciziMena; DPH nepřepočítávat.
Ověřeno 23. 10. 2026: z 215 verzí bez částky na nasvsetin.cz má 149 hodnotu vč. DPH.
Server občas vrací přechodné chyby TLS → interval ≥ 2 s + opakování (řeší Http).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from ..http import Http, now_utc
from ..db import upsert

SOURCE_ID = "registr_smluv.xml"
NS = {"r": "http://portal.gov.cz/rejstriky/ISRS/1.2/"}
URL = "https://smlouvy.gov.cz/smlouva/{v}/xml/registr_smluv_smlouva_{v}.xml"


def _f(x):
    try:
        return float(x) if x not in (None, "") else None
    except ValueError:
        return None


def parse(xml_bytes: bytes, id_verze: str) -> dict:
    root = ET.fromstring(xml_bytes)
    d = root.find("r:data", NS)
    s = d.find("r:smlouva", NS)
    g = lambda el, p: (el.find(p, NS).text if el is not None and el.find(p, NS) is not None else None)
    bez, s_dph = _f(g(s, "r:hodnotaBezDph")), _f(g(s, "r:hodnotaVcetneDph"))
    cizi = s.find("r:ciziMena", NS)
    ch, cm = (_f(g(cizi, "r:hodnota")), g(cizi, "r:mena")) if cizi is not None else (None, None)
    kind = "bez_dph" if bez is not None else "s_dph" if s_dph is not None else "cizi_mena" if ch is not None else "nezjisteno"
    strany = [g(x, "r:ico") for x in s.findall("r:smluvniStrana", NS)]
    return dict(id_verze=id_verze, id_smlouvy=g(d, "r:identifikator/r:idSmlouvy"), predmet=g(s, "r:predmet"),
                datum_uzavreni=g(s, "r:datumUzavreni"), cas_zverejneni=g(d, "r:casZverejneni"),
                hodnota_bez_dph=bez, hodnota_s_dph=s_dph, cizi_hodnota=ch, cizi_mena=cm, value_kind=kind,
                publikujici_ico=g(s, "r:subjekt/r:ico"), strany_ico=",".join(x for x in strany if x),
                platny=1 if (g(d, "r:platnyZaznam") or "1") in ("1", "true") else 0,
                source_url=URL.format(v=id_verze), imported_at=now_utc())


def sync(con, http: Http, verze: list[str], refresh: bool = False) -> dict:
    """Verze v registru jsou neměnné → stahuje se jen chybějící id_verze (idempotentní)."""
    have = {r[0] for r in con.execute("SELECT id_verze FROM rs_verze")} if not refresh else set()
    todo = [v for v in dict.fromkeys(verze) if v not in have]
    ok, err = 0, 0
    for v in todo:
        url = URL.format(v=v)
        try:
            row = parse(http.get_bytes(url), v)
        except Exception as e:
            http._log(SOURCE_ID, url, status="error", attempts=1, error=str(e)[:300]); err += 1
            continue
        upsert(con, "rs_verze", [row]); con.commit()
        http._log(SOURCE_ID, url, http_status=200, status="downloaded", attempts=1)
        ok += 1
    return {"status": "hotovo", "nove": ok, "preskoceno_existujici": len(verze) - len(todo), "chyby": err}
