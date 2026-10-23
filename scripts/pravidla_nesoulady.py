"""Deterministická pravidla R13–R18 („nesoulady k vysvětlení“).

Čisté funkce (testovatelné) + adaptéry na existující data repa. Výstup = seznam signálů
ve tvaru red_flags@1 (kod, zavaznost, popis, castka_Kc, odkazy), které scripts/signaly_v2.py
převede na signaly@2.

R13 kumulace dodatků vs. původní smlouva (§ 222 odst. 4 a 9 ZZVZ)
R14 veřejná zakázka těsně pod limitem VZMR / součet smluv jednoho dodavatele nad limitem
R15 zrušená VZ následovaná prodloužením / dodatkem stávající smlouvy
R16 cenový rozdíl návrh / usnesení / smlouva / rozpočet u téže akce
R17 prodleva usnesení → podpis smlouvy (nebo smlouva před usnesením)
R18 nárůst ceny mezi první a poslední smlouvou téže akce

Limity a jejich zdroje: data/analyzy/pravidla_konfigurace.json.
Signály nejsou zjištěním pochybení – slouží k prioritizaci ověřování.
"""
import datetime as dt
import json
import re
import unicodedata


def fmt(x):
    return f"{x:,.0f}".replace(",", " ")


def nacti_konfiguraci(path="data/analyzy/pravidla_konfigurace.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def datum(s):
    """Přijme 'YYYY-MM-DD' nebo 'DD.MM.YYYY'; jinak None."""
    if not s:
        return None
    for f in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------- R13
def r13_dodatky(smlouva, konf):
    """smlouva: {nazev, druh: 'stavebni_prace'|'dodavky_sluzby'|None, puvodni, zaklad, dodatky:[{id, castka|None}], odkazy}
    Vrací seznam signálů (0 nebo 1)."""
    z = konf["zmena_zavazku_222"]
    puv = smlouva.get("puvodni")
    dod = smlouva.get("dodatky") or []
    if not puv or not dod:
        return []
    known = [d["castka"] for d in dod if d.get("castka") is not None]
    nezname = len(dod) - len(known)
    if not known:
        return []
    cisty = sum(known)
    absolutni = sum(abs(x) for x in known)
    druh = smlouva.get("druh")
    limit = z["odst4_stavebni_prace"] if druh == "stavebni_prace" else z["odst4_dodavky_sluzby"]
    pomer = absolutni / puv
    pozn_druh = "" if druh else " Druh plnění neurčen – použit přísnější limit 10 %."
    pozn_nez = f" {nezname} dodatků bez hodnoty – součet může být vyšší." if nezname else ""
    zaklad = smlouva.get("zaklad", "neurceno")
    base = (f"{smlouva['nazev']}: {len(known)} dodatků, součet změn {fmt(cisty)} Kč "
            f"(absolutně {fmt(absolutni)} Kč) = {pomer*100:.1f} % původní ceny {fmt(puv)} Kč ({zaklad}).")
    if pomer > z["odst9_souhrn_odst5_6"]:
        zav, txt = "vysoka", f" Překračuje i 30 % (§ 222 odst. 9) – ověřit právní titul změn.{pozn_druh}{pozn_nez}"
    elif pomer > limit:
        zav, txt = "stredni", f" Nad limitem § 222 odst. 4 ({limit*100:.0f} %) – ověřit, podle kterého ustanovení byly změny provedeny.{pozn_druh}{pozn_nez}"
    elif pomer > limit * z["pasmo_blizko_limitu"]:
        zav, txt = "nizka", f" Blízko limitu § 222 odst. 4 ({limit*100:.0f} %).{pozn_druh}{pozn_nez}"
    else:
        return []
    return [{"kod": "R13-kumulace-dodatku", "zavaznost": zav, "popis": base + txt,
             "castka_Kc": cisty, "odkazy": list(smlouva.get("odkazy") or [])}]


def r13_ze_zakazek(vz):
    """Adaptér: verejne_zakazky.json → vstupy R13 (jen zakázky s dodatky v datech)."""
    out = []
    for zk in vz.get("zakazky", []):
        sm = zk.get("smlouva") or {}
        dod = sm.get("dodatky")
        if not dod:
            continue
        druh_txt = (zk.get("druh") or "").lower()
        druh = "stavebni_prace" if "stavebn" in druh_txt else ("dodavky_sluzby" if re.search(r"dodáv|služb", druh_txt) else None)
        # dodatky v datech mají pole 'Kc' bez určení základu → porovnáváme se s_DPH, pokud bez_DPH chybí
        puv, zaklad = (sm.get("bez_DPH"), "bez_DPH") if sm.get("bez_DPH") else (sm.get("s_DPH"), "s_DPH (základ dodatků neurčen)")
        out.append({"nazev": zk["nazev"], "druh": druh, "puvodni": puv, "zaklad": zaklad,
                    "dodatky": [{"id": d.get("id"), "castka": d.get("Kc")} for d in dod],
                    "odkazy": [sm.get("url")] + [f"https://www.hlidacstatu.cz/Detail/{d['id']}" for d in dod if d.get("id")]})
    return out


# ---------------------------------------------------------------- R14
def limit_vzmr(d, druh, konf):
    for p in konf["vzmr_limity_bez_DPH"]:
        od = datum(p["od"])
        do = datum(p["do"]) if p["do"] else None
        if d >= od and (do is None or d <= do):
            return p[druh]
    return None


def r14_pod_limitem(zakazka, konf):
    """zakazka: {nazev, druh: 'stavebni_prace'|'dodavky_sluzby'|None, predp_hodnota (bez DPH), datum, odkazy}"""
    d = datum(zakazka.get("datum"))
    hod = zakazka.get("predp_hodnota")
    if not d or not hod:
        return []
    druhy = [zakazka["druh"]] if zakazka.get("druh") else ["dodavky_sluzby", "stavebni_prace"]
    out = []
    for druh in druhy:
        lim = limit_vzmr(d, druh, konf)
        if lim and konf["pasmo_tesne_pod_limitem"] * lim <= hod < lim:
            jisty = "" if zakazka.get("druh") else " (druh plnění neurčen – limit platí jen pokud jde o tento druh)"
            out.append({"kod": "R14-tesne-pod-limitem-VZMR", "zavaznost": "nizka",
                        "popis": f"{zakazka['nazev']}: předp. hodnota {fmt(hod)} Kč = {hod/lim*100:.1f} % limitu VZMR "
                                 f"{fmt(lim)} Kč pro {druh.replace('_', ' ')} k {d.isoformat()}{jisty}.",
                        "castka_Kc": hod, "odkazy": list(zakazka.get("odkazy") or [])})
    return out


def r14_deleni(smlouvy, konf, okno_dni=365):
    """smlouvy: [{dodavatel_ico, druh, bez_DPH, datum, id}] – součet smluv jednoho dodavatele v okně,
    každá pod limitem VZMR, součet nad limitem → kandidát na dělení předmětu (jen pokud jde o stejný předmět – ověřit)."""
    out = []
    by = {}
    for s in smlouvy:
        if s.get("dodavatel_ico") and s.get("bez_DPH") and datum(s.get("datum")) and s.get("druh"):
            by.setdefault((s["dodavatel_ico"], s["druh"]), []).append(s)
    for (ico, druh), ss in sorted(by.items()):
        ss.sort(key=lambda s: datum(s["datum"]))
        for i, s0 in enumerate(ss):
            d0 = datum(s0["datum"])
            okno = [s for s in ss[i:] if (datum(s["datum"]) - d0).days <= okno_dni]
            lim = limit_vzmr(d0, druh, konf)
            if len(okno) >= 2 and lim and all(s["bez_DPH"] < lim for s in okno) and sum(s["bez_DPH"] for s in okno) >= lim:
                out.append({"kod": "R14-deleni-predmetu", "zavaznost": "nizka",
                            "popis": f"Dodavatel IČO {ico}: {len(okno)} smluv ({druh.replace('_', ' ')}) do {okno_dni} dní, každá pod limitem VZMR "
                                     f"{fmt(lim)} Kč, součet {fmt(sum(s['bez_DPH'] for s in okno))} Kč – ověřit, zda jde o jeden předmět.",
                            "castka_Kc": sum(s["bez_DPH"] for s in okno), "odkazy": [s.get("id") for s in okno]})
                break
    return out


# ---------------------------------------------------------------- R15
STOP = {"a", "v", "ve", "na", "pro", "k", "ke", "o", "s", "se", "z", "do", "c", "č", "smlouve", "smlouvy", "smlouva",
        "dodatek", "mesta", "vsetin", "vsetine", "vsetina", "ii", "i", "iii"}


def tokeny(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return {t for t in re.findall(r"[a-z0-9]{3,}", s) if t not in STOP}


def shoda(a, b):
    """Podíl tokenů kratšího názvu, které jsou v delším (robustní vůči 'Dodatek č. 2 ke smlouvě o …')."""
    ta, tb = tokeny(a), tokeny(b)
    if not ta or not tb:
        return 0.0
    m = min(len(ta), len(tb))
    return len(ta & tb) / m


def r15_zruseni_prodlouzeni(zrusene, smlouvy, konf):
    """zrusene: [{zakazka, terminy:[YYYY-MM-DD]}]; smlouvy: [{id, predmet, datum}]."""
    k = konf["zruseni_a_prodlouzeni"]
    out = []
    for z in zrusene:
        terminy = sorted(d for d in (datum(t) for t in z.get("terminy", [])) if d)
        if not terminy:
            continue
        for s in smlouvy:
            ds = datum(s.get("datum"))
            pred = s.get("predmet") or ""
            if not ds or not any(w in pred.lower() for w in k["klicova_slova_prodlouzeni"]):
                continue
            pred_zr = [t for t in terminy if 0 <= (ds - t).days <= k["okno_dni"]]
            if pred_zr and shoda(z["zakazka"], pred) >= k["min_shoda_nazvu"]:
                out.append({"kod": "R15-zruseni-VZ-a-prodlouzeni", "zavaznost": "stredni",
                            "popis": f"{z['zakazka']}: zrušeno {len(terminy)}× (naposledy {pred_zr[-1].isoformat()}), "
                                     f"poté {ds.isoformat()} '{pred.strip()}' – ověřit hodnotu a právní titul prodloužení bez soutěže.",
                            "castka_Kc": s.get("castka"), "odkazy": [f"https://www.hlidacstatu.cz/Detail/{s['id']}"]})
    return out


# ---------------------------------------------------------------- R16
def r16_cenovy_rozdil(akce, konf):
    """akce: {akce, body:[{typ, castka, zaklad, zdroj, ref?}]}"""
    t = konf["cenovy_rozdil"]

    def rozdil(a, b):
        d = abs(a["castka"] - b["castka"])
        return d > t["tolerance_absolutni_Kc"] and d > t["tolerance_relativni"] * max(a["castka"], b["castka"])

    def odk(*bb):
        return [x for b in bb for x in (b.get("ref"), b["zdroj"]) if x]

    out = []
    body = akce.get("body", [])
    by = {}
    for b in body:
        by.setdefault(b["typ"], []).append(b)
    for a in by.get("navrh", []):
        for b in by.get("schvaleno", []):
            if a["zaklad"] == b["zaklad"] and rozdil(a, b):
                out.append({"kod": "R16-cena-navrh-vs-schvaleno", "zavaznost": "nizka",
                            "popis": f"{akce['akce']}: cena v návrhu {fmt(a['castka'])} Kč ≠ schváleno {fmt(b['castka'])} Kč "
                                     f"(rozdíl {fmt(b['castka']-a['castka'])} Kč) – ověřit zdůvodnění změny na jednání.",
                            "castka_Kc": b["castka"] - a["castka"], "odkazy": odk(a, b)})
    for a in by.get("schvaleno", []):
        for b in by.get("smlouva", []):
            if a["zaklad"] == b["zaklad"] and rozdil(a, b):
                out.append({"kod": "R16-cena-schvaleno-vs-smlouva", "zavaznost": "stredni",
                            "popis": f"{akce['akce']}: schváleno {fmt(a['castka'])} Kč ≠ smlouva {fmt(b['castka'])} Kč ({a['zaklad']}).",
                            "castka_Kc": b["castka"] - a["castka"], "odkazy": odk(a, b)})
    for a in by.get("rozpocet", []):
        for b in by.get("smlouva", []):
            if b["zaklad"] in ("s_DPH", "neurceno") and b["castka"] - a["castka"] > t["tolerance_absolutni_Kc"]:
                out.append({"kod": "R16-smlouva-nad-rozpoctem", "zavaznost": "stredni",
                            "popis": f"{akce['akce']}: smlouva {fmt(b['castka'])} Kč ({b['zaklad']}) převyšuje rozpočet akce "
                                     f"{fmt(a['castka'])} Kč o {fmt(b['castka']-a['castka'])} Kč – ověřit krytí (další RO, odpočet DPH, etapizace).",
                            "castka_Kc": b["castka"] - a["castka"], "odkazy": odk(a, b)})
    return out


# ---------------------------------------------------------------- R17
def r17_prodleva(vazba, konf):
    """vazba: {akce, usneseni, datum_usneseni, smlouva, datum_smlouvy, *_zdroj}
    Smlouva podepsaná PŘED usnesením → stredni; prodleva nad limitem → nizka."""
    k = konf.get("prodleva_usneseni_smlouva", {"limit_dni": 90})
    du, ds = datum(vazba.get("datum_usneseni")), datum(vazba.get("datum_smlouvy"))
    if not du or not ds:
        return []
    dni = (ds - du).days
    odk = [vazba.get("usneseni"), vazba.get("smlouva"), vazba.get("datum_usneseni_zdroj"), vazba.get("datum_smlouvy_zdroj")]
    if dni < 0:
        return [{"kod": "R17-smlouva-pred-usnesenim", "zavaznost": "stredni",
                 "popis": f"{vazba['akce']}: smlouva podepsána {ds.isoformat()}, tj. {-dni} dní PŘED usnesením {vazba['usneseni']} "
                          f"({du.isoformat()}) – ověřit, zda šlo o jiné znění, nebo o dodatečné schválení.",
                 "castka_Kc": None, "odkazy": [o for o in odk if o]}]
    if dni > k["limit_dni"]:
        return [{"kod": "R17-prodleva-usneseni-smlouva", "zavaznost": "nizka",
                 "popis": f"{vazba['akce']}: smlouva podepsána {dni} dní po usnesení {vazba['usneseni']} "
                          f"({du.isoformat()} → {ds.isoformat()}) – ověřit důvod prodlevy a shodu podmínek se schváleným zněním.",
                 "castka_Kc": None, "odkazy": [o for o in odk if o]}]
    return []


# ---------------------------------------------------------------- R18
def r18_vyvoj_ceny(retezec, konf):
    """retezec: {akce, smlouvy:[{datum, castka, zaklad, ref, castka_zdroj}]} – první vs. poslední smlouva téže akce (stejný základ DPH)."""
    k = konf.get("vyvoj_ceny_retezce", {"narust_stredni": 0.5, "narust_vysoka": 1.0})
    ss = sorted((s for s in retezec.get("smlouvy", []) if datum(s.get("datum")) and s.get("castka")), key=lambda s: datum(s["datum"]))
    if len(ss) < 2:
        return []
    a, b = ss[0], ss[-1]
    if a["zaklad"] != b["zaklad"]:
        return []
    narust = (b["castka"] - a["castka"]) / a["castka"]
    if narust <= k["narust_stredni"]:
        return []
    zav = "vysoka" if narust > k["narust_vysoka"] else "stredni"
    return [{"kod": "R18-narust-ceny-v-retezci-smluv", "zavaznost": zav,
             "popis": f"{retezec['akce']}: cena první smlouvy {fmt(a['castka'])} Kč ({a['datum']}) → poslední {fmt(b['castka'])} Kč "
                      f"({b['datum']}), {a['zaklad']}, nárůst {narust*100:.0f} % ({len(ss)} {'smlouvy' if len(ss) < 5 else 'smluv'}) – ověřit změnu rozsahu a zdůvodnění.",
             "castka_Kc": b["castka"] - a["castka"],
             "odkazy": [x for s in (a, b) for x in (s.get("ref"), s.get("castka_zdroj")) if x]}]


# ---------------------------------------------------------------- běh nad repem
def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def vsechna_pravidla(konf=None):
    konf = konf or nacti_konfiguraci()
    flags = []
    vz = _load("data/zakazky/verejne_zakazky.json") or {}
    for s in r13_ze_zakazek(vz):
        flags += r13_dodatky(s, konf)
    zr = _load("data/zakazky/verejne_zakazky_zrusene.json") or {}
    for z in zr.get("zakazky", []):
        flags += r14_pod_limitem({"nazev": z["nazev"], "druh": None, "predp_hodnota": z.get("predp_hodnota"),
                                  "datum": z.get("uverejneno"), "odkazy": [zr.get("zdroj")]}, konf)
    for z in vz.get("zakazky", []):
        druh_txt = (z.get("druh") or "").lower()
        druh = "stavebni_prace" if "stavebn" in druh_txt else None
        flags += r14_pod_limitem({"nazev": z["nazev"], "druh": druh, "predp_hodnota": z.get("predp_hodnota"),
                                  "datum": z.get("uverejneno"), "odkazy": [z.get("url")]}, konf)
    reg = _load("data/smlouvy/oprava_hodnot_registru_2026-10-23.json")
    verze = reg.get("verze") if isinstance(reg, dict) else reg
    smlouvy = [{"id": v["version_id"], "predmet": v.get("predmet"), "datum": v.get("datum_uzavreni"),
                "castka": v.get("s_dph")} for v in (verze or []) if isinstance(v, dict) and v.get("version_id")]
    flags += r15_zruseni_prodlouzeni(zr.get("opakovana_zruseni", []), smlouvy, konf)
    cb = _load("data/analyzy/cenove_body.json") or {}
    for a in cb.get("akce", []):
        flags += r16_cenovy_rozdil(a, konf)
    vr = _load("data/analyzy/vazby_rozhodnuti.json") or {}
    for v in vr.get("usneseni_smlouva", []):
        flags += r17_prodleva(v, konf)
    for r in vr.get("retezce_smluv", []):
        flags += r18_vyvoj_ceny(r, konf)
    return flags


if __name__ == "__main__":
    import collections
    f = vsechna_pravidla()
    print(len(f), dict(collections.Counter(x["kod"] for x in f)))
    for x in f:
        print("-", x["kod"], x["zavaznost"], x["popis"][:160])
