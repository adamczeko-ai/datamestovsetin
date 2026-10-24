"""Pseudonymizace IČO podnikajících fyzických osob (OSVČ) v data/*.jsonl (§ 5 docs/PREDAVANI_MEZI_RELACEMI.md).

Režimy:
- „hmac“ (doporučený): kód = FO- + HMAC-SHA256(klíč, IČO)[:12]; klíč jen v proměnné prostředí VSETIN_PSEUDO_KLIC
  (nikdy v repu). Kód je stabilní napříč běhy i soubory, z kódu nelze IČO zpětně zjistit bez klíče.
- „poradi“ (bez klíče, bezpečný výchozí): kód = FO-NNNN podle pořadí výskytu; na IČO nezávisí. Propojení napříč
  běhy se neudrží (stejná OSVČ může v dalším běhu dostat nový kód) – jen do nastavení klíče.
Prostý hash IČO bez klíče se NEPOUŽÍVÁ: 8místné IČO je zpětně dohledatelné hrubou silou.

Které IČO jsou FO: subjekty_ares.jsonl (fyzicka_osoba / právní forma FO dle ARES) a graf_uzly.jsonl (fo=true).
Nahrazuje se všude: pole ico, id záznamů (ico:…, subjekt:…), hrany grafu, URL ARES i výskyty v textu (i „123 45 678“).
"""
from __future__ import annotations

import glob
import hashlib
import hmac
import json
import os
import re

from . import pseudo
from .store import otisk

PROMENNA_KLICE = "VSETIN_PSEUDO_KLIC"
ARES_ZAKLAD = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"
RE_ICO = re.compile(r"(?<![\d/])(\d{3})[  ]?(\d{2})[  ]?(\d{3})(?![\d/])")
RE_KOD = re.compile(r"FO-(\d{4,})\b")
PORADI_SOUBORU = ["subjekty_ares", "graf_uzly"]  # nejdřív zdroje identity, pak ostatní abecedně


def _nacti(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fo_ico(data_dir: str) -> set[str]:
    out = set()
    p = os.path.join(data_dir, "subjekty_ares.jsonl")
    if os.path.exists(p):
        for r in _nacti(p):
            ico = r.get("ico") or ""
            if re.fullmatch(r"\d{8}", ico) and (r.get("fyzicka_osoba") or str(r.get("pravni_forma")) in pseudo.FO_PRAVNI_FORMY):
                out.add(ico)
    p = os.path.join(data_dir, "graf_uzly.jsonl")
    if os.path.exists(p):
        for r in _nacti(p):
            if r.get("fo") and re.fullmatch(r"\d{8}", r.get("ico") or ""):
                out.add(r["ico"])
    return out


class Mapovani:
    def __init__(self, klic: str | None, start: int = 0):
        self.klic = klic.encode() if klic else None
        self.rezim = "hmac" if klic else "poradi"
        self.mapa: dict[str, str] = {}
        self.dalsi = start

    def kod(self, ico: str) -> str:
        if ico not in self.mapa:
            if self.klic:
                self.mapa[ico] = "FO-" + hmac.new(self.klic, ico.encode(), hashlib.sha256).hexdigest()[:12]
            else:
                self.dalsi += 1
                self.mapa[ico] = f"FO-{self.dalsi:04d}"
        return self.mapa[ico]


def _nahrad(o, fo: set[str], m: Mapovani):
    if isinstance(o, dict):
        return {k: _nahrad(v, fo, m) for k, v in o.items()}
    if isinstance(o, list):
        return [_nahrad(x, fo, m) for x in o]
    if isinstance(o, str):
        if o.startswith(ARES_ZAKLAD + "/") and o[len(ARES_ZAKLAD) + 1:].split("?")[0] in fo:
            return ARES_ZAKLAD  # URL ARES s IČO FO -> obecná adresa registru
        return RE_ICO.sub(lambda x: m.kod("".join(x.groups())) if "".join(x.groups()) in fo else x.group(0), o)
    return o


def aplikuj(data_dir: str, klic: str | None = None, fo: set[str] | None = None, objekty: list | None = None) -> dict:
    """Pseudonymizuje IČO FO ve všech data/*.jsonl a v předaných objektech (např. manifest, mění se na místě).

    Vrátí souhrn (bez IČO) pro manifest."""
    klic = klic if klic is not None else (os.environ.get(PROMENNA_KLICE) or None)
    fo = fo if fo is not None else fo_ico(data_dir)
    soubory = sorted(glob.glob(os.path.join(data_dir, "*.jsonl")))
    poradi = sorted(soubory, key=lambda f: (PORADI_SOUBORU.index(os.path.basename(f)[:-6])
                                            if os.path.basename(f)[:-6] in PORADI_SOUBORU else 99, f))
    start = 0
    if not klic:  # navázat číslování na kódy, které už v datech jsou
        for f in soubory:
            with open(f, encoding="utf-8") as fh:
                for x in RE_KOD.finditer(fh.read()):
                    start = max(start, int(x.group(1)))
    m = Mapovani(klic, start)
    zmeneno_souboru, zmeneno_radku = 0, 0
    for f in poradi:
        radky = _nacti(f)
        nove, videno, zmena = [], set(), False
        for r in radky:
            r2 = _nahrad(r, fo, m)
            if r2 != r:
                r2["sha256"] = otisk(r2)
                zmena = True
                zmeneno_radku += 1
            k = (r2["id"], r2["sha256"])
            if k in videno:  # stejná verze vznikla dvakrát (surová a už pseudonymizovaná) -> jednou
                zmena = True
                continue
            videno.add(k)
            nove.append(r2)
        if zmena:
            zmeneno_souboru += 1
            tmp = f + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                for r in nove:
                    fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            os.replace(tmp, f)
    for o in objekty or []:  # stejné mapování i pro manifest apod.
        nove = _nahrad(o, fo, m)
        o.clear()
        o.update(nove)
    return {"rezim": m.rezim, "pocet_fo_ico_v_behu": len(m.mapa), "zmenenych_radku": zmeneno_radku,
            "zmenenych_souboru": zmeneno_souboru, "posledni_poradi": m.dalsi if m.rezim == "poradi" else None}
