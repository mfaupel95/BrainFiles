# Audit aller fuenf Windows-Startwege. REIN LESEND - schreibt nichts.
#
# Aufruf (Host-PowerShell, 5.1 genuegt):
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File startup-audit.ps1
#
# Entscheidet die eine Frage, die in diesem Bereich alles entscheidet:
# "Fuehrt Windows diese Datei/diesen Wert aus?" - nicht "ist die Datei da?".
#
# PS-5.1-Fallen, die hier bewusst vermieden sind:
#   - $pid ist schreibgeschuetzt, niemals als Schleifenvariable
#   - kein Get-FileHash (fehlt in 5.1)
#   - kein netstat-Parse ("ABHOEREN" mit Umlaut)

$ErrorActionPreference = 'Continue'
$OutputEncoding = [Console]::OutputEncoding

function Kopf($t) {
  ""
  "=== $t ==="
}

# --------------------------------------------------------------- 1 Startup-Ordner
Kopf '1) Startup-Ordner (Nutzer) - jede Datei wird ausgefuehrt'

$sc = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
if (Test-Path -LiteralPath $sc) {
  # WICHTIG: Ein Unterordner wird NICHT ausgefuehrt - sein Inhalt ist der
  # sichere Ablageort fuer abgeschaltete Eintraege. Deshalb wird die Tiefe
  # unterschieden: nur Dateien DIREKT im Startup-Ordner sind ein Befund.
  # Ohne diese Unterscheidung meldet der Audit die korrekt abgelegten
  # Dateien als gefaehrlich - der Audit darf sich nicht selbst widersprechen.
  $ebene0 = @(Get-ChildItem -LiteralPath $sc -Force -ErrorAction SilentlyContinue)
  if ($ebene0.Count -eq 0) { '  (leer)' }

  foreach ($e in $ebene0) {
    if ($e.PSIsContainer) {
      $drin = @(Get-ChildItem -LiteralPath $e.FullName -Force -ErrorAction SilentlyContinue)
      if ($drin.Count -eq 0) {
        "  [Ordner  ] $($e.Name)  (leer)"
      } else {
        "  [sicher  ] $($e.Name)\  <- Unterordner: $($drin.Count) Datei(en) hier abgelegt, wird NICHT ausgefuehrt"
        foreach ($d in $drin) { "               - $($d.Name)" }
      }
      continue
    }
    $name = $e.Name
    if ($name -eq 'desktop.ini') {
      "  [egal    ] $name  (Systemdatei, fuehrt Windows nie aus)"
      continue
    }
    $ext = $e.Extension.ToLowerInvariant()
    $echt = @('.lnk', '.url', '.vbs', '.exe', '.bat', '.cmd', '.ps1', '.msc', '.scf')
    if ($echt -contains $ext) {
      "  [startet ] $name"
    } else {
      # Unbekannte Endung: Windows oeffnet sie mit dem Standardprogramm
      # (im Haus: Notepad). Umbenennen hat sie nicht deaktiviert.
      "  [!! Datei ] $name  <- unbekannte Endung '$ext', wird OEFNEN statt starten"
    }
  }
} else {
  "  Startup-Ordner nicht gefunden: $sc"
}

Kopf '1b) Startup-Ordner (alle Benutzer)'
$scAll = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\StartUp'
if (Test-Path -LiteralPath $scAll) {
  @(Get-ChildItem -LiteralPath $scAll -Force -ErrorAction SilentlyContinue) |
    ForEach-Object { "  $($_.Name)" }
}

