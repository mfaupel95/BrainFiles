---
name: handel-spur-optimierung
description: "Use when eine Handel-Spur mathematisch optimiert wird."
category: brainfiles
platforms: [windows]
---

# Handel-Spur optimieren: messen, belegen, dann aendern

## Wann
Eine Spur soll „besser" werden — Eingangsfilter, Ausstiegsgeometrie, Auswahl der
Vorbilder, Sizing. Abgrenzung: Anbinden/Betrieb/Auswerten einer Spur steht in
`handel-spuren`, der Nautilus-Knoten in `nautilus-okx-handel`, der allgemeine
Nachweis-Ablauf (Sicherung, Diff, Commit, echter Lauf) in `brainfiles-auftrag`.
Dieser Skill ist die REIHENFOLGE und die Beweisregel fuer Parameteraenderungen
an Spuren.

## Reihenfolge — nicht abkuerzen

0. **Ohne benannte Spur: erst die LANDKARTE, dann das Ziel.** Ein Auftrag
   ohne Spur ist keine Absichtserklaerung fuer irgendeine Spur, sondern die
   Frage "wo liegt ueberhaupt ein Hebel". Die Reihenfolge ist dann:
   `Handel/kosten_wendepunkt.py` ueber ALLE Spuren (Spalten: Runden,
   Trefferquote, `f_max` = die Gebuehr je Runde, ab der die Spur kippt) ->
   **Stichprobengroesse** als eigentliches Auswahlkriterium -> Optimierer auf
   EINEN Kandidaten. Die Landkarte sortiert nach `f_max`, entschieden wird
   nach Runden: alles unter 30 Ausstiegen je Haelfte ist "nicht entschieden",
   und dort zu optimieren heisst, Zufall zu polieren. Nur Spuren mit
   echtem Backtest-Vorrat (Jahre, Hunderte Runden) sind ein Ziel. Reisst
   keine die Schwelle, ist die Landkarte selbst das Ergebnis, und das
   Verdikt lautet "derzeit kein optimierbarer Track" - ein Befund, keine
   Verweigerung.
1. **Messen, nicht erinnern.** Vor jeder Aussage die vorhandene Auswertung
   fahren: `<spur>/auswertung.py`, sonst `auswertung_alle.py`. Immer getrennt
   ausweisen: nach Kosten UND vor Kosten, echte Handelsrunden getrennt von
   Stoerungen (ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung). Ein
   frueheres Lesebild darf kippen, wenn die Stichprobe waechst — die groessere
   Stichprobe gewinnt.
2. **Pruefbarkeit aus den Journalfeldern ableiten, nicht aus der Idee.**
   `handelsjournal.csv` traegt: zeit, modus, aktion, kette, wallet, token,
   symbol, preis, menge, einsatz_usd, wert_usd, marktkap_usd, slippage_pct,
   gebuehr_pct, grund. Rueckwirkend pruefbar sind damit Marktkapitalisierung,
   Kette, Wallet, Zeitpunkt. NICHT aus dem JOURNAL pruefbar: das Signalalter
   (steht nur in `ablehnungen.csv`, und dort nur fuer ABGELEHNTE Signale ohne
   Ergebnis).

   **Die Ausstiegsgeometrie haengt NICHT mehr am Journal:** Kerzen aus der
   Historie sind die Preispfade. Stop-Hoehe, Ziel-Vielfaches und Trailing sind
   damit rueckwirkend pruefbar geworden (Backtest, s. unten) - wer sie weiter
   fuer unpruefbar haelt, laesst den billigsten Hebel liegen.
3. **Eine Buchhaltung, nie zwei.** Paarung und Kennzahlen kommen aus der Spur
   selbst: `<spur>/auswertung.py` per `importlib.util.spec_from_file_location`
   mit EINDEUTIGEM Modulnamen laden (alle Spuren besitzen ein Modul
   `auswertung`; ueber `sys.path` gewaenne die zuletzt eingefuegte), dann
   `lade_ausstiege()` und `buchauswertung.kennzahlen()` benutzen. Ein
   nachgebautes Paarungsverfahren liefert andere Zahlen und macht den Vergleich
   wertlos.
