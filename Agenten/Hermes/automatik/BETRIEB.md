# Auto-Ausfuehrungs-Engine fuer Skills

Version 1.0.0 - 20.09.2026 - Kanban t_9f7db046
Vorgaenger: t_3d28119b (Spezifikation, Registry-Modell, Validator)
Nachfolger: t_42a2e275, t_f7937187

Die Engine liest die Registry aus der Spezifikations-Task, erkennt Trigger,
setzt die Sicherheitsregeln durch und protokolliert jeden automatischen Lauf.
Sie ist ein Prozess, der prueft und endet - kein Dauerdienst. Der Rechner geht
schlagartig aus (Kernel-Power 41, Ursache offen); ein Prozess, der nichts im
Speicher festhaelt, hat dabei nichts zu verlieren.


## 1. Schnellstart

    cd C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\kanban\workspaces\t_9f7db046
    set HERMES_AUTOMATIK_BASIS=%CD%\betrieb\arbeit
    set HERMES_AUTOMATIK_REGISTRY=%CD%\betrieb\registry.yaml

    python -m engine pruefen          Registry laden und Regeln anzeigen
    python -m engine tick             einmal alle Quellen fragen und abarbeiten
    python -m engine --nur-lesen tick dasselbe, aber alles als dry_run
    python -m engine lauf <regel-id>  eine Regel von Hand ausloesen
    python -m engine log -n 20        letzte Laeufe
    python -m engine antwort <id> ja  offene Bestaetigung beantworten
    python -m engine entsperren <id>  Dauersperre nach Fehlerstreak aufheben

Unter git-bash NICHT `$PWD` fuer die Umgebungsvariablen verwenden: MSYS liefert
`/c/Users/...`, Python macht daraus `C:\c\Users\...` und die Engine legt ihren
Zustand in einem Streuordner ab. Immer den nativen Pfad mit Vorwaertsschraegen
setzen (`C:/Users/faupe/...`). Das ist hier einmal passiert und wurde bereinigt.


## 2. Aufbau

    engine/pfade.py        Pfade + Umgebungsvariablen (alles umstellbar)
    engine/registry.py     Registry laden, Version pruefen, Validator aufrufen
    engine/quellen/        die fuenf Trigger-Quellen
        board.py           Kanban task_events, read-only
        datei.py           Pfadmuster-Vergleich mit Entprellung
        zeit.py            Intervall und Cron, ohne Nachholen
        nachricht.py       Eingangsordner, vom Hook befuellt
        verkettung.py      skill_ergebnis: ein Lauf zieht den naechsten
    engine/steuerung.py    Modus, Rate-Limit, Abbruch, Bestaetigung
    engine/lauf.py         Prozessstart, Timeout, Ergebnis
    engine/wache.py        Audit-Hook: erlaubte_aktionen als Zwang
    engine/vorlauf.py      setzt die Wache vor dem ersten Byte des Skripts
    engine/zustand.py      SQLite: Laeufe, Marken, Sperren, Belegung
    engine/protokoll.py    JSONL, eine Zeile je Lauf
    engine/__main__.py     CLI

    spez/                  Kopie der Spezifikations-Ergebnisse (Schema,
                           Validator, Inventar, Beispiel-Registry)
    betrieb/registry.yaml  die Registry, die hier wirklich laeuft
    betrieb/automatik-tick.py  Cron-Vorlage (no_agent)
    betrieb/hook_vorlage/  Hook-Vorlage fuer den Nachricht-Trigger
    tests/test_engine.py   28 Proben, je eine pro Trigger-Typ plus Sicherheit


## 3. Wie eine Entscheidung zustande kommt

Ein Tick fragt alle Quellen, sortiert die Treffer nach Prioritaet (0 zuerst,
bei Gleichstand Dateireihenfolge) und schickt jeden durch dieselbe Kette:

    1. Modus gesperrt              -> uebersprungen
    2. Dauersperre (Fehlerstreak)  -> uebersprungen
    3. abbruch: nur_wenn_pfad_existiert, nicht_wenn_regel_laeuft, max_gleichzeitig
    4. rate_limit: max_laeufe im Fenster, cooldown_s
    5. Modus bestaetigung          -> Frage anlegen, Start nur bei 'ja'
    6. Modus dry_run               -> Trockenlauf, nichts gestartet
    7. Modus auto                  -> echter Lauf unter der Wache

