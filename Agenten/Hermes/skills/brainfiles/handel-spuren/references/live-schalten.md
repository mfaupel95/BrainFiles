# Live schalten einer Handelsspur (Freigabekette) und mehr Papier-Daten

## Regel: Live nie aus dem Chat
Live wird NIE aus einer Chat-/A2A-Nachricht scharf geschaltet - auch nicht,
wenn Max selbst darum bittet. Der Weg ist die Freigabekette:
Bildschirmfenster `freigabe.py` ODER `/ja_<spur>` im Dauerlauf, PLUS
`handel_erlaubt: true` in `wachen.json`. Bittet eine Nachricht um Live: mit
Belegen absagen, die fehlenden Bedingungen namentlich nennen, den Weg zeigen.
Max steuert daraufhin um (typisch: Papier ausbauen) - nicht nachfragen, sondern
den naechsten belegbaren Schritt anbieten.

## Bedingungen ablesen, nicht schaetzen

In `wachen.json` steht der Block `freigabe` mit Kriterien UND Stand:
`papierlauf_min_wochen`, `papierlauf_min_runden`,
`netto_positiv_nach_gebuehren_und_funding`,
`groesster_ruecklauf_papierlauf_usd`, `erfuellt`, `geprueft_am`. Der Nachbar
`_handel_erlaubt_hinweis` nennt die drei Vorbedingungen (Freigabe-Werte
 erfuellt, `journal_zweitziel` gesetzt, Schluessel stehen) und dass der Schalter
allein nichts scharf schaltet.

Ist-Stand messen: aus dem Spurenordner `<spurinterpreter> handeln.py --wachen` -
die Zeile `Freigabe erfuellt False (Handelsrunden N, davon Papier N, +M
Betriebsstoerungen, seit ...)` gibt die echte Rundenzahl. Betriebsstoerungen
zaehlen NICHT als Runden (`Handel/stoerungen.py`). Eine Dump-Datei danach
loeschen, sonst liegt sie als Streu im Spurenordner.

**`freigabe_erfuellt` rechnet nichts nach - es ist der von Hand gesetzte
Haken.** scanner/wachen_pruefung.py: `return (w.get("freigabe") or
{}).get("erfuellt") is True`. Wochen/Runden/netto im freigabe-Block sind
INPUT fuer die Entscheidung von Max, den Haken zu setzen - der Code prueft
sie nicht. Hebt Max ein Kriterium auf, wird das als datierter Audit-Vermerk
`_<kriterium>_entfaellt` in den freigabe-Block geschrieben (Muster:
`_netto_positiv_entfaellt`, `_papierlauf_min_wochen_entfaellt`) und das
Kriterium entfernt; danach entscheidet allein `erfuellt`. Den Haken setzt
nicht der Agent - er bleibt die von Hand gesetzte Endabnahme, auch wenn die
Kriterien dahinter weggefallen sind.

**Nicht jedes Kriterium steht im freigabe-Block — manche nur in den
Handelsregeln.** `papierlauf_min_runden` (die 50 Runden) war bei xperp nie
als Feld in `wachen.json`, sondern nur in `Handelsregeln.md` Bedingung 1
verankert. Beim Lockern eines Kriteriums BEIDE Orte pruefen: den
freigabe-Block UND die Bedingung-1-Zeile der Handelsregeln; fehlt das Feld
in der wachen.json, ist die Handelsregeln-Zeile die einzige Stelle, die
angepasst werden muss (dort den Entfall mit Datum + "Max" vermerken).

## Vor dem Live

- **Der ERSTE echte Geldpfad des Systems wird geplant, dann gebaut.** Wenn die
  ganze Spur-Flotte bislang Papier war und eine Spur als erste echtes Geld
  bewegen soll: erst einen Plan schreiben (KRAKEN-LIVE-PLAN.md-Muster), der
  (a) die Faehigkeit der Zielboerse ehrlich benennt, (b) in Stufen aufteilt,
  (c) je Stufe eine eigene Bestaetigung mit Betragshoehe verlangt, (d) die
  Nachweis-Kette festschreibt (Kerzen, Paar-Info, Guthaben, validierte
  Order ohne echte Ausfuehrung, --live mit gesperrter Kette sagt welche Sperre
  zu war). Max waehlte "erst Doku/Plan schreiben, dann bauen" - dieser Plan
  wird NICHT eingebaut, bevor er ihn freigibt. Ein "ja" auf einen Plan ist
  NICHT die Live-Freigabe. Das Muster gilt je Zielboerse: KRAKEN-LIVE-PLAN.md
  ist die Kraken-Fassung, MOSAIC-LIVE-PLAN-OKX.md die OKX-Fassung.
