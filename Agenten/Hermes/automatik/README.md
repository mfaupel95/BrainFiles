# Automatik - Auto-Ausfuehrungs-Engine fuer Skills und Regelwerke

Dauerhaftes, versioniertes Home der vier Kinder-Tasks von Kanban `t_42a2e275`
(spez / engine / reaktion / automatik). Vorher lagen die Bausteine getrennt in
den fluechtigen Kanban-Workspaces `kanban/workspaces/t_*`; hier sind sie in
EINEM Ordner zusammengefuehrt, weil alleine so beide Pfad-Module (engine und
Kopplung) auf EINE Wurzel zeigen und die Kopplung Engine+Reaktion als
sys.path-Geschwister findet.

## Struktur

    automatik/
      engine/         Ausfuehrungs-Engine (Registry laden, Quellen fragen, Regeln abarbeiten)
        quellen/      Ausloeser je Trigger-Typ (datei, zeit, board_event, nachricht, skill_ergebnis)
        pfade.py      alle Pfade ueber HERMES_AUTOMATIK_*-Variablen konfigurierbar
      automatik/      Kopplungsschicht (Reaktion auf Lauf-Zeilen, Rueckweg, Sperren, Nachlaeufe)
      spez/           Spezifikation: Registry-Schema, Validator, Skill-Inventar-Skripte
        scripts/      inventar.py (auto-Regel), registry_pruefen.py, skill_*.py
      betrieb/        Betriebsfassung
        registry.yaml die laufende Regelkonfiguration (5 Regeln, meist dry_run)
        automatiktick.template.py  Vorlage des Cron-Ticks (in scripts/ installiert)
        arbeit/       Laufzeitstand - NICHT versioniert (zustand.db, laeufe.jsonl ...)
      reaktion.py     Reaktionsschicht (Regeln, Kanaele, Melde-Haltung)
      kanaele.py, engine_zeilen.py, reaktionen.yaml   Reaktionskonfiguration
      tests/          Test-Engine + Ende-zu-Ende der Kopplung
      pruefen.py      Gesamtprobe: alle 3 Suiten (45 Checks)
      SPEZIFIKATION.md / BETRIEB.md / AUTOMATIK.md / README-reaktion.md

## Der eine Eintrittspunkt im Takt

`Agenten/Hermes/scripts/automatik-tick.py` ist der Cron-Einstieg (no_agent,
kein Modell): erst `python -m engine tick`, dann `python -m automatik durchgang`.
Beide rechnen OHNE Speicherzustand als kurze Prozesse - der Rechner geht
schlagartig aus, und ein Prozess, der nichts festhaelt, hat dabei nichts zu
verlieren (BETRIEB.md).

## Master-SCHALTER (EIN/AUS)

    (nicht gesetzt / != 0)      Automatik eingeschaltet (Normalbetrieb, Vorgabe)
    HERMES_AUTOMATIK_AKTIV=0    INGESAMT AUS - der Cron laeuft weiter, tut nichts
                               und meldet nichts (auch "aus"/"off"/"false").

Zusaetzlich steht jede Regel in `betrieb/registry.yaml` auf
`modus: dry_run|auto|bestaetigung|gesperrt`. Stand 30.09.2026: eine auto-Regel
(`inventar-nach-skill-aenderung`, schreibt nur ins eigene Home), der Rest
dry_run/bestaetigung/gesperrt (Board-blocker, MCP-Drift, Sichern, Handels-Spur).

## Selbst pruefen

    python3 pruefen.py                 # Engine + Reaktion + Kopplung, 3 Suiten gruen
    python3 -m engine pruefen          # Registry laden und Regeln anzeigen
    python3 -m automatik stand         # Marken, offene Nachlaeufe, Sperren

(Die Tools-python nach dem Update hat kein pytest/yaml mehr - `python3` nutzen.)

## Pfade

Alle Pfade sind variabel. Der Lauf setzt sie in `scripts/automatik-tick.py` so,
dass er NEU in den scratch-Workspaces landen kann: ENGINE/REAKTION=Home,
BASIS/KOPPLUNG/ABLAGE=`betrieb/arbeit/`, REGISTRY=`betrieb/registry.yaml`,
REAKTIONSKONFIG=`reaktionen.yaml`, VALIDATOR=`spez/scripts/registry_pruefen.py`.