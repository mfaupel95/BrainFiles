$ErrorActionPreference = 'Stop'
$root   = 'C:\Users\faupe\Documents\BrainFiles\MaxHirn'
$wissen = Join-Path $root 'Wissen'
$index  = Get-Content (Join-Path $wissen 'INDEX.md') -Raw
$erlaubt = @('archiv','betrieb','finanzen','handel','hardware','holz','ki-agenten','mcp','profil','sicherheit','steuern','system')
$ids = @{}
$fehler = 0

Get-ChildItem $wissen -Filter *.md | Where-Object { $_.Name -notlike '*.bak*' } | ForEach-Object {
    $n = $_.Name
    $t = Get-Content $_.FullName -Raw
    $kopf = ($t -split "`r?`n")

    # 1. Frontmatter genau einmal, korrekt begrenzt
    if ($kopf[0] -ne '---') { Write-Output ("KEIN FRONTMATTER: " + $n); $fehler++; return }
    $ende = 1; while ($ende -lt $kopf.Count -and $kopf[$ende] -ne '---') { $ende++ }
    if ($ende -ge $kopf.Count) { Write-Output ("FRONTMATTER NICHT GESCHLOSSEN: " + $n); $fehler++; return }
    $fm = $kopf[1..($ende-1)]

    # 2. Pflichtfelder
    foreach ($f in @('id','title','tags','created','updated','related','summary')) {
        if (-not ($fm | Where-Object { $_ -match ('^' + $f + ':') })) { Write-Output ("FELD FEHLT (" + $f + "): " + $n); $fehler++ }
    }

    # 3. ID eindeutig
    $id = (($fm | Where-Object { $_ -match '^id:' }) -replace '^id:\s*','').Trim()
    if ($ids.ContainsKey($id)) { Write-Output ("ID DOPPELT: " + $id + " in " + $n); $fehler++ } else { $ids[$id] = $n }

    # 4. Tags kontrolliert
    $tagzeile = (($fm | Where-Object { $_ -match '^tags:' }) -replace '^tags:\s*','').Trim(' ', '[', ']')
    foreach ($tag in ($tagzeile -split ',')) {
        $tag = $tag.Trim()
        if ($tag -and ($erlaubt -notcontains $tag)) { Write-Output ("TAG NICHT IN LISTE (" + $tag + "): " + $n); $fehler++ }
    }

    # 5. In Registry eingetragen? (INDEX.md selbst ausgenommen)
    if ($n -ne 'INDEX.md' -and $index -notmatch [regex]::Escape($id)) { Write-Output ("NICHT IN REGISTRY: " + $n + " (" + $id + ")"); $fehler++ }

    # 6. Genau eine H1 direkt nach dem Frontmatter vorhanden
    if (-not ($t -match '(?m)^#\s+\S')) { Write-Output ("KEINE H1: " + $n); $fehler++ }
}

# 7. Registry-Zeilen: verweist jeder Pfad auf eine existierende Datei?
foreach ($z in ($index -split "`r?`n")) {
    if ($z -match '`(Wissen/[^`]+\.md)`') {
        $p = Join-Path $root ($Matches[1] -replace '/','\')
        if (-not (Test-Path $p)) { Write-Output ("REGISTRY-PFAD FEHLT: " + $Matches[1]); $fehler++ }
    }
}

# 8. Zugaenge.md: bewusst ohne Frontmatter, aber registriert?
if ($index -notmatch '20260830-zugaenge') { Write-Output 'ZUGAENGE NICHT REGISTRIERT'; $fehler++ }

Write-Output ('--- Notizen geprüft: ' + $ids.Count + ' | Fehler: ' + $fehler)
