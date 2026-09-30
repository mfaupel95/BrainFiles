---
id: 20260921-gates-und-freigabe
title: 'Handel — Gates und Freigabe'
tags: [handel, sicherheit]
created: 2026-09-21
updated: 2026-09-30
related: ['[[Handel/Spuren-Uebersicht]]', '[[Wissen/Handelsregeln]]']
summary: 'Die Sperrenkette vor jeder Live-Order, das Freigabefenster und die Armingschritte — in der Reihenfolge, in der sie geprueft werden.'
---

# Gates und Freigabe

## Die Sperrenkette (jede Spur prueft selbst)

Eine Live-Order entsteht nur, wenn **alle** Punkte offen sind:

1. `handel_erlaubt: true` in der `wachen.json`
2. `freigabe.erfuellt: true` — der von Hand gesetzte Haken (siehe unten)
3. Offenes **Freigabefenster** (`freigabe_fenster.json`, `freigabefenster.py`)
4. `handel_erlaubt` gilt fuer **diesen** Modus: kein Demo-/Papierzwang im Code-Pfad
5. Guthaben in der Kontowaehrung ≥ `mindest_guthaben*`
6. Boersen-Schluessel vorhanden und **orderfaehig** (nicht read-only, richtige Umgebung)
7. Risikogrenzen/Deckel (Ratsche, `max_pro_trade`, Plaetze)

**Der Live-Modus wird nicht aus Chat oder A2A gesetzt.** Kein Befehl schaltet live; nur die
Freigabekette (Bildschirmfenster `freigabe.py` oder `/ja_<spur>` **im Dauerlauf**, auf eine
**wartende Anfrage**) plus `handel_erlaubt=true`.

**Wichtig und oft falsch erinnert:** `freigabe.erfuellt` ist **nur der von Hand gesetzte
Haken** — Wochen, Runden und „netto positiv" rechnet der Code NICHT. Diese Kriterien sind
Eingabe fuer die Entscheidung des Menschen, nicht Maschinenlogik.

## Arming-Sequenz (wenn eine Spur live soll)

1. `herzschlag_max_minuten` auf 180 (Live-Spuren muessen die PC-Ausfall-Luecke ueberleben).
2. `handel_erlaubt: true`.
3. `freigabe.erfuellt: true` (Haken).
4. `/ja_<spur>` **im Dauerlauf** (Fenster max. 24 h, nur auf Anfrage des Dauerlaufs;
   `/ja` ohne wartende Anfrage tut nichts).
5. Vorher: Schluessel-Test mit einem signierten LESEaufruf gegen den **Registry-Host**.

## AUTO_FREIGABE

`dauerlauf.pruefe_anfragen()` oeffnet die Fenster der Spuren aus `AUTO_FREIGABE` sofort selbst
(`freigegeben_von: auto`, 12 h), statt auf `/ja` zu warten. Sie greift **nur**, wenn
`nur_fenster_fehlt()` GENAU EINEN Sperrgrund nennt und darin das Wort **„Freigabefenster"**
vorkommt — also nur, wenn sonst nichts sperrt.

**Merksatz.** Wer eine Spur per AUTO_FREIGABE scharf haben will, muss dafuer sorgen, dass die
`--vorschau`-Zeile „Live waere gesperrt durch:" genau einen Grund nennt. Nennt sie zwei
(z. B. fehlendes Guthaben UND Fenster), greift die Auto-Freigabe nicht — richtig so.

**Die Zeile muss es auch GEBEN.** Bei den Buch-Spuren (`spur_buch.py`) fehlte sie bis zum
30.09.2026 vollstaendig: `zyklus()` druckte bei `--vorschau` nur „Vorschau: keine Dateien
geschrieben." Damit fand `nur_fenster_fehlt()` nie eine Sperrzeile, gab `None` zurueck — und
AUTO_FREIGABE konnte fuer **keine** Buch-Spur greifen, auch mit vollem Guthaben nicht. Behoben:
die Vorschau ruft jetzt dieselbe `sperren_live()`-Kette wie der Live-Lauf und nennt sie
(Commit 32eb2fd). Betroffen waren alle Buch-Spuren (`moondev_listingarb`,
`moondev_topmovers`, `trendwende_btc`, `liq_wand`, `iv_wand`, `moondev_funding`).
Merksatz: eine Sperre, die niemand ausspricht, ist keine.

