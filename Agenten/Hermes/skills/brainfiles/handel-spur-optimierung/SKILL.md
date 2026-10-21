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
   Reisst keine die Schwelle, ist die Landkarte selbst das Ergebnis, und das
   Verdikt lautet "derzeit kein optimierbarer Track" - ein Befund, keine
   Verweigerung.

   ## Kandidatensweep: Fenster fixieren, Klone zusammenfassen, beide Fenster fordern

   Ein Sweep ueber N Kandidaten (Strategie-Dateien, Parameter, Filter) hat drei
   Fallen. Alle drei lassen die schoenste Zahl entstehen, ohne dass eine Aussage
   dahintersteht - alle drei kommen VOR der Empfehlung, nicht danach.

   1. **Ein Fenster hat Anfang UND Ende - eine Tageszahl allein ist keins.** Ohne
      festen Endpunkt laeuft jeder Lauf bis "jetzt", und zwei Laeufe derselben
      Tageszahl sind zwei verschiedene Marktstuecke (gemessen: gleiche Strategie,
      gleiche Kerzenzahl, 3,25 h Versatz an beiden Enden, +117,04 gegen +187,47 -
      dieselbe Regel auf anderen Kerzen, keine bessere Regel). Also beide Laeufe auf
      denselben Endpunkt setzen (dann sind die Fenster ineinander enthalten) und die
      **Zeitstempel** beider Laeufe gegenhalten, nicht die Tageszahl.
   2. **Identische Zahlen heissen: ein Signal, N mal abgeschrieben.** Fuenf
      Kandidaten eines 42-Dateien-Sweeps lieferten exakt gleiche Rundenzahl, Quote
      und gleiches Ergebnis auf drei Nachkommastellen - dieselbe Regel unter
      anderem Dateinamen. 42 Zeilen waren 31 Regeln, und die "besten" Kandidaten die
      am staerksten geklonten. Nach jedem Sweep die Zahlen tupeln, Gruppen bilden
      (`(pnl, runden, treffer)`) und je Gruppe EINEN Vertreter bewerten. Eine Quote
      von 100 % bei 1-2 Runden traegt keine Information - die Rundenzahl daneben
      ist die Aussage, und dieselben zwei Runden in zwei Fenstern bleiben dieselben
      zwei.
   3. **Das Auswahlkriterium ist das WACHSEN ueber die Fensterlaenge, nicht das
      Vorzeichen in einem Fenster.** Eine Kante, die im langen Fenster schrumpft, war
      ein Zeitraum, keine Regel (28 Tage +187 gegen 42 Tage -18,59 bei 29 Runden).
      Nur eine Kante, die mit dem Fenster waechst, uebersteht beide (gemessen: +64
      gegen +244 bei 71,4 % Treffer und dem niedrigsten Drawdown der Positivliste).
      Also beide Fenster fahren und die **Differenz** ansehen - schrumpfend =
      verworfen, wachsend = Kandidat. Und die Grenze mitnennen: 14 Runden sind kein
      Beleg fuer Hebel, das Verdikt lautet dann "Kandidat", nicht "traegt".

   **Reihenfolge der drei Schranken: Klone erst auszaehlen, dann die Rundenzahl
   lesen, dann das Wachstum.** Wer mit der PnL-Spalte beginnt, landet bei der
   Klongruppe. Nach dem Sweep die Zahlen tupeln und je Gruppe EINEN Vertreter
   bewerten - dann erst ist die Rundenzahl dieses Vertreters aussagekraeftig.

   **Die beiden Kandidaten mit dem hoechsten PnL sind meistens dieselbe Regel
   unter anderem Dateinamen - und der Klon mit dem hoechsten PnL verliert im
   langen Fenster am meisten.** Gemessen bei 42 Dateien: `rsi_30` fuehrte mit
   +680,85 (2 Runden), dieselben 2 Runden aber -236,04 im langen Fenster. Ein
   Vorzeichen auf 1-2 Runden ist ein Vorzeichen ueber 1-2 Runden.
