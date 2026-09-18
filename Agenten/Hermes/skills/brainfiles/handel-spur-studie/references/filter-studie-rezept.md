# Rezept: Eingangsfilter-Studie auf den Kopier-Spuren

## 1 Feldinventar (welche Hebel sind pruefbar)

`spiegel/handelsjournal.csv` und `kopier/handelsjournal.csv` tragen:
`zeit, modus, aktion, kette, wallet, token, symbol, preis, menge,
einsatz_usd, wert_usd, marktkap_usd, slippage_pct, gebuehr_pct, grund`.
`kopier1zu1` traegt zusaetzlich `wallet_name, tx, trade_zeit, preis_vorbild,
preis_einstieg, kurs_ausstieg`.

- **Pruefbar:** Marktkapitalisierung beim Einstieg, Kette, Wallet, Zeitpunkt,
  Ausstiegsgrund, Einsatz/Wert je Runde.
- **Aktionsnamen sind je Spur verschieden** (`schliessen` vs. `AUSSTIEG`);
  das Fixture muss den Namen der Zielspur treffen, sonst liest die Auswertung
  null Zeilen und die Studie meldet still ein leeres Bild.
- **Nicht pruefbar:** Signalalter (steht nur in `ablehnungen.csv`, und dort nur
  fuer abgelehnte Signale ohne Ergebnis), Buchtiefe je Token, realisierter
  Nachlauf (Slippage ist eine Annahme, keine Buchung).

## 2 Buchhaltung anbinden

```python
spec = importlib.util.spec_from_file_location("auswertung_%s" % spur, pfad)
modul = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = modul
spec.loader.exec_module(modul)
aus = modul.lade_ausstiege()      # optional: lade_ausstiege(pfad)
kosten = modul._kosten()          # Rueckfall, wenn die Zeile keine Kostensaetze traegt
```

Kennzahlen immer ueber `buchauswertung.kennzahlen(aus, kosten)`; die Ausstiegs-Dicts
tragen `zeit, name, grund, einsatz, wert, netto_pct` plus die Extraspalten
`kette, symbol, token, marktkap_usd, wallet` und `kosten` (Faktorpaar).
Die Marktkapitalisierung wird intern ueber die `eroeffnen`-Zeilen je `token`
ggelesen - im Fixture muss die Eroeffnungszeile sie tragen, sonst ist sie leer.

## 3 Regelsatz und Verdikt

- Untergrenzen `marketcap_band_usd`: 100k, 150k, 250k, 500k (Status 50k).
- Obergrenzen: 1M (Status), 2M, 5M.
- Kette: nur Solana.
- Gegenproben-Regel: Band verschieben statt oeffnen (z. B. Untergrenze 250k
  und Kette ungleich Solana) - sie muss schwach oder negativ ausfallen.

Verdikt: `traegt`, wenn beide Haelften besetzt (>= 30) und positiv sind und
beide die Restgruppe schlagen; `nicht entschieden` bei zu kleiner Gruppe;
sonst `verworfen`.

## 4 Testfixture (synthetisches Journal)

Kopfzeile: dieselben Spalten wie das echte Journal. Je Posten ZWEI Zeilen mit
**gleichem `token`**:

1. `eroeffnen` mit `marktkap_usd`, `einsatz_usd`, `slippage_pct`, `gebuehr_pct`
2. `schliessen` mit `einsatz_usd` und `wert_usd` (ohne Marktkap - die kommt
   ueber den Token-Join)

Zeiten so streuen, dass beide Zeithaelfte besetzt sind (sonst lautet jedes
Verdikt "nicht entschieden" und der Test prueft nichts). Ausgang konstruieren,
nicht zufaelligen: ein Band gewinnt, das andere verliert - dann kippt die
invertierte Datenlage das Verdikt und die Gegenprobe ist belegt.

## 5 Befehle

```bash
cd Agenten/Handel
scanner/.venv/Scripts/python.exe filter_studie.py --spur spiegel --json
scanner/.venv/Scripts/python.exe spiegel/auswertung.py      # Soll-Zahlen, Paritaet
cd tests && ../scanner/.venv/Scripts/python.exe -m unittest test_filter_studie
```

Die Spurtestsuiten laufen aus dem `tests`-Ordner (`python -m unittest test_x`);
aus dem Spurenordner scheitert `discover` mit "not importable".

## 6 Versionierung

Neue Ordner und Ergebnisdateien brauchen eigene `!`-Zeilen in `.gitignore`
(jede Ebene einzeln), sonst bleibt die Arbeit unversioniert:
`!Agenten/Handel/docs/design/`, `!Agenten/Handel/docs/plans/`,
`!Agenten/Handel/filter_studie_ergebnis.json`. Gegenprobe:
`git status --porcelain -- <ordner>` zeigt `??` (sichtbar) statt `!!`.
