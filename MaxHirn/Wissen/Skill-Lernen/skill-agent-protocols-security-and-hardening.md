---
name: skill-agent-protocols-security-and-hardening
description: Security-First-Entwicklungspraktiken — Drei-Tier-Grenzsystem, OWASP-Top-10-Prävention, Input-Validierung, Secrets-Management, npm-audit-Triage.
metadata:
  type: reference
---

**Zweck:** Drei-Tier-System (Always/Ask/Never) als Checkliste für alle sicherheitsrelevanten Entscheidungen. OWASP Top 10 mit konkreten TypeScript-Beispielen: Injection-Prävention (parametrisierte Queries), XSS (React auto-escaping), Broken Access Control (ownerId-Prüfung nach Authentifizierung). Input-Validierung mit Zod an Systemgrenzen. npm-audit-Entscheidungsbaum: Critical/High reachable = sofort fixen.

**Wann nutzen:** Bei allem mit User-Input, Auth/AuthZ, sensiblen Daten, externen API-Integrationen, File-Uploads. Als Checkliste vor jedem Release.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Übersicht.

**Ergebnis:** Skill vollständig geladen. ~5 Seiten. Einer der ausführlichsten Skills — praxisnah mit Copy-Paste-Snippets für jede Kategorie.

**Gelernt:** "Ask First"-Kategorie ist nützlich — nicht alles ist verboten, aber neue Auth-Flows und Datenkategorien brauchen explizite Freigabe. `httpOnly + secure + sameSite` als Pflicht-Kombination für Session-Cookies. npm-audit-Triage: "Is the vulnerable function actually called in your code path?" — nicht jede Critical-Meldung blockiert den Release. Direkt auf Agenten/Bus, Agenten/Handel (Python-Äquivalente: Parameterisierung via `?`-Platzhalter, Secrets in `.env`, keine Stack-Traces in API-Antworten) anwendbar.

**Grenzen:** Node.js/TypeScript-zentriert. Python-Äquivalente (SQLite-Parameterisierung, python-dotenv, Flask-Security) sind bekannt, werden aber nicht gezeigt. Für PowerShell-Skripte gilt nur: keine Secrets im Code, keine Shell-Injection durch nicht escapte Parameter.
