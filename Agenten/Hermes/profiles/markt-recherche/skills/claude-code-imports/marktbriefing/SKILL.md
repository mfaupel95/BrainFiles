---
name: marktbriefing
description: Trägt einen geprüften Marktüberblick aus den fertigen traderhub-Boards zusammen — Zinsen/Makro, Sektorrotation, Einzelwerte. Benutzen bei "Marktüberblick", "Marktbriefing", "market", "wie steht der Markt", "Marktlage", oder als Routine. Nur lesen, keine Prognose, kein Handel.
---

# Marktbriefing

Ziel: ein Bildschirm mit geprüften Zahlen. Keine Prognose, kein Handelsvorschlag,
kein Kursziel. Der Chat-Verlauf zählt nicht — im Routinelauf ist das Briefing
erst fertig, wenn der Stand in `Wissen/Marktlage-<Monat>-<Jahr>.md` steht.

Abgrenzung: [[Marktscanner]] ist der OKX-Krypto-Scanner mit begrenztem
Selbsthandel. Dieses Briefing fasst nur an, es handelt nichts.

## 1. Die Befehle, die wirklich laufen

Alle über die `traderhub`-Skill (Details dort). Ausgabe ist JSON auf stdout.

```
traderhub board get --board macro       # Zinsen, CPI, Arbeitsmarkt, Öl, Dollar, M2, Sentiment
traderhub board get --board movers      # Gewinner / Verlierer / aktiv + Screener-Listen
traderhub board rotation                # GICS-Sektorrotation, relative Stärke je Zeitfenster
```

Bei Bedarf zusätzlich, nicht standardmäßig:

```
traderhub board get --board calendar         # Earnings / IPOs / Ex-Dividende, 14 Tage
traderhub board get --board fed               # Fed-Bilanz + Primärhändler + FOMC-Dokumente
traderhub board get --board term-structure    # BTC/ETH-Futures-Kurve + annualisierte Basis
```

`alice analysis` (technischer Blick auf einen einzelnen Wert oder Index) **nur
auf ausdrücklichen Wunsch** — es gehört nicht ins Standardbriefing.

## 2. Pflichtprüfungen vor dem Schreiben

- **`meta` jedes Payloads lesen.** `origin: "hub"` = gehostete Daten, `origin:
  "local"` = eigene Schlüssel. `stale: true` = die obere Quelle hat sich nicht
  aktualisiert, es ist der letzte gute Stand — **das dann im Briefing sagen**.
- **`asOf` / `cachedAt`** nennen, wenn der Stand nicht von heute ist.

## 3. Einheiten-Fallen (aus der traderhub-Skill)

- `percent_change` auf movers/discover ist ein **Bruch**: `0,052` = +5,2 %.
- `dividend_yield`, ETF-`weight` sind **Dezimalbrüche**: `0,012` = 1,2 %.
- `rotation`-`returns` und `rel_strength` sind **Dezimalbrüche**: `0,219` = +21,9 %.
- OECD-Reihen (`global cpi --transform yoy`, `global rates`) sind in
  **Prozentpunkten**: `3,72` = 3,72 %.
- `dollar_volume` ist Preis × Volumen — die einzige über Ticker hinweg
  vergleichbare Umsatzzahl. `rvol` = Volumen gegen den eigenen 20-Tage-Schnitt.

## 4. Ausgabe

```
## Marktüberblick — <Wochentag> <Datum>

Quelle: traderhub (origin: <hub|local>), Stand <asOf>. <Hinweis nur falls stale.>

### Zinsen & Makro
| Kennzahl | Aktuell | Einordnung |
| Fed Funds / 2J / 10J / 10J–2J / CPI YoY / 10J-Breakeven /
  Arbeitslosenquote / Erstanträge / WTI / Dollar-Index / M2 / UMich-Sentiment |

### Sektorrotation (relative Stärke vs. Benchmark)
- Führend / Nachzügler über 1W, 1M, 3M, 6M.

### Einzelwerte
- Gewinner (Top 5), Verlierer (Top 5), meistgehandelt (Top 5) — je mit
  %-Änderung (aus dem Bruch umgerechnet) und Dollar-Volumen.

### Bild
Ein Absatz: was die Zahlen zusammen sagen. Als Einordnung markiert, nicht als
Vorhersage.
```

## 5. Regeln

- **Keine Prognose ohne Kennzeichnung.** Formulierungen wie „higher for longer"
  sind Einordnung, kein Kursziel. Kein Zeithorizont behaupten.
- **Nichts handeln, nichts versenden, nichts scharfschalten.** Wie [[Routinen]]
  festhält: aus einem Zeitplan heraus wird nie Geld bewegt.
- **Nichts erfinden.** Fehlt ein Board oder ist es `stale`, steht das im Text.
- Zahlen aus [[Marktlage-August-2026]] & Co. werden zitiert, nicht nachgemessen
  ([[INDEX]]-Regel).

## 6. Ablage (nur im Routinelauf oder auf „ablegen")

1. Snapshot in `Wissen/Marktlage-<Monat>-<Jahr>.md` **fortschreiben** — eine
   Notiz je Monat, neue Tagesstände als datierter Abschnitt oben, alte stehen
   lassen. Frontmatter `updated` hochsetzen.
2. Gibt es die Monatsnotiz noch nicht: neu anlegen mit vollständigem Frontmatter
   (`id: JJJJMMTT-marktlage-<monat>-<jahr>`, tags `[finanzen]`, `related` auf
   `20260907-marktbriefing`).
3. **`Wissen/INDEX.md` im selben Schritt nachziehen** — beim ersten Anlegen der
   Monatsnotiz eine Registry-Zeile unter „Steuern und Geld".
4. Mit Skill `sichern` committen.

Bei manuellem Aufruf ohne „ablegen": nur Chat, nichts schreiben.
