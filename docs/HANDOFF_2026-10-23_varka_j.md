# Předávací zpráva: várka j (autonomní), 23. 10. 2026, 3:45 SELČ

## OPRAVA k várce i
Smlouva na **stavbu lávky Vs-01-Bel existuje**: Mitrenga-stavby, spol. s r.o., 9,44 mil. Kč bez DPH (11,42 mil. s DPH), podepsána 23. 6. 2026 (HS 38483666). Dřívější fulltextové dotazy ji nenašly, protože název smlouvy neobsahuje označení lávky. Data jsou opravená.

## Veřejné zakázky (profil vhodne-uverejneni.cz/profil/00304450)
Profil eviduje 267 zakázek v plnění, 178 ukončených a **84 zrušených**.

| Zakázka | Předp. hodnota | Nabídek | Vítěz | Cena bez DPH | Poměr |
|---|---|---|---|---|---|
| Oprava lávky Lázky (design & build) | 12,0 mil. | **2** | Mitrenga-stavby | 9,44 mil. | 78,7 % |
| Kolumbárium | 46,0 mil. | 4 | [FO-004] | 38,78 mil. | 84,3 % |
| Hřiště Pod Pecníkem | 12,0 mil. | 3 | SPORT Construction | **11 999 917** | **99,9993 %** |
| VZT Městské lázně | 11,0 mil. | 3 | JASY Vsetín | 9,38 mil. | 85,3 % |
| Přednádražní prostor I.B | **257,6 mil.** | – | – | – | stále „vyhodnocování“ (lhůta 19. 2. 2024) |

## Nová zjištění
- **Lávka u průmyslovky (Vs-04-Bel):** v roce 2022 byl rozpočet 23 mil. Kč, v roce 2025 byla podepsána smlouva o dílo s **Mitrenga-stavby na 68,98 mil. Kč bez DPH (83,47 mil. s DPH)**. Cena je zhruba 3× vyšší než původní rozpočet. Mitrenga postaví obě lávky.
- **Hřiště Pod Pecníkem:** vítězná nabídka je o 82,71 Kč nižší než předpokládaná hodnota. To je běžný signál k ověření (únik informace o předpokládané hodnotě), ale samo o sobě nic nedokazuje.
- **Rozklikávací rozpočet** města je jen odkaz na Monitor MF. Data podle jednotlivých akcí (ORG) tam nejsou, takže vrstvu „skutečnost po akcích“ z něj sestavit nejde.
- Stránka **Střet zájmů** na webu města je **prázdná**.
- V přezkoumání hospodaření přibyla **Zpráva o ověření účetní závěrky 2025**, k vytěžení.

## Implementováno
- `data/zakazky/verejne_zakazky.json`
- Pravidla v analytice: R8 málo nabídek, R9 cena u předpokládané hodnoty, R10 nárůst ceny proti rozpočtu, R11 dlouho neukončená zakázka. Celkem 97 signálů.
- Prohlížeč dat: nová záložka **Zakázky a smlouvy**, odkazy na zdroje u signálů.