**Beleg.** 21.09.2026: `xperp` 00:02 live, `scanner` 01:52 live, `mosaic` 06:58:40
Auto-Freigabe, Zyklus 07:11:27 „ok". `kraken` und frueher `mosaic` waren nicht durch das
Fenster gesperrt, sondern durch das **Guthaben in der richtigen Waehrung** („nur 33.15 EUR
frei, noetig 60.00", „nur 0.00 USDT frei, noetig 30.00").

## Punkt 3 hat ZWEI Formen — und eine kann still fehlen

Punkt 3 der Handelsregeln ("scharf geschaltet wird von Hand") ist zweimal umgesetzt,
und die Spur muss BEIDE kennen:

| Form | Modul | Wo sie greift |
|---|---|---|
| Freigabefenster am Bildschirm | `freigabe.py` (Tk) | jemand sitzt davor, bestaetigt je Einstieg |
| **Zeitfenster** | `freigabefenster.py` (`freigabe_fenster.json`) | Dauerbetrieb: `AUTO_FREIGABE` oder `/ja` am Handy |

**Unter `MAXHIRN_ROUTINE=1` ist `sitzung_da()` immer `False`** — und der Dauerlauf setzt
die Variable seit dem 21.09.2026 in BEIDEN Modi. Eine Spur, deren Sperrtext nur
`sitzung_da()` prueft, kann damit **im Dauerlauf nie live gehen**, egal wie oft ein Fenster
offen ist. Der Dauerlauf protokolliert trotzdem `<spur> (live) ok` — das ist SEIN Modus,
kein Beleg fuer eine Order.

**Beleg 21.09.2026 (mosaic):** Sperrtext `keine Sitzung am Bildschirm - Freigabefenster
nicht moeglich` → `nur_fenster_fehlt` sah "genau ein Grund, Wort Freigabefenster" →
oeffnete im 30-Minuten-Takt Fenster, die nichts bewirkten; das Journal hatte keine einzige
Live-Zeile. Zusaetzlich stand in `hole_freigabe()` `str(HIER.parent)`, obwohl `HIER` in
mosaic/handeln.py ein **String** ist (`os.path.dirname`) — `AttributeError` schon VOR dem
`try`, also "Freigabefenster nicht verfuegbar" und kein Einstieg, auch am Bildschirm.

**Messprobe (die einzige Wahrheit):** `<spurinterpreter> handeln.py --vorschau` **mit**
`MAXHIRN_ROUTINE=1` — genau so ruft der Dauerlauf sie. Steht dort "nicht offen - keine
Sitzung am Bildschirm und kein Zeitfenster", fehlt die zweite Form. Ohne die Variable
sieht dieselbe Spur frei aus.

### Die Beschwerde kann selbst falsch sein — die Spur muss das Fenster LESEN koennen

**Beleg 22.09.2026 (scanner, live):** In jedem Zyklus stand
`scanner: --live angefordert, aber gesperrt: Freigabefenster nicht offen ...` — obwohl der
Dauerlauf `--live` nur vergibt, wenn `freigabefenster.lade(spur).offen()` wahr ist, und das
Fenster bis `02:02:42` offen war.

