"""Nedestruktivní normalizace formátu dat na ISO 8601 (RRRR-MM-DD).

Použití: python3 scripts/normalizace_dat.py [--kontrola]

Původní pole zůstávají beze změny, přidává se vedle nich pole s příponou `_iso`:
- data/smlouvy/oprava_hodnot_registru_2026-10-23.json: verze[].datum_uzavreni „DD.MM.RRRR“ → datum_uzavreni_iso
- data/smlouvy/uver_CSOB_*.json: retezec[].datum → datum_iso (text, který není datem, např. „neuvedeno (…)“ → null)
Skript je idempotentní (opakované spuštění nic nezmění). --kontrola: nic nezapisuje, návratový kód 1, pokud
by se něco změnilo (pro CI / plánovaný běh).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SOUBORY = [  # (soubor, seznam, pole)
    ("data/smlouvy/oprava_hodnot_registru_2026-10-23.json", "verze", "datum_uzavreni"),
    ("data/smlouvy/uver_CSOB_2026.json", "retezec", "datum"),
    ("data/smlouvy/uver_CSOB_kontokorent_2011.json", "retezec", "datum"),
]


def na_iso(hodnota):
    """„12.05.2026“ / „2026-05-12“ → „2026-05-12“; jiný text nebo neplatné datum → None."""
    if not isinstance(hodnota, str):
        return None
    m = re.fullmatch(r"\s*(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})\s*", hodnota)
    if m:
        d, mo, y = map(int, m.groups())
    else:
        m = re.fullmatch(r"\s*(\d{4})-(\d{2})-(\d{2})\s*", hodnota)
        if not m:
            return None
        y, mo, d = map(int, m.groups())
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def normalizuj(data: dict, seznam: str, pole: str) -> int:
    """Doplní pole <pole>_iso hned za <pole>; vrátí počet změněných záznamů."""
    zmen = 0
    nove = []
    for zaznam in data[seznam]:
        iso = na_iso(zaznam.get(pole))
        if zaznam.get(pole + "_iso", "chybi") == iso:
            nove.append(zaznam)
            continue
        out = {}
        for k, v in zaznam.items():
            if k == pole + "_iso":
                continue
            out[k] = v
            if k == pole:
                out[pole + "_iso"] = iso
        nove.append(out)
        zmen += 1
    data[seznam] = nove
    return zmen


def main(argv=None) -> int:
    kontrola = "--kontrola" in (argv if argv is not None else sys.argv[1:])
    celkem = 0
    for rel, seznam, pole in SOUBORY:
        cesta = os.path.join(ROOT, rel)
        with open(cesta, encoding="utf-8") as f:
            data = json.load(f)
        zmen = normalizuj(data, seznam, pole)
        celkem += zmen
        print(f"{rel}: {zmen} záznamů doplněno o {pole}_iso")
        if zmen and not kontrola:
            with open(cesta, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
    return 1 if (kontrola and celkem) else 0


if __name__ == "__main__":
    sys.exit(main())
