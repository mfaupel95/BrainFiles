---
name: skill-maxhirn-rueckschau
description: Trockenlauf des Skills MaxHirn:rueckschau - beschreibt, wie gespeicherte Sitzungen auf wiederkehrende Muster geprüft würden; hier auf den Lern-Ablauf bezogen, ohne Sitzungsdaten zu lesen.
metadata:
  type: reference
---

**Zweck:** Wertet gespeicherte Claude-Sitzungen aus, um wiederkehrende Arbeit und Umwege zu finden und daraus Skills abzuleiten. Die Auswertung läuft über ein Skript, nicht über Lesen von Hand.

**Wann nutzen:** Bei „was wiederholt sich“, „wo verliere ich Zeit“ oder bevor ein neuer Skill entworfen wird.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie die Sitzungen für die Frage ausgewertet würden, ob der Lern-Ablauf wiederkehrende Muster zeigt. Keine Sitzungsdaten gelesen, keine Skills abgeleitet.

**Ergebnis:**

Der Ablauf (laut Skill): Ein Skript zählt Sitzungen, Anweisungen und Befehle, dazu Themen und Fehlersignaturen. Gezählt wird je Signatur die Zahl verschiedener Sitzungen und Tage. Ein Muster braucht mehrere Sitzungen, ein Vorfall reicht nicht.

Für den Lern-Ablauf heißt das:
1. **Was zu prüfen wäre:** Ob dieselben Umwege in mehreren Sitzungen auftauchen, etwa beim Schreiben der Notizen, beim Index oder beim Aufrufen von Skills.
2. **Wie:** Fehlersignaturen mit `--umwege` über den Zeitraum seit dem Start des Ablaufs. Das Thema „skill-lernen“ muss in der Themenliste stehen, sonst untertreibt der Bericht.
3. **Einschränkung:** Der Lern-Ablauf lief in mehreren Sitzungen parallel, und Fortschrittszeilen anderer Sitzungen tauchen auf. Eine Häufigkeit über Sitzungen wäre dadurch verzerrt.

Der Ablauf erkennt keine Muster, die in den Lernnotizen selbst stehen. Die Notizen beschreiben die Skills, nicht die Arbeitsweise der Sitzung.

**Gelernt:** Eine Auswertung über mehrere parallele Sitzungen zählt dieselbe Arbeit mehrfach. Vor einer Zählung braucht es eine Abgrenzung, welche Sitzung welchen Skill gelaufen hat.

**Grenzen:** Keine Sitzungsdaten gelesen. Die Themenliste des Skripts enthält „skill-lernen“ vermutlich nicht. Das wurde nicht geprüft.
