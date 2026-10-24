# PROMPT PRO CLAUDE CODE – VSETÍN OSINT: horní panel, „K prověření“, řazení smluv podle částky

## Role a hranice
Jsi seniorní frontend/UX vývojář a znalec WCAG 2.2. Pracuj česky.
- Pracuj **jen** v `/home/administrator/vsetin-osint-dev`.
- Nasazení do `/opt/vsetin-osint`, restart Dockeru i změny v produkční DB jen po výslovném schválení vlastníka (Adam).
- Nejdřív analyzuj existující frontend (`osint036.js`, `osint036.css`, `main.css`, šablony) a API. Drž zavedené konvence (třídy `rc-*`, hash routing `#rc/...`).
- Nedělej refactoring mimo rozsah.
- Výsledek dej jako PR do `adamczeko-ai/datamestovsetin` (nebo do repa aplikace, pokud je jiné) podle `docs/PREDAVANI_MEZI_RELACEMI.md`: větev `predani/ui-panel-…`, štítek `predani`.

## Výchozí stav (ověřeno 24. 10. 2026 na nasvsetin.cz, RC 038, šířka 1704 px)
Pořadí prvků v `<header>` (výška 60 px):

`Značka` · `Interní režim` (chip `rc-chip`) · `Přihlášeno` (text) · **`Odhlásit`** (`button.rc-logout`, zelené primární tlačítko 103×44) · prázdný `span` · `<nav aria-label="Analytické obrazovky">` s 6 odkazy: Přehled `#rc` (aria-current), Hledat `#rc/search`, Organizace `#rc/org`, Pracovní přehled `#rc/work`, Mapa a vztahy `#rc/relations`, Zdroje a metodika `#rc/sources`.

**Problémy:**
1. Blok stavu účtu leží **mezi značkou a navigací**, takže panel rozděluje a odtrhuje navigaci od značky.
2. `Odhlásit` má nejsilnější vizuální důraz v panelu (zelené primární tlačítko), přitom jde o nejméně častou akci.
3. „Přihlášeno“ a „Interní režim“ říkají totéž dvakrát.
4. Prázdný `span` (0×22) je zbytečný prvek v DOM.
5. Šest položek navigace a stav účtu se na mobilu nevejdou. Responzivní řešení (≤ 1024 px) neověřeno.

## Úkol 1 – Horní panel: jedno tlačítko účtu úplně vpravo
Cílové rozložení zleva doprava:

`[Značka + verze]  [navigace …]  ⟶ (volné místo) ⟶  [K prověření (počet)]  [Účet]`

- **Účet** je jediný prvek, úplně vpravo:
  - nepřihlášený uživatel: tlačítko **„Přihlásit“**, které otevře stávající login (`/api/internal/login`),
  - přihlášený uživatel: tlačítko **„Odhlásit“** a před ním malý chip **„Interní režim“** (text „Přihlášeno“ odstranit).
  - Styl je sekundární: obrys nebo „ghost“, ne plná zelená. Plná barva zůstává aktivní položce navigace.
- Stav přihlášení se bere z `/api/internal/session`. Po přihlášení nebo odhlášení se tlačítko přepne bez reloadu a fokus zůstane na něm.
- Odstranit prázdný `span`.
- **Přístupnost:**
  - tlačítko je `<button>` s viditelným textem,
  - po přepnutí se oznámí přes `aria-live="polite"` („Přihlášeno – interní režim“ / „Odhlášeno“),
  - kontrast ≥ 4,5 : 1,
  - cílová plocha ≥ 24×24 px (WCAG 2.5.8),
  - viditelný fokus (2.4.7).
- **Responzivita:** při šířce ≤ 1024 px se navigace sbalí do tlačítka „Menu“ (`aria-expanded`, `aria-controls`, Esc zavírá). „Účet“ a „K prověření“ zůstanou viditelné. Žádný vodorovný posuvník při 360 px.

## Úkol 2 – Nová obrazovka „K prověření“ (`#rc/check`)
Vlastník chce místo, kde ho systém sám upozorní na anomálie, nejasnosti v tocích peněz a v pravidlech. **V UI nepoužívej označení „kostlivci“.** Interní pracovní název je v pořádku, ale veřejný text musí být neutrální, jinak hrozí riziko obvinění.

