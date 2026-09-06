---
id: 20260906-verbesserer
title: 'Verbesserer — Spur 1'
tags: [handel]
created: 2026-09-06
updated: 2026-09-06
related: [20260831-marktscanner, 20260830-handelsbots, 20260902-handelsregeln, 20260830-schutzregeln, 20260830-routinen]
summary: 'Wöchentliche Schleife, die aus Journal und Kurshistorie out-of-sample geprüfte Vorschläge für bessere Scanner-Parameter macht — Entscheidung, Grenzen, schwache Stelle, Stand.'
---

# Verbesserer — Spur 1

Am 06.09.2026 auf Max' Anweisung gebaut („bau einen selbstverbessernden AI
Trading Agent"): ein Modul `../Agenten/Handel/verbesserer/`, das **wöchentlich**
das Handelsjournal und OKX-Tageskerzen liest, in einem fest begrenzten
Parameterraum per Walk-Forward einen besseren Kandidaten sucht und daraus
**einen begründeten Vorschlag** ablegt. Angewandt wird nichts von selbst — der
Vorschlag geht per Telegram an Max, `/ja` im [[Routinen|Dauerlauf]] wendet ihn
an und committet ihn einzeln.

Erste Ausbaustufe: nur [[Marktscanner|Spur 1]] (Scanner/OKX Spot). Code,
Dateien und Bedienung im Detail: `../Agenten/Handel/verbesserer/README.md`.
Diese Notiz hält fest, was dort **nicht** steht: die Entscheidung, ihre
Grenzen, die schwache Stelle und den Stand.

**Warum:** 16 Tasks subagent-getrieben, mit Zweig-Review und Fix-Welle —
mehrere Tage Arbeit. Ohne diese Notiz beginnt die nächste Ausbaustufe (Spur 2/3)
bei der Frage von vorn, warum die Overfitting-Sperre so schwach ist und was der
Verbesserer nie anfassen darf.

**Stand:** 2026-09-06

## Die Entscheidung

Verworfen wurde (B) nur Auswerter + LLM ohne Backtest — das wären Vorschläge
ohne Out-of-sample-Prüfung, genau der Fehler aus [[Handelsbots]]. Und (C)
kontinuierliche Optimierung im Dauerlauf — höchste Komplexität, stärkster
Regelkonflikt, Overfitting durch Dauerlauf auf denselben Daten.

Gewählt: ein **eigenständiges Modul mit fester Kette** —
Auswerter → Walk-Forward-Backtest → beschränkte Suche → Vorschlags-Bauer →
LLM-Digest → Telegram → CRLF-schonendes Anwenden. Deterministisch; das LLM
annotiert nur, es entscheidet nichts.

## Was er ändern darf — und was nie

Änderbar (Whitelist in `verbesserer/spuren.json`, jeweils in festem
Wertebereich): die Tore `mindest_score` / `max_volatilitaet_pa` /
`mindest_chance_risiko`, der Pflicht-Stop-Bereich (nur innerhalb 4–15 %, nie
abschaltbar), `abklingzeit_tage`, die Chance-/Risiko-Gewichte in `bewertung.py`,
und die Watchlist (nur Streichen von Werten mit negativem OOS-Beitrag; Aufnahme
neuer Werte erst Phase 2).

**Nie:** `handel_erlaubt`, die fixen Deckel (`max_pro_trade_usd`,
`max_gesamt_usd`, `max_offene_positionen`), die Blöcke `freigabe` / `drawdown` /
`herzschlag` / `kill_switch`. Das steht als **fest verdrahtete Denylist** in
`anwenden.py` und schlägt jede Whitelist — egal, was `spuren.json` deklariert.
`anwenden.py` prüft beim Anwenden zusätzlich jeden geänderten Wert erneut gegen
seinen Bereich (fail-closed: nicht-numerischer oder gelöschter Schlüssel →
Abbruch).

