# Automatik: Skills, die von alleine laufen und reagieren

Version 1.0.0 - 20.09.2026 - Kanban t_f7937187
Vorgaenger: t_3d28119b (Spezifikation), t_9f7db046 (Engine), t_f682e5c1 (Reaktion)

Diese Datei ist die Betriebsanleitung der Gesamtanlage. Die beiden Haelften
haben eigene, ausfuehrlichere Dokumente; dort steht das Innenleben:

    <Engine>/BETRIEB.md      Trigger, Registry, Wache, Sicherheitsregeln
    <Reaktion>/README.md     Befunde, Kanaele, Eskalation, reaktionen.yaml

Hier steht, wie beide zusammen betrieben werden - und was zwischen ihnen
passiert, denn genau dort war der Bruch.


## 1. Die drei Teile in einem Bild

    Aussenwelt              Engine (t_9f7db046)          Kopplung (hier)
    ----------              --------------------          ---------------
    Datei geaendert  --\
    Zeit/Cron        ---\   1. Quelle sieht Ereignis
    Board-Ereignis   ----+->2. Steuerung entscheidet
    Nachricht        ---/      (Modus, Rate-Limit, Sperre,
    Vorlauf-Ergebnis --/        Bestaetigung)
                            3. Lauf unter der Wache
                            4. eine Zeile in laeufe.jsonl  --> liest jede
                                                                neue Zeile
                                                                   |
    Telegram  <-------------------------------------------------+  v
    Board-Kommentar <-----------------------------------------+ Reaktionsschicht
    Memory-Notiz  <-------------------------------------------+ (t_f682e5c1)
    Log       <-----------------------------------------------+  |
                                                                 |
                            zustand.db  <-- Sperre  <-- sperren.json
                            steuerung   <-- Nachlauf <-- nachlauf.jsonl

Die Rollenteilung ist der Kern und wird nirgends gebrochen:

    Engine     darf STARTEN, meldet nichts.
    Reaktion   darf MELDEN und MERKEN, startet nichts.
    Kopplung   traegt zwischen beiden, startet nichts selbst.

Ein faelliger Nachlauf wird der Engine als gewoehnlicher Ausloeser vorgelegt;
sie wendet ihre eigenen Regeln an (Modus, Rate-Limit, Dauersperre,
Bestaetigungspflicht). Es gibt also genau EINE Stelle, die ueber das Starten
entscheidet - sonst haette man zwei Systeme mit zwei Meinungen und keinem
gemeinsamen Rate-Limit.


## 2. Schnellstart

    cd <Kopplungs-Workspace>          (dieser Ordner)

    python pruefen.py                 alle drei Teile testen (45 Pruefungen)
    python -m automatik stand         wo steht die Anlage gerade
    python -m automatik durchgang --probe   entscheiden, nichts bewirken
    python -m automatik durchgang     Normalbetrieb: lesen, melden, zurueckgeben
    python -m automatik nachholen     nur Sperren und faellige Nachlaeufe

Die Engine wird weiterhin aus ihrem eigenen Workspace bedient:

    cd <Engine-Workspace>
    python -m engine tick             Quellen fragen, Treffer abarbeiten
    python -m engine log -n 20        letzte Laeufe
    python -m engine antwort <id> ja  offene Bestaetigung freigeben
    python -m engine entsperren <id>  Dauersperre aufheben

Der volle Takt ist immer `engine tick` gefolgt von `automatik durchgang`.
Reihenfolge ist Absicht: der Tick schreibt Lauf-Zeilen, der Durchgang
beantwortet sie. Beides sind kurze Prozesse ohne Speicherzustand - derselbe
Grund wie in BETRIEB.md (der Rechner geht schlagartig aus, Kernel-Power 41).

Unter git-bash NICHT `$PWD` fuer Umgebungsvariablen verwenden: MSYS liefert
`/c/Users/...`, Python macht daraus `C:\c\Users\...`, und die Anlage legt ihren
Zustand in einem Streuordner ab. Immer nativ mit Vorwaertsschraegen setzen
(`C:/Users/faupe/...`).


