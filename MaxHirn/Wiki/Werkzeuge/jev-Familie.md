---
id: 20261002-jev-familie
title: 'Die Jev-Repos im Haus: jevgrep, fast-jev-compaction, jev-trader, jev-chat-jarvis'
tags: [werkzeuge, fremd, jev, code]
created: 2026-10-02
updated: 2026-10-02
related: ['[[Werkzeuge/jevgrep]]', '[[Handel/Spuren-Uebersicht]]', '[[Betrieb/Fremd-Material]]']
summary: 'Vier Klone aus der Jev/TypeSafe-Welt: was jeder tut, was davon laeuft, was einen Schluessel braucht und wo Mercury (ueber die Bruecke) passt - und wo nicht.'
---

# Die Jev-Familie im Haus

Alle vier liegen als Klone in `Werkstatt` (Fork `mfaupel95/...`). Gemeinsam ist
ihnen **ein Modell**: Jev von TypeSafe — kein Chat-Modell, sondern ein **Richter**, der
einen Zustand gegen typisierte Fragen auswertet (`noul` = ja/nein-Wahrscheinlichkeit,
`choice`, `score`). Deshalb sprechen sie alle denselben Endpunkt an:
`POST <basis>/systemone`.

| Repo | Was es tut | Stand im Haus | Braucht |
|---|---|---|---|
| **jevgrep** | Code per Frage finden (Dateien + Quelltextausschnitte) | **laeuft**, auf Mercury 2.5 ueber die eigene Bruecke | `INCEPTION_API_KEY` (gesetzt) |
| **fast-jev-compaction** | Claude-Code-Plugin: wirft bei der Kompaktierung alte Werkzeugaufrufe weg, die Jev fuer entbehrlich haelt — nichts wird umgeschrieben | Klon vorhanden, **nicht eingebunden** (kein Eintrag in `~/.claude/plugins`) | `TYPESAFE_API_KEY` |
| **jev-trader** | Eine Entscheidung je Monad-Block (~300 ms): Jev sieht das Kuru MON-USDC-Orderbuch und antwortet buy/sell; je Block eine Post-Only-Limit-Order | Klon vorhanden, `.env` eingerichtet, **`MODEL=mock`, `DRY_RUN=true`**, kein privater Schluessel, laeuft nicht | `TYPESAFE_AI_API_KEY` (leer) fuer echtes Jev |
| **jev-chat-jarvis** | Android-App (11+), chinesisch: liest in Chat-Apps mit und schlaegt Antworten vor, ein Klick fuellt sie ein | Klon vorhanden, **nicht gebaut/installiert** | eigene App-Anmeldung |

## Was Mercury fuer die Familie bedeutet

Die eigene Bruecke (`Agenten/Werkzeuge/jevgrep/jev_bruecke.py`) uebersetzt genau dieses
`/systemone`-Protokoll auf ein OpenAI-kompatibles Modell. Sie kann deshalb **jeden** der
vier bedienen — mit einer Einschraenkung, die man messen muss: **Zeit**.

| Bedarf | Mercury ueber die Bruecke | Urteil |
|---|---|---|
| jevgrep (60-400 Anfragen je Suche, gebuendelt) | Median 1,40 s je Anfrage | **passt** (56,7 s je Suche) |
| fast-jev-compaction (eine Anfrage je Kompaktierung) | ~1,5 s | **passt**, aber nur wenn das Plugin eine eigene Basis-URL akzeptiert (`TYPESAFE_API_KEY`/`SYSTEM_ONE_URL` stehen im Code fest) |
| jev-trader (eine Entscheidung je Block, ~300 ms) | ~1,5 s | **passt NICHT** — 5x zu langsam; dafuer ist der Mock-Momentum-Heuristik-Modus gedacht |

Mercury bringt 10 Mio. Gratis-Token je Schluessel mit (Free-Plan 100 Mio.), danach
0,04 USD/1M in der Aktion. Fuer jev-traders Dauerbetrieb waere selbst ein bezahlter
Mercury-Zugang teuer (jede Entscheidung ein Aufruf) — dort gehoert ein echtes
TypeSafe-Konto hin, nicht die Bruecke.

## Merksatz

`/systemone` ist der gemeinsame Stecker. Wer ihn einmal bedienen kann (die Bruecke),
versorgt die ganze Familie — solange die **Latenz** zur Frage passt: gebuendelte
Recherche ja, Sekundentakt nein.