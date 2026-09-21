---
name: skill-schleifen
description: "Use when aus Skills eine Schleife als Routine wird."
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Skills, Selbstverbesserung, Routinen, Cron, Automatik]
    related_skills: [beobachtungslog, sammelauftrag, dauerprozess-bewachen, bus-integration, betriebsrunde, brainfiles-auftrag]
---

# Skill-Schleifen: aus vorhandenen Skills eine Routine bauen

Eine **Schleife** ist eine Kette vorhandener Bausteine (Skills, Skripte) plus ein
Zeitplan plus ein Abbruchkriterium. Dieses Skill beantwortet drei Fragen in
dieser Reihenfolge: **Lohnt es sich ueberhaupt? Wie baue ich sie? Woran merke
ich, dass sie wertlos ist?**

Es baut keine Fachlogik und keine zweite Fassung eines vorhandenen Pruefers.
Wer hier etwas nachbaut, was `optimierungen-finden.py` schon kann, prueft
hinterher nur seine eigene Formel.

## Wann

- „mach daraus eine Routine“, „das soll automatisch laufen“, „lerne das selbst“, „Schleife“, „Loop“
- derselbe Handgriff ist **zum zweiten Mal** von Hand gelaufen (Beleg: zwei Eintraege im Beobachtungslog oder zwei Sitzungen)
- es fehlt eine Wache: ein Dienst laeuft, aber niemand merkt, wenn er ausfaellt
- ein Bericht wird von Hand zusammengesucht, obwohl alle Zahlen maschinell vorliegen

**Nicht dafuer:** eine einzelne Sitzung sammeln (`sammelauftrag`), eine Regel
der Handels-Spuren aendern (`handel-spuren`), einen Dauerprozess starten und
bewachen (`dauerprozess-bewachen`), eine neue `.ps1` an den Bus haengen
(`bus-integration`), Skill-Inhalte pflegen (`beobachtungslog`,
`skill-library-sync`), eine einmalige Sitzungsarbeit — dafuer `brainfiles-auftrag`.

## Schwelle: fuenf Fragen, alle mit ja

1. **Wiederkehr** — derselbe Ausloeser, ohne Menschen, mindestens einmal im
   Monat erwartet. Nicht geplant, sondern **belegt** (zweimal passiert).
2. **Pruefkriterium** — es gibt eine Zeile, an der man in zehn Sekunden sieht,
   dass der Lauf richtig war. Wer kein Pruefkriterium nennen kann, hat keinen
   Kandidaten, sondern eine Hoffnung.
3. **Stiller Erfolg** — der Normalfall **schweigt**. Eine Meldung, die jeden Tag
   kommt, wird nach einer Woche ignoriert; damit ist die Schleife schaedlicher
   als keine (sie frisst Aufmerksamkeit und meldet den Ausfall mit).
4. **Entscheidungsarm** — der Einzelfall braucht keinen Menschen und keine
   Abwaegung. Was Abwaegung braucht („beurteile“, „schlage vor“), darf nur
   **berichten**, nicht handeln.
5. **Kein Eingriff** — rein lesend oder additiv. Nichts Irreversibles:
   kein Loeschen, kein Senden nach draussen, kein Posten, kein Geld, keine
   Massenoperation. Aus einem Zeitplan wird **nie** gehandelt und Stufe 0/1
   (`MaxHirn/Wissen/Schutzregeln.md`) nie automatisiert.

Faellt eine Frage: keine Routine. Stattdessen die Beobachtung ins Log
(`beobachtungslog`) und liegen lassen. Hausregel: **was kein Pruefkommando hat,
darf keine Routine werden** — es wuerde still falsch laufen.

## Vor dem Bauen: Ueberlappung ausschliessen

```bash
ls Agenten/Hermes/cron/output/                     # was schon laeuft
powershell -NoProfile -Command "Get-ScheduledTask -TaskName 'MaxHirn-*' | Select-Object TaskName,State"
```

Dazu die Tabelle in `MaxHirn/Wissen/Routinen.md` und der Skill
`sammelauftrag` (Abschnitt Verfahren, Schritt 1). Deckt eine bestehende Routine
80 % ab: **erweitern, nicht neu anlegen.** Zwei Quellen fuer denselben Bericht
sind kein doppelter Schutz, sondern zwei Stellen, an denen er falsch werden kann.

## Bausteine, die es schon gibt

