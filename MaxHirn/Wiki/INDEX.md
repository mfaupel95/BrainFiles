---
id: 20260921-wiki-index
title: 'Wiki — Index'
tags: [betrieb, wiki]
created: 2026-09-21
updated: 2026-09-30
related: ['[[LEITFADEN]]', '[[Wissen/INDEX]]']
summary: 'Einstieg in das Agenten-Wiki: Verzeichnis aller Seiten mit Zweck, plus die Regel, wann hier etwas abgelegt wird.'
---

# Wiki — Index

Dieses Wiki ist der **Lernspeicher der Agenten** (Hermes, Claude, Codex). Es steht
neben `Wissen/` und ersetzt es nicht:

| Ort | Wem gehoert es | Inhalt |
|---|---|---|
| `Wissen/` | Max | Wer Max ist, Fristen, Vertraege, Hardware, Entscheidungen mit Begruendung |
| `Wiki/` (hier) | den Agenten | Was wir beim Arbeiten gelernt haben: Fallen, Merksaetze, Betriebsstand, offene Punkte |
| `../Agenten/Hermes/skills/` | den Agenten | Verfahren *zum Abarbeiten* — verweist auf Wiki-Seiten, wiederholt sie nicht |
| `../Werkstatt/` | allen | Durchgangsware: Zwischenstaende, Protokolle eines einzelnen Laufs |

Erreichbar auch als `O:\Wiki` (Junction, wie `Modelle` und `Werkstatt`).
In Obsidian erscheint der Ordner als `Wiki/` mit `[[Wikilinks]]` im Graphen.

## Regel fuer jede Sitzung

Arbeitsanweisung (was wohin gehoert, Hausformat, harte Regeln): [LEITFADEN.md](LEITFADEN.md).

1. **Vor einer Aufgabe:** hier nachsehen, wenn es um Betrieb, Handel oder Werkzeuge geht —
   die Seite nennt den Stand und die Falle, die Zeit gekostet hat.
