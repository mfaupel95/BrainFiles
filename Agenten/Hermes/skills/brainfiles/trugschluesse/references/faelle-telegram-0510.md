# Belegte Faelle — 05.10.2026, zweite Haelfte (Telegram-Bruecke)

Eine Sitzung, in der die **Diagnose** stimmte und trotzdem drei Faelle entstanden —
zwei davon in meinem eigenen Werkzeug, einer in meiner Abschlussmeldung. Jeder
Fall: **Behauptung** — **wie sie entstand** — **wie sie auffiel** — **Beleg**.

Der Telegram-Befund selbst gehoert in `telegram-bruecke-diagnose` (Skill-Text).
Hier steht, was **ueber** die Diagnose gilt.

## Der Satz dieser Haelfte

> *Eine Schleife, die einen Zustand nicht repariert, sieht wie Aktivitaet aus.*
> 41 Reconnect-Versuche alle 300 s — und kein einziger hat den Prozesszustand
> angefasst.

## Der Befund im Haus

### 1. `adapter_unavailable` bei gruenem Paket, gruener Pruefung, geladener Registry
- Behauptung (der Gateway-Status): `telegram` ist `retrying`,
  `error_code: adapter_unavailable`, `needs_attention: true`.
- Was ich zuerst vermutete, jeweils mit Beleg **widerlegt**:
  - *Paket fehlt*: `tools/python-3.14.7…/python.exe -c "import telegram"` →
    `telegram 22.8` aus dem gestagten venv. Der `site-packages`-Ordner dieses
    Python enthaelt nur `pip` — die Verzeichnisliste erzeugt den Fehlalarm, der
    Import nicht.
  - *Credentials falsch*: Token in `.env` (46 Zeichen) vorhanden, kein
    User-Store-Eintrag — richtig und harmlos. Ein echter Credential-Fehler zeigt
    sich als `failed to connect` mit Telegram-HTTP-Fehler, nicht als
    `adapter_unavailable`.
  - *Plugins nicht geladen*: Eine Probe mit exakt dem Bootstrap-Weg
    (`hermes_bootstrap` → `discover_plugins()` → `platform_registry`)
    registriert `telegram` fehlerfrei; `check_fn` und `ensure_deps_fn` liefern
    beide `True`.
- Warum es trotzdem auftrat: **nicht belegt.** `run_startup.py:1213-1234` ruft
  `_create_adapter`, bekommt `None`, schreibt `adapter_unavailable` und stellt
  den Eintrag in die Reconnect-Warteschlange. Der Watcher versucht es alle 300 s
  weiter — im **selben** Prozess, dessen Zustand kaputt ist.
- Heilung: kontrollierter Neustart ueber die geplante Aufgabe. Beleg danach:
  `✓ telegram connected` und `[Telegram] Telegram polling confirmed healthy:
  getUpdates progressing (generation 1)` bei `code_version 0.21.5`; eine echte
  Zustellung kam mit `message_id 10888` an.
- **Regel: „Paket fehlt" ist die teuerste Nicht-Ursache, weil sie plausibel
  klingt.** Die leere `site-packages`-Liste des `tools`-Python sieht nach dem
  Befund aus und ist es nicht — die Fremdpakete kommen aus
  `installs/<hash>/environments/<id>/venv/Lib/site-packages` ueber
  `pm/environments.py::activate_dependencies`.
- **Regel: eine Reconnect-Schleife ist kein Reparaturversuch.** 41 Versuche in
  5 Stunden, alle im selben Prozess. Die Frage ist nie „was loest die Schleife
  aus", sondern „was repariert sie" — hier: nichts.

### 2. Der Prozess-Doppelstart als Nebenbefund
- Beobachtung: `logs/gateway.log` meldet nach dem Neustart
  `Previous gateway life (pid=24872 …) exited UNCLEANLY (… a pkill/taskkill of
  the host interpreter image)`.
- Das war **meine eigene** Beendigung, kein unabhaengiger Crash. Als zweiter
  Befund gefuehrt haette es den Bericht um eine erfundene Ursache erweitert.
- **Regel: eine Abbruchmeldung, die die eigene Handlung beschreibt, ist kein
  Befund.** Sie wird als Nebenwirkung benannt, nicht in die Ursachenliste.

### 3. Der Dauer-Fehlalarm daneben
`hermes_cli/observability/shared_metrics.py:176` ruft
`path.mkdir(parents=True, exist_ok=True, mode=mode)` auf ein Pfad, der als
**Datei** existiert → `FileExistsError: [WinError 183]` im Sekundentakt. Sichtbar
in `errors.log` alle 20 Sekunden.

- Warum hier gelistet: dieser Fehler steht im **gleichen** Log wie die Diagnose
  und faellt bei jeder Durchsicht auf. Er hat mit keinem Plattform-Adapter zu
  tun. Ungeprueft mitgenommen haette er das Bild verfaelscht.
