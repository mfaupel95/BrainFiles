# Leitstand — eine Oberfläche für Überwachen, Freigeben, Backtesten und Markt

**Datum:** 2026-09-29
**Status:** Spezifikation genehmigt (Max, 2026-09-29); ergänzt um Optimieren,
Urteile und Bedienkomfort (Max, 2026-09-29), zur Prüfung
**Betrifft:** `Agenten/Handel` — neue Dateien `leitstand.py`, `leitstand_freigaben.py`,
`leitstand_backtests.py`, `leitstand_backtests.json`, `leitstand_markt.py`,
`leitstand_bedienung.py`; kleine Änderungen an `handelszentrale.py`,
`freigabefenster.py` und `backtest_urteile.py`

## Zweck

Heute verteilt sich die Arbeit am Handel auf mehrere Wege: die Handelszentrale
(Tk, nur lesend) zum Überwachen, Telegram zum Freigeben, die Kommandozeile für
Backtests, `prognose_berichte/` für den Marktscanner. Ziel ist **ein Fenster**,
aus dem Max überwacht, freigibt und backtestet, ohne Telegram oder Kommandozeile.

Entscheidungen von Max (2026-09-29):

| Frage | Entscheidung |
|---|---|
| Was darf die Oberfläche bewirken? | Lesen, Freigeben, Backtests starten. **Nie live handeln.** |
| Welche Backtests? | Erst die eigenen (Schritt 1), freqtrade später (Schritt 2) |
| Form | Tkinter-Fenster, kein Server, kein offener Port |
| Freigabe | Offene Anfragen des Dauerlaufs anzeigen und beantworten, Schließen, Notaus |
| Markt | Was das System schon hat (Schritt 1); Knöpfe zu FreqUI/OpenTerminal/Kronos in Schritt 2 |
| Aufbau | Neues Rahmenfenster mit Reitern, Handelszentrale unverändert als Reiter |

**Nicht Teil dieser Spezifikation (Schritt 2, eigene Spezifikation):**
freqtrade-Backtests, Knöpfe zu fremden Web-Oberflächen.

## Erfolgskriterien

1. `leitstand.py` öffnet ein Fenster mit vier Reitern: Überwachen, Freigaben, Backtests, Markt.
2. Eine vom Dauerlauf gestellte Freigabe-Anfrage lässt sich im Leitstand mit Ja
   (Dauer 1–24 h) oder Nein beantworten; die Wirkung ist dieselbe wie bei `/ja` bzw. `/nein`.
3. Schließen je Spur und Notaus wirken sofort und schreiben einen Grund.
4. Ein Backtest lässt sich aus dem Reiter starten, abbrechen und später nachlesen.
5. `test_handelszentrale_rein_lesend.py` bleibt grün; dieselbe Prüfung gilt neu für `leitstand_markt.py`.
6. `python handelszentrale.py` funktioniert allein wie bisher.
7. Eine Parametersuche (`optimieren.py`) lässt sich mit Trockenlauf starten; das
   Ergebnis erscheint als Tabelle. Übernommen wird nie aus dem Leitstand.
8. Backtest-Urteile lassen sich als Vorschau rechnen und **genau so, wie in der
   Vorschau gezeigt**, nach Bestätigung eintragen.

## Aufbau

```
leitstand.py                 Tk-Wurzel, ttk.Notebook, Takt für refresh()
 ├─ Überwachen   handelszentrale.Handelszentrale(rahmen)   liest nur
 ├─ Freigaben    leitstand_freigaben.FreigabenReiter        schreibt NUR über freigabefenster.*
 ├─ Backtests    leitstand_backtests.BacktestReiter         startet Prozesse, legt Läufe ab
 └─ Markt        leitstand_markt.MarktReiter                liest nur
```

Jeder neue Reiter ist eine Klasse, die einen `ttk.Frame` füllt, und hat `refresh()`.
`leitstand.py` ruft `refresh()` nur für den sichtbaren Reiter auf. Die
Handelszentrale behält ihren eigenen `_planer`.

### Änderung an `handelszentrale.py`

`Handelszentrale.__init__(self, root)` nimmt künftig ein beliebiges Tk-Widget als
Elternteil. Titel, Geometrie und `minsize` setzt sie nur, wenn das Elternteil
ein `tk.Tk` ist. `root.after(...)` funktioniert auf jedem Widget und bleibt.
Keine neuen Schreibzugriffe, keine neuen Imports; die AST-Prüfung gilt unverändert.

