# Zadání pro Claude Code / Codex – integrace MONITOR, RÚIAN, RVZ, VR

**Prostředí:** výhradně `/home/administrator/vsetin-osint-dev`. Produkce `/opt/vsetin-osint` je **jen pro čtení**.
**Kontext:** `docs/AUDIT_INTEGRACI_2026-10-23.md`, `data/integrace/stav_zdroju_2026-10-23.json`
**Výchozí kód:** `scripts/sync/sync_core.py` (idempotentní stahování s evidencí), `scripts/sync/parse_monitor_finm.py`, testy v `tests/`.

## Pravidla
1. Nejprve analyzuj existující konektory dev aplikace: strukturu, běh úloh (tabulka „Pokrytí a stav zdrojů“), SQLite schéma a konvence. **Přizpůsob se jim**, `sync_core.py` ber jen jako referenci.
2. Neměň produkční DB ani konfiguraci, nerestartuj Docker, nenasazuj a nezakládej produkční cron.
3. Každá nová úloha musí být idempotentní: podmíněný GET (ETag), SHA-256 a evidence běhů. Opakování při 429/5xx s exponenciální prodlevou a `Retry-After`.
4. Zápis do DB se dělá jako upsert podle přirozeného klíče (viz níže), uvnitř transakce a až po úplném stažení a validaci souboru.
5. Výstupem každé úlohy je řádek v přehledu stavu zdrojů (poslední běh, úspěch, počet záznamů, ETag/hash).

## Úloha 1 – MONITOR FIN 2-12 M (priorita 1)
- Objev období: katalog `…/api/opendata/monitor` → položky `FinM_{RRRR}/…` (od 2026) a `FinM/…` (do 2025). Kontrola nových dat přes RSS `…/api/opendata/rss`.
- URL souboru: `soubor_ke_stažení` + **`.zip`** (bez přípony 404).
- Parsuj `FINM01_UJ_*.csv` (UTF-8 s BOM, `;`, znaménko mínus na konci). Uchovávej řádky pro IČO z konfigurace: výchozí 00304450 a dále příspěvkové organizace a obchodní společnosti města z `data/entity/subjekty.json`.
- Klíč: `(obdobi, ucjed, typ, paragraf, polozka, uz, zdroj, nastroj, mimud, partner)`, hodnoty `schvaleny`, `po_zmenach`, `vysledek`.
- Konsolidace: vedle hrubých částek počítej i konsolidované bez 4134/4138/5345/5348 a označ je jako odvozené. Rozdíl 4134 ≠ 5345 zaloguj, nevyrovnávej.
- Akceptační test: pro 08/2026 a IČO 00304450 je 1 745 řádků; 8115 po změnách 118 457 944,86; 8123 = 107 500 000.
- Územní transfery (náhrada za Územní registr dotací) se odvozují ze stejného souboru: řádky se sloupcem `partner` ≠ prázdný.

## Úloha 2 – RÚIAN VFR (priorita 2)
- `https://vdp.cuzk.gov.cz/vymenny_format/soucasna/{poslední den měsíce RRRRMMDD}_OB_541630_UKSH.xml.zip`, jednou měsíčně.
- Streamově (lxml iterparse) importuj adresní místa, stavební objekty, parcely, ulice a ZSJ. Klíčem jsou kódy RÚIAN. Geometrii zatím jen jako definiční bod (S-JTSK).
- UI musí uvádět, že **RÚIAN neprokazuje vlastnictví**.
- Akceptace (soubor 20260930): 3 778 AM / 6 739 SO / 26 965 parcel.

## Úloha 3 – RVZ open data (priorita 3)
- Měsíčně po 5. dni: `opendata-rvz/VZ-{MM}-{RRRR}.zip` (183 MB, 1,3 GB JSON). **Streamově** (ijson), filtr podle `zadavatele[].subjekt.ico ∈ sledovaná IČO` a dodavatelů ve sledovaných IČO.
- Klíč: `identifikator_NIPEZ` (+ část). Uchovávej `casova_znacka` pro detekci novějších verzí.
- Nejdřív jednorázově projdi 02/2024–09/2026 a zjisti, zda Město Vsetín vůbec vystupuje. Pokud ne, zapiš do stavu zdroje „zdroj neobsahuje zakázky města (e-nástroj mimo RVZ)“.
- Zátěž: jeden soubor měsíčně, nestahovat paralelně.

## Úloha 4 – Veřejný rejstřík (priorita 4)
- CKAN `dataor.justice.cz`, soubory `*-actual-ostrava-{RRRR}.csv.gz` pro formy: sro, as, spolek, ustav, nadace, pobspolek a další relevantní. Vsetínsko = **KS Ostrava**.
- Bez ETag → rozhoduje SHA-256 z `sync_core`. IČO doplnit na 8 znaků (`zfill(8)`).
- Fyzické osoby ve statutárních orgánech: ukládej jméno a funkci s datem zápisu a výmazu. **Neukládej** datum narození ani adresu bydliště (minimalizace).
- Ověř, zda stávající úloha „ARES – veřejný rejstřík“ už tyto údaje nemá. Pokud ano, dataor použij jen jako hromadný doplněk a porovnání.

## Úloha 5 – Registr dotací (priorita 5, podmíněně)
- Neimplementovat automaticky, dokud vlastník nepotvrdí podmínky použití nedokumentovaného `/api/grants/*` u MF.
- Územní část pokrývá Úloha 1.

## Úloha 6 – ČÚZK REST API KN (blokováno)
- Až po registraci vlastníkem. Klíč ukládat do `.env` na serveru, nikdy do repa ani na klienta. Respektovat limit volání a účel podle §1 odst. 2 katastrálního zákona.

## Schéma evidence (navrženo, přizpůsobit stávající DB)
```sql
CREATE TABLE IF NOT EXISTS sync_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL, url TEXT NOT NULL, checked_at TEXT NOT NULL,
  http_status INTEGER, etag TEXT, last_modified TEXT, size_bytes INTEGER,
  sha256 TEXT, status TEXT NOT NULL CHECK (status IN ('downloaded','not_modified','unchanged_hash','error')),
  local_path TEXT, attempts INTEGER NOT NULL DEFAULT 1, error TEXT,
  records_upserted INTEGER, import_status TEXT
);
```

## Definice hotového
- Testy prochází v dev prostředí: unit testy a jeden živý běh každé úlohy.
- Druhé spuštění téhož dne nic nestáhne (304 / unchanged_hash), což dokládá evidence.
- Úloha je vidět v „Pokrytí a stav zdrojů“ v dev.
- Předávací zpráva s diffem, výsledky testů a návrhem nasazení. **Nasazení schvaluje vlastník.**