- **OKX als Zielboerse: drei eigene Vorbedingungen pruefen, bevor der Orderweg
  gebaut wird.** (a) Instrumente gegen das Spot-Sortiment pruefen - oeffentliche
  API `/api/v5/public/instruments?instType=SPOT`, `state` muss `live` sein;
  `instId`-Namen wie `BTC-USDT` stimmen, ein `bare_symbol` (`AAVE`) nicht als
  Order-Ziel. (b) Der Key braucht `Trade`-Recht UND eine gefuellte IP-Whitelist;
  ein `read_only`-Key (oder leere Whitelist) laesst die erste echte Order still
  scheitern. Das stellt Max im OKX-Dashboard um, nicht ein Agent - nie die
  Key-Datei dafuer lesen. (c) OKX-Spot ist Long-only ohne Hebel; passt nur zu
  Long-Spuren. Der eigene Order-Zweig nutzt `POST /api/v5/trade/order`
  (HMAC-SHA256-Signatur), Stop-Loss als Boersen-Order via
  `/api/v5/trade/order-algo` (ueberlebt Neustart) - nie eine skript-bewachte
  Position als Ersatz.
- **Den gemeinsamen Buchkern nicht live-faehig machen, wenn nur EINE Spur
  echten Geldpfad soll.** `spur_buch.py` ist als "Kein Live-Zweig" gebaut;
  dort einen Live-Pfad einbauen druckt auf alle 9 Bot-Spuren, die ihn nutzen.
  Stattdessen der Spur einen EIGENEN abgetrennten Live-Zweig im eigenen
  handeln.py geben (nach dem kraken/handeln.py-Muster), Papier laeuft im
  Dauerlauf unveraendert weiter.
- **Vor dem Umbau messen, ob jede Spur ihr Instrument ueberhaupt an der
  Zielboerse handeln kann.** "Alle Spuren an Boerse X anbinden" ist sonst ein
  stiller Bruch: OKX-Swap-Derivate (whale/liquidation/sentiment), Pump.fun-
  Kleinstcoins (sniper/funding/topmovers) und RSS-Stimmung existieren auf
  Kraken nicht als handelbares Paar. Je Spur wachen.json lesen, was sie als
  `inst`/`uly`/`ccy` fuehrt, gegen das Sortiment der Zielboerse pruefen - nur
  die vertraeglichen bekommen den echten Orderweg, der Rest bleibt Papier.

- Boersen-Schluessel: das Konto muss Ordern duerfen (nicht `read_only`) und die
  IP-Whitelist fuer Orders muss stehen - vorher pruefen, sonst scheitert die
  erste echte Order.
- `herzschlag_max_minuten` gegen die GELTENDE Hausregel setzen, nicht gegen den
  Docstring: seit der 19.09.-Regel gilt **180 fuer ALLE Spuren, auch Live**
  (T-004: kein Herzschlag-Fehlschluss auf echten Positionen nach einem
  Rechner-Ausfall). Die alte "45 fuer Live"-Grenze ist obsolet, steht aber in
  manchen `_herzschlag`-Notizen noch. VOR dem Aendern pruefen, welche Regel
  aktuell ist (Memory/Bus-Zeile), sonst stellt man eine Live-Spur auf 45 und
  schlaegt bei JEDER Stoerung flach.
- Erst dann die Freigabekette ausloesen.

## Mehr Daten im Papierlauf

- **Positionsgroesse vergroessern geht NUR papier-seitig.** Ein `papier_faktor`
  in `wachen.json` (Standard 1.0) skaliert die Sizing-Werte im Papierlauf; Live
  rechnet unveraendert. Umsetzung: eine Helper-Funktion, die bei `live=True` das
  `w` unveraendert zurueckgibt und sonst eine Kopie mit skalierten Schluesseln
  liefert - so ist sie ohne Netz testbar.
- **Alle Sizing-Schluessel zusammen skalieren:** `risiko_je_anlauf_usd`,
  `max_margin_je_anlauf_usd`, `max_margin_gesamt_usd`. Bleibt der Gesamtdeckel
  unskaliert, bindet er sofort und der Faktor kommt nicht an.
