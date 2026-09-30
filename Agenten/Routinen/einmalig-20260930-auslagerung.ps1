#Requires -Version 5.1
<#
    einmalig-20260930-auslagerung.ps1

    Anlass (gemessen 30.09.2026, siehe MaxHirn/Wissen/Hardware.md):
    Die Commit-Grenze steht fest bei 75,7 GB = 63,7 GB RAM + 8 GB (C:) + 4 GB (O:).
    C:\pagefile.sys ist auf 8192/8192 FEST gesetzt (Maximum = 8192, kann nicht
    wachsen), O:\pagefile.sys steht auf 4096/16384 und ist nie gewachsen
    (Peak 715 MB). Folge: 296 Speichernot-Meldungen (Ereignis 2004) in 14 Tagen,
    am 30.09.2026 einunddreissig Anwendungsabstuerze mit 0xc000012d
    (STATUS_COMMITMENT_LIMIT) zwischen 10:12 und 10:46, darunter dwm.exe und der
    Hermes-Gateway.

    Was dieses Skript tut: es vergroessert NUR die Auslagerungsdatei auf O: und
    laesst C: unveraendert. O: hat rund 110 GB frei, es wird nichts verschoben
    und nichts geloescht.

    Aufruf (braucht erhochte Rechte):
        powershell -NoProfile -ExecutionPolicy Bypass -File Routinen\einmalig-20260930-auslagerung.ps1 -Testlauf
        powershell -NoProfile -ExecutionPolicy Bypass -File Routinen\einmalig-20260930-auslagerung.ps1
        powershell -NoProfile -ExecutionPolicy Bypass -File Routinen\einmalig-20260930-auslagerung.ps1 -Rueckgaengig

    Danach ist ein NEUSTART noetig; erst dann greift die groessere Commit-Grenze.
#>
[CmdletBinding()]
param(
    [switch]$Testlauf,
    [switch]$Rueckgaengig,
    [int]$ZielMB = 32768
)

$ErrorActionPreference = 'Stop'
$Sicherung = Join-Path $PSScriptRoot 'einmalig-20260930-auslagerung.sicherung.json'

function Kopf($t) { "`n=== $t ===" }

function Ist_Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Zeige_Stand {
    Kopf "Auslagerungsdateien jetzt"
    $cs = Get-CimInstance Win32_ComputerSystem
    "Automatisch verwaltet : $($cs.AutomaticManagedPagefile)"
    $set = Get-CimInstance Win32_PageFileSetting
    if (-not $set) { "  (keine Einstellung hinterlegt - Windows verwaltet selbst)" }
    foreach ($s in $set) {
        "  {0,-24} Anfang {1,7} MB   Maximum {2,7} MB" -f $s.Name, $s.InitialSize, $s.MaximumSize
    }
    $nutzung = Get-CimInstance Win32_PageFileUsage
    foreach ($u in $nutzung) {
        "  {0,-24} belegt {1,7} MB   Peak {2,7} MB" -f $u.Name, $u.CurrentUsage, $u.PeakUsage
    }
    $os = Get-CimInstance Win32_OperatingSystem
    "  Commit-Grenze         {0,10:N1} GB" -f ($os.TotalVirtualMemorySize / 1MB)
    "  Commit frei           {0,10:N1} GB" -f ($os.FreeVirtualMemory / 1MB)
    "  RAM                   {0,10:N1} GB" -f ($os.TotalVisibleMemorySize / 1MB)
}

function Hole_Seite($buchstabe) {
    $set = @(Get-CimInstance Win32_PageFileSetting | Where-Object { $_.Name -like "$buchstabe`:*" })
    if ($set.Count -gt 0) { return $set[0] }
    return $null
}

