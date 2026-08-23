---
name: posteingang
description: Sortiert neue Dateien aus Claude/Posteingang/ in die Archivstruktur ein und indexiert neu. Benutzen, wenn Max um Aufräumen des Posteingangs bittet, wenn dort Dateien liegen, oder bei Formulierungen wie "sortier das ein", "räum auf", "was liegt im Posteingang".
---

# Posteingang einsortieren

Max zieht neue Dateien einfach nach `Claude/Posteingang/`. Dieser Skill bringt
sie an ihren Platz.

## Ablauf

**1. Schauen, was da ist** — nicht blind sortieren:

```powershell
Get-ChildItem Claude\Posteingang -Recurse -File | Measure-Object | Select-Object Count
```

Ist der Ordner leer, hier aufhören und das sagen.

**2. Bei mehr als ein paar Dutzend Dateien erst ein Testlauf:**

```powershell
Claude\ArchivSuche\.venv\Scripts\python.exe Claude\ArchivSuche\sort_inbox.py --dry-run
```

**3. Sortieren:**

```powershell
Claude\ArchivSuche\.venv\Scripts\python.exe Claude\ArchivSuche\sort_inbox.py
```

Die Ausgabe ist standardmäßig kurz (nur Zahlen je Zielordner). `--details` nur,
wenn wirklich geklärt werden muss, *welche* Datei wohin ging.

**4. Rest von Hand.** Was liegen bleibt, konnte das Skript nicht sicher zuordnen —
das ist kein Fehler. Diese Dateien einzeln ansehen (Inhalt lesen, nicht nur den
Namen) und gezielt in den passenden Unterordner von `Claude/Dokumente/` bzw.
`Bilder/`, `Videos/`, `Musik/` verschieben. **Nicht raten.**

**5. Index aktualisieren**, falls `sort_inbox.py` das nicht schon selbst getan hat:

```powershell
Claude\ArchivSuche\.venv\Scripts\python.exe Claude\ArchivSuche\index.py
```

## Regeln

- **Sensible Dateien nie automatisch verschieben** — Passwort-Exporte,
  Zertifikate (`.pfx`), private Schlüssel. Melden und liegen lassen.
- Ganze Ordner werden samt Unterstruktur übernommen, wenn der Name die Kategorie
  verrät (`Studium/` → `Dokumente/Privat/Studium`). Die Regeln stehen in
  `ORDNER_REGELN` in `sort_inbox.py` und lassen sich dort erweitern.
- Nach dem Lauf einmal gegenprüfen, dass der Posteingang tatsächlich leerer ist —
  Erfolgsmeldungen nicht ungeprüft glauben.
