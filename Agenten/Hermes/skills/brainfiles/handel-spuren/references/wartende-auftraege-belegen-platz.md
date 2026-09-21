# Wartende Auftraege belegen einen Platz

## Der Vorfall

xperp hatte an EINEM Abend **13 offene Limit-Auftraege** an der Boerse stehen:
CL sechsmal, XAU fuenfmal, BZ und CRCL je einmal. Max meldete das als "viele
positionen mehrfach gebucht".

Es waren **keine Positionen**. `/account/positions` kannte nur BTC-Short und
HBAR. Die 13 lagen in `/trade/orders-pending`.

## Die Ursache

xperp setzt seinen Einstieg aus einer Zonenrechnung - also ein **Kauflimit
unter dem Markt** (gemessen: CRCL 93.81 bei Markt 94.84). Solange es nicht
fuellt, ist es ein *wartender Auftrag* und noch **keine Position**.

`pruefe_einstiege()` zaehlte aber nur `z["positionen"]`:

```python
belegt = z["positionen"]                      # FALSCH
if len(belegt) >= w["max_offene_anlaeufe"]:
    return
```

Folge: nach dem Stellen war fuer Platz, Margin **und Familienanteil** alles
unveraendert - der naechste Zyklus legte fuer denselben Basiswert nach. Und der
uebernaechste. Sechs Stueck CL.

## Die Regel

**Alles, was Kapital binden KANN, belegt einen Platz - nicht erst das, was es
schon bindet.**

```python
belegt = list(z["positionen"]) + list(z.get("wartende", {}).values())
```

Das gilt fuer jede Spur mit Limit-Einstieg. Eine Spur, die nur marktbar kauft,
hat das Problem nicht - genau deshalb faellt es beim Umbau auf Limit-Einstieg
nicht von selbst auf.

## Aufraeumen: der juengste Auftrag gewinnt

`xperp/dubletten_stornieren.py` (Trockenlauf ist Standard, `--anwenden` noetig)
laesst je Basiswert **den juengsten** Auftrag stehen - er traegt den aktuellsten
Zonenpreis - und storniert die aelteren. 13 -> 4. Danach das Buch
(`zustand["wartende"]`) gegen die Boerse nachziehen, nicht umgekehrt.

## Fallen, beide teuer bezahlt

**1. Doppelte JSON-Kodierung.** `okxf._roh` macht `json.dumps(body)` selbst.
Wer einen fertigen JSON-String uebergibt, bekommt HTTP 400 - neunmal, bis man
es sieht. **Body als dict uebergeben.**

**2. Die Diagnose an der falschen Stelle.** "Mehrfach gebucht" erst an
`/trade/orders-pending` UND `/account/positions` pruefen, bevor man im Buch
sucht. Das Buch war hier korrekt - die Boerse nicht.

## Test-Muster

Der Test muss den Zaehler treffen, nicht den Effekt:

```python
def test_wartender_auftrag_belegt_einen_platz(self):
    z = {"positionen": [], "wartende": {"CL-100": {...}}}
    w = {"max_offene_anlaeufe": 1, ...}
    # kein zweiter Anlauf, obwohl 0 Positionen offen sind
    self.assertEqual(handeln.pruefe_einstiege(z, [kand], False), None)
```

Gegenprobe: Fix stashen, Tests laufen lassen - bei xperp fielen 3 von 8.
