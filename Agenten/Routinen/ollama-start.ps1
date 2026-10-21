# Startet Ollama (ollama serve) - die lokale Modell-Laufzeit, an der alle
# LLM-Urteile haengen (Moon-Dev-Agenten, LLM-Spuren). Von der Aufgabenplanung
# bei der Anmeldung aufgerufen (+15 Sekunden Verzoegerung).
#
# WARUM: Ollama hat keinen Windows-Dienst (gemessen 16.09.2026: kein
# ollama-Process, kein Service-Eintrag, Port 11434 zu, nachdem die
# Start-Sitzung endete). Ohne Ollama liefern alle LLM-Aufrufe leeren Content
# und die Agenten fallen still auf "DO NOTHING" zurueck.
#
# Laeuft schon ein Ollama (auch ein von Hand gestartetes), wird NICHTS
# gestartet - zwei Server auf demselben Port schliessen sich aus; die
# Verzweigung steht im Protokoll.
#
# Erst-Einrichtung / Neuaufsetzen der Aufgabe (Administrator noetig fuer die
# Registrierung, nicht fuer den Betrieb):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\ollama-start-aufgabe.ps1

$ErrorActionPreference = 'Stop'
# =====================================================================
# AUSGESETZT seit 11.10.2026: Ollama wurde deinstalliert. Alle Hermes-Profile
# und die default-Config laufen jetzt ueber die managede llamacpp-Runtime
# (Port 18434, provider: llamacpp, Modell gemma-4-E4B-it-OBLITERATED-Q8_0).
# Der Scheduled Task ruft dieses Skript weiter auf, tut aber nichts mehr.
# Original (falls je noetig): Agenten/Routinen/ollama-start.ps1.bak-20261011
# Erst-Einrichtung einer neuen lokalen Laufzeit siehe Hermes local_runtime.
# =====================================================================
$logs = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  OLLAMA AUSGESETZT (deinstalliert 11.10.2026) - nichts zu tun." |
  Add-Content (Join-Path $logs 'ollama-start-letzter-lauf.log') -Encoding UTF8
exit 0