"""CLI: python -m integrace <zdroj> [volby]

Příklady (vývoj):
  python -m integrace monitor --od 2020 --db /home/administrator/vsetin-osint-dev/data/integrace.db
  python -m integrace ruian
  python -m integrace rvz --rok 2026 --mesic 9
  python -m integrace rvz --od 2024            # zpětné doplnění (2024 roční + měsíce 2025…)
  python -m integrace akceptace                # kontrolní hodnoty po prvním živém běhu
  python -m integrace vr
  python -m integrace smlouvy --verze-soubor verze.txt
  python -m integrace dotace --allow-undocumented
  python -m integrace dokumenty --seznam dokumenty.txt --texty raw/texty
  python -m integrace stav
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from . import db
from .http import Http, now_utc
from . import akceptace
from .sources import monitor_finm, ruian_vfr, rvz, vr, registr_smluv, monitor_dotace, dokumenty

HERE = os.path.dirname(__file__)


def load_config(path: str | None) -> dict:
    path = path or os.environ.get("INTEGRACE_CONFIG") or os.path.join(HERE, "config.json")
    if not os.path.exists(path):
        path = os.path.join(HERE, "config.example.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="integrace")
    ap.add_argument("zdroj", choices=["monitor", "ruian", "rvz", "vr", "smlouvy", "dotace", "dokumenty", "stav", "akceptace"])
    ap.add_argument("--db", default=os.environ.get("INTEGRACE_DB", "integrace.db"))
    ap.add_argument("--cache", default=os.environ.get("INTEGRACE_CACHE", "integrace_cache"))
    ap.add_argument("--config")
    ap.add_argument("--od", type=int, help="MONITOR: první rok (výchozí 2020); RVZ: zpětné doplnění od roku")
    ap.add_argument("--rok", type=int)
    ap.add_argument("--mesic", type=int)
    ap.add_argument("--verze-soubor", help="registr smluv: soubor s idVerze (1 na řádek)")
    ap.add_argument("--seznam", help="dokumenty: soubor s URL (1 na řádek, volitelně source_id<TAB>URL)")
    ap.add_argument("--texty", default=os.environ.get("INTEGRACE_TEXTY", "raw/texty"), help="dokumenty: cílová složka textů")
    ap.add_argument("--allow-undocumented", action="store_true", help="povolit nedokumentované API Registru dotací")
    a = ap.parse_args(argv)

    if a.zdroj == "akceptace":  # jen čtení DB, nezapisuje sync_run
        con = db.connect(a.db)
        rep = akceptace.run(con)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return 0 if rep["selhalo"] == 0 else 1

    cfg = load_config(a.config)
    icos = set(cfg["sledovana_ico"])
    con = db.connect(a.db)
    http = Http(con, a.cache, min_interval=cfg.get("min_interval_s", {}).get(a.zdroj, 1.0))
    run = con.execute("INSERT INTO sync_run (source_id, started_at, status) VALUES (?,?, 'bezi')", (a.zdroj, now_utc())).lastrowid
    con.commit()
    res, status = None, "ok"
    try:
        if a.zdroj == "monitor":
            start = a.od or cfg.get("monitor_od", 2020)
            res = []
            for y, m in monitor_finm.periods(start):
                if y < 2026 and m != 12 and not cfg.get("monitor_mesicne_pred_2026", False):
                    continue  # do 2025 stačí roční výkaz (12) – menší zátěž
                try:
                    res.append(monitor_finm.sync_period(con, http, y, m, icos))
                except Exception as e:  # jedno období nesmí zastavit ostatní
                    http._log(monitor_finm.SOURCE_ID, monitor_finm.url_for(y, m), status="error", attempts=http.max_attempts,
                              error=f"{type(e).__name__}: {e}"[:500])
                    res.append({"obdobi": f"{y}-{m:02d}", "status": "chyba", "chyba": f"{type(e).__name__}: {e}"[:200]})
            if res and all(r["status"] == "chyba" for r in res):
                status = "chyba"
        elif a.zdroj == "ruian":
            res = ruian_vfr.sync(con, http, cfg.get("obec_kod", 541630))
        elif a.zdroj == "rvz" and a.od:
            res = rvz.sync_range(con, http, icos, a.od)
            if res and all(r["status"] == "chyba" for r in res):
                status = "chyba"
        elif a.zdroj == "rvz":
            t = date.today()
            py, pm = rvz.periods(t.year - 1, t)[-1]  # poslední publikovaný soubor (ISVZ k 5. dni)
            y, m = a.rok or py, a.mesic if a.mesic is not None else pm
            res = rvz.sync_month(con, http, y, m, icos)
        elif a.zdroj == "vr":
            res = vr.sync(con, http, sorted(cfg.get("vr_ico", cfg["sledovana_ico"])))
        elif a.zdroj == "smlouvy":
            if not a.verze_soubor:
                ap.error("--verze-soubor je povinný")
            verze = [x.strip() for x in open(a.verze_soubor, encoding="utf-8") if x.strip()]
            res = registr_smluv.sync(con, http, verze)
        elif a.zdroj == "dokumenty":
            if not a.seznam:
                ap.error("--seznam je povinný")
            res = dokumenty.sync(con, http, dokumenty.nacti_seznam(a.seznam), a.texty)
            if res["chyby"] and not res["dokumentu"]:
                status = "chyba"
        elif a.zdroj == "dotace":
            if not a.allow_undocumented:
                status, res = "preskoceno", "Registr dotací používá nedokumentované API – spusťte s --allow-undocumented po schválení vlastníkem."
            else:
                res = monitor_dotace.sync(con, http, cfg["mesto_ico"])
        elif a.zdroj == "stav":
            res = [dict(zip(("zdroj", "posledni_beh", "stav", "zaznamu"), r)) for r in con.execute(
                "SELECT source_id, MAX(started_at), status, records_upserted FROM sync_run GROUP BY source_id")]
            res.append({"ledger": [dict(zip(("zdroj", "stav", "pocet"), r)) for r in con.execute(
                "SELECT source_id, status, COUNT(*) FROM sync_ledger GROUP BY 1,2")]})
    except Exception as e:  # zaznamenat a vrátit nenulový kód
        status, res = "chyba", f"{type(e).__name__}: {e}"
    # konektor vrátil chybu ve výsledku (např. RÚIAN/RVZ bez spojení) → běh nesmí být evidován jako „ok“
    if status == "ok" and isinstance(res, dict) and res.get("status") == "chyba":
        status = "chyba"
    con.execute("UPDATE sync_run SET finished_at=?, status=?, detail=? WHERE id=?",
                (now_utc(), status, json.dumps(res, ensure_ascii=False)[:20000], run))
    con.commit()
    print(json.dumps({"zdroj": a.zdroj, "stav": status, "vysledek": res}, ensure_ascii=False, indent=1))
    return 0 if status in ("ok", "preskoceno") else 1


if __name__ == "__main__":
    sys.exit(main())
