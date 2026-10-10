---
id: 20261001-werkzeug-fallen
title: 'Lektionen — Werkzeug-Fallen (grep {0,4000} und jevgrep Exit 1)'
tags: [lektion, werkzeuge, grep, jevgrep, regex]
created: 2026-10-01
updated: 2026-10-01
related: ['[[Werkzeuge/jevgrep]]', '[[Wissen/Hardware]]', '[[Lektionen/Windows-Umgebung]]']
summary: 'Zwei gemessene Stolpersteine der Werkzeuge: (1) grep mit {0,N}-Quantor auf einer langen Zeile laeuft in katastrophales Backtracking und frisst den Commit-Speicher (62,6 GB, 0xc000012d); (2) jevgrep bricht mit Exit 1 und "stdin is not a tty" ab — die Zeile ist MSYS-Rauschen, der echte Grund ist der Anbieter (429/402).'
---

# Werkzeug-Fallen

Zwei Stolpersteine, die Zeit gekostet haben, hier so dokumentiert, dass ein
frischer Agent den Workaround ohne Nachfragen anwenden kann. Beide sind
**gemessen**, nicht geraten.

---

## 1. grep mit `{0,N}`-Quantor auf einer langen Zeile — Regex-Amoklauf (T-228)

**Symptom.** Ein `grep -o -E '(de|ger):\{[^}]{0,4000}'` auf einer minifizierten
JS-Datei (eine einzige, sehr lange Zeile) hielt am 30.09.2026 **62,6 GB
virtuellen Speicher** und legte `node.exe` und den Explorer lahm
(`0xc000012d` = `STATUS_COMMITMENT_LIMIT`). Jeder neue Prozess scheiterte beim
Start, bis der Amok-`grep.exe` beendet war (danach 43 GB frei).

**Ursache.** Katastrophales Backtracking: der `{0,4000}`-Quantor auf einer
langen Zeile ohne Zeilenumbruch zwingt die Regex-Engine, an jeder
Startposition bis zu 4000 Zeichen durchzuprobieren — bei einer minifizierten
Datei ist das eine einzige Zeile, und der Speicher explodiert.

**Workaround.** Die Zeile begrenzen oder das Muster so bauen, dass kein
offener `{0,N}`-Quantor auf eine lange Zeile trifft:

```bash
# 1) Zeilenlaenge begrenzen, bevor grep sie sieht (hier: 200 Zeichen)
fold -w 200 datei.js | grep -o -E '(de|ger):\{[^}]{0,4000}'

# 2) Wiederholung begrenzen statt offen lassen
grep -o -E '(de|ger):\{[^}]{0,200}' datei.js

# 3) MSYS-Rauschen und Locale-Effekte ausschalten
LANG=C LC_ALL=C grep --color=never -o -E '...' datei.js

# 4) Zeitgrenze setzen, damit ein Amoklauf nicht den Rechner lahmlegt
timeout 30 grep -o -E '...' datei.js
```

**Datum.** 30.09.2026 (gemessen, siehe `Wissen/Hardware.md`).
**Betroffene Version.** MSYS `grep` (git-bash `/usr/bin/grep`); das Muster
`{0,4000}` ist die eigentliche Gefahr, unabhaengig von der grep-Version.

---

## 2. jevgrep bricht mit Exit 1 und "stdin is not a tty" ab (T-304)

**Symptom.** Von neun jevgrep-Laeufen am 01.10.2026 endeten vier sofort
(0,2–0,7 s, Exit 1) mit der Zeile `stdin is not a tty` und ohne Suchausgabe —
unabhaengig davon, ob stdin aus der Konsole, aus `/dev/null` oder aus einer
Datei kam, und unabhaengig vom Vordergrund. Dieselbe Frage ueber dieselbe
Wurzel gelang Sekunden spaeter.

