# Předávací zpráva: MONITOR, registry dotací, VR a test webu (23. 10. 2026, 07:10–08:40 SELČ)

## Ověření výchozího stavu
- Commit 60ec274 z předchozí relace na GitHubu **nebyl**. Rebasován na `origin/main` (6af1aae), konflikt v CHANGELOG vyřešen sloučením obou větví. Push opět nejde (neplatný `GH_TOKEN`), proto předávám jako patch.
- Jiné relace mezitím dokončily RO 2022–2024, ZÚ 2023–2025, zakázky z profilu (vhodne-uverejneni.cz) a kauzy K-001–K-003. Úkol A6 (RO 2024, ZÚ) jsem proto **neopakoval**.

## Hotovo

| Soubor | Obsah | Ověření |
|---|---|---|
| `data/monitor/finm_rada_2020_2025_vsetin.json` | FIN 2-12 M 12/2020–12/2025: rekapitulace po konsolidaci a financování | 2024 a 2025 = ZÚ **na haléř** (příjmy, výdaje, kapitálové výdaje, 8115 upravený) |
| `data/monitor/kontrola_RO_8115_monitor.json` | měsíční 8115 v MONITORu proti řadě RO 2025/2026 | 8× shoda, 3× rozdíl (viz níže) |
| `data/dotace/uzemni_registr_vsetin_poskytovatel_2026.csv` + `_souhrn.json` | 107 záznamů a 106 příjemců peněz od města (2026, k 31. 8.) | úplné stránkování; FO anonymizována |
| `data/dotace/uzemni_registr_vsetin_prijemce_2026.json` | 28 poskytovatelů peněz městu (Zlínský kraj 6,39 mil.) | součet obcí 281 500 = pol. 4121 v FINM 08/2026 |
| `data/dotace/statni_registr_vsetin_prijemce.csv` + `_souhrn.json` | 101 záznamů a 90 dotací státu městu 2014–2026 | úplné |
| `data/entity/vr_organy_mestske_spolecnosti_2026-10-23.json` | společníci a aktuální orgány 7 společností + TJ Zbrojovka | bez dat narození a adres |
| `scripts/monitor_rada_vsetin.py` | generátor řady a kontrola proti ZÚ | běží, výstup výše |
| `docs/TEST_WEBU_2026-10-23.md` | 20 kontrol B1, model B2, funkce B3, WCAG B4, škála B5 | – |
| `docs/ZADANI_CLAUDE_CODE_model_UI_2026-10-23.md` | Z1–Z9 s akceptačními hodnotami | – |

## Klíčová zjištění (fakt / indicie / hypotéza)
1. **Fakt:** MONITOR (tab. IV) a závěrečný účet 2024 a 2025 se shodují na haléř. Pro roky do 2025 je MONITOR spolehlivý zdroj „skutečnosti“.
2. **Fakt:** `pol_8115.skutecnost` v `zaverecny_ucet_2023_2025.json` obsahuje i krátkodobé operace řízení likvidity 8117/8118 (rozdíl +60 / −10 / −50 mil. Kč v letech 2023/2024/2025). Doporučuji pole přejmenovat nebo rozdělit. Do cizích dat jsem nezasahoval.
3. **Fakt:** A-2025-01 se v zaúčtovaných datech státní pokladny projevuje **už v 04/2025** (8115 po změnách 149 533 188,60 místo 150 190 284,54). Nezávislé potvrzení. **Hypotéza:** RO 4 bylo zaúčtováno s financováním 75 238 904,06 Kč.
4. **Fakt:** A-2025-02 (+2 000 v RO 15): MONITOR 09/2025 = 188 903 434,25. Překlep je ve zveřejněném PDF.
5. **Fakt:** RO 24/2025 končí na 207 352 071,31, MONITOR i ZÚ 207 352 097,86 (+26,55 Kč). Nevysvětleno, ověřit v PDF RO 24.
6. **Indicie:** město do 31. 8. 2026 převedlo Vsetínské sportovní a DK přesně 8/12 ročních kompenzací (C001, C002). Odpovídá měsíčním splátkám, nedokládá úhradu konkrétní smlouvy.
7. **Fakt:** 2026 – největší příjemci peněz města: TS města p.o. 90,0 mil., Z-Group bus 22,9 mil., TJ Zbrojovka 20,95 mil., ZŠ Luh 20,9 mil., knihovna 20,1 mil. Návratná výpomoc NA CESTĚ, z. s. 11 mil.
8. **Fakt:** Ve státním registru dotací 2014–2026 (příjemce město) **nejsou lávky**. Největší položky: MVK Dolní náměstí 40,7 mil., Cyklostezka Rokytenka 40,2 mil., Řemeslo má budoucnost 52,9 mil. (2018–2019), Revitalizace Kolonie 36,9 mil. (2015).
9. **Fakt:** IČO 60042354 (MŠ Trávníky 1218) je v MONITORu 2026 jen s vratkou 237 517,38 Kč, ARES vrací 404. **Hypotéza:** zrušena nebo sloučena v roce 2025/2026.

## Neprovedeno / blokováno
- **A4 RVZ 02/2024–08/2026:** jeden měsíc má ~183 MB ZIP a 1,3 GB JSON, celkem asi 5,5 GB. To je hromadné stahování s významnou zátěží, potřebuje schválení a patří na server (ijson). Profil zadavatele města je vhodne-uverejneni.cz (zjištěno jinou relací); jde o nástroj, který RVZ zatím nepublikuje. Hypotéza z auditu tím je **podpořena, ne prokázána**.
- **A2 transfery 2024–2025:** starý výkaz FIN 2-12 M (do 2025) nemá sloupec Partner Fin a registr vrací jen aktuální load. Historie transferů je jen ve „FINM208/207“ (bez partnera), nebo ji musí doplnit MF.
- WCAG ruční testy (klávesnice v grafech, zoom 200 %, 320 px, čtečka) – viz TEST_WEBU B4.
- Push na GitHub.

## Další fronta
1. Claude Code: Z1 (hodnoty smluv) a Z2 (transfery) – největší přínos za nejmenší práci.
2. Server: RVZ 2024–2026 streamově, filtr na IČO města a jeho organizací.
3. Ověřit +26,55 Kč v RO 24/2025 a přejmenovat pole 8115 v ZÚ JSON (vlastník dat ZÚ).
4. Lávka Vs-04-Bel: dohledat poskytovatele programové dotace (smlouva 39253570) a spárovat s Územním registrem (Zlínský kraj 6,39 mil.).
