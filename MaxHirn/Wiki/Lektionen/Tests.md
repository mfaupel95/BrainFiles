---
id: 20260921-tests
title: 'Lektionen — Tests'
tags: [lektion, tests]
created: 2026-09-21
updated: 2026-10-05
related: ['[[Handel/Lektionen]]', '[[Lektionen/Git-und-Textdateien]]']
summary: 'Tests, die echte Datenordner ODER den laufenden Betrieb anfassen; Modulwaechter und Trockenmodus als Gegenmittel; sys.path-Reihenfolge; Tests, die nichts pruefen.'
---

# Tests

## 1. Ein Test darf nie in einen echten Zielpfad schreiben

**Regel.** Jede Testklasse, die eine Funktion mit Journal-/Zustandsaufruf direkt prueft,
setzt `SCHREIBEN = False`, patcht Wachen- und Journalpfade auf einen Tempordner **und**
baut einen Modulwaechter: `setUpModule` merkt Dateiliste und Groessen des echten
Spurordners, `tearDownModule` vergleicht.

**Warum.** Drei belegte Faelle:

- Die Suiten von `spiegel` und `omniquant` behielten das ECHTE `journal_zweitziel`
  (`Q:\Handel_Journal\<spur>`) — jeder Testlauf ueberschrieb die Ausser-Haus-Kopie mit
  Tempdaten, Zustand 13.816 → 222 Byte, alle Tests gruen. Bedingung 4 still verletzt.
- `moondev_funding`-Tests buchten 16 Zeilen ins echte Journal.
- Nach jedem Lauf der Spurentests meldet `spiegelstand.py` kurzzeitig Abweichungen
  (`scanner/ablehnungen.csv`, `orbk/zustand.json`) — die Tests laufen in die echten
  Ordner, Q: zieht erst im naechsten Zyklus nach. **Das heilt von selbst**; bleibt eine
  Abweichung ueber zwei Zyklen, ist es ein echter Befund.

**Gegenprobe nach jeder Suite:** `Agenten/Handel/spiegelstand.py` muss byte-gleich melden.

## 2. `sys.path` — Reihenfolge entscheidet, welches Modul geladen wird

**Regel.** Die eigene Spur ZULETZT einfuegen und absichern:

```python
sys.path.insert(0, SPUR)
...
assert h.__file__.startswith(str(SPUR))
```

**Warum.** `for p in (SPUR, HANDEL, scanner): sys.path.insert(0, p)` stellt `scanner`
nach vorne — der Test laedt dann `scanner/handeln.py` statt der eigenen Spur und ist
gruen, ohne die eigene Spur zu beruehren. Gleichnamige Module gibt es mehrfach
(`gitter/grid.py` neben `Handel/grid.py`, `handeln.py` in jeder Spur).

**Testaufruf-Falle.** Spurtestsuiten nur aus `<spur>/tests` heraus starten
(`python -m unittest test_<spur>`); aus dem Spurenordner scheitert `discover` mit
„Start directory is not importable", und `-m unittest tests.test_x` zieht das falsche
`handeln.py`.

## 3. Ein Test, der nichts prueft, ist schlimmer als keiner

**Belegter Fall (16.09.2026).** `bewertung.bewerten(kerzen, richtung="long", gewichte=None)`
— ein Test uebergab sein Gewichte-Dict POSITIONELL; es landete in `richtung`, rutschte
still in den `long`-Zweig, und `66.7 == 66.7` war gruen. Seitdem wirft `bewerten()` bei
unbekannter Richtung `ValueError`.

**Regel.** Optionale Argumente als Keyword uebergeben und in der Funktion pruefen, ob der
Wert ueberhaupt der erwartete Typ ist. Ein Test an einem festen Beispielwert darf nicht
an einem festen Datum haengen — `test_risikovorfilter` hatte ein hartes `JETZT =
2026-09-17`; als der Vorfilter mit echtem `jetzt` rechnete, war das 12-h-Fenster leer.

## 4. Tests, die an Namen statt an Regeln haengen, brechen beim Aufraeumen

**Belegter Fall.** Der Bus-Test `test_skillkatalog` prueft `apple-notes`; als die
Skill-Bibliothek entdoppelt wurde, fiel er. Richtig ist die Pruefung der REGEL
(„jeder nicht ladbare Eintrag fehlt in der Faehigkeitsliste und steht in der
Schlusszeile").

## 5. Ein Nachbar verdeckt das eigene Modul (22.09.2026)

`live_kraken.py` laedt die Haus-Kraken-Spur ueber den PFAD und legt dabei
`Agenten/Handel/kraken` auf `sys.path`. Wird es vor der eigenen Suite importiert
(alphabetische Reihenfolge beim `discover`), gewinnt `kraken/handeln.py` und die
Suite prueft still das FALSCHE Modul - sie war gruen, weil die Zusicherung
`h.__file__.startswith(SPUR)` den Fall abfaengt.

Zwei Fallen in der Reparatur:

1. `if p not in sys.path` ist hier falsch: die Nachbarspur hat die Pfade schon
   eingetragen, nur weiter hinten - der eigene Ordner muss trotzdem nach vorne
   (`sys.path.insert(0, p)` ohne Bedingung).
2. Fremde Spurordner vorher entfernen und `sys.modules.pop("handeln")`, sonst
   liegt das bereits geladene fremde Modul im Cache.

**Merksatz:** Eine Suite, die ihr eigenes Modul importiert, muss VOR dem Import
aufraeumen und danach pruefen, WAS sie geladen hat (`__file__`).

## 6. Ein Test darf auch den LAUFENDEN Betrieb nicht anfassen (23.09.2026)

**Belegter Fall.** `Agenten/Handel/tests/test_moondev_dauerlauf.py` baute den ECHTEN Treiber und
rief `zyklus()`. Ein Lauf hat damit:

- die **lebenden** Moon-Dev-Agenten als Waisen beendet (8 PIDs — der Treiber startete sie 60 s
  spaeter neu, der Betrieb merkte es nur daran),
- die **Logdatei des Laufs** gedreht (`moondev_sniper.log`, 160,6 MB → `.log.1`),
- seine Startzeilen **ins echte Treiberlog** geschrieben,
- vier eigene Agenten als **Waisen** stehen gelassen.

**Regel.** Fuer jede Suite, die Betriebscode startet, gibt es einen **Trockenmodus** — ein
Konstruktorargument, das die drei Eingriffe abschaltet: kein Aufraeumen fremder Prozesse, Logs in
einen `tempfile.mkdtemp()`-Ordner, nichts ins echte Log (`MoonDevDauerlauf(trocken=True)`).
Der Test prueft den Vertrag selbst (`TrockenlaufSchutzTest`): Treiberlog unveraendert, Logbasis im
Tempordner, `aufraeumen()` wird nicht gerufen.

**Zweite Falle: die Wurzel ist frueher tot als der Nachfahre.** `_stoppe()` endet, wenn die Wurzel
schon `poll() is not None` liefert — der venv-Launcher ist dann weg, waehrend der Interpreter
weiterlaeuft. `taskkill /T` erreicht ueber eine tote Wurzel nichts mehr. Der Test sammelt deshalb
**vor** dem Beenden die Nachfahren aus der Prozessliste (Parentkette, transitive Huelle) und beendet
sie einzeln. Nachweis: `pythonw.exe`-Prozesse danach **10** (Treiberpaar + 8 Agenten).

## 7. Laufender Stand

Agenten/Handel, `discover -s tests -t tests`: **891 Tests, 0 rote** (29.09.2026,
735 s; erstmals seit Wochen ohne roten Test) — die vier roten vom 29.09. waren alle
**kaputte Pruefungen, keine Codeprobleme**:

| Test | Fehler | Ursache |
|---|---|---|
| `test_handelszentrale_bindung.NamensfalleTest` | Modulname doppelt | `historie` lag zweimal im Suchraum → `historie_binance.py` |
| `test_omniquant_fassung.LadeBerichtTest` (2) | Uhrzeitbombe | festes Datum im Fixture, „Alter < 26 h" kippte nach 26 h |
| `test_replay.FensterTest` | Laufzeitvergleich | 0,97 / 0,93 auf zwei Durchgaengen — misst Maschinenlast, nicht die Regel |
| `test_moondev_dauerlauf.StartStoppTest` | Agent tot nach 6 s | Rate-Limit des Datenanbieters, kein Treiberfehler (s. § 8) |

Vor jeder Aussage „durch die Aenderung rot" per A/B gegen `HEAD` gegenpruefen.

## 8. Den Start pruefen, nicht das Ueberleben

Ein Test, der von einem **fremden Dienst** abhaengt, meldet dessen Ausfaelle als
Codeproblem. `test_moondev_dauerlauf` verlangte „der Agent laeuft nach 6 Sekunden
noch"; in der vollen Suite (drei Dauerlauf-Stufen parallel) fiel er um, einzeln
lief er gruen. Die Agenten sterben im Normalfall an der Gratis-Grenze ihres
Datenanbieters (CoinGecko HTTP 429, gemessen 21.09.2026) — das ist erwartetes
Verhalten, kein Fehler des Treibers.

Muster: **die Entscheidung als reine Funktion herausziehen** und vier Faelle
unterscheiden, statt „lebt / lebt nicht" zu einer Ja-Nein-Frage zu machen:

```python
def starturteil(self, name, code, log):
    if code is None:              return "laeuft"
    if code in self.STARTERFEHLER: return "startfehler"    # 0xC0000135 u. a.
    if not (log.exists() and log.stat().st_size > 0):
        return "startproblem"     # tot und kein Log-Byte: Aufruf stimmt nicht
    return "laufzeitende"         # gestorben, hat aber gearbeitet: Normalfall
```

Nur `startfehler` und `startproblem` lassen den Test fehlschlagen. Dazu gehoert
die **Gegenprobe** auf die reine Funktion — ohne sie ist nicht belegt, dass der
Test ueberhaupt rot werden kann. Und: Warten auf ein Merkmal (Prozess lebt ODER
Log hat Inhalt, bis 15 s) statt auf eine feste Sekundenzahl.

Dasselbe gilt fuer den Aufraeumteil: er gehoert ins `finally`, sonst bleiben nach
einem fehlgeschlagenen Test Waisen stehen (Leak-Muster vom 21.09.2026, § 6).

## 9. Ein Test kann gruen sein, waehrend der Betrieb ein ANDERES Modul laedt (30.09.2026)

`mosaic/handeln.py` lud `import boersenstops` — und bekam `scanner/boersenstops.py`,
weil `scanner/` in seinem `sys.path` weiter vorn liegt. Der eigene Test lief gruen:
er hatte sein Verzeichnis per `sys.path.insert(0, HIER)` **zuletzt** eingefuegt und
damit nach vorn gestellt. Im echten Zyklus kam der fremde Namensvetter, und der
Abgleich endete mit `pruefe() got an unexpected keyword argument 'standard'` —
sichtbar erst im Lauf, nicht in der Suite.

Gegenmittel: ein Modul, dessen Name auch in einem anderen Spurenordner liegt,
bekommt einen **eigenen** Namen (`mosaic/boersenabgleich.py`). Dann kann keine
`sys.path`-Reihenfolge mehr entscheiden, welches Modul gemeint ist. Und: die erste
echte Ausfuehrung nach dem Einbau ansehen, nicht nur die Tests.

**Merksatz:** ein gruener Test belegt, dass das *geladene* Modul stimmt — nicht,
dass der Betrieb dasselbe laedt.

## 9. Ein Test, der die Betriebsdatei anfasst, braucht ZWEI Schranken (03.10.2026)

Befund aus der Fehlersuche vom 03.10.2026: `scanner/tests/test_einstieg_ist_marktkurs.py`
rief `handeln.vorschlaege()` mit `SCHREIBEN=True` und **ungebogenem Pfad**.
`vorschlaege()` protokolliert je Markt (`bewertete Maerkte`, `Kurs nicht abrufbar`) —
jede Testausführung landete damit in der **echten** `scanner/ablehnungen.csv`.

Drei unabhängige Belege, keiner davon geraten:

1. Die Zeile `2026-10-02T22:15:57+00:00,zyklus,bewertete Maerkte,1` stand mitten
   im Betriebsprotokoll — zwischen echten Zykluszeiten.
2. Der Modulwächter `test_papier_laesst_live_stehen` meldete
   `geaendert=['ablehnungen.csv']`.
3. Ein isolierter Lauf ließ die Datei von 3230 B auf 3784 B wachsen.

**Zwei Schranken, weil beide nötig sind.** `SCHREIBEN=False` nimmt *diesem*
Aufrufer das Schreiben. Der umgebogene Pfad schützt die Datei auch dann, wenn ein
späterer Test `SCHREIBEN` wieder anstellt. Wer nur eine baut, hat die Hälfte gebaut.

### Der teure Teil: die Reihenfolge im tearDown

Die erste Fassung meines Fixes hatte einen Reihenfolgefehler:

```python
def tearDown(self):
    handeln.ABLEHNUNGEN = self._alt_abl        # Pfad ZURÜCK
    handeln.ABLEHNUNGEN.unlink(missing_ok=True)  # löscht jetzt die ECHTE Datei
```

Die echte `scanner/ablehnungen.csv` war kurz weg. Sie wurde byte-gleich aus der
Bedingung-4-Spiegelung `Q:\Handel_Journal\ablehnungen.csv` wiederhergestellt —
nicht weil es Glück war, sondern weil die Spiegelung genau dafür da ist.

**Richtig:**

```python
def tearDown(self):
    handeln.ABLEHNUNGEN.unlink(missing_ok=True)  # löscht die TEMP-Datei
    handeln.ABLEHNUNGEN = self._alt_abl          # dann zurücksetzen
```

**Merksatz:** ein Test-Wächter, der die echte Datei löscht, ist teurer als der
Wächter selbst. Und: die Reihenfolge in einem `tearDown` ist Code, kein Detail —
`Pfad zurücksetzen` und `Datei löschen` dürfen sich nicht über Kreuz kommen.

## Ein Attrappenbau kann sieben Fehlschläge machen (05.10.2026)

**Regel: eine Attrappe braucht EINEN Zeitanker für Datei und „jetzt".**

Beim Bau der Historie-Wache (`test_historie_wache.py`) kostete die Attrappe
vier Runden, weil jede Runde eine andere Annahme trug:

1. **Zu hohe Ebene.** Die Attrappe lag in `tmp/historie`, die Wache liest
   `tmp/daten/historie` — der Test prüfte den Fehlerpfad, nicht die Regel.
2. **Zwei Zeitanker.** Datei und „jetzt" trugen verschiedene Konstanten; die
   gespannte Datei lag damit in der **Zukunft**, jede Reihe war jünger als null
   Tage, und **7 Fehlschläge** kamen aus einem Vorzeichenfehler im Attrappenbau,
   nicht aus der Regel.
3. **Zu wenige Reihen.** Die Tests legten je 1–4 Reihen an, der Backtest
   verlangt `mindest_symbole=30`. Die Wache meldete dann immer die
   *Mindestzahl*, und die *Altersregel* war gar nicht pruefbar (4 Fehlschläge).
   Die beiden Regeln brauchen getrennte Attrappen-Mengen.
4. **Falscher Anker.** `WURZEL = HIER.parents[3]` endete in `C:\Users\faupe\Documents`
   statt im BrainFiles — der Test las ein `replay.py`, das es dort nicht gibt.
5. **`self` im Lambda.** `w._groesse_gb = lambda: 0.0` statt
   `lambda _ordner=None: 0.0` — 9 Fehlschläge, weil die echte Funktion einen
   Pfad erwartet.

**Merksatz: die Zahl der Fehlschläge sagt nichts über die Regel.** Sie sagt, wie
viele Annahmen die Attrappe trug. Eine Attrappe mit **einer** Zeitkonstante
(`Attrappe.JETZT`) und **genau** so vielen Reihen, wie die geprüfte Regel
verlangt, ist die einzige Form, die eine Regel entscheidet.

## Ein Test findet den Fehler, den die Messung nicht fand (05.10.2026)

**Regel: eine geschätzte Zahl braucht eine Rechnung, die man nachrechnen kann.**

In `historie-nachladen.py` zaehlte `vorhanden` die alten Reihen doppelt
(`len(alt)` plus alle Dateien). Drei alte Reihen galten als „6 vorhanden",
dadurch verschoben sich `fehlend` und die **geschaetzte Laufzeit**. Der Code las sich
richtig; der Test `test_drei_alte_und_27_fehlende` rechnete `30 − 3 = 27` und
bekam 24.

Gegenprobe: den Zaehler rausnehmen, 2 von 10 Tests werden rot, zurueckgesetzt
wieder gruen. **Ohne die Gegenprobe haette der Test den Fehler nur beschrieben.**

**Merksatz: wer eine Zahl im Code FREI eintippt statt sie aus den Zaehlern zu
rechnen, hat einen Befund und keinen Beleg.**

### Merksatz

Zwei Schranken, wenn ein Test Betriebsdaten berührt: **Schreibschalter aus und
Pfad umbiegen**. Und im `tearDown` **erst löschen, dann zurücksetzen**.