import json,collections,sys
rows=[]
for p in (1,2,3):
    lines=open(f"raw/ro2026_radky_part{p}.tsv",encoding="utf-8").read().rstrip("\n").split("\n")
    if p==1: lines=lines[1:]
    for l in lines:
        c=l.split("\t"); assert len(c)==10,(p,l)
        rows.append(dict(ro=int(c[0]),typ=c[1],odpa=c[2] or None,pol=c[3],org=c[4] or None,orj=c[5] or None,pred=float(c[6]),zmena=float(c[7]),po=float(c[8]),popis=c[9]))
exp_n={1:2,2:4,3:14,4:15,5:38,6:11,7:28,8:29,9:30,10:17,11:31,12:23,13:2,14:65,15:15,16:14,17:16,18:24}
exp={1:(0,0,0),2:(0,3443920,3443920),3:(17211652.89,17211652.89,0),4:(188905,192663.31,3758.31),5:(11940778.37,12217903.4,277125.03),6:(1326727.89,197575,-1129152.89),7:(1111000,28802200,27691200),8:(5500,5500,0),9:(4348283.45,4908411.06,560127.61),10:(1846896.55,1846896.55,0),11:(1125668,1125668,0),12:(0,114877314.88,114877314.88),13:(0,0,0),14:(4855946.08,490598,-4365348.08),15:(156953,156953,0),16:(382500,382500,0),17:(163463,2963463,2800000),18:(1567135,1567135,0)}
bad=0
for ro in range(1,19):
    rr=[r for r in rows if r["ro"]==ro]
    s={t:round(sum(r["zmena"] for r in rr if r["typ"]==t),2) for t in "PVF"}
    ok=len(rr)==exp_n[ro] and (s["P"],s["V"],s["F"])==exp[ro]
    arith=[r for r in rr if round(r["pred"]+r["zmena"],2)!=round(r["po"],2)]
    if not ok or arith: bad+=1; print("RO",ro,len(rr),exp_n[ro],s,exp[ro],arith[:2])
print("rows",len(rows),"bad",bad)
chain=collections.defaultdict(list)
for r in rows:
    if r["odpa"]=="6409" or r["pol"].startswith("81"): chain[(r["odpa"],r["pol"],r["org"])].append(r)
for k,v in chain.items():
    for a,b in zip(v,v[1:]):
        if round(a["po"],2)!=round(b["pred"],2): print("chain break",k,a["ro"],a["po"],b["ro"],b["pred"])
json.dump(rows,open("/home/claude/rows.json","w"),ensure_ascii=False)
