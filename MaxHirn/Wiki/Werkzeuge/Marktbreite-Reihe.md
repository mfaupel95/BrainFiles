---
titel: Die Marktbreite als Reihe
aktualisiert: 2026-10-01
tags: [werkzeug, krypto, markt, breite, regime, reihe, wache]
---

# Die Marktbreite als Reihe

> **Merksatz:** Ein Messpunkt ist keine Richtung. „Die Breite schrumpft\" ist erst
> eine Aussage, wenn dieselbe Rechnung viele Tage hintereinander vorliegt — und
> die Rechnung muss bei jedem Tag dieselbe sein, sonst misst die Reihe sich selbst.

## Wofuer

Der Anteil der liquiden OKX-USDT-Paare, die ueber ihrer EMA200 stehen
(Tageskerzen, letzte **abgeschlossene** Kerze). Das ist die Trend-Breite des
Gesamtmarkts, nicht die Bewegung einzelner Werte. Rein lesend, oeffentliche
Schnittstelle, kein Schluessel.

## Die drei Teile

| Teil | Ort | Rolle |
|---|---|---|
| Werkzeug | `Agenten/Werkzeuge/breite.py` | messen, nachrechnen, anzeigen, auswerten |
| Reihe | `Agenten/Werkzeuge/breite-reihe.jsonl` | EINE Zeile je Kerzentag (Laufzeitstand, **nicht versioniert**, geht in die Sicherung) |
| Wache | `Agenten/Hermes/scripts/breite-wache.py` | Cron `breite-wache` (936bc3806c86), taeglich 19:00, `no_agent`, Telegram, leere Ausgabe = nichts senden |

```
python Agenten/Werkzeuge/breite.py                 # messen und zeigen (aendert nichts)
python Agenten/Werkzeuge/breite.py --merken        # messen und die Reihe fortschreiben
python Agenten/Werkzeuge/breite.py --fuellen --tage 250   # rueckwaerts nachrechnen
python Agenten/Werkzeuge/breite.py --fuellen --tage 250 --ueberschreiben
python Agenten/Werkzeuge/breite.py --reihe         # Verlauf, Veraenderung je Tag, LUECKEN
python Agenten/Werkzeuge/breite.py --statistik     # Verteilung + Folgeverhalten
python Agenten/Werkzeuge/breite.py --json          # Maschinenform
```

19:00 ist Absicht: die OKX-Tageskerze wechselt 16:00 UTC (= 18:00 Berlin),
gemessen wird also nach dem Wechsel.

## Das Fenster (geaendert 30.09.2026)

Gerechnet wird auf den letzten **600 abgeschlossenen** Kerzen bis einschliesslich
des Zieltags (`FENSTER`, in Live-Lauf und Nachrechnung derselbe Wert). Vorher war
das Fenster „was OKX in einem Aufruf zurueckgibt\" — 300 Kerzen minus die laufende,
also 299. Der Nachrechnungsweg nahm aber die ganze vorhandene Geschichte.

**Warum das kein Detail ist:** die EMA wird mit der SMA der ersten 200 Kerzen
gestartet; dieser Startwert klingt mit `(1-k)^Schritte` ab. Gemessen
(`Agenten/Hermes/cache/scratch/probe_ema_konvergenz.py`):

| Startwert-Gewicht | Abstand zur EMA200 bei 4 Paaren (alt → gereift) |
|---|---|
| 299 Kerzen: ~37 % | BTC **-1,24 → +4,52 %**, APT **-11,52 → -1,24 %**, ETH **-12,18 → -0,57 %**, SEI **-20,53 → -17,95 %** |
| 600 Kerzen: ~2 % | wie 1200 Kerzen: ueber 250 Tage **identisch** (Mittel 12,8, Median 6,9, min 0,0, max 96,5) |

Bei 299 Kerzen dreht der Startwert das **Vorzeichen** einzelner Paare. Die Reihe
fuehrt deshalb EINE Regel: 600 Kerzen, immer.

Gegenprobe, dass 600 reicht (`Agenten/Hermes/cache/scratch/probe_breite_gegen.py`,
Fenster 600 gegen 1200 ueber dieselben 250 Tage): Mittel, Median, kleinster und
groesster Wert sind **gleich**. Auf einzelnen Tagen kippt trotzdem ein Paar — am
2026-07-01 steht die Breite mit 600 Kerzen auf 6,9 %, mit 1200 auf 10,3 %, das ist
1 von 29 Paaren genau an der EMA. Ein laengeres Fenster waere an dieser Stelle
schaerfer, kostet aber die halbe Geschichte (30 Paare x 1200 Kerzen) und aendert
die Richtungsaussage nicht.

