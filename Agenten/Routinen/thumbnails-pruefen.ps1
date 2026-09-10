# Prueft, ob Windows fuer Bilder und Videos Miniaturansichten erzeugen kann.
#
# Trennt zwei Faelle, die im Explorer gleich aussehen:
#   1. Windows kann keine Miniatur erzeugen  -> Datei kaputt oder Handler defekt
#   2. Windows kann es, zeigt sie aber nicht -> Anzeigeproblem in der Shell
#
# Aufruf:  powershell -File thumbnails-pruefen.ps1 [-Ordner <Pfad>] [-Anzahl <N>]
# Ausgabe ist bewusst kurz (nur Zahlen). Siehe Wissen/Miniaturansichten.md

param(
    [string]$Ordner = "$env:USERPROFILE\Pictures",
    [int]$Anzahl = 40
)

$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'Bus\Ereignis.ps1')      # neu
$marke = Melde-Start -Wer 'routine/thumbnails-pruefen'                  # neu
try {                                                                    # neu
Add-Type -AssemblyName System.Drawing

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class ThumbPruef {
    [StructLayout(LayoutKind.Sequential)]
    public struct SIZE { public int cx; public int cy; }

    [ComImport, Guid("bcc18b79-ba16-442f-80c4-8a59c30c463b"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IShellItemImageFactory {
        void GetImage(SIZE size, int flags, out IntPtr phbm);
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    public static extern void SHCreateItemFromParsingName(
        [MarshalAs(UnmanagedType.LPWStr)] string pszPath, IntPtr pbc,
        [MarshalAs(UnmanagedType.LPStruct)] Guid riid,
        [MarshalAs(UnmanagedType.Interface)] out object ppv);

    public static IntPtr Get(string path, int size, int flags) {
        Guid iid = new Guid("bcc18b79-ba16-442f-80c4-8a59c30c463b");
        object o;
        SHCreateItemFromParsingName(path, IntPtr.Zero, iid, out o);
        IShellItemImageFactory f = (IShellItemImageFactory)o;
        SIZE s; s.cx = size; s.cy = size;
        IntPtr h;
        f.GetImage(s, flags, out h);
        return h;
    }
}
'@

# 0x08 = SIIGBF_THUMBNAILONLY : echte Miniatur, KEIN Icon-Ersatz.
#        Ohne dieses Flag liefert Windows ersatzweise das Dateisymbol
#        zurueck - der Test wuerde dann immer "erfolgreich" melden.
# 0x10 = SIIGBF_INCACHEONLY   : nur aus dem Cache lesen, nichts erzeugen.
function Get-Miniatur {
    param([string]$Pfad, [int]$Flags = 0x08)
    try {
        $h = [ThumbPruef]::Get($Pfad, 256, $Flags)
        if ($h -eq [IntPtr]::Zero) { return $null }
        $bmp = [System.Drawing.Bitmap]::FromHbitmap($h)
        $groesse = "$($bmp.Width)x$($bmp.Height)"
        $bmp.Dispose()
        return $groesse
    } catch { return $null }
}

# Zerstoerte Dateien (Netzteildefekt, siehe Archiv/BESCHAEDIGTE_DATEIEN.md)
# haben ueber die ersten 4096 Byte durchgehend denselben Wert. Die duerfen
# nicht als Fehlschlag zaehlen - dort ist wirklich nichts mehr zu sehen.
function Test-Zerstoert {
    param([string]$Pfad)
    try {
        $fs = [System.IO.File]::OpenRead($Pfad)
        $puffer = New-Object byte[] 4096
        $gelesen = $fs.Read($puffer, 0, 4096)
        $fs.Close()
        if ($gelesen -lt 16) { return $true }
        for ($i = 1; $i -lt $gelesen; $i++) {
            if ($puffer[$i] -ne $puffer[0]) { return $false }
        }
        return $true
    } catch { return $true }
}

if (-not (Test-Path -LiteralPath $Ordner)) {
    Write-Output "Ordner nicht gefunden: $Ordner"
    Melde-Ende -Marke $marke -Code 1 -Text "Ordner nicht gefunden: $Ordner" # neu
    exit 1
}

$dateien = Get-ChildItem -LiteralPath $Ordner -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -match '^\.(jpg|jpeg|png|gif|bmp|heic|mp4|mov|avi|mkv)$' }

if ($dateien.Count -eq 0) {
    Write-Output "Keine Bild- oder Videodateien in: $Ordner"
    Melde-Ende -Marke $marke -Code 0 -Text "keine Bild-/Videodateien in $Ordner" # neu
    exit 0
}

$probe = $dateien | Get-Random -Count ([Math]::Min($Anzahl, $dateien.Count))
$zerstoert = 0; $mitMiniatur = 0; $ohneMiniatur = 0
$beispiele = @()

foreach ($d in $probe) {
    if (Test-Zerstoert $d.FullName) { $zerstoert++; continue }
    if (Get-Miniatur $d.FullName)   { $mitMiniatur++ }
    else {
        $ohneMiniatur++
        if ($beispiele.Count -lt 3) { $beispiele += $d.Name }
    }
}

Write-Output "Ordner            : $Ordner"
Write-Output "Dateien gesamt    : $($dateien.Count)"
Write-Output "Stichprobe        : $($probe.Count)"
Write-Output "zerstoert (0xFF)  : $zerstoert"
Write-Output "intakt MIT Bild   : $mitMiniatur"
Write-Output "intakt OHNE Bild  : $ohneMiniatur"
if ($beispiele) { Write-Output "Beispiele ohne    : $($beispiele -join ', ')" }

Write-Output ""
if ($ohneMiniatur -eq 0 -and $mitMiniatur -gt 0) {
    Write-Output "BEFUND: Windows erzeugt Miniaturen einwandfrei."
    Write-Output "        Werden im Explorer trotzdem nur Symbole gezeigt, ist es"
    Write-Output "        ein ANZEIGEproblem - siehe Wissen/Miniaturansichten.md."
} elseif ($mitMiniatur -eq 0) {
    Write-Output "BEFUND: Windows erzeugt fuer keine Datei eine Miniatur."
    Write-Output "        Hier lohnt die Pruefung der Handler und Codecs."
} else {
    Write-Output "BEFUND: gemischt - einzelne Dateien scheitern, andere nicht."
}

Melde-Ende -Marke $marke -Code 0                                        # neu
} catch {                                                                # neu
  Melde-Ende -Marke $marke -Code 1 -Text "$_"                           # neu
  throw                                                                 # neu
}                                                                        # neu
