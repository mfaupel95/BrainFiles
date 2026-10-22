---
name: skill-security-review
description: Trockenlauf des Skills security-review — Code-Branch auf Sicherheitslücken prüfen (Injection, Auth, Crypto, RCE); 3-Phasen-Methode; Subagents für False-Positive-Filter; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Security-fokussierter Code-Review des aktuellen Branch-Diffs — nur neu eingeführte Schwachstellen.

**Lauf:** 2026-10-22, trockenlauf.

**Ablauf (3 Phasen):**
1. Kontext lesen: vorhandene Sicherheits-Frameworks, Sanitierungs-Muster
2. Vergleich: Abweichungen von bestehenden Mustern
3. Bewertung: Injection-Punkte, Auth-Bypässe, unsichere Deserialisierung

**Kategorien:**
- Input-Validierung: SQL/Command/XXE/Template/NoSQL Injection, Path Traversal
- Auth: Bypass, Privilege Escalation, JWT, Session
- Crypto: Hardcoded Keys, schwache Algorithmen, Zertifikat-Validierung
- Code Execution: Pickle, YAML, Eval, XSS
- Data Exposure: PII, Debug-Info, API-Leaks

**Ausgeschlossen:** DoS, gespeicherte Secrets, Rate Limiting

**Konfidenz-Schwelle:** >80 % für Report; <0.7 = nicht melden

**Ausgabe-Format:**
```
# Vuln 1: <Typ>: `datei.py:42`
* Severity: High/Medium
* Exploit Scenario: ...
* Recommendation: ...
```

**False-Positive-Filterung:** Jede gefundene Schwachstelle wird in einem separaten parallelen Subagent mit der kompletten Ausschluss-Liste geprüft. Nur Konfidenz ≥ 8 kommt in den finalen Report.

**Harte Ausschlüsse (nie melden):**
- DoS, Memory/CPU, veraltete Libs, Race Conditions (theoretisch)
- Shell-Skripte (kein konkreter Angreiferpfad), Log Spoofing
- Markdown-Dateien, React/Angular XSS (außer dangerouslySetInnerHTML)
- Regex-Injection/-DoS, SSRF nur auf Pfad (nicht Host)
- KI-Prompt-Injektion in System-Prompts ist KEIN Fund
