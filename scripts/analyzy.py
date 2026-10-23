"""Analytické výstupy nad RO 2024–2026.
- akce_timeline.json: sledování investičních/opravných akcí podle ORG kódu napříč RO a roky
  (obdoba 'bill tracking' z Councilmatic – každá akce má časovou osu rozhodnutí a peněz)
- red_flags.json: pravidlové signály k ověření (ne obvinění)
Použití: python3 scripts/analyzy.py"""
import json,collections,re
ROKY=(2023,2024,2025,2026)
ops=[]
for y in ROKY:
    d=json.load(open(f"data/rozpocet/{y}/rozpoctova_opatreni_{y}.json"))
    for o in d["opatreni"]:
        for r in o["radky"]:
            ops.append(dict(r,rok=y,ro=o["cislo"],ro_id=o["id"],organ=o["organ"],datum=o["datum"],usneseni=o["usneseni"]))
# --- 1) akce timeline: ORG kódy ve tvaru 0000xxxx (investiční akce OSMISR) a 2xxxxxxx (účelové akce/příspěvky)
def akce_key(r):
    org=(r["org"] or "").split(" ")[0]
    if r["odpa"]=="6409" or r["typ"]!="V": return None
    if re.fullmatch(r"0000\d{4}",org): return org
    return None
ak=collections.defaultdict(list)
for r in ops:
    k=akce_key(r)
    if k: ak[k].append(r)
timeline=[]
for k,rr in ak.items():
    rr.sort(key=lambda r:(r["rok"],r["ro"]))
    BAD=r"(Úspora|Změna rozpočtového|Nerealizov|přesun|Uvolnění|- snížení|snížení$|odloženo)"
    kand=[re.sub(r"\s*-\s*(snížení|navýšení)$","",r["popis"]) for r in rr if r["popis"] and not re.search(BAD,r["popis"],re.I)]
    nazev=max(kand,key=len) if kand else re.sub(r"^(Uvolnění rezervy\s*-\s*)","",rr[0]["popis"])
    timeline.append({"org":k,"nazev":nazev,
      "pocet_zmen":len(rr),"roky":sorted({r["rok"] for r in rr}),
      "soucet_zmen_Kc":round(sum(r["zmena"] for r in rr),2),
      "navyseni_Kc":round(sum(r["zmena"] for r in rr if r["zmena"]>0),2),
      "snizeni_Kc":round(sum(r["zmena"] for r in rr if r["zmena"]<0),2),
      "posledni_stav":{"rok":rr[-1]["rok"],"po":rr[-1]["po"]},
      "udalosti":[{"rok":r["rok"],"ro":r["ro_id"],"organ":r["organ"],"datum":r["datum"],"usneseni":r["usneseni"],"pol":r["pol"],"pred":r["pred"],"zmena":r["zmena"],"po":r["po"],"popis":r["popis"]} for r in rr]})
timeline.sort(key=lambda a:-abs(a["navyseni_Kc"]))
json.dump({"schema":"vsetin-osint/akce-timeline@1","pocet_akci":len(timeline),"akce":timeline},open("data/analyzy/akce_timeline.json","w"),ensure_ascii=False,indent=1)
# --- 2) red flags
flags=[]
def add(kod,zav,popis,refs,castka=None): flags.append({"kod":kod,"zavaznost":zav,"popis":popis,"castka_Kc":castka,"odkazy":refs})
# R1: velké jednorázové navýšení akce (>= 5 mil. nebo >= +100 % při pred>=1 mil.)
for r in ops:
    if r["typ"]=="V" and r["odpa"]!="6409" and r["zmena"]>0:
        if r["zmena"]>=5e6 or (r["pred"]>=1e6 and r["zmena"]>=r["pred"]):
            add("R1-velke-navyseni","stredni" if r["zmena"]<2e7 else "vysoka",f"{r['popis']}: {r['pred']:,.0f} → {r['po']:,.0f} Kč".replace(","," "),[r["ro_id"],r["usneseni"]],r["zmena"])
# R2: opakované navyšování téže akce (>=3 navýšení)
for a in timeline:
    n=sum(1 for u in a["udalosti"] if u["zmena"]>0)
    if n>=3: add("R2-opakovane-navysovani","stredni",f"{a['nazev']} (ORG {a['org']}): {n}× navýšeno, celkem +{a['navyseni_Kc']:,.0f} Kč".replace(","," "),[u["ro"] for u in a["udalosti"]],a["navyseni_Kc"])
