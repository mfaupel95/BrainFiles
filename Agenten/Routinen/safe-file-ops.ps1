# Sicherheitswaechter fuer Dateioperationen. Als Skript aufrufbar oder als
# Bibliothek (dot-sourced).
#
# BUS: Bibliothek - kein eigener Lauf. Sie wird von posteingang.ps1 und
# datensortierung.ps1 dot-sourced; die Start/Ende-Meldung gehoert zum Einbinder
# (routine/posteingang bzw. routine/datensortierung), nicht hierher. Sonst
# entstuende bei jedem Aufruf des Einbinders ein zweiter Zyklus im Journal.
#
# Warum es dieses Skript gibt: Die Schutzstufen in Wissen/Schutzregeln.md sind
# Prosa. Wer "aufraeumt", ueberschreitet sie stillschweigend - und Stufe 0
# heisst: die Datei ist danach weg, ohne Zweitquelle. Dieses Skript macht die
# Prosa abfragbar, BEVOR irgendetwas geschrieben wird.
#
# Es entscheidet, es raeumt nicht auf. Moegliche Urteile:
#   ERLAUBT            - nichts spricht dagegen
#   SICHERUNG_PFLICHT  - erst .bak-JJJJMMTT, dann aendern, dann echten Lauf zeigen
#   QUARANTAENE        - nur in den _zu_loeschen-Ordner verschieben, nie loeschen
#   ABBRUCH            - Stufe 0 oder Schluesseldatei: nicht anfassen
#
# Ohne -Ausfuehren wird nur geurteilt und nichts geschrieben (Vorgabe).
# Geloescht wird hier nie aus eigenem Antrieb; QUARANTAENE verschiebt, mehr nicht.
#
# Pfade relativ zu diesem Skript ($PSScriptRoot), damit BrainFiles umziehen kann.
# Protokoll: Agenten/Routinen/logs/sicherheitspruefung.log
#   geschrieben nur bei -Ausfuehren oder bei ABBRUCH (ein blockierter Versuch
#   gehoert ins Protokoll, ein trockener Aufruf nicht).
#
# Gegenseite: MaxHirn/optional-skills/productivity/data-guard-audit/ haelt
# dieselben Stufen fuer die Agentenseite. Menschliche Quelle der Wahrheit bleibt
# Wissen/Schutzregeln.md - bei Abweichung gilt die Notiz, nicht dieses Skript.
#
# Exitcodes: 0 ERLAUBT | 1 ABBRUCH | 2 SICHERUNG_PFLICHT | 3 QUARANTAENE

[CmdletBinding()]
param(
  [string]$Pfad,

  [ValidateSet('lesen','loeschen','massenhaft_loeschen','ueberschreiben','verschieben','umbenennen')]
  [string]$Aktion,

  # Ohne diesen Schalter wird nichts veraendert. Vorgabe ist der Trockenlauf.
  [switch]$Ausfuehren,

  # Tor statt Urteil: Der Aufrufer sagt, welches Urteil er voraussetzt. Weicht
  # das tatsaechliche ab, endet der Lauf mit 4 und es wird nichts getan. Damit
  # prueft eine Routine, dass der Schutz noch scharf ist, statt darauf zu
  # vertrauen - eine spaetere Regeländerung faellt dann auf, statt still zu wirken.
  [ValidateSet('ERLAUBT','ABBRUCH','SICHERUNG_PFLICHT','QUARANTAENE')]
  [string]$Erwartet,

  # Keine Ausgabe im Normalfall, nur bei verletzter Erwartung. Fuer Aufrufe aus
  # Routinen, deren Protokoll sonst zugemuellt wird.
  [switch]$Stille
)

$ErrorActionPreference = 'Stop'

# --- Stufenregeln -----------------------------------------------------------
# Geprueft wird von oben nach unten, der erste Treffer gewinnt. Muster sind
# regulaere Ausdruecke auf einen normalisierten Pfad (Kleinbuchstaben,
# Schraegstriche, absolute Form).
#
# Reihenfolge ist Teil der Regel: Stufe 0 vor Stufe 2-Ausnahmen vor Stufe 1.
# Sonst zoege die allgemeine Regel "/agenten/routinen/" die Protokolle mit,
# die laut Schutzregeln ausdruecklich Stufe 2 sind.