- **Der Faktor beschleunigt die Rundenzahl NICHT.** `papierlauf_min_runden` ist
  ein Zaehler (eine Runde entsteht durch Stop/Ziel, nicht durch Groesse); der
  Faktor macht `netto_positiv` und `groesster_ruecklauf` aussagekraeftiger,
  bringt aber keine Runde naeher an die Mindestzahl. Das offen sagen, bevor
  jemand darauf baut.
- Ruecknahme-Bedingung mitschreiben: `papier_faktor` zurueck auf 1.0.

## OKX-Live-Bereitschaft verifizieren (bevor "erledigt" geglaubt wird)

Wenn Max meldet, er habe die Keys umgestellt ("erledigt"), NICHT glauben -
verifizieren. Die drei Pruefungen, in dieser Reihenfolge:

0. **Erst den RICHTIGEN Key-Satz pruefen - je Spur ein anderer.** xperp/okxf
   liest `OKX_API_KEY/SECRET/PASSPHRASE`, scanner/okx liest
   `OKX_LIVE_API_KEY/SECRET/PASSPHRASE`. Wer nur `OKX_LIVE_*` umstellt, hat
   xperp nicht angefasst - und umgekehrt. Vor jeder Aussage "der Key ist
   umgestellt" greppen, welchen Satz die Spur wirklich liest
   (`grep -n OKX_ <spur>/okx*.py`). `OKX_BASE` ist der Host fuer BEIDE.
   `https://my.okx.com` ist der Konto-PORTAL-Host, kein API-Host - ein
   signierter Aufruf dagegen liefert 50101. API-Host ist `www.okx.com`
   (global) oder `eea.okx.com` (EEA-Account); Max' Konto ist EEA.

1. **Keys authentifizieren auf dem RICHTIGEN Host.** `OKX 50101: APIKey does
   not match current environment` heisst: der Key gehoert zu einem anderen
   Host als dem, gegen den du pruefst. `OKX_BASE` steht in der Registry
   (`[Environment]::GetEnvironmentVariable('OKX_BASE','User')`), nicht im
   Prozess-Env. Teste den Guthaben-Abruf gegen DIESEN Host - nicht gegen
   `www.okx.com` raten. Ein Key vom EEA-Portal (my.okx.com/eea.okx.com) ist
   auf `www.okx.com` ungueltig und umgekehrt.
2. **Demo-Modus in der REGISTRY pruefen, nicht im Prozess-Env.**
   `okxf.demo_modus()` liest `HKCU\Environment` ueber einen Rueckfall - eine
   bash-Session kann `OKX_SIMULATED=1` als Artefakt tragen, wodurch
   `demo_modus()` im Test `True` zeigt, waehrend der echte Dauerlauf (ueber
   die geplante Aufgabe gestartet) es `False` hat. Pruefen:
   `[Environment]::GetEnvironmentVariable('OKX_DEMO','User')` UND
   `'OKX_SIMULATED','User'` UND die System-Variante (`'Machine'`). Nur wenn
   dort etwas steht, ist der Demo-Modus im Betrieb aktiv. Ein Test mit
   `env -u OKX_SIMULATED -u OKX_DEMO` zeigt den Betriebszustand.
2b. **Ein funktionierender Key kann trotzdem 50101 liefern - dann ist der
   Demo-Schalter die Ursache, nicht der Key.** `OKX_SIMULATED`/`OKX_DEMO`
   gesetzt => das Modul haengt `x-simulated-trading: 1` an jeden Call; ein
   ECHTER Trade-Key darauf liefert 50101, auch wenn Base und IP-Whitelist
   stimmen. Wurde die Whitelist geleert und die Base geprueft, aber 50101
   bleibt: `OKX_SIMULATED` loeschen (Benutzervariable), NICHT den Key neu
   erstellen. Gegenprobe mit `env -u OKX_SIMULATED -u OKX_DEMO` (Betriebszu-
   stand): authentifiziert der Key dann, war der Schalter das Problem.
