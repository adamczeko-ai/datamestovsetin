#!/usr/bin/env bash
# VSETIN OSINT - prvni zivy beh balicku integrace/ na DEV serveru + akceptace + kontrola idempotence.
# Spousti se NA SERVERU (ssh). Idempotentni - lze spustit opakovane.
# Kroky: kontrola -> klon/aktualizace -> offline testy -> beh 1 -> beh 2 (nic se nesmi stahnout znovu)
#        -> akceptace (JSON report) -> souhrn.
# Nikdy: /opt, produkcni DB, Docker, restart sluzeb, cron, apt, push. Zapisuje jen do $DEV_DIR/data/integrace*.
# Promenne:
#   DEV_DIR   (vychozi /home/administrator/vsetin-osint-dev)
#   KLON      (vychozi /home/administrator/datamestovsetin)
#   VETEV     (vychozi main; pro test PR pred mergem napr. claude/2026-10-23-integrace-akceptace)
#   RVZ_OD=2024  zpetne doplneni RVZ (22 souboru, ~2,5 GB stahovani, jednou) - VYCHOZI VYPNUTO, jen posledni mesic
#   MONITOR_OD   (vychozi 2020)
#   JEN_TESTY=1  jen offline testy, bez sitovych behu
set -Eeuo pipefail

DEV_DIR="${DEV_DIR:-/home/administrator/vsetin-osint-dev}"
KLON="${KLON:-/home/administrator/datamestovsetin}"
VETEV="${VETEV:-main}"
REPO_URL="${REPO_URL:-https://github.com/adamczeko-ai/datamestovsetin.git}"
RVZ_OD="${RVZ_OD:-}"
MONITOR_OD="${MONITOR_OD:-2020}"
JEN_TESTY="${JEN_TESTY:-0}"

krok() { echo; echo "=== $* ==="; }
stop() { echo "STOP: $*"; exit 2; }

krok "1/7 Kontrola prostredi"
for p in "$DEV_DIR" "$KLON"; do
  rp="$(realpath -m "$p")"
  [[ "$rp" == /opt || "$rp" == /opt/* ]] && stop "$p lezi v /opt (produkce) - odmitnuto"
done
[[ -d "$DEV_DIR" ]] || stop "dev slozka $DEV_DIR neexistuje"
command -v git >/dev/null || stop "chybi git"
command -v python3 >/dev/null || stop "chybi python3"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || stop "python3 je starsi nez 3.10"
command -v flock >/dev/null || stop "chybi flock (util-linux)"
mkdir -p "$DEV_DIR/data"
export INTEGRACE_DB="$DEV_DIR/data/integrace.db"
export INTEGRACE_CACHE="$DEV_DIR/data/integrace_cache"
[[ "$(realpath -m "$INTEGRACE_DB")" == /opt/* ]] && stop "INTEGRACE_DB v /opt - odmitnuto"
exec 9>"$DEV_DIR/data/.integrace.lock"
flock -n 9 || stop "jiny beh integrace prave probiha (zamek $DEV_DIR/data/.integrace.lock)"
echo "uzivatel: $(id -un) | $(python3 --version 2>&1) | DB: $INTEGRACE_DB"
echo "volne misto v $DEV_DIR: $(df -h --output=avail "$DEV_DIR" | tail -1)"

krok "2/7 Klon repa ($VETEV)"
if [[ -d "$KLON/.git" ]]; then
  [[ -z "$(git -C "$KLON" status --porcelain --untracked-files=no)" ]] || stop "klon $KLON obsahuje neulozene zmeny - nic nemenim"
  git -C "$KLON" fetch -q origin "$VETEV"
  git -C "$KLON" checkout -q "$VETEV" 2>/dev/null || git -C "$KLON" checkout -q -b "$VETEV" "origin/$VETEV"
  git -C "$KLON" merge -q --ff-only "origin/$VETEV"
else
  git clone -q -b "$VETEV" "$REPO_URL" "$KLON"
fi
cd "$KLON"
echo "$VETEV = $(git rev-parse --short HEAD)"
[[ -f integrace/akceptace.py ]] || stop "integrace/akceptace.py ve vetvi $VETEV chybi - nejdriv mergnout PR"
INT() { PYTHONPATH="$KLON" python3 -m integrace "$@"; }

krok "3/7 Offline testy"
python3 -W ignore -m unittest discover -s tests 2>&1 | tail -n 3
python3 -W ignore -m unittest discover -s tests >/dev/null 2>&1 || stop "testy selhaly - zivy beh nespoustim"
[[ "$JEN_TESTY" == "1" ]] && { echo "JEN_TESTY=1 - konec"; exit 0; }

VERZE="$(mktemp)"; trap 'rm -f "$VERZE"' EXIT
echo 38540900 > "$VERZE"   # jedna verze registru smluv pro akceptaci value_kind

beh() {  # $1 = cislo behu
  local n="$1" rc=0
  krok "$((n + 3))/7 Zivy beh $n"
  INT monitor --od "$MONITOR_OD" > "$DEV_DIR/data/integrace_beh${n}_monitor.json" || rc=1
  INT ruian                      > "$DEV_DIR/data/integrace_beh${n}_ruian.json"   || rc=1
  INT vr                         > "$DEV_DIR/data/integrace_beh${n}_vr.json"      || rc=1
  INT smlouvy --verze-soubor "$VERZE" > "$DEV_DIR/data/integrace_beh${n}_smlouvy.json" || rc=1
  if [[ -n "$RVZ_OD" ]]; then
    INT rvz --od "$RVZ_OD"       > "$DEV_DIR/data/integrace_beh${n}_rvz.json"     || rc=1
  else
    INT rvz                      > "$DEV_DIR/data/integrace_beh${n}_rvz.json"     || rc=1
  fi
  for f in "$DEV_DIR"/data/integrace_beh"${n}"_*.json; do
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["zdroj"].ljust(8), d["stav"])' "$f" || echo "$f: neplatny JSON"
  done
  return $rc
}
beh 1 || echo "VAROVANI: nektery zdroj v behu 1 skoncil chybou (viz integrace_beh1_*.json); pokracuji"
beh 2 || echo "VAROVANI: nektery zdroj v behu 2 skoncil chybou"

krok "6/7 Akceptace"
TS="$(date -u +%Y%m%dT%H%MZ)"
REP="$DEV_DIR/data/integrace_akceptace_$TS.json"
set +e; INT akceptace > "$REP"; ARC=$?; set -e
python3 - "$REP" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for k in d["kontroly"]:
    print(f'{k["vysledek"]:10} {k["id"]:28} ocekavano={k.get("ocekavano")} zjisteno={k.get("zjisteno")}')
print(f'\nok={d["ok"]} selhalo={d["selhalo"]} nespusteno={d["nespusteno"]} info={d["info"]}')
PY

krok "7/7 Stav evidence"
INT stav | head -n 60
echo
echo "Report: $REP"
echo "Nic nebylo nasazeno do produkce, cron nezalozen, Docker beze zmeny."
exit $ARC
