"""Křížová kontrola konzistence dat (jen čtení zdrojových dat) -> data/analyzy/konzistence.json.

Použití: python3 scripts/kontrola_konzistence.py [--vystup data/analyzy/konzistence.json]

Zdrojová data se NIKDY nemění. Každý rozpor se zapíše s oběma hodnotami, jejich zdrojem (soubor, cesta)
a datem zjištění; stav „ke_kontrole“. Stav, který mezitím upravil člověk (např. „vysvetleno“), se při
dalším běhu zachová (stabilní id rozporu = hash kontroly a obou stran).

Kontroly:
  K1  RO: řádky v JSON vs roční CSV vs souhrnné CSV 2023–2026 (multimnožina řádků)
  K2  RO: bilance (P, V, F) = součet řádků; aritmetika řádku pred + zmena = po
  K3  subjekty.json blok „ares“ vs data/entity/ares_overeni.json (obchodní jméno, sídlo)
  K4  IČO s chybnou kontrolní číslicí (mod 11) ve všech data/**/*.json
  K5  RO schválené ZM/RM: datum RO vs datum zasedání/schůze v data/usneseni/usneseni_vazby_RO.json
  K6  fyzická osoba jako dodavatel/účastník v kurátorovaných datech (právní forma FO dle ARES) – k pseudonymizaci
  K7–K13 v scripts/kontrola_konzistence_krizova.py (odvozené soubory, částky smluv, odkazy, stavy signálů,
         data a časové osy, ZÚ × MONITOR, duplicitní ID)
Návratový kód 0 (nálezy nejsou chyba běhu); 2 = chyba vstupních dat (nečitelný soubor).
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from ares_overeni import ico_ok  # noqa: E402

TZ = ZoneInfo("Europe/Prague")
ROKY_RO = (2023, 2024, 2025, 2026)
FO_FORMY = {"100", "101", "102", "103", "104", "105", "106", "107", "108", "424", "425"}


def p(*a):
    return os.path.join(ROOT, *a)


def nacti(rel):
    with open(p(rel), encoding="utf-8") as f:
        return json.load(f)


def strana(soubor, cesta, hodnota):
    return {"soubor": soubor, "cesta": cesta, "hodnota": hodnota}


def rozpor(kontrola, popis, a, b, **kw):
    klic = json.dumps([kontrola, a, b], ensure_ascii=False, sort_keys=True)
    return {"id": f"{kontrola}-{hashlib.sha256(klic.encode()).hexdigest()[:10]}", "kontrola": kontrola,
            "popis": popis, "a": a, "b": b, **kw}


def _f(x):
    return None if x in (None, "") else round(float(x), 2)


def _radek(r, ro=None):
    return (str(ro if ro is not None else r.get("ro")), r.get("typ"), r.get("odpa") or None, r.get("pol") or None,
            r.get("org") or None, r.get("orj") or None, _f(r.get("pred")), _f(r.get("zmena")), _f(r.get("po")))


def k1_ro_json_csv():
    out = []
    souhrn = list(csv.DictReader(open(p("data/rozpocet/rozpoctova_opatreni_2023-2026_radky.csv"), encoding="utf-8")))
    for rok in ROKY_RO:
        js = f"data/rozpocet/{rok}/rozpoctova_opatreni_{rok}.json"
        cs = f"data/rozpocet/{rok}/rozpoctova_opatreni_{rok}_radky.csv"
        a = Counter(_radek(r, o["cislo"]) for o in nacti(js)["opatreni"] for r in o["radky"])
        b = Counter(_radek(r) for r in csv.DictReader(open(p(cs), encoding="utf-8")))
        c = Counter(_radek(r) for r in souhrn if r["rok"] == str(rok))
        for (na, x), (nb, y), (sa, sb) in (((js, a), (cs, b), ("JSON", "roční CSV")),
                                            ((cs, b), ("data/rozpocet/rozpoctova_opatreni_2023-2026_radky.csv", c),
                                             ("roční CSV", "souhrnné CSV"))):
            for radek in sorted(set(x) | set(y), key=str):
                if x[radek] != y[radek]:
                    out.append(rozpor("K1", f"RO {rok}: řádek se liší mezi {sa} a {sb}",
                                      strana(na, f"RO {radek[0]}", {"radek": list(radek), "pocet": x[radek]}),
                                      strana(nb, f"RO {radek[0]}", {"radek": list(radek), "pocet": y[radek]})))
    return out


def k2_ro_bilance():
    out = []
    for rok in ROKY_RO:
        js = f"data/rozpocet/{rok}/rozpoctova_opatreni_{rok}.json"
        for o in nacti(js)["opatreni"]:
            if not o["radky"]:
                continue
            b = o["bilance"]
            for typ, pole in (("P", "prijmy"), ("V", "vydaje"), ("F", "financovani")):
                s = round(sum(r["zmena"] for r in o["radky"] if r["typ"] == typ), 2)
                if abs(s - (b.get(pole) or 0)) > 0.01:
                    out.append(rozpor("K2", f"{o['id']}: bilance {pole} ≠ součet řádků typu {typ}",
                                      strana(js, f"{o['id']}.bilance.{pole}", b.get(pole)),
                                      strana(js, f"{o['id']}.radky[typ={typ}].zmena (součet)", s)))
            for i, r in enumerate(o["radky"]):
                if None not in (r.get("pred"), r.get("zmena"), r.get("po")) and abs(r["pred"] + r["zmena"] - r["po"]) > 0.01:
                    out.append(rozpor("K2", f"{o['id']}: řádek {i + 1} pred + zmena ≠ po",
                                      strana(js, f"{o['id']}.radky[{i}].pred+zmena", round(r["pred"] + r["zmena"], 2)),
                                      strana(js, f"{o['id']}.radky[{i}].po", r["po"])))
    return out


def k3_ares():
    out = []
    ao = "data/entity/ares_overeni.json"
    a = {r["ico"]: r for r in nacti(ao)["subjekty"]}
    for i, s in enumerate(nacti("data/entity/subjekty.json")["subjekty"]):
        r, b = a.get(s.get("ico") or ""), s.get("ares") or {}
        if not r:
            continue
        for pole, pole_a in (("obchodni_jmeno", "obchodni_jmeno"), ("sidlo", "sidlo")):
            if b.get(pole) and r.get(pole_a) and b[pole] != r[pole_a]:
                out.append(rozpor("K3", f"IČO {s['ico']}: {pole} v subjekty.json ≠ ares_overeni.json",
                                  strana("data/entity/subjekty.json", f"subjekty[{i}].ares.{pole}", b[pole]),
                                  strana(ao, f"subjekty[ico={s['ico']}].{pole_a}", r[pole_a])))
    return out


def k4_ico():
    nalez = {}

    def walk(o, f, cesta):
        if isinstance(o, dict):
            for k, v in o.items():
                if (k == "ico" or k.startswith("ico_")) and isinstance(v, str) and re.fullmatch(r"\d{8}", v):
                    if not ico_ok(v):
                        nalez.setdefault(v, []).append((f, f"{cesta}.{k}"))
                else:
                    walk(v, f, f"{cesta}.{k}")
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, f, f"{cesta}[{i}]")

    for f in sorted(glob.glob(p("data", "**", "*.json"), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        if "/schema/" in rel or rel.endswith("analyzy/konzistence.json"):
            continue
        walk(json.load(open(f, encoding="utf-8")), rel, "$")
    out = []
    for ico, mista in sorted(nalez.items()):
        out.append(rozpor("K4", f"IČO {ico} nemá platnou kontrolní číslici (mod 11) – překlep nebo zástupná hodnota",
                          strana(mista[0][0], mista[0][1], ico),
                          strana("výpočet mod 11", "scripts/ares_overeni.ico_ok", False),
                          vyskyty=len(mista), dalsi_mista=[f"{a}:{b}" for a, b in mista[1:6]]))
    return out


def k5_ro_datum():
    out = []
    vz = "data/usneseni/usneseni_vazby_RO.json"
    v = nacti(vz)
    zm = {int(x["zasedani"]): x["datum"] for x in v.get("index_ZM", []) if x.get("zasedani") and x.get("datum")}
    rm = {int(x["schuze"]): x["datum"] for x in v.get("index_RM_2026", []) if x.get("schuze") and x.get("datum")}
    for rok in ROKY_RO:
        js = f"data/rozpocet/{rok}/rozpoctova_opatreni_{rok}.json"
        for o in nacti(js)["opatreni"]:
            u, d = o.get("usneseni") or "", o.get("datum")
            m = re.search(r"/(\d+)/(ZM|RM)/(\d{4})", u)
            if not (m and d):
                continue
            n, org, r = int(m.group(1)), m.group(2), int(m.group(3))
            idx = zm if org == "ZM" else (rm if r == 2026 else {})
            # číslo zasedání se v novém volebním období opakuje -> párovat jen v rámci roku usnesení
            if n in idx and idx[n][:4] == str(r) and idx[n] != d:
                out.append(rozpor("K5", f"{o['id']}: datum RO ≠ datum {n}. {'zasedání ZM' if org == 'ZM' else 'schůze RM'}",
                                  strana(js, f"{o['id']}.datum", d),
                                  strana(vz, f"index_{'ZM' if org == 'ZM' else 'RM_2026'}[{n}].datum", idx[n]),
                                  usneseni=u))
    return out


def k6_fo_v_kuratorovanych():
    """Účastník/dodavatel s IČO, které ARES vede jako FO, a jménem bez pseudonymu."""
    out = []
    a = {r["ico"]: r for r in nacti("data/entity/ares_overeni.json")["subjekty"]}
    for f in sorted(glob.glob(p("data", "zakazky", "*.json")) + glob.glob(p("data", "smlouvy", "*.json"))):
        rel = os.path.relpath(f, ROOT)

        def walk(o, cesta):
            if isinstance(o, dict):
                ico, nazev = o.get("ico"), o.get("nazev")
                r = a.get(ico) if isinstance(ico, str) else None
                if r and str(r.get("pravni_forma")) in FO_FORMY and isinstance(nazev, str) and "[FO" not in nazev:
                    out.append(rozpor("K6", f"IČO {ico}: fyzická osoba (právní forma {r.get('pravni_forma')}) uvedena jménem",
                                      strana(rel, f"{cesta}.nazev", "(jméno – neuvádí se)"),
                                      strana("data/entity/ares_overeni.json", f"subjekty[ico={ico}].pravni_forma",
                                             r.get("pravni_forma")),
                                      navrh="pseudonymizovat jméno v odvozených datech (rozhodne vlastník dat)"))
                for k, v in o.items():
                    walk(v, f"{cesta}.{k}")
            elif isinstance(o, list):
                for i, x in enumerate(o):
                    walk(x, f"{cesta}[{i}]")
        walk(json.load(open(f, encoding="utf-8")), "$")
    return out


KONTROLY = [("K1", "RO: řádky JSON vs roční CSV vs souhrnné CSV", k1_ro_json_csv),
            ("K2", "RO: bilance a aritmetika řádků", k2_ro_bilance),
            ("K3", "subjekty.json vs ares_overeni.json", k3_ares),
            ("K4", "IČO – kontrolní číslice", k4_ico),
            ("K5", "RO: datum vs index zasedání ZM / schůzí RM", k5_ro_datum),
            ("K6", "FO jménem v kurátorovaných datech (zakázky, smlouvy)", k6_fo_v_kuratorovanych)]

import kontrola_konzistence_krizova as _krizova  # noqa: E402  K7–K13 (odvozené soubory, smlouvy, odkazy, …)
_krizova.kk = sys.modules[__name__]
KONTROLY += _krizova.KONTROLY_DALSI


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--vystup", default=p("data", "analyzy", "konzistence.json"))
    a = ap.parse_args(argv)
    ted = datetime.now(TZ).isoformat(timespec="seconds")
    predchozi = {}
    if os.path.exists(a.vystup):
        predchozi = {r["id"]: r for r in json.load(open(a.vystup, encoding="utf-8")).get("rozpory", [])}
    souhrn, rozpory = [], []
    for kod, popis, fn in KONTROLY:
        try:
            nalez = fn()
        except (OSError, ValueError, KeyError) as e:
            print(f"CHYBA vstupních dat v {kod}: {type(e).__name__}: {e}", file=sys.stderr)
            return 2
        for r in nalez:
            old = predchozi.get(r["id"])
            r["zjisteno"] = old["zjisteno"] if old else ted
            r["stav"] = old["stav"] if old else "ke_kontrole"
            if old and old.get("poznamka_cloveka"):
                r["poznamka_cloveka"] = old["poznamka_cloveka"]
        souhrn.append({"kontrola": kod, "popis": popis, "pocet": len(nalez)})
        rozpory += nalez
    zmizele = sorted(set(predchozi) - {r["id"] for r in rozpory})
    out = {"schema": "vsetin-osint/konzistence@1", "stav_k": ted,
           "poznamka": "Rozpory k ověření, nejsou zjištěním pochybení. Zdrojová data se nemění; stav upravuje člověk.",
           "souhrn": souhrn, "zmizele_od_minula": zmizele, "rozpory": rozpory}
    os.makedirs(os.path.dirname(os.path.abspath(a.vystup)), exist_ok=True)
    with open(a.vystup, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({"souhrn": souhrn, "celkem": len(rozpory), "zmizele": len(zmizele)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
