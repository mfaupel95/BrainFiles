---
name: okx-orderweg-diagnose
description: "Use when eine OKX-Order scheitert oder ein Adapter gegen ein Demo-Konto geprueft wird (Code deuten)."
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [OKX, Handel, Live, Fehlersuche, Belegpflicht]
    related_skills: [handel-spuren, okx-live-anbinden, betriebsrunde]
---

# Orderweg einer Live-Spur: deuten, belegen, sicher beheben

Eine Handelsspur meldet einen Orderfehler vom Handelsplatz (Verkauf/Kauf/Stop
fehlgeschlagen, OKX-Code). Dieses Skill ist die Reihenfolge, in der so ein Fall
abgeraeumt wird: Ursache an der AUFRUFSTELLE festmachen, mit einem LESENDEN
Aufruf belegen, dann die kleinste sichere Aenderung — und Tests, die den Fall
festhalten. Es gilt fuer jede Live-Spur (scanner, xperp, mosaic, kraken), nicht
fuer die Auswertung der Buecher (`handel-spuren`).

## When to Use

- „scanner: Verkauf X fehlgeschlagen: OKX 51000 …" / „Kauf X fehlgeschlagen" / „Stop … fehlgeschlagen"
- ein OKX-Code muss gedeutet werden (51000, 51603, 51008, 50119, 50101, 50124,
  51006, 51001)
- ein Adapter/Probe soll gegen ein DEMO-Konto verifiziert werden (welche
  Instrumentklasse handelt dieses Konto ueberhaupt, und fuellt sie?)
- eine echte Position scheint zu fehlen, oder das Buch und das Konto passen nicht zusammen
- eine Order soll gesetzt/verkauft werden und der Live-Pfad ist unklar

## Pruefregel (die tragende Regel)

