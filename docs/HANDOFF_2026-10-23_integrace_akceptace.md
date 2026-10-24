# Předávka: integrace – akceptace a první živý běh na dev (23. 10. 2026 odpoledne)

**Relace:** Claude in Chrome + cloudový sandbox. **Přístup na server: žádný.** Produkce ani dev se neměnily.

## 1. Proč integrace „nefungují“ (diagnóza, ověřeno)

| Vrstva | Stav | Doklad |
|---|---|---|
| Zdroje (MONITOR, RÚIAN, RVZ, dataor, ARES) | dostupné bez autentizace | HEAD 23. 10. 12:50 SELČ, viz `data/integrace/evidence_stazeni.json` |
| Kód konektorů (`integrace/`) | hotový, 64 offline testů OK | `python3 -m unittest discover -s tests` |
| **Živý běh MONITOR/RÚIAN/RVZ** | **nikdy neproběhl** | Cloud tyto hosty nepustí (egress proxy 403). Dev server nemá spouštěcí skript pro `integrace/` (`nasazeni_dev.sh` řeší jen AI pipeline) |
| Web nasvsetin.cz | zdroje jsou vedeny jako „neintegrováno“ | stránka Zdroje a metodika, 12:45 SELČ. Údaj je **pravdivý** |

Kód tedy není chybný. Chybí krok „spustit na dev a doložit výsledek“. Tato várka ho připravuje tak, aby šel provést jedním příkazem a výsledek se dal ověřit strojově.

## 2. Dnešní kontrola nových verzí (nic se znovu nestahovalo)

| Soubor | Výsledek |
|---|---|
| MONITOR FINM2026 08/2026 | ETag `"6ab496d0-17be1a8"` se shoduje s importem z 22. 10. |
| MONITOR 09/2026 | 404, zatím nepublikováno (RSS: poslední publikace ÚSC 24. 9.) |
| RÚIAN VFR 20260930 | ETag/Last-Modified beze změny. 20261031 vrací 404 |
| RVZ VZ-09-2026 | ETag beze změny. VZ-10-2026 vrací 404 (očekáváno k 5. 11.) |

## 3. Změny v kódu (větev `claude/2026-10-23-integrace-akceptace`)

1. **`integrace/sources/rvz.py`**
   - Rok 2024 se stahuje z ročního souboru `VZ-2024_rocni.zip`. Ověřeno: měsíční názvy pro 2024 vrací 404, takže dosavadní konektor rok 2024 vůbec nedoplnil.
   - `periods()` a `sync_range()` doplňují data zpětně od roku 2024. Soubory se zpracují postupně a ETag zabrání opakovanému stažení. Chyba jednoho období neshodí ostatní.
   - Konektor nově hledá IČO i mezi **účastníky** (podané nabídky), dříve jen mezi zadavateli a dodavateli. Do sloupce `role_okruhu` zapisuje roli: zadavatel / dodavatel / účastník.
   - Výchozí měsíc respektuje publikaci k 5. dni. Dříve se před 5. dnem pokoušel stáhnout nepublikovaný soubor.
2. **`integrace/db.py`:** idempotentní migrace sloupců (`ALTER TABLE … ADD COLUMN`, jen pokud chybí).
3. **`integrace/akceptace.py`** + `python -m integrace akceptace`: tabulku akceptace z `INTEGRACE_NASAZENI.md` převádí na 21 strojových kontrol a 4 kontroly idempotence. Výsledek každé kontroly: `ok` / `selhalo` / `nespusteno` / `info`. Návratový kód ≠ 0 při selhání. Pouze čte DB.
4. **`scripts/nasazeni_integrace_dev.sh`:** připraví prostředí, spustí offline testy, provede **běh 1** a ihned **běh 2** (ověří, že se nic nestáhne znovu), spustí akceptaci a uloží JSON report. Odmítne `/opt`, zakládá zámek (flock), necron, nesahá na Docker, apt ani push. Zapisuje jen do `$DEV_DIR/data/integrace*`.
5. **`tests/test_integrace_rvz_akceptace.py`:** 8 nových testů (roční soubor, období, role účastník, zpětné doplnění a idempotence přes mock server, migrace, akceptace).

## 3a. Simulace skriptu v sandboxu (bez přístupu ke zdrojům MONITOR/RÚIAN/RVZ)

