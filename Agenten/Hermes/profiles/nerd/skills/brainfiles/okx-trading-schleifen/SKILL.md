---
name: okx-trading-schleifen
description: "Use when OKX-/Handels-Schleifen als Routine gebaut werden."
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [OKX, Handel, Routinen, Cron, Bericht, Waechter]
    related_skills: [skill-schleifen, handel-spuren, bus-integration, brainfiles-auftrag]
---

# OKX-/Handels-Schleifen: Bericht, Wache, Skill-Nutzung

Baut aus den lesenden OKX-Kanaelen und den Handels-Spuren drei no_agent-Crons:
**taeglicher Markt-/Spuren-Bericht**, **Gesundheit-Wache** (still bei Erfolg)
und **Skill-Nutzung nur fuer okx-*/handel-***. Rein lesend, ohne Schluessel.

Es baut KEINE Fachlogik nach: Spurenkennzahlen kommen aus
`auswertung_alle.kennzahlen_fuer`, nie aus einer eigenen Formel. Und es
**aendert nie Parameter** — Vorschlaege zeigen nur an, WO eine Pruefung
(`handel-spur-optimierung`) lohnt (Schutzstufe 1, aus einem Zeitplan wird nie
eingegriffen). Abstrakter Rahmen: `skill-schleifen`; dieses Skill ist die
konkrete OKX-/Handels-Ausfuehrung.

## When to Use

- „OKX und Trading-Skills als Routine“, „Marktbericht taeglich“, „OKX-Wache“
- ein taeglicher Blick auf DEX-Top-Volumen + Spurenkennzahlen fehlt
- niemand merkt, wenn die lesenden OKX-Kanaele (REST, onchainos-CLI) ausfallen
- Skill-Nutzung nur fuer die okx-*/handel-* Gruppe statt aller Skills

## Prerequisites

- **onchainos-CLI** (okx-dex-market): `C:\Users\faupe\.local\bin\onchainos.exe`
  (im PATH als `onchainos`). Read-only ohne Anmeldung, kein Schluessel.
- **OKX-REST** oeffentlich: `https://www.okx.com/api/v5/...` — kein Schluessel.
- **auswertung_alle** unter `Agenten/Handel/` (reine Stdlib, per `sys.path`
  importierbar; braucht `stoerungen`, `risikostufe`, `zeitfenster` im selben
  Ordner).
- **Cron-Zustellung**: aus der TUI kommt `deliver='origin'` nirgends an —
  `deliver='telegram'` setzen.

## How to Run

Drei Skripte unter `Agenten/Hermes/scripts/`, je ein Cron:

```bash
python Agenten/Hermes/scripts/okx-trading-bericht.py          # taeglich 07:45
python Agenten/Hermes/scripts/okx-gesundheit.py --alles        # alle 30 Min, still
python Agenten/Hermes/scripts/okx-skill-nutzung.py            # montags 09:35
```

## Quick Reference

onchainos-CLI (read-only, JSON mit `ok:true`):

```bash
onchainos memepump tokens --chain solana
onchainos leaderboard list --chain solana --time-frame 3 --sort-by 4
```

OKX-REST (oeffentlich):

```
https://www.okx.com/api/v5/market/tickers?instType=SPOT
https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT
https://www.okx.com/api/v5/public/time
```

Cron anlegen (ueber das `cronjob`-Tool):

```
cronjob action=create no_agent=true script=<name>.py \
  schedule="45 7 * * *" deliver='telegram' failure_deliver='telegram'
```

## Procedure

1. **Datenwege pruefen** (ohne Schluessel): `onchainos memepump tokens
   --chain solana` und `curl -s .../api/v5/market/ticker?instId=BTC-USDT`
   muessen JSON liefern. Faellt einer aus, den Bericht darauf einstellen.
2. **Bericht bauen** (`okx-trading-bericht.py`): drei Teile — DEX-Top-Volumen
   (memepump, Top-5 nach `volumeUsd1h`), Leaderboard (Top-3 nach `txVolume`),
   BTC/ETH/SOL-Kurse (OKX-REST, `instId` in BTC-USDT/ETH-USDT/SOL-USDT).
   Spurenteil: `auswertung_alle.kennzahlen_fuer(spur)` fuer jede Spur.
3. **Vorschlaege nur bei belastbarem Buch**: `ausw.belastbar(k)`
   (MIN_RUNDEN=8) VOR dem Vorschlag pruefen — 1-3 Runden sind Rauschen, kein
   Fehlalarm. Schwelle: `pct < 0` ODER `treffer_pct < 45`.
4. **Wache bauen** (`okx-gesundheit.py`): prueft `public/time` (REST) und
   `memepump tokens` (CLI). **Leere Ausgabe = gesund** (Watchdog-Muster).
   Kein Schluessel, kein Guthaben/Wallet (Zugaenge.md ist die einzige Ablage).
5. **Fehlerrichtung herstellbar**: `--onchainos-json`/`--ticker-json`
   (Bericht) und `--cli`/`--api-url` (Wache) ersetzen die echten Quellen.
6. **Prueffunktion von Meldung trennen**: `bericht(...)`/`pruefen(...)`
   geben Listen zurueck und sind importierbar; `main()` druckt nur.
7. **Beide Richtungen fahren**: gesund (Zahlen) + praepariert (tote Datei/
   tote URL) — der praeparierte Lauf muss genau die erwarteten Zeilen zeigen.
8. **Crons anlegen** (`cronjob action=create`, `no_agent=true`,
   `deliver='telegram'`). Fuer einen gefilterten Aufruf einen Wrapper anlegen
   (siehe Pitfalls: `script` nimmt keine Argumente).
9. **Einmal echt feuern** (`cronjob action='run'`) und nachlesen
   (`action='list'`: `last_run_at`, `last_status`; Datei in
   `Agenten/Hermes/cron/output/<job-id>/`). Echter Lauf muss = Handlauf sein.
10. **Dokumentieren + sichern**: Zeile in `MaxHirn/Wissen/Routinen.md`
    (byte-genau, CRLF), `.gitignore`-Gegenprobe `git check-ignore -v <pfad>`,
    Commit nur eigene Pfade (`brainfiles-auftrag`).

## Pitfalls

- **OKX-REST antwortet urllib mit 403, curl nicht.** Ohne `User-Agent`-Header
  lehnt `api/v5/*` ab. Immer
  `urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ..."})`.
- **`script` im Cron nimmt KEINE Argumente.** `script: "x.py --nur okx"`
  scheitert mit "Script file not found". Wrapper anlegen, der `sys.argv`
  setzt und das Ziel per `importlib.util.spec_from_file_location` laedt
  (Dateinamen mit Bindestrich sind nicht importierbar).
- **`instId`-Filter im Tickers-Endpunkt greift nicht** — `tickers?instType=SPOT`
  liefert ALLE Paare. Fuer einen Kurs den Einzel-Endpunkt
  `market/ticker?instId=BTC-USDT` nutzen, oder im Batch nach `instId` filtern.
- **Vorschlaege sind keine Aenderung.** Der Bericht sagt nur, WO eine
  Parameterpruefung lohnt; anpassen bleibt Freigabe ueber
  `handel-spur-optimierung`. Nie aus einem Zeitplan in wachen.json eingreifen.
- **1-3 Runden sind kein Befund.** `belastbar()` (MIN_RUNDEN=8) vor jedem
  Vorschlag — sonst erzeugt jede neue Spur einen Fehlalarm.
- **Wache schweigt bei Erfolg.** Leere Ausgabe = nichts senden. Eine Meldung,
  die jeden Lauf kommt, wird nach einer Woche ignoriert.
- **`curator usage` zaehlt `act` und `use` getrennt** — ein Skill kann in
  beiden Listen stehen (act=1, use=0). Kein Fehler, nur zwei Sichten.
- **onchainos-Aufrufe dauern 15-45 s** — Zeitgrenze grosszuegig setzen
  (Bericht ~120 s, Wache ~30 s).

## Verification

```bash
python Agenten/Hermes/scripts/okx-trading-bericht.py --nur-spuren   # Spurenkennzahlen, exit 0
python Agenten/Hermes/scripts/okx-gesundheit.py --cli C:/tote/cli.exe  # genau 1 Befund
```

Dann `cronjob action='list'`: alle drei Auftraege `state=scheduled`,
`last_status=ok`, `next_run_at` gesetzt. Eine Schleife ist fertig, wenn beide
Richtungen belegt sind, der Auftrag einmal echt gefeuert hat und die Zeile in
`Routinen.md` steht.