Ursache: `scanner/handeln.py` legte am Modulkopf **nur** `<spur>/../../Bus` auf `sys.path`,
nie den `Handel/`-Ordner. `zeitfenster_offen()` las das Fenster per blankem
`import freigabefenster` → `ModuleNotFoundError` → der `except`-Zweig gab **still `False`**
zurueck. Seit `MAXHIRN_ROUTINE=1` in beiden Modi ist `sitzung_da()` zusaetzlich dauerhaft
`False` — Regel 3 war damit fuer den scanner **dauerhaft zu**, und er handelte Papier,
waehrend der Dauerlauf `(live)` protokollierte. Erster echter Live-Kauf nach dem
21.09. 21:53: **22.09. 00:14 UTC** (`Buch gegen Boerse`: `ETH-USDC` 0,037301 @ 2773.36,
`SOL-USDC` 0,80283 @ 118.63).

**Regel fuer jede Spur.** Module aus `Handel/` — `freigabefenster`, `freigabe`, `ratschen`,
`risikostufe`, `spur_buch` — nur **ueber den Pfad** laden (`spec_from_file_location`) oder
`HANDEL` selbst in `sys.path` legen. Ein blankes `import` haengt an der Reihenfolge der
`sys.path`-Eintraege, die im Spurlauf anders ist als von Hand.

**Gegenprobe, die den Fehler zeigt** (aus dem Spurenordner, ohne den Elternordner):

```bash
cd Agenten/Handel/scanner && .venv/Scripts/python.exe -c \
  "import handeln; print(handeln.zeitfenster_offen())"
```

Vorher: `ModuleNotFoundError` in `zeitfenster_offen()` → `False`. Nachher: derselbe Wert,
den `freigabefenster.lade("scanner").offen()` liefert.

## Wiedervorlage-Fristen

`freigabefenster.neue_anfrage_erlaubt()` verhindert, dass dieselbe Frage alle 30 Minuten
gestellt wird. Ohne diese Frist stand am 12.09.2026 um 19:06 eine Ablehnung und um 19:20
schon die naechste Frage. Eine unbeantwortete Anfrage **verfaellt**; ein `/ja` von gestern
Nacht ist keine Freigabe fuer heute frueh (`melder.leeren()` beim Start).

## Notaus

`/stop` schliesst alle Fenster; beendet sich der Dauerlauf (Strg+C), schliesst der
**Basislauf** alle Fenster (nie eine Stufe — sie wuerde dem Basislauf mitten im Handel die
Freigabe nehmen). Positionsschliessungen laufen ueber Stop-/Risikologik, **nicht** ueber den
Herzschlag (siehe [[Handel/Lektionen]]).

## Herzschlag

`herzschlag_max_minuten: 180` fuer alle Spuren (19.09.2026 von 45 angehoben). Grund: die
ungeklaerten Abschaltungen des Rechners (T-004) liessen die Luecke ueber 45 min wachsen, und
ein Fehlschluss der Live-Position waere Verlust in echtem Geld. Der Waechter startet einen
toten Lauf nach spaetestens 30 min neu, ein Zyklus dauert 1-2 min — eine Stoerung heilt nach
rund 32 min von selbst. **Jede Grenze darunter stellt bei JEDER Stoerung flach** (am
11./12.09.2026 mit 30 min in xperp/swap passiert). Wer eine Spur live nimmt, setzt 180
BEVOR `handel_erlaubt` auf `true` geht. Der Wert ist die Zahl in der `wachen.json`
(`_herzschlag_regel` ist nur Doku) und wirkt ohne Neustart.

**Selbstsperre durch die falsche Quelle (23.09.2026, moondev_marktlage):** Der Herzschlag ist
das Alter des letzten **Zyklus** — er muss aus dem Zustand kommen, den der **laufende** Zweig
schreibt. `_papier_zustand()` las nur `zustand.json`; seit die Spur live lief, schrieb der
Papierzweig nichts mehr (Stand 22.09. 21:12), waehrend live alle 15 Minuten lief. Nach 180 min
meldete die Spur **„Live waere gesperrt durch: Herzschlag alt"** — sie sperrte sich selbst, und
weil `nur_fenster_fehlt` GENAU EINEN Grund verlangt, oeffnete AUTO_FREIGABE weiter Fenster fuer
einen Lauf, der nicht handeln konnte. Richtig ist der **frischste** der beiden Staende (Papier
und Live): nur Papier sperrt eine Spur, die nie live lief; nur Live ist ein Kreislauf.
Merksatz: **Wenn ein Tor aus einem Zustand liest, muss es der Zustand des Zweigs sein, der
schreibt.** Und `--vorschau` mit `MAXHIRN_ROUTINE=1` ist der einzige Beleg fuer den Modus.

