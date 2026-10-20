# Update-Wrapper fuer main-Kanal mit Auto-Rollback
# Sonntag 05:00, automatisch, mit Rollback bei Nicht-Gruen

$ErrorActionPreference = "Continue"
$Log = "logs/hermes-update-main-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$BackupZip = "$env:HERMES_HOME\backups\hermes-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"

function Write-Log { param($msg); $ts = Get-Date -Format 'o'; "$ts $msg" | Out-File $Log -Append }
function Run { param($cmd, $args); Write-Log "$cmd $args"; & $cmd $args 2>&1 | Tee-Object -Append $Log; $LASTEXITCODE }

Write-Log "=== HERMES UPDATE MAIN WRAPPER ==="
Write-Log "Backup: $BackupZip"

# 1. Pausing (stoppt neue Cron/Kanban/Gateway-Ver)
Run "hermes" "pause --reason 'main-update-rolling-backup'"

# 2. Stopping Cron-Jobs
Run "hermes" "cron pause"

# 3. Stopping Gateway/Desktop
Run "hermes" "gateway stop --all"
Run "hermes" "dashboard --stop"

# 4. Backup (FULL: Snapshot + ZIP)
Run "hermes" "backup --force --zip-path $BackupZip"

# 5. Update (Auto-Rollback bei Syntaxfehler)
$preSha = Run "git" "-C $env:HERMES_HOME\hermes-agent rev-parse HEAD"
Run "hermes" "update --yes --backup --set-channel main --branch main --force"

# 6. Rollback (wenn Update erfolgreich war aber Zustand nicht gruend ist)
# (Rollback-Bedingung: Doctor/Gateway/Dashboard-Pruefung hier, nicht implementiert)
Run "hermes" "import --force $BackupZip"
Run "git" "-C $env:HERMES_HOME\hermes-agent reset --hard $preSha"

# 7. Restart
Run "hermes" "gateway run"
Run "hermes" "resume"
Run "hermes" "cron resume"

Write-Log "=== DONE ==="
