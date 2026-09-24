# Die Freigabe von Hand (Punkt 3 der Handelsregeln)

Scharf geschaltet wird von Hand. Dafür gibt es **zwei Fassungen**, und eine von
beiden muss offen sein.

## Fassung 1 — Bildschirm (`freigabe.py`)

- Läuft, wenn `sitzung_da()` wahr ist, also `sys.stdin.isatty()` und
  `MAXHIRN_ROUTINE` **nicht** gesetzt.
- Zeigt je Vorschlag die Werte aus `wachen.json` als Ist/Soll-Tabelle, lässt
  sie innerhalb der Grenzen verstellen; die Obergrenze jedes Reglers **ist**
  der Wachenwert.
- `FREIGABE_ZEITLIMIT_S` (120 s) ohne Bedienung → Ablehnung. Die Uhr ist der
  tragende Schutz, nicht die Sitzungserkennung: `isatty()` meldet unter
  Windows auch bei umgeleitetem stdin ein Terminal.
- Fenster schließen, Escape, Entf = Nein. Ablehnen verwirft auch, was in
  derselben Runde schon bestätigt war.
- Reißt eine Grenze, ist der Knopf gesperrt; `Invoke` auf einen gesperrten
  Knopf tut nichts, ein gesperrter Auftrag lässt sich also auch per Enter
  nicht durchdrücken.
- Halten alle Grenzen, aber `freigabe.erfuellt` oder `handel_erlaubt` stehen
  auf `false`, gibt das Fenster **Papier** frei und sagt das auf dem Knopf —
  nie stillschweigend.
- **Stillgelegte Spuren sperrt das Fenster.** `stillgelegt` aus der
  `wachen.json` der Spur ist eine eigene Zeile in der Wachen-Tabelle
  (`freigabe.stillgelegt()`); sie zählt **nicht** als Zustandszeile, sondern
  als harte Zeile — der Knopf ist **gesperrt** und heißt „Stillgelegt“, der
  Hinweis sagt „hier wird nichts freigegeben — weder live noch als Papier“.
  Gesperrt statt Papier, weil ein bestätigter Papierauftrag eine Zusage wäre,
  die niemand einlöst (das jeweilige `handeln.py` verweigert stillgelegte
  Spuren ganz), und weil „Werte anpassen“ hier nichts zu sagen hätte. Der
  Schutz greift **auch wenn jemand `handel_erlaubt` und `freigabe.erfuellt` von
  Hand umlegt**. Gelesen wird das Feld, nicht eine Liste im Code — beim
  Wiederanschalten wird dort zurückgesetzt, hier nichts nachgezogen. Nachweis:
  `tests/test_freigabe_papier.py` (inkl. Gegenprobe: aktive Spur gibt weiter
  `live`), Gegenprobe `--nur-pruefen`.
- `--nur-pruefen` rechnet ohne Fenster und ohne Bestätigung: für Routinen und
  als Testpfad.

## Fassung 2 — Zeitfenster (`freigabefenster.py`)

- `anfrage_stellen()` merkt eine wartende Anfrage vor, öffnet aber nichts.
  Gestellt wird sie nur vom Dauerlauf, und nur wenn **nichts außer der
  Freigabe** fehlt — sonst wären es Fragen, die auch nach einem `/ja`
  folgenlos blieben.
- `oeffnen()` gibt nur frei, wenn eine Anfrage wartet. Damit kann eine
  übernommene Telegram-Sitzung nicht aus dem Nichts scharf schalten.
- `/ja [h]` öffnet, `/nein` lehnt ab, `/stop` schließt alles sofort.
  `MAX_STUNDEN` = 24 als Deckel: eine Freigabe, die man vergessen kann, ist
  kein Fenster, sondern ein Dauerzustand. `ANTWORT_FRIST_MINUTEN` = 30.
- `schliessen()` geht immer, ohne Anfrage und ohne Frist.
- Der Text nennt die Grenzen aus `wachen.json` mit — ohne sie wäre die
  Freigabe eine Blankounterschrift.

## Was für beide gilt

- **Ausstiege laufen nie durch die Freigabe.** Ein Stop muss auch dann
  greifen, wenn niemand davorsitzt. Bestätigt wird nur, was Geld bindet.
- **Unmittelbar vor dem Einstieg noch einmal prüfen.** Zwischen
  Sperrenprüfung und Kauf liegen Netzabfragen, und `/stop` kann dazwischen
  greifen. Ist das Fenster dann zu, unterbleibt der Einstieg.
- **Protokoll:** `freigabe_journal.jsonl`, eine Zeile je Entscheidung. Nur
  anhängen, nie lesen, entscheidet nichts; ein Schreibfehler darf ein
  Freigeben nie verhindern. Wer ohne Fenster freigibt (Zeitfenster-Weg), ruft
  `freigabe.audit(...)` selbst auf — sonst fehlt die Spur.
- **Was das Fenster zeigt, muss ausgeführt werden können.** Die Groesse wird
  VOR dem Freigabefenster auf das FREIE Guthaben gedeckelt (freies Guthaben
  minus Gebuehrenpuffer der Zielboerse) und faellt sie unter die Untergrenze
  des Einsatzes, wird nicht gehandelt — mit Begruendung im Log. Sonst zeigt das
  Fenster einen Betrag, den die Boerse ablehnt: das ist kein Handel, sondern
  Laerm, und im Protokoll nicht von einem Signalfehler zu unterscheiden.
- **Das Guthaben-Tor meint den KLEINSTEN Einsatz, nicht einen Wunschpuffer.**
  `mindest_guthaben_…` muss so tief liegen, dass der Mindest-Einsatz hineinpasst
  (Mindest-Einsatz + kleiner Rest). Ein Tor aus einer veralteten Rechnung
  (z. B. „3x Einsatz“, als der Einsatz noch halb so hoch war) sperrt den
  Live-Zweig dauerhaft, waehrend alles "scharf" aussieht — und weil
  `nur_fenster_fehlt` GENAU EINEN Grund verlangt, oeffnet der Fahrer weiter
  Fenster fuer einen Lauf, der nicht handeln kann.
- Der Sperrgrund muss **genau ein** Grund bleiben und das Wort
  „Freigabefenster“ tragen — daran hängt `dauerlauf.nur_fenster_fehlt`.

## Neue Spur an die Freigabe hängen

1. `SPUR = "<spur>"` als Modulkonstante setzen.
2. `sitzung_da()` aus der bestehenden Spur übernehmen (nicht neu erfinden).
3. `zeitfenster_offen()` ergänzen: `freigabefenster.lade(SPUR).offen()`, in
   `try/except` — im Zweifel **nicht** freigegeben, im Zweifel Papier.
4. Die siebte Sperre in `sperren_live()` als
   `if not sitzung_da() and not zeitfenster_offen(): …` mit dem Wort
   „Freigabefenster“ im Text.
5. Im Einstiegszweig verzweigen: Sitzung → Fenster je Vorschlag; sonst
   Zeitfenster → alle Vorschläge in einem Zug, protokolliert.
6. Gegenprobe wie im Skill beschrieben, mit stillgelegtem Order-Pfad.
