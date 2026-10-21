---
name: skill-agent-protocols-incident-response-and-postmortems
description: Produktionsausfälle in fünf Phasen bearbeiten — Triage, Stabilisieren, Kommunizieren, Auflösen, Postmortem ohne Schuldzuweisung.
metadata:
  type: reference
---

**Zweck:** Strukturiertes Incident-Response-Protokoll für Produktionsausfälle: fünf Phasen (Triage → Stabilisieren → Kommunizieren → Auflösen → Postmortem). Rollenzuweisung (Incident Commander, Comms, Technical Lead), Beweissicherung vor Log-Rotation, Blameless-Postmortem-Format.

**Wann nutzen:** Nutzer oder SLIs in deployed Umgebungen betroffen — Seiten-Alert, Kunden-Meldungen, Datenverlust, Sicherheitsereignis. Nicht für lokale Test-Fehler (dafür `debugging-and-error-recovery`).

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. Kompakter Skill (~1 Seite) mit klarer Phasenstruktur. Postmortem-Abschnitt betont: Blameless, Contributing Factors statt "Five Whys", Action Items mit Eigentümer und Fälligkeit.

**Gelernt:** "Prefer reversible changes" als Stabilisierungs-Grundregel. Direkt anwendbar auf Handelssystem-Ausfälle: Handelsagent-Absturz = Incident; `Wiki/DockerDesktop.md` und `Wiki/Routinen.md` enthalten bereits einige dieser Muster. Beweissicherungs-Schritt (Logs, Metriken, Config-Versionen mit UTC-Zeitstempel) fehlt derzeit in den Routinen.

**Grenzen:** Auf Cloud-/SLO-Infrastruktur ausgerichtet. Lokaler Handelsbetrieb hat keine Status-Page und keine On-Call-Eskalation — das Kernprinzip (Rollback bevorzugen, UTC-Zeitstempel, Blameless) gilt aber trotzdem.
