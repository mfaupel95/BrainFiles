---
id: 20261022-claude-code-auto-mode-abrechnung
title: 'Claude Code: Auto-Mode-Abrechnung'
tags: [claude-code, auto-mode, abrechnung]
created: 2026-10-22
updated: 2026-10-22
related: [Verbindungen]
summary: 'Wann Claude Code Auto-Mode-Prüfungen serverseitig oder lokal ausführt und wie die Abrechnung beim hier geprüften Pro-Login einzuordnen ist.'
---

# Claude Code: Auto-Mode-Abrechnung

Am 22.10.2026 war Claude Code 2.1.307 installiert, `defaultMode` stand auf `auto`, und `claude auth status` meldete einen direkten `claude.ai`-Login über den First-Party-Provider mit Pro-Abo. In den geprüften Claude-Code-Einstellungen und der Sitzung waren weder `ANTHROPIC_BASE_URL` noch `CLAUDE_CODE_AUTO_MODE_SERVER` gesetzt; es war kein Gateway konfiguriert.

Anthropic beschreibt den neuen serverseitigen Auto-Mode-Klassifizierer für API-, Enterprise-, Cloud- und Gateway-Sitzungen. Der Klassifizierer-Aufwand wird für Pro-, Max- und Team-Nutzer nicht zusätzlich berechnet. Damit war für den geprüften Pro-Login keine Änderung nötig; die Auto-Mode-Funktion war bereits im installierten Client enthalten.

**Warum:** `CLAUDE_CODE_AUTO_MODE_SERVER=0` macht serverseitige Prüfungen nicht kostenlos, sondern schaltet sie auf lokale Klassifizierer-Anfragen um, die wie zuvor auf die Nutzung angerechnet werden. Die Variable ist temporär. Bei einem Gateway wäre für serverseitige Prüfungen stattdessen nötig, dass es `safeguards`-Anfragen und `safeguard_results`-Antworten unverändert durchreicht.

**Prüfung:** In einer betroffenen Sitzung `/status` aufrufen. Die Zeile `Auto mode server` zeigt `Enabled`, wenn die serverseitigen Prüfungen für diese Sitzung aktiv sind; `Disabled` bedeutet, dass Claude Code auf den lokalen Klassifizierer zurückgefallen ist. Plan, Provider und Gateway können sich ändern und sind daher nur für den Messstand oben bestätigt.

Quellen: [Anthropic: Auto mode für Pro, Max und Team](https://claude.com/resources/articles/auto-mode-default-in-claude-code), [Hinweis zu Auto-Mode-Klassifizierer-Anfragen](https://code.claude.com/docs/en/auto-mode-classifier-billing), [Gateway-Passthrough](https://code.claude.com/docs/en/llm-gateway-protocol#feature-pass-through).