3. **Das Konto muss die HANDELSWAEHRUNG haben, nicht nur authentifizieren.**
   Ein Guthaben-Abruf, der `0.0` liefert, heisst: Keys ok, aber kein Kapital.
   Vor "live-faehig" das volle Balance abfragen
   (`/api/v5/account/balance` ohne `ccy`) und pruefen, dass die Waehrung der
   Spur (USDT/USDC) mit eq>0 da ist - Staubbetraege in anderen Waehrungen
   (EURC/BTC/MON/...) sind kein Handelskapital. Ohne die Handelswaehrung kann
   die Spur nichts kaufen, selbst mit Freigabe.

   **Pruefe zuerst, ob die WAEHRUNG falsch gewaehlt ist, bevor du Geld
   bewegst.** Fehlt genau die Handelswaehrung, die anderen Stablecoins aber
   liegen im selben Konto, ist die kleinere Aenderung nicht der Umtausch,
   sondern der Wechsel der Quote-Waehrung auf eine, die schon da ist (gemessen:
   eine OKX-Spot-Spur verlangte USDT, davon lag nichts vor, waehrend USDC frei
   lag — die Paare BTC/ETH/SOL gibt es gegen beide). Das ist kein Trick, sondern
   derselbe Markt mit anderer Rechnung. Was dabei mitmuss, alles zusammen:
   `instrumente` in der `wachen.json` (die Kerzen kommen vom selben Endpunkt),
   `mindest_guthaben_<ccy>`, ein Feld `guthaben_waehrung`, die
   Guthaben-Funktion des Order-Moduls (`guthaben_waehrung(ccy="USDC")` mit
   erhaltenem Altnamen, falls Tests ihn aufrufen), jede gedruckte Zeile mit der
   alten Waehrung und die Test-Wachen. Danach `--vorschau` lesen: das Tor muss
   offen sein, ohne dass eine Order lief. Das Backtest-Urteil aendert der
   Waechsel nicht — ein negativ gemessenes Urteil bleibt negativ.

## Auto-Freigabe (Dauerlauf bestaetigt selbst)

Max kann die Freigabekette automatisieren: `AUTO_FREIGABE` in `dauerlauf.py`
listet die Spuren, fuer die der Dauerlauf die Freigabe OHNE `/ja` erteilt. In
`pruefe_anfragen()` ruft er dann `anfrage_stellen()` und direkt
`freigabefenster.oeffnen(spur, AUTO_FREIGABE_STUNDEN, "auto")` — genau der Weg,
den `/ja` geht, nur ohne menschliche Bestaetigung. Zeitlich begrenzt
(`AUTO_FREIGABE_STUNDEN`, z. B. 12h): danach laeuft die Freigabe ab und es muss
wieder bestaetigt werden. Kein Dauerzustand.

- **Der Live-Pfad prueft BEIDE Bedingungen unabhaengig voneinander:**
  `freigabe.erfuellt` (Bedingung 1, der von Hand gesetzte Haken) UND das
  Freigabefenster (`freigabefenster.lade(spur).offen()`). Die Auto-Freigabe
  oeffnet nur das Fenster — `freigabe.erfuellt` muss SEPARAT auf `true` stehen,
  sonst verweigert der Live-Pfad weiter (Grund `freigabe.erfuellt=false`).
  Beim Einbauen der Auto-Freigabe also auch den Haken setzen, wenn die
  Bedingungen gelockert sind.
- **Auto-Freigabe nur fuer Spuren mit ECHTEM Live-Pfad.** Vorher pruefen, ob
  `handeln.py` `--live` wirklich unterstuetzt oder verweigert: `grep -c
  "verweigert" <spur>/handeln.py` > 0 heisst Papier-only (die moondev-Spuren
  verweigern `--live` — sie haben keinen echten Orderweg und koennen gar nicht
  live handeln). Eine Auto-Freigabe fuer eine Papier-Spur ist wirkungslos.
- **Auch eine FERTIGE Spur wird nicht automatisch scharf - die Formulierung
  entscheidet.** `nur_fenster_fehlt` verlangt GENAU EINEN Grund und darin das
  Wort „Freigabefenster“. Zwei Randfaelle folgen daraus, beide im Betrieb
  gemessen: (a) eine Spur mit ZWEI Gruenden wird nie gefragt (die zweite
  Blockade haelt die Freigabe still zu); (b) eine Spur OHNE Blockade druckt
  `Live waere gesperrt durch: nichts` — auch das ist kein Fenster-Grund, also
  wird nicht gefragt und die Auto-Freigabe schaltet NICHTS. Wer vorhersagen
  will, ob eine Spur scharf geht, liest die `--vorschau`-Zeile; aus „der
  Schalter steht auf true“ und „das Guthaben reicht“ folgt es NICHT. Soll eine
  bereite Spur ueber die Auto-Freigabe scharf werden, muss ihr Vorschau-Text
  das fehlende Fenster in genau dieser Form nennen - das ist eine Aenderung am
  Sperrtext (siehe pitfalls.md, erster Punkt: der Text ist eine Schnittstelle),
  nicht am Dauerlauf. Konsequenz fuer den Bericht: „nur noch das Fenster fehlt“
  und „die Auto-Freigabe oeffnet es dann von selbst“ sind zwei verschiedene
  Aussagen — die zweite nur sagen, wenn die Zeile sie traegt.
