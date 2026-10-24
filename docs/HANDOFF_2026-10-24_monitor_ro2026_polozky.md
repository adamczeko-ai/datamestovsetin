# Předávací zpráva: RO 2026 × MONITOR na úrovni paragraf/položka (24. 10. 2026)

Protokol `predani@1`. Navazuje na `scripts/kontrola_monitor_vs_ro2026.py`, kde se celkové součty shodují přesně a paragrafy jen 16/27.

## Nové
- `data/monitor/monitor_vs_ro2026_par_pol_2026-08.csv` obsahuje 172 kombinací paragraf/položka.
  - Každá má změnu podle MONITOR (`po změnách − schválený`, FIN 2-12 M 2026/08, ETag `6ab496d0-17be1a8`), změnu podle RO č. 1–15 (`data/rozpocet/2026`), rozdíl a kategorii.
  - Bez konsolidace 5341–5349 a bez třídy 8.
- `scripts/kontrola_monitor_vs_ro2026_polozky.py` (exit 0) ověřuje:
  - součet rozdílů = 0,00 Kč,
  - CSV odpovídá RO JSON (0 odchylek).

## Výsledek (Odvozeno)
| Kategorie | Položek | Rozdíl MONITOR − RO |
|---|---:|---:|
| shoda | 61 | 0 |
| rezerva (5901/6901) čerpaná mimo zveřejněná RO | 8 | −2 986 923,27 Kč |
| přesun mezi paragrafy / mimo zveřejněná RO | 75 | +2 714 923,27 Kč |
| přesun mezi položkami v rámci paragrafu | 28 | +272 000,00 Kč |

**Zjištění:** do 31. 8. 2026 bylo z rezerv (hlavně 6409/5901, dále 3113, 3419, 3792, 4329, 4339, 4349, 6115/5901) rozděleno přibližně **2,99 mil. Kč** do 75 položek jiných paragrafů. Šlo hlavně o drobné dotace (5222/5223), platy a provoz.
- Tyto změny **nejsou ve zveřejněných RO č. 1–15**, ale v účetnictví (MONITOR) jsou.
- Pravděpodobně jde o rozpočtové změny v kompetenci správců rozpočtu nebo o RO, která se nezveřejňují. **Jde o indicii, ne o zjištění pochybení.**
- Otázka k vysvětlení: kde se tyto změny schvalují a zveřejňují?

## Konkrétní nesoulady k vysvětlení (Indicie)
1. **3635 vs 3613, 850 000 Kč.** RO 7 (usnesení 24/24/ZM/2026, PDF s. 9) schvaluje „Oprava kanalizace v čp. 1356, pod MVK“ na ODPA **3635** (ORG 26135602). Ověřil jsem to přímo v PDF, parser je správně. MONITOR nemá v roce 2026 žádný řádek 3635 a stejná částka je navíc v ODPA **3613** (stejný objekt čp. 1356). Usnesení zastupitelstva tedy uvádí jiný paragraf, než podle kterého se účtuje.
2. **26 197 Kč (3113):** RO je vede jako 6351 (investiční příspěvek PO), MONITOR jako 5331 (neinvestiční).
3. **73 054 Kč:** RO 8 je dává na 5311/5011 (platy, městská policie), MONITOR na 4199/5410.
4. **6402/5364, +352 665,93 Kč:** vratky dotací ve finančním vypořádání nad rámec RO.

## Návrh integrace
- Konektor `integrace/sources/monitor_finm.py` už ukládá řádky FIN. Navrhuji přidat odvozenou tabulku `rozpocet_zmeny_monitor(obdobi, paragraf, polozka, zmena)` a pravidlo signálu **R-RO-1: „změna rozpočtu bez zveřejněného RO“**, které porovná MONITOR s `data/rozpocet/<rok>`.
- Akceptační hodnoty pro 2026/08: součet rozdílů 0,00; rezervy −2 986 923,27; 61 shod ze 172.
- Signály z bodů 1–4 patří do `data/analyzy/signaly.json`. Stavy edituje jen člověk.

## Otevřené
- Ověřit v pravidlech rozpočtového hospodaření města (usnesení 20/22/ZM/2025, zmocnění RM), jaké změny smí provádět správci rozpočtu bez RO a zda se zveřejňují.