# Stufe 0: Original ohne Zweitquelle. Schluessel und Zertifikate zusaetzlich:
# nicht lesen, damit sie nie in einem Protokoll oder Transkript landen.
$script:Stufe0GeheimMuster = @(
  '/(zugaenge)\.md$'
  '/\.env$'
  '/id_rsa$'
  '\.(env|pem|pfx|p12|kdbx|key|ovpn|jks|keystore)$'
)

# Stufe 0: die Archivdaten. Seit dem 07.09.2026 liegen sie auf O:\Archiv,
# der Altbestand kann noch unter MaxHirn\Claude liegen.
$script:Stufe0Muster = @(
  # Die ganze Archivwurzel, nicht nur die bekannten Unterordner: das Archiv ist
  # am 07.09.2026 nach O:\Archiv gezogen. Ein neuer Unterordner waere sonst
  # ungeschuetzt, bis jemand diese Liste nachzieht (Fund 12.09.2026).
  '^o:/archiv(/|$)'
  '/maxhirn/claude/(dokumente|bilder|videos|musik|posteingang)(/|$)'
)

# Stufe 2 trotz allgemeiner Stufe-1-Regel: reproduzierbar oder ausdruecklich
# freigegeben (Protokolle, Umgebungen, Fremdbaeume, Indexdatenbanken).
$script:Stufe2ImmerMuster = @(
  '/agenten/routinen/logs(/|$)'
  '/\.venv(/|$)'
  '/__pycache__(/|$)'
  '/node_modules(/|$)'
  '/\.git(/|$)'
)

# Stufe 1: betrieblich. Ersetzbar, aber sie brechen still - der Schaden zeigt
# sich Wochen spaeter als Sicherung, die aufgehoert hat zu laufen.
$script:Stufe1Muster = @(
  '/maxhirn/(agents|claude|dashboard)\.md$'
  '/maxhirn/\.claude/skills(/|$)'
  '/maxhirn/\.agents/skills(/|$)'
  '/maxhirn/optional-skills(/|$)'
  '/maxhirn/\.obsidian(/|$)'
  '/maxhirn/archiv/archivsuche(/|$)'
  '/maxhirn/(sichern|install)[^/]*\.ps1$'
  '/agenten/routinen(/|$)'
  '/agenten/mcp-server(/|$)'
  '/agenten/handel(/|$)'
  '/agenten/hermes(/|$)'
  '/agenten/bus(/|$)'
  '/agenten/\.claude(/|$)'
  '/agenten/(sichern|mcp-sync-check)[^/]*\.(ps1|json)$'
)

# --- Pfadwerkzeuge ----------------------------------------------------------

function Get-NormalisiertenPfad {
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Eingabe)

  $p = $Eingabe
  if (-not [System.IO.Path]::IsPathRooted($p)) {
    $p = Join-Path (Get-Location).Path $p
  }
  try { $p = [System.IO.Path]::GetFullPath($p) } catch { }
  return ($p -replace '\\', '/').ToLowerInvariant()
}

function Test-Geheimpfad {
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Normalisiert)

  foreach ($m in $script:Stufe0GeheimMuster) {
    if ($Normalisiert -match $m) { return $true }
  }
  return $false
}

function Get-Schutzstufe {
  <#
    Liefert 0, 1 oder 2 fuer einen Pfad. 2 ist die Vorgabe: was keine Regel
    nennt, ist laut Schutzregeln frei - nicht umgekehrt.
  #>
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Pfad)

  $n = Get-NormalisiertenPfad -Eingabe $Pfad

  if (Test-Geheimpfad -Normalisiert $n) { return 0 }
  foreach ($m in $script:Stufe0Muster)      { if ($n -match $m) { return 0 } }
  foreach ($m in $script:Stufe2ImmerMuster) { if ($n -match $m) { return 2 } }
  foreach ($m in $script:Stufe1Muster)      { if ($n -match $m) { return 1 } }
  return 2
}

