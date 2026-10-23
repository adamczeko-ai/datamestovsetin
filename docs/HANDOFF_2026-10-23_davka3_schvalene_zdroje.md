# Předávací zpráva – dávka 3 (schválené objemové zdroje)

> **Poznámka k nahrání (23. 10. 2026, 11:30 SELČ):** do repa nahrána jen data na nových cestách. Balík `connectors/` a moje verze RO 2023/2024 nejsou nahrány – v repu je již `integrace/` a RO z jiné relace (křížová kontrola: `docs/OPRAVA_A-2023-03_a_krizova_kontrola_RO_2026-10-23.md`). Kompletní stav je v patchi `datamestovsetin_2026-10-23_davka5.patch`.


**Relace:** Claude in Chrome + sandbox, 23. 10. 2026, 07:15–07:45 SELČ
**Schválení:** správce 23. 10. 2026 (FIN 2010–2023, NIPEZ VZ, dataor, Rozvaha/VYKZZ)
**Přerušení:** po průchodu NIPEZ se prohlížeč dočasně odpojil; nálezy zůstaly v paměti stránky a po obnovení spojení (07:45) byly přeneseny.

## Výsledky

| Oblast | Stav | Soubor |
|---|---|---|
| FIN 2-12 M 2010–2023 (open data) | **hotovo, ověřeno** | `data/monitor/finm_vsetin_2010_2026.json` (nahrazuje `finm_vsetin_2024_2026.json`) |
| Časová řada UI × open data | **shoda na haléř 2010–2025** | `data/monitor/rozpocet_rada_2010_2026.json` |
| Rozvaha + VYKZZ 12/2025 | **hotovo, ověřeno** – ukazatele 16 subjektů = UI | `data/monitor/ukazatele_organizaci_mesta_2024_2025.json` |
| dataor – účasti města | **hotovo** – 8 subjektů, ověřeno ARES VR | `data/entity/spolecnosti_mesta.json` |
| NIPEZ VZ 02/2024–09/2026 | **hotovo** – 163 nálezů → 83 unikátních zakázek (přeneseno po obnovení spojení) | `data/zakazky/nipez_vz_okruh_mesta_2024_2026.json` |
| Konektory | rozšířeny, **14/14 testů OK** | `connectors/` |

## Ověřená fakta
1. **Rozpočet 2010–2023:** pro každý rok P + F = V (0,00) ve všech stupních; konsolidovaná skutečnost (bez pol. 534x) se shoduje s UI MONITOR na haléř. Do r. 2012 je IČO ve zdroji desetimístné (`0000304450`).
2. **Dluhová služba:** dlouhodobé úvěry (8123/8124) byly v letech 2010–2016 jen v řádu jednotek mil. Kč ročně (splátky ~0,6–2,4 mil.); další čerpání úvěru je až v roce 2026 (2,44 mil. Kč k 08/2026, rozpočet 107,5 mil.).
3. **Krátkodobé operace (8117/8118)** se objevují od roku 2022: 2022 +25/−125, 2023 +60/−120, 2024 +125/−115, 2025 +580/−530, 2026 +114,6/−250 mil. Kč. Kumulativně jsou záporné, proto jde pravděpodobně o operace řízení likvidity, ne o dluh (**indicie**, metodika neověřena).
4. **Účasti města (VR, platné zápisy KS Ostrava):**
   - Městské lesy Vsetín, s. r. o. (47678054) – 100 %, ZK 5 mil.
   - Technické služby Vsetín, s.r.o. (26782596) – 100 %, ZK 34,032 mil.
   - Vsetínská sportovní, s.r.o. (28593987) – 100 %, ZK 5 mil.
   - Dům kultury Vsetín, spol. s r. o. (47972114) – 100 %, ZK 1,806 mil.
   - DN Vsetín s.r.o. (19690711) – 100 %, ZK 1 000 Kč, zapsáno 5. 9. 2023
   - o.p.s. se zakladatelem městem: Azylový dům pro ženy a matky s dětmi (25909614), Společnost pro komunitní práci Vsetín „v likvidaci“ (26838354)
   - nepřímo: VALAŠSKÁ PALAČINKÁRNA s.r.o. (08012733) – 1/3 Dům kultury Vsetín, zbytek fyzické osoby