2. **Nach einer Aufgabe:** jede Lehre, die in einem Monat noch gilt, in eine Seite
   schreiben (Skill `wiki-pflege`, Abschnitt „Ablage"). Kein Angebot, sondern Ablage.
3. **Kein Tagebuch.** Keine Sitzungsprotokolle, keine Ausgabe eines einzelnen Laufs.
   Nur was wieder gilt.

## Seiten

### Lektionen — teuer bezahlte Fallen

| Seite | Zweck |
|---|---|
| [Lektionen/Git-und-Textdateien.md](Lektionen/Git-und-Textdateien.md) | Zeilenenden, .gitignore-Whitelist, index.lock, Fremdarbeit im Baum, Zugangsdaten im Arbeitsbaum |
| [Lektionen/Tests.md](Lektionen/Tests.md) | Tests, die in echte Datenordner schreiben; Modulwaechter; sys.path-Reihenfolge |
| [Lektionen/Windows-Umgebung.md](Lektionen/Windows-Umgebung.md) | PYTHONHOME, Pfadaufloesung, Umgebungsvariablen, Auslagerungsdatei/Commit-Limit |
| [Lektionen/Wahrheit-pruefen.md](Lektionen/Wahrheit-pruefen.md) | Buch gegen Boerse, Zaehler gegen Ursache, „laeuft" gegen „laeuft richtig", deklariert gegen real |
| [Lektionen/Boersen-und-Schluessel.md](Lektionen/Boersen-und-Schluessel.md) | Zwei Werkzeuge auf einem Schluessel (Nonce-Einheit), zwei Namen fuer ein Programmpaar, eine Abweisung ohne Zeugen ist keine Messung |
| [Lektionen/Memory-Verluste.md](Lektionen/Memory-Verluste.md) | Memory-Eintraege belegbar verloren/ersetzt: falscher `old_text` loescht fremde Eintraege, `replaced_entries` lesen, `memory-verlust.py`, Pending-Queue |

### Betrieb

| Seite | Zweck |
|---|---|
| [Betrieb/Hermes.md](Betrieb/Hermes.md) | Installation, Profile, config.yaml-Fallen, Gateway, Kompression, Delegation |
| [Betrieb/Interpreter-Landkarte.md](Betrieb/Interpreter-Landkarte.md) | Welcher Python gehoert zu welcher Komponente, und wie man den falschen erkennt (Muster: 41 Sitzungen mit `ModuleNotFoundError`) |
| [Betrieb/Wachen-und-Aufgaben.md](Betrieb/Wachen-und-Aufgaben.md) | Geplante Aufgaben, Cron-Wachen, Muster „leere Ausgabe = nichts senden" |
| [Betrieb/Kanban-Boards.md](Betrieb/Kanban-Boards.md) | Die Boards des Hauses, der Board-Satz, `ready` wird sofort ausgefuehrt, gemessener Stand 30.09.2026 |
| [Betrieb/Sicherung-und-Laufwerke.md](Betrieb/Sicherung-und-Laufwerke.md) | C:/O:/G:/Q:, Junctions, Was versioniert und was gesichert wird |
| [Betrieb/Docker-und-Sandbox.md](Betrieb/Docker-und-Sandbox.md) | Docker-Terminal, windows-mcp als Rueckfallweg, weitergeleitete Variablen |
| [Betrieb/Systemleistung-2026-09-29.md](Betrieb/Systemleistung-2026-09-29.md) | Commit-Erschoepfung und MCP-Spawn-Sturm: Befund, Kur, zwei Lehren (30.09.2026 nachgetragen) |
| [Betrieb/Arbeitsverzeichnis.md](Betrieb/Arbeitsverzeichnis.md) | Hermes startet in `Agenten/Hermes`, Pfade bleiben relativ zur Wurzel: Anker `cd "$HERMES_HOME/../.."`, die gemessene Falle und was unberuehrt bleibt |
| [Betrieb/Fremd-Material.md](Betrieb/Fremd-Material.md) | Die Grenze zwischen eigenem Code und Fremd-Material: eine Quelle (`Agenten/FREMD-Liste.json`), der Leser `fremd.py`, 831 Dateien / 173.481 Zeilen eigener Code gegen 4,2 Mio. mit Fremdem |

### Handel

| Seite | Zweck |
|---|---|
| [Handel/Spuren-Uebersicht.md](Handel/Spuren-Uebersicht.md) | Welche Spur existiert, welchen Orderweg sie hat, live oder Papier |
| [Handel/Gates-und-Freigabe.md](Handel/Gates-und-Freigabe.md) | Sperrenkette, Freigabefenster, AUTO_FREIGABE, Arming |
| [Handel/Kosten-und-Bedingungen.md](Handel/Kosten-und-Bedingungen.md) | Gebuehren, Bedingungen 1-5, f_max-Merksatz |
| [Handel/Boersen-und-Schluessel.md](Handel/Boersen-und-Schluessel.md) | OKX EEA/Kraken, Margin-Waehrung, welche Variable welche Spur liest |
| [Handel/Lektionen.md](Handel/Lektionen.md) | Buch war Fiktion, Stoerung vs. Runde, Papier im Live-Buch, Netzfehler im Zyklus |
| [Handel/Backtest-Fundament.md](Handel/Backtest-Fundament.md) | Historische Daten 2021-2026, die ersten Zahlen je Spur, vier Fallen des Replays |
| [Handel/Strategie-Kennzahlen.md](Handel/Strategie-Kennzahlen.md) | Formelblatt von Max: t-Statistik der Expectancy, Stop aus der MAE, was zeitbasiert NICHT geht |
| [Handel/Freqtrade-Bots.md](Handel/Freqtrade-Bots.md) | Die drei Moon-Dev-Bots: was laeuft, der erste Backtest (alle negativ, Verlust = Gebuehr), die Loopback-Falle |
| [Handel/Dauerlauf-Tode.md](Handel/Dauerlauf-Tode.md) | T-193: Rueckgabe 143 = MSYS-timeout (Fingerabdruck-Tabelle), Sperren-Churn, Speicherdruck, die neue Wache |
| [Handel/omnitrade-Spur.md](Handel/omnitrade-Spur.md) | Weg B: der Rust-Lauf entscheidet, Kraken ordert — zwei Zeugen statt state=running, Zustand statt Orderliste, echter Verkaufspreis |
| [Handel/nautilus-rust-Quant-Ebene.md](Handel/nautilus-rust-Quant-Ebene.md) | Die fuenf Rust-Crates als Lehrstueck: harte Ebenen-Grenze, 20 Tests gruen, Gate lehnt das Demo-Buch ab — und warum hier kein Atlas moeglich ist |

### Werkzeuge und Offenes

| Seite | Zweck |
|---|---|
| [Werkzeuge/MoonDev-GUI-und-RBI.md](Werkzeuge/MoonDev-GUI-und-RBI.md) | Startfenster des moon-dev-Klons: warum die RBI-Knoepfe starben (UTF-8, src/.env), conda-Ausfuehrung ersetzt, und die nachgemessenen Strategie-Ergebnisse (95-97 % Verlust gegen +128 % Buy & Hold) |
| [Werkzeuge/repos-zentrale.md](Werkzeuge/repos-zentrale.md) | Startfenster fuer REPOS (46 Klone), WERKSTATT (Projekte, Datenfelder, Ablagen) und HANDEL (Spuren und Werkzeuge, 162 Zeilen): Gruppen, Startbelege, der Bereich "Was dieses Projekt kann" mit anklickbaren Befehlen, Kopieren und Bot-Auftrag; dazu die Layout-Lehre (Spaltenbreiten aus Baumbreite und DPI rechnen, `stretch=False`) |
| [Werkzeuge/Fundus-Skills-Bots.md](Werkzeuge/Fundus-Skills-Bots.md) | Skill-Fundus, Hermes-Bibliothek, Repo-Bots, Katalog |
| [Werkzeuge/jevgrep.md](Werkzeuge/jevgrep.md) | Fremd-CLI `jg`: Fragen an einen unbekannten Codebestand, laeuft unter Windows (npm-`os`-Falle), rund 4 US-Cent je Suche — braucht aber einen Jev-Schluessel; das lokale Urteil ist durchgerechnet und verworfen |
| [Werkzeuge/Claude-Red-und-nerd-Bot.md](Werkzeuge/Claude-Red-und-nerd-Bot.md) | Offensive-Security-Sammlung claude-red als Fundus-Faehigkeit, der Bot `nerd`, Defender sperrt vier Skill-Dateien |
| [Werkzeuge/SkillSpector.md](Werkzeuge/SkillSpector.md) | Sicherheitsscan der Skills (NVIDIA SkillSpector): Aufruf, Falschmeldungen, Risikowert lesen |
| [Werkzeuge/kraken-cli.md](Werkzeuge/kraken-cli.md) | Kraken CLI selbst gebaut (Windows, kein WSL), Wrapper `Agenten/Werkzeuge/kraken.ps1`, die Schluessel-Namen-Falle, Papiermodus mit echter Gebuehr |
| [Werkzeuge/kraken-abweisungs-sonde.md](Werkzeuge/kraken-abweisungs-sonde.md) | Zeuge und Wache fuer zeitweise Kraken-Abweisungen: vier Wege (offen/signiert x Spot/Futures), Kuehlzeit gegen den Lockout-Timer, Rohantwort im Fehlerfall |
| [Werkzeuge/Ollama-Bruecke.md](Werkzeuge/Ollama-Bruecke.md) | Der eine Weg zum lokalen Sprachmodell-Urteil ohne Schluessel: Ollamas `/v1` liefert bei Denk-Modellen leeren content, die Bruecke ruft nativ mit `think:false`; Wache und Treiber-Anschluss |
| [Werkzeuge/openmontage.md](Werkzeuge/openmontage.md) | Video- und Bilderzeugung: Zero-Key-Demos, welcher Anbieterschluessel wirklich traegt, lokale Diffusion auf der 3060 Ti, CUDA-Wheel-Falle |
| [Werkzeuge/Kronos.md](Werkzeuge/Kronos.md) | Kerzen-Foundation-Modell lokal: Aufruf, der pandas-2.2.2-Absturz (`-X faulthandler`), erster Messbefund gegen die Nullinie |
| [Werkzeuge/Fomo-Radar.md](Werkzeuge/Fomo-Radar.md) | Robinhood-Chain-Beobachtung: was schluessellos laeuft (147 Wallets, 65 Fills), Fallen, Anschluss als Papierspur |
| [Werkzeuge/Marktdaten-und-Bot-markt-recherche.md](Werkzeuge/Marktdaten-und-Bot-markt-recherche.md) | Marktdaten ohne Schluessel (OKX/Yahoo/RSS), das Werkzeug `marktdaten.py` und der Bot `markt-recherche` |
| [Werkzeuge/Marktbreite-Reihe.md](Werkzeuge/Marktbreite-Reihe.md) | Marktbreite als Zeitreihe (`breite.py`), das Fenster-Problem (Startwert drehte das Vorzeichen), Wachenregeln, acht Monate Baerenmarkt vor einem September-Gipfel |
| [Werkzeuge/okx-bot-waechter.md](Werkzeuge/okx-bot-waechter.md) | Waechter ueber die echten OKX-Bots (Future DCA/Grid): letzte kaufbare Grenze, Munition, Liquidation; stoppen, vorschlagen, bauen |
| [Werkzeuge/Bonsai-2-27B.md](Werkzeuge/Bonsai-2-27B.md) | Ternares 27B-Modell lokal (5,95 GB, PrismML-Fork von llama.cpp): 32 t/s auf der 3060 Ti bei 8k Kontext, kein Hermes-Agent-Modell (64k-Grenze), Ollama kann die Dateien nicht laden |
| [Werkzeuge/ai4trade-AI-Trader.md](Werkzeuge/ai4trade-AI-Trader.md) | Signalplattform ai4trade.ai: Agent `HermesMax2` (ID 25973), Heartbeat per Cron gepollt |
| [Werkzeuge/config-gegenprobe.md](Werkzeuge/config-gegenprobe.md) | Jede Behauptung der Hermes-Configs gegen die Wirklichkeit: Programmpfade, lokale Adressen, lokale Modellnamen; Wache montags, Befund 29.09.2026 |
| [Werkzeuge/Paperclip.md](Werkzeuge/Paperclip.md) | Paperclip-CLI (`paperclipai`, Node): der verwaltete Install-Weg scheitert unter Windows an Doppelpunkten im Sperr-Dateinamen, deshalb npm in eigenem Prefix plus zwei PATH-Weiterleitungen in `~/.local/bin`; kein `update`/`uninstall`, aktualisiert wird per npm |
| [Offen/Entscheidungen.md](Offen/Entscheidungen.md) | Was auf eine Entscheidung von Max wartet |
| [Roadmap.md](Roadmap.md) | Zielkarte: gemessene Luecken nach Wirkung sortiert (Zuverlaessigkeit, Schlankheit, Personalisierung, Autonomie) |
| [[Hermes-Wartung]] | `hermes update` fahren: Ablauf, EXIT 1, Gateway-Task, blockierte Werkzeuge | Werkzeuge |
