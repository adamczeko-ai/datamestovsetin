# Audit datových integrací – VSETÍN OSINT

**Relace:** Claude (Chrome + cloudový sandbox), 23. 10. 2026, 00:00–01:30 SELČ
**Rozsah:** 7 zdrojů ze zadání + ARES jako doplněk k Veřejnému rejstříku
**Přístup na server (`/opt/vsetin-osint`, `…-dev`): ŽÁDNÝ.** Nic jsem neměnil na produkci ani ve vývoji. Výsledkem jsou ověření zdrojů, prototyp sync jádra s testy a zadání pro Claude Code.

## 0. Výchozí stav (ověřeno)

- **GitHub `datamestovsetin`:** 2 commity z 22. 10. (rozpočty 2001–2026, RO 2025 a 2026, registr 38 subjektů). Žádný z 7 zdrojů tam není.
- **nasvsetin.cz → Zdroje a metodika:** všech 7 zdrojů je vedeno jako *neintegrováno / nedostupné*. Běží 21 jiných úloh, z toho 20 OK a 1 částečně (archiv dokumentů města). Mezi nimi jsou „ekonomika – dotace“ (Hlídač státu, sekundární zdroj), „ARES – veřejný rejstřík“ a „zakázky (RSS)“.
- **Evidence stažení** dosud neexistovala. Založil jsem `data/integrace/evidence_stazeni.json` a v prototypu tabulku `sync_ledger`. Nic z dnešních testů nebylo stahováno opakovaně.
- **Cloudový sandbox** na zdroje nedosáhne (proxy odmítá spojení; výjimkou je ARES). Testy proto běžely v prohlížeči přes `fetch()` na stránce zdroje.

## 1. Souhrn stavů

| # | Zdroj | Stav | Klíčový nález |
|---|---|---|---|
| 1 | MONITOR – FIN 2-12 M | **TESTOVÁNO** | ZIP/CSV bez autentizace, ETag a 304 fungují. Data Vsetína za 08/2026 sedí na RO 2026. |
| 2 | RÚIAN – VFR obec 541630 | **TESTOVÁNO** | 3 778 adresních míst, 6 739 stavebních objektů a 26 965 parcel v jednom souboru o 6 MB |
| 3 | NIPEZ – RVZ open data | **TESTOVÁNO** | Formát funguje. Město Vsetín v 09/2026 nemá žádný záznam; možná používá nástroj, který RVZ zatím nepublikuje. |
| 4 | Veřejný rejstřík (dataor) + ARES | **TESTOVÁNO** | Rejstříkovým soudem je KS Ostrava. IČO jsou bez úvodních nul. ARES ověřil 37 z 38 IČO. |
| 5 | MONITOR – Registr dotací | **PŘÍSTUP OVĚŘEN** | Jde jen o interní JSON API, mimo open data katalog |
| 6a | ČÚZK REST API KN | **BLOKOVÁNO** | Bez API klíče (registrace musí provést vlastník) |
| 6b | ČÚZK DP/WSDP | DOKUMENTACE OVĚŘENA | Placená služba; údaje o vlastnících jsou mimo rozsah |
| – | Sbírka listin | **BLOKOVÁNO** (hromadně) | Oficiální strojová služba nenalezena |

Strojová verze: `data/integrace/stav_zdroju_2026-10-23.json`.

**Pořadí priorit beze změny.** MONITOR je nejdál a nic ho neblokuje. Upozornění k RÚIAN: data parcel z VFR pokrývají velkou část toho, co se čekalo od ČÚZK, a to bez API klíče.

## 2. Zdroje podrobně

### 2.1 MONITOR – rozpočtová data (FIN 2-12 M)
- **Katalog:** `https://monitor.statnipokladna.gov.cz/api/opendata/monitor` (DCAT-AP-CZ, JSON-LD, 811 datových sad, z toho 49 číselníků). Změny publikuje RSS `…/api/opendata/rss`.
- **Soubor:** `/data/extrakty/csv/FinM2026/2026_08_Data_CSUIS_FINM2026.zip` (24,9 MB). Obsahuje FINM01_UJ (1,65 mil. řádků), FINM01_KRAJ, FINM01_REP a FINM02.
- **Úskalí:**
  1. `soubor_ke_stažení` v katalogu je **bez `.zip` a vrací 404**, příponu je nutné doplnit.
  2. Od roku 2026 je výkaz ve složce `FinM2026`, starší roky jsou ve `FinM`.
  3. V katalogu chybí období 01 a 07/2026.
  4. `Last-Modified` obsahuje aktuální čas, nepoužívat. Změnu spolehlivě pozná ETag (mtime+velikost); `If-None-Match` vrací 304.
  5. Záporné částky mají znaménko na konci (`12394400.48-`).
