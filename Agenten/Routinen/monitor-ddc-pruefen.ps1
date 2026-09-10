<#
.SYNOPSIS
    Prueft fuer jeden angeschlossenen Monitor, ob er ueber DDC/CI antwortet.

.DESCRIPTION
    Fragt jeden physischen Monitor direkt ueber dxva2.dll ab (dieselbe
    Schnittstelle, die PowerToys PowerDisplay benutzt):
      - Capability-Zeichenkette (Modell, unterstuetzte VCP-Codes)
      - Helligkeit (min/aktuell/max)
    Nur lesend. Keine Adminrechte noetig. Aendert nichts am Monitor.

    Hintergrund: Wissen/Hardware.md, Abschnitt "Monitore und PowerToys
    PowerDisplay". Die ASUS MG278 (DISPLAY2, in Windows "Generic PnP Monitor")
    liefert Stand 02.09.2026 nichts zurueck (Win32-Fehler 0xC0262583,
    ERROR_GRAPHICS_DDCCI_INVALID_DATA) und wird von PowerDisplay verworfen.

    Reihenfolge zum Beheben:
      1. Dieses Skript ausfuehren  -> Ausgangsstand festhalten.
      2. Am MG278-OSD: Menu > System Setup > DDC/CI > On (bzw. Enable).
      3. Hilft das nicht: MG278 ~30 s komplett vom Strom trennen (nicht nur
         Standby), DP-Kabel pruefen/tauschen, anderen DP-Eingang probieren.
      4. Dieses Skript erneut ausfuehren. Antwortet die MG278 jetzt, in
         PowerToys > PowerDisplay auf "Monitore aktualisieren" klicken.

.EXAMPLE
    Rechtsklick auf die Datei > "Mit PowerShell ausfuehren"
    oder:
        .\monitor-ddc-pruefen.ps1
#>

[CmdletBinding()]
param()

. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\Ereignis.ps1')      # neu
$marke = Melde-Start -Wer 'routine/monitor-ddc-pruefen'                 # neu
try {                                                                    # neu

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class DdcProbe {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int l,t,r,b; }
  [StructLayout(LayoutKind.Sequential)] public struct PHYSICAL_MONITOR {
    public IntPtr h;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string desc;
  }
  public delegate bool MonitorEnumProc(IntPtr hMon, IntPtr hdc, ref RECT r, IntPtr d);
  [DllImport("user32.dll")] public static extern bool EnumDisplayMonitors(IntPtr h, IntPtr c, MonitorEnumProc cb, IntPtr d);
  [DllImport("dxva2.dll", SetLastError=true)] public static extern bool GetNumberOfPhysicalMonitorsFromHMONITOR(IntPtr hMon, out uint n);
  [DllImport("dxva2.dll", SetLastError=true)] public static extern bool GetPhysicalMonitorsFromHMONITOR(IntPtr hMon, uint n, [Out] PHYSICAL_MONITOR[] arr);
  [DllImport("dxva2.dll", SetLastError=true)] public static extern bool GetCapabilitiesStringLength(IntPtr h, out uint len);
  [DllImport("dxva2.dll", SetLastError=true)] public static extern bool CapabilitiesRequestAndCapabilitiesReply(IntPtr h, StringBuilder s, uint len);
  [DllImport("dxva2.dll", SetLastError=true)] public static extern bool GetMonitorBrightness(IntPtr h, out uint min, out uint cur, out uint max);
  [DllImport("dxva2.dll", SetLastError=true)] public static extern bool DestroyPhysicalMonitor(IntPtr h);
}
"@

# EDID-Namen je aktiver Anzeige aus WMI (fuer die Zuordnung zum "Generic PnP Monitor")
$edid = @{}
try {
  Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID -ErrorAction Stop | ForEach-Object {
    $name = ($_.UserFriendlyName | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ }) -join ''
    $edid[$_.InstanceName] = $name
  }
} catch { }

