# Spur 3 — Kraken, Spot, nur Long, in EUR

Angelegt am 02.09.2026, auf Anweisung von Max, als Antwort auf T-027: Bis
dahin war Kraken ausdrücklich **keine** Spur — nicht aus Prinzip, sondern
weil ihm alles fehlte, was die Handelserlaubnis trägt. Dieser Ordner liefert
das Fehlende nach: eine `wachen.json`, ein Skript, das sie liest, ein Journal,
einen Herzschlag.

## Warum das nicht dasselbe ist wie der Kraken-MCP

Beide sprechen mit derselben API und benutzen denselben Schlüssel. Der
Unterschied ist nicht technisch, er ist der ganze Punkt:

| | MCP-Server (`../../MCP-Server/kraken/`) | diese Spur |
|---|---|---|
| Grenzen in einer Datei | nein | `wachen.json` |
| Pflicht-Stop, Kill-Switch | nein | ja, nicht abschaltbar |
| Journal, Herzschlag | nein | `handelsjournal.csv`, `zustand.json` |
| Scharfschalten von Hand | nein | `freigabe.py`, Spur `kraken` |
| **Order erlaubt** | **nein** | ja, wenn alle Sperren offen sind |

Deshalb bleiben `kraken_order_aufgeben` und `kraken_order_stornieren` im
MCP-Server weiterhin verboten (Wissen/Handelsregeln.md). Eine Chat-Sitzung
bringt keine Wachen mit; dieses Skript bringt sie mit.

## Dateien

| Datei | Inhalt |
|---|---|
| `wachen.json` | die Grenzen. Einzige Wahrheit. Wird gelesen, nie geschrieben — außer von `sperre_zu`, und nur von `true` auf `false` |
| `kraken.py` | Anbindung: öffentliche Kurse, signierte Orders. Nur Standardbibliothek, kein eigenes `.venv` |
| `scan.py` | Tagesscan der Watchlist → `berichte/` |
| `handeln.py` | der Zyklus: Ausstiege, Einstiege, Journal, Zustand |
| `wachen_kraken.py` | Bedingungen 1–5. Die währungsneutrale Rechnung kommt aus `../scanner/wachen_pruefung.py` und steht nur dort |
| `handelsjournal.csv` | jede Aktion, mit Gebühr in den Beträgen |
| `zustand.json` | offener Bestand, letzte Stops, letzter Lauf (= Herzschlag) |

Journal und Zustand sind nicht versioniert (Rauschen), aber gesichert.

## Aufruf

```
..\scanner\.venv\Scripts\python.exe scan.py
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau
..\scanner\.venv\Scripts\python.exe handeln.py --papier
..\scanner\.venv\Scripts\python.exe handeln.py --live
..\scanner\.venv\Scripts\python.exe handeln.py --wachen
```

Täglich läuft `../../Routinen/kraken-scanner.ps1` (Scan + Papier), wöchentlich
deckt `../../Routinen/handel-wachen.ps1` diese Spur mit ab.

## Neun Sperren vor der ersten echten Order

Alle müssen offen sein, sonst handelt auch `--live` nur auf Papier — und sagt,
welche zu war:

1. `wachen.json` → `handel_erlaubt: true`
2. `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` gesetzt
3. `--live` ausdrücklich auf der Kommandozeile
4. `freigabe.erfuellt: true` (Bedingung 1: 6 Wochen Papier, ≥ 50 Runden, netto positiv)
5. Herzschlag frisch (Bedingung 3)
6. rollierender Erwartungswert ≥ 0 (Bedingung 5)
7. `journal_zweitziel` gesetzt (Bedingung 4)
8. mindestens `mindest_guthaben_eur` frei auf dem Konto
9. eine Sitzung am Bildschirm für das Freigabefenster

Sperre 7 und 8 hat nur diese Spur. Sperre 8, weil am 02.09.2026 **0,0094 EUR**
frei auf dem Konto lagen — der Rest steckt in Coins. Ein Kauf-Automat ohne
Fiat kauft nichts, er scheitert nur, und die Fehlermeldung sieht aus wie ein
Schlüsselproblem.

## Die Gebühr ist die Hauptzahl dieser Spur

Kraken nimmt bei Volumen unter 10.000 EUR **0,40 % Taker** (Maker 0,25 %),
gemessen an der Staffel am 02.09.2026. Eine Runde aus Markt-Kauf und
Markt-Verkauf kostet also **0,80 %** — bei 50 EUR Einsatz 0,40 EUR. OKX nimmt
0,05 %; Kraken ist das Achtfache.

Drei Grenzen folgen daraus, und sie sind der einzige Unterschied zu Spur 1:

