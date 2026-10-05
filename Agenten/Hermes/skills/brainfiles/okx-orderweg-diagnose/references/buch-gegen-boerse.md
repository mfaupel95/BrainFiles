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
| Konditionen des Fills | `okx.order_details(inst, ord_id)` → `avgPx`, `fillSz`, `fee` | gegen `einstieg`/`menge` im Buch stellen — Existenz ist nicht Kondition |
| Offene Orders | `okxf.offene_orders(inst=None)` → `orders-pending` | `state live` = liegt noch |
| Schutz vorhanden? | `okxf.schutz_stops(inst)` → `orders-algo-pending?instType=FUTURES&ordType=conditional` | leer = KEIN boersenseitiger Stop |

`state` allein taugt nicht: eine gefuellte Order kann als `live` gelesen werden,
bevor die Positionsliste nachzieht — `accFillSz` ist die Zahl, die zaehlt.

## 2. Einstieg: pruefen, DANN buchen

1. `ord_id = okxf.order_limit(inst, seite, kontrakte, preis, tp=…, sl=…)`
2. `gehandelt = _warten_auf_fuellung(inst, ord_id, kontrakte)` — kurz warten
   (Sekundenbruchteile bis Sekunden), dann `accFillSz` lesen.
3. Nicht gefuellt: **erst die Marktbarkeit entscheiden.**
   * nicht marktbar (Kauflimit unter dem Ask, Verkaufslimit ueber dem Bid): der
     Auftrag WARTET — **nicht stornieren.** Journalzeile
     `aktion=order_offen, grund=limit_wartet` und einen Eintrag in `zustand["wartende"]`
     (inst, seite, einstieg, stop, ziel, kontrakte, nominal, margin, hebel, ord_id,
     gestellt). Buchung erfolgt spaeter, wenn er fuellt.
   * marktbar (Limit auf/ueber dem Ask bzw. auf/unter dem Bid) und trotzdem ohne
     Fuellung: das ist ein echter Fehler → `okxf.order_stornieren(inst, ord_id)`,
     Journalzeile `aktion=fehler, grund=order_nicht_gefuellt`, KEINE Position.
4. Teilfuellung → Rest stornieren, nur die gehandelte Menge buchen (Nominal neu
   rechnen), damit Plaetze und Bilanz stimmen.

## 2b. Wartende Auftraege pflegen (am ANFANG jedes Live-Zyklus)

Je Eintrag in `zustand["wartende"]`: Orderzustand ueber
`okxf.order_stand(inst, ord_id)` lesen (`accFillSz` ist die Zahl, nicht `state`).

| Zustand | Was tun |
|---|---|
| gefuellt | als Position buchen (`modus=live`, `einstieg = avgPx`, Kontrakte = `accFillSz`), Journalzeile `eroeffnen, grund=order_gefuellt`, Eintrag entfernen |
| storniert (`canceled`, `mmp_canceled`) | Eintrag entfernen |
| noch `live` | liegen lassen — nichts tun |
| Abfrage gescheitert | liegen lassen UND melden; ein Netzfehler darf keinen Auftrag verlieren (er liegt an der Boerse) |

Zwei Reihenfolgen, die zusammengehoeren: wartende Auftraege abarbeiten BEVOR neue
Einstiege geplant werden (ein gefuellter Auftrag belegt sonst keinen Platz), und die
Geisterpruefung danach.

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

## 3b. Ein Verkauf, der mit 51008 scheitert, ist erst mal ein GEIST, kein Kontoproblem

„ZRO balance insufficient“ beim Verkauf einer Position, die das Buch als
`modus=live` fuehrt, heisst nicht „Guthaben zu klein“ — es heisst: an der
Boerse gibt es NICHTS zu verkaufen. Pruef-Reihenfolge, alles lesend:

