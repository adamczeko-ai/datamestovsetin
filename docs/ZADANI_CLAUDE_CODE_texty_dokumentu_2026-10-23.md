# Zadání pro Claude Code (dev server): texty dokumentů po stranách + SHA-256

*2026-10-23. Schváleno vlastníkem: úprava stahování na **dev** serveru. Produkce se nemění.*

## Cíl
Stáhnout dokumenty města, na které odkazují data repa (158 URL v `data/integrace/dokumenty_seznam.txt`). Text každého uložit po stranách do `raw/texty/<sha256>/p<N>.txt` s `meta.json` a celé to dostat do repa přes PR. Z těchto textů pak čte plánovaná úloha „nesoulady“, která neumí stahovat z mestovsetin.cz.

## Hranice (závazné)
- Pracuj jen v `/home/administrator/vsetin-osint-dev` a v klonu repa `adamczeko-ai/datamestovsetin`.
- **Zakázáno bez dalšího schválení:**
  - cokoli v `/opt/vsetin-osint`, produkční DB, Docker restart, cron, deploy, síťová konfigurace,
  - `apt install` (server sdílí prod i dev),
  - OCR.
- Do `main` nepushuj (je chráněný). Výstup dej jako PR.
- Nevymýšlej výsledky. Do reportu dej skutečné výstupy příkazů. Časy uváděj v Europe/Prague.

## Postup

### 1. Diagnostika (jen čtení)
```bash
python3 --version                      # potřeba >= 3.10
which pdftotext && pdftotext -v        # poppler-utils
python3 -c "import pypdf; print(pypdf.__version__)"
df -h /home/administrator
find /home/administrator -maxdepth 3 -name datamestovsetin -type d   # existující klon?
```
- Když chybí `pdftotext` i `pypdf`, **neinstaluj systémově**. Vytvoř venv v dev složce: `python3 -m venv /home/administrator/vsetin-osint-dev/.venv-integrace` a v něm `pip install pypdf`. Venv je izolovaný a nesahá na systém.

### 2. Klon a testy
```bash
cd <klon> && git fetch origin && git checkout main && git pull --ff-only
python3 -m unittest tests.test_dokumenty tests.test_integrace -v
```
Pokud testy selžou, zastav a nahlas chybu.

### 3. Běh v dev
```bash
cd <klon>
export INTEGRACE_DB=/home/administrator/vsetin-osint-dev/data/integrace.db
export INTEGRACE_CACHE=/home/administrator/vsetin-osint-dev/data/integrace_cache
python3 -m integrace dokumenty --seznam data/integrace/dokumenty_seznam.txt --texty raw/texty
python3 -m integrace dokumenty --seznam data/integrace/dokumenty_seznam.txt --texty raw/texty   # 2. běh = idempotence
```
- Rychlost je 1 dotaz za 2 s (`min_interval_s.dokumenty`), celkem zhruba 6 minut.
- `integrace_cache/` a `*.db` jsou v `.gitignore`. Originály PDF se do repa neukládají, jen texty.

### 4. Akceptace
| Kontrola | Očekáváno |
|---|---|
| 1. běh | `dokumentu` ≥ 158 (balíčky ZIP se rozpadnou na členy), `chyby` = jen nedostupné URL, každá se jménem |
| 2. běh | `nove_texty` = 0, v `sync_ledger` stav `not_modified` / `unchanged_hash` |
| `raw/texty/*/meta.json` | každý má `sha256` = název složky, `pocet_stran` ≥ 1 |
| Balíček ZM 18 (`id_dokumenty=562068`) | mezi členy je `navrh-usneseni_108136.html` nebo `…108129.html`; text obsahuje prázdnou kupní cenu (`…,- Kč`) – ověřuje K-002 |
| RO 4/2025 (`id_dokumenty=564065`) | text obsahuje `10 150 000` a `33 152 000` |
| `bez_textove_vrstvy` | seznam skenů (např. zpráva auditora ZÚ 2025), jen nahlásit, neOCRovat |
| velikost `raw/texty` | `du -sh raw/texty`, nahlásit (odhad jednotky až desítky MB) |

### 5. Předání
```bash
git checkout -b data/texty-dokumentu-<YYYY-MM-DD>
git add raw/texty && git commit -m "data: texty dokumentů města po stranách (dokumenty@texty@1)"
git push -u origin data/texty-dokumentu-<YYYY-MM-DD>
# PR do main (REST nebo web); popis = výsledky akceptace
```
Report do hlavního koordinačního chatu musí obsahovat: provedené kroky, výstupy obou běhů, akceptační tabulku s reálnými hodnotami, seznam chyb a skenů, odkaz na PR.

## Rollback
- Zavřít PR, případně `git revert` merge commitu. `raw/texty` je čistě aditivní.
- Dev: `rm -rf /home/administrator/vsetin-osint-dev/data/integrace_cache` a `sqlite3 $INTEGRACE_DB "DROP TABLE dokument_text"` (ostatní tabulky zůstanou). Případně smazat `.venv-integrace`.

## Plánování (NEZAKLÁDAT bez schválení)
Návrh: denně 06:20 po `monitor`, přičemž seznam se před během přegeneruje `python3 scripts/seznam_dokumentu.py`. Plánovaná úloha „nesoulady“ běží v 06:39, takže by měla čerstvé texty.