| | Spur 1 (OKX) | Spur 3 (Kraken) |
|---|---|---|
| Mindest-Stopweite | 4 % | **5 %** |
| Mindest-Chance/Risiko | 1,5 | **2,0** |
| Mindest-Score | 60 | **65** |

Die Gebühr steht auch im Papierlauf in den Beträgen: die Kauf-Zeile im Journal
trägt Einsatz **plus** Gebühr, die Verkauf-Zeile den Erlös **nach** Gebühr.
Ein Papierlauf, der sie wegließe, empfähle eine Strategie, die live verliert —
genau der Fehler aus `Wissen/Handelsbots.md`.

## Stand 02.09.2026

- `handel_erlaubt: false`, `freigabe.erfuellt: false` — der Live-Pfad ist noch
  **nie** scharf gelaufen.
- Erster Papierlauf am 02.09.2026: 4 Positionen (XETHZEUR, LINKEUR, SOLEUR,
  XXBTZEUR), 200 EUR gebunden, Rahmen voll.
- Die sechs Wochen aus Bedingung 1 laufen ab diesem Tag.
- `journal_zweitziel` ist seit dem 13.09.2026 gesetzt
  (`Q:\Handel_Journal\kraken`): Journal und Zustand gehen nach jedem Zyklus
  zusätzlich außer Haus (Bedingung 4). Der eigene Zustand trägt
  `journal_zweitziel_ok` / `_info`, `handeln.py --wachen` zeigt beide.

## Stillgelegt seit 03.09.2026

Am 03.09.2026 auf Max' Anweisung abgeschaltet: `stillgelegt: true` in
`wachen.json`. `handeln.py` verweigert seitdem **jeden** Lauf, auch Papier —
die sechs Wochen aus Bedingung 1 laufen damit nicht weiter.

Die Tagesroutine `MaxHirn-Kraken-Spur3` ist **weiterhin aktiv** und läuft jeden
Tag (nachgemessen am 12.09.2026, Aufgabe im Zustand *Ready*, letzter Logeintrag
13:51): erst `scan.py` mit der Rangliste nach `berichte/`, dann
`handeln.py --papier`, das den Lauf verweigert und den Grund ausgibt. So bleibt
die Rangliste als Nachweis erhalten, ohne dass gehandelt wird. Der Dauerlauf
führt die Spur nicht mehr. — Das Feld `_stillgelegt` in `wachen.json` behauptete,
die Aufgabe sei **abgeschaltet**; das war falsch und ist am 12.09.2026
richtiggestellt worden. Gelöscht ist nichts.

Der Grund steht als `_stillgelegt_grund` in `wachen.json` und ist gerechnet,
nicht behauptet: eine Rückrechnung über 720 Tageskerzen und 8 Paare
(03.09.2026), Gebühr 0,80 % je Runde eingerechnet, ergab in **jeder** geprüften
Kombination einen negativen Erwartungswert je Runde — 30 Tage / Stop 8 % =
−1,37 %, 90 Tage / Stop 8 % = −1,97 %, 180 Tage / Stop 15 % = −2,99 %. Der
Hauptposten ist die Kraken-Gebühr, nicht das Signal.

### Was das Abschalten technisch heißt

- `wachen.json` → `stillgelegt: true`. `handeln.py` bricht damit **vor** allem
  anderen ab, in jedem Modus.
- `freigabe.py` liest dasselbe Feld und **sperrt** das Fenster für diese Spur
  (Knopf „Stillgelegt", Hinweis „hier wird nichts freigegeben — weder live noch
  als Papier"), seit 12.09.2026. Ohne dieses Feld wäre die Spur nur zufällig
  Papier, nämlich solange `handel_erlaubt` und `freigabe.erfuellt` false sind.
- Routine deaktiviert, Dauerlauf-Eintrag entfernt. Gelöscht ist nichts.

### Wiederanschalten — zwei Handgriffe, eine Bedingung

1. **`stillgelegt` auf `false`** (Stufe 1: `.bak-JJJJMMTT`, eine Zeile, Diff
   ansehen). Danach ist das Freigabefenster wieder normal bedienbar.
2. **`handeln.py --wachen` ansehen.** Die sechs Wochen und ≥ 50 Runden aus
   Bedingung 1 sind seit dem 03.09.2026 **nicht** gelaufen — sie müssten neu
   aufgebaut werden, und die Rückrechnung sagt vorher, mit welchem Vorzeichen.
3. Erst wenn `freigabe.erfuellt` **und** `handel_erlaubt` von Hand auf true
   stehen (Stufe 1) und die Routine wieder greift, ist die Spur zurück.

Was **nicht** reicht: `handel_erlaubt: true` allein. Das Skript bleibt Papier,
solange Bedingung 1 offen ist, und das Fenster gibt dann Papier frei — es nennt
den Grund.

## Wieder angeschaltet am 12.09.2026

Max' Anweisung „Kraken anschalten". Geändert wurde **eine Zeile** in
`wachen.json`: `stillgelegt` von `true` auf `false` (Sicherung
`wachen.json.bak-20260912-vor-anschalten`, Diff angesehen). Das Freigabefenster
ist damit wieder normal bedienbar, `handeln.py` läuft wieder — als Papier.

Der erste Lauf hat getan, was das Modell vorsieht: der Herzschlag war 13.265
Minuten alt (seit dem 03.09.), also hat der Notausstieg die vier offenen
Papierpositionen vom 02.09.2026 zu aktuellen Kursen geschlossen —
XETHZEUR +2,56, LINKEUR +1,69, SOLEUR +0,74, XXBTZEUR −0,24 EUR, zusammen
**+4,75 EUR** (G/V nach Gebühr). Danach war der Bestand flach.

**Stand unmittelbar danach** (`handeln.py --wachen`):

| Bedingung | Stand |
|---|---|
| 1 Freigabe erfüllt | **false** — 4 Runden, alle Papier, seit 2026-09-12 |
| 2 Rücklauf | 0,44 EUR von Höchststand 4,39 → Faktor 1,00 |
| 3 Herzschlag | frisch (0 min) |
| 4 Journal-Zweitziel | **nicht gesetzt** |
| 5 Rollierender EV | n/a (zu wenig Runden) |
| Guthaben | **0,00 EUR frei, nötig 60,00** |

`handel_erlaubt` und `freigabe.erfuellt` stehen weiter auf **false** — sie
umzulegen wäre eine Behauptung, die die Zahlen nicht hergeben: von den sechs
Wochen und 50 Runden aus Bedingung 1 sind 4 Runden gelaufen, und die sechs
Wochen zählen ab heute. Das ist Max' Entscheidung, sobald die Zahlen stehen.

## Fallen

- **Kraken antwortet unter dem kanonischen Paarnamen**, nicht unter dem
  angefragten: `XBTEUR` kommt als `XXBTZEUR` zurück. `kraken.py` greift
  deshalb nie über den Schlüssel zu.
- **Der Secret ist base64** und muss vor dem HMAC dekodiert werden, sonst
  meldet Kraken „Invalid key" — was wie ein falscher Schlüssel aussieht.
- **Die Nonce muss je Schlüssel streng steigen.** Läuft gleichzeitig der
  MCP-Server mit demselben Schlüssel, kann ein Lauf klemmen. Dann wiederholen,
  nicht den Schlüssel tauschen.
- **Mengen werden abgerundet**, nie auf. `ordermin` und `costmin` des Paares
  entscheiden, ob die Order überhaupt zulässig ist — `menge_fuer()` prüft das,
  bevor Geld fließt.
- **`vol_exec`, nicht `vol`:** eine teilweise gefüllte Kauforder verkauft sonst
  mehr, als sie gekauft hat.

## Festliegende Posten — Ordermin und Sonderformen (01.10.2026, T-280)

Drei Posten liessen sich nicht verkaufen, aus ZWEI Gruenden: PEPE (409.009,94) und
ONDO (10,74331) lagen unter dem `ordermin` ihres Paares (1.500.000 bzw. 15), und
ADA.S/ATOM21.S/HYPE.B/XPEV.EQ haben **überhaupt kein Paar** — Sonderformen
(gestakt bzw. tokenisiert), dort ist Unstaking der Weg, nicht eine Order.

- **Nachsehen statt raten:** `python lagerbestand.py` (Vorgabe: nur festliegende
  Posten; `--alle`, `--json`, `--ohne-kurse`). Es liest `ordermin`/`costmin` aus
  `AssetPairs` und sagt je Posten, was fehlt bzw. dass kein Markt existiert.
- Vor jeder Order gilt weiter `menge_fuer()`: es prüft `ordermin`/`costmin`, damit
  eine zu kleine Order gar nicht erst rausgeht.
- **Barmittel ist kein Befund:** USDC/ZEUR stehen als `quote` im Buch, nicht als
  Basiswert, und werden getrennt geführt — sonst erklärt das Werkzeug sie fälschlich
  als „gestakt“.
- Zahlen, der ganze Bestand und die OKX-Entsprechung (`BETH-USDT`/`OKSOL-USDT`,
  Fehler `51155`) stehen im Wiki: `MaxHirn/Wiki/Handel/Boersen-und-Schluessel.md`.