| Zweck | Baustein |
|---|---|
| uncommittete Arbeit, letzte Laeufe, Aufgabenplanung einsammeln | `Agenten/Hermes/skills/brainfiles/sammelauftrag/scripts/sammeln.py` |
| Skill-Bedarf / „gibt es dafuer schon etwas“ | `Agenten/Werkzeuge/fundus-suche.ps1` |
| Skill-Nutzung (was lohnt, was ist teuer) | `hermes curator usage` ueber `scripts/skill-usage-report.py` |
| Routine- und Prozess-Drift | `Agenten/Hermes/scripts/optimierungen-finden.py` |
| feuern die Cron-Auftraege selbst noch? | `Agenten/Hermes/scripts/automatik-waechter.py` |
| Dienste und Ports | `bus-waechter.py`, `omniroute-waechter.py`, `atlas-watcher.py`, `systemdiagnose` |
| System, Drift, Rechte | `Agenten/Routinen/systempruefung.ps1` |
| Handels-Spuren (Spiegel, Auswertung, Ratschen) | `Handel/spiegelstand.py`, `Handel/auswertung_alle.py`, `Handel/pruefe_ratschen.py` |
| Beobachtungen aus echter Arbeit | `MaxHirn/Wissen/Beobachtungen/log/` |

## Vier Muster — eine aussuchen, nicht mischen

1. **Waechter** — Zustand messen, bei Abweichung eingreifen (Neustart) oder
   melden. Vorbild: `bus-waechter.py`. Kann heilen, muss es aber nicht.
2. **Sammeln → melden** — ein Skript holt Zahlen, die Ausgabe ist die Meldung.
   Vorbilder: `skill-usage-report.py`, `repo-updates-check.py`.
3. **Kette** — Stufe 2 sieht die Ausgabe von Stufe 1 (`context_from`), oder der
   Lauf sieht seine eigene vorherige Ausgabe (`continuity`). Fuer Digest und
   Dedupe: nur die Veraenderung melden.
4. **Drift** — `monitor` laeuft billig, der Agent wird nur bei geaenderter
   Ausgabe geweckt. Ausgabe muss deterministisch sein (kein Zeitstempel),
   sonst sieht jeder Lauf wie eine Aenderung aus.

## Welcher Mechanismus

| | Wann | Wie |
|---|---|---|
| **Skript ohne Modell** | deterministisch, Zahlen vorhanden, still bei Erfolg | `cronjob action=create no_agent=true script=<name>.py deliver='telegram'` |
| **Cron-Auftrag mit Modell** | eine Empfehlung, Formulierung oder Abwaegung ist Teil der Lieferung | `prompt` selbsttragend, `enabled_toolsets` einschraenken, `script` fuer die Vorarbeit |
| **Windows-Aufgabe** | braucht PowerShell/Windows-Kontext, Admin, oder einen Wrapper mit Log und Bus-Meldung | `bus-integration` |

Drei Regeln, die jede Schleife hier einhalten muss:

- **Nichts, was ein Skript kann, als Modelllauf.** Ein `no_agent`-Auftrag kostet
  keine Tokens und kann sich nicht verplaudern.
- **Ein Waechter darf nicht ueber den Weg melden, den er ueberwacht.** Die
  Meldung geht direkt an Telegram (Cron), nicht durch den Bus und nicht durch
  den ueberwachten Dienst. Anlass: der Bus war vier Tage aus und meldete nichts,
  weil niemand die Meldekette selbst bewachte.
- **Zweiter Zutritt bei Totalausfall.** Ein Waechter, der im selben Mechanismus
  laeuft wie das, was er bewacht, schweigt mit. Deshalb ruft die Prueffunktion
  auch der **andere** Mechanismus auf — Vorbild: `automatik-waechter.py`
  (Hermes-Cron) und `optimierungen-finden.py` (Windows-Aufgabe) teilen dieselbe
  Funktion `befunde_holen()`.

## Ablauf

1. **Wiederkehr belegen.** *Fertig, wenn* zwei unabhaengige Belege genannt sind
   (Log-Eintraege, Sitzungen, Journalzeilen) — nicht ein Gefuehl.
2. **Ueberlappung pruefen.** *Fertig, wenn* die vorhandenen Laeufe gelistet und
   je Kandidat „neu“ oder „erweitern“ entschieden ist.
3. **Pruefkriterium in Zeilenform schreiben** — welche Zeile bedeutet was, und
   welche Ausgabe bedeutet „gesund“ (in der Regel: leer). *Fertig, wenn* das
   Kriterium im Kopf des Skripts steht, nicht im Chat.
4. **Fehlerrichtung herstellbar machen.** Das Skript nimmt eine andere
   Eingabedatei an (`--datei` oder eine Umgebungsvariable) und ein
   `--alles` fuer die Zahlen im gesunden Fall. *Fertig, wenn* der Fehlerfall
   ohne Eingriff in die echten Daten erzeugbar ist — sonst wird er nie geprueft.
5. **Prueffunktion und Meldung trennen** — `befunde_holen(datei=None)` gibt eine
   Liste zurueck und ist importierbar; die Textform (`meldung`, `main`) bleibt im
   Skript. *Fertig, wenn* die Funktion ohne `print` benutzbar ist.
6. **Beide Richtungen fahren** (siehe Nachweis). *Fertig, wenn* der gesunde
   Lauf 0 Zeichen ausgibt und der praeparierte Lauf **genau** die erwarteten
   Zeilen zeigt — Fehlalarme zaehlen wie verpasste Treffer.
7. **Einplanen.** `cronjob action=create` mit `no_agent=true`, `script`,
   `schedule`, `deliver='telegram'` (aus der TUI kommt `origin` **nirgends** an),
   bei Bedarf `failure_deliver`. *Fertig, wenn* die Auftragsliste ihn mit
   `state=scheduled` und gesetztem `next_run_at` zeigt.
8. **Einmal echt feuern** (`action='run'`) und den Lauf **nachlesen**
   (`last_run_at`, `last_status`, Datei in `Agenten/Hermes/cron/output/`).
   *Fertig, wenn* der echte Lauf dieselbe Ausgabe liefert wie der Handlauf.
9. **Dokumentieren** — Zeile in `MaxHirn/Wissen/Routinen.md` (Byte-genau,
   CRLF-Rezept in `bus-integration`), und wenn die Schleife Dateien anlegt:
   `.gitignore`-Freigabe plus Gegenprobe `git check-ignore -v <pfad>`.
   Die Zeile behauptet erst dann „eingeplant“, wenn der Auftrag existiert **und**
   einmal gelaufen ist. *Fertig, wenn* eine fremde Sitzung die Schleife in
   `Routinen.md` findet — nicht im Chatverlauf.
10. **Sichern** — nur eigene Pfade, `brainfiles-auftrag`.

## Lebensdauer: abnehmen und stilllegen

- **Abnahmetermin** statt Dauerbetrieb auf Verdacht: nach vier Wochen die
  Bilanz ansehen (Meldungen, Eingriffe, Fehlalarme).
- **Stilllegungskriterien:** keine Meldung ueber viele Laeufe, obwohl der Bedarf
  belegt war (Kriterium falsch, nicht der Dienst gesund) — jede Meldung ohne
  Folge — der Ausloeser ist am Ende immer ein Mensch (dann wieder Auftrag).
- **Stilllegen heisst `pause`, nicht `remove`.** Der Verlauf in
  `cron/output/` und der Eintrag in `Routinen.md` sind der Beleg, dass die Frage
  einmal geprueft wurde.
- **Obergrenze:** hoechstens eine neue Schleife je Woche. Jede kostet
  Aufmerksamkeit, nicht nur Tokens; ab etwa zwoelf Meldungen pro Woche zuerst
  konsolidieren (gleiche Uhrzeit, ein Bericht statt vier).

## Fallen (alle schon getroffen)

- **`hermes cron doctor` ist hier blind.** Es meldet „No active jobs configured“,
  waehrend fuenf Auftraege feuern — es liest einen anderen Speicher. Die
  gefeuerten Auftraege stehen in `Agenten/Hermes/cron/jobs.json`; das ist die
  Quelle, aus der der laufende Scheduler wirklich liest.
- **`hermes cron status` meldet „Gateway is not running — cron jobs will NOT
  fire“, waehrend die Auftraege feuern.** Ein Statuskommando beschreibt nicht
  immer den Prozess (dieselbe Falle wie `projectatlas watch-status`). Beleg ist
  `last_run_at` gegen die Uhr, nicht der Statusbericht.
- **Feldnamen:** `last_run_at`, `next_run_at`, `last_status`, `last_error`,
  `last_fire_error`, `last_delivery_error`, `failure_streak`, `state`. Es gibt
  kein `last_run`; ein `job.get("last_run")` liefert immer `None` und liest sich
  wie „nie gelaufen“.
- **Der leiseste echte Ausfall ist die nicht zugestellte Meldung.** Der Auftrag
  laeuft, `last_status: ok`, und trotzdem kommt nichts an
  (`last_delivery_error`). Wer nur auf Fehler des Laufs sieht, verpasst ihn.
- **„Feuert nicht mehr“ braucht eine Schonfrist.** Erwartete Luecke aus dem
  Zeitplan (2,5-fach + 15 Minuten) — sonst meldet jede ausgeschaltete Nacht und
  jeder verpasste Termin einen Ausfall. Ein Auftrag, der **noch nie** lief, hat
  dagegen keine Ausrede: dort reicht die 1,25-fache Luecke.
- **Einmalauftraege sind keine Schleife.** `kind: once` hat keine erwartete
  Luecke und darf nie einen „feuert nicht mehr“-Befund erzeugen.
- **Bewusst stehen gelassene Zustaende brauchen eine Whitelist**, sonst meldet
  die Schleife jede Woche denselben Satz und wird ignoriert
  (`KNOWN_LEICHEN` in `optimierungen-finden.py`).
- **Aus der TUI liefert `deliver='origin'` nichts.** Cron-Auftraege in einer
  TUI-Sitzung sind lokal; nur ein Plattformziel wie `telegram` kommt an. Keine
  Zusage „du bekommst dann eine Nachricht“, wenn `deliver` nicht umgestellt ist.
- **Ein Test darf nie in einen echten Zielpfad schreiben.** Die Fehlerrichtung
  mit `--datei`/Umgebungsvariable in den Temp-Ordner legen; die Falle aus den
  Spiegel-Tests (Testsuite ueberschrieb die Ausser-Haus-Kopie) kostete
  still eine Bedingung.
- **Zeilenenden.** `MaxHirn/Wissen/Routinen.md` ist CRLF — nicht mit
  `write_file`/`patch` anfassen, sondern byte-genau einsetzen und danach
  `git diff --numstat` pruefen (1/1 = gewollt, ganze Datei = Alarm).
- **Neue Dateien sind unsichtbar**, bis sie in der `.gitignore`-Freigabe
  stehen: `git check-ignore -v <pfad>` und `git ls-files <muster>` als
  Gegenprobe.
- **Nicht am Arbeitsbaum vorbeiarbeiten:** im Mehrsitzungsbetrieb nur die
  eigenen Pfade stagen (`git status` kann Fremdarbeit zeigen, die liegen bleibt).
- **`script` im Cron nimmt KEINE Argumente.** `script: "x.py --nur okx"`
  scheitert mit "Script file not found". Fuer einen gefilterten Aufruf einen
  Wrapper anlegen, der `sys.argv` setzt und das Ziel per
  `importlib.util.spec_from_file_location` laedt (Dateinamen mit Bindestrich
  sind nicht importierbar).
- **OKX-REST antwortet urllib mit 403, curl nicht.** Ohne `User-Agent`-Header
  lehnt `api/v5/*` ab (gefundene Falle beim Bau des okx-trading-bericht).
  Immer `urllib.request.Request(url, headers={"User-Agent": ...})` verwenden.
- **onchainos-CLI (okx-dex-market) liefert read-only ohne Anmeldung:**
  `memepump tokens --chain solana`, `leaderboard list --chain solana
  --time-frame 3 --sort-by 4` und `market index` geben JSON mit `ok:true`
  zurueck, ohne Schluessel. Damit ist ein no_agent-Bericht moeglich, der die
  OKX-DEX-Daten ohne Zugangsdaten holt. Pfad: `C:\Users\faupe\.local\bin\onchainos.exe`.

## Nachweis

Beide Richtungen, je ein Kommando — der Text ist der Beleg, nicht die Absicht:

```bash
python Agenten/Hermes/scripts/<name>.py --alles          # gesund: Zahlen, exit 0
python Agenten/Hermes/scripts/<name>.py --datei <temp>   # praepariert: genau die erwarteten Zeilen
```

Dann der echte Lauf: `cronjob action='run'` und danach `action='list'`
(`last_run_at`, `last_status`) plus die Ausgabedatei in
`Agenten/Hermes/cron/output/<job-id>/`. Eine Schleife ist fertig, wenn
(a) beide Richtungen belegt sind, (b) der Auftrag einmal von selbst gefeuert
hat und (c) die Zeile in `MaxHirn/Wissen/Routinen.md` steht.

Vorlage fuer den Skriptkopf und die Trennung von Prueffunktion und Meldung:
`references/schleife-vorlage.py`.