# R3: rozhodnutí Rady o velké částce mimo ZM (RM, kapitálové výdaje >= 2 mil.)
for r in ops:
    if r["organ"]=="RM" and r["typ"]=="V" and r["pol"].startswith("6") and r["odpa"]!="6409" and r["zmena"]>=2e6:
        add("R3-RM-velka-investice","nizka",f"RM rozhodla o +{r['zmena']:,.0f} Kč: {r['popis']}".replace(","," "),[r["ro_id"],r["usneseni"]],r["zmena"])
# R4: výkup/nabytí nemovitostí (pol. 6130) – vždy k ověření ceny a posudku
for r in ops:
    if r["pol"]=="6130" and r["zmena"]>0:
        add("R4-nakup-nemovitosti","stredni",f"{r['popis']}: +{r['zmena']:,.0f} Kč".replace(","," "),[r["ro_id"],r["usneseni"]],r["zmena"])
# R5: dotace/příspěvky spolkům a firmám (pol. 5222, 6322, 5213, 5221, 6313) >= 300 tis.
for r in ops:
    if r["typ"]=="V" and r["pol"] in ("5222","6322","5213","6313","5221","6323") and r["zmena"]>=3e5:
        add("R5-dotace-subjektu","nizka",f"{r['popis']}: +{r['zmena']:,.0f} Kč".replace(","," "),[r["ro_id"],r["usneseni"]],r["zmena"])
# R6: náklady soudních sporů / satisfakce (pol. 5192)
for r in ops:
    if r["pol"]=="5192" and r["zmena"]>0:
        add("R6-soudni-spory","vysoka",f"{r['popis']}: +{r['zmena']:,.0f} Kč".replace(","," "),[r["ro_id"],r["usneseni"]],r["zmena"])
# R7: dofinancování ztrát / mimořádné příspěvky PO
for r in ops:
    if re.search(r"dofinanc|ztrát|minulých let",r["popis"] or "",re.I) and r["zmena"]>=1e6:
        add("R7-dofinancovani-PO","vysoka",f"{r['popis']}: +{r['zmena']:,.0f} Kč".replace(","," "),[r["ro_id"],r["usneseni"]],r["zmena"])
# R8/R9: veřejné zakázky
try:
    vz=json.load(open("data/zakazky/verejne_zakazky.json"))
    for z in vz["zakazky"]:
        sm=z.get("smlouva") or {}
        if z.get("pomer_cena_predp") and z["pomer_cena_predp"]>=0.98:
            add("R9-cena-u-predpokladane-hodnoty","stredni",f"{z['nazev']}: cena {z['pomer_cena_predp']*100:.3f} % předpokládané hodnoty",[z.get("url"),sm.get("url")],sm.get("bez_DPH"))
        n=len(z.get("ucastnici",[]))
        if n and n<=2: add("R8-malo-nabidek","nizka",f"{z['nazev']}: jen {n} nabídky",[z.get("url")],sm.get("bez_DPH"))
        if "vyvoj_rozpoctu" in z: add("R10-narust-ceny-proti-rozpoctu","vysoka",z.get("signal",""),[sm.get("url")],sm.get("bez_DPH"))
        if z.get("stav","").startswith("zakázka neukončena"): add("R11-zakazka-dlouho-neukoncena","stredni",f"{z['nazev']}: {z['stav']}",[z.get("url")],z.get("predp_hodnota"))
except FileNotFoundError: pass
try:
    zr=json.load(open("data/zakazky/verejne_zakazky_zrusene.json"))
    for o in zr["opakovana_zruseni"]:
        if o["pocet_zruseni"]>=3: add("R12-opakovane-zruseni-VZ","nizka",f"{o['zakazka']}: zrušeno {o['pocet_zruseni']}×",[zr["zdroj"]],max(o["predp_hodnoty"]))
except FileNotFoundError: pass
order={"vysoka":0,"stredni":1,"nizka":2}
flags.sort(key=lambda f:(order[f["zavaznost"]],-(f["castka_Kc"] or 0)))
summ=collections.Counter(f["kod"] for f in flags)
json.dump({"schema":"vsetin-osint/red-flags@1","upozorneni":"Signály jsou pravidlové a slouží k prioritizaci ověřování. Nejsou zjištěním pochybení.","souhrn":summ,"signaly":flags},open("data/analyzy/red_flags.json","w"),ensure_ascii=False,indent=1)
print("akce",len(timeline),"flags",len(flags),dict(summ))
for a in timeline[:8]: print(a["org"],a["navyseni_Kc"],a["pocet_zmen"],a["roky"],a["nazev"][:60])
