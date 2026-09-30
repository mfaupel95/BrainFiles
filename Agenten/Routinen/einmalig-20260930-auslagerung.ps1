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

    STAND 30.09.2026 12:29 - der Vorzustand hat sich geaendert:
    Um 11:59 lief dieses Skript bereits einmal (Sicherung: 8192/8192 auf C:,
    4096/16384 auf O:). Danach wurde von Hand umgestellt: C: steht auf
    selbstverwaltet (0/0, aktuell 21 GB belegt), der Eintrag auf O: ist WEG.
    Die Commit-Grenze liegt damit bei 84,5 GB - aber die 21 GB liegen auf C:,
    das nur noch 19,3 GB frei hat: eine selbstverwaltete Datei waechst dort
    unbegrenzt und fuellt das Laufwerk. Deshalb legt -Anlegen den Eintrag auf
    O: neu an (114 GB frei) und C_FestMB pinnt C: wieder auf einen festen Wert.

    Danach ist ein NEUSTART noetig; erst dann greift die groessere Commit-Grenze.

    AUSGEFUEHRT 30.09.2026 12:33: C: auf 8192/8192 festgelegt, O: auf
    32768/32768 angelegt. Der O:-Eintrag kam ueber den REGISTRY-Weg
    (HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\
    PagingFiles = "C:\pagefile.sys 8192 8192" + "O:\pagefile.sys 32768 32768"),
    weil New-CimInstance am UInt32-Typ scheiterte (siehe Setze_Seite). WMI zeigt
    beide Eintraege, O: hat 114 GB frei. NEUSTART STEHT AUS - erst danach gilt
    die Commit-Grenze von rund 103,7 GB statt 84,5 GB.
#>
[CmdletBinding()]
param(
    [switch]$Testlauf,
    [switch]$Rueckgaengig,
    [switch]$Anlegen,
    [int]$ZielMB = 32768,
    [int]$C_FestMB = 8192
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
        $vorhanden.InitialSize = [uint32]$anfangMB
        $vorhanden.MaximumSize = [uint32]$maxMB
        Set-CimInstance -InputObject $vorhanden
    } else {
        # [uint32] ist PFLICHT: Win32_PageFileSetting.InitialSize ist UInt32, und
        # ein Int32 aus der Parameteruebergabe loest "Typenkonflikt fuer die
        # Eigenschaft InitialSize" aus. Mit $ErrorActionPreference='Stop' stirbt
        # das Skript dort STILL - der Lauf am 30.09.2026 12:30 setzte deshalb nur
        # C: und brach vor dem O:-Eintrag ab, ohne eine Zeile ins Log zu schreiben.
        New-CimInstance -ClassName Win32_PageFileSetting -Property @{
            Name = "$buchstabe`:\pagefile.sys"
            InitialSize = [uint32]$anfangMB
            MaximumSize = [uint32]$maxMB
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
if (-not $ziel -and -not $Anlegen) {
    "ABBRUCH: auf O: ist keine Auslagerungsdatei eingerichtet."
    "Dieses Skript vergroessert eine VORHANDENE Datei und legt keine neue an."
    "Erst von Hand eine Auslagerungsdatei auf O: anlegen, dann hier erneut."
    "ODER mit -Anlegen aufrufen: dann wird der Eintrag auf O: angelegt"
    "(gemessen 30.09.2026: O: hat 114 GB frei, C: nur 19 GB - die grosse"
    "Auslagerungsdatei gehoert auf O:)."
    exit 5
}

Kopf "Was geaendert wird"
if ($ziel) {
    "  O:\pagefile.sys   {0} / {1} MB  ->  {2} / {2} MB" -f $ziel.InitialSize, $ziel.MaximumSize, $ZielMB
} else {
    "  O:\pagefile.sys   (kein Eintrag)  ->  NEU angelegt: {0} / {0} MB" -f $ZielMB
}
$cjetzt = Hole_Seite 'C'
if ($C_FestMB -gt 0 -and $cjetzt) {
    "  C:\pagefile.sys   {0} / {1} MB  ->  FEST {2} / {2} MB" -f `
        $cjetzt.InitialSize, $cjetzt.MaximumSize, $C_FestMB
    "                    (C: hat nur wenig Platz; eine selbstverwaltete Datei"
    "                     waechst dort unbegrenzt und fuellt das Laufwerk)"
} elseif ($cjetzt) {
    "  C:\pagefile.sys   unveraendert ({0} / {1} MB)" -f $cjetzt.InitialSize, $cjetzt.MaximumSize
} else {
    "  C:\pagefile.sys   (kein Eintrag - bleibt so)"
}
"  Commit-Grenze     {0:N1} GB  ->  rund {1:N1} GB" -f `
    ((Get-CimInstance Win32_OperatingSystem).TotalVirtualMemorySize / 1MB), `
    ((63.7 + ($C_FestMB / 1024) + ($ZielMB / 1024)))

if ($Testlauf) {
    Kopf "Testlauf - es wurde NICHTS geaendert"
    "Scharf ausfuehren ohne -Testlauf. Danach ist ein NEUSTART noetig."
    exit 0
}

Kopf "Scharf"
Sichere
Set-CimInstance -InputObject (Get-CimInstance Win32_ComputerSystem) -Property @{ AutomaticManagedPagefile = $false }
if ($C_FestMB -gt 0 -and $cjetzt) {
    Setze_Seite 'C' $C_FestMB $C_FestMB
    "  C: auf $C_FestMB / $C_FestMB MB festgelegt"
}
Setze_Seite 'O' $ZielMB $ZielMB
"  O: auf $ZielMB / $ZielMB MB gesetzt"
Zeige_Stand
"`nFertig. NEUSTART noetig, erst danach greift die groessere Commit-Grenze."
"Rueckgaengig: dasselbe Skript mit -Rueckgaengig."