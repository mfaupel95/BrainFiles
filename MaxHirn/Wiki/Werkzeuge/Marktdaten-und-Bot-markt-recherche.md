---
titel: Marktdaten ohne Schluessel und der Bot markt-recherche
aktualisiert: 2026-09-25
tags: [werkzeug, recherce, krypto, aktien, bots, marktdaten]
---

# Marktdaten ohne Schluessel und der Bot `markt-recherche`

> **Merksatz:** Ein Kurs ohne Quelle und Uhrzeit ist keine Antwort. Das Werkzeug
> unten liefert beides in jeder Zeile — wer Zahlen anderswo herholt, muss das
> selbst nachweisen.

## Wofuer

Aktuelle Krypto- und Aktienfragen belegen, statt aus dem Gedaechtnis zu
antworten: Kurs, Zeitreihe, Schlagzeilen — plus die Auswertung der eigenen
Handelsspuren. Alles rein lesend, kein Schluessel, keine Kosten.

## Das Werkzeug

`Agenten/Werkzeuge/marktdaten.py`, nur Standardbibliothek, gemessen am
22.09.2026:

```
python Agenten/Werkzeuge/marktdaten.py kurs BTC-USDT AAPL "^GDAXI" VUSA.DE XAU=F
python Agenten/Werkzeuge/marktdaten.py kerzen ETH-USD --zeitraum 1mo --intervall 1d
python Agenten/Werkzeuge/marktdaten.py news AAPL --anzahl 5
python Agenten/Werkzeuge/marktdaten.py news --anzahl 10      # Markt- und Krypto-Feeds
python Agenten/Werkzeuge/marktdaten.py selbsttest            # Parser ohne Netz
```

| Frage | Weg | Bemerkung |
|---|---|---|
| Krypto-Kurs (24 h) | OKX `/api/v5/market/ticker` | Hausboerse; `-USDT`/`-USDC`/`-USD` am Symbol entscheidet |
| Aktie, Index, ETF, Rohstoff | Yahoo Chart v8 | Waehrung, Boerse, Vortagesschluss kommen mit; `^GDAXI`, `.DE` fuer Xetra, `XAU=F` |
| Kerzen | dieselbe Yahoo-Schnittstelle | fuer beide Welten (`BTC-USD`) |
| News | RSS der Redaktionen | CoinDesk, Cointelegraph, CryptoSlate, MarketWatch; je Ticker Yahoo (`?s=AAPL`) |

**Grüne Probe (22.09.2026):** `BTC-USDT 86119.40 USDT -0.58% (OKX)`,
`AAPL 339.75 USD +2.54% (Yahoo)`, `^GDAXI 25578.85 EUR +0.70%`,
`VUSA.DE 128.515 EUR`, `XAU=F 823.70 USD`; 14 Tests grün
(`Agenten/Handel/tests/test_marktdaten.py`), Selbsttest ohne Netz grün.

## Der Bot

`Agenten/Hermes/profiles/markt-recherche` — ein Profil **ohne Repo**, angelegt
23.09.2026 mit `hermes profile create markt-recherche --clone-from
hermes-wartung`:

- Arbeitsbereich `terminal.cwd = Agenten\Handel` (dort liegen die
  Marktdaten- und Auswertungswerkzeuge)
- Modell `nous/deepseek-v4-flash-0731` (Flottenstandard), `auth.json` als
  Symlink auf den Root-Store, keine Kanalzugangsdaten (der SkillsBot bedient
  ihn ueber `/bot`)
- Skills zusätzlich: `markt-recherche` (Verfahren), `handel-spur-studie`,
  `scrapling-ernte`, `fundus-zugriff`, `marktbriefing`, `notiz`
- Rolle in der eigenen `SOUL.md`: jede Zahl mit Quelle und Zeit, erst die
  Antwort, dann die Belege, rein lesend, nie eine Order

**Beleg (23.09.2026, Kaltstart 39 s):**

```
hermes -p markt-recherche chat -Q -q "Nenne den aktuellen Kurs von BTC-USDT und
von AAPL, je mit Quelle und Uhrzeit. Nutze dafuer Agenten\Werkzeuge\marktdaten.py."
BTC-USDT: 86.052,40 USDT (-0,72%), Quelle OKX, Stand 22.09.2026 22:16 UTC.
AAPL: 339,75 USD (+2,54%), Quelle Yahoo, Stand 22.09.2026 20:00 UTC (letzter
Schluss, nicht live).
```

Der Bot erkennt dabei selbst, dass der Yahoo-Wert der letzte Schluss ist — die
Unterscheidung live/letzter Schluss gehoert in den Bericht.

## Fallen

- **CoinGecko als Hauptquelle scheitert** (HTTP 429 im Haus, mehrfach gemessen).
  Nutzbar bleiben OKX und Binance; fuer Aktien Yahoo.
- **Indizes ohne Caret loesen nicht auf** (`DAX` → leer, `^GDAXI` richtig);
  `Handel/moondev_daten.py` fuehrt bewusst nur OKX-Themen (Funding, Open
  Interest, Liquidationen).
- **Die Yahoo-Schnittstelle ist nicht offiziell dokumentiert** — faellt sie aus,
  ist das ein Befund und keine stille Luecke.
- **`--anzahl` bei `news` zaehlt die Gesamtzeilen**, nicht je Feed.
- **Kein Orderweg.** Dieses Werkzeug und der Bot sind rein lesend; Order und
  Freigabe laufen ausschliesslich ueber die Freigabekette der Spuren.

