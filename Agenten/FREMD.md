# Fremd-Material im BrainFiles-Baum

Diese Datei ist die **lesbare Fassung** der Grenze zwischen eigenem Code und
Fremd-Material. Die maschinenlesbare Quelle ist `Agenten/FREMD-Liste.json`; gelesen
wird sie von `Agenten/Werkzeuge/fremd.py` (Python) und per `ConvertFrom-Json` von
den PowerShell-Werkzeugen. Ein Test vergleicht die Pfadmengen dieser Datei und der
JSON - laufen sie auseinander, wird es rot.

## Warum es das gibt

Fremd-Material liegt **mitten in eigenen Ordnern**. `Agenten/Handel/OpenAlice`
allein stellt 482 Dateien und 513.266 Zeilen - **81 %** aller Zeilen in
`Agenten/Handel` (unser Handelscode: 508 Dateien, 122.253 Zeilen). Jede
Bestands-, Such- oder Aufraeumfrage musste das bisher im Kopf abziehen, und jedes
Werkzeug hatte eine eigene Vorstellung davon, was dazugehoert.

## Was fremd heisst

Material, das wir **nicht pflegen** - ein Klon, ein Import, ein Fremdprojekt im
eigenen Baum. Kriterium ist nicht Sprache, Groesse oder Qualitaet, sondern die
Frage: *aendern wir es, oder benutzen wir es?*

Daraus folgen drei Regeln:

1. **Fremdes wird nicht gezaehlt.** Bestand, Umfang, Doppelungen laufen ohne es -
   mit einem Schalter, um es dazuzunehmen (`bestand.py --mit-fremd`).
2. **Fremdes wird nicht aufgeraeumt.** Kein Umbenennen, Verschieben, Loeschen,
   kein "Verbessern" in fremden Baeumen.
3. **Fremdes wird nicht verschwiegen.** Die Zentrale zeigt es als Zeile mit Rolle
   und Herkunft - man soll es finden, nur nicht mitzaehlen.

**Nicht** fremd sind: eigene Spuren und Werkzeuge, Laufzeitstaende (unser Betrieb,
nur nicht versioniert) und `Werkstatt` als Ganzes (das traegt eigene Projekte;
nur die Klonsammlung `Werkstatt` steht in der Liste).

## Die Liste

