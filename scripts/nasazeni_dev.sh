#!/usr/bin/env bash
# VSETIN OSINT - nasazeni AI analytiky na DEV server (schvaleno vlastnikem 2026-10-23, rozsah jen dev).
# Spousti se na serveru (posila ho nasad_dev_ai.ps1 pres ssh). Idempotentni - lze spustit opakovane.
# Kroky: kontrola -> klon/aktualizace -> venv (pypdf, jsonschema) -> testy -> dry-run pipeline
#        -> overeni prav k push -> ostry beh -> cron (s zalohou crontabu).
# Nikdy: /opt, produkcni DB, Docker, restart sluzeb, apt, push do main.
# Promenne: KLON, DEV_DIR, REPO_URL, DRY_ONLY=1 (jen dry-run, bez cronu), CRON=0 (bez cronu)
set -Eeuo pipefail

DEV_DIR="${DEV_DIR:-/home/administrator/vsetin-osint-dev}"
KLON="${KLON:-/home/administrator/datamestovsetin}"
REPO_URL="${REPO_URL:-https://github.com/adamczeko-ai/datamestovsetin.git}"
DRY_ONLY="${DRY_ONLY:-0}"
CRON="${CRON:-1}"
VENV="$DEV_DIR/.venv-integrace"
MARK="# VSETIN-OSINT dev AI pipeline"

krok() { echo; echo "=== $* ==="; }
stop() { echo "STOP: $*"; exit 2; }

krok "1/8 Kontrola prostredi"
for p in "$DEV_DIR" "$KLON"; do
  rp="$(realpath -m "$p")"
  [[ "$rp" == /opt || "$rp" == /opt/* ]] && stop "$p lezi v /opt (produkce) - odmitnuto"
done
[[ -d "$DEV_DIR" ]] || stop "dev slozka $DEV_DIR neexistuje"
command -v git >/dev/null || stop "chybi git"
command -v python3 >/dev/null || stop "chybi python3"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || stop "python3 je starsi nez 3.10"
command -v flock >/dev/null || stop "chybi flock (util-linux)"
echo "uzivatel: $(id -un), python: $(python3 --version 2>&1), pdftotext: $(command -v pdftotext || echo ne)"
echo "casova zona: $(cat /etc/timezone 2>/dev/null || readlink /etc/localtime || echo ?)"

krok "2/8 Klon repa"
if [[ -d "$KLON/.git" ]]; then
  [[ -z "$(git -C "$KLON" status --porcelain)" ]] || stop "klon $KLON obsahuje neulozene zmeny - nic nemenim"
  git -C "$KLON" fetch -q origin main
  git -C "$KLON" checkout -q main
  git -C "$KLON" merge -q --ff-only origin/main
else
  git clone -q "$REPO_URL" "$KLON"
fi
cd "$KLON"
echo "main = $(git rev-parse --short HEAD)"
[[ -x scripts/dev_pipeline.sh ]] || stop "scripts/dev_pipeline.sh na main chybi - nejdriv mergnout PR #5"

krok "3/8 Python prostredi (jen venv v dev slozce, zadne apt)"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" || stop "python3 -m venv selhal (chybi balicek python3-venv - instalace vyzaduje schvaleni)"
fi
"$VENV/bin/python" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
"$VENV/bin/python" -m pip install -q pypdf jsonschema || stop "pip install pypdf jsonschema selhal"
PY="$VENV/bin/python"
echo "venv: $("$PY" -c 'import pypdf, jsonschema; print("pypdf", pypdf.__version__, "| jsonschema OK")')"

krok "4/8 Testy"
"$PY" -m unittest discover -s tests 2>&1 | tail -n 3
"$PY" -m unittest discover -s tests >/dev/null 2>&1 || stop "testy selhaly"

krok "5/8 Zkusebni beh nanecisto (stahne dokumenty, nic nepushne)"
KLON="$KLON" DEV_DIR="$DEV_DIR" PY="$PY" scripts/dev_pipeline.sh --dry-run || true
cat "$DEV_DIR/data/analytika/posledni_beh.json"
grep -q '"stav": "chyba"' "$DEV_DIR/data/analytika/posledni_beh.json" && stop "dry-run skoncil chybou - viz $DEV_DIR/logs"
[[ -z "$(git status --porcelain)" ]] || stop "klon neni po behu cisty"
[[ "$DRY_ONLY" == 1 ]] && { echo "DRY_ONLY=1 - konec bez ostreho behu a cronu"; exit 0; }

krok "6/8 Prava k zapisu do repa"
PUSH_OK=0
# test prav na neexistujici vetvi (dry-run nic nevytvori); na data/texty-auto by mohl selhat jen kvuli non-fast-forward
if git push --dry-run -q origin HEAD:refs/heads/data/test-prav-zapisu >/dev/null 2>&1; then PUSH_OK=1; fi
TOKEN_OK=0; [[ -s "$DEV_DIR/.env.github" ]] && TOKEN_OK=1
echo "push: $PUSH_OK, GitHub token (.env.github): $TOKEN_OK"
[[ "$PUSH_OK" == 1 ]] || echo "VAROVANI: server nema pravo push - pipeline pobezi jen nanecisto (--dry-run)"

krok "7/8 Ostry beh"
if [[ "$PUSH_OK" == 1 ]]; then
  KLON="$KLON" DEV_DIR="$DEV_DIR" PY="$PY" scripts/dev_pipeline.sh || true
  cat "$DEV_DIR/data/analytika/posledni_beh.json"
else
  echo "preskoceno (chybi pravo push)"
fi

krok "8/8 Cron (pracovni dny 05:47 Europe/Prague, nezavisle na zone serveru)"
if [[ "$CRON" != 1 ]]; then
  echo "CRON=0 - preskoceno"
else
  ARG=""; [[ "$PUSH_OK" == 1 ]] || ARG=" --dry-run"
  RADEK="47 * * * 1-5 [ \"\$(TZ=Europe/Prague date +\\%H)\" = \"05\" ] && KLON=$KLON DEV_DIR=$DEV_DIR PY=$PY $KLON/scripts/dev_pipeline.sh$ARG"
  ZAL="$HOME/crontab.zaloha-$(date +%Y%m%d-%H%M%S)"
  crontab -l >"$ZAL" 2>/dev/null || : >"$ZAL"
  echo "zaloha crontabu: $ZAL"
  { grep -vF "$MARK" "$ZAL" | grep -vF "scripts/dev_pipeline.sh" || true; echo "$MARK (schvaleno 2026-10-23)"; echo "$RADEK"; } | crontab -
  echo "--- crontab -l (posledni 3 radky)"; crontab -l | tail -n 3
fi

echo
echo "HOTOVO. Souhrn: $DEV_DIR/data/analytika/posledni_beh.json, logy: $DEV_DIR/logs/"
echo "Rollback: crontab <zaloha>  (a pripadne rm -rf $DEV_DIR/data/analytika $VENV)"