Schriftgröße und Risikostufe (`--schrift`, `--risiko`) sind heute Modul-Globale,
die `main()` setzt. `leitstand.py` bietet dieselben beiden Argumente und setzt
dieselben Globalen vor dem Aufbau.

## Freigaben-Reiter

### Anzeige

Eine Zeile je Spur aus `freigabefenster.alle()`, dazu jede Spur aus
`dauerlauf.SPUREN` ohne Eintrag (Stand „Papier“):

| Spalte | Quelle |
|---|---|
| Stand | `Fenster.text()` |
| Anfrage verfällt in | `anfrage_bis` minus jetzt (nur bei wartender Anfrage) |
| Freigegeben von / am | `freigegeben_von`, `freigegeben_am` |
| Zuletzt geschlossen / Grund | `zuletzt_geschlossen`, `schliess_grund` |
| Auto | Spur steht in `dauerlauf.AUTO_FREIGABE` |

Aktualisierung alle 5 s; dabei wird die Datei nur gelesen.

### Aktionen

| Knopf | aktiv, wenn | ruft | Rückfrage |
|---|---|---|---|
| Freigeben … | `anfrage_offen()` | Dialog, dann `oeffnen(spur, stunden, wer="leitstand")` | der Dialog |
| Ablehnen | `anfrage_offen()` | `schliessen(spur, "abgelehnt (Leitstand)")` | Ja/Nein |
| Schließen | `offen()` | `schliessen(spur, "von Hand (Leitstand)")` | Ja/Nein |
| Notaus | immer | `alles_schliessen("Notaus (Leitstand)")` | Ja/Nein, rot |

„abgelehnt“ im Grund löst die 12-h-Wiedervorlage aus, wie bei `/nein`.

### Freigabe-Dialog

Erfüllt Punkt 3 der Handelsregeln (am Bildschirm, Werte sichtbar, Selbstablehnung):

- Er zeigt die Grenzen aus der `wachen.json` der Spur. Die Wertetabelle, die heute
  `anfrage_text()` für Telegram baut, wird in eine Funktion
  `freigabefenster.grenzwerte(w, waehrung) -> list[tuple[str, str]]` (Bezeichnung,
  formatierter Wert) herausgezogen; `anfrage_text()` und der Dialog benutzen beide sie.
- Dauer: Drehfeld 1–24 h, Vorgabe = die bei der Anfrage genannte Dauer.
- **Ja** ruft `oeffnen(...)`. Gibt `oeffnen` `None` zurück (Anfrage inzwischen
  verfallen), meldet der Dialog das und schreibt nichts.
- **Nein** wirkt wie der Knopf „Ablehnen“.
- **120 s ohne Bedienung:** Der Dialog schließt sich, **es wird nichts geschrieben**.
  Jede Bedienung setzt die Uhr zurück, wie in `freigabe.py`. Die Anfrage verfällt
  danach regulär nach `ANTWORT_FRIST_MINUTEN`.

Eine noch offene Telegram-Nachricht bleibt stehen; ein späteres `/ja` findet
keine wartende Anfrage mehr und bewirkt nichts.

### Gleichzeitiges Schreiben

`freigabe_fenster.json` hat künftig zwei Schreiber (Dauerlauf und Leitstand).
`_lies` und `_schreib` laufen heute ohne Sperre; ein Lesen-Ändern-Schreiben
des einen kann das des anderen überschreiben.

Änderung in `freigabefenster.py`:

- Ein Kontextmanager `_gesperrt()` um jede Lesen-Ändern-Schreiben-Folge
  (`anfrage_stellen`, `oeffnen`, `schliessen`, `alles_schliessen`). Die Sperre ist
  eine Datei `freigabe_fenster.json.lock`, angelegt mit `O_CREAT|O_EXCL`.
  Gewartet wird höchstens 5 s, danach `TimeoutError`. Eine Sperrdatei, die älter
  als 30 s ist, gilt als verwaist und wird entfernt.
- `_schreib` schreibt in `freigabe_fenster.json.tmp` und ersetzt per `os.replace`.

