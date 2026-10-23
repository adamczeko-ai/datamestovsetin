# Oprava anomálie A-2023-03 a křížová kontrola RO 2023/2024

**Relace:** Claude in Chrome, 23. 10. 2026, 11:30 SELČ – nezávislé vytěžení RO 2023 a 2024 z PDF (jiný parser, párování podle souřadnic).

## 1. A-2023-03 je chyba parseru, ne nesoulad ve zdroji
- **Tvrzení v repu:** RO 16/2023 je nevyrovnané o 202 922,10 Kč (příjmy +36 043, výdaje +238 965,10).
- **Ověřený fakt (PDF RO 16/2023, id_dokumenty 555796, str. 3):** v tabulce PŘÍJMY je řádek
  `3639 2322 | 0,00 | 202 922,10 | 202 922,10 | Pojistné plnění` – řádek **bez ORJ**, který dřívější parser nezachytil.
- „Celkem PŘÍJMY“ v PDF = **238 965,10 Kč** = „Celkem VÝDAJE“ → **RO 16/2023 je vyrovnané**.
- Výdaj 3613/5171 +202 922,10 (opravy po škodních událostech) je tedy krytý pojistným plněním.
- **Dopad:** opravit `data/rozpocet/2023/rozpoctova_opatreni_2023.json` (anomálie A-2023-03, RO 16 – doplnit řádek P 3639/2322), `rozpoctova_opatreni_2023_radky.csv`, `data/rozpocet/rozpoctova_opatreni_2023-2026_radky.csv`, `data/analyzy/signaly.json` (2 výskyty), `docs/HANDOFF_2026-10-23_varka_h.md`.
- Hypotéza o krytí z rezervy 6402/5901 (−200 000 Kč mezi RO 10 a RO 20) zůstává samostatnou otázkou – s RO 16 nesouvisí.

## 2. Drobnost RO 5/2023
- Řádek `5311 6125 0010 | 1 000 000,00 | (−94 592 / +94 592) | 1 000 000,00` obsahuje dvě dílčí změny v jednom řádku (čistá změna 0). Repo řádek nemá; na součty vliv nemá. Doporučení: doplnit se změnou 0 a poznámkou.

## 3. Křížová kontrola (nezávislé vytěžení × repo)
| Rok | RO | Řádky (já / repo) | Bilance P/V/F | Výsledek |
|---|---|---|---|---|
| 2024 | 22 | 406 / 406 | shoda ve všech 22 RO | **nezávisle potvrzeno** |
| 2023 | 22 | 473 / 471 | shoda kromě RO 16 (viz výše) | rozdíl jen RO 5 (0 Kč) a RO 16 |

Moje verze dat je v patchi `datamestovsetin_2026-10-23_davka5.patch` (`data/rozpocet/2023`, `/2024`), do repa jsem ji záměrně nenahrál, abych nepřepsal práci jiné relace.
