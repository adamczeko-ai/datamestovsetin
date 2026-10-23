"""Sestaví data/analyzy/signaly.json (vsetin-osint/signaly@2) ze čtyř zdrojů:
  1) data/analyzy/red_flags.json (pravidla R1–R12, formát red-flags@1 – beze změny, dál ho čte index.html)
  2) anomálie A-* ze souborů rozpočtových opatření a z kontroly MONITOR
  3) nová pravidla R13–R18 (scripts/pravidla_nesoulady.py)
  4) ruční signály analytiků P-* (data/smlouvy/parovani_ico.json → signaly_k_overeni)
a připojí ruční stavy ověření z data/analyzy/signaly_stavy.json (ten soubor skript NIKDY nezapisuje).

ID signálu je deterministické (hash kódu pravidla, odkazů a částky), takže stav ověření přežije
přegenerování. Když pravidlo/data změní klíčové údaje, vznikne nové ID a starý stav se objeví
v 'osirele_stavy' k ruční kontrole.

Použití: python3 scripts/signaly_v2.py   (spouštět z kořene repa)
"""
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
import pravidla_nesoulady  # noqa: E402

UPOZORNENI = ("Signály a nesoulady slouží k prioritizaci ověřování. Nejsou zjištěním pochybení ani obviněním. "
              "Stav 'potvrzeno' znamená, že nesoulad v datech byl potvrzen nezávislým zdrojem, nikoli že došlo k porušení předpisů.")

RE_RO = re.compile(r"^RO-\d{4}-\d+$")
RE_USN = re.compile(r"/(ZM|RM)/\d{4}$")
RE_HS = re.compile(r"hlidacstatu\.cz/Detail/\d+|smlouvy\.gov\.cz")
RE_VZ = re.compile(r"vhodne-uverejneni\.cz|/zakazka/|profil")


def klasifikuj(ref):
    if ref is None:
        return None
    ref = str(ref)
    if RE_RO.match(ref):
        typ = "rozpoctove_opatreni"
    elif RE_USN.search(ref):
        typ = "usneseni"
    elif RE_HS.search(ref):
        typ = "smlouva"
    elif ref.startswith("http") and RE_VZ.search(ref):
        typ = "verejna_zakazka"
    elif ref.startswith("http"):
        typ = "url"
    elif ref.startswith("data/"):
        typ = "datovy_soubor"
    else:
        typ = "dokument"
    return {"typ": typ, "ref": ref, "url": ref if ref.startswith("http") else None,
            "strana": None, "citace": None, "sha256": None, "stazeno": None, "overeno": False}


def stabilni_id(kod, odkazy, castka):
    klic = "|".join([kod] + [str(o) for o in (odkazy or [])] + [f"{castka:.2f}" if isinstance(castka, (int, float)) else "-"])
    return "S-" + hashlib.sha1(klic.encode("utf-8")).hexdigest()[:10]


def z_flagu(flags, zdroj):
    out, videno = [], collections.Counter()
    for f in flags:
        sid = stabilni_id(f["kod"], f.get("odkazy"), f.get("castka_Kc"))
        videno[sid] += 1
        if videno[sid] > 1:
            sid = f"{sid}-{videno[sid]}"
        out.append({"id": sid, "kod": f["kod"], "zdroj_signalu": zdroj, "zavaznost": f["zavaznost"],
                    "popis": f["popis"], "castka_Kc": f.get("castka_Kc"),
                    "dukazy": [d for d in (klasifikuj(o) for o in (f.get("odkazy") or [])) if d],
                    "stav": "novy", "stav_detail": None, "puvodni": f})
    return out


