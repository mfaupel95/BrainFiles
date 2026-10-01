# Geld verfolgen: Einzahlung, Umbuchung, Guthaben je Wallet

Wann: "hab eingezahlt", "das Guthaben fehlt", "warum kann die Spur nicht handeln",
"wo ist das Geld hin". Diese Datei ist die Nachweis-Kette und die Leseordnung.

## Grundregel

**Eine Einzahlung wird ueber die BUCHUNGSKETTE nachgewiesen, nicht ueber einen
Saldo.** Ein Kontostand von 0 in einem Wallet beweist nur, dass das Geld nicht
DORT liegt - nicht, dass es nicht angekommen ist. Und "hab eingezahlt" ist eine
Behauptung wie jeder andere gemeldete Zustand: erst die Buchung zeigen, dann die
Lage der Spur beurteilen.

## Reihenfolge (jede Stufe ist ein eigener Messpunkt)

1. **Eingang pruefen** - `DepositStatus` des SPOT-Kontos, je Waehrung. Liefert
   Betrag, Status und einen Epoch-Zeitstempel. Nach Zeit sortieren und das Datum
   per `datetime` umrechnen, nie im Kopf.
2. **Gegenbuchung suchen** - `Ledgers` (PLURAL, siehe Falle unten) fuer dieselbe
   Waehrung. Eine Buchung `type=transfer` mit `refid` heisst: interne Umbuchung,
   das Gegenstueck liegt in einem anderen Wallet. Der Zeitabstand zwischen Ein-
   und Abbuchung ist oft klein (Minuten) - dann ging das Geld nicht in den Handel.
3. **Zielkonto pruefen** - beim Futures-Dienst `/transfers` (Liste ist
   AUFSTEIGEND, siehe Falle) und `/accounts` gegen ALLE Konten und ALLE
   Waehrungsschluessel. Erst wenn dort nichts steht, ist es nicht dort.
4. **Alle Spot-Wallets pruefen** - `BalanceEx` (Einlagen/Bestand), dazu die
   Margin-Seite (`OpenPositions`, `TradeBalance` mit den `mf`-Feldern): eine
   Umbuchung kann auch ins Margin-Wallet gehen.
5. **Erst dann urteilen** und die Kette Schritt fuer Schritt berichten
   (Betrag + Status + Zeitstempel der Einzahlung, Gegenbuchung mit refid und
   Zeitpunkt, was auf der Zielseite steht, was NICHT dort steht), dann EINE
   naechste Handlung nennen.

## Aufrufe

```python
k = _lade("kraken", os.path.join(HANDEL, "kraken", "kraken.py"))
k._roh_privat("DepositStatus", asset="USDC")     # Eingaenge je Waehrung
k._roh_privat("Ledgers", asset="USDC", start=<epoch>)   # PLURAL
k._roh_privat("WithdrawStatus", asset="USDC")    # Gegenrichtung
k._roh_privat("BalanceEx")                       # Spot-Bestand

kf = _lade("kraken_futures", os.path.join(HANDEL, "nautilus_kraken", "kraken_futures.py"))
kf._roh("/transfers")                            # Lesen: post=False
kf._roh("/accounts")                             # alle Konten, alle Waehrungen
```

OKX als Gegenprobe: `/api/v5/account/balance` (signiert) - **`availEq` je
Waehrung ist die Kaufkraft, `eq` ist der Bestand inkl. gebundener Betraege**; ein
voll aussehendes `eq` kann bei `availEq` fast nichts bedeuten.

## Fallen

- **`/0/private/Ledger` gibt HTTP 404** - der Endpunkt heisst `Ledgers`. Ein 404
  liest sich wie "gibt es nicht" und schickt die Suche auf die falsche Spur.
- **Die `/transfers`-Liste des Futures-Dienstes ist AUFSTEIGEND** (aeltester
  Vorgang zuerst): `liste[:6]` zeigt die AELTESTEN und verdeckt genau den frischen
  Transfer. Nach Zeit sortieren oder das Ende nehmen - und die Anzahl der
  Eintraege nennen, nicht nur die Auswahl.
- **Konten nicht nach `usd`/`eur` filtern.** Das Futures-Konto traegt ein Dutzend
  Konten (`cash`, `flex`, `fi_<coin>usd`, Einzelwaehrungskonten) mit je vielen
  Waehrungsschluesseln; nur die Werte ungleich 0 ausgeben, sonst liest man
  "alles 0" aus einer abgeschnittenen Liste.
