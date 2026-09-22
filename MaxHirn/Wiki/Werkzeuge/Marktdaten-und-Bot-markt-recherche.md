---
titel: Marktdaten ohne Schluessel und der Bot markt-recherche
aktualisiert: 2026-09-23
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

## Abgrenzung

- Verfahren und Trigger: Skill `markt-recherche`
- Spuren auswerten und deuten: `handel-spur-studie`, [[../Handel/Lektionen.md]]
- Bot-Zugang per Telegram: `/bots` und `/bot NAME` im SkillsBot,
  [../Werkzeuge/Fundus-Skills-Bots.md](Fundus-Skills-Bots.md)
