# Waechter-Registrierung und Statusdatei-Pfade (Befund 07.10.2026, omnitrade)

Vier Regeln aus einem Fall, in dem ein Live-Lauf 45 h tot lag, ohne dass der
Waechter eingriff (omnitrade `live.json` / `ema_cross_20_50`):

## 1. Eine Wiederbelebungs-Wache startet nur, was in ihrer REGISTRIERUNG steht

Der Waechter iteriert eine benannte Menge (`LAEUFE` in `omnitrade_start.py`),
liest je Eintrag dessen `statusdatei()` und startet nur diesen Eintrag neu.
Ein Lauf, der nicht in der Liste steht, wird zwar als "steht" gemeldet, aber
nie wiederbelebt — tagelang, waehrend alle Beteiligten auf die Wache
vertrauen. Vor der Aussage "der Waechter hat es nicht neu gestartet" die
Liste pruefen, die die Wache wirklich durchlaeuft, und den Lauf EINTRAGEN
statt von Hand neu zu starten: ein Handstart stirbt beim naechsten Ausfall
erneut unbemerkt.

## 2. Derselbe Dateipfad an ZWEI Stellen gebaut, driftet auseinander

`statusdatei()` lief zentral und bekam eine Ausnahme fuer den Legacy-Lauf
(ema_cross -> `live.json` statt `live_<strategie>_<symbol>.json`). Die
Startfunktion `befehl()` baute den `--status-file`-Pfad aber INLINE — der
Fix an der Helferfunktion wirkte nicht auf den Start, und der Lauf schrieb
die benannte Datei, waehrend Pruefung und Handelszentrale `live.json` lasen.
Regel: Pfad EINMAL zentral rechnen und Beide Zweige (Pruefen UND Starten)
darueber fuehren. Nach dem Fix den LAUFENDEN Prozess gegen seine
Kommandozeile pruefen (`Get-CimInstance Win32_Process ... CommandLine`),
nicht die Funktion.

## 3. Wiederbeleben = erst Duplikate zaehlen, dann EINEN starten

Mehrere `starte()`-Aufrufe bei toter Statusdatei erzeugen je einen Prozess:
die Pruefung sieht die tote Datei, haelt jede Instanz fuer erlaubt und
startet. Vor dem ersten Neustart die Prozessliste nach Kommandozeile
(`--status-file`) gruppieren, Ueberzaehlige PID-genau beenden, EINEN
starten und im naechsten Aufruf die Prozesszahl nachzaehlen. Gehoert zum
Muster "erst sichern, dann pruefen, dann PID-genau beenden".

## 4. Eine tote Statusdatei aus dem Glob der Wache nehmen: umbenennen, nicht loeschen

Eine Leiche ohne lebenden Schreiber (state auf `running`, PID tot, mehrere
Tage alt) bleibt bei jedem Takt in der Lauf-Liste und wird ewig als
"steht/BEENDET" gemeldet. `live_ema_cross_20_50_BTCUSDC.json` nach
`...json.leiche-20261007` umbenennen: der Beleg bleibt, die Wache listet
sie nicht mehr.
