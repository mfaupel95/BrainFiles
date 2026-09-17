# Entwurf: Auswertung und Berichte

Stand 17.09.2026. Thema 3 des Vierer-Programms (4 Aufräumen → **3 Auswertung** →
2 Betrieb → 1 neue Spur). Vorgänger: `BEFUND-hygiene-2026-09-17.md`.

Dies ist ein Entwurf, kein Umsetzungsplan. Er beschreibt, **was** entsteht und
**warum**; die Schrittfolge steht danach in einem eigenen Plan.

## Das Problem

Vier Beobachtungen, alle belegt:

1. **Keine Zeitachse.** Jede Auswertung zeigt „alles seit Anfang".
   `auswertung_alle.py` und `buchauswertung.py` kennen kein Fenster. Die Frage
   „läuft es gerade besser als letzten Monat?" ist heute unbeantwortbar.
2. **Keine Gesamtbilanz.** `spiegel`, `omniquant`, `kopier`, `kopier1zu1` haben
   eigene `auswertung.py` mit eigener Rückgabeform und tauchen in der Übersicht
   von `auswertung_alle.py:417` nicht auf. Niemand rechnet den Gesamtstand.
3. **Die Übersicht täuscht Abdeckung vor.** `supertrend`, `moondev_funding` und
   `iv_wand` stehen in `auswertung_alle.SPUREN` (Z. 48-65), führen aber kein
   Journal; `macd_mtf` nur `handelsjournal.falsch-skaliert-20260915.csv` und ein
   Risikostufen-Journal. Sie liefern dauerhaft einen Strich, der wie „keine
   Trades" aussieht und in Wahrheit „kein Buch" heißt.
4. **Der Bericht ist zu lang und zeigt keinen Verlauf.** `tagesbericht.py:1020`
   fährt 24 Spurenblöcke in fester Reihenfolge ab, alle gleich gewichtet.
   `melder.py:68` vermerkt die 4096-Zeichen-Grenze von Telegram und zerlegt den
   Bericht bereits heute in mehrere Nachrichten. Ein Vortagsstand wird nirgends
   gespeichert: `dauerlauf.py:814-818` baut den Bericht ab 8 Uhr und schickt ihn
   weg.

Dazu ein struktureller Befund: `tagesbericht.py` hat für jede Spur eine eigene
`spur_*()`-Funktion, die liest, rechnet **und** formatiert. `auswertung_alle.py`
liest dieselben Journale ein zweites Mal mit eigener Rechnung. Dieselbe Spur
wird zweimal interpretiert, und die Ergebnisse haben keine gemeinsame Form.

### Was die Journale hergeben

Sechs Spuren haben genug Zeilen, um über der Schwelle `MIN_RUNDEN = 8` etwas zu
behaupten: `spiegel` (1405), `xperp` (125), `scanner` (90), `kopier` (56),
`kraken` (42), `swap` (31).

`nautilus` hat 370 Journalzeilen, davon sind **366 `zyklus`** — eine
Nicht-Handelsaktion. Vier Handelszeilen. Die Spur gehört unter die Schwelle.

Die übrigen Journale liegen bei 1 bis 11 Zeilen.

### Format der Journale

Durchgehend einheitlich bis auf einen Ausreißer: Spalte `zeit` als ISO-8601 mit
explizitem Offset `+00:00` — UTC-aware, nie „Z", nie naiv. Aktionsspalte
`aktion`, mit drei Vokabularfamilien (`kauf`/`verkauf`, `eroeffnen`/
`schliessen`, dazu `gitter` mit `KAUF` und `omniquant` mit `EINSTIEG`/
`AUSSTIEG`).

**Ausreißer `orbk`:** führt nur ein Datum (`2026-09-13`), ohne Uhrzeit, ohne
Zone, und statt `aktion` die Spalte `richtung`. Zeitfenster wirken dort
tagesgenau. Das wird benannt, nicht stillschweigend gerundet.

Lücken fürs Protokoll: `gitter/handelsjournal.mittel.csv` ist leer, `spiegel`
hat keine `.mittel.csv`, `macd_mtf` keine reguläre `handelsjournal.csv`.

