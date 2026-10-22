---
name: skill-scanner-papier
description: Trockenlauf des Skills scanner-papier — Scanner-Varianten im Papiermodus auswerten, Signale/Ausstiege verfolgen; Fallen; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Scanner-Varianten im Papier-Modus auswerten ohne den Live-Scanner anzufassen.

**Lauf:** 2026-10-22, trockenlauf.

**Ort:** `Werkstatt/scanner-varianten/` (nicht versioniert). Python: `Agenten/Handel/.venv/Scripts/python.exe`.

**Befehle:**
- Auswerten: `python auswertung.py` im Ordner → n, netto %, t, t(Tag), Tage, offene Positionen
- Signale (täglich 08:10): `papier.py`, schreibt `papier.lock`
- Ausstiege (stündlich :05): `papier_stunde.py` mit 1H-Kerzen
- Status: `Get-ScheduledTask MaxHirn-Scanner-Papier-Stunde | Get-ScheduledTaskInfo`

**Zahlen lesen:**
- `t(Tag)` zählt, nicht `t` — Signale eines Tages hochkorreliert
- Erst ab Dutzenden Einstiegstagen belastbar
- Netto-Formel: `100*(ex/ein - 1 - 2*GEB)`, GEB 0,1 % je Seite

**Fallen:**
- Stop und Ziel in derselben Stunde → Stop gewinnt (pessimistisch, Absicht)
- `X-USD` entspricht OKX-instId `X-USDT`; nur `confirm==1`-Kerzen
- `papier_stunde.py` überspringt bei `papier.lock` jünger als 1200 s — kein Fehler
- Stand 04.10.2026: v0=v2 und v1=v4 liefern identische Zahlen (Regime-Tore prüfen)
- `schtasks` in Git-Bash scheitert → PowerShell `Get-ScheduledTask`

**Grenze:** Ändert den Live-Scanner nie. Übernahme von Varianten entscheidet nur Max.