4. **Beleg vor Vorschlag.** Eine Regel gilt nur als Vorschlag, wenn ALLE vier
   Bedingungen halten: (a) Zeithalbierung — nach `zeit` sortieren, aeltere 60 %
   Suchhaelfte, juengere 40 % Gegenprobe; (b) Besetzung — mindestens 30
   Ausstiege je Gruppe in JEDER Haelfte; (c) Vorzeichen — in beiden Haelften
   positiv nach Kosten; (d) Vorsprung — in beiden Haelften besser als die
   Restgruppe.
5. **Gegenprobe fahren.** Dieselbe Messung mit der UMGEKEHRTEN Regel (Band
   verschieben statt oeffnen) muss die Gegenrichtung zeigen — sonst ist die
   Zahl ein Artefakt. Ein Test, der nur den Wunschfall prueft, ist kein Test.
6. **Verdikt-Wortschatz:** `traegt` / `nicht entschieden` / `verworfen`.
   „nicht entschieden" ist das ehrliche Ergebnis kleiner Buecher (unter 30
   Ausstiegen je Haelfte) — dort wird KEIN Verdikt erfunden. Junge Spuren
   liefern genau das; so stehen lassen.
7. **Kosten dominieren — und die Kosten selbst sind erst eine Annahme.** Bei
   3–5 % Slippage je Seite liegt das Ergebnis VOR Kosten oft nahe Null und NACH
   Kosten deutlich negativ: dann beherrscht die Annahme das Urteil, nicht der
   Markt. Eine Regel, die nur vor Kosten traegt, ist kein Vorschlag, sondern
   eine Slippage-Korrektur — als solche benennen. Bevor eine
   Ausstiegsgeometrie gegeneinander antritt, wird die Annahme GEMESSEN
   (Ordergroesse gegen echte Pool-Tiefe, mehrere Groessen, Median und
   Perzentile) — Verfahren, Formel und die drei Fallen unter
   `references/kosten-slippage.md`. Passt die Annahme nicht zum Median, aendert
   das nicht das Vorzeichen des Urteils, aber die Aussage „wie schlimm"; das
   getrennt sagen, statt die alte Zahl weiterzutragen.
