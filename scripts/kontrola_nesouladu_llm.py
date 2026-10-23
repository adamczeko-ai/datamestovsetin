"""Deterministická kontrola výstupu LLM vrstvy (nesoulady k vysvětlení).

Vstup: kandidát od LLM (JSON dle data/schema/nesoulady-llm.schema.json, může obsahovat chyby).
Výstup: vyčištěný soubor – projdou jen nesoulady, které
  - mají >= 2 citace ze dvou různých zdrojů (soubor#pointer nebo dokument+strana),
  - každá citace je DOSLOVA obsažena ve zdroji (po normalizaci mezer),
  - zdroj je soubor uvnitř repa (žádné '..', absolutní cesty ani URL),
  - popis/otázka neobsahují zakázané výrazy.
Ostatní jdou do 'zahozeno' s důvodem. ID se přečíslují na N-<YYYYMMDD>-NNN.

Použití: python3 scripts/kontrola_nesouladu_llm.py <kandidat.json> <vystup.json>
Exit 0 = výstup zapsán a validní; 1 = kandidát nečitelný / výstup nevalidní.
Kontrola NEumí spolehlivě poznat jméno fyzické osoby v popisu – to zůstává na lidské revizi PR.
"""
import datetime as dt
import json
import os
import re
import sys

ZAKAZANE = re.compile(r"nepravost|podvod|pochyben|korupc|nezákonn|zpronevěr|úmysl|tunel", re.I)
WS = re.compile(r"[\s  ]+")


def norm(s):
    return WS.sub(" ", str(s)).strip()


def hodnota(root, zdroj, strana):
    """Vrátí text zdroje pro porovnání, nebo vyhodí ValueError s důvodem."""
    if re.match(r"^[a-z]+://", zdroj):
        raise ValueError("URL není ověřitelný zdroj – citovat lze jen soubory v repu")
    cesta, _, ptr = zdroj.partition("#")
    if os.path.isabs(cesta) or ".." in cesta.split("/"):
        raise ValueError("cesta mimo repo")
    plna = os.path.join(root, cesta)
    if not os.path.isfile(plna):
        raise ValueError(f"soubor neexistuje: {cesta}")
    if cesta.endswith(".json"):
        with open(plna, encoding="utf-8") as fh:
            v = json.load(fh)
        if ptr:
            for k in ptr.strip("/").split("/"):
                k = k.replace("~1", "/").replace("~0", "~")
                try:
                    v = v[int(k)] if isinstance(v, list) else v[k]
                except (KeyError, IndexError, ValueError):
                    raise ValueError(f"JSON pointer nenalezen: {ptr}")
        return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    with open(plna, encoding="utf-8") as fh:
        return fh.read()


def cislo_varianty(t):
    """'68 983 751' / '68983751' / '68983751.0' → množina normalizovaných tvarů."""
    t = norm(t)
    holy = t.replace(" ", "")
    out = {t, holy}
    if re.fullmatch(r"-?\d+(\.0+)?", holy):
        out.add(str(int(float(holy))))
    return out


def citace_ok(root, c):
    text = c.get("text") or ""
    if len(norm(text)) < 3:
        return "citace je prázdná nebo kratší než 3 znaky"
    try:
        src = norm(hodnota(root, c.get("zdroj", ""), c.get("strana")))
    except ValueError as e:
        return str(e)
    src_holy = src.replace(" ", "")
    if norm(text) in src or any(v in src or v in src_holy for v in cislo_varianty(text) if len(v) >= 3):
        return None
    return f"citace nenalezena doslova ve zdroji {c.get('zdroj')}"


def zkontroluj(kandidat, root="."):
    dnes = dt.date.today().strftime("%Y%m%d")
    ok, zahozeno = [], list(kandidat.get("zahozeno", []))
    for n in kandidat.get("nesoulady", []):
        duvody = []
        for pole in ("popis", "otazka_k_vysvetleni"):
            m = ZAKAZANE.search(n.get(pole) or "")
            if m:
                duvody.append(f"zakázaný výraz v '{pole}': {m.group(0)}")
        cit = n.get("citace") or []
        zdroje = {(c.get("zdroj"), c.get("strana")) for c in cit}
        if len(cit) < 2 or len(zdroje) < 2:
            duvody.append("méně než 2 citace z různých zdrojů")
        for c in cit:
            d = citace_ok(root, c)
            if d:
                duvody.append(d)
        for pole in ("akce", "typ", "popis", "jistota", "otazka_k_vysvetleni"):
            if not n.get(pole):
                duvody.append(f"chybí pole {pole}")
        if duvody:
            zahozeno.append({"puvodni": n, "duvody": duvody})
        else:
            ok.append(n)
    for i, n in enumerate(ok, 1):
        n["id"] = f"N-{dnes}-{i:03d}"
        n.setdefault("souvisejici_signal", None)
        n["citace"] = [{"zdroj": c["zdroj"], "strana": c.get("strana"), "text": c["text"]} for c in n["citace"]]
        for k in list(n):
            if k not in ("id", "akce", "typ", "popis", "citace", "jistota", "otazka_k_vysvetleni", "souvisejici_signal"):
                n.pop(k)
    return {"schema": "vsetin-osint/nesoulady-llm@1", "beh": kandidat.get("beh", {}), "nesoulady": ok, "zahozeno": zahozeno}


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    try:
        with open(argv[1], encoding="utf-8") as fh:
            kand = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print("Kandidát nečitelný:", e)
        return 1
    out = zkontroluj(kand, ".")
    try:
        from jsonschema import Draft202012Validator
        with open("data/schema/nesoulady-llm.schema.json", encoding="utf-8") as fh:
            errs = list(Draft202012Validator(json.load(fh)).iter_errors(out))
    except ImportError:
        errs = []
    if errs:
        print("Výstup nevalidní:", [e.message for e in errs[:5]])
        return 1
    os.makedirs(os.path.dirname(argv[2]) or ".", exist_ok=True)
    with open(argv[2], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"prošlo {len(out['nesoulady'])}, zahozeno {len(out['zahozeno'])} → {argv[2]}")
    for z in out["zahozeno"]:
        print("  ZAHOZENO:", (z.get("puvodni") or {}).get("popis", "")[:80], "|", "; ".join(z.get("duvody", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
