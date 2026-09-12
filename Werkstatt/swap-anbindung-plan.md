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
