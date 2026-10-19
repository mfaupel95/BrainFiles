# Pruefung: Sind Claude Desktop und Hermes mit den MCP-Servern in Sync?
#
# Hintergrund: Beide Agenten konfigurieren ihre Server doppelt -
# claude_desktop_config.json (Claude) und Hermes/config.yaml (Hermes).
# Aenderungen an MCP-Server-Pfaden, Argumenten oder Umgebungsvariablen muessen
# an BEIDEN Stellen gemacht werden. Das ist fehleranfaellig.
#
# Dieses Skript vergleicht das Manifest (MCP-Manifest.json, Quelle der Wahrheit)
# gegen die Laufzeit-Konfigurationen beider Agenten und prueft, ob die
# Serverprogramme existieren.
#
# Hinweise:
# - Claude-Desktop installiert als MSIX-Paket: Konfiguration liegt im
#   Paket-Container (LocalCache\Roaming\Claude), NICHT unter %APPDATA%.
# - Hermes-Konfiguration liegt in Agenten\Hermes\config.yaml (nicht MaxHirn\Hermes).
# - Das Manifest kennt ein Feld 'agent': 'beide' (Standard), 'hermes' oder
#   'claude', wenn nur ein Agent den Server eintragen soll.
# - Exit-Code: 0 = alles in Ordnung, 1 = Fehler gefunden.
#   Der Parameter -Streng wird aus Kompatibilitaet akzeptiert (Fehler fuehren
#   immer zu Exit 1).
#
# Aufruf: powershell -ExecutionPolicy Bypass -File mcp-sync-check.ps1 [-Streng]

param([switch]$Streng)

$ErrorActionPreference = 'Stop'
$wurzel = Split-Path $PSScriptRoot -Parent
$manifest = Join-Path $PSScriptRoot 'MCP-Manifest.json'
$confHermes = Join-Path $wurzel 'Agenten\Hermes\config.yaml'

# Claude-Konfiguration suchen: erst der MSIX-Container (Pfad der installierten App),
# dann der klassische Pfad %APPDATA%\Claude. Eine verwaiste klassische Datei daneben
# wuerde den Abgleich verfaelschen - sie wird unten gemeldet.
$confClaude = $null
$kandidaten = @()
$pakete = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Packages') -Directory -Filter 'Claude_*' -ErrorAction SilentlyContinue
foreach ($p in $pakete) {
  $kandidaten += (Join-Path $p.FullName 'LocalCache\Roaming\Claude\claude_desktop_config.json')
}
$kandidaten += (Join-Path $env:APPDATA 'Claude\claude_desktop_config.json')
foreach ($k in $kandidaten) {
  if (Test-Path $k) { $confClaude = $k; break }
}

$fehler = @()
$warnungen = @()

function Schreibe($marker, $text) {
  Write-Host ('  ' + $marker + ' ' + $text)
}

# Hermes: Servernamen aus dem mcp_servers-Block der YAML ziehen.
# Nur Schluessel mit EXAKT 2 Leerzeichen Einzug und ohne Wert gelten als Servername.
function HoleHermesNamen {
  param($pfad)
  $zeilen = Get-Content $pfad
  $idx = ($zeilen | Select-String -Pattern '^mcp_servers:' | Select-Object -First 1).LineNumber
  if (-not $idx) { return $null }
  $namen = @()
  for ($i = $idx; $i -lt $zeilen.Count; $i++) {
    $ln = $zeilen[$i]
    if ($ln -match '^[A-Za-z0-9_]' -and $ln -notmatch '^mcp_servers:') { break }
    if ($ln -match '^  ([A-Za-z0-9_.\-]+):\s*$') { $namen += $Matches[1]; continue }
    # 'enabled: false' auf Serverebene: eingetragen, aber abgeschaltet - zaehlt
    # nicht als vorhanden. Ohne das meldete der Abgleich revolut-x und blender
    # als OK, obwohl Hermes sie gar nicht startet (29.09.2026).
    if ($ln -match '^    enabled:\s*false\s*$' -and $namen.Count) { $namen = @($namen | Select-Object -SkipLast 1) }
  }
  return $namen
}

Write-Host '=== MCP-Sync-Pruefung ==='

# 1. Grunddateien vorhanden?
if (-not (Test-Path $manifest)) {
  $fehler += 'Manifest fehlt: ' + $manifest
} else {
  Schreibe 'OK' 'Manifest vorhanden'
}

$claude = $null
if (-not $confClaude) {
  $warnungen += 'Claude-Konfiguration nicht gefunden (weder %APPDATA% noch MSIX-Container)'
} else {
  Schreibe 'OK' ('Claude-Konfiguration: ' + $confClaude)
  $zweiteClaude = @($kandidaten | Where-Object { $_ -ne $confClaude -and (Test-Path $_) })
  if ($zweiteClaude.Count -gt 0) {
    $warnungen += 'Zweite Claude-Konfiguration vorhanden, nicht gelesen: ' + ($zweiteClaude -join ', ') + ' - verwaiste Datei kann den Abgleich verfaelschen'
  }
  try {
    $claude = @((Get-Content $confClaude -Raw | ConvertFrom-Json).mcpServers.PSObject.Properties.Name | Sort-Object)
  } catch {
    $fehler += 'Claude-Konfiguration ungueltig: ' + $_
    $claude = @()
  }
}

