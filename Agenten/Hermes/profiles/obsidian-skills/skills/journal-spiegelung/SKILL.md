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
Vor jedem Schritt das Laufwerk prüfen, nicht den Pfad raten:
`powershell -NoProfile -Command "Get-CimInstance Win32_LogicalDisk | Where-Object {$_.DeviceID -eq 'Q:'}"`
(oder `ls /q/`). Kein Eintrag → SSD anstecken und warten, bevor
weitergemacht wird. Ein nicht gemountetes Ziel führt zu stummen Fehlern.
Q: trägt das Label `musik_lib` (SanDisk, exFAT); der Buchstabe hängt am
Anstecken, ohne Eintrag in der Laufwerksliste ist die Platte einfach weg.

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

### 5. Verifikation (byte-genau, nicht „Datei ist da")

```
cd "$HERMES_HOME/../.." && Agenten/Handel/scanner/.venv/Scripts/python.exe Agenten/Handel/spiegelstand.py
```

Durch das `terminal`-Tool aufrufen. **Hermes startet in `Agenten/Hermes`, alle Pfade hier sind
relativ zur BrainFiles-Wurzel** — deshalb der `cd` davor (`$HERMES_HOME` ist in jeder Sitzung
gesetzt). Das Modul geht alle `*/wachen.json` unter
`Agenten/Handel` durch und zeigt je Spur: Ziel, Kopiestand (byte-genau, wie
`cmp`), Journalzeilen, Alter des Herzschlags und den Vermerk
`journal_zweitziel_ok`. Rueckgabecode 0 = jede Spur im Dauerlauf byte-gleich,
1 = mindestens eine Abweichung. Es schreibt nichts; die Spurliste kommt aus
`dauerlauf.SPUREN`, per `ast` gelesen (kein Import der halben Handelsumgebung).
Denselben Aufruf liefert der Tagesbericht als Zeile (`spiegelstand.kurz()`),
und die Systempruefung fuehrt ihn als Block 11 taeglich um 07:00.

Einzeln nachsehen:

```
cmp <spur>/handelsjournal.csv Q:/Handel_Journal/<spur>/handelsjournal.csv
```

Die Kopie traegt die **Quell-mtime** (`copy2` erhaelt die Metadaten) — das
Alter der Kopie beweist also nichts; verglichen wird der Inhalt.

Der Ausrollweg über mehrere Spuren (Reihenfolge, Nachweise, Commits, die
Falle mit den Testzyklen) steht im Skill `handel-spuren`:
`references/spur-weite-aenderung.md`.

**Taeglich ohne Zutun:** dieselbe Pruefung laeuft als Block 11 der
Systempruefung (`Agenten/Routinen/systempruefung.ps1`, taeglich 07:00) und
meldet eine Abweichung in den Bericht; Block 12 prueft daneben, ob der
Dauerlauf laeuft und sein letzter Zyklus nicht aelter als 45 min ist. Im
Abendbericht steht der Stand als eigene Zeile.

## Stand (13.09.2026) — alle Spuren spiegeln

`spiegele_journal` und `vermerke_spiegelung` stehen in
`Handel/scanner/wachen_pruefung.py`. Jede Spur im Dauerlauf hat ein eigenes
Ziel und ruft die Kopie nach jedem Zyklus auf:

| Spur | Skript | Ziel |
|---|---|---|
| scanner | `handeln.py` | `Q:\Handel_Journal` (Wurzel) |
| xperp | `handeln.py` | `Q:\Handel_Journal\xperp` |
| nautilus | `handeln.py` (eigenes venv) | `Q:\Handel_Journal\nautilus` |
| swap | `handeln.py` | `Q:\Handel_Journal\swap` |
| orbk | `handeln.py` | `Q:\Handel_Journal\orbk` |
| omniquant | `handeln.py` | `Q:\Handel_Journal\omniquant` |
| spiegel | `spiegel.py` | `Q:\Handel_Journal\spiegel` |
| kraken | `handeln.py` | `Q:\Handel_Journal\kraken` |

Kopiert wird in **allen** Zyklenpfaden, auch im Notausstieg (Kill-Switch,
alter Herzschlag) — gerade der gehört ausser Haus. Reihenfolge im Zyklus:
**erst** Herzschlag und Journal schreiben, **dann** kopieren.

Zwei Fallen:

- **`journal_zweitziel` im wachen.json beweist nichts.** Es ist die Absicht;
  erst der Aufruf im Zyklus ist die Kopie (bis 13.09.2026 hatten swap, orbk,
  omniquant und spiegel das Ziel bzw. den Aufruf nicht).
