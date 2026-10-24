# PROMPT PRO CLAUDE CODE – VSETÍN OSINT v3: interní analytický nástroj, propojený model, „K prověření“

Nahrazuje v2 (v repu nebyla). Rozhodnutí vlastníka (Adam, 24. 10. 2026): **žádný veřejný režim**. Nástroj slouží jen jemu, interně. Cílem je co nejúplnější sběr a propojení **veřejně dostupných** dat.

## 0. Hranice
- **Prostředí:** jen vývoj (`/home/administrator/vsetin-osint-dev`). Nasazení a zásahy do produkční DB jen po schválení vlastníka. Výstup = PR podle `docs/PREDAVANI_MEZI_RELACEMI.md`, štítek `predani`, jedno téma = jeden PR.
- **Co tento prompt ruší:** všechny zábrany určené pro veřejné zobrazení (anonymizace, „zveřejnitelné“ stavy, skrývání jmen). Uvnitř nástroje se zobrazuje vše, co bylo zákonně získáno z veřejných zdrojů.
- **Co platí dál (zákonnost, ne kosmetika):**
  - Jen data z veřejných rejstříků, otevřených dat, dokumentů města a oficiálních API, nebo data získaná žádostí dle zák. 106/1999.
  - **Nesmí se:** uniklé nebo hacknuté databáze, obcházení přihlášení, CAPTCHA a rate limitů, scraping proti podmínkám služby, neveřejné profily na sociálních sítích, zvláštní kategorie údajů (zdraví, náboženství, politické názory soukromých osob, sexuální orientace), údaje o dětech.
  - **Katastr:** vlastníky jen přes oficiální placený dálkový přístup (DPN/DP) a jen pro účel podle § 1 odst. 2 katastrálního zákona. Data se dál nešíří (§ 53). REST API vlastníky neobsahuje.
  - **Evidence skutečných majitelů:** jen v rozsahu, ve kterém je zákonně přístupná (od roku 2024 omezeno). Případnou žádost o přístup s prokázaným zájmem podává vlastník.
- **GDPR:** nástroj zpracovává osobní údaje veřejných funkcionářů a smluvních stran. Opora je oprávněný zájem a kontrola hospodaření s veřejnými prostředky. Opatření nesnižují rozsah dat, chrání nástroj:
  - celý web za přihlášením,
  - přístupový log,
  - u každého údaje jeho původ,
  - šifrované zálohy.
- **Princip analýzy:** signál ≠ obvinění. Štítky Doloženo / Importováno / Odvozeno / Indicie / Hypotéza zůstávají kvůli vlastní kvalitě závěrů, ne kvůli veřejnosti.

## 0a. Kde smí být osobní údaje (doplněk po kontrole konzistence, 24. 10. 2026)
Toto zadání ruší zábrany **pro zobrazení uvnitř nástroje**. Neruší ochranu úložišť, která jsou veřejná. Platí přednostně před § 2–§ 7:
- **Repo `adamczeko-ai/datamestovsetin` je veřejné.** Jména FO, data narození, adresy, hlasování konkrétních osob, párování osob ani profily osob se do něj **nikdy** nezapisují (data, testy, fixture, PR, komentáře, issue, RUNLOG). Pro toto repo dál platí `docs/PREDAVANI_MEZI_RELACEMI.md` § 5 beze změny.
- Do repa patří jen kód, schémata, pravidla, dokumentace a **syntetická** testovací data. Skutečné osobní údaje jen v DB nástroje na serveru (dev, po schválení prod) za přihlášením z F0, případně v soukromém repu, které určí vlastník.
- **Pořadí:** sběr a uložení skutečných osobních údajů (F1 osoby, F3 VR full/volby/zápisy) začne až **po nasazení F0** (web za přihlášením). Do té doby se F1–F3 vyvíjí a testuje jen se syntetickými daty.
- **LIA a DPIA:** opora „oprávněný zájem“ (čl. 6 odst. 1 písm. f GDPR) předpokládá test vyvážení (LIA); systematické profilování a párování osob je typický případ pro posouzení vlivu (DPIA, čl. 35). Součástí F0 je návrh LIA a DPIA k podpisu vlastníkem (správcem). Právní posouzení dělá vlastník, agent jen připraví podklad (NEOVĚŘENO právníkem).
- Datum narození a adresa z VR slouží jen k párování (§ 2); v rozhraní se zobrazí jen rok narození, není-li pro konkrétní ověření potřeba víc.

