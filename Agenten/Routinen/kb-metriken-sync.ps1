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

# Bus-Anbindung (Hausmuster): jede geplante Routine meldet Start und Ende.
$agenten = Join-Path $REPO_ROOT 'Agenten'
. (Join-Path $agenten 'Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/kb-metriken-sync' `
           -Log 'Agenten/Routinen/logs/kb-metriken-sync-letzter-lauf.md'

if (-not (Test-Path $VENV)) {
    Write-Warning "kb-metriken-sync: venv nicht gefunden ($VENV), abgebrochen."
    Melde-Ende -Marke $marke -Code 1 -Text 'venv nicht gefunden'
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
for spur in ['scanner', 'xperp', 'llm_stunde', 'omnitrade2']:
    snapshot_sync(spur)
kb_snapshot_json(pathlib.Path(r'$ZIEL_JSON'))
print('ok')
"@

$result = & $VENV -c $py_code 2>&1
if ($LASTEXITCODE -ne 0 -or $result -notmatch "ok") {
    Write-Warning "kb-metriken-sync: Python-Fehler: $result"
    Melde-Ende -Marke $marke -Code 1 -Text "Python-Fehler: $result"
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

Melde-Ende -Marke $marke -Code 0 -Text 'ok' 
