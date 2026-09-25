# OKX-Fehler richtig lesen (und nicht dreimal senden)

Befund vom 20.09.2026, Spur `scanner`: Journal zeigte
`Verkauf AVAX-USDT fehlgeschlagen: HTTP Error 400: Bad Request`.
Daraus ist nicht ablesbar, was zu tun ist. Dahinter steckten ZWEI Fehler.

## 1. Orderfehler kommen mit HTTP 200

OKX lehnt eine Order fachlich ab, antwortet aber mit **HTTP 200** und
`code: "1"`. Die eigentliche Auskunft steht in `data[0].sMsg`/`sCode`:

```json
{"code":"1","msg":"All operations failed",
 "data":[{"sCode":"51020","sMsg":"Your order amount does not meet the minimum order amount."}]}
```

Wer nur das aeussere `msg` ausliest, schreibt "All operations failed" ins
Journal. Immer `data[0].sMsg` bevorzugen, `msg` nur als Rueckfall.

## 2. HTTP 4xx darf nicht als Transportfehler gelten

`_roh()` las die OKX-Auskunft nur bei 401/403 aus. Ein **400** fiel als
roher `HTTPError` durch und wurde von `_mit_wiederholung` fuer einen
Transportfehler gehalten - also **dreimal erneut gesendet**. Bei einer
Verkaufsorder ist jeder Versuch eine echte Order.

Regel: ALLE 4xx als fachlichen `OKXFehler` werfen (keine Wiederholung),
nur echte Transportfehler wiederholen.

## Gegenprobe (am echten Endpunkt, ohne Geld zu bewegen)

Eine Order mit zu kleiner Menge senden - OKX lehnt sie ab, es entsteht
keine Position:

```python
okx.markt_verkauf('AVAX-USDT', 0.001)
# vorher: HTTP Error 400: Bad Request
# jetzt:  OKX 51020: Your order amount does not meet the minimum order amount.
```

## 3. `50119`/`50101` heisst meist FALSCHER HOST, nicht toter Schluessel

Symptom: **jede** Order scheitert mit `OKX 50119: API key doesn't exist (HTTP
401)`, waehrend Leseaufrufe weiter funktionieren.

Mechanismus: ein Zugang besteht aus Schluessel **und** Host (`OKX_BASE`, EEA
`https://eea.okx.com` gegen global `www.okx.com`). Wird der Schluessel mit
Registry-Rueckfall gelesen (`_variable`), der Host aber nur aus der
Prozessumgebung (`_env`), dann findet ein Kindprozess ohne geerbte
Benutzervariablen den Schluessel - und signiert gegen den Vorgabe-Host. Der
Fehler sieht wie ein toter Schluessel aus, ist aber ein falscher Endpunkt.

**Regel: Schluessel und Host gehoeren zu EINEM Zugang - wer einen Teil mit
Rueckfall liest, liest jeden Teil so.** Und: ein `50119`/`50101`, das auf
JEDER Order steht, ist kein abgelaufener Schluessel.

Pruefen, **bevor** ein Schluessel getauscht wird:

```bash
env -u OKX_BASE python -c "import okx; print(okx._live_basis())"
# muss den EEA-Host nennen, sonst faellt der Kindprozess auf den globalen zurueck
```

Reihenfolge der Diagnose: erst Host, dann Kontoberechtigung, dann Schluessel.
Kontoberechtigung lesend: `/api/v5/account/config` signiert, Feld `perm`
(`read_only,trade`) und Feld `ip` (leer = keine IP-Sperre). **`okx._roh()` gibt
die DATA-LISTE zurueck, nicht das Antwort-Dict** - ein Probeaufruf mit `.get()`
faellt mit `AttributeError` um, obwohl der Abruf geklappt hat.

## 5. `51001` = unbekanntes Instrument — erst die Spur suchen, dann deuten

`51001` ("Instrument ID does not exist") heisst: die Anfrage trug eine
`instId`, die die Boerse nicht kennt. Typische Ursachen: ein **abgelaufener
Kontrakt** (Papier- und Live-Buecher behalten das Instrument, die Boerse kennt
es nicht mehr), ein fehlender Suffix (`-USDT`, `-SWAP`) oder ein Symbol der
falschen Boerse (Kraken `XBT/USD` an einem OKX-Endpunkt).

