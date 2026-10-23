# Changelog – data VSETÍN OSINT

## 2026-10-22
- Přidán soupis schválených rozpočtů 2001–2026 (ds-1010).
- Přidána rozpočtová opatření 2026 č. 1–18 (378 řádků, validováno).
- Přidán registr subjektů z RO 2026 (26 IČO, neověřeno v ARES).
- Přidána vazba Lávka Vs-01-Bel: rozhodnutí → peníze.

## 2026-10-22 (2. várka)
- Přidána rozpočtová opatření 2025 č. 1–24 (411 řádků, validováno) + 4 anomálie ve zdroji.
- Registr subjektů sloučen do `data/entity/subjekty.json` (38 subjektů, výskyty 2025/2026).
- Vazba Lávka doplněna o další lávky z rozpočtu 2025.

## 2026-10-22 (3. várka)
- RO 2024 č. 1–22 (406 řádků, validováno) + 4 anomálie.
- Nová složka `data/kauzy/`: K-001 spory na ochranu osobnosti (5,01 mil. Kč v 2024).
- Souhrnné CSV RO 2024–2026; obecný validátor `scripts/validate_ro.py`.
- Registr subjektů: 41 subjektů + osoby z veřejných dokumentů (příjemci podpory).

## 2026-10-22 (4. várka)
- Závěrečný účet + přezkoumání hospodaření 2024 a 2025; rekonciliace RO vs. ZÚ.
- Anomálie A-2025-01 a A-2024-01 potvrzeny.

## 2026-10-22 (6. várka)
- Kauza K-002: nabytí Tribuny na Ohradě od TJ MEZ (33,15 mil. Kč; cena v materiálech pro ZM nevyplněná).
- Opraveno vysvětlení A-2025-01: úprava bodu 5 rozdíl nevysvětluje (zůstává otevřené).
- Index balíčků materiálů ZM 2025–2026 (ZIP).

## 2026-10-23 (7. várka – autonomní)
- Analytika: časová osa 99 akcí, 79 signálů k ověření (scripts/analyzy.py).
- Přístupný prohlížeč dat index.html (GitHub Pages).
- K-002 doplněna o smlouvy z registru (kupní smlouva 33,15 mil., historie dotací TJ MEZ 2016–2026).
- README, roadmapa funkcí podle Hlídače státu, CityVizoru, Councilmaticu a zIndexu.

## 2026-10-23 (8. várka – autonomní)
- RO 2023 (22 RO, 471 řádků) + ZÚ 2023, rekonciliace; chyba v Tabulce 1 ZÚ 2023.
- Párování 6 akcí se smlouvami (Hlídač státu); vazba dárce→dodavatel H & B delta.
- K-001 +745 tis. (2023). Analytika a prohlížeč rozšířeny o 2023.

## 2026-10-23 (9. várka – autonomní)
- Smlouvy: DN Vsetín s.r.o., AERV o.p.s., FC Vsetín (Sportovní areál Ohrada), kolumbárium – IČO, hodnoty, schvalovatelé.
- RO 2022 – jen narativní body (zdroj bez tabulek), anomálie A-2022-01/02.

## 2026-10-23 (10. várka – autonomní)
- Veřejné zakázky z profilu zadavatele; smlouva na stavbu lávky Vs-01-Bel nalezena (oprava); Vs-04-Bel 83,47 mil.
- Pravidla R8–R11, záložka Zakázky a smlouvy v prohlížeči.

## 2026-10-23 (11. várka – autonomní, zkrácená)
- K-003 lávka Vs-04-Bel: SoD TM Stav 19,48 mil. (2022) → narovnání 2,17 mil. (2023) → SoD Mitrenga 68,98 mil. (2025).
- Přednádražní prostor I.B: smlouva EUROVIA+SMO 169,16 mil. (2024) + dodatky 9,0 mil.; profil zadavatele neaktualizován.
- Zpráva o ověření účetní závěrky 2025 je sken bez textové vrstvy (25 str.) – nevytěženo.

