# scanner_quant — Quant-Urteil für Scanner (Spot) und xperp-Auswahl (Long/Short)

Stand: 2026-10-07. **Kopien** von `../scanner/scan.py` und `../xperp/auswahl.py`, damit
die Altspuren unberührt bleiben. Handelt nichts, schreibt nur nach `berichte/` (und nicht im `--kurz`-Lauf).

## Was dazukommt

`quant.py` rechnet je Tageskerzenreihe (mind. `lang` + 10 Kerzen, sonst kein Urteil;
`lang` = 200 für Spot, 100 für xperp) für `richtung="long"` oder `"short"`:

| Größe | Bedeutung |
|---|---|
| `ordnung` 0–4 | Long: Kurs > SMA20 > SMA50 > SMA`lang` und Kurs > SMA`lang`; Short: alles umgekehrt |
| `effizienz30` | Kaufman: Nettoweg / Gesamtweg über 30 Tage; Trend vs. Zappeln |
| `dehnung_atr` | Abstand zur SMA50 in ATR-Einheiten **in Richtung**; über 6 = `zu_gedehnt` (beim Short: Absturz, Squeeze-Gefahr) |
| `schwung_je_atr` | 20-Tage-Rendite je ATR14, beim Short vorzeichenverkehrt |
| `korr_ref_60t`, `rel_staerke_30t_pct` | gegen BTC, nur zur Information |
| `quant_score` 0–100 | gewichtet aus den ersten vier; **bei `zu_gedehnt` auf 50 gedeckelt** |

Warum ATR statt z-Wert für die Dehnung: der z-Wert der letzten 50 Schlusskurse ist
bei einer steilen Rampe nach oben gedeckelt (gemessen: +100 % in 20 Tagen ergibt nur
z = 2,5) und trennt Spitzen deshalb nicht von normalen Trends. Der z-Wert steht
trotzdem im Ergebnis (`dehnung_z`).

Trendgüte und „nicht gedehnt“ zählen nur, wenn der Kurs auf der richtigen Seite der
SMA50 steht. Ohne diese Bedingung bekam ein sauberer *Ab*wärtstrend als Long 45 von 100
(gemessen am Testfall, vor dem Fix).

## Verdrahtung

- `okx.py`, `bewertung.py`, `wachen.json` werden aus `../scanner` **gelesen**, nicht
  kopiert — eine Börsenanbindung, eine Grenzdatei.
- `quant.json` steuert die Wirkung. **Standard: `"modus": "bericht"`** — nur zusätzliche
  Spalten, die Tor-Spalte bleibt wie im Original. `"modus": "tor"` verlangt zusätzlich
  `quant_score >= mindest_quant_score` und nicht `zu_gedehnt`. `"aktiv": false` = Lauf
  wie das Original.
- Tracking-Spur heißt `scanner_quant`, nicht `scanner`.

## xperp (Short und Long)

`auswahl_quant.py` ist die Kopie von `xperp/auswahl.py`: gleiche Kennzahlen, Tore und
Listen, dazu die Spalte `Q` (Quant-Score der Richtung der Liste) und `!qd` (gedehnt).
`--rang quant` sortiert Long-/Short-Liste nach dem Quant-Score statt nach den Punkten.
Das Urteil kommt aus den Tageskerzen, die `sammle()` ohnehin holt, es gibt keinen
zusätzlichen Abruf. `okxf.py` wird aus `../xperp` gelesen.

**`LANG = 100` statt 200:** Am 07.10.2026 hatte keiner der 181 Kontrakte 210 Tageskerzen,
mit 200 wäre die Spalte komplett leer geblieben. Mit 100 bekommen rund 40 ein Urteil,
die jüngeren zeigen `-`.

## Aufrufe

```
python scanner_quant/scan.py --kurz      # Tabelle, schreibt nichts
python scanner_quant/scan.py             # mit Bericht nach berichte/
python scanner_quant/auswahl_quant.py --zweck short --rang quant
cd scanner_quant && python -m unittest discover -s tests
```

## Offen (bewusst)

- **Nicht belegt, ob das Urteil trennt.** Erst im Modus `bericht` laufen lassen und
  mit den späteren Ausgängen vergleichen (Journal), dann entscheiden, ob `tor` sperren
  darf. Die Gewichte in `quant.GEWICHTE` und die Schwellen sind Annahmen, keine
  Messung.
- **Live-Pfad von xperp nicht verdrahtet:** `xperp/handeln.py` und `bot.py` sind nicht
  kopiert. Die Quant-Spalte ist ein Vorschlag in der Rangliste, keine Sperre im
  Handel. Dort erst verdrahten, wenn die Messung (oben) das Urteil trägt.
- Funding (beim Short ein Zuschuss oder Kostenpunkt) fließt nicht ins Urteil ein.
- Werte mit unter 210 Tageskerzen (z. B. OKB) bekommen kein Urteil; im Tor-Modus
  gilt das Tor für sie als zu.
