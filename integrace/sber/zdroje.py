"""Kolektory zdrojů pro scripts/sber.py.

Každý kolektor dostane Beh (HTTP klient, sklad JSONL, kurzor zdroje, limity) a vrátí
(pocty, kurzor, poznamka). Výjimka = selhání zdroje; ostatní zdroje běží dál (řeší sber.py).
Inkrementalita: dokument se stahuje, jen pokud jeho id_dokumenty ještě není v data/dokumenty.jsonl
(nebo čeká na konverzi); zakázky od kurzoru „stazeno_do“; registr smluv jen chybějící detaily.
"""
from __future__ import annotations

import json
import re
import urllib.error
from dataclasses import dataclass, field
from datetime import date, timedelta

from ..http import HostUnreachable, Http
from . import profil, pseudo, registr, vismo
from .store import Sklad, sha256_bytes, ted

UA = "VSETIN-OSINT research (cech.lpt@gmail.com)"
B = vismo.BASE
SLOZKY = {  # URL ověřené z předávky (odkazy na webu města, 22. 10. 2026)
    "usneseni_ZM": B + "/usneseni%2Dzastupitelstva%2Dmesta%2Dvsetin%2Dvypis/ds-1004/p1=72157",
    "usneseni_RM": B + "/usneseni%2Drady%2Dmesta%2Dvsetin%2Dvypis/ds-1006/p1=72149",
    "materialy_zm": B + "/materialy%2Dzastupitelstva%2Dmesta%2Dvsetin%2Dpro%2Dverejnost/ds-19121/p1=72158",
    "rozpoctova_opatreni": B + "/rozpoctova%2Dopatreni/ds-19317/p1=72083",
    "uredni_deska": B + "/vismo/zobraz_dok.asp?ud=2&p1=72363",
}
# roční složky RO z předávky (P1b); nové roky se hledají ve výpisu kořenové složky
RO_ROKY = {2026: 19928, 2025: 19876, 2024: 19802, 2023: 19725, 2022: 19647, 2021: 19587,
           2020: 19502, 2019: 19393, 2018: 19318, 2017: 19252}
ARES_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{}"
ZNOVU = {"doc_nekonvertovano", "nastroj_chybi", "chyba_stazeni"}  # dokumenty k opakování


NEDOSAZITELNE = (HostUnreachable, urllib.error.URLError, TimeoutError, ConnectionError)  # síť, ne chyba zdroje


class CastecnaChyba(Exception):
    """Zdroj selhal po části práce: uloží se počty a kurzor k poslednímu úspěchu, stav = chyba."""

    def __init__(self, msg, pocty, kurzor):
        super().__init__(msg)
        self.pocty, self.kurzor = pocty, kurzor


@dataclass
class Beh:
    http: Http
    sklad: Sklad
    kurzor: dict
    limit: int = 20             # max. nových dokumentů / intervalů za běh a zdroj
    limit_rs: int = registr.LIMIT_DETAILU
    limit_ares: int = 200
    max_stranek: int = 5
    dnes: date = field(default_factory=date.today)
    log: callable = print

    def pocty(self):
        return {"nove": 0, "zmeneno": 0, "nezmeneno": 0, "chyby": 0}


def _pridej(pocty, stav):
    pocty[stav] = pocty.get(stav, 0) + 1


def get(beh: Beh, url: str) -> tuple[int, bytes | None, str | None]:
    """(http_kód, data, content_type); 0 = síťová chyba. robots.txt kontroluje Http."""
    resp, _ = beh.http._open(url, {})
    if isinstance(resp, urllib.error.HTTPError):
        return resp.code, None, None
    with resp:
        return resp.status, resp.read(), resp.headers.get("Content-Type")


def get_text(beh: Beh, url: str) -> str:
    code, data, ct = get(beh, url)
    if code != 200 or data is None:
        raise RuntimeError(f"HTTP {code}: {url}")
    m = re.search(r"charset=([\w-]+)", ct or "")
    enc = m.group(1) if m else ("utf-8" if b"utf-8" in data[:2000].lower() else "windows-1250")
    return data.decode(enc, "replace")


