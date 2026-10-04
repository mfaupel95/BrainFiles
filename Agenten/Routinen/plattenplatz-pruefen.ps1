# Plattenplatz-Pruefung (Task 6 des Plans vom 30.09.2026, Vorfall T-228).
#
# BUS: Bibliothek - dieser Teilschritt ist KEIN eigener periodischer Lauf.
# Er wird ausschliesslich aus systempruefung.ps1 Abschnitt 7b gestartet
# (`& powershell -NoProfile -File $pp -OhneOrdner`, bei Warnung ohne den
# Schalter), und die geplante Aufgabe gehoert der Systempruefung
# (MaxHirn-Systempruefung) - eine eigene Plattenplatz-Aufgabe gibt es nicht.
# Die Bus-Meldung traegt deshalb die Systempruefung: eine eigene hier erzeugte
# wuerde denselben Befund ZWEIMAL ins Journal schreiben, weil die Datei bei
# Bedarf zweimal laeuft (schnell, dann mit Ordner). test_anbindung_routinen.py
# nimmt genau darum jede Datei mit dieser Kennzeichnung aus - die Ausnahme
# steht in der Datei selbst und ist damit sichtbar.
#
# Meldet freien Platz je Laufwerk, den freien Commit (Commit-Grenze minus
# zugesagter Speicher) und die drei groessten Wachstumsordner auf C:.
# Warnt bei C: unter 60 GB frei oder freiem Commit unter 10 GB.
#
# Rein lesend. Ausgabe: je Zeile "WARN ..." oder "INFO ...". Exitcode 1 bei
# mindestens einer Warnung, sonst 0. Laeuft in Windows PowerShell 5.1 und 7.
# Eingehaengt in systempruefung.ps1, Abschnitt 7.
#
# -OhneOrdner ueberspringt die Ordnermessung (schnell, nur Laufwerke/Commit).

param([switch]$OhneOrdner)

$ErrorActionPreference = 'Continue'
$warnC      = 60   # GB frei auf C:
$warnCommit = 10   # GB freier Commit
$warnungen  = 0

function Zeile($art, $text) { Write-Output "$art $text"; if ($art -eq 'WARN') { $script:warnungen++ } }

# Verzeichnisgroesse ohne Junctions/Symlinks; unlesbare Ordner zaehlen 0.
function OrdnerGb($pfad) {
  $summe = [long]0
  $stapel = [System.Collections.Generic.Stack[string]]::new()
  $stapel.Push($pfad)
  while ($stapel.Count -gt 0) {
    $d = $stapel.Pop()
    try {
      $di = [System.IO.DirectoryInfo]::new($d)
      foreach ($f in $di.EnumerateFiles()) { $summe += $f.Length }
      foreach ($u in $di.EnumerateDirectories()) {
        if (-not ($u.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) { $stapel.Push($u.FullName) }
      }
    } catch { }
  }
  [math]::Round($summe / 1GB, 2)
}

# 1) Laufwerke
foreach ($bst in 'C', 'O', 'G') {
  $dv = Get-PSDrive -Name $bst -ErrorAction SilentlyContinue
  if (-not $dv) { Zeile 'INFO' "Laufwerk ${bst}: nicht vorhanden."; continue }
  $frei = [math]::Round($dv.Free / 1GB, 1)
  if ($bst -eq 'C' -and $frei -lt $warnC) { Zeile 'WARN' "Laufwerk C: nur $frei GB frei (Warnschwelle $warnC GB)." }
  else { Zeile 'INFO' "Laufwerk ${bst}: $frei GB frei." }
}

# 2) Commit (Vorfall 30.09.: Commit-Grenze erreicht, Fehler 0xc000012d)
$os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
if ($os) {
  $grenze = [math]::Round($os.TotalVirtualMemorySize / 1MB, 1)
  $frei   = [math]::Round($os.FreeVirtualMemory / 1MB, 1)
  if ($frei -lt $warnCommit) { Zeile 'WARN' "Commit: nur $frei GB frei von $grenze GB (Warnschwelle $warnCommit GB) - Auslagerungsdatei pruefen." }
  else { Zeile 'INFO' "Commit: $frei GB frei von $grenze GB." }
} else { Zeile 'INFO' 'Commit: nicht lesbar.' }

# 3) Wachstumsordner auf C: (feste Kandidaten, die erfahrungsgemaess wachsen)
if (-not $OhneOrdner) {
  $nutzer = $env:USERPROFILE
  $kandidaten = @(
    "$nutzer\AppData\Local\Temp", "$nutzer\AppData\Local\Docker", "$nutzer\AppData\Local\Packages",
    "$nutzer\AppData\Local\npm-cache", "$nutzer\AppData\Local\pip", "$nutzer\AppData\Local\uv",
    "$nutzer\AppData\Roaming\Claude", "$nutzer\.cache", "$nutzer\.claude", "$nutzer\.docker",
    "$nutzer\.ollama", "$nutzer\.lmstudio", "$env:ProgramData\Docker", "$env:SystemRoot\Temp"
  )
  $mess = foreach ($k in $kandidaten) {
    if (Test-Path -LiteralPath $k) { [pscustomobject]@{ Pfad = $k; Gb = (OrdnerGb $k) } }
  }
  $mess | Sort-Object Gb -Descending | Select-Object -First 3 | ForEach-Object {
    Zeile 'INFO' ("Gross: {0} GB  {1}" -f $_.Gb, $_.Pfad.Replace($nutzer, '~'))
  }
}

if ($warnungen -gt 0) { exit 1 } else { exit 0 }
