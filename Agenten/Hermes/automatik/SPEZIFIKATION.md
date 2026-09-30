# Spezifikation: Trigger- und Skill-Registry-Modell

Version 1.0.0 - 20.09.2026 - Kanban t_3d28119b
Nachfolger-Tasks: t_9f7db046 (Engine), t_f682e5c1 (Reaktionsschicht)

Diese Datei ist die Wahrheit fuer die Frage: welcher Skill darf ohne expliziten
Nutzeraufruf laufen, wodurch wird er ausgeloest, und was darf er dabei tun.

Mitgelieferte, ausfuehrbare Teile (kein Papier ohne Probe):

    registry.schema.json          JSON-Schema 2020-12 der Registry
    registry.example.yaml         6 Regeln, alle Skills existieren wirklich
    registry.negativ.yaml         6 Regeln mit Verstoessen (Negativtest, 7 Meldungen)
    inventar.json / inventar.md   maschinelles Skill-Inventar mit Belegen
    scripts/inventar.py           erzeugt das Inventar
    scripts/registry_pruefen.py   Schema + Existenz + Sicherheitsregeln
    scripts/test_registry.py      Testlauf; alle 4 Tests gruen am 20.09.2026

Belegter Stand der Proben:

    python scripts/inventar.py
    -> 52 Skills; none=20, local=6, extern=16, geld=6, destruktiv=4

    python scripts/registry_pruefen.py registry.example.yaml   -> Exit 0
    python scripts/registry_pruefen.py registry.negativ.yaml   -> Exit 1, 7 Meldungen
    python scripts/test_registry.py                            -> Exit 0, alle gruen


## 1. Inventar (Schritt 1 der Aufgabe)

Quelle: Agenten/Hermes/profiles/one-skill-to-rule-them-all/skills
52 aktive SKILL.md, 80 weitere unter .archive/ (nicht geladen, nicht triggerbar).

Je Skill erfasst inventar.json: name, pfad, zweck (description), version,
zeichen, eingaben, nebenwirkung, belege.

Die Nebenwirkungsklasse ist nicht geschaetzt. Jeder Skill traegt seine Belege
mit Marker und Zeilennummer, damit eine Einordnung im Streitfall nachpruefbar
ist. Fuenf Klassen, aufsteigend:

| Klasse | Bedeutung | Zahl | Beispiele |
|---|---|---|---|
| none | liest/erklaert nur | 20 | brainfiles/mcp-sync, okx-dex-market, claude-code-imports/archiv |
| local | schreibt lokal Dateien/Repos | 6 | note-taking/obsidian, claude-code-imports/umzug |
| extern | verlaesst den Rechner | 16 | chat, github/github-pr-workflow, brainfiles/bus-integration |
| geld | Handel, Wallet, Zahlung | 6 | brainfiles/handel-spuren, okx-agentic-wallet, okx-defi |
| destruktiv | loescht oder verwirft | 4 | claude-code-imports/sichern, brainfiles/skill-library-sync |

Pflege der Markerlisten: scripts/risiko_marker.py. Die Marker sind absichtlich
spezifisch. Ein erster Durchlauf mit dem Marker "order" traf "in order to" in
acht harmlosen Skills und stufte sie faelschlich als geld ein - deshalb heisst
der Marker heute "place_order", "limit order", "kraken_order" usw. Wer Marker
erweitert, laesst danach scripts/test_registry.py laufen: Test 4 verlangt, dass
jede Klasse != none mindestens einen Beleg hat.


## 2. Trigger-Modell (Schritt 2)

Fuenf Ereignistypen, mehr nicht. Jeder Typ hat feste Bedingungsfelder, die das
Schema erzwingt (allOf/if-then), damit eine Regel nicht halb spezifiziert ist.

| Typ | Quelle in dieser Installation | Bedingungen |
|---|---|---|
| board_event | Kanban-DB Agenten/Hermes/kanban.db, Event-Kinds created/claimed/blocked/review/done/failed | ereignis (Pflicht), assignee, titel_enthaelt, board |
| datei | Dateiwaechter auf Pfadmuster unterhalb BrainFiles | pfad_muster (Pflicht), aktion, mindestabstand_s |
| zeit | Hermes-Cron (cron/jobs.json, Feld script + no_agent) | intervall_min ODER cron, nur_wenn_wach |
| nachricht | Gateway-Hook agent:start bzw. Telegram-Bus | kanal (Pflicht), muster (Pflicht), nur_von |
| skill_ergebnis | Verkettung: ein anderer Regel-Lauf ist fertig | regel (Pflicht), status |

Prioritaet: Feld trigger.prioritaet, 0 = hoechste, 100 = niedrigste. Bei
gleichzeitigen Treffern laeuft die kleinere Zahl zuerst; bei Gleichstand gilt
die Reihenfolge in der Datei. Empfohlene Vergabe:

    0-19    Meldungen, die einen wartenden Menschen betreffen (Board blocked)
    20-49   Bestandsaufnahmen und Pruefungen
    50-79   Berichte und Verkettungen
    80-100  alles, was gesperrt ist oder bewusst zuletzt laufen darf