## 2026-10-23 (12. várka – autonomní)
- 80 zrušených VZ (2013–2026, předp. hodnoty celkem 377,9 mil. Kč); opakovaná zrušení (Senior taxi 6×); pravidlo R12.
- K-003: zrušená VZ na lávku Vs-04-Bel (58 mil., 2025) před SoD 68,98 mil.
- Audit účetní závěrky 2025 (AUDIT TEAM, s.r.o.) – výrok bez výhrad (OCR skenu).

## 2026-10-23 (13. várka – autonomní)
- K-003: VZ I (58 mil., 4 nabídky, zrušena) → VZ II (72 mil., 6 nabídek, Mitrenga 68,98 mil.).
- Senior taxi: přehled smluv 2018–2026; svoz odpadu – Technické služby Vsetín, s.r.o.
- JSON Schema (data/schema/) + scripts/validate_schemas.py – všechna data validní.

## 2026-10-23 (várka n)
- K-003: písemná zpráva VZ I (MUVS 90996/2025) – nabídky 71,4–79,5 mil. bez DPH, zrušení 10. 7. 2025 dle § 127/2 d) (vše nad max. cenou 58 mil.; nejasná technická kvalifikace). Mitrenga ve VZ II o 3,35 % níž.
- Senior taxi: 38999306 = Dodatek č. 2 (D2 0542 2025, 31. 7. 2026) – prodloužení po zrušených VZ 2026.
- Odpad: hlavní smlouva 695/1S/2022 (HS 22831685) s Technickými službami Vsetín, s.r.o. (IČO 26782596); VZ otevřené řízení, předp. 138,6 mil./48 měs.; registr 28,3 mil. bez DPH; dodatky 1 a 4.
## 2026-10-23
- Audit 7 zdrojů pro integraci (`docs/AUDIT_INTEGRACI_2026-10-23.md`, `data/integrace/stav_zdroju_2026-10-23.json`).
- Založena evidence stažení (`data/integrace/evidence_stazeni.json`).
- MONITOR FIN 2-12 M 08/2026 – souhrn Vsetína a křížová kontrola s RO 2026 (`data/monitor/`).
- Ověření 38 IČO v ARES (`data/entity/ares_overeni_2026-10-23.json`): 37 OK, 60042354 nenalezeno.
- Prototyp idempotentního stahování `scripts/sync/` + testy `tests/` (6/6 OK, mock).
- Zadání pro Claude Code (`docs/ZADANI_CLAUDE_CODE_integrace_2026-10-23.md`).

## 2026-10-23 (MONITOR, registry dotací, VR, test webu)
- MONITOR FIN 2-12 M 2020–2025: rekapitulace a financování; 2024/2025 = ZÚ na haléř (`data/monitor/finm_rada_2020_2025_vsetin.json`).
- Měsíční 8115 vs RO 2025/2026: MONITOR nezávisle potvrzuje A-2025-01 (od 04/2025) a A-2025-02; nový drobný rozdíl +26,55 Kč u RO 24/2025 (`data/monitor/kontrola_RO_8115_monitor.json`).
- ZÚ JSON: `pol_8115.skutecnost` zahrnuje 8117/8118 (rozdíl +60/−10/−50 mil.) – k opravě vlastníkem dat.
- Registry dotací: územní (107 příjemců od města, 28 poskytovatelů městu) a státní (101 záznamů 2014–2026) → `data/dotace/`.
- ARES-VR: společníci a aktuální orgány městských společností (minimalizováno) → `data/entity/vr_organy_mestske_spolecnosti_2026-10-23.json`.
- Test webu nasvsetin.cz (20 kontrol, model, funkce, WCAG) → `docs/TEST_WEBU_2026-10-23.md`; zadání Z1–Z9 → `docs/ZADANI_CLAUDE_CODE_model_UI_2026-10-23.md`.

