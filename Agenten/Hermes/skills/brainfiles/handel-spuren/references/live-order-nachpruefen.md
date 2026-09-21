# Live-Order am Handelsplatz nachpruefen (und was ein falscher Einstiegspreis kostet)

Ausloeser: "in meinem OKX sehe ich keine Order" / "funktioniert das ueberhaupt?" /
Zweifel an einem echten Kauf einer Live-Spur.

## 1. Nicht am Konto zweifeln, sondern am Handelsplatz nachfragen

Eine Journal-Zeile `live,kauf` ist eine Buchung, kein Beleg. Die Order-IDs liegen
in `<spur>/zustand.json` je Position (`kauf_ord_id`, `stop_ord_id`); damit sind
alle Antworten lesend und signiert zu holen:

- `GET /api/v5/trade/order?instId=<inst>&ordId=<id>` → `state: filled`,
  `accFillSz`, **`avgPx`** (echter Fuellungspreis), `fee`, `cTime`
- `GET /api/v5/trade/orders-history?instType=SPOT` → Orders des Kontos
- `GET /api/v5/trade/orders-algo-pending?instType=SPOT&ordType=conditional` →
  der Notausstieg muss `state: live` sein, sonst liegt die Position unbewacht
- `GET /api/v5/account/config` → `uid` gegen `mainUid`: sind sie verschieden,
  liegt die Order in einem UNTERKONTO und ist in der Hauptoberflaeche unsichtbar

The werkzeug `scripts/okx_live_order_probe.py` faehrt alle vier Aufrufe ueber das
okx-Modul der Spur und vergleicht `avgPx` mit dem Bucheinstieg.

## 2. Eine unsichtbare Order ist kein Fehlerbeweis

Gruende, aus denen ein echter Kauf in der App nicht auffaellt:

- Paar in der Quote-Waehrung, die man gerade nicht im Filter hat (USDC statt USDT)
- Betraege um 60 USD sind in der Order-Historie eine Zeile unter vielen
- gebundene Coins erscheinen als `frozen` (der Notausstieg reserviert sie)
- Unterkonto (siehe `uid` vs. `mainUid`)

Umgekehrt gilt: eine SICHTBARE Order beweist nicht, dass Stop, Ziel und Risiko
stimmen - dafuer muss man `avgPx` gegen den Einstieg im Buch rechnen.

## 3. Die eigentliche Falle: gehandelt wird auf einer Datei, die niemand mehr schreibt

`scanner/handeln.py` SCANNT NICHT SELBST - es liest `scanner/berichte/neuester.json`
(Zeile ~815) und rechnet Vorschlaege, Stops und Ziele auf den Kursen aus dieser
Datei. Erzeuger ist ein eigener Wrapper (`Routinen/marktscanner.ps1`), der sich
abmeldet, sobald der Dauerlauf die Spur fuehrt:

    ENDE uebersprungen: der Dauerlauf fuehrt die Spur (PID ...) - ein zweiter
    Schreiber auf denselben Zustand ist nicht noetig.

Der Dauerlauf fuehrt aber nur `handeln.py`, nicht den Scan. Ergebnis: der
Kursbericht friert ein, der Verbraucher handelt weiter - Einstieg im Buch 1360,
tatsaechliche Fuellung 1512 (`avgPx`), Stop real -18 % statt der berechneten
-8,9 %, also das Doppelte des geplanten Verlusts in echtem Geld.

**Regel:** Vor dem Scharfschalten einer Spur und danach bei jeder Zweifelsfrage
die Frische JEDER konsumierten Datei beweisen (`ls -l` gegen `date`, dazu der
Computed-Wert im Bericht gegen den letzten Kurs) und die Frage beantworten: wer
SCHREIBT das, was diese Spur LESEN wird? Ein Wrapper, der sich wegen des
Dauerlaufs abmeldet, nimmt dem Verbraucher seine Datenquelle weg - Erzeuger und
Verbraucher muessen sichtbar getrennte Aufgaben bleiben.

Nebenbefund derselben Pruefung: dieselbe Veraltung trifft auch die Papierbuecher
(alle Einstiege eines Zyklus stammen aus dem alten Bericht), also vor jeder
Auswertung die Herkunft der Einstiegspreise pruefen.

