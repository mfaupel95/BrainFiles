---
name: posteingang
description: Sortiert neue Dateien aus Archiv/Posteingang/ in die Archivstruktur ein und indexiert neu. Benutzen, wenn Max um Aufräumen des Posteingangs bittet, wenn dort Dateien liegen, oder bei Formulierungen wie "sortier das ein", "räum auf", "was liegt im Posteingang".
---

# Posteingang einsortieren

Max zieht neue Dateien einfach nach `Archiv/Posteingang/`. Dieser Skill bringt
sie an ihren Platz.

## Ablauf

**1. Schauen, was da ist** — nicht blind sortieren:

```powershell
$pe = if ($env:ARCHIV_ROOT) { $env:ARCHIV_ROOT } else { 'Archiv' }
Get-ChildItem (Join-Path $pe 'Posteingang') -Recurse -File | Measure-Object | Select-Object Count
```

Der Datenzweig liegt seit dem 07.09.2026 auf `O:\Archiv` (`ARCHIV_ROOT`); der
Werkzeugordner `Archiv\ArchivSuche\` bleibt auf `C:`. Ist der Ordner leer, hier
aufhören und das sagen.

**2. Bei mehr als ein paar Dutzend Dateien erst ein Testlauf:**

```powershell
Archiv\ArchivSuche\.venv\Scripts\python.exe Archiv\ArchivSuche\sort_inbox.py --dry-run
```

**3. Sortieren:**

```powershell
Archiv\ArchivSuche\.venv\Scripts\python.exe Archiv\ArchivSuche\sort_inbox.py
```

Die Ausgabe ist standardmäßig kurz (nur Zahlen je Zielordner). `--details` nur,
wenn wirklich geklärt werden muss, *welche* Datei wohin ging.

**4. Rest von Hand.** Was liegen bleibt, konnte das Skript nicht sicher zuordnen —
das ist kein Fehler. Diese Dateien einzeln ansehen (Inhalt lesen, nicht nur den
Namen) und gezielt in den passenden Unterordner von `%ARCHIV_ROOT%\Dokumente\`
bzw. `\Bilder\`, `\Videos\`, `\Musik\` verschieben (also unter `O:\Archiv\`).
**Nicht raten.**

**5. Index aktualisieren**, falls `sort_inbox.py` das nicht schon selbst getan hat:

```powershell
Archiv\ArchivSuche\.venv\Scripts\python.exe Archiv\ArchivSuche\index.py
```

## Regeln

- **Sensible Dateien nie automatisch verschieben** — Passwort-Exporte,
  Zertifikate (`.pfx`), private Schlüssel. Melden und liegen lassen.
- Ganze Ordner werden samt Unterstruktur übernommen, wenn der Name die Kategorie
  verrät (`Studium/` → `Dokumente/Privat/Studium`). Die Regeln stehen in
  `ORDNER_REGELN` in `sort_inbox.py` und lassen sich dort erweitern.
- Nach dem Lauf einmal gegenprüfen, dass der Posteingang tatsächlich leerer ist —
  Erfolgsmeldungen nicht ungeprüft glauben.
