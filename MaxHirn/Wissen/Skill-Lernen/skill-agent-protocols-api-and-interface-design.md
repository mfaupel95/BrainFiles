---
name: skill-agent-protocols-api-and-interface-design
description: Trockenlauf des Skills agent-protocols:api-and-interface-design - prüft die Schnittstelle von skill-lernen (Eingaben, Ausgaben, Zustände) auf Festlegung und Mehrdeutigkeit.
metadata:
  type: reference
---

**Zweck:** Leitet Schnittstellenregeln für REST, TypeScript und Module her: Vertrag zuerst, einheitliche Fehler, Validierung an den Grenzen, additive Erweiterung, Hyrum's Law.

**Wann nutzen:** Beim Entwurf neuer Schnittstellen, bei Modulgrenzen und vor Änderungen an öffentlichen Verträgen.

**Lauf:** 2026-10-21, trockenlauf, Aufgabe: die Schnittstelle von `skill-lernen/SKILL.md` als API prüfen. Nichts geändert.

**Ergebnis:** Der Skill ist für Code-Schnittstellen geschrieben. Angewendet auf einen Skill ohne Code ergibt sich folgendes Bild.

Festgelegt:
- Ausgabeort und Dateiformat der Fortschrittstabelle.
- Ausgabeort der Notiz (`MaxHirn/Wissen/Skill-Lernen/`) und ihr Frontmatter.
- Die Pflicht, den Index zu ergänzen.
- Die Modi `voll`, `trockenlauf`, `nicht-ausführbar`.

Mehrdeutig:
1. **Eingabe.** Der Kandidat kommt aus der Skill-Liste der Sitzung. Die Liste ändert sich je Sitzung, daher ist ein Lauf nicht reproduzierbar.
2. **Dateiname der Notiz.** Der Abschnitt „Dateien“ nennt `<skill-name>.md`, Schritt 6 nennt `name: skill-<…>`. Welcher Dateiname gilt, steht nirgends.
3. **Statuswerte.** `nicht-ausführbar (2x)` ist im Schritt „Ablauf 2“ eingeführt, aber nicht in der Statusliste von Schritt 7. Die Zählung ist nur durch Lesen der Tabelle möglich.
4. **Spalte „Notiz oder Grund“.** Sie enthält einmal einen Pfad, einmal einen Grund. Ein Parser kann das nicht unterscheiden.
5. **Datumsformat.** Nicht festgelegt.
6. **Indexzeile.** „Die letzte Zeile, die mit `- \`` beginnt“ ist eindeutig nur, solange der Index nur eine Notizliste hat. Die `id` ist nur als Beispiel angegeben.
7. **Modus „voll“.** Schritt 4 verlangt Trockenlauf bei Außenwirkung. Schritt 6 nennt „voll“, ohne die Bedingung zu wiederholen.
8. **Aufgabe in Schritt 5.** „Aus Max' Kontext“ lässt die Auswahl offen. Es gibt keine Vorgabe, wie eine Aufgabe ausgewählt wird.

**Gelernt:** Eine Schnittstelle ohne feste Form ist eine Quelle für Fehler. Die Regel „Fehlt etwas, nicht raten“ hilft nur, wenn die Felder eindeutig benannt sind. Ein Trockenlauf eignet sich gut für diese Prüfung, weil er nichts verändert.

**Grenzen:** Die Prüfung ist eine Lesebewertung. Die Lösungen werden nicht umgesetzt, weil dieser Lauf nur prüft.
