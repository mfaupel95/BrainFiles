# Eine mitgelieferte Anleitung ausfuehren: Vorflug, Start, Nachweis

Fuer den Auftrag "diese Anleitung ausfuehren" (Repo-README, Vault-Notiz, ein
mitgeliefertes Handbuch). Gilt fuer jedes Werkzeug, das ein Konto oder eine
externe Schnittstelle anfasst; bei einem HANDELSWERKZEUG ist jeder Schritt
davor ein Vorflug.

## 1. Die richtige Anleitung finden

- Unter aehnlichem Namen liegen oft MEHRERE Dokumente (gross geschriebene
  Spezifikation neben der Hausnotiz). Vor dem ersten Befehl beide lesen.
- **Pruefmerkmal: die echte Anleitung nennt das Einstiegspaar, das im Baum
  WIRKLICH existiert** - Binary/Paketpfad, Skriptdatei, Statusdatei, Schalter,
  die `--help` kennt. Ein Dokument, das einen ANDEREN Workspace beschreibt
  (Dienstordner, Compose-Dateien, Pfade, die es nicht gibt), ist eine
  Spezifikation oder ein KI-Entwurf. Ihn zuerst zu fahren kostet pro Schritt
  einen Fehlversuch, und der Bericht nennt danach die falsche Anleitung.
- Probe in einer Minute: jede im Dokument genannte Datei mit `ls` und jedes
  genannte Flag mit `--help` gegen den Baum halten. Treffer = Anleitung.
- Das Ergebnis der Ausfuehrung gehoert AN die Anleitung (kurzer Block am Ende:
  Schalter, Kennung des Laufs, gemessener Kontostand, Logpfad, wie man
  nachsieht) - sonst ist die Notiz nach dem Lauf wieder nur eine Behauptung.

## 2. Vorflug: der lesende Pfad zuerst

- Viele Werkzeuge bringen einen Schalter fuer den **lesenden** Aufruf mit, oft
  abgeschaltet geparkt: ein `#[ignore]`-Test, ein `--dry-run`, ein `validate`,
  eine `status`-/`balance`-Funktion. Genau den ZUERST fahren - er belegt
  Schluessel, Region/Host und Anmeldung, ohne eine einzige Order.
- Die Ausgabe dieses Vorflugs ist der Beleg: Kontostand bzw. Gegenseite mit
  Zahlen nennen (frei/gesperrt je Waehrung), nicht "Verbindung ok".
- Voraussetzungen nur auf EXISTENZ pruefen, Werte nie ausgeben:
  `[Environment]::GetEnvironmentVariable('NAME','User')` und davon Laenge/
  Anfang melden. `reg query HKCU\Environment` druckt die Werte im Klartext -
  als Nachweis unbrauchbar.
- **Demo/Testnetz ausdruecklich pruefen, nicht annehmen:** der Lauf muss die
  Umgebung im eigenen Statusbericht nennen (`network: testnet`). "Papier" ist
  kein Zustand, den man dem Schalter glaubt, sondern einer, den das Artefakt
  zeigt.

## 3. Nur ein Lauf zur Zeit

Vor dem Start die Prozesszahl des ZIELBINAERS messen - erwartet ist 1 (der
eigene). Zwei Laeufe ordern doppelt und schreiben in dieselbe Statusdatei:

```bash
powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { \$_.Name -like '<binaer>*' } | Measure-Object).Count"
```

Muster aus Teilen bauen, wenn der eigene Aufruf den Namen enthaelt (der Filter
findet sonst die eigene Kommandozeile mit).

- **Die Doppelstart-Pruefung muss im ABGELEHNTEN Fall bewiesen werden.** Sie
  gegen den wirklich laufenden Prozess aufrufen und Exitcode ungleich 0
  verlangen; ein durchgelaufener Start beweist nichts ueber die Pruefung. Eine
  Pruefung, die still durchfaellt (Nulltreffer), startet einen ZWEITEN Lauf -
  beide ordern doppelt und schreiben dieselbe Statusdatei, und sichtbar ist
  davon nur eine wachsende Kerze. Der zweite Lauf muss sofort per PID sterben.
  Haeufigste Ursache des stillen Durchfallens: Kurznamen fremder Textwerkzeuge
  (`tasklist`, `find`) in einer `.cmd` — volle Pfade nehmen oder in PowerShell
  per `Get-CimInstance Win32_Process -Filter` fragen (siehe
  `windows-host-zugriff`).
- **Fuer einen Lauf, den der Nutzer von Hand startet, gehoert ein
  Wurzel-Aufrufer** ins Wurzelverzeichnis (Muster: ohne Argument den lesenden
  Stand zeigen, mit `start` starten, dieselbe Doppelstart-Pruefung, Freigabe
  per `!/<name>.cmd` in der `.gitignore`): seine Shell startet in der Wurzel,
  waehrend das Werkzeug in einem Unterordner liegt.

## 4. Start

- Dauerlauf IMMER ueber `terminal(background=true, notify=true)` mit `cwd` =
  Repo-Ordner und umgeleiteter Ausgabe. Shell-Wrapper (`nohup`, `disown`,
  `setsid`, `&`) werden abgelehnt bzw. machen den Prozess unverfolgbar - ohne
  Wrapper abschicken, den Prozessstatus in einem SEPARATEN Aufruf lesen.
- Fertig gebautes Binary direkt starten (`./target/<profil>/<name>`), wenn ein
  Bau vorliegt; `cargo run`/`npm run` haengen sonst den Bau vor jeden Start und
  verdoppeln den Prozessbaum (Launcher + Kind).
- **Artefakt- und Lognamen mit der HOST-Uhr bilden** (`Get-Date -Format
yyyyMMdd-HHmm`), nicht mit `date` aus dem Terminal: die Container-Uhr der
  Sandbox laeuft nach Ruhezustand nach (gemessen ~4-5 h), und ein aus ihr
  benanntes Log traegt dauerhaft die falsche Stunde.
- Der erste Zustand nach dem Start ist "starting" mit 0 Kerzen/Ticks - das ist
  kein Fehler. Erst wenn ein paar Perioden durch sind, ueber `orders_placed`
  und `last_error` urteilen:

## 5. Nachweis aus dem Artefakt, nicht aus stdout

- Das Werkzeug schreibt seinen Zustand selbst (Statusdatei, JSON, DB). DIESE
  ist der Zeuge - ein leerer Log ist bei gepufferter Ausgabe normal und kein
  Abbruch.
- Fuer die Anzeige den LESENDEN Weg der Hausschicht nehmen (eine Bruecke, die
  die Statusdatei parst) und ihre Felder nennen: Zustand, Gegenstand, Umgebung,
  Kennung, Zaehler, `last_error`. Ein leeres `last_error` plus wachsende
  Zaehler ist der belastbare "laeuft".
- Bleibt der Zaehler stehen, ist die Ursache ERST in der Statusdatei zu suchen,
  dann im Prozess, dann im Netz.

## 6. Beenden

- Der dokumentierte Weg (Strg+C im eigenen Terminal) gilt nur fuer einen
  Vordergrundlauf. Fuer den Hintergrundlauf die Kennung aus der Statusdatei
  nehmen und den Prozess namentlich beenden (`taskkill /IM <binaer> /F`), danach
  die Prozesszahl nachzaehlen.
- Ein hartes Beenden laesst die Statusdatei auf "running" stehen. Wer den Lauf
  spaeter bewertet, prueft deshalb Prozess UND Zeitstempel der Datei, nicht den
  Zustandstext allein. **Und die Kennung IN der Datei gegen die lebenden
  Prozesse halten:** nach dem Beenden einer falschen zweiten Instanz nannte die
  Datei deren tote PID, waehrend der gesunde Lauf weiterlief; beim naechsten
  Takt hat der Lauf sie selbst ueberschrieben. Erst ein Vergleich von Kennung
  und Prozessliste entscheidet, ob der Lauf tot ist - die Datei allein sagt es
  nicht, und ein zweiter Start "weil die PID tot ist" ist genau der Doppelstart.
- Ein laufendes Handelswerkzeug gehoert NICHT stillschweigend in einen
  Dauerbetrieb: Wache nach Hausmuster anbieten (leere Ausgabe = nichts senden),
  statt den Prozess ohne Aufsicht stehen zu lassen.
