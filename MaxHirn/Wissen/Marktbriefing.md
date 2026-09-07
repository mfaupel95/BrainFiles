---
id: 20260907-marktbriefing
title: 'Marktbriefing — Routine und Verfahren'
tags: [handel, finanzen]
created: 2026-09-07
updated: 2026-09-07
related:
  - id: 20260830-routinen
  - id: 20260831-marktscanner
  - id: 20260830-marktlage-august-2026
  - id: 20260907-marktlage-september-2026
summary: 'Lesende Routine, die aus den fertigen traderhub-Boards einen geprüften Marktüberblick zusammenträgt und als Monatsnotiz fortschreibt.'
---

# Marktbriefing — Routine und Verfahren

Ein wiederkehrender Marktüberblick aus **geprüften Zahlen**, nicht aus einer
Meinung. Entstanden am 07.09.2026 aus einer Sitzung, die „market" nur mit einem
Wort anfragte — der Überblick war in fünf Minuten aus `traderhub` zusammen und
damit ein Kandidat für eine Routine.

Abgrenzung: [[Marktscanner]] ist der OKX-Krypto-Scanner mit begrenztem
Selbsthandel; er entscheidet und handelt. Das Marktbriefing **liest nur** — kein
Handel, kein Versand, keine Prognose mit Zeithorizont.

## Skill und Ablauf

- **Skill:** `.claude/skills/marktbriefing/SKILL.md` (Arbeitskopie im Vault,
  siehe [[Skill-Bibliothek]]). Aufruf `/marktbriefing`.
- **Boards (fest):** `traderhub board get --board macro`, `--board movers`,
  `traderhub board rotation`. Optional `--board calendar`, `--board fed`,
  `--board term-structure`. `alice analysis` nur auf ausdrücklichen Wunsch.
- **Ausgabe:** Zinsen-&-Makro-Tabelle · Sektorrotation (relative Stärke über
  1W/1M/3M/6M) · Einzelwerte (Gewinner/Verlierer/aktiv) · ein Absatz „Bild".
- Vollständige Schrittfolge und die Einheiten-Fallen stehen im Skill.

## Pflichtprüfungen

- `meta.origin` (`hub`/`local`) und `meta.stale` jedes Payloads lesen; `stale`
  im Text nennen.
- `asOf` nennen, wenn der Stand nicht von heute ist.
- **Einheiten:** `percent_change` und die `rotation`-Felder sind Dezimalbrüche
  (`0,052` = 5,2 %); OECD-Reihen sind Prozentpunkte. Nicht verwechseln.

## Ablage

- Snapshot in `Wissen/Marktlage-<Monat>-<Jahr>.md` — **eine Notiz je Monat**,
  neue Tagesstände als datierter Abschnitt oben, alte stehen lassen. Erste
  laufende Fassung: [[Marktlage-September-2026]].
- [[Marktlage-August-2026]] war eine Video-Auswertung; die monatlichen
  `Marktlage-*`-Notizen laufen ab September als Routine-Ausgabe weiter.
- Beim ersten Anlegen einer Monatsnotiz `Wissen/INDEX.md` im selben Schritt
  nachziehen, dann mit Skill `sichern` committen.

## Zeitplan

- **Wrapper:** `Agenten/Routinen/marktbriefing.ps1`, Protokoll
  `Agenten/Routinen/logs/marktbriefing-letzter-lauf.log`, Rohabzug je Tag
  `marktbriefing-daten-JJJJ-MM-TT.json`.
- Zwei Stufen: (1) Boards ziehen und roh ablegen — muss gelingen, kein Login
  nötig; (2) `claude -p /marktbriefing` schreibt die Notiz — schlägt das fehl,
  bleibt der Rohabzug und ein Logeintrag „manuell nachziehen".
- **Warum diese Claude-Sitzung geplant wird, Tagesbriefing aber nicht:** Der
  Blocker dort ist `Profil`/`Verbindungen` ([[Routinen]]). Das Marktbriefing
  hängt an keinem von beidem — `traderhub` ist hub-first, ohne Schlüssel.
- Status siehe [[Routinen]]: Registrierbefehl liegt bereit, die geplante Aufgabe
  ist noch nicht angelegt.

## Grenzen

- Der Rohabzug ist ein Momentwert, kein Verlauf — er wird je Tag überschrieben
  (`logs/`, nur letzter Lauf, [[Schutzregeln]] Stufe 2).
- `traderhub`-Boards sind Tages- bis Quartalskadenz. Realtime-Kurse und K-Linien
  liegen woanders (`alice analysis`).
- Kein Ersatz für die Handelsentscheidung — das Briefing ordnet ein, es rät nicht.
