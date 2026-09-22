---
id: 20260921-wiki-index
title: 'Wiki — Index'
tags: [betrieb, wiki]
created: 2026-09-21
updated: 2026-09-21
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
| [Lektionen/Git-und-Textdateien.md](Lektionen/Git-und-Textdateien.md) | Zeilenenden, .gitignore-Whitelist, index.lock, Fremdarbeit im Baum |
| [Lektionen/Tests.md](Lektionen/Tests.md) | Tests, die in echte Datenordner schreiben; Modulwaechter; sys.path-Reihenfolge |
| [Lektionen/Windows-Umgebung.md](Lektionen/Windows-Umgebung.md) | PYTHONHOME, Pfadaufloesung, Umgebungsvariablen, Auslagerungsdatei/Commit-Limit |
| [Lektionen/Wahrheit-pruefen.md](Lektionen/Wahrheit-pruefen.md) | Buch gegen Boerse, Zaehler gegen Ursache, „laeuft" gegen „laeuft richtig" |
| [Lektionen/Boersen-und-Schluessel.md](Lektionen/Boersen-und-Schluessel.md) | Zwei Werkzeuge auf einem Schluessel (Nonce-Einheit), zwei Namen fuer ein Programmpaar |

### Betrieb

| Seite | Zweck |
|---|---|
| [Betrieb/Hermes.md](Betrieb/Hermes.md) | Installation, Profile, config.yaml-Fallen, Gateway, Kompression, Delegation |
| [Betrieb/Wachen-und-Aufgaben.md](Betrieb/Wachen-und-Aufgaben.md) | Geplante Aufgaben, Cron-Wachen, Muster „leere Ausgabe = nichts senden" |
| [Betrieb/Sicherung-und-Laufwerke.md](Betrieb/Sicherung-und-Laufwerke.md) | C:/O:/G:/Q:, Junctions, Was versioniert und was gesichert wird |
| [Betrieb/Docker-und-Sandbox.md](Betrieb/Docker-und-Sandbox.md) | Docker-Terminal, windows-mcp als Rueckfallweg, weitergeleitete Variablen |

### Handel

| Seite | Zweck |
|---|---|
| [Handel/Spuren-Uebersicht.md](Handel/Spuren-Uebersicht.md) | Welche Spur existiert, welchen Orderweg sie hat, live oder Papier |
| [Handel/Gates-und-Freigabe.md](Handel/Gates-und-Freigabe.md) | Sperrenkette, Freigabefenster, AUTO_FREIGABE, Arming |
| [Handel/Kosten-und-Bedingungen.md](Handel/Kosten-und-Bedingungen.md) | Gebuehren, Bedingungen 1-5, f_max-Merksatz |
| [Handel/Boersen-und-Schluessel.md](Handel/Boersen-und-Schluessel.md) | OKX EEA/Kraken, Margin-Waehrung, welche Variable welche Spur liest |
| [Handel/Lektionen.md](Handel/Lektionen.md) | Buch war Fiktion, Stoerung vs. Runde, Papier im Live-Buch, Netzfehler im Zyklus |

### Werkzeuge und Offenes

| Seite | Zweck |
|---|---|
| [Werkzeuge/Fundus-Skills-Bots.md](Werkzeuge/Fundus-Skills-Bots.md) | Skill-Fundus, Hermes-Bibliothek, Repo-Bots, Katalog |
| [Werkzeuge/SkillSpector.md](Werkzeuge/SkillSpector.md) | Sicherheitsscan der Skills (NVIDIA SkillSpector): Aufruf, Falschmeldungen, Risikowert lesen |
| [Werkzeuge/kraken-cli.md](Werkzeuge/kraken-cli.md) | Kraken CLI selbst gebaut (Windows, kein WSL), Wrapper `Agenten/Werkzeuge/kraken.ps1`, die Schluessel-Namen-Falle, Papiermodus mit echter Gebuehr |
| [Offen/Entscheidungen.md](Offen/Entscheidungen.md) | Was auf eine Entscheidung von Max wartet |
| [Roadmap.md](Roadmap.md) | Zielkarte: gemessene Luecken nach Wirkung sortiert (Zuverlaessigkeit, Schlankheit, Personalisierung, Autonomie) |