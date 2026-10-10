---
name: journal-spiegelung
description: "Bedingung 4: Journal auf externe SSD spiegeln."
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Handel, Journal, Bedingung-4, BrainFiles]
---

# Journal-Spiegelung (Bedingung 4)

## Wann
Eine Handels-Spur (scanner, xperp, orb) braucht Bedingung 4 oder den Spiegelungs-Pfad zu ändern.

## Prozedur

### 0. Externe SSD prüfen
Vor jedem Schritt: `ls /c/Users/faupe/Q:/` ausführen. Existiert nicht → SSD einstecken und warten, bevor weitergemacht wird. Ein nicht gemountetes Ziel führt zu stummen Fehlern.

### 1. Bestandsaufnahme
Alle Spuren unter `Agenten/Handel/<spur>/wachen.json` prüfen.
`journal_zweitziel` ist `None` → muss gesetzt werden.

**Nur Projekte mit wachen.json** (Spur 2, 3, 4) verwenden `journal_zweitziel` direkt.
Andere Projekte (Omnitrade/Rust, CryptoPredictions/ML, NautilusTrader/Live, OpenAlice) haben kein `wachen.json` und benötigen einen alternativen Spiegelungsmechanismus (Symlink, rsync, oder Kopie der Log-Dateien).

### 2. Externe SSD identifizieren
- Üblich: `Q:` (ExFAT, externes Laufwerk).
- **NIEMALS `G:`** — gleiches Gehäuse wie lokale Platte.

### 3. Zielordner anlegen
`<SSD>\Handel_Journal\<spur>` — jeder Spur einen eigenen Unterordner (unterschiedliche CSV-Formate).

Für Projekte ohne wachen.json: eigene Unterverzier anlegen, z.B.
`<SSD>\Handel_Journal\omnitrade\`, `<SSD>\Handel_Journal\cryptopredictions\`.

### 4. wachen.json aktualisieren
- `journal_zweitziel` auf den Pfad setzen.
- `_journal_zweitziel`-Kommentar aktualisieren: „Bedingung 4. Pfad fuer die Journal-Spiegelung nach jedem Zyklus. Nicht G: (gleiches Gehaeuse). null -> Live gesperrt."
- Commit.

### 5. Verifikation
```python
import wachen_pruefung as wp
ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
# ok == True, dann Dateien vergleichen
```

## Pitfalls
- **G: nicht verwenden** — gleiches Gehäuse wie lokale Platte, bei Hardware-Defekt sind Quelle und Ziel gleichzeitig weg.
- **CSV-Formate spur-spezifisch** — scanner/ (`zeit,modus,aktion,inst,preis,usd,...`) und xperp/ (`zeit,modus,aktion,inst,seite,familie,kontrakte,...`) haben unterschiedliche Spalten, daher separate Zielordner.
- **journal_zweitziel == null sperrt Live** — aktivierter Sicherheitsmechanismus.
- **Keine absoluten Pfade in Skripten** — brechen bei Umzug.