**Lesen vor Deuten, Beleg vor Aussage.** Jede Aussage ueber echtes Geld wird mit
einem signierten LESEaufruf bewiesen (Kontostand je Waehrung, Orderhistorie) —
aus der Fehlermeldung allein wird nichts geschlossen, und zum Diagnostizieren
wird NIE eine Order gesetzt (auch keine kleine, auch nicht „zum Testen").

## Procedure

1. **Fehlerzeile woertlich nehmen, Aufrufstelle suchen.** `grep -n "fehlgeschlagen"
   <spur>/handeln.py`. Achtung: eine Meldezeile umfasst oft MEHRERE Aufrufe — ein
   „Verkauf fehlgeschlagen" kann aus der Mengen-/Detailabfrage davor stammen, nicht
   aus dem Verkaufsaufruf selbst. Die Zeile lesen, die den Text druckt, und sehen,
   welche Aufrufe in ihrem `try` stehen.
2. **Code der Aufrufstelle zuordnen** (Tabelle: `references/okx-fehler-und-nachweis.md`).
   `51000` = Parameter leer/ungueltig, nicht „Order unbekannt" (`51603`).
3. **Belegen statt vermuten** — aus dem Spur-Ordner, mit dem Haus-`okx`-Modul:
   Basis und Schluessel ausgeben (`okx._live_basis()`, `okx.schluessel_vorhanden()`),
   dann `okx._roh(pfad, signiert=True)` fuer Kontostand je Waehrung und Orderhistorie.
   Rezept + fertige Endpunkte: `references/okx-fehler-und-nachweis.md`.
   Fertige Sonde statt Handarbeit: `scripts/okx-zugang-pruefen.py` druckt Host,
   Handelsrecht, freie Quote-Waehrung und die offenen Notausstiege — rein lesend,
   setzt keine Order.
   Gegen ein DEMO-Konto: `scripts/okx-demo-matrix.py` (Host x Demo-Kopf x
   Instrumentklasse x Orderbuch in einem Lauf, `--order <inst> <sz>` setzt genau
   eine Kauforder).
   Buch gegen Boerse stellen (Fuellung, Geister, Wiederherstellung):
   `references/buch-gegen-boerse.md`.
   **Und der teuerste Fall davon: ein HANDVERKAUF, der als Geist gebucht wird** —
   `references/handverkauf-geist.md`. Drei eigene Befunde vom 05.10.2026:
   `positions-history` liefert `avgPx: None`, der Verkaufspreis steht nur in
   `/trade/fills`; die Geisterpruefung kannte nur „da" oder „weg" und keinen
   TEILVERKAUF; und der Groessenabgleich lief NACH der Geisterpruefung, war bei
   einer auf null gelaufenen Position also wirkungslos. Vier echte Positionen
   verloren ueber Nacht ihren Erloes (STRK realisiert +70,76 USD, gebucht 0,00).
   **Was offen ist, abgesichert und wie viel Luft bleibt** (Kontostand je
   Waehrung, offene Positionen, Stops mit ihrer Menge): 
   `references/kontostand-und-positionen.md` — dort steht auch, warum die
   Kontoebene von `/account/balance` nur die Summe traegt und ein Parser
   dort ein Konto mit 949 USDC als leer meldet, und **was zu tun ist, wenn
   die Messung sagt, dass eine Position bereits gedeckt ist**: eine bereits
   gesicherte Position ist keine Aufgabe, sonst verkauft die zweite
   Schutzebene beim ersten Treffer doppelt.
4. **Folgen benennen**: was war echt (Konto), was nur Buch (Journal), was der Nutzer
   wissen muss. Leere Kontodetails + leere Orderhistorie = die Position hat es am
   Handelsplatz nie gegeben — dann ist der abgebrochene Verkauf RICHTIG gewesen.
5. **Kleinste sichere Aenderung bauen.** Bei einem Verkauf ohne Order-Kennung: vor
   jeder Abfrage abbrechen und es im Klartext drucken — siehe Pitfalls. Bestehende
   Aufraeumfunktionen der Spur nutzen statt eine zweite Wahrheit zu bauen.
6. **Test, der den Fall festhaelt** — im Attrappen-Stil der Spur
   (`scanner/tests/test_handeln_boersenstop.py`): Attrappe statt `okx`, Journal in
   eine Temp-Datei, und pruefen, dass KEINE Order an die Boerse geht.
7. **Belegen und sichern**: Tests der Spur,
   `Agenten/Handel/spiegelstand.py` (Bedingung 4, muss byte-gleich melden),
   Commit nur eigener Pfade (`brainfiles-auftrag`).
8. **Kein Dauerlauf-Neustart noetig**: der Dauerlauf startet `handeln.py` je
   Zyklus als eigenen Prozess — die Aenderung wirkt im naechsten Zyklus.
9. **Wenn der Befund „Handverkauf" lautet, ist der GEIST fast schon gebucht.**
   Wer eine Position von Hand schliesst, erzeugt drei Zustandsuebergaenge
   gleichzeitig (Menge kleiner, dann 0, offene Algo-Order verschwindet) — und
   die Geisterpruefung sieht davon nur „fehlt". Bevor du `buchbereinigung_geist`
   in einem Journal suchst, frag `/trade/fills` (der einzige Ort mit dem
   Ausfuehrungspreis) und stelle die Buerge-Menge gegen die Buchmenge. Details,
   Uhrzeit-Kette und die gebaute Bruecke: `references/handverkauf-geist.md`.

## Pitfalls

- **`code=1 All operations failed` sagt NICHTS — der Grund steht in `data[0]`.**
  OKX meldet je Order `sCode`/`sMsg` IM Datensatz, das Top-Level-`code` ist nur
  die Zusammenfassung (bei mehreren Orders in einem Aufruf ist sie immer `1`).
  Reihenfolge: `data[0].sCode`, `data[0].sMsg`, dann `ordId`/`algoId` pruefen —
  sonst deutet man „All operations failed" als Guthaben- oder Rechteproblem,
  waehrend in `sCode` z. B. `51006` (Preisband) oder `51001` (Instrument) steht.
- **Im `posMode=net_mode` kein `posSide` mitschicken.** `posMode` aus
  `/account/config` lesen; ein Orderkoerper mit `posSide: long` auf einem
  net_mode-Konto ist ein Formfehler, kein Handelsfehler. `posSide` gehoert nur
  in den long/short-Modus.
- **`50101`/`50119`/`51001` zuerst gegen die EIGENE Aenderung stellen, nicht
  gegen den Schluessel.** Alle drei entstehen auch durch einen fehlenden oder
  falschen Kopf (`x-simulated-trading`), einen falschen Host oder einen
  Tippfehler im Pfad. Bevor ein neuer Schluessel angelegt oder eine neue ID
  gebaut wird, den Aufruf mit den Daten eines NACHBARWEGS wiederholen, der
  nachweislich funktioniert (gleicher Host, gleiche Signatur, anderer Pfad) —
  erst wenn der Nachbarweg traegt, ist der Schluessel das Problem.
- **`51000 Parameter ordId error` ist ein Parameterproblem, kein Bestandsproblem.**
  Python-`urlencode` schreibt `None` als den Text „None"; eine Position ohne
  Order-Kennung schickt also genau das. Ein formal gueltiger, aber unbekannter
  `ordId` ergibt `51603`. Immer die Aufrufstelle lesen, nie den Code allein deuten.
- **Eine ANGENOMMENE Order ist keine Position.** `order_limit()` gibt die ordId
  zurueck, sobald der Handelsplatz sie annimmt — nicht wenn sie fuellt. Wer sofort
  bucht, hat bei einem Limit, das nie fuellt, eine Position im Buch und an der
  Boerse nur eine offene Order (`accFillSz 0`, `state live`): ein Platz ist belegt,
  der Ausstieg verkauft ins Leere, Funding und Bilanz rechnen fuer etwas, das
  niemand haelt. Vor dem Buchen die Fuellung pruefen (`accFillSz`), bei 0 die Order
  stornieren und nichts buchen, bei Teilfuellung den Rest stornieren und nur das
  - **Unbekannte Antwort (Abfragefehler) zaehlt als nicht gefuellt.**
  - **Ein Limit HINTER dem Markt ist keine Nichtfuellung, sondern ein WARTENDER Auftrag.**
    Ein Kauflimit unter dem Ask (bzw. ein Verkaufslimit ueber dem Bid) kann im Moment
    gar nicht fuellen — es wartet auf einen Ruecklauf, und das ist bei einer
    Einstiegsrechnung aus Zonen/Swing-Punkten die Absicht. Erst die Marktbarkeit
    entscheiden, dann urteilen (`kurs_und_spanne` → letzter Kurs, Bid, Ask):
    **marktbar und trotzdem nicht gefuellt** = echter Fehler (stornieren, Journalzeile
    `order_nicht_gefuellt`); **nicht marktbar** = liegen lassen, Journalzeile
    `order_offen` mit Grund `limit_wartet`, und eine eigene Liste im Zustand
    (`wartende`) fuehren. Diese Liste am ANFANG jedes Live-Zyklus abarbeiten: gefuellt →
    als Position buchen (Stop und Ziel haengen als `attachAlgoOrds` an der Order und
    werden beim Fuellen aktiv), storniert → vergessen, sonst unveraendert liegen
    lassen. Ohne diesen dritten Weg entsteht eine Schleife: Order setzen, Order nach
    Sekunden wegwerfen, Order wieder setzen — jede Runde ein Fehlerprotokolleintrag,
    den niemand entscheiden kann, und ein Platz, der nie belegt wird.
- **Das Buch gegen die BOERSE pruefen, nicht gegen sich selbst.** `/account/positions`
  ist die Wahrheit eines Live-Buchs; fehlender Bestand oder Groesse 0 (OKX behaelt
  geschlossene Positionen als Zeile) ist ein Geist. Beim Ausbuchen die offene Order
  dazu stornieren, sonst fuellt sie spaeter und erzeugt eine Position ohne Buch.
  Reihenfolge beachten: **erst den Orderzustand fragen, dann ausbuchen** — ein
  Limit, das genau jetzt fuellt, sieht wie ein Geist aus, ist aber eine echte
  Position (gefuellte Order = Position, auch wenn die Positionsliste nachhinkt).
  Faellt die Abfrage aus, bleibt das Buch unberuehrt: ein Netzfehler darf nie
  Positionen loeschen.
- **Ein PAPIERLAUF schliesst keine Position mit `modus=live`.** Loest der
  Kill-Switch aus, waehrend die Spur ohne Fenster (oder mit `handel_erlaubt=false`)
  im Papier laeuft, schliesst die Flachstellung sonst auch echte Positionen — aber
  nur im Buch, an der Boerse bleibt die Position offen. Ergebnis: eine gehebelte
  Position ohne Buch, kein Ausstieg, kein Funding. Solche Positionen im Papierlauf
  stehen lassen und im Klartext melden; geschlossen werden sie nur vom Live-Lauf.
- **Sperre und Kill-Switch sind zwei Dinge — vor dem Entsperren beide rechnen.**
  `handel_erlaubt=true` allein genuegt nicht: liegt der Ruecklauf ueber
  `kill_switch_gesamt_usd`, stellt der naechste Zyklus sofort wieder flach und
  verkauft dabei die gerade wieder eingebuchte Position. Vor dem Entsperren die
  eigene `lage()` fragen (Ruecklauf, Hoechststand, Groessenfaktor) und den Deckel
  datiert anheben oder die Sperre bleibt sinnlos. Danach einen Zyklus abwarten und
  Buch, Journal und Boerse gegeneinander belegen.
- **Eine ausgebuchte, aber echt vorhandene Position gehoert ins Buch zurueck** — mit
  den Werten der Eroeffnungszeile aus dem JOURNAL, nie geschaetzt; zusaetzlich
  pruefen, ob der boersenseitige Stop noch steht (Anhaenge einer Order greifen
  nicht immer), und ihn sonst nachsetzen. Eine gehebelte Position ohne Stop laeuft
  bis zur Liquidation, wenn der Rechner ausfaellt.
- **Kein Market-Verkauf ohne Order-Kennung.** Eine Position ohne `kauf_ord_id` hat am
  Handelsplatz nichts, was verkauft werden koennte: der Verkauf muss VOR der ersten
  Abfrage abbrechen. Ein Market-Verkauf ohne Kennung verkauft nicht „nichts", sondern
  den GESAMTEN Bestand dieses Werts auf dem Konto — auch Coins, die die Spur nie
  gekauft hat.
- **Die Quote-Waehrung entscheidet, was kaufbar ist.** `ccy=USDT` gegen `ccy=USDC`
  pruefen: bei 0 USDT scheitert JEDE `-USDT`-Vorschau, waehrend die `-USDC` desselben
  Laufs durchgeht. Solche Fehlkaeufe fallen nicht auf — sie stehen nur nicht im Buch.
- **Ein Buch fuer Papier und Live.** Faellt ein Live-Kauf aus, fuellt der naechste
  Papierlauf dasselbe Buch; im Live-Lauf stehen dann Positionen ohne jede Order,
  belegen Plaetze und laufen bei jedem Ausstieg in denselben Fehler. Ein Live-Lauf
  muss Papier-Altlasten VOR dem Handeln ausbuchen (idempotent, im Live-Pfad gated).
- **Ein fehlgeschlagener LESEaufruf darf keinen Ausstieg blockieren.** Eine
  Mengenabfrage, die die ganze Verkaufslogik umwirft, macht aus einem
  Verbindungsfehler eine offene Position. Abfrage und Verkauf getrennt behandeln
  (Menge notfalls aus dem Buch rechnen) — aber nur, wenn die Order-Kennung wirklich
  vorhanden ist.
- **Kein Schalter fuer eine Diagnose.** Ein Fehlercode ist kein Grund, `--live` zu
  fahren, eine Testorder zu setzen oder Guthaben zu verschieben. Beweis ist der
  LESEaufruf.
- **`OKX 1: All operations failed` ist meist KEIN freies Guthaben, nicht ein toter
  Schluessel.** `availEq` der Margin-Waehrung ist 0, obwohl die Spur in ihrem
  eigenen Modell Platz sieht. Eine CROSS-Margin-Position (oft eine uebernommene
  Fremdposition, `fremdposition_uebernommen` im Journal) bindet das GESAMTE Konto,
  waehrend die Spur `isolated` eroeffnet und ihr `max_margin_gesamt_usd` nur das
  eigene Buch zaehlt. Beleg: `/account/balance?ccy=<margin>` (`availEq` 0 bei
  gefuelltem `eq`/`frozenBal`) + `/account/positions` auf `mgnMode=cross`. Die Spur
  muss vor dem Eroeffnen das freie `availEq` der Boerse lesen und bei 0
  ueberspringen statt blind eine Order zu schicken, die gar nicht fuellen kann.
- **`50119`/`50101` heisst meistens FALSCHER HOST, nicht toter Schluessel.** Ein
  Prozess, der die Windows-Benutzervariablen nicht geerbt hat (aus einem MCP-Server
  oder einer geplanten Aufgabe gestartet), findet den Schluessel ueber den
  Registry-Rueckfall, den HOST aber nicht, wenn der nur aus `os.environ` gelesen
  wird — dann signiert ein EEA-Schluessel gegen `www.okx.com`, und OKX antwortet
  `50119 API key doesn't exist`. **Regel: Schluessel und Host gehoeren zu EINEM
  Zugang — wer einen von beiden mit Rueckfall liest, liest den anderen genauso.**
  Probe ohne Netz: `env -u OKX_BASE <venv>/python.exe -c "import okx; print(okx._live_basis())"`
  muss die Kontakt-Basis liefern. Vor dem Umbau pruefen, was die Nachbarspuren tun
  (`xperp/okxf.py`, `mosaic/okx_spot.py`) — dort steht die richtige Form meist schon.
- **`50124` heisst FALSCHER MARKT-NAMENSRAUM, nicht fehlende Berechtigung.** Ein
  Markt kann oeffentlich gelistet und trotzdem nicht handelbar sein: auf einem
  EEA-Konto liegt er nur als XPERP-Kontrakt (`instType=FUTURES`,
  `XAU-USD_UM_XPERP-…`), waehrend die Spur den gleichnamigen gewoehnlichen
  Perpetual (`instType=SWAP`, `XAU-USDT-SWAP`) schickt. `/account/config` zeigt
  dann `perm: read_only,trade` und `acctLv: 2` — die Rechte sind in Ordnung.
  **Reihenfolge: erst den Namensraum, dann die Rechte.** Beleg ist die
  ORDERHISTORIE des vermuteten Zwillings mit passendem `instType` (der falsche
  Typ gibt `51015 Instrument ID doesn't match instrument type`) plus
  `/account/positions` je `instType`; nie eine Testorder zur Diagnose. Fix an der
  Aufrufstelle: je Basiswert EINMAL auf den handelbaren Zwilling aufloesen (nicht
  je Kandidat), den vollen Kontaktdatensatz mitgeben (ctVal/tickSz/Hebel des
  GEHANDELTEN Kontrakts) und eine Reihe ohne Zwilling aus der Liste fallen lassen
  statt in einen Fehler laufen. Codes und Sonden:
  `references/okx-fehler-und-nachweis.md`.
  **Und ein DEMO-Konto handelt eine ANDERE Instrumentklasse als das Live-Konto.**
  Vor der Verifikation eines Adapters gegen ein OKX-Demo-Konto die handelbare
  Klasse MESSEN, nicht annehmen — ein EEA-Demo-Konto handelte in der Messung
  `FUTURES` (datiert, z. B. `BTC-USD_UM-261030`: Order fuellt) und weder `SWAP`
  (`50124`) noch XPERP (`51001`, Instrument auf dem Konto nicht vorhanden).
  Der Kopf `x-simulated-trading: 1` ist dabei PFLICHT: ohne ihn antwortet jeder
  signierte Aufruf `50101`, und das liest sich wie ein falscher Schluessel.
  Messmatrix und Buch-Falle: `references/okx-fehler-und-nachweis.md`. Das ist eine
  KONTO-Konfiguration, kein Codefehler: ein `SWAP`-Adapter kann auf so einem Konto
  NICHT demo-verifiziert werden, egal wie korrekt er ist — also entweder den
  Adapter auf die handelbare Klasse umstellen oder das Konto mit der Klasse
  versehen, und das VOR dem Bauen entscheiden.
  **Bleibt danach eine Testposition offen, weil sie sich nicht verkaufen laesst,
  gehoert eine WACHE dazu — nicht die Zusage, spaeter nachzusehen.** Max liest
  das im Chat; er will den ersten echten Vorgang automatisch gemeldet haben.
  Also Cron (`no_agent`, leere Ausgabe = nichts senden) mit genau vier
  Bedingungen: Schutz-Stop weg **oder Stop-MENGE kleiner als die
  Positionsmenge** (Summe der `sz`, nicht die ANZAHL der Stops), Position
  geschlossen (mit PnL), Kurs naeher als ~1,5 % am Stop (einmal je
  Annaeherung), Abfrage kaputt (hoechstens alle 6 h).
  Die Mengenfassung ist der Teil, der gern fehlt: eine Wache, die `len(stops)`
  prueft, schweigt genau dann, wenn eine zweite Order die Position vergroessert
  (2,1 -> 2,2 Kontrakte bei einem Stop ueber 2,1) — der Rest laeuft nackt, und
  sie meldet „geschuetzt".  Die Merkdatei nach `Agenten/Hermes/cache/`, Kern bei
  der Spur, duenner Wrapper in `Agenten/Hermes/scripts/` — das Cron-Feld `script`
  nimmt nur einen DATEINAMEN, keinen Pfad. Fertiges Muster zum Abschreiben:
  `Agenten/Handel/omnitrade/demo_position_wache.py` (Kern, reine `beurteilen()`
  plus duenne `lage()`), `Agenten/Hermes/scripts/okx-demo-wache.py` (Wrapper per
  Pfad importiert, fehlender Kern = Exit 2 statt leerer Ausgabe),
  `omnitrade/tests/test_demo_position_wache.py` (Tests nur gegen die reine
  Funktion, kein Netz). Vor dem Setzen des Stops die
  haengenden Verkaufsorders stornieren, sonst liegen zwei Verkaeufe plus Stop auf
  demselben Bestand.  **Vor dem Bau oder der Verifikation eines Perpetual-Adapters die handelbare
  Klasse des Zielkontos belegen**
  (`/account/config` `perm`/`settleCcy` + eine kleine Spot-Order als Positivprobe),
  und das `InstType`-Enum des Adapters gegen die EEA-tradable Klasse pruefen
  (EEA-Perpetuals sind `FUTURES`/XPERP, nicht `SWAP`). **Geglueckte
  Zwischenendpoints sind KEIN Handelsbeweis.** `set-leverage` und `ensure-net-mode`
  sind Konto-Endpunkte und laufen auch auf einem Konto durch, das den Markt
  trotzdem nicht handeln darf — eine Verifikationsprobe darf da nicht stehen
  bleiben ("leverage ok, net-mode ok" ≠ "handelbar"). Beweisen darf es nur die
  (kleine) Order selbst oder die signierte Sichtbarkeits-Differenz; und die
  DEMO-Balance muss die Quote-Waehrung der Ziel-Order ueberhaupt tragen (ein
  Demo-Konto ohne USDT kann keine `-USDT`-Order finanzieren, egal welche Rechte
  es haelt).
  **Der Beweis dafuer ist die DIFFERENZPROBE signiert gegen unsigniert.**
  `/api/v5/public/instruments` ist ein OEFFENTLICHER Endpunkt, wird aber mit
  Anmeldekopf auf den Kontoumfang eingeschraenkt. Denselben Pfad also zweimal
  rufen — einmal mit Signatur, einmal ohne, gleicher Host, gleiche Instrument-ID:
  **unsigniert `state: live` und signiert `51001 Instrument doesn't exist` heisst,
  dass es den Markt gibt und das KONTO ihn nicht sehen darf.** Das ist eine
  Berechtigungsgrenze, kein Namensfehler und kein Tippfehler in der ID — und sie
  ist mit keiner Codeaenderung zu beheben. Ohne diese Probe liest sich `51001` wie
  eine falsche Instrument-ID, und man baut die ID endlos um (Kurzform, volle Form,
  anderer Verfall), waehrend jede Variante am gleichen Wall endet.
  **Reihenfolge daraus: bei JEDEM `51001` auf eine ID, die man oeffentlich
  gelistet gesehen hat, zuerst unsigniert gegenpruefen** — erst danach ueber
  Namensraum oder Adapter nachdenken. Positivprobe nicht vergessen: eine kleine
  Spot-Order auf demselben Konto belegt, dass Schluessel, Signatur, Host und
  Passphrase in Ordnung sind, und grenzt den Befund auf die Instrumentklasse ein.
- **Ein fehlgeschlagener Ausstieg hinterlaesst einen halben Zustand.** Der Verkauf
  bestellt ZUERST den Notausstieg ab (sonst blockiert er den Bestand). Scheitert der
  Verkauf DANACH, steht die Position ohne Stop an der Boerse, bis der naechste Zyklus
  es erneut versucht — ueber Nacht mit einem Festnetz-Verlustrisiko, das niemand
  sieht. Nach einem fehlgeschlagenen Verkauf den Stop mit der ECHTEN Fuellungsmenge
  (`accFillSz` der Kauforder) neu setzen; einen alten, nicht stornierbaren Stop
  unberuehrt lassen (er schuetzt schon) und ohne Stop-Preis melden statt raten.
  Gegenprobe: `/api/v5/trade/orders-algo-pending` fuer **JEDE** `ordType`
  (`conditional` UND `oco`; je nach Anlageweg liegt der Stop in der einen oder
  anderen Liste) muss fuer JEDE Live-Position eine Verkaufsorder zeigen. Ein
  leeres `conditional` allein ist KEIN Beleg fuer "kein Stop" — und wer darauf
  hin nachsetzt, erzeugt einen Doppelstop (zwei Verkaufsorders auf denselben
  Bestand).
- **Ein gefeuerter Boersen-Stop ist am BESTAND zu erkennen, nicht am Algo-Zustand.**
  OKX laesst die Algo-Antwort nach dem Ausloesen auf `state=effective` und
  `accFillSz=0` stehen (gemessen: der Stop hatte eine echte Market-Sell-Fuellung
  erzeugt, der Algo meldete weiter "wirksam"; auch `cancel-algos` darauf gibt dann
  `51400`, also erledigt). Wer den Algo-Zustand als Wahrheit nimmt, haelt eine
  verkaufte Position fuer geschuetzt und beschriftet den Ausstieg mit dem falschen
  Grund. Reihenfolge: **erst den Bestand der Basiswaehrung lesen**
  (`/account/balance?ccy=<coin>`), ist er auf null -> die Position ist an der Boerse
  weg; dann den echten Ausstiegspreis aus der juengsten gefuellten Order
  (`/trade/orders-history` der Verkaufsseite) holen. Ohne belegten Fuellungspreis
  wird NICHT gebucht — lieber laut melden als einen Kurs erfinden.
- **Ein Buchfeld, das nur beim KAUF gesetzt wird, ist keine Wache.** Ein Merker wie
  `boersen_stop_fehlt` wird beim Eroeffnen geschrieben und danach nie wieder
  geprueft: er behauptet dauerhaft "Stop ist da", waehrend die Position laengst
  ungeschuetzt offen liegt (Stornos von Hand, fehlgeschlagene Wiederanlage nach
  einem abgebrochenen Verkauf, von Hand reduzierte Stueckzahl). Der Stop-Zustand
  gehoert in JEDEN Live-Zyklus, nicht in die Eroeffnung. Fertiges Muster:
  `scanner/boersenstops.py` (liest je Position Bestand + Stop, setzt fehlende
  Stops nach, bucht boersenseitige Ausstiege mit echtem Preis aus; Vorschau ist
  Standard) — Details in `handel-spuren`, Blatt `live-order-und-buchpflege` im Skill `handel-spuren` (Abschnitt 5c).
- **Modul-Attrappen: das Modulattribut patchen, nicht `sys.modules`.** Wird ein
  Helfer ueber den PFAD geladen und als Attribut gehalten, laeuft eine Attrappe, die
  nur `sys.modules["<name>"]` umbiegt, ins Leere — der Test ist dann gruen oder rot
  aus dem falschen Grund. Ebenso: einen Helfer aus dem ELTERN-Ordner (z. B.
  `spiegelstand.py`, das `risikostufe` importiert) per `sys.path.APPEND` einbinden,
  nie per `insert(0, ...)` — sonst verdraengt ein gleichnamiges Modul der Spur
  (`handeln.py` liegt in vielen Ordnern) das richtige.
- **Diagnose-Skripte nicht in den Spur-Ordner legen.** Nach
  `Agenten/Hermes/cache/` schreiben und danach loeschen; der Spur-Ordner ist
  versioniert und wird gespiegelt.
- **Eine Probe oder ein Adapter-Beispiel druckt NIE Schluesselfragmente.**
  Ein `eprintln!("key={}… secret={}…", &key[..8], &secret[..8])` als
  Debug-Zeile schreibt Praxis und Passphrase-Fragment in jedes Log und in jede
  Sitzung — acht Zeichen sind genug, um sie wiederzuerkennen, und der Nutzer
  haelt sie fuer ausgegeben. Beleg dafuer, dass die Zugangsdaten da sind, ist
  ein BOOLEAN (`key gesetzt: true`) oder die Laenge, niemals ein Anfang der
  Zeichenkette. Beim Lesen einer fremden Probe zuerst nach `[..8]`/`[:8]`
  greppen.
- **Die Instrument-Notation steht EINMAL im Code.** OKX kennt drei
  kontraktbasierte Familien an der ID: `-SWAP`, `_XPERP-` und datiert
  `-YYMMDD`. Drei Kopien dieser Regel (Client, CLI, Beispiel) laufen
  auseinander, sobald eine Familie dazukommt — genau so entstand ein
  `BTC-USD-*`-Praefix-Raten im Beispiel, das datierte `BTC-USD_UM-…` nicht
  erkannte. Richtig ist eine Funktion im Exchange-Modul, die Symbol ->
  `Option<InstType>` abbildet (`None` = kein Kontrakt, der Aufrufer
  entscheidet), und alle anderen Schichten delegieren dorthin. Beim Erweitern
  um eine Familie zuerst die bestehenden Kopien suchen
  (`grep -rn "ends_with(\"-SWAP\")"`) und ersetzen, nicht daneben ergaenzen.
- **Ein Sicherungsauftrag ist manchmal die Antwort „nichts“.** Geprueft lag ein
  vollstaendiger OCO (Stop *und* Ziel auf der vollen Menge) — drei zusaetzliche
  TP-Stufen haetten beim ersten Treffer doppelt verkauft, weil ihre Mengen sich
  mit der Zielmenge des OCO ueberschneiden. Vor JEDER Schutz-Order den Zustand
  neu lesen: zwischen Analyse und Order aendern sich Mengen und Stops, und wer
  auf einer Tabelle von vor einer Minute handelt, baut die zweite Schutzebene.
  Messung und Order gehoeren in **einen** Lauf.
- **Ein HANDVERKAUF im Buch, der als Geist gebucht wird, ist der teuerste
  Fall — und er sieht harmlos aus.** Am 05.10.2026 hat Max ueber Nacht vier
  echte Live-Positionen per Hand verkauft (Stops). Das Haus buchte sie als
  `buchbereinigung_geist` mit Erloes 0.00 — ein Geist wird neutral gebucht — und
  die Kapitalkurve zeigte vier Verkaeufe ohne Verlust. Die Boerse fuehrte die
  Ergebnisse die ganze Zeit: STRK `realizedPnl +70,76`, QUANT `−18,47`, SOL
  `+0,96`. Drei belegte Ursachen: (a) `_geist_erloes` liest den Verkaufspreis aus
  `/account/positions-history` und bekommt dort `avgPx: None` — der Preis steht
  nur in `/trade/fills` → `fillPx`; (b) die Geisterpruefung kannte nur „da" oder
  „weg" und keinen TEILVERKAUF (Buch 19.616 → 12.033 → 8.033 → 0, jede Welle als
  `handanpassung` gebucht, nie als Verkauf); (c) `bueche_groessen_abgleichen` lief
  NACH der Geisterpruefung und war bei einer auf null gelaufenen Position
  wirkungslos. **Merksatz: ein im Journal verbuchter Verkaufspreis, der EXAKT dem
  Einstand entspricht, ist kein Verkauf — das ist das Kennzeichen eines
  Geisters.** So findet man die betroffenen Positionen:
  `grep -h ",live," handelsjournal*.csv | grep -v anpassen`. Und die Regel NICHT
  abschalten — sonst bleiben Positionen stehen, die die Boerse schon verkauft
  hat, und die Spur kauft beim naechsten Signal in eine Position, die es nicht
  gibt. Details und die gebaute Bruecke: `references/handverkauf-geist.md`.
