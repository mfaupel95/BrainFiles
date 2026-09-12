# Spiegel-Spur — Papierbuch für Copy-Trading

**Sie kopiert nichts. Sie kauft nichts. Sie rechnet nach, was Nachahmen
gekostet hätte.** Angelegt am 12.09.2026 nach `Werkstatt/fomo-copy-trading-plan.md`
auf Max' „Ja zum Papierweg".

## Anlass

Die vorgelegte Anleitung wollte einen Telegram-Bot die Wallet erzeugen lassen,
Guthaben dorthin überweisen und fremde Trader spiegeln. Wer die Adresse
erzeugt, hat den Schlüssel — das verstößt gegen die Hausregel, dass Zugangswerte
in eigenen Händen liegen, und gegen Punkt 3 der Handelsregeln. Diese Spur
beantwortet dieselbe Frage mit eigenen Mitteln: Was bringt das Nachahmen,
nachdem Slippage, Gebühr und Fehlschläge bezahlt sind?

## Aufrufe

Kein eigenes `.venv` — die Spur läuft mit dem des Marktscanners
(`..\scanner\.venv\Scripts\python.exe`, nur Standardbibliothek).

```powershell
cd Agenten\Handel\spiegel

# Grenzen ansehen
..\scanner\.venv\Scripts\python.exe spiegel.py --wachen

# Verfolgungsliste aus dem Feed neu bauen (schreibt nur verfolgte.json)
..\scanner\.venv\Scripts\python.exe spiegel.py --waehlen

# Was wäre dran - nichts wird geschrieben
..\scanner\.venv\Scripts\python.exe spiegel.py --vorschau

# Ein Papierzyklus mit Journal
..\scanner\.venv\Scripts\python.exe spiegel.py --papier

# Welche Wallets haben getragen, welche gemessenen Zahlen lügen
..\scanner\.venv\Scripts\python.exe spiegel.py --bilanz

# verweigert mit einem Grund, bucht Papier
..\scanner\.venv\Scripts\python.exe spiegel.py --live

# Tests
..\scanner\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Woher die Signale kommen

Über das OnchainOS-CLI (`lesen.py`, nur lesende Unterbefehle):

| Quelle | Befehl | Was es liefert |
|---|---|---|
| Live-Feed | `tracker activities` (smart_money, kol) | echte Käufe der gelabelten Wallets, je Kette |
| Messung | `leaderboard list` | PnL, Trefferquote, Handelszahl je Wallet |
| Kurs | `market prices` | Stapelabfrage für offene Kopien |
| Risiko | `security token-scan` | Honeypot, Mint-Rechte, Scheinliquidität |

**Die Auswahl ist der Feed, nicht die Rangliste.** Wer nur die Gewinner einer
Rangliste kopiert, betreibt Zuchtauswahl nach dem Ergebnis. Die Ranglistenzahlen
werden mitgeschrieben — ob sie die *Kopierbarkeit* vorhersagen, ist eine offene
Frage und keine Annahme. `--bilanz` stellt sie später gegen das Ergebnis.

## Kosten, ehrlich gerechnet

`wachen.json` führt Slippage und Gebühr; sie wirken **zweimal** — beim Kauf
teurer, beim Verkauf billiger. Dazu der Test
`test_eine_kopie_ohne_kursbewegung_verliert_geld`: Wer kauft und sofort
verkauft, ist im Minus. Das ist die Zahl, die Nachahmer in der Wirklichkeit
bezahlen und die in jeder Anleitung fehlt.

## Grenzen (Auszug aus `wachen.json`)

| Grenze | Wert | Warum |
|---|---|---|
| je Kopie | 50 USD | die Spur soll eine Frage beantworten, kein Kapital bewegen |
| offen / je Token | 20 / 2 | ein einzelner Token darf das Buch nicht prägen |
| Kill-Switch | 100 USD | Rücklauf, dann alles flach |
| Slippage / Gebühr | 3 % / 1 % | Annahme für dünne Bücher plus Vorlauf |
| Stop / Ziel / Frist | −25 % / +60 % / 24 h | eigene Mathematik, kein Auto-Exit nach Vorbild |
| Signalalter | 300 s | Hinterherlaufen ist kein Nachahmen |
| Marktkapitalisierung | 50.000 – 20 Mio USD | keine Kleinstbetrugs-Bücher, keine ausgewachsenen Werte |
| Risikostufen | safe, LOW | Honeypot und Mint-Rechte fliegen raus |

## Kein Orderpfad

`lesen.ruf()` weist jeden Schreib-Unterbefehl ab, **bevor** ein Prozess startet
(`Schreibversuch`); `spiegel.py` ruft das CLI gar nicht selbst, sondern nur über
`lesen.py` (per Test belegt: der Modulquelltext enthält weder `subprocess` noch
`onchainos`). `--live` verweigert mit genau einem Grund ohne das Wort
*Freigabefenster* — dieselbe Schnittstelle, an der `dauerlauf.nur_fenster_fehlt`
entscheidet, ob überhaupt gefragt wird.

## Erste Messung (12.09.2026, echte Abfragen)

- Ketten mit Daten: Solana, Base, Ethereum, BNB, X Layer. Robinhood antwortet
  auf die Rangliste mit einem Fehler und bleibt draußen.
- **305 Wallets** im Feed, davon nur **13 in einer Rangliste** — die gelabelten
  Wallets sind größtenteils nicht die gemessenen Top-Trader.
- Erster Zyklus: 773 Signale, 10 Kopien (Zyklusdeckel). Der häufigste
  Ablehnungsgrund war die Marktkapitalisierung **unter** 50.000 USD — die
  frischen Käufe im Feed sind fast alle Kleinstwerte, also genau die Zone, in
  der Rug Pulls sitzen.

## Offen

1. Kein Konto-Abgleich: Das Buch glaubt sich selbst (bekannt aus der
   SWAP-Arbeit).
2. Die Slippage-Annahme (3 %) ist gesetzt, nicht gemessen. Vor jedem
   Live-Gedanken gegen echte Bucheindrücke prüfen.
3. Der Live-Pfad fehlt bewusst. Es gibt keinen Schalter, nur Papier.
4. Echtzeit: Der Feed wird im Takt abgefragt (`dauerlauf.py`), nicht über
   `onchainos ws`. Für Millisekunden-Nachahmen wäre ein WebSocket nötig — und
   das wäre ein anderer Plan, nicht dieser.