## Der gewählte Ansatz

Drei Ansätze standen zur Wahl:

- **A — Schnappschuss-zentriert.** Täglicher Stand je Spur als einzige
  Grundlage. Verworfen: eine später korrigierte Kostenformel rechnet die
  Vergangenheit nicht mit.
- **B — nur Journale.** Kein neues Artefakt, alles bei Bedarf gerechnet.
  Verworfen: dass gestern eine Sperre offen war und heute zu ist, steht in
  keinem Journal.
- **C — Hybrid. Gewählt.** Zahlen aus den Journalen mit Zeitfenster als
  Parameter; dazu ein bewusst dünner Schnappschuss für das, was die Journale
  nicht rekonstruieren können.

C trägt alle vier Punkte, ohne die Journale zu entmachten: die Kostenrechnung
bleibt an einer Stelle und bleibt rückwirkend korrigierbar.

## Die Schichten

**`lage.py` — Erhebung.** Liefert je Spur eine Struktur in *einer* festen Form:
Name, Währung, offene Positionen, Sperrenlage, Kennzahlen im gewünschten
Zeitfenster, Herkunftsvermerk. Formatiert nichts. Die Spureneigenheiten — welches
Feld der Einsatz ist, welches Journal, welches Prüfmodul — wandern aus
`tagesbericht.py` hierher und stehen dann einmal statt zweimal.

**`buchauswertung.py` / `auswertung_alle.py` — Rechnung, bleibt wo sie ist.**
Bekommen das Zeitfenster als Parameter, werden von `lage.py` aufgerufen. Die
Kostenformeln werden **nicht** angefasst.

**`tagesbericht.py` — nur noch Darstellung.** Nimmt Lage-Strukturen entgegen,
wendet die Vorrangregel an, schreibt Text.

Der Gewinn ist nicht Eleganz, sondern dass Wochenbericht, Vortagsvergleich und
Konsolenauswertung dieselbe Erhebung benutzen statt dreier Kopien — sonst driften
die Zahlen zwischen Handy und Konsole auseinander, und man weiß nicht, welche
stimmt.

Der Preis: `lage.py` wird groß, weil 24 Spureneigenheiten irgendwo stehen müssen.
Kleiner als die Summe dessen, was heute doppelt liegt, aber nicht klein.

## Zeitachse, Gesamtbilanz, leere Spuren

**Zeitfenster.** `buchauswertung.lade_zeilen()` und `auswertung_alle.zeilen()`
bekommen `seit`/`bis` und filtern über die Spalte `zeit`. Kommandozeile:
`--seit 2026-09-01` oder `--tage 30`. Ohne Angabe bleibt alles wie heute.

**`MIN_RUNDEN` gilt je Fenster.** Ein Monat mit fünf Runden sagt nichts, und die
Ausgabe muss das schreiben statt eine Zahl zu zeigen — sonst erzeugt die
Zeitachse genau die Scheingenauigkeit, die die Schwelle verhindern soll.

**Verlauf statt Einzelwert.** Die letzten *n* Fenster nebeneinander (Vorschlag:
vier Wochen). Derselbe Aufruf *n*-mal, keine neue Rechnung.

**Gesamtbilanz.** Die fünf Spuren mit eigener `auswertung.py` müssen eine
gemeinsame Mindestform liefern — `{n, ergebnis, treffer, waehrung}` —, damit sie
summierbar werden. Das ist der einzige Eingriff in diese Dateien, und er rührt
die Formeln nicht an, sondern nur die Rückgabe.

Zwei Ehrlichkeitsregeln für die Summe:

- **Währungen werden nicht stumm gemischt.** `kraken` rechnet EUR, der Rest USD.
  Entweder getrennte Summen oder eine benannte Umrechnung.
- **Papier und Live getrennt.** Eine Zahl, die Papiergewinne mit echten
  verrechnet, ist schlimmer als keine.

**Leere Spuren.** Dritte Kategorie **„kein Buch"** neben „belastbar" und „zu
wenige Runden", mit der Angabe, seit wann. Eine Spur, die seit sechs Wochen läuft
und kein Journal hat, ist ein Betriebsfehler, keine Formatfrage.