- **Položka navigace:** „K prověření“ s odznakem počtu nových otevřených signálů (`aria-label="K prověření, 5 nových"`). Odznak se zobrazí jen nad 0.
- **Zdroj dat:**
  - `data/analyzy/signaly.json` (schéma `signaly@2`),
  - stavy z `data/analyzy/signaly_stavy.json` (edituje jen člověk),
  - nesoulady z `data/analyzy/llm/nesoulady_*.json`.
  - Pokud aplikace tyto soubory nemá v API, přidej endpoint `GET /api/signals` jen pro čtení. Ten vrací `id, pravidlo (R1–R16…), kategorie, titulek, otázka_k_vysvětlení, částka, typ_částky, subjekty (IČO), důkazy [{url, lokátor, sha256}], stav, poprvé_zjištěno, naposledy_ověřeno`.
- **Kategorie (filtry):** Toky peněz · Rozpočet a rozpočtová opatření · Zakázky a smlouvy · Pravidla a postupy · Subjekty a vazby.
- **Zobrazení:**
  - karta nebo řádek: titulek, otázka k vysvětlení, částka s typem, štítek důvěry (Doloženo / Odvozeno / Indicie / Hypotéza), stav (nový / ověřuje se / vysvětleno / potvrzeno / zamítnuto), odkazy na důkazy,
  - řazení podle závažnosti, částky a data.
- **Viditelnost:**
  - **nepřihlášený uživatel** vidí jen signály se stavem, který člověk označil jako zveřejnitelný (např. `potvrzeno` nebo `vysvětleno`),
  - **interní režim** vidí vše,
  - nikdy nezobrazovat hypotézu jako fakt,
  - ke každé položce trvale připojit větu: „Signál není zjištěním pochybení; slouží k prioritizaci ověřování.“
- **Autonomní upozornění:** odznak počítá signály s `poprvé_zjištěno` > posledního zobrazení obrazovky. Čas posledního zobrazení si ukládej v `localStorage` jen jako pohodlí, s `try/catch`. E-mailová nebo push upozornění jsou mimo rozsah (vyžadují schválení).
- **Akceptace:**
  - signály z PR #16 (RO 7: ODPA 3635 vs 3613, 850 000 Kč; čerpání rezerv mimo zveřejněná RO, cca 2,99 mil. Kč) se po sloučení zobrazí v kategorii „Rozpočet a rozpočtová opatření“,
  - každý odkaz na důkaz vede na existující URL.

## Úkol 3 – Řazení smluv podle částky
**Ověřený stav:**
- `GET /api/registry/contracts` vrací pole o **přesně 500 záznamech** s poli `version_id, contract_id, month_key, ico_match, published_at, signed_at, value_raw, value_kind, valid_record, registry_url`.
- 500 záznamů přesně je pravděpodobně oříznutí. **Řazení v prohlížeči nad oříznutou množinou by ukazovalo nepravdivé „největší smlouvy“.**

**Implementace:**
- **Server:** přidej parametry `sort=value|signed_at|published_at`, `order=asc|desc`, `limit`, `offset` a hlavičku nebo pole `total`. Řaď v databázi nad celou množinou.
- **Hodnoty `value_raw`:**
  - `value_kind` (bez DPH / vč. DPH / neuvedeno) se **nepřepočítává**: DPH sazbu neznáme, převod by byl odhad,
  - výchozí řazení je podle `value_raw` a typ se zobrazí u každé částky,
  - přepínač „jen bez DPH / jen vč. DPH / vše“,
  - záznamy bez částky jsou vždy **na konci** a označené „neuvedeno“ (není to nula).
- **UI:**
  - záhlaví sloupce „Smluvní hodnota“ je tlačítko s `aria-sort` (`ascending/descending/none`),
  - klik přepíná sestupně → vzestupně,
  - stav řazení je v URL (`#rc/...?sort=value&order=desc`),
  - stránkování ukazuje „1–50 z N“.
- Pod tabulkou zůstává text: „Smluvní hodnota není platba; různé druhy částek se nesčítají.“
- **Testy:**
  - API vrací správné pořadí včetně hodnot `null` na konci a `total`,
  - UI má správné `aria-sort` a klávesnicové ovládání (Enter/Space).

## Testy a výstup
- Unit a integrační testy pro všechny 3 úkoly. Ruční kontrola v dev na šířkách 360, 768, 1280 a 1704 px a s klávesnicí.
- Automatická kontrola přístupnosti (axe nebo pa11y, pokud jsou k dispozici), 0 nových chyb.
- Snímky obrazovky před a po (desktop a mobil) přilož do PR.
- **Report:**
  - změněné soubory,
  - skutečné výstupy testů,
  - co zůstalo neověřeno,
  - návrh nasazení (záloha, kroky, ověření, rollback), který **čeká na schválení vlastníka**.