def projdi_vypis(beh: Beh, url: str) -> dict:
    """Výpis složky vismo včetně stránkování (max. beh.max_stranek stránek)."""
    out = {"soubory": [], "podslozky": [], "detaily": []}
    fronta, videno = [url], set()
    while fronta and len(videno) < beh.max_stranek:
        u = fronta.pop(0)
        if u in videno:
            continue
        videno.add(u)
        v = vismo.parse_listing(get_text(beh, u), u)
        ids = {s["id_dokumenty"] for s in out["soubory"]}
        out["soubory"] += [s for s in v["soubory"] if s["id_dokumenty"] not in ids]
        out["podslozky"] += v["podslozky"]
        out["detaily"] += [d for d in v["detaily"] if d not in out["detaily"]]
        # další stránky jen dokud stránka přináší dosud neznámé dokumenty
        if any(f"dok:{s['id_dokumenty']}" not in beh.sklad["dokumenty"].latest for s in v["soubory"]):
            fronta += [s for s in v["stranky"] if s not in videno]
    return out


def k_stazeni(beh: Beh, soubory: list[dict]) -> list[dict]:
    dok = beh.sklad["dokumenty"].latest
    nove = [s for s in soubory if f"dok:{s['id_dokumenty']}" not in dok]
    znovu = [s for s in soubory if dok.get(f"dok:{s['id_dokumenty']}", {}).get("kvalita_textu") in ZNOVU]
    return (nove + znovu)[:beh.limit]


def stahni_dokument(beh: Beh, s: dict, typ: str, pocty: dict, slozka: str | None = None):
    """Stáhne soubor, zapíše záznam do dokumenty.jsonl, vrátí (data, text, kvalita) nebo None."""
    code, data, ct = get(beh, s["url"])
    rec = {"id": f"dok:{s['id_dokumenty']}", "source_url": s["url"], "retrieved_at": ted(),
           "id_dokumenty": s["id_dokumenty"], "typ": typ, "titul": pseudo.nazev(s.get("titul")),
           "info": pseudo.info_dokumentu(s.get("info")), "slozka": slozka, "zverejneno": vismo.datum_iso(s.get("info"))}
    if code != 200 or data is None:
        rec.update(kvalita_textu="chyba_stazeni", http=code)
        _pridej(pocty, "chyby")
        beh.sklad["dokumenty"].add(rec)
        return None
    fmt = vismo.typ_souboru(data, ct)
    text, kvalita = (None, "zip") if fmt == "zip" else vismo.text_dokumentu(data)
    if fmt == "doc" and kvalita == "nastroj_chybi":
        kvalita = "doc_nekonvertovano"
    rec.update(zdroj_sha256=sha256_bytes(data), bajty=len(data), format=fmt, content_type=ct, kvalita_textu=kvalita)
    beh.sklad["dokumenty"].add(rec)
    return data, text, kvalita


# --- usnesení RM a ZM ---

def usneseni(beh: Beh):
    pocty = beh.pocty()
    for klic in ("usneseni_ZM", "usneseni_RM"):
        v = projdi_vypis(beh, SLOZKY[klic])
        for s in k_stazeni(beh, v["soubory"]):
            r = stahni_dokument(beh, s, klic, pocty, SLOZKY[klic])
            if not r or not r[1]:
                continue
            datum = vismo.datum_iso(s.get("titul"))
            ids = {}
            for u in vismo.parse_usneseni(r[1], s["id_dokumenty"]):
                rid = f"usneseni:{s['id_dokumenty']}:{u['cislo']}"
                ids[rid] = ids.get(rid, 0) + 1
                rec = {"id": rid if ids[rid] == 1 else f"{rid}~{ids[rid]}", "source_url": s["url"],
                       "retrieved_at": ted(), **u, "datum": datum,
                       "nazev": pseudo.nazev(u["nazev"]), "text": pseudo.text(u["text"]),
                       "kategorie": None, "kategorie_verze": None, "parser": "integrace.sber.vismo.parse_usneseni"}
                _pridej(pocty, beh.sklad["usneseni"].add(rec))
    return pocty, {"posledni_kontrola": ted()}, None


# --- materiály ZM ---

