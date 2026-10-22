# Roadmapa funkcí VSETÍN OSINT: inspirace u podobných řešení

*Sestaveno 23. 10. 2026. Priorita: P1 = hned, P2 = další sprint, P3 = později.*

## Co dělají podobná řešení

| Řešení | Klíčové funkce | Co si převzít |
|---|---|---|
| **Hlídač státu** | propojení registru smluv s obchodním a insolvenčním rejstříkem, databáze osob (politici, sponzoři), K-Index, hlídání nových smluv e-mailem, API a MCP server | automatické párování akcí a usnesení se smlouvami, hlídací dotazy, MCP/API integrace |
| **CityVizor** (MF ČR / Otevřená města) | rozklikávací rozpočet až na faktury, plán vs. skutečnost, faktury ke stažení, vazba na registr smluv | vrstva „skutečnost“ (čerpání), faktury, plán vs. realita u každé akce |
| **Councilmatic** (Chicago, NYC) | sledování návrhu od předložení po schválení, profily zastupitelů, odběr novinek ke konkrétnímu bodu nebo osobě, kalendář jednání | časová osa akce (hotovo: `akce_timeline.json`), profily zastupitelů a hlasování, odběry |
| **zIndex** (Datlab) | hodnocení zadavatele: počet nabídek, koncentrace dodavatelů, nástroje podporující soutěž, rozhodnutí ÚOHS | skóre transparentnosti města podle vlastních pravidel |
| **OpenBudgets.eu / OpenSpending** | jednotný datový model rozpočtů, srovnání v čase a mezi obcemi | srovnání Vsetína s podobně velkými městy (Monitor státní pokladny) |

## Implementováno v této várce
- **P1, časová osa akcí** (`data/analyzy/akce_timeline.json`): 99 akcí podle kódu ORG, každá změna s RO, orgánem, usnesením a částkou. Obdoba „bill tracking“ z Councilmatic.
- **P1, signály k ověření** (`data/analyzy/red_flags.json`, `scripts/analyzy.py`): 7 pravidel, celkem 79 signálů (velká navýšení, opakované navyšování, investice schválené radou, nákupy nemovitostí, dotace subjektům, soudní spory, dofinancování příspěvkových organizací).
- **P1, přístupný prohlížeč dat** (`index.html`, připravený pro GitHub Pages):
  - karty Akce, Signály, Kauzy a Řádky RO s vyhledáváním
  - tmavý režim, ovládání klávesnicí, cíle pro klepnutí 44 px, bez vodorovného posunu na šířce 390 px
- **Párování se smlouvami (ručně):** kupní smlouva na Tribunu ověřena v registru smluv (Hlídač státu 34141081, 33 150 000 Kč).

## Další kroky
| P | Funkce | Zdroj dat | Proč |
|---|---|---|---|
| P1 | Automatické párování akcí a subjektů se smlouvami (podle IČO a klíčových slov) | Hlídač státu API (token) nebo smlouvy.gov.cz | propojí rozhodnutí → peníze → dodavatele |
| P1 | Vrstva „skutečnost“: čerpání akcí | Monitor státní pokladny (FIN 2-12 M), rozklikávací rozpočet města, ZÚ | plán vs. realita (cíl projektu) |
| P1 | Stav dokumentu: návrh / schváleno / upraveno | výpisy usnesení, balíčky materiálů ZM | zveřejněná RO nejsou vždy schválené znění |
| P2 | Profily zastupitelů a hlasování | zápisy ZM a videozáznamy | odpovědnost konkrétních lidí |
| P2 | Hlídací pes (RSS / e-mail) na nové RO, usnesení a smlouvy s vybranými IČO | složky webu města, registr smluv | upozornění na novinky |
| P2 | Skóre transparentnosti města (vlastní „zIndex“) | anomálie A-*, včasnost zveřejnění, prázdné ceny | měřitelný ukazatel v čase |
| P3 | Srovnání s městy 20–30 tis. obyvatel | Monitor státní pokladny | kontext a benchmark |
| P3 | Lávka a další pilotní akce jako „karta akce“ s fotkami a stavem | vlastní sběr | vazba na reálné výsledky |

## Doporučení pro WCAG 2.2 a UX (vlastní web)
- Každá tabulka má `<caption>` a `th scope`, čísla se zarovnávají vpravo (`tabular-nums`).
- Záložky splňují ARIA pattern tabs (šipky, `aria-selected`).
- Výsledky vyhledávání se ohlašují přes `aria-live`.
- Fokus je vždy viditelný (2.4.7, 2.4.11), cíle mají aspoň 24×24 px (2.5.8), zde dokonce 44 px.
- U každé částky je odkaz na zdrojový dokument (ověřitelnost) a je označeno, zda jde o návrh, nebo schválené znění.
