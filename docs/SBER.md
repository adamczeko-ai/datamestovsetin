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
- Síťově nedosažitelný hostitel (timeout, reset spojení, nedostupný robots.txt) má stav **`unreachable`**: zapíše se do `zdroje.<z>.nedosazitelny` (čas, důvod) a do RUNLOG, ale **není to chyba běhu** a nepřidává se do `chyby`. Odpověď serveru s HTTP chybou (4xx/5xx od cíle) zůstává `chyba`.
- Návratový kód `sber.py`: 0 = všechny zdroje `ok` nebo `unreachable`, 1 = alespoň jeden zdroj `chyba`.

## Dosažitelnost zdrojů z cloudu (diagnostika 23. 10. 2026)

| Hostitel | Z cloudového prostředí Claude | Kde spouštět |
|---|---|---|
| www.mestovsetin.cz, mapy.mestovsetin.cz | **nedosažitelné**: egress proxy tunel povolí (CONNECT 200), ale brána se k serveru nespojí (HTTPS: reset při TLS handshaku; HTTP: `503 upstream connect error … connection timeout`). DNS v pořádku (78.156.158.91, 85.92.62.117). Příčinou je pravděpodobně IP/geo filtr na straně hostingu města (HYPOTÉZA, z cloudu neověřitelné). mestovsetin.cz bez www: 403 od proxy (není v allowlistu). | mimo cloud (server, lokálně) |
| www.vhodne-uverejneni.cz | OK (Crawl-delay 30 s) | kdekoli |
| smlouvy.gov.cz | OK, ale přerušovaně (občas reset spojení) | kdekoli |
| ares.gov.cz | OK | kdekoli |

Zdroje **`usneseni`, `materialy_zm`, `rozpoctova_opatreni` a `uredni_deska`** proto musí běžet mimo cloud, na serveru nebo lokálně:

```bash
python3 scripts/sber.py --source usneseni --source materialy_zm --source rozpoctova_opatreni --source uredni_deska
```

Cloudový běh je přeskočí bez chyby (stav `unreachable`). Ostatní zdroje (`profil_zadavatele`, `registr_smluv`, `ares`) mohou běžet i v cloudu.

## Pseudonymizace a interpretace

- Fyzické osoby v odvozených datech (text, názvy, strany, účastníci) se nahrazují `[FO]`, u subjektů `[FO – pseudonymizováno]`. Firmy s právní formou, instituce a obce zůstávají. Jména se pseudonymizují i u funkcionářů (konzervativně).
- Metoda je heuristická (`integrace/sber/pseudo.py`):
  - oslovení (i s velkým písmenem) a tituly,
  - slovník křestních jmen se skloňováním (česká, slovenská, cizí a vietnamská jména), jméno + až 2 další slova,
  - příjmení na -ová, instrumentál po „s/se/a“,
  - jméno před „bytem / nar. / r. č.“,
  - příjemce dotace či daru v dativu („poskytnutí dotace X Y, …“), „fyzické osobě X Y“,
  - dokumenty o volbách (zápis o výsledku voleb, kandidáti) pseudonymizované celoplošně,
  - jména odvozená z názvů, které předávka pseudonymizovala.
- Nemění se:
  - ulice a adresy („ul./třída/nábřeží …“, „Tomáše Bati 21, Zlín“),
  - instituce pojmenované po osobě (škola, nadace, univerzita …),
  - firmy s právní formou.
- Kontrola 23. 10. 2026 po přegenerování: zúžený vzorec (křestní jméno nebo příjmení na -ová) našel 17 dvojic, **0 skutečných osob** (ulice, místa, instituce). Ve 173 náhodných vzorcích širokého vzorce nebyla žádná jednoznačná osoba. **Vzácná jména se však zachytit nemusí**, proto před dalším zveřejněním (web, export) doporučujeme namátkovou kontrolu člověkem.
- U subjektu FO z ARES se nepřebírá jméno ani sídlo (právní formy 100–108, 424, 425).
- Data nejsou zjištěním pochybení. Jakákoli interpretace (souvislost, podezření) se označuje jako **HYPOTÉZA** a ověřuje ji člověk.

## Pseudonymizace IČO OSVČ (§ 5 protokolu `docs/PREDAVANI_MEZI_RELACEMI.md`)

IČO podnikajících fyzických osob se po každém importu a sběru nahradí kódem (`integrace/sber/ico_fo.py`). Nahrazuje se všude: pole `ico`, id záznamů (`ico:…`, `subjekt:…`), hrany grafu, URL ARES, výskyty v textu včetně tvaru „123 45 678“ a manifest.

| Režim | Kdy | Kód | Vlastnosti |
|---|---|---|---|
| `hmac` (doporučený) | je nastavena proměnná prostředí `VSETIN_PSEUDO_KLIC` | `FO-` + 12 hex znaků HMAC-SHA256 | stabilní napříč běhy a soubory; bez klíče nevratný |
| `poradi` (výchozí bez klíče) | klíč chybí | `FO-0001`, `FO-0002`, … podle pořadí výskytu | na IČO nezávisí; propojení napříč běhy se neudrží (stejná OSVČ může dostat další kód) |

- Prostý hash IČO bez klíče se nepoužívá. Osmimístné IČO by šlo zpětně dohledat hrubou silou.
- Klíč patří jen do proměnných prostředí (nastavení prostředí VSETIN-OSINT nebo serveru). Nikdy do repa, PR ani logu.
- Po nastavení klíče přegenerujte data: `python3 scripts/import_inbox.py --handoff …`, potom `python3 scripts/sber.py`. Tím vzniknou stabilní kódy.
- Manifest obsahuje jen režim a počty (`pseudonymizace_ico_fo`), žádná IČO.

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

Zdroje webu města musí běžet mimo cloud (viz Dosažitelnost zdrojů z cloudu). V cloudu mohou běžet `profil_zadavatele`, `registr_smluv` a `ares`. Zdroje webu města tam skončí stavem `unreachable` a běh nespadne.

1. `git pull` větve, `python3 scripts/sber.py` (výchozí limity: 20 dokumentů na zdroj, 500 detailů registru smluv, 200 IČO, 20 intervalů profilu).
2. `python3 scripts/validate_schemas.py && python3 -m unittest discover -s tests`. Při chybě nevytvářet PR s daty, jen zprávu.
3. Commit `data/*.jsonl`, `data/manifest.json`, `docs/RUNLOG.md` na větev `sber/<YYYY-MM-DD>` a PR do `main`. Nikdy push do `main`, nikdy merge. `data/analyzy/signaly_stavy.json` se nemění.
4. Doporučená frekvence: denně (úřední deska se jinak ztrácí, protože nemá archiv). Profil zadavatele a registr smluv stačí denně v noci. Při 500 detailech za běh dožene registr smluv zbývajících ~4 600 verzí asi za 10 běhů. Pak se stahují jen nové verze.
