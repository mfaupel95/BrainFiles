---
name: hermes-cron-wartung
description: "Use when Loops/Cron im Hermes-Haus pruefen oder einrichten."
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Cron, Loops, Wachen, Gateway, Wartung, Betrieb]
    related_skills: [skill-schleifen, bus-integration, dauerprozess-bewachen, hermes-config-ops, sammelauftrag, telegram-bruecke-diagnose]
---

# Cron und Loops im Hermes-Haus warten

Der Bestand an wiederkehrenden Auftraegen (Wachen, Loops, Routinen) ist ueber
mehrere Profile verteilt und wird von Statuskommandos falsch beschrieben.
Dieses Skill sagt, wo die Wahrheit liegt, wie man den Bestand in einem Durchgang
liest, und welche Fallen beim Einrichten und Reparieren Zeit kosten.

**Bauen** einer neuen Schleife (fuenf-Fragen-Schwelle, vier Muster, Vorlage):
`skill-schleifen`. Dieses Skill ist die Bestands- und Reparaturseite davon.

## When to Use — Wann

- „Loops einrichten“, „das soll stuendlich laufen“, „Routine anlegen“
- „welche Loops laufen ueberhaupt“, „feuert X noch“, „warum kommt keine Meldung“
- ein Auftrag steht auf `blocked_config`, `delivery_failed` oder hat einen
  `failure_streak`
- mehrere Antworten auf eine Nachricht (mehrere Bots bedienen denselben Kanal)

## Erst klaeren: welcher Mechanismus

| | Wann | Wie |
|---|---|---|
| **Hermes-Cron** | Haus-Standard fuer Wachen und Loops, still bei Erfolg | `cronjob_manage` (Profil `jobs.json`) |
| **Windows-Aufgabenplanung** | PowerShell noetig, Admin, Wrapper mit Log und Bus-Meldung | `MaxHirn-*`-Aufgaben, siehe `MaxHirn/Wissen/Routinen.md` |
| **`/loop`** | **Nur** innerhalb einer laufenden Sitzung (Polling waehrend der Arbeit) | sitzungsgebunden: stirbt mit der Sitzung, fuer Bots untauglich |

`hermes loops` gibt es nicht („is not a `hermes` command“). „Loop“ heisst im
Haus **Cron-Auftrag**; wer `/loop` fuer einen Bot einrichtet, baut etwas, das
niemand am Leben haelt.

## Wo die Wahrheit liegt

- Hauptprofil: `Agenten/Hermes/cron/jobs.json` — hier liegen die Wachen
  (`no_agent`), die meisten Eintraege des Hauses.
- Bot-Profile: `Agenten/Hermes/profiles/<name>/cron/jobs.json`.
- Ein Profil ohne `jobs.json` hat null Auftraege; `hermes -p <name> cron list`
  liest denselben Speicher und bestaetigt es je Profil (ein `--profile`-Flag
  gibt es nicht).
- `hermes cron doctor` und `hermes cron status` lesen einen **anderen**
  Speicher: „No active jobs configured“ bzw. „Gateway is not running — cron jobs
  will NOT fire“, waehrend Dutzende feuern. Beleg ist `last_run_at` gegen die
  Uhr und die Datei, nie der Statusbericht.

## Ablauf: Bestand pruefen

1. **Bestand lesen, nicht erfragen.** `scripts/cron-bestand-pruefen.py` laeuft
   ueber alle `jobs.json` und meldet nur Befunde (leere Ausgabe = gesund).
   *Fertig, wenn* die Summen je Profil (gesamt / enabled / `no_agent`) und die
   Befundliste vorliegen. `--alles` zeigt zusaetzlich die gesunden Zeilen.
2. **Befundarten trennen:** `last_status != ok` (Lauf scheiterte) —
   `last_delivery_error` (Lauf ok, **Meldung kam nicht an**: der leiseste
   Ausfall) — `failure_streak` (haelt an) — `next_run_at` in der Vergangenheit
   (Scheduler tickt fuer dieses Profil nicht) — noch nie gelaufen.
3. **Kanalpruefung** bei Zustellbefund: `scripts/cron-bestand-pruefen.py
   --kanaele` zeigt je Profil, ob ein Token gesetzt ist, auf welchen Chat es
   hoert, und wer zuletzt in den Chat gesendet hat. Ursachen und Behebungen:
   `references/gateway-und-zustellung.md`.
