# Předávací zpráva – Rozpočet a rozpočtová opatření 2026

**Relace:** Claude (Chrome), 22. 10. 2026 večer (SELČ)
**Zdroj:** mestovsetin.cz → Hospodaření města → Rozpočet města Vsetín (ds-1010) → 2026 – Rozpočtová opatření (ds-19928)

## Co je hotové

| Soubor | Obsah | Ověření |
|---|---|---|
| `data/rozpocet/index_schvalene_rozpocty.json` | Soupis schválených rozpočtů za roky 2001–2026: 26 dokumentů s URL a `id_dokumenty`, k tomu fronta dalších složek | ručně proti DOM |
| `data/rozpocet/2026/rozpoctova_opatreni_2026.json` | RO č. 1–18/2026: orgán, datum, usnesení, hlavní body, bilance a 378 rozpočtových řádků | viz níže |
| `data/rozpocet/2026/rozpoctova_opatreni_2026_radky.csv` | stejné řádky jako plochá tabulka | — |
| `data/entity/subjekty_z_ro2026.json` | 26 subjektů s IČO uvedeným v textu RO | neověřeno v ARES |
| `data/rozpocet/2026/vazba_lavka_Vs-01-Bel.json` | časová osa lávky Vs-01-Bel v Lázkách: stav → nabídka → rozhodnutí → peníze | — |

**Kontroly dat (všechny prošly):** počet řádků na RO, P + F = V pro každé RO, pred + změna = po pro každý řádek a souvislá návaznost rezerv (6409) i financování (81xx) přes všech 18 RO.

## Hlavní zjištění

- **Investiční rezerva** ORG 10000004 klesla z 70,0 mil. na 16,5 mil. Kč a **neinvestiční rezerva** ORG 10000002 z 28,0 mil. na 4,2 mil. Kč.
- **Úvěr:** v pol. 8123 je 0 → 207,5 mil. Kč. RO 12 (ZM) přidalo 107,5 mil. Kč a RO 17 (ZM) dalších 100 mil. Kč místo stejné částky z pol. 8113.
- **Největší navýšení v RO 12 (ZM, 22. 6. 2026):** Sportovní areál Ohrada +47 mil., FVE ZŠ Ohrada +35,3 mil., kolumbárium +25,2 mil. a oprava lávky Vs-01-Bel +12,8 mil. Kč.
- **TJ Zbrojovka Vsetín, z.s.:** dotace na tenisovou halu 20 mil. Kč (RO 7), později navýšená na 22,5 mil. Kč (RO 17).
- **Nákupy nemovitostí:** pozemky a „hospoda U Marka“ od ZETEX, spol. s r.o. za 9,0 mil. Kč (RO 9), garáže a pozemky Velký Skalník v e-aukci za 4,0 mil. Kč (RO 17) a kauce na dražbu 400 tis. Kč (RO 16).
- **Lávka (pilot):** diagnostika 550 tis. Kč (ZM 8/23/ZM/2026), stavební práce 12,8 mil. Kč (ZM 24,38/26/ZM/2026).

## Na co si dát pozor

- RO 4 uvádí usnesení `15/89/R/2026`, zřejmě jde o překlep ve zdroji.
- Význam ORJ 0010, 0017 a 0018 jsem odvodil z kontextu.
- Popisy řádků jsou mírně normalizované. Čísla jsou beze změny.

## Další krok (fronta)

1. RO 2025 (ds-19876) a starší ročníky, stejnou metodou.
2. Závěrečný účet (ds-1076): skutečné čerpání proti RO.
3. Ověření IČO v ARES, propojení s registrem smluv (lávka, Sportovní areál Ohrada, ZETEX).
4. Usnesení RM/ZM, na která RO odkazují: doplnit plné texty.

## UX / WCAG – mestovsetin.cz (pro referenci, nikoli náš web)

- Tři odkazy bez přístupného názvu (4.1.2 / 2.4.4).
- Seznam rozpočtů je rozdělený do dvou struktur, data u let 2020–2026 chybí (1.3.1).
- Odkaz na rozpočet 2004 vede na legacy doménu vismo.obce.cz.
- **Doporučení pro náš web:** u každého dokumentu zobrazovat orgán, datum a číslo usnesení jako strukturovaná metadata (`<dl>`), ne jen text odkazu.

## Metoda (reprodukovatelnost)

PDF jsem stáhl v kontextu stránky mestovsetin.cz pomocí `fetch()` a text extrahoval přes pdf.js 4.4.168. Řádky tabulek parsuje regex `ODPA POL [ORG] ORJ pred zmena po popis`, kde ORJ = `00\d\d`. Cloudový sandbox na mestovsetin.cz přímo nedosáhne (proxy 403), proto extrakce probíhá v prohlížeči.
