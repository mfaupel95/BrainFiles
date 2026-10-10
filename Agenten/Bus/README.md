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
hermes-maks-pc). Einrichtung: Kopf von skillsbot.py
(BotFather -> SKILLSBOT_TOKEN -> TELEGRAM_CHAT_ID -> --probe).
Dauerbetrieb ueber Agenten/Routinen/skillsbot.ps1 (Task
BrainFiles-SkillsBot).

WICHTIG: Der SkillsBot braucht einen EIGENEN Bot. TELEGRAM_TOKEN ist der
Freigaben-Bot von dauerlauf.py/melder.py - zwei Poller an einem Token
verschlucken Order-Freigaben. Deshalb verweigert skillsbot.py den
Dauerbetrieb ohne SKILLSBOT_TOKEN.

## Deutung

Teilprojekt 3. Hier geht das nicht.

## Feste Handelsbefehle

Der Text aller LESENDEN Handelsbefehle steht seit 15.09.2026 in
`Agenten/Handel/befehle.py` - EINE Quelle fuer beide Bots. Der Handelsbot
sendet sie als HTML (`melder`, parse_mode=HTML), der SkillsBot als Klartext
(`handel_befehle.klartext`). Eine zweite Fassung waere eine zweite Wahrheit:
der Handelsbot zeigte dann etwas anderes als der SkillsBot.

In beiden Bots:
- `/lage`: JETZT - offene Positionen je Spur, Live-Tore, offene Freigaben,
  Kopie ausser Haus. Bis 15.09.2026 war `/lage` derselbe Bericht wie
  `/bericht`, nur ohne Rangliste - zwei Befehle, eine Auskunft.
- `/bericht`: der volle Tagesbericht (Spuren, Wachen, Bilanzen, Rangliste).
- `/spuren`: alle Spur-Namen. `/spur NAME`: eine Spur in der Tiefe -
  Positionen mit Kurs und Stop-Abstand, Wachen und Ratsche, Journal,
  letzte Ablehnung.
- `/strategien`: die Bilanz aller Spuren nebeneinander, gruppiert nach
  Strategie (Kontrakt, Spot, Feed, Grid, Indikator), je Spur aus ihrer
  zustaendigen Auswertung. Unter 8 Runden steht ein `*` (Befund, keine
  Messung).
- `/indikatoren`: die vier Indikator-Spuren (macd_mtf, squeeze, supertrend,
  wavetrend) - Einstiege, Ausstiege, Ausstiegsgruende, offene Positionen.
- `/markt`: BTC/ETH/SOL - Kurs, 24 h, ATR(1 h), Abstand zum SMA50.
  Beobachtung, keine Order und keine Prognose.
- `/status` (SkillsBot): gespeicherter Dateistand aller Spuren.
  `/papierstatus`: Live-Daten werden nie als Papierpositionen ausgegeben.
- `/prognose [N]` (SkillsBot, bis 240 s): Marktbeobachtung ueber alle
  Spot-Paare, beide Richtungen, keine Order, kein Berichtschreiben. Im
  Handelsbot verweist der Befehl hierher, damit die Analyse den Handelszyklus
  nicht blockiert. Ohne N ganzer Markt; N zwischen 1 und 200.
- `/model` (SkillsBot): Modell, Endpunkt und Fallback-Kette, auf denen der Bot
  laeuft - rein lesend aus der Hermes-config. Der Bot hat kein eigenes Modell;
  gewechselt wird in `Agenten/Hermes/config.yaml`.
- `/skills [SUCHE]` (SkillsBot): die geladenen Skills, nach Gruppen gefiltert.
- `/skill NAME` (SkillsBot): ein Skill im Volltext - lesen.
- `/run NAME [Auftrag]` (SkillsBot, bis 5 min): einen Skill **ausfuehren** -
  der Bot schickt per A2A den Auftrag "Fuehre den Skill NAME aus" an Hermes und
  gibt dessen Antwort zurueck. Ausgefuehrt wird nur, was im Katalog steht UND
  ladbar ist; ein Teiltreffer muss eindeutig sein. Unbekannter Name, Tippfehler
  oder ein Skill eines fremden Systems enden OHNE A2A-Aufruf mit Begruendung -
  sonst liefe irgendein Skill, und niemand erfuehre welcher. Vorher kommt eine
  Zwischenmeldung ("Fuehre X aus ..."), weil eine Ausfuehrung dauern darf.
- Unbekannte Slashbefehle gehen nicht an A2A; Freitext weiterhin schon.

Nur Handelsbot (dauerlauf.py, einziger Schreiber der Freigabefenster):
- `/freigabe_xperp`: wartende Anfrage samt Grenzen lesen, nichts oeffnen.
- `/ja_xperp STUNDEN`: nur die aktuelle XPERP-Anfrage, 0 < Stunden <= 24.
- `/nein_xperp` und `/stop_xperp`: nur XPERP-Fenster schliessen; Spot bleibt.
- `/scan`, `/hilfe`, `/pause`, `/weiter`.

Freigabe ist ein Zeitfenster, keine Einzelorder. Sie hebt keine Wache auf.
Stop schliesst das Fenster fuer neue Einstiege, stellt keine Position glatt
und stoppt nicht den Prozess. Die SWAP-Spur ist seit dem 12.09.2026
live-faehig (nach XPERP-Muster, eigene Freigabekette); sie ist derzeit ueber
`handel_erlaubt=false` und die offene Freigabe GESPERRT, nicht stillgelegt.
Ob eine Spur live kann, wird aus ihrer `wachen.json` gelesen und nicht im
Code behauptet - `/lage` und `/status` zeigen den Stand.

Tests: `python -m unittest discover -s Agenten/Bus/tests -p test_handel_befehle.py`
und `python -m unittest discover -s Agenten/Handel/tests -t Agenten/Handel/tests`
aus der Repo-Wurzel - Hermes-Sitzungen starten in `Agenten/Hermes`, also vorher
`cd "$HERMES_HOME/../.."`. Nach Codeaenderungen muessen die jeweiligen Bot-Prozesse
neu laden. Einen Handelsprozess mit offenem Live-Fenster nicht unangekuendigt
neu starten.

## Nachrichtentyp "signal" (Fremd-Werkzeuge)

`fremd_signal.melden_signal(wer, signal)` schickt ein Signal durch das Tor `Handel/fremd_tor.py` (Schema + `fremd_signale/wachen.json`, Tor ist ab Werk zu) und schreibt es als `was="signal"` (durchgelassen) oder `was="signal_verworfen"` (Grund im Text) ins Journal. Beide bleiben fuer den Sprecher still. Ausgefuehrt wird nichts; das wachen.json-Gate in Handel/ entscheidet. Test: `python tests/test_fremd_signal.py`.

`adapter_itb.py` uebersetzt die letzte Zeile der `signals.csv` von intelligent-trading-bot (kaufen = long, verkaufen = flat) und meldet sie ueber `fremd_signal` (also durchs Tor); je Kerze hoechstens einmal, ts_utc = Kerzenschluss. Test: `python tests/test_adapter_itb.py`.
