# Spiegel/Kopier-Spuren: Eingangsfilter mathematisch optimieren

Stand: 18.09.2026 · Auftrag: Max ("Handel/spiegel und copy Spuren mathematisch
optimieren", Stufe 1 gewaehlt, Stufen 2 und 3 vorgemerkt) · Status:
**Spezifikation, wartet auf Freigabe** (Nutzer-Review-Gate des
brainstorming-Skills). Vor der Freigabe wird kein Code geschrieben.

## 1 Auftrag und Abgrenzung

**Teil dieser Spezifikation:** Eingangsfilter der drei Kopier-Spuren `spiegel`,
`kopier`, `kopier1zu1` auf den vorhandenen Journalen mathematisch pruefen und
daraus eine begruendete Aenderung der Wachen vorschlagen.

**Nicht Teil:** jede Aenderung an laufenden Spuren, jede Live-Frage, jede
Aenderung an Einsatzgroessen, Ausstiegsgeometrie, Vorbild-Auswahl. Die letzten
beiden sind vorgemerkt (Abschnitt 8).

## 2 Ausgangslage (gemessen am 18.09.2026)

| Spur | Ausstiege | Treffer | Ø nach Kosten | Ø vor Kosten | Kosten |
|---|---|---|---|---|---|
| spiegel | 807 | 25 % | −9,32 % | −1,77 % | 3048 USD |
| kopier | 47 | 19 % | −11,05 % | +0,29 % | — |
| kopier1zu1 | 12 | 17 % | −13,76 % | −2,75 % | 39,61 USD |

spiegel nach Ausstiegsgrund: Stop 427 (0 % Treffer, Ø −46,3 %), Trail 114
(56 %, +65,3 %), Ziel 43 (100 %, +91,9 %), Frist 43 (28 %, −6,5 %), Herzschlag
alt 180 (45 %, +6,2 %).

spiegel nach Marktkapitalisierung: **< 250k: 580 Ausstiege, 23 % Treffer, Ø
−14,39 %** (vor Kosten −7,26 %) · 250k–1M: 208, 30 %, **+4,18 %** (vor Kosten
+12,85 %) · 1M–5M: 13, 38 %, +3,80 % · ≥ 5M: 6, 0 %, −15,21 %.

Nach Kette (nur spiegel, belastbare Zahl): solana 738 Ausstiege (25 %,
−9,10 %) · base 18 (28 %, −14,92 %) · bnb 35 (29 %, −11,06 %) · ethereum 12
(17 %, −6,35 %) · xlayer 4 (0 %, −19,11 %).

Zwei Befunde tragen die ganze Runde: **Vor Kosten ist spiegel nahezu bei Null**
(−1,77 % je Position), nach Kosten bei −9,32 % — der Kostensatz ist die
groesste Einzelposition. Und **72 % aller Kopien liegen unter 250k
Marktkapitalisierung** und kosten −14,39 %, waehrend das Band 250k–1M +4,18 %
verdient.

## 3 Was rueckwirkend pruefbar ist — und was nicht

Das Journal (`handelsjournal.csv`) traegt je Zeile: `zeit`, `modus`, `aktion`,
`kette`, `wallet`, `token`, `symbol`, `preis`, `menge`, `einsatz_usd`,
`wert_usd`, `marktkap_usd`, `slippage_pct`, `gebuehr_pct`, `grund`.

**Pruefbar:** Marktkapitalisierung beim Einstieg, Kette, Wallet, Zeitpunkt.

**Nicht pruefbar (ehrliche Grenze):** das Signalalter (steht nur in
`ablehnungen.csv` und dort nur fuer ABGELEHNTE Signale, ohne Ergebnis);
Buchtiefe je Token; realisierter Nachlauf je Position (die 3 % bzw. 5 %
Slippage sind eine Annahme, keine Buchung).

**Folge:** Das Signalalter bleibt in dieser Runde unangetastet — es ist nur
prospektiv pruefbar (zweites Buch). Die pruefbaren Hebel sind
Marktkapitalisierungsband und Kette.

## 4 Methodik

**4.1 Eine Buchhaltung.** Die Paarung Einstieg/Ausstieg kommt aus
`<spur>/auswertung.py`, Funktion `lade_ausstiege()`. Geladen wird ueber den
PFAD (`importlib.util.spec_from_file_location`) mit eindeutigen Modulnamen,
weil alle drei Spuren ein Modul `auswertung` besitzen. Kein zweites
Paarungsverfahren — zwei Buchhaltungen derselben Sache sind zwei Wahrheiten.

**4.2 Zeithalbierung.** Die Ausstiege werden nach `zeit` sortiert; die aelteren
60 % sind die Suchhaelfte, die juengeren 40 % die Gegenprobe. Eine Regel gilt
nur als Vorschlag, wenn sie in BEIDEN Haelften dasselbe Vorzeichen zeigt und
ihr Betrag ausserhalb der Streuung der Gegengruppe liegt.

**4.3 Gepruefte Regeln** (je Spur): Untergrenze `marketcap_band_usd` in
{50k (Status), 100k, 150k, 250k, 500k}; Obergrenze in {1M (Status), 2M, 5M};
Kette = nur Solana; Kombination Untergrenze x Kette.

**4.4 Kennzahlen je Gruppe:** Anzahl Ausstiege, Trefferquote, Ø nach Kosten,
Ø vor Kosten, Median, Summe USD. Mindestbesetzung 30 Ausstiege je Gruppe in
JEDER Haelfte, sonst gilt die Gruppe als **nicht entschieden**.

**4.5 Ausgabe:** Ergebnistabelle, Verdikt je Regel (tragefaehig / nicht
entschieden / verworfen) und — nur bei "tragefaehig" — die vorgeschlagenen
Wachen-Werte.

## 5 Erfolgskriterien

1. Die Studie laeuft ohne Netz, rein lesend auf Journalen und `wachen.json`.
2. Jede vorgeschlagene Wertänderung ist in beiden Haelften belegt, mit Anzahl
   und Streuung.
3. Gegenprobe: derselbe Lauf mit der umgekehrten Regel (das Band verschieben
   statt es zu oeffnen, z. B. 250k–1M gegen 50k–250k) muss die Gegenrichtung
   zeigen — sonst ist die Zahl ein Artefakt.
4. Kein Vorschlag, der die Stichprobe unter 30 Ausstiege je Haelfte drueckt.
5. Die Studie aendert NICHTS an den Spurenwachen; sie liefert nur Vorschlaege.

## 6 Deliverables

| Datei | Zweck |
|---|---|
| `Agenten/Handel/filter_studie.py` | Studienwerkzeug, `--spur spiegel\|kopier\|kopier1zu1\|alle`, `--json` |
| `Agenten/Handel/filter_studie_ergebnis.json` | Ergebnisse aller Spuren |
| `Agenten/Handel/tests/test_filter_studie.py` | Test auf kuenstlicher Journaldatei mit bekanntem Ausgang |
| dieser Text | Design und Nachweis |

Der Test arbeitet ausschliesslich auf Tempdateien mit erfundenen Journalen —
die Studie darf die echten Spurenordner nicht anfassen (Haustest-Regel: ein
Test schreibt nie in einen echten Zielpfad).

## 7 Grenzen und Risiken

- **In-Sample-Falle:** Alle Regeln stammen aus derselben Stichprobe. Die
  Zeithalbierung mildert das, hebt es nicht auf. Die Studie liefert einen
  Vorschlag, keinen Beweis.
- **Kostenannahme:** 3 % (spiegel) bzw. 5 % (kopier, kopier1zu1) Slippage ist
  je Position ungemessen. Eine hoehere Untergrenze kann genauso gut eine
  Slippage-Korrektur sein. Deshalb wird jede Gruppe nach UND vor Kosten
  ausgewiesen.
- **Kleine Buecher:** kopier (47) und kopier1zu1 (12 Ausstiege) koennen die
  Mindestbesetzung nicht erreichen — dort lautet das Ergebnis voraussichtlich
  "nicht entschieden". Die Studie erfindet dort kein Verdikt.
- **Altbestand** vor dem 15.09.2026 traegt andere Ausstiegsfelder (`ziel`,
  `stop_pct`). Ausstiegsgruende werden berichtet, aber nicht als Stellhebel
  gelesen.

## 8 Vorgemerkt (Stufen 2 und 3)

**V1 — Ausstiegsgeometrie (Stop-Hoehe, Trailing-Aktivierung).** Braucht die
Preispfade je Position; die stehen nicht im Journal. Voraussetzung ist ein
Schattenbuch (zweites Papierbuch mit den Alternativeinstellungen) und eine
Pfadaufzeichnung im Zustand — `hoechster_kurs` laeuft bereits mit, ein
vollstaendiger Pfad fehlt. Messzeitraum mindestens 4 Wochen bzw. bis 30
Ausstiege je Zweig erreicht sind.

**V2 — Vorbild-Auswahl nach belegter Bilanz** (kopier, kopier1zu1). Braucht
Zeithalbierung und eine Mindestzahl Runden je Wallet; ohne das ist es reine
Nachschau-Auswahl. Die Daten von heute zeigen das Muster bereits: eine Wallet
mit 13 Ausstiegen steht bei Ø −27,87 %, eine mit 3 Ausstiegen bei +42,21 %.

Beide Vormerkungen bekommen einen eigenen Design-Zyklus, sobald Stufe 1
abgeschlossen ist.

## 9 Offene Entscheidung (Review-Gate)

Freigabe dieser Spezifikation durch Max. Danach folgt Schritt 9 des
brainstorming-Skills (writing-plans) und erst dann die Implementierung.
