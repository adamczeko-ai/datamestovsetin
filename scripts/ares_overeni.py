"""Ověření IČO z datových souborů v ARES (REST API MF ČR).

Sbírá IČO z polí "ico"/"ico_*" a z textu ve tvaru "IČO 12345678" ve všech data/**/*.json,
ověří kontrolní číslici, dotáže ARES a uloží data/entity/ares_overeni.json.
Použití: python3 scripts/ares_overeni.py   (vyžaduje přístup na ares.gov.cz)
"""
import json, glob, re, time, sys, urllib.request, urllib.error, datetime, zoneinfo

ARES = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{}"
RE_TXT = re.compile(r"IČO[:\s]*([0-9]{6,8})\b")
OUT = "data/entity/ares_overeni.json"


def ico_ok(ico: str) -> bool:
    """Kontrolní číslice IČO (mod 11)."""
    if not re.fullmatch(r"[0-9]{8}", ico):
        return False
    s = sum(int(ico[i]) * (8 - i) for i in range(7))
    c = (11 - s % 11) % 10
    return c == int(ico[7])


def collect():
    found = {}  # ico -> {soubory, nazvy}
    def add(ico, f, nazev=None):
        ico = ico.zfill(8)
        r = found.setdefault(ico, {"soubory": set(), "nazvy_v_datech": set()})
        r["soubory"].add(f)
        if nazev:
            r["nazvy_v_datech"].add(nazev.strip())
    def walk(o, f):
        if isinstance(o, dict):
            nazev = o.get("nazev") or o.get("dodavatel") or o.get("subjekt")
            for k, v in o.items():
                if (k == "ico" or k.startswith("ico_")) and isinstance(v, str) and re.fullmatch(r"[0-9]{6,8}", v):
                    add(v, f, nazev if isinstance(nazev, str) and k == "ico" else None)
                else:
                    walk(v, f)
        elif isinstance(o, list):
            for x in o:
                walk(x, f)
        elif isinstance(o, str):
            for m in RE_TXT.finditer(o):
                add(m.group(1), f)
    for f in sorted(glob.glob("data/**/*.json", recursive=True)):
        if f == OUT or "/schema/" in f or "/entity/ares_overeni_" in f:
            continue
        walk(json.load(open(f, encoding="utf-8")), f)
    return found


def ares(ico):
    req = urllib.request.Request(ARES.format(ico), headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None


def ares_reg(reg, ico):
    url = ARES.replace("ekonomicke-subjekty/", reg + "/").format(ico)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=20) as r:
            return 200, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None


def overit_ico(ico, get=ares, get_reg=ares_reg, pauza=0.25) -> dict:
    """Ověří jedno IČO: kontrolní číslice, základní registr, u 404 dílčí registry RŽP/RES.

    get(ico) -> (http_kód, json|None), get_reg(registr, ico) -> totéž (lze podstrčit, např. pro scripts/sber.py).
    """
    row = {"kontrolni_cislice_ok": ico_ok(ico)}
    if not row["kontrolni_cislice_ok"]:
        return row
    code, d = get(ico)
    time.sleep(pauza)
    row["ares_http"] = code
    if code == 404:  # vymazané z OR vrací základní endpoint 404 -> dílčí registry
        for reg in ("ekonomicke-subjekty-rzp", "ekonomicke-subjekty-res"):
            c2, d2 = get_reg(reg, ico)
            if d2 and d2.get("zaznamy"):
                z = d2["zaznamy"][0]
                row.update({"zdroj_detail": f"{reg}/{ico}", "stav": "ZANIKLY" if z.get("datumZaniku") else None,
                            "obchodni_jmeno": z.get("obchodniJmeno"), "pravni_forma": z.get("pravniForma"),
                            "datum_zaniku": z.get("datumZaniku")})
                break
    if d:
        row.update({
            "obchodni_jmeno": d.get("obchodniJmeno"),
            "pravni_forma": d.get("pravniForma"),
            "sidlo": (d.get("sidlo") or {}).get("textovaAdresa"),
            "datum_vzniku": d.get("datumVzniku"),
            "datum_zaniku": d.get("datumZaniku"),
            "datum_aktualizace_ares": d.get("datumAktualizace"),
        })
    return row


def main():
    found = collect()
    now = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Prague")).strftime("%Y-%m-%d %H:%M")
    rows = []
    for ico in sorted(found):
        src = found[ico]
        r = overit_ico(ico, ares, ares_reg)
        row = {"ico": ico, "kontrolni_cislice_ok": r.pop("kontrolni_cislice_ok"),
               "soubory": sorted(src["soubory"]), "nazvy_v_datech": sorted(src["nazvy_v_datech"]), **r}
        rows.append(row)
    stav = {"v_ares": sum(1 for r in rows if r.get("ares_http") == 200),
            "nenalezeno": [r["ico"] for r in rows if r.get("ares_http") == 404 and not r.get("obchodni_jmeno")],
            "chybna_kontrolni_cislice": [r["ico"] for r in rows if not r["kontrolni_cislice_ok"]],
            "zanikle": [r["ico"] for r in rows if r.get("datum_zaniku")]}
    out = {"schema": "vsetin-osint/ares-overeni@1",
           "zdroj": "ARES REST API (ares.gov.cz), ekonomické subjekty",
           "stav_k": now + (" SELČ" if datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Prague")).strftime("%Z") == "CEST" else " SEČ"),
           "metoda": "IČO z polí ico/ico_* a z textu 'IČO NNNNNNNN' ve všech data/**/*.json; kontrolní číslice mod 11; dotaz ARES.",
           "pocet": len(rows), "souhrn": stav, "subjekty": rows}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"pocet": len(rows), **stav}, ensure_ascii=False))


def zapsat_do_subjektu():
    """Doplní do data/entity/subjekty.json u každého subjektu blok 'ares' z ares_overeni.json."""
    a = {r["ico"]: r for r in json.load(open(OUT, encoding="utf-8"))["subjekty"]}
    f = "data/entity/subjekty.json"
    d = json.load(open(f, encoding="utf-8"))
    for s in d["subjekty"]:
        r = a.get(s.get("ico") or "")
        if not r or (s.get("ares") or {}).keys() & {"zdroj", "zdroj_ico"}:
            continue  # chybí, nebo ručně doplněný detail – nepřepisovat
        if r.get("obchodni_jmeno"):
            s["ares"] = {"stav": "zaniklý" if r.get("datum_zaniku") else "aktivní",
                         "obchodni_jmeno": r.get("obchodni_jmeno"),
                         "pravni_forma": r.get("pravni_forma"), "sidlo": r.get("sidlo")}
        else:
            s["ares"] = {"stav": "nenalezeno v základním registru ARES"}
    d["poznamka"] = ("IČO převzata z textu dokumentů; ověřena v ARES (blok 'ares', detail "
                     "data/entity/ares_overeni.json). Role popsána dle kontextu dokumentu.")
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if "--zapsat" in sys.argv:
        zapsat_do_subjektu()
    else:
        sys.exit(main())