Beim ersten Nachrechnen (`--ueberschreiben`) wurde keine Live-Messung verworfen:
der alte Wert bleibt als `live_alt` in der Zeile (plus `live_alt_unter`).

## Die Reihe als Zeitzeuge (Stand 30.09.2026)

250 Kerzentage, **2026-01-22 bis 2026-09-28**, 30 Paare in der Liste; gemessen
werden je Tag 28 oder 29 (SEI-USDT existiert erst ab Juni — 129 Tage mit 28,
121 mit 29). Ein Fehlschlag wird **namentlich** in `offen` gefuehrt: TON-USDT an
einem Tag, SEI-USDT an 129.

| Monat | Tage | Mittel | min–max |
|---|---|---|---|
| 01/2026 | 10 | 2,5 % | 0 – 7,1 |
| 02/2026 | 28 | 0,0 % | 0 – 0 |
| 03/2026 | 31 | 2,2 % | 0 – 3,6 |
| 04/2026 | 30 | 3,6 % | 3,6 |
| 05/2026 | 31 | 8,0 % | 3,6 – 21,4 |
| 06/2026 | 30 | 9,5 % | 0 – 13,8 |
| 07/2026 | 31 | 7,5 % | 3,5 – 10,3 |
| 08/2026 | 31 | 18,9 % | 3,5 – 44,8 |
| 09/2026 | 28 | **58,5 %** | 27,6 – **96,5** |

Gesamt: Mittel 12,8 %, Median 6,9 %, 209 von 250 Tagen unter 20 % Breite, 8 Tage
ueber 80 %. Der Umschwung auf breiten Aufwaertstrend liegt in **September 2026** —
vorher war der Markt ueber acht Monate fast durchgehend unter seiner EMA200.
Wer heute „100 % Breite\" sieht, sieht den Gipfel eines Anstiegs, nicht den
Normalzustand.

## Was die Wache meldet

`zeilen(m, merker, schwelle)` — Reihenfolge der Regeln, jede Zeile ein Grund:

| Regel | Ausloeser |
|---|---|
| erste Messung | kein Merker vorhanden |
| Stufenwechsel | `ok` ≥ 80 % / `achtung` ≥ 60 % / `warnung` darunter |
| neue Abwaertskreuze | Paar steht unter der EMA200, das es vorher nicht tat - namentlich **hoechstens `NEU_UNTER_MAX` (5)**, die NAECHSTEN an der EMA200, der Rest als Zahl (und N weitere) |
| weiter unter der EMA200 | die namentliche Liste, wenn schon gemeldet wurde |
| Rueckgang | ≥ `RUCKGANGS_PP` (10) Punkte gegenueber der **letzten Meldung** |
| unvollstaendige Messung | Deckung < 90 % (`DEKKUNG_MIN`) |
| Schwelle | einmalig beim Uebergang unter `--schwelle` |
| Nachfuellung / Abgleich | siehe unten |

**Warum die Liste begrenzt ist (01.10.2026):** faellt die Breite von 96 % auf 20 %,
kreuzt fast der ganze Korb auf einmal auf — 23 Paare ergaben 27 Zeilen und 1.045
Zeichen, also einen Datenauszug statt einer Nachricht. Genannt werden die fuenf
NAECHSTEN an der EMA200 (ein Paar, das gerade eben darunter faellt, ist das
Fruehwarnzeichen; eines, das schon weit darunter steht, war auch vorher schon
unter ihr). Gemessen: dieselbe Lage ergibt jetzt 10 Zeilen und 406 Zeichen.
**Gemeldet wird die Zahl weiter vollstaendig** (Neu unter der EMA200 (23)), und der gemerkte Stand traegt alle 23 Namen - nur die Anzeige ist gekuerzt.
und der gemerkte Stand traegt alle 23 Namen — nur die Anzeige ist gekuerzt.

**Der Rueckgang rechnet gegen die letzte MELDUNG, nicht gegen den Vortag.** Sonst
summiert sich „vorgestern −9, gestern −9\" nie zu einer Nachricht. Innerhalb der
Stufe `ok` war die Wache vorher blind: 100 % auf 81 % haette keine Zeile erzeugt —
diese Regel ist der einzige Grund, warum ein Schrumpfen im gruenen Bereich
ueberhaupt auffaellt.

