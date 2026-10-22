---
name: skill-skills-truman
description: Trockenlauf des Skills skills:truman — Tagesrückblick als 3-Personen-Sendung aus Git-Commits + Claude-Sessions; Serien-Episoden mit Cliffhangern.
metadata:
  type: reference
---

**Zweck:** Den Arbeitstag als TV-Sendungsmanuskript aufbereiten — unterhaltsam, aber auf echten Daten basierend. Letzter Block (Regieanmerkungen + Vorschau) ist echter Rückblick.

**Wann nutzen:** `/truman` für Tagesrückblick, Wochenzusammenfassung oder auf Anfrage "zeig mir meinen Tag als Sendung".

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill geladen. ~3 Seiten. Originell — Unterhaltung + ehrliche Retrospektive.

**Gelernt — Ablauf:**
1. `scripts/collect.sh` ausführen (lokal, kein Netzwerk) → Commits, Reflog, Claude-Aussagen
2. `~/.claude/truman/state.json` lesen → Staffel/Episode bestimmen, letzte Cliffhanger laden
3. Drehbuch schreiben nach fester Struktur
4. In `~/.claude/truman/episodes/S01E04.md` speichern + state.json aktualisieren
5. Optional: Artifact veröffentlichen

**Drehbuch-Struktur:**

| Block | Inhalt |
|---|---|
| Titel | `S01E04 — 「Titel」` — Ergebnis nicht vorwegnehmen |
| Cold Open | Dramatischste Szene der Stunde mit Zeitstempel |
| Akt 1 | Beginn — erste Aussage, erster Commit |
| Akt 2 | Konflikt — Wiederholungen, Resets, häufige Wechsel |
| Akt 3 | Schluss — letzter Commit + ehrliches Ende-Signal |
| Regieanmerkungen | ≤3 beobachtete Signale (nur Fakten, keine Persönlichkeitsbewertung) |
| Nächste Folge | 2–3 unfertige Punkte mit Liegezahl in Tagen |

**Kernregeln:**
- 3. Person ("er/sie" aus `state.json`), niemals 2. Person
- Zeitstempel häufig einbauen ("18:31 Uhr")
- Originalzitate **unverändert** (Tippfehler bleiben!)
- Keine Psychologie — nur beobachtbares Verhalten
- 800–1300 Zeichen, 2 Minuten Lesezeit
- Keine Emojis

**Cliffhanger-Mechanismus:** Nicht abgeschlossene Punkte als Cliffhanger speichern → nächste Episode zeigt "N. Folge hintereinander" wenn wieder auftaucht → ehrlichstes Feedback.

**Staffel-System:** Monatlich (Januar = S01, Februar = S02). Tagesbeginn um 05:00 Uhr.

**Datenschutz:** Vor Veröffentlichung: Zugangsdaten/Kundennamen aus Zitaten entfernen, Repo-Namen maskieren anbieten.

**Grenzen:** Braucht `scripts/collect.sh` im Skill-Verzeichnis. Ohne Daten (kein Commit, keine Aussage) → kein Manuskript.