- **Epoch-Zeitstempel umrechnen, nicht schaetzen.** Eine Kopfrechnung macht aus
  einem alten Vorgang scheinbar einen frischen (oder umgekehrt) - und damit aus
  einem Beleg einen Fehlschluss.
- **Die Boerse kennt Wallets, die ihre Handels-API NICHT zeigt** (Consumer-App-/
  Pay-Guthaben neben dem Handelstopf). Eine Einzahlung kann "Success" sein und in
  KEINEM ueber die API lesbaren Wallet auftauchen. Dann heisst die richtige
  Antwort: Kette nennen, sagen dass es in diesem Login verbucht wurde, und EINEN
  Handgriff in der Boersen-Oberflaeche vorschlagen - nicht "Geld verschwunden".
- **Bei Kraken-Futures liegt das Geld im `flex`-Konto, nicht im `cash`-Konto.**
  Gemessen an einem multiCollateral-Konto: `accounts.cash.balances` steht auf
  0,0, waehrend `accounts.flex.availableMargin` den verfuegbaren Betrag traegt
  (dazu `currencies.<CCY>.available` je Waehrung und `balanceValue` als
  Gesamtwert). Wer nur `cash` liest, meldet 0,0 USD - das sieht wie ein leeres
  Konto aus und ist kein Fehler, der auffaellt: das Guthaben-Tor der Spur bleibt
  still zu, ohne Meldung, ohne Absturz. Erst `flex`, dann `cash` als Rueckfall
  fuer reine Cash-Konten. Ein Coin-Bestand in `fi_<coin>usd` finanziert keine
  Order - die Besicherung haengt an der Waehrung des Verrechnungskontos.
- **Ein Tor, das einen FESTEN Feldnamen liest, kann still 0 messen.** Beim Bau
  eines Guthaben-Tores die ROHE Antwort der Boerse einmal daneben halten und
  pruefen, ob das gelesene Feld gefuellt ist: "0 frei" liest sich wie "kein
  Geld", nicht wie ein Fehler. Gegenprobe nach dem Fix am echten Konto (nicht
  am Testfixture) und in der `--vorschau` der Spur: der Guthaben-Sperrgrund
  muss VERSCHWINDEN, wenn Geld da ist.