**Bevor der Code gedeutet oder die gemeldete Spur repariert wird, ihn in DER
Spur suchen, die ihn angeblich schreibt:**

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel
grep -rn '51001' xperp/ nautilus_kraken/ | head -20
```

Ein leerer Treffer ist der Befund: diese Spur erzeugt den Code nicht. Gemessen
trat `51001` ausschliesslich in `xperp` auf (abgelaufener Kontrakt
`CL-USD_UM_XPERP-310509` ueber `okxf.letzter_kurs_mit_fallback`), waehrend die
nautilus-Arme die Zahl nirgends enthielten - ihnen wurde sie trotzdem
zugeschrieben. Und die Trefferzahl sagt nichts: derselbe Zahlenwert steht
harmlos in Modell-Metadaten und Kennungen, also die **Fundstelle** lesen, nie
bloss zaehlen. Ein `grep -r` ueber ganz `Agenten/` laeuft in den Timeout -
imner je Spur/Ordner suchen.

## Falle beim Nachstellen

OKX antwortet ohne `User-Agent` mit **HTTP 403 (Cloudflare 1010)**. Wer
ein Wegwerfskript baut und `okx.HEADERS` vergisst, misst seinen eigenen
Fehler und haelt ihn fuer einen Schluesselfehler.

## 4. Storno einer Algo-Order: `50014` = instId fehlt, `51400` = erledigt

Befund 23.09.2026, Spur `scanner`: jede Runde
`offener Stop 3940642343922589696 bleibt liegen: OKX 50014: Parameter instId
can not be empty`, und `zustand.json` trug **23 Kopien** desselben Stops.

Zwei Fehler auf einmal:

* `cancel-algos` braucht **`instId`**. Ohne sie: `50014`, der Stop laesst sich
  **nie** abbestellen. Gemessen am EEA-Host mit einer Attrappen-Kennung:
  `{"algoId": FAKE}` -> `50014`; `{"algoId": FAKE, "instId": "ZEC-USDC"}` ->
  `51400 Order cancellation failed as the order has been filled, canceled or
  does not exist`.
* **`51400` heisst erledigt, nicht Fehler.** Wer es als Fehler behandelt,
  laesst den Merker fuer immer liegen und meldet jede Runde dasselbe. Ein
  Stop, den es nicht mehr gibt, ist kein offener Stop.

Regel: `stop_stornieren(algo_id, inst)` - Instrument IMMER mitgeben;
`51400` still als erledigt werten; fehlt einem Alteintrag das Instrument,
lesend nachholen (`stop_inst`, `state`/`instId` aus `order-algo`).

Der zweite Fehler war der Merker selbst: `z["offene_stops"].append(...)` ohne
Dedupe. Wuchs bei jedem weiteren Ausstiegsversuch, denn solange der Verkauf
zusatzlich scheiterte (falscher Host, `50119`), blieb die Position im Buch und
der naechste Zyklus merkte denselben Stop erneut.

**Merksatz: ein Merker, der nur beim Erfolg faellt, braucht einen Dedupe - und
eine Antwort, die "gibt es nicht mehr" bedeutet, ist kein Fehler.**

Nachweis/Bestandsaufraeumer: `Agenten/Handel/scanner/stops_bereinigen.py`
(Vorschau Standard, `--anwenden`, `--stornieren` fuer Waisenstops);
Tester `scanner/tests/test_okx_stornieren.py`; Gegenprobe
`zustand.json` (23 -> 0, Buch gegen Boerse 5/5 ueber
`/api/v5/trade/orders-algo-pending?ordType=conditional`).

## 6. `50103` aus einer UNGESIGNETEN Abfrage — sieht wie ein fehlender Schluessel aus

`OKX 50103: OK-ACCESS-KEY can not be empty` heisst: die Anfrage ging OHNE Signatur
raus. Beim Sondieren vergisst man das leicht, denn `_roh(pfad)` signiert NICHT —
der Schalter muss ausdruecklich mit: `_roh('/api/v5/account/positions',
signiert=True)`. Ohne ihn liest man einen Schluesselfehler, wo keiner ist, und
"repariert" die Schluessel einer Spur, die gesund ist.

**Regel: bevor ein Schluessel verdaechtigt wird, pruefen, ob die Sonde ueberhaupt
signiert hat.** Lesende Kontodaten (`account/positions`, `account/balance`,
`trade/orders-algo-pending`) brauchen `signiert=True`, oeffentliche Marktdaten
(`market/*`, `public/*`) nicht. GET-Parameter gehoeren in den PFAD (so wie oben),
`body=` ist fuer POST.

Alle conditional Stops eines Kontos liegen in EINEM Aufruf
(`orders-algo-pending?ordType=conditional`): je Zeile `algoId`, `instId`, `sz`,
`slTriggerPx`, `tdMode`, `side`, `reduceOnly`. Das ist die Quelle fuer die Frage
"welche Schutz-Orders liegen am Markt, und deckt jede eine Position?" — und
`reduceOnly: true` ist der Grund, warum eine Order groesser als ihre Position
dort harmlos ist (siehe SKILL.md, "Waisen").
