# Reaktions- und Benachrichtigungsschicht

Kanban t_f682e5c1 · Stand 20.09.2026 · Ordner
`Agenten/Hermes/kanban/workspaces/t_f682e5c1`

Diese Schicht führt keine Skills aus. Sie liest, was die Engine (t_9f7db046)
je Lauf protokolliert, entscheidet daraus eine Reaktion, benachrichtigt und
merkt sich das Ergebnis. Die Trennung ist Absicht: die Engine darf starten,
diese Schicht darf melden und merken. Deshalb läuft sie auch dort, wo kein
Skill gestartet werden darf.

## Dateien

    reaktion.py        Entscheidung (rein) + Ausführung + CLI
    kanaele.py         Außenseite: Log, Board, Telegram/Bus, basic-memory
    reaktionen.yaml    Reaktionsregeln (was nach einem Lauf passiert)
    test_reaktion.py   10 Tests mit Kanal-Attrappe, ohne Nebenwirkung
    engine_zeilen.py   erzeugt ECHTE Engine-Lauf-Zeilen für den Durchstich
    ende_zu_ende.py    Durchstich mit den echten Kanälen (schreibt sichtbar)
    reaktion-log.jsonl Protokoll, eine Zeile je Reaktion
    zustand.json       Fehlerstreak, Versuch, letzter Erfolgs-Abdruck je Regel
    nachlauf.jsonl     Bitte an die Engine: Regel später nochmal
    sperren.json       Bitte an die Engine: Regel nicht mehr

## Befunde: was die Schicht aus einem Lauf liest

Die Engine schreibt zwei Angaben über den Ausgang: `exit` (Prozess-Exitcode,
`null` wenn gar kein Prozess lief) und `ergebnis` (ihr eigenes Vokabular).
`ergebnis` hat Vorrang — nur die Engine weiß, ob überhaupt etwas gestartet
wurde. Sechs Befunde:

    Befund           Auslöser                          Reaktion
    ---------------  --------------------------------  -------------------------
    grenzverletzung  Aktion außerhalb erlaubte_aktionen sperren + alle Kanäle
    probelauf        modus=dry_run                     nur Log
    uebersprungen    ergebnis=uebersprungen            nur Log, kein Zähler
    wartet           ergebnis=bestaetigung_offen       melden, nicht eskalieren
    erfolg           ergebnis=erfolg bzw. exit=0       je melde_erfolg
    fehler           alles andere, auch exit=null      Wiederholung/Eskalation

Grenzverletzung steht zuerst, weil sie schwerer wiegt als ein Fehlschlag und
nie durch eine Wiederholung „geheilt" werden darf. Ein unbekanntes Wort im
Feld `ergebnis` gilt als **fehler**, nicht als Erfolg: Drift zwischen Engine
und Schicht wird gemeldet, nicht verschluckt.

## Reaktionsregeln konfigurieren (reaktionen.yaml)

Auflösung: `defaults`, feldweise überschrieben von `regeln.<regel_id>`. Genau
eine Ebene, keine Vererbungskette — im Zweifel sind zwei Zeilen zu lesen.

    kanal            log | board | telegram | log+board | log+telegram | alle
    memory_notiz     Notizpfad, Platzhalter {regel_id} und {skill}
    melde_erfolg     nie | immer | bei_aenderung
    eskalation.wiederholungen       0..5 (die Schicht merkt vor, startet nicht)
    eskalation.wiederhol_abstand_s  >= 10
    eskalation.danach               melden | board_blocken | regel_sperren | still

Prüfen ohne Wirkung:

    python reaktion.py --konfig-pruefen --konfig reaktionen.yaml

`bei_aenderung` vergleicht einen SHA-256-Kurzabdruck der Ausgabe mit dem
letzten Erfolg. Eine Regel, die stündlich dasselbe meldet, meldet damit
genau einmal — und wieder, sobald sich das Ergebnis ändert.