1. **Messen, nicht erinnern.** Vor jeder Aussage die vorhandene Auswertung
   fahren: `<spur>/auswertung.py`, sonst `auswertung_alle.py`. Immer getrennt
   ausweisen: nach Kosten UND vor Kosten, echte Handelsrunden getrennt von
   Stoerungen (ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung). Ein
   frueheres Lesebild darf kippen, wenn die Stichprobe waechst — die groessere
   Stichprobe gewinnt.

   **Die Zahl, ueber die ein SPUR-URTEIL faellt, ist der GEBUEHREN-EXCESS —
   nicht `mean%` und nicht die Trefferquote.** Reihenfolge und Auslesefragen
   stehen in `handel-spuren/references/edge-und-statistik-audit.md`; hier nur
   die Kurzform, weil sie bei JEDER Optimierung anfaellt: Excess gegen
   BUY & HOLD des eigenen Instruments, dann gegen die Gebuehr der Boerse der
   Position, und die drei Alarme der Echtheit (Haltedauer im Aufrufertakt,
   ein Instrument traegt die Stichprobe, identische Einstiegspreise je
   (Instrument, Tag) = Preis uebernommen statt geholt). Weicht der Excess
   zwischen kurzen und langen Runden um mehr als ein paar Prozentpunkte ab,
   misst die Zahl die Auswahl — das ist ein Befund ueber die Auswahl und
   entwertet die Gesamtzahl, auch wenn sie gross aussieht.
   Und: **eine gute Kennzahl ersetzt die Sperrenkette nie.** „Darf handeln"
   ist eine Aussage ueber den Boersen-Stop und das Freigabefenster, nicht
   ueber die Performance; eine Spur mit sauberem Excess bleibt abgeschaltet,
   wenn ihr Schalter das sagt.

   **Beim Buch-gegen-Boerse-Abgleich zuerst das `modus`-Feld jeder Position
   lesen, bevor ein fehlender Stop als Befund gilt.** Eine Position mit
   `modus: papier` im Buch braucht keinen Boersen-Stop - ein fehlender Stop
   dort ist kein Befund, sondern der erwartete Zustand (gemessen:
   moondev_marktlage fuehrte eine BTC-Position als papier, die offenen Orders
   zeigten keinen BTC-Stop, alles korrekt). Erst die live-Positionen
   (`modus: live` oder fehlendes Feld bei einer Spur, die live laeuft) gegen
   die Boerse pruefen. Umgekehrt: eine live-Position, deren Boersenmenge
   deutlich vom Buch abweicht (Buch 244 gegen Boerse 2653,9 Kontrakte), ist
   ein echter Befund - entweder eine fremde/Hand-Position auf dem Konto oder
   ein abgedriftetes Buch. Nicht raten, gegen die Order-Historie klaeren.

   **Ein Audit ueber das GESAMTE Journal misst Altbestand - die
   Datenabdeckung gehoert an die Seite der Zahl.** Ein Echtheits-Alarm
   (identischer Einstiegspreis je (Instrument, Tag)) und der Excess rechnen
   ueber alle Runden seit Spurbeginn; liegt der letzte Fehlvorfall VOR einem
   Fix, meldet der Alarm einen behobenen Fehler weiter und die tolle Zahl
   beschreibt die Vergangenheit (gemessen 10.10.2026: 182 von 190
   Scanner-Kaeufen stammten aus der Zeit vor dem Preis-Fix, der Excess
   +7,48 % war Altbestand, kein heutiger Edge). Drei Bausteine gehoeren in
   jedes solche Werkzeug: (1) Alarme mit Zeitfenster
   (`PREIS_FENSTER_TAGE`, Standard 14) - ein Vorfall, dessen letzter Fall
   aelter ist als das Fenster, kann die heutige Statistik nicht verzerren,
   ein frischer Fehler schlaegt sofort wieder an; (2) eine `nNeu`-Spalte
   (Runden mit Einstieg in den letzten N Tagen), damit sichtbar ist, wie
   viel der Zahl aktuell ist; (3) ein "Statistik ALT"-Befund bei >80 %
   Altbestand statt stiller Gesamtzahl. Vor jeder "Spur ist gut/kaputt"-
   Aussage erst zaehlen: wie viele Runden sind juenger als das Fenster?
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

   **Der Test prueft die EIGENSCHAFT, nicht den Schalterstand.** Wird eine
   Freigabe umgestellt (Papier/Live, `handel_erlaubt`, `freigabe.erfuellt`),
   wird ein Test rot, der `assertTrue(w["handel_erlaubt"])` traegt - und das ist
   kein Defekt, sondern der Schalter, der seine Arbeit tut. Ein solcher Test ist
   eine ZWEITE Wahrheit ueber eine Zahl, die die Wache selbst traegt; bei jeder
   Umstellung meldet er "geaendert", nicht "kaputt", und trainiert den Reflex,
   rote Tests wegzuklicken. Umstellen heisst: **Form pruefen, nicht Stand**
   (`assertIsInstance(w["handel_erlaubt"], bool)`), die inhaltlichen Regeln
   daneben stehen lassen (Boerse, Hebel, Instrument, Grenzwerte) und im
   Kommentar festhalten, WANN und WARUM umgestellt wurde - sonst liest die
   naechste Sitzung den Kommentar als Hausregel und schliesst wieder auf.
   Gegenprobe: Schalter testweise auf den anderen Wert setzen, der Test muss
   gruen bleiben. Genau so ist belegt: 8/8 gruen in BEIDEN Schalterstellungen,
   waehrend `assertTrue` bei der einen rot war.

   **Der Applier fuer die wachen.json steht in `references/wachen-applier.md`** -
   gezielter Feldersatz im Text, `json.loads` als Pruefung, `count == 1` je
   Feldersatz, Komma an der Vorzeile, Erklaertext mitziehen. `json.dumps` als
   Schreibweg normalisiert die ganze Datei und erzeugt einen Diff ueber hunderte
   Zeilen fuer drei Felder.
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
`handel-spur-studie` unter `references/backtest-fundament.md` (dort liegen auch
`historie_binance.py`, `replay.py`, `optimieren.py` und der Zuschnitt fuer Spuren
ohne Kerzenreihe). Er beantwortet
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
- **Eine AUFTRAGSBANDZAHL ist selten die Filterachse.** „Alle Spuren mit 1-3
  Takeprofit", „mit Quote ueber 50 %", „ab 2R" bezeichnen Merkmale
  GESCHLOSSENER Runden; ein Mechanismus, der eine OFFENE Position
  veraendert, haengt am Buch (Einstieg, Stop, Kurs). Bandzahl als Relevanz
  beantworten, Mechanismus an den Zustand haengen; Gegenprobe: dieselbe
  Position mit verschiedenem `ziel_r` rechnen — gleicher Stop heisst: das
  Band war nie die Achse. Herleitung und vier Schranken (Trigger in R,
  nur schuetzende Richtung, nie ueber die Liquidationsmarke, Mindestabstand
  zum Kurs) in `references/trailing-stop-gehebelt.md`.
