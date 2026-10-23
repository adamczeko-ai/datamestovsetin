"""Kontrola RO 2024 proti řádkům „Celkem PŘÍJMY/VÝDAJE/FINANCOVÁNÍ“ z PDF (vytěženo 2026-10-23)."""
import collections, json, sys
d = json.load(open("data/rozpocet/2024/rozpoctova_opatreni_2024.json", encoding="utf-8"))
CEL = {1:(-73200,-73200,0),2:(0,2665000,2665000),3:(3793300,3793300,0),4:(3210739.03,3210739.03,0),5:(107000,107000,0),
 6:(60000,10745223.82,10685223.82),7:(12961799.14,12961799.14,0),8:(1036700,1036700,0),9:(5283310.39,5043075.42,-240234.97),
 10:(988000,6012000,5024000),11:(95000,95000,0),12:(612208,612208,0),13:(29128,29128,0),14:(1220000,1220000,0),
 15:(467250,9208212,8740962),16:(374208,374208,0),17:(175848,175848,0),18:(30196210.12,946856,-29249354.12),
 19:(18583,18583,0),20:(204500,204500,0),21:(-114872,-157878.03,-43006.03),22:(-33146488.38,23833,33176921.38)}
bad = 0
for o in d["opatreni"]:
    s = tuple(round(sum(r["zmena"] for r in o["radky"] if r["typ"] == t), 2) for t in "PVF")
    ar = [r for r in o["radky"] if round(r["pred"] + r["zmena"], 2) != round(r["po"], 2)]
    if s != tuple(round(x, 2) for x in CEL[o["cislo"]]) or ar:
        bad += 1; print("RO", o["cislo"], s, CEL[o["cislo"]], len(ar))
rows = sum(len(o["radky"]) for o in d["opatreni"])
print("RO", len(d["opatreni"]), "rows", rows, "bad", bad)
sys.exit(1 if bad or rows != 406 else 0)