# --- Quarantaene ------------------------------------------------------------
# Laut Schutzregeln wandern Loeschkandidaten nach .../Posteingang/_zu_loeschen/
# und werden dort von einem Menschen entschieden. Bewusst NICHT neben die Datei:
# ein Ordner im Archiv selbst wuerde beim naechsten Sortierlauf wieder
# eingesammelt, und die beiseitegelegten Dateien waeren stillschweigend zurueck.

function Get-QuarantaeneOrdner {
  [CmdletBinding()]
  param()

  $kandidaten = @()
  if (Test-Path -LiteralPath 'O:\Archiv\Posteingang') {
    $kandidaten += 'O:\Archiv\Posteingang\_zu_loeschen'
  }
  $alt = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) 'MaxHirn\Claude\Posteingang'
  if (Test-Path -LiteralPath $alt) {
    $kandidaten += (Join-Path $alt '_zu_loeschen')
  }

  if ($kandidaten.Count -eq 0) { return $null }
  return $kandidaten[0]
}

function Move-InQuarantaene {
  <#  Verschiebt eine Datei in den Quarantaeneordner. Loescht nie.  #>
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Quelle)

  $ordner = Get-QuarantaeneOrdner
  if (-not $ordner) {
    throw 'Kein Quarantaeneordner vorhanden (weder O:\Archiv\Posteingang noch MaxHirn\Claude\Posteingang).'
  }
  if (-not (Test-Path -LiteralPath $ordner)) {
    New-Item -ItemType Directory -Path $ordner | Out-Null
    $hinweis = @(
      'Hier liegen Loeschkandidaten aus Stufe 0.',
      '',
      'Entschieden wird von Hand, nicht von einem Skript. Ein automatischer',
      'Lauf, der diesen Ordner durchsucht, gehoert ausgenommen - sonst sind die',
      'Dateien beim naechsten Lauf wieder im Archiv.',
      '',
      "Angelegt: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    ) -join "`n"
    Set-Content -LiteralPath (Join-Path $ordner 'LIESMICH.txt') -Value $hinweis -Encoding UTF8
  }

  # GetFileName statt Split-Path -Leaf: Split-Path -LiteralPath liefert in
  # PowerShell 7 einen leeren Wert. Aus dem leeren Namen entstuende ein Ziel
  # ohne Dateinamen, und der Move scheitert dann in 5.1 mit einer Meldung, die
  # auf den Parametersatz zeigt statt auf die Ursache (erlebt 11.09.2026).
  $name = [System.IO.Path]::GetFileName($Quelle)
  if ([string]::IsNullOrWhiteSpace($name)) {
    throw "Aus '$Quelle' laesst sich kein Dateiname gewinnen - Abbruch statt Blindverschieben."
  }
  $ziel = Join-Path $ordner $name
  if (Test-Path -LiteralPath $ziel) {
    $ziel = Join-Path $ordner ('{0}.{1}' -f $name, (Get-Date -Format 'yyyyMMdd-HHmmss'))
  }
  # .NET statt Move-Item: verhaelt sich in 5.1 und 7 gleich.
  if ([System.IO.Directory]::Exists($Quelle)) {
    [System.IO.Directory]::Move($Quelle, $ziel)
  } else {
    [System.IO.File]::Move($Quelle, $ziel)
  }
  return $ziel
}

function New-Sicherungskopie {
  <#  Legt die .bak-JJJJMMTT-Kopie an, die Stufe 1 vor jeder Aenderung verlangt.  #>
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Quelle)

  if (-not (Test-Path -LiteralPath $Quelle)) { return $null }
  $ziel = '{0}.bak-{1}' -f $Quelle, (Get-Date -Format 'yyyyMMdd')
  if (Test-Path -LiteralPath $ziel) {
    $ziel = '{0}.bak-{1}' -f $Quelle, (Get-Date -Format 'yyyyMMdd-HHmmss')
  }
  Copy-Item -LiteralPath $Quelle -Destination $ziel -Recurse -Force
  return $ziel
}

# --- Urteil -----------------------------------------------------------------

function Get-Schutzurteil {
  <#
    Urteil zu einer geplanten Operation. Aendert nichts.
    Rueckgabe: Objekt mit Pfad, Stufe, Geheim, Entscheidung, Grund.
  #>
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$Pfad,
    [Parameter(Mandatory)]
    [ValidateSet('lesen','loeschen','massenhaft_loeschen','ueberschreiben','verschieben','umbenennen')]
    [string]$Aktion
  )

  $n     = Get-NormalisiertenPfad -Eingabe $Pfad
  $stufe = Get-Schutzstufe -Pfad $Pfad
  $geheim = Test-Geheimpfad -Normalisiert $n

  $zerstoerend = $Aktion -in @('loeschen','massenhaft_loeschen','ueberschreiben','verschieben','umbenennen')

  $ergebnis = [pscustomobject]@{
    Pfad         = $n
    Aktion       = $Aktion
    Stufe        = $stufe
    Geheim       = $geheim
    Entscheidung = 'ERLAUBT'
    Grund        = 'Stufe 2: reproduzierbar oder in Git - freie Hand.'
  }

  if ($stufe -eq 0) {
    if ($geheim) {
      $ergebnis.Entscheidung = 'ABBRUCH'
      $ergebnis.Grund = 'Stufe 0 (Schluessel/Zertifikat): weder lesen noch schreiben noch loeschen. Die Datei ist die einzige Ablage.'
    }
    elseif ($Aktion -in @('loeschen','massenhaft_loeschen','ueberschreiben')) {
      $ergebnis.Entscheidung = 'ABBRUCH'
      $ergebnis.Grund = 'Stufe 0: Original ohne Zweitquelle. Kein Loeschen, kein Ueberschreiben - auch nicht auf Ansage.'
    }
    elseif ($Aktion -in @('verschieben','umbenennen')) {
      $ergebnis.Entscheidung = 'QUARANTAENE'
      $ergebnis.Grund = 'Stufe 0: nur in den _zu_loeschen-Ordner verschieben, dort entscheidet ein Mensch.'
    }
    else {
      $ergebnis.Entscheidung = 'ERLAUBT'
      $ergebnis.Grund = 'Stufe 0: Lesen ist erlaubt, Schreiben nicht.'
    }
  }
  elseif ($stufe -eq 1 -and $zerstoerend) {
    $ergebnis.Entscheidung = 'SICHERUNG_PFLICHT'
    $ergebnis.Grund = 'Stufe 1: erst .bak-JJJJMMTT anlegen, dann aendern, dann einen echten Lauf zeigen.'
  }

  return $ergebnis
}

# --- Ausfuehrung ------------------------------------------------------------

function Write-Waechterprotokoll {
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Zeile)

  $logs = Join-Path $PSScriptRoot 'logs'
  if (-not (Test-Path -LiteralPath $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
  $log = Join-Path $logs 'sicherheitspruefung.log'
  '{0} | {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Zeile |
    Add-Content -LiteralPath $log -Encoding UTF8
}

function Invoke-Schutzpruefung {
  <#
    Fuehrt die Pruefung aus und setzt je Urteil die sichere Variante um.
    Ohne -Ausfuehren passiert nichts ausser der Ausgabe.
  #>
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$Pfad,
    [Parameter(Mandatory)][string]$Aktion,
    [switch]$Ausfuehren,
    [string]$Erwartet,
    [switch]$Stille
  )

  $urteil = Get-Schutzurteil -Pfad $Pfad -Aktion $Aktion

  if (-not $Stille) {
    'STUFE: {0}'         -f $urteil.Stufe        | Write-Output
    'ENTSCHEIDUNG: {0}'  -f $urteil.Entscheidung | Write-Output
    'GRUND: {0}'         -f $urteil.Grund        | Write-Output
    'PFAD: {0}'          -f $urteil.Pfad         | Write-Output
  }

  # Tor: nur pruefen, nicht handeln. Steht vor der Urteilslogik, weil ein
  # Aufrufer mit -Erwartet eine Zusicherung will, keine Nebenwirkung.
  if ($Erwartet) {
    if ($urteil.Entscheidung -ne $Erwartet) {
      Write-Output ('ERWARTUNG VERLETZT: erwartet {0}, tatsaechlich {1}' -f $Erwartet, $urteil.Entscheidung)
      Write-Output ('GRUND: {0}' -f $urteil.Grund)
      Write-Waechterprotokoll -Zeile ('TOR VERLETZT | {0} | {1} statt {2} | {3}' -f $Aktion, $urteil.Entscheidung, $Erwartet, $urteil.Pfad)
      exit 4
    }
    if (-not $Stille) { Write-Output ('TOR GEHALTEN: {0}' -f $Erwartet) }
    exit 0
  }

  $tat = $false

  switch ($urteil.Entscheidung) {
    'ABBRUCH' {
      Write-Waechterprotokoll -Zeile ('ABBRUCH | {0} | {1}' -f $Aktion, $urteil.Pfad)
      Write-Output 'Die Operation wird nicht ausgefuehrt.'
      exit 1
    }
    'QUARANTAENE' {
      if ($Ausfuehren) {
        $ziel = Move-InQuarantaene -Quelle $Pfad
        $tat = $true
        Write-Output ('Verschoben nach: {0}' -f $ziel)
        Write-Waechterprotokoll -Zeile ('QUARANTAENE | {0} -> {1}' -f $urteil.Pfad, $ziel)
      }
      else {
        Write-Output 'Trockenlauf: es wuerde in den _zu_loeschen-Ordner verschoben.'
      }
      exit 3
    }
    'SICHERUNG_PFLICHT' {
      if ($Ausfuehren) {
        $bak = New-Sicherungskopie -Quelle $Pfad
        $tat = $true
        Write-Output ('Sicherung angelegt: {0}' -f $bak)
        Write-Waechterprotokoll -Zeile ('SICHERUNG | {0} -> {1}' -f $urteil.Pfad, $bak)
        Write-Output 'Erst nach dieser Kopie aendern - und danach einen echten Lauf zeigen.'
      }
      else {
        Write-Output 'Trockenlauf: es wuerde eine .bak-JJJJMMTT-Kopie angelegt.'
      }
      exit 2
    }
    default {
      if ($Ausfuehren) {
        Write-Waechterprotokoll -Zeile ('ERLAUBT | {0} | {1}' -f $Aktion, $urteil.Pfad)
        Write-Output 'Erlaubt. Die Operation selbst bleibt beim Aufrufer.'
      }
      else {
        Write-Output 'Trockenlauf: erlaubt.'
      }
      exit 0
    }
  }
}

# --- Einsprung ---------------------------------------------------------------
# Bei dot-sourced Aufruf (. .\safe-file-ops.ps1) nur die Funktionen laden, damit
# andere Routinen Get-Schutzurteil benutzen koennen.

if ($MyInvocation.InvocationName -ne '.') {
  if ([string]::IsNullOrWhiteSpace($Pfad) -or [string]::IsNullOrWhiteSpace($Aktion)) {
    Write-Output 'Sicherheitswaechter fuer Dateioperationen'
    Write-Output ''
    Write-Output '  .\safe-file-ops.ps1 -Pfad <pfad> -Aktion <aktion> [-Ausfuehren]'
    Write-Output ''
    Write-Output 'Aktionen: lesen, loeschen, massenhaft_loeschen, ueberschreiben, verschieben, umbenennen'
    Write-Output 'Ohne -Ausfuehren nur Urteil, ohne jede Aenderung.'
    Write-Output ''
    Write-Output 'Exitcodes: 0 ERLAUBT | 1 ABBRUCH | 2 SICHERUNG_PFLICHT | 3 QUARANTAENE'
    Write-Output '          4 Erwartung verletzt (nur mit -Erwartet, es wird nichts getan)'
    Write-Output ''
    Write-Output 'Tor statt Urteil: -Erwartet <Urteil> prueft nur und handelt nicht.'
    exit 0
  }
  Invoke-Schutzpruefung -Pfad $Pfad -Aktion $Aktion -Ausfuehren:$Ausfuehren -Erwartet $Erwartet -Stille:$Stille
}
