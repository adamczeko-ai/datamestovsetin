"""Validace datových souborů proti JSON Schema v data/schema/. Použití: python3 scripts/validate_schemas.py

JSON soubory se validují celé; data/*.jsonl řádek po řádku proti data/schema/jsonl-<nazev>.schema.json
a navíc se kontroluje, že sha256 řádku odpovídá obsahu a že se dvojice (id, sha256) neopakuje.
"""
import json,glob,os,sys
from jsonschema import Draft202012Validator
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from integrace.sber.store import otisk
M={"rozpoctove-opatreni":sorted(glob.glob("data/rozpocet/20??/rozpoctova_opatreni_20??.json")),"kauza":sorted(glob.glob("data/kauzy/K-*.json")),"subjekty":["data/entity/subjekty.json"],"verejne-zakazky":["data/zakazky/verejne_zakazky.json"],"signaly":["data/analyzy/signaly.json"],"signal-stavy":["data/analyzy/signaly_stavy.json"],"nesoulady-llm":sorted(glob.glob("data/analyzy/llm/nesoulady_*.json")),"ares-overeni":["data/entity/ares_overeni.json"],"parovani-ico":["data/smlouvy/parovani_ico.json"],"manifest":[f for f in ["data/manifest.json"] if os.path.exists(f)]}
bad=0
for sch,files in M.items():
    v=Draft202012Validator(json.load(open(f"data/schema/{sch}.schema.json")))
    for f in files:
        errs=list(v.iter_errors(json.load(open(f))))
        print(("OK  " if not errs else f"ERR {len(errs)} ")+f)
        for e in errs[:3]: print("    ",list(e.absolute_path)[:6],e.message[:120])
        bad+=len(errs)
for f in sorted(glob.glob("data/*.jsonl")):
    sch=f"data/schema/jsonl-{os.path.basename(f)[:-6].replace('_','-')}.schema.json"
    if not os.path.exists(sch):
        print(f"ERR chybí schéma {sch} pro {f}"); bad+=1; continue
    v=Draft202012Validator(json.load(open(sch)))
    errs,seen,n=[],set(),0
    for i,line in enumerate(open(f,encoding="utf-8"),1):
        if not line.strip(): continue
        n+=1; r=json.loads(line)
        errs+=[(i,list(e.absolute_path)[:4],e.message[:120]) for e in v.iter_errors(r)]
        if r.get("sha256")!=otisk(r): errs.append((i,["sha256"],"neodpovídá obsahu záznamu"))
        k=(r.get("id"),r.get("sha256"))
        if k in seen: errs.append((i,["id","sha256"],"duplicitní dvojice id + sha256"))
        seen.add(k)
    print(("OK  " if not errs else f"ERR {len(errs)} ")+f"{f} ({n} řádků)")
    for e in errs[:3]: print("    ",*e)
    bad+=len(errs)
sys.exit(1 if bad else 0)
