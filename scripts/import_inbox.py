"""Jednorázový převod předávky data/inbox (repo vsetin-osint-handoff) do data/*.jsonl.

Použití:
  python3 scripts/import_inbox.py --handoff ../vsetin-osint-handoff [--dry-run]
Handoff repo se jen čte (`git show <commit>:<soubor>`); do něj se nic nezapisuje.
Záznam: id, source_url, retrieved_at (Europe/Prague, čas zpracování v předávce), sha256 (obsahový
otisk), puvod (repo, větev, commit, soubor, PR). Opakované spuštění nic nezdvojí (dedup id + sha256).
Pseudonymizace: text a názvy přes integrace/sber/pseudo.py; jména odvozená z názvů bodů, které
předávka už pseudonymizovala, se nahrazují i ve skloňovaných tvarech v textu téhož usnesení.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from integrace.sber import ico_fo, pseudo, store, vismo  # noqa: E402
from integrace.sber.profil import PROFIL  # noqa: E402
from integrace.sber.zdroje import ARES_URL, RO_ROKY, SLOZKY  # noqa: E402

REPO = "adamczeko-ai/vsetin-osint-handoff"
VETVE = {  # větev -> PR v handoff repu
    "osint/2026-10-23-inbox-davka-p1": 3,
    "osint/2026-10-23-davka-p2": 4,
    "osint/2026-10-23-davka-p3-graf": 5,
    "osint/2026-10-23-registr-smluv": 7,
}


def git(handoff, *args) -> bytes:
    return subprocess.run(["git", "-C", handoff, *args], check=True, capture_output=True).stdout


def cas(s: str | None) -> str:
    """Čas z předávky -> ISO Europe/Prague. „23. 10. 2026 8:34:07“, ISO UTC „…Z“."""
    if not s:
        raise ValueError("chybí čas")
    if re.match(r"\d{4}-\d\d-\d\dT", s):
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.astimezone(store.TZ).isoformat(timespec="seconds")
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s+(\d{1,2}):(\d\d):(\d\d)", s)
    if not m:
        raise ValueError(f"neznámý formát času: {s}")
    d, mo, y, h, mi, se = map(int, m.groups())
    return datetime(y, mo, d, h, mi, se, tzinfo=store.TZ).isoformat(timespec="seconds")


class Import:
    def __init__(self, sklad: store.Sklad, handoff: str):
        self.sklad, self.handoff = sklad, handoff
        self.pocty: dict[str, dict] = {}
        self.ids: dict[tuple[str, str], int] = {}
        self.vetve: dict[str, str] = {}

    def nacti(self, vetev: str, soubor: str):
        commit = self.vetve.setdefault(vetev, git(self.handoff, "rev-parse", f"origin/{vetev}").decode().strip())
        data = git(self.handoff, "show", f"{commit}:{soubor}")
        self.puvod = {"repo": REPO, "vetev": vetev, "commit": commit, "soubor": soubor, "pr": VETVE[vetev],
                      "sha256_souboru": store.sha256_bytes(data)}
        self.gh_url = f"https://github.com/{REPO}/blob/{commit}/{soubor}"
        return json.loads(data)

    def add(self, nazev: str, rec: dict, retrieved_at: str):
        base = rec["id"]
        n = self.ids[(nazev, base)] = self.ids.get((nazev, base), 0) + 1
        if n > 1:  # duplicitní klíč ve zdroji (např. stejné číslo usnesení dvakrát v dokumentu)
            rec["id"] = f"{base}~{n}"
        rec.setdefault("source_url", self.gh_url)
        rec["retrieved_at"] = retrieved_at
        rec["puvod"] = self.puvod
        stav = self.sklad[nazev].add(rec)
        p = self.pocty.setdefault(nazev, {"nove": 0, "zmeneno": 0, "nezmeneno": 0})
        p[stav] += 1


def import_p1(im: Import):
    v = "osint/2026-10-23-inbox-davka-p1"
    P = "data/inbox/"
    u = im.nacti(v, P + "vsetin_osint_usneseni_2026-10-22.json")
    t_u = cas(u["sbirano"])
    usn_puvod, usn_url = im.puvod, im.gh_url
    k = im.nacti(v, P + "vsetin_osint_kategorie_dodavatele_2026-10-23.json")
    t_k = cas(k["stazeno_zpracovano"])
    kat = {}
    for x in k["usneseni"]:
        kat.setdefault((x["id_dokumenty"], x["cislo"]), []).append(x)
    kat_dok = k["dokumenty"]
    # dokumenty usnesení + usnesení
    im.puvod, im.gh_url = usn_puvod, usn_url
    for org, docs in u["dokumenty"].items():
        for idd, d in sorted(docs.items(), key=lambda x: int(x[0])):
            kd = kat_dok.get(str(d["id_dokumenty"]), {})
            im.add("dokumenty", {"id": f"dok:{d['id_dokumenty']}", "source_url": d["url"], "id_dokumenty": d["id_dokumenty"],
                                 "typ": f"usneseni_{org}", "org_kod": d.get("org_kod") or kd.get("org_kod") or org,
                                 "titul": d["titul"], "zverejneno": vismo.datum_iso(d["zverejneno"]),
                                 "slozka": SLOZKY[f"usneseni_{org}"], "znaku": d.get("znaku"),
                                 "kvalita_textu": d.get("kvalita_textu") or kd.get("kvalita_textu") or "ok"}, t_u)
            datum = vismo.datum_iso(d["titul"])
            for x in d["usneseni"]:
                kk = (kat.get((x["id_dokumenty"], x["cislo"])) or [None]).pop(0) if kat.get((x["id_dokumenty"], x["cislo"])) else None
                jmena = pseudo.jmena_z_pseudonymu(x["nazev"], kk["nazev"]) if kk and kk.get("pseudonymizovano") else []
                im.add("usneseni", {
                    "id": f"usneseni:{x['id_dokumenty']}:{x['cislo']}", "source_url": d["url"], "cislo": x["cislo"],
                    "org": kk["org"] if kk else x["org"], "id_dokumenty": x["id_dokumenty"], "datum": datum,
                    "nazev": pseudo.nazev(kk["nazev"] if kk else x["nazev"], jmena), "text": pseudo.text(x["text"], jmena),
                    "vyroky": x["vyroky"], "ico": x["ico"], "castky": x["castky"],
                    "kategorie": kk["kategorie"] if kk else x.get("kategorie"),
                    "kategorie_verze": k["parser_verze"] if kk else None, "parser": "inbox P1 (pdf.js, Claude in Chrome)"}, t_u)
    for d in u["neparsovano_doc"]:
        org = "RM" if "rady" in d["titul"] or "rada" in d["titul"] else "ZM" if "zastupitel" in d["titul"] or "ZM" in d["titul"] else None
        im.add("dokumenty", {"id": f"dok:{d['id_dokumenty']}", "source_url": vismo.FILE_URL.format(d["id_dokumenty"]),
                             "id_dokumenty": d["id_dokumenty"], "typ": f"usneseni_{org}" if org else "usneseni",
                             "titul": d["titul"], "zverejneno": vismo.datum_iso(d["zverejneno"]), "format": "doc",
                             "kvalita_textu": "doc_nekonvertovano", "poznamka": d["duvod"]}, t_u)
    im.qa_p1 = k["qa"]

    # finance, orgány: soubory + stránky
    f = im.nacti(v, P + "vsetin_osint_finance_organy_2026-10-22.json")
    t_f = cas(f["sbirano_prague"])
    for sl, s in f["slozky_dokumentu"].items():
        tituly = {str(p.get("id_dokumenty")): p.get("titul") for p in s["polozky"] if p.get("id_dokumenty")}
        for idd, fs in s["soubory"].items():
            im.add("dokumenty", {"id": f"dok:{idd}", "source_url": vismo.FILE_URL.format(idd), "id_dokumenty": int(idd),
                                 "typ": sl, "titul": pseudo.nazev(fs.get("titul") or tituly.get(idd)),
                                 "slozka": vismo.BASE + s["slozka"], "content_type": fs.get("content_type"),
                                 "bajty": fs.get("bajty"), "zdroj_sha256": fs.get("sha256"), "stran": fs.get("stran"),
                                 "kvalita_textu": "ok" if fs.get("raw") else (fs.get("poznamka") or "bez_textu"),
                                 "text": pseudo.text(fs.get("raw"))}, t_f)
    for idd, fs in f["dalsi_soubory"]["soubory"].items():
        p = f["dalsi_soubory"]["polozky"].get(idd, {})
        im.add("dokumenty", {"id": f"dok:{idd}", "source_url": vismo.FILE_URL.format(idd), "id_dokumenty": int(idd),
                             "typ": "jiny", "titul": pseudo.nazev(p.get("titul")), "slozka": p.get("zdroj"),
                             "content_type": fs.get("content_type"), "bajty": fs.get("bajty"),
                             "zdroj_sha256": fs.get("sha256"), "stran": fs.get("stran"),
                             "kvalita_textu": "ok" if fs.get("raw") else (fs.get("poznamka") or "bez_textu"),
                             "text": pseudo.text(fs.get("raw"))}, t_f)
    stranky = {s["url"]: s for s in f["stranky"].values()}
    for path, s in f["detailni_stranky"].items():
        stranky.setdefault(vismo.BASE + path, {"url": vismo.BASE + path, **s})
    for url, s in sorted(stranky.items()):
        odk = [{"t": pseudo.nazev(o.get("t")), "h": o.get("h")} for o in s.get("odkazy", [])
               if re.search(r"File\.ashx|/ds-|/d-\d", o.get("h") or "")]
        im.add("stranky", {"id": f"stranka:{url.replace(vismo.BASE, '')}", "source_url": url,
                           "text": pseudo.text(s.get("text")), "odkazy_dokumenty": odk}, t_f)

    # subjekty z ARES
    a = im.nacti(v, P + "vsetin_osint_subjekty_ares_2026-10-23.json")
    t_a = cas(a["stazeno"])
    for s in a["subjekty"]:
        fo = bool(s.get("fyzicka_osoba"))
        im.add("subjekty_ares", {"id": f"ico:{s['ico']}", "source_url": ARES_URL.format(s["ico"]), "ico": s["ico"],
                                 "kontrolni_cislice_ok": s["ico_checksum_ok"], "stav": s["stav"],
                                 "obchodni_jmeno": pseudo.FO_ARES if fo else s.get("obchodniJmeno"),
                                 "pravni_forma": s.get("pravniForma"), "sidlo": None if fo else s.get("sidlo"),
                                 "datum_vzniku": s.get("datumVzniku"), "datum_zaniku": s.get("datumZaniku"),
                                 "datum_aktualizace_ares": s.get("datumAktualizace"), "fyzicka_osoba": fo,
                                 "pocet_usneseni": s.get("pocet_usneseni")}, t_a)

    # materiály ZM
    m = im.nacti(v, P + "vsetin_osint_materialy_zm_2026-10-23.json")
    t_m = cas(m["zpracovano"])
    for b in m["balicky"]:
        im.add("dokumenty", {"id": f"dok:{b['id_dokumenty']}", "source_url": vismo.FILE_URL.format(b["id_dokumenty"]),
                             "id_dokumenty": b["id_dokumenty"], "typ": "materialy_zm_balicek", "titul": b["titul"],
                             "slozka": SLOZKY["materialy_zm"], "zdroj_sha256": b["sha256"], "bajty": b["bajty"],
                             "format": "zip", "kvalita_textu": "zip", "pocet_souboru": b["pocet_souboru"]}, t_m)
    for x in m["materialy"]:
        im.add("materialy_zm", {"id": f"material_zm:{x['id_dokumenty_balicku']}:{x['soubor']}",
                                "source_url": vismo.FILE_URL.format(x["id_dokumenty_balicku"]), "zasedani": x["zasedani"],
                                "id_dokumenty_balicku": x["id_dokumenty_balicku"], "sha256_balicku": x["sha256_balicku"],
                                "soubor": x["soubor"], "vec": pseudo.nazev(x["vec"]),
                                "predklada_funkcionar": pseudo.FO if x.get("predklada_funkcionar") else None,
                                "datum_zasedani": vismo.datum_iso(re.search(r"Pro zasedání dne\s*([\d. ]+\d{4})", x["text"] or "") and
                                                                  re.search(r"Pro zasedání dne\s*([\d. ]+\d{4})", x["text"]).group(1)),
                                "castky": x["castky"], "ma_duvodovou_zpravu": x["ma_duvodovou_zpravu"],
                                "usneseni_cislo": x.get("usneseni_cislo"), "shoda_nazvu": x.get("shoda_nazvu"),
                                "text": pseudo.text(x["text"])}, t_m)

    # rozpočtová opatření
    r = im.nacti(v, P + "vsetin_osint_rozpoctova_opatreni_2026-10-23.json")
    t_r = cas(r["zpracovano"])
    for o in r["opatreni"]:
        im.add("dokumenty", {"id": f"dok:{o['id_dokumenty']}", "source_url": o["zdroj_url"], "id_dokumenty": o["id_dokumenty"],
                             "typ": "rozpoctove_opatreni", "titul": o["titul"], "zdroj_sha256": o.get("sha256"),
                             "slozka": f"{vismo.BASE}/{o['rok']}%2Drozpoctova%2Dopatreni/ds-{RO_ROKY.get(o['rok'])}/archiv=0&p1=72083",
                             "kvalita_textu": "ok" if o["polozky"] else "bez_rozpadu_polozek"}, t_r)
        im.add("rozpoctova_opatreni", {"id": f"ro:{o['id_dokumenty']}", "source_url": o["zdroj_url"], "rok": o["rok"],
                                       "cislo": o["cislo"], "schvaluje": o["schvaluje"], "titul": o["titul"],
                                       "id_dokumenty": o["id_dokumenty"], "zdroj_sha256": o.get("sha256"),
                                       "polozky": [{**p, "nazev": pseudo.nazev(p.get("nazev")), "text": pseudo.text(p.get("text"))}
                                                   for p in o["polozky"]],
                                       "polozky_stav": "inbox ro-v1" if o["polozky"] else "neparsovano"}, t_r)


def import_p2(im: Import):
    v = "osint/2026-10-23-davka-p2"
    P = "data/inbox/"
    c = im.nacti(v, P + "vsetin_osint_casove_osy_2026-10-23.json")
    t = cas(c["zpracovano"])
    for projekt in ("lavka", "nadrazi"):
        for x in c[projekt]:
            klic = x.get("cislo") or f"{x.get('datum')}:{x.get('nazev')}"
            im.add("casove_osy", {"id": f"osa:{projekt}:{x['typ']}:{klic}", "source_url": x.get("zdroj_url") or im.gh_url,
                                  "projekt": projekt, **{k: v_ for k, v_ in x.items() if k != "zdroj_url"},
                                  "nazev": pseudo.nazev(x.get("nazev")), "akce": pseudo.nazev(x.get("akce")),
                                  "parser_verze": c["parser_verze"]}, t)
    d = im.nacti(v, P + "vsetin_osint_uredni_deska_2026-10-23.json")
    t = cas(d["zpracovano"])
    for x in d["dokumenty"]:
        im.add("uredni_deska", {"id": f"ud:{x['id_dokumenty']}", "source_url": vismo.FILE_URL.format(x["id_dokumenty"]),
                                "id_dokumenty": x["id_dokumenty"], "titul": pseudo.nazev(x["titul"]),
                                "info": pseudo.info_dokumentu(x["info"]), "vyveseno": x["vyveseno"], "sejmuto": x["sejmuto"],
                                "content_type": x["content_type"], "bajty": x["bajty"], "zdroj_sha256": x["sha256"],
                                "stran": x["stran"], "kvalita_textu": "ok" if x.get("raw") else "bez_textu",
                                "kategorie_ud": x["kategorie_ud"], "text": pseudo.text(x["raw"])}, t)
    im.add("uredni_deska_snimky", {"id": f"ud_snimek:{t}", "source_url": d["zdroj"],
                                   "id_dokumenty": sorted(x["id_dokumenty"] for x in d["dokumenty"]),
                                   "pocet": len(d["dokumenty"])}, t)
    z = im.nacti(v, P + "vsetin_osint_verejne_zakazky_2026-10-23.json")
    t = cas(z["zpracovano"])
    for x in z["zakazky"]:
        # 1 záznam (2025) bez kódu: formát XMLdataVZ v100 parser předávky nepřečetl -> náhradní id, doplní živý sběr
        vid = x["kod"] or "bez-kodu:" + store.sha256_bytes((x.get("nazev") or "").encode())[:12]
        im.add("verejne_zakazky", {"id": f"vz:{vid}", "source_url": PROFIL, **x, "kod_chybi": not x["kod"] or None,
                                   "ucastnici": [{**u, "nazev": pseudo.nazev_subjektu(u.get("nazev"))} for u in x["ucastnici"]],
                                   "dodavatele": [{**u, "nazev": pseudo.nazev_subjektu(u.get("nazev"))} for u in x["dodavatele"]],
                                   "format_zdroje": f"inbox P2f {z['parser_verze']}", "profil_url": PROFIL}, t)
    im.ukazatele_vz = z["ukazatele"]
    w = im.nacti(v, P + "vsetin_osint_vyber_dodavatele_v2_2026-10-23.json")
    t = cas(w["zpracovano"])
    for x in w["vyber_dodavatele"]:
        im.add("vyber_dodavatele", {"id": f"vd:{x['cislo_usneseni']}", "source_url": x["zdroj_url"], **x,
                                    "zakazka": pseudo.nazev(x.get("zakazka")), "nazev_bodu": pseudo.nazev(x.get("nazev_bodu")),
                                    "vitez_nazev": pseudo.nazev_subjektu(x.get("vitez_nazev")),
                                    "parser_verze": w["parser_verze"]}, t)


def import_p3(im: Import):
    g = im.nacti("osint/2026-10-23-davka-p3-graf", "data/inbox/vsetin_osint_graf_entit_2026-10-23.json")
    t = cas(g["zpracovano"])
    for u in g["uzly"]:
        rec = {**u, "label": pseudo.nazev_subjektu(u.get("label")) if u["typ"] == "subjekt" and not u.get("fo") else u.get("label")}
        if u["typ"] == "usneseni":
            rec["label"] = pseudo.nazev(u.get("label"))
        rec["source_url"] = u.get("zdroj_url") or im.gh_url
        rec.pop("zdroj_url", None)
        im.add("graf_uzly", rec, t)
    for h in g["hrany"]:
        im.add("graf_hrany", {"id": f"hrana:{h['typ']}:{h['z']}>{h['c']}", **h}, t)


def import_rs(im: Import):
    r = im.nacti("osint/2026-10-23-registr-smluv", "data/inbox/vsetin_osint_registr_smluv_2026-10-23.json")
    t = cas(r["zpracovano"])
    for x in r["smlouvy"]:
        rec = {"id": f"rs:{x['id_smlouvy']}", "id_verze": x["id_smlouvy"], "source_url": x["url"],
               **{k: v for k, v in x.items() if k not in ("id_smlouvy", "url")},
               "predmet": pseudo.nazev(x.get("predmet")),
               "smluvni_strany": [pseudo.nazev_subjektu(s) for s in x.get("smluvni_strany") or []],
               "detail": None, "parser_verze": r["parser_verze"]}
        im.add("registr_smluv", rec, t)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="import_inbox.py")
    ap.add_argument("--handoff", required=True, help="klon adamczeko-ai/vsetin-osint-handoff (jen čtení)")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--bez-ico-fo", action="store_true",
                    help="servisní: nepseudonymizovat IČO OSVČ (spustit ico_fo.aplikuj až po sloučení s dalšími daty)")
    a = ap.parse_args(argv)
    sklad = store.Sklad(a.data_dir)
    im = Import(sklad, a.handoff)
    zac = store.ted()
    for fn in (import_p1, import_p2, import_p3, import_rs):
        fn(im)
    if a.dry_run:
        print(json.dumps({"dry_run": True, "pocty": im.pocty}, ensure_ascii=False, indent=1))
        return 0
    sklad.flush()
    man_path = os.path.join(a.data_dir, "manifest.json")
    man = store.nacti_manifest(man_path)
    man["import_inbox"] = {
        "cas": zac, "repo": REPO, "vetve": {v: {"commit": c, "pr": VETVE[v]} for v, c in im.vetve.items()},
        "pocty": im.pocty, "qa_p1": im.qa_p1, "ukazatele_vz_p2f": im.ukazatele_vz,
        "neprevzato": ["ico_frekvence a ico_jmeno_heuristika (usnesení; odvoditelné, heuristika obsahuje jména)",
                       "plný raw text výpisů usnesení (text je u jednotlivých usnesení, originál na source_url)",
                       "vyber_dodavatele v1 (nahrazeno v2 z PR #4)", "fakta/statistika grafu (odvoditelné z uzlů a hran)",
                       "RUNLOG a průzkum konkurence (Markdown, ponecháno v handoff repu)"],
    }
    # výchozí kurzory pro inkrementální sběr
    kurzory = {
        # předávka P2f obsahuje jen 2017–2023 (formát v100 od 2024 nepřečten) -> živý sběr od 2024-01-01
        "profil_zadavatele": {"stazeno_do": "2023-12-31"},
        "rozpoctova_opatreni": {"rocni_slozky": {str(k): v for k, v in sorted(RO_ROKY.items())}},
        "uredni_deska": {"url": SLOZKY["uredni_deska"]},
    }
    for z, k in kurzory.items():
        zz = man.setdefault("zdroje", {}).setdefault(z, {"chyby": []})
        zz["kurzor"] = {**k, **(zz.get("kurzor") or {})}
    # § 5 protokolu: IČO OSVČ pseudonymizovat (po zápisu, přes všechny soubory najednou)
    if not a.bez_ico_fo:
        man["pseudonymizace_ico_fo"] = ico_fo.aplikuj(a.data_dir, objekty=[man])
    store.zapis_manifest(man_path, man, None, a.data_dir)
    print(json.dumps({"pocty": im.pocty, "vetve": im.vetve}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