## Marktbreite (EMA200) als Reihe

> **Merksatz:** Ein Messpunkt ist keine Richtung. `breite.py --merken` schreibt
> den Wert fort — erst zwei Messungen erlauben "schrumpft" oder "erholt sich".

`Agenten/Werkzeuge/breite.py` (25.09.2026, Auftrag Max "Breite als Reihe") misst
ueber 30 liquide USDT-Paare den Anteil, der ueber seiner **EMA200** liegt:
Tageskerzen, letzte **geschlossene** Kerze, OKX oeffentlich, nur
Standardbibliothek, kein Schluessel.

```
python Agenten/Werkzeuge/breite.py              # messen und zeigen (schreibt nichts)
python Agenten/Werkzeuge/breite.py --merken     # in die Reihe schreiben
python Agenten/Werkzeuge/breite.py --reihe      # Verlauf je Kerzentag
```

Reihe: `Agenten/Werkzeuge/breite-reihe.jsonl` — Laufzeitstand wie die
Handelsjournale, **nicht versioniert**; die Sicherung nach G:/Q: nimmt sie
trotzdem mit.

**Die Reihe fuehrt EINE ZEILE JE KERZENTAG**, nicht je Messung: eine Messung
derselben Kerze **ersetzt** ihre Zeile, die letzte des Tages gewinnt. Vorher
stand hier ein Anbau bei jedem Lauf — sechs Laeufe am 25.09.2026 ergaben sechs
Zeilen mit **demselben** Wert (Kerze 2026-09-23, 100,0 %), und "die letzten 30
Messungen" waren damit **ein Tag**. Genau die Richtungsaussage, fuer die die
Reihe gebaut ist, war so nicht belegbar. Die Tageskerze wechselt **16:00 UTC**;
der Cron um 19:00 Ortszeit (17:00 UTC) liegt richtig danach. `--reihe` rechnet
daraus den Verlauf und nennt die Veraenderung in Punkten je Tag; bei nur einem
Kerzentag sagt es ausdruecklich, dass ein Messpunkt keine Richtung ist.
Tests `Agenten/Werkzeuge/tests/test_breite.py` (10, ohne Netz, biegt die Naht
`REIHE` auf einen Temp-Ordner um und prueft, dass der echte Stand unberuehrt
bleibt).

Wache: `Agenten/Hermes/scripts/breite-wache.py`, Hermes-Cron `breite-wache`
(taeglich 19:00, `no_agent`, Telegram, leere Ausgabe = nichts senden). Sie misst,
haengt an und meldet nur: Stufenwechsel (ok ab 80 % / achtung ab 60 % / warnung),
ein Paar, das **neu** unter seine EMA200 faellt, einen **Rueckgang um 10 Punkte
oder mehr** gegenueber der letzten Meldung, oder eine unvollstaendige Messung.
Tests `Agenten/Hermes/scripts/test_breite_wache.py` (13, ohne Netz) — sie pruefen
die **Regeln** (wann geschwiegen wird), nicht die Tageszahl.

**Der Rueckgang war zuerst nicht gemeldet** (gefunden am 25.09.2026 beim
Nachlesen des eigenen Entwurfs): gemeldet wurden nur Stufenwechsel und neue
Abwaertskreuze — innerhalb der Stufe `ok` war die Wache damit **blind**. Ein
Rueckgang von 100 % auf 81 % haette keine Nachricht erzeugt, obwohl genau das
"die Breite schrumpft" ist. Der Vergleich laeuft gegen den letzten **gemeldeten**
Wert, nicht gegen den letzten Messwert: 3 Punkte am Tag sind nach vier Tagen
EINE Nachricht statt vier. Nach jeder Meldung setzt der Bezug neu auf.

**Erste Messung (25.09.2026, 01:52): 29 von 29 = 100,0 %** — jedes gemessene
Paar ueber seiner EMA200. Das ist eine **spaete Signatur, kein Kaufsignal**: es
gibt keinen Nachzuegler mehr, in den Geld rotieren koennte. Die Fruehwarnzeichen
sind die Paare **knapp** ueber der Linie (APT +0,43 %, OP +1,96 %, SEI +2,46 %,
DOT +3,26 %, ATOM +3,70 %) — sie fallen zuerst.

**Falle (gemessen):** OKX beantwortet `urllib` ohne User-Agent mit **HTTP 403**.
Ohne den Kopf liefern ALLE Paare einen Fehler und die Breite waere "0 von 0 =
0,0 %" — eine glatte Falschaussage. Deshalb nennt jede Ausgabe die **Deckung**
(wie viele von wie vielen gemessen, plus die Namen der nicht messbaren Paare);
`TON-USDT` existiert auf dem EEA-Host nicht (`OKX 51001`).

## Abgrenzung

- Verfahren und Trigger: Skill `markt-recherche`
- Breite als Einzelwert (24-h-Momentum, CoinGecko): `Handel/moondev_marktlage`
  fuehrt `breite` als Teil seines Regimes — das ist eine **andere** Groesse als
  der EMA200-Anteil hier
- Spuren auswerten und deuten: `handel-spur-studie`, [[../Handel/Lektionen.md]]
- Bot-Zugang per Telegram: `/bots` und `/bot NAME` im SkillsBot,
  [../Werkzeuge/Fundus-Skills-Bots.md](Fundus-Skills-Bots.md)
