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
