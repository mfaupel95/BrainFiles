# kraken.ps1 - startet die kraken-cli mit dem RICHTIGEN Schluesselpaar.
#
# WARUM ES DIESEN UMFANG GIBT (gemessen 22.09.2026):
# In der Benutzerumgebung liegen ZWEI Kraken-Paare:
#   KRAKEN_API_KEY / KRAKEN_API_SECRET          -> von Kraken abgelehnt
#                                                  ("EAPI:Invalid key")
#   KRAKEN_SPOT_API_KEY / KRAKEN_SPOT_API_SECRET -> das Paar, mit dem unsere
#                                                  Spuren arbeiten (gueltig)
# kraken.py liest das SPOT-Paar, die kraken-cli liest die generischen Namen.
# Ohne Uebersetzung scheitert jede private Abfrage der CLI - und zwar mit
# einer Meldung, die nach falschem Schluessel aussieht, obwohl nur der falsche
# NAME gelesen wurde. Dieser Wrapper setzt die generischen Namen aus den
# SPOT-Variablen; Werte werden nie ausgegeben.
#
# Aufruf (Beispiele):
#   .\kraken.ps1 ticker BTCUSD -o json
#   .\kraken.ps1 balance -o json
#   .\kraken.ps1 order buy XBTEUR 0.0002 --type market --validate -o json
#
# Gesperrt bleibt gesperrt: echte Orders aus einer Sitzung sind laut
# Wissen/Handelsregeln.md nicht erlaubt. Fuer den Handel gilt der Beleg-Weg
# (Agenten/Handel/freigabebeleg.py + Kraken-MCP-Werkzeug kraken_order_mit_beleg).
#
# KEIN param-Block und kein [CmdletBinding()]: sonst deutet PowerShell
# CLI-Schalter als eigene Parameter ("-o" wird zu -OutVariable/-OutBuffer und
# bricht mit "Parametername o ist nicht eindeutig" ab). Die Argumente laufen
# deshalb unveraendert ueber $args durch.

$ErrorActionPreference = 'Continue'

$exe = Join-Path $PSScriptRoot '..\..\Werkstatt\Repos\kraken-cli\target\release\kraken.exe'
if (-not (Test-Path $exe)) {
    Write-Error ("kraken-cli nicht gebaut: $exe`n" +
        "Bauen (dauert beim ersten Mal laenger, braucht Rust):`n" +
        "  cd <BrainFiles>\Werkstatt\Repos\kraken-cli`n" +
        "  cargo build --release --bin kraken")
    exit 1
}

function Hole-BenutzerVariable([string]$Name) {
    # Erst die Prozessumgebung, dann die Registry - dieselbe Reihenfolge wie
    # kraken.py. Get-ItemProperty HKCU nutzt in manchen Sitzungen einen anderen
    # Benutzerkontext; [Environment]::GetEnvironmentVariable ist verlaesslich.
    $wert = [Environment]::GetEnvironmentVariable($Name, 'User')
    if (-not $wert) {
        $wert = [Environment]::GetEnvironmentVariable($Name, 'Process')
    }
    if ($wert) { return $wert.Trim() }
    return ''
}

$spotKey = Hole-BenutzerVariable 'KRAKEN_SPOT_API_KEY'
$spotSecret = Hole-BenutzerVariable 'KRAKEN_SPOT_API_SECRET'
if (-not $spotKey -or -not $spotSecret) {
    Write-Error ('KRAKEN_SPOT_API_KEY / KRAKEN_SPOT_API_SECRET fehlen - ' +
        'ohne sie kann die CLI nichts Privates abfragen.')
    exit 1
}

# Uebersetzung der Namen; die Werte bleiben im Prozess, sie werden nicht gezeigt.
$env:KRAKEN_API_KEY = $spotKey
$env:KRAKEN_API_SECRET = $spotSecret

& $exe @args
exit $LASTEXITCODE