4. **Erst den Empfaenger klaeren, dann handeln.** Eine Nachricht in einer
   Gruppe liegt bei JEDEM Profil, das den Chat bedient; die Antwort auf eine
   Bot-Meldung ist damit kein Beweis, welches Profil gemeint ist. Vor dem
   ersten Schreibzugriff feststellen, welcher Bot der Absender war (die
   Antwortzeile in `profiles/<p>/state.db`, Tabelle `messages`, Rolle
   `assistant`) und ob das eigene Profil ueberhaupt zustaendig ist.
   Spalten, Abfragen und Fallen: `references/sitzungsspuren-lesen.md`.
   *Fertig, wenn* Absender und Zustaendigkeit belegt sind.
5. **Aenderung am fremden Profil zurueckgeben, nicht selbst tun.** Ein
   Repo-Bot fasst fremde Profile nicht an (Hausregel). Der Bericht nennt
   Profil, Datei, Schluessel und den fertigen Auftrag — die Ausfuehrung macht
   der Wartungsbot. *Fertig, wenn* der Auftrag ohne Rueckfrage ausfuehrbar ist.
6. **Ueberlappung ausschliessen, bevor du anlegst.** Ein neuer Auftrag, der
   dieselbe Arbeit tut wie ein vorhandener, ist kein doppelter Schutz, sondern
   eine zweite Stelle, an der sie falsch werden kann — und er kostet bei jedem
   Lauf Tokens. Vor `action=create` im Hauptprofil
   (`Agenten/Hermes/cron/jobs.json`) und im eigenen Profil nach Auftraegen
   suchen, deren `script` oder `prompt` dieselbe Quelle anfasst (gleicher
   Dateiname, gleiche Datenbank, gleicher Bericht). Deckt ein vorhandener
   Auftrag das zu 80 % ab: **erweitern, nicht neu anlegen.** *Fertig, wenn* je
   Kandidat „neu“ oder „erweitern“ entschieden und begruendet ist.
7. **Einrichten** (wenn es der eigene Auftrag ist): `cronjob_manage
   action=create` mit `schedule` und selbsttragendem `prompt`. Kann ein Skript
   die Arbeit tun, dann `no_agent=true` + `script` — kostet keine Tokens und
   kann sich nicht verplaudern. *Fertig, wenn* die Liste den Auftrag mit
   `state=scheduled` und gesetztem `next_run_at` zeigt.
8. **Die Nutzlast einmal von Hand fahren, bevor du sie glaubst.** Ruft der
   Auftrag einen anderen Bot (`hermes -p <name> chat -q "..."`), fahre genau
   diesen Aufruf einmal selbst und lies die Antwort: er belegt, dass der Bot
   antwortet, was er liefert und wie lange der Kaltstart dauert (Antwort mit
   echten Daten in unter zehn Sekunden ist normal). Ein Prompt mit einer Zeile,
   die in der bash des Agenten ins Leere laeuft (siehe Fallen), faellt hier auf
   und nicht erst im ersten geplanten Lauf. *Fertig, wenn* eine echte Antwort
   mit Daten vorliegt, nicht nur die Zusage, dass es gehen wird.
9. **Dokumentieren.** Eine Zeile in `MaxHirn/Wissen/Routinen.md` (CRLF!
   byte-genau einsetzen, nie `write_file`/`patch`; danach `git diff --numstat`
   pruefen: 1/1 gewollt, ganze Datei = Alarm). Die Zeile behauptet
   „eingeplant“ erst, wenn der Auftrag existiert **und** einmal gelaufen ist.

## Fallen

- **Doppelte Zustellung durch mehrere Kanal-Profile.** Tragen mehrere Profile
  dasselbe `TELEGRAM_ALLOWED_CHATS` und je ein eigenes Token, sieht **jeder**
  jede Nachricht und antwortet. Auf eine Frage kommen dann fuenf Rueckfragen
  statt einer Antwort. Diagnose: `--kanaele` zaehlt die
  `Sending response ... to <chat>`-Zeilen je `logs/gateway.log`. Behebung: auf
  EINEM Profil stehen lassen, die anderen austragen.
- **`blocked_config` ist kein Lauf-Fehler, sondern ein Zustell-Fehler.** Ein
  Profil ohne Kanalkennung kann nicht zustellen; `deliver: telegram` (bloss die
  Plattform, ohne Chat) loest gar kein Ziel auf. Entweder Kennung ins Profil
  oder `deliver` auf ein aufloesbares Ziel setzen — nur wieder einschalten
  heilt nichts.
