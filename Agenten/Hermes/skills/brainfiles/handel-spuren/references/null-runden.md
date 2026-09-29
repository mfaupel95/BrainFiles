# „Null Runden" - welche Null ist es?

Wann: Die Auswertung meldet fuer eine Spur `keine geschlossenen Runden`, oder
Max fragt „warum hat X 0 Runden / da stimmt doch etwas nicht".

## Erst trennen, dann suchen

Eine Null hat vier moegliche Bedeutungen. Sie sehen in der Auswertung gleich
aus, sind aber vier verschiedene Lagen - und nur zwei davon sind ein Fehler:

| Lage | Kennzeichen | Fehler? |
|---|---|---|
| wartet auf das erste Signal | Journal leer, keine Position, Zustand frisch | nein |
| arbeitet, Stop noch nicht erreicht | Positionen im Buch, Journal ohne Ausstieg | nein |
| Ausbuecher ohne Handelsentscheidung | Journal nur mit `buchbereinigung`/`herzschlag` | nein (Anzeige!) |
| **Stall** | offene Position, deren Instrument nicht mehr geprueft wird | **ja** |

Die Auswertung nennt seit dem 29.09.2026 alle vier im Klartext
(`auswertung_alle.offene_positionen()`, `zeige()`). Vorher stand ueberall
derselbe Satz „keine geschlossene Runde" - das ist der Grund, warum ein
echter Stall unbemerkt bleibt.

## Die Stall-Falle (der teuerste der vier Faelle)

Ein Zyklus, der seine Ausstiege ueber `for inst in w["instrumente"]` faehrt,
verliert jede Position, deren Instrument spaeter aus der Liste genommen wird
(Instrumententausch, Boersenwechsel, Quote-Wechsel USDT -> USDC). Sie wird nie
wieder angesehen, nie geschlossen, belegt den Platz und steht im Buch.

Regel: **Ausstiege laufen ueber Plan + Bestand, Einstiege nur ueber den Plan.**

```python
plan = wp.plan_instrumente(w)              # die Wachenliste
verwaist = wp.verwaiste_instrumente(w, z)  # offen, aber nicht mehr im Plan
if verwaist:
    print("Verwaiste Instrumente ...", file=sys.stderr)   # melden, nie still
for inst in wp.pruef_instrumente(w, z):    # Plan + Bestand
    ...
    if inst in plan:                       # Einstieg bleibt begrenzt
        pruefe_einstieg(...)
```

Angewandt auf macd_mtf, squeeze, wavetrend, supertrend (29.09.2026; squeeze
schloss daraufhin zwei SOL-USDT-Positionen, die acht Tage unangetastet lagen)
und mosaic (Papierzweig). Test, der die Regel im Quelltext festhaelt:
`Agenten/Handel/tests/test_verwaiste_instrumente.py` - pruefe die Eigenschaft
per Muster, nicht eine eingerueckte Zeile.

## Zwei weitere Ursachen, die wie eine Null aussehen

- **Fehlender Kurs.** `spur_buch.pruefe_ausstiege` uebersprang eine Position ohne
  Kurs stillschweigend. Jetzt wird sie gemeldet - die Position bleibt stehen,
  aber man sieht es.
- **Kein Rechenweg.** Ein Journal fuehrt Aktionen, die `kennzahlen_fuer()`
  nicht kennt: die nautilus-Arme buchen `eroeffnen`/`schliessen`, nicht
  `kauf`/`verkauf`. Ergebnis war eine harte Null bei vorhandenen Runden
  (`runden_nautilus`, seit 29.09.2026: nautilus 0 -> 7 Runden).
  Ein NEUES Buchformat heisst also immer: Rechenweg in `runden_fuer()`
  nachziehen.

## Nachweis, nicht Vermutung

    cd Agenten/Handel
    scanner/.venv/Scripts/python.exe auswertung_alle.py | grep -A3 "=== <SPUR> ==="
    scanner/.venv/Scripts/python.exe -c "import auswertung_alle as a; print(a.runden_fuer('<spur>'))"

Ein Nachweis ist keine Wache: fuer Spuren, die still stehen sollen, gehoert ein
Cron dazu (Muster `Agenten/Hermes/scripts/spur-wache.py`).