---
name: handel-risikosteuerung
description: "Use when eine Risikoschranke ueber das Buch gebaut wird."
category: brainfiles
platforms: [windows]
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Handel, Risiko, Deckel, Wachen, BrainFiles]
    related_skills: [handel-spuren, handel-spur-optimierung, trugschluesse]
---

# Risiko ueber das ganze Buch steuern

## When to Use

- Ein Konzentrationsdeckel wird verlangt („kein Instrument darf mehr als X %
  tragen"), oder eine bestehende Grenze soll je Basis gelten.
- Eine offene Position liegt ohne Schutzstop im Buch.
- Eine stehende Wache soll Belastung, Konzentration oder fehlenden Schutz melden.
- Vor einer Kapitalentscheidung oder einem Bericht ueber das Haus gefragt wird:
  „auf was liegt eigentlich das meiste Geld?".

## Wann
Eine Schranke ueber **alle** Spuren, nicht ueber eine: Deckel auf Konzentration
(„kein Instrument darf mehr als X % tragen"), Gruppierung nach Basis, ein
Schutz auf einer bereits offenen Position, oder eine stehende Wache, die
Belastung meldet. Abgrenzung: eine einzelne Spur anbinden/auswerten steht in
`handel-spuren`, eine Spur mathematisch verbessern in `handel-spur-optimierung`,
Zustaende belegen statt vermuten in `trugschluesse`.

Die Hausregel gilt unveraendert: **kein Geld selbst bewegen.** Jede Massnahme,
die eine bestehende Position schliesst, ist eine Order und gehoert in die
Freigabekette — eine Schranke bauen heisst nie, eine Position aufzurueumen.

## Reihenfolge — nicht abkuerzen

1. **Das Buch lesen, nicht die Notizen.** Alle Risikostufen einbeziehen: Basis,
   `.mittel`, `.hoch` sind drei Buecher, aber **ein** Haus. Ein Deckel, der nur
   die Basis sieht, ist an den Tagen falsch, an denen eine andere Stufe laeuft.
   Je Position gehende Felder sammeln: Instrument, Seite, Einstieg, Stop, Nominal.
2. **Zwei Linsen trennen und beide nennen.** *Risiko* = Abstand Einstieg/Stop auf
   das Nominal. *Kapital* = das Nominal selbst. Beide addieren sich je Position
   korrekt (jede Position hat ihren Stop); gestapelt ist das **Kapital auf einer
   Basis**. Die Differenz zwischen SpURENSUMME und BASIS-SUMME ist deshalb
   **keine** „Doppelzaehlung" — wer sie so nennt, hat die Rechnung nicht
   verstanden und korrigiert dann die falsche Zahl.
3. **Nach kanonischer Identitaet gruppieren, nie nach dem Symbol-String.** Alle
   Schreibweisen einer Basis fuehren auf EINEN Namen: Perp-Suffix (`-SWAP`),
   Perp-Bindung (`_UM_XPERP`), Quote-Anhaenge (`-USDC`, `-USDT`, `-USD`, `-EUR`)
   und boerseneigene Abweichungen (Krypto-Bitcoin heisst je nach Boerse `BTC`
   oder `XBT` — beide gehoeren zusammen). **Ein Deckel, den man mit einem
   anderen Namen umgeht, ist kein Deckel.**
4. **Eine Position ohne Schutzstop ist kein Befund nebenbei, sie ist der
   Befund.** Sie ist nicht risikofrei, sie ist der **ganze Einsatz** offen. Sie
   gehoert in die erste Zeile der Meldung und in den Betrag, mit dem die
   Gesamtzahl nach der Korrektur sinkt.
5. **Ein Deckel bindet NEUE Einstiege, nie bestehende Positionen.** Wer eine
   Basis einmal ueberschreitet, hat sie schon bezahlt — das Kapital lag schon
   drin. Ein Deckel, der beim Start sofort N Spuren einfriert, ist ein
   Abschaltknopf mit anderem Namen. Bestehende Positionen laufen unter ihren
   gebuchten Stops und Fristen aus; sie zu schliessen ist eine Order.
6. **Der Deckel ist eine Tabelle, keine Zahl.** Je Basis eine Grenze plus der
   Grund im Wachen-Kommentar. Ein Sonderfall ist immer eine Entscheidung, die man
   begruendet — nicht ein Wert, den man nachjustiert, weil eine Basis knapp
   drueber liegt.
7. **Das Tor gehoert an den ORDERAUFruf, nicht in die Signalberechnung.** Eine
   Spur, die ein Signal sieht und es nicht handelt, sieht fuer tot aus; eine
   Stille-Wache wuerde sie als tot melden, ohne zu wissen warum. Am Orderweg
   wird der Einstieg abgelehnt und protokolliert — die Spur laeuft weiter und
   sieht gesund aus. Jeden echten Orderweg pruefen: das gemeinsame Buch
   (`spur_buch.sperren_live()`) **und** der asynchrone Executor. Fehlt die
   Verdrahtung in einem von beiden, ist die Schranke halb gebaut.
8. **Die Wache meldet eine Veraenderung, nie den Stand.** Sonst wird sie
   abgeschaltet und damit blind. Verglichen wird gegen den letzten Lauf, nicht
   gegen gestern.

## Pitfalls

- **Skripte direkt in `Agenten/Handel` brauchen `HANDEL = HIER`, nicht
  `os.path.dirname(HIER)`.** Im zweiten Fall zeigt der Pfad auf `Agenten/`, die
  Spur-Schleife laeuft ins Leere und das Ergebnis lautet „keine offenen
  Positionen im Haus". Das ist schlimmer als ein Absturz: die Zahl sieht aus wie
  ein Befund und ist keiner. Fuer Dateien **unter** `Agenten/Handel/<spur>/` gilt
  weiter `HANDEL = os.path.dirname(HIER)`.
- **Die Merkdatei einer Wache speichert Strings, keine Tupel.** JSON schreibt
  Tupel als Listen und laesst sie als Listen zurueckkommen; der Vergleich
  passt dann nie, und dieselbe Meldung kommt bei **jedem** Lauf wieder — genau
  so wird eine Wache abgeschaltet.
- **Eine geratene Schwelle verfehlt den Wert knapp darunter.** Neben der
  Schwelle immer die **Top-N** unbedingt ausgeben: die Frage „auf was liegt das
  meiste Geld" faellt auch dann an, wenn die Antwort knapp unter der Grenze
  liegt.
- **Die Polaritaet eines Rueckgabewerts ist Teil des Vertrags.** `liefert
  (gesperrt, grund)` und im Test als `(offen, grund)` gelesen heisst: drei
  Tests melden das Gegenteil. Steht im Docstring, und die Testvariable heisst
  nach dem **Wert**, nicht nach der Hoffnung.
- **Pfade aus `__file__`: die Ebenen zaehlen.** `os.pardir` zu oft oder zu
  selten ergibt `ModuleNotFoundError` auf ein Modul, das sehr wohl im Haus liegt.
- **Ein Gate-Schluessel, der beim Aufruf still verworfen wird, sieht wie eine
  Messung aus.** Nach dem Bau immer **zwei** Werte gegen dieselbe Grundlage
  fahren und die Zahlen vergleichen; sind sie gleich, ist nicht der Markt
  schuld, sondern die Verdrahtung.
- **Ein Vergleichsschalter braucht einen Gegenbeweis.** „Der Arm legt seine
  eigenen Dateien an" ist zuwenig — zusaetzlich pruefen, dass der Hauptarm
  unangetastet blieb (Aenderungszeitstempel vorher/nachher).

## Verification

Der Auftrag ist fertig, wenn diese vier Zeilen sichtbar sind:

1. **Wirkung als Zahl.** Gesamtrisiko vor/nach der Aenderung; die Differenz
   muss genau der erklaerte Betrag sein (eine nachtraeglich gesetzte Schranke
   senkt das Gesamtrisiko um `Einsatz − Restrisiko`).
2. **Der Deckel ist nicht umgehbar.** Zwei oder mehr Schreibweisen derselben
   Basis gegen das Tor fahren — alle muessen dasselbe ergeben.
3. **Die Wache schweigt, wenn nichts passiert.** Erster Lauf meldet, zweiter
   schweigt; das Loeschen der Merkdatei laesst sie wieder melden (sonst prueft
   der Test einen Zustand, nicht eine Funktion).
4. **Jede neue Spur hat ihr eigenes Spiegelziel.** Hauptarm und Schattenarm auf
   dasselbe `Q:\`-Verzeichnis zu schreiben erfuellt Bedingung 4 durch
   Ueberschreiben, nicht durch Spiegeln.

Sammelnachweis:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && \
  ./scanner/.venv/Scripts/python.exe basis_deckel.py && \
  ./scanner/.venv/Scripts/python.exe spiegelstand.py
```

## Reference

Wo der Schutzstopf auf einer bereits offenen Position hingehört — je nach
Ausstiegsmodell (Gitter, Trend, Zeitfenster, reiner Notaus) — und wie man die
Distanz aus der Geometrie der Spur ableitet:
`references/schutzstopf-platzierung.md`.