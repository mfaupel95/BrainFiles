---
name: skill-maxhirn-verbindungen
description: Trockenlauf des Skills MaxHirn:verbindungen - prüft Anbindung von MCP-Servern und Erweiterungen; hier beschrieben, welche Server der Lern-Ablauf braucht. Keine Server angesprochen.
metadata:
  type: reference
---

**Zweck:** Prüft und repariert die Anbindung externer Dienste: MCP-Server, Erweiterungen, Anmeldungen. Drei Konfigurationsebenen, die sich widersprechen können. Vor jeder Änderung Sicherung und Ansage.

**Wann nutzen:** Wenn ein Server fehlt, eine Verbindung fehlschlägt oder ein erwartetes Werkzeug nicht auftaucht.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, welche Server der Lern-Ablauf braucht und welche fehlen würden. Keine Server angesprochen, nichts eingetragen.

**Ergebnis:**

Der Lern-Ablauf braucht **keinen MCP-Server**. Die Schritte laufen über lokale Dateien und Befehle:
- Lesen und Schreiben der Notizen unter `MaxHirn/Wissen/Skill-Lernen/`
- Anfügen an `MaxHirn/Wissen/INDEX.md` und `Werkstatt/Projekte/skill-lernen/fortschritt.md`
- Aufruf des jeweiligen Skills über das Skill-Werkzeug

Ein fehlender Server würde also nur dann auffallen, wenn ein aufgerufener Skill selbst einen Server braucht. Das betrifft die Trockenläufe mit Außenbezug, etwa Kraken für `geld`, `traderhub` für `marktbriefing`, `archiv` für Suchen. Im Lauf ist das für `geld` und `marktbriefing` ausdrücklich ausgeschlossen worden, für `archiv` über den Befehl statt den Server.

Fehlen würde damit im Lern-Ablauf selbst nichts. Die Liste der Server aus dem Skill ist für den Lern-Ablauf nicht relevant.

**Gelernt:** Ein Ablauf, der nur lokal arbeitet, sollte das in seiner Beschreibung festhalten. Dann fällt ein Ausfall eines Servers nicht als Lern-Fehler auf, sondern als Problem des aufgerufenen Skills.

**Grenzen:** Keine Konfiguration gelesen, keine Verbindung geprüft. Ob die Skills, die der Lern-Ablauf aufruft, selbst funktionieren, ist eine andere Frage.
