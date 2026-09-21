# Betriebsfehler in Spuren finden (Spur laeuft, schreibt aber kein Journal)

Ausloeser: `auswertung_alle.py` meldet fuer eine laufende Spur "kein Buch" /
"keine geschlossene Runde", obwohl `zustand.json` frisch ist. Das ist der
verdaechtigste Zustand im ganzen Handelsbaum: die Spur meldet dem Dauerlauf
"ok", bucht aber nie. Drei Ursachen decken die Faelle ab (alle am 20.09.2026
real gefunden).

## Reihenfolge der Pruefung

1. **Wachen-JSON parst?** Der haeufigste und stillste Fehler.
   ```
   scanner/.venv/Scripts/python.exe -c "import json;[print(s, json.load(open(s+'/wachen.json',encoding='utf-8')) and 'ok') for s in ['SPUR']]"
   ```
   Ein kaputtes `wachen.json` laesst die Spur in JEDEM Zyklus beim Laden
   abstuerzen. Im Dauerlauf-Log steht dann `Rueckgabe 1` statt `ok` - das
   unterscheidet diesen Fall von den anderen beiden.
   Reparatur binaer, CRLF erhalten:
   ```python
   import re, json
   b = open(p, 'rb').read()
   neu = re.sub(rb',(\s*)\]', rb'\1]', b, count=1)   # trailing comma
   open(p, 'wb').write(neu)
   json.load(open(p, encoding='utf-8'))              # Gegenprobe
   ```

2. **Vorschau-Lauf ohne Absturz?**
   `scanner/.venv/Scripts/python.exe SPUR/handeln.py --vorschau`
   Exit 0 heisst nur: kein Absturz. Es heisst NICHT, dass die Spur ein
   Signal bilden kann - siehe Punkt 3.

3. **Bildet `signal()` ueberhaupt je ein Signal?** Der teuerste Fehler, weil
   die Spur tagelang gruen laeuft. Nie an der Ausgabe messen, sondern den
   Indikator ueber die letzten N Kerzen zaehlen lassen:
   ```python
   w = h.lade_wachen(); inst = w['instrumente'][0]
   k = h.lade_kerzen(inst, w.get('zeitrahmen','4H'), 300)
   tr = [i for i in range(len(k)-200, len(k)) if h.signal(k, i)]
   print('Signale in 200 Kerzen:', len(tr))
   ```
   0 Signale bei einem Trendwechsel-Indikator ueber 200 Kerzen ist ein
   Befund, keine Marktlage.

## Der stille Import (supertrend, 5 Tage signalfrei)

```python
try:
    sys.path.insert(0, HANDEL)
    import indikatoren as xi
except ImportError:
    return None          # <- verschluckt den Fehler, Spur laeuft "gruen"
```
`Handel/indikatoren.py` gibt es nicht - `supertrend()` liegt in
`xperp/indikatoren.py` (so steht es auch im README der Spur). Der Import
schlug still fehl, `signal()` gab IMMER None zurueck.

Regel: **Ein fehlender Indikator ist kein "kein Signal", sondern ein
Abbruch.** Import auf den richtigen Ordner ziehen und laut werden lassen:
```python
xperp = os.path.join(HANDEL, "xperp")
if xperp not in sys.path:
    sys.path.insert(0, xperp)
import indikatoren as xi
# except ImportError -> raise RuntimeError(...), nie return None
```
Gegenprobe nach dem Fix ist Pflicht: Signale in den letzten 200 Kerzen
zaehlen (oben). Vorher 0, nachher 6 - erst das beweist den Fix.

## Journal an fremdem Ort (nautilus_kraken_futures)

Eine Spur kann eine zweite Strategie im Ordner einer anderen fahren:
`nautilus_kraken_futures` hat keinen eigenen Ordner, ihr Buch ist
`nautilus_kraken/handelsjournal.futures.csv`. `auswertung_alle.py` suchte
`HIER/<spur>/handelsjournal.csv` und meldete "kein Buch" bei 105 gefuellten
Zeilen.

Loesung in `auswertung_alle.py` - eine Zuordnung, die `hat_buch()` UND
`zeilen()` gemeinsam nutzen (sonst laufen die beiden auseinander):
```python
FREMDES_BUCH = {
    "nautilus_kraken_futures": ("nautilus_kraken", "handelsjournal.futures.csv"),
}

def _ort(spur, datei):
    if spur in FREMDES_BUCH:
        ordner, eigene = FREMDES_BUCH[spur]
        return ordner, (eigene if datei == "handelsjournal.csv" else datei)
    return spur, datei
```
Die Risikostufen-Umbenennung (`risikostufe.datei_fuer`) muss VOR `_ort()`
laufen, damit `handelsjournal.mittel.csv` nicht zur Futures-Datei wird.

## Was KEIN Betriebsfehler ist

Eine Spur ohne Journal, die erst wenige Tage laeuft und deren Tor selten
aufgeht (iv_wand, iv_waelle), ist eine wahre Aussage - nicht reparieren.
Unterscheidungsmerkmal: `signal()` liefert im 200-Kerzen-Test Treffer, es
fehlt nur die Gelegenheit.

## Auswertung im Hintergrund fahren

`auswertung_alle.py` holt Live-Kurse fuer alle offenen Positionen und
braucht ueber 7 Minuten - laeuft im Vordergrund in den Tool-Timeout.
Immer als Hintergrundlauf mit Log:
```
scanner/.venv/Scripts/python.exe auswertung_alle.py > auswertung_alle_lauf.log 2>&1
```
danach `read_file` auf das Log (233 Zeilen, Uebersichtstabelle am Ende).