- **`no_agent` + `script`: leere Ausgabe sendet nichts** (stiller Erfolg, so
  gewollt). Ein Auftrag, der jeden Lauf eine Zeile meldet, wird nach einer
  Woche ignoriert — dann lieber Befund statt Status.
- **`script` nimmt keine Argumente.** `script: "x.py --nur okx"` scheitert mit
  „Script file not found“; fuer einen gefilterten Aufruf einen Wrapper anlegen.
- **Eine Wache darf nicht ueber den Weg melden, den sie ueberwacht** (Bus,
  ueberwachter Dienst). Sonst schweigt sie mit dem Ausfall.
- **Python nicht per Heredoc oder `-c` starten.** In der MSYS-bash
  verstuemmeln Backslashes und Anfuehrungszeichen den Code: `f.replace('\\','/')`
  endet als `SyntaxError: unterminated string literal`, ein `-c` mit Quotes
  bricht frueher. Skript mit `write_file` in den Scratch-Ordner legen und als
  Datei starten (`python <pfad>`) — das laeuft reproduzierbar.
- **Bevor du „fehlt" oder „ist nicht gesetzt" meldest, die autoritative Quelle
  fragen.** Eine versionierte Datei im Arbeitsbaum wird schnell uebersehen,
  und ein falscher Hinweis kostet mehr Zeit als die Pruefung: erst
  `git ls-files --error-unmatch <pfad>`, dann lesen. Zwei Kandidaten fuer
  dieselbe Sache (Wurzel- vs. Profilpfad) sind kein Widerspruch, sondern eine
  Auswahl — beide nennen.
- **`tasklist` mit EINEM Schraegstrich:** `tasklist /FI "IMAGENAME eq
  python.exe" /FO CSV`. Die in MSYS uebliche Verdopplung (`//FI`) wird als
  ungueltige Option abgelehnt.
- **PowerShell-Zeilen in einem Cron-Prompt laufen ins Leere.** Ein Prompt wird
  vom Agenten in der bash dieses Hauses ausgefuehrt; `Remove-Item Env:X
  -ErrorAction SilentlyContinue` endet dort mit `command not found` (rc 127)
  und wird von der naechsten Anweisung ueberholt — der Auftrag sieht trotzdem
  gesund aus. Umgebungsaufraeumen gehoert in das Skript, das seine Umgebung
  selbst setzt, nicht in den Prompt.
- **`last_status: ok` eines Sammlers sagt nichts ueber seine Quelle.** Ein
  `no_agent`-Sammler meldet den Lauf, nicht die Gesundheit der Datenbank, die er
  fuellt. Ist die Quelle krank (Zeilen ohne `finished_at`, einzelne Schritte
  dauerhaft im Timeout), laeuft der Auftrag weiter auf `ok`, und die Daten
  veralten still. Bei „warum kommen keine neuen Daten“ zuerst die Quelldatenbank
  lesen: offene Zeilen und die letzten Laufzeiten je Schritt.
- **Nie aus einem Zeitplan heraus handeln.** Ein Cron-Lauf legt keinen Schalter
  um, bewegt kein Geld und loescht nichts; Stufe 0/1 bleibt Handarbeit.

## Antwortform (Hausregel)

- Ergebnis zuerst, danach der Beleg; Zahlen aus der Datei, nicht geschaetzt.
- **Eine** begruendete Empfehlung statt einer Optionsliste. Mehrere gleichwertige
  Wege anzubieten ist keine Sorgfalt, sondern eine verschobene Entscheidung.
- Max fuenf sichtbare Punkte je Gruppe, wichtigster zuerst; am Ende genau EINE
  naechste Aktion, unter zwei Minuten machbar.
- Bei fremden Profilen: Zustand melden und den Auftrag formulieren — nicht
  selbst hineinschreiben.

## Lebensdauer

- Nach vier Wochen Bilanz: Meldungen, Eingriffe, Fehlalarme.
- Stilllegen heisst `pause`, nicht `remove` — der Verlauf in `cron/output/` und
  die Zeile in `Routinen.md` belegen, dass die Frage geprueft wurde.
- Hoechstens eine neue Schleife je Woche; ab etwa zwoelf Meldungen pro Woche
  zuerst konsolidieren (gleiche Uhrzeit, ein Bericht statt vier).