`auto_anwenden` steht auf `false` und es gibt keinen Code, der `true`
auswertet. Den Schalter umzulegen braucht erst eine Änderung an
[[Handelsregeln]] (Stufe-1-Regel: „vorgeschlagen — mit der Rechnung dazu —,
nicht heimlich eingesetzt").

## Der Anwende-Weg

`lauf.py` schreibt **nur** nach `verbesserer/berichte/<datum>-spur1/`
(`bericht.md` mit den vier Pflichtzahlen, `wachen.neu.json`, `bewertung.patch`,
`commit.txt`). Einziger schreibender Pfad in die Scanner-Dateien ist
`anwenden.py`, aufgerufen aus dem Telegram-`/ja` im Dauerlauf: Arbeitsbaum
prüfen → Denylist + Bereich → zeitgestempeltes `.bak` → `wachen.json` per
gezielter Text-Ersetzung (kein `json.dump`, sonst CRLF→LF, siehe
[[Schutzregeln]] / Memory `crlf-im-vault`), `bewertung.py` per Patch →
`git add` nur der zwei betroffenen Dateien → `git commit -F commit.txt`.
`/nein` schiebt den Ordner nach `berichte/abgelehnt/`.

Mitgeliefert wurde eine **Angleichung von `scanner/handeln.py`**: der Papierpfad
zieht jetzt dieselbe `GEBUEHR_PCT = 0.0005` je Seite ab wie der Backtest —
vorher rechnete er ohne Gebühr, was [[Handelsregeln]] einen Fehler nennt.
Journalrunden vor dem 06.09.2026 tragen keine Gebühr und sind nicht direkt
vergleichbar.

## Die schwache Stelle

Die Overfitting-Sperre ist **ein schwaches Sieb**: Auswahl und Prüfung nutzen
dieselbe Kennzahl über dieselben Testfenster. Ein Kandidat wird nur
vorgeschlagen, wenn er die Basis im Aggregat **und** in einer Mehrheit der
Einzelfenster schlägt (mehr als die Hälfte, mindestens `overfit_min_fenster`)
und `>= overfit_min_runden` OOS-Runden hat. Ein echter Train/Test-Split fehlt —
das ist bewusst Folgearbeit (Redesign von `ruecktest.py`/`suche.py`), sicher
solange Papierbetrieb läuft. Der Bericht sagt das in den Warnungen selbst.

Aus [[Handelsbots]]: über lange Zeiträume lag jede getestete mechanische
Krypto-Strategie nahe null, leicht darunter. Der Verbesserer sucht deshalb
nicht den großen Wurf, sondern kleine, belegbare Verschiebungen — und die
Historie umfasst nur ein bis zwei Jahre Tageskerzen mit wenigen echten
Regimewechseln.

## Stand 2026-09-06

- **Ausbaustufe 1 fertig und nach `master` gemergt** (Merge `6795a31`,
  16 SDD-Tasks + Zweig-Review + Fix-Welle, 100 Modul-Tests grün, eigenes
  stdlib-only venv `verbesserer/.venv` auf Python 3.13.15).
- **Aufgabe `MaxHirn-Verbesserer`** ([[Routinen]]): sonntags 08:30, direkt nach
  `MaxHirn-Handel-Wachen` (08:00). Wrapper `Agenten/Routinen/verbesserer.ps1`.
- **Erster Lauf am 06.09.2026** von Hand ausgelöst: Kerzen für 15 Paare geholt,
  ein Vorschlag erzeugt (Basis −0,057 → 1,016 netto_gv_je_runde, schlägt in
  7 von 12 Fenstern, 36 OOS-Runden; Vorschlag: Pflicht-Stop-Min 4→5 %,
  Abklingzeit 3→4 Tage, Watchlist 15→11). Liegt offen in
  `berichte/2026-09-06-spur1/` und wird beim nächsten Dauerlauf-Zyklus per
  Telegram angefragt.
- **Live nie scharf** — Spur 1 steht weiter auf `handel_erlaubt: false`
  ([[Marktscanner]], „Drei Sperren").

## Folgearbeit (nicht in dieser Stufe)

- Echter Train/Test-Split im Walk-Forward (die schwache Stelle oben).
- Kerzen per Zeitstempel-Raster statt Listenindex ausrichten — vor jedem
  Watchlist-Ausbau.
- TP6: Ausweitung auf [[XPERP-Handel|Spur 2]] (Margin, Funding, Liquidation als
  dritter Ausstiegsgrund) und Spur 3 (Kraken, EUR, 0,80 % je Runde).
- Aufnahme neuer Watchlist-Werte aus einem Kandidatenpool.

Vollständiger Entwurf mit Abnahmekriterien:
`../Werkstatt/spec-selbstverbessernder-handelsagent-2026-09-06.md` (Werkstatt
ist Durchgangsware — diese Notiz ist die dauerhafte Fassung).