5. **Zaniklé MŠ** (60609231, 60609249, 60042354) ještě vykazují rozvahu 12/2025 (VH 0) → zánik pravděpodobně v roce 2026.
6. **NIPEZ:** 2024 je zveřejněn jen jako roční soubor `VZ-2024_rocni.zip`; měsíční názvy vrací 404. Jediný přenesený nález: část zakázky RVZ2600120973/011 (svoz odpadu, obec Valašská Senice, hlavní zadavatel Sdružení obcí 62334743) – dodavatelem je **Technické služby Vsetín, s.r.o.** (městská společnost).

## NIPEZ – zakázky okruhu města (83)
- **53 zakázek** zadalo město nebo jeho p.o., **28** obsahuje městskou firmu jako účastníka či dodavatele (Technické služby Vsetín 25×, Dům kultury 3×, DN Vsetín 3×).
- **Lávka Vs-01-Bel (pilot):** zakázka RVZ2600110987, smlouva 23. 6. 2026 s **Mitrenga-stavby, spol. s r.o.** za **9 440 000 Kč bez DPH**; podány **2 nabídky** (oprava v dávce 5). Doplněno do `data/rozpocet/2026/vazba_lavka_Vs-01-Bel.json`.
- Další velké smlouvy města (bez DPH): Přednádražní prostor I.B (154,48 mil., sdružení EUROVIA + SMO + KKS, zadavatel s ŘSZK), Lávka u Průmyslovky II (68,98 mil., Mitrenga-stavby), stavební úpravy MVK a TIC (42,62 mil., Metrostav CZ), střechy a FVE (26,41 mil., H & B delta).
- ~~U 40 ze 41 zakázek … 1 účastník~~ – **opraveno v dávce 5**: RVZ u smlouvy uvádí jen vybraného dodavatele; skutečné počty nabídek (pole podane_nabidky_nebo_zadosti_o_ucast) mají medián 3, jedinou nabídku má 9 ze 40 soutěží města.

## Indicie / k ověření
- **DN Vsetín s.r.o.** – nová městská společnost (2023) se ZK 1 000 Kč; účel a činnost nezjištěny.
- U NIPEZ se nálezy týkají i **městských firem jako dodavatelů** – po serverovém průchodu rozlišit roli (zadavatel × dodavatel).

## Kontrolní protokol

| Kontrola | Výsledek |
|---|---|
| FIN 2010–2023: P+F−V | 0,00 (14/14) |
| FIN 2010–2023: konsolidace × UI | 0,00 (14/14) |
| Součet položek financování = F | 0,00 (14/14) |
| Rozvaha/VYKZZ × UI (aktiva, cizí zdroje, VH, náklady, výnosy) | shoda 16/16 |
| dataor nálezy × ARES VR | 8/8 potvrzeno |
| NIPEZ průchod | 25 souborů, 0 chyb, 163 nálezů; přenos 1/163 |
| Unit testy | 14/14 |

## Nevyřešené
1. **NIPEZ** – pravidelný běh na serveru (`connectors/nipez_rvz.py`); ověřit počty nabídek v profilu zadavatele a doplnit plné názvy zakázek.
2. Konsolidace příjmů 08/2026 v UI (rozdíl 140 287 460 Kč) – metodika.
3. dataor `zaj_sdr_po`, `spol_pod` – soubory nejdou dekomprimovat.
4. Push na GitHub – repozitář není v autorizovaných zdrojích relace (403).

## Doporučený další krok
Spustit zadání pro Claude Code (`docs/ZADANI_CLAUDE_CODE_integrace_2026-10-23.md`) v dev – nejprve `nipez_rvz` (dokončení dávky 3) a `monitor_finm` (celá řada 2010–2026 pravidelně).
