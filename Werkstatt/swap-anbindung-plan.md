# SWAP anbinden (Papier zuerst)

Stand 11.09.2026. Alles unten ist am Host aus dem Code gelesen, nicht erinnert.

## Befund

- **Kontraktzugang kann SWAP schon.** `xperp/okxf.py:192` `swap_instrument()`
  holt einen Perpetual per instId; `okxf.py:215` leitet einen Namen auf
  `-SWAP` dorthin. Probe am Host: `CHIP-USDT-SWAP` liefert ctVal 100, lotSz 1,
  tickSz 0.00001, lever 20, Kurs 0.04631. `okxf.tickers("SWAP")` gibt 478
  Reihen, `okxf.tickers()` 207 - das SWAP-Universum ist das groessere.
- **Auswertung kann SWAP schon.** `xperp/bot.py:386` erkennt `ist_swap` und
  holt den passenden Ticker (`bot.py:387`); `historie.py:44` `swap_id()` baut
  den SWAP-Namen, `stopwahl.py` und `bot.py trend` nutzen ihn.
- **Die Auswahl kann SWAP nicht.** `okxf.py:184` `instrumente()` ist fest
  `instType=FUTURES`, und `auswahl.py:248` zieht ausschliesslich daraus. Darum
  erreicht kein SWAP-Wert die Rangliste; SWAP ist heute nur ueber einen
  ausdruecklich genannten instId erreichbar.
- **Die Ueberwachung ist instType-blind.** `handeln.py:235` `pruefe_ausstiege`
  rechnet allein aus `zustand.json` (stop/ziel/liq), `handeln.py:266` schliesst
  per instId. Eine SWAP-Position wuerde genauso ueberwacht wie eine XPERP.
- **`okxf.positionen()` (326) und `okxf.offene_orders()` (396) sind
  FUTURES-fest und haben derzeit keinen einzigen Aufrufer** im Handel-, Bus-
  und Testbaum. Wirkung heute: keine. Wirkung spaeter: sobald ein Abgleich
  Konto/Spur gebaut wird, fehlt SWAP darin.
- **Es gibt gar keinen Konto-Abgleich.** Die Spur glaubt ihrem eigenen
  `zustand.json`. Manuell geschlossene oder nicht gefuellte Positionen sieht sie
  nicht. Bestandsrisiko, unabhaengig von SWAP.
- **Sperren:** `handeln.py:543` `sperren_live()` kennt sieben Gruende, keiner
  betrifft SWAP. `dauerlauf.py:361` schreibt im Telegram-Text
  "SWAP bleibt gesperrt." - diese Zeile wird durch die Anbindung falsch und
  gehoert mitgeaendert.

## Korrektur

Ich hatte gesagt, ohne instType-Erweiterung gaebe es fuer SWAP **keine
Stop-Ueberwachung**. Das ist falsch: der Ausstieg liest den eigenen Zustand,
nicht das Konto. Die Aussage ist zurueckgezogen.

## Bauplan - neue Spur `Agenten/Handel/swap/`, xperp bleibt unangetastet

Wiederverwenden statt kopieren: `okxf.py`, `indikatoren.py`, `stopwahl.py` aus
`xperp/` per `sys.path`. Zwei Fassungen derselben Sache sind der Fehler, den
dieser Ordner schon einmal hatte.

1. **Universum** (neu, nur lesend): `swap/kandidaten.py` - SWAP-Reihen holen,
   durch dieselben Tore schicken (`min_umsatz_24h_usd`, `vola_tor_pa`,
   `min_historie_tage`, `familien`) und dieselbe Kandidatenform liefern wie
   `auswahl.py`. Gegenprobe: `xperp/handeln.py --vorschau` daneben halten.
2. **Wachen:** `swap/wachen.json` als Kopie von `xperp/wachen.json`,
   `handel_erlaubt=false`. Keine neuen Grenzen erfinden.
3. **`swap/handeln.py`:** aus xperp uebernehmen, `SPUR="swap"`,
   `pruefe_einstiege`/`pruefe_ausstiege` unveraendert, `sperren_live()` mit
   allen sieben Gruenden und dem Wort "Freigabefenster",
   `freigabefenster.lade("swap")`.