- **Konsequenz klar benennen, bevor gebaut wird:** Auto-Freigabe = die Spur
  handelt vollautomatisch mit echtem Geld, jedes Einstiegssignal wird ohne
  menschliche Bestaetigung ausgefuehrt. Die zeitliche Begrenzung ist die einzige
  Grenze.
- **Ein aufgeladenes Guthaben IST eine Live-Freigabe.** Fehlt nur noch die
  Handelswaehrung, dann raeumt das Aufladen den letzten Nicht-Fenster-Grund weg —
  im naechsten Zyklus nennt die Vorschau nur noch das Fenster, und die
  Auto-Freigabe oeffnet es. Wer zum Aufladen raet, sagt die Folge mit; wer sie
  nicht will, laesst das Guthaben und nennt die zwei Wege (Spur aus
  `AUTO_FREIGABE` nehmen oder `handel_erlaubt` auf false). Umgekehrt gilt: vor
  dem Aufladen die Waehrung pruefen (siehe oben) — meist fehlt kein Geld,
  sondern die falsche Rechnungswaehrung.
- **Eine bereite Spur scharf stellen — was sofort wirkt und was einen Neustart
  braucht.** Nennt die Vorschau GENAU EINEN Grund und dieser heisst
  "Freigabefenster" (der Haken `freigabe.erfuellt` steht schon), dann stellt der
  LAUFENDE Dauerlauf selbst eine Anfrage (`anfrage_stellen`,
  `anfrage_bis` in `freigabe_fenster.json`). `freigabefenster.oeffnen(spur,
  stunden, wer)` bestaetigt sie — ohne wartende Anfrage verweigert `oeffnen()`
  bewusst (nichts wird aus dem Nichts scharf; der Anstoss kommt immer vom
  Dauerlauf, der die Lage geprueft hat). Danach laeuft die Spur im NAECHSTEN
  Zyklus live, **ohne Neustart**: der Modus kommt aus der Fensterdatei. Ein
  Neustart ist nur noetig, wenn `AUTO_FREIGABE` selbst geaendert wurde (das
  Tupel steht im laufenden Prozess) oder ein Code-Pfad angefasst ist. Beleg ist
  die Logzeile `<spur> (live) ok` im `dauerlauf.log`.
