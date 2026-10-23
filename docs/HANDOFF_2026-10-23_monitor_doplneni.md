# Předávací zpráva: doplnění MONITOR (Claude in Chrome), 23. 10. 2026

Navazuje na balík `integrace/` a `data/monitor/` (finm_rada, souhrn 2026/08). **Neduplikuji** řadu 2020–2025, kontrolu ZÚ ani registry dotací. Přidávám jen to, co v repozitáři chybělo.

## Nové
1. **Rekonciliace FIN × Územní registr** (`scripts/kontrola_fin_vs_uzemni_registr.py`). Rozdíl je 0,00 Kč. Údaj „107 příjemců“ znamená 107 řádků registru, tedy 106 subjektů: NA CESTĚ má dva řádky (transfer a zápůjčku 11 mil. Kč).
   - Pravidla, jak sestavit registr z FIN (pro konektor `monitor_finm`):
     - výdaje (`ci_type` 3) s partnerem a bez účelového znaku, bez položek 5341–5349,
     - vyloučit partnera 00000111 a položky 5363 a 5366,
     - zápůjčky (6422 a podobné) vést odděleně jako `Borrow`,
     - vratky = položka 2229 s partnerem.
   - Sloupec `prijato_od_partnera_vse_kz` obsahuje všechny příjmy od partnera včetně pokut (2212), nejen vratky.
2. **Transfery 2026 po obdobích** 02–08. Hodnoty jsou kumulativní a monotónní (žádný příjemce neklesá).
3. **VZZ a rozvaha 2025/2024** města a 14 PO. Kontroly prošly 30/30.
   - Indicie k ověření: ZŠ a MŠ Luh má náklady +59 % a aktiva 91,3 → 124,5 mil. Kč.
4. **RO 2026 × MONITOR na úrovni součtů.** Doplňuje existující kontrolu financování (8113/8115/8123).
   - Součty sedí přesně.
   - Paragrafy sedí 16/27. Největší rozdíly jsou 3613 (+850 000) a 3419 (+466 000).
   - Hypotéza: přesuny z rezervy nebo dotačních programů mimo zveřejněná RO.
5. **Příjemci mimo `subjekty.json`:** 91 subjektů s názvy z ARES. Jediná fyzická osoba je anonymizovaná.
6. **Watchlist:** návrh 10 PO podle položky 5331, k tomu 2 zaniklé nebo sloučené MŠ jako historické subjekty. Návrh čeká na schválení vlastníkem.

## Zjištění pro model
- ZŠ a MŠ Luh (60990406) a ZŠ a MŠ Ohrada 1876 (60990368) mají v ARES `stavZdrojeVr = NEEXISTUJICI`, nejsou tedy ve VR. Konektor `vr` je u nich nenajde, zdrojem musí být RES nebo rejstřík škol.
- Výnosy z transferů (B.IV) ve VZZ škol se nesmí sčítat s transfery z FIN (dvojí započtení).

## Otevřené
- Paragrafové rozdíly RO × MONITOR 2026 (viz bod 4).
- Stav MŠ Trávníky 1218 (60042354): ověřit v rejstříku škol a v usneseních ZM.
