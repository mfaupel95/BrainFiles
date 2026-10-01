# Schwellen setzen (Tore, Filter, Gates)

Gilt für alles, was eine Auswahl trifft: Score-Grenzen, „günstige Einstiege“,
Sperren. Zwei Fehlerrichtungen, beide gefährlich:

- **Das Tor geht nie auf** → sieht wie Sicherheit aus, ist ein Fehler. Eine
  Auswahl, die nie etwas meldet, hat noch keinen einzigen Datenpunkt geprüft.
- **Das Tor geht nie zu** → der Filter ist Dekoration und suggeriert Prüfung.

## Regeln

1. **Nie einen Messwert aus der Schwelle ableiten.** Ein Ziel, das auf
   `preis + mindest_cr * risiko` hochgezogen wird, erfüllt das C/R-Tor immer —
   das Tor ist damit wirkungslos. Messwerte kommen aus dem Markt (Hoch der
   letzten 60 Tage, Tief der letzten 20), und ob es reicht, sagt der
   Verhältniswert selbst.
2. **Prüfen, ob eine geborgte Kennzahl bedeutet, was die Lage braucht.**
   Volumenbestätigung (jüngstes Volumen über dem Schnitt) beschreibt einen
   **Ausbruch**; ein Rücksetzer geschieht bei fallendem Volumen. Dafür gehört
   eine Lebendigkeitsprüfung hin (5 Tage gegen 30 Tage ≥ 0,5), keine
   Ausbruchskennzahl.
3. **Eine Grenze, eine Stelle.** Existiert der Wert schon in `wachen.json`
   (Score, Volatilität, Stop-Spanne), denselben Wert verwenden. Eine zweite
   Schwelle ist eine zweite Meinung über dasselbe Geld. Die Regel gilt für
   **dieselbe Frage** — eine gespiegelte Richtung ist eine andere Frage, dort
   gilt Regel 9.
4. **An der echten Verteilung kalibrieren, bevor es scharf geht.** Über die
   ganze Grundgesamtheit laufen lassen, Verteilung der Kennzahlen und offene
   Tore je Wert ausgeben, mehrere Tor-Sätze durchprobieren und einen wählen,
   der **ein paar** Treffer liefert — nicht null und nicht alles. Ohne diese
   Runde ist jeder Wert geraten.
   **So wird gemessen** (bewährtes Muster): ein Wegwerfskript unter
   `Agenten/Hermes/cache/` zieht die Daten für 10–20 Werte, bildet **alle**
   möglichen Fenster (nicht nur das jüngste) und zählt je Wert und insgesamt,
   wie oft das Tor öffnet. Ausgegeben werden zwei Zahlen: die Öffnungsrate
   (Anteil aller Fenster) und die **Verteilung der Kennzahl in den
   ausgelösten Fenstern** als Perzentile (min, p10, p25, Median, p75, max).
   Die Untergrenze gehört ins Rauschband (unteres Fünftel), und der Lauf
   zeigt, wie viele Fenster bei welcher Schwelle bleiben. Beispiel: 15
   USDT-Perpetuals, 1287 Fenster, 142 Auslösungen = 11,0 %; Kennzahlen-p10
   0,037, Median 0,333; Schwelle 0,10 → 8,9 %. **Beide** Zahlen (vorher /
   nachher) in den Kommentar an der Konstante; die Zahlen im Lauf, nicht im
   Kopf, sind der Beleg.
5. **Beide Richtungen testen.** Je Tor ein Fall, der es reißt und den Namen
   des Tores in der Begründung trägt, plus ein Positivfall, in dem der ganze
   Satz hält. Kennzahlen im Test durch feste Werte ersetzen, damit jeder Test
   genau ein Tor prüft.
6. **Null Treffer ist ein Ergebnis, keine Stille.** Ausdrücklich melden („N
   Märkte geprüft, kein Treffer“) und die Rohwerte samt Tor-Namen in den
   Bericht schreiben. Ein Tag ohne Meldung darf nie wie ein Ausfall aussehen.
7. **Die Kalibrierung dokumentieren.** Im Modul und im README festhalten,
   welche Werte woher kommen und welche Fehlkonstruktion man dabei behoben hat
   — wer später an der Zahl dreht, findet die Begründung sonst nicht.