- **Eine zurueckgenommene Spur wieder scharf stellen (Auftrag "<spur> wieder
  live und Handel erlaubt") sind DREI Schritte, nicht einer.** (1)
  `handel_erlaubt` in der wachen.json auf true UND den alten
  `_handel_erlaubt_vermerk` durch einen neuen datierten Vermerk ersetzen (der
  alte begruendet sonst weiter das Gegenteil - ein Widerspruch in der Datei ist
  schlimmer als kein Vermerk). (2) Die Spur in `dauerlauf.AUTO_FREIGABE`
  zuruecknehmen und den Kommentar darueber, der die Herausnahme begruendet,
  mitschreiben. (3) Dauerlauf neu starten - das Tupel liegt im laufenden
  Prozess. Belegen vor dem Neustart: `handeln.py --vorschau` muss "Live waere
  gesperrt durch: nichts" sagen, und das Guthaben-Tor mit echten Zahlen zeigen
  (`handeln._guthaben_text(json.load(open('wachen.json')))` - `wachen()` gibt es
  in kraken/handeln.py nicht).
- **Eine Spur, die aus dem Papier zurueck ins Live kommt, traegt Papier-
  Positionen ohne Order-Kennung.** Der erste Live-Lauf bucht sie per
  `bueche_papier_altlasten_aus` als "buchbereinigung" aus (kraken-Massstab:
  `kauf_txid` fehlt; scanner: `kauf_ord_id`; xperp: `modus`). Das ist gewollt,
  aber es muss VOR dem Neustart gesagt werden - sonst sieht es im Journal wie
  ein Verlusttag aus.
- **Boerse wechseln statt Waehrung (`boerse` in der wachen.json).** Wenn die
  Zielboerse den Markt kennt, aber unter eigenem Paarnamen und in anderer
  Kontowaehrung: Adaptermodul mit DENSELBEN Funktionsnamen wie das bisherige
  Order-Modul, Bindung ueber eine Funktion (nicht per Import), Paar-Abbildung an
  EINER Stelle mit lautem Fehler bei Unbekanntem, Sperrenkette je Boerse
  (Schluessel, Demo-Modus, Guthaben in der richtigen Waehrung, Mindestbetrag aus
  der wachen.json). Die Instrumente duerfen in den alten Namen stehen bleiben,
  damit Kerzen und Papierzweig unberuehrt sind — nur die Order wird uebersetzt.
  Vollstaendiges Rezept mit den Fallen (JSON-Duplikatschluessel, `.format`+`%`,
  Testvergleich ueber Modulnamen): `references/zweite-boerse.md`.
- **`handel_erlaubt: true` ist ein Schalter, kein Orderweg — erst die Flotte
  pruefen, dann scharf stellen.** Auftraege wie "alle Spuren live offen und
  handel_erlaubt" sind mit einem Dateischalter erledigt, sagen aber nichts
  darueber, welche Spur ueberhaupt ordern KANN. Vor jeder Meldung "erlaubt":
  je Spur nach einem Orderaufruf im Code suchen (Endpunkt-Zeichenketten wie
  `/api/v5/trade/order`, `AddOrder`, `place_order`, `order_senden`; Testdateien
  und `tests/` ausschliessen, sonst zaehlt ein Demo-Testskript als Live-Pfad).
  Spuren ohne Orderaufruf bekommen den Schalter mit Vermerk
  (`_handel_erlaubt_vermerk`: "kein Orderaufruf im Code - hat heute keine
  Wirkung") — sonst liest die naechste Sitzung den Schalter als Faehigkeit.
- **Die Spurenliste NIE zweitens fuehren.** Welche Spur laeuft, steht in
  `dauerlauf.SPUREN` (Dict, nicht Liste — beim Auslesen per Regex die
  Klammer-Ebene zaehlen, sonst trifft die Suche `NUR_BASIS` oder einen Kommentar).
  Wer eine Statusanzeige baut, liest sie von dort; die Werkzeuge dafuer sind
  `Agenten/Handel/spuren_stand.py` (Tabelle: handel_erlaubt, Herzschlag, Fenster,
  `freigabe.erfuellt`, Orderpfad, Buchgroesse, Zyklusalter) und
  `Agenten/Handel/sperrgruende.py` (Sperrgruende aus der EIGENEN Vorschau jeder
  Spur, markiert "nur das Fenster fehlt" = der Fall, in dem die Auto-Freigabe
  greift). Beide rein lesend — sie ersetzen die Frage "welche Spur darf und
  woran haengt sie" durch eine Messung, statt durch eine gepflegte Zweitliste.

## Papier und Live teilen EIN Buch — der teuerste Zwischenzustand

Jede Spur fuehrt EIN Buch (`zustand.json`) fuer beide Modi. Laeuft sie mit
geschlossenem Fenster im Papier, fuellt sie dasselbe Buch; wird das Fenster
dann geoeffnet, liest der Live-Pfad diese Positionen als seine eigenen. Ihnen
fehlt die `kauf_ord_id`, am Handelsplatz gibt es also nichts zu verkaufen:
das Buch ist mit Plaetzen belegt (kein Neukauf mehr), jeder Ausstiegsversuch
laeuft in einen Fehler, und ein Notausstieg will verkaufen, was nicht da ist.

- **Messen statt ahnen:** `zustand.json` lesen und je Position `kauf_ord_id`
  pruefen. `null` bei `modus: live` = Papier-Altlast. Gegenprobe:
  `grep -c ",live," <spur>/handelsjournal.csv` gegen die Zahl der
  Buchpositionen — ein volles Buch ohne Live-Zeilen ist der Befund.
- **Einmal-Aufraeumen heilt nicht.** Das Aufraeumen von Hand
  (`buchbereinigung.py`-Muster: Positionen OHNE Order zum Marktkurs als
  Papier-Verkauf mit eigenem `grund` ausbuchen, Positionen MIT Order liegen
  lassen, idempotent) wirkt nur bis zum naechsten Papier-Zyklus.
- **Dauerhaft sind zwei Wege, am besten beide:** (a) der Live-Zweig raeumt zu
  BEGINN jedes Live-Laufs selbst aus — eine Funktion, die vor dem
  Ausstiegspruefen laeuft, ohne Kurs nichts anfasst und die Altlast als
  Papier-Verkauf journalisiert; (b) jede Position traegt ihren Modus und der
  Live-Pfad ueberspringt fremde (`if p.get("modus") != "live": continue`).
  (b) allein genuegt, wenn die Spur den Modus immer setzt — ein Altbestand
  ohne Feld gilt dann als Papier und bleibt liegen, was gewollt ist.
- **Test:** Temp-Buch mit je einer Position mit und ohne Order, Fake-Boerse fuer
  den Kurs; geprueft wird: keine Order ausgeloest, genau eine Journalzeile mit
  dem eigenen Grund, die Position MIT Order bleibt. Ohne Test waechst der
  Zustand nach.

## Nach dem Scharfschalten beobachten

Eine scharfe Spur kann still nichts tun — aus zwei Gruenden, die im Journal
gleich aussehen (keine neue Zeile):

1. **Die Order scheitert.** Fehler gehen auf stderr, der Dauerlauf verwirft sie
   und meldet die Spur als `ok`. Deshalb: **jede Fehlerstelle im Live-Pfad
   schreibt eine Journalzeile** (`modus="live"`, `aktion="fehler"`,
   `grund=<Meldung>`) — mindestens Kauf, Stop und Verkauf. Die Zeile ersetzt
   keine Buchung (die Auswertung zaehlt nur `kauf`/`verkauf`) und macht aus
   einem ausbleibenden Einstieg eine beantwortbare Frage. Genau der Fall, der
   die offene Frage „darf der Schluesselsatz ordern?" entscheidet, ist sonst
   unsichtbar.
2. **Das Fenster ist abgelaufen.** Danach laeuft die Spur wieder Papier, bis die
   Auto-Freigabe neu oeffnet oder jemand `/ja` sagt — das sieht ohne Meldung aus
   wie „die Spur tut nichts".

Wache dafuer (Muster `Agenten/Hermes/scripts/mosaic-live-wache.py`, Hermes-Cron
mit `no_agent`): Journalzeilen mit `modus="live"` zaehlen, jede NEUE melden
(`LIVE: <zeit> <aktion> <inst> @ <kurs> <einsatz>` bzw.
`LIVE-FEHLER: <zeit> <inst> <grund>`), zusaetzlich den Wechsel des Fensters
melden und sonst SCHWEIGEN (leere Ausgabe = keine Nachricht). Den Stand in eine
Laufzeitdatei unter `Agenten/Hermes/cache/` schreiben, sonst meldet die Wache
jedes Mal alles erneut; im Erstlauf nur den Zustand setzen und nichts senden.
Beleg je Meldungsart: eine Probe-Journalzeile in einem Temp-Ordner — der erste
Lauf meldet genau einmal, der zweite ist still.

## Wie man Max die Entscheidung stellt

Live-Fragen sind Entscheidungen mit Geld — sie gehoeren als NUMMERIERTE Optionsliste
vorgestellt (Empfehlung zuerst, je Option eine Zeile Konsequenz), damit Max mit zwei
Woertern antworten kann. Er tut das: „Ja", „Liegen lassen ja", „2. ja", oder er
antwortet mit einer Bedingung („Auf okx usdc nehmen!"), die keine der beiden Optionen
war, sondern die Ursache der Frage aufloest.

- **Ein „ja" ohne Nummer bezieht sich auf die Empfehlung.** Nicht nachfassen.
- **„Liegen lassen" heisst: nichts aendern.** Keine Datei anfassen, keinen Schalter
  setzen — und das im Bericht ausdruecklich als getroffene Entscheidung nennen.
- **Eine Antwort, die eine VORAUSSETZUNG nennt statt einer Option, ist ein Auftrag an
  der Ursache.** Wer dann nur die gewaehlte Option ausfuehrt, laesst den teuren Teil
  stehen (Beispiel: statt Geld umzutauschen die Handelswaehrung der Spur wechseln).
- **Die eindeutige Haelfte sofort ausfuehren, die uneindeutige benennen** — nicht
  beides zurueckstellen: eine Rueckfrage auf eine schon erteilte Anweisung kostet
  einen Zug und wirkt, als haette man nichts verstanden.

## Sibling-Session armiert parallel

In einem Baum mit mehreren Sitzungen kann eine ANDERE Session eine
live-faehige Spur scharf stellen (Commits wie `handel_erlaubt=true`,
`herzschlag 45`, `AUTO_FREIGABE`), waehrend der Key noch kaputt ist. Das
kollidiert mit einem eigenen Sicherheits-Revert und ist genau der
Halbzustand, den man zurueckdrehen will. Vor und nach der eigenen Aenderung
`git log --oneline -1 -- <spur>/wachen.json` + `git status --porcelain`
pruefen - der gelesene Stand ist eine Momentaufnahme. Ist der eigene Commit
von `index.lock` blockiert (Sibling committet gerade), NICHT den Lock
erzwingen (Korruptionsrisiko) - den Revert auf der Platte lassen, den
Konflikt namentlich melden und Max entscheiden lassen, ob die Sibling-Session
pausiert wird. Ein Revert, der nicht committet ist, wird vom naechsten
Sibling-Commit ueberschrieben.

## Bau-Details fuer einen echten OKX-Live-Zweig

- **Papier und Live mit GETRENNTEN Betraegen fahren.** `live_max_pro_trade_usd`,
  `live_max_offene_positionen`, `live_max_gesamt_usd` in `wachen.json`; Papier
  rechnet weiter mit den Basis-Werten (`max_pro_trade_usd` usw.). So bleibt der
  Papierlauf statistisch aussagekraeftig, waehrend Live klein anfaengt (z. B.
  10/5/200 gegen 150/4/600). Der Live-Code liest die `live_*`-Felder mit
  Fallback auf die Basis-Werte.
- **Damit das Freigabefenster gegen die LIVE-Grenzen prueft** (nicht gegen die
  grossen Papier-Werte, sonst wuerde ein 100-USDT-Auftrag im Fenster
  durchkommen): `freigabe.pruefe()` muss im `SPOTARTIG`-Zweig die `live_*`-
  Felder bevorzugen (Fallback auf `_z(...)`), und die Spur im Freigabefenster
  registrieren (`WACHEN`, `SPOTARTIG`, `BETRAGSFELD`, `TITEL`, `RECHNER` in
  `freigabe.py`) - sonst kennt `bestaetige()` sie gar nicht ("Unbekannte
  Spur").
- **OKX_DEMO/OKX_SIMULATED als HARTE Live-Sperre behandeln.** Ist eine der
  Variablen gesetzt, geht auch `--live` aufs DEMO-Konto - ohne eigene Sperre
  faellt das nicht auf, die "echte" Order laeuft nur aufs falsche Konto. In
  `live_sperren()` einen Grund `OKX_DEMO/OKX_SIMULATED gesetzt - Demo-Konto`
  aufnehmen.
- **Ein Test kann diese Variablen nicht ueber `os.environ.pop` loeschen.** Das
  OKX-Modul liest Keys und Demo-Flag ueber einen Registry-Rueckfall
  (`HKCU\Environment`), der unabhaengig von der Prozessumgebung lebt - der
  `pop` bleibt wirkungslos und der Test muss die Modul-FUNKTION direkt mocken
  (`okx_spot.demo_modus = lambda: False`, `okx_spot.schluessel_vorhanden =
  lambda: True`) und in `tearDown` zuruecksetzen.
- **Beim Einbauen des Live-Zweigs in eine bestehende `lauf()`: die `live`-Flag
  am Funktionsanfang mit `False` initialisieren**, VOR jedem `if live:`-Zweig.
  Papier-/Vorschau-Modi pruefen diesen Zweig ebenfalls; ist `live` nur im
  Live-Zweig gesetzt, gibt es dort einen NameError.
- **Eine Variable, die nur in einem optionalen inneren try/except gesetzt wird
  (z. B. `algo_id`), VOR dem try auf `None` initialisieren.** Der
  Exception-Zweig, der nicht `continue`-t, laeuft sonst in den Append weiter
  und wirft NameError (Fall: Stop fehlgeschlagen UND Rueckverkauf
  fehlgeschlagen -> Position trotzdem buchen und als unbewacht markieren).
- **Ein Test, der eine Journal-Zeile einer Live-Funktion pruefen will, muss
  `SCHREIBEN=True` setzen (auf den Temp-JOURNAL-Pfad).** Mit `SCHREIBEN=False`
  entsteht die Datei nie und `open` wirft FileNotFoundError. Temp-Ziel plus
  Modulwaechter schuetzen den echten Spurenordner.
