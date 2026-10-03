---
id: 20261001-guthaben-und-umschichtung
title: 'Handel — Guthaben und Umschichtung'
tags: [handel, boersen, guthaben]
created: 2026-10-01
updated: 2026-10-01
related: ['[[Handel/Boersen-und-Schluessel]]', '[[Handel/Gates-und-Freigabe]]']
summary: 'Wo Kapital liegt, was davon wirklich frei ist, und die drei Gruende, warum ein Posten nicht verkaufbar ist (Ordermin, costmin, gestakte Form, Compliance-Sperre).'
---

# Guthaben und Umschichtung

## Die Frage hinter jeder Sperre

Ein Guthaben-Tor liest die **freie** Waehrung, nicht den Kontowert. Beide Boersen
haben am 01.10.2026 gezeigt, wie weit das auseinanderliegt:

| Boerse | Kontowert | wirklich frei | was es bindet |
|---|---|---|---|
| OKX (EEA) | 1.094,77 USD | 30,84 USDC | 215,99 USD isoEq (XPERP-Margin) + ~500 USDC in drei scanner-Positionen mit Stop |
| Kraken | ~570 EUR (+ XXLM/XXBT/XETH ohne Kursaufloesung) | 53,81 EUR + 25,08 USDC | 4 Positionen der kraken-Spur (200 EUR), 1 Margin-Position SUIEUR |

**Merksatz:** `eqUsd` ist keine Verfuegbarkeit. Bei OKX ist das Feld `availBal`
massgeblich; `eq`/`eqUsd` zaehlen Margin und offene Orders mit.

## Drei Gruende, warum ein Posten nicht verkaufbar ist

Alle drei am 01.10.2026 an echten Posten erlebt — der Verkaufsversuch scheitert
sonst mit einer Kraken-Meldung, die wie ein Rechteproblem aussieht:

1. **Unter dem Ordermin.** `PEPEEUR` verlangt 1.500.000 PEPE, im Konto lagen
   409.009,94 (~1,58 EUR). `ONDOEUR` verlangt 15 ONDO, es lagen 10,74331
   (~4,84 EUR). Beide bleiben liegen, bis mehr zusammenkommt — kein Fehler,
   eine Mengenschwelle.
2. **Gestakte Form ohne eigenes Paar.** `ADA.S` ist gestakte Cardano; Kraken
   fuehrt **kein** `ADA.S/EUR` (`AssetPairs` liefert fuer `base=ADA.S` eine leere
   Liste). Der Verkauf muss ueber Unstaking laufen, nicht ueber eine Order.
   Gleiches Muster: `ATOM21.S`, `HYPE.B`, `XPEV.EQ` — der Punkt im Namen ist das
   Kennzeichen.
3. **Gebunden statt frei.** Bei OKX trugen ETH/SOL/BTC ein `availBal` von 7e-9
   (Rundungsrest) — sie stecken in Margin bzw. unter dem Schutz-Stop des scanner.

**Vor jedem Umschichten pruefen:** Paar existiert (`AssetPairs`, `status=online`),
Menge >= `ordermin`, Wert >= `costmin` (0,45 EUR bei Kraken). Ein `validate`-Lauf
kostet nichts und sagt vorher, ob die Boerse die Order annimmt.

## Der Umschichtungslauf vom 01.10.2026

