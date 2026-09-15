# Spur `iv_wand` (Papier) - der Strike mit dem groessten Open Interest

Im Optionsmarkt liegt bei bestimmten Strikes viel offenes Interesse (Open
Interest). Dort sitzen die Absicherungen, und der Kurs wird von diesen Zonen
angezogen oder abgestossen - die "Wand". Diese Spur rechnet sie selbst aus den
oeffentlichen OKX-Daten.

## Wie die Wand entsteht

1. OKX `/public/open-interest?instType=OPTION&uly=BTC-USD` - Open Interest je
   Option (`oiUsd`).
2. OKX `/public/opt-summary?uly=BTC-USD` - implizite Volatilitaet je Option
   (`markVol`).
3. Nur Verfaelle in **7 bis 45 Tagen** (nahe Verfaelle, wo gehandelt wird).
4. Open Interest je **Strike** summieren (Call + Put gehoeren zusammen - beide
   Seiten hedgen am selben Punkt). Der groesste Strike ist die Wand; die
   durchschnittliche IV dieses Strikes steht als Notiz im Zustand.

## Regel

- Spot **unter** der Wand, Abstand <= `max_abstand_pct` (5 %) -> **long**,
  Ziel ist die Wand.
- Spot **ueber** der Wand, im selben Abstand -> **short**, Ziel ist die Wand.
- Weiter weg oder genau auf der Wand -> kein Geschaeft.

Der Stop ist ein fester Prozentsatz (4 %), die Groesse risiko-normiert. Das
**Ziel ist ein Marktpunkt**, kein Vielfaches des Stops - dafuer hat das
gemeinsame Buch (`Handel/spur_buch.py`) den Parameter `ziel_preis`. Ein Ziel
hinter dem Einstieg wird abgelehnt statt gebucht (das waere sofort erreicht).

## Grenzen

- **Kein Optionshandel.** Gehandelt wird der Spot-Papierpreis (BTC-USDT), nicht
  die Option. Die Optionen liefern nur die Zone.
- **Kein Live-Zweig.** `--live` verweigert.
- **Eine Position** (`max_offene_positionen = 1`): die Wand ist eine Zone, nicht
  viele. Wechselt sie, wird die alte Position erst durch Stop/Ziel geschlossen.
- Die Wand aendert sich mit dem Open Interest. Jeder Zyklus liest sie neu; das
  Journal nennt den Strike, der beim Einstieg galt.

## Aufruf

```powershell
cd Agenten/Handel/iv_wand
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau
..\scanner\.venv\Scripts\python.exe handeln.py --papier
..\scanner\.venv\Scripts\python.exe handeln.py --wachen
```

Tests ohne Netz: `python -m unittest test_iv_wand` **aus dem Ordner `tests/`**.