## 3. Wo was liegt

    automatik/pfade.py      alle Pfade, jeder ueber eine Variable umstellbar
    automatik/kopplung.py   Hinweg (Log -> Reaktion), Rueckweg (Sperre/Nachlauf)
    automatik/__main__.py   CLI
    tests/ende_zu_ende.py   6 Proben ueber die ganze Kette
    pruefen.py              startet alle drei Testreihen in fester Reihenfolge
    arbeit/kopplung.json    Marken dieser Schicht (wie weit gelesen)
    arbeit/kopplung-log.jsonl   was jeder Durchgang getan hat

Umgebungsvariablen dieser Schicht:

    HERMES_AUTOMATIK_ENGINE          Workspace der Engine
    HERMES_AUTOMATIK_REAKTION        Workspace der Reaktionsschicht
    HERMES_AUTOMATIK_ABLAGE          Zustandsdateien der Reaktionsschicht
    HERMES_AUTOMATIK_REAKTIONSKONFIG reaktionen.yaml
    HERMES_AUTOMATIK_KOPPLUNG        Arbeitsordner dieser Schicht
    HERMES_AUTOMATIK_BASIS           Arbeitsordner der Engine   (wie Engine)
    HERMES_AUTOMATIK_REGISTRY        Registry, die gefahren wird (wie Engine)

Die letzten beiden heissen absichtlich wie bei der Engine: die Kopplung fuehrt
keinen zweiten Zustand ein. Wer den Tick von Hand startet und danach den
Durchgang, arbeitet garantiert auf demselben Log.

Die Kopplung merkt sich nur, WIE WEIT sie gelesen hat (Zeilenzahl, nicht
Inhalt). Das Log wird nur angehaengt, nie umgeschrieben - darum genuegt die
Zahl, und ein Rechner, der mitten im Schreiben ausgeht, verliert hoechstens die
letzte Zeile, nicht die Marke.


## 4. Einen neuen Trigger-Skill hinzufuegen

Fuenf Schritte. Schritt 3 und 4 sind die, die man gerne ueberspringt und dann
in einer Woche sucht.

### Schritt 1: Skill oder Skript bereitstellen

    skill_art: skript   Python-Datei unter Agenten/Hermes/scripts (oder in
                        HERMES_AUTOMATIK_SKRIPTPFADE). Laeuft unter der Wache,
                        die Grenze ist hier echt.
    skill_art: skill    SKILL.md, also ein Agentenlauf. Die Wache greift dort
                        NICHT - der Weg ist gesperrt und braucht
                        HERMES_AUTOMATIK_SKILL_START=1. Standard bleibt: nein.

Ein Skript nimmt seine Parameter als `--flagge wert`; Booleans folgen
store_true (`true` wird zur Flagge, `false` laesst sie weg). Es schreibt sein
Ergebnis nach stdout - diese Ausgabe landet im Log und ist spaeter der Text,
an dem die Reaktionsschicht "hat sich etwas geaendert" erkennt.

### Schritt 2: Regel in die Registry

In `<Engine>/betrieb/registry.yaml` unter `regeln:` anhaengen. Pflichtfelder
und erlaubte Werte stehen in `spez/registry.schema.json`; `spez/registry.example.yaml`
hat ein Beispiel je Trigger-Typ. Das Geruest:

    - id: mein-trigger                 eindeutig, kleingeschrieben
      beschreibung: >
        Warum diese Regel existiert - ein Satz, kein Absatz.
      skill: scripts/meins.py
      skill_art: skript
      trigger:
        typ: datei                     datei | zeit | board_event | nachricht | skill_ergebnis
        prioritaet: 20                 kleiner = frueher
        bedingungen:
          pfad_muster: ["Wissen/**/*.md"]
          aktion: modified
          mindestabstand_s: 120        entprellt Editor und git-Wechsel
      parameter: {}
      erlaubte_aktionen: [lesen, bericht_schreiben]
      schreibpfade: ["Agenten/Hermes/kanban/workspaces/.../bericht.json"]
      modus: dry_run                   IMMER so anfangen
      timeout_s: 180
      rate_limit: {max_laeufe: 12, fenster_s: 86400, cooldown_s: 120}
      abbruch: {bei_fehlerstreak: 3}

