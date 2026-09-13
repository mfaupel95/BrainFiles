# Omniquant-Spur

Papierbuch auf dem **Prognose-Bericht**: handelt die Treffer, die
`prognose.py` findet, als Papierpositionen — mit Kosten auf beiden Seiten,
Zwangsschluss und Kill-Switch.

Angelegt am 13.09.2026 auf Max' Anweisung („Omniquant AI trader in Handel/
implementieren“). „Omniquant“ ist **keine** externe API: Die Recherche vom
10.09.2026 hatte omniquant.trade als kommerziellen Prognosedienst geprüft und
abgeraten („auf dem eigenen Buch nach Kosten negativ“). Diese Spur setzt
dieselbe Idee auf eigenen Daten und unter eigener Kontrolle um — dieselbe
Kategorie Werkzeug, das prognose.py schon ist, nur mit einem Buch dahinter.

## Was sie ist

- **Signalquelle:** `../prognose_berichte/neuester.json` — der volle Lauf von
  `prognose.py`, nicht der `--kurz`-Weg. Ein Bericht älter als
  `max_bericht_alter_stunden` (26 h) ist kein Signal: dann wird nichts
  eröffnet (Abstention ist Teil der Strategie).
- **Einstieg:** aktueller Kurs, aber nur wenn er noch zwischen Stop und Ziel
  liegt (long: `stop < kurs < ziel`, short: `ziel < kurs < stop`). Liegt er
  dahinter, ist das Signal verfallen.
- **Streuung:** `max_je_basiswert` (1) verhindert Klumpen — SOL-USDC und
  SOL-USDT sind zwei Treffer, aber ein Vermögenswert. Je Basiswert geht nur
  der Stärkste (C/R × Score) durch; ein offener Basiswert bekommt keine
  zweite Position, ein heute geschlossener kommt heute nicht wieder.
- **Kosten:** Slippage + Gebühr wirken auf beiden Seiten (Kauf teurer,
  Verkauf billiger).
- **Ausstiege:** Stop, Ziel, Zwangsschluss nach `max_halte_dauer_tage`,
  Herzschlag-Flachstellung nach Ausfall.
- **Kill-Switch:** kumulierte Verluste gegen `max_gesamt_risiko_usd` — danach
  keine neuen Einstiege.

## Was sie nicht ist

**Kein Orderpfad.** Es gibt keinen Zweig, der etwas kauft: `--live`
verweigert mit genau einem Grund, in dem das Wort *Freigabefenster* nicht
vorkommt — der Dauerlauf fragt deshalb nie eine Freigabe an, die nichts
öffnen kann (Muster: spiegel-Spur).

## Aufrufe

```powershell
scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was wäre dran, ohne zu schreiben
scanner\.venv\Scripts\python.exe handeln.py --papier     # ein Papierzyklus mit Journal
scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen als Momentaufnahme
scanner\.venv\Scripts\python.exe handeln.py --live       # verweigert, nennt den Grund
```

## Tests

```powershell
scanner\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Die Tests brauchen kein Netz: `bericht_quelle` und `letzter_kurs_quelle`
sind Seams in `handeln.py` (None → echte Quelle), die Tests setzen Lambdas.

## Verdrahtung

Eine Spur, die niemand meldet, ist keine Spur — fünf Stellen, alle fünf
gesetzt:

1. `dauerlauf.SPUREN` — Start im 24/7-Lauf (Papier, wie alle Spuren ohne
   offenes Fenster).
2. `Bus/handel_befehle.SPUREN` — `/status` listet sie.
3. `tagesbericht.spur_omniquant()` + Eintrag im `baue()`-Tupel.
4. Bus-Anbindung im Skript selbst: `with ereignis.lauf("handel/omniquant")`.
5. `.gitignore`-Whitelist: Code/Wachen/Tests freigegeben, `zustand.json` und
   `handelsjournal.csv` gesperrt (schreibt jeder Zyklus).

## Grenzen (wachen.json)

Alle Werte sind bewusst konservativ gesetzt, keine gemessen — und vor jedem
Live-Gedanken zu belegen (Stufe 1: ändern heißt sichern, echter Lauf, Commit).