## 2026-10-23 (úvěr ČSOB, oprava hodnot registru, K-003)
- Řetězec úvěrového rámce 500 mil. Kč ČSOB: usnesení 25/24 a 23/26/ZM/2026 → smlouva 38540900 (splatnost 2049, splátky od 2030) → RO 12/17 → MONITOR čerpání 2,44 mil. k 31. 8. (`data/smlouvy/uver_CSOB_2026.json`).
- Ověření hodnot 215 verzí registru „nezjištěno“: 149 má hodnotu vč. DPH (`data/smlouvy/oprava_hodnot_registru_2026-10-23.json`).
- K-003: dotace Zlínského kraje 2,007 mil. (max. 5 % z CZV 40,16 mil., výplata po 11/2027) (`data/kauzy/doplneni/K-003_doplneni_dotace_ZK_2026-10-23.json`).
- Nová anomálie A-2025-05: +26,55 Kč v 8115 mezi zveřejněnými RO 2025 a ZÚ/MONITOR.

## 2026-10-23 (balík integrace/)
- `integrace/` – konektory MONITOR FIN 2-12 M (HTTP Range), RÚIAN VFR, RVZ (proudově), ARES-VR, registr smluv (XML), Registr dotací (vypnuto bez povolení); SQLite + evidence `sync_ledger`/`sync_run`; CLI `python -m integrace`.
- Testy `tests/test_integrace.py`: 12 offline OK + 2 živé (ARES, registr smluv) OK.
- Runbook a akceptační hodnoty: `docs/INTEGRACE_NASAZENI.md`.

## 2026-10-23 (vrstva nesouladů – varianta A, PR feature/ai-nesoulady)
- Signály v2 (`data/analyzy/signaly.json`, schéma signaly@2): stabilní ID, stavy ověření (`signaly_stavy.json`, edituje jen člověk), důkazní řetězec; migrace 100 signálů red_flags@1 + 15 anomálií bez ztráty dat.
- Pravidla R13–R16 (`scripts/pravidla_nesoulady.py`): kumulace dodatků (§ 222), těsně pod limitem VZMR / dělení, zrušená VZ → prodloužení, cenový rozdíl návrh/usnesení/smlouva/rozpočet; limity se zdroji v `pravidla_konfigurace.json`.
- LLM vrstva: prompt `ai/PROMPT_nesoulady.md`, kontrola doslovných citací `scripts/kontrola_nesouladu_llm.py`; slepý test K-002/K-003 jádro 5/7, 0 falešných.
- Plánovaná úloha (varianta A): `ai/ULOHA_planovana.md`, architektura A/B `docs/AI_VARIANTA_A.md`.

## 2026-10-23 (doplnění MONITOR – Claude in Chrome)
- Rekonciliace transferů města 2026/08: FIN 2-12 M × Územní registr – **0,00 Kč rozdíl** (325 850 645,01 Kč; 106 příjemců). Registr nezahrnuje technický kód 00000111, sankce GFŘ (5363) a pol. 5366 u Zlínského kraje; NA CESTĚ má v registru Transfer 239 300 + zápůjčku 11 mil. (`scripts/kontrola_fin_vs_uzemni_registr.py`).
- Transfery 2026 po obdobích 02–08 (`data/monitor/monitor_finm_vsetin_transfery_2026_obdobi.csv`).
- Účetní výkazy 2025/2024 (VZZ, rozvaha) města a 14 PO, vnitřní kontroly 30/30 (`data/monitor/monitor_vzz_…`, `monitor_rozvaha_…`).
- RO 2026 (č. 1–15) × MONITOR 2026/08: příjmy 44 118 311 a výdaje 185 477 256 Kč – přesná shoda; paragrafy 16/27 (`scripts/kontrola_monitor_vs_ro2026.py`).
- 91 příjemců transferů mimo `subjekty.json` s názvy z ARES; návrh rozšíření watchlistu (10 škol a školek podle pol. 5331).
- MŠ Ohrada 1879 (60609249) zanikla 23. 1. 2026 (ARES RES); 60042354 = MŠ Trávníky 1218 (název z registru, ARES nezná) – jen vratka 237 517,38 Kč.