- **OKX blockt urllib ohne ausdruecklichen User-Agent mit `403 error code: 1010`.**
  `urllib.request` sendet den Standard-UA `Python-urllib/3.x`, den OKXs
  Cloudflare-Schutz ablehnt — die signierte Anfrage kommt nie an, und der Fehler
  sieht wie ein Schluessel-/Signaturproblem aus. Es genuegt IRGENDEIN
  ausdruecklicher Wert (`User-Agent: Python/3.11` wird angenommen, ein
  Browser-String ebenso); nur der Standard wird abgelehnt. Jeder rohe OKX-Aufruf
  (Probe, Diagnose) setzt den Header deshalb selbst; der Rust-`reqwest`-Client
  sendet von sich aus einen gueltigen UA und ist davon unberuehrt.
- **Antwortform an Max.** Zuerst die Ursache in einem Satz, dann die Belege
  (Zahlen, nicht Adjektive), dann was jetzt anders ist und was absichtlich NICHT
  angefasst wurde (Fremdarbeit im Arbeitsbaum, laufende Prozesse), am Ende genau
  eine naechste Aktion. Keine Optionsliste, keine Rueckfrage nach Erlaubnis fuer
  additive Arbeit.

## Verification

```bash
cd Agenten/Handel/<spur>/tests && ../.venv/Scripts/python.exe -m unittest discover -s . -t .
cd Agenten/Handel && scanner/.venv/Scripts/python.exe spiegelstand.py   # byte-gleich (Q:)
```

Ein Fall ist fertig, wenn der Code an der Aufrufstelle erklaert ist, ein LESEaufruf
die Aussage belegt (Konto/Historie), ein Test den Fall festhaelt und der Spiegel
byte-gleich meldet.
