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
