---
id: 20260908-volumen-drift-signal
title: 'Volumen-Drift-Momentum im XPERP-Signal'
tags: [handel]
created: 2026-09-08
updated: 2026-09-08
related: [20260901-xperp-handel, 20260901-saisonalitaet-signal, 20260902-handelsregeln]
summary: 'Eigener Nachbau des Prinzips von Swift Algo X (TradingView, Invite-Only) - volumengewichtete Preisdrift mit Mehrfach-Zeitebenen-Bestaetigung, hoch gewichtet ins XPERP-Signal, mit Vorrang vor der Saisonalitaet.'
---

# Volumen-Drift-Momentum im XPERP-Signal

Am 08.09.2026 auf Anweisung als eigener Indikator gebaut, angestossen durch
den TradingView-Indikator
**[Swift Algo X](https://de.tradingview.com/script/lQ4ztT8g-Swift-Algo-X/)**
(Autor swiftalgo, Invite-Only/Closed-Source). Umgesetzt in
`Agenten/Handel/xperp/indikatoren.py` (`volumen_drift()`, greift in `lage()`
ein), sichtbar in `bot.py lage`, plus eine eigenstaendige TradingView-Fassung
unter `Werkstatt/Ausgabe/2026-09-08_Volumen-Drift-Momentum.pine`.

**Warum eine Notiz:** Es ist bereits der zweite Fall, in dem ein Closed-
Source-TradingView-Indikator nicht kopiert, sondern nur im Prinzip
nachgebaut und dann hoch gewichtet in `lage()` eingehaengt wird (erster Fall:
[[Saisonalitaet-Signal]]). Zwei hoch gewichtete Bausteine gleichzeitig ist
neu und braucht eine klare Vorrangregel, sonst ist sie beim naechsten Umbau
nicht mehr nachvollziehbar.

1. **Swift Algo X ist Closed-Source.** Der Pine-Code ist nirgends einsehbar,
   nur die Methodik auf der TradingView-Seite beschrieben (Volumen-Drift-
   Momentum-Engine, 144er-Parameter-Optimizer, 8-Timeframe-Trend-Dashboard).
   Kopiert werden konnte nichts. Nachgebaut wurden zwei der drei Bausteine:
   die Volumen-Drift-Momentum-Engine und eine vereinfachte Mehrfach-
   Zeitebenen-Bestaetigung. Der Parameter-Optimizer (Meta-Werkzeug, kein
   Signal) wurde bewusst weggelassen.
2. **Kern:** `Summe(Schlusskursaenderung * Volumen) / Summe(Volumen)` ueber n
   Kerzen (Grundprinzip wie OBV/Klinger), durch ATR(14) geteilt. Zaehlt nur,
   wenn das Fenster-Volumen deutlich (>= 15 %) ueber dem Volumen davor liegt.
3. **Zeitebenen-Bestaetigung:** Python verschmilzt dieselbe Kerzenreihe
   synthetisch zu 2x/4x-Kerzen (kein Zusatzabruf noetig, weil `lage()` nur
   eine Reihe bekommt). Die Pine-Fassung fragt dagegen echte hoehere
   Zeitebenen per `request.security()` ab - bewusster Unterschied zwischen
   beiden Fassungen, kein Fehler.

## Wie es wirkt

| Lage | Folge im SIGNAL |
|---|---|
| Volumen-Drift = aktuelles Signal | Signal bleibt, Grund: „+ Volumen-Drift ... bestätigt" |
| Aktuelles Signal neutral | Volumen-Drift **setzt** die Richtung |
| Volumen-Drift widerspricht aktuellem Signal (auch wenn dieses schon durch Saisonalität gesetzt wurde) | Volumen-Drift **überstimmt** |

`richtung` wird nur ≠ 0, wenn Basis-, 2x- und 4x-Ebene **alle** dasselbe
Vorzeichen zeigen — Widerspruch zwischen den Ebenen zählt als **kein**
Signal, nicht als schwaches.

## Vorrangregel bei zwei hoch gewichteten Bausteinen

Saisonalität und Volumen-Drift dürfen beide die Richtung setzen/kippen.
Auf Anweisung vom 08.09.2026: **Volumen-Drift hat bei Widerspruch Vorrang** —
umgesetzt, indem `lage()` sie schlicht als Letztes prüft. Die Prüfreihenfolge
im Code ist die Rangfolge; keine separate Fallunterscheidung nötig, aber
beim nächsten dritten hoch gewichteten Baustein muss diese Reihenfolge-Regel
laut ausgesprochen werden, sonst verschiebt sich die Rangfolge unbemerkt.

## Nachrechnen

```powershell
cd Agenten\Handel\xperp
..\.venv\Scripts\python.exe test_indikatoren.py
..\.venv\Scripts\python.exe bot.py lage --wert SOL
```

Die Zeile „Volumen-Drift Score ..." zeigt Score, Volumen-Verhältnis und
Richtung; bei gesetzter Richtung eine zweite Zeile mit den Scores der beiden
Bestätigungs-Zeitebenen.

Verwandt: [[XPERP-Handel]], [[Saisonalitaet-Signal]], [[Schutzregeln]]
