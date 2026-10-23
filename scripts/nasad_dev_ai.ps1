<#
.SYNOPSIS
  VSETIN OSINT - nasazeni AI analytiky na DEV server (schvaleno vlastnikem 2026-10-23, rozsah jen dev).

.DESCRIPTION
  Spousti se na tvem Windows PC. Pres SSH provede na dev serveru:
    kontrola -> klon/aktualizace repa -> venv (pypdf, jsonschema) -> testy -> beh nanecisto
    -> overeni prav k push -> ostry beh -> cron (pracovni dny 05:47 Europe/Prague, se zalohou crontabu).
  Predtim (volitelne) mergne PR #5 pod tvym GitHub uctem (gh CLI).
  Nikdy nesaha na /opt (produkci), produkcni DB, Docker, restart sluzeb ani apt. Lze spustit opakovane.

.PARAMETER Server
  SSH cil, napr. administrator@nasvsetin.cz nebo administrator@10.0.0.5

.EXAMPLE
  .\nasad_dev_ai.ps1 -Server administrator@nasvsetin.cz
.EXAMPLE
  .\nasad_dev_ai.ps1 -Server administrator@nasvsetin.cz -JenNanecisto
.EXAMPLE
  .\nasad_dev_ai.ps1 -Server administrator@nasvsetin.cz -GitHubTokenSoubor C:\tajne\gh_token.txt
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [int]$Port = 22,
    [string]$Klon = '/home/administrator/datamestovsetin',
    [string]$DevDir = '/home/administrator/vsetin-osint-dev',
    [switch]$JenNanecisto,      # jen kontrola + beh nanecisto, bez ostreho behu a cronu
    [switch]$BezCronu,          # neinstalovat cron
    [switch]$BezMerge,          # nemergovat PR #5 (napr. uz je mergnuty)
    [string]$GitHubTokenSoubor  # soubor s GitHub tokenem (jen repo datamestovsetin) -> $DevDir/.env.github, prava 600
)

$ErrorActionPreference = 'Stop'
$Repo = 'adamczeko-ai/datamestovsetin'
$Log = Join-Path (Get-Location) ('nasazeni-dev-{0:yyyyMMdd-HHmmss}.log' -f (Get-Date))
Start-Transcript -Path $Log | Out-Null

function Krok($t) { Write-Host "`n### $t" -ForegroundColor Cyan }

try {
    Krok 'Kontrola nastroju na tomto PC'
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
        throw 'Chybi ssh. Windows: Nastaveni > Aplikace > Volitelne funkce > Klient OpenSSH.'
    }
    foreach ($p in @($Klon, $DevDir)) {
        if ($p -match '^/opt(/|$)') { throw "Cesta $p lezi v /opt (produkce) - odmitnuto." }
    }
    $sshArgs = @('-T', '-p', "$Port", $Server)

    if (-not $BezMerge) {
        Krok 'PR #5 (automatizace) -> main'
        if (Get-Command gh -ErrorAction SilentlyContinue) {
            $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'   # PS 5.1: stderr nativniho prikazu nesmi shodit skript
            $stav = gh pr view 5 -R $Repo --json state --jq '.state' 2>$null
            $ErrorActionPreference = $prev
            if ($stav -eq 'OPEN') {
                Write-Host 'PR #5 je otevreny. Main je chraneny (1 schvaleni), vlastni PR schvalit nelze -> merge s --admin pod tvym uctem.'
                $ok = Read-Host 'Mergnout PR #5 ted? (a/n)'
                if ($ok -eq 'a') { gh pr merge 5 -R $Repo --merge --admin; if ($LASTEXITCODE) { throw 'gh pr merge selhal' } }
                else { throw 'Bez merge PR #5 neni na main skript dev_pipeline.sh - konec.' }
            } else { Write-Host "PR #5: $stav" }
        } else {
            Start-Process "https://github.com/$Repo/pull/5"
            Read-Host 'gh CLI neni nainstalovane. V otevrenem prohlizeci mergni PR #5 a stiskni Enter'
        }
    }

    if ($GitHubTokenSoubor) {
        Krok 'GitHub token -> dev server (.env.github, prava 600)'
        $token = (Get-Content -Raw -Path $GitHubTokenSoubor).Trim()
        if ($token -notmatch '^(github_pat_|ghp_)[A-Za-z0-9_]+$') { throw 'Soubor neobsahuje GitHub token (github_pat_... / ghp_...).' }
        ("GITHUB_TOKEN=$token`n") | ssh @sshArgs "umask 077; mkdir -p '$DevDir'; cat > '$DevDir/.env.github'"
        if ($LASTEXITCODE) { throw 'Zapis tokenu na server selhal.' }
        Remove-Variable token
        Write-Host 'ulozeno'
    }

    Krok "Nasazeni na $Server (dev)"
    $bash = @'
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
'@ -replace "`r", ''
    $bash += "`n# konec"   # bez koncoveho LF: PowerShell 5.1 pripoji CRLF -> "\r" skonci v komentari
    $dry = if ($JenNanecisto) { 1 } else { 0 }
    $cron = if ($BezCronu -or $JenNanecisto) { 0 } else { 1 }
    $prikaz = "KLON='$Klon' DEV_DIR='$DevDir' DRY_ONLY=$dry CRON=$cron bash -s"
    $bash | ssh @sshArgs $prikaz
    $kod = $LASTEXITCODE

    Krok 'Souhrn posledniho behu (posledni_beh.json)'
    ssh @sshArgs "cat '$DevDir/data/analytika/posledni_beh.json' 2>/dev/null || echo 'souhrn neexistuje'"

    if ($kod -eq 0) { Write-Host "`nHOTOVO (exit 0). Log: $Log" -ForegroundColor Green }
    elseif ($kod -eq 2) { Write-Host "`nZASTAVENO bezpecnostni kontrolou (exit 2) - duvod je o par radku vyse (STOP: ...). Log: $Log" -ForegroundColor Yellow }
    else { Write-Host "`nCHYBA (exit $kod). Log: $Log" -ForegroundColor Red }
    exit $kod
}
catch {
    Write-Host "CHYBA: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