Der laufende Dauerlauf übernimmt das erst nach einem Neustart. Bis dahin bleibt
eine Kollision im Millisekundenbereich möglich. Den Neustart entscheidet Max.

## Backtest-Reiter

### ⚠ Abweichung vom genehmigten Entwurf — bitte prüfen

Der genehmigte Entwurf sah eine Liste der einzelnen Backtest-Skripte vor. Beim
Schreiben fand sich `replay.py` aus dem Backtest-Fundament (Design vom 2026-09-24):
ein Kern, der die Spuren über ihre echten Module nachrechnet, **nur unter
`daten/backtest/<spur>/<lauf>/` schreibt** (abgesichert durch `NichtsAusserhalbTest`)
und die Kennzahlen als **einheitliches JSON** ausgibt
(`spur`, `runden`, `offen`, `gebuehr_pct`, `fenster`, `kerzenquelle`, `kennzahlen`).

Daher zwei Arten von Läufen:

1. **Replay (Hauptweg):** Spur wählen, dazu `--max-kerzen`, `--gebuehr` und
   optional `--gegenprobe`. Das Ergebnis erscheint als Kennzahlen-Tabelle; Läufe
   verschiedener Spuren lassen sich so nebeneinanderstellen. Angeboten werden die
   Spuren aus `SPUREN_TEIL_A`. Spuren aus `NICHT_NACHRECHENBAR` erscheinen
   ausgegraut mit dem dort hinterlegten Grund. Spuren aus `SPUREN_TEIL_B` kommen
   nur dazu, wenn der Plan belegt, dass `replay.py` sie über die Kommandozeile
   korrekt fährt.
2. **Einzelskripte (Zusatz):** Einträge aus `leitstand_backtests.json`, Ausgabe als Text.

Dazu kommen die zwei eigenen Bereiche **Optimieren** und **Urteile** (unten).
Alle vier teilen sich Prozessführung, „ein Lauf gleichzeitig“ und die Ablage.

Backtest-Runden zählen weiterhin **nicht** für die Freigabe-Bedingungen
(Design Backtest-Fundament); der Reiter sagt das in einer festen Zeile.

### `leitstand_backtests.json`

```json
{
  "_zweck": "Welche Einzelskripte der Leitstand starten darf. Aufnahme nur nach Pruefung (siehe docs/design/2026-09-29-leitstand-design.md).",
  "eintraege": [
    {
      "name": "Gitter",
      "skript": "gitter/backtest_gitter.py",
      "felder": [
        {"flag": "--wochen", "typ": "float", "vorgabe": 8.0, "min": 1, "max": 104}
      ],
      "schreibt": []
    }
  ]
}
```

Der Eintrag oben zeigt das Format; welche Skripte tatsächlich aufgenommen werden,
legt der Plan nach der Prüfung fest. Pfade sind relativ zu `Agenten/Handel`.
Gestartet wird mit demselben Interpreter, der den Leitstand ausführt
(`sys.executable`). Der Replay ist kein Eintrag, er ist fest im Reiter.

**Aufnahmebedingung** eines Einzelskripts, im Plan je Skript nachzuweisen:
- Es ruft keine Order-Funktion auf und baut keinen Börsen-Client mit Schlüssel.
- Keine Datei in `schreibt` wird von `dauerlauf.py`, `handeln.py`, `bot.py` oder
  einer Spur gelesen.

Kandidaten: `gitter/backtest_gitter.py`, `orb/backtest.py`, `orbk/backtest.py`,
`backtest_prognose.py`, `bt_varianten_fast.py`; `nautilus/backtest.py` und
`iv_waelle/backtest_iv_waelle.py` nur, wenn ihre `backtest_ergebnis.json` im
Betrieb nicht gelesen wird.
`optimieren.py` und `backtest_urteile.py` stehen **nicht** in der Liste; sie haben
eigene Bereiche (unten), weil ihr Ablauf mehr als „starten und lesen“ ist.

### Optimieren (`optimieren.py`)

Korrektur gegenüber der ersten Fassung: `optimieren.py` **liest** `spur_opt.json`
(Suchbereich) und schreibt nur die Vorschlagsdatei
`daten/backtest/<spur>/optimierung.json`, nie eine `wachen.json`. Kein Betriebsteil
liest `optimierung.json` (geprüft 2026-09-29). Das Skript darf deshalb voll in den Leitstand.