- **Der Trailing-Stop muss die MENGEN-Deckung pruefen, nicht nur die
  Kennung.** `references/trailing-stop-gehebelt.md` fordert in Abschnitt 5.1
  als ERSTE Reihenfolge „Buch gegen Boerse, und zwar je MENGE - erst
  zusammenfuehren, dann trailingen". Der Grund: eine Position, die an der
  Boerse in MEHREREN Schutzauftraegen liegt (die Menge aufgeteilt, weil
  nachtraeglich nachgesetzt wurde), ist nicht trailingbar - der engste
  feuert zuerst, die anderen bleiben als Waisen zurueck.
  **Ein Treffer genuegt nicht.** „Die Position hat einen `stop_id`" ist die
  ZUSTANDSAussage; die Schutzfrage ist die MENGE. Messbar als
  Deckungsgrad (gedeckte Kontrakte / Buchmenge), Bedingungen fuer „geschuetzt"
  sind `reduceOnly` + Gegenrichtung + eine Ausloesung.
  GEMESSEN 05.10.2026 an `trailing.py` (318 Zeilen, 19/19 Tests gruen): die
  sechs anderen Regeln der Seite sind einzeln verdrahtet und einzeln getestet
  (Trigger, Hochstand statt Kurs, Mindestabstand, Richtungszwang,
  Liquidationsmarke) - aber `verdrahtung()` reicht fuenf Zahlen durch,
  `menge` wird nur zum Bestellen benutzt, ein Deckungsgrad wird NICHT
  geprueft, und kein Test fuehrt Mengen-Deckung. Auch in der Verdrahtung der
  aufrufenden Spur (`xperp/handeln.py`, Funktion `_trailing_versuch`) steht
  `stopdeckung` dreimal - **alle drei als Fehlertext, keines als Aufruf**.
  Das ist kein Widerspruch zur Referenz, sondern ihre Reihenfolge:
  Abschnitt 5 sagt „pruefe das, BEVOR du verdrahtest". Die Verdrahtung war
  gebaut, die Vorpruefung fehlt.
  Gegenprobe, die gehoert: eine Position mit GETEILTER Deckung muss
  abgelehnt werden (Meldung: erst zusammenfuehren), dieselbe Position mit
  voller Deckung darf durch. Ohne diese Gegenprobe ist ein Trailing-Code
  gruen, der genau den Zustand erzeugt, den `xperp/stopdeckung.py` am
  05.10.2026 mit 19 ungedeckten Kontrakten aufgedeckt hat.