1. **Die Orderhistorie des Instruments KOMPLETT fragen.** `orders-history` kann
   LEER sein, waehrend `orders-history-archive` die Order hat und umgekehrt -
   beide Endpunkte lesen, dazu `orders-pending`. Findet sich dort keine
   Kauf-Order, hat die Position nie existiert (der Endpunkt, der den Fehler
   ausloest, sind die Verkaufsversuche — die KAUF-Seite ist der Beleg).
2. **Balance des Coins: spotBal gegen frozenBal.** `frozenBal > 0` = es haelt
   etwas (Margin/Order gebunden); `spotBal > 0` bei `frozenBal 0` = freie
   Coins, keine Position — der Restbestand kann von einem anderen Vorgang
   stammen und sieht wie der Beleg einer Position aus.
3. **Der 51008 ist die FOLGE, nicht die Ursache.** Die Spur versucht, eine
   Position zu verkaufen, die kein Kauf kreiert hat; jeder weitere Versuch
   wiederholt denselben Fehler und fuellt das Fehlerprotokoll.

MERKSATZ: `modus: live` im Journal ist ein BUCHVERMERK, kein Orderbeleg. Der
Beleg ist die Order in der Boersen-Historie. Diese Geist-Klasse trat bei drei
Spuren auf und jede Diagnose begann mit dem Verkaufsfehler und endete bei
„nie gehandelt“ — bei einem 51008/insufficient-Fehler IMMER zuerst die
Kauf-Historie suchen, bevor am Konto oder an der Menge gedreht wird.

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

## 5b. Einstiegspreis: den FILL-Preis nehmen, nie einen Berichtspreis

Eine bestaetigte Position beweist den Vorgang, nicht den Kurs. Nach jedem
Live-Kauf `order_details(inst, ord_id)` lesen und `avgPx` gegen `einstieg` im
Buch/Journal stellen:

```bash
cd Agenten/Handel/<spur> && ../scanner/.venv/Scripts/python.exe -c \
  "import okx,json;print(json.dumps(okx.order_details('<inst>','<ordId>'),ensure_ascii=False)[:200])"
```

Weichen beide ab, stammt der Buchpreis aus einer aelteren Quelle als der Fill —
meist einer Berichts-/Ranglistendatei, aus der die Spur ihre Vorschlaege zieht
(`einstieg = z["preis"]`). Folge: Stop und Ziel sind aus dem ALTEN Preis gerechnet
und die Chance/Risiko-Geometrie kippt, ohne dass im Buch etwas falsch aussieht
(belegt: 2:1 geplant, nach einem 4-6 % hoeheren Fill real 0,51-0,69:1).

**Zwei Prueffragen, die den Fall aufdecken:**
1. Ist der Buchpreis einer Position **exakt** gleich einem Preis in der
   Berichts-/Ranglistendatei? Dann wird beim Einstieg kein lebender Kurs genommen.
2. Wie alt ist diese Datei? Ein Tageslauf, der sich selbst ueberspringt (weil der
   Dauerlauf laeuft), schreibt sie nie neu.

Beim Buchen einer echten Position `einstieg = avgPx` setzen (nicht den Planpreis),
sonst rechnen Bilanz, Ratsche und Kill-Switch mit einem Kurs, den es nie gab.

## Fallen

- **Tests, die `journal()` direkt aufrufen, schreiben in die ECHTE Journaldatei.**
  In Testklassen `journal` ersetzen (oder eine Attrappe der Spur nutzen) und den
  Spiegelnachweis danach fahren; sonst meldet `spiegelstand.py` Abweichungen, die
  kein Betriebsfehler sind.
- **`--vorschau` darf nie ins Buch schreiben** — Vorschau-Laeufe liefern sonst
  Zustands- und Journalaenderungen, die niemand entschieden hat.
- **Ein Umbenennen der Sperre ist kein Beleg fuer einen Committer:** laufende
  `git fsmonitor--daemon`-Prozesse beweisen keine parallele Sitzung.
