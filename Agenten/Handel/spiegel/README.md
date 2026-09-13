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

# Was das BUCH getragen hat: Bilanz vor/nach Kosten, nach Kette, Grund und Tiefe
..\scanner\.venv\Scripts\python.exe auswertung.py

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

## Kosten gemessen, nicht geschätzt (12.09.2026)

`spiegel.py --messen` hält die zwei Kostenposten gegen echte Marktdaten — 15
frische Signale, 50 USD Einsatz:

| Posten | Schnitt | Median | größter |
|---|---|---|---|
| **Tiefe** (Pool-Effekt bei 50 USD) | 0,73 % | 0,20 % | 3,59 % (2.789 USD Liquidität) |
| **Nachlauf** (Kurs jetzt gegen den Kurs des Vorbilds, 6–61 s später) | +2,77 % | 0,00 % | +34,59 % |

**Befund:** Der Nachlauf ist der größere Posten, nicht die Tiefe. Bei normaler
Tiefe zahlt man für 50 USD praktisch nichts (0,2 %), aber bis der eigene Kauf
draußen ist, ist der Kurs im Schnitt fast 3 % weg — bei einem laufenden Pump
auch 35 %. Zusammen mit 1 % Gebühr ergibt das rund **4 % Startnachteil**, also
genau die **3 % + 1 %** aus `wachen.json`. Die Annahme trägt damit nicht, weil
sie streng ist, sondern weil sie gemessen passt.

Zwei Einschränkungen, ehrlich: Die Tiefe ist eine **untere** Grenze
(Constant-Product-Näherung; konzentrierte Liquidität, Spread und
Prioritätsgebühren stecken nicht darin), und der Nachlauf ist eine
**Momentaufnahme**; er schwankt mit dem Markt und muss gelegentlich neu
gemessen werden.

## Was das Buch getragen hat (13.09.2026, 45 Ausstiege)

`auswertung.py` liest das Journal und rechnet die Bilanz **vor** und **nach**
Kosten (die Netto-Rendite ist über die Kostensätze zurückrechenbar, nichts
geschätzt). Momentaufnahme, weil der Lauf weiterschreibt:

| | Wert |
|---|---|
| Ausstiege | 45 (18 über Ziel, 27 über Stop) |
| Ergebnis | +518 USD auf 2.250 USD Einsatz (+23,0 % je Position) |
| davon Kosten | 224 USD |
| **Median je Position** | **−30,8 %** |
| Treffer (Wert > Einsatz) | 19 von 45 (42 %) |
| bester / schlechtester | +505 % / −58 % |

**Der Befund ist der Widerspruch zwischen Mittelwert und Median.** Der
Durchschnitt ist positiv, aber die *typische* Kopie verliert 30 %. Das Buch
trägt an wenigen Ausreißern (+505 %, +110 % über Ziel) und verliert breit über
den Stop. Wer nur den Mittelwert liest, hält das für eine tragfähige Strategie;
bei 45 Kopien ist das noch keine Antwort, aber die Verteilung ist schief, und
das gehört neben die Zahl.

Der zweite Befund: **Die Kosten fressen fast die Hälfte des Bruttogewinns**
(224 von 714 USD). 3 % + 1 % je Seite sind bei einem Buch, das im Schnitt
+33 % vor Kosten macht, kein Rauschen.

### Abgrenzung zu `--bilanz`

`spiegel.py --bilanz` zerlegt nach **Herkunft** (welche Wallet hat getragen),
`auswertung.py` nach **Ergebnis** (trägt das Nachahmen, und in welcher Tiefe).
Beides ist nötig; die Mechanik teilen sie über `Handel/buchauswertung.py`, damit
es keine zweite Formel für dieselbe Frage gibt. Die Bilanz steht auch als Zeile
im Tagesbericht (`Auswertung: …`) — sie kommt aus derselben Quelle.

## Offen

1. Kein Konto-Abgleich: Das Buch glaubt sich selbst (bekannt aus der
   SWAP-Arbeit).
2. Die Slippage-Annahme ist am 12.09.2026 gemessen worden und trug (siehe
   oben). Sie ist eine Annahme auf einer Stichprobe von 15 — vor jedem
   Live-Gedanken neu messen.
3. Der Live-Pfad fehlt bewusst. Es gibt keinen Schalter, nur Papier.
4. Echtzeit: Der Feed wird im Takt abgefragt (`dauerlauf.py`), nicht über
   `onchainos ws`. Für Millisekunden-Nachahmen wäre ein WebSocket nötig — und
   das wäre ein anderer Plan, nicht dieser.