$hermesNamen = @()
if (-not (Test-Path $confHermes)) {
  $warnungen += 'Hermes-Konfiguration nicht gefunden: ' + $confHermes
} else {
  Schreibe 'OK' 'Hermes-Konfiguration vorhanden'
  $hermesNamen = @(HoleHermesNamen -pfad $confHermes | Sort-Object)
  if (-not $hermesNamen) {
    $fehler += 'Hermes-Konfiguration enthaelt keinen mcp_servers-Block'
  }
}

if ($confClaude -and $claude) { Schreibe 'OK' ('Claude hat ' + $claude.Count + ' Server eingetragen') }
if ($hermesNamen) { Schreibe 'OK' ('Hermes hat ' + $hermesNamen.Count + ' Server eingetragen') }

# 1b. Konfiguration neuer als Manifest? (stille App-Ueberschreibungen erkennen)
if (Test-Path $manifest) {
  $manifestZeit = (Get-Item $manifest).LastWriteTime
  foreach ($conf in @($confClaude, $confHermes)) {
    if ($conf -and (Test-Path $conf)) {
      $confZeit = (Get-Item $conf).LastWriteTime
      if ($confZeit -gt $manifestZeit) {
        $warnungen += 'Konfiguration neuer als Manifest: ' + $conf + ' (' + $confZeit.ToString('yyyy-MM-dd HH:mm') + ') - vermutlich App-Ueberschreibung, Manifest pruefen'
      }
    }
  }
}

# 2. Serverprogramme existieren?
if (Test-Path $manifest) {
  $mcp = Get-Content $manifest -Raw | ConvertFrom-Json
  $soll = @($mcp.servers | Where-Object { $_.enabled })
  $sollNamen = @($soll | ForEach-Object { $_.name })

  Write-Host ''
  Write-Host '=== Serverprogramme existieren? ==='
  foreach ($srv in $soll) {
    $cwd = Join-Path $wurzel $srv.cwd
    if (-not (Test-Path $cwd)) {
      $fehler += $srv.name + ': Verzeichnis fehlt: ' + $cwd
      continue
    }
    $cmdPfad = $null
    if ($srv.command -match '^[.\\]') { $cmdPfad = Join-Path $cwd $srv.command }
    elseif ($srv.args -and $srv.args.Count -gt 0 -and $srv.args[0] -match '^[.\\]') { $cmdPfad = Join-Path $cwd $srv.args[0] }
    if ($cmdPfad -and -not (Test-Path $cmdPfad)) {
      $fehler += $srv.name + ': Programm fehlt: ' + $cmdPfad
    } else {
      Schreibe 'OK' $srv.name
    }
  }

  # 3. Abgleich Manifest <-> Agenten
  Write-Host ''
  Write-Host '=== Abgleich Manifest <-> Agenten ==='
  foreach ($srv in $soll) {
    $agent = $srv.agent
    if (-not $agent) { $agent = 'beide' }
    if ($agent -in @('beide', 'claude') -and $confClaude -and $claude -and ($srv.name -notin $claude)) {
      $fehler += $srv.name + ': im Manifest aktiv (' + $agent + '), fehlt bei Claude'
    }
    if ($agent -in @('beide', 'hermes') -and $hermesNamen -and ($srv.name -notin $hermesNamen)) {
      $fehler += $srv.name + ': im Manifest aktiv (' + $agent + '), fehlt bei Hermes'
    }
  }
  $alleAgentenNamen = @(($claude + $hermesNamen) | Sort-Object -Unique)
  foreach ($name in $alleAgentenNamen) {
    if ($name -notin $sollNamen) {
      $warnungen += $name + ': in Agenten-Konfiguration, aber NICHT im Manifest'
    }
  }
  foreach ($aus in $mcp.disabled) {
    if ($aus.name -in $claude -or $aus.name -in $hermesNamen) {
      $warnungen += $aus.name + ': im Manifest deaktiviert, laeuft aber bei einem Agenten'
    }
  }
}

# 4. Klartext-Zugangsdaten in der Claude-Konfiguration?
if ($confClaude) {
  Write-Host ''
  Write-Host '=== Klartext-Zugangsdaten pruefen ==='
  $conf = Get-Content $confClaude -Raw
  $gefunden = $false
  foreach ($muster in @('KRAKEN_API_KEY', 'KRAKEN_API_SECRET', 'REVOLUT_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')) {
    $rgx = [regex]::new('"?' + [regex]::Escape($muster) + '"?\s*:\s*"([^"]{20,})"')
    $m = $rgx.Match($conf)
    if ($m.Success -and -not $m.Groups[1].Value.StartsWith('${env:')) {
      $warnungen += 'Moeglicher Klartext-Schluessel in Claude-Konfiguration: ' + $muster
      $gefunden = $true
    }
  }
  if (-not $gefunden) { Schreibe 'OK' 'Keine Klartext-Schluessel gefunden' }
}

# Ausgabe
Write-Host ''
if ($fehler.Count -eq 0 -and $warnungen.Count -eq 0) {
  Write-Host '=== ALLES IN ORDNUNG ==='
  exit 0
}
if ($warnungen.Count -gt 0) {
  Write-Host '=== WARNUNGEN ==='
  foreach ($w in $warnungen) { Write-Host ('  WARN ' + $w) }
}
if ($fehler.Count -gt 0) {
  Write-Host '=== FEHLER ==='
  foreach ($f in $fehler) { Write-Host ('  FEHLER ' + $f) }
  exit 1
}
exit 0