Auftrag Max („umschichten"): acht ungenutzte Kraken-Kleinbestaende in EUR. Fuenf
davon waren verkaufbar:

| Paar | Menge | Erloes (brutto) |
|---|---|---|
| KASEUR | 1.228,38704 | ~47,87 EUR |
| STGEUR | 221,83731 | ~28,95 EUR |
| JTOEUR | 52,68217 | ~25,64 EUR |
| SYNEUR | 159,218683 | ~22,13 EUR |
| DUALEUR | 4.914,7 | ~12,83 EUR |

**ZEUR 53,81 -> 189,42 EUR** (+135,61 netto; die Differenz zu 137,42 brutto ist
die Taker-Gebuehr). Wirkung sofort messbar: `kraken/handeln.py --vorschau` nennt
das Guthaben-Tor nicht mehr — `EUR 189.42/60.00`.

### OKX, gleicher Auftrag („okx auch")

`USDC availBal 31,50 -> 144,70 USD`. Sechs von acht Posten verkauft:

| Paar | Menge | Wert |
|---|---|---|
| NEIRO-USDC | 272.000 | ~25,12 USD |
| DOGS-USDC | 447.312 | ~21,73 USD |
| EURC-USDC | 15,988 | ~18,07 USD |
| ACE-USDC | 84,2174 | ~15,44 USD |
| WAXP-USDC | 1.266,513357 | ~7,87 USD |
| CHIP-USDC | 100,83 | ~4,33 USD |

**Zwei Posten sind gesperrt** — `OKX 51155: You can't trade this pair … due to
local compliance restrictions`: `BETH-USDT` (160,77 USD) und `OKSOL-USDT`
(20,00 USD). Beides sind **gestakte Formen** (Beacon-ETH, OKX-Staked-SOL), und
OKX fuehrt sie auf dem EEA-Konto **nur gegen USDT** — kein USDC-Paar. Der Fehler
51155 kommt **vor** jeder Mengenpruefung; ein gueltiges Paar und eine Menge ueber
`minSz` genuegen nicht, wenn die Compliance-Region des Kontos das Instrument
ausschliesst. Pruefen laesst sich das nur am Orderweg, nicht an `/public/instruments`.

**Folge, die mitgedacht gehoert:** Das Guthaben-Tor war bei `mosaic` die letzte
Sperre vor dem Freigabefenster. Nach dem Verkauf nannte
`mosaic/handeln.py --vorschau` nur noch „Freigabefenster nicht offen" — und
`mosaic` steht in `dauerlauf.AUTO_FREIGABE`, oeffnet sein Fenster also selbst.

**Eingetreten ist es anders, und das ist die eigentliche Lehre:** Der **scanner**
war schneller. Er laeuft live mit offenem Fenster (bis 16:36) und sah die
144,70 USDC im selben Zyklus — um **10:04:13/10:04:16** kaufte er ZEC-USDC
(65,96 USDC) und SUI-USDC (77,96 USDC), zusammen 143,92. `availBal` USDC stand
danach wieder auf **0,00**, und `mosaic` hatte zwei Sperrgruende statt einem —
`nur_fenster_fehlt()` verlangt genau einen, also wurde gar kein Fenster
geoeffnet. Ein freigemachtes Guthaben ist keine Zuweisung: **wer zuerst liest,
nimmt es.**

`mosaic` hat im ganzen Vorgang **nicht** gehandelt (Journal unveraendert, letzter
Eintrag 05:05:40). Beide neuen Positionen sind echte scanner-Kaeufe und stehen
mit Orderkennung im Journal (`live,kauf,ZEC-USDC`, `live,kauf,SUI-USDC`).

Nicht angefasst: PEPE, ONDO, ADA.S (Gruende 1 und 2 oben).

## Was aus dem freigemachten Guthaben wurde (01.10.2026, 13:25)

Max: „kraken scharf". Die Spur war seit dem 30.09. doppelt gesperrt
(`handel_erlaubt=false`, `freigabe.erfuellt=false`) und dazu durch Bedingung 5
(EV −0,028 EUR auf 6 Handelsrunden). Nach dem Setzen von `freigabe.erfuellt`
sperrte sie sich SOFORT selbst wieder: `sperre_zu()` schreibt `handel_erlaubt`
auf false, sobald Bedingung 5 reisst — der Schalter allein genuegt also nicht.

Max hat Bedingung 5 fuer kraken ausgesetzt. Sie ist **nicht geloescht**, sondern
ueber `bedingung_5_aktiv: false` in der wachen.json abschaltbar; fehlt das Feld,
gilt sie wie bisher. Die Entscheidung steht als `_bedingung_5_entfaellt` mit
Datum und beiden Messungen in derselben Datei.

**Wirkung, gemessen:** `handeln.py --vorschau` meldet um 13:25
`Live waere gesperrt durch: nichts`. Um 13:25:51 stellte die Spur drei Belege
aus (XLTCZEUR, ADAEUR, SOLEUR, je 50 EUR); SOLEUR wurde 13:27:22 ueber die Hand
ausgefuehrt — **0,47998464 SOL @ 104,26 EUR, Stop 97,72 liegt an der Boerse**
(`OpenOrders`, 11 Auftraege). Kraken-Konto: ZEUR 189,42 -> 139,03, SOL
1,0796 -> 1,5596.

### Nebenbefund: der Papierzweig konnte gar nicht kaufen
Beim Nachziehen der Suite fiel ein `UnboundLocalError` in
`pruefe_einstiege`: `gefuellt` und `fuellung_bestaetigt` entstanden nur im
Live-Zweig (eingeschleppt mit der `pos_id`-Paarung, c8cc154 vom 30.09.). Jeder
Papierkauf warf — die Spur lief seit dem 30.09. nur noch live oder gar nicht.
Behoben durch Vorbelegung `(menge, True)`; ein Papierkauf hat keine
Boersenfuellung. kraken-Suite 174 Tests, vorher 8 Fehler, jetzt gruen.

Die zwei Testfehler-Quellen waren beide dieselbe Klasse: eine Attrappe, die
`fuellung_abwarten` nicht kannte (die Funktion kam mit dem T-102-Fix, die
Attrappe nie nachgezogen), und ein Test, der den Stand VOR T-102 einfror
(`..._wird_nicht_gebucht`).

## Die Kraken-Wache und zwei Fallen im eigenen Zugriff (01.10.2026)

`Agenten/Hermes/scripts/kraken-wache.py` (Hermes-Cron `kraken-wache`, alle
30 Minuten, no_agent, leere Ausgabe = nichts senden) meldet nur Neues: Live-Kauf,
Live-Verkauf, `fehler`-Zeile, Live-Position ohne Boersen-Stop, Guthaben-Tor zu,
Stillstand ab 45 min, Belegverfall ab fuenf Belegen ohne Ausfuehrung.

Die erste Fassung meldete **alle vier Positionen als ungeschuetzt** und
**EUR 0,00 frei** — beides falsch. Zwei Fallen im Zugriff auf das eigene Modul:

1. **`kraken.kontostaende()` liefert die KRAKEN-Namen** (`ZEUR`, `XXBT`), nicht
   die lesbaren (`EUR`, `XBT`). Wer `staende["EUR"]` liest, bekommt 0.00 und
   meldet ein geschlossenes Tor, das weit offen ist. Richtig ist die
   Haus-Funktion `handeln.guthaben_lage(w)` — sie loest ueber `quote.lesbar` auf.
2. **`kraken.offene_orders()` gibt FERTIG** `{txid: {paar, seite, art, menge,
   preis}}` zurueck. Ein zweites `.get("open")` darauf findet nichts, und die
   Felder heissen `seite`/`menge`, nicht `type`/`vol`. Beides zusammen meldete
   jeden Schutz-Stop als fehlend.

**Merksatz:** Eine Wache, die den Zugriff selbst nachbaut, prueft ihren
Nachbau, nicht die Spur. Wo eine Haus-Funktion existiert
(`guthaben_lage`, `offene_orders`), wird sie aufgerufen — nicht die Rohform
daneben gestellt. Und ein Fehlalarm ist hier teurer als eine spaete Meldung:
er schickt Max nachts zu einer Position, die die ganze Zeit geschuetzt war.

## Falle im eigenen Aufruf

`markt_verkauf(paar, menge, echt=True)` liefert die Kraken-Antwort — **nicht** das
gewohnte `{result: {txid: [...]}}`-Dict, das `_roh_privat` zurueckgibt. Mein
`r.get('txid')` warf deshalb `'str' object has no attribute 'get'`, **nachdem**
alle fuenf Orders bereits gefuellt waren. Der Fehler sah wie fuenf Fehlschlaege
aus, war aber ein Parser-Fehler im Aufrufer.

**Merksatz:** Nach einem Verkauf nie der Rueckgabe glauben — Kontostand und
`ClosedOrders` sind die Zeugen. Im Zweifel beide vor dem zweiten Versuch lesen,
sonst verkauft man zweimal.