`erlaubte_aktionen` und `schreibpfade` sind keine Bitte an das Modell, sondern
eine Grenze im Kindprozess: was fehlt, wird beim Versuch mit Exit 97
abgebrochen. Lieber zu eng beginnen - eine zu enge Regel faellt beim ersten
Probelauf auf, eine zu weite erst, wenn etwas kaputt ist.

### Schritt 3: Validator laufen lassen

    cd <Engine-Workspace>
    python spez/scripts/registry_pruefen.py betrieb/registry.yaml

Der Validator ist die einzige Implementierung der Sicherheitsregeln S1-S8. Die
Engine prueft nichts selbst nach - sie ruft ihn. Eine Registry mit Befund wird
komplett abgelehnt, nicht teilweise geladen: eine halb geladene Regelmenge ist
die gefaehrlichste Zwischenlage.

### Schritt 4: Reaktion festlegen

In `<Reaktion>/reaktionen.yaml` unter `regeln:` mit derselben `id` eintragen.
Ohne Eintrag gelten die `defaults` - das ist absichtlich der leiseste Weg
(nur Log), aber meist nicht das, was man will:

    mein-trigger:
      kanal: log+telegram        log | board | telegram | log+board | log+telegram | alle
      melde_erfolg: bei_aenderung   nie | immer | bei_aenderung
      eskalation:
        wiederholungen: 1        0..5; die Schicht merkt vor, startet nicht selbst
        wiederhol_abstand_s: 300
        danach: melden           melden | board_blocken | regel_sperren | still

Pruefen:

    cd <Reaktion>
    python reaktion.py --konfig-pruefen --konfig reaktionen.yaml

`melde_erfolg: bei_aenderung` ist die richtige Voreinstellung fuer alles, was
oft laeuft: gemeldet wird nur, wenn sich die Ausgabe gegenueber dem letzten
Erfolg geaendert hat. Sonst gewoehnt man sich das Wegwischen an, und dann
uebersieht man die eine Meldung, die zaehlt.

### Schritt 5: Trocken beobachten, dann scharf stellen

    cd <Engine-Workspace>   && python -m engine --nur-lesen tick
    cd <Kopplungs-Workspace> && python -m automatik durchgang --probe

`--nur-lesen` erzwingt dry_run fuer diesen Aufruf, auch wenn Regeln auto sagen;
`--probe` entscheidet vollstaendig, meldet nichts und verbraucht keine Marke.
Beides zusammen zeigt den kompletten Weg ohne jede Wirkung.

Erst wenn zwei, drei Probelaeufe das Erwartete zeigen: `modus: auto` setzen.


## 5. Sicherheitsregeln, die nicht verhandelbar sind

1. Neue Regeln beginnen auf `dry_run`. Die Registry-Defaults stehen deshalb
   auf dry_run - eine unvollstaendige Regel wirkt nicht.
2. Nur Nebenwirkungsklasse `none` oder `local` darf `auto`. Alles darueber
   (geld, destruktiv, extern) braucht `bestaetigung`. Der Validator setzt das
   durch; das Inventar (`spez/inventar.md`) sagt, welche Klasse ein Skill hat.
3. `skill_art: skill` bleibt gesperrt. Ein Agentenlauf laesst sich von innen
   nicht bewachen. Freigabe nur bewusst, nur mit einem Menschen am Rechner.
4. Eine Grenzverletzung wird nie wiederholt. Sie bedeutet, dass ein Lauf etwas
   getan hat, was die Registry nicht erlaubt - das ist schwerer als ein
   Fehlschlag und wird nicht durch einen zweiten Versuch geheilt, sondern
   gesperrt.
5. Der Vault MaxHirn wird von keiner Automatik beschrieben. Der Memory-Kanal
   schreibt ins basic-memory-Projekt, nicht in den Vault.
6. Nichts wird nachgeholt. Marken werden gesetzt, sobald ein Ereignis gesehen
   wurde - nicht erst nach erfolgreichem Lauf. Nach einem Stromausfall startet
   also kein Stapel nachgeholter Automatik. Faellige Nachlaeufe aelter als eine
   Stunde verfallen ebenfalls.
