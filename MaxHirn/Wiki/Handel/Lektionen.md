---
id: 20260921-handel-lektionen
title: 'Handel — Lektionen'
tags: [handel, lektion]
created: 2026-09-21
updated: 2026-09-22
related: ['[[Handel/Spuren-Uebersicht]]', '[[Lektionen/Wahrheit-pruefen]]']
summary: 'Die teuren Lehren aus dem Handelsteil: Buch und Boerse liefen auseinander, Papier mischte sich in Live-Buecher, Stoerungen sahen wie Runden aus, Preisregeln fehlten beim Notausstieg.'
---

# Handel — Lektionen

## 1. Ein Buch ist kein Beweis — die Boerse ist einer

**Belegter Fall (21.09.2026).** `xperp` fuehrte vier Positionen (ZEC, XAG, LINK, ETC) bei
Buchmodus live. An der Boerse existierten sie nicht: `/account/positions` kannte nur die
manuelle FIL-Position und einen XRP-Rest. Zweiter Zeuge: von 14 Live-Zeilen im Journal waren
**alle 14 `funding`** — kein Live-Kauf, kein Live-Verkauf. Die Positionen stammten aus dem
Papierlauf bei Buchmodus live. Am selben Tag dasselbe Muster bei `scanner`.

**Regel.** „Spur X ist live mit N Positionen" NIE aus `zustand.json` schliessen. Drei Zeugen:
Buch, Journal (**Live-Kaufzeilen muessen existieren**) und Boerse (`/account/positions`,
bei Kraken Balance + Open Orders).

**Fix (Muster fuer alle Spuren mit Live-Zweig).** Neue Positionen tragen `modus` (live/papier)
plus Orderkennung; am Anfang JEDES Live-Laufs bucht `bueche_papier_altlasten_aus()` Positionen
ohne Order als Papier-Verkauf mit Grund `buchbereinigung` aus.
`xperp` hat **kein** `kauf_ord_id`-Feld — dort ist der Massstab `modus`.

## 2. Nie im Papierlauf schliessen, was live offen ist

**Belegter Fall.** `flach_stellen`/`pruefe_ausstiege` schlossen im PAPIERLAUF auch Positionen
mit `modus=live` — aber nur im **Buch**, an der Boerse blieb die Position offen (HBAR:
„papier,schliessen,kill_switch" im Journal, 9,4 Kontrakte offen). Jetzt bleiben
`modus=live`-Positionen im Papierlauf stehen und werden gemeldet; geschlossen werden sie nur
vom Live-Lauf. Tests: `xperp/tests/test_handeln_geister`.

**Verwandt:** `mosaic` ist die einzige Spur mit einem MODUS-Waechter je Position
(`if p.get('modus') != 'live': continue`) — Papier und Live liegen dort in EINEM Buch, ohne
sich zu stoeren. `scanner` hat diesen Waechter nicht; dort war die Bereinigung noetig.

## 3. Eine Stoerung ist keine Runde

**Regel.** Ausstiege mit `herzschlag` im Grund sind Zwangsschluesse und werden in der
Auswertung **getrennt** gefuehrt. Die eine Definition liegt in `Handel/stoerungen.py`
(`ist_stoerung`, `teile_runden`); Wachen laden sie ueber den PFAD
(`scanner/wachen_pruefung.stoerungen_modul()`), weil eine Spur mit eigenem Ordner als
`sys.path[0]` startet.

**Belegte Groessen (15.09.2026):** 296 echte Runden, 21 Stoerungen (xperp 12, kraken 8,
swap 1) — xperp hatte damit **11 echte Runden statt 23**, kraken **2 statt 10**. Alle 21
zwischen 03.09. und 14.09., allein 7 am 12.09. — die Haeufung IST die Fehlersuche.
**Ueberraschend und wichtig:** bei kraken waren die Zwangsschluesse **+4,59 EUR positiv** und
die echten Runden -4,50 EUR negativ, bei xperp umgekehrt (-0,74 gegen +38,14 USD). Die
Richtung ist nicht vorhersagbar — deshalb beides getrennt ausweisen, nicht eines weglassen.

**Ursache war die Herzschlag-Grenze selbst** (30 min): jeder Rechnerneustart stellte flach und
buchte eine „Runde", die keine Entscheidung war. Deshalb 180 min (siehe
[[Handel/Gates-und-Freigabe]]).

## 4. Die Rueckgabe des Kindprozesses ist nicht das Ergebnis