- **Vsetín (IČO 00304450, ÚJ 1000017218), 08/2026:** 1 745 vlastních řádků. Dalších 55 řádků patří jiným subjektům (31 IČO), u kterých je Vsetín partnerem transferu.
- **Křížová kontrola s RO 2026 (repo):** položky 8115 (118 457 945 = RO 14), 8123 (107 500 000 = RO 12) a 8113 (200 000 000, stav před RO 17) **souhlasí přesně**. Ověřený fakt: MONITOR a zpracovaná RO jsou konzistentní.
- **Pozor, konsolidace:** položky 4134 (1 356,6 mil.) a 5345 (1 224,3 mil.) jsou převody mezi vlastními účty. Bez konsolidace by příjmy vycházely 2,1 mld. Kč. Metodiku MONITORu (proč 4134 ≠ 5345) jsem neověřil.
- Souhrn: `data/monitor/finm_2026_08_vsetin_souhrn.json`

### 2.2 RÚIAN – VFR
- `https://vdp.cuzk.gov.cz/vymenny_format/soucasna/{RRRRMMDD}_OB_541630_UKSH.xml.zip`, bez autentizace, vychází měsíčně.
- Soubor k 30. 9. 2026: 6,18 MB ZIP, 54 MB XML. Obsahuje 1 obec, 3 části obce, 3 KÚ, 30 ZSJ, 144 ulic, 6 739 stavebních objektů, 3 778 adresních míst a 26 965 parcel. ETag i Last-Modified jsou platné.
- **Nejde o důkaz vlastnictví.** Parcely nemají LV ani vlastníky.

### 2.3 NIPEZ – Registr veřejných zakázek
- Open data od 02/2024: `https://isvz.nipez.cz/sites/default/files/content/opendata-rvz/{VZ|DNS|SON|…}-{MM}-{RRRR}.zip`. Aktualizace probíhá k 5. dni v měsíci, ETag a 304 fungují.
- VZ-09-2026: 183 MB ZIP a 1,29 GB JSON (schéma 2.10.2). Vyžaduje **streamové zpracování**.
- **IČO 00304450 se v 09/2026 nevyskytuje.** „Vsetín“ se objevuje 1 021× u jiných zadavatelů, např. Okresního soudu. Zdrojem jsou zatím jen VVZ, NEN, Tender arena a TENDERMARKET. **Hypotéza:** město zadává přes nástroj, který RVZ nepublikuje. Ověřit profil zadavatele města.
- Synchronní a asynchronní API RVZ vyžaduje oprávnění podle RPP a pro tento účel se nehodí.

### 2.4 Veřejný rejstřík a ARES
- `dataor.justice.cz` je CKAN: `/api/3/action/package_show?id={forma}-actual-ostrava-{RRRR}` → `/api/file/…csv.gz|xml.gz`.
- **Subjekty z Vsetínska jsou u KS Ostrava** (ARES-VR: `soud: KSOS`), v souboru pro Brno nebyl nalezen žádný. `spolek-actual-ostrava-2026`: 14 801 subjektů, z toho 1 130 s „Vsetín“.
- Soubory nemají ETag ani Last-Modified, deduplikace proto jen přes SHA-256. IČO je bez nul (`536024`), normalizovat na 8 znaků.
- **ARES** (z cloudu dosažitelný): 38 IČO z `subjekty.json` → 37× 200. **60042354 (MŠ Trávníky 1218) vrací 404**, ač má platný kontrolní součet. Hypotéza: subjekt byl sloučen se ZŠ a MŠ Trávníky 1217 (60990449), neověřeno. Výstup: `data/entity/ares_overeni_2026-10-23.json`.
- **Sbírka listin:** oficiální strojové rozhraní jsem nenašel, hromadné stahování z or.justice.cz nedoporučuji.

### 2.5 MONITOR – Registr dotací
- Veřejná webová aplikace volá `/api/grants/local/search` a `/api/grants/state/search`. Tato API **nejsou v open data katalogu ani dokumentována**.
- Územní registr: Vsetín jako poskytovatel v roce 2026 (load 2608) → 107 příjemců, typy Transfer/Borrow. Jako příjemce figuruje ve 28 záznamech. Data pocházejí z FIN 2-12 M (sloupec Partner Fin), jsou kumulativní a **nejde o jednotlivá dotační rozhodnutí**.
- Státní registr: Vsetín jako příjemce má 101 záznamů za roky 2014–2026, včetně ID dotace, programu a poskytovatele (např. IROP: MVK Dolní náměstí, Cyklostezka Rokytenka).
- Doporučení: územní transfery brát **z open data FIN 2-12 M** (stejný zdroj, stabilní). U státního registru požádat MF o potvrzení podmínek užití API. Do té doby jen ruční nebo málo frekventované dotazy.
- Data obsahují i fyzické osoby, proto platí minimalizace (u FO neukládat jméno ani adresu bez právního titulu).

