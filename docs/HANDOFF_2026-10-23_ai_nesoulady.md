# HANDOFF 2026-10-23: vrstva „nesoulady k vysvětlení“ (varianta A)

Větev `feature/ai-nesoulady` → PR do `main`. Práce proběhla v cloudovém klonu repa. Server (prod ani dev) nebyl dotčen.

## Provedené změny
| Soubor | Co |
|---|---|
| `data/schema/signaly.schema.json` | signaly@2: stabilní ID, stav, důkazní řetězec (typ, ref, URL, strana, citace, sha256, stazeno, overeno), `puvodni` |
| `data/schema/signal-stavy.schema.json` | ruční stavy ověření včetně `druhe_overeni` |
| `data/schema/nesoulady-llm.schema.json` | výstup LLM vrstvy |
| `data/analyzy/signaly.json` | 121 signálů = 100 z red_flags@1 + 6 z R13–R16 + 15 anomálií A-* |
| `data/analyzy/signaly_stavy.json` | 3 stavy migrované z textu „POTVRZENO“ (A-2023-01, A-2024-01, A-2025-01) |
| `data/analyzy/pravidla_konfigurace.json` | limity VZMR a § 222 se zdroji a příznakem ověření |
| `data/analyzy/cenove_body.json` | vstup R16; každá hodnota má pointer do repa, ověřeno testem |
| `scripts/pravidla_nesoulady.py` | R13 kumulace dodatků, R14 těsně pod limitem / dělení, R15 zrušení VZ → prodloužení, R16 cenový rozdíl |
| `scripts/signaly_v2.py` | generátor signaly@2, připojení stavů, osiřelé stavy |
| `scripts/kontrola_nesouladu_llm.py` | doslovné ověření citací, min. 2 zdroje, zakázané výrazy, cesty jen v repu |
| `scripts/validate_schemas.py` | + 3 nová schémata |
| `ai/PROMPT_nesoulady.md`, `ai/ULOHA_planovana.md` | prompt LLM vrstvy a postup plánované úlohy |
| `ai/test/*` | slepý test K-002/K-003 |
| `tests/test_pravidla_nesoulady.py`, `tests/test_signaly_v2.py`, `tests/test_kontrola_nesouladu_llm.py` | 31 nových testů |
| `docs/AI_VARIANTA_A.md` | architektura A/B, nastavení, rizika, náklady, rollback |

`red_flags.json` ani `index.html` se nemění. Prohlížeč dál čte red_flags@1.

## Testy (skutečně spuštěno 2026-10-23)
- `python3 -m unittest discover -s tests`: **37/37 OK** (31 nových + 6 stávajících).
- `python3 scripts/validate_schemas.py`: všech 11 souborů OK.
- Slepý test LLM: jádro **5/7**, 0 falešných, 0 zahozených citací. Podrobně v `ai/test/vyhodnoceni_2026-10-23.md`.

## Nové signály R13–R16 nad aktuálními daty
- R14 ×3: Senior taxi 2020/2022 – předp. hodnota 1,8 mil. = 90 % tehdejšího limitu 2 mil. Druh plnění není v datech uveden, limit pro služby je předpoklad.
- R15 ×1: Senior taxi – zrušeno 6×, poté Dodatek č. 2 (31. 7. 2026).
- R16 ×2: K-002 návrh 34,0 vs. schváleno 33,15 mil.; K-003 rozpočet 23 mil. vs. SoD TM Stav 23,57 mil. s DPH (předpoklad: rozpočet vč. DPH).
- R13 ×0: Přednádražní prostor I.B má dodatky 9,02 mil. = 5,3 % (pod pásmem). Základ DPH dodatků v datech není určen.

## Otevřená rizika
- Limit VZMR před 3. 4. 2025 (2/6 mil.) je v konfiguraci označen `overeno: false`. Hranice pro nadlimitní VZ v § 222 odst. 4 se nekontroluje.
- Kontrola neumí spolehlivě detekovat jména fyzických osob v popisu, zbývá lidská revize.
- LLM zatím cituje vytěžená data, ne originály. Chybí `raw/texty/` ze serveru.
- Izolace slepého testu byla instrukční. Test proběhl jednou nad dvěma kauzami.

## Doporučený další krok
1. Vlastník: zapnout ochranu `main` (vyžadovat PR), projít a mergnout PR.
2. Schválit změnu na dev serveru: ingest ukládá text po stranách + sha256 (`raw/texty/`).
3. Doplnit do promptu kontrolní seznam pro minutá jádra (prodleva usnesení → smlouva, první vs. poslední cena akce).
