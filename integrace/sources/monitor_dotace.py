"""MONITOR – Registr dotací přes NEDOKUMENTOVANÉ API webové aplikace (/api/grants/*).

Spouští se jen s explicitním přepínačem --allow-undocumented (rozhodnutí vlastníka; doporučeno
potvrdit podmínky u MF). Územní transfery lze bez tohoto API získat z FIN 2-12 M (monitor_finm),
pozor: registr ve výchozím zobrazení vynechává přeposlané státní prostředky (např. ZŠ Luh 2026:
registr 20,88 mil., FIN 2-12 M 38,08 mil. Kč).
"""
from __future__ import annotations

import json
import urllib.parse

from ..http import Http, now_utc
from ..db import upsert

SOURCE_ID = "monitor.dotace"
BASE = "https://monitor.statnipokladna.gov.cz/api/grants"


def _pages(http: Http, path: str, params: dict, page_size: int = 100):
    page = 1
    while True:
        q = urllib.parse.urlencode({**params, "page": page, "pageSize": page_size})
        j = json.loads(http.get_bytes(f"{BASE}/{path}?{q}", {"Accept": "application/json"}))
        items = j.get("items") or []
        yield from items
        if page * page_size >= (j.get("total") or 0) or not items:
            break
        page += 1


def sync(con, http: Http, ico: str) -> dict:
    ts = now_utc()
    loc = [dict(rok=x["year"], load_id=x["loadID"], poskytovatel_ico=x["providerId"], prijemce_ico=x["receiverId"],
                prijemce_nazev=x.get("receiverName") if x.get("receiverForm") not in (None, "", "Zahraniční") else None,
                prijemce_forma=x.get("receiverFormName"), druh=x.get("valueType"), poskytnuto=x.get("valueOut"),
                vraceno=x.get("valueIn"), imported_at=ts)
           for side in ("provider", "receiver")
           for x in _pages(http, "local/search", {side: ico, ("receiver" if side == "provider" else "provider"): "",
                                                   "withPurpose": "false", "sortColumn": "load_id", "sortDir": "DESC"})]
    st = [dict(rok=x["year"], id_dotace=x["grantId"], poskytovatel_ico=x.get("providerId"), prijemce_ico=x["receiverId"],
               nazev=x.get("grantName"), program=x.get("programName"), datum_zdroj=str(x.get("grantDate") or "") or None,
               castka=x.get("value"), imported_at=ts)
          for x in _pages(http, "state/search", {"provider": "", "receiver": ico, "grant": "", "sortColumn": "rok", "sortDir": "DESC"})]
    n1, n2 = upsert(con, "dotace_uzemni", loc), upsert(con, "dotace_statni", st)
    con.commit()
    return {"status": "hotovo", "uzemni": n1, "statni": n2}
