# Alter jedes offenen Pfades in Minuten - Grundlage fuer die Frage, welche
# Fremdarbeit ruht und welche eine laufende Sitzung gerade schreibt.
#
# Aufruf aus der Repo-Wurzel:
#   powershell -NoProfile -File <skillordner>\scripts\offene-pfade-alter.ps1
#
# Bewusst ohne Parameter: die Zahlen sind die Antwort, die Ausgabe wird gelesen
# (Alter aufsteigend sortiert), nicht maschinell weiterverarbeitet.

$wurzel = (Get-Location).Path
$jetzt = Get-Date

Write-Output ('Jetzt (Host): ' + $jetzt.ToString('HH:mm:ss'))
Write-Output '--- letzte Commits (Zeit = Aktivitaet der Sitzung) ---'
git log -3 --format='%h %ci %s'
Write-Output '--- offene Pfade ---'

git status --porcelain | ForEach-Object {
    $zeile = $_.ToString()
    if ($zeile.Length -lt 4) { return }
    $pfad = $zeile.Substring(3).Trim('"').Trim()
    $voll = Join-Path $wurzel $pfad
    if (Test-Path $voll) {
        $i = Get-Item $voll
        $art = if ($i.PSIsContainer) { 'ORDNER' } else { 'DATEI' }
        $alter = [math]::Round(($jetzt - $i.LastWriteTime).TotalMinutes, 0)
    } else {
        # Eine geloeschte Datei hat keine mtime: Ersatzwahrheit ist der ELTERNORDNER
        # (Windows schreibt beim Loeschen die Ordnerzeit fort).
        $ord = Split-Path $voll -Parent
        $art = 'GELOESCHT'
        $alter = if (Test-Path $ord) {
            [math]::Round(($jetzt - (Get-Item $ord).LastWriteTime).TotalMinutes, 0)
        } else { '?' }
    }
    '{0,5} min  {1,-9} {2}  {3}' -f $alter, $art, $zeile.Substring(0, 2), $pfad
} | Sort-Object
