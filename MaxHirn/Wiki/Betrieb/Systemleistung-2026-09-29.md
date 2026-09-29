# Systemleistung 2026-09-29 — Design & Entscheidung

Stand: 2026-09-29, Europe/Berlin.

## 1. Zweck

Der PC meldete sich "sehr langsam". Diese Doc hält Ursache, Sofortbehebung,
die getroffene Entscheidung (Option 4: nichts weiter bauen) und den geplanten
Neustart fest. Sie ist Spezifikation für die Nachwelt, kein Arbeitsplan.

## 2. Befund (gemessen am Host)

| Größe                       | vorher (Notfall)            | nachher (jetzt)        |
|-----------------------------|-----------------------------|------------------------|
| Freies Commit (virt. Speicher) | **1,7 GB** von 87,7 GB     | **14 GB** von 78,5 GB  |
| Python-Prozesse             | **248** (195 älter 60 min)  | **40**                 |
| RAM frei                    | 30,7 GB                     | 33 GB                  |
| CPU                         | 12 % (idle)                 | 9 % (idle)             |
| Uptime                      | 99,6 h                      | 100 h                  |

**Ursache war die Commit-Erschöpfung, nicht CPU oder RAM.**
- ~200 Zombie-Python-Prozesse der MCP-Server (mail 44×, windows-mcp 42×,
  kraken 42×, archiv 38×, tooluniverse 38×, blender 14×) belegten
  **~29,6 GB Commit**. Sie wachsen seit dem Boot im Kreis (Spawn-Kette,
  siehe unten), ohne jemals zu enden.
- Folgen: `WinError 1455 "Auslagerungsdatei zu klein"`, SIGTERM-Wellen,
  und der lokale Modell-Rückfall der Bots (Ollama qwen35-8k) war wertlos,
  weil kein Commit für neue Modelle übrig war.

## 3. Sofortbehebung (bereits wirksam, heute Abend)

1. **Zombies gekillt** — jede MCP-Gruppe auf die 3 jüngsten Prozesse
   begrenzt (`Stop-Process`), 200 beendet. Python 248 → 40, Commit 14 GB frei.
2. **Wache `mcp-zombie-wache`** — Hermes-Cron, alle 15 min, `no_agent`,
   Telegram, **leere Ausgabe = gesund**: hält jede MCP-Gruppe bei den
   3 jüngsten Prozessen, meldet nur Aenderung/Anomalie.
3. Live-Handel (3 Stufen), MoonDev und Gateway wurden **nicht angefasst**.

## 4. Entscheidung Max (Option 4, 29.09.2026)

- **Kein weiterer Umbau jetzt.** Die Wache bleibt aktiv und wird beobachtet.
- Die **Spawn-Kette (Ursache) wird NICHT jetzt angefasst** — sie erfordert
  einen eigenen, abgestimmten Eingriff in die MCP-Startkonfiguration
  (Claude-Desktop / Hermes-Gateway vs. Server-venv-Autostart) und ist als
  Folgeaufgabe dokumentiert (T-152).
- **Kein Code an der Wache oder am Tagesbericht.**
- Unter der Hand sichtbar bleiben: 100 h Uptime, Memory Compression 7,5 GB —
  wird vom geplanten Neustart (Abschnitt 6) entlastet.

## 5. Bewertung der übrigen Kandidaten (nicht umgesetzt)

| Kandidat                          | Einschätzung                                     | Status        |
|-----------------------------------|--------------------------------------------------|---------------|
| MCP-Spawn-Kette beheben           | eigentliche Ursache; braucht eigenen Eingriff    | Folgeaufgabe T-152 |
| Defender-Ausnahmen (MsMpEng 532 MB) | scannt zur Laufzeit; sinnvoll, aber später     | Vorschlag, offen |
| Autostart-Last (NordVPN, Docker, Chrome) | kein akutes Problem, da Commit jetzt frei | Vorschlag, offen |
| Geplanter Neustart                | entlädt Memory Compression + Restlecks           | **einplanen** (Abschnitt 6) |

## 6. Geplanter Neustart (einplanen, NICHT jetzt ausführen)

**Wann:** ein ruhiges Zeitfenster AUSSERHALB der Nachtsicherungen
(20:00 G:, 21:00 O:, 22:00 Posteingang) — sinnvoll: nach 22:30 Uhr oder
vor 07:30 Uhr morgens.

**Warum sicher (Live-Richtungen):**
- Die drei Handels-Dauerlauf-Stufen starten sich über ihre Wächter-Tasks
  bei der nächsten Anmeldung selbst (Anmeldung-Trigger). Ein Neustart ist
  damit Selbstheilung, kein Eingriff.
- Offene Live-Positionen laufen mit Herzschlag-Regel 180 min: selbst wenn
  der Dauerlauf nach dem Logon 2-3 h nicht startete, würde nichts
  unkontrolliert flachgestellt.
- Voraussetzung vor dem Neustart ist ein frischer Zwischenstand
  (20:00-Nachtsicherung) bzw. die Zweitkopie — nie um 19:50 neu starten.

**Ausführung:**
1. `spiegelstand.py` und offene Live-Positionen prüfen (sind gesichert /
   freigabefenster zu).
2. Neustart mit `Restart-Computer -Force` (Status: wartet auf ein
   ruhiges Fenster + Max' Freigabe des Zeitpunkts).
3. Nach dem Logon: Dauerlauf-Stufen (PID-Dateien), Gateway, Dashboard,
   MCP-Wachen-Prüfung `mcp-zombie-wache` und Commit-Lage prüfen.

## 7. Erfolgskriterien

- Commit dauerhaft ≥ 8 GB frei bei 40-50 Python-Prozessen.
- `mcp-zombie-wache` meldet nichts (gesund) über mehrere Tage.
- Nach dem Neustart laufen alle drei Risikostufen + Gateway + Dashboard
  wieder, Bedingung 4 (Spiegelung) unverändert byte-gleich.

## 8. Beschlossen

- **29.09.2026** — Max: Option 4, Reboot einplanen.
