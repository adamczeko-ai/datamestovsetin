"""Validace datových souborů proti JSON Schema v data/schema/. Použití: python3 scripts/validate_schemas.py"""
import json,glob,sys
from jsonschema import Draft202012Validator
M={"rozpoctove-opatreni":sorted(glob.glob("data/rozpocet/20??/rozpoctova_opatreni_20??.json")),"kauza":sorted(glob.glob("data/kauzy/K-*.json")),"subjekty":["data/entity/subjekty.json"],"verejne-zakazky":["data/zakazky/verejne_zakazky.json"],"signaly":["data/analyzy/signaly.json"],"signal-stavy":["data/analyzy/signaly_stavy.json"],"nesoulady-llm":sorted(glob.glob("data/analyzy/llm/nesoulady_*.json")),"ares-overeni":["data/entity/ares_overeni.json"],"parovani-ico":["data/smlouvy/parovani_ico.json"]}
bad=0
for sch,files in M.items():
    v=Draft202012Validator(json.load(open(f"data/schema/{sch}.schema.json")))
    for f in files:
        errs=list(v.iter_errors(json.load(open(f))))
        print(("OK  " if not errs else f"ERR {len(errs)} ")+f)
        for e in errs[:3]: print("    ",list(e.absolute_path)[:6],e.message[:120])
        bad+=len(errs)
sys.exit(1 if bad else 0)