## 1. Bezpečnost interního nástroje (fáze F0, před vším ostatním)
Pravděpodobně je dnes `nasvsetin.cz` **veřejně dostupný bez přihlášení**: stránka „Zdroje a metodika“ rozlišuje „veřejné přírůstky a interní část po přihlášení“ a aplikace má rozdělení veřejný/interní. Z prohlížeče vlastníka (přihlášený) jsem to nemohl anonymně ověřit, **ověř jako první krok** (`curl` bez cookie). Pro interní nástroj s osobními údaji je to hlavní riziko.
1. **Celý web a všechna API za autentizací.** Výjimkou je jen přihlašovací stránka a `/api/health`. Druhý faktor (TOTP) pro vlastníka. Session cookie `Secure; HttpOnly; SameSite=Strict`.
2. Volitelně **IP allowlist** nebo přístup přes VPN či Tailscale. Rozhodne vlastník.
3. `robots.txt: Disallow: /`, `X-Robots-Tag: noindex`. Požádat o odstranění dosud indexovaných stránek (návod pro vlastníka, neprovádět).
4. **Audit log** přihlášení a exportů. Rate limit na login.
5. **Zálohy DB šifrované.** Test obnovy.
6. **Akceptace:** anonymní `curl` na `/`, `/api/organizations` a `/api/registry/contracts` vrací 401 nebo přesměrování na login. Žádná data bez přihlášení.

Nasazení F0 do produkce je změna konfigurace, proto **čeká na výslovné schválení** vlastníka. Připrav přesné kroky a rollback.

## 2. Jednotný datový model
Po vzoru FollowTheMoney. Entity i vazby mají `id`, `zdroj_url`, `lokator`, `sha256`, `stitek`, `ziskano` (čas, Europe/Prague) a `platnost_od/do`.

| Entita | Klíč | Zdroje |
|---|---|---|
| Subjekt (PO) | IČO | ARES, VR (dataor + ARES-VR), RES, rejstřík škol |
| **Osoba (FO)** | interní ID; párovací klíče: jméno + datum narození z VR, IČO podnikající FO | VR (statutáři, společníci, prokuristé, členové orgánů), usnesení a zápisy ZM/RM (zastupitelé, hlasování), registr smluv (FO podnikatelé, podpisy), RISPF a Územní registr (příjemci FO), kandidátní listiny volby.cz, Centrální registr oznámení (rozsah dle zákona) |
| Funkce/role | osoba + subjekt + role + od–do | VR, usnesení (výbory, komise, rady PO), weby města |
| Rozhodnutí | číslo usnesení | `data/usneseni/`, zápisy |
| Hlasování | usnesení + osoba + hlas | zápisy ZM (pokud obsahují jmenovité hlasování) |
| Rozpočtový řádek | rok + ODPA + POL + ORG | RO (`data/rozpocet/`), MONITOR FIN |
| Akce/projekt | ORG | RO, `akce_timeline.json` |
| Transfer | poskytovatel + příjemce + období + položka | MONITOR FIN 2026+, Územní registr |
| Dotace | EDS/kapitola | RISPF, `data/dotace/`, Hlídač státu (sekundární) |
| Zakázka | ID VZ | profil zadavatele, NIPEZ open data |
| Smlouva | ID + verze | registr smluv (+ `oprava_hodnot_registru`) |
| Nemovitost | parcela/stavba (RÚIAN kód) | RÚIAN; vlastník jen z oficiálního DP (viz § 0) |
| Dokument | sha256 | `raw/texty/` |
| Signál | stabilní ID | `data/analyzy/signaly.json` |

**Párování osob (klíčové pro analýzu vazeb):**
- **přesné:**
  - jméno + datum narození (VR),
  - IČO podnikající FO,
  - jméno + funkce + období ve stejném zdrojovém dokumentu,
- **odvozené:** jméno + obec + shodný kontext (stejný subjekt nebo usnesení),
- **kandidát:** jen shodné jméno. Zobrazí se, ale **nikdy se z něj nestaví signál bez potvrzení**, protože shodné jméno neznamená stejnou osobu.