8. **Kosten- und Abschlagsannahmen genauso kalibrieren wie Tore.** Ein
   Papierlauf mit geschätzten Kosten ist eine Wunschrechnung. Zwei Posten
   getrennt messen, weil sie verschieden groß sind:
   - **Buch-Effekt** des eigenen Einsatzes — Näherung für ein
     Constant-Product-Buch: `2 × Einsatz / Liquidität` in Prozent. Das ist eine
     **untere** Grenze: Spread, konzentrierte Liquidität und
     Prioritätsgebühren fehlen darin, und genau das dazuschreiben.
   - **Nachlauf** — Kurs jetzt gegen den Kurs, den das Vorbild bekommen hat.
     Das ist der Posten, den ein Nachahmer wirklich verliert, und er steht in
     keiner Pool-Tiefe; er wächst mit dem Abstand zwischen Signal und eigenem
     Kauf.
   Über eine Stichprobe frischer Signale messen und die Verteilung ausgeben
   (Schnitt, Median, größter) statt eines Mittelwerts allein. Als eigenen
   **Modus ins Programm** legen (`--messen`), der das Buch nicht anfasst,
   damit die Messung wiederholbar ist; Rohwerte in eine nicht versionierte
   Datei, die Zahl samt Methode ins README und in `wachen.json`. Bleibt die
   Annahme danach stehen, gehört in die Begründung, **dass sie gemessen
   trägt** — nicht, dass sie streng ist. Eine Messung ist eine Momentaufnahme:
   dazuschreiben, wann neu zu messen ist.
   - **Gebührensätze an einer ECHTEN Füllung prüfen, nicht an einer Tarifseite
     oder einem Abo-Versprechen.** Zwei Zeugen, beide aus der API: die
     abgerechnete Order (`TradesHistory` der Börse: `cost` gegen `fee`, beide
     je Trade) und der Kontostand-Tarif (`GET /0/private/TradeVolume`, Feld
     `fees[paar].fee` für Taker bzw. `fees_maker`; dazu `volume` = 30-Tage-
     Volumen und `nextfee`/`nextvolume` der nächsten Stufe). Ein Nullsatz, der
     nur in `wachen.json` steht, ist eine Annahme: `handeln.py --wachen` zeigt
     die Datei, nicht die Wahrheit. Ein Abo-/Aktionsvorteil ist kein
     Marktpreis — sein Wegfall gehört als auslösende Bedingung an dieselbe
     Stelle wie der Wert (`_gebuehren_abo` samt Rücknahme-Satz), und die
     Rücknahme passiert **bevor** Runden für die Freigabe gezählt werden.
   - **Ein fehlendes Gebührenfeld ist auch eine Aussage.** Spuren, deren
     Auswertung über einen gemeinsamen Leser läuft (z. B.
     `auswertung_alle.runden_indikator`), rechnen ohne `gebuehr_taker` in
     `wachen.json` **brutto** — dann gehört der Satz als Kommentarfeld in die
     `wachen.json`, damit niemand das Netto aus der Zahl liest. Für OKX und
     Deribit steht das Verfahren (zwei Zeugen: `/api/v5/account/trade-fee` und
     `/api/v5/trade/fills`), die zwei Einheiten (`gebuehr_taker` = Bruch,
     `gebuehr_pct` = Prozent), das Werkzeug `Agenten/Handel/gebuehren_setzen.py`
     und die gemessenen Sätze (Spot 0,10 % / Futures 0,05 %) in
     `references/gebuehren-belegen.md`.
9. **Dieselbe Zahl in gespiegelter Richtung ist keine Kalibrierung.** Wird eine
   Schwelle auf die Gegenrichtung übertragen (Long-Tor → Short), erst **beide
   Verteilungen messen** (Median, oberes Quartil, Maximum je Richtung) und den
   **Rang** übertragen, nicht die Zahl. Ist die Bewertungs-Skala
   richtungsgebunden kalibriert, liegt dieselbe Zahl auf der Gegenseite über
   dem Tagesmaximum: das Tor geht dann nie auf, und es fällt nicht auf, weil
   die Ausgabe nur „nichts gefunden“ sagt — genau die Stille, die Regel 6
   verbietet. Im Tor benennen, woher die Zahl kommt („oberes Quartil der
   Short-Verteilung“), und dazuschreiben, wann neu zu messen ist. Der
   Gegenprobe-Lauf gehört dazu: **ein** Treffer auf der neuen Seite ist der
   Beleg, dass das Tor überhaupt öffnen kann.
10. **Eine kumulierte Reihe nie über Mittelwerte des Standes vergleichen.**
    CVD, OBV, kumuliertes Volumen: der Stand trägt die gesamte Vorgeschichte,
    ein steil gestiegener und danach leicht gefallener Verlauf hat trotzdem
    einen höheren Mittelwert als die ältere Fensterhälfte — die Gegenbewegung
    liest sich dann als Bestätigung des Trends. Verglichen wird die
    **Steigung** der jüngsten Hälfte (Zuwachs je Eimer), normalisiert auf die
    mittlere absolute Eimer-Bewegung, damit die Kennzahl über Instrumente
    vergleichbar bleibt. Der erste Testlauf einer solchen Komponente fällt
    genau daran auf: der Fall mit der Gegenbewegung bleibt aus.
