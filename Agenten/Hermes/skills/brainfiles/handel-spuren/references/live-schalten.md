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
- **Konsequenz klar benennen, bevor gebaut wird:** Auto-Freigabe = die Spur
  handelt vollautomatisch mit echtem Geld, jedes Einstiegssignal wird ohne
  menschliche Bestaetigung ausgefuehrt. Die zeitliche Begrenzung ist die einzige
  Grenze.

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
