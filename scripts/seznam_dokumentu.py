"""Sestaví seznam dokumentů města pro `python -m integrace dokumenty` ze všech URL dokumentů,
na které už odkazují data v repu (mestovsetin.cz/assets/File.ashx…).

Výstup: data/integrace/dokumenty_seznam.txt  (source_id<TAB>URL, seřazeno, bez duplicit)
source_id = mesto.<první složka pod data/>  (např. mesto.rozpocet, mesto.kauzy, mesto.usneseni)
Použití: python3 scripts/seznam_dokumentu.py   (z kořene repa)
"""
import glob
import re

RE = re.compile(r"https://(?:www\.)?mestovsetin\.cz/assets/File\.ashx\?id_org=\d+&id_dokumenty=\d+")


def sestav(root="data"):
    zaznamy = {}
    for p in sorted(glob.glob(f"{root}/**/*.json", recursive=True)):
        sid = "mesto." + p.split("/")[1]
        with open(p, encoding="utf-8") as f:
            for url in RE.findall(f.read()):
                url = url.replace("://www.", "://")  # sjednotit host
                zaznamy.setdefault(url, sid)
    return sorted(zaznamy.items(), key=lambda kv: (kv[1], kv[0]))


if __name__ == "__main__":
    z = sestav()
    with open("data/integrace/dokumenty_seznam.txt", "w", encoding="utf-8") as f:
        f.write("# Generováno scripts/seznam_dokumentu.py – dokumenty města, na které odkazují data repa\n")
        for url, sid in z:
            f.write(f"{sid}\t{url}\n")
    print(len(z), "URL")
