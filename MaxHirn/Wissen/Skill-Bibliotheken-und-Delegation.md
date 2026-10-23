---
id: 20261023-skill-bibliotheken-delegation
title: Skill-Bibliotheken und Delegation
tags: [betrieb, agenten, skills]
created: 2026-10-23
updated: 2026-10-23
related: [[Hermes]]
summary: Vorschlag fuer schlanke, auf Rollen zugeschnittene Skill-Bibliotheken und Delegation zwischen Codex, Claude und Hermes.
---

## Bestand am 2026-10-23

- Hermes hat 47 Skill-Ordner zentral unter `Agenten/Hermes/skills/` und 40 Profile.
- Codex hat lokal 38 Ordner unter `~/.agents/skills` sowie 2 unter `~/.codex/skills`; die groessere Sitzungsauswahl enthaelt zusaetzlich gebuendelte/Remote-Pakete.
- Claude hat 27 Vault-Skills unter `.claude/skills/`.
- Das Hermes-Profil `codex-programming` nutzt GPT-5.6, hat aber derzeit keinen profilbezogenen Skill-Ordner.
- `omnitrade3` hat einen breiten Skill-Pfad mit allgemeinen Paketen (u. a. Office, Social, Recherche und Entwicklung). Daneben gibt es bereits konkrete Hermes-Bundles wie `spur`, `handel-betrieb`, `systemcheck`, `sitzung` und `wissen`.

Das sind Ordner-/Profilzahlen, keine Aussage, dass jeder Skill aktiv geladen oder inhaltlich identisch ist. Gleichnamige Ordner muessen ueber SKILL.md-Inhalt, Version und Herkunft abgeglichen werden, bevor Kopien vereinheitlicht werden.

## Verteilungsvorschlag

| Rolle/Profil | Kernskills | Delegation |
|---|---|---|
| Codex / `codex-programming` | Git-Worktrees, systematische Fehlersuche, Tests, Code-Review, GitHub-PR, Projektregeln | Implementierung und lokale Repo-Arbeit; an Claude fuer unabhaengige Review- oder Dokumentationsspur geben |
| Hermes `lotse` | Auftragszerlegung, Task-Register, Status-/Kontextuebergabe, Routing | Router: entscheidet nach Besitzbereich und Aufgabe, delegiert Arbeit und sammelt Resultate; keine doppelte Implementierung |
| Hermes `omnitrade*` / Handel | nur Handels- und Risikospuren, Markt-/Datenpruefung, journal und live-betriebliche Diagnose | Scanner liefert Kandidat, Pruefer beurteilt ihn, Disponent berechnet Auftrag; Ausfuehrungsgrenze und Wachen bleiben verbindlich |
| Claude | Vault-Wissen, Archiv, Dokumente, Skills/Wiki und laengere Synthese | Kontext-/Quellenarbeit, dauerhafte Notizen und unabhaengiger Gegencheck; keine gleichzeitige Besitzbereich-Aenderung ohne Abstimmung |
| Alle | kleine gemeinsame Basis: Hausregeln, Security-/Secrets-Hygiene, Quellenbeleg, Uebergabeformat | Rolle laedt nur das passende Paket pro Aufgabe, nicht die ganze Bibliothek |

## Effizienzregeln

1. Skill-Inventar zentral mit Quelle, Version/Hash, Zielplattform, Rolle und letztem Abgleich fuehren; gemeinsame Skills aus einer kanonischen Quelle ableiten, plattformspezifische Adapter getrennt halten.
2. Pro Auftrag einen verantwortlichen Schreiber benennen. Parallel delegieren nur bei unabhaengigen Fragen oder klar getrennten Dateien; ein Agent integriert und prueft den Gesamtstand.
3. Bestehende Hermes-Bundles nach Aufgabe verwenden. Bundles klein halten (typisch 2-3 Skills), um Prompt-Last und irrelevante Regeln zu senken.
4. Skill-Sync erst nach inhaltlichem Diff und Versions-/Lizenzpruefung. Nicht blind die gesamten Bibliotheken kopieren.
5. Nach Abschluss Provenienz, PR/Commit, Tests und offene Punkte in einer kurzen Uebergabe festhalten.

## Naechster Schritt

Die Zuordnung ist ein Vorschlag, keine Installation. Vor Schreibzugriffen auf Codex-, Claude- oder Hermes-Skill-Bibliotheken ist eine konkrete Liste mit Quell-/Zielpfaden und Aenderungsumfang vorzulegen. Als erste kleine Umsetzung bietet sich ein read-only Inventar mit SKILL.md-Hash, Profilzuordnung und Duplikat-/Lueckenliste an; danach koennen gezielte profileigene Hermes-Bundles vorgeschlagen werden.
