---
name: markt-recherche
description: "Use when Krypto-/Aktien-Zahlen belegt werden muessen."
category: brainfiles
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [markt, recherche, krypto, aktien, belege, brainfiles]
    related_skills: [handel-spuren, handelsspur-studie, scrapling-ernte, fundus-zugriff]
---

# Marktrecherche: Krypto und Aktien belegen statt behaupten

Eine Recherche zu Krypto oder Aktien ist erst fertig, wenn **jede Zahl eine
Quelle und einen Zeitstempel** traegt. Dafuer gibt es hier ein Werkzeug; es
ersetzt das Raten und das Abschreiben aus dem Gedaechtnis.

## When to Use (Wann)

- "wie steht Bitcoin / eine Aktie gerade", "was ist heute im Markt los"
- eine Behauptung aus einer Notiz oder einem Chat soll gegengeprueft werden
- eine eigene Handelsspur soll ausgewertet werden (Abschnitt "Auswertung")
- Katalysatoren (News, Zahlen, Termine) fuer eine Entscheidung sammeln

**Nicht dafuer:** eine Order ausloesen (das ist die Freigabekette der Spuren),
Anlageberatung, oder eine Spur live schalten.

## Werkzeug (kein Schluessel, keine Kosten)

`Agenten/Werkzeuge/marktdaten.py`, nur Standardbibliothek, gemessen 22.09.2026:

    python marktdaten.py kurs BTC-USDT AAPL "^GDAXI" VUSA.DE XAU=F
    python marktdaten.py kerzen ETH-USD --zeitraum 1mo --intervall 1d
    python marktdaten.py news AAPL --anzahl 5
    python marktdaten.py news --anzahl 10          # Markt- und Krypto-Feeds
    python marktdaten.py selbsttest                # Parser ohne Netz

Dazu die **Marktbreite** — der Anteil der Top-Paare ueber ihrer **EMA200**
(Tageskerzen, letzte geschlossene Kerze). Ein Messpunkt ist keine Richtung:
`--merken` schreibt die Reihe fort, `--reihe` zeigt den Verlauf. Wer eine
Richtung behauptet ("die Breite schrumpft"), braucht mindestens zwei Messungen.

    python Agenten/Werkzeuge/breite.py              # messen und zeigen
    python Agenten/Werkzeuge/breite.py --merken     # an die Reihe anhaengen
    python Agenten/Werkzeuge/breite.py --reihe      # Verlauf

Die Wache dazu (`Agenten/Hermes/scripts/breite-wache.py`, Cron `breite-wache`,
taeglich 19:00) meldet nur Aenderungen — Stufenwechsel, ein Paar, das neu unter
seine EMA200 faellt, eine unvollstaendige Messung. Details und Fallen:
[[Marktdaten-und-Bot-markt-recherche]]

Aus dem Arbeitsbereich `Agenten\Handel` heraus (dort steht der Bot) heisst
derselbe Aufruf `python ..\Werkzeuge\marktdaten.py kurs ...` - der Pfad ist
relativ zur Repo-Wurzel angegeben.

Quellen und ihre Grenzen:

| Frage | Weg | Bemerkung |
|---|---|---|
| Krypto-Kurs (24 h) | OKX `/api/v5/market/ticker` | Hausboerse; `-USDT`/`-USDC`/`-USD` am Symbol |
| Aktie, Index, ETF, Rohstoff | Yahoo Chart v8 (`meta`) | Waehrung, Boerse und Vortagesschluss kommen mit; Xetra `.DE`, DAX `^GDAXI`, Gold `XAU=F` |
| Kerzen | dieselbe Yahoo-Schnittstelle | fuer beide Welten (`BTC-USD`); `--zeitraum`/`--intervall` |
| News | RSS der Redaktionen | CoinDesk, Cointelegraph, CryptoSlate, MarketWatch; je Ticker Yahoo-Headline-Feed (`?s=AAPL`) |
| Orderbuch, Funding, Open Interest | `Handel/moondev_daten.py` (OKX oeffentlich) | fuehrt das Werkzeug bewusst nicht |

**CoinGecko nicht als Hauptquelle:** antwortet im Haus regelmaessig mit HTTP 429
(Rate Limit) - nur als Notnagel. Wer 429 sieht, hat keine Marktlage gemessen,
sondern eine Grenze erreicht.

Krypto-Kurse immer mit dem Paar nennen (`BTC-USDT`), nicht mit dem Symbol allein:
ohne Paar ist "der Kurs" nicht bestimmt.