- **Ziel nie auf den Ordner einer anderen Spur zeigen lassen.** swap stand auf
  `Q:\Handel_Journal\xperp` — solange niemand kopierte, harmlos; mit Aufruf
  hätte es die xperp-Kopie überschrieben (gleiche Dateinamen).

## Kopie aus einem eigenen venv (Muster: nautilus)

Läuft eine Spur in einem eigenen venv (`nautilus/.venv`), wird
`scanner/wachen_pruefung.py` per `importlib.util.spec_from_file_location`
geladen — **nicht** über einen zusätzlichen `sys.path`-Eintrag für
`scanner/`: dort liegen `okx.py` und `handeln.py`, die im fremden venv Namen
verdecken können. Die Datei braucht nur die Standardbibliothek.

Reihenfolge im Zyklus: **erst** Herzschlag und Journal schreiben, **dann**
kopieren. Ein hängender USB-Wandler darf den Zyklus verzögern, aber nicht den
Herzschlag verschlucken. Ein fehlendes Ziel ist kein Fehler des Zyklus
(Rückgabecode bleibt 0) — dafür muss der Ausfall sichtbar sein: Ergebnis in
den Zustand schreiben (`vermerke_spiegelung`, Felder `journal_zweitziel`,
`journal_zweitziel_ok`, `journal_zweitziel_info`, Schreiben nur bei Änderung)
und in `--wachen`/`--status` anzeigen. Ohne diesen Vermerk verschwindet eine
ausgefallene Kopie lautlos, weil der Dauerlauf bei Rückgabe 0 nur "ok"
protokolliert.

Gibt `vermerke_spiegelung` True zurück (Stand hat gewechselt), wird `ZUSTAND`
einmal **nachgezogen** — sonst läge auf Q: genau in diesem Zyklus ein älterer
Zustand als lokal, und die `cmp`-Prüfung meldete eine Abweichung.

Eine **Vorschau darf den Zustand nicht schreiben**: der Dauerlauf fragt jede
Spur zusätzlich mit `--vorschau` ab (`nur_fenster_fehlt`), ein schreibender
Vorschau-Lauf setzt damit einen frischen Herzschlag und lässt die Q:-Kopie
älter aussehen als den eigenen Zustand (swap und xperp bis 13.09.2026).

## Pitfalls
- **Einfacher Backslash vor einem Buchstaben im JSON-Pfad ist ein Escape.**
  `"journal_zweitziel": "Q:\\Handel_Journal\fib_retrace"` wird von
  `json.load` als `Q:\Handel_Journal\x0cib_retrace` (Formfeed 0x0C vor
  'ib_retrace') geparst — das Ziel ist unerreichbar, die Spur spiegelt still
  nie, und spiegelstand meldet dauerhaft "Ordner nicht erreichbar", obwohl
  der Ordner existiert (11.10.2026: fib_retrace). Bei JEDEM neuen Ziel nach
  dem Setzen gegenpruefen:
  `python -c "import json,os; z=json.load(open('wachen.json',encoding='utf-8'))['journal_zweitziel']; print(repr(z), os.path.isdir(z))"`
  — `repr()` zeigt ein Formfeed als `\x0c`, ein korrekter Pfad als `\\`.
- **Testzyklen spiegeln mit.** Faehrt ein Test den vollen `lauf()` und patcht
  nur `ZUSTAND`/`JOURNAL` auf Temp-Pfade, kopiert die Spiegelung die
  **Temp-Datei an das echte Ziel** — im Zielordner liegt danach ein
  200-Byte-Teststand statt der echten Kopie (und im echten Zustand kann der
  Test-Vermerk stehen). Das Wachen-Fixture im Test muss deshalb ein
  **Temp-Ziel** tragen oder `None`; nie die echte `wachen.json` als Fixture.
- **G: nicht verwenden** — gleiches Gehaeuse wie lokale Platte, bei Hardware-Defekt sind Quelle und Ziel gleichzeitig weg.
- **CSV-Formate spur-spezifisch** — scanner/ (`zeit,modus,aktion,inst,preis,usd,...`) und xperp/ (`zeit,modus,aktion,inst,seite,familie,kontrakte,...`) haben unterschiedliche Spalten, daher separate Zielordner.
- **journal_zweitziel == null sperrt Live** — aktivierter Sicherheitsmechanismus.
- **Keine absoluten Pfade in Skripten** — brechen bei Umzug.