### 2.6 ČÚZK
- **REST API KN** (`api-kn.cuzk.gov.cz`) je zdarma po registraci (Identita občana nebo účet DP), ApiKey se posílá v hlavičce. Platí limit volání. API **neposkytuje osobní údaje** a údaje lze užít jen k účelům podle §1 odst. 2 zák. 256/2013 Sb. Klíč nesmí být na klientovi. → BLOKOVÁNO, dokud vlastník projektu nerozhodne o registraci.
- DP a WSDP jsou placené služby s údaji o vlastnících. Mimo rozsah.

## 3. UX / technická kontrola nasvsetin.cz (jen čtení, automaticky)
- Vyhovuje: `lang="cs"`, viewport, `<main>`, skip link, chybějící alt 0, odkazy bez názvu 0, pole bez labelu 0, konzole bez chyb.
- Ke zlepšení: 4 tabulky bez `<caption>` a bez `scope` (WCAG 1.3.1, doporučení). Ve stavech zdrojů chybí rozlišení *neintegrováno* × *ověřeno, čeká na implementaci*. Po nasazení doplnit stav podle `stav_zdroju_*.json`.
- Klávesnici, kontrast a čtečku jsem netestoval, vyžaduje ruční test.

## 4. Nevyřešené problémy
1. Bez přístupu na server nelze ověřit kód konektorů ani DB. Vše výše je ověření zdrojů, ne integrace.
2. Registr dotací stojí na nedokumentovaném API, podmínky užití potvrdit u MF.
3. Neznámý e-nástroj města pro zakázky (RVZ 09/2026 = 0 záznamů).
4. ČÚZK API KN čeká na registraci vlastníkem.
5. Nevysvětlený rozdíl 4134/5345 v konsolidaci.
6. IČO 60042354 není v ARES.
7. Push na GitHub z této relace nelze (neplatný token), změny jsou předány jako patch.

## 5. Kontrolní protokol

| Kontrola | Výsledek |
|---|---|
| Katalog MONITOR `/api/opendata/monitor` | 200, 76 297 B, 811 sad |
| FINM2026 08/2026 bez `.zip` | 404 |
| FINM2026 08/2026 `.zip` HEAD, poté `If-None-Match` | 200 / 304 |
| RSS MONITOR | 200; FIN 2-12 M 08/2026 publikováno 24. 9. 2026 (shodně s ETag mtime) |
| `/api/grants/local/search` provider=00304450 | 200, total 107 |
| `/api/grants/state/search` receiver=00304450 | 200, total 101 |
| VFR 20260930 OB 541630 | 200, 6 178 614 B, název obce „Vsetín“ |
| RVZ VZ-09-2026 HEAD, `If-None-Match` a `If-Modified-Since` | 200 / 304 / 304 |
| dataor CKAN `package_list` | 9 496 balíčků |
| ARES ×38 | 37×200, 1×404 |
| `tests/test_sync_core.py` | 4/4 OK (lokální mock server) |
| `tests/test_parse_monitor_finm.py` | 2/2 OK (vzorek reálných řádků) |
| Validita JSON ve `data/integrace`, `data/monitor` a `ares_overeni` | OK |

## Zdroje
- https://monitor.statnipokladna.gov.cz/datovy-katalog/open-data
- https://monitor.statnipokladna.gov.cz/registr-dotaci/uvod
- https://mf.gov.cz/cs/ministerstvo/media/tiskove-zpravy/2026/ministerstvo-financi-zprehlednuje-informace-o-dota-64833
- https://vdp.cuzk.gov.cz/vdp/ruian/vymennyformat
- https://isvz.nipez.cz/opendata/nova
- https://podpora.nipez.cz/cs/pravidla-pouziti-sluzeb-nipez/latest/registr-verejnych-zakazek
- https://dataor.justice.cz/
- https://ares.gov.cz/
- https://www.cuzk.gov.cz/aplikace-dp/zakladni-informace
- https://api-kn.cuzk.gov.cz/PodminkyUzivani
- https://nasvsetin.cz/#rc/sources