## Ablauf einer Recherche

1. **Frage in einen Satz schneiden.** Welche Entscheidung braucht die Zahlen?
   Danach die Symbole waehlen - nicht alles abfragen.
2. **Zahlen holen** (`kurs`, `kerzen`) - Quelle und Zeit stehen in jeder Zeile.
3. **Katalysatoren holen** (`news`, RSS): Titel und Zeit, nicht die Deutung. Die
   Deutung gehoert in den Bericht, ausdruecklich als eigene Zeile.
4. **Gegenprobe bei zwei Quellen.** Krypto: OKX gegen Binance
   (`api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT`). Passt der Kurs nicht,
   erst Paar-Zuordnung und Zeit pruefen, dann berichten.
5. **Ausgeben: erst die Antwort, dann die Belege.** Telegram-tauglich, je Zeile
   eine Zahl mit Quelle und Zeit, keine Tabelle, kein Fliesstext.

## Auswertung eigener Daten

"Auswertung" meint die eigenen Spuren, nicht den Markt. Reihenfolge nach Aufwand:

    python Handel/spuren_stand.py                   # Tabelle aller Spuren (lesend)
    python Handel/auswertung_alle.py                # Runden, Trefferquote, G/V je Spur
    python Handel/auswertung_alle.py --risiko mittel
    python Handel/kosten_wendepunkt.py              # f_max je Buch (Gebuehr je Runde)
    python Handel/prognose.py                       # marktweite Einstiege (keine Spur)

Dort gelten: Kennzahlen auf **echten Runden** (Zwangsschluesse stehen getrennt,
`Handel/stoerungen.py`), unter 8 Runden ist ein Wert ein Befund und keine
Messung, und nichts ist aus `zustand.json` abzuleiten - die Boerse ist der
zweite Zeuge (`/account/positions`, Balance).

## Belegpflicht

- Eine Zahl ohne Quelle und Zeit ist ein Fehler, keine Antwort.
- Kurse sind Momentaufnahmen: Zeit IMMER mitnennen, sonst ist der Bericht nach
  einer Stunde falsch und niemand merkt es.
- Fehlt eine Quelle (Netz, 429, Symbol unbekannt), das **sagen** - nicht die
  Luecke mit einer plausiblen Zahl fuellen.
- Symbole, die nicht aufloesen, namentlich nennen (`DAI` hat auf OKX kein
  Spot-Paar).

## Fallen

- **OKX blockt `urllib` ohne User-Agent mit HTTP 403.** Ein eigenes Skript, das
  den Kopf nicht mitgibt, bekommt fuer JEDES Paar einen Fehler — und "0 von 0
  Paaren" waere eine glatte Falschaussage. Deshalb gehoert die **Deckung** neben
  jede Zahl (wie viele von wie vielen gemessen, welche nicht messbar sind).
- **`DAX` ist kein Yahoo-Symbol.** Indizes brauchen das Caret (`^GDAXI`), ETF
  und Auslandswerte die Endung (`.DE`), Rohstoffe die Futures-Form (`XAU=F`).
  Ein leerer Kurs heisst meist falsches Symbol, nicht fehlende Daten.
- **Yahoo liefert `regularMarketPrice` auch ausserhalb der Handelszeit** - das
  ist der letzte Schluss, kein Live-Kurs. Die Uhrzeit in der Ausgabe lesen.
- **`--anzahl` bei `news` ist die Gesamtzahl der Zeilen**, nicht je Feed.
- **Die Yahoo-Schnittstelle ist nicht offiziell dokumentiert.** Sie traegt hier
  seit dem 22.09.2026; faellt sie aus, ist OKX/Binance fuer Krypto der Ersatz und
  fuer Aktien eine andere oeffentliche Quelle - nicht raten, melden.
- **Keine Order auf diesem Weg.** Werkzeug und Skill sind rein lesend.

## Abgrenzung

- Handelsregeln, Freigabe, Papier/Live: `Handel/AGENTS.md`, `Wissen/Handelsregeln.md`
- Spuren auswerten und deuten: `handel-spur-studie` (im Bot vorhanden) und
  die Betriebsdoku `handel-spuren` im Hauptbaum
- Webseiten ernten, wenn RSS nicht reicht: `scrapling-ernte`, `wiki-pflege`
- Fundus fremder Faehigkeiten: `fundus-zugriff`