7. Ein Automatiksystem, das seinen eigenen Ausfall verschweigt, ist schlimmer
   als keines. Darum: kaputte Registry -> die Kopplung meldet trotzdem;
   unlesbare Lauf-Zeile -> Fehler im Bericht, aber die naechste Zeile wird
   beantwortet; stummer Kanal -> steht als `gescheiterte_kanaele` im Protokoll.


## 6. Belegter Ende-zu-Ende-Lauf (20.09.2026)

Testreihe, ein Befehl, reproduzierbar:

    python pruefen.py

    gruen  Engine (t_9f7db046)                   16.0s  28 passed
    gruen  Reaktionsschicht (t_f682e5c1)          0.8s  alle Tests gruen (11)
    gruen  Kopplung Ende-zu-Ende (t_f7937187)     4.1s   6 passed

    alles gruen (3 Laeufe)

Die sechs E2E-Proben (tests/ende_zu_ende.py) fahren jeweils eine eigene Welt
(eigenes tmp_path, eigene Zustands-DB, eigene Registry, Attrappen statt Board
und Telegram) und belegen:

    1. Datei geaendert -> Skript lief wirklich -> Erfolg gemeldet -> Memory
       geschrieben; der zweite Durchgang meldet nichts mehr (Marke haelt).
    2. Fehlschlag -> vorgemerkt -> nach Faelligkeit von der Engine neu
       gestartet, sichtbar als eigene Log-Zeile "ausgeloest_durch: nachlauf:".
    3. Grenzverletzung -> Wache bricht ab (Exit 97, Zieldatei existiert nicht)
       -> Regel in der Engine gesperrt -> naechster Lauf uebersprungen.
    4. Uebersprungener Lauf bleibt still (nur Log, keine Meldung).
    5. --probe entscheidet alles, bewirkt nichts und verbraucht keine Marke.
    6. Kaputte und unvollstaendige Log-Zeilen halten die Kopplung nicht an.

Echter Lauf gegen den Betrieb, ohne Attrappen:

    cd <Engine>    && python -m engine lauf inventar-nach-skill-aenderung
      -> erfolg, 624 ms, Exit 0, "52 Skills; none=20, local=6, extern=16,
         geld=6, destruktiv=4", aktionen_genutzt: [datei_schreiben]

    cd <Kopplung>  && python -m automatik durchgang
      -> Kopplung: 1 neue Lauf-Zeile(n), 1 gemeldet
         inventar-nach-skill-aenderung -> erfolg via log+telegram

    Belege in <Reaktion>/reaktion-log.jsonl:
         "kanaele": ["log","telegram"],
         "belege": {"telegram": [true,"weg=bus"],
                    "memory":   [true,"\"operation\":\"append\",\"fileCreated\":true"]}

Das ist der Nachweis der Akzeptanzkriterien: Trigger -> Skill lief automatisch
-> Reaktion ausgefuehrt -> Log- UND Memory-Eintrag vorhanden.

Der sicherheitskritische Pfad ebenfalls echt belegt, nicht nur im Test. Eine
echte Verstoss-Zeile (die Wache brach `inventar.py` ab, weil der Lauf ohne
gesetzte Umgebungsvariablen ausserhalb seiner schreibpfade schreiben wollte)
lief durch einen Durchgang mit eigenem Arbeitsordner:

    python -m automatik durchgang
      -> inventar-nach-skill-aenderung -> grenzverletzung via board+log+telegram [gesperrt]
         Kanal versagt: board   (kein task_id in der Lauf-Zeile - korrekt gemeldet)
         Sperre uebertragen: GRENZE VERLETZT ... nutzte datei_schreiben
                             .../spez/inventar.json, erlaubt war lesen,
                             bericht_schreiben, datei_schreiben
    python -m automatik stand
      -> In der Engine gesperrt: inventar-nach-skill-aenderung

Die Stolperfalle dahinter gehoert zum Betriebswissen: `python -m engine lauf
<id>` OHNE gesetzte HERMES_AUTOMATIK_BASIS/_REGISTRY nimmt die Standardpfade
(`<Engine>/arbeit`, `spez/registry.example.yaml`). Die Beispiel-Registry zeigt
mit ihren schreibpfaden auf den Spez-Workspace t_3d28119b - der Lauf schreibt
aber nach t_9f7db046 und wird deshalb voellig zu Recht von der Wache
abgebrochen. Immer beide Variablen setzen (Abschnitt 2), sonst entsteht
nebenbei ein zweiter Zustandsordner mit eigener zustand.db.

