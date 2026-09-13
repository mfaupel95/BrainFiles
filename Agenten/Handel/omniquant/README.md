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
- **Kosten:** Slippage + Gebühr wirken auf **beiden** Seiten des Wegs (Kauf
  teurer, Verkauf billiger). Eine Position ohne Kursbewegung ergibt daher ein
  Minus von rund 0,5 % — der Test, der ein Papierbuch ehrlich macht. Eine
  Rechnung mit nur einer Kostenseite wäre um die Hälfte zu optimistisch.
- **Ausstiege:** Stop, Ziel, Zwangsschluss nach `max_halte_dauer_tage`,
  Herzschlag-Flachstellung nach Ausfall.
- **Kill-Switch:** kumulierte Verluste gegen `max_gesamt_risiko_usd` — danach
  keine neuen Einstiege.

## Buchgewinn/-verlust und Auswertung

Jede Position führt `mfe_pct`/`mae_pct` (größter Buchgewinn/-verlust seit dem
Einstieg, an den Zykluspunkten gemessen — eine Untergrenze). Beim Ausstieg
gehen Score, C/R, Haltedauer und die Extreme ins Journal. `auswertung.py`
liest daraus die Bilanz und trennt **vor** von **nach** Kosten (die
Netto-Rendite ist über die bekannten Kostensätze zurückrechenbar, nichts
geschätzt). Die Mechanik teilt sie mit der Spiegel-Spur über
`Handel/buchauswertung.py` — was hier steht, ist nur die Konfiguration dieser
Spur (Aktionen, Spalten, Score- und C/R-Bänder). Eine zweite Formel für
dieselbe Frage wäre eine zweite Wahrheit.

```powershell
scanner\.venv\Scripts\python.exe auswertung.py           # Bilanz und Datenlage
scanner\.venv\Scripts\python.exe auswertung.py --min 20  # strengere Schwelle
```

Sie behauptet nichts aus zu wenig Daten: unter 8 Ausstiegen gibt es Rohzahlen
und den Satz, dass es für eine Schwelle nicht reicht, je Gruppe erst ab 5
Beobachtungen einen Hinweis (Muster: `_mindest_score_short` in
`prognose.json`). Ein Tor aus drei Trades zu drehen ist Rauschen, kein Lernen.

**Sichtbar an zwei Orten**, beide aus derselben Quelle (`kernzeile()` /
`kernzeilen()`) — eine zweite Formel wäre eine zweite Wahrheit:

- **Tagesbericht:** eine Zeile `Auswertung: …` unter dem Omniquant-Block
  (kommt über `spur_omniquant()["bilanz"]`, gedruckt von `baue()`).
- **GUI:** der Block `Auswertung (Journal)` mit Bilanz, vor/nach Kosten,
  Trefferquote, Buchgewinn/-verlust und den Hinweisen.

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
scanner\.venv\Scripts\python.exe auswertung.py           # Bilanz aus dem Journal
```

Die Kopfzeile jedes Laufs schlüsselt auf, warum ein Treffer kein Kandidat
wurde (`6 Treffer; 2 verfallen, 1 gefiltert …`) — ohne diese Zahlen sieht
„0 Kandidaten" aus wie „kein Signal". Keine dieser Zeilen trägt ein Wort aus
der Dauerlauf-Meldeliste (`verkauf`, `stop`, `KILL`, `gesperrt`, `ausstieg`),
der Regelzyklus bleibt also still.

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

## Journal außer Haus (Bedingung 4, seit 13.09.2026)

Nach jedem Zyklus gehen `handelsjournal.csv` und `zustand.json` zusätzlich nach
`journal_zweitziel` aus `wachen.json` (`Q:\Handel_Journal\omniquant`), wie bei
den anderen Spuren. Die Kopie liegt **nach** dem Schreiben von Herzschlag und
Journal: ein hängendes Zweitlaufwerk darf den Zyklus verzögern, nicht den
Herzschlag verschlucken. Ein fehlendes Ziel ist kein Fehler des Laufs.

Sichtbar wird eine ausgefallene Kopie im eigenen Zustand:
`journal_zweitziel_ok` (true/false) und `journal_zweitziel_info` (Pfad oder
Grund), geschrieben nur beim Wechsel. `handeln.py --wachen` zeigt beide an.
Kopiert wird mit `scanner/wachen_pruefung.spiegele_journal` — eine
Implementierung für alle Spuren.

## Grenzen (wachen.json)

Alle Werte sind bewusst konservativ gesetzt, keine gemessen — und vor jedem
Live-Gedanken zu belegen (Stufe 1: ändern heißt sichern, echter Lauf, Commit).