Warum nur diese fuenf: jeder Typ existiert hier bereits als Mechanismus. Die
Zeit-Quelle ist der Hermes-Cron, der mit script + no_agent ein Skript ohne
Modellaufruf startet (Vorbild: der Auftrag skill-usage-report, Montag 9:30).
board_event liest die Events, die kanban_* ohnehin schreibt. nachricht haengt am
Hook-System (Agenten/Hermes/hooks/, Events gateway:startup, session:*, agent:*),
das heute leer ist und genau dafuer gedacht ist.

nur_wenn_wach ist kein Komfortfeld: dieser Rechner geht schlagartig aus
(Kernel-Power 41, Ursache offen). Nachgeholte Sammellaeufe nach einem Ausfall
sind der gefaehrlichste Fall, den diese Registry kennt - deshalb entfaellt ein
verpasster Zeitlauf ersatzlos, statt sich zu stapeln.


## 3. Registry (Schritt 3)

Format: YAML, validiert gegen registry.schema.json (Version 1.0.0).
Aufbau: registry_version, defaults, regeln[].

Eine Regel besteht aus:

    id                  eindeutig, klein, mit Bindestrichen; Referenz im Log
    skill               Pfad im Profil ODER Skriptname unter Hermes/scripts
    skill_art           skill | skript
    trigger             typ + prioritaet + bedingungen (siehe Abschnitt 2)
    parameter           flache Werte, die an den Skill gehen
    erlaubte_aktionen   Obergrenze der Wirkung (Pflicht, siehe unten)
    schreibpfade        Whitelist; Pflicht bei datei_schreiben/git_commit/loeschen
    modus               dry_run | auto | bestaetigung | gesperrt
    timeout_s           5..3600
    rate_limit          max_laeufe, fenster_s, cooldown_s
    kanal               log | board | telegram | Kombinationen | alle
    abbruch             bei_fehlerstreak, nicht_wenn_regel_laeuft,
                        nur_wenn_pfad_existiert, max_gleichzeitig
    eskalation          wiederholungen, wiederhol_abstand_s, danach

Aktionsvokabular (erlaubte_aktionen), aufsteigend nach Wirkung:

    lesen               immer implizit erlaubt
    bericht_schreiben   Text in den eigenen Ausgabeordner
    datei_schreiben     Dateien innerhalb schreibpfade
    git_commit          Commit im erlaubten Pfad, ohne push
    git_push            Veroeffentlichung
    nachricht_senden    Telegram, Mail, A2A
    board_schreiben     Kanban-Kommentar oder Statuswechsel
    prozess_starten     Dauerlauf/Server
    loeschen            Dateien entfernen
    handel              Order, Swap, Transfer, Wallet

Die Liste ist eine Obergrenze, keine Absicht: die Engine bricht ab, sobald ein
Lauf etwas ausserhalb versucht. Das ist der einzige Punkt, an dem die Registry
einen Skill zuverlaessig begrenzt - eine SKILL.md ist Prosa und haelt sich nur
freiwillig an ihre eigenen Regeln.

defaults ist absichtlich restriktiv: modus dry_run. Eine Regel, die ihren Modus
nicht selbst setzt, protokolliert nur, was sie tun wuerde. Wer eine Regel
scharf stellt, muss das ausdruecklich hinschreiben.


## 4. Sicherheitsregeln (Schritt 4)

S1  Unbekannter Skill ist ein Fehler, kein Hinweis. Jeder skill-Wert muss als
    SKILL.md im Profil bzw. als Skript unter Hermes/scripts existieren. Eine
    Engine, die einen unbekannten Namen startet, tut etwas anderes als die
    Registry sagt.

S2  handel, git_push und loeschen nie im Modus auto - unabhaengig davon, wie
    harmlos der Skill sonst aussieht. Das Schema erzwingt das zusaetzlich.

S3  Der Modus darf die belegte Nebenwirkungsklasse nicht ueberschreiten:

        none, local, extern   ->  hoechstens auto
        geld, destruktiv      ->  hoechstens bestaetigung

    Geprueft wird gegen inventar.json, nicht gegen eine Einschaetzung im Kopf.
    Aendert ein Skill sich und bekommt eine hoehere Klasse, faellt seine Regel
    beim naechsten Pruefen durch - das ist der Sinn von Regel 1 im Beispiel.

S4  Schreibpfade sind eng. Laufwerkswurzeln, "." und einteilige Pfade sind
    verboten. Schreibpfade sind Praefix-Whitelists, keine Muster.

S5  Jede auto-Regel braucht ein eigenes rate_limit. Defaults reichen nicht:
    wer scharf stellt, benennt die Obergrenze.

S6  Jede auto-Regel braucht abbruch oder eskalation. Eine Automatik ohne
    Abbruchbedingung ist ein Dauerlauf mit Zufallsende.

