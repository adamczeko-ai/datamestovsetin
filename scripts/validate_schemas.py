"""Validace datových souborů proti JSON Schema v data/schema/. Použití: python3 scripts/validate_schemas.py

Registrace je decentralizovaná: každé data/schema/*.schema.json nese klíč "x-data-files" se seznamem
souborů nebo globů (relativně ke kořeni repa), které validuje. Centrální slovník neexistuje – nové schéma
se zaregistruje samo a PR přidávající schémata spolu nekolidují.

JSON soubory se validují celé; *.jsonl řádek po řádku a navíc se kontroluje, že sha256 řádku odpovídá
obsahu a že se dvojice (id, sha256) neopakuje.
Chybou je také: schéma bez "x-data-files", schéma, kterému neodpovídá žádný soubor, a datový soubor
(data/**/*.json, data/**/*.jsonl), který nevaliduje žádné schéma a není ve výjimkách
data/schema/bez_schematu.txt (soubory bez schématu ke dni zavedení; seznam se smí jen zmenšovat).
"""
import glob
import json
import os
import sys

from jsonschema import Draft202012Validator

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCHEMA_DIR = "data/schema"
KLIC = "x-data-files"
VYJIMKY = f"{SCHEMA_DIR}/bez_schematu.txt"


def _rel(p, root):
    return os.path.relpath(p, root).replace(os.sep, "/")


def schemata(root=ROOT):
    """{cesta schématu: (schéma, [soubory])} – soubory podle globů z x-data-files."""
    out = {}
    for s in sorted(glob.glob(os.path.join(root, SCHEMA_DIR, "*.schema.json"))):
        with open(s, encoding="utf-8") as f:
            sch = json.load(f)
        soubory = set()
        for vzor in sch.get(KLIC) or []:
            soubory.update(_rel(p, root) for p in glob.glob(os.path.join(root, vzor), recursive=True))
        out[_rel(s, root)] = (sch, sorted(soubory))
    return out


def datove_soubory(root=ROOT):
    """Všechny datové soubory, které musí mít schéma (mimo data/schema/)."""
    out = set()
    for vzor in ("data/**/*.json", "data/**/*.jsonl"):
        out.update(_rel(p, root) for p in glob.glob(os.path.join(root, vzor), recursive=True))
    return sorted(f for f in out if not f.startswith(SCHEMA_DIR + "/"))


def vyjimky(root=ROOT):
    p = os.path.join(root, VYJIMKY)
    if not os.path.exists(p):
        return set()
    with open(p, encoding="utf-8") as f:
        return {r.split("#", 1)[0].strip() for r in f} - {""}


def pokryti(root=ROOT):
    """Vrátí seznam problémů registrace (prázdný = vše pokryto)."""
    sch = schemata(root)
    chyby = []
    for s, (obsah, soubory) in sch.items():
        if not obsah.get(KLIC):
            chyby.append(f"{s}: chybí neprázdný klíč {KLIC}")
        elif not soubory:
            chyby.append(f"{s}: {KLIC} neodpovídá žádný soubor")
    pokryto = {f for _, soubory in sch.values() for f in soubory}
    vyj = vyjimky(root)
    for f in datove_soubory(root):
        if f not in pokryto and f not in vyj:
            chyby.append(f"{f}: nevaliduje ho žádné schéma (doplň {KLIC} do schématu)")
    for f in sorted(vyj):
        if not os.path.exists(os.path.join(root, f)):
            chyby.append(f"{VYJIMKY}: {f} neexistuje – odeber řádek")
    return chyby


def _otisk():
    sys.path.insert(0, ROOT)
    from integrace.sber.store import otisk  # jediná definice obsahového otisku (sběr i validace)
    return otisk


def validuj_jsonl(v, cesta):
    otisk = _otisk()
    errs, seen, n = [], set(), 0
    with open(cesta, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            n += 1
            r = json.loads(line)
            errs += [(i, list(e.absolute_path)[:4], e.message[:120]) for e in v.iter_errors(r)]
            if r.get("sha256") != otisk(r):
                errs.append((i, ["sha256"], "neodpovídá obsahu záznamu"))
            k = (r.get("id"), r.get("sha256"))
            if k in seen:
                errs.append((i, ["id", "sha256"], "duplicitní dvojice id + sha256"))
            seen.add(k)
    return errs, n


def main(root=ROOT):
    bad = 0
    for s, (obsah, soubory) in schemata(root).items():
        Draft202012Validator.check_schema(obsah)
        v = Draft202012Validator(obsah)
        for f in soubory:
            cesta = os.path.join(root, f)
            if f.endswith(".jsonl"):
                errs, n = validuj_jsonl(v, cesta)
                print(("OK  " if not errs else f"ERR {len(errs)} ") + f"{f} ({n} řádků)")
                for e in errs[:3]:
                    print("    ", *e)
            else:
                with open(cesta, encoding="utf-8") as fh:
                    errs = list(v.iter_errors(json.load(fh)))
                print(("OK  " if not errs else f"ERR {len(errs)} ") + f)
                for e in errs[:3]:
                    print("    ", list(e.absolute_path)[:6], e.message[:120])
            bad += len(errs)
    for c in pokryti(root):
        print("ERR " + c)
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