- **Nach einem Signaturumbruch JEDE Aufrufstelle pruefen, nicht die
  umgebaute.** Ein `return (wert, grund)` statt `return wert` macht jeden
  Aufrufer zum `TypeError`, und wenn der Aufrufer es abfaengt, tarnt das den
  Fehler als Testfehler: sieben echte Fehler sahen wie Testfehler aus. Nach
  dem Umbruch `search_files` nach dem Funktionsnamen und jede Stelle gegenlesen.
- **Eine Funktion gibt IMMER dieselbe Form zurueck — auch im Erfolgsfall.**
  Ein `return (kandidat, grund)` mit `kandidat=None` im Missfall und ein nacktes
  `return {...}` im Erfolgsfall zwingt jeden Aufrufer zu `isinstance(...)`,
  und diese Verteidigung verbirgt den naechsten echten Fehler in derselben
  Zeile.
- **Ein Datenstand, auf dem eine Gegenprobe laeuft, ist selbst eine
  Voraussetzung — und verfällt still.** Ein Backtest-Gegenvergleich bricht mit
  „nichts geprueft" ab, wenn die Historie zu duenn ist (gemessen: 3 von 30
  noetigen Tagesreihen, davon 10 Tage alt — beide Gegenproben meldeten 0
  gepruefte Punkte, alle Tests sonst gruen). Das ist KEIN Defekt der Spur und
  kein Defekt der Gegenprobe, sondern ein Befund ueber die Datenmenge: als
  solcher melden (Reihen auf der Platte, ihre Anzahl, das Alter der jüngsten
  Kerze), mit Vermerk, wo sie nachgefüllt wird. Ein `grep` nach dem
  Nachladeaufruf zeigt die eigentliche Ursache: ein Datenstand, den nur ein
  Handgriff fuellt und den keine Routine auffaellt, waechst nie von allein.
  Daraus folgt die Wache-Regel unter `wirkung-nachweisen` — melden, nicht
  nachladen. Ob ein Nachladeaufruf im Baum überhaupt existiert, beantwortet
  eine Volltextsuche ueber `Agenten/Routinen/` und `Agenten/Hermes/scripts/`
  (`search_files`, Muster der Funktionsname des Nachladens). Laeuft der
  Befund in einem Worktree, zuerst gegen den HAUPTBAUM pruefen: dort fehlen
  die Reihen nicht.
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
- **`optimieren.py` verlangt `lade_wachen()` im Spurenmodul - nicht jede Spur
  hat es.** Der Lauf bricht sofort mit `replay.spur_modul(...).lade_wachen()`
  ab, wenn die Spur zu einer anderen Familie gehoert (gemessen: trendwende_btc
  hat kein `lade_wachen`, die Indikator-Spuren schon). Vor dem Start pruefen,
  dass das Modul die Funktion traegt (`grep -n 'def lade_wachen' <spur>/*.py`),
  sonst ist der Lauf eine sofortige Leiche und die anderen Spuren laufen
  scheinbar parallel weiter, waehrend nur der eine Job tot ist. Eine Spur ohne
  `lade_wachen` ist kein Optimierer-Kandidat, auch wenn sie in `spur_opt.json`
  steht - das ist ein Befund ueber die Spur-Familie, kein Fix am Optimierer.
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
- **Ein kurzes Fenster ist kein Urteil — die volle verfuegbare Historie fahren,
  bevor eine Spur beurteilt wird.** Der Standard-Backtest (`--kerzen 3000` =
  ~125 Tage) ist ein guenstiger Ausschnitt, kein Beleg: gemessen an squeeze
  war das 125-Tage-Fenster positiv (+0,345 USD/Runde, Quote 45 %), das volle
  716-Tage-Fenster negativ (-0,102 USD/Runde, Quote 38,6 %). Ein positives
  kurzes Fenster heisst nur, dass der Zeitraum guenstig war. Vor jedem
  Spur-Urteil die volle verfuegbare Historie fahren (bei Binance-Reihen ab
  2021: `replay.lauf_a(spur, gebuehr, lauf, bis_ms=..., wachen_patch=...)` mit
  `bis_ms` auf das Fensterende) und die Quote/Runden beider Fensterlaengen
  nebeneinander nennen — schrumpft die Quote mit dem Fenster, war das kurze
  Fenster der Ausreisser.
