# Fensterzahl zaehlen - vor und nach einem Klick.
#
# Zweck: eine Behauptung wie "wt -w 0 oeffnet kein neues Fenster" messen statt
# glauben. Aufruf ueber das terminal-Werkzeug:
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File fenster_zaehlen.ps1
#   powershell ... -File fenster_zaehlen.ps1 -Prozess WindowsTerminal
#
# -Prozess filtert auf einen Programmnamen (ohne .exe, Teiltreffer).
# Ausgabe: eine Zeile je sichtbarem Fenster, dann die Anzahl. Es wird NICHTS
# gestartet oder beendet.
#
# ZWEI FALLEN, beide am 30.09.2026 erlebt:
# (1) `GetWindowTextW` OHNE `CharSet = CharSet.Unicode` liefert EIN Zeichen je
#     Fenster ("Claude" -> "C"): die W-Funktion schreibt UTF-16, .NET marshallt
#     aber ANSI und bricht am ersten Null-Byte ab. Der Zaehler stimmt dann, die
#     Titel sind unbrauchbar - ein Fehler, der wie ein Anzeigeproblem aussieht.
# (2) Format-Table bestimmt Spaltenbreiten aus der Konsolenbreite - in einem
#     nicht-interaktiven Host (Hermes-terminal) kam dabei eine 1 Zeichen breite
#     Spalte heraus. Deshalb feste Formatierung mit -f.
# (3) Ein Hashtable, der in einer Pipeline gefuellt wird, war hier leer - die
#     Prozessspalte stand voller "?". Deshalb eine foreach-Schleife und
#     ContainsKey mit [int]-Schluessel.
#
# Merksatz: in einem Scriptblock-Delegate (EnumWindows-Callback) geht die
# Ausgabe verloren (Write-Output/Zeichenketten) - nur Seiteneffekte (Liste,
# $script:-Variable) kommen an.

param([string]$Prozess = '')

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class FensterZahl {
  public delegate bool Cb(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Cb p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, out int p);
}
'@

$liste = New-Object System.Collections.ArrayList
$cb = [FensterZahl+Cb]{
  param($h, $l)
  if ([FensterZahl]::IsWindowVisible($h)) {
    $sb = New-Object Text.StringBuilder 512
    [void][FensterZahl]::GetWindowTextW($h, $sb, 512)
    if ($sb.Length -gt 0) {
      $pr = 0
      [void][FensterZahl]::GetWindowThreadProcessId($h, [ref]$pr)
      [void]$liste.Add([pscustomobject]@{ Titel = $sb.ToString(); Pid = [int]$pr })
    }
  }
  return $true
}
[void][FensterZahl]::EnumWindows($cb, [IntPtr]::Zero)

$prozesse = @{}
foreach ($p in (Get-CimInstance Win32_Process)) { $prozesse[[int]$p.ProcessId] = $p.Name }

$gezeigt = 0
foreach ($f in $liste) {
  $name = if ($prozesse.ContainsKey($f.Pid)) { $prozesse[$f.Pid] } else { '?' }
  if ($Prozess -and ($name -notlike "*$Prozess*")) { continue }
  $titel = $f.Titel -replace '\s+', ' '
  if ($titel.Length -gt 52) { $titel = $titel.Substring(0, 52) }
  "{0,-7} {1,-24} {2}" -f $f.Pid, $name, $titel
  $gezeigt++
}
""
if ($Prozess) { "Sichtbare Fenster von *$Prozess*: $gezeigt" }
else { "Sichtbare Fenster: $gezeigt" }