## Der Schnappschuss

Trägt nur, was aus den Journalen nicht rekonstruierbar ist. Alles andere wäre
eine zweite Wahrheit.

**Inhalt je Spur, vier Felder:** offene Positionen (Instrument, Einsatz,
Einstieg), Sperrenlage, Rundenzähler der Wachen, Stillgelegt-Merker.
Ausdrücklich **nicht**: Bilanz, Trefferquote, Rendite — die kommen aus den
Journalen und werden bei jedem Lesen neu gerechnet.

**Ort:** eine zentrale Datei je Tag unter `stand/JJJJ-MM-TT.json`, **nicht** je
Spurordner. Drei Gründe:

1. `spiegelstand.py:37` prüft genau zwei Dateinamen je Spur
   (`handelsjournal.csv`, `zustand.json`). Ein dritter dort würde die
   Spiegelprüfung verändern — ein Schreibpfadeingriff, den dieser Umbau nicht
   braucht.
2. Der Schnappschuss ist spurübergreifend und gehört nicht in einen Spurordner.
3. Bedingung 4 bleibt unberührt: der Schnappschuss ist abgeleitet, kein Buch.

**Bewusst in Kauf genommen:** ein verlorener Schnappschuss ist unwiederbringlich.
Ein fehlender Vortagsvergleich ist eine Unbequemlichkeit, ein falsch gespiegeltes
Buch ein Schaden.

**Wer schreibt ihn:** derselbe Zweig in `dauerlauf.py:814`, der heute ab 8 Uhr
den Bericht baut — erst Schnappschuss, dann Bericht, der den von gestern daneben
legt. Ein zusätzlicher Auslöser wäre ein zweiter Ort zum Scheitern.

**Aufräumen:** Dateien älter als 90 Tage werden beim Schreiben entfernt.
`stand/` gehört in die Ausschlussliste der `.gitignore` — Laufzeitdaten.

## Guthabenabgleich

Echten Börsenzugriff haben genau drei Spuren: `kraken/kraken.py`,
`scanner/okx.py`, `xperp/okxf.py`. Die übrigen 21 führen Papierbücher. Für sie
gibt es nichts abzugleichen, und ein „Abgleich" gegen ein leeres Konto wäre eine
Zahl, die Vertrauen erzeugt, ohne etwas zu prüfen.

**Für die drei Live-Spuren:** Buchbilanz gegen Kontostand, plus Differenz und
Vorzeichen. Ziel ist nicht Übereinstimmung — die kann es bei offenen Positionen
gar nicht geben —, sondern die **Erklärbarkeit der Differenz**: Bilanz plus
gebundener Einsatz plus nicht verbuchte Gebühren sollte den Kontostand ergeben.
Bleibt ein Rest, ist er der Fund. Eine systematisch danebenliegende Kostenformel
zeigt sich hier als wachsender Rest und sonst nirgends.

**Für die 21 Papierspuren:** keine Zeile, sondern „Papierbuch" — dieselbe
Ehrlichkeitsregel wie „kein Buch".

**Abruf nur beim Schnappschuss**, einmal täglich, nie beim Berichtbauen. Der
Bericht darf nicht am Netz hängen; `tagesbericht.py` ist ausdrücklich so gebaut,
dass der Rahmen ohne Netz steht. Fällt der Abruf aus, trägt der Schnappschuss
den Ausfallgrund statt einer Zahl.

**Reihenfolge:** zuletzt. Der einzige Teil mit Außenabhängigkeit; alles andere
funktioniert ohne ihn.

## Der Bericht

**Vorrangregel**, drei Ränge:

1. **Braucht Aufmerksamkeit** — Ausfall beim Einsammeln, neu geschlossene Sperre,
   Position jenseits einer Schwelle, Spur stillgelegt, Herzschlag zu alt. Voller
   Block.
2. **Hat sich bewegt** — offene Positionen, seit gestern geschlossene Runden.
   Voller Block.
3. **Der stille Rest** — **eine Sammelzeile**, die zählt und benennt:
   „18 Spuren still: macd_mtf, squeeze, …".