Každá vazba nese `metoda_parovani` a `jistota`. Vlastník může párování ručně potvrdit nebo zamítnout. Zápis jde do `data/entity/parovani_osob_stavy.json` a stroj ho nikdy nepřepisuje.

## 3. Rozšíření sběru dat (každý zdroj = konektor + manifest + kontrola)
Přidej podle hodnoty a dostupnosti. U každého zdroje nejdřív ověř podmínky a jen zapiš „ověřeno / blokováno“, nic nevymýšlej.
1. **VR úplné výpisy** (`full`, nejen `actual`) pro subjekty z watchlistu: historie statutárů a společníků. Ukládej jméno, datum narození, adresu a funkci od–do. Datum narození a adresa slouží k jednoznačnému párování.
2. **Zápisy a usnesení ZM, RM a výborů:** prezence, jmenovité hlasování (pokud je v zápisech), střety zájmů ohlášené na jednání.
3. **Volby** (volby.cz): kandidátky do zastupitelstva Vsetína (jméno, věk, strana, povolání, pořadí, zvolen).
4. **Centrální registr oznámení** (veřejní funkcionáři města): ověř, v jakém rozsahu a jakým postupem je přístupný. Je-li nutná žádost, připrav její text pro vlastníka.
5. **Financování politických stran** (ÚDHPSH, výroční zprávy, dárci): dárci ↔ dodavatelé města (pravidlo R-DAR-1).
6. **ISIR** (insolvenční rejstřík) pro dodavatele a příjemce.
7. **NIPEZ open data** (`isvz.nipez.cz/opendata`): nabídky, uchazeči, ceny.
8. **Sbírka listin:** účetní závěrky městských společností (PDF → text, `integrace dokumenty`). Jen ruční nebo oficiální cestou, bez obcházení ochran.
9. **Katastr:** RÚIAN pro identifikaci. Vlastnické údaje jen z oficiálního DP na pokyn vlastníka pro konkrétní nemovitost spojenou s akcí nebo smlouvou.

## 4. Analytické vrstvy
1. **Profil osoby** (nová obrazovka `#rc/person/{id}`):
   - funkce v čase (město, PO, společnosti, spolky),
   - hlasování,
   - smlouvy, dotace a transfery subjektů, kde působí,
   - kandidatury,
   - časová osa.
2. **Finanční profil subjektu:** smlouvy (bez DPH / vč. DPH / neuvedeno), transfery, dotace, VZZ a rozvaha. Typy částek se nesčítají.
3. **Časová osa akce (ORG):** usnesení → RO → zakázka → smlouva a dodatky → čerpání → stav. Pilot: lávky K-003, čp. 1356.
4. **Rekonciliace zdrojů po každé synchronizaci** (`scripts/kontrola_*`). Výsledky se zapisují jako signály.
5. **Síť vztahů:** osoby ↔ subjekty ↔ peníze. Zobrazuje cesty mezi dvěma uzly („jak souvisí X a Y“) s jistotou každé hrany.

## 5. Pravidla signálů (R1–R16 ponechat, přidat)
| Kód | Pravidlo | Výchozí štítek |
|---|---|---|
| R-RO-1 | změna rozpočtu v MONITOR bez zveřejněného RO | Indicie |
| R-RO-2 | RO schvaluje jiný paragraf, než podle kterého se účtuje (3635 vs 3613) | Indicie |
| R-FIN-1 | transfer > 100 tis. Kč bez dohledaného usnesení nebo smlouvy | Indicie |
| R-FIN-2 | platby nebo vratky po zániku subjektu | Doloženo/Indicie |
| R-SML-1 | podíl smluv bez ceny > 30 % | Odvozeno |
| R-SML-2 | podpis smlouvy před schvalujícím usnesením | Indicie |
| R-SML-3 | dělení: stejný dodavatel a předmět do 90 dní, součet nad limitem VZMR | Indicie |
| R-KON-1 | koncentrace dodavatele > 40 % za 3 roky | Odvozeno |
| **R-VAZ-1** | osoba (párování přesné/odvozené) ve funkci u poskytovatele i příjemce téže smlouvy, dotace nebo transferu | Indicie |
| **R-VAZ-2** | zastupitel nebo radní hlasoval o usnesení ve prospěch subjektu, kde má funkci nebo podíl (bez ohlášeného střetu zájmů v zápisu) | Indicie |
| **R-VAZ-3** | dodavatel nebo příjemce, jehož statutár či společník je kandidát/zastupitel nebo s ním sdílí jiný subjekt | Indicie |
| **R-DAR-1** | dárce politické strany zastoupené v ZM je dodavatelem města do 24 měsíců od daru | Indicie |
| **R-INS-1** | smlouva nebo dotace subjektu v insolvenci | Doloženo |