if ($edid.Count) {
  Write-Host "Aktive Monitore laut WMI:" -ForegroundColor Cyan
  $edid.GetEnumerator() | ForEach-Object { "  {0,-22} {1}" -f $_.Value, $_.Key }
  Write-Host ""
}

$hmons = New-Object System.Collections.ArrayList
$cb = [DdcProbe+MonitorEnumProc] { param($hMon, $hdc, $r, $d) [void]$hmons.Add($hMon); return $true }
[void][DdcProbe]::EnumDisplayMonitors([IntPtr]::Zero, [IntPtr]::Zero, $cb, [IntPtr]::Zero)

$idx = 0
$ok = 0
$fail = 0
foreach ($hm in $hmons) {
  $idx++
  $n = 0
  [void][DdcProbe]::GetNumberOfPhysicalMonitorsFromHMONITOR($hm, [ref]$n)
  if ($n -lt 1) { continue }
  $arr = New-Object 'DdcProbe+PHYSICAL_MONITOR[]' $n
  [void][DdcProbe]::GetPhysicalMonitorsFromHMONITOR($hm, $n, $arr)
  foreach ($pm in $arr) {
    Write-Host ("==== HMONITOR #{0}  '{1}' ====" -f $idx, $pm.desc) -ForegroundColor Cyan
    $len = 0
    $okLen = [DdcProbe]::GetCapabilitiesStringLength($pm.h, [ref]$len)
    if ($okLen -and $len -gt 0) {
      $sb = New-Object System.Text.StringBuilder ([int]$len)
      $okCap = [DdcProbe]::CapabilitiesRequestAndCapabilitiesReply($pm.h, $sb, $len)
      $mn = 0; $cur = 0; $mx = 0
      $okB = [DdcProbe]::GetMonitorBrightness($pm.h, [ref]$mn, [ref]$cur, [ref]$mx)
      Write-Host "  DDC/CI: ANTWORTET" -ForegroundColor Green
      Write-Host ("  Capability : {0}" -f $sb.ToString())
      if ($okB) { Write-Host ("  Helligkeit : min=$mn aktuell=$cur max=$mx") }
      $ok++
    }
    else {
      $err = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
      $hex = ('0x{0:X8}' -f ($err -band 0xFFFFFFFF))
      Write-Host "  DDC/CI: KEINE ANTWORT" -ForegroundColor Red
      Write-Host ("  Win32-Fehler: {0} ({1})" -f $err, $hex)
      switch ($hex) {
        '0xC0262582' { Write-Host "  -> ERROR_GRAPHICS_DDCCI_VCP_NOT_SUPPORTED: der DDC/CI-Kanal"
                       Write-Host "     traegt keine gueltigen MCCS-Daten. Meist DDC/CI im OSD aus." }
        '0xC0262583' { Write-Host "  -> ERROR_GRAPHICS_DDCCI_INVALID_DATA: Monitor sendet keine"
                       Write-Host "     gueltigen MCCS-Daten. Meist DDC/CI im OSD aus." }
        '0xC0262580' { Write-Host "  -> I2C-Sendefehler: DDC/CI-Leitung/Anschluss stoerungsbehaftet." }
        '0xC0262581' { Write-Host "  -> I2C-Empfangsfehler: DDC/CI-Leitung/Anschluss stoerungsbehaftet." }
      }
      $fail++
    }
    [void][DdcProbe]::DestroyPhysicalMonitor($pm.h)
  }
}

Write-Host ""
Write-Host ("Ergebnis: {0} Monitor(e) antworten, {1} nicht." -f $ok, $fail) -ForegroundColor Cyan
if ($fail -gt 0) {
  Write-Host "Ein nicht antwortender Monitor laesst sich mit PowerToys PowerDisplay"
  Write-Host "nicht regeln. Schritte siehe Kopf dieses Skripts."
}

Melde-Ende -Marke $marke -Code 0 -Text "$ok ok, $fail ohne Antwort"     # neu
} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
