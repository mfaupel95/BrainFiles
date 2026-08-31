# Phase 7 -- Die KI-Ablagen im Benutzerordner: aufraeumen, nicht verschieben.
#
# Max' Entscheidung vom 30.08.2026: die Konfiguration bleibt, wo die Programme
# sie suchen. ~/.claude, ~/.codex und %APPDATA%\Claude sind fest verdrahtet;
# eine Junction dorthin waere ein zusaetzlicher Mechanismus, der bei jedem
# Umzug erneut gerichtet werden muss.
#
# Dieses Skript loescht deshalb NUR, was nachweislich leer ist, und legt sonst
# eine Tabelle vor. Was hier steht, gehoert in
# Wissen/KI-Ablagen-im-Benutzerordner.md.
#
#   .\70-benutzerordner.ps1            nur ansehen
#   .\70-benutzerordner.ps1 -Echt      die leeren Ordner entfernen

param([switch]$Echt)
$DryRun = -not $Echt

. "$PSScriptRoot\gemeinsam.ps1"

$orte = @(
    @{ Pfad = "$env:USERPROFILE\.claude"                      ; Zweck = 'Claude Code: Sitzungen, Projekte, Skills, Plugins' }
    @{ Pfad = "$env:USERPROFILE\.codex"                       ; Zweck = 'Codex: Sitzungen, Konfiguration, Automationen' }
    @{ Pfad = "$env:USERPROFILE\.agents"                      ; Zweck = 'gemeinsame Agenten-Skills' }
    @{ Pfad = "$env:USERPROFILE\.ollama"                      ; Zweck = 'Ollama: Schluesselpaar und Konfiguration (nicht die Modelle)' }
    @{ Pfad = "$env:USERPROFILE\.cua-driver"                  ; Zweck = 'Computer-Use-Treiber' }
    @{ Pfad = "$env:USERPROFILE\.claude-server-commander"     ; Zweck = 'Desktop Commander: Konfiguration und Aufrufprotokoll' }
    @{ Pfad = "$env:USERPROFILE\.tooluniverse"                ; Zweck = 'ToolUniverse: Cache' }
    @{ Pfad = "$env:APPDATA\Claude"                           ; Zweck = 'Claude Desktop: MCP-Konfiguration, Erweiterungen' }
    @{ Pfad = "$env:LOCALAPPDATA\Claude"                      ; Zweck = 'Claude Desktop: Programmstand' }
    @{ Pfad = "$env:LOCALAPPDATA\OpenAI\Codex"                ; Zweck = 'Codex: Programm und Laufzeiten' }
    @{ Pfad = "$env:LOCALAPPDATA\Ollama"                      ; Zweck = 'Ollama: Protokolle' }
    @{ Pfad = "$env:LOCALAPPDATA\Claude-3p"                   ; Zweck = 'Rest einer alten Installation' }
    @{ Pfad = "$env:LOCALAPPDATA\Claude-Data"                 ; Zweck = 'Rest einer alten Installation' }
    @{ Pfad = "$env:APPDATA\Claude Code"                      ; Zweck = 'Chrome-Anbindung' }
    @{ Pfad = "$env:APPDATA\Hermes"                           ; Zweck = 'Hermes: Programmstand (Daten liegen in Agenten\Hermes)' }
)

$tabelle = @()
foreach ($o in $orte) {
    if (-not (Test-Path $o.Pfad)) { continue }
    $dateien = @(Get-ChildItem $o.Pfad -Recurse -Force -File -EA SilentlyContinue)
    $mb = [math]::Round((($dateien | Measure-Object Length -Sum).Sum) / 1MB, 1)
    $tabelle += [pscustomobject]@{
        MB       = $mb
        Dateien  = $dateien.Count
        Geaendert = (Get-Item $o.Pfad -Force).LastWriteTime.ToString('yyyy-MM-dd')
        Ort      = $o.Pfad.Replace($env:USERPROFILE, '~')
        Zweck    = $o.Zweck
    }
}
$tabelle | Sort-Object -Property MB -Descending | Format-Table -AutoSize -Wrap

# --- Nur das nachweislich Leere ------------------------------------------
Schritt ''
$leer = @($tabelle | Where-Object { $_.Dateien -eq 0 })
if (-not $leer) { Schritt 'Nichts nachweislich Leeres gefunden.' 'ok' }
foreach ($l in $leer) {
    $voll = $l.Ort.Replace('~', $env:USERPROFILE)
    if ($DryRun) { Schritt "[Probe] loeschen (0 Dateien): $($l.Ort)" }
    else { Remove-Item -LiteralPath $voll -Recurse -Force; Schritt "geloescht (0 Dateien): $($l.Ort)" 'ok' }
}

Schritt ''
Schritt 'Alles Uebrige bleibt liegen: die Programme suchen es genau dort.' 'warn'
Bilanz "$($tabelle.Count) KI-Ablagen im Benutzerordner, $($leer.Count) davon leer und entbehrlich."
Protokoll-Schreiben '70-benutzerordner' | Out-Null