- **Haus-Backtest gegen Freqtrade vergleichen heisst: Zeitraum UND Spur
  angleichen.** Die Freqtrade-Referenz (z. B. 541 Runden / -4,45 %) ist nur
  dann squeeze-spezifisch, wenn `hausspur.name = squeeze` in der
  Backtest-Config steht (die HausSpur-Strategie faehrt sonst ALLE Spuren), und
  sie laeuft ueber 716 Tage auf Binance Futures, waehrend der Haus-Backtest
  standardmaessig 125 Tage auf OKX-Spot faehrt. Zwei verschiedene Zeitraeume
  und Boersen sind kein Vergleich — erst beide auf dasselbe Fenster und
  dieselbe Spur bringen, dann die Richtung (nicht die Hohe) gegenhalten.
- **`kosten_wendepunkt.runden_aus_journal(pfad)` gibt ein TUPEL zurueck
  `(runden, zwang)`, nicht die Rundenliste.** `wendepunkt()` nimmt die
  Rundenliste als Argument. Wer das Tupel direkt in `wendepunkt()` steckt,
  bekommt `TypeError: must be real number, not tuple`; wer `runden_aus_journal`
  als `kennzahlen`-Ersatz ruft, findet kein Attribut `kennzahlen`. Die
  Kennzahlen heissen `R, C, p, f_max, ev_ohne, ergebnis_summe` (kein
  `netto_pct_mittel`).
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
- **Eine Gegenprobe, die den geprueften Zweig nie erreicht, beweist nichts.** Bei
  jedem Test gegen einen Ausfuehrer mit Vorbedingungen (leere Warteschlange,
  fehlender Auftrag, keine Daten) enden beide Varianten mit demselben exit 0, und
  der Test gilt als gruen. Gemessen: beide Laeufe stumm, die unterschiedliche
  Zeile wurde nie gelesen. Deshalb den Zweig **direkt nachbauen** (den Import,
  nicht den ganzen Lauf) und beide Fassungen im selben Kontext fahren, bis die
  eine rot ist.
