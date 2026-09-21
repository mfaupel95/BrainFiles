# Buch gegen Boerse stellen: Fuellung, Geister, Wiederherstellung

Rezept zur Regel „das Buch gegen den Handelsplatz pruefen" aus dem SKILL.md.
Gilt fuer jede OKX-Live-Spur; die Haus-Funktionsnamen stehen in `spur/okxf.py`
bzw. `spur/okx.py` und sind ueberall gleich benannt.

## 1. Wer hat recht? (immer die Boerse)

| Frage | Aufruf | Lesart |
|---|---|---|
| Bestand | `okxf.positionen()` → `/api/v5/account/positions` | Liste mit `instId`, `pos`, `notionalUsd`, `upl`, `ccy` |
| Im Buch, nicht an der Boerse | Buch `zustand.json` gegen die Liste | Geist: ausbuchen + offene Order stornieren |
| An der Boerse, nicht im Buch | Liste gegen das Buch | unverwaltet: keine Ausstiegslogik, kein Funding |
| Order wirklich gehandelt? | `okxf.gefuellte_kontrakte(inst, ord_id)` → `accFillSz` | `0` = angenommen, nicht gefuellt |
| Offene Orders | `okxf.offene_orders(inst=None)` → `orders-pending` | `state live` = liegt noch |
| Schutz vorhanden? | `okxf.schutz_stops(inst)` → `orders-algo-pending?instType=FUTURES&ordType=conditional` | leer = KEIN boersenseitiger Stop |

`state` allein taugt nicht: eine gefuellte Order kann als `live` gelesen werden,
bevor die Positionsliste nachzieht — `accFillSz` ist die Zahl, die zaehlt.

## 2. Einstieg: pruefen, DANN buchen

1. `ord_id = okxf.order_limit(inst, seite, kontrakte, preis, tp=…, sl=…)`
2. `gehandelt = _warten_auf_fuellung(inst, ord_id, kontrakte)` — kurz warten
   (Sekundenbruchteile bis Sekunden), dann `accFillSz` lesen.
3. `0` oder unbekannt → `okxf.order_stornieren(inst, ord_id)`, Journalzeile
   `aktion=fehler, grund=order_nicht_gefuellt`, KEINE Position.
4. Teilfuellung → Rest stornieren, nur die gehandelte Menge buchen (Nominal neu
   rechnen), damit Plaetze und Bilanz stimmen.

## 3. Geister ausbuchen (idempotent, am Anfang jedes Live-Laufs)

Reihenfolge je Buchposition mit `modus=live`:

1. Bestand an der Boerse? vorhanden → stehen lassen.
2. Fehlt er: **Orderzustand fragen** (`gefuellte_kontrakte`). Gefuellt → echte
   Position, stehen lassen (die Positionsliste hinkt manchmal nach).
3. Sonst: offene Order stornieren, dann ausbuchen mit
   `grund=buchbereinigung_geist`, `modus=papier` in der Journalzeile.
4. Abfrage gescheitert → gar nichts tun und das melden.

Zwei Aufraeumer, zwei Ursachen: `bueche_papier_altlasten_aus()` (Position ohne
Live-Herkunft, Feld `modus`) und `bueche_geister_aus()` (kein Bestand an der
Boerse). Beide laufen im Live-Zweig VOR der ersten Sperrenpruefung.

## 4. Eine echte Position zurueck ins Buch

Werte aus der EROEFFNUNGSZEILE des Journals nehmen (Einstieg, Kontrakte,
Nominal, Margin, Hebel, Stop, Ziel, Liquidation) — nichts schaetzen, nichts aus
dem aktuellen Kurs rechnen. Als eigenes, einmal ausfuehrbares Werkzeug mit
Trockenlauf bauen (Muster: `xperp/hbar_zurueckbuchen.py`), `zustand.json` vorher
sichern, eine Journalzeile mit `grund=buchwiederherstellung` schreiben.
Danach `okxf.schutz_stops(inst)` pruefen und bei leerer Liste einen Stop mit
`okxf.schutz_stop_setzen(inst, seite, kontrakte, stop, ziel)` nachsetzen.

## 5. Nachweis

```bash
cd Agenten/Handel/<spur>/tests && ../.venv/Scripts/python.exe -m unittest discover -s . -t .
cd Agenten/Handel && scanner/.venv/Scripts/python.exe spiegelstand.py   # byte-gleich
cd Agenten/Handel/<spur> && ../scanner/.venv/Scripts/python.exe -c "import okxf; print(okxf.positionen())"
```

Ein Zyklus muss abgewartet werden (der Dauerlauf startet `handeln.py` je Zyklus
neu): erst danach sagt das Log `<spur> (live) ok`, ob die Sperrenkette den Lauf
ueberhaupt live fahren liess.

## Fallen

- **Tests, die `journal()` direkt aufrufen, schreiben in die ECHTE Journaldatei.**
  In Testklassen `journal` ersetzen (oder eine Attrappe der Spur nutzen) und den
  Spiegelnachweis danach fahren; sonst meldet `spiegelstand.py` Abweichungen, die
  kein Betriebsfehler sind.
- **`--vorschau` darf nie ins Buch schreiben** — Vorschau-Laeufe liefern sonst
  Zustands- und Journalaenderungen, die niemand entschieden hat.
- **Ein Umbenennen der Sperre ist kein Beleg fuer einen Committer:** laufende
  `git fsmonitor--daemon`-Prozesse beweisen keine parallele Sitzung.
