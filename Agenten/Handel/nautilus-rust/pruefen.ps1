# pruefen.ps1 — nautilus-rust reproduzierbar bauen, testen und die drei
# Programme einmal wirklich laufen lassen. Exit 0 nur, wenn ALLES sauber ist.
# Aufruf:  & 'Agenten/Handel/nautilus-rust/pruefen.ps1'   (PowerShell)
#          pwsh Agenten/Handel/nautilus-rust/pruefen.ps1  (bash/MSYS)
# Falle: $ErrorActionPreference='Stop' + 'cargo ... 2>&1' bricht ab, weil
# stderr als Fehler zaehlt (NativeCommandError) — deshalb nur $LASTEXITCODE.

$ErrorActionPreference = 'Continue'
$hier = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $hier

function Fehler($text) {
    Write-Host "PRUEFEN FEHLER: $text" -ForegroundColor Red
    exit 1
}

Write-Host '[1/5] cargo fmt --check'
cargo fmt --check
if ($LASTEXITCODE -ne 0) { Fehler 'cargo fmt --check (Exit ' + $LASTEXITCODE + ')' }

Write-Host '[2/5] cargo build --workspace'
cargo build --workspace
if ($LASTEXITCODE -ne 0) { Fehler 'cargo build --workspace' }

Write-Host '[3/5] cargo test --workspace'
cargo test --workspace
if ($LASTEXITCODE -ne 0) { Fehler 'cargo test --workspace' }

Write-Host '[4/5] quant-alpha -> ranked_book.json'
& .\target\debug\quant-alpha.exe
if ($LASTEXITCODE -ne 0) { Fehler 'quant-alpha.exe' }
if (-not (Test-Path .\ranked_book.json)) { Fehler 'ranked_book.json fehlt nach quant-alpha' }

Write-Host '[5/5] quant-strategy + quant-planes'
& .\target\debug\quant-strategy.exe
if ($LASTEXITCODE -ne 0) { Fehler 'quant-strategy.exe' }
& .\target\debug\quant-planes.exe
if ($LASTEXITCODE -ne 0) { Fehler 'quant-planes.exe (Ebenen-Grenze verletzt)' }

Write-Host 'PRUEFEN OK: fmt, build, 20 Tests, alle drei Programme' -ForegroundColor Green
exit 0
