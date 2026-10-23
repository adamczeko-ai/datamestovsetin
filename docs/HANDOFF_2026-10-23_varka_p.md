# Předávka – várka p (párování IČO se smlouvami v registru smluv)

*23. 10. 2026, ~11:30 SELČ. Autonomní várka (Claude, Cowork).*

## Cíl
Roadmapa P1, automatické párování subjektů se smlouvami podle IČO. Ruční fulltext (`parovani_akci.json`) nahrazuje systematický dotaz přes všechna IČO ověřená ve várce o.

## Metoda
- Na každé ze 73 IČO z `data/entity/ares_overeni.json` (bez města) šly dva dotazy do podrobného vyhledávání registru smluv:
  - **A:** publikuje Město Vsetín, smluvní strana je dané IČO,
  - **B:** publikuje dané IČO, smluvní strana je město.
  - Hledá se jen v posledních verzích záznamů. Žádný dotaz nenarazil na limit 500 záznamů.
- Cloudový sandbox má smlouvy.gov.cz, hlidacstatu.cz a data.smlouvy.gov.cz zablokované. Skript `scripts/registr_smluv_parovani_ico.js` proto běžel v prohlížeči na smlouvy.gov.cz.
- Souhrn jsem přenesl ručně a přepis ověřil kontrolním součtem. Shoduje se se zdrojem: 63 IČO, součet bez DPH 1 216 479 434 Kč, součet s DPH 1 286 325 466 Kč a hash identifikátorů.
- U 8 klíčových smluv jsem otevřel detail záznamu a ověřil datum uzavření, číslo smlouvy, hodnotu a návaznou smlouvu.

## Výstup
- `data/smlouvy/parovani_ico.json`: souhrn za každé IČO a signály P-01 až P-04.
  - Souhrn obsahuje počet smluv, součty bez DPH a s DPH zvlášť, období, počet dodatků a z nich se změnou ceny, dary městu a 3 největší smlouvy s odkazem.
  - Smlouvy našlo 60 z 73 IČO, celkem 767 smluv.
  - 13 IČO žádnou smlouvu s městem v registru nemá. Patří sem i příspěvkové organizace, které se objevují jen ve vícestranných smlouvách.
- `data/schema/parovani-ico.schema.json` + zařazení do `validate_schemas.py`. Všech 13 souborů je validních.
- `K-003`: smlouva 39830353 je potvrzená jako Dodatek č. 1 k SoD 0138 2025 na lávku Vs-04-Bel. Jde o +641 950,51 Kč bez DPH a změnu termínu, cena díla je teď 69 625 701 Kč bez DPH.

## Signály k ověření (nejsou zjištěním pochybení)
| ID | Popis |
|---|---|
| P-01 | Čtyři dodavatelé projektu MVK č.p. 1356 (FUSION ARCHITECTS, FORM, LPT System, H & B delta) uzavřeli s městem darovací smlouvy s po sobě jdoucími čísly 0781–0784 2025, ve dnech 12.–15. 12. 2025, na 10–25 tis. Kč. Ověřit účel darů a pravidla přijímání darů od dodavatelů. |
| P-02 | AERV o.p.s.: smlouvu o vkladu 3,6 mil. Kč (714/1S/2023) město uzavřelo 21. 12. 2023, tedy 10 dní před dnem zrušení společnosti. Předtím: zhodnocení předmětu nájmu 18,33 mil. Kč bez DPH (6/2023) a ukončení nájmu (11/2023). Likvidační zůstatek byl převeden obci smlouvou 0740 2024, hodnota v registru není uvedena. |
| P-03 | Vysoký podíl dodatků: Martin Urban má 14 dodatků na 37 smluv (11 mění cenu), TM Stav 31 dodatků na 71 smluv (259 mil. Kč, 2016–2024). |
| P-04 | Oprava K-003 (viz výše). |

## Omezení
- Pole IČO smluvní strany není při zveřejnění povinné, takže výsledky mohou být neúplné.
- Data jsou data zveřejnění, ne uzavření (kromě ověřených detailů).
- Registr uvádí u smlouvy buď hodnotu bez DPH, nebo s DPH, proto se součty nesčítají.
- Seznam všech 767 smluv po řádcích jsem neukládal, kvůli omezení přenosu z prohlížeče. Skript ho vygeneruje znovu (`window._rs2` / `parovani()`).

## Další krok
1. Napojit `integrace/sources/registr_smluv.py` na seznam `id_verze` z tohoto párování. Doplní přesné hodnoty a datum uzavření pro všechny smlouvy, server musí mít přístup na smlouvy.gov.cz.
2. P-02: dohledat usnesení RM/ZM ke vkladu 3,6 mil. a ke zrušení AERV (10–12/2023) a výši likvidačního zůstatku (ZÚ 2024).
3. Doplnit do `analyzy.py` pravidlo „dar od dodavatele ±12 měsíců od zakázky“, zdroj `parovani_ico.json`.
