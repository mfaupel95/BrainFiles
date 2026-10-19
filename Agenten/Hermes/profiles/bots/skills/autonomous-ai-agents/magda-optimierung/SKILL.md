---
name: magda-optimierung
description: Prune and consolidate the MAGDA repo-bot memory md files.
category: autonomous-ai-agents
---

# MAGDA-Optimierung (Dateien pflegen)

Die MAGDA-Dateien sind das geteilte Gedaedchtnis aller Repo-Bots (Auftrag Max
13.10.2026). Sie wachsen, wenn jeder Lauf seinen Stand anhängt — der Zweck
ist, sie kompakt und aktuell zu halten. Dieses Skill wird periodisch gerufen
(ueblicherweise aus einem Cron oder vom Interpool); es fasst zusammen statt
nur anzuhängen.

## Was bereinigt wird

- **Prolog-Datei je Profil:** `Agenten/Hermes/profiles/<bot>/MAGDA.md`
  Abschnitte: `## Letzter Stand` / `## Offene Punkte` / `## Erinnerungen` /
  `## Ziel des naechsten Laufs`.
- **Zentrale Datei:** `Agenten/Hermes/MAGDA.aktuell.md` — eine Zeile je Profil
  plus Uebergreifender-Punkte-Block oben.

## Regeln (nicht verhandelbar)

1. **Nur verdichten, nie loeschen was noch gilt.** Ein Stand, der schon erledigt
   ist (Trade geschlossen, PR gemergt, Datei gebaut), wird in eine Zeile
   gekuerzt oder entfernt; ein OFFENER Punkt bleibt, bis er wirklich zu ist.
2. **Erinnerungen/Fallen sind die Kronjuwelen.** Verfahren, Fallen und
   Max-Praeferenzen in `## Erinnerungen` niemals kuerzen — sie sind der
   eigentliche Gewinn. Loeschen nur, wenn sie offensichtlich veraltet.
3. **Letzter Stand je Profil = genau eine kompakte Zeile** in der zentralen
   Datei (was, wann). Den `Datum` immer behalten.
4. **Offene Punkte, die aelter als 7 Tage sind und keine Aktivitaet sehen:
   markieren und in einen Abstell-Block `## Alte Punkte (7+ Tage)` verschieben**,
   nicht stillschweigend loeschen — Max entscheidet ueber Verwerfen.
5. **Konsistenz pruefen:** Profil-Liste in der zentralen Datei muss der
   tatsaechlichen `profiles/`-Liste entsprechen (fehlende ergaenzen, tote
   entfernen, solange nicht `.deleted`/`.sicherung`).
6. **Pfade relativ zur Wurzel.** Vor den Lese-/Schreibzugriffen:
   `cd "$HERMES_HOME/../.."` (kurz `cd ..`), dann relative Pfade.
7. Nach der Optimierung die Aenderung melden (wie viele Dateien, was gekuerzt,
   was als offen behalten).

## Ablauf

1. Liste aller echten Profile holen (`profiles/`, ohne `.deleted`/`.sicherung`,
   35 Stueck).
2. Zentrale Datei lesen, Prolog pro Profil lesen (gezielt, nicht alle riesig).
3. Je Profil: Letzter Stand auf eine Zeile, Offene Punkte condensieren,
   Erinnerungen unangetastet lassen.
4. Uebergreifenden-Punkte-Block oben: erledigte raus, offene dem aktuellen
   Stand anpassen.
5. Dateien zurueckschreiben (atomar; bei grossen Profilen nur den Abschnitt
   patchen statt das ganze File neu zu schreiben — der Rest kann parallele
   Schreibzugriffe anderer Bots tragen).
6. Ergebnis kurz melden.

## Fallen

- **Parallele Schreiber:** Andere Bots koennen gerade in ihre MAGDA.md
  schreiben. Nur den eigenen/zu pflegenden Abschnitt patchen, nie das ganze
  File neu schreiben, sonst ueberschreibst du den Stand eines laufenden Bots.
- `profiles/` enthaelt `.deleted` und `.sicherung` — keine MAGDA dort.
- Die Dateien sind Betriebsdateien, NICHT versioniert — kein Commit noetig.
