"""Inkrementální sběr veřejných dokumentů VSETÍN OSINT do data/*.jsonl.

Použití (z kořene repa):
  python3 scripts/sber.py                          # všechny zdroje
  python3 scripts/sber.py --source profil_zadavatele --source ares
  python3 scripts/sber.py --dry-run --limit 2       # stahuje a parsuje, ale nic nezapíše

Zdroje: usneseni (RM, ZM), materialy_zm, rozpoctova_opatreni, uredni_deska (snímek při každém běhu),
profil_zadavatele (vhodne-uverejneni.cz XMLdataVZ), registr_smluv (detail max. 500 verzí za běh),
ares (nová IČO z dat).
Pravidla: jen veřejné dokumenty; max. 1 požadavek/s na hostitele (víc, žádá-li robots.txt Crawl-delay);
User-Agent „VSETIN-OSINT research (cech.lpt@gmail.com)“; robots.txt se respektuje (nedostupný = zdroj
vynechán); fyzické osoby v odvozených datech pseudonymizovány (integrace/sber/pseudo.py).
Stav sběru: data/manifest.json; záznam běhu: docs/RUNLOG.md. Selhání zdroje nezastaví ostatní.
Nedosažitelný hostitel (síť: timeout, reset, nedostupný robots.txt) = stav „unreachable“: zapíše se do
manifestu, ale není to chyba běhu (např. web města z cloudové egress brány – viz docs/SBER.md).
Návratový kód: 0 = všechny zdroje ok nebo unreachable, 1 = alespoň jeden zdroj selhal.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
import urllib.error
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrace.http import Http  # noqa: E402
from integrace.sber import store, zdroje  # noqa: E402
from integrace.sber.registr import LIMIT_DETAILU  # noqa: E402
import ares_overeni  # noqa: E402


def main(argv=None, http: Http | None = None, dnes: date | None = None) -> int:
    """http/dnes lze podstrčit (testy offline)."""
    ap = argparse.ArgumentParser(prog="sber.py", description=__doc__.split("\n")[0])
    ap.add_argument("--source", action="append", choices=sorted(zdroje.ZDROJE),
                    help="zdroj (opakovatelné; výchozí všechny)")
    ap.add_argument("--dry-run", action="store_true", help="nic nezapisovat (data, manifest, RUNLOG)")
    ap.add_argument("--limit", type=int, default=20, help="max. nových dokumentů / intervalů na zdroj (výchozí 20)")
    ap.add_argument("--limit-rs", type=int, default=LIMIT_DETAILU, help="max. detailů registru smluv (≤ 500)")
    ap.add_argument("--limit-ares", type=int, default=200, help="max. nových IČO v ARES")
    ap.add_argument("--max-stranek", type=int, default=5, help="max. stránek výpisu složky")
    ap.add_argument("--max-pokusu", type=int, default=3, help="opakování při 429/5xx/síťové chybě")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--manifest", default=None, help="výchozí <data-dir>/manifest.json")
    ap.add_argument("--runlog", default=os.path.join(ROOT, "docs", "RUNLOG.md"))
    a = ap.parse_args(argv)

    src = a.source or list(zdroje.ZDROJE)
    man_path = a.manifest or os.path.join(a.data_dir, "manifest.json")
    man = store.nacti_manifest(man_path)
    sklad = store.Sklad(a.data_dir)
    http = http or Http(None, tempfile.mkdtemp(prefix="sber-"), min_interval=1.0, max_attempts=a.max_pokusu,
                timeout=a.timeout, user_agent=zdroje.UA, robots=True)
    limity = {"limit": a.limit, "limit_rs": min(a.limit_rs, LIMIT_DETAILU), "limit_ares": a.limit_ares,
              "max_stranek": a.max_stranek}
    beh = {"zacatek": store.ted(), "rezim": "dry-run" if a.dry_run else "ostry", "zdroje": src,
           "limity": limity, "vysledky": {}}

    for z in src:
        zac = store.ted()
        kurzor = dict((man.get("zdroje", {}).get(z) or {}).get("kurzor") or {})
        b = zdroje.Beh(http=http, sklad=sklad, kurzor=kurzor, limit=a.limit, limit_rs=limity["limit_rs"],
                       limit_ares=a.limit_ares, max_stranek=a.max_stranek, dnes=dnes or date.today(),
                       log=lambda *x: print(*x, file=sys.stderr))
        try:
            fn = zdroje.ZDROJE[z]
            pocty, novy_kurzor, pozn = fn(b, ares_overeni.overit_ico) if z == "ares" else fn(b)
            stav = "ok"
            vys = {"stav": stav, "pocty": pocty, "poznamka": pozn}
            chyba = pozn if pozn and pozn.startswith("vyhledávání") else None
            store.zapis_zdroj(man, z, zacatek=zac, stav=stav, pocty=pocty, kurzor={**kurzor, **novy_kurzor},
                              chyba=chyba, soubory=[f"data/{f}.jsonl" for f in zdroje.SOUBORY[z]])
        except zdroje.NEDOSAZITELNE as e:  # síťová nedostupnost hostitele: zaznamenat, nejde o chybu běhu
            msg = f"{type(e).__name__}: {e}"
            if isinstance(e, urllib.error.HTTPError):  # odpověď serveru = skutečná chyba
                vys = {"stav": "chyba", "chyba": msg}
                store.zapis_zdroj(man, z, zacatek=zac, stav="chyba", chyba=msg)
            else:
                vys = {"stav": "unreachable", "poznamka": msg}
                store.zapis_zdroj(man, z, zacatek=zac, stav="unreachable", poznamka=msg)
        except zdroje.CastecnaChyba as e:  # část práce hotová: uložit počty a kurzor, stav = chyba
            msg = str(e)
            vys = {"stav": "chyba", "chyba": msg, "pocty": e.pocty}
            store.zapis_zdroj(man, z, zacatek=zac, stav="chyba", pocty=e.pocty, kurzor={**kurzor, **e.kurzor},
                              chyba=msg, soubory=[f"data/{f}.jsonl" for f in zdroje.SOUBORY[z]])
        except Exception as e:  # selhání jednoho zdroje nezastaví ostatní
            msg = f"{type(e).__name__}: {e}"
            traceback.print_exc(file=sys.stderr)
            vys = {"stav": "chyba", "chyba": msg}
            store.zapis_zdroj(man, z, zacatek=zac, stav="chyba", chyba=msg)
        beh["vysledky"][z] = vys
        print(json.dumps({"zdroj": z, **vys}, ensure_ascii=False), file=sys.stderr)

    beh["konec"] = store.ted()
    if not a.dry_run:
        zapsano = sklad.flush()
        beh["zapsano_radku"] = zapsano
        man["posledni_beh"] = {k: beh[k] for k in ("zacatek", "konec", "rezim", "zdroje", "limity")}
        man["posledni_beh"]["stav"] = {z: v["stav"] for z, v in beh["vysledky"].items()}
        store.zapis_manifest(man_path, man, sklad, a.data_dir)
        store.zapis_runlog(a.runlog, beh)
    else:
        beh["by_bylo_zapsano_radku"] = {n: len(f.pending) for n, f in sklad.files.items()}
    print(json.dumps(beh, ensure_ascii=False, indent=1))
    return 0 if all(v["stav"] in ("ok", "unreachable") for v in beh["vysledky"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