function Sichere {
    $stand = @()
    foreach ($s in @(Get-CimInstance Win32_PageFileSetting)) {
        $stand += [pscustomobject]@{ Name = $s.Name; InitialSize = $s.InitialSize; MaximumSize = $s.MaximumSize }
    }
    $auto = (Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile
    [pscustomobject]@{
        Datum           = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
        Automatisch     = $auto
        Auslagerungen   = $stand
    } | ConvertTo-Json -Depth 4 | Set-Content -Path $Sicherung -Encoding UTF8
    "Sicherung des Vorzustands: $Sicherung"
}

function Setze_Seite($buchstabe, $anfangMB, $maxMB) {
    $vorhanden = Hole_Seite $buchstabe
    if ($vorhanden) {
        $vorhanden.InitialSize = $anfangMB
        $vorhanden.MaximumSize = $maxMB
        Set-CimInstance -InputObject $vorhanden
    } else {
        New-CimInstance -ClassName Win32_PageFileSetting -Property @{
            Name = "$buchstabe`:\pagefile.sys"; InitialSize = $anfangMB; MaximumSize = $maxMB
        } | Out-Null
    }
}

# --------------------------------------------------------------------------
if (-not (Ist_Admin) -and -not $Testlauf) {
    "ABBRUCH: Dieses Skript braucht erhochte Rechte."
    "Starte es in einer PowerShell als Administrator, oder aus einer normalen"
    "PowerShell so:"
    "    Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','$PSCommandPath'"
    exit 3
}

Zeige_Stand

if ($Rueckgaengig) {
    Kopf "Rueckgaengig"
    if (-not (Test-Path $Sicherung)) {
        "ABBRUCH: keine Sicherung gefunden ($Sicherung)."
        "Rueckgaengig von Hand: C: auf 8192/8192, O: auf 4096/16384 setzen."
        exit 4
    }
    $alt = Get-Content $Sicherung -Raw | ConvertFrom-Json
    "Sicherung vom $($alt.Datum)"
    Set-CimInstance -InputObject (Get-CimInstance Win32_ComputerSystem) -Property @{ AutomaticManagedPagefile = [bool]$alt.Automatisch }
    foreach ($s in $alt.Auslagerungen) {
        $b = $s.Name.Substring(0, 1)
        Setze_Seite $b $s.InitialSize $s.MaximumSize
        "  {0} zurueck auf {1}/{2} MB" -f $s.Name, $s.InitialSize, $s.MaximumSize
    }
    Zeige_Stand
    "`nFertig. Neustart noetig."
    exit 0
}

$ziel = Hole_Seite 'O'
if (-not $ziel) {
    "ABBRUCH: auf O: ist keine Auslagerungsdatei eingerichtet."
    "Dieses Skript vergroessert eine VORHANDENE Datei und legt keine neue an."
    "Erst von Hand eine Auslagerungsdatei auf O: anlegen, dann hier erneut."
    exit 5
}

Kopf "Was geaendert wird"
"  O:\pagefile.sys   {0} / {1} MB  ->  {2} / {2} MB" -f $ziel.InitialSize, $ziel.MaximumSize, $ZielMB
"  C:\pagefile.sys   unveraendert (bleibt fest auf 8192/8192)"
"  Commit-Grenze     {0:N1} GB  ->  rund {1:N1} GB" -f `
    ((Get-CimInstance Win32_OperatingSystem).TotalVirtualMemorySize / 1MB), `
    ((63.7 + 8 + ($ZielMB / 1024)))

if ($Testlauf) {
    Kopf "Testlauf - es wurde NICHTS geaendert"
    "Scharf ausfuehren ohne -Testlauf. Danach ist ein NEUSTART noetig."
    exit 0
}

Kopf "Scharf"
Sichere
Set-CimInstance -InputObject (Get-CimInstance Win32_ComputerSystem) -Property @{ AutomaticManagedPagefile = $false }
Setze_Seite 'O' $ZielMB $ZielMB
"  O: auf $ZielMB / $ZielMB MB gesetzt"
Zeige_Stand
"`nFertig. NEUSTART noetig, erst danach greift die groessere Commit-Grenze."
"Rueckgaengig: dasselbe Skript mit -Rueckgaengig."