## 4. Buchen erst nach der FUELLUNG, nicht nach der Annahme

`order_limit()` liefert die `ordId`, sobald die Boerse die Order **angenommen**
hat - `state: live` heisst nicht "gefuellt". Wer sofort bucht, fuehrt Positionen,
die es nicht gibt: das Buch zaehlt einen Platz als belegt, jeder Ausstieg verkauft
ins Leere, die Bilanz zeigt eine Position ohne Deckung.

- Vor dem Bucheintrag `GET /api/v5/trade/order?instId=<i>&ordId=<id>` lesen und
  `accFillSz` pruefen: **0 → Order stornieren, keine Position buchen** (Journal-
  Zeile mit eigenem Grund), **Teilfuellung → Rest stornieren und nur das
  Gehandelte buchen**.
- **Unbekannt zaehlt wie nicht gefuellt.** Scheitert die Abfrage, lieber die Order
  stornieren als eine Position erfinden - der naechste Zyklus kann neu einsteigen.
- Kurz warten (wenige Sekunden, wenige Versuche) statt sofort zu urteilen: ein
  Limit am Markt fuellt oft in Sekunden.

## 5. Buch gegen die Boerse abgleichen - ein Geist belegt einen Platz

`/api/v5/account/positions` ist die Wahrheit. Ein Bucheintrag mit `modus: live`,
der dort **fehlt** oder mit **`pos: 0`** steht (OKX behaelt geschlossene Positionen
als Zeile), ist ein Geist: ausbuchen und die offene Order dazu stornieren.

**Reihenfolge der Fragen - die Order zuerst, sonst bucht man eine echte Position aus:**

1. Position an der Boerse vorhanden (`pos != 0`)? → behalten.
2. Sonst: Order gefuellt (`accFillSz > 0`)? → **behalten** - eine offene Order
   kann SEKUNDEN nach der Pruefung fuellen; zu diesem Zeitpunkt sieht die
   Position wie ein Geist aus, ist aber echt (sie lief danach ohne Buch weiter:
   kein Ausstieg, kein Funding, keine Bilanz).
3. Sonst: Geist → offene Order stornieren, dann ausbuchen.

Faellt die Abfrage aus, wird **nichts** gebucht: ein Netzfehler darf das Buch
nicht leeren. Nach jeder Live-Aenderung `zustand.json` gegen `/account/positions`
legen und **beide** Richtungen nennen - Buch ohne Boerse (Geist) und Boerse ohne
Buch (unbewacht).

## 6. Eine Position ohne boersenseitigen Stop ist nicht fertig gebucht

Stop und Ziel als `attachAlgoOrds` **der Order** greifen nur, wenn sie zum
Fuellungszeitpunkt gueltig sind. Wird eine Limit-Order erst spaeter gefuellt oder
vorher storniert, liegt die Position ohne Stop - `/api/v5/trade/orders-algo-pending?instType=FUTURES&ordType=conditional`
ist dann **leer**, obwohl die Position offen ist.

- Nach jedem Einstieg UND nach jedem Wiederherstellen einer Position pruefen, ob
  ein Algo-Stop offen ist; fehlt er, per `POST /api/v5/trade/order-algo`
  nachreichen: Gegenseite der Position, `ordType: conditional`,
  `reduceOnly: true`, `slOrdPx: -1` (Market-Ausloesung - ein Stop, der selbst ein
  Limit ist, fuellt im Absturz nicht).

## 7. Eine Position ins Buch zurueckholen, nie ins Blaue buchen

Findet man eine echte Position ohne Bucheintrag, wird sie **wiederhergestellt**,
nicht verkauft: Werte aus der ErOEFFNUNGSzeile des Journals (Einstieg, Kontrakte,
Stop, Ziel, Liquidation, Hebel), nichts schaetzen; dazu eine Journal-Zeile mit
eigenem Grund (`buchwiederherstellung`), eine `.bak-JJJJJMMTT`-Sicherung der
`zustand.json` und im Bericht ausdruecklich, was der Kill-Switch derselben Spur
gleichzeitig getan hat. Ein Kill-Switch, der flachstellt, und ein Geist-Fund
gehoeren zusammen genannt - sonst klingt ein Buchbereinigungsfehler nach einer
Handelsentscheidung.