1. Spur wählen (nur Spuren mit Eintrag in `spur_opt.json`), dazu `--monate`,
   `--fenster`, `--max-kandidaten`, optional `--gebuehr`.
2. **Trockenlauf zuerst, automatisch** (`--trocken`): Kandidatenzahl, Zeitraum,
   Takt und geschätzte Dauer. Erst danach wird „Rechnen“ aktiv; ändert sich ein
   Wert, ist der Trockenlauf erneut fällig.
3. Rechnen läuft wie jeder Lauf (niedrige Priorität, einer gleichzeitig, abbrechbar).
4. Anzeige aus `optimierung.json`: Grundlinie (heutige Einstellung) oben, darunter
   die Kandidaten mit `netto_je_runde` und Urteil je Fenster, überlebende
   hervorgehoben; `ohne_wirkung` als eigener Hinweis („Feld X ändert nichts“).
5. **Übernahme bleibt bei Max.** Für einen überlebenden Kandidaten zeigt der
   Leitstand die Änderung als Diff „`<spur>/wachen.json`: alt → neu“ mit Knopf
   „Kopieren“. Der Leitstand schreibt nie in eine `wachen.json` — ein
   geänderter Stop oder ein anderes Ziel ist eine Entscheidung über Geld.

### Urteile (`backtest_urteile.py`)

`backtest_urteile.py` schreibt in `gitter/`, `orbk/` und `nautilus/wachen.json`
die Felder `backtest_bestanden`, `backtest_urteil`, `backtest_geprueft_am`
(mit `.bak`, nie `handel_erlaubt`). `orbk/wachen_orb.py` liest `backtest_bestanden`
als eine Freigabe-Bedingung — das Eintragen wirkt also in den Betrieb.

Entscheidung Max: **eingetragen wird genau das, was die Vorschau gezeigt hat.**

Änderung an `backtest_urteile.py` (zwei neue Optionen, bestehende Aufrufe unverändert):

- `--vorschau --vorschau-datei <pfad>`: wie bisher nichts in eine `wachen.json`,
  zusätzlich wird die Vorschau als JSON abgelegt: je Spur `bestanden`, `urteil`,
  `kennzahlen`, der alte Wert und ein SHA-256 der `wachen.json` zum Zeitpunkt
  der Vorschau; dazu `stand`.
- `--aus-vorschau <pfad>`: rechnet **keinen** Motor. Liest die Vorschau, prüft
  - `stand` höchstens **60 Minuten** alt,
  - der SHA-256 jeder betroffenen `wachen.json` unverändert,

  und ruft dann für jede Spur mit `bestanden` ≠ `None` die bestehende
  `freigabe_schreiben(...)` mit genau diesen Werten auf; `backtest_urteile.json`
  wird wie bei einem normalen Lauf aktualisiert. Schlägt eine Prüfung fehl,
  wird **nichts** geschrieben und der Grund ausgegeben.

Ablauf im Leitstand:

1. „Vorschau rechnen“ (Spuren wählbar) — Laufzeit bis 15 min je Motor, abbrechbar.
   Ablage unter `backtest_laeufe/<zeit>-urteile-vorschau.json`.
2. Tabelle je Spur: Urteil, `backtest_bestanden` alt → neu, Urteilstext.
3. „Urteile eintragen …“ (nur aktiv, wenn sich etwas ändert und die Vorschau
   jünger als 60 min ist) öffnet einen Bestätigungsdialog, der **jede** Änderung
   einzeln auflistet. Ja → `backtest_urteile.py --aus-vorschau <datei>`.
   Der Dialog schließt sich nach 120 s ohne Bedienung, ohne zu schreiben.
4. Ergebniszeile: welche Dateien geschrieben wurden, oder warum nicht.

Das Eintragen setzt nur **eine** Bedingung; scharf schaltet weiterhin Max über
den Freigaben-Reiter.

### Ablauf eines Laufs

- Start als `subprocess.Popen` mit `BELOW_NORMAL_PRIORITY_CLASS`, Arbeitsordner
  `Agenten/Handel`, stdout und stderr zusammengeführt, zeilenweise über eine
  Queue ins Textfeld.
