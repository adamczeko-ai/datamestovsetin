#!/usr/bin/env bash
# VSETÍN OSINT – automatický běh AI analytiky na DEV serveru (schváleno vlastníkem 2026-10-23, rozsah: jen dev).
#
# Co dělá (v tomto pořadí):
#   1. aktualizuje klon repa na origin/main (jen fast-forward, klon musí být čistý)
#   2. spustí testy repa – když selžou, končí bez jakéhokoli zápisu
#   3. stáhne dokumenty města a uloží texty po stranách (python -m integrace dokumenty)
#   4. nové texty pošle jako PR z jediné větve data/texty-auto (přepisuje se; nikdy přímo do main)
#   5. spustí deterministickou analytiku (R1–R16, signály v2, export ověřených signálů)
#      do $DEV_DIR/data/analytika/ – soubory v repu vrátí do původního stavu
#   6. zapíše souhrn běhu do $DEV_DIR/data/analytika/posledni_beh.json
# Jazykový model zde NEběží – LLM vrstva je plánovaná úloha v Claude (varianta A), která čte repo.
#
# Nikdy: /opt, produkční DB, Docker, restart služeb, push do main.
# Použití:  KLON=/cesta/ke/klonu scripts/dev_pipeline.sh [--dry-run]
#   --dry-run = vše kromě push a založení PR
# Proměnné: DEV_DIR (výchozí /home/administrator/vsetin-osint-dev), KLON (povinné), SEZNAM, PY,
#           GITHUB_TOKEN nebo soubor $DEV_DIR/.env.github s řádkem GITHUB_TOKEN=… (jen pro PR), GITHUB_API (test)
set -Eeuo pipefail

DEV_DIR="${DEV_DIR:-/home/administrator/vsetin-osint-dev}"
KLON="${KLON:?Nastavte KLON = cesta ke klonu adamczeko-ai/datamestovsetin}"
REPO="adamczeko-ai/datamestovsetin"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

