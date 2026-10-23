# Slepý test LLM vrstvy – K-002 a K-003 (2026-10-23)

## Metoda
- Vstupy: `ai/test/slepy/K-002.json` a `K-003.json`. Jsou to kopie kauz bez ručních závěrů: odstraněna pole `pozorovani`, `dalsi_krok`, `otazky`, `upozorneni`, `srovnani_VZ_I_II` a `penize.narust_nasobek`.
- Referenční seznam `ai/test/ocekavane.json` byl sepsán **před** během.
- Model: Claude Opus 5.5 jako subagent v izolované složce s instrukcí nečíst nic jiného. Izolace je instrukční, ne technická.
- Prompt: `ai/PROMPT_nesoulady.md` (nesoulady@1).
- Kandidát prošel `scripts/kontrola_nesouladu_llm.py`. Výsledek je v `ai/test/vysledek_slepy_test_2026-10-23.json`.

## Výsledek

| | počet |
|---|---|
| Nesouladů od modelu | 6 |
| Zahozeno kontrolou citací | 0 (všech 12+ citací nalezeno doslova ve zdroji) |
| Jádro nalezeno | **5 / 7** (G1, G2, G6, G7, G8; G6 a G7 v jednom nesouladu N-006) |
| Jádro minuto | 2 / 7: **G3** (smlouva 3,5 měsíce po usnesení), **G5** (SoD 19,48 → 68,98 mil.) |
| Volitelné nalezeno | G4 (částečně v N-002), G9 (N-004), G10 (N-003) |
| Falešné (ruční revize) | 0 |

## Omezení (nutno číst s výsledkem)
- Jde o jeden běh nad 2 kauzami. LLM je nedeterministický, takže výsledek nelze zobecnit.
- Vstupy nebyly surové dokumenty, ale už vytěžená data. Časová osa obsahuje interpretační poznámky (např. „+24 %“, „k ověření, zda dodatek“). Reálný běh nad texty dokumentů bude těžší.
- Referenční seznam sestavil stejný autor jako test. Nezávislé vyhodnocení zatím chybí.
- Minutá jádra jsou typu „časová prodleva“ a „srovnání dvou smluv napříč roky“. Doporučení: doplnit do promptu explicitní kontrolní seznam (datum usnesení vs. podpis smlouvy; první vs. poslední cena akce). Pravidlo R16 lze rozšířit o porovnání prodlevy usnesení → smlouva.