# ------------------------------------------------------------------- 2 Run/RunOnce
Kopf '2) Registry: Run und RunOnce'
foreach ($root in @('HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion',
                    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion')) {
  foreach ($sub in @('Run', 'RunOnce')) {
    $k = Join-Path $root $sub
    $v = Get-ItemProperty -Path $k -ErrorAction SilentlyContinue
    if (-not $v) { continue }
    $props = $v.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' }
    if ($props.Count -eq 0) { continue }
    "  [$k]"
    foreach ($pr in $props) {
      $val = $pr.Value
      if ($null -eq $val) { $val = '(leer)' }
      "    $($pr.Name) = $val"
    }
  }
}

# --------------------------------------------------------------- 3 StartupApproved
Kopf '3) StartupApproved (bezieht sich auf den DATEINAMEN, nicht auf den Inhalt)'
foreach ($sub in @('StartupFolder', 'Run')) {
  $k = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\$sub"
  $v = Get-ItemProperty -Path $k -ErrorAction SilentlyContinue
  if (-not $v) { continue }
  "  [$sub]"
  $props = $v.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' }
  foreach ($pr in $props) {
    $b = $pr.Value
    if (-not $b) { "    $($pr.Name) = (kein Wert)"; continue }
    # 02 = freigegeben, 03 = gesperrt. 00 heisst "nicht gesetzt" und ist
    # KEIN Beweis fuer "laeuft" - nur der Prozess ist das.
    $zustand = switch ($b[0]) { 2 { 'freigegeben' } 3 { 'gesperrt' } default { "unbekannt(0x$('{0:x2}' -f $b[0]))" } }
    "    $($pr.Name) = $zustand"
  }
}

# --------------------------------------------------------------- 4 Logon-Aufgaben
Kopf '4) Geplante Aufgaben mit Logon-Trigger (Aktion auf Sichtbarkeit pruefen)'
$zeilen = @()
Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object {
  $t = $_
  $logon = $false
  $trigTxt = @()
  foreach ($tr in $t.Triggers) {
    if ($tr.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger') { $logon = $true }
    $d = $tr.Delay
    $trigTxt += "$($tr.CimClass.CimClassName)$(if ($d) { " Delay=$d" })"
  }
  if (-not $logon) { return }
  foreach ($a in $t.Actions) {
    $cmd = "$($a.Execute) $($a.Arguments)"
    # Konsolenprogramme ohne Hidden blitzen bei der Anmeldung als Fenster auf.
    $versteckt = ($cmd -match 'WindowStyle\s+Hidden') -or
                 ($a.Execute -match 'wscript|pythonw|\.vbs$') -or
                 ($cmd -match '//B')
    $zeilen += [PSCustomObject]@{
      Task   = $t.TaskName
      State  = $t.State
      Versteckt = $versteckt
      Trigger = ($trigTxt -join ' | ')
      Aktion  = $cmd
    }
  }
}
if ($zeilen.Count -eq 0) {
  '  (keine Logon-Aufgaben gefunden)'
} else {
  $zeilen | Sort-Object Task | Format-Table -AutoSize | Out-String -Width 400
}

# ------------------------------------------------------------------- 5 Prozesse
Kopf '5) Laufende Prozesse, deren Kommandozeile auf einen Startup-Pfad zeigt'
$treffer = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'Start Menu.+Startup' })
if ($treffer.Count -eq 0) {
  '  (keiner) - kein Startup-Eintrag laeuft gerade'
} else {
  foreach ($p in $treffer) {
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
    $parentName = if ($parent) { $parent.Name } else { '(beendet)' }
    "  PID $($p.ProcessId)  $($p.Name)"
    "     Kommandozeile: $($p.CommandLine)"
    "     Start: $($p.CreationDate)"
    "     Elternprozess: $parentName"
  }
}

Kopf '6) Auf einen Port lauschen (wer haengt wirklich dran)'
$port = 20128
try {
  $c = New-Object Net.Sockets.TcpClient
  $c.Connect('127.0.0.1', $port)
  $c.Close()
  "  Port $port ist BELEGT"
  # Get-NetTCPConnection ist der verlaessliche Leser; netstat nicht parsen.
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object {
      $owner = $_
      $pr = Get-CimInstance Win32_Process -Filter "ProcessId=$($owner.OwningProcess)" -ErrorAction SilentlyContinue
      "  PID $($owner.OwningProcess) $($pr.Name)"
      "     $($pr.CommandLine)"
    }
} catch {
  "  Port $port ist frei"
}

""
"=== Merksatz ==="
"Umbenennen deaktiviert einen Startup-Eintrag NICHT. Windows fuehrt jede Datei"
"im Startup-Ordner aus; eine unbekannte Endung wird mit dem Standardprogramm"
"geoeffnet (Notepad). Richtig ist: in einen Unterordner verschieben."
"Umbenennen gilt nur fuer Registry-Werte unter ...\CurrentVersion\Run."