- **Regel: ein Fehler im selben Log ist nicht Teil des Befunds, den man sucht.**
  Erst pruefen, ob er denselben Gegenstand betrifft — sonst als getrennten,
  unerklaerten Fehler fuehren.

## Fehler in meinem Werkzeug

### 4. Ein gruener Kanal verdeckt einen toten
- Behauptung (von mir): „mindestens eine Anbindung lebt", Exit 0.
- Entstehung: Das Urteil war `any()` ueber drei Anbindungen. Im `gateway_state`
  gibt es zwei Telegram-Eintraege — `telegram` (Hauptbot, `retrying`) und
  `bots:telegram` (verbunden). Der verbundene Eintrag machte das Gesamturteil
  gruen, waehrend der tote nur in einer Detailzeile stand.
- Auffiel: Die Gegenprobe mit genau dieser Besetzung lieferte **Exit 0**. Der
  Einzelauszug war richtig, die **Aggregation** beantwortete eine andere Frage
  als die gestellte.
- Beleg: Nach dem Umbau meldet derselbe Aufbau `1 Anbindung(en) nicht gesund:
  Gateway telegram`, Exit 1. Die Messwerte darueber bleiben unveraendert.
- **Regel: das Urteil traegt die Frage, die gestellt wurde.** „Laeuft es
  ueberhaupt" und „laeuft jede Anbindung" sind zwei Fragen. Fuer die weiche
  gehoert der Name des toten Eintrags in die **Antwortzeile**, nicht in eine
  Detailzeile.

### 5. Die Gegenprobe pruefte gegen nichts (MSYS-Pfad)
- Behauptung (von mir): die Attrappe belege „keine Anbindung lebt".
- Entstehung: Die Attrappe lag unter `$TMPDIR` — ein MSYS-Pfad. Das Werkzeug
  laeuft als native Windows-Python und bildet ihn nicht ab. Die Datei wurde nie
  gefunden, `os.path.isfile` lieferte `False`, und das Werkzeug meldete
  **ehrlich** `gateway_state.json fehlt`.
- Auffiel: Der Fehlertext war richtig und meine Deutung falsch. „Datei fehlt"
  bedeutet: du hast die falsche Datei gesucht. Nicht: die Datei fehlt.
- Beleg: Derselbe Aufbau mit `C:/…`-Pfaden lieferte die vollstaendige Tabelle.
- **Regel: jeder Attrappenlauf braucht den Pfad, den das Werkzeug aufloest —
  nicht den Pfad, unter dem die Attrappe liegt.** Unter Windows gegen `C:`.

## Fehler in meiner Abschlussmeldung

### 6. „Ursache gefunden" waere eine erfundene Tatsache gewesen
- Behauptung (nahezu): der Gateway habe den Adapter wegen X nicht gebaut.
- Tatsache: Drei Hypothesen widerlegt, die Ursache offen. Die Meldung nannte
  das getrennt: heilbar durch Neustart, Grund **nicht belegt**, als offenes
  Feld weitergegeben.
- **Regel: die Belegpflicht gilt fuer die Erklärung genauso wie fuer den
  Zustand.** Wer den Zustand messen kann und die Ursache nicht, sagt das.

### 7. Der Lint-Hinweis als Fehlermeldung
- Beobachtung: `skill_manage` meldete `author 'Hermes' should be 'Hermes Agent'
  (proper caps)` — bei gleichzeitigem Vorliegen von `Hermes Agent` im Feld.
- Entschieden: Der Wert ist `Hermes` (Hausregel und HARDLINE-Standard), die
  Warnung ist konventionsfehlerlich. Korrigiert, nicht befolgt.
- **Regel: eine Automatik, die einer verschriftlichten Regel widerspricht, wird
  benannt und ueberstimmt.** Nicht die Regel aufweichen.

## Was daraus als Regel bleibt

1. **Eine Schleife, die nichts repariert, sieht wie Aktivitaet aus.** Die Frage
   lautet „was repariert sie", nicht „was loest sie aus".
2. **„Paket fehlt" ist die teuerste Nicht-Ursache.** Die leere
   `site-packages`-Liste des `tools`-Python sieht nach dem Befund aus; der
   Import beweist das Gegenteil.
3. **Das Urteil traegt die gestellte Frage.** Weiche Frage → Name des toten
   Eintrags in die Antwortzeile.
4. **„Datei fehlt" heisst: du suchst die falsche Datei.** Gegenlauf-Pfade auf
   Windows mit `C:` bauen.
5. **Eine Abbruchmeldung ueber die eigene Handlung ist kein Befund.**
6. **Die Belegpflicht gilt fuer die Erklaerung genauso wie fuer den Zustand.**