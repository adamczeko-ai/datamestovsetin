# Předávka – várka o (ověření subjektů v ARES)

*23. 10. 2026, ~10:45 SELČ. Autonomní várka (Claude, Cowork).*

## Cíl
Odstranit výhradu „IČO neověřena v ARES“ v registru subjektů. Je to předpoklad pro P1 automatické párování se smlouvami podle IČO.

## Vztah k dřívějšímu ověření
Navazuje na `data/entity/ares_overeni_2026-10-23.json` (38 IČO, 22:08 UTC 22. 10.), který zůstává beze změny. Tato várka rozšiřuje pokrytí na všechna IČO v `data/**` (74), přidává fallback na dílčí registry (AERV) a ověření zdroje u 60042354.

## Implementováno
- `scripts/ares_overeni.py`: posbírá IČO z polí `ico`/`ico_*` a z textu „IČO NNNNNNNN“ ve všech `data/**/*.json`, zkontroluje kontrolní číslici (mod 11) a dotáže se ARES REST. Subjekty vymazané z OR vrací základní endpoint jako 404, proto skript u nich zkouší dílčí registry RŽP a RES.
  - Spuštění: `python3 scripts/ares_overeni.py` (výsledek do `data/entity/ares_overeni.json`)
  - `--zapsat` doplní blok `ares` do `subjekty.json`. Ručně doplněné detaily (mají klíč `zdroj` nebo `zdroj_ico`) nepřepisuje.
- `data/entity/ares_overeni.json`: 74 IČO (po rebase na 772236b).
- `data/schema/ares-overeni.schema.json` + zařazení do `validate_schemas.py`. Všech 10 souborů je validních.
- `subjekty.json`:
  - blok `ares` u všech subjektů s IČO
  - nová IČO z ARES u subjektů, kde se název shoduje jednoznačně: Damostis s.r.o. 23287152, MUNIPOLIS s.r.o. 29198950
  - u farního sboru ČCE jsou uvedení dva kandidáti, protože ze zdroje nelze určit, o který sbor jde

## Výsledky
| Ukazatel | Hodnota |
|---|---|
| IČO celkem | 74 |
| ověřeno v ARES | 72 |
| chybná kontrolní číslice | 0 |
| zaniklé | 1 (AERV 26863081) |
| nenalezeno | 1 (60042354) |
| nesoulad názvu | 0 (jen poznámky v závorkách u 2 subjektů) |

## Zjištění
1. **AERV o.p.s. (26863081)**
   - Jediným zakladatelem byla obec, Město Vsetín.
   - Rozhodnutím správní rady 11. 10. 2023 byla zrušena k 31. 12. 2023. Likvidace začala 1. 1. 2024, výmaz z OR proběhl 18. 12. 2024 (KS Ostrava, O 200).
   - V roce 2023 město současně zaplatilo *Dohodu o narovnání AERV* 3 848 880 Kč (RO 8/2023) a peněžitý vklad 3,6 mil. Kč (RO 21/2023).
   - Zapsáno do `vazby_k_overeni`. Je to signál k ověření, ne zjištění pochybení.
2. **MŠ Vsetín, Trávníky 1218 (IČO 60042354)**
   - IČO je ve zdroji výslovně: RO 11/2025, usn. 14/73/RM/2025, dotace OP JAK 380 000 Kč. Text PDF jsem znovu ověřil přes pdf.js.
   - ARES subjekt nezná. Nenašel se v základním registru, VR, RES, RŽP ani RŠ, ve webovém vyhledávání ARES ani podle názvu či adresy.
   - Je potřeba ověřit v rejstříku škol MŠMT. Může jít o chybu IČO v dokumentu města, nebo o chybějící záznam v ARES.

## Omezení
- Push na GitHub z této relace selhal: proxy vrací 403, protože repozitář není mezi autorizovanými zdroji relace. Změny jsou commitnuté lokálně a předané jako git bundle a patch.
- Z cloudového sandboxu jsou blokované hlidacstatu.cz, data.smlouvy.gov.cz a mestovsetin.cz. ARES je dostupný. Dokumenty města šly číst přes prohlížeč uživatele.
- Osobní údaje fyzických osob z VR (data narození, adresy členů orgánů) jsem záměrně neukládal.

## Další krok (doporučení)
1. **P1 párování smluv podle IČO.** Nejlepší zdroj jsou otevřená data registru smluv (měsíční XML dumpy na data.smlouvy.gov.cz). Je potřeba povolit doménu v Settings → Capabilities, případně dodat token Hlídače státu. Potom lze spárovat všech 67 ověřených IČO se smlouvami města (IČO 00304450) automaticky místo ručních dotazů.
2. Ověřit MŠ Trávníky 1218 v rejstříku škol.
3. AERV: dohledat usnesení ZM ke zrušení společnosti (říjen–listopad 2023) a ke vkladu 3,6 mil.