S7  Zeit-Trigger unter 5 Minuten sind Dauerbetrieb, nicht Automatik, und
    gehoeren nicht in diese Registry. Wer sekundengenau reagieren muss, braucht
    einen Dienst und eine ausdrueckliche Anweisung.

S8  Bestaetigung heisst: Rueckfrage ueber kanal, Start erst nach Ja, Verfall
    nach timeout_s. In einer Sitzung ohne anwesenden Nutzer gilt keine Antwort
    als Nein. Diese Sitzung hat das am eigenen Leib belegt: execute_code und
    mehrere Schreibversuche wurden headless abgewiesen, weil niemand zustimmen
    konnte (siehe Abschnitt 6).

Zusaetzlich mechanisch geprueft: doppelte Regel-IDs und Verkettungen
(skill_ergebnis), die auf eine nicht existierende Regel-ID zeigen.


## 5. Was die Engine daraus bauen muss (Uebergabe an t_9f7db046)

1.  Registry laden: yaml.safe_load, dann Draft202012Validator gegen
    registry.schema.json, dann die Pruefungen S1-S8. Praktisch: die Engine ruft
    scripts/registry_pruefen.py mit --json auf und startet nur bei leerem
    schemafehler und regelfehler. Damit gibt es genau eine Implementierung der
    Regeln, nicht zwei, die auseinanderlaufen.

2.  Trigger-Quellen anbinden:
    - zeit: Hermes-Cron. Ein Auftrag je Regel, Feld script + no_agent: true,
      schedule.kind cron oder interval. Muster: cron/jobs.json, Auftrag
      skill-usage-report.
    - board_event: Events aus Agenten/Hermes/kanban.db pollen (die kanban_*
      Tools schreiben sie ohnehin) und auf ereignis/assignee filtern.
    - datei: ein Waechter auf die pfad_muster, mindestabstand_s als Entprellung.
    - nachricht: Hook-Verzeichnis Agenten/Hermes/hooks/<name>/ mit HOOK.yaml
      (name, description, events) und handler.py (def handle(event_type,
      context)). Verfuegbare Events: gateway:startup, session:start/end/reset,
      agent:start, agent:step, agent:end, command:*. Fehler in Hooks blockieren
      die Pipeline nicht - die Engine darf sich also nicht darauf verlassen,
      dass ein Hook-Fehler sichtbar wird, und muss selbst loggen.
    - skill_ergebnis: nach jedem Lauf die Kette auswerten.

3.  Skill-Aufruf kapseln: parameter uebergeben, timeout_s erzwingen,
    Exit-Status und Ausgabe erfassen, erlaubte_aktionen als harte Grenze
    durchsetzen (nicht als Bitte an das Modell).

4.  Log je Lauf, strukturiert und eine Zeile je Lauf (JSONL): zeit, regel_id,
    trigger_typ, ausgeloest_durch, skill, modus, dauer_ms, exit, aktionen_genutzt,
    abbruchgrund. Ohne aktionen_genutzt ist im Nachhinein nicht pruefbar, ob die
    Grenze gehalten hat.

5.  dry_run muss echt sein: alles pruefen, Log schreiben, Skill nicht starten.

Wichtig fuer die Engine-Task: dieser Rechner erlaubt in einer Sitzung ohne
anwesenden Nutzer kein execute_code und keine als gefaehrlich erkannten Shell-
Kommandos. Eine Engine, die zum Starten eines Skills eine solche Bruecke
braucht, laeuft unbeaufsichtigt nie. Sie muss ihre Laeufe als eigene Prozesse
ueber den Cron oder einen Dienst starten, nicht aus einer Agentensitzung heraus.


## 6. Gelernt beim Bauen (fuer die Folge-Tasks)

- Die Hermes-Kommandopruefung schlaegt auch beim SCHREIBEN einer Datei zu, wenn
  darin ein vollstaendiges Loesch-Kommando als Literal steht. Drei write_file-
  Laeufe liefen dadurch in den 420-s-Timeout, ein Heredoc wurde als "recursive
  delete" blockiert. Loesung: Risikomuster in eine eigene Datei mit einzelnen
  Wortteilen auslagern (scripts/risiko_marker.py). Wer einen Scanner fuer
  gefaehrliche Kommandos schreibt, teilt die Muster auf.
- O:\Werkstatt ist eine Junction; Schreiben dorthin scheitert an
  HERMES_WRITE_SAFE_ROOT. Arbeitsergebnisse gehoeren in den Kanban-Workspace
  unter C:\Users\faupe\Documents\BrainFiles.
- Ein Marker-Scanner ohne Negativtest liefert Unsinn mit ruhigem Gewissen: die
  erste Fassung stufte 19 von 52 Skills als geld ein, nach dem Verschaerfen
  waren es 6. Erst der Belegzwang (Zeilennummer + Fundstelle) machte den Fehler
  sichtbar.
