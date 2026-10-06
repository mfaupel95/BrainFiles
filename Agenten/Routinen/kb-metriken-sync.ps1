# kb-metriken-sync.ps1
# Berechnet Spur-Metriken aus tracking.db und committed spur-metriken.json in den Vault.
# Aufrufen: alle 6h per Aufgabenplanung (Aufgabe: MaxHirn-KB-Metriken-Sync).
# Laeuft aus jedem Verzeichnis (lokalisiert sich selbst).

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$SCRIPT_DIR = $PSScriptRoot
$REPO_ROOT   = (Resolve-Path "$SCRIPT_DIR\..\.." ).Path
$HANDEL_DIR  = Join-Path $REPO_ROOT "Agenten\Handel"
$VENV        = Join-Path $HANDEL_DIR "scanner\.venv\Scripts\python.exe"
$ZIEL_JSON   = Join-Path $REPO_ROOT "MaxHirn\Wissen\KB\data\spur-metriken.json"

# Python-Umgebungsvariablen saeubern (verhindert venv-Konflikt unter MCP-Supervisor)
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

if (-not (Test-Path $VENV)) {
    Write-Warning "kb-metriken-sync: venv nicht gefunden ($VENV), abgebrochen."
    exit 1
}

# Snapshot berechnen und JSON schreiben
$py_code = @"
import sys, pathlib
sys.path.insert(0, r'$HANDEL_DIR')
from tracking import init_tracking, snapshot_sync, kb_snapshot_json
import pathlib

init_tracking()
# Alle bekannten Spuren
for spur in ['spur1', 'spur2']:
    snapshot_sync(spur)
kb_snapshot_json(pathlib.Path(r'$ZIEL_JSON'))
print('ok')
"@

$result = & $VENV -c $py_code 2>&1
if ($LASTEXITCODE -ne 0 -or $result -notmatch "ok") {
    Write-Warning "kb-metriken-sync: Python-Fehler: $result"
    exit 1
}

# JSON committen (nur wenn sich etwas geaendert hat)
Push-Location $REPO_ROOT
try {
    $status = git status --porcelain "MaxHirn/Wissen/KB/data/spur-metriken.json" 2>&1
    if ($status) {
        git add "MaxHirn/Wissen/KB/data/spur-metriken.json"
        git commit -m "kb-sync: Spur-Metriken aktualisiert $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        Write-Host "kb-metriken-sync: committed."
    } else {
        Write-Host "kb-metriken-sync: keine Aenderung, kein Commit."
    }
} finally {
    Pop-Location
}
