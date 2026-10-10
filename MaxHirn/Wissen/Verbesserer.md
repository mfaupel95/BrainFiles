---
id: 20260906-verbesserer
title: 'Verbesserer — Spur 1'
tags: [handel]
created: 2026-09-06
updated: 2026-10-08
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

**Stand:** 2026-10-07

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
und `>= overfit_min_runden` OOS-Runden hat. Der Bericht sagt das in den
Warnungen selbst.

**Seit Stufe 1.5 (07.10.2026) gibt es eine vierte, zusätzliche Sperre:** ein
echter Holdout-Block. `suche()` schneidet vor Suche und Walk-Forward die
letzten `holdout_tage` Tage (60) ab; der Sieger muss die Basis danach **auf
diesem nie gesehenen Block** schlagen (`netto_gv_je_runde` höher, `n >=
holdout_min_runden` = 8) — sonst kein Vorschlag, `grund="Holdout nicht
bestanden"`, der abgelehnte Kandidat (`fast_kandidat`) wird nur im Digest
annotiert. Reicht die Historie nach Abzug des Holdouts nicht für
`oos_training_tage` plus `overfit_min_fenster` Testfenster, lehnt die Suche
mit `grund="zu wenig Historie fuer Holdout"` ab statt es stillschweigend zu
übergehen. `lauf.py` zieht dafür 540 statt 480 Tageskerzen. Ein echter
Train/Test-Split zwischen Auswahl und Prüfung fehlt aber weiterhin — die
Holdout-Sperre prüft nur den Sieger der Suche, nicht jeden Kandidaten während
des Abstiegs.

Aus [[Handelsbots]]: über lange Zeiträume lag jede getestete mechanische
Krypto-Strategie nahe null, leicht darunter. Der Verbesserer sucht deshalb
nicht den großen Wurf, sondern kleine, belegbare Verschiebungen — und die
Historie umfasst nur ein bis zwei Jahre Tageskerzen mit wenigen echten
Regimewechseln.

## Stand 2026-10-07

- **Ausbaustufe 1.5 fertig** (F7 Kerzen-Ausrichtung per Kalendertag in
  `ruecktest.ausrichten()`, F4 Holdout-Sperre in `suche()`): 5 Tasks,
  117 Modul-Tests grün. Ein zu junges Listing (< 90 % der Tage des längsten)
  fällt beim Ausrichten mit Hinweis heraus statt die Watchlist zu kürzen.
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

- Echter Train/Test-Split zwischen Auswahl und Overfitting-Prüfung während des
  Abstiegs (die Holdout-Sperre aus Stufe 1.5 prüft nur den fertigen Sieger).
- TP6: Ausweitung auf [[XPERP-Handel|Spur 2]] (Margin, Funding, Liquidation als
  dritter Ausstiegsgrund) und Spur 3 (Kraken, EUR, 0,80 % je Runde) — erbt
  Ausrichten und Holdout erst mit eigener Stufe.
- Aufnahme neuer Watchlist-Werte aus einem Kandidatenpool.

**Erledigt in Stufe 1.5 (07.10.2026):** Kerzen per Kalendertag statt
Listenindex ausrichten (F7); echter Holdout-Block als vierte Sperre (F4).

Vollständiger Entwurf mit Abnahmekriterien:
`../Werkstatt/Ablage/Plaene/spec-selbstverbessernder-handelsagent-2026-09-06.md` und
`../Werkstatt/Ablage/Plaene/spec-verbesserer-stufe-1-5-2026-10-04.md` (Werkstatt ist
Durchgangsware — diese Notiz ist die dauerhafte Fassung).

## Spur 2 (XPERP) — wöchentliche Schleife (10.10.2026)

Eigener Lauf `Agenten/Handel/verbesserer/xperp_lauf.py` (Routine
`Agenten/Routinen/verbesserer-spur2.ps1`, getrennt von Spur 1 wegen der Laufzeit).
Spec `Werkstatt/spec-verbesserer-spur2-schleife-2026-10-09.md`, Plan
`Werkstatt/plan-verbesserer-spur2-schleife-2026-10-10.md`.

- **Suchraum:** acht Schlüssel der `xperp/wachen.json` (Stop, Ziel,
  Einstiegsabschlag, fünf Trailing-Werte), Grenzen in `spuren.json`.
  `vola_tor_pa` und `min_umsatz_24h_usd` fehlen mit Absicht: der Rücktest liest
  sie nicht, eine Änderung hätte keine Wirkung.
- **Stufen:** Koordinatenabstieg → Sieb a–e (gleiche Fenster wie die Suche) →
  Holdout (letzte 20 Tage, nie in der Suche) → Max per `/ja`. Bestanden heißt
  „Vertrag erfüllt", nicht „live besser"; der Bericht zeigt Fenster, Abstand je
  Regel, Holdout und einen Absatz „Nicht geprüft".
- **Fenster:** Block `spur2` in `verbesserer/konfig.json` (80 Tage Rückblick,
  15er-Fenster, 20 Tage Holdout), am 10.10.2026 gemessen: erster Lauf rund 7 Minuten,
  danach Merkmals-Cache-Treffer. **Funding-Grenze:** OKX liefert Funding nur ca.
  94 Tage zurück; Instrumente, deren Funding nach dem Simulationsstart beginnt,
  werden ausgelassen und im Bericht genannt (78 von 233).
- **Holdout-Verschleiß:** `holdout_max_nutzungen` 8; Zähler in
  `verbesserer/xperp_holdout_nutzung.json` (Datei löschen = zurücksetzen), der
  Bericht meldet den Block danach als „verbraucht".
- **Abbruch:** fehlender Cache, `FundingLuecke` oder kein OKX-Instrumentenstamm
  schreiben einen Bericht mit Grund, nie ein `commit.txt`; Exitcode 1.
- **Rücknahme:** `anwenden.py` legt vor dem Schreiben ein `.bak` an
  (`verbesserer/bak/<zeit>/`), danach `git revert` des Anwende-Commits.
  Die Denylist (u. a. `max_hebel`, `llm_*`, `familien`, `trailing_aktiv`,
  `handel_erlaubt`) gilt beim Anwenden erneut; eine seit dem Lauf geänderte Wache
  (z. B. Kill-Switch) wird nicht überschrieben.