**Ursache.** Die Zeile `stdin is not a tty` ist **MSYS-Rauschen**, nicht aus
jevgrep (im `dist` nirgends zu finden). Der echte Grund ist der **Anbieter**:
die Sonde `Agenten/Werkzeuge/jevgrep/sonde_zen.py` antwortet
`429 FreeUsageLimitError` fuer `jev-1.13-free` (freies Kontingent nach rund
zehn Suchen an einem Abend aufgebraucht) und `402 Insufficient account funds`
fuer das bezahlte `jev-1.13` (Konto ohne Guthaben). jevgrep nennt den Grund
nicht — es bricht ohne Ausgabe ab oder laeuft in die Zeitueberschreitung.

**Workaround.** In jevgrep nichts suchen, wenn der Anbieter abweist — das ist
Anbieterverhalten, kein Schluesselfehler. Vor jeder Suche die Sonde laufen
lassen und ihren Befund weitergeben:

```bash
python Agenten/Werkzeuge/jevgrep/sonde_zen.py   # nennt HTTP-Status und Dauer
```

- `429` → freies Kontingent aufgebraucht: spaeter erneut versuchen (Zeitfenster).
- `402` → bezahltes Modell ohne Guthaben: bei OpenCode Zen aufladen
  (0,042 USD/1M Eingabe ≈ 4 US-Cent je Suche).
- `403 error code 1010` → Cloudflare weist ab, **nicht** der Schluessel.
- Exit 1 ohne Ausgabe → Anbieter hat abgewiesen; Sonde laufen lassen, dann handeln.

Der Schluessel selbst war nie das Problem: `jg doctor` antwortet „Jev
connection verified", solange das Kontingent traegt.

**Datum.** 01.10.2026 (gemessen, siehe `Werkzeuge/jevgrep.md` und
`Archiv/TASKS.md` T-304).
**Betroffene Version.** jevgrep 0.7.0 (npm `@dzhng/jevgrep`), Anbieter
OpenCode Zen (`jev-1.13-free` / `jev-1.13`).
## 3. „Datei verschwunden" erst messen - drei Fehlalarme an einem Abend (T-100, 05.10.2026)

Drei Dateien galten als Opfer des Dateischwunds, keine war es:

- `tasks_eintragen_strk.py` und `tasks_eintragen_t365.py`: die `.pyc` lagen noch in `__pycache__/`, die `.py` fehlten - aber die `.py` hatte ich selbst mit `rm -f` geloescht. Die `.pyc` bleibt dabei als Artefakt liegen; ein `pyc ohne py` ist deshalb KEIN Schwundbeweis, solange der eigene Loeschbefehl in derselben Sitzung liegt.
- `commitmsg_skill_trailing.md`: galt als „beim Commit-Aufruf weg" - sie lag die ganze Zeit mit 2158 B da. Ich hatte sie als `.md` geschrieben und mit `-F ...txt` referenziert. `git commit -F` meldet dann `could not read log file`; das liest sich wie eine verschwundene Datei, ist aber ein Tippfehler im eigenen Aufruf.

**Merksatz:** Vor jeder Schwundmeldung zwei Zeugen: (1) eine Markerdatei anlegen und ihr Alter messen (`date -r <datei>`), (2) die Uhr des eigenen Werkzeugs gegen die Host-Uhr pruefen (`git log -1 --format=%ci`). Erst wenn der Marker selbst verschwindet, ist es Schwund. `__pycache__`-Reste und `-F`-Fehlermeldungen sind Fehlalarme.

**Zusatz:** `cache/scratch` ist als Wache-Ziel ungeeignet - der Ordner wird nach 24 h Ruhe automatisch geleert, eine Wache dort meldete planmaessiges Aufraeumen als Schwund.
## 4. Ein fremder Eintrag im geteilten Index nimmt eine Loeschung mit (06.10.2026)

Beim Schliessen von T-368 (Commit `8e4afed6`) landete eine FREMDE Loeschung im eigenen
Commit: `Werkstatt/FREQTRADE-SETUP-GUIDE.md`, 368 Zeilen. Die Datei war Minuten vorher
von der Routine `fremdarbeit-einziehen` gerade WIEDERHERGESTELLT worden (Commit `bb348a7c`,
24 ruhende Dateien) - eine PR hatte sie am 05.10. 22:30 entfernt, die Routine holte sie zurueck,
mein `git add MaxHirn/Archiv/TASKS.md` + `git commit` nahm die Vormerkung mit.