**Belegter Fall.** `nautilus`-Arme lieferten Rueckgabe 1 („keine Quote angekommen und
Kopier-Spur tot"), `0xC0000409` und 300-s-Timeouts. Ursache war **Speicherdruck**, nicht Logik.
Nach dem Aufraeumen liefen sie. Also: vor jeder Logikdiagnose den Speicher/Commit pruefen
([[Lektionen/Windows-Umgebung]]).

## 5. Ein Ziel, das strukturell unerreichbar ist

**Belegter Fall.** Die Nautilus-Arme stoppen bei -19,8 % und trailen ab **+30 %** mit 25 %
Abstand — in 4-6 Tagen **kein einziger Ausstieg**, weil +30 % fuer BTC in einer Woche nicht
kommt (Peak +8,5 %). Der wirkliche Ausstieg ist die **Frist (168 h)**. Zusatzbefund: die 4
Positionen eines Arms sind EINE Wette (Minuten auseinander, selbes Instrument).

**Merksatz.** Vor dem Einbau einer Ausstiegsgeometrie die gemessene Verteilung der Bewegung
pruefen (Geometrie-Gegenprobe: Break-even = Stop/(Stop+Ziel) gegen die Trefferquote). Positive
Gegenprobe heisst nur „nicht offensichtlich falsch".

## 6. Optimieren am Original, nie an einer Nachbildung

**Belegter Fall.** `gitter/backtest_gitter.py` faehrt `gitter/handeln.py` **selbst**
(`leiter_bauen`, `arme`, `walk` per importlib) — eine Nachbildung wuerde die Nachbildung
optimieren. Befund: 42 Parameterkombinationen spannen nur +0,17 bis +2,23 %, der Parameter ist
NICHT der Hebel; Korrelation Markt/Gitter +0,78 ueber 52 Wochen — das Gitter folgt der
Marktrichtung und verliert in steigenden Fenstern. Geaendert wurde nur, was out-of-sample
ueberlebte (`stufen` 12 → 6, ~1,4 pp). Zusatzfalle: die Leiter entsteht nur beim **Erstlauf**
und wird nie verschoben — ein neuer `stufen`-Wert wirkt nur auf eine frische Leiter.

## 7. Zahlen brauchen das Skript

Jede Kennzahl auf dieser Wiki-Seite ist mit dem genannten Werkzeug nachrechenbar
(`auswertung_alle.py`, `kosten_wendepunkt.py`, `stoerungen.py`, `spiegelstand.py`,
`pruefe_ratschen.py`). Eine Kennzahl ohne Werkzeug ist beim naechsten Mal eine Behauptung.

## 8. Jede Boerse hat Preisregeln — ein roher Rechenwert fehlt den Notausstieg

**Belegter Fall (22.09.2026, Zyklus 42, `mosaic` live auf Kraken).** Kauft `SOL-USDC`, will den
Stop setzen, Kraken antwortet `EOrder:Invalid price:SOL/EUR price can only be specified up to
2 decimals` — daraufhin verkauft die Spur die Position **sofort zurueck** (richtige Reaktion:
nie eine Position ohne Notausstieg halten). Kosten 0,605 EUR in gut einer Sekunde, ohne Handel.

**Ursache.** `kraken._add_order` schrieb `str(preis)` — der Stop-Preis kommt aus
`Einstieg x (1 - stop_pct)` und hat praktisch immer zu viele Stellen. Die erlaubte Stellenzahl
steht **je Paar** in `AssetPairs.pair_decimals` (SOLEUR/XETHZEUR 2, XXBTZEUR 1, AKEEUR 8,
KASEUR 5) — ein fester Formatstring waere fuer jedes andere Paar falsch. Bei OKX heisst dieselbe
Regel `tickSz` (`okx_spot.slTriggerPx` sendete ebenfalls roh).

**Fix.** `kraken.preis_gerundet(paar, preis, richtung="auf")` und das Gegenstueck
`okx_spot.preis_gerundet`; beide runden AUF (der Long-Stop liegt nie tiefer als gerechnet, das
Risiko wird also nicht groesser als die Wache erlaubt) und geben einen fertig formatierten
String zurueck (`str(float)` schreibt kleine Werte als `1e-08`, was ebenfalls abgelehnt wird).
Tests: `kraken/tests/test_preis_gerundet.py`, `mosaic/tests/test_preis_gerundet.py`.

**Merksatz.** Ein Orderpreis gehoert durch die Regeln der Boerse, bevor er rausgeht — und die
Regeln kommen aus der API des Paares, nicht aus einer Konstanten. Probe ohne Geld: `AddOrder`
mit `validate=true` nimmt den gerundeten Preis an und den rohen nicht.