---
name: scanner-papier
description: Papier-Test der Scanner-Varianten v0-v4 auswerten, pruefen oder reparieren (nur Messung, kein Geld). Benutzen bei "Papier-Test auswerten", "wie laufen die Varianten", "Scanner-Varianten", "wer gewinnt v4", "Stundenlauf haengt", "t(Tag)".
---

# Scanner-Papier-Test

Ort: `Werkstatt/scanner-varianten/` (nicht versioniert). Python: `Agenten/Handel/.venv/Scripts/python.exe`.

## 1. Befehle
- Auswerten: im Ordner `python auswertung.py` -> je Variante n, netto %, t, t(Tag), Tage, offene Positionen.
- Signale (taeglich 08:10, Aufgabe `MaxHirn-Scanner-Papier`): `papier.py`, schreibt `papier.lock`.
- Ausstiege (stuendlich :05, Aufgabe `MaxHirn-Scanner-Papier-Stunde`): `papier_stunde.py` mit 1H-Kerzen.
- Status: `Get-ScheduledTask MaxHirn-Scanner-Papier-Stunde | Get-ScheduledTaskInfo`; Log `Agenten/Routinen/logs/scanner-papier-stunde-letzter-lauf.log`.
- Doku der Aufgaben: [[Routinen]].

## 2. Lesen der Zahlen
- **t(Tag) zaehlt**, nicht t: Signale eines Tages sind hochkorreliert.
- Erst ab einigen Dutzend Einstiegstagen belastbar; "offen %" ist Buchgewinn, nicht realisiert.
- Netto-Formel `100*(ex/ein-1-2*GEB)`, GEB 0,1 % je Seite.

## 3. Fallen
- Stop und Ziel in derselben Stunde: Stop gewinnt (pessimistisch, Absicht).
- Coin `X-USD` entspricht OKX-instId `X-USDT`; nur `confirm==1`-Kerzen.
- `papier_stunde.py` ueberspringt bei `papier.lock` juenger als 1200 s - kein Fehler.
- Stand 04.10.2026: v0=v2 und v1=v4 liefern identische Zahlen (Regime-Tore greifen noch nicht? pruefen).
- `schtasks` in Git-Bash scheitert (Pfadumwandlung) -> PowerShell `Get-ScheduledTask`.
- `Routinen.md` ist CRLF: nur gezielter Binaerersatz, kein Rewrite.

## 4. Grenzen
- Aendert den Live-Scanner nie; Uebernahme von v4 entscheidet nur Max, erst bei genug abgeschlossenen Trades.