DAS MUSTER: `git add <eigene Pfade>` + `git commit` OHNE Pfadangabe committet den GANZEN Index,
nicht die eben vorgemerkten Pfade. Eine parallele Sitzung (oder eine Routine) kann Sekunden vorher
etwas anderes vorgemerkt haben - es faehrt mit, unter MEINER Meldung.

GEGENMITTEL, drei Schritte, alle drei noetig:

1. **Vor** dem Commit `git diff --cached --numstat` LESEN (nicht nur ausfuehren) - steht dort ein
   Pfad, den man nicht kennt, ist er fremd.
2. Bei fremden Pfaden mit EIGENEM Index committen: `GIT_INDEX_FILE=<scratch>/idx_<thema>` +
   `git read-tree HEAD` + `git add <eigene Pfade>` + `git commit` (ohne Pfadangabe).
3. **Nach** dem Commit `git show HEAD --stat` pruefen. Steht dort eine Datei, die nicht ins Thema
   gehoert, ist sie mitgenommen worden - und die Reparatur ist ein FOLGE-Commit, der den Inhalt
   aus dem Vorgaenger-Stand zurueckholt (`git checkout <vorgaenger> -- <pfad>`), NIE ein `--amend`
   oder force-push (der Baum hat einen geteilten Index und fremde Arbeit).

WARUM ES SCHLIMM IST: die geloeschte Datei war schon einmal weg und gerade wieder da. Der eigene
Commit loeschte sie ein ZWEITES Mal, ohne dass die Meldung das Wort 'Loeschung' enthielt -
`2 files changed, 15 insertions(+), 382 deletions(-)` liest sich wie eine TASKS-Aenderung.
MERKSATZ: `git diff --cached --numstat` vor dem Commit und `git show HEAD --stat` danach sind
die beiden Blicke, die den geteilten Index beherrschbar machen. Ohne sie faellt es erst auf,
wenn jemand die Datei vermisst.

## 5. Drei Statusmeldungen, die nicht stimmen (07.10.2026)

Beim Abarbeiten von T-302/T-249/T-254 kamen drei Werkzeugmeldungen, die je
etwas anderes behaupteten als die Messung. Alle drei sind harmlos, aber jede
haette eine falsche Entscheidung ausloesen koennen.

**(a) `hermes gateway status` meldet 'Gateway is not running', waehrend er laeuft.**
Gemessen: `gateway_state.json` trug `gateway_state: running` mit PID 70456, der
Prozess war da, und alle Plattformen (a2a, telegram, photon, webhook) standen auf
`connected`. Die Statusabfrage ist unzuverlaessig. Wahrheit sind ZWEI Zeugen:
`gateway_state.json` UND der Prozess (Namensmuster aus Teilen bauen, eigenen PID
ausschliessen). Nicht die Statuszeile.

**(b) `paperclipai doctor` meldet 'Port 3100 is already in use' als Warnung.**
Das ist der NORMALFALL, wenn die Instanz laeuft - die Meldung liest sich wie ein
Konflikt, ist aber der Beleg fuer einen gesunden Dienst. Wer sie als Fehler liest,
startet einen zweiten Prozess gegen dieselbe Datenbank.

**(c) Der Router fuehrt KEIN `gh/`-Praefix - nur `github/`.** Und selbst `github/`
loest nicht auf, solange der `github`-Provider in OmniRoute auf `is_active=0` steht.
Gemessen gegen `/v1/models` (1831 Modelle live): 64 von 106 Eintraegen der
Hauptconfig waren tot, darunter ALLE 62 `gh/*` und `github/*`.

**MERKSATZ:** Ein Eintrag in einer Auswahlliste ist kein Beleg, dass das Modell
existiert. Wer eine Liste kuerzt oder erweitert, prueft jeden Namen gegen die
LIVE-Quelle (`/v1/models` beim Router) - nicht gegen die Liste selbst, die ihre
eigene Nutzung waere. Und eine Statusmeldung ohne zweiten Zeugen ist eine
Behauptung, keine Messung.
