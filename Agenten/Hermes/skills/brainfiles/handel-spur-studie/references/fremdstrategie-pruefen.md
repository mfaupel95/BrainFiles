# Fremde Strategien pruefen (Ideenquellen, Werkzeug, Verdikt)

Fuer den Auftrag "such neue Strategien fuer unseren Handel" - die Quelle liefert
Ideen, die Zahlen liefert der eigene Rechner. Regelwerk und Verdiktmasstab stehen
in SKILL.md, Abschnitt "Eine fremde Strategie pruefen"; hier stehen die
Quellen-Eigenheiten und das Nachweisrezept.

## Quantpedia lesen

- **Der freie Bestand ist klein und filtert sich ueber die Abo-Spalte:**
  `https://quantpedia.com/screener/?FilterSubscription=Only+Free` listet rund 70
  Strategien (der Rest, 900+, ist Premium). Ohne Abo ist damit auch die
  Krypto-Auswahl praktisch leer.
- **Fallen beim Filtern:** der Marktfilter `?FilterMarkets=crypto` antwortet mit
  "No Results", obwohl es Krypto-Strategien gibt - die Marktspalte der freien
  Liste ist die verlaessliche Quelle. Die Filterwerte sind also nicht die der
  Oberflaeche (dort `equities`, `commodities`, `currencies`).
- **Was auf einer Strategie-Seite steht:** `Simple trading strategy` (die Regeln
  in Prosa), Instrumente, Komplexitaet, Umfang der Universumsliste, Rebalancing-
  Periode - und direkt darunter die Gegenprobe (QuantConnect-Ergebnis mit Sharpe,
  CAGR, Drawdown, Win Rate, Orderzahl). Die Quelle des Paperwerts steht unter
  "Notes to Indicative Performance".
- **Der Blog ist die frischere Quelle** fuer Regeln, die noch nicht im Screener
  stehen (Saisonalitaet, Rotation, Trend-Ausbrueche); die Artikel nennen die
  Fenster und die Kennzahlen meist direkt.

## Nachrechnen

```bash
cd Agenten/Handel
.venv/Scripts/python.exe quantpedia_probe.py stunde        # Stundenprofil (UTC)
.venv/Scripts/python.exe quantpedia_probe.py fenster 21 22 # Kauf/Verkauf je Stunde
.venv/Scripts/python.exe quantpedia_probe.py donchian      # MAX-Regel und Donchian
.venv/Scripts/python.exe quantpedia_probe.py vergleich     # gegen Buy & Hold
```

Daten: `daten/historie/BTCUSDT_1H.json` / `_1D.json`, Format `[ts_ms, o, h, l, c, v]`.
Jedes Ergebnis traegt brutto UND netto bei 0,05 / 0,1 / 0,6 % je Seite - ohne die
Nettozeile ist die Messung unbrauchbar. `fenster` und `donchian` weisen die
Zeithalbierung mit aus; `vergleich` nennt Rueckgang und Tage im Markt.

Fuer andere Instrumente als BTC die Datei im Modul umbiegen (`EINSATZ_DATEI_1H` /
`EINSATZ_DATEI_1D`) - die Rechnung ist instrumentenunabhaengig.

## Verdikt-Schema fuer den Bericht

Je Kandidat eine Zeile: Signale/Jahr · Kante je Runde · brutto p.a. · netto p.a.
bei 0,1 %/Seite · max. Rueckgang · Zeit im Markt · t · Zahl der Runden. Dann ein
Satz Verdikt. Am Ende genau EIN Vorschlag (welcher Kandidat, welche Fassung) -
keine Optionsliste.

## Gemessene Kalibrierung (Stand 30.09.2026, BTC 2021-01..2026-09)

Diese Zahlen stehen mit Herleitung in `Wiki/Handel/Lektionen.md`, Abschnitt
"Quantpedia" - hier nur als Anhalt, wohin die Rechnung kippt:

| Familie | Signale/Jahr | netto p.a. (0,1 %/Seite) |
|---|---|---|
| Nacht-Saisonalitaet BTC (21-23 UTC) | ~365 | stark negativ |
| MAX(10), ein Tag halten | 66 | negativ |
| Donchian-Tagesausbruch (20/30 Tage) | 4-6 | positiv, Rueckgang halbiert |
| Buy & Hold | 0 | positiv, groesster Rueckgang |

Merksatz aus dieser Messung: die Richtung des Befunds kann stimmen (das
Stundenprofil war in beiden Haelften positiv, t > 2) und die handelbare Regel
trotzdem tot sein - die Kante je Tag lag bei 0,03 %, der Rundlauf bei 0,1 %.
