# Sběr dat (`scripts/sber.py`) a datová vrstva `data/*.jsonl`

Stav k 23. 10. 2026 (Europe/Prague). Fáze 1: jednorázová inicializace z předávky + inkrementální sběr.

## Co vzniklo

| Část | Soubor | Popis |
|---|---|---|
| Vstupní bod | `scripts/sber.py` | `--source X` (opakovatelné), `--dry-run`, `--limit`, `--limit-rs` (≤ 500), `--limit-ares`, `--max-stranek` |
| Import předávky | `scripts/import_inbox.py --handoff <klon>` | jednorázově data/inbox z větví handoff repa (PR #3, #4, #5, #7) → `data/*.jsonl`; handoff repo jen čte (`git show`) |
| Knihovna | `integrace/sber/` | `store` (JSONL, deduplikace, manifest, RUNLOG), `pseudo` (pseudonymizace FO), `vismo` (web města), `profil` (XMLdataVZ), `registr` (registr smluv), `zdroje` (kolektory) |
| HTTP | `integrace/http.py` | rozšířeno: volitelný User-Agent, robots.txt + Crawl-delay, provoz bez SQLite evidence |
| ARES | `scripts/ares_overeni.py` | nová funkce `overit_ico()` (logika beze změny, sdílí ji `sber.py`) |
| Schémata | `data/schema/jsonl-*.schema.json`, `manifest.schema.json` | validuje `scripts/validate_schemas.py` (každý řádek JSONL + kontrola sha256 a duplicit) |
| Stav | `data/manifest.json` | poslední běh, kurzory, počty a posledních 20 chyb po zdrojích, souhrn souborů |
| Log | `docs/RUNLOG.md` | jedna sekce za ostrý běh (dry-run se nezapisuje) |
| Testy | `tests/test_sber.py` | parsery na uložených vzorcích, deduplikace, manifest, schémata, robots.txt, end-to-end s podvrženým HTTP |

## Datový model

Každý řádek `data/<nazev>.jsonl` je jeden záznam s poli **`id`, `source_url`, `retrieved_at`, `sha256`**.

- `sha256` = SHA-256 kanonického JSON obsahu záznamu bez polí `sha256`, `retrieved_at`, `source_url`, `puvod` (obsahový otisk; změna jen času nebo URL novou verzi nevytvoří). U staženého souboru je otisk souboru zvlášť v `zdroj_sha256`.
- Soubory jsou **append-only**. Shodné `(id, sha256)` se přeskočí, změněný obsah stejného `id` se připíše jako nová verze. Platí poslední řádek s daným `id`. Nic se nemaže.
- `puvod` (jen u importu předávky): repo, větev, commit, soubor, PR, sha256 souboru.

| Soubor | id | Zdroj |
|---|---|---|
| `usneseni.jsonl` | `usneseni:<id_dokumenty>:<číslo>` | výpisy usnesení RM (ds-1006) a ZM (ds-1004) |
| `dokumenty.jsonl` | `dok:<id_dokumenty>` | evidence stažených souborů webu města (kvalita textu, sha256, .doc ke konverzi) |
| `materialy_zm.jsonl` | `material_zm:<balíček>:<soubor>` | materiály ZM pro veřejnost (ds-19121, ZIP) |
| `rozpoctova_opatreni.jsonl` | `ro:<id_dokumenty>` | RO 2017–2026 (ds-19317 a roční podsložky) |
| `uredni_deska.jsonl`, `uredni_deska_snimky.jsonl` | `ud:<id>`, `ud_snimek:<čas>` | úřední deska; snímek seznamu při každém běhu (web nemá archiv) |
| `verejne_zakazky.jsonl` | `vz:<kód>` | profil zadavatele vhodne-uverejneni.cz, XMLdataVZ |
| `registr_smluv.jsonl` | `rs:<idVerze>` | registr smluv; `detail` = XML metadata verze |
| `subjekty_ares.jsonl` | `ico:<IČO>` | ARES |
| `vyber_dodavatele.jsonl`, `casove_osy.jsonl`, `graf_uzly.jsonl`, `graf_hrany.jsonl`, `stranky.jsonl` | viz schémata | jen z předávky (odvozené vrstvy P1d v2, P2g, P3i, stránky webu) |

Vztah k dřívějším datům: `data/rozpocet/`, `data/zakazky/`, `data/entity/` zůstávají beze změny (kurátorované, validované). JSONL je surovější, úplnější vrstva se zdrojem u každého záznamu.

## Pravidla sběru

- Jen veřejně publikované dokumenty. User-Agent `VSETIN-OSINT research (cech.lpt@gmail.com)`.
- Max. 1 požadavek/s na hostitele. Pokud robots.txt uvádí `Crawl-delay`, platí delší interval (vhodne-uverejneni.cz: 30 s).
- robots.txt se načte před prvním požadavkem na hostitele. Zakázaná URL se nestahuje. Když robots.txt není dostupný (síť, 5xx), hostitel se pro běh vynechá (konzervativně). 404 = vše povoleno.
- Selhání jednoho zdroje nezastaví ostatní; chyba jde do `manifest.json` (`zdroje.<z>.chyby`) a do RUNLOG. Kurzor zdroje se při chybě neposune.
- Návratový kód `sber.py`: 0 = všechny zdroje ok, 1 = alespoň jeden zdroj selhal.

## Pseudonymizace a interpretace

- Fyzické osoby v odvozených datech (text, názvy, strany, účastníci) se nahrazují `[FO]`, u subjektů `[FO – pseudonymizováno]`. Firmy s právní formou, instituce a obce zůstávají. Jména se pseudonymizují i u funkcionářů (konzervativně).
- Metoda je heuristická (`integrace/sber/pseudo.py`): oslovení, tituly, slovník křestních jmen se skloňováním, příjmení na -ová, instrumentál po „s/se“, jména odvozená z názvů pseudonymizovaných v předávce. Po importu prošla kontrola zbytkových vzorů (dvojice slov s velkým písmenem v kontextu jména). V textech, které kontrola neodhalí, **mohou zůstat jména, zejména vzácnější**. Před dalším zveřejněním (web, export) proto doporučujeme namátkovou kontrolu člověkem.
- U subjektu FO z ARES se nepřebírá jméno ani sídlo (právní formy 100–108, 424, 425).
- Data nejsou zjištěním pochybení. Jakákoli interpretace (souvislost, podezření) se označuje jako **HYPOTÉZA** a ověřuje ji člověk.

## Zdroje a inkrementalita

| Zdroj | Co dělá běh | Kurzor v manifestu |
|---|---|---|
| `usneseni` | výpis ZM a RM (1. stránka a další, dokud přibývají neznámé dokumenty) → nové PDF/.doc → `pdftotext` / `antiword` → rozpad na usnesení; opakuje dokumenty `doc_nekonvertovano` (264 .doc z předávky) | `posledni_kontrola` |
| `materialy_zm` | nové ZIP balíčky → návrhy usnesení (HTML) | `posledni_kontrola` |
| `rozpoctova_opatreni` | kořenová složka + roční složky aktuálního a předchozího roku → nové PDF | `rocni_slozky` |
| `uredni_deska` | **snímek seznamu při každém běhu** + stažení nových příloh | `url`, `posledni_snimek`, `detail_na_soubory` |
| `profil_zadavatele` | XMLdataVZ od `stazeno_do − 60 dní` do dneška po ≤ 180denních intervalech (`--limit` intervalů za běh) | `stazeno_do` |
| `registr_smluv` | 1. stránka vyhledávání (nové verze) + detail XML čekajících verzí, nejnovější první, **max. 500 za běh**; 5 chyb za sebou = zdroj ukončen | `ceka_na_detail` |
| `ares` | IČO z usnesení, zakázek, stran smluv a výběru dodavatele, která ještě nejsou v `subjekty_ares.jsonl` | `ceka_na_overeni` |

Kurzor profilu po importu: `2023-12-31`. Předávka P2f obsahuje jen zakázky 2017–2023 (+1 neúplnou z 2025): export XMLdataVZ od roku 2024 mísí dvě struktury zakázky a parser předávky novější z nich nepřečetl. Sběr proto doplní roky 2024–2026.

## Spuštění

```bash
python3 scripts/import_inbox.py --handoff ../vsetin-osint-handoff   # jednorázově (opakování nic nezdvojí)
python3 scripts/sber.py --dry-run --limit 2                           # zkouška bez zápisu
python3 scripts/sber.py                                               # plný inkrementální běh
python3 scripts/validate_schemas.py && python3 -m unittest discover -s tests
```

Závislosti: Python 3.10+ (standardní knihovna), `jsonschema` (jen validace a testy), `pdftotext` (poppler-utils) a `antiword` pro text z PDF/.doc. Když nástroj chybí, dokument se zaeviduje s `kvalita_textu = nastroj_chybi` a zpracuje se při dalším běhu.

## Naplánovaný běh (návrh – NEZAKLÁDAT bez schválení vlastníka)

Běh musí probíhat v prostředí s přístupem na www.mestovsetin.cz a smlouvy.gov.cz. Z cloudového prostředí Claude je web města blokován a smlouvy.gov.cz jen přerušovaně dostupný.

1. `git pull` větve, `python3 scripts/sber.py` (výchozí limity: 20 dokumentů na zdroj, 500 detailů registru smluv, 200 IČO, 20 intervalů profilu).
2. `python3 scripts/validate_schemas.py && python3 -m unittest discover -s tests`. Při chybě nevytvářet PR s daty, jen zprávu.
3. Commit `data/*.jsonl`, `data/manifest.json`, `docs/RUNLOG.md` na větev `sber/<YYYY-MM-DD>` a PR do `main`. Nikdy push do `main`, nikdy merge. `data/analyzy/signaly_stavy.json` se nemění.
4. Doporučená frekvence: denně (úřední deska se jinak ztrácí, protože nemá archiv). Profil zadavatele a registr smluv stačí denně v noci. Při 500 detailech za běh dožene registr smluv zbývajících ~4 600 verzí asi za 10 běhů. Pak se stahují jen nové verze.
