# Předávání práce mezi relacemi Claude (protokol `predani@1`)

Platí pro všechny relace, které přispívají do `adamczeko-ai/datamestovsetin`:
- Claude in Chrome (sběr a ověřování dat v prohlížeči),
- Claude Code (implementace),
- plánované úlohy (`ai/ULOHA_*.md`).

Cíl: každý poznatek dorazí jako **PR v jednotném tvaru**. Hlavní relace „Testování VSETÍN OSINT aplikace“ ho pak umí bez ručního přepisování připravit k integraci.

## 1. Kdo co smí
| Kdo | Smí | Nesmí |
|---|---|---|
| Přispívající relace | vlastní větev, commity, PR do `main`, štítky | push do `main`, merge, měnit cizí datové soubory (`subjekty.json`, `signaly_stavy.json`, data jiných várek) |
| Hlavní relace (integrace) | revize PR, opravy ve stejné větvi, příprava integrace (konektor, schéma, test), komentáře, štítek `pripraveno-k-merge` | merge (rozhoduje vlastník), produkce `/opt/vsetin-osint` |
| Vlastník (Adam) | schválení (review) a merge PR, nasazení | – |

## 2. Větev a PR
- Větev: `predani/<zdroj>-<tema>-<YYYY-MM-DD>`, např. `predani/monitor-transfery-2026-10-23`.
- PR do `main` se štítkem **`predani`**. Šablona `.github/pull_request_template.md` se vyplní celá.
- Jedno téma = jeden PR. Žádné hromadné balíky různých zdrojů.
- Před vytvořením PR větev přeskládej (rebase) na aktuální `main`. Nový oddíl v `CHANGELOG.md` vlož **před poslední oddíl**, ne na konec, ať nevzniká konflikt se souběžnými relacemi.

## 3. Povinný obsah PR
1. **Data:** `data/<zdroj>/…` (CSV v UTF-8 se středníkem, nebo JSON se schématem v `data/schema/`).
2. **Manifest:** `data/<zdroj>/manifest_<tema>_<YYYY-MM-DD>.json` obsahuje:
   - `url`, `etag` nebo `last_modified`, `sha256` a `radku` u každého souboru,
   - čas stažení v Europe/Prague.
3. **Kontrola:** `scripts/kontrola_<tema>.py`, při úspěchu exit 0. Musí ověřit aspoň jednu nezávislou shodu (součty, rekonciliaci s jiným zdrojem) nebo vnitřní konzistenci.
4. **Předávací zpráva:** `docs/HANDOFF_<YYYY-MM-DD>_<tema>.md` s oddíly:
   - *Nové*,
   - *Zjištění pro model* (pravidla parseru, mapování),
   - *Otevřené*,
   - *Návrh integrace*: který konektor v `integrace/sources/`, jaká tabulka a jaké akceptační hodnoty.
5. **Štítky tvrzení:** Doloženo / Odvozeno / Indicie / Hypotéza. Indicie a hypotézy nikdy nezapisovat jako fakt.
6. **CI zelené:** `python3 scripts/ci_validate.py` a nová kontrola.

## 4. Co udělá hlavní relace s PR se štítkem `predani`
Postup je v `ai/ULOHA_predani_integrace.md`. Stručně:
- spustí kontroly,
- porovná data s `integrace/` a navrhne nebo doplní konektor a akceptační test,
- výsledek zapíše jako komentář a ve stejné větvi,
- pak nastaví štítek `pripraveno-k-merge`, případně `potrebuje-opravu`.

O merge rozhoduje vlastník.

## 5. Ochrana osobních údajů
- Fyzické osoby: jen jméno, funkce a období.
- Nikdy bydliště, datum narození, rodné číslo.
- Podnikající fyzická osoba v datech o příjemcích se anonymizuje.
