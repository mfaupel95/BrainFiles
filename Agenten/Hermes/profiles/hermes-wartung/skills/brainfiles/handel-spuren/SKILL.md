---
name: handel-spuren
description: "Handelsspuren auf Wachen, Spiegel und Freigabe prüfen."
version: 0.1.0
author: Maximilian Faupel (maximilian-faupel), Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [handel, spuren, wachen, papier, optimierung, backtest]
    related_skills: [aufgaben-verfolgen, systemdiagnose]
---

# Handelsspuren — Prüfung und Optimierung

Eine Handelsspur wird durch `wachen.json` (Grenzen), `handeln.py` (Logik),
Journal (Buch) und gegebenenfalls `dauerlauf.py`-Eintrag (Start) definiert.
Die zentrale Prüfungsstelle ist `spiegelstand.py` (Bedingung 4: Journal-Ziel).

## Wann verwendet

- **„Prüfe die Handelsspuren"** oder **„Was läuft in Handel?"** → Übersicht
  über alle aktiven Spuren mit Wachen-Status.
- **„Offene Tasks in Handel"** → TASKS.md + FREMD-Phasen.json im Handel-
  Kontext lesen; Spuren mit offenen Task-Hinweisen identifizieren.
- **„T-413 / Spiegelung / journal_zweitziel fehlt"** → direkt dieses Skill
  nutzen: spiegelstand.py laufen, Feld reparieren.
- **„Wachen eines Arms fehlen"** → prüfen, ob die Spur Arm-Wachen neu
  generiert (handeln.py-Schreibmuster) → Änderung an das Haupt-wachen.json.
- **„Optimiere die Handelsspuren"** → Wachen-Checkliste durchgehen, nur
  Punkte ohne Max-Entscheidung angehen.

## Wann nicht

- Einzelne Spur reparieren, wenn der Code-Fehler bekannt ist → direkt die
  Spur-Datei und Tests anschauen, nicht diesen Umbrella laden.
- Neue Spur bauen → `freigabe.py` und die bestehenden Wachen als Vorbild
  nehmen, nicht von Null beginnen.

## Vorbereitung — immer zuerst

**Schutzregeln lesen.** Vor jedem schreibenden Zugriff auf `Agenten/Handel/`:

```
read_file(path="C:/Users/faupe/Documents/BrainFiles/MaxHirn/Wissen/Schutzregeln.md", limit=30)
```

`Agenten/Handel/` ist nicht in der geschützten Liste — Schreibzugriffe sind
erlaubt. Backups (`.bak-YYYYMMDD`) vor jeder Änderung erstellen.

## Übersicht beschaffen

Die aktiven Spuren mit ihren Wachen in einem Überblick. Priorität:
erst die Spuren mit `handel_erlaubt: true`, dann die mit offenen Tasks,
dann der Rest nach Bedarf.

**Achtung:** Nicht alle `wachen.json`-Dateien gleichzeitig lesen — die
Datenmenge sprengt den Kontext (>100 KB-Budget). Stattdessen gezielt die
relevanten Spuren einzeln lesen.

## Wachen-Status schnell erfassen

Für jede Spur prüfen (Reihenfolge):

1. **`handel_erlaubt`** — `true` = Live-Pfad vorhanden; `false` = nur Papier.
2. **`journal_zweitziel`** — Bedingung 4. Muss ein Q:-Pfad sein
   (`Q:\\Handel_Journal\\<spur>`). Fehlt es → `spiegelstand.py` meldet
   "kein Ziel".
3. **`herzschlag_max_minuten`** — 180 für Papier, 45 für live.
   Fehlt komplett → Spur läuft nie.
4. **`freigabe.erfuellt`** — bei live-Spuren: `true` nur wenn Max den Haken
   gesetzt hat; nicht vom Code berechnet.
5. **`boerse` / `instrumente`** — stimmt die Börse mit den Keys überein?

## Spiegelstand prüfen

```
terminal(command="python C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/spiegelstand.py --handel C:/Users/faupe/Documents/BrainFiles/Agenten/Handel --stunden 30", timeout=120)
```

**Ausgabe lesen:**
- `stand: gleich` → Bedingung 4 erfüllt
- `stand: kein Ziel` → `journal_zweitziel` fehlt oder ist leer
- `stand: ABWEICHUNG` → Kopie hinterher
- `Ziel fehlt` → Ordner existiert nicht auf Q: (SSD nicht angesteckt oder Zielordner fehlt)

**Eine einzelne ABWEICHUNG kann ein Transient sein.** Der Dauerlauf kopiert
im Zyklus; läuft `spiegelstand` mitten in der Kopie, meldet es einen
Unterschied, der beim nächsten Lauf weg ist (belegt: nautilus_kraken meldete
`[zustand.json]`, byte-genauer Vergleich war identisch, nächster Lauf `gleich`).
Vor „Kopie hinkt hinterher" die betroffene Datei byte-genau vergleichen
(`cmp <quelle> <ziel>` / `md5sum`) oder `spiegelstand` erneut laufen lassen —
erst ein bestätigter Unterschied ist ein Befund.

Spuren nicht in `dauerlauf.SPUREN` werden als `[nicht in dauerlauf.SPUREN]`
markiert — mitgeprüft, aber nicht in die Anzahl mitgezählt.

## Wachen-Felder reparieren

Wenn `spiegelstand.py` eine Spur als "kein Ziel" meldet:

1. **Schutzregeln prüfen** (siehe Vorbereitung)
2. **`.bak-YYYYMMDD` erstellen** (vor der Änderung)
3. **Feld mit patch hinzufügen:**
   ```python
   patch(
       path="<wachen.json>",
       old_string="<letzter Eintrag vor Schlussklammer>",
       new_string="<letzter Eintrag>,\n  \"journal_zweitziel\": \"Q:\\\\Handel_Journal\\\\<spur>\""
   )
   ```
   **Escape:** Im JSON-String werden Backslashes verdoppelt.
   Das `patch`-Tool erhält den String als Python-Literal — `\\` in der
   new_string entspricht einem einzelnen `\` im JSON.
4. **Verifizieren** mit `json.load`:
   ```python
   import json
   with open("<pfad>", encoding="utf-8") as f:
       w = json.load(f)
   print(repr(w.get("journal_zweitziel")))
   ```
   Korrekt: `'Q:\\Handel_Journal\\<spur>'` (Python-Repr mit einzelnen
   Backslashes).

## Das handeln.py-Überschreibungs-Fallen

Manche Spuren erzeugen ihre Arm-Wachen-Dateien neu, jedes Mal wenn sie
laufen. Konkret: `llm_stunde/handeln.py` (Zeile 121-130) liest das
**Haupt-`wachen.json`** und schreibt für jeden Arm ein neues
`wachen.json` in `laeufe/<variante>-<arm>/`.

**Folge:** Jede manuelle Änderung an einem Arm-`wachen.json` wird beim
nexten Zyklus überschrieben. Die Änderung gehört **entweder** in das
Haupt-`wachen.json` (wird vererbt) **oder** in die Generierungsfunktion —
nicht nur in den Arm.

**Prüfen, ob eine Spur dieses Muster hat:**

```python
from hermes_tools import search_files
matches = search_files(
    pattern=r"wachen\.json.*write_text",
    path="C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/<spur>/handeln.py",
    target="content"
)
```

Bei Treffer: Änderung an das Haupt-`wachen.json` schreiben.

## Q: für Journal-Ziele

`journal_zweitziel`-Pfade zeigen auf `Q:\\Handel_Journal\\<spur>`. `Q:` ist
**keine Junction, sondern eine echte tragbare SSD** (SanDisk, exFAT, Disk 3,
Volume-Label `musik_lib`) — dieselbe Platte, auf die `sichern-ausser-haus.ps1`
die Ausser-Haus-Kopie schreibt. Die Spiegelungsfunktion kopiert Journal,
Zustand und Ablehnungen nach diesem Ziel.

**Wenn das Ziel fehlt** (`spiegelstand.py` meldet "Ziel fehlt"):
- Zuerst prüfen, ob Q: überhaupt angesteckt ist (`ls Q:/`), dann ob der
  Zielordner existiert (`ls Q:/Handel_Journal/<spur>`).
- Fehlt der Ordner, ist er nicht „zerstört" — er wurde nie angelegt oder
  die SSD ist nicht da. Kein Administrator-Eingriff nötig.
- **Nie** den Q:-Pfad in der Wachen ändern, solange Q: funktioniert.

## Backtest-Kohärenz

Spuren mit `wachen.json` in `daten/backtest/<spur>/` gelten nur für den
Backtest — kein Live-Gegenstück, `handel_erlaubt: false`, kein Orderweg.
Sie werden von `spiegelstand.py` als `ausserhalb` markiert, aber mitgeprüft.

Papierbuch (`handel_erlaubt: false`, journal_zweitziel auf Q:) ist ein
laufendes Buch mit echten Kerzen. Backtest-Buch (`daten/backtest/`) ist
statisch. Beide dürfen nicht verwechselt werden.

## Checkliste: Wachen-Status je Spur

| Feld | Erwarteter Wert | Auffälligkeit |
|---|---|---|
| `handel_erlaubt` | `true` / `false` | `true` ohne freigabe.erfuellt = Max-Freigabe |
| `journal_zweitziel` | `Q:\\Handel_Journal\\<spur>` | Fehlt → sofort melden |
| `herzschlag_max_minuten` | 180 (papier) / 45 (live) | Fehlt → Spur schreit |
| `freigabe.erfuellt` | `true` nur bei Max | `false` bei live = korrekter Standby |
| `boerse` | passt zu Keys + Guthaben | falsch → Orders scheitern |

## Was ohne Max-Entscheidung nicht angefasst wird

- Stop-Weite, Risikowerte, Hebel: nur Max entscheidet. Stand anzeigen,
  nicht ändern.
- Live-Freigabe (`handel_erlaubt: true`): nur Max setzt `freigabe.erfuellt`.
- Neue Instrumente: nur nach Prüfung von Handelbarkeit und Guthaben.

## Pitfalls

- **Arm-Wachen überschreiben.** Spuren mit wachen.json-Schreiblogik in
  `handeln.py` (wie llm_stunde) erzeugen ihre Arm-Dateien jedes Mal neu.
  Änderungen an den Arm-Dateien werden beim nächsten Zyklus überschrieben.
  Änderung hingeschrieben an das Haupt-`wachen.json` (Vererbung) oder an
  die Generierungsfunktion — nie nur an den Arm.
- **Mehrere Arme, EIN Ziel = Überschreibung.** Eine Spur mit mehreren
  Armen (z. B. llm_stunde: 6 Straenge) erbt anfangs alle das Haupt-
  `journal_zweitziel`; im Zyklus überschreiben sich die Journale gegenseitig
  auf Q:. Jede Arm-Wachen braucht ihr EIGENES Ziel (Unterordner des
  Hauptziels, z. B. `Q:\\Handel_Journal\\llm_stunde\\ema1h-L`). Nach dem
  Generieren immer die Arm-Wachen lesen und prüfen, dass die Zielfelder
  verschieden sind.
- **Wachen-Wert ist instrument-spezifisch.** Ein Sizing-/Deckel-Wert, der
  für ein Instrument „korrigiert" wurde (z. B. `max_pro_trade_usd` passend
  zu einem SOL-Kontrakt), wird falsch, sobald die Spur auf ein anderes
  Instrument wechselt (z. B. BTC-Kontrakt ≈ 84.000 USD). `menge_fuer`
  rechnet `int(betrag // kurs)` = Nominal durch Kurs — ein Deckel, der
  unter dem Kontraktwert liegt, ergibt dauerhaft 0 Kontrakte („Einsatz
  kleiner als ein Kontrakt"). Vor einem Live-Versuch: Deckel gegen den
  AKTUELLEN Kontraktwert prüfen, nicht gegen den, für den der Vermerk
  geschrieben wurde.
- **Instrument-Mapping prüfen, bevor man es „fixt".** `spur_buch.venue_inst()`
  übersetzt das Buch-Instrument in die Börsen-Schreibweise (kraken_futures:
  `BTC-USDC` → `PF_XBTUSD`). Ein vermeintlicher Mapping-Bug ist oft gar
  keiner — der echte Blocker sitzt woanders (Sizing, Guthaben, Freigabe-
  fenster). Erst `venue_inst()` + `menge_fuer()` mit dem echten Instrument
  aufrufen, dann entscheiden.
- **Parallele Sitzung kann die Lösung schon committet haben.** Im geteilten
  Arbeitsbaum: vor dem Bauen eines Fixes `git status`/`git log` und die
  Testdatei prüfen — existieren Tests für das Feature, hat eine andere
  Sitzung es evtl. schon gelöst. Eigene redundante Patches zurücknehmen
  (Datei auf HEAD-Stand bringen), statt Doppel-Code zu committen.
- **JSON-Escape bei Backslashes.** `journal_zweitziel` enthält Windows-Pfade
  mit `\`. Im JSON-String verdoppelt: `Q:\\Handel_Journal\\llm_stunde`.
  Beim Patchen: `\\` in der new_string für die JSON-Darstellung.
- **alle Wachen auf einmal lesen.** Ergebnis sprengt Kontext, Aufruf bricht
  ab. Stattdessen: Spuren nacheinander, nach Priorität (live zuerst).
- **Backtest-Wachen als Live-Freigabe lesen.** `daten/backtest/*/wachen.json`
haben `handel_erlaubt: false` und keinen Orderweg — keine Live-Grenzen.
- **Q: als Junction ansehen.** Q: ist eine echte tragbare SSD (exFAT, Disk 3),
  keine Junction. "Ziel fehlt" heißt: SSD nicht angesteckt oder Zielordner
  fehlt — kein Administrator-Eingriff, kein Wachen-Pfad-Umbau.
- **Herzschlag-Feld-Namen.** Einige Wachen nutzen `herzschlag_max_minutes`,
  andere `herzschlag_max_minuten` (mit/ohne `n`). Beide existieren.
  Fehlt das Feld komplett, läuft die Spur nie.

## Verification

Nach einer Änderung:

1. `spiegelstand.py` erneut laufen → betroffene Spur zeigt jetzt
   `stand: gleich` (oder nicht mehr `kein Ziel`)
2. JSON-Inhalt des Feldes mit `json.load` prüfen → tatsächlich gelesener
   Wert entspricht dem erwarteten Pfad
3. `.bak`-Datei existiert und enthält den alten Stand

Laufender Dauerlauf muss nicht neu gestartet werden — die Spur liest
`wachen.json` bei jedem Zyklus neu.