4. **Tests:** `swap/tests/test_swap_papier.py` - Kontraktzugang,
   Kandidatenform, Sperrliste vollstaendig, Order-Pfad per Lambda stillgelegt.
   Ein Test darf `markt_kauf` nie erreichen. `unittest discover` im Spurordner.
5. **Dauerlauf** (Stufe 1, `.bak-JJJJMMTT` vorher): Spur eintragen, Zeile 361
   richtigstellen. Jede neue Ausgabezeile muss allein verstaendlich sein und
   Instrument und Seite selbst nennen.
6. **Journal/Bericht:** `handelsjournal.csv` und
   `tagesbericht.py:120 spur_xperp_positionen()` um die Spur ergaenzen.
7. **Versionieren:** jede neue `.py`/`.json` braucht eine eigene `!`-Zeile in
   `.gitignore` (Whitelist), Gegenprobe `git check-ignore -v <pfad>`.

## Was in Papier nicht passieren kann

`live` bleibt `False`, solange ein Sperrgrund steht. Ohne Sitzung oder offenes
Zeitfenster wird weder `order_limit` noch `markt_schliessen` erreicht; der
Order-Pfad bleibt im Test stillgelegt.

## Offen, vor jedem Live-Gedanken

1. Ob OKX fuer SWAP andere Orderparameter braucht (ccy, Margin-Modus) -
   ungeprueft, wird nicht geraten.
2. Kontraktgroesse: ctVal 100 beim CHIP-SWAP. `kontrakte_aus_nominal()` gegen
   beide Kontraktarten pruefen, sonst 100-facher Positionsfehler.
3. Konto-Abgleich als eigene Aufgabe - erst danach ueber Live nachdenken.
4. Live oeffnet nur Max von Hand am Bildschirmfenster.

## Stand 11.09.2026

- **Schritt 1 gebaut und geprueft:** `swap/kandidaten.py` + `swap/tests/test_kandidaten.py`.
  7 Tests gruen (0,6 s), echter Lauf gegen OKX: 464 lebende USDT-Perpetuals,
  davon 19 der 20 umsatzstaerksten mit Kennzahlen, Tabelle ueber `auswahl.tabelle()`.
- **Schritt 2 gebaut:** `swap/wachen.json` als Kopie von xperp, Werte unveraendert,
  `handel_erlaubt=false`, `_zweck` auf die SWAP-Spur richtiggestellt.
- **Aenderung am Plan, aus Sicherheit:** `swap/handeln.py` wird *papierfest*
  gebaut - kein Live-Zweig, keine Order-Funktion im Modul, per Test belegt.
  Der erste Entwurf (xperp/handeln.py importieren und seine Pfadkonstanten
  umbiegen) war zu gefaehrlich: xperp/handeln.py enthaelt den Live-Order-Pfad
  (`hebel_setzen`, `order_limit`), und ein Fehler in meiner
  modus-Unterscheidung haette eine echte Order erreichen koennen. Der Live-Zweig
  entsteht spaeter bewusst nach xperp-Muster, mit Max am Bildschirm.
- **Offen:** `swap/handeln.py` (Kandidaten -> anlauf -> Papierposition ->
  Ausstiege/Funding/Journal), Tests dafuer, danach erst `dauerlauf.py` (Stufe 1,
  `.bak-JJJJMMTT` vorher).

## Stand 12.09.2026 (weitergebaut, Spur laeuft) 

- **Schritt 3 gebaut:** `swap/handeln.py`, papierfest: okxf-Order-Funktionen
  beim Import stillgelegt (`Papierfehler`), kein `live=True` im Modul,
  `--live` verweigert mit genau einem Grund ohne das Wort Freigabefenster.
  16 Tests dazu, gesamt 23/23 gruen gegen den aktuellen Stand (0,7 s).
- **Hermes hat parallel weitergebaut** (Commit 9828f29): dauerlauf.py
  kennt die Spur als Papierspur (SPUREN, Zeile 121), Tagesbericht und /status
  verdrahtet, Whitelist korrigiert. Sein Zusatz im Code: pruefe_ausstiege
  prueft LIQUIDATION vor dem Stop (im xperp-Original ist der Liq-Zweig tot,
  weil der Stop ihn schluckt - siehe Skill-Notiz). Geprueft: auch ein
  `--live`-Aufruf durch den Dauerlauf bleibt Papier (Modul verweigert).
