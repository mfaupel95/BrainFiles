---
name: leitstand-handel
description: Use when the user asks about the trading system (Handel, Omnitrade, Spuren, Kurse), the Hermes profiles, or the Fremd-Repos in Werkstatt/Repos, or asks for an overview of the Leitstand
---

# Leitstand: Handel und Repos

## Grundregel

Der Leitstand ist **rein lesend**. Er handelt nicht, legt keine Orders an und
aendert keine Konfiguration. Order-Schritte laufen nur ueber die bestehenden
Skripte, nie aus diesem Plugin heraus.

Vor jedem Order-Schritt: zuerst den Preislauf frisch ausfuehren (`bot.py` mit
`--historie auto`). Nie mit Preisen aus einem frueheren Lauf arbeiten.

## Wo was liegt

- Handel: `Agenten/Handel/`. Zahlen einer Spur stehen in `<spur>/wachen.json`,
  nicht im Code. Betrieb: `dauerlauf.py`, Dict `SPUREN` ab Zeile 140.
- Auswertung: `Agenten/Handel/omnitrade_auswertung.py` (rein lesend).
- Repos: `Werkstatt/Repos/` (rund 55 Klone). `origin` ist `mfaupel95/<name>`,
  `upstream` das Original.
- Hermes-Profile: `Agenten/Hermes/profiles/` (rund 35 Profile).

## Was man nicht liest

- `Agenten/Handel/OpenAlice/`: fremdes Projekt, nur bei ausdruecklichem Bezug.
- `.venv`-Ordner: Interpreter, kein Projektcode.
- `Agenten/Handel/README.md` (53 KB): nicht als Einstieg, dafuer `AGENTS.md`.

## Git-Regeln im geteilten Arbeitsbaum

- Kein `git stash`. Eigene Arbeit sofort committen.
- Gemergt wird nur per PR, nie direkt nach `master` schieben.
- Nicht pushen, ohne dass Max es ausdruecklich anweist.