## Aufruf

    python reaktion.py --ergebnis lauf.jsonl        eine oder mehrere Zeilen
    cat laeufe.jsonl | python reaktion.py --stdin   Fließbetrieb
    python reaktion.py --ergebnis x.json --probe    entscheidet, meldet nicht
    python test_reaktion.py                         10 Tests, Exit 0

Exitcodes: 0 = nichts Schlimmes, 1 = mindestens ein Fehler/Grenzverletzung,
2 = ein Kanal ist ausgefallen (die Reaktion selbst hat funktioniert).

## Verdrahtung mit der Engine (für t_f7937187)

Die Engine schreibt ihr Log über `engine/protokoll.py` nach
`arbeit/laeufe.jsonl` (Pfad umstellbar über `HERMES_AUTOMATIK_BASIS`). Die
Schicht liest genau dieses Format. Einfachste Verdrahtung, ein Durchgang:

    python engine_zeilen.py > /tmp/laeufe.jsonl      # bzw. echtes Engine-Log
    python reaktion.py --ergebnis /tmp/laeufe.jsonl

Im Dauerbetrieb liest der Aufrufer nur die noch nicht verarbeiteten Zeilen
(Wasserstand über `lauf_id` oder Byte-Offset) und schickt sie durch `--stdin`.
Die Schicht ist dabei idempotent gegenüber Wiederholungen **nicht** — jede
Zeile erzeugt eine Reaktion. Der Wasserstand gehört darum zum Aufrufer.

Rückkanal zur Engine, bewusst als Datei und nicht als Start:

    nachlauf.jsonl   Wiederholungswunsch mit faellig_ab (Untergrenze, kein Termin)
    sperren.json     Regel-Sperre nach Grenzverletzung oder danach=regel_sperren

Die Engine wendet beim Einlesen weiterhin ihre eigenen Regeln an (Rate-Limit,
Modus, Sperre). Es gibt nur eine Stelle, die entscheidet, was laufen darf.

## Belegte Eigenheiten dieser Installation

- **Board-Kanal:** `hermes kanban` verweigert in einer Kanban-Sitzung jede
  Änderung, solange `HERMES_DELEGATED_CHILD_CONTEXT` gesetzt ist. Die Variable
  wird für den Unterprozess entfernt — sonst scheitert der Kanal lautlos
  (Exitcode 0, Text „cannot mutate").
- **Memory-Kanal:** schreibt in das basic-memory-Projekt (`~/basic-memory`),
  **nicht** in den Vault MaxHirn. Das ist Grenze, nicht Zufall: der Vault
  bleibt die einzige Wahrheit und wird von keiner Automatik beschrieben.
- **OpenBLAS:** `basic-memory tool` lädt ein Embedding-Modell und brach drei
  von fünf Mal mit „Memory allocation failed after 10 retries" ab (ein Thread
  je Kern, hier 28). `OPENBLAS_NUM_THREADS=1` behebt das; der Kanal ist
  langsamer, aber nicht mehr sporadisch stumm.
- **Board-Block:** `hermes kanban block` meldet „cannot block", wenn der Task
  schon blockiert ist. Der Kanal prüft danach den Status — der gewünschte
  Zustand ist erreicht, also gilt es als Erfolg.
- **Wiederholte Blocks:** Das Board schiebt einen mehrfach geblockten Task
  selbst nach `triage` („unblock loop detected"). Das ist erwünscht: aus der
  flatternden Störung wird ein Fall für einen Menschen.

## Grenzen

- Die Schicht startet nie einen Skill. Ein Prozess, der nachstartet, wäre eine
  zweite Engine mit zweiter Sicherheitsprüfung.
- Sie schreibt nichts in den Vault MaxHirn.
- Sie erfindet keine Felder: fehlt in einer Lauf-Zeile sowohl `exit` als auch
  `ergebnis`, wird die Zeile mit Feldnamen abgelehnt statt zurechtgebogen.
