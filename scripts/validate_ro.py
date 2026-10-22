"""Validace přepsaných řádků RO proti kontrolním součtům z parseru v prohlížeči.
Použití: python3 scripts/validate_ro.py 2024"""
import json,sys,glob,collections
rok=sys.argv[1]; exp=json.load(open(f"scripts/kontrola_{rok}.json"))
rows=[]
for p in sorted(glob.glob(f"raw/ro{rok}_radky_part*.tsv")):
    for l in open(p,encoding="utf-8").read().rstrip("\n").split("\n"):
        if l.startswith("ro\t"): continue
        c=l.split("\t"); assert len(c)==10,l
        rows.append(dict(ro=int(c[0]),typ=c[1],odpa=c[2] or None,pol=c[3],org=c[4] or None,orj=c[5] or None,pred=float(c[6]),zmena=float(c[7]),po=float(c[8]),popis=c[9]))
bad=0
for ro,(n,P,V,F) in exp.items():
    rr=[r for r in rows if r["ro"]==int(ro)]
    s={t:round(sum(r["zmena"] for r in rr if r["typ"]==t),2) for t in "PVF"}
    ar=[r for r in rr if round(r["pred"]+r["zmena"],2)!=round(r["po"],2)]
    if len(rr)!=n or (s["P"],s["V"],s["F"])!=(P,V,F) or ar: bad+=1;print("RO",ro,len(rr),n,s,(P,V,F),ar[:2])
print("rows",len(rows),"bad",bad)
ch=collections.defaultdict(list)
for r in rows:
    if r["odpa"]=="6409" or r["pol"].startswith("81"): ch[(r["odpa"],r["pol"],r["org"],r["orj"])].append(r)
for k,v in ch.items():
    for a,b in zip(v,v[1:]):
        if round(a["po"],2)!=round(b["pred"],2): print("chain",k,"RO",a["ro"],a["po"],"-> RO",b["ro"],b["pred"],"diff",round(b["pred"]-a["po"],2))
json.dump(rows,open(f"/home/claude/rows{rok}.json","w"),ensure_ascii=False)