- **Eine Attrappen-Wache, die selbst eine Sperre ausloest, prueft die Sperre.**
  `0.0` in Kill- und Ratschenfelden bedeutet „sofort ausloesen“, nicht „keine
  Schwelle“ — der Test nimmt den Kill-Pfad statt des Signal-Zweigs und meldet
  Erfolg am falschen Ort. Gemessen: drei Laeufe mit Mirror-Aufrufen, alle in der
  Kill-Verzweigung. Sperrfelder weglassen, dann den Weg erneut fahren.
- **In-Sample-Falle.** Alle Regeln stammen aus derselben Stichprobe; die
  Zeithalbierung mildert das, hebt es nicht auf. Ergebnis als Vorschlag
  ausweisen, nie als Beweis.
- **Auswahl nach Ergebnis ist die verfuehrerischste Regel** (nur Vorbilder mit
  belegter Bilanz kopieren). Ohne Zeithalbierung und Mindestzahl Runden je
  Wallet ist das Nachschau-Auswahl — im selben Datensatz kippt sie nach hinten.
- **Ein Audit mit Zeitfenster braucht Tests in zwei Schichten.** Die
  Kern-Logik (z. B. Preis-Gleichheit) mit explizitem `fenster_tage=0`
  pruefen - sonst wandert ein festes Testdatum in das Fenster und der Test
  schlaegt je nach Laufzeitpunkt anders aus (gemessen: Daten vom 19.09.
  lagen bei einem 30-Tage-Fenster am 10.10. noch drin). Die Fensterfaelle
  selbst mit RELATIVEN Daten bauen (jetzt − 60 Tage = still, heute = Alarm),
  nie mit festen Kalenderdaten - ein festes Datum ist eine Uhrzeitbombe,
  die genau dann schlaegt, wenn der Test alt genug ist, um ausserhalb des
  Fensters zu liegen.
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
- **Ein Punktebuch (kein Einsatz) kann eine Live-Freigabe NIE tragen.** Fuehrt
  das Buch keinen Einsatz, ist die Gebuehr dort nicht abziehbar - `netto_positiv`
  aus einem Punktebuch ist nicht kostenbereinigt und sieht gesund aus, waehrend
  jede Live-Runde an der Boersengebuehr verliert (gemessen 14.10.2026: orbk
  +0,180 R/Runde im Punktebuch, aber f_max +0,06 % gegen 1,20 %/Runde Kraken-
  Gebuehr = -1,14 % je Live-Runde). Vor jeder Live-Freigabe `f_max` gegen
  `2 x gebuehr_taker` pruefen; die Wache `Agenten/Hermes/scripts/live-kosten-wache.py`
  (Cron alle 6 h, no_agent) macht das automatisch fuer alle scharfen Spuren
  (Orderweg + handel_erlaubt) und meldet jede, deren f_max die Kosten nicht deckt.
- **Ein Filter, der bei einer Wand-Spur half, uebertraegt sich nicht auf die
  Schwester - erst die Rueckrechnung ueber das Journal fahren.** Der
  Mindest-Zielabstand-Filter (iv_wand, 02.10.) reparierte iv_wand, aber auf
  liq_wand angewandt blieb der Rest negativ (Filter >= 0,3 %: 13 Runden,
  -4,73 %). Ein Filter ist kein universeller Fix: vor der Uebernahme den Filter
  auf dem Journal der Ziel-Spur rueckrechnen (Runden unter der Schwelle
  verwerfen, Summe der verbleibenden pruefen) - nur wenn der Rest positiv wird,
  ist er ein Kandidat. Die Gegenprobe gehoert in den Test, nicht nur in die
  Ueberlegung.

## Nachweis
Ein Optimierungsauftrag ist fertig, wenn (a) die Messung mit Stichprobenzahlen
vorliegt, (b) jede vorgeschlagene Regel beide Haelften und die Gegenprobe
ueberlebt hat oder ausdruecklich „nicht entschieden" lautet, (c) die
Spezifikation freigegeben und committet ist, (d) die Aenderung eine Sicherung
und einen sauberen Diff hat (`git diff --numstat`, gepusht), und (e) die
naechste echte Dauerlauf-Zyklus die Wirkung zeigt.