def materialy_zm(beh: Beh):
    pocty = beh.pocty()
    v = projdi_vypis(beh, SLOZKY["materialy_zm"])
    for s in k_stazeni(beh, v["soubory"]):
        r = stahni_dokument(beh, s, "materialy_zm_balicek", pocty, SLOZKY["materialy_zm"])
        if not r or vismo.typ_souboru(r[0]) != "zip":
            continue
        sha = sha256_bytes(r[0])
        for m in vismo.parse_balicek_zm(r[0]):
            rec = {"id": f"material_zm:{s['id_dokumenty']}:{m['soubor']}", "source_url": s["url"], "retrieved_at": ted(),
                   "zasedani": vismo.zasedani_z_titulu(s.get("titul") or ""), "id_dokumenty_balicku": s["id_dokumenty"],
                   "sha256_balicku": sha, **m, "vec": pseudo.nazev(m["vec"]),
                   "predklada_funkcionar": pseudo.FO if m["predklada_funkcionar"] else None,
                   "text": pseudo.text(m["text"]), "usneseni_cislo": None}
            _pridej(pocty, beh.sklad["materialy_zm"].add(rec))
    return pocty, {"posledni_kontrola": ted()}, None


# --- rozpočtová opatření ---

def rozpoctova_opatreni(beh: Beh):
    pocty = beh.pocty()
    roky = {int(k): v for k, v in (beh.kurzor.get("rocni_slozky") or {}).items()} or dict(RO_ROKY)
    koren = projdi_vypis(beh, SLOZKY["rozpoctova_opatreni"])
    for p in koren["podslozky"]:
        m = re.search(r"(20\d\d)", p["titul"] + p["url"])
        if m and "rozpo" in (p["titul"] + p["url"]).lower():
            roky.setdefault(int(m.group(1)), p["ds"])
    for rok in sorted(r for r in roky if r >= beh.dnes.year - 1):
        url = f"{B}/{rok}%2Drozpoctova%2Dopatreni/ds-{roky[rok]}/archiv=0&p1=72083"
        v = projdi_vypis(beh, url)
        for s in k_stazeni(beh, v["soubory"]):
            r = stahni_dokument(beh, s, "rozpoctove_opatreni", pocty, url)
            if not r:
                continue
            t = vismo.parse_ro_titul(s.get("titul") or "")
            rec = {"id": f"ro:{s['id_dokumenty']}", "source_url": s["url"], "retrieved_at": ted(), "rok": rok,
                   **t, "titul": s.get("titul"), "id_dokumenty": s["id_dokumenty"], "zdroj_sha256": sha256_bytes(r[0]),
                   "kvalita_textu": r[2], "text": pseudo.text(r[1]), "polozky": [], "polozky_stav": "neparsovano"}
            _pridej(pocty, beh.sklad["rozpoctova_opatreni"].add(rec))
    return pocty, {"rocni_slozky": {str(k): v for k, v in sorted(roky.items())}, "posledni_kontrola": ted()}, None


# --- úřední deska (snímek při každém běhu) ---

def uredni_deska(beh: Beh):
    pocty = beh.pocty()
    url = beh.kurzor.get("url") or SLOZKY["uredni_deska"]
    v = projdi_vypis(beh, url)
    znamy = beh.kurzor.get("detail_na_soubory") or {}
    soubory = list(v["soubory"])
    for d in [d for d in v["detaily"] if d not in znamy][:beh.limit]:  # detail -> přílohy
        znamy[d] = [s["id_dokumenty"] for s in vismo.parse_listing(get_text(beh, d), d)["soubory"]]
    for d in v["detaily"]:
        for idd in znamy.get(d, []):
            if idd not in {s["id_dokumenty"] for s in soubory}:
                soubory.append({"id_dokumenty": idd, "titul": None, "info": None, "url": vismo.FILE_URL.format(idd), "detail": d})
    for s in k_stazeni(beh, soubory):
        r = stahni_dokument(beh, s, "uredni_deska", pocty, url)
        if not r:
            continue
        info = s.get("info") or ""
        rec = {"id": f"ud:{s['id_dokumenty']}", "source_url": s["url"], "retrieved_at": ted(),
               "id_dokumenty": s["id_dokumenty"], "titul": pseudo.nazev(s.get("titul")), "info": pseudo.info_dokumentu(info),
               "vyveseno": vismo.datum_iso(m.group(1)) if (m := re.search(r"[Vv]yvěšeno[^0-9]{0,15}([\d. ]{8,12})", info)) else None,
               "sejmuto": vismo.datum_iso(m.group(1)) if (m := re.search(r"[Ss]ejmut[oí][^0-9]{0,15}([\d. ]{8,12})", info)) else None,
               "detail_url": s.get("detail"), "zdroj_sha256": sha256_bytes(r[0]), "bajty": len(r[0]),
               "kvalita_textu": r[2], "text": pseudo.text(r[1])}
        _pridej(pocty, beh.sklad["uredni_deska"].add(rec))
    cas = ted()
    snimek = {"id": f"ud_snimek:{cas}", "source_url": url, "retrieved_at": cas,
              "id_dokumenty": sorted({s["id_dokumenty"] for s in soubory}), "pocet": len({s["id_dokumenty"] for s in soubory})}
    beh.sklad["uredni_deska_snimky"].add(snimek)
    return pocty, {"url": url, "posledni_snimek": cas, "detail_na_soubory": znamy}, f"snímek: {snimek['pocet']} dokumentů"