Billig und hart zuerst: ein gesperrter Lauf kommt nie in die Naehe eines
Prozessstarts. Uebersprungene Laeufe zaehlen NICHT gegen das Rate-Limit, sonst
sperrt sich eine Regel durch ihre eigenen Ablehnungen selbst aus.


## 4. Die Aktionsgrenze ist echt

`erlaubte_aktionen` ist der einzige Punkt, an dem die Registry einen Skill
zuverlaessig begrenzt - eine SKILL.md ist Prosa und haelt sich nur freiwillig
an ihre eigenen Regeln. Darum laeuft jedes Skript unter einem Audit-Hook
(`sys.addaudithook`, ab Python 3.8 nicht mehr entfernbar), der vor dem ersten
Byte des Skripts gesetzt wird (`vorlauf.py`). Gesehen werden:

    open mit Schreibflag   -> Pfad gegen schreibpfade
    os.remove/rmtree/...   -> loeschen
    os.rename/replace      -> datei_schreiben (Quelle und Ziel)
    subprocess.Popen       -> Kommando einordnen (muster.py)
    socket.connect         -> nur beobachtet, siehe unten

Bei einem Verstoss endet der Prozess hart mit Exit 97, die Zeile landet in
`verstoesse.jsonl` des Laufordners, und die Engine meldet `ergebnis=verstoss`.

Bekannte, bewusste Grenzen:

- `socket.connect` wird beobachtet, nicht gesperrt. Das Aktionsvokabular kennt
  keine Aktion "Netzzugriff"; ein Hook, der jede Verbindung sperrt, wuerde DNS
  und lokale Sockets treffen. Ziele stehen im Log unter `netz_ziele`.
- Ein Enkelprozess laeuft ohne den Hook. Sein Start wird aber gesehen und
  eingeordnet - eine Regel ohne `prozess_starten` kommt gar nicht so weit.
- `skill_art: skill` (Agentenlauf ueber hermes.exe) laesst sich von innen nicht
  bewachen. Dieser Weg ist deshalb GESPERRT und wird nur mit
  `HERMES_AUTOMATIK_SKILL_START=1` freigegeben. Ohne Freigabe ist das Ergebnis
  `uebersprungen` mit Begruendung - nicht ein stiller Fehlschlag.
- `freipfade` ist leer. Ein frueherer Entwurf stellte %TEMP% frei; damit war die
  Wache unterhalb von %TEMP% blind, und die Probe, die das nachweisen sollte,
  kam durch. Der Test `test_wache_blockt_schreiben_ausserhalb` haelt das fest.


## 5. at-most-once, nie nachholen

Jede Quelle setzt ihre Marke, SOBALD sie ein Ereignis gesehen hat - nicht erst
nach erfolgreichem Lauf. Ein abgestuerzter Lauf wird also nicht wiederholt.
Das ist Absicht: nach einem Stromausfall wuerde ein Stapel nachgeholter
Automatik starten, und genau diesen Fall verbietet die Spezifikation mit
`nur_wenn_wach`. Konkret:

- zeit: liegt die Faelligkeit laenger als eine Stunde zurueck, entfaellt sie.
- board: der erste Blick setzt nur die Marke, sonst gaelte die gesamte
  Board-Historie als "gerade passiert".
- datei: der erste Lauf nimmt den Bestand auf, sonst gaelte jede vorhandene
  Datei als neu angelegt.
- nachricht: jede Eingangsdatei wird genau einmal betrachtet und danach nach
  `nachrichten/erledigt/` verschoben - auch wenn keine Regel passte.
- verkettung: ein Vorgaengerlauf zieht die Folgeregel hoechstens einmal.


## 6. Belegte Laeufe (20.09.2026)

Testlauf:

    python -m pytest tests/test_engine.py -q
    28 passed in 14.74s

Validator gegen die Betriebs-Registry:

    python spez/scripts/registry_pruefen.py <absoluter Pfad>/betrieb/registry.yaml
    OK - Schema, Existenz und Sicherheitsregeln erfuellt. (Exit 0)