## Pin auf einen Signalgeber: die Wette ist die Quelle, nicht der Schalter

Eine Spur, die die POSITION eines fremden Laufs spiegelt (z.B. `omnitrade_futures`
ueber `status/<datei>.json`), hat zwei Stellschrauben: welchen Lauf sie spiegelt
(`statusdatei`) und ob sie ordert (`handel_erlaubt` / `freigabe.erfuellt`).
Der Pin ist eine **Produktentscheidung und gehoert gemessen**, nicht gewaehlt -
er wird nur dann umgestellt, wenn der Sweep eine bessere Quelle NAMTlich
begründet. Fuenf Schritte, jeder mit Beleg:

1. **Lauf starten, Quelle pruefen.** Ohne laufenden Lauf liefert die Quelle kein
   Signal und die Spur sammelt null Runden - das sieht wie ein Fehler der Spur
   aus und ist einer der Quelle (gemessen 04.10.: Pin zeigte ins Leere UND alle
   Statusdateien standen auf `stopped`; ein Fix an der Naht allein liefert weiter
   null Runden). Beide Ursachen getrennt beheben und die Reihenfolge benennen:
   Naht zuerst, dann laufender Lauf.
2. **Die Kette belegen, nicht nur den Prozess.** `quelle()` liefert ein TUPEL
   `(daten, kurse, fehler)` - nicht das `daten`-Dict. `signal(daten[inst], w)`
   bekommt die INNERE Map. Wer `daten.get('symbol')` sucht, rechnet nie und
   sieht gesund aus.
3. **`--vorschau` mit `MAXHIRN_ROUTINE=1`.** Nur so meldet die Sperrzeile, was der
   Dauerlauf wirklich sieht. Die Zeile `'<spur> (live) ok'` im Log ist der MODUS
   DES DAUERLAUFS, kein Orderbeleg.
4. **Vor dem Umstellen den Sweep fahren** (siehe Kandidatensweep oben) und im
   `_statusdatei_vermerk` festhalten, welche Zahlen den Pin gestuetzt und welche
   ihn widerlegt haben. Der Vermerk ist das Argument, warum jemand in einem Jahr
   nicht zurueckstellt.
5. **Mit dem Pin auch die Groessengrenze pruefen.** Ein Wachen-Feld kann der
   NOMINALwert fuer genau eine Boersen-Einheit sein und dabei groesser sein als
   das gesamte Kontoguthaben (`max_pro_trade_usd: 90000` = genau 1 Kontrakt
   PF_XBTUSD, waehrend 69,88 USD frei sind). Das ist kein Fehler, aber es heisst:
   die Wache sagt dem Code „du darfst 90.000 einsetzen", und das Guthaben-Tor
   greift erst beim Orderaufbau. Als Vermerk festhalten, BEVOR live geschaltet
   wird - nicht danach.

**Papier bleibt die Voreinstellung, auch wenn die Kante belegt ist.** Ein
Backtest ist eine Messung ueber historische Kerzen; ein Live-Weg braucht zusaetzlich
eigene Runden gegen dieselbe Quelle (T-347) und Guthaben (T-291). Beide fehlen ->
die Spur bleibt Papier, und das ist ein Befund, kein Widerstand.

Regelkatalog, Werkzeugaufruf und Paritaetsprobe: `references/filter-studie.md`.
Kostenschaetung gegen echte Tiefe messen: `references/kosten-slippage.md`.
Wachen-Datei aendern ohne Fremdtext und Ganzdatei-Diff: `references/wachen-applier.md`.
Trailing-Stop an gehebelten Positionen: `references/trailing-stop-gehebelt.md` -
dort auch, WARUM ein R-Band aus dem Auftrag fast nie die Filterachse ist.