## 2026-10-23 (várka o – ověření subjektů v ARES)
- `scripts/ares_overeni.py` + `data/entity/ares_overeni.json`: 74 IČO (rozšiřuje `ares_overeni_2026-10-23.json` s 38 IČO), 72 ověřeno, 0 chybných kontrolních číslic; schéma + validace.
- `subjekty.json`: blok `ares` u všech subjektů s IČO; doplněna IČO Damostis (23287152) a MUNIPOLIS (29198950).
- AERV o.p.s. (zakladatel město) zrušena k 31. 12. 2023, vymazána z OR 18. 12. 2024 – souvislost s narovnáním 3,85 mil. a vkladem 3,6 mil. (2023) zapsána k ověření.
- MŠ Trávníky 1218 (IČO 60042354 dle RO 11/2025) v ARES neexistuje – k ověření.

## 2026-10-23 (texty dokumentů – schváleno pro dev)
- `integrace/sources/dokumenty.py` + CLI `python -m integrace dokumenty`: stažení dokumentů města (PDF/HTML/ZIP), text po stranách do `raw/texty/<sha256>/p<N>.txt` + `meta.json`, tabulka `dokument_text`; skeny označeny `textova_vrstva: false` (bez OCR).
- `scripts/seznam_dokumentu.py` → `data/integrace/dokumenty_seznam.txt` (158 URL z dat repa).
- Testy `tests/test_dokumenty.py` (7, offline); ověřeno na reálné příloze registru smluv (kupní smlouva Tribuna): SHA-256 = hash uvedený registrem, 13/13 stran s textem.
- Zadání pro Claude Code: `docs/ZADANI_CLAUDE_CODE_texty_dokumentu_2026-10-23.md`.
- Revize stavů A-2023-01/A-2024-01 (potvrzena existence nesouladu, výše se liší o 5 514,00 / 34 012,00 Kč) a A-2025-01 (potvrzeno včetně výše).

## 2026-10-23 (várka p – párování IČO se smlouvami)
- `data/smlouvy/parovani_ico.json`: 73 ověřených IČO × registr smluv (obousměrně) → 60 IČO, 767 smluv; součty, dodatky, dary, největší smlouvy; skript `scripts/registr_smluv_parovani_ico.js`; schéma + validace.
- Signály P-01 (dary 4 dodavatelů projektu MVK, smlouvy 0781–0784 2025), P-02 (AERV: vklad 3,6 mil. 10 dní před zrušením), P-03 (podíl dodatků Martin Urban, TM Stav).
- K-003: 39830353 = Dodatek č. 1 k SoD Vs-04-Bel, +641 950,51 Kč bez DPH, cena díla 69,63 mil. bez DPH.

## 2026-10-23 (várka q – kauza K-004 AERV)
- `data/kauzy/K-004_AERV_zruseni.json`: řetězec dohoda 2012 → narovnání DPH 3 848 880 Kč (= 21 % z 18 328 000) → zrušení (usn. 10/9/ZM/2023) → vklad 3,6 mil. na likvidaci (usn. 1/10/ZM/2023) → převod likvidačního zůstatku (2024) → výmaz.
- Signál P-02 „zčásti vysvětleno“; otevřené: výše likvidačního zůstatku.

## 2026-10-23 (kontrola konzistence dat, větev claude/auto-konzistence-2026-10-23)
- `scripts/kontrola_konzistence.py` → `data/analyzy/konzistence.json` (schéma `konzistence.schema.json`): K1 RO JSON × CSV × souhrnné CSV, K2 bilance a aritmetika RO, K3 subjekty × ARES, K4 kontrolní číslice IČO, K5 datum RO × index zasedání ZM/RM, K6 FO jménem v kurátorovaných datech. Zdrojová data se nemění; rozpor = obě hodnoty se zdrojem, stav „ke_kontrole“ (stav od člověka se zachová).
- Výsledek 23. 10. 2026: K1–K3, K5 bez rozporu (K5 porovnala 35 RO); K4 2× (zástupná IČO 00000000, 00000111); K6 6× (3 IČO FO jménem v `parovani_ico.json`, `nipez_vz_okruh_mesta_2024_2026.json`, `verejne_zakazky.json`).
- Kontrola konzistence rozšířena o K7–K13 (`scripts/kontrola_konzistence_krizova.py`): odvozené soubory × přegenerování, částky téže smlouvy napříč soubory, odkazy a JSON pointery, osiřelé stavy signálů a ID anomálií, data a časové osy kauz, ZÚ × MONITOR, duplicitní ID.
