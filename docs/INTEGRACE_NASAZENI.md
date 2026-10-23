# Integrace datových zdrojů: nasazení (balík `integrace/`)

**Stav k 23. 10. 2026:** kód je hotový a otestovaný offline (12/12 testů, z toho 2 živé přeskočené) a živě proti ARES a registru smluv. MONITOR, RÚIAN a RVZ proti živým zdrojům **neběžely**, protože cloudové prostředí k nim nemá síťový přístup. První živý běh těchto tří zdrojů proběhne až ve vývojovém prostředí.

## Co balík dělá

| Příkaz | Zdroj | Výstupní tabulky | Změny | Zátěž |
|---|---|---|---|---|
| `python -m integrace monitor` | MONITOR FIN 2-12 M (open data) | `monitor_finm_radek`, `monitor_rekapitulace`, `observed_transfer` | ETag přes HEAD; stahuje jen potřebné členy ZIP (HTTP Range) | ~4 MB/rok (do 2025), ~19 MB/měsíc (2026+) |
| `python -m integrace ruian` | RÚIAN VFR obce 541630 | `ruian_adresni_misto`, `ruian_stavebni_objekt`, `ruian_parcela`, `ruian_ulice` | If-None-Match / If-Modified-Since | 6 MB/měsíc |
| `python -m integrace rvz [--rok R --mesic M]` | NIPEZ RVZ open data | `rvz_zakazka`, `rvz_smlouva` | ETag; novější `casova_znacka` přepisuje starší | ~180 MB/měsíc, zpracování proudově |
| `python -m integrace vr` | ARES-VR | `vr_subjekt`, `vr_angazma` | SHA-256 odpovědi | 9 dotazů |
| `python -m integrace smlouvy --verze-soubor F` | Registr smluv (XML verze) | `rs_verze` | verze jsou neměnné, stahuje se jen chybějící `idVerze` | 1 dotaz / 2 s |
| `python -m integrace dotace --allow-undocumented` | MONITOR Registr dotací (**nedokumentované API**) | `dotace_uzemni`, `dotace_statni` | přepis podle klíče | ~4 dotazy |
| `python -m integrace dokumenty --seznam data/integrace/dokumenty_seznam.txt --texty raw/texty` | dokumenty města (PDF/HTML/ZIP) | `dokument_text` + `raw/texty/<sha256>/p<N>.txt`, `meta.json` | podmíněné stahování; stejný SHA-256 = beze změny | 158 URL, 1 dotaz / 2 s |
| `python -m integrace stav` | evidence | `sync_run`, `sync_ledger` | – | – |

- Používá jen standardní knihovnu Pythonu 3.10+, žádné závislosti.
- Databáze aplikace se **nemění**. Balík zapisuje do vlastní SQLite (`INTEGRACE_DB`), aplikace z ní čte.
- Osobní údaje: z VR se ukládá jen jméno a funkce s daty, žádná data narození ani adresy. U Registru dotací se jména fyzických osob neukládají.

## Nasazení do vývoje (Claude Code / Codex)

```bash
cd /home/administrator/vsetin-osint-dev
git -C <klon datamestovsetin> pull
cp -r <klon>/integrace ./integrace && cp integrace/config.example.json integrace/config.json
export INTEGRACE_DB=$PWD/data/integrace.db INTEGRACE_CACHE=$PWD/data/integrace_cache
python3 -m unittest <klon>/tests/test_integrace.py -v        # offline testy
python3 -m integrace monitor --od 2020                         # 6× roční + 2026 měsíčně
python3 -m integrace ruian
python3 -m integrace vr
python3 -m integrace rvz --rok 2026 --mesic 9
python3 -m integrace stav
```

### Akceptace (hodnoty ověřené 22.–23. 10. 2026)

| Kontrola | Očekávaná hodnota |
|---|---|
| `monitor_rekapitulace` 2025-12, řádek 4200 (příjmy po konsolidaci) | 1 003 369 035,77 (= ZÚ 2025) |
| 2025-12, řádek 4430 (výdaje po konsolidaci) | 1 082 275 065,54 (= ZÚ 2025) |
| 2024-12: 4200 / 4430 | 954 467 444,47 / 933 707 707,92 |
| `monitor_finm_radek` 2026-08, ico 00304450 | 1 745 řádků |
| `observed_transfer` 2026-08, Město → 28593987 / 47972114 / 75063468 | 18 298 000 / 12 400 000 / 90 006 566,86 |
| `observed_transfer` 2026-08, součet příjemců od města (všechny položky) | 352 871 840,46 (111 příjemců; Územní registr ve výchozím zobrazení vynechává přeposlané státní prostředky) |
| RÚIAN 20260930 | 3 778 AM / 6 739 SO / 26 965 parcel / 144 ulic |
| `vr_subjekt` | 9 subjektů, všechny u KSOS |
| `rs_verze` 38540900 | `s_dph` 500 000 000 |
| 2. spuštění stejného dne | MONITOR `beze_zmeny`, RÚIAN `beze_zmeny` (304), VR `importovano: 0` |

## Plánování (návrh, NEZAKLÁDAT bez schválení vlastníka)

| Úloha | Kdy | Proč |
|---|---|---|
| monitor | denně 06:10 (v měsících bez publikace jen HEAD) | MONITOR publikuje 2-12 M kolem 24. dne následujícího měsíce, RSS `…/api/opendata/rss` |
| ruian | 2. den v měsíci 05:20 | VFR k poslednímu dni měsíce |
| rvz | 6. den v měsíci 05:40 | aktualizace ISVZ k 5. dni |
| vr | týdně, pondělí 05:50 | změny ve VR |
| smlouvy | po každém importu registru smluv v aplikaci, jen nové `idVerze` | oprava `value_kind` (M-01) |

## Napojení na aplikaci (navazuje na ZADANI_CLAUDE_CODE_model_UI Z1–Z5)
- **Z1:** aplikace bere `value_kind` a hodnoty z `rs_verze` podle `version_id`.
- **Z2:** profil příjemce zobrazuje `observed_transfer` jako „transfery od Města (kumulativně, indicie)“.
- **Z5:** stránka financí města čte `monitor_rekapitulace` (do 2025 tab. IV, od 2026 řádky `*_odv` = odvozeno).
- Adresy: `vr_subjekt.sidlo_adm_kod` je kód adresního místa RÚIAN → spojení s `ruian_adresni_misto.kod`.
- Stav zdrojů na webu: `sync_run` a `sync_ledger` (škála B5).

## Otevřené / blokované
- **Registr dotací:** použití nedokumentovaného API musí schválit vlastník. Územní transfery pokrývá `monitor`.
- **ČÚZK API KN:** potřebuje registraci vlastníka (Identita občana). Klíč patří jen do `.env` na serveru.
- **Sbírka listin:** oficiální strojové rozhraní neexistuje.
- **RVZ:** zakázky města z profilu vhodne-uverejneni.cz RVZ zatím nepublikuje, takže výsledek může být prázdný.