def anomalie():
    out = {}
    soubory = sorted(set(glob.glob("data/rozpocet/20??/rozpoctova_opatreni_20??*.json")))
    for p in soubory:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        for a in d.get("anomalie", []) or []:
            out.setdefault(a["id"], (a, p))
    p = "data/monitor/kontrola_RO_8115_monitor.json"
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        for a in d.get("anomalie_nove", []) or []:
            if isinstance(a, dict) and a.get("id"):
                out.setdefault(a["id"], (a, p))
    res = []
    for aid, (a, p) in sorted(out.items()):
        popis = a.get("popis") or a.get("text") or ""
        res.append({"id": aid, "kod": "A-anomalie-dat", "zdroj_signalu": "anomalie",
                    "zavaznost": a.get("zavaznost") if a.get("zavaznost") in ("vysoka", "stredni", "nizka") else "stredni",
                    "popis": popis, "castka_Kc": None,
                    "dukazy": [{"typ": "datovy_soubor", "ref": p, "url": None, "strana": None, "citace": None,
                                "sha256": None, "stazeno": None, "overeno": False}],
                    "stav": "novy", "stav_detail": None, "puvodni": a})
    return res


def analyticke():
    """Signály P-* sepsané analytiky (párování IČO se smlouvami). Stav z textu se NEpřebírá – ten nastavuje člověk."""
    p = "data/smlouvy/parovani_ico.json"
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    out = []
    for s in d.get("signaly_k_overeni", []) or []:
        if not (isinstance(s, dict) and re.fullmatch(r"P-\d{2,3}", str(s.get("id", "")))):
            continue
        dukazy = [{"typ": "smlouva", "ref": str(z), "url": f"https://smlouvy.gov.cz/smlouva/{z}", "strana": None,
                   "citace": None, "sha256": None, "stazeno": None, "overeno": False} for z in s.get("zdroje", []) or []]
        dukazy.append({"typ": "datovy_soubor", "ref": p, "url": None, "strana": None, "citace": None,
                       "sha256": None, "stazeno": None, "overeno": False})
        out.append({"id": s["id"], "kod": "P-analyticky-signal", "zdroj_signalu": "analytik",
                    "zavaznost": s.get("zavaznost") if s.get("zavaznost") in ("vysoka", "stredni", "nizka") else "stredni",
                    "popis": f"{s.get('typ', '')}: {s.get('popis', '')}".strip(": "), "castka_Kc": None,
                    "dukazy": dukazy, "stav": "novy", "stav_detail": None, "puvodni": s})
    return out


def nacti_stavy(p="data/analyzy/signaly_stavy.json"):
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh).get("stavy", {})


def sestav():
    with open("data/analyzy/red_flags.json", encoding="utf-8") as fh:
        rf = json.load(fh)
    sig = z_flagu(rf["signaly"], "pravidlo")
    sig += z_flagu(pravidla_nesoulady.vsechna_pravidla(), "pravidlo")
    sig += anomalie()
    sig += analyticke()
    # kolize ID mezi zdroji (nemělo by nastat) → chyba
    dup = [k for k, n in collections.Counter(s["id"] for s in sig).items() if n > 1]
    if dup:
        raise SystemExit(f"Duplicitní ID signálů: {dup}")
    stavy = nacti_stavy()
    ids = {s["id"] for s in sig}
    for s in sig:
        if s["id"] in stavy:
            s["stav"] = stavy[s["id"]]["stav"]
            s["stav_detail"] = stavy[s["id"]]
    order = {"vysoka": 0, "stredni": 1, "nizka": 2}
    sig.sort(key=lambda s: (order[s["zavaznost"]], s["kod"], -(abs(s["castka_Kc"] or 0)), s["id"]))
    return {"schema": "vsetin-osint/signaly@2",
            "vygenerovano": dt.datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds"),
            "upozorneni": UPOZORNENI,
            "souhrn": {"podle_kodu": dict(collections.Counter(s["kod"] for s in sig)),
                       "podle_stavu": dict(collections.Counter(s["stav"] for s in sig)),
                       "celkem": len(sig)},
            "osirele_stavy": sorted(k for k in stavy if k not in ids),
            "signaly": sig}


if __name__ == "__main__":
    out = sestav()
    with open("data/analyzy/signaly.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out["souhrn"], ensure_ascii=False))
    if out["osirele_stavy"]:
        print("POZOR – osiřelé stavy:", out["osirele_stavy"])