# --- profil zadavatele ---

def profil_zadavatele(beh: Beh):
    pocty = beh.pocty()
    do_ = date.fromisoformat(beh.kurzor.get("stazeno_do") or "2016-12-31")
    od = max(date(2017, 1, 1), do_ - timedelta(days=60))  # 60 dní překryv: změny stavu zakázek
    hotovo = None
    for i, (a, b) in enumerate(profil.intervaly(od, beh.dnes)):
        if i >= beh.limit:
            break
        url = profil.url_interval(a, b)
        try:
            code, data, _ = get(beh, url)
            if code != 200 or not data:
                raise RuntimeError(f"HTTP {code}: {url}")
            zakazky = profil.parse(data)
            if any(not z["kod"] for z in zakazky):  # neznámá struktura XML – interval nepřijmout
                raise ValueError(f"zakázka bez kódu (neznámá struktura XML): {url}")
        except Exception as e:
            if hotovo is None and isinstance(e, NEDOSAZITELNE):
                raise  # hostitel nedosažitelný hned od začátku -> unreachable
            kurzor = {"stazeno_do": (hotovo or do_).isoformat(), "posledni_kontrola": ted()}
            raise CastecnaChyba(f"{type(e).__name__}: {e}", pocty, kurzor) from e
        for z in zakazky:
            rec = {"id": f"vz:{z['kod']}", "source_url": url, "retrieved_at": ted(), **z,
                   "format_zdroje": "XMLdataVZ v100", "profil_url": profil.PROFIL}
            _pridej(pocty, beh.sklad["verejne_zakazky"].add(rec))
        hotovo = b
    kurzor = {"stazeno_do": max(hotovo or do_, do_).isoformat(), "posledni_kontrola": ted()}
    return pocty, kurzor, None


# --- registr smluv ---

def registr_smluv(beh: Beh):
    pocty = beh.pocty()
    rs = beh.sklad["registr_smluv"]
    poznamka = None
    try:  # nové verze z první stránky vyhledávání
        for v in registr.parse_hledani(get_text(beh, registr.HLEDANI)):
            if f"rs:{v}" not in rs.latest:
                _pridej(pocty, rs.add({"id": f"rs:{v}", "id_verze": v, "source_url": registr.DETAIL_HTML.format(v=v),
                                       "retrieved_at": ted(), "detail": None}))
    except Exception as e:
        poznamka = f"vyhledávání: {type(e).__name__}: {e}"[:300]
    cekajici = [r for r in rs.latest.values() if not r.get("detail")]
    cekajici.sort(key=lambda r: (r.get("publikovano") or "9999", int(r["id_verze"])), reverse=True)
    chyby_za_sebou, uspechy = 0, 0
    for r in cekajici[:min(beh.limit_rs, registr.LIMIT_DETAILU)]:
        url = registr.rs.URL.format(v=r["id_verze"])
        try:
            code, data, _ = get(beh, url)
            if code != 200 or not data:
                raise RuntimeError(f"HTTP {code}")
            det = registr.parse_detail(data, r["id_verze"])
        except Exception as e:
            _pridej(pocty, "chyby")
            chyby_za_sebou += 1
            if chyby_za_sebou >= 5:  # zdroj zjevně nedostupný – nezatěžovat dál
                if uspechy == 0 and isinstance(e, NEDOSAZITELNE):
                    raise e
                raise RuntimeError(f"5 chyb detailu za sebou, poslední {r['id_verze']}: {type(e).__name__}: {e}")
            continue
        chyby_za_sebou, uspechy = 0, uspechy + 1
        _pridej(pocty, rs.add({**{k: v for k, v in r.items() if k not in ("sha256",)}, "detail": det,
                               "detail_sha256": sha256_bytes(data), "retrieved_at": ted()}))
    zbyva = sum(1 for x in rs.latest.values() if not x.get("detail"))
    return pocty, {"ceka_na_detail": zbyva, "posledni_kontrola": ted()}, poznamka