8. **Design-Gate.** Erst Design, dann Code (Skills `brainstorming`, danach
   `writing-plans`): Messung zeigen -> 2–3 Wege mit Abwaegung und EINER
   Empfehlung -> genau EINE Frage -> Spezifikation nach
   `Agenten/Handel/docs/design/JJJJ-MM-TT-<thema>-design.md` (Selbstpruefung:
   Platzhalter, Widerspruch, Umfang, Mehrdeutigkeit) -> Freigabe abwarten ->
   Plan nach `Agenten/Handel/docs/plans/` -> TDD-Umsetzung. Kein Code vor der
   Freigabe. Vorgemerkte Stufen bekommen einen eigenen Abschnitt in der
   Spezifikation, nicht einen Nebensatz.
   Beim Schreiben des Plans drei Selbstpruefungen, die Zeit sparen:
   **jeden geratenen Bezeichner am Code nachlesen** (Parameternamen, Schluessel,
   Signaturen - ein erfundener Name wirkt spaeter nicht, das Programm laeuft und
   veraendert nichts) und **jeden Codeblock kompilieren** (alle ```python-Bloecke
   extrahieren und `compile()`; ein Plan mit ungueltigem Code laesst den
   Ausfuehrenden den Plan debuggen). Einheiten ausdruecklich nennen - Index oder
   Zeitstempel, Prozent oder Anteil -, denn die falsche Einheit ergibt kein
   Fehlerbild, sondern ein still falsches Ergebnis. Dazu die **Laufzeit der
   geplanten Tests** ueberschlagen: ein Test, der je Aufruf eine grosse
   Datenreihe durchrechnet, macht die Suite unbrauchbar - Fenster oder
   Reihenlaenge als Parameter vorsehen. Ein Plan, dessen Tests Stunden dauern,
   wird umgangen statt ausgefuehrt.
9. **Aendern (Stufe 1).** Sicherung `<datei>.bak-JJJJMMTT` -> byte-genauer
   Ersatz (Rohbytes lesen, Zeilenende erhalten, `wb` schreiben) -> Beleg:
   `git diff --numstat` zeigt `1 1` bzw. `2 2`; zeigt es die ganze Datei,
   zuruecknehmen und neu patchen. Den Grund der Aenderung in den Erklaertext der
   Wache schreiben (jeder Wachen-Wert traegt seinen Grund) -> committen und
   pushen -> den naechsten Dauerlauf-Zyklus als Live-Beleg lesen.

   **Jeden ABGELEITENEN Wert mitziehen — er faellt still.** Ein Wachen-Feld
   traegt die Herleitung seines Nachbarn im `_`-Erklaertext; aendert man eines,
   wird der andere ungueltig, ohne dass irgendetwas einen Fehler meldet.
   Gefordert ist `max_pro_trade_usd >= risiko_je_position_usd /
   pflicht_stop_prozent_min`. Senkt man den Mindeststop von 5,0 auf 3,0 %, sind
   das 5,0 / 0,03 = 166,67 statt 100 — ein Deckel von 150 haette das Risiko je
   Position still auf 4,50 statt 5,00 USD geschrumpft. Der Gross-Nominal im
   Journal ist die einzige Spur: er steht auf `min(risiko/stop, deckel)` und
   laesst sich rueckwaerts auf den wirksamen Deckel zurueckrechnen.

   **Jeden Werten-Feld testweise zuruecksetzen (Gegenprobe), bevor „fertig"
   gemeldet wird.** Ein Test, der eine Handlung prueft, muss auch dann rot
   werden koennen. Den Deckel auf den alten Wert setzen, den Test laufen lassen,
   die Fehlermeldung lesen, zuruecksetzen: ein Test, der nie rot wurde, belegt
   nichts.
10. **Grenzen der Aenderung nennen — vorher pruefen, wohin sie reicht.** Ein
    reiner Eingangsfilter wirkt nur auf NEUE Positionen; offene laufen unter
    ihren gebuchten Stops aus. **Eine Ausstiegsgeometrie erreicht aber auch
    OFFENE Positionen**, wenn die Spur skaliert: `skalieren.skaliere()` rechnet
    Stop und Ziel bei jeder Vergroesserung neu aus dem aktuellen `stop_pct` und
    `r`, ein neues Signal auf demselben Instrument zieht die offene Position also
    auf die neue Geometrie nach. Gemessen: eine Position, eroeffnet unter 5 % /
    2R, trug nach der Umstellung auf 3 % / 1,5R `stop_pct` 3,00 und ein um
   gerechnetes Ziel — beide Werte wortgleich auf der Journalzeile. Nur Positionen
    OHNE weitere Skalierung behalten den alten Stand.

    Also vor dem Commit fragen: Skaliert diese Spur? Dann die Wirkung auf die
    offenen Positionen benennen (wer zieht wann nach), statt pauschal
    „wirkt erst auf neue Positionen" zu schreiben. In beiden Faellen gilt: die
    naechste Auswertung ist GEMISCHT und taugt nicht als Beweis der Wirkung.
    Das sagen, statt eine Zahl zu deuten.

## Ausstiegsgeometrie: erst nachrechnen, dann ein zweites Buch

**Reihenfolge.** Zuerst der Backtest - Rezept und Werkzeugfallen stehen im Skill
`handel-spur-studie` unter `references/backtest-fundament.md`. Er beantwortet
Stop-Hoehe, Ziel-Vielfaches
und Trailing ueber Monate bis Jahre in Minuten bis Stunden, mit Walk-Forward und
ungesehenem Prueffenster. Das Schattenbuch ist danach fuer das zustaendig, was
Kerzen NICHT zeigen: Ausfuehrung, Quote-Ticks, Daten ohne freie Historie.

Vorlage fuer das Schattenbuch ist der Risikostufen-Lauf: derselbe Code, eigene Dateien je Ausfertigung
(`*.mittel.json`, eigenes Journal, eigene PID/Log), Eintrag in `SPUREN` UND in
`NUR_BASIS` (sonst laeuft die Spur doppelt). Fuer eine Ausstiegsvariante:
Startskript, das eine Kennung setzt; die Spur erweitert nur die Dateinamen; das
Hauptbuch bleibt UNVERAENDERT (es ist die Vergleichsgrundlage). Ein Arm je
Runde — zwei Arme gleichzeitig kosten den dreifachen Feed-Abruf je Zyklus und
verwaessern das Bild. Messzeitraum bis 30 Ausstiege je Arm. Billige Naeherung
fuer spaeter: `tiefster_kurs` je Position im Zustand mitschreiben (analog
`hoechster_kurs`) — grob, weil die Reihenfolge von Hoch und Tief nicht
rekonstruierbar ist. Wird die Auswertung verfrueht angefragt („alle N
Ausstiege auswerten", bevor die Schwele erreich ist): erst zaehlen, unter 30
je Arm ehrlich „nicht entschieden" sagen (n=1-Token-Falle bedenken), dann
Waechter-Cron bis zur Schwele — vollstaendiger Ablauf in
`references/schattenbuch-auswertung.md`.

## Wenn alles negativ ist: nicht die Geometrie suchen, sondern reihen

Der haeufigste Endstand einer Optimierung ist: **jede Kandidaten-Geometrie ist
negativ.** Dann ist die Reihenfolge:

1. **Am Werkzeug zweifeln, nicht am Markt.** Zwei Laeufe, ein Parameterwert
   verschieden. Bleibt die Zahl gleich, war der Setzer tot und jede weitere
   Messung Muell (`messwerkzeug-gegenprobe`). Gemessen 04.10.2026: `replay.py
   --setzen` wirkte fuer die Kerzenspuren nicht, die Suche haette neunmal
   dieselbe Rechnung gefahren.
2. **Rohzeilen sind keine Runden.** Die Hausfunktion
   `kosten_wendepunkt.kennzahlen()` rechnet die Paarung; eine selbst gezaehlte
   `AUSSTIEG`-Zeile nicht (1181 Zeilen sind 579 Runden). Zwischenstand und
   Ergebnis unterscheiden sich um fast eine Groessenordnung — die Zahl sah
   schlimmer aus, als sie war.
3. **Erst rechnen, wenn der Prozess beendet ist.** Eine geschriebene Datei ist
   ein Zwischenstand mit derselben Form wie ein Ergebnis.
4. **Dann die Hausregeln pruefen, wenn zwei Wege auseinanderlaufen.** Fehlt in
   einem Weg eine Regel (gemessen: die Docht-Regel T-202/T-177 in
   `backtest_prognose`), ist das die Ursache — nicht Stop, Ziel oder Sizing.

Erst wenn das alles geprueft ist und die Zahl **trotzdem** negativ bleibt, ist
das Verdikt „verworfen" ehrlich. Dann **kein Verdikt erfinden**, sondern den
besten Kandidaten ausweisen **und ausdruecklich sagen, dass er noch nicht
traegt**: das ist eine Fehlstellung abgestellt, kein Vorteil gewonnen. Dieser
Satz gehoert in den Vermerk der geaenderten Wache, sonst liest die naechste
Auswertung die Zahl als Freigabe.

**Der Trost fuer die Spur, die nichts erreicht:** eine verworfene Geometrie ist
oft eine Fehlstellung, kein Ergebnis — sie kann um eine Groessenordnung besser
sein als die heutige (gemessen: 5,0 %/2,0R kostete 0,803 USD je Runde,
3,0 %/1,5R nur 0,074, bei 1007 Runden). Ein Wechsel ist trotzdem **kein**
Gewinn, und offene Positionen laufen unter der alten Geometrie aus.

## Tor-Regeln optimieren: erst den BINDENDEN Grund messen

„Erlaubte Volatilitaet erhoehen" heisst nicht, die Zahl zu erhoehen - es heisst,
den Grund zu finden, der die Spur schliesst. Reihenfolge:

1. **Die Sperrgruende aller Spuren sammeln** (`Handel/sperrgruende.py`, sonst
   `spuren_stand.py`): je Spur die Woerter der eigenen `--vorschau`-Sperrzeile.
   Erst das trennt „haengt am Guthaben" von „haengt am Fenster" von „haengt am
   Signal" von „hat gar keinen Live-Pfad".
2. **Den Kandidaten-Kegel messen.** Beim Scanner ist das `scanner/scan.py`: es
   druckt je Markt Score, Chance/Risiko, Volatilitaet und ob alle Tore bestehen.
   Die Verteilung der fraglichen Spalte zeigt, ob dieses Tor ueberhaupt greift -
   und wo die Grenze wirklich liegt.
3. **Zaehlen, was die Lockerung NETTO bringt**: Kandidaten im neu erlaubten Band
   UND ob sie die uebrigen Tore bestehen. Gemessen: 60 Maerkte bewertet, 3 im
   neu erlaubten Band, 0 davon ueber der Score-Schwelle. Die Lockerung war
   richtig (das Tor ist fuer spaeter offen), bringt heute aber keinen Trade -
   genau so berichten, statt „Tor erhoeht" als Wirkung zu verkaufen.
4. **Die Grenze an die Ausstiegsgeometrie koppeln.** Eine Volatilitaets- oder
   Range-Grenze ist nur relativ zum Stop sinnvoll: liegt die Tagesspanne ueber
   dem Stop-Abstand, wird der Stop zum Rauschen. Den Deckel deshalb aus dem Stop
   ableiten (hier 2,0 Tagesspannen, weil der Stop der Spur 7 % betraegt) und die
   Kopplung im Vermerk nennen - sonst ist die naechste Erhoehung wieder ein
   Griff ohne Rechnung. Wer mehr will, muss den Stop mitwachsen lassen (Stop als
   Vielfaches der Tagesspanne) - das aendert die Geometrie und braucht eine
   eigene Messung.
5. **Alle Stellen finden, die DASSELBE Tor sind.** Dieselbe Zahl steht oft in
   der `wachen.json` der Spur UND im Marktscanner (`prognose.json`) UND in
   einer Geschwister-Spur (z. B. `scanner` und `kraken`); ein Tor an zwei
   Stellen mit zwei Zahlen ist zwei Wahrheiten. Jede Stelle nennen und
   mitziehen, je Stelle ein datierter Vermerk.

## Pitfalls
- **Identische Geometrie in mehreren Spuren heisst: nie einzeln optimiert.**
  Tragen N Schwestern-Spuren denselben `pflicht_stop_prozent_min` und
  `ziel_r_vielfaches`, ist das keine Konfiguration, sondern eine kopierte
  Vorgabe. Dann lautet die Frage nicht "was ist fuer Spur X am besten",
  sondern "ist diese Geometrie ueberhaupt richtig" - einmal beantwortet und
  als Hauswert gesetzt. N Spuren einzeln zu optimieren, die dieselbe Zahl
  tragen, vervielfacht die Laufzeit und liefert am Ende N Messungen fuer
  dieselbe Groesse.
- **Der Optimierer schreibt erst am Ende - nicht auf ihn warten.** Ein Lauf
  ueber Jahrzehnte mal neun Kandidaten rechnet weit laenger als ein
  Werkzeug-Timeout (gemessen: ueber 15 Minuten, zwei Prozesse, Ausgabedatei
  0 Bytes, kein Fehler im stderr). Als Hintergrundauftrag starten, den
  unabhaengigen Teil des Auftrags beantworten, das Ergebnis melden lassen,
  sobald es eintrifft. Ein Optimierer, der scheinbar haengt, arbeitet
  meistens - ein leerer stdout ist bei ihm kein Abbruchsignal.
- **Der Backtest kann eine ANDERE QUOTE messen, als die Spur handelt.**
  Der Historienleser bildet `BTC-USDC` auf die USDT-Reihe ab. Bei BTC ist
  der Unterschied unter 0,1 % und das eine dokumentierte Naeherung - aber
  es muss gesagt werden, sonst gilt eine BTC-USDC-Messung als gemessen.
  Vor dem Interpretieren pruefen, welche Reihen wirklich geladen wurden
  (`Historienleser` je Instrument aufrufen und die Laenge vergleichen).
- **Ein Suchschluessel muss ZWEI Pruefungen bestehen: dass die Spur ihn liest -
  UND dass der Schalter beim Aufruf ankommt.** Die erste Pruefung ist billig:
  welche Namen kommen in `<spur>/handeln.py` als `w.get("...")` vor und welche
  davon stehen in der `wachen.json`. Ein geratener Name wirkt nicht, alle
  Kandidaten sind identisch und die Suche meldet "kein Hebel", ohne dass je
  etwas veraendert wurde; der Optimierer prueft deshalb jeden Suchschluessel
  gegen die `wachen.json` und bricht mit Namensliste ab.

  **Diese erste Pruefung genuegt nicht, sie kann gruen sein und es trotzdem
  nichts messen.** Der Schluessel kann in `handeln.py` UND in der `wachen.json`
  korrekt heissen und beim Aufruf trotzdem verloren gehen, weil die aufrufende
  Funktion den Parameter anders nennt (`wachen_patch=` statt `setzen=`) und die
  Aufrufstelle den Schalter nicht mitgibt. Gemessen: zwei Geometrien mit
  BITGLEICHEN Kennzahlen (gleiche Rundenzahl, gleiche Quote, gleiches
  Ergebnis auf drei Nachkommastellen), und beide Wachen-Kopien behielten nach
  dem Lauf die unveränderten Ausgangswerte.

  **Deshalb die zweite Pruefung, die man nicht überspringen darf: vor der
  Suche ZWEI Kandidaten fahren und die Kennzahlen vergleichen.** Sind sie gleich,
  ist nicht der Markt schuld, sondern die Verdrahtung - und die Suche ist bis
  zur Reparatur wertlos, egal was sie spaeter meldet. Danach in der
  Wachen-Kopie des Backtest-Ordners nachsehen, ob der gesetzte Wert dort
  ueberhaupt angekommen ist (`_backtest_gesetzt`): das trennt "Schalter
  verworfen" von "Schalter angekommen, Spur ignoriert ihn".
  **Ein Schalter, dessen Wirkung niemand geprueft hat, ist kein Schalter.**
- **Walk-Forward: EIN Lauf je Kandidat, danach aufteilen** - nicht ein Lauf je
  Fenster. Vergleichsmass ist das Ergebnis je Runde aus der Hausfunktion
  (`kosten_wendepunkt.wendepunkt()` liefert `R, C, p, f_max, ev_ohne,
  ergebnis_summe` - **kein** `netto_pct_mittel`, das stammt aus
  `backtest_prognose.kennzahlen`), **netto nach Gebuehren**.
- **Das Urteil lautet "besser als die HEUTIGE Einstellung", nicht "besser als
  die eigene Suchhaelfte".** Der Vergleich innerhalb eines Kandidaten misst den
  Regimewechsel zwischen den Haelften - gemessen liess er 18 von 18 Kandidaten
  durch und war damit kein Filter. Erst die Grundlinie im selben Zeitraum messen
  (heutige Wachen-Werte), dann jedes auswertbare Fenster gegen sie pruefen,
  mindestens zwei, Mindestvorsprung 0,10 % je Runde.
- **Mindestens 30 Runden je Fenster**, nicht 8: bei ~0,5 % Vorsprung gegen ~5 %
  Streuung ist alles darunter Rauschen. Ein Fenster unter der Schwelle zaehlt als
  "nicht auswertbar", nicht als gewonnen, und die Periode gehoert in den Bericht
  - dieselbe Spur steht ueber 5,7 Jahre bei +0,08 % je Runde netto und im
  12-Monats-Fenster bei -0,99 %.
- **Backtest-Runden sind Messung, keine Freigabe.** Sie zaehlen NICHT fuer die
  Bedingungen in `Wissen/Handelsregeln.md` und gehoeren getrennt ausgewiesen -
  ein historischer Lauf ist keine Live-Erfahrung.
- **Ein Gate-Schluessel kann VERSCHACHTELT liegen.** In `prognose.json` steht
  die Volatilitaetsgrenze unter `tore.max_volatilitaet_pa`, nicht auf der
  obersten Ebene; in der `wachen.json` derselben Spur auf der obersten. Ein
  Ersatz auf der falschen Ebene findet nichts, meldet keinen Fehler und die
  Datei gilt als geaendert. Vor dem Schreiben `count(alt) == 1` asserten,
  danach `json.loads` fahren und die Zahl zuruecklesen.
- **Ein Test gegen eine KONSTANTE der Wachen ist bei jeder Umstellung rot.**
  `assertEqual(w["ziel_r_vielfaches"], 2.0)` meldet nicht, dass etwas kaputt
  ist — er meldet, dass sich ein Wert geaendert hat. Das ist die teuerste
  Testform, weil sie den Rot-Pflicht-Creflex trainiert: man gewöhnt sich daran,
  drei rote Tests als "Umstellung" wegklicken und übersieht dabei echte Fehler.
  **Gefrorene Werte fliegen raus, nicht auf die neue Zahl gesetzt.** Statt
  `assertAlmostEqual(ziel/stop, 2.0)` drei Optionen, in dieser Reihenfolge:

  1. **Gegen die Regel pruefen, die gilt.** `ziel_abstand / stop_abstand` ==
     `w["ziel_r_vielfaches"]` — liest denselben Wert wie der Code, überlebt
     jede Umstellung und schlägt immer noch an, wenn Stop und Ziel auseinanderlaufen.
  2. **Die Zustaendigkeit pruefen, nicht den Zahlenwert.** „Das Ziel liegt
     ausserhalb des Stops" gilt für 1,5 wie für 2,0 — das ist die Eigenschaft,
     die die Geometrie ueberhaupt trägt.
  3. **Nur wo der Wert selbst das Gesetz ist** (ein Freigabe-Schalter, ein
     Risikoprozentsatz als Sicherheitsgrenze) darf der Test den Wert festnageln —
     dann mit einem datierten Vermerk, WARUM er eingefroren ist.

  Merksatz: ein Test, der einen Wert festnagelt, den man selbst setzt, ist eine
  zweite Wahrheit über dieselbe Zahl. Beim Umstellen wird die zweite Wahrheit
  nicht mitgezogen, sondern nur ihre Warnwirkung abgeschaltet.
- **Nach dem Commit `git log` lesen, nicht nur `git status`.** Zwischen
  `read-tree` und dem Commit kann ein fremder Commit landen, der dieselbe Datei
  anfasst; der eigene Commit sitzt dann darauf und sieht vollstaendig aus. Nach
  dem Commit `git diff <fremder-commit> <eigener-commit> -- <datei>` lesen und
  bestaetigen, dass die fremde Arbeit nicht ueberschrieben wurde. Ein fremder
  Commit, der nur zwei Zeilen derselben Datei aendert, ist dabei harmlos und
  wird korrekt ueberbaut — man muss es nur wissen statt zu raten.
- **In-Sample-Falle.** Alle Regeln stammen aus derselben Stichprobe; die
  Zeithalbierung mildert das, hebt es nicht auf. Ergebnis als Vorschlag
  ausweisen, nie als Beweis.
- **Auswahl nach Ergebnis ist die verfuehrerischste Regel** (nur Vorbilder mit
  belegter Bilanz kopieren). Ohne Zeithalbierung und Mindestzahl Runden je
  Wallet ist das Nachschau-Auswahl — im selben Datensatz kippt sie nach hinten.
- **Ein Auswertungswerkzeug schreibt nie in einen Spurenordner.** Test auf
  Tempjournalen mit bekanntem Ausgang, dazu ein Modulwaechter (`setUpModule`
  merkt Dateiliste und Groessen der Spurenordner, `tearDownModule` vergleicht)
  — sonst schreibt ein Testlauf ins echte Buch.
- **Der Dauerlauf ist der einzige Schreiber.** Nie einen Papierzyklus von Hand
  fahren; fuer eine Vorschau `--vorschau` benutzen (schreibt keinen Zustand).
- **Wegwerfskripte in den Arbeitsbaum legen** (`Agenten/Hermes/cache/`), nicht
  nach `%LOCALAPPDATA%\Temp`: ausserhalb `HERMES_WRITE_SAFE_ROOT` wird der
  Schreibvorgang verweigert.
- **Neue Ordner bleiben unversioniert, bis JEDE Whitelist-Ebene freigegeben ist**
  (`!Agenten/Handel/docs/` + `!.../docs/design/` + `!.../design/*.md`); Nachweis:
  `git status --porcelain` zeigt `??` statt `!!`.
- **Die Zeilenenden der .gitignore aus den Rohbytes ableiten** und mit demselben
  Terminator anhaengen; danach `git diff --numstat` pruefen (eine gewollte Zeile
  = `1 1`).
- **Eine Ausstiegsschwelle muss im Haltefenster ERREICHBAR sein — vorher messen.**
  Steht die Trailing-Aktivierung bei +30 %, die Frist bei 168 h, und der hoechste
  Stand des Instruments nach sechs Tagen bei +8,5 %, dann hat das Trailing nie
  gegriffen: der Ausstieg ist die Frist, und gemessen wird „X Tage halten" statt
  der Ausstiegsregel. Die Aktivierung aus dem INSTRUMENT ableiten (Peak ueber das
  Haltefenster der laufenden Positionen), nie aus Stop oder Wunschdenken — sonst
  ist die Regel nicht falsch, sondern nur unerreichbar. Gilt verstaerkt, wenn die
  Spur einen PROXY auf ein anderes Instrument bucht: dann zaehlt die Volatilitaet
  des Proxy (z. B. BTC), nicht die des Signals (Token).
- **Vier Positionen, die Minuten auseinander auf DEMSELBEN Instrument eroeffnet
  wurden, sind EINE Wette.** Fuer jede Auswertung zaehlen sie als ein Datenpunkt;
  als vier gelesen entsteht eine Schein-Stichprobe (gleichzeitige Korrelation,
  zu kleine Streuung). Vor jeder Kennzahl pruefen, ob die Positionen unabhaengige
  Einstiege sind oder ein Vorbild-Signal vervielfacht haben.

## Nachweis
Ein Optimierungsauftrag ist fertig, wenn (a) die Messung mit Stichprobenzahlen
vorliegt, (b) jede vorgeschlagene Regel beide Haelften und die Gegenprobe
ueberlebt hat oder ausdruecklich „nicht entschieden" lautet, (c) die
Spezifikation freigegeben und committet ist, (d) die Aenderung eine Sicherung
und einen sauberen Diff hat (`git diff --numstat`, gepusht), und (e) der
naechste echte Dauerlauf-Zyklus die Wirkung zeigt.

Regelkatalog, Werkzeugaufruf und Paritaetsprobe: `references/filter-studie.md`.
Kostenschaetzung gegen echte Tiefe messen: `references/kosten-slippage.md`.