- **Spot -> Futures-Wallet bewegen geht NICHT ueber die Futures-API.**
  `/derivatives/api/v3/transfer` nimmt nur `amount`/`fromAccount`/`toAccount`/
  `unit` und lehnt alles ab, was nicht auf der Futures-Seite liegt
  (`invalidAccount` = falscher Account-WERT, nicht falscher Schluessel; von
  `spot` sagt sogar der offizielle Weg: "does not yet support transfers from
  spot"). Der Weg Richtung Futures-Wallet laeuft ueber die SPOT-Seite
  (`Withdraw` mit dem Futures-Wallet als Ziel) und braucht die Withdraw-
  Berechtigung am SPOT-Key - fehlt sie, antwortet `EGeneral:Permission denied`
  und die Bewegung ist eine Portal-Aktion von Max (Boersen-Oberflaeche oder
  Key-Editor), kein API-Retry. Ein Probe-Transfer mit `amount: 1.0` ist
  gefahrlos (er laesst sich sofort zurueckbuchen); erst nach dem Beleg die
  volle Menge senden. Die offizielle kraken-cli liest
  `KRAKEN_FUTURES_API_KEY`/`_SECRET` (Mehrzahl), die Haus-Variablen heissen
  `KRAKEN_FUTURE_*` (Einzahl) - der Wrapper `kraken.ps1` setzt sie, der
  Raw-Aufruf nicht. Das `flex`-Konto nimmt EUR und USDC als Collateral
  (Settlement-Liste); EUR dort zaehlt als USD-Aequivalent im availableMargin.
- **Kein Geld selbst bewegen.** Ein Transfer zwischen Konten ist eine Kontohandlung
  und erst nach ausdruecklichem Ja faellig; bis dahin baut man den Weg (z. B.
  `POST /transfer`) und laesst ihn liegen. Dasselbe gilt fuer Umschichten in eine
  andere Waehrung.
- **Zugangsdaten nur auf EXISTENZ pruefen.** `reg query HKCU\Environment` gibt die
  Werte im Klartext aus (Passphrasen landen im Sitzungsprotokoll) - fuer einen
  Nachweis `[Environment]::GetEnvironmentVariable(name, 'User')` lesen und nur
  Laenge/Anfang nennen. Gilt fuer jeden Zugangsvergleich (OKX, Kraken, MCP).
  **Und einen Hash-Helfer NIE kurz benennen:** `function H { ... }` kollidiert mit
  dem Alias `h` → `Get-History`, die Bindung schlaegt fehl und PowerShell druckt
  die Argumente im Fehlertext aus - der geheime Wert steht dann im Sitzungs-
  protokoll, obwohl die Funktion nur einen Hash liefern sollte. Lange, eindeutige
  Namen (`Sha256Hex`) verwenden und nur `GLEICH`/`ANDERS` bzw. die ersten
  Hexzeichen ausgeben, nie den Wert, aus dem der Hash gebildet wurde.
- **Nebenbefund mitberichten:** verschwindet beim Kontolesen eine Handposition
  samt Schutzauftraegen, ist die Besicherung des Kontos ebenfalls weg - der
  Sperrgrund der Spur kann sich dadurch aendern. Handbuchungen sind von den
  Hausspuren nicht verursacht; sie gehoeren in den Bericht, nicht in eine stille
  Buchkorrektur.
- **Ein Guthaben in der FALSCHEN Waehrung sieht aus wie "genug Geld" und
  haelt das Tor trotzdem zu.** Eine Spur mit `mindest_guthaben_eur` handelt
  ausschliesslich aus dem EUR-Fiat-Topf (`guthaben("ZEUR")`); ein
  Euro-Stablecoin (EURC) oder ein anderer Stablecoin auf dem Konto zaehlt nicht
  dazu - ein ansehnlicher Stablecoin-Bestand laesst den Sperrgrund still bestehen
  ("300+ vorhanden, warum wird nicht gehandelt?" = 298 EURC liegen, gesucht
  sind 60 ZEUR). Vor der Diagnose klaeren, welche WAEHRUNG der Tor-Schluessel
  liest und dass der Konto-Bestand in GENAU dieser Waehrung steht - nicht nur
  "es ist Geld da".
- **Kraken hat eine STILLE Ordergroessen-Grenze je Order: darunter ok, darueber
  `EOrder:Insufficient funds`, trotz freien Guthabens und `hold_trade=0`.**
  Gemessen beim EURC-Verkauf: 10/100/150 gingen durch, 200 und mehr wurden
  abgewiesen, `validate=true` akzeptierte jeden Betrag. Symptom ist eine
  Kontoseite, die "Insufficient funds" sagt, waehrend Balance die Menge frei
  zeigt und keine Reserve erkennbar ist (validate ok, hold_trade 0). Dann in
  TRANCHEN unter der Grenze verkaufen, statt weiter zu experimentieren - und die
  Grenze im Wiki festhalten; das System dokumentiert sie nicht.
- **`kraken.guthaben()` hat keinen `fake`-Parameter** - wer live pruefen will,
  fragt die Balance direkt (`_mit_wiederholung(kraken._roh_privat,
  "Balance")`). Und der MCP-Paarsucher filtert nicht: `kraken_paare_suchen`
  liefert immer dieselbe ungefilterte Liste, die API-Abfrage
  (`_roh_oeffentlich("AssetPairs", pair=...)`) ist der zuverlaessige Weg.
- **Ein ansehnlicher Stablecoin-Vorrat + nur wenige quotierte Paare = kein
  Umbau der Spur auf den Stablecoin.** "Auf X umstellen" heisst die Watchlist
  auf die wenigen Paare reduzieren, die der Stablecoin quotiert - ein massiver
  Strategieeingriff, kein kleiner Umbau. Praktische Loesung bleibt der Tausch
  in die Handelswaehrung (die Spur unveraendert lassen).

## Was ein brauchbarer Bericht enthaelt

Gemessene Kette in Schritten (je Schritt Betrag/Zeitpunkt), wo es NICHT ist, wo
es laut Buchung hin ging, was das fuer die Spur bedeutet (Sperrgrund, weiter
Papier) - und genau eine naechste Handlung unter zwei Minuten.
