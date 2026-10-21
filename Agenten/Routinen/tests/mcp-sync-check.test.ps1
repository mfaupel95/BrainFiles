# mcp-sync-check.test.ps1 - Tests fuer mcp-sync-check.ps1 (Hausstil wie Bus-Tests, kein Framework).
# Aufruf: powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/tests/mcp-sync-check.test.ps1
# Endet mit "mcp-sync-check bestanden". Nur ASCII im Quelltext.
#
# Hintergrund (T-434, 21.10.2026): Der Pruefer liess ausgeschaltete Config-Eintraege
# (enabled: false) in BEIDEN Namenslisten verschwinden. Sieben OAuth-Kandidaten standen
# deshalb in Agenten/Hermes/config.yaml, fehlten im Manifest und meldeten nichts. Der
# Test haelt die neue Regel fest: so ein Eintrag ist ein HINWEIS, kein Fehler - und ein
# dokumentierter Eintrag (Manifest.disabled) schweigt.
$ErrorActionPreference = 'Continue'
$Checker = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'mcp-sync-check.ps1'
$Ps = (Get-Process -Id $PID).Path
$script:Fehler = 0
$script:Aufraeumen = New-Object System.Collections.ArrayList

function Pruefe([string]$Name, [bool]$Bedingung, [string]$Detail = '') {
    if ($Bedingung) { Write-Host "  ok     $Name" }
    else { Write-Host "  FEHLT  $Name $Detail"; $script:Fehler++ }
}
function Neue-Wurzel {
    $p = Join-Path ([IO.Path]::GetTempPath()) ('mcp sync test ' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $p | Out-Null
    [void]$script:Aufraeumen.Add($p)
    return $p
}
function Schreibe([string]$Pfad, [string]$Inhalt) {
    $d = Split-Path $Pfad -Parent
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    [IO.File]::WriteAllText($Pfad, $Inhalt, (New-Object System.Text.UTF8Encoding($false)))
}
function Neue-Fixture([string]$ServersJson, [string]$DisabledJson, [string]$HermesYaml) {
    $w = Neue-Wurzel
    $m = Join-Path $w 'MCP-Manifest.json'
    Schreibe $m ('{"version":"test","updated":"2026-10-21","servers":[' + $ServersJson + '],"disabled":[' + $DisabledJson + ']}')
    $c = Join-Path $w 'config.yaml'
    Schreibe $c $HermesYaml
    $cc = Join-Path $w 'claude_desktop_config.json'
    Schreibe $cc '{"mcpServers":{}}'
    return [pscustomobject]@{ Wurzel = $w; Manifest = $m; Config = $c; Claude = $cc }
}
function Lauf($fx) {
    $o = & $Ps -NoProfile -ExecutionPolicy Bypass -File $Checker -Manifest $fx.Manifest -ConfigHermes $fx.Config -ConfigClaude $fx.Claude 2>&1 | Out-String
    return [pscustomobject]@{ Exit = $LASTEXITCODE; Out = $o }
}
function Y([string[]]$Zeilen) { return (($Zeilen -join "`n") + "`n") }

Write-Host '--- Geruest ---'
Pruefe 'Pruefer vorhanden' (Test-Path -LiteralPath $Checker)

Write-Host '--- ausgeschalteter Eintrag ohne Manifest (HINWEIS) ---'
$fx = Neue-Fixture '' '' (Y @(
    'mcp_servers:',
    '  geistig:',
    '    url: https://beispiel.invalid/mcp',
    '    auth: oauth',
    '    enabled: false',
    '  laeuft:',
    '    command: node'
))
$r = Lauf $fx
Pruefe 'Hinweis genannt' ($r.Out -match 'HINWEIS geistig: in Hermes-Config abgeschaltet') $r.Out
Pruefe 'Hinweis ist kein Fehler (Exit 0)' ($r.Exit -eq 0) "Exit=$($r.Exit)"
Pruefe 'kein FEHLER-Block' (-not ($r.Out -match '=== FEHLER ===')) $r.Out
Pruefe 'ausgeschaltete werden beziffert' ($r.Out -match 'aber ausgeschaltet: geistig') $r.Out
Pruefe 'eingeschalteter bleibt sichtbar' ($r.Out -match 'laeuft: in Agenten-Konfiguration, aber NICHT im Manifest') $r.Out

Write-Host '--- dokumentierter Kandidat schweigt ---'
$fx = Neue-Fixture '' ('{"name":"geistig","reason":"Kandidat, geprueft"}') (Y @(
    'mcp_servers:',
    '  geistig:',
    '    url: https://beispiel.invalid/mcp',
    '    enabled: false'
))
$r = Lauf $fx
Pruefe 'kein Hinweis fuer dokumentierten Eintrag' (-not ($r.Out -match 'HINWEIS geistig')) $r.Out
Pruefe 'Exit 0' ($r.Exit -eq 0) "Exit=$($r.Exit)"

Write-Host '--- Manifest deaktiviert, Agent laesst es laufen (alte Regel) ---'
$fx = Neue-Fixture '' ('{"name":"alt","reason":"am 16.09. entfernt"}') (Y @(
    'mcp_servers:',
    '  alt:',
    '    command: node'
))
$r = Lauf $fx
Pruefe 'Warnung statt Hinweis' (($r.Out -match 'alt: im Manifest deaktiviert, laeuft aber bei einem Agenten') -and (-not ($r.Out -match 'HINWEIS alt'))) $r.Out

Write-Host '--- aktiver Server fehlt bei Hermes (FEHLER) ---'
$fx = Neue-Fixture '{"name":"fehlt","enabled":true,"agent":"hermes","type":"stdio","command":"node.exe","cwd":"Agenten"}' '' (Y @(
    'mcp_servers:',
    '  anderer:',
    '    command: node'
))
$r = Lauf $fx
Pruefe 'Fehler gemeldet' ($r.Out -match 'fehlt: im Manifest aktiv \(hermes\), fehlt bei Hermes') $r.Out
Pruefe 'Exit 1' ($r.Exit -eq 1) "Exit=$($r.Exit)"

Write-Host '--- Hermes-Config ohne mcp_servers-Block (FEHLER) ---'
$fx = Neue-Fixture '' '' (Y @('gateway:', '  port: 9900'))
$r = Lauf $fx
Pruefe 'fehlender Block gemeldet' ($r.Out -match 'enthaelt keinen mcp_servers-Block') $r.Out
Pruefe 'Exit 1' ($r.Exit -eq 1) "Exit=$($r.Exit)"
Pruefe 'kein Absturz auf leerer Liste' (-not ($r.Out -match 'NullReference|Cannot .* on a null')) $r.Out

Write-Host '--- echte Hausdateien (Gegenprobe, rein lesend) ---'
$hermes = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'Hermes\config.yaml'
$r = & $Ps -NoProfile -ExecutionPolicy Bypass -File $Checker -ConfigHermes $hermes 2>&1 | Out-String
Pruefe 'echter Lauf liest die Hermes-Config' ($r -match 'Hermes-Konfiguration vorhanden') $r
Pruefe 'echter Lauf nennt die drei ausgeschalteten' ($r -match 'aber ausgeschaltet: .*affinity.*blender.*revolut-x') $r
Pruefe 'echter Lauf ohne Hinweis (Config == Manifest)' (-not ($r -match 'HINWEIS ')) $r
Pruefe 'echter Lauf Exit 0 oder 1 (nicht 2)' (($LASTEXITCODE -eq 0) -or ($LASTEXITCODE -eq 1)) "Exit=$($LASTEXITCODE) $r"

# === ENDE (neue Testabschnitte oberhalb dieser Zeile einfuegen) ===
foreach ($p in $script:Aufraeumen) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
if ($script:Fehler -gt 0) { Write-Host "mcp-sync-check FEHLGESCHLAGEN: $($script:Fehler) Pruefung(en)"; exit 1 }
Write-Host 'mcp-sync-check bestanden'
