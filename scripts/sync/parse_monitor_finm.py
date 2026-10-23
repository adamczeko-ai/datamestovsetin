"""Parser extraktu MONITOR FIN 2-12 M (FINM01_UJ_*.csv uvnitř ZIP) pro jedno IČO.

Ověřeno v prohlížeči 23. 10. 2026 nad 2026_08_Data_CSUIS_FINM2026.zip:
  - oddělovač ';', hlavička ve tvaru '"Výkaz"ZC_VYKAZ:ZC_VYKAZ;...' (uvozovky ztrojené)
  - částky s tečkou a koncovou mezerou, záporné hodnoty mají '-' NA KONCI ('12394400.48-')
  - sloupec IČO = ZC_ICO (5. sloupec), 'Partner Fin' = IČO protistrany transferu
Výstup: řádky, kde IČO účetní jednotky = zadané IČO (vlastní rozpočet),
a zvlášť řádky, kde je zadané IČO v roli partnera (transfery jiných subjektů).
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile

COLS = ["vykaz", "tabulka", "obdobi", "ucjed", "ico", "kraj", "nuts", "typ",
        "paragraf", "polozka", "uz", "zdroj", "nastroj", "mimud", "partner",
        "schvaleny", "po_zmenach", "vysledek", "zkopirovano"]


def num(s: str) -> float:
    s = s.strip()
    if not s:
        return 0.0
    neg = s.endswith("-")
    v = float(s.rstrip("-"))
    return -v if neg else v


def iter_rows(zip_path: str, member_prefix: str = "FINM01_UJ_"):
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if n.startswith(member_prefix))
        with z.open(name) as fh:
            text = io.TextIOWrapper(fh, encoding="utf-8-sig", newline="")
            next(text)  # hlavička
            for rec in csv.reader(text, delimiter=";"):
                if len(rec) < 18:
                    continue
                yield name, rec


def extract(zip_path: str, ico: str):
    own, partner = [], []
    for name, rec in iter_rows(zip_path):
        if ico not in (rec[4], rec[14]):
            continue
        row = dict(zip(COLS, rec + [""] * (len(COLS) - len(rec))))
        for k in ("schvaleny", "po_zmenach", "vysledek"):
            row[k] = num(row[k])
        row["soubor"] = name
        (own if rec[4] == ico else partner).append(row)
    return own, partner


if __name__ == "__main__":
    o, p = extract(sys.argv[1], sys.argv[2])
    print(len(o), len(p))