### Drei Integrationsfehler, die dieser Lauf gefunden hat

Sie stehen hier, weil sie beide Haelften einzeln gruen gelassen haetten:

1. `ergebnis: verstoss` fehlte in der Vokabeltabelle der Reaktionsschicht
   (`reaktion.py`, ENGINE_BEFUND). Unbekanntes gilt dort als "fehler" - ein
   von der Wache abgebrochener Lauf waere also WIEDERHOLT statt gesperrt
   worden. Der uebliche Erkennungsweg greift hier nicht: bei einem Abbruch ist
   `aktionen_genutzt` leer, der Vergleich genutzte/erlaubte Aktionen schlaegt
   nicht an. Ebenso ergaenzt: `timeout` (-> fehler) und `abgelehnt` (->
   uebersprungen; ein Nein ist kein Grund zur Eskalation).
   Festgehalten in test_reaktion.py, Test 11.
2. `durchgang --probe` schrieb seine Marken fort. Die geprueften Zeilen galten
   danach als beantwortet, und der naechste echte Durchgang haette sie nie
   gemeldet - eine Probe, die Meldungen verschluckt.
   Festgehalten in tests/ende_zu_ende.py, test_probe_bewirkt_nichts.
3. `kommando` und `verstoesse` galten als Drift. Die Engine schreibt beide bei
   echten Laeufen mit; sie stehen jetzt in KANNFELDER, damit die Driftwarnung
   scharf bleibt statt abgeschaltet zu werden.


## 7. In den Takt nehmen

Der Cron-Auftrag muss BEIDE Schritte machen. Ein Tick ohne Durchgang laeuft
still ins Log, und niemand erfaehrt davon.

    1. <Engine>/betrieb/automatik-tick.py nach
       Agenten/Hermes/scripts/automatik-tick.py kopieren.
    2. Im Skript nach dem Tick den Durchgang anhaengen (derselbe Prozess,
       damit es keine zweite Zustandsquelle gibt):
           subprocess.run([sys.executable, "-m", "automatik", "durchgang"],
                          cwd=KOPPLUNG)
    3. Cron-Auftrag: script: "automatik-tick.py", no_agent: true,
       schedule.kind: interval, minutes: 15, deliver: telegram.
       Muster ist der bestehende Auftrag bus-waechter.
    4. Leere Ausgabe heisst "nichts zu melden" und wird nicht zugestellt -
       beide Teile halten sich daran.

Zusaetzlich einmal taeglich `python -m automatik nachholen`: ein Nachlauf wird
faellig, ohne dass eine neue Lauf-Zeile entsteht. Wer nur auf neue Zeilen
wartet, holt ihn nie nach.


## 8. Claude-Code-Integration: was uebernommen wurde und was nicht

Das Repo `everything-claude-code` ist hier Vorbild, nicht Vorlage. Was sich
bewaehrt hat und in dieser Anlage steckt:

- Hooks entscheiden nicht, sie melden. Die Hook-Vorlage der Engine
  (`betrieb/hook_vorlage/handler.py`) legt nur eine Datei in den Eingang und
  ruft die Engine nicht auf. Ein Hook, der die Pipeline blockieren kann, wird
  irgendwann abgeschaltet; eine Datei im Eingang wird beim naechsten Tick
  gesehen, auch wenn der Hook kaputt war. Das ist dieselbe Haltung wie bei den
  PreToolUse-Hooks im Repo, die warnen statt zu blockieren.
- Ein Hook, der WIRKLICH sperren soll, muss im Prozess sitzen, nicht daneben.
  Genau das ist `engine/wache.py`: ein Audit-Hook, der vor dem ersten Byte des
  Skripts steht (`engine/vorlauf.py`) und `open`/`remove`/`rename`/`Popen`
  gegen `erlaubte_aktionen` prueft. Ein Hook, der nur eine Warnung auf stderr
  schreibt, waere hier zu wenig gewesen.
