---
name: brainstorming
description: Use when kreative Arbeit ansteht; erst Design, dann Code.
---

# Brainstorming: Ideen zu Designs

Ideen durch natuerlichen Dialog mit dem Nutzer in ausgereifte Designs und Spezifikationen verwandeln. Erst verstehen, dann Design praesentieren, erst nach Zustimmung implementieren.

<HARD-GATE>
Keine Implementierung (kein Code, kein Scaffolding, keine Aenderung), bevor das praesentierte Design vom Nutzer genehmigt ist. Gilt fuer JEDES Projekt, auch scheinbar triviale.
</HARD-GATE>

## Anti-Pattern: "Das ist ja einfach"

Jedes Projekt durchlaeuft diesen Prozess. Bei einfachen Dingen (Todo-Liste, Ein-Funktions-Utility, Config-Aenderung) ist das Design kurz - ein paar Saetze - wird aber trotzdem praesentiert und genehmigt. Ungepruefte Annahmen verursachen den meisten vergeudeten Aufwand.

## Checkliste (in Reihenfolge)

1. **Projektkontext erkunden** - Dateien, Docs, letzte Commits lesen (search_files, read_file, `git log` im Terminal).
2. **Visuelle Begleitung nur bei Bedarf anbieten** - nicht vorab. Erst wenn eine Frage gezeigt besser verstanden wird als beschrieben, in eigener Nachricht anbieten und auf Antwort warten. Bei Ablehnung textbasiert weiter, nicht erneut anbieten.
3. **Klaerende Fragen** - einmal fragen: Zweck, Constraints, Erfolgskriterien. Bevorzugt Multiple-Choice, nur eine Frage pro Nachricht.
4. **2-3 Ansaetze vorschlagen** - mit Abwaegungen und Empfehlung.
5. **Design praesentieren** - abschnittsweise, Umfang an Komplexitaet skalieren (wenige Saetze bis 200-300 Woerter), nach jedem Abschnitt Rueckmeldung holen.
6. **Spezifikation schreiben** - Design-Doc ablegen und committen.
7. **Self-Review der Spezifikation** - Platzhalter, Widersprueche, Umfang, Mehrdeutigkeit pruefen (siehe unten).
8. **Nutzer-Review** - Nutzer die Spezifikation pruefen lassen, auf Antwort warten. Nur nach Zustimmung weiter.
9. **Uebergang** - writing-plans-Skill laden und Implementierungsplan erstellen.

## Designprozess

**Idee verstehen:**
- Erst Projektzustand pruefen, dann fragen.
- Anfragen mit mehreren unabhaengigen Teilsystemen sofort kennzeichnen und zuerst zerlegen (was gehoert zusammen, in welcher Reihenfolge?). Jedes Teilprojekt bekommt eigenen Design-/Plan-/Implementierungszyklus.
- Fokus: Zweck, Constraints, Erfolgskriterien.

**Ansaetze erkunden:**
- 2-3 verschiedene Ansaetze mit Abwaegungen praesentieren, Empfehlung mit Begruendung.
- YAGNI: Unnoetige Features konsequent entfernen.

**Design isolieren:**
- System in kleine Einheiten mit klaren Grenzen und wohldefinierten Interfaces zerlegen.
- Je Einheit beantwortbar: Was tut sie, wie nutzt man sie, wovon haengt sie ab?
- Einheit ohne Lektuere der Interna verstehbar? Interna aendern, ohne Nutzer zu brechen? Wenn nicht, sind die Grenzen schlecht.
- Wird eine Datei gross, ist das ein Signal, dass sie zu viel tut.

**Bestehende Codebasis:**
- Erst Struktur erkunden, bestehenden Mustern folgen.
- Probleme, die die Arbeit betreffen, als gezielte Verbesserung einbauen.
- Kein unzusammenhaengendes Refactoring.

## Nach dem Design

**Spezifikation:** Design-Doc schreiben (z.B. `docs/design/YYYY-MM-DD-<thema>-design.md`) und committen. Woerter wie geschrieben: Der Plan baut darauf auf.

**Self-Review (frische Augen):**
1. Platzhalter-Scan: "TBD", "TODO", unvollstaendige Abschnitte? Beheben.
2. Interne Konsistenz: Widersprueche zwischen Abschnitten? Architektur passt zu Feature-Beschreibung?
3. Umfang: fokussiert genug fuer EINEN Implementierungsplan? Zerlegung noetig?
4. Mehrdeutigkeit: Anforderung auf zwei Arten lesbar? Dann eine Variante waehlen und explizit machen.

Gefundene Probleme inline beheben, danach erneut reviewen.

**Nutzer-Review-Gate:** Nutzer die Spezifikation pruefen lassen und auf Antwort warten. Bei Aenderungswuenschen anpassen und Review-Schleife wiederholen. Erst nach Zustimmung weiter.

**Implementierung:** writing-plans-Skill laden. Auf brainstorming folgt nur writing-plans.

Adaptiert aus obra/superpowers (Fork mfaupel95/superpowers), 16.09.2026.
