# BrainFiles Bus

Der Bus meldet den Start und die Beendigung aller geplanten Aufgaben an ein zentrales Journal, wertet deren Erfolg aus und sichert Fehler auf dem Handy.

Ein toter Bus darf niemals einen Lauf abbrechen — alle Erzeuger schreiben lokal ins Journal zurück.

## Dateien

- `bus.py` — Der HTTP-Dienst. Schreibt ins Journal, verteilt Ereignisse an den Sprecher.
- `journal.py` — Der einzige Ort der Wahrheit: `journal/JJJJ-MM-TT.jsonl`.
- `ereignis.py` — Python-Erzeuger: Stellt lokale Versuche an, fällt sonst ans Journal zurück.
- `Ereignis.ps1` — PowerShell-Erzeuger: `Melde-Start` und `Melde-Ende`.
- `auffaellig.py` — Regeln für Fehlerauswertung: Exitcode, Median-Dauer, Ausbleiben.
- `sprecher.py` — Der Melder: tastet Fehler und Tagesmeldungen aus, fädelt sich in `bus.py` ein.
- `bus.json` — Der Port und die PID des laufenden Busses.
- skillsbot.py — Telegram-Bruecke zum A2A-Agenten: Max fragt, Hermes antwortet mit allen Skills.

## Von Hand starten

```bash
python bus.py
```

Der Bus benutzt Port 8766 (in `bus.json` nachzuschauen, falls belegt). Die Adresse ist `127.0.0.1` — nur lokal.

## Registrieren für Systemstart

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Agenten\Routinen\bus.ps1
```

Erfordert Administrator-Rechte. Danach:

- Aufgabenplanung: `BrainFiles-Bus`
- Trigger: Bei Systemstart
- Aktion: `python Agenten\Bus\bus.py`
- Bei Fehler: Neustart nach 1 Minute, maximal 99 Versuche
- Zeitlimit: unbegrenzt

## Journal

Liegt in `Agenten/Bus/journal/JJJJ-MM-TT.jsonl` — tägliche Rotation, JSONL-Format, 8 Felder je Zeile:

```json
{
  "id": "uuid (eindeutig je Ereignis)",
  "wer": "routine/sicherung oder handel/dauerlauf oder ...",
  "was": "start oder ende",
  "code": "Exitcode (nur bei was=ende, null bei Erfolg)",
  "dauer_s": "Laufdauer in Sekunden (nur bei was=ende, null bei Fehler)",
  "text": "Freitext-Grund (nur bei Fehler, sonst '')",
  "log": "Relativer Pfad zum Protokoll (sonst '')",
  "zeit": "ISO-8601 mit Zeitzone"
}
```

## Tests

```bash
python tests/test_ende_zu_ende.py
```

Führt alle 8 Modultests aus und nimmt die vier Abnahmepunkte ab:

1. Alle Komponenten melden Start und Ende
2. Ein erzwungener Fehler erscheint binnen einer Minute auf dem Handy
3. Ein gestoppter Bus lässt einen Sicherungslauf durchlaufen
4. Die Tagesmeldung listet alle Läufe des Tages

## Abruf und Steuerung (Teilprojekt 2, geliefert am 2026-09-11)

`skillsbot.py` nimmt Nachrichten von Max per Telegram entgegen und reicht sie
per A2A an den lokalen Hermes-Agenten weiter (Port 9900, Agent
hermes-maks-pc, 43 Skills). Einrichtung: Kopf von skillsbot.py
(BotFather -> SKILLSBOT_TOKEN -> TELEGRAM_CHAT_ID -> --probe).
Dauerbetrieb ueber Agenten/Routinen/skillsbot.ps1 (Task
BrainFiles-SkillsBot).

WICHTIG: Der SkillsBot braucht einen EIGENEN Bot. TELEGRAM_TOKEN ist der
Freigaben-Bot von dauerlauf.py/melder.py - zwei Poller an einem Token
verschlucken Order-Freigaben. Deshalb verweigert skillsbot.py den
Dauerbetrieb ohne SKILLSBOT_TOKEN.

## Deutung

Teilprojekt 3. Hier geht das nicht.

## Feste Handelsbefehle (xperp zuerst)

SkillsBot (eigener Token, kein Handels-Poller):
- `/status`: lokale Zustandsdateien, xperp vor Spot; Zeitstempel und Modus.
- `/papierstatus`: Live-Daten werden nicht als Papierpositionen ausgegeben.
- `/prognose [N]`: vorhandene Spot-Marktbeobachtung mit `--kurz`, keine
  Order, kein Berichtschreiben. Ohne N ganzer Markt; N zwischen 1 und 200.
  Zeitlimit 240 Sekunden, danach kleinere Stichprobe anfordern.
- Unbekannte Slashbefehle gehen nicht an A2A; Freitext weiterhin schon.

Handelsbot (dauerlauf.py, einziger Schreiber der Freigabefenster):
- `/freigabe_xperp`: wartende Anfrage samt Grenzen lesen, nichts oeffnen.
- `/ja_xperp STUNDEN`: nur die aktuelle XPERP-Anfrage, 0 < Stunden <= 24.
- `/nein_xperp` und `/stop_xperp`: nur XPERP-Fenster schliessen; Spot bleibt.
- `/papierstatus`: derselbe lokale Papierstatus wie im SkillsBot.
- `/prognose` verweist zum SkillsBot, damit Analyse den Handelszyklus nicht blockiert.

Freigabe ist ein Zeitfenster, keine Einzelorder. Sie hebt keine Wache auf.
Stop schliesst das Fenster fuer neue Einstiege, stellt keine Position glatt
und stoppt nicht den Prozess. Normale SWAPs sind noch nicht vollstaendig
bewacht angebunden; die neuen Befehle aktivieren sie nicht.

Tests: `python -m unittest discover -s Agenten/Bus/tests -p test_handel_befehle.py`
und `python -m unittest discover -s Agenten/Handel/tests` aus der Repo-Wurzel.
Nach Codeaenderungen muessen die jeweiligen Bot-Prozesse neu laden. Einen
Handelsprozess mit offenem Live-Fenster nicht unangekuendigt neu starten.