- Matcher gehoeren in Daten, nicht in Code. `hooks.json` im Repo haelt seine
  Bedingungen als Ausdruecke; hier tun das `registry.yaml` und
  `reaktionen.yaml`. Beide sind schema-geprueft, damit ein Tippfehler auffaellt
  statt still nichts zu tun.

Was bewusst NICHT uebernommen wurde:

- Keine Hooks und keine Regeln in die laufende Hermes-Konfiguration schreiben.
  Alles bleibt in den Workspaces; das Scharfstellen ist ein bewusster
  Kopierschritt (Abschnitt 7), keine Nebenwirkung eines Testlaufs.
- Keine fremden MCP-Eintraege. Wahrheit bleibt Agenten/MCP-Manifest.json.
- Keine Skills aus fremden Sammlungen uebernehmen. Die Bibliothek hier ist
  bewusst schlank und kuratiert (skill-library-sync).

Fuer eine Plugin-Anbindung an Claude Code gilt dasselbe Muster: das Plugin
duerfte den Eingangsordner befuellen (`nachricht`-Trigger) und `automatik stand`
lesen - aber nicht `durchgang` ausloesen. Sonst gaebe es wieder zwei Stellen,
die ueber das Starten entscheiden.


## 9. Wenn etwas schiefgeht

    Nichts wird gemeldet
        python -m automatik stand
          "Lauf-Zeilen gesamt" vs "beantwortet": stehen beide gleich, gab es
          nichts Neues. Klafft eine Luecke, lief der Durchgang nicht.
        Steht in reaktionen.yaml melde_erfolg: bei_aenderung und hat sich die
          Ausgabe nicht geaendert? Dann ist Schweigen richtig.

    Alles wird gemeldet (Rauschen)
        melde_erfolg auf bei_aenderung, kanal auf log stellen. Meldungen, die
        man wegwischt, sind schlimmer als keine.

    Eine Regel laeuft nicht mehr
        python -m automatik stand      -> "In der Engine gesperrt"
        cd <Engine> && python -m engine log -n 20   -> Grund steht drin
        Nach Klaerung: python -m engine entsperren <regel-id>
        Vorher verstehen, warum gesperrt wurde. Bei "Reaktionsschicht:
        Grenzverletzung" hat ein Lauf eine Grenze verletzt - das ist kein
        Anlass zum Entsperren, sondern zum Lesen von verstoesse.jsonl.

    Dieselbe Meldung mehrfach
        arbeit/kopplung.json ansehen. Wurde "log_zeilen" von Hand
        zurueckgesetzt, wird ab dort neu gemeldet.

    "Registry abgelehnt"
        cd <Engine> && python spez/scripts/registry_pruefen.py betrieb/registry.yaml
        Die Kopplung meldet weiter, startet aber nichts nach - Absicht.

    Kanal versagt (gescheiterte_kanaele im Protokoll)
        telegram: Agenten/Bus pruefen.
        board:    HERMES_DELEGATED_CHILD_CONTEXT stoert `hermes kanban`; die
                  Kanalschicht entfernt die Variable bereits fuer den
                  Unterprozess.
        memory:   basic-memory laedt ein Embedding-Modell; bei "OpenBLAS error:
                  Memory allocation failed" laeuft zu viel parallel. Die
                  Kanalschicht setzt bereits OPENBLAS_NUM_THREADS=1.

    "verstoss" direkt nach einem Handlauf
        Stand HERMES_AUTOMATIK_BASIS/_REGISTRY gesetzt? Ohne sie greift die
        Beispiel-Registry mit fremden schreibpfaden, und die Wache bricht
        voellig korrekt ab. Der Fehler liegt im Aufruf, nicht in der Regel.
        Nebenwirkung: ein zweiter Arbeitsordner <Engine>/arbeit mit eigener
        zustand.db. Loeschen, sonst laufen zwei Zustaende nebeneinander.

    Nach einem Absturz
        Nichts tun. Es wird absichtlich nichts nachgeholt; faellige Nachlaeufe
        aelter als eine Stunde verfallen. Ein Blick auf `automatik stand` und
        `engine log` zeigt, was zuletzt lief.