## Guthaben-Tor und Einsatz-Deckelung (23.09.2026)

- `mindest_guthaben_eur` ist die Untergrenze des freien Guthabens, damit der **kleinste** Einsatz
  hineinpasst (marktlage: 70 bei Mindest-Einsatz 60; vorher 100 aus einer veralteten Rechnung
  „3x 30 EUR", was bei 88,56 EUR frei den Live-Zweig dauerhaft sperrte — Auftrag Max
  „Marktlage 70").
- Der Einsatz wird **zusaetzlich auf das freie Guthaben gedeckelt**
  (`live_kraken.einsatz_gedeckelt`, `frei*(1-gebuehr_taker-0,2 %)`) und faellt er unter
  `live_einsatz_min_eur`, wird nicht gehandelt. Ein Signal von 150 EUR bei 88 EUR frei waere
  sonst eine abgelehnte Order — kein Handel, aber im Log nicht von einem Signalfehler zu
  unterscheiden.
- Reihenfolge merken: **erst deckeln, dann das Freigabefenster zeigen** — das Fenster muss den
  Betrag zeigen, der wirklich ausgefuehrt wird.

## Freigabekette einrichten — Checkliste (nautilus_kraken, 24.09.2026)

Ein Schalter ist keine Freigabe. Wer eine Spur scharf stellt, geht diese
fuenf Punkte durch — jeder hat schon einmal gefehlt:

1. **Herzschlag 180, auch live.** Die 45-Minuten-Grenze fuer Live-Spuren ist
   seit 19.09.2026 aufgehoben (T-004): ein Rechner-Ausfall stellt sonst echte
   Positionen ohne Handelsentscheidung flach und bucht eine Runde, die keine
   war. `systempruefung.ps1` Block 11b prueft 180 fuer alle Spuren.
2. **Guthaben-Tor in der Sperrenkette**, in der Waehrung des Kontos
   (`live_einsatz_eur` gegen `kraken_rest.guthaben()`). Ohne das Tor
   scheitert die Order an `EOrder:Insufficient funds` und die Spur saehe
   trotzdem `ok` aus. Ohne Einsatz-Zahl: keine Abfrage, kein Tor.
3. **Eigener Live-Einsatz** (`live_einsatz_eur`, `live_max_risiko_gesamt_eur`):
   der Papier-Einsatz von 50 EUR darf nicht ungefragt live gehen. `--wachen`
   muss beide Zahlen zeigen.
4. **Schutz-Stop gehoert zum Kauf.** Nach `markt_kauf(...)` sofort
   `stop_setzen(...)` — ohne ihn laeuft die Position bis zum naechsten Zyklus
   ungeschuetzt, und der kann bei einem Ausfall Stunden spaeter kommen.
5. **Papierbestand im gemeinsamen Buch schuetzen.** Positionen ohne
   `modus=live` sind Papier; der Live-Lauf ordert sie NIE (sonst verkauft der
   erste echte Zyklus BTC, das es an der Boerse nicht gibt). Neue Positionen
   tragen ihren Stempel, der Rest gilt als Papier.

Probe zum Schluss: `handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1`. Nennt sie
genau EINEN Grund mit dem Wort „Freigabefenster", stellt der Dauerlauf die
Anfrage und die Auto-Freigabe greift nicht (sie verlangt genau einen
Fenster-Grund). Nennt sie einen zweiten Grund, fragt niemand — und die Spur
bleibt still stehen.