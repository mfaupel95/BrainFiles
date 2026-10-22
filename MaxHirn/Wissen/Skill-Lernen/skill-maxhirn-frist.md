---
name: skill-maxhirn-frist
description: Trockenlauf des Skills MaxHirn:frist - erfasst Fristen mit Konsequenz in Wissen/Fristen.md; hier geprüft, ob die Lernnotizen eine Frist enthalten.
metadata:
  type: reference
---

**Zweck:** Erfasst eine Frist erst dann als erledigt, wenn sie in `Wissen/Fristen.md` steht. Liest Schreiben vollständig, belegt Daten aus dem Schreiben statt aus dem Gedächtnis und trennt Zahlungsfrist von Rechtsbehelfsfrist.

**Wann nutzen:** Bei Bescheiden, Mahnungen, Kündigungen, Verträgen oder Rechnungen mit Zahlungsziel, sobald ein Datum Konsequenzen hat.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: prüfen, ob die Lernnotizen eine Frist mit Konsequenz enthalten, und beschreiben, wo sie eingetragen würde. Nichts in `Wissen/Fristen.md` geschrieben.

**Ergebnis:**

Bestand (lesend): Fünf Lernnotizen enthalten das Wort „Frist“ oder „bis zum“. Die Treffer sind Felder der Vorlage (`Frist? Keine.`), keine echten Fristen. Eine Frist mit Konsequenz gibt es in den Lernnotizen nicht.

Wo eine solche Frist eingetragen würde: in `Wissen/Fristen.md`, nach Datum sortiert, als offenes Kästchen. Die Datei enthält derzeit drei Zeilen mit dem Wort „frist“, deren Inhalt in diesem Lauf nicht gelesen wurde.

Der Skill ist für externe Schreiben gebaut: Bescheide, Mahnungen, Verträge. Lernnotizen sind interne Protokolle ohne Zahlungsziel. Der Skill greift hier nicht.

**Gelernt:** Der Frist-Skill schützt davor, dass Fristen im Gespräch verloren gehen. In den Lernnotizen entsteht keine Frist, also gibt es nichts zu erfassen. Die Treffer nach dem Stichwort zeigen, dass das Suchen nach Fristen eher Vorlagenfelder findet als echte Fristen.

**Grenzen:** Die Suche ist ein Stichwortlauf über fünf Notizen. Eine Frist in einer anderen Form (z. B. „bis 30.11.“) wäre so nicht gefunden worden.
