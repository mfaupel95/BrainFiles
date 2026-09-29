# Leitstand — eine Oberfläche für Überwachen, Freigeben, Backtesten und Markt

**Datum:** 2026-09-29
**Status:** Entwurf in zwei Abschnitten genehmigt (Max, 2026-09-29), Spezifikation zur Prüfung
**Betrifft:** `Agenten/Handel` — neue Dateien `leitstand.py`, `leitstand_freigaben.py`,
`leitstand_backtests.py`, `leitstand_backtests.json`, `leitstand_markt.py`;
kleine Änderungen an `handelszentrale.py` und `freigabefenster.py`

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
**Ausgeschlossen:** `optimieren.py` (schreibt `spur_opt.json`) und
`backtest_urteile.py` (schreibt `backtest_urteile.json`) — beide wirken in den Betrieb.

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

## Arbeitsort

Codearbeit in einem eigenen Worktree nach `AGENTS.md` dieses Ordners. Die
Zweig-Regel der Repo-Wurzel (nur `master`) bleibt gewahrt: Der Arbeitszweig wird
nach Abschluss auf `master` zusammengeführt und gelöscht.

## Offene Punkte für den Plan

1. Fährt `replay.py` die Spuren aus `SPUREN_TEIL_B` über die Kommandozeile korrekt?
2. Je Einzelskript: Nachweis der Aufnahmebedingung.
3. Wird `freigabe_fenster.json` gespiegelt (z. B. per `spiegelstand.py`)? Falls ja,
   dürfen `.lock` und `.tmp` nicht mitlaufen.