for p in "$DEV_DIR" "$KLON"; do
  rp="$(realpath -m "$p")"
  if [[ "$rp" == /opt || "$rp" == /opt/* ]]; then
    echo "ODMÍTNUTO: $p leží v /opt (produkce)"; exit 3
  fi
done

OUT="$DEV_DIR/data/analytika"
LOGDIR="$DEV_DIR/logs"
mkdir -p "$OUT" "$LOGDIR" "$DEV_DIR/data"
export INTEGRACE_DB="${INTEGRACE_DB:-$DEV_DIR/data/integrace.db}"
export INTEGRACE_CACHE="${INTEGRACE_CACHE:-$DEV_DIR/data/integrace_cache}"
DATUM="$(TZ=Europe/Prague date +%F)"
START="$(TZ=Europe/Prague date -Iseconds)"
LOG="$LOGDIR/ai-pipeline-$DATUM.log"
exec >>"$LOG" 2>&1

exec 9>"$DEV_DIR/.ai-pipeline.lock"
if ! flock -n 9; then echo "$START jiná instance běží – končím"; exit 0; fi

PY="${PY:-python3}"
[[ -x "$DEV_DIR/.venv-integrace/bin/python" && "${PY}" == "python3" ]] && PY="$DEV_DIR/.venv-integrace/bin/python"
SEZNAM="${SEZNAM:-data/integrace/dokumenty_seznam.txt}"

STAV="ok"; PR_URL=""; POZN=()
log() { echo "[$(TZ=Europe/Prague date +%T)] $*"; }
souhrn() {
  "$PY" - "$OUT/posledni_beh.json" "$START" "$STAV" "$PR_URL" "$DRY_RUN" "${POZN[@]+"${POZN[@]}"}" <<'EOF'
import json, sys, datetime, zoneinfo
out, start, stav, pr, dry, *pozn = sys.argv[1:]
konec = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")
json.dump({"schema": "vsetin-osint/dev-pipeline-beh@1", "zacatek": start, "konec": konec, "stav": stav,
           "pr": pr or None, "dry_run": dry == "1", "poznamky": pozn}, open(out, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
EOF
}
uklid() {  # vrátí klon do stavu před během (klon byl na začátku ověřeně čistý → mění se jen to, co vytvořil tento běh)
  [[ -d "$KLON/.git" ]] || return 0
  git -C "$KLON" reset -q --hard 2>/dev/null || true
  git -C "$KLON" clean -fdq -- raw/texty data/analyzy 2>/dev/null || true
  git -C "$KLON" checkout -q main 2>/dev/null || true
}
trap 'STAV="chyba"; POZN+=("neočekávaná chyba na řádku $LINENO"); uklid; souhrn; exit 1' ERR

log "=== start $START (dry_run=$DRY_RUN, python=$PY)"
cd "$KLON"
if [[ -n "$(git status --porcelain)" ]]; then
  STAV="chyba"; POZN+=("klon není čistý – nic se neprovádí"); log "${POZN[-1]}"; souhrn; exit 4
fi
git fetch -q origin main
git checkout -q main
git merge -q --ff-only origin/main
log "main = $(git rev-parse --short HEAD)"

# 2) testy – bez zelených testů se nic nezapisuje
if ! "$PY" -m unittest discover -s tests >"$LOGDIR/testy-$DATUM.log" 2>&1; then
  STAV="chyba"; POZN+=("testy selhaly – viz testy-$DATUM.log"); log "${POZN[-1]}"; souhrn; exit 5
fi
log "testy OK"

# 3) texty dokumentů
"$PY" scripts/seznam_dokumentu.py
if ! "$PY" -m integrace dokumenty --seznam "$SEZNAM" --texty raw/texty >"$OUT/dokumenty_vysledek.json"; then
  POZN+=("stahování dokumentů hlásí chybu – viz dokumenty_vysledek.json"); STAV="varovani"
fi
log "dokumenty: $(tr -d '\n ' <"$OUT/dokumenty_vysledek.json" | grep -o '"nove_texty":[0-9]*' || true)"

# 4) PR s novými texty
if [[ -n "$(git status --porcelain -- raw/texty data/integrace/dokumenty_seznam.txt)" ]]; then
  BR="data/texty-auto"   # jedna větev = jeden otevřený PR, který se každým během aktualizuje
  git checkout -q -B "$BR"
  git add raw/texty data/integrace/dokumenty_seznam.txt
  ID=()  # identita pro commit, jen když ji klon nemá nastavenou
  [[ -n "$(git config user.email || true)" ]] || ID=(-c "user.name=VSETIN OSINT dev pipeline" -c "user.email=noreply@nasvsetin.cz")
  git "${ID[@]+"${ID[@]}"}" commit -q -m "data: texty dokumentů po stranách (automaticky, dev $DATUM)"
  if [[ "$DRY_RUN" == 1 ]]; then
    POZN+=("dry-run: commit na $BR, bez push a PR")
  else
    git push -q -f origin "$BR"   # větev data/texty-auto patří jen této úloze
    TOKEN="${GITHUB_TOKEN:-}"
    [[ -z "$TOKEN" && -f "$DEV_DIR/.env.github" ]] && TOKEN="$(sed -n 's/^GITHUB_TOKEN=//p' "$DEV_DIR/.env.github")"
    if [[ -z "$TOKEN" ]]; then
      POZN+=("větev $BR pushnuta, PR nezaložen – chybí GITHUB_TOKEN"); STAV="varovani"
    else
      API="${GITHUB_API:-https://api.github.com}/repos/$REPO/pulls"
      H=(-H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json")
      if ! PR_URL="$(curl -fsS "${H[@]}" "$API?state=open&head=${REPO%%/*}:$BR" | "$PY" -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["html_url"] if d else "")')"; then
        PR_URL=""; POZN+=("větev $BR pushnuta, GitHub API nedostupné nebo token neplatný – PR nezaložen"); STAV="varovani"
      elif [[ -z "$PR_URL" ]]; then
        BODY="$("$PY" -c 'import json,sys; print(json.dumps({"title": "Texty dokumentů po stranách (automaticky z dev serveru)", "head": sys.argv[2], "base": "main", "body": f"Automatický běh scripts/dev_pipeline.sh na dev serveru (založeno {sys.argv[1]}); větev se každým během přepíše aktuálním stavem. Obsah: raw/texty/<sha256>/p<N>.txt + meta.json. Testy před během prošly. Výsledek stahování: data/analytika/dokumenty_vysledek.json na dev serveru."}))' "$DATUM" "$BR")"
        if ! PR_URL="$(curl -fsS "${H[@]}" -X POST "$API" -d "$BODY" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["html_url"])')"; then
          PR_URL=""; POZN+=("založení PR selhalo – větev $BR je pushnutá"); STAV="varovani"
        fi
      fi
      log "PR: $PR_URL"
    fi
  fi
  git checkout -q main
else
  log "žádné nové texty"
fi

# 5) deterministická analytika do $OUT (repo se vrátí do původního stavu)
"$PY" scripts/analyzy.py >/dev/null
"$PY" scripts/signaly_v2.py >/dev/null
"$PY" scripts/export_verejne_signaly.py "$OUT/verejne_signaly.json"
if ! "$PY" scripts/validate_schemas.py >"$OUT/validace.txt" 2>&1; then
  POZN+=("validace schémat hlásí chyby – viz validace.txt"); STAV="varovani"
fi
cp data/analyzy/signaly.json data/analyzy/red_flags.json data/analyzy/akce_timeline.json "$OUT/"
git checkout -q -- data/analyzy
git clean -fdq -- data/analyzy

souhrn
log "=== konec, stav=$STAV ${PR_URL}"
