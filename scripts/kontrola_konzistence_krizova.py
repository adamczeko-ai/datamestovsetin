"""Rozšíření scripts/kontrola_konzistence.py o kontroly K7–K13 (jen čtení dat).

Zapojení: kontrola_konzistence.py na konci seznamu KONTROLY přidá KONTROLY_DALSI z tohoto modulu.
Výstup a stavový model (ke_kontrole → člověk) jsou společné, viz kontrola_konzistence.py.

  K7  odvozené soubory (red_flags, akce_timeline, signaly) odpovídají přegenerování ze zdrojů
  K8  tatáž smlouva (ID verze registru / Hlídače státu) má ve všech souborech stejnou částku na stejném základu DPH
  K9  řetězce, které jsou cestou do repa (volitelně s #/json/pointer), odkazují na existující soubor a pointer
  K10 ruční stav signálu bez signálu (osiřelý) a anomálie A-* se stejným ID, ale různým popisem
  K11 datum minulé události v budoucnosti; časová osa kauzy není vzestupná
  K12 závěrečný účet × MONITOR FIN 2-12 M (upravený rozpočet a skutečnost; respektuje anotaci 8115 + 8117 + 8118)
  K13 duplicitní ID v seznamu záznamů
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

kk = None  # modul kontrola_konzistence; nastaví ho kontrola_konzistence.py při načtení (bez kruhového importu)

TZ = ZoneInfo("Europe/Prague")
VYNECHAT = ("data/schema/", "data/analyzy/konzistence.json")


def _soubory():
    for f in sorted(glob.glob(kk.p("data", "**", "*.json"), recursive=True)):
        rel = os.path.relpath(f, kk.ROOT)
        if rel.startswith(VYNECHAT[0]) or rel == VYNECHAT[1]:
            continue
        with open(f, encoding="utf-8") as fh:
            yield rel, json.load(fh)


def _walk(o, path=()):
    yield path, o
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, path + (i,))


def _ptr(path):
    return "/" + "/".join(str(x).replace("~", "~0").replace("/", "~1") for x in path)


def _resolve(obj, pointer):
    for k in [x for x in pointer.strip("/").split("/") if x != ""]:
        k = k.replace("~1", "/").replace("~0", "~")
        obj = obj[int(k)] if isinstance(obj, list) else obj[k]
    return obj


def k7_odvozene():
    if not os.path.exists(kk.p("scripts", "signaly_v2.py")):
        return []
    out = []
    t = tempfile.mkdtemp()
    try:
        for d in ("data", "scripts"):
            shutil.copytree(kk.p(d), os.path.join(t, d))
        for s in ("scripts/analyzy.py", "scripts/signaly_v2.py"):
            r = subprocess.run([sys.executable, s], cwd=t, capture_output=True, text=True)
            if r.returncode:
                raise ValueError(f"{s} selhal: {r.stderr.strip()[-200:]}")
        for f in ("red_flags.json", "akce_timeline.json", "signaly.json"):
            rel = f"data/analyzy/{f}"
            with open(os.path.join(t, rel), encoding="utf-8") as fh:
                a = json.load(fh)
            b = kk.nacti(rel)
            a.pop("vygenerovano", None), b.pop("vygenerovano", None)
            if a != b:
                na = len(a.get("signaly", a.get("akce", [])))
                nb = len(b.get("signaly", b.get("akce", [])))
                out.append(kk.rozpor("K7", f"{rel}: neodpovídá přegenerování ze zdrojů (scripts/analyzy.py, scripts/signaly_v2.py)",
                                     kk.strana(rel, "$ (v repu)", {"zaznamu": nb}),
                                     kk.strana("přegenerováno", "$", {"zaznamu": na}),
                                     navrh="přegenerovat (mechanická oprava)"))
    finally:
        shutil.rmtree(t, ignore_errors=True)
    return out


ID_KLICE = ("version_id", "id_verze", "hs", "id")
CASTKA = {"bez_DPH": "bez_DPH", "bez_dph": "bez_DPH", "bez_DPH_registr": "bez_DPH",
          "s_DPH": "s_DPH", "s_dph": "s_DPH", "s_DPH_registr": "s_DPH"}


def k8_castky_smluv():
    idx = collections.defaultdict(list)
    for rel, d in _soubory():
        if rel.startswith("data/analyzy/"):
            continue
        for path, v in _walk(d):
            if not isinstance(v, dict):
                continue
            sid = next((str(v[k]) for k in ID_KLICE if isinstance(v.get(k), (str, int)) and re.fullmatch(r"\d{6,9}", str(v.get(k)))), None)
            if not sid and isinstance(v.get("url"), str):
                m = re.search(r"hlidacstatu\.cz/Detail/(\d+)", v["url"])
                sid = m.group(1) if m else None
            if not sid:
                continue
            for k, zaklad in CASTKA.items():
                c = v.get(k)
                if isinstance(c, (int, float)) and c:
                    idx[(sid, zaklad)].append((round(float(c), 2), rel, _ptr(path + (k,))))
    out = []
    for (sid, zaklad), h in sorted(idx.items()):
        if len({round(c) for c, _, _ in h}) > 1:
            a = h[0]
            b = next(x for x in h if round(x[0]) != round(a[0]))
            out.append(kk.rozpor("K8", f"smlouva {sid}: různé částky {zaklad} v datech",
                                 kk.strana(a[1], a[2], a[0]), kk.strana(b[1], b[2], b[0]), vyskyty=len(h)))
    return out


RE_CESTA = re.compile(r"^((?:data|scripts|docs|tests|ai|integrace|raw)/[^\s#*<>{}]+?)(#(/\S*))?$")


def k9_odkazy():
    out = []
    for rel, d in _soubory():
        for path, v in _walk(d):
            if not isinstance(v, str):
                continue
            m = RE_CESTA.match(v.strip())
            if not m:
                continue
            cil = m.group(1).rstrip(").,;")
            if not os.path.exists(kk.p(cil)):
                out.append(kk.rozpor("K9", f"odkaz na neexistující soubor {cil}", kk.strana(rel, _ptr(path), v),
                                     kk.strana(cil, "(soubor)", "neexistuje")))
            elif m.group(3) and cil.endswith(".json"):
                try:
                    _resolve(kk.nacti(cil), m.group(3))
                except (KeyError, IndexError, ValueError, TypeError):
                    out.append(kk.rozpor("K9", f"neplatný JSON pointer v odkazu na {cil}", kk.strana(rel, _ptr(path), v),
                                         kk.strana(cil, m.group(3), "nenalezeno")))
    return out


def k10_signaly():
    out = []
    sp, tp = "data/analyzy/signaly.json", "data/analyzy/signaly_stavy.json"
    if os.path.exists(kk.p(sp)) and os.path.exists(kk.p(tp)):
        ids = {s["id"] for s in kk.nacti(sp)["signaly"]}
        for k in kk.nacti(tp).get("stavy", {}):
            if k not in ids:
                out.append(kk.rozpor("K10", f"ruční stav {k} nemá signál (osiřelý)", kk.strana(tp, f"/stavy/{k}", k),
                                     kk.strana(sp, "/signaly[*]/id", "chybí")))
    popisy = collections.defaultdict(list)
    for rel, d in _soubory():
        if rel.startswith("data/analyzy/"):
            continue
        for path, v in _walk(d):
            if isinstance(v, dict) and isinstance(v.get("id"), str) and re.fullmatch(r"A-\d{4}-\d{2}", v["id"]) and v.get("popis"):
                popisy[v["id"]].append((v["popis"].strip(), rel, _ptr(path + ("popis",))))
    for aid, h in sorted(popisy.items()):
        if len({x[0] for x in h}) > 1:
            a = h[0]
            b = next(x for x in h if x[0] != a[0])
            out.append(kk.rozpor("K10", f"anomálie {aid}: stejné ID, různý popis", kk.strana(a[1], a[2], a[0][:200]),
                                 kk.strana(b[1], b[2], b[0][:200])))
    return out


KLICE_MINULE = {"datum", "podpis", "uverejneno", "datum_uzavreni", "zverejneno", "datum_vzniku", "datum_zaniku"}


def _datum(s):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s) or re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", s)
    if not m:
        return None
    g = m.groups()
    try:
        return datetime(int(g[0]), int(g[1]), int(g[2])).date() if len(g[0]) == 4 else datetime(int(g[2]), int(g[1]), int(g[0])).date()
    except ValueError:
        return "neplatne"


def k11_data(dnes=None):
    dnes = dnes or datetime.now(TZ).date()
    out = []
    for rel, d in _soubory():
        for path, v in _walk(d):
            if path and isinstance(v, str) and path[-1] in KLICE_MINULE:
                x = _datum(v)
                if x == "neplatne":
                    out.append(kk.rozpor("K11", "neplatné datum", kk.strana(rel, _ptr(path), v), kk.strana("kalendář", "-", "neexistuje")))
                elif x and x > dnes:
                    out.append(kk.rozpor("K11", "datum minulé události leží v budoucnosti", kk.strana(rel, _ptr(path), v),
                                         kk.strana("dnes (Europe/Prague)", "-", dnes.isoformat())))
    for f in sorted(glob.glob(kk.p("data", "kauzy", "K-*.json"))):
        rel = os.path.relpath(f, kk.ROOT)
        prev = None
        for i, u in enumerate(kk.nacti(rel).get("casova_osa", [])):
            m = re.match(r"^\d{4}-\d{2}-\d{2}", str(u.get("datum", "")))
            if m and prev and m.group(0) < prev[0]:
                out.append(kk.rozpor("K11", "časová osa kauzy není seřazená vzestupně",
                                     kk.strana(rel, f"/casova_osa/{prev[1]}/datum", prev[0]),
                                     kk.strana(rel, f"/casova_osa/{i}/datum", m.group(0))))
            if m:
                prev = (m.group(0), i)
    return out


def k12_zu_monitor():
    zp, mp = "data/zaverecny_ucet/zaverecny_ucet_2023_2025.json", "data/monitor/finm_rada_2020_2025_vsetin.json"
    if not (os.path.exists(kk.p(zp)) and os.path.exists(kk.p(mp))):
        return []
    zu, mo = kk.nacti(zp)["roky"], kk.nacti(mp)["roky"]
    out = []
    for rok, r in sorted(zu.items()):
        if rok not in mo:
            continue
        roz = r.get("rozpocet", {})
        for klic, kod in (("prijmy", "4200"), ("vydaje", "4430"), ("kapitalove_vydaje", "4220"), ("pol_8115", "8115")):
            z, m = roz.get(klic) or {}, mo[rok].get(kod)
            if not m:
                continue
            for i, pole in ((1, "upraveny"), (2, "skutecnost")):
                h = z.get(pole)
                if h is None:
                    continue
                cil, ozn = m[i], kod
                if klic == "pol_8115" and pole == "skutecnost" and z.get("skutecnost_zahrnuje_8117_8118"):
                    cil = m[2] + mo[rok].get("8117", [0, 0, 0])[2] + mo[rok].get("8118", [0, 0, 0])[2]
                    ozn = "8115+8117+8118"
                if abs(h - cil) > 0.005:
                    out.append(kk.rozpor("K12", f"ZÚ {rok} {klic}.{pole} ≠ MONITOR {ozn}",
                                         kk.strana(zp, f"/roky/{rok}/rozpocet/{klic}/{pole}", h),
                                         kk.strana(mp, f"/roky/{rok}/{kod}/{i}", round(cil, 2))))
    return out


def k13_duplicity():
    out = []
    for rel, d in _soubory():
        if rel.startswith("data/analyzy/"):
            continue
        for path, v in _walk(d):
            if isinstance(v, list) and len(v) > 1 and all(isinstance(x, dict) for x in v):
                c = collections.Counter(str(x["id"]) for x in v if x.get("id") not in (None, ""))
                for k, n in sorted(c.items()):
                    if n > 1:
                        kopie = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in v if str(x.get("id")) == k}
                        out.append(kk.rozpor("K13", f"ID {k} je v seznamu {n}× ({'shodné kopie' if len(kopie) == 1 else 'různý obsah'})",
                                             kk.strana(rel, _ptr(path), k), kk.strana(rel, _ptr(path), n)))
    return out


KONTROLY_DALSI = [
    ("K7", "odvozené soubory odpovídají přegenerování ze zdrojů", k7_odvozene),
    ("K8", "tatáž smlouva má všude stejnou částku (stejný základ DPH)", k8_castky_smluv),
    ("K9", "odkazy na soubory a JSON pointery v datech", k9_odkazy),
    ("K10", "ruční stavy signálů a jednoznačnost ID anomálií", k10_signaly),
    ("K11", "data minulých událostí a pořadí časové osy kauz", k11_data),
    ("K12", "závěrečný účet × MONITOR FIN 2-12 M", k12_zu_monitor),
    ("K13", "duplicitní ID v seznamech", k13_duplicity),
]
