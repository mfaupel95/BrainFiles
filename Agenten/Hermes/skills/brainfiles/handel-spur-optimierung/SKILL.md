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
10. **Grenzen der Aenderung nennen.** Ein Eingangsfilter wirkt nur auf NEUE
    Positionen; offene laufen unter ihren gebuchten Stops und Fristen aus. Die
    naechste Auswertung ist deshalb GEMISCHT und taugt nicht als Beweis der
    Wirkung — dafuer braucht es Tage neuer Positionen. Das sagen, statt eine
    Zahl zu deuten.

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
- **Nur Schluessel tunen, die die Spur WIRKLICH liest.** Vor dem Bau einer
  Suchtabelle messen, welche Namen in `<spur>/handeln.py` als `w.get("...")`
  vorkommen und welche davon in der `wachen.json` stehen. Ein geratener Name
  wirkt nicht: alle Kandidaten sind identisch und die Suche meldet "kein Hebel",
  obwohl nie etwas veraendert wurde. Der Optimierer prueft deshalb jeden
  Suchschluessel gegen die `wachen.json` und bricht mit Namensliste ab.
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
