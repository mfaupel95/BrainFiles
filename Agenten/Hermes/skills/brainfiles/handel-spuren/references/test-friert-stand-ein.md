# Ein Test darf einen STAND einfrieren

## Das Muster

Ein Test, der gegen einen Commit-Hash, eine Byte-Gleichheit oder eine feste
Anzahl prueft, meldet **Aenderung**, nicht **Fehler**. Er wird rot, sobald
jemand woanders korrekt arbeitet - und faellt dann als Rauschen durch, bis
ihn niemand mehr ernst nimmt. Das ist schlimmer als kein Test.

Drei Faelle aus BrainFiles, alle am selben Tag (21.09.2026):

| Test | Was er einfror | Was daran kaputtging |
|---|---|---|
| `Bus/tests/test_anbindung_handel.test_melder_bleibt_unveraendert` | `melder.py` byte-genau gegen Commit `3a9b6e5` | Nach der Telegram-400-Reparatur rot, obwohl die Spec unverletzt war |
| `tests/test_lage.test_holer_sind_vollzaehlig` | genau 28 Holer | Jede neue Spur macht ihn rot |
| `tests/test_risikovorfilter` | festes JETZT `2026-09-17 12:00` | Wurde mit dem Kalender falsch, nicht mit dem Code |

## Die Regel

**Pruefe die EIGENSCHAFT, die gelten soll - nicht den Zustand, in dem sie
gerade zufaellig steht.**

Die Spec hinter dem melder-Test lautete: *melder.py wird nur aufgerufen, nicht
zur Bus-Stelle umgebaut.* Das ist pruefbar, ohne einen Hash zu nennen:

```python
# schlecht - friert einen Stand ein
self.assertEqual(hashlib.sha256(quelle).hexdigest(), "3a9b6e5...")

# gut - prueft die Regel
self.assertNotIn("import ereignis", quelle)
self.assertNotIn("bus.py", quelle)
self.assertNotIn("8787", quelle)
```

Und statt einer festen Anzahl die Beziehung zur Quelle der Wahrheit:

```python
# schlecht
self.assertEqual(len(lage.HOLER), 28)

# gut - jede Spur aus dauerlauf.SPUREN hat einen Holer,
# Praefix erlaubt (xperp liest ueber spur_xperp_positionen)
for spur in dauerlauf.SPUREN:
    self.assertTrue(any(name.startswith("spur_" + spur)
                        for name in lage.HOLER))
```

Bei Zeitbezug: die Zeit als Parameter hereingeben, nie `datetime.now()` gegen
eine Konstante im Test stellen.

```python
# gut - der Test waehlt die Zeit, die Funktion rechnet
self.assertTrue(wx.wochenende_sperrt(W, _zeit(4, 19, 0)))   # Fr 19:00 UTC
self.assertFalse(wx.wochenende_sperrt(W, _zeit(0, 9)))      # Mo 09:00
```

## Wann ein eingefrorener Stand DOCH richtig ist

Wenn die Unveraenderlichkeit selbst der Vertrag ist und es keine formulierbare
Eigenschaft gibt - etwa bei einer Fixture-Datei, deren Inhalt eine gemessene
Realitaet festhaelt (`kerzen_BTC-USDT_1H_8760.json`). Dann gehoert in den Test
eine Zeile, die sagt WARUM eingefroren wird, und wer ihn erneuern darf.

## Gegenprobe beim Umbau

Nach dem Umbau muss der Test den urspruenglichen Fehler noch fangen. Also:
Regel verletzen (z. B. `import ereignis` testweise in `melder.py` schreiben),
Test laufen lassen, rot sehen, zuruecknehmen. Ein umgebauter Test, der nichts
mehr faengt, ist ein geloeschter Test mit Zeremonie.
