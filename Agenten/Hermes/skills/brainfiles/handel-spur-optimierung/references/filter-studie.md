# Eingangsfilter-Studie (Rezept)

Werkzeug im Haus: `Agenten/Handel/filter_studie.py`, Ergebnis
`Agenten/Handel/filter_studie_ergebnis.json`, Test
`Agenten/Handel/tests/test_filter_studie.py`. Spuren mit eigener
Auswertung: `spiegel`, `kopier`, `kopier1zu1`.

## Aufruf

```bash
cd Agenten/Handel
./scanner/.venv/Scripts/python.exe filter_studie.py              # alle Spuren, Bericht
./scanner/.venv/Scripts/python.exe filter_studie.py --spur spiegel --json
cd tests && ../scanner/.venv/Scripts/python.exe -m unittest test_filter_studie
```

Der Test laeuft aus `tests/` heraus (Spurentestsuiten laufen nur aus dem eigenen
Ordner). `--journal` ist der Testhaken: dieselbe Journaldatei fuer alle Spuren.

## Paritaetsprobe (Pflicht vor jeder Zahl)

Die Studie muss dieselbe Kopfzahl liefern wie die Spur selbst:

```bash
./scanner/.venv/Scripts/python.exe spiegel/auswertung.py | grep -E 'Ausstiege|Kosten'
```

Erwartet: identische Anzahl Ausstiege und identische Ø-Werte vor/nach Kosten.
Weicht die Studie ab, ist die Studie falsch — nicht die Spur.

## Regelkatalog

Je Spur gemessen, jede Regel gegen Gesamt, beide Zeithaelfte und die
Restgruppe:

| Regel | pruef() |
|---|---|
| `untergrenze <x>` | `marktkap_usd >= x` fuer x in 100k, 150k, 250k, 500k |
| `obergrenze <x>` | `marktkap_usd <= x` fuer x in 2M, 5M (Status ist 1M) |
| `nur solana` | `kette == "solana"` |
| `untergrenze 250k ohne solana` | x >= 250k **und** kette != solana (Gegenprobe) |

Die letzten beiden sind die Gegenprobe: ein Band zu VERSCHIEBEN und die Kette zu
drehen muss die Gegenrichtung zeigen.

## Verdikt (die vier Bedingungen an EINER Stelle)

```python
if alt["n"] < mindest or jung["n"] < mindest:
    return "nicht entschieden", "Gruppe zu klein"
if alt["netto"] <= 0 or jung["netto"] <= 0:
    return "verworfen", "in einer Haelfte nicht positiv"
if alt["netto"] <= rest_alt["netto"] or jung["netto"] <= rest_jung["netto"]:
    return "verworfen", "kein Vorsprung gegen die Restgruppe"
return "traegt", "in beiden Haelften positiv und besser als der Rest"
```

`alt`/`jung` sind die REGEL-Gruppe je Zeithaelfte, `rest_*` die Restgruppe
derselben Haelfte. Die Halbierung passiert auf der VOLLEN Liste und wird dann je
Regel gefiltert — sonst sind die Haelften nicht vergleichbar.

## Kennzahlen je Gruppe

Aus `buchauswertung.kennzahlen(teilmenge, kosten)`:
`n`, `quote` (Trefferquote), `netto_pct` (nach Kosten), `brutto_pct` (vor
Kosten), `median_pct`, `gv_usd`. Kosten je Zeile kommen aus den Spalten
`slippage_pct`/`gebuehr_pct` des Journals, sonst aus `_kosten()` der Spur.

## Was die Kennzahlen typischerweise zeigen (Muster, nicht Ort)

- Der **Stop** stellt den groessten Block der Ausstiege und realisiert mehr
  Verlust als der Deckel vorsieht: Memecoin-Buecher rutschen durch den Stop.
  Deshalb ist die Ausstiegsform die wichtigere Frage als jeder Eingangsfilter —
  und die einzige, die ein zweites Buch beantwortet.
- Die **untere Bandgrenze** ist der staerkste Eingangshebel; Obergrenzen,
  Kettenfilter und „nur die besten Wallets" fielen in der Pruefung durch.
- Kleine Buecher liefern durchweg „nicht entschieden". Das ist das Ergebnis,
  nicht ein Mangel des Werkzeugs.
- Vor Kosten liegt eine solche Kopier-Spur oft nahe Null: die Slippage-Annahme
  ist der groesste Einzelposten. Jede Aussage ohne Vor-Kosten-Spalte ist blind.
