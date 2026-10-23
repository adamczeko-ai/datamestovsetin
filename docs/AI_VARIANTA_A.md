# AI vrstva „nesoulady k vysvětlení“ – architektura a nastavení

*2026-10-23. Stav: návrh + prototyp. Nic není nasazeno na server.*

## Proč dvě vrstvy

| Vrstva | Co dělá | Kde | Auditovatelnost |
|---|---|---|---|
| Deterministická (R1–R16, anomálie A-*) | čísla, součty, limity ZZVZ, časová okna | `scripts/analyzy.py`, `scripts/pravidla_nesoulady.py`, `scripts/signaly_v2.py` | plná: stejný vstup dává stejný výstup, testy |
| LLM | čtení textů, rozpory mezi dokumenty o téže akci | `ai/PROMPT_nesoulady.md` + kontrola `scripts/kontrola_nesouladu_llm.py` | citace se ověřují doslova, co neprojde, se zahodí |

Stavy ověření (`novy` → `overuje_se` → `vysvetleno` / `potvrzeno` / `zamitnuto`) nastavuje **jen člověk** v `data/analyzy/signaly_stavy.json`. ID signálů jsou deterministická, takže stav přežije přegenerování.

## Varianta A: plánovaná úloha Claude nad repem (doporučeno jako start)

```
server dev (sync_core) ──push dat──► GitHub repo ──clone──► plánovaná úloha Claude (cloud)
                                         ▲                         │
                                         └──── PR ai/nesoulady-* ◄─┘
                                         vlastník: review → merge
```

- **Na serveru nic neběží a nic se tam nemění.** Úloha čte jen repo a výstup dává jako PR.
- LLM je samotná úloha (Claude), takže není potřeba API klíč ani infrastruktura.
- Postup běhu: `ai/ULOHA_planovana.md`.

### Nastavení (jednorázově)
1. **Ochrana `main` (dělá vlastník):** GitHub → Settings → Branches → pravidlo pro `main`: „Require a pull request before merging“. Bez toho by AI technicky mohla zapsat do `main`. Tuto změnu nastavení jsem neprováděl.
2. Merge PR s touto vrstvou. Úloha do té doby skončí se zprávou „čeká na merge“.
3. Plánovaná úloha v Claude (nastavena 2026-10-23): pracovní dny ráno, výstup PR + oznámení.
4. Doplnit do serverového ingestu (`scripts/sync/`) ukládání **textu dokumentů po stranách** do `raw/texty/<sha256>/p<N>.txt` a `sha256` do `evidence_stazeni.json`. Bez toho LLM cituje jen vytěžená data, ne originály. Jde o změnu na dev serveru a vyžaduje schválení.

### Zjištěná omezení prostředí (ověřeno 2026-10-23)
- Shell cloudové úlohy **nedosáhne** na mestovsetin.cz, hlidacstatu.cz ani monitor.statnipokladna.cz. Na smlouvy.gov.cz a GitHub dosáhne. Stahování proto musí zůstat na serveru.
- `gh` GraphQL v relaci nefunguje. PR se zakládá přes REST (`gh api repos/.../pulls`).

### Rizika A
| Riziko | Opatření |
|---|---|
| Halucinace / nepřesná citace | kontrola doslovných citací, min. 2 zdroje, zahazování |
| Dehonestace (viz K-001) | zakázané výrazy, neutrální formulace, princip čtyř očí před předáním KV |
| GDPR (fyzické osoby) | prompt zakazuje analýzu fyzických osob; skript to neumí spolehlivě poznat, proto lidská revize PR |
| Závislost na službě / změna modelu | verze promptu ve výstupu, deterministická vrstva funguje i bez LLM |
| Šum (příliš mnoho signálů) | stavy + měření přesnosti pravidel z `signaly_stavy.json` |

**Náklady A:** v rámci předplatného Claude (běhy čerpají limity účtu), infrastruktura 0 Kč.
**Rollback A:** vypnout nebo smazat plánovanou úlohu; zavřít otevřené PR; `git revert` merge commitu vrstvy. Zdrojová data se nemění.

## Varianta B: samostatný worker (až po stabilizaci A)

```
VPS / mini-PC (mimo produkční server) ── Tailscale/WireGuard nebo Cloudflare Tunnel + Access (MFA)
   ├─ cron/systemd timer: git pull (read-only deploy key)
   ├─ python skripty + Claude API (nebo lokální LLM)
   └─ PR přes fine-grained token: contents:write jen na větve ai/*, pull_requests:write
```

- Bez otevřených portů. Přístup jen přes VPN nebo tunel s MFA.
- Dva tokeny: read-only pro čtení a PR-only pro zápis. `main` chrání branch protection.
- Výhoda: běh nezávislý na plánovači, možnost lokálního LLM, delší úlohy.
- Rizika: správa stroje (aktualizace, zálohy), únik tokenu (krátká expirace, rotace), náklady na API podle objemu.
- Lokální LLM: kvalita na české právně-finanční texty je výrazně nižší. Smysl má jen při požadavku, aby data neopustila vlastní HW (data jsou ale veřejná).
- **Rollback B:** zastavit timer, revokovat tokeny a deploy key, odpojit tunel.
