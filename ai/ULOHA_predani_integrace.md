# Plánovaná úloha: příprava předaných PR k integraci

Verze `uloha-predani@1` (2026-10-23). Úlohu spouští hlavní relace „Testování VSETÍN OSINT aplikace“ (plánovač Claude, např. každý pracovní den v 7:30 Europe/Prague), případně ručně. Každý běh začíná bez paměti.

## Hranice (závazné)
- Pracuje se jen v klonu repa v cloudu. Server ani produkce se neoslovují.
- **Nikdy merge, nikdy push do `main`.** Commity jen do větve předávaného PR, a to jen opravy a doplnění integrace.
- Ve zdrojových datech PR se nemění hodnoty. Pokud jsou chybné, PR dostane štítek `potrebuje-opravu` a komentář s důkazem.
- Časy uvádět v Europe/Prague.

## Postup
1. Najdi otevřené PR se štítkem `predani` a bez štítků `pripraveno-k-merge` a `potrebuje-opravu`: `gh pr list --label predani --state open`.
2. U každého PR:
   1. Checkout větve. Pokud nejde čistě přeskládat na `main`, napiš komentář „nutný rebase“, dej štítek `potrebuje-opravu` a pokračuj dalším PR.
   2. `python3 scripts/ci_validate.py` a všechny `scripts/kontrola_*.py`, které PR přidává nebo mění.
   3. Zkontroluj povinný obsah podle `docs/PREDAVANI_MEZI_RELACEMI.md` (§ 3).
   4. Porovnej s `integrace/`. Jsou-li data reprodukovatelná konektorem, doplň do `tests/` akceptační test s hodnotami z předávací zprávy (offline, fixture z manifestu), případně úpravu konektoru. Každou změnu commitni do větve PR.
   5. Napiš komentář do PR:
      - výsledky kontrol (skutečný výstup),
      - co jsi doplnil,
      - doporučení: sloučit / opravit / zamítnout s důvodem.
   6. Nastav štítek `pripraveno-k-merge`, nebo `potrebuje-opravu`.
3. Souhrn běhu: jedna zpráva vlastníkovi se seznamem PR a stavem každého. Pokud nebylo co zpracovat: „beze změn“.