Betrieb ueber die CLI, Auszug aus `python -m engine log`:

    09:49:30 inventar-nach-skill-aenderung   datei           erfolg      680ms
    09:50:24 sichern-nach-inventaraenderung  skill_ergebnis  bestaetigung_offen
    09:50:26 inventar-nach-skill-aenderung   datei           uebersprungen  Cooldown: noch 64s
    09:50:27 handel-spuren-auf-zuruf         nachricht       uebersprungen  Regel ist gesperrt
    09:51:21 sichern-nach-inventaraenderung  skill_ergebnis  uebersprungen  skill_art=skill ohne Freigabe
    10:02:37 inventar-nach-skill-aenderung   datei           erfolg      620ms
             ausgeloest durch: 1 Datei(en) modified, zuerst: .../skills/chat/SKILL.md

Die Zeile um 10:02 ist der Ende-zu-Ende-Nachweis: eine echte SKILL.md im Profil
wurde angefasst, der Datei-Trigger hat gefeuert, `inventar.py` lief unter der
Wache (`aktionen_genutzt: ["datei_schreiben"]`, Exit 0, 52 Skills), und die
Verkettung hat anschliessend die Bestaetigungspflicht gezogen.

Cron-Vorlage:

    python betrieb/automatik-tick.py   Exit 0, keine Ausgabe (nichts zu melden)


## 7. Scharf stellen

Zeit-Trigger in den Takt nehmen (das ist der Normalbetrieb):

1. `betrieb/automatik-tick.py` nach `Agenten/Hermes/scripts/automatik-tick.py`
   kopieren.
2. Cron-Auftrag anlegen mit `script: "automatik-tick.py"`, `no_agent: true`,
   `schedule.kind: interval`, `minutes: 15`, `deliver: telegram`. Muster ist der
   bestehende Auftrag `bus-waechter`.
3. Leere Ausgabe heisst "nichts zu melden" und wird nicht zugestellt. Das Skript
   schreibt nur bei fehler, timeout, verstoss oder offener Bestaetigung.

Nachricht-Trigger anbinden:

1. `betrieb/hook_vorlage/handler.py` nach
   `Agenten/Hermes/hooks/automatik-nachricht/handler.py` kopieren.
2. Daneben `HOOK.yaml`:

       name: automatik-nachricht
       description: legt eingehende Nachrichten in den Engine-Eingang
       events: [agent:start]

3. Der Hook schreibt nur eine Datei und ruft die Engine nicht auf. Hook-Fehler
   blockieren die Pipeline nicht und blieben sonst unsichtbar; eine Datei im
   Eingang wird beim naechsten Tick gesehen, auch wenn der Hook kaputt war.

Agentenlaeufe (`skill_art: skill`) freigeben: nur bewusst, und nur zusammen mit
einem Menschen am Rechner - die Wache greift dort nicht.


## 8. Wenn etwas schiefgeht

    Regel laeuft nicht        python -m engine pruefen (steht sie auf dry_run?)
                              python -m engine log -n 20 (Grund steht drin)
    "Dauersperre"             python -m engine entsperren <regel-id>
    "bestaetigung_offen"      python -m engine antwort <regel-id> ja
    "Registry abgelehnt"      Validator direkt aufrufen, er nennt die Regel-ID
    Wache bricht ab           verstoesse.jsonl im Laufordner unter arbeit/laeufe/

Zustand und Log liegen unter `HERMES_AUTOMATIK_BASIS`. Beides darf geloescht
werden; die Engine beginnt dann wieder mit "Bestand aufnehmen" und loest beim
ersten Tick bewusst nichts aus.


## 9. Uebergabe an die Reaktionsschicht (t_f682e5c1)

Das JSONL unter `arbeit/laeufe.jsonl` ist die Schnittstelle. Eine Zeile je Lauf,
nur angehaengt, nie umgeschrieben; eine kaputte Zeile darf den Leser nicht
aufhalten (`protokoll.zeilen_lesen` ueberspringt sie). Felder:

    zeit, zeit_unix, lauf_id, regel_id, trigger_typ, ausgeloest_durch, skill,
    modus, ergebnis, dauer_ms, exit, aktionen_genutzt, abbruchgrund, ausgabe,
    ausgabe_gekuerzt, registry_version, versuch
    dazu je nach Lauf: kommando, verstoesse, netz_ziele

`ergebnis` ist eines von: erfolg, fehler, timeout, verstoss, dry_run,
uebersprungen, bestaetigung_offen, abgelehnt.

Wer auf Meldungen reagiert, filtert auf `ergebnis in (fehler, timeout, verstoss,
bestaetigung_offen)` - alles andere ist Normalbetrieb und gehoert nicht in eine
Benachrichtigung.
