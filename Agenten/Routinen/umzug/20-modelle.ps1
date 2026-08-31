# Phase 2 -- Modelle aus dem Vault heraus und die Ollama-Ablage geradeziehen.
#
# Der Ordner ist mit 51 GB der groesste im Vault und gehoert dort nicht hin:
# er ist neu herunterladbar (so steht es in Schutzregeln.md), wird aber jede
# Nacht mitgesichert. Nebenbei wird ein alter Fehler behoben - OLLAMA_MODELS
# zeigt auf Modelle\Ollama\models (1 Blob), waehrend der wirkliche Store mit
# 16,9 GB in Modelle\blobs + Modelle\manifests liegt.
#
# Ollama erwartet in OLLAMA_MODELS einen Ordner, der 'blobs' und 'manifests'
# NEBENEINANDER enthaelt. Genau das wird Modelle\Ollama\Store.
#
#   .\20-modelle.ps1            Trockenlauf
#   .\20-modelle.ps1 -Echt      wirklich (beendet Ollama und startet es neu)

param([switch]$Echt)
$DryRun = -not $Echt

. "$PSScriptRoot\gemeinsam.ps1"
$pfade  = Get-Pfade
$wurzel = Get-Wurzel
function P([string]$r) { Join-Path $wurzel $r }

Schritt "Wurzel: $wurzel"

# --- 1. Ollama beenden -----------------------------------------------------
# Windows verweigert das Umbenennen eines Ordners, unter dem eine laufende
# .exe liegt. Ollama ist ein Dienst ohne eigenen Zustand im Programmordner -
# beenden und neu starten kostet nichts.
$ollamaWar = Get-Process -Name 'ollama', 'ollama app' -ErrorAction SilentlyContinue
if ($ollamaWar) {
    Schritt "Ollama laeuft ($($ollamaWar.Count) Prozesse) und muss weichen."
    if (-not $DryRun) {
        $ollamaWar | Stop-Process -Force
        Start-Sleep -Seconds 2
        Schritt 'Ollama beendet.' 'ok'
    }
} else { Schritt 'Ollama laeuft nicht.' 'ok' }

# Andere Blockierer melden, aber nicht anfassen.
$fremd = Get-Process | Where-Object { $_.Path -like "*BrainFiles*Modelle*" }
if ($fremd -and -not $DryRun) {
    $fremd | ForEach-Object { Schritt "  BLOCKIERT NOCH: $($_.Name) (PID $($_.Id))" 'fehler' }
    Bilanz 'abgebrochen - es laufen noch Programme aus Modelle\.' -Erfolg:$false
    return
}

# --- 2. Verschieben --------------------------------------------------------
Schritt ''
Schritt 'Verschieben:'
foreach ($m in $pfade.Modelle) { Verschiebe -Von (P $m.Von) -Nach (P $m.Nach) -DryRun:$DryRun }

foreach ($n in $pfade.ModelleNeu) {
    if (-not (Test-Path (P $n))) {
        if ($DryRun) { Schritt "  [Probe] anlegen: $n" } else { New-Item -ItemType Directory -Path (P $n) -Force | Out-Null; Schritt "  angelegt: $n" 'ok' }
    }
}

# --- 3. Die verwaiste zweite Ablage --------------------------------------
# Erst Hash-Vergleich, dann Urteil. Name und Groesse allein sind kein Beweis.
Schritt ''
$alt = P 'Modelle\Ollama\models'
if (Test-Path $alt) {
    $altBlobs = @(Get-ChildItem (Join-Path $alt 'blobs') -File -EA SilentlyContinue)
    $store    = P $pfade.OllamaStore
    $doppelt = 0; $eigen = @()
    foreach ($b in $altBlobs) {
        $imStore = Join-Path $store "blobs\$($b.Name)"
        if ((Test-Path $imStore) -and (Get-FileHash $b.FullName).Hash -eq (Get-FileHash $imStore).Hash) { $doppelt++ }
        else { $eigen += $b.Name }
    }
    Schritt "verwaiste Ablage Modelle\Ollama\models: $($altBlobs.Count) Blobs, davon $doppelt auch im Store."
    if ($eigen) { $eigen | ForEach-Object { Schritt "  NUR HIER: $_" 'warn' } }
    if ($eigen.Count -eq 0 -and $altBlobs.Count -gt 0 -and -not $DryRun) {
        Remove-Item -LiteralPath $alt -Recurse -Force
        Schritt 'verwaiste Ablage entfernt (jeder Blob lag hash-gleich im Store).' 'ok'
    }
}
foreach ($l in $pfade.ModelleLeer) {
    if ((Test-Path (P $l)) -and -not (Get-ChildItem (P $l) -Recurse -Force -EA SilentlyContinue)) {
        if (-not $DryRun) { Remove-Item -LiteralPath (P $l) -Force -Recurse; Schritt "leerer Altordner entfernt: $l" 'ok' }
    }
}

# --- 4. OLLAMA_MODELS richtigstellen --------------------------------------
Schritt ''
$soll = P $pfade.OllamaStore
$ist  = [Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'User')
Schritt "OLLAMA_MODELS bisher: $ist"
Schritt "OLLAMA_MODELS kuenftig: $soll"
if (-not $DryRun -and $ist -ne $soll) {
    [Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $soll, 'User')
    $env:OLLAMA_MODELS = $soll
    Schritt 'gesetzt (Benutzervariable).' 'ok'
}

# --- 5. Was ist Kimi-K2.7-Code wirklich? ----------------------------------
# 32 GB, aber im Arbeitsbaum liegt keine Gewichtsdatei. Nur berichten - ueber
# 32 GB entscheidet Max, nicht ein Skript.
Schritt ''
$kimi = P 'Modelle\Kimi-K2.7-Code'
if (Test-Path $kimi) {
    $lfs = git -C $kimi lfs ls-files 2>&1 | Select-Object -First 5
    $n   = (git -C $kimi lfs ls-files 2>&1 | Measure-Object).Count
    Schritt "Kimi-K2.7-Code: $n von LFS verwaltete Dateien, davon ausgecheckt:"
    $lfs | ForEach-Object { Schritt "  $_" }
}

# --- 6. Ollama zurueck und Gegenprobe -------------------------------------
if (-not $DryRun -and $ollamaWar) {
    $exe = P 'Modelle\Programme\Ollama\ollama app.exe'
    if (Test-Path $exe) { Start-Process $exe; Start-Sleep -Seconds 5; Schritt 'Ollama neu gestartet.' 'ok' }
}
if (-not $DryRun) {
    $liste = & (P 'Modelle\Programme\Ollama\ollama.exe') list 2>&1
    $liste | ForEach-Object { Schritt "  $_" }
    $modelle = ($liste | Select-Object -Skip 1 | Where-Object { $_ -match '\S' }).Count
    Bilanz "Modelle liegen in BrainFiles\Modelle; ollama list meldet $modelle Modell(e)." -Erfolg:($modelle -gt 0)
} else {
    Bilanz 'Probe gelaufen - nichts veraendert.'
}
Protokoll-Schreiben '20-modelle' | Out-Null
