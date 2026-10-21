# Rückgabeformen der Handelskette

Eine Quelle für alle drei Stufen (Scanner → Prüfer → Disponent). Jede Stufe
beginnt ihre Antwort mit **`status: <wert>`** als erster Zeile, danach feste
Felder im Format `schluessel: wert`. Die Form lässt sich maschinell prüfen:
`python Agenten/Handel/agenten/rueckgabe_pruefen.py <scanner|pruefer|disponent> <datei>`
(Datei oder `-` für Standardeingabe). Das Skript ist die Wahrheit, dieser Text ihre Erklärung.

**Eingangsregel (jede Stufe):** Fehlt ein Pflichtfeld der Vorstufe oder hat es kein
gültiges Format, antwortet die Stufe nur mit
`status: eingabe-ungueltig` und `feld: <name>` — sie rechnet nicht weiter und
rät nichts dazu.

## Scanner

`status: kandidaten` oder `status: heute-nichts` (kein Kandidat ist ein vollwertiges Ergebnis).
Höchstens 5 Kandidaten, je Kandidat eine Zeile
`kandidat: paar=…; richtung=…; spur=…; atr_pct=…; warum=…; dagegen=…` mit diesen Feldern:

| Feld | Format |
|---|---|
| `paar` | z. B. `BTC/USD` |
| `richtung` | `long` oder `short` |
| `spur` | `1` (Spot) oder `2` (Hebel) |
| `atr_pct` | Zahl in Prozent, Zeitrahmen in Klammern, z. B. `2.9 (1d)` |
| `warum` | ein Grund |
| `dagegen` | mindestens ein Punkt |

Dazu `rang:` (Rangfolge) und `lage:` (ein Satz).

## Prüfer

Bekommt **nur** `paar`, `richtung`, `spur` — nicht `warum`, nicht `dagegen`, nicht die
Scanner-ATR. Die tragende Zahl rechnet er aus Rohkerzen selbst.

`status: geprueft` mit Feldern:

| Feld | Format |
|---|---|
| `urteil` | `ja` oder `nein` (kein Mischwert) |
| `tragende_zahl` | Zahl samt Einheit |
| `stichprobe_n` | ganze Zahl (Kerzen) |
| `zeitraum` | Von–bis |
| `gegenszenario` | zwei Sätze |
| `widerlegt_ab_kurs` | Zahl (Kursniveau) |
| `atr_pct` | Zahl, Zeitrahmen in Klammern — **maßgeblich** gegenüber der Scanner-ATR |
| `nicht_geprueft` | Text oder `nichts` |

## Disponent

Verlangt vom Prüfer `urteil: ja`, `widerlegt_ab_kurs` und `atr_pct`. Fehlt eines,
antwortet er `status: eingabe-ungueltig` und liest `wachen.json` gar nicht erst.

`status: auftrag` (alle Wachen halten) oder `status: grenze-verletzt` (nichts wird vorgelegt, die Grenze wird genannt). Felder:

`paar`, `richtung`, `spur`, `einstieg`, `stop`, `stopweite_pct`, `stopweite_atr`,
`positionswert`, `margin`, `hebel`, `risikobetrag` (Zahl mit Währung),
`wachen:` (je Grenze eine Zeile `grenze=…; ist=…; soll=…; haelt=ja|nein`),
`befehl:` (fertiger Block ohne Platzhalter), `dagegen:` (ein Satz).
