---
name: skill-loop
description: Trockenlauf des Skills loop — wiederkehrende Prompts mit fester Taktung (Cron) oder selbst-getaktet (ScheduleWakeup + Monitor); Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Prompt wiederholt ausführen — mit fester Taktung oder dynamisch selbst-getaktet.

**Lauf:** 2026-10-22, trockenlauf.

**Syntax:** `/loop [interval] <prompt>` oder `/loop <prompt>`

**Parsing:**
1. Führendes Token `^\d+[smhd]$` → Interval (Rest = Prompt)
2. Endet mit `every <N><unit>` → Interval (Rest = Prompt)
3. Sonst → kein Interval, dynamic mode

**Fester Interval (CronCreate):**
- `Nm` (≤59) → `*/N * * * *`; `Nm` (≥60) → `0 */H * * *`
- `Nh` (≤23) → `0 */N * * *`; `Nd` → `0 0 */N * *`
- Nicht-teilbar → auf nächsten sauberen Wert runden, vorher melden
- `CronCreate(cron, prompt, recurring: true)`, auto-expire nach 7 Tagen
- Dann Prompt **sofort** ausführen

**Dynamic mode (ScheduleWakeup):**
1. Prompt jetzt ausführen
2. Falls auf Event gewartet wird (CI, Log, Datei) → Monitor armen (timeout 1800s)
3. `ScheduleWakeup(delaySeconds, reason, prompt="/loop <original>", noop: true/false)`
   - Mit Monitor: 1200–1800s als Fallback-Heartbeat
   - Ohne Monitor: Takt nach beobachteter Änderungsrate
4. Stoppen: `ScheduleWakeup(stop: true)` + `TaskStop(Monitor)` + PushNotification

**noop-Regel:** `noop: true` wenn nichts geändert (collapse im Terminal); `false` wenn etwas passiert ist.
