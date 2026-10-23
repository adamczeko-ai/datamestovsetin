# Slepý test LLM vrstvy – prompt nesoulady@2 (2026-10-23)

Prompt `nesoulady@2` přidává kontrolní seznam o osmi bodech. Výsledky obou nových běhů prošly kontrolou `scripts/kontrola_nesouladu_llm.py`, která nic nezahodila.

## 1. Opakovaný test K-002 a K-003 (stejné vstupy a reference jako u @1)

| Ref. | Nesoulad | @1 | @2 |
|---|---|---|---|
| G1 | návrh 34,0 × schváleno 33,15 mil. | ano | ano (N-002) |
| G2 | návrh usnesení bez ceny | ano | ano (N-001) |
| G3 | smlouva 3,5 měsíce po usnesení | **ne** | **ne** |
| G5 | SoD 19,48 → 68,98 mil. | **ne** | ano (N-003) |
| G6 | předp. hodnota VZ I 58 mil. × nabídky 71–79 mil. | ano | ano (N-005) |
| G7 | VZ II navýšena na 72 mil. | ano | ano (N-005) |
| G8 | narovnání 2,17 mil. – důvod | ano | ano (N-004) |

- **Jádro: @1 5/7, @2 6/7.**
- Navíc @2 vrátil N-006: novou SoD schválil starosta a usnesení RM/ZM v datech chybí (jistota nízká). Neověřeno. Může jít o běžný postup po rozhodnutí o výběru dodavatele, proto ho neřadím mezi falešné.
- G3 model nenašel ani s kontrolním seznamem. **Případ nově deterministicky pokrývá pravidlo R17** (`R17-prodleva-usneseni-smlouva`, 101 dní) a G5 pravidlo R18 (nárůst o 254 %).
- **Výhrada:** seznam vznikl až po prvním testu, takže tento test zčásti měří přeučení na známé případy. Proto níže následuje holdout.

## 2. Holdout K-004 (kauza nepoužitá k ladění promptu)

Reference: `ai/test/ocekavane_holdout_K-004.json`, sepsaná před během. Výsledek: `ai/test/vysledek_holdout_K-004_2026-10-23.json`.

| Ref. | Nesoulad | Nalezeno |
|---|---|---|
| H1 | výše likvidačního zůstatku chybí | ano (N-001) |
| H2 | vklad 3,6 mil. do rušené společnosti | ano (N-003, částečně N-001) |
| H3 | odpočet DPH 3 848 880 Kč nedoložen | ano (N-004) |
| H4 (volitelné) | pohledávka z titulu úvěru ČSOB | ne |
| H5 (volitelné) | ZM schválilo dodatek k Dohodě, registr uvádí dodatek k nájemní smlouvě | **ano (N-002)** |
| H6 (volitelné) | provozovatel inkubátoru po zrušení | ne |

- **Jádro 3/3, volitelné 1/3.**
- Navíc vrátil N-005 (základ DPH kompenzace SOHZ, nízká jistota) a N-006 (správní rada rozhodla o zrušení dřív než ZM, nízká jistota). N-006 je pravděpodobně legitimní pořadí kroků u o.p.s., takže je to kandidát na stav `zamitnuto`. Rozhodne člověk.

## Omezení
- Každá varianta proběhla jednou a model není deterministický.
- Vstupy jsou vytěžená data, ne originální dokumenty.
- Reference i hodnocení připravil stejný autor. Nezávislé hodnocení zatím chybí.
- Holdout vstup obsahuje pole `penize.pozn` s částečnou interpretací DPH, což H3 usnadňuje.
