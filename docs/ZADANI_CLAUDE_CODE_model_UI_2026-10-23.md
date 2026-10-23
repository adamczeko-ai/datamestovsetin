# Zadání pro Claude Code / Codex: úpravy modelu a UI podle testu webu (23. 10. 2026)

**Prostředí:** jen `/home/administrator/vsetin-osint-dev`. Produkce `/opt/vsetin-osint` je jen pro čtení. Nasazení schvaluje vlastník.
**Podklady:** `docs/TEST_WEBU_2026-10-23.md` (ID nálezů), `data/dotace/*`, `data/monitor/*`, `data/entity/vr_organy_mestske_spolecnosti_2026-10-23.json`
**Postup:** nejdřív projdi existující schéma SQLite, importéry a API (`/api/organizations*`, `/api/search`, `/api/registry/contracts`) a přizpůsob se jejich konvencím.

## Z1 – Hodnota smlouvy z registru (M-01) – priorita 1
- V importu registru smluv čti `hodnotaBezDph`, `hodnotaVcetneDph` a `ciziMena{hodnota, mena}`.
- Ukládej `value_without_vat`, `value_with_vat`, `foreign_value`, `foreign_currency` a odvozené `value_kind`. DPH nepřepočítávej.
- Migrace: přepočti `value_kind` u existujících verzí z uloženého XML/JSON. Pokud surová data nejsou uložená, stáhni verze znovu s limitem 1 req/s.
- **Akceptace:** 39950637 → s DPH 114 804,80; 39950633 → s DPH 63 426,99; 39962817 → bez DPH 83 125 a s DPH 100 581,25. Ve vzorku 500 verzí klesne podíl „nezjištěno“ ze 49 % na ≤ 20 %.

## Z2 – Zjištěné transfery z MONITORu (M-02) – priorita 1
- Nová tabulka `observed_transfer(provider_ico, recipient_ico, year, period_end, kind[Transfer|Borrow], amount_out, amount_in, source_url, load_id, fetched_at, evidence_level='secondary_aggregate')`.
- Zdroj: open data FIN 2-12 M (FINM01_UJ, sloupec Partner Fin) jako primární cesta; `data/dotace/uzemni_registr_vsetin_poskytovatel_2026.csv` jako seed a kontrola.
- UI v profilu příjemce: „Transfery od Města Vsetín 2026 (k 31. 8.): 18 298 000 Kč · zdroj MONITOR · kumulativně, nejde o úhradu konkrétní smlouvy“.
- U kurátorované smlouvy stejného páru a roku zobrazit poměr „čerpáno / smluvní částka“ s popiskem **indicie**.
- **Akceptace:** Vsetínská sportovní 18 298 000 / 27 447 000 = 66,7 %; DK 12 400 000 / 18 600 000; VHK z.s. 5 668 000 / 8 500 000.

## Z3 – Organizace: pokrytí a identita (M-05, M-06, M-07, B1 #16) – priorita 2
- Doplnit 15 příspěvkových organizací města podle `uzemni_registr_vsetin_poskytovatel_2026.csv` (forma PO_USC), kategorie „Příspěvková organizace“. Identitu ověřit v ARES.
- Pozor na 60042354 (MŠ Trávníky 1218): v ARES 404, v MONITORu 2026 jen vratka 237 517,38 Kč. Stav nastavit na „pravděpodobně zaniklá – ověřit“.
- U všech organizací přidat zdroj ARES (`evidence_level=primary`, datum ověření) vedle `canonical2026`.
- Typ vazby `zrizovatel` (Město → PO). Pole `previous_names[]` z ARES-VR, prohledávat i ve vyhledávání.
- **Akceptace:** `/api/organizations` vrací ≥ 24 subjektů; hledání „P.M.B. Moravia“ najde VHK Vsetín s.r.o.

## Z4 – Orgány společností z VR (M-03) – priorita 2
- Import z ARES `/ekonomicke-subjekty-vr/{ico}` pro městské společnosti: aktuální i historické členy statutárního orgánu a dozorčí rady (`datumZapisu`, `datumVymazu`, `vznikFunkce`, `zanikFunkce`).
- **Neukládat** `datumNarozeni` ani adresu fyzických osob (minimalizace). Osoby nespojovat podle jména, kandidáty na sloučení posílat do fronty (M-04).
- **Akceptace:** DN Vsetín 4, Dům kultury 5, Městské lesy 7, TS Vsetín 8, Vsetínská sportovní 7 aktuálních členů. Stav VR k datu importu, porovnat s `data/entity/vr_organy_mestske_spolecnosti_2026-10-23.json`.

## Z5 – MONITOR rozpočet města (pokračování úlohy 1 z integračního zadání) – priorita 2
- Pro roky do 2025 brát **tab. IV rekapitulace** (FINM203, řádky 4200 příjmy po konsolidaci, 4430 výdaje po konsolidaci, 4440 saldo) a tab. III financování (FINM202).
- Od 2026 (FINM2026 bez tab. IV) počítat konsolidaci z položek 413x a 534x.
- Stahovat **HTTP Range** jen potřebné členy ZIP (~4 MB místo ~24 MB), změny hlídat přes ETag.
- **Akceptace:** 2024 a 2025 = závěrečný účet na haléř (4200, 4430, 4220). Řada 8115 sedí s RO podle `data/monitor/kontrola_RO_8115_monitor.json`.

## Z6 – Konzistence času „poslední kontroly“ (B1 #15) – priorita 2
- Jedna definice pro přehled, profil i `/api/health`, např. „poslední úspěšný běh libovolné plánované úlohy“, s časem v SELČ a odkazem na detail. Přehled nesmí ukazovat starší hodnotu než `/api/health`.

## Z7 – Hledání (F-01, F-02, F-07) – priorita 3
- Shoda na hranici slova (FTS5 s `unicode61 remove_diacritics 2`), prefixové dotazy (`lávk*`), volitelně jednoduchý český stemmer.
- Popisek „Datum“ u výsledků registru přejmenovat na „Zveřejněno“; pokud je známé datum podpisu, zobrazit i „Podepsáno“.
- **Akceptace:** `lávka` nevrací „Václavka“, `lávka` a `lávky` vrací shodnou množinu.

## Z8 – Přístupnost (A-01, A-02) – priorita 3
- `<caption>` (může být vizuálně skrytý) a `th scope` u všech 7 tabulek.
- Po hledání zapsat do `aria-live` větu „Nalezeno N výsledků v M kategoriích“.

## Z9 – Stavová škála zdrojů (B5) – priorita 3
- Zavést stavy `nesledovano | overeno_dostupne | vyvoj | integrovano | chyba | blokovano` s odkazem na protokol ověření.

## Obecně
- Testy: unit testy pro každý importér a snapshot API pro akceptační hodnoty.
- Každý importér zapisuje do `sync_ledger` (ETag/hash, viz `scripts/sync/sync_core.py`).
- Výstupem je předávací zpráva s diffem, výsledky testů a návrhem nasazení.
