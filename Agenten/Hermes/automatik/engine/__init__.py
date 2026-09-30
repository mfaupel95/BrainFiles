"""Auto-Ausfuehrungs-Engine fuer Skills (Kanban t_9f7db046).

Liest die Registry aus der Spezifikations-Task (t_3d28119b), erkennt Trigger,
setzt die Sicherheitsregeln durch und protokolliert jeden automatischen Lauf.

Aufbau:
    pfade       Pfade und Umgebungsvariablen
    registry    Registry laden + ueber den Validator der Spez pruefen
    quellen/    die fuenf Trigger-Quellen (board, datei, zeit, nachricht, kette)
    steuerung   Modus, Rate-Limit, Abbruch, Bestaetigung -> Entscheidung
    lauf        Skill/Skript starten, Timeout, Ergebnis
    wache       Audit-Hook: erlaubte_aktionen als Zwang im Kindprozess
    vorlauf     setzt die Wache vor dem ersten Byte des Skripts
    zustand     SQLite: Laeufe, Marken, Sperren, Belegung, Bestaetigungen
    protokoll   JSONL-Log, eine Zeile je Lauf
    __main__    CLI (pruefen, tick, lauf, log, antwort, entsperren)
"""