| Pfad | Art | Herkunft | Regel |
| `Agenten/Werkzeuge/jevgrep/node_modules` | Fremd-Paket | npm-Paket @dzhng/jevgrep 0.7.0 samt Abhaengigkeiten (typescript, web-tree-sitter) | nur benutzen, nie aendern |
| `Agenten/Handel/OpenAlice` | Fremdprojekt | Klon eines fremden Quant-Frameworks (eigene workspaces/, runs/, .claude/) | nur lesen |
| `Agenten/MCP-Server/ant.dir.ant.anthropic.filesystem` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.cursortouch.windows-mcp` | Fremd-Klon | ueber ant installierter MCP-Server (Windows-Zugriff vom Host) | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.anthropic.pdf-server-mcp` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.blender.blender-mcp` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.canva.affinity` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.jerichosequitin.metabase` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.mnemoverse.mcp-memory-server` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.oogunbiyi21.stats-compass-mcp` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.perseus-computing-llc.perseus-vault` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.revolut-engineering.revolut-x-api` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.socketdev.socket-mcp` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.tooluniverse.tooluniverse-mcp` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/MCP-Server/ant.dir.gh.wonderwhy-er.desktopcommandermcp` | Fremd-Klon | ueber ant installierter MCP-Server | nur lesen |
| `Agenten/Hermes/tools` | Fremd-Werkzeuge | von Hermes heruntergeladene Laufzeiten (python, node, git, bun, chromium, ffmpeg, llama.cpp, ripgrep, uv, cua-driver, agent-browser) | nur lesen |
| `Agenten/Hermes/skills/OmniRoute` | Fremd-Klon | Klon; traegt geladene Skills (cli-models, omni-mcp, omni-models) | nur lesen |
| `Agenten/Hermes/skills/claude-code` | Fremd-Klon | Klon; traegt den geladenen Skill plugin-dev/mcp-integration | nur lesen |
| `Agenten/Hermes/skills/onchainos-skills` | Fremd-Klon | Klon; traegt die vier geladenen okx-*-Skills | nur lesen |
| `Agenten/Hermes/skills/one-skill-to-rule-them-all` | Fremd-Klon | Klon; traegt den geladenen Skill task-observer | nur lesen |
| `Agenten/Hermes/skills/one-skill-to-rule-them-all-main` | Fremd-Klon | Klon (Zweitfassung) | nur lesen |
| `Werkstatt` | Klonsammlung | 53+ Klone fremder Projekte direkt in Werkstatt (seit 14.10.2026; vorher Werkstatt/Repos), nur Git-Ordner zaehlen | nur lesen; Pflege ausschliesslich ueber Agenten/Werkzeuge/repos-updaten.py |
| `Werkstatt/Ausgemustert` | Stillgelegt | stillgelegte Anlagen (u.a. die alte Hermes-Installation samt eigener Python-Laufzeit) | nur lesen |
| `Werkstatt/repos-verschoben-aus-skills` | Fremd-Klone | am 21.09.2026 aus Agenten/Hermes/skills ausgelagerte Fremd-Klone (unsloth, nautilus_trader, EasyCLIProxyAPI, chromaprint, public-apis, acoustid-index) | nur lesen |
| `Werkstatt/Worktrees` | Klonsammlung | Arbeitskopien (worktrees) der eigenen Forks, u.a. copilot-worktrees | nur lesen |
| `Werkstatt/zustand-sicherung-20260916-015331` | Altstand | Zustandssicherung vom 16.09.2026 | nur lesen |
| `Werkstatt/handel-stack` | Altstand (Spiegel 18.09.) | privater GitHub-Spiegel von Agenten/Handel, Stand 18.09.2026 (mfaupel95/handel-stack) | nur lesen |
| `Werkstatt/CryptoPredictions` | Fremd-Klon | geklontes Fremd-Repo (Kursvorhersage-Toolbox) | nur lesen |
| `Werkstatt/CryptoTrade` | Fremd-Klon | geklontes Fremd-Repo (LLM-Agent fuer Krypto-Handel) | nur lesen |
| `Werkstatt/FinRL` | Fremd-Klon | geklontes Fremd-Repo (Financial Reinforcement Learning) | nur lesen |
| `Werkstatt/RLTrader` | Fremd-Klon (unsere Arbeit) | notadamking/RLTrader (github), Vorgaenger von TensorTrade - upstream seit 2019 ruhend; Klon mit eigenem .git, Fernsicherung als privates Repo mfaupel95/rltrader (01.10.2026) | nur lesen; Betrieb ueber rltrader.cmd (Docker, CPU) |
| `Werkstatt/intelligent-trading-bot` | Fremd-Klon | geklontes Fremd-Repo (Handelsbot) | nur lesen |
| `Werkstatt/freqtrade` | Fremd-Klon | Klon des fre freqtrade-Frameworks | nur lesen |
| `Werkstatt/OmniRoute` | Fremd-Klon (in Betrieb) | Quell-Klon von OmniRoute - laeuft als Router auf Port 20128 | nur lesen; Start ueber Agenten/Routinen/omniroute-start.ps1 |
| `Werkstatt/omnitrade` | Fremd-Klon (unsere Arbeit) | Rust-Workspace omnitrade (Fork mfaupel95/omnitrade, upstream jackby03) | nur lesen; Arbeit ueber das eigene Repo |

## Wie man sie aendert

1. Eintrag in `Agenten/FREMD-Liste.json` ergaenzen (Pfad relativ zur Wurzel, mit
   `/`, ohne `..` und ohne Laufwerksbuchstaben).
2. Dieselbe Zeile hier eintragen (oder die Tabelle neu erzeugen:
   `python Agenten/Werkzeuge/fremd.py --tabelle`).
3. Pruefen: `python Agenten/Werkzeuge/fremd.py --pruefen` muss "gesund" sagen,
   `python -m unittest discover -s Agenten/Werkzeuge/tests` muss gruen bleiben.

Ein Eintrag ist eine **Aussage ueber Herkunft** und wird von Hand gepflegt - nie
geraten. Die `warum`-Zeile nennt den Grund, der zaehlt (Groesse, Zeilen, oder
"traegt geladene Skills").

## Was die Liste nicht ist

Kein Manifest (sie startet nichts), keine Sperrliste (sie verhindert kein Lesen -
im Gegenteil, sie macht Fremdes auffindbar) und kein Aufraeumauftrag.
