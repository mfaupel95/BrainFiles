# Ein Fenster als PNG aufnehmen - auch wenn es verdeckt ist.
#
# Warum nicht ein einfaches Bildschirmfoto: das zeigt, was gerade obenauf liegt.
# PrintWindow zeichnet das Fenster selbst, auch verdeckt, und holt es nicht in
# den Vordergrund (der Bildschirm bleibt also unangetastet).
#
# Warum per EnumWindows und nicht per FindWindow: ein Titel mit Sonderzeichen
# (z. B. ".") kommt je nach Aufrufer verstuemmelt an, dann findet FindWindow
# nichts. Gesucht wird deshalb ueber den ANFANG des Titels.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File fenster-foto.ps1 -Titel "Zentrale - Repos"
#   powershell ... -Titel "Leitstand" -Ziel C:\temp\leitstand.png

param(
    [Parameter(Mandatory = $true)][string]$Titel,
    [string]$Ziel = "$env:TEMP\fenster.png"
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class F {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  public static IntPtr Finde(string anfang) {
    IntPtr fund = IntPtr.Zero;
    EnumWindows((h, l) => {
      if (!IsWindowVisible(h)) return true;
      var sb = new StringBuilder(512);
      GetWindowText(h, sb, 512);
      if (sb.ToString().StartsWith(anfang)) { fund = h; return false; }
      return true;
    }, IntPtr.Zero);
    return fund;
  }
}
"@

$h = [F]::Finde($Titel)
if ($h -eq [IntPtr]::Zero) {
    Write-Output "FENSTER NICHT GEFUNDEN: '$Titel'"
    exit 3
}

$r = New-Object F+RECT
[void][F]::GetWindowRect($h, [ref]$r)
$b = $r.R - $r.L
$hh = $r.B - $r.T
if ($b -le 0 -or $hh -le 0) {
    Write-Output "FENSTER OHNE FLAECHE: ${b}x${hh} - minimiert?"
    exit 4
}

$bmp = New-Object System.Drawing.Bitmap $b, $hh
$g = [System.Drawing.Graphics]::FromImage($bmp)
$dc = $g.GetHdc()
# Flag 2 = PW_RENDERFULLCONTENT, sonst bleiben manche Oberflaechen leer.
[void][F]::PrintWindow($h, $dc, 2)
$g.ReleaseHdc($dc)
$bmp.Save($Ziel, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()

Write-Output "Fenster $($h.ToInt64()): ${b}x${hh} bei $($r.L),$($r.T)"
Write-Output "gespeichert: $Ziel"