**Skóre priority:** `závažnost × log10(částka + 10) × jistota párování`. Signál z „kandidátního“ párování osob se nevytváří.

## 6. „K prověření“ (interní, bez veřejné varianty)
- **Fronta podle priority** s filtry (kategorie, subjekt, osoba, akce, období, štítek, stav).
- **Karta signálu** obsahuje:
  - co nesedí,
  - otázku k vysvětlení,
  - částku a její typ,
  - mini-graf řetězce důkazů,
  - lokátory zdrojů,
  - „proč se to zobrazuje“,
  - historii.
- **Stavy:** nový → ověřuje se → vysvětleno / potvrzeno / zamítnuto. Stav mění jen vlastník.
- **Akce:**
  - poznámka a připojení dokumentu,
  - návrh žádosti dle zák. 106/1999 (jen vygeneruje text),
  - potvrzení nebo zamítnutí párování osob,
  - export podkladů k signálu (PDF/ZIP s důkazy) pro vlastní potřebu.
- **Upozornění:**
  - odznak nových signálů,
  - denní souhrn „co přibylo“ na úvodní obrazovce,
  - e-mail nebo push jen po schválení vlastníkem (mimo rozsah F1–F5).
- **Kvalita pravidel:** podíl zamítnutých signálů na pravidlo a slepý test (`ai/test/`). Žádný nový falešný signál v K-002/K-003.

## 7. Grafika
- **Design tokeny**, světlý a tmavý režim, kontrast ≥ 4,5 : 1.
- **Grafy:**
  - Sankey „město → příjemci“,
  - časové osy akcí a osob,
  - síť vztahů (hrany podle jistoty: plná / čárkovaná / tečkovaná),
  - small multiples rozpočtu 2020–2026,
  - u každého grafu přepínač „Tabulka“.
- **Spojité časové osy.** Mezery v datech vyznač „neimportováno“ (dnes graf smluv skáče z 2020-06 na 2025-09).
- **Úvodní přehled:** KPI (rozpočet, transfery, smlouvy, nové signály), „co se změnilo“, top 5 položek k prověření.
- **Jména osob zobrazuj v plném znění všude**, s odkazem na profil osoby.

## 8. Fáze (každá = PR se štítkem `predani`)
1. **F0** – zabezpečení (§ 1). Kód ve vývoji, nasazení po schválení.
2. **F1** – model entit včetně osob, párování a API (`/api/entity`, `/api/links`, `/api/person/{id}`, `/api/signals`).
3. **F2** – finanční profil subjektu a oprava hodnot smluv. Akceptace: Vsetínská sportovní, transfer 2026 = 18 298 000 Kč.
4. **F3** – nové zdroje z § 3, postupně: VR full → zápisy ZM → volby → ostatní.
5. **F4** – pravidla z § 5. Akceptace: R-RO-1 a R-RO-2 vrátí signály z PR #16.
6. **F5** – „K prověření“, profil osoby, síť vztahů a grafika.

## 9. Testy a výstup každé fáze
- Unit testy pravidel a párování (včetně testu, že shoda jen podle jména **nevytvoří** signál).
- `python3 scripts/ci_validate.py` zelený. Přístupnost (axe/pa11y), 360–1704 px. Výkon API < 500 ms.
- Test F0: anonymní požadavky vrací 401.
- **Report:**
  - změněné soubory,
  - skutečné výstupy testů,
  - co zůstalo neověřeno nebo blokováno a proč,
  - návrh nasazení a rollbacku (čeká na schválení).