- Höchstens **ein** Lauf gleichzeitig; der Start-Knopf ist gesperrt, solange einer läuft.
- Abbrechen: `terminate()`, nach 5 s `kill()`.
- Replay-Läufe bekommen `--lauf leitstand-<JJJJMMTT-hhmmss>`, damit sie keine
  anderen Läufe unter `daten/backtest/` überschreiben.

### Ablage

Jeder Lauf schreibt `backtest_laeufe/<JJJJMMTT-hhmmss>-<name>.json` mit
`name`, `befehl`, `start`, `ende`, `exit_code`, `abgebrochen`, `ausgabe`
(Text, auf 1 MB gekürzt) und bei Replay zusätzlich `ergebnis` (das geparste JSON).
Der Reiter listet diese Dateien, neueste zuerst; ein Klick zeigt Ausgabe bzw.
Kennzahlen. Der Ordner wird nicht versioniert und von keinem Betriebsteil gelesen.

## Markt-Reiter

- Liest `prognose_berichte/neuester.json` und, falls vorhanden,
  `prognose_berichte/neuester.weit.json` (Umschalter „streng / weit“).
- Zeigt `datum`, das Alter aus `erzeugt` (gelb ab 26 h), `maerkte_geprueft`,
  die Treffer als Tabelle (Spalten aus den Feldern, die `prognose.py` in `treffer`
  schreibt) und darunter die Tore aus `tore`.
- Fehlt der Bericht oder ist er unlesbar: Hinweis im Reiter, kein Absturz.
- Kein Knopf „Scan jetzt“: `prognose.py` schreibt Berichte und sendet Meldungen;
  das bleibt beim Dauerlauf.
- Holt keine Kurse selbst; Kurse zeigt der Überwachen-Reiter.

## Bedienung

Gemeinsame Bausteine in `leitstand_bedienung.py` (Tooltip, sortierbare Tabelle,
Zustandsdatei), damit die Reiter sie nicht je einzeln bauen.

**Hinweise und Statusleiste**
- Wartet eine Freigabe-Anfrage, heißt der Reiter „Freigaben (n)“ und das Fenster
  blinkt einmal in der Taskleiste (`FlashWindowEx` über `ctypes`, Windows; sonst
  nur der Reitertitel). Neu blinkt es erst bei der nächsten neuen Anfrage.
- Statusleiste unten: Dauerlauf läuft ja/nein (aus seinem Herzschlag, wie die
  Handelszentrale ihn liest), Zeit der letzten Aktualisierung, laufender
  Backtest mit Name und verstrichener Zeit, letzte Meldung einer Schreibaktion.

**Tastatur**
- Strg+1 … Strg+4 wechseln die Reiter, F5 aktualisiert den sichtbaren Reiter,
  Esc schließt einen Dialog (= Abbrechen, schreibt nichts), Strg+Plus/Minus
  ändern die Schriftgröße.
- **Notaus, Freigeben, Urteile eintragen haben kein Kürzel** — sie sollen nie
  aus Versehen per Taste auslösen.
- Jeder gesperrte Knopf hat einen Tooltip mit dem Grund
  („keine wartende Anfrage“, „erst Trockenlauf“, „Vorschau älter als 60 min“).

**Tabellen und Vergleich**
- Alle Tabellen sortieren per Klick auf den Spaltenkopf (nochmal = umgekehrt,
  Zahlen numerisch) und haben ein Filterfeld über der Tabelle.
- In der Laufliste lassen sich zwei Replay-Läufe markieren; „Vergleichen“ zeigt
  ihre Kennzahlen nebeneinander mit Differenzspalte.
- „Kopieren“ legt die sichtbare Tabelle tabulatorgetrennt in die Zwischenablage;
  „CSV …“ speichert sie in einen frei gewählten Pfad.

**Zustand merken**
- `leitstand_zustand.json` (nicht versioniert, von keinem Betriebsteil gelesen):
  letzter Reiter, Fenstergröße und -lage, Schriftgröße, zuletzt benutzte Werte
  je Backtest-Art, Sortierung je Tabelle.
- Geschrieben beim Schließen und nach Wertänderungen (gebündelt, höchstens alle 5 s),
  atomar über `.tmp` + `os.replace`. Unlesbar oder fehlend → Vorgaben, kein Absturz.