- **Echte Papierlaeufe beobachtet:** TRX-USDT-SWAP long eroeffnet mit voller
  Journalzeile (19:18/19:22), geschlossen per Herzschlag-Notausstieg (19:53) -
  der Sicherheitspfad hat mit echten Daten funktioniert.
- **Offen:** (1) uncommittet: test_handeln_papier.py (LF-Normalisierung);
  (2) xperp-LiQ-Fix ist eine Stufe-1-Aenderung am Live-Pfad - nur mit Max'
  Einverstaendnis; (3) kontrakte_aus_nominal() gegen SWAP-ctVal pruefen;
  (4) Konto-Abgleich bleibt eigene Aufgabe; (5) Live nur von Hand am
  Bildschirmfenster.

### Erledigt am 12.09.2026 (Max' Einverstaendnis lag vor)

- **(2) umgesetzt:** `xperp/handeln.py` prueft LIQUIDATION vor Stop und Ziel,
  dieselbe Reihenfolge wie swap. Nachweis `xperp/test_ausstieg.py`: 9 Tests,
  Long und Short, inkl. Kurs genau auf der Schwelle; `okxf.markt_schliessen`
  im Test durch einen Werfer ersetzt (der Order-Pfad wird nie erreicht), das
  Journal der Spur ist vor und nach dem Lauf byte-gleich.
- **(3) fuer TRX geprueft:** ctVal 1000 TRX, lotSz 0,01 -> 0,73 Kontrakte sind
  gueltig, `kontrakte_aus_nominal(247,55 USD)` rechnet 0,72. Kein 100-facher
  Fehler. CHIP (ctVal 100) bleibt offen, weil kein Kandidat anstand.
- **Neue Beobachtung, ungeklaert:** im `dauerlauf.log` fehlen zwischen 21:23
  und 21:54 alle Zykluszeilen (Takt 15 min), und das Journal hat zwei
  Eroeffnungen derselben Reihe (19:18:14 / 19:22:56), obwohl
  `pruefe_einstiege` die zweite ueberspringt. Nicht geraten - beobachten.

## Stand 12.09.2026 (Live-Pfad angebunden, Weg A vorbereitet)

- **swap/handeln.py:** Live-Zweig nach xperp-Muster, sieben Sperren (letzte:
  `kein offenes Freigabefenster (Handelsregeln Punkt 3)`), boersenseitiger
  Stop (tp/sl an der Order). Tests: 30/30 gruen. Sicherung:
  `handeln.py.bak-20260912-221103`.
- **kontrakte_aus_nominal() gegen SWAP-ctVal belegt:** CHIP 100 -> 20 Kontrakte
  = 100 USD, BTC 0.01 -> 0.11 = 99 USD, XAU 0.001 -> 29 = 98.6 USD. Kein
  Positionsfehler; die Falle war nur der Instrumenten-Lookup ueber den Basiswert.
- **dauerlauf.py:** Befehle /freigabe_swap, /ja_swap, /nein_swap, /stop_swap
  (Block generalisiert, xperp-Texte unveraendert bis auf entferntes
  `SWAP bleibt gesperrt.`), Kommentare korrigiert. Sicherung:
  `dauerlauf.py.bak-20260912-*`. Handel/tests 24 OK, Bus test_handel_befehle
  8 OK. KEIN Neustart - wirkt beim naechsten regularen Start.
- **Echter --live-Lauf:** `gesperrt durch: wachen.json handel_erlaubt=false;`n  `freigabe.erfuellt=false (Bedingung 1); kein offenes Freigabefenster` -> Papier.
- **Scharf schalten bleibt Max:** wachen.json `handel_erlaubt=true` UND
  Freigabefenster (nach Dauerlauf-Neustart per /ja_swap, sonst per Hand am PC).
- **Uncommittet:** dauerlauf.py, swap/handeln.py, test_handeln_papier.py.
