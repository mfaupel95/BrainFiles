# Wird von der Windows-Aufgabenplanung taeglich aufgerufen.
#
# agent.py check schweigt, wenn nichts faellig ist - dann passiert auch hier
# nichts. Nur bei einer faelligen Tranche wird ins Log geschrieben und eine
# Sprechblase angezeigt.
#
# Bewusst PowerShell statt .cmd: Batch verschluckt Umlaute und meldet einen
# fehlenden Zwischenspeicher nicht zuverlaessig.

$ErrorActionPreference = 'Stop'
$hier = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $hier '.venv\Scripts\python.exe'
$agent = Join-Path $hier 'agent.py'
$log = Join-Path $hier 'check.log'

if (-not (Test-Path $python)) { exit 1 }

$ausgabe = & $python $agent check 2>&1 | Out-String
$ausgabe = $ausgabe.Trim()

if ([string]::IsNullOrWhiteSpace($ausgabe)) { exit 0 }

"[{0:yyyy-MM-dd HH:mm}] {1}`n" -f (Get-Date), $ausgabe |
    Add-Content -Path $log -Encoding UTF8

# Sprechblase im Infobereich. Ohne Zusatzsoftware und ohne erhoehte Rechte -
# msg.exe scheitert unter Windows Home mit "Zugriff verweigert".
try {
    Add-Type -AssemblyName System.Windows.Forms
    $icon = New-Object System.Windows.Forms.NotifyIcon
    $icon.Icon = [System.Drawing.SystemIcons]::Information
    $icon.BalloonTipTitle = 'DCA-Sparplan'
    $icon.BalloonTipText = ($ausgabe -split "`n" | Select-Object -First 3) -join "`n"
    $icon.Visible = $true
    $icon.ShowBalloonTip(20000)
    Start-Sleep -Seconds 12
    $icon.Dispose()
} catch {
    # Ohne Desktop-Sitzung (Task laeuft im Hintergrund) gibt es keine
    # Sprechblase. Das Log bleibt die verlaessliche Spur.
}