**Die Wache heilt still.** Nach dem Fortschreiben laeuft `fuellen` mit den gerade
geholten Kerzen (`messen(mit_verlauf=True)` — kein zweiter Abruf), **wenn** die
Luecke in diesen Verlauf passt. Die Heiltiefe ist seit 01.10.2026 nicht mehr fest:
`_heil_tage` zaehlt die fehlenden Kerzentage zwischen der letzten Zeile und der
gerade gemessenen Kerze und heilt genau so weit zurueck (mindestens `HEIL_TAGE` 5,
hoechstens `HEIL_MAX` 120, plus eine Randkerze). Vorher heilten feste 5 Tage: war
der Rechner drei Wochen aus, blieb die Luecke stehen und fiel nur auf, wenn jemand
`--reihe` las. Ist die Luecke laenger als der mitgemessene Verlauf, holt `fuellen`
die Kerzen selbst nach — anders waeren die aeltesten fehlenden Tage unerreichbar.
Was auch danach fehlt (aelter als `HEIL_MAX`), wird als `Luecke bleibt: …` gemeldet.
Gemeldet wird sonst nur, wenn wirklich Tage fehlten **oder** wenn Live-Weg und
Nachrechnung um mehr als `ABGLEICH_TOLERANZ` (0,5 Punkte) auseinanderlaufen.
Geschrieben wird auch bei leerer Ausgabe: leere Ausgabe heisst nichts zu sagen,
nicht nichts getan.

`--reihe` nennt Luecken ausdruecklich (T-204): fehlt ein Kalendertag zwischen der
aeltesten und der neuesten Zeile, steht dort `LUECKEN: N Kerzentag(e) fehlen
zwischen …` mit den Bereichen; ohne Luecke sagt die Ausgabe das ebenfalls
(`Keine Luecke zwischen …`). Nachgemessen am 01.10.2026 an einer kuenstlichen
Reihe (Reihe bis 10.09., Kerze 30.09., 19 fehlende Tage): Heiltiefe 20, danach
19 Kerzentage nachgefuellt, 0 Luecken — die echte Reihe ist mit 252 Kerzentagen
(22.01.–30.09.2026) luecklos.

## Fallen

- **Ein zu kurzes Fenster misst den Startwert, nicht den Markt** (oben). Wer die
  Fensterlaenge aendert, aendert bei einem Teil der Paare das Vorzeichen — und
  eine Reihe aus zwei Fenstern ist keine Reihe.
- **`--fuellen` ohne `--ueberschreiben` ist die richtige Vorgabe.** Live-Zeilen
  sind der Beleg, dass der Tag wirklich gemessen wurde; sie werden nicht still
  ersetzt, nur fehlende Tage ergaenzt.
- **Die Zahl der Paare aendert sich im Lauf der Zeit** (Listungen, Ausfaelle):
  `n_gesamt` steht in jeder Zeile und muss mitgelesen werden. „25 von 29\" und
  „25 von 28\" sind verschiedene Prozente.
- **Ein Fehlschlag darf nicht still aus der Liste fallen** — er wuerde die Quote
  schoenrechnen. Deshalb `offen` je Zeile und die Deckungszeile in der Meldung.
- **OKX braucht einen User-Agent**, sonst HTTP 403 (siehe Skill `marktbreite-messen`).
- **Nicht aus `zustand.json`, Journalen oder Notizen ableiten** — immer messen;
  die Reihe ist die Ausnahme, weil sie selbst die Messung mit Zeitbezug traegt.

## Offene Punkte

- **10 Punkte als Rueckgangsschwelle** bleiben eine Setzung (T-099): gemessen
  sind an 250 Tagen nur 16 Tagesaenderungen ≥ 10 Punkte, und in Hochphasen
  (Breite vorher ≥ 60) fiel die Breite an 3 von 10 Tagen — diese Stichprobe ist
  fuer ein Perzentil zu klein. Entscheidung, wenn 30 Hochphasen-Tage vorliegen.
- **SEI-USDT ab Juni im Nenner** (T-204): der Sprung 28 → 29 Paare ist in den
  Monatszahlen enthalten.

## Siehe auch

- [[Marktdaten-und-Bot-markt-recherche]] — Kurse, Kerzen, News ohne Schluessel
- [[Spuren-Uebersicht]] — die Breite ist der MARKT, nicht das eigene Buch
- Skill `marktbreite-messen` — Verfahren und Regeln, die die Zahl tragen