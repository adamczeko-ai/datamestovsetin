# Zadání pro Claude Code (dev server): automatizace AI analytiky

*2026-10-23. Schváleno vlastníkem: automatizace a nasazení analytiky **jen na dev serveru**. Zveřejňovat se smí jen signály ověřené člověkem. Produkce se nemění.*

## Co se nasazuje
`scripts/dev_pipeline.sh` (repo `adamczeko-ai/datamestovsetin`, `main`) spouštěný cronem v pracovní dny ráno:
1. Aktualizuje klon na `origin/main` (jen fast-forward). Klon musí být čistý, jinak skript nic nedělá.
2. Spustí testy repa. Když selžou, nic se nezapisuje.
3. Stáhne texty dokumentů po stranách (`python -m integrace dokumenty`).
4. Nové texty pošle jako PR z jediné větve `data/texty-auto`, nikdy do `main`.
5. Spustí deterministickou analytiku (R1–R16, signály v2, export ověřených signálů) do `data/analytika/` v dev složce. Soubory v repu vrátí do původního stavu.
6. Zapíše souhrn běhu do `data/analytika/posledni_beh.json` (časy v Europe/Prague) a log do `logs/ai-pipeline-<datum>.log`.

Jazykový model na serveru neběží. LLM vrstva je plánovaná úloha v Claude, která čte `main`.

## Hranice (závazné)
- Pouze `/home/administrator/vsetin-osint-dev` a klon repa. Skript `/opt` sám odmítne (exit 3).
- **Bez dalšího schválení zakázáno:**
  - cokoli v `/opt/vsetin-osint` a produkční DB,
  - Docker, restart služeb, síť,
  - `apt install`, OCR,
  - napojení dev aplikace na výstupy (zatím jen soubory).
- Cron jen v uživatelském crontabu účtu, pod kterým běží dev, ne systémový.
- **GitHub token nevytvářej a negeneruj.** Pokud chybí, nasaď v režimu bez PR (viz krok 3) a nahlas to.
- Do reportu dávej jen skutečné výstupy příkazů.

## Postup

### 0. Předpoklad
Hotové zadání `docs/ZADANI_CLAUDE_CODE_texty_dokumentu_2026-10-23.md`, tedy klon, testy, venv a první běh `dokumenty`. Pokud ještě neproběhlo, udělej nejdřív jeho kroky 1–4. Krok 5 (ruční PR) přeskoč, PR založí pipeline.

### 1. Diagnostika (jen čtení)
```bash
timedatectl | grep -i "time zone"        # časová zóna serveru (pro cron)
cron --version 2>/dev/null; systemctl is-active cron crond 2>/dev/null
crontab -l 2>/dev/null                   # stávající úlohy – NEMĚNIT, jen přidat
git -C <klon> remote -v && git -C <klon> config user.email
git -C <klon> ls-remote origin >/dev/null && echo "čtení OK"
git -C <klon> push --dry-run origin HEAD:refs/heads/data/texty-auto 2>&1 | tail -1   # zápisová práva
ls -l /home/administrator/vsetin-osint-dev/.env.github 2>/dev/null
"$PY" -c "import jsonschema, pypdf" 2>&1 # PY = venv python, pokud existuje
```
- `jsonschema` chybí: doinstaluj **jen do venv** (`.venv-integrace/bin/pip install jsonschema pypdf`), ne systémově.
- `git push --dry-run` selže: nasaď bez PR a nahlas, že vlastník musí doplnit přístup.

### 2. Zkušební běh nanečisto
```bash
cd <klon> && KLON=$PWD scripts/dev_pipeline.sh --dry-run
cat /home/administrator/vsetin-osint-dev/data/analytika/posledni_beh.json
tail -n 30 /home/administrator/vsetin-osint-dev/logs/ai-pipeline-$(TZ=Europe/Prague date +%F).log
git -C <klon> status --short   # musí být prázdné
```
Očekávaný výsledek:
- `stav` je `ok` nebo `varovani`, s důvodem v `poznamky`,
- existuje `data/analytika/signaly.json`,
- `verejne_signaly.json` má `pocet: 0` (zatím nic není ověřeno druhým člověkem),
- klon je čistý.

### 3. Ostrý běh
- Pokud je k dispozici `GITHUB_TOKEN` (env nebo `.env.github`, oprávnění 600): `KLON=<klon> scripts/dev_pipeline.sh`. Ověř, že vznikl jeden PR z `data/texty-auto` a jeho URL je v `posledni_beh.json`.
- Bez tokenu, ale s právem push: skript větev pushne a do `poznamky` zapíše „PR nezaložen“. PR založí vlastník ručně.
- Bez práva push: zůstaň u `--dry-run` v cronu a nahlas to.

### 4. Cron (pracovní dny 05:47 Europe/Prague)
- Server v Europe/Prague: řádek `47 5 * * 1-5`.
- Server v UTC: `47 3 * * 1-5` v létě, resp. `47 4 * * 1-5` v zimě. Pokud cron podporuje `CRON_TZ`, použij `CRON_TZ=Europe/Prague` a `47 5 * * 1-5`.
```bash
( crontab -l 2>/dev/null; echo '# VSETIN-OSINT dev AI pipeline (schváleno 2026-10-23)'; \
  echo '47 5 * * 1-5 KLON=<klon> <klon>/scripts/dev_pipeline.sh' ) | crontab -
crontab -l | tail -n 3
```
Stávající řádky crontabu se nesmí změnit. Před změnou ulož zálohu: `crontab -l > ~/crontab.zaloha-2026-10-23`.

### 5. Akceptace
| Kontrola | Očekáváno |
|---|---|
| `--dry-run` | exit 0, klon čistý, `posledni_beh.json` existuje |
| ostrý běh | jeden otevřený PR z `data/texty-auto` (nebo poznámka, proč ne) |
| 2. ostrý běh týž den | žádné nové texty a žádný druhý PR |
| `verejne_signaly.json` | `pocet: 0`, dokud vlastník nevyplní `druhe_overeni` |
| `crontab -l` | původní řádky + 2 nové |

## Rollback
```bash
crontab ~/crontab.zaloha-2026-10-23         # vrátí crontab do původního stavu
rm -rf /home/administrator/vsetin-osint-dev/data/analytika /home/administrator/vsetin-osint-dev/logs/ai-pipeline-*
```
Otevřený PR z `data/texty-auto` stačí zavřít. Repo ani produkce se nemění.

## Report do hlavního koordinačního chatu
- výstupy diagnostiky,
- obsah `posledni_beh.json` z obou běhů,
- URL PR,
- výpis `crontab -l` po změně,
- co bylo blokováno a co musí udělat vlastník (token, práva).
