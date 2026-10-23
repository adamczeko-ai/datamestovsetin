# datamestovsetin: data projektu VSETÍN OSINT

Ověřitelná paměť rozhodnutí města Vsetín: **rozhodnutí → peníze → výsledky**. Vše je vytěženo z veřejných dokumentů na mestovsetin.cz a v registru smluv. Každý záznam odkazuje na zdroj.

**Prohlížeč dat:** `index.html` (zapněte GitHub Pages: Settings → Pages → Branch `main` / root).

| Složka | Obsah |
|---|---|
| `data/rozpocet/` | schválené rozpočty 2001–2026 (index), rozpočtová opatření 2023–2026 (JSON + CSV), anomálie |
| `data/zaverecny_ucet/` | ZÚ a přezkoumání hospodaření 2023–2025, rekonciliace s RO |
| `data/usneseni/` | vazby usnesení ZM na RO, index výpisů a balíčků ZM |
| `data/kauzy/` | K-001 spory na ochranu osobnosti, K-002 Tribuna Na Ohradě |
| `data/entity/` | registr subjektů (IČO) ověřený v ARES (`ares_overeni.json`) |
| `data/smlouvy/` | párování IČO se smlouvami v registru smluv (`parovani_ico.json`), párování akcí, úvěr |
| `data/analyzy/` | časová osa akcí, signály k ověření |
| `scripts/` | `validate_ro.py <rok>`, `analyzy.py`, `validate_schemas.py`, `ares_overeni.py` |
| `docs/` | předávací zprávy, roadmapa |

**Metoda:** PDF se čtou v prohlížeči (pdf.js), tabulky parsuje regex a výsledek prochází validací (počty řádků, součty P + F = V, aritmetika řádků, návaznost rezerv) a rekonciliací se závěrečným účtem.

**Upozornění:** signály a anomálie slouží k prioritizaci ověřování, nejsou zjištěním pochybení.
