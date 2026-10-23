# Předávací zpráva: úvěr ČSOB, hodnoty registru smluv, K-003 (23. 10. 2026, 08:45–09:50 SELČ)

## Hotovo
| Soubor | Obsah |
|---|---|
| `data/smlouvy/uver_CSOB_2026.json` | Řetězec: závazek úvěrového financování FVE ZŠ Ohrada 32,88 mil. (25/24/ZM/2026) → úvěrový rámec 500 mil. ČSOB (23/26/ZM/2026, 22. 6.) → smlouva 26. 6. 2026 (3M PRIBOR + 0,001 %, čerpání do 2029, splátky 6,25 mil./čtvrtletí 2030–2049, nezajištěno) → RO 12 (107,5 mil.) a RO 17 (207,5 mil.) → MONITOR: k 31. 8. 2026 vyčerpáno 2 439 797 Kč. Navíc dodatek č. 3 ke staršímu úvěru 2053/10/5625 (23/27/ZM/2026). |
| `data/smlouvy/oprava_hodnot_registru_2026-10-23.json` | 215 verzí z webu bez částky: 149 má v registru hodnotu vč. DPH (1,18 mld. Kč celkem), 66 bez hodnoty |
| `data/kauzy/doplneni/K-003_doplneni_dotace_ZK_2026-10-23.json` | Dotace Zlínského kraje na lávku Vs-04-Bel: do 2 007 000 Kč, max. 5 % z předpokládaných CZV 40 159 444,22 Kč, realizace do 30. 11. 2027, výplata po závěrečné zprávě |
| `data/monitor/kontrola_RO_8115_monitor.json` | PDF RO 24/2025 ověřeno → nová anomálie A-2025-05 (+26,55 Kč) |

## Opravy předchozích zjištění
- Transfer Zlínského kraje městu 6,39 mil. (Územní registr 2026) **nesouvisí** s dotací na lávku. Dotace se vyplácí až po závěrečné zprávě. Opraveno v `uzemni_registr_vsetin_prijemce_2026.json`.

## Technické
- smlouvy.gov.cz (HTML detail i přílohy) **je dostupný z cloudového sandboxu**. Hromadné ověřování registru jde dělat skriptem, ne přes prohlížeč. data.smlouvy.gov.cz (měsíční dumpy) dostupný není.
- Při ~1 dotazu/s vracel proxy/server přechodné chyby SSL EOF (63/215). Při 2–6 s prodlevě prošlo vše. Pro server doporučuji ≥ 2 s a backoff.
- Push na GitHub: git proxy odmítá (repo není v autorizovaných zdrojích relace). Řešení: přidat repo `adamczeko-ai/datamestovsetin` do zdrojů relace, nebo nahrát přes web UI.

## Fronta
1. Úvěr 2053/10/5625: výše, účel a dodatek č. 3 (registr smluv, ZM 27 – balíček materiálů).
2. Krátkodobý úvěr pol. 8113 (200 mil. v rozpočtech 2024–2026): smlouva a čerpání (MONITOR 8113 výsledek = 0 ve všech letech 2020–2025).
3. K-003: žádost o dotaci RP02-26DT5/004 – rozpis CZV (40,16 mil.) proti SoD 68,98 mil. bez DPH.
4. Z1 (hodnoty registru) a Z2 (transfery) pro Claude Code – podklady hotové.
