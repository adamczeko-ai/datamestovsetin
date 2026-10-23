<!-- Protokol docs/PREDAVANI_MEZI_RELACEMI.md – u předávacích PR přidej štítek `predani` -->
## Co přináší
- 

## Soubory
- [ ] data: `data/<zdroj>/…`
- [ ] manifest se sha256 a ETag / Last-Modified
- [ ] kontrola `scripts/kontrola_<tema>.py` (exit 0)
- [ ] předávací zpráva `docs/HANDOFF_<datum>_<tema>.md` včetně oddílu *Návrh integrace*
- [ ] CHANGELOG (oddíl vložen před poslední oddíl)

## Ověření (skutečné výstupy)
```
python3 scripts/ci_validate.py
python3 scripts/kontrola_<tema>.py
```

## Štítky tvrzení
Doloženo / Odvozeno / Indicie / Hypotéza – indicie a hypotézy nejsou fakty.

## Návrh integrace
Konektor / tabulka / akceptační hodnoty:

## Otevřené otázky
- 
