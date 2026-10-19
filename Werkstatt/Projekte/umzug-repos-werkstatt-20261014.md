# Umzug: Werkstatt/Repos/* -> Werkstatt/ (Auftrag Max 14.10.2026)

## Auftrag
1. Alle Repos aus Werkstatt/Repos direkt nach Werkstatt/ verschieben, alle Verweise nachziehen.
2. Alle auf GitHub PRIVAT laufenden Repos loeschen (nur lokal betreiben; Origin/Fork-Remote aus den Klonen).
   Ausnahme: mfaupel95/BrainFiles (Workspace-Remote, Push-Routinen haengen dran; Entscheidung Max offen).

## Fakten (gemessen 14.10.)
- Werkstatt = Junction auf O:\Werkstatt (intakt).
- Werkstatt/Repos: 53 Git-Klone + 6 lose Dateien (rule_repo-bots.*, rrb.fix).
- Kollisionen: OmniRoute (echter Zweitklon; Produktionsklon liegt direkt in Werkstatt mit origin=diegosouzapw) ->
  Repos-Klon nach Werkstatt/Ausgemustert/OmniRoute-duplikat-20261014. intelligent-trading-bot (Junction auf
  Werkstatt\intelligent-trading-bot) -> nur Junction entfernen.
- Live-Prozesse aus Repos: kraken-cli-MCP x7 (config.yaml:1204), ziplime-MCP x10 (config.yaml+MCP-Manifest),
  moon-dev-Agenten x9 (moondev_dauerlauf), radar-sammler watch x2 (scripts/radar-sammeln.py:36).
- .gitignore: `Werkstatt/*/` (Z.484) ignoriert die Klone auch am neuen Ort -> nur Kommentare anpassen.
- 96 private GitHub-Repos (95 + BrainFiles), davon ~85 `*-privat`-Mirrors (Remote 'privat', mit Git-Remote-Backup
  angelegt, keine Routine recreiert sie).

## Ablauf (belegt je Schritt)
A. Referenzen umschreiben (getrackte Dateien, ohne TASKS.md): Werkstatt/Repos -> Werkstatt (alle Schreibweisen).
B. Prozesse stoppen (kraken-cli/ziplime/radar/moondev).
C. Verschieben (PowerShell Move-Item; Sonderfaelle OmniRoute + itb-Junction; lose Dateien mit).
D. Neustart: moondev-Task, Radar-Cron, MCP-Spawn (neue Pfade).
E. Gegenprobe: git grep Reste, repos-zentrale-Tests, fundus-suche, Pfad-Existenz, dauerlauf.log.
F. GitHub: private Repos loeschen (gh repo delete), Remotes in Klonen auf origin=upstream umstellen, Doku nachziehen.
G. Commit (eigene Pfade, eigener Index) + Bericht.

## Offen fuer Max
- BrainFiles-Remote loeschen? (Empfehlung: NEIN - Push-Routinen + Team-Backup)
- public Forks bleiben (nur 'als privat laufende' gemaess Auftrag).
