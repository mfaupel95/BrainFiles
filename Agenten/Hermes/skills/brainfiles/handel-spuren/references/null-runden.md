# „Null Runden" - welche Null ist es?

Wann: Die Auswertung meldet fuer eine Spur `keine geschlossenen Runden`, oder die
Frage kommt als „warum hat X 0 Runden, da stimmt doch etwas nicht".

## Erst trennen, dann suchen

Eine Null hat vier Bedeutungen. In der Auswertung sehen sie gleich aus, es sind
aber vier verschiedene Lagen - nur eine davon ist ein Fehler:

| Lage | Kennzeichen | Fehler? |
|---|---|---|
| wartet auf das erste Signal | Journal leer, keine Position, Zustand frisch | nein |
| arbeitet, Stop noch nicht erreicht | Positionen im Buch, Journal ohne Ausstieg | nein |
| Ausbuecher ohne Handelsentscheidung | Journal nur mit `buchbereinigung`/`herzschlag` | nein (Anzeige!) |
| **Stall** | offene Position, deren Instrument nicht mehr geprueft wird | **ja** |

Merksatz: Eine Null ist erst dann eine Aussage, wenn dabeisteht, was sie zaehlt.
Ein Text, der alle vier Lagen gleich beschreibt, versteckt genau den einen echten
Fehler. Beim Bauen einer Kennzahl die Gegenfrage stellen: welche Zustaende fallen
auf denselben Satz?

Beleg-Nachweis statt Vermutung: `auswertung_alle.offene_positionen(spur)` liest
den Zustand tolerant (fehlende Datei, kaputtes JSON, fehlendes `positionen`-Feld
geben `None`) und `zeige()` nennt die Lage im Klartext - „aber N offene
Position(en) im Buch", „daneben N Ausstiege ohne Handelsentscheidung", „wartet
auf ihr erstes Signal".

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

Die drei Helfer liegen in `scanner/wachen_pruefung.py` und gehoeren dorthin, wo
`wp` schon importiert ist - die Spur selbst wird nicht umgebaut.

## Den Stall in allen Spuren finden (Audit-Rezept)

    cd BrainFiles
    git grep -l '"instrumente"' -- 'Agenten/Handel/*/wachen*.json'
    grep -n 'for inst in\|instrumente' Agenten/Handel/<spur>/handeln.py

Jeden Fund einordnen, bevor etwas geaendert wird - nicht jede Liste ist ein
Fehler:

- **Ausstiegs-Schleife ueber die Planliste** = die Falle, umstellen.
- **Einstiegs-Schleife** ist richtig so (Einstiege bleiben auf den Plan
  begrenzt); eine Spur darf daneben eine solche Schleife behalten.
- **Schleife ueber die Marktdaten des Zyklus** (`for inst in sorted(daten)`) ist
  sicher.
- **Datensammel-Schleife ueber die Planliste** ist derselbe Fehler eine Ebene
  tiefer: eine Position auf einem gestrichenen Symbol bekommt keinen Kurs mehr.
  `spur_buch` meldet den fehlenden Kurs jetzt, schliesst die Position aber nicht.

## Buchformat und Rechenweg

- **Kein Rechenweg.** Ein Journal fuehrt Aktionen, die der Verteiler nicht kennt
  (Arme buchen `eroeffnen`/`schliessen`, nicht `kauf`/`verkauf`) - Ergebnis ist
  eine harte Null bei vorhandenen Runden. Neues Buchformat heisst immer:
  Rechenweg an der EINEN Stelle nachziehen (`runden_fuer()`), nicht in jedem
  Aufrufer.
- **Fehlender Kurs.** Eine Position ohne Kurs darf nicht stillschweigend
  uebersprungen werden - melden, sonst blockiert sie unsichtbar.
- **Ausbuecher** (`buchbereinigung`, Zwangsschluss) sind zu Recht keine Runden -
  aber dann muss die Anzeige genau das sagen.

## Ein Test gegen die Zeile meldet Umbau, keine Fehler

Der Test, der eine solche Regel festhaelt, prueft die EIGENSCHAFT: im Quelltext
muss `if inst in plan:` unmittelbar vor dem Einstiegsaufruf stehen - gleich wie
der Aufruf heisst und wie er eingerueckt ist (Muster statt exakter Zeile). Ein
Test gegen eine exakt eingerueckte Zeile oder gegen `inspect.getsource(<eine
Funktion>)` wird bei jeder Verlagerung rot, ohne dass sich am Verhalten etwas
geaendert hat; eine verlegte Zuordnung ist kein Fehler. Ebenso: eine feste Zahl
oder ein Commit-Hash als Erwartung meldet Aenderung, nicht Fehler - pruefe die
Regel.

## Nachweis

    cd Agenten/Handel
    scanner/.venv/Scripts/python.exe auswertung_alle.py | grep -A3 "=== <SPUR> ==="
    scanner/.venv/Scripts/python.exe -c "import auswertung_alle as a; print(a.runden_fuer('<spur>'))"

Ein Nachweis ist keine Wache: fuer Spuren, die still stehen sollen, gehoert ein
Cron dazu (Muster `Agenten/Hermes/scripts/spur-wache.py`). Nach jeder Aenderung
an den Buchpfaden zusaetzlich `spiegelstand.py` laufen lassen - die Buecher
muessen byte-gleich nach Q: gespiegelt sein.
