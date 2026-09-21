# Junges Schattenbuch auswerten + Watchdog bis Mindest-Stichprobe

Vollstaendiger Ablauf fuer die Folgefrage, die nach dem Anlegen eines
Schattenbuchs (spiegel_knapp/spiegel_weit o.ae.) kommt: "alle N Ausstiege
auswerten" — typischerweise lange bevor die Mindestbesetzung erreicht ist.

## Schritt 1 — Erst Ausstiege zaehlen, NICHT auswerten

Bevor irgendeine Auswertung laeuft, die Ausstiege je Arm zaehlen. Bloss alle
Zeilen mit `aktion == "schliessen"` im Arm-Journal zaehlen. Vorgehen ueber
`terminal` und ein kleines Python:

```python
import csv
for buch in ("handelsjournal.knapp.csv", "handelsjournal.weit.csv"):
    z = list(csv.DictReader(open(buch, encoding="utf-8")))
    print(buch, "Ausstiege:", sum(1 for r in z if r.get("aktion") == "schliessen"))
```

## Schritt 2 — Mindestbesetzungs-Gate (30 je Arm)

Unterschreitet EIN Arm 30 Ausstiege, lautet das Verdikt **"nicht entschieden"**
(Wortschatz aus handel-spur-studie). Auswerten darf man trotzdem — aber als
Zwischenstand, NIE als Befund.

- Die vorhandenen Ausstiege anzeigen (Einstieg/Ausstieg/Rendite/Grund/Zeit),
  aber ausdruecklich kennzeichnen, dass sie die Schwele nicht erreichen.
- **n=1-Token-Falle:** 2-3 Ausstiege, die alle denselben Token betreffen und
  alle mit `grund=stop` enden, sind EIN Datenpunkt, keine drei. Keine Aussage
  zur Ausstiegsgeometrie daraus ziehen.
- **Vergleichsbasis im selben Fenster pruefen:** das Hauptbuch kann im
  Aktivierungsfenster des Schattenbuchs 0 Ausstiege haben — dann ist auch der
  A/B-Vergleich nicht moeglich. Das explizit sagen statt eine Zahl zu deuten.
- Pfade: Hauptbuch `handelsjournal.csv`; Arme haengen das Suffix vor die Endung
  (`handelsjournal.knapp.csv`, `handelsjournal.weit.csv`).

## Schritt 3 — Watchdog-Cron bis Mindest-Stichprobe

Wenn die Auswertung verfrueht war, KEINE Rueckfrage stellen — die Arme
weiterlaufen lassen und einen Cron aufsetzen, der meldet, sobald die Schwele
erreicht ist. Watchdog-Muster: `no_agent=True`, Skript zaehlt, **leere Stdout =
nichts senden**, Nicht-Null-Exit oder Timeout sendet Fehler.

Fertiges, parametrisierbares Zaehlskript liegt im Skill unter
`scripts/schattenbuch-ausstiege-zaehler.py` (nur Standardbibliothek). Erst
nach `Agenten/Hermes/scripts/` (oder direkt per `--ordner` ansprechbar)
kopieren bzw. aufrufen. Aufrufbeispiele:

```
python schattenbuch-ausstiege-zaehler.py --ordner Agenten/Handel/spiegel   # Default knapp/weit
python schattenbuch-ausstiege-zaehler.py --ordner <spur> --arme A B C --mindest 20 --schritt 5
```

Cron-Definition (ueber `cronjob`, Schema wie im Arbeitslauf 2026-09-19
angewendet):

```
- schedule: every 30m
- name: spiegel-arm-ausstiege
- no_agent: true
- deliver: all            # Telegram etc., zum Feuerzeitpunkt aufgeloest
- script: <skript>.py     # unter Agenten/Hermes/scripts/
```

Skript-Verhalten (im Skill-Skript bereits umgesetzt):

```python
MINDEST = 30    # siehe Gate, per --mindest
SCHRITT = 10    # erst bei 30 melden, dann 40, 50, ...  (keine Dauerwiederholung)
if min(n) < MINDEST: return          # still
schwelle = (min(n) // SCHRITT) * SCHRITT
if schwelle < MINDEST: return
print("Meldung mit den Arm-Zaehlern und dem Auswertungsaufruf")
```

- **Schwellen-escalation, nicht jeden Tick melden:** die Meldung nur beim
  Ueberschreiten eines Vielfachen von SCHRITT aussenden (30, 40, 50, ...),
  sonst spammt der Cron dieselbe Zahl halbstuendlich.
- Verifikation VOR dem Anlegen, laut Tests 2026-09-19: (a) `python <skript>
  --ordner <spur>` bei <MINDEST muss leerer Stdout + Exit 0 zurueckgeben
  (nichts senden); (b) mit `--mindest 3 --schritt 1` und zwei Tempjournalen a
  3 Eintraegen muss die Meldung erscheinen.
- Abgrenzung zu `dauerprozess-bewachen`: dort geht es um laufende Prozesse;
  hier um einen stumm wachsenden CSV-Zaehler, der erst an der Schwele meldet.

## Abgrenzung

- Verhaelt sich wie ein Schatten-Papiertest: messen, Gate pruefen, ehrlich
  "nicht entschieden" sagen, dann Waechter bis zur Schwele — kein erfundener
  Befund aus jungem Buch.
- Die Schwele (30 je Arm, Messzeitraum bis dahin) steht bereits im
  Haupt-SKILL `handel-spur-optimierung`; dieser Ablauf fuegt die Auswertungs-
  und Waechtermechanik hinzu.