- Liegt eine gemerkte Fensterlage außerhalb aller Bildschirme, wird sie verworfen.

## Fehlerbehandlung

- Jede Dateilesung im Leitstand fängt `OSError` und `ValueError` ab und zeigt
  „nicht lesbar“, statt abzustürzen (Muster wie `handelszentrale.lade_json`).
- Schreibaktionen im Freigaben-Reiter melden ihr Ergebnis in einer Statuszeile,
  z. B. „xperp scharf für 6:00 h“, „Anfrage war verfallen — nichts geändert“,
  „Sperre belegt — bitte erneut“.
- Ein abstürzender Backtest-Prozess wird mit Exit-Code abgelegt; der Leitstand läuft weiter.

## Tests

Alle Tests arbeiten mit temporären Dateien: keine echte `freigabe_fenster.json`,
kein echtes `daten/backtest/`, kein Netz.

| Test | prüft |
|---|---|
| `test_handelszentrale_rein_lesend.py` | unverändert grün |
| `test_leitstand_markt_rein_lesend.py` | dieselbe AST-Prüfung für `leitstand_markt.py` |
| `test_handelszentrale_als_rahmen.py` | die Handelszentrale baut sich in einem `ttk.Frame` auf; allein gestartet setzt sie den Titel |
| `test_freigabefenster_sperre.py` | zwei parallele Schreiber verlieren keinen Eintrag; eine verwaiste Sperre wird entfernt; keine `.tmp` bleibt liegen |
| `test_freigabefenster_grenzwerte.py` | `anfrage_text()` liefert vor und nach dem Herausziehen denselben Text |
| `test_leitstand_freigaben.py` | Ja/Ablehnen nur bei wartender Anfrage; verfallene Anfrage → nichts geschrieben; Zeitablauf → nichts geschrieben; Notaus schließt alle |
| `test_leitstand_backtests_liste.py` | jedes Skript existiert, jedes `flag` steht in dessen `add_argument`, kein `schreibt`-Eintrag wird im Betrieb gelesen, `optimieren.py` und `backtest_urteile.py` stehen nicht drin |
| `test_leitstand_backtests_lauf.py` | mit einem Mini-Skript: Ausgabe kommt an, nur ein Lauf gleichzeitig, Abbruch wirkt, Ablagedatei ist vollständig |
| `test_leitstand_markt.py` | Bericht-Fixture wird angezeigt; fehlender Bericht → Hinweis; Alterswarnung ab 26 h |
| `test_leitstand_optimieren.py` | „Rechnen“ erst nach Trockenlauf; Wertänderung sperrt wieder; Diff-Anzeige aus einer Fixture-`optimierung.json`; keine Schreibstelle auf `wachen.json` (AST) |
| `test_backtest_urteile.py` (erweitert) | `--vorschau-datei` schreibt keine `wachen.json`; `--aus-vorschau` schreibt genau die Vorschauwerte; > 60 min alt → nichts geschrieben; geänderte `wachen.json` (Hash) → nichts geschrieben; kein Motor wird aufgerufen |
| `test_leitstand_bedienung.py` | Sortierung numerisch/text; Filter; Zustandsdatei: Rundreise, unlesbar → Vorgaben, Fensterlage außerhalb verworfen; Notaus/Freigeben/Eintragen ohne Tastenkürzel |

## Arbeitsort

Codearbeit in einem eigenen Worktree nach `AGENTS.md` dieses Ordners. Die
Zweig-Regel der Repo-Wurzel (nur `master`) bleibt gewahrt: Der Arbeitszweig wird
nach Abschluss auf `master` zusammengeführt und gelöscht.

## Offene Punkte für den Plan

1. Fährt `replay.py` die Spuren aus `SPUREN_TEIL_B` über die Kommandozeile korrekt?
2. Je Einzelskript: Nachweis der Aufnahmebedingung.
3. Wird `freigabe_fenster.json` gespiegelt (z. B. per `spiegelstand.py`)? Falls ja,
   dürfen `.lock` und `.tmp` nicht mitlaufen.
4. `backtest_urteile.py` startet seine Motoren selbst mit `scanner/.venv` bzw.
   `nautilus/.venv`; der Leitstand ruft es deshalb mit `scanner/.venv` auf
   (wie im Kopfkommentar), nicht mit `sys.executable`.