# --- ARES pro nová IČO ---

def _ico_z_dat(sklad: Sklad) -> set[str]:
    out = set()
    for r in sklad["usneseni"].latest.values():
        out.update(r.get("ico") or [])
    for r in sklad["verejne_zakazky"].latest.values():
        out.update(x["ico"] for x in (r.get("ucastnici") or []) + (r.get("dodavatele") or []) if x.get("ico"))
    for r in sklad["registr_smluv"].latest.values():
        out.update(x["ico"] for x in ((r.get("detail") or {}).get("strany") or []) if x.get("ico"))
    for r in sklad["vyber_dodavatele"].latest.values():
        if r.get("vitez_ico"):
            out.add(r["vitez_ico"])
    return {i.zfill(8) for i in out if re.fullmatch(r"\d{6,8}", i)}


def ares(beh: Beh, overit_ico):
    """overit_ico = scripts/ares_overeni.overit_ico (předává scripts/sber.py)."""
    pocty = beh.pocty()
    sub = beh.sklad["subjekty_ares"]
    nova = sorted(i for i in _ico_z_dat(beh.sklad) if f"ico:{i}" not in sub.latest)

    def g(ico):
        code, data, _ = get(beh, ARES_URL.format(ico))
        return code, (json.loads(data) if code == 200 and data else None)

    def g_reg(reg, ico):
        code, data, _ = get(beh, ARES_URL.replace("ekonomicke-subjekty/", reg + "/").format(ico))
        return code, (json.loads(data) if code == 200 and data else None)

    for ico in nova[:beh.limit_ares]:
        r = overit_ico(ico, g, g_reg, pauza=0)  # interval 1 s drží Http
        fo = str(r.get("pravni_forma")) in pseudo.FO_PRAVNI_FORMY
        if fo:
            r.update(obchodni_jmeno=pseudo.FO_ARES, sidlo=None)
        stav = ("ok" if r.get("ares_http") == 200 else "zanikly" if r.get("datum_zaniku")
                else "chybna_kontrolni_cislice" if not r["kontrolni_cislice_ok"] else "nenalezeno")
        _pridej(pocty, sub.add({"id": f"ico:{ico}", "source_url": ARES_URL.format(ico), "retrieved_at": ted(),
                                "ico": ico, "stav": stav, "fyzicka_osoba": fo, **r}))
    return pocty, {"ceka_na_overeni": max(0, len(nova) - beh.limit_ares), "posledni_kontrola": ted()}, None


ZDROJE = {
    "usneseni": usneseni, "materialy_zm": materialy_zm, "rozpoctova_opatreni": rozpoctova_opatreni,
    "uredni_deska": uredni_deska, "profil_zadavatele": profil_zadavatele, "registr_smluv": registr_smluv,
    "ares": ares,
}
SOUBORY = {
    "usneseni": ["dokumenty", "usneseni"], "materialy_zm": ["dokumenty", "materialy_zm"],
    "rozpoctova_opatreni": ["dokumenty", "rozpoctova_opatreni"],
    "uredni_deska": ["dokumenty", "uredni_deska", "uredni_deska_snimky"],
    "profil_zadavatele": ["verejne_zakazky"], "registr_smluv": ["registr_smluv"], "ares": ["subjekty_ares"],
}
