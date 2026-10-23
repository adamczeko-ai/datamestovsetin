# Plánovaná úloha: nesoulady k vysvětlení (varianta A)

Verze: `uloha@1` (2026-10-23). Úlohu spouští plánovač Claude každý pracovní den. Každý běh začíná v čisté relaci bez paměti, takže vše potřebné je v tomto souboru a v `ai/PROMPT_nesoulady.md`.

## Hranice (závazné)

- Pracuje se jen v klonu repa `adamczeko-ai/datamestovsetin` v cloudovém prostředí. Server (`/opt/vsetin-osint`, `/home/administrator/vsetin-osint-dev`) se nikdy neoslovuje.
- Výstup je výhradně **PR do `main`** z větve `ai/nesoulady-<YYYY-MM-DD>`. Nikdy push do `main`, nikdy merge.
- Nezapisovat do `data/analyzy/signaly_stavy.json`, do zdrojových dat (`data/rozpocet`, `data/kauzy`, `data/smlouvy`, `data/zakazky`, …) ani do `raw/`.
- Smí se měnit jen:
  - `data/analyzy/red_flags.json` a `akce_timeline.json` (regenerace skriptem),
  - `data/analyzy/signaly.json`,
  - nový soubor `data/analyzy/llm/nesoulady_<YYYY-MM-DD>.json`.
- Shell z cloudu nedosáhne na mestovsetin.cz, hlidacstatu.cz ani monitor.statnipokladna.cz. Nová data dodává server do repa a úloha je jen analyzuje. Nestahovat obcházením (curl přes jiné služby, zrcadla).
- Časy uvádět v Europe/Prague.

## Postup

1. Naklonovat repo (mělký klon) a přepnout na `main`. Pokud chybí `scripts/signaly_v2.py` nebo `ai/PROMPT_nesoulady.md`, skončit se zprávou „čeká na merge PR s vrstvou nesouladů“.
2. Zjistit **změny od posledního běhu**.
   - Poslední běh = nejnovější soubor `data/analyzy/llm/nesoulady_*.json` (datum v názvu). Pokud žádný není, berou se změny za posledních 7 dní.
   - Seznam souborů: `git log --since=<datum> --name-only --pretty=format: -- data raw | sort -u`. Vyloučit `data/analyzy/`.
3. Deterministická vrstva, vše z kořene repa:
   ```
   python3 scripts/analyzy.py
   python3 scripts/signaly_v2.py
   python3 scripts/validate_schemas.py
   python3 -m unittest discover -s tests
   ```
   Pokud selže validace nebo testy, **nevytvářet PR s nesoulady**. Místo toho vytvořit PR/issue jen s popisem chyby, případně jen zprávu, pokud PR nejde.
4. LLM vrstva: podle `ai/PROMPT_nesoulady.md` projít změněné soubory z kroku 2 a s nimi související kauzy a akce.
   - Kandidáta uložit mimo repo (např. `/tmp/kandidat.json`).
   - Potom spustit `python3 scripts/kontrola_nesouladu_llm.py /tmp/kandidat.json data/analyzy/llm/nesoulady_<YYYY-MM-DD>.json`.
   - Pokud se nic nezměnilo a v signálech není nic nového, PR nevytvářet. Stačí krátká zpráva „beze změn“.
5. Commit a PR:
   - Commit s popisem, branch `ai/nesoulady-<YYYY-MM-DD>`, push, PR do `main`.
   - Popis PR obsahuje:
     - souhrn: počty nových a zaniklých signálů podle kódu, osiřelé stavy,
     - každý nesoulad jednou větou s ID a otázkou k vysvětlení,
     - co kontrola zahodila a proč,
     - výsledky testů (skutečně spuštěné),
     - **návrhy změn stavů**, pouze jako text pro vlastníka.
   - Na začátek popisu PR dát upozornění: „Nesoulady nejsou zjištěním pochybení. Před předáním KV/vedení ověří člověk (princip čtyř očí).“
6. Závěrečná zpráva (krátce): odkaz na PR, počty, co vyžaduje pozornost vlastníka.
