<#
Zaehlt die sichtbaren Fenster dieses Desktops - und nennt auf Wunsch ihre Besitzer.

Anlass: "wieder viele Fenster offen" ist ohne Zahl nicht pruefbar. Ein Programm,
das je Klick ein Terminal oeffnet, sieht nach zwanzig Klicks wie ein Fehler aus,
ist aber nur eine Summe. Vor und nach einem Probelauf zaehlen: bleibt die Zahl
gleich, hat der Aufruf KEIN Fenster geoeffnet.

  powershell -NoProfile -File scripts/fenster-zaehlen.ps1
  powershell -NoProfile -File scripts/fenster-zaehlen.ps1 -Liste
  powershell -NoProfile -File scripts/fenster-zaehlen.ps1 -Prozess WindowsTerminal

Die Zahl steht als letzte Zeile ("Fenster: n"). Gezaehlt werden nur SICHTBARE
Fenster MIT Titel - leere Hilfsfenster wuerden sonst mitzaehlen.

FALLE: aus bash heraus NICHT als `powershell -Command "..."` einbetten - die
Shell frisst `$variable` und `$PID`, die Ausgabe ist verstuemmelt. Skript als
Datei schreiben, dann mit -File aufrufen.
#>
param(
  [switch]$Liste,
  [string]$Prozess = ''
)

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class FensterZaehler {
  public delegate bool Cb(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Cb p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int p);
}
'@

$gefunden = New-Object System.Collections.ArrayList
$cb = [FensterZaehler+Cb]{
  param($h, $l)
  if ([FensterZaehler]::IsWindowVisible($h)) {
    $text = New-Object Text.StringBuilder 512
    [void][FensterZaehler]::GetWindowTextW($h, $text, 512)
    if ($text.Length -gt 0) {
      $besitzer = 0
      [void][FensterZaehler]::GetWindowThreadProcessId($h, [ref]$besitzer)
      [void]$gefunden.Add([pscustomobject]@{ Titel = $text.ToString(); Pid = $besitzer })
    }
  }
  return $true
}
[void][FensterZaehler]::EnumWindows($cb, [IntPtr]::Zero)

$zeilen = @()
foreach ($f in $gefunden) {
  $p = Get-Process -Id $f.Pid -ErrorAction SilentlyContinue
  $name = '?'
  if ($p) { $name = $p.ProcessName }
  if ($Prozess -and $name -ne $Prozess) { continue }
  $zeilen += [pscustomobject]@{ Titel = $f.Titel; Pid = $f.Pid; Prozess = $name }
}

if ($Liste) {
  foreach ($z in $zeilen) {
    '{0,7}  {1,-18} {2}' -f $z.Pid, $z.Prozess, $z.Titel
  }
}
"Fenster: $($zeilen.Count)"