Skript proběhl celý: ARES-VR 9/9 a registr smluv 38540900 = 500 000 000 Kč (živě, `ok`), 2. běh VR byl `unchanged_hash` ×9. Simulace odhalila **3 chyby, všechny opravené a pokryté testy**:
1. RÚIAN a RVZ při chybě spojení vracely `{"status":"chyba"}`, CLI ale evidovalo běh v `sync_run` jako **„ok“**. Web by tak mohl ukazovat falešný úspěch. Nově chyba konektoru = `chyba` a návratový kód 1.
2. Kontrola idempotence hlásila `ok` i tehdy, když 2. běh skončil jen chybami. Nově vyžaduje úspěšnou podmíněnou kontrolu bez chyb.
3. Výpis stavů v bash používal syntaxi f-stringu, která na Pythonu 3.10 neprojde.

**Opakovaná simulace po opravě (commit 9f4eb17):** monitor/ruian/rvz `chyba` (správně, hosty jsou blokovány), smlouvy/vr `ok`. Akceptace: ok 4, selhalo 3 (idempotence nedostupných zdrojů), nespuštěno 18. Exit 1. Výsledek odpovídá skutečnému stavu.

Na rychlost to vliv nemá, ale je dobré to vědět: nedostupný host stojí v každém období 5 pokusů s exponenciální prodlevou (~30 s). To je záměr: přechodné výpadky se tak přečkají.

**Doporučení:** pokud vlastník v nastavení Claude (Settings → Capabilities, povolené domény) přidá `monitor.statnipokladna.gov.cz`, `vdp.cuzk.gov.cz`, `isvz.nipez.cz` a `dataor.justice.cz`, může první živý běh a akceptaci provést přímo cloudová relace, a to bez serveru a bez rizika pro dev i produkci.

## 4. Spuštění na dev (krok pro vlastníka nebo Claude Code)

Z Windows PowerShellu:

```powershell
ssh administrator@192.168.1.111 "git -C ~/datamestovsetin fetch -q origin && git -C ~/datamestovsetin checkout -q claude/2026-10-23-integrace-akceptace && git -C ~/datamestovsetin pull -q --ff-only && VETEV=claude/2026-10-23-integrace-akceptace bash ~/datamestovsetin/scripts/nasazeni_integrace_dev.sh"
```

Po merge PR stačí bez `VETEV`. Zpětné doplnění RVZ (22 souborů, celkem **~2,5 GB**, jednorázově) zapni přidáním `RVZ_OD=2024`. Výchozí běh stahuje jen poslední měsíc (~183 MB). U MONITOR od 2020 se díky HTTP Range stahuje jen ~4 MB/rok a ~19 MB/měsíc 2026.

**Hotovo je tehdy, když** report `integrace_akceptace_*.json` má `selhalo = 0`, `idempotence.*` jsou `ok` a RVZ `info` je blízko referenčním 83 / 53. Teprve poté lze stav zdroje změnit na **IMPLEMENTOVÁNO VE VÝVOJI**. Produkční nasazení a cron schvaluje vlastník.

## 4a. Návrh integrace
- Konektory: `integrace/sources/monitor_finm.py`, `ruian_vfr.py`, `rvz.py`, `vr.py`, `registr_smluv.py` (beze změny architektury).
- Tabulky: `monitor_*`, `observed_transfer`, `ruian_*`, `rvz_zakazka` (nově `role_okruhu`), `rvz_smlouva`, `vr_*`, `rs_verze`, evidence `sync_run` a `sync_ledger`.
- Akceptační hodnoty: `integrace/akceptace.py` (21 kontrol + 4 kontroly idempotence). Zdrojem je tabulka v `docs/INTEGRACE_NASAZENI.md`.
- Štítky tvrzení: hodnoty akceptace jsou **Doloženo** (ověřeno 22.–23. 10. proti souborům s uvedeným ETag). Odchylka RVZ 83 → konektor je **Hypotéza**, dokud neproběhne živý běh.

## 5. Otevřené

- Registr dotací: API není dokumentované a podmínky užití musí potvrdit MF. Vypnuto (`--allow-undocumented`).
- ČÚZK API KN: čeká na registraci vlastníka. Klíč patří jen do `.env` na serveru.
- Sbírka listin: oficiální strojová služba neexistuje, hromadně se nestahuje.
- Web: stav zdrojů na nasvsetin.cz má po prvním úspěšném dev běhu číst `sync_run`/`sync_ledger` (zadání Z1–Z5). Dokud se tak nestane, je „neintegrováno“ správný údaj.
