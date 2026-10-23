"""Export signálů, které smí být ZVEŘEJNĚNY na nasvsetin.cz (rozhodnutí vlastníka 2026-10-23: jen ověřené člověkem).

Do exportu projde signál jen když:
  - jeho stav v data/analyzy/signaly_stavy.json je 'potvrzeno' nebo 'vysvetleno', A ZÁROVEŇ
  - má vyplněné 'druhe_overeni' (princip čtyř očí).
Nikdy se neexportují: stavy 'novy', 'overuje_se', 'zamitnuto', výstupy LLM (data/analyzy/llm/*),
pole 'puvodni' ani interní poznámky.

Vstup:  data/analyzy/signaly.json (generuje scripts/signaly_v2.py)
Výstup: argument 1, výchozí data/analyzy/verejne_signaly.json
Použití: python3 scripts/export_verejne_signaly.py [vystup.json]
"""
import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

ZVEREJNITELNE = {"potvrzeno", "vysvetleno"}
UPOZORNENI = ("Zveřejněny jsou jen nesoulady ověřené dvěma lidmi. 'Potvrzeno' znamená, že rozdíl v datech potvrdil "
              "nezávislý zdroj a vysvětlení zatím chybí – nejde o zjištění pochybení ani obvinění. "
              "'Vysvětleno' znamená, že rozdíl má doložené vysvětlení.")


def vyber(signaly):
    out = []
    for s in signaly:
        st = s.get("stav_detail") or {}
        if s.get("stav") in ZVEREJNITELNE and st.get("druhe_overeni") and s.get("zdroj_signalu") != "llm":
            out.append({"id": s["id"], "kod": s["kod"], "stav": s["stav"], "popis": s["popis"],
                        "castka_Kc": s.get("castka_Kc"), "zavaznost": s["zavaznost"],
                        "oduvodneni": st.get("oduvodneni"), "overeno_dne": st.get("datum"),
                        "dukazy": [{k: d.get(k) for k in ("typ", "ref", "url", "strana")} for d in s.get("dukazy", [])]})
    return out


def main(argv):
    vystup = argv[1] if len(argv) > 1 else "data/analyzy/verejne_signaly.json"
    with open("data/analyzy/signaly.json", encoding="utf-8") as f:
        sig = json.load(f)
    vyb = vyber(sig["signaly"])
    out = {"schema": "vsetin-osint/verejne-signaly@1",
           "vygenerovano": dt.datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds"),
           "upozorneni": UPOZORNENI, "pocet": len(vyb), "signaly": vyb}
    with open(vystup, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"zveřejnitelných signálů: {len(vyb)} → {vystup}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