Der Bericht fällt damit von ~24 Blöcken auf typischerweise fünf bis acht plus
eine Zeile, und `melder.py` muss ihn nicht mehr zerhacken.

**Vortagsvergleich.** Der Schnappschuss von gestern wird daneben gelegt. Gezeigt
wird die *Differenz*: neue Position, geschlossene Position, Sperre auf/zu,
Rundenzahl gestiegen. Fehlt der Vorgänger, steht das als Satz im Bericht und der
Bericht baut trotzdem.

**Zahlen im Bericht.** Je Spur eine Kennzahlzeile im Fenster der **letzten sieben
Tage**, nicht „seit Anfang". Unter `MIN_RUNDEN` steht „zu wenige Runden (3)"
statt einer Zahl. Bei den heutigen Journalgrößen wird das die Mehrheit der Zeilen
sein — kein Mangel, sondern die ehrliche Auskunft, und es macht die sechs Spuren
mit Substanz zum ersten Mal sichtbar.

**Zwei Berichte:**

| | wann | Inhalt |
|---|---|---|
| täglich | ab 8 Uhr, wie heute | Ränge 1 und 2, Sammelzeile, Vortagsdifferenz |
| wöchentlich | montags | Vierwochenverlauf, Gesamtbilanz getrennt nach Papier und Live, Guthabenabgleich der drei Live-Spuren, Kategorien „zu wenige Runden" und „kein Buch" |

Beide aus derselben Lage-Struktur, zwei Darstellungsfunktionen. Der
Wochenbericht hängt am selben Zweig in `dauerlauf.py`, mit einer
Wochentagsprüfung daneben.

## Fehlerverhalten

Die Regel aus `tagesbericht.py` bleibt: jede Spur wird einzeln eingesammelt, ein
Ausfall steht als Zeile im Bericht, die anderen kommen trotzdem. Drei neue
Ausfälle bekommen dieselbe Behandlung — fehlender Vortagsschnappschuss,
gescheiterter Guthabenabruf, unlesbares Journal. Alle drei erzeugen einen Satz,
keinen Abbruch.

## Prüfung

`unittest`, unter `tests/`, wie im Baum üblich.

- `lage.py` gegen erfundene Journale in einem Temp-Ordner: Zeitfenster schneidet
  richtig, `MIN_RUNDEN` greift je Fenster, `orbk`s Nur-Datum-Format wird
  tagesgenau behandelt.
- **Gesamtbilanz: Währungen werden nicht stumm addiert, Papier und Live bleiben
  getrennt.** Der Test, der den gefährlichsten Fehler dieses Umbaus abfängt.
- Vorrangregel: Spur mit neuer Sperre landet in Rang 1, stille Spur im
  Sammelrest.
- Vortagsvergleich mit fehlendem Vorgänger baut einen vollständigen Bericht.
- Schnappschuss schreibt ausschließlich nach `stand/`, in Tests in einen
  Temp-Ordner. Kein Test fasst ein echtes Ziel an; `journal_zweitziel` wird
  nirgends berührt, weil der Schnappschuss kein Buch ist.

**Bedingung 4:** Der Umbau fasst keinen Journal- oder Zustandsschreibpfad an —
`auswertung_alle.py` und `tagesbericht.py` lesen heute nur und lesen danach nur.
Trotzdem läuft `spiegelstand.py` danach einmal als Nachweis. Billig, und es
schließt die Frage, statt sie zu behaupten.

## Ausdrücklich nicht in diesem Entwurf

- **Die Kostenformeln.** Keine Zahl in `buchauswertung.py` oder
  `auswertung_alle.py` wird geändert. Zeigt der Guthabenabgleich einen Fehler,
  ist das ein Befund für eine eigene Runde.
- Die Punkte aus `BEFUND-hygiene-2026-09-17.md` (CI, `xperp`-Doppelwahrheiten,
  die drei Review-Dokumente).
- Themen 2 und 1 — Betrieb/Überwachung und die neue Spur.
- Die leeren Spuren **reparieren**. Der Entwurf macht sichtbar, dass
  `supertrend`, `moondev_funding` und `iv_wand` kein Buch führen; warum, gehört
  zu Thema 2.
