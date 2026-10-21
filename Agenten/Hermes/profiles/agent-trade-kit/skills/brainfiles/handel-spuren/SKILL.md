---
name: handel-spuren
description: "Spuren in Agenten/Handel anbinden, pruefen, auswerten."
version: 0.1.0
author: Hermes
category: brainfiles
metadata:
  hermes:
    tags: [Trading, Paper-Trading, Journal, Optimierung]
---

# Handelsspuren

## Wann
Jede Änderung unter `Agenten/Handel/**`: Sperre ergänzen, Freigabe verdrahten,
Analysemodul bauen, Wachenwerte anfassen, Tests schreiben, Spur an fremden Feed
haengen (Kurs-, Signal-, Wallet-Daten).

Welche Spuren es gibt, steht in `dauerlauf.SPUREN` — von dort lesen, nicht aus
diesem Kopf: die Liste aendert sich (kraken war stillgelegt und laeuft wieder als
Papier, orbk kam dazu, omniquant ist eine Papierspur auf dem Prognose-Bericht).

Ausloeser → Referenz:
- Komplett-Neubau einer Spur (von der verifizierten, abgebrochenen Aufgabe bis
  zur laufenden GUI: Vorbilder lesen, bauen, verdrahten, beweisen,
  Dauerlauf-Start): `references/neue-spur-ende-zu-ende.md`
- Bus-Meldung „Ergebniscode 1“ deuten; „nimm die Spur auf Dauerbeobachtung“
  (heisst: sie steht in `dauerlauf.SPUREN` UND jede Positionsaenderung erreicht
  Telegram); Bestandscheck „was ist noch nicht angebunden?“:
  `references/anbindungs-audit.md`
- **Bestehende Spur nachtraeglich in den Takt haengen** (sie hat `handeln.py` +
  `wachen.json`, laeuft aber nicht im Dauerlauf - auch mehrere auf einmal, mit
  allen fuenf Stellen, dem Vertrag des Tagesberichts, der Nachweis-Kette von der
  Warteschlangen-Probe bis zum ersten Zyklus und den Fallen dabei):
  `references/spur-nachtraeglich-anschliessen.md`
- Bilanz deuten, „das heisst, wir haetten X gewonnen?" — ein Papierbuch-Ergebnis
  hat fuenf Fragen, bevor es eine Antwort ist:
  `references/buchergebnis-pruefen.md`
- „Code optimieren", „Suche nach Luecken", „mach das sichtbar" — Pruef- und
  Haertungsweg mit Verdachtsmuster-Checkliste, Fix-Disziplin, Nachweis-Kette:
  `references/spur-haerten.md`
- **Zustandsbericht** („Bericht", „wie laeuft die Spur") — lesend, mit den
  Quellen, den Lese-Fallen (BOM im Bus-Journal, UTC vs. lokal, Vorschau-Lauf je
  Zyklus, kurze Abstaende vs. Luecken) und der Form, die Max erwartet:
  `references/spur-bericht.md`
- Änderung, die **alle Spuren** trifft („das gilt für alle", Bedingung 4, neuer
  Kosten-/Ausstiegsgrund, Befund an mehreren Spuren) — Ausrollweg von Inventar
  bis Commit, inklusive Testaufruf-Falle und versehentlich überschriebener Kopie
  außer Haus: `references/spur-weite-aenderung.md`
- „werte die Daten aus", „optimiere die Strategien" oder eine Freigabe
  (Bedingung 1: 50 Runden netto positiv) — Weg von den Journalen zur EINEN
  belegten Aenderung, mit den Zahlen, die eine Aenderung tragen, und dem, was
  eine duenne Stichprobe NICHT hergibt: `references/auswertung-und-optimierung.md`
- Eine andere Sitzung laesst Arbeit im Baum liegen („wenn die Session fertig ist,
  mitnehmen", eine geaenderte Datei, die man selbst nicht angefasst hat) —
  Fertig-Erkennung, Waechter-Cron, getrennter Commit und die Frage, was eine
  Entscheidung von Max braucht: `references/fremdarbeit-mitnehmen.md`
- **Risikostufen** („mit groesseren Positionen fahren", „zweiter Lauf mit mehr
  Einsatz", „mehr Daten in kuerzerer Zeit", `HANDEL_RISIKO`, `--risiko`,
  `risikostufe.py`): derselbe Handel mit Faktor 1/2/4 auf getrennten Dateien —
  was skaliert wird und was nie, warum eine Stufe nie live geht, kein Telegram
  bekommt und warum der Spiegel aussen vor bleibt: `references/risikostufen.md`
- Uebergeordnete Ansicht ueber ALLE Spuren („GUI fuer meine Handelsspuren"):
  Abschnitt „Ein Fenster ueber alle Spuren".

- **Externe Kennzahlen, die unsere Kerzen nicht hergeben** („Santiment“, aktive
  Adressen, MVRV, Exchange-Zu-/Abfluesse, Social Volume, Dev-Aktivitaet):
  `references/santiment.md` — SanAPI ohne Schluessel, jede Metrik mit eigenem
  Zeitfenster.
- **Schattenbuch-Spur** (dieselbe Signalquelle mit ANDEREN Parametern parallel
  laufen lassen, Hauptbuch bleibt Vergleichsgrundlage — spiegel_knapp/weit):
  `references/schattenbuch-spur.md` — Suffix-Mechanik durch die
  Datei-Konstanten, Launcher je Arm, Verdrahtung inkl. spiegelstand- und
  Bus-Anbindungs-Falle.

## Landkarte (nur was zum Arbeiten nötig ist)
- `Agenten/Handel/<spur>/` — je Spur `handeln.py`, `wachen.json` (die Grenzen;
  nur gelesen, einzige Ausnahme `sperre_zu` true→false), `zustand.json`,
  `handelsjournal.csv`.
- `Agenten/Handel/dauerlauf.py` — 24/7-Treiber. Startet je Spur
  `handeln.py --live/--papier` als Unterprozess und **liest dessen Ausgabe**.
- `Agenten/Handel/freigabe.py` — Bestätigungsfenster am Bildschirm, je
  Vorschlag einzeln.
- `Agenten/Handel/freigabefenster.py` — Zeitfenster fürs Handy (`/ja`, `/nein`,
  `/stop`), eigener Zustand in `freigabe_fenster.json`, nie in wachen.json.
- `Agenten/Handel/prognose.py` — Beobachter über den ganzen Markt in **beiden
  Richtungen** (LONG/SHORT), stellt keine Order, kennt keine Spur, Tore je
  Richtung in `prognose.json`.
- `Agenten/Handel/spiegel/` — Papierbuch auf fremdem Feed (OnchainOS):
  `lesen.py` liest nur, `spiegel.py` bucht nach, kein Orderpfad. Muster fuer jede
  weitere Feed-Anbindung: `references/fremdfeed-papierbuch.md`. Zweite Anbindung
  nach demselben Muster: `kopier/` (Pump.fun-REST, Positions-Spiegel statt
  Transaktions-Stream, mit Einlauf-Regel).
- `Agenten/Handel/CryptoPredictions_Wissen.md` — Wissensdatei des
  Handelsverzeichnisses: Datenquellen fuer historische Krypto-Marktdaten,
  Erklaerungen zu CryptoPredictions. Handelswissen gehoert hierher (anhaengen,
  `.bak-JJJJMMTT` vorher), nicht in neue Dateien.
- Interpreter je Spur: Vorgabe `scanner/.venv\Scripts\python.exe` im
  Handel-Ordner, Aufruf aus dem jeweiligen Spurordner. Spur mit EIGENEM venv
  (z. B. nautilus: nautilus_trader liegt nicht im scanner-venv) traegt im
  SPUREN-Eintrag `"python": os.path.join(HIER, "<spur>", ".venv", "Scripts",
  "python.exe")` — `zyklus_spur` UND `nur_fenster_fehlt` muessen
  `d.get("python", PYTHON)` respektieren (beide Stellen: die Vorschau-Frage laeuft
  ueber den zweiten Aufruf).

## Prozedur
1. **Lage lesen, nicht erinnern.** `handeln.py --vorschau` mit
   `MAXHIRN_ROUTINE=1` läuft ohne Fenster und nennt jede geschlossene Sperre.
   Sperrliste im Code lesen (`sperren_live`), nicht aus dem Gedächtnis.
2. **Sichern** (Stufe 1): `.bak-JJJJMMTT` für jede Datei, die angefasst wird —
   auch `wachen.json` und `zustand.json`, wenn ein Testlauf sie berühren kann.
3. **Ändern:** Sperren gehören in `sperren_live()` bzw. die gleichnamige Funktion
   der Spur, nicht verstreut in den Rumpf von `lauf()`.
4. **Ohne Broker testen.** `cd <spur> && python -m unittest discover -s tests`.
   Interpreter **absolut** angeben (z. B.
   `C:/…/Handel/scanner/.venv/Scripts/python.exe`): ein relativer Pfad bricht nach
   dem `cd`, und die leere Ausgabe sieht wie „keine Tests“ aus statt wie ein
   Fehler. Für den Live-Pfad `pruefe_einstiege`/`pruefe_ausstiege` per Lambda
   stilllegen, Fenster regulär öffnen, Lauf starten, Zustandsdateien
   vorher/nachher per Hash vergleichen. Ein Test darf `markt_kauf` nie erreichen.
   Eine geänderte Ausgabezeile **rendern statt lesen**: die `print`-Anweisung per
   `ast.get_source_segment` holen, mit `ast.parse`/`compile` übersetzen, mit
   Beispieldaten ausführen. Eine Formatprüfung im Kopf ist kein Nachweis, und
   `ast.parse` prüft nur Syntax.
5. **Versionieren.** `.gitignore` ist eine **Whitelist**. Jede neue
   `.py`/`.json`/Testdatei braucht eine eigene `!`-Zeile, sonst landet sie still
   nicht im Verlauf — es sei denn, eine Glob-Zeile deckt sie schon
   (`!Agenten/Handel/*.py`, `!Agenten/Handel/tests/*.py`).
   `git add --dry-run <ordner>` zeigt, was wirklich in den Commit kaeme.
   - **Ein neuer Spurordner ist zunaechst komplett unsichtbar.** `git status
     --porcelain --ignored <ordner>` zeigt ihn als `!!`; `git status` allein
     schweigt, das `git add` tut nichts und meldet nichts. Vier Eintraege je
     Spur sind das Muster (`!…/<spur>/*.py`, `*.md`, `*.json`, `tests/*.py`) —
     damit war der Ordner freigegeben, ohne eigene Ordnerzeile. Wirkt eine
     Dateizeile trotzdem nicht (git steigt in einen ignorierten Ordner nicht
     hinab), erst `!<ordner>/` setzen, danach greifen die Dateizeilen.
     `zustand.json`, `handelsjournal.csv` und `.bak-JJJJMMTT` bleiben draussen:
     die Sperrliste weiter unten gewinnt als spaetere Regel, und `.bak-JJJJMMTT`
     endet nicht auf `.json`. Gegenprobe: `git diff --cached --name-only` darf
     keine dieser drei enthalten.
   - Eine solche Zeile ohne `!` ist eine **Sperre** — sieht wie eine Freigabe aus,
     bewirkt das Gegenteil; mehrfach eingefuegte gleiche Bloecke sind dasselbe
     Symptom. Gegenprobe zweimal: `git check-ignore -v <pfad>` nennt die
     entscheidende Regel, `git status --porcelain <ordner>` muss die neuen Dateien
     als `??` zeigen.
   - Versionierte Textdateien nie komplett neu schreiben: Fassung aus `HEAD` holen
     (Verlauf LF, Arbeitsbaum gern CRLF), nur die gewollten Stellen ersetzen;
     `git diff --stat` muss die geaenderte Zeilenzahl zeigen, nicht die ganze Datei.
   - In einem Baum mit mehreren Sitzungen gehoert in den Commit eine **explizite
     Pfadliste**, nie `git add -A <ordner>`: im Handel-Baum lag uncommittete
     Fremdarbeit (`spiegel/spiegel.py`, Ablehnungs-Protokollierung), die so unter
     die eigene Commit-Nachricht rutschte. Nach dem Commit `git show --stat` gegen
     die Absicht halten. Ist es passiert: `git reset --soft HEAD~1`,
     `git restore --staged <fremddatei>`, erneut committen, die Fremdaenderung
     unangetastet lassen und im Abschlussbericht nennen (braucht eine Entscheidung
     von Max, keine stille Mitnahme).
   - Der gelesene Stand ist eine MOMENTAUFNAHME: vor dem Aendern
     `diff <eigene .bak> <datei>` — nur diese Differenz zeigt, was seit dem Lesen
     dazukam; eine Meldung "Datei wurde von einer anderen Sitzung geaendert" ist
     kein Beleg, weder fuer eine Aenderung noch fuer deren Fehlen.
   - Wird im selben Zug eine Vault-Notiz geaendert (`MaxHirn/Wissen/*.md`), gehoert
     ihr `updated:`-Feld auf den heutigen Tag: Block 10c der Systempruefung meldet
     jede uncommittete Notiz mit altem `updated:` als offenen Punkt.
6. **Abschliessen, nicht nachfragen.** Ein „Ja" oder „Luecken schliessen" auf eine
   Empfehlung heisst: im vollen Umfang umsetzen (Code, Tests, Doku, Commit,
   Aufraeumen) — nicht nachbestaetigen lassen. Abschlussbericht in zwei Teilen:
   **was jetzt nachweisbar anders ist** (mit dem Befehl, der es zeigt —
   Systempruefung, `spiegelstand.py`, Testlauf, Logzeile) und **was absichtlich
   NICHT angefasst wurde** — fremde Spuren, laufende Prozesse, Altbestaende ohne
   Ziel, dazu jeder Wert, der eine Entscheidung von Max braucht (`gebuehr_taker`,
   Herzschlag-Grenzen, stillgelegte Pfade). Offene Entscheidungen aussprechen,
   nicht stillschweigend mitentscheiden. Entscheidet Max einen solchen Wert,
   gehoert die Entscheidung mit Datum und Ruecknahme-Bedingung an beide Orte
   (Erklaerfeld in `wachen.json`, z. B. `_gebuehren_abo`, UND die Wissensnotiz) —
   eine Kostensenkung ohne Ruecknahme-Regel zaehlt spaeter Runden fuer die
   Freigabe, die live nicht gelten. Und vorher lesen, welcher Satz ueberhaupt
   gelesen wird (`gebuehr_maker` liest `handeln.py` nicht): ein geaenderter Wert,
   den niemand liest, ist keine Aenderung. Und ein Wert, der nur im ERSTLAUF
   gelesen wird, wirkt nicht auf den laufenden Zustand: die Gitter-Leiter entsteht
   nur bei `neu = not z.get("leiter")` und wird danach nie verschoben — ein
   geaendertes `stufen` gilt erst auf eine frische Leiter. Vor jeder
   Parameter-Aenderung nachsehen, WANN der Wert gelesen wird, und die Wirkung im
   Bericht auf diesen Zeitpunkt datieren.
## Pitfalls
Die **vollstaendigen** Lektionen stehen in `references/pitfalls.md` (82 Punkte,
mit Begruendung und Messwerten). Hier nur die Landkarte, ein Satz je Punkt.
Vor jeder Aenderung an einer Spur den Punkt lesen, der greift - die Kurzfassung
ersetzt die Begruendung nicht.

1. **Der Sperrtext ist eine Schnittstelle.**
2. **Diagnose in jedem Modus drucken, den ein Aufrufer parst.**
3. **Gemeldet wird zeilenweise, nicht im Block.**
4. **Ein Ausstiegsgrund ausserhalb des Stichwortfilters meldet nichts.**
5. **Zwei Prozesse mit identischer Kommandozeile sind kein Doppellauf.**
6. Erst nachsehen, wer den Ausstieg speist, bevor eine Marktart als unsicher
7. Eine Uhrzeit ohne Datum und ohne Zone liest sich als Frist in der
8. **Drei Uhren in derselben Pruefung: Journal = UTC, Log und Bus = lokal.**
9. Ein Test darf in keinen echten Zielpfad schreiben — auch der richtige Aufruf
10. **Ein Wegwerfskript laedt die Spur ueber den DATEIPFAD, nicht per `import`.**
11. **Eine Stoerung gehoert aus der KENNZAHL, nicht aus der Kapitalkurve.**
12. **Zahlen im Quelltext sind Behauptungen.**
13. **Plan (Stufe 1) fuer jede angefasste Datei.**
14. **Code-Ersetzungen an Dateien mit `\n` im Quelltext:.**
15. **Eine Sperre muss auch aufgehen können.**
16. **Zwei Fassungen derselben Sperre, eine Wahrheit.**
17. **Zustandsdateien vergiften sich.**
18. Ein neues Feld je Position bekommt einen Altbestand-Rueckfall, sonst kippt
19. **Eine Ablehnung darf nicht gleich wieder gefragt werden.**
20. **Vor jeder Aenderung an `SPUREN` erst nachsehen, was schon laeuft.**
21. Eine zweite Aufgabe auf derselben Spur ist ein zweiter Schreiber — auch wenn
22. **Die Herzschlag-Grenze folgt der Selbstheilungszeit, nicht dem Gefuehl.**
23. **Eine Regel ohne Messung verfaellt.**
24. **Erst die Geometrie rechnen, dann Parameter drehen.**
25. **Festes Nominal bei variablem Stop heisst ungleiches Risiko je Platz.**
26. **Ein erhoehtes Limit kann wirkungslos sein — vorher nachrechnen, WELCHES Limit greift.**
27. **Der Abnahme-Nachweis laeuft am ECHTEN Zyklus, nicht am Testaufruf.**
28. **Ein Schwellwert aus einer FREMDEN Groesse ist ein latenter Defekt.**
29. **Eine Sicherung, die man nicht sieht, kann man nicht pruefen.**
30. **Ungepruefte Funktionen sind der Ort, an dem solche Defekte ueberleben.**
31. **Erst der Import-Kette folgen, dann "kein Code liest das" behaupten.**
32. **Ein Schwellwert aus einer FREMDEN Groesse ist ein latenter Defekt.**
33. **"Unerreichbar" ist bei einem Drawdown-Schwellwert das falsche Wort.**
34. **Eine geteilte Umsetzung ueber den PFAD laden, nicht ueber `sys.path`.**
35. **Ein neuer Konfigurationsschluessel wirkt erst, wenn die ABLEITUNG ihn kennt.**
36. **Eine Schutzschwelle nimmt den HOECHSTEN Fall, nicht den Mittelwert.**
37. Eine STRUKTURELLE Grenze ist ein Beleg, keine erfundene Zahl — und der
38. **Fehlt eine Schwelle, darf nichts erfunden werden.**
39. Die Zahlen aller Spuren ohne eigene `auswertung.py` liefert
40. **Zwangsschluesse sind keine Runden.**
41. **Ein Backtest, der die Spur nachbaut, optimiert die Nachbildung.**
42. Erst trennen (suchen/pruefen), dann urteilen — sonst ist der Befund
43. Spannt der ganze Parameterraum fast nichts, ist der Parameter nicht der
44. **Ein Befund eines Subagenten ist ein Hinweis, keine Tatsache.**
45. Vor jeder Deutung eines Journals pruefen, ob die Runden aus eigenen
46. **Testfallen in den Spuren:.**
47. Ein Papier-Umfang darf groesser sein als das Muster - das ist kein
48. **Anbinden heisst: JEDE Liste, die eine Spur nennt, mitziehen.**
49. Backtest-Urteile: der Sammler ist `Handel/backtest_urteile.py`, die Felder
50. **Vier Indikator-Spuren sind seit dem 15.09.2026 angeschlossen.**
51. **Der richtige Testaufruf steht im Testkopf, nicht in der Gewohnheit.**
52. **Vier Indikator-Spuren liegen gebaut, aber unangeschlossen.**
53. **Keine absoluten Benutzerpfade in Skripten.**
54. **Nur `dauerlauf.py` selbst braucht einen Neustart.**
55. **Tests dürfen keinen Konfigurationswert behaupten.**
56. **`.env`, `Wissen/Zugaenge.md`, `proxy.yaml` sind tabu.**
57. Ein Buch, das nur Buchungen protokolliert, kann "Tor" und "voller Platz" nicht
58. Ein volles Buch ist ein Durchsatz-Problem, kein Tor-Problem — und der Umfang
59. Ein Signal-Feed ist ein FENSTER, kein Stammbuch: die Wallet-Liste altert in
60. Ein Test, der eine Grenze aus der Datei liest, misst nach einer
61. **Ein modulweiter Schreibschalter leckt zwischen Testdateien.**
62. **Eine neue Spur muss in die Meldungen, sonst meldet sie niemand.**
63. Bus und Tagesbericht lesen feste Feldnamen — eine Spur mit anderer
64. Ein richtiger Feldname kann die falsche GROESSE tragen — Einheit pruefen, nicht
65. „Rueckgabe N“ nach Spur-Neueintrag: die Spur selbst crasht, nicht die
66. **`handeln.py` muss `--papier` als Flag UND als Positional akzeptieren.**
67. **Datenquelle als Test-Seam austauschbar machen.**
68. **Erweiterst du die Signatur einer ersetzten Funktion, muessen die Doubles mit.**
69. **Eine geaenderte Signatur trifft auch die Aufrufer, die kein Test beruehrt.**
70. Ein Stummel im Testbaum kann den geaenderten Aufruf verbergen — am echten
71. **Ein Pruefer, der Quelltext parst, erblindet still, wenn sich die Form aendert.**
72. **Eine Papier-Position in `zustand.json` ist der zweite Zyklus-Test.**
73. **Keine Behauptung ueber eine andere Spur im Code.**
74. **Wachen-Module liegen nicht immer im eigenen Ordner.**
75. **Ausstiegsgruende nach Schwere pruefen, nicht nach Naehe.**
76. **Ausgabe testen, nicht Quelltext.**
77. „Prognose: Exit-Code 1” ist normal, aber nur der volle Lauf ist ein
78. Der Boersen-Stop ist eine Order mit eigenem Leben: jeder Ausstieg muss ihn
79. **Eine Vorschau, die schreibt, ist keine Vorschau.**
80. Die Befehls-Ebene ist eine eigene Naht - und `/lage` darf nicht `/bericht`
81. **Ein neuer Spurordner ist in `.gitignore` nur freigegeben, nicht entsorgt.**

82. **Eine Statistik darf auf einer tieferen Reihe rechnen, ein Kurssignal nicht - und nur, wenn beide gleichzeitig enden.**

83. **Eine neue Spur kopiert die Sperrschreibungen des Vorbilds** — `z["modus"]` setzen und `wx.sperre_zu()` in Kill- und EV-Zweig, sonst schliessen die Notbremsen das Wachen-Tor nie.

84. **'Verwaiste Sperre ... wird ersetzt' ohne Zyklus-Zeilen dazwischen ist ein Absturzloop, kein haengender Prozess.**

85. **Eine 'Fixes Applied'-Notiz einer fremden Sitzung ist eine Behauptung, kein Beweis — nach jeder uebernommenen Fremdaenderung die VOLLE Testsuite laufen lassen.**

## Welche Daten eine Sperre liest

Jede Bedingung, die eine Spur sperrt oder entsperrt, legt ausdrücklich fest,
auf welcher Datenmenge sie rechnet — das ist eine Entscheidung, keine
Nebenbedingung. Geltende Regel: eine **Betriebsstoerung** (Herzschlag-
Zwangsschluss, Notaus) ist keine Handelsentscheidung und darf eine
Erwartungswert-Sperre nicht auslösen. Die **Kapitalkurve** (Drawdown, Ratsche,
Halbierung, Kill-Switch) rechnet weiter auf ALLEN Buchungen — eine Stoerung ist
eingetragen und hat Geld bewegt.

- **Genau EIN Feld trägt die Zahl, auf der die Sperre beruht.** Heißt es
  `rollierender_ev`, dann ist das die Zahl der Bedingung; die Zahl über alle
  Buchungen bekommt einen eigenen Namen (`rollierender_ev_alle`). Ein Feld mit
  zwei Bedeutungen ist der Fehler: Anzeige und Sperrtext lesen dasselbe Feld,
  und hinterher kann niemand sagen, worauf gesperrt wurde.
- **Die Umstellung gehört in ALLE Wachenfassungen** (scanner, xperp, kraken,
  orbk) — jede hat ihre eigene `lage()`. Eine vergessene Fassung sieht nicht
  wie ein Fehler aus, sondern wie eine Spur mit anderen Zahlen.
- **Ein Test ohne Gegenprobe bleibt stillschweigend grün.** Der Test muss so
  gebaut sein, dass er mit der ALTEN Rechnung fehlschlägt: mehrere echte
  Runden mit Gewinn gegen eine Handvoll Zwangsschlüsse mit Verlust, so dass
  die alte Zahl negativ und die neue positiv ist — plus eine Zusicherung auf
  den alten Wert (`assertLess(s["rollierender_ev_alle"], 0)`).
- **Am lebenden System nachweisen, nicht nur im Test:** je Spur
  `handeln.py --wachen` fahren und die Zeile der Bedingung aus dem echten
  Journal zeigen (Spur, Zahl, ob gesperrt). Erst das belegt, dass die
  Umstellung wirkt — und deckt auf, wo eine Spur unter der Messgrenze liegt
  (`n/a`, zu wenig Handelsrunden).

Rezept mit Testgerüst, Journal-Formen je Spur und Prüfkommandos:
`references/sperren-datenbasis.md`

## Einzelne Spuren im Detail

Die datierten Kapitel je Spur (SWAP anbinden, Omniquant, Kraken wieder im
Dauerlauf, Gitter, Nautilus, ORB-Grundregel) stehen in
`references/spuren-einzeln.md` - Nachschlagewerk, nicht Prozedur. Nur laden,
wenn genau diese Spur ansteht.

## Boersendaten und Orderflow

Detaillierte API-Fallen fuer OKX/Kraken-Kerzen und Orderflow (Rubik/CVD) stehen in `references/boersen-datenzugriff.md`. Kernregeln: `okxf.kerzen()` unbekannte Instrumente leere Liste (len pruefen); Kraken-OHLC max 720 Kerzen ohne Rueckwaerts-Pagination (M15 7,5 Tage); 4h-CVD nur ueber `/rubik/` (nicht aus dem Tape); Host nur `www.okx.com`; Rubik-429 wird nicht wiederholt. **Vor dem Anbinden einer Spur die Warmlauf-Laenge ihres Indikators gegen die Abrufgrenze rechnen** — ein Indikator, der mehr Historie braucht als der Abruf liefert, ist nicht ungenau, sondern still tot (Details und die OKX-Grenzen: `references/boersen-datenzugriff.md`).

## Ein Fenster ueber alle Spuren (Handelszentrale, 13.09.2026)

- **Die zentrale Ansicht liest ihre Spurliste aus `dauerlauf.SPUREN`.** Eine
  zweite Liste in der GUI altert beim naechsten neuen Spurordner still.
- **Der eigene Modulname darf keinem Spurmodul gleichen.** `Handel/gui.py` hiess
  zuerst so — wie `omniquant/gui.py`. Mit `Handel/` auf `sys.path` fing der Import
  das fremde Fenster ab, fuenf Omniquant-Tests brachen mit `module 'gui' has no
  attribute 'fuss_texte'`: nicht kaputt, sondern gegen das falsche Modul gelaufen.
  Dieselbe Falle wie die zwei `auswertung.py`, nur ueber einen Ordner hinweg; ein
  Test haelt den Handel-Kopf frei von doppelten Modulnamen.
- **Ein zentraler Leser muss ALLE Zustandsformen kennen, sonst zeigt er still
  null.** Je Spur ein Testfall in ihrer echten Schreibweise (`position` statt
  `positionen`, `richtung` statt `seite`, `preis_einstieg`/`stop_preis`,
  `symbol`+`kette` statt `inst`, `paar` statt `inst`, `usd`/`eur` statt `nominal`)
  plus eine Formpruefung gegen die echten Dateien: die Zahl der gelesenen
  Positionen muss der in `zustand.json` entsprechen. Ein falscher Feldname sieht
  nicht wie ein Fehler aus, sondern wie "0 Positionen".
- **Die Quellenzuordnung ist eine zweite Liste, die still altert.** Die
  Handelszentrale holt ihren Kursweg aus einem eigenen `QUELLE`-Dict (Spur ->
  okx/kraken/feed); fehlt die Spur darin, nimmt sie die VORGABE (okx) — die
  Anzeige behauptet eine falsche Boerse, der Chart holt Kerzen vom falschen Markt.
  Der Kursweg ist der GENERISCHE Schluessel aus `positionen_aus()` (`inst` ODER
  `paar` ODER `token`), nicht `roh["inst"]`: die Kraken-Spur schreibt `paar`, mit
  `roh["inst"]` stand dort `None` ("Quelle okx (None)", Chart ohne Kerzen, ohne
  Fehlermeldung). Beim Aufnehmen einer Spur BEIDE Stellen pruefen — `QUELLE` und
  Schluesselwahl — und danach `handelszentrale.py --pruefen` gegen die echte Datei
  laufen lassen: dort muss "Quelle <erwartet> (<paar>)" stehen.
- **Zeitstempel fremder Dateien: Zone und Form pruefen, nicht schneiden.**
  `dauerlauf.log` traegt LOKALE Zeit ohne Jahr (`13.09. 18:25:44`); gegen UTC
  gerechnet stand in der Kopfzeile "letzter Zyklus vor -120 min", waehrend der
  Dienst lief. In derselben Zone vergleichen, Jahr aus dem Bezug; ein Eintrag mehr
  als einen Tag in der Zukunft gehoert zum Vorjahr. `strptime("%d.%m.")` warnt
  seit Python 3.13 — von Hand parsen. Nicht jedes Journal hat eine Uhrzeit: die
  ORB-Spur schreibt `2026-09-13`, ein starres `zeit[11:16]` liest dort eine leere
  Spalte (Datum anzeigen, nicht "--:--").
- **Nebenlaeufigkeit deckeln: ein Kurs-Worker gleichzeitig.** Die Feed-Kurse
  (Spiegel) laufen ueber ein CLI und brauchen Sekunden; ohne Sperre stapeln sich
  die Threads im Viertelminutentakt, das Fenster lebt von Altantworten. Kurse und
  Kerzen nur ueber Queues ins Widget, nie aus dem Thread heraus.
- **Der Autostart laeuft ueber die Aufgabenplanung, nicht ueber den
  Startup-Ordner:** `Routinen/handelszentrale.ps1` (Bus-angebunden, Waechter ueber
  den Fenstertitel) + `Routinen/handelszentrale-aufgabe.ps1` (legt
  `MaxHirn-Handelszentrale` an, erhoehte PowerShell noetig). Ein von einem Skript
  gestartetes Fenster hat kein Vordergrundrecht und sieht aus wie „weg" —
  Gegenmittel ist `nach_vorn()` im Programm, nicht im Starter.
- **Ein Leseprogramm wird per AST geprueft, nicht per Stichwort.** Verboten:
  `open` mit w/a/x/+, `json.dump`, `csv.writer`, `os.remove/rename/replace`,
  `import subprocess` — dazu ein Laufzeittest, der Groesse und mtime ALLER
  Spurdateien vor und nach einem vollen Leselauf vergleicht. Gegenstueck zum
  spiegel-Test (verbietet `subprocess` im Quelltext).
- **Ein echter Fensteraufbau gehoert in die Suite.** Ein tk-Mock verdeckt genau
  die zwei Startfehler (fehlendes `from tkinter import ttk`, ein `root` in einer
  Builder-Methode, die nur `self.root` kennt): `root.withdraw()`, Fenster bauen,
  `root.update()`, Tabellenzeilen gegen die gelesenen Positionen pruefen — deckt
  beides ab, ohne Bildschirm.
- **Den Fensterinhalt beweist man aus den Widgets, nicht per Foto.** Fenster
  in-process bauen (`root.withdraw()`), `root.update()`, Inhalt lesen: Titel,
  Tabellenzeilen (`t_pos.get_children()` + `item(..., "values")`), Konsolentext,
  Fusszeile — und die Chartflaeche per `canvas.postscript()` auf
  Zeichenoperationen pruefen (Vorbild
  `Agenten/Hermes/cache/hz_fensterpruefung.py`). Kommt eine Bildschirmaufnahme
  einfarbig zurueck, ist der Desktop nicht abgreifbar: dann ist die Widget-Ausgabe
  der Nachweis, nicht das Foto. Ein Startbefehl ueber `Start-Process`/`cmd start`
  kehrt erst zurueck, wenn das Kind den Ausgabekanal schliesst — erst den
  Fenstertitel pruefen.
- **Persistierte Windows-Terminal-Layouts sind ein zweiter, unsichtbarer Starter.**
  `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\state.json`
  speichert unter `persistedWindowLayouts` ALLE offenen Fenster mit ihrer
  Kommandozeile, sobald WT mit `firstWindowPreference: persistedWindowLayout`
  laeuft. Jedes Layout mit `python.exe gui.py` / `handelszentrale.py` und falschem
  WorkingDirectory (Repo-Wurzel statt `Agenten/Handel`) baut bei JEDEM WT-Start
  ein Fehlerfenster auf (`can't open file ...\BrainFiles\handelszentrale.py`,
  Exit 2) — ein Fenster, das 'immer wieder aufspringt', ohne Task oder Autostart.
  Am 14.09.2026: 10 von 12 gespeicherten Layouts liefen die venv-python aus der
  falschen Wurzel (eines davon `prognose.py --kurz`, das den OKX-Transportfehler
  1/6-Spam erzeugte). Gegenmittel: WT schliessen, kaputte Layouts aus
  `state.json` entfernen (nur die ohne `python.exe` behalten), WT neu starten.
  `powershell -File handelszentrale.ps1` haengt an der Konsole, weil pythonw die
  Ausgabekanaele erbt — erst den FENSTERTITEL pruefen. Einen veralteten
  GUI-Prozess (Startzeit VOR dem letzten Datei-Mtime) per `Stop-Process` beenden
  und den Wrapper laufen lassen: er startet den aktuellen Code neu und schreibt
  das fehler.log frisch.
- **Der Autostart gehoert in `Routinen/`, nicht in den Startup-Ordner.**
  `Routinen/handelszentrale.ps1` startet das Fenster bei der Anmeldung (+2 Min),
  wenn keines offen ist; `Routinen/handelszentrale-aufgabe.ps1` legt die Aufgabe
  an (erhoehte PowerShell noetig, der Wrapper laeuft auch ohne). Der Waechter
  prueft den FENSTERTITEL, keine PID-Datei — so zaehlt auch ein von Hand
  gestartetes Fenster, und ein Absturz hinterlaesst keine Sperre. Gestartet wird
  `pythonw.exe` (kein Konsolenfenster), Aufbau-Fehler nach
  `Routinen/logs/handelszentrale-fehler.log`. Regeln fuer Starter-Routinen
  (Bus-Anbindung, Abnahme ueber die Aufgabenplanung, Zeile in
  `Wissen/Routinen.md` erst wenn die Aufgabe steht): Skill `bus-integration`.

## ORB-Grundregel: ein Trade je UTC-Tag, und das Merkzeichen muss den Ausstieg ueberleben
- **Ein Tagesschutz, der nur die offene Position anschaut, ist keiner.** `_schon_gehandelt_heute` prueft nur `z["position"]["tag"]`; der Ausstieg entfernt die Position, damit war die Sperre im selben Zyklus wieder offen, und derselbe Breakout (gleiche Kerzen, gleiche Range) stieg sofort erneut ein: Endloskreis Ausstieg→Wiedereinstieg. Symptom-Kette (Befund 13.09.2026, orbk): Journal fuellt sich mit byte-identischen Ausstiegszeilen (51 an einem Tag), die Position "haengt" in zustand.json (wird ja nie wirklich geschlossen), und weil der Dauerlauf-Filter `ausstieg` case-insensitiv faengt, geht jede Viertelstunde eine AUSSTIEG-Meldung nach Telegram. Fix: Merkzeichen `zuletzt_gehandelt_tag` im Zustand, beim EINstieg gesetzt (nicht beim Ausstieg: eine gestern eroeffnete, heute geschlossene Position darf heute neu einsteigen), geprueft in `_schon_gehandelt_heute` nach dem Pop. Regressionstest laesst den echten `lauf()`-Zyklus Ende-zu-Ende laufen (Temp-Zustandsdateien, `_jetzt`/`_letzter_kurs`/`_wachen`/`kerzen_quelle` gepatcht) plus Gegenprobe ohne Merkzeichen, die den Fehler reproduziert — ein Test, der den Fix nur mitlaufen laesst, beweist nichts.

## Werkzeugfallen am Host
- **`vision_analyze`/`video_analyze` erreichen lokale Dateien NUR aus dem Media-Cache unter HERMES_HOME** (`video_cache/`, `temp_vision_images/`, `image_cache/` — Pfade anderswo heissen "media file not found"). Selbst aus dem Cache schlaegt der Anbieter mit 404 ("Couldn't find that, sorry.") fehl, wenn der OmniRoute-Router Bildinhalte nicht weiterreicht — der lokale Vision-Weg ist dann tot. Fallback fuer Video: ffmpeg-Frames ziehen (`ffmpeg -i v.mp4 -vf fps=1 frame_%02d.jpg`) und per Windows-OCR auslesen (`Windows.Media.Ocr.OcrEngine` via PowerShell, offline, kein Key) — fuer Trading-Dashboards reicht das (Zahlen + UI-Labels). Skripte: `Agenten/Hermes/cache/ocr_frame.ps1`.
- **Scratch- und Probe-Dateien nicht nach `Werkstatt/` legen.** `Werkstatt` ist
  eine Junction auf `O:`; `write_file` loest den Pfad auf sein echtes Ziel auf und
  verweigert ihn (`outside HERMES_WRITE_SAFE_ROOT`). Ablage fuer Wegwerf-Skripte:
  `Agenten/Hermes/cache/` (innerhalb BrainFiles, nicht versioniert). Zwei Vorlagen
  dort: eine **Filterprobe**, die nachbildet, was `dauerlauf.zyklus()` aus der
  Spur-Ausgabe nach Telegram schickt (`verkauf`, `stop`, `KILL`, `gesperrt`,
  `ausstieg`) — zeigt vor dem Commit, ob eine neue Ausgabezeile Spam erzeugt; und
  eine **Verbraucherprobe**, die `dauerlauf.Lauf.nur_fenster_fehlt(spur, d)`
  direkt aufruft und `None` erwartet, wenn die Spur keinen Live-Pfad hat. Beides
  gegen eine Spur laufen lassen, nicht gegen die Vermutung.
- **Backslashes in Windows-Pfaden nicht am Tool-Ergebnis zaehlen.** Die Ausgabe
  kommt JSON-kodiert zurueck, jeder Backslash erscheint doppelt: eine Datei mit
  `'Handel\spiegelstand.py'` zeigt in der Antwort `Handel\\spiegelstand.py`. Wer
  daraus zwei Backslashes schliesst und mit vier ersetzt, trifft nichts (Assertion
  `count == 1` schlaegt fehl — oder schlimmer, sie trifft und schreibt Unsinn).
  Gegenmittel: Zielzeile mit `repr()` ausgeben und **Zeile fuer Zeile** ersetzen
  (`split("\n")`, Praefix suchen, Zeile tauschen), statt im ganzen Text.
- **Terminal-Ausgabe nicht als Beweis fuer exakte Zeichen nehmen (Diffs, JSON mit
  Sonderzeichen, ein Commit-Hash, ein Textmuster-Treffer) — bei Zweifel in eine
  Datei schreiben und mit `read_file` zurueckholen.** Die gerenderte
  Tool-Antwort kann einzelne Zeichen unterdruecken oder verschieben, ohne dass
  die zugrundeliegenden Daten falsch sind. Ein kleines Diagnoseskript, das sein
  Ergebnis als JSON in eine Datei schreibt statt es zu drucken, und per
  `read_file` gelesen wird, zeigt den echten Stand zuverlaessig — dieselbe
  Disziplin wie bei den doppelten Backslashes, nur fuer den allgemeinen Fall.
  Vor jeder Aussage "das Muster existiert nicht" oder "dieser Commit/Wert ist
  da" erst so gegenpruefen, statt der gedruckten Ausgabe zu glauben.
- **Das Host-PowerShell-Werkzeug hat eine harte Zeitgrenze (~300 s).** Eine
  rekursive Größenmessung über einen großen Baum reißt sie. Stattdessen
  vorher/nachher `Win32_LogicalDisk.FreeSpace` messen oder je Ordner einzeln — der
  Zuwachs ist die belastbare Zahl.
- **`Get-FileHash` gibt es in dieser PowerShell nicht** (5.1.26100.9444:
  `Get-Command Get-FileHash` liefert nichts, der Aufruf bricht mit "Die Benennung
  ... wurde nicht als Name eines Cmdlet ... erkannt" ab). Ein Pruefblock, der
  daran scheitert, liest sich im Bericht wie "nichts gefunden" — der
  Regelwerk-Block der Systempruefung lief so wochenlang nie. Hashing ueber .NET:
  `[System.Security.Cryptography.SHA256]::Create()` +
  `[System.IO.File]::ReadAllBytes($pfad)`. Bei jedem neuen Pruefblock pruefen, ob
  alle benutzten Cmdlets existieren.
- Windows begrenzt die Kommandozeile (~32k Zeichen): ein großer
  PowerShell-Here-String scheitert mit `WinError 206`. Lange Dateien in Teilen
  schreiben (`Set-Content`, dann `Add-Content`) oder einen kleinen Applier die
  Nutzlast aus einer Datei holen lassen. Dasselbe fuer mehrzeilige Shell-Einzeiler
  (Schleife mit mehreren Befehlen): sie werden als „inline command payload“
  abgewiesen, BEVOR sie laufen — ein Retry mit demselben Text scheitert identisch.
  Schritte getrennt aufrufen oder das gespeicherte Skript mit `bash <pfad>`
  ausfuehren.
- **Ein zu grosser Schreibvorgang bricht mitten im Stream ab, nicht mit einem
  Fehler.** Ein `write_file` mit sehr viel Nutzlast (grob ueber 8K Token
  Argumente) laeuft in einen Stream-Timeout, und die Aktion wurde dann NICHT
  ausgefuehrt — ein Retry mit demselben Text scheitert identisch. Grosse Dateien
  in mehreren kleineren Aufrufen schreiben oder den Kern schreiben und den Rest
  per `patch` anhaengen. Dieselbe Grenze gilt fuer lange Tool-Einzeiler.
- **Ein Suchanker mit escapten Anfuehrungszeichen trifft nicht.** Beim Aendern
  eines JSON-Kommentarfelds (`"_feld": "... \"wort\" ..."`) bricht der Patch
  mit „Escape-drift detected" ab, weil der Anker ein `\"` enthaelt. Anker ohne
  escapte Zeichen waehlen — einen Teilstring ohne Anfuehrungszeichen (die
  Satzhaelfte, einen Zahlenwert) — und den Rest in einem zweiten Aufruf
  ersetzen. Gilt auch fuer Anker mit Backslash-Pfaden: erst `repr()` der
  Rohzeile zeigen, dann das Muster bauen.
- Geschriebene `.py`/`.json` pruefen — den NEUEN Text im Speicher VOR dem
  Schreiben, nicht erst die Platte danach: `ast.parse` bzw. `json.loads` (ein
  eingefuegtes Feld ohne abschliessendes Komma faellt sonst erst auf, wenn die
  Datei unlesbar liegt und jeder Leser der Spur — Systempruefung,
  `spiegelstand.py` — darueber stolpert; Suchmuster ohne Delimiter bauen, ein
  mitkopiertes Anfuehrungszeichen trifft nichts), dazu kein BOM und kein `\r`.
  Ueber einen PowerShell-Here-String mit `utf-8-sig` einlesen, `\r` entfernen,
  mit `newline=""` schreiben.
- `search_files`-Regex-Pattern werden intern gewrappt: escaped Klammern (`\(`) in
  einer Alternation brechen mit „unclosed group“ ohne klaren Grund. Nach dem
  nackten Symbol suchen (ohne `(`), wenn eine Mustersuche mit Klammern zweimal
  scheitert.
- Viele chirurgische Ersetzungen in einer Datei: je (alt, neu)-Paar mit
  `count == 1` asserten, danach `ast.parse` — ein stiller Mehrfachtreffer oder
  eine verrutschte Fundstelle faellt sofort auf. Zeilenenden vorher erkennen
  (LF/CRLF) und beim Schreiben erhalten.

## References
- `references/santiment.md` — Santiment SanAPI (GraphQL, anonym in der freien
  Stufe nutzbar): wo das Repo liegt, welche Metriken live geprueft sind, dass
  JEDE Metrik ihr eigenes Zeitfenster hat und `erlaubtes_fenster()` die Grenze
  aus der Fehlermeldung liest, warum eine leere Reihe kein Fehler ist und wie
  der MCP-Weg (OAuth) daneben aussieht.
- `references/schattenbuch-spur.md` — Varianten einer bestehenden Spur mit
  getrennten Dateien (Suffix durch die Datei-Konstanten, Launcher je Arm):
  Mechanik, Verdrahtung inkl. spiegelstand- und Bus-Anbindungs-Falle,
  Auswertung erst ab genug Ausstiegen je Arm.
- `references/browser-edge-sperre.md` — Hermes-Edge / browser-profile: eine
  laufende Headless-Edge-Instanz hält Cookies/Sessions gesperrt und bricht
  die Sicherungsläufe mit FEHLER 32 / Exit 20/21. `/XD browser-profile` in
  sichern.ps1 und sichern-zweitkopie.ps1; `0xC000013A` = Rechner-Neustart
  (Event 1074), kein Skript-Fix.
- `references/pitfalls.md` — ALLE Pitfalls im Volltext (82 Punkte, gleiche Nummer wie die Landkarte in SKILL.md):
  Meldungen und Schnittstellen, Sperren und Schwellen, Testfallen,
  Doppellauf und Neustart, Buch und Ablehnungen, Naht und Signatur,
  Auswertung und Backtest. **Vor jeder Spuraenderung lesen.**
- `references/spur-weite-aenderung.md` — Änderung über ALLE Spuren ausrollen:
  Inventar, Stufe-1-Sicherung, byte-genaue Ersetzungen in `wachen.json`/Code, alle
  Zyklenpfade inkl. Notausstieg, Testaufruf (`discover -s tests -t tests`), echter
  Lauf + byte-genauer Vergleich, Automatik-Nachweis über das Bus-Journal, Doku an
  drei Orten, getrennte Commits je Regel und Repo — plus die Falle „Testzyklen
  spiegeln ihre Temp-Zustandsdatei an das echte Ziel".
- `references/schwellen-haerten.md` — Verfahren, mit dem die Schutzwerte einer
  Spur vertrauenswuerdig werden: Buchrisiko feststellen, fehlende Eingabe aus
  dem Code ablesen statt raten, Betrag herleiten und ausdruecklich hinschreiben,
  warnen statt ausloesen, `halbierung_im_gewinn` pruefen statt "erreichbar" zu
  behaupten, Stand aller fuenf Spuren, die Spalten des Pruefskripts.
- `references/sicherungen-pruefen.md` — Sicherungen (Ratsche, Kill-Switch,
  Deckel, Groessenfaktor) und die Werkzeuge, mit denen man prueft, dass sie
  greifen koennen: absoluter Betrag statt Quote von fremder Groesse, warum
  "greift erst im Minus" nicht "abgeschaltet" heisst, der Vorrang des
  ausdruecklichen Werts, und "keine Negativ-Aussage aus einer abgeschnittenen
  Suche" (Import-Kette!).
- `references/anbindungs-audit.md` — Bestandsaufnahme „was laeuft, was ist
  angebunden, was ist Altlast“: Verdrahtungsstellen gegeneinander halten,
  Aufrufer greppen, Befund richtig deuten.
- `references/spur-nachtraeglich-anschliessen.md` — eine BESTEHENDE Spur (oder
  mehrere) nachtraeglich in den Takt haengen: die fuenf Stellen, der Vertrag des
  Tagesberichts, der geteilte Journal-Leser, die Nachweis-Kette bis zum ersten
  Zyklus, und die Fallen (Zustand schlaegt wachen.json, fehlender
  Duplikat-Schutz, CRLF im Test-grep).
- `references/freigabe-kette.md` — Punkt 3 der Handelsregeln in beiden Fassungen:
  Bildschirm- und Zeitfenster, wer wann öffnet, was eine Freigabe nicht kann.
- `references/tor-kalibrierung.md` — Schwellen und Kostenannahmen kalibrieren,
  ohne dass sie entweder nichts filtern, nie aufgehen oder eine Wunschrechnung
  sind (Tore, Filter, Slippage/Gebühr).
- `references/fremdfeed-papierbuch.md` — Spur an fremden Signal-Feed haengen
  (Copy-Trading, Spiegelung, Signalstudie): Leser mit Schreibschutz, Auswahlregel
  gegen Zuchtauswahl, Kosten zweimal gerechnet, Tore vor jeder Buchzeile.
- `references/buchergebnis-pruefen.md` — Buch-Ergebnis deuten, bevor es als Gewinn
  gelesen wird: Papier vs. Geld, Saldo vs. Umsatz, Abhaengigkeit von den
  Top-Positionen, Mittelwert UND Median, was nicht in der Zahl steckt. Ausloeser:
  „das heisst, wir haetten X gewonnen?".
- `references/spur-haerten.md` — bestehende Spur pruefen, haerten, messbar machen:
  acht Verdachtsmuster (toter Code mit Docstring-Behauptung, erfundene Feldnamen,
  zu enge Ausnahmen, fehlende Deckel), Fix-Disziplin, Nachweis-Kette. Ausloeser:
  „Code optimieren", „Luecken suchen".
- `references/spur-bericht.md` — Zustandsbericht ueber eine laufende Spur:
  Quellen in Reihenfolge, Lese-Fallen (Bus-Journal mit BOM, UTC vs. lokale
  Bus-Zeit, 1-s-Vorschau-Lauf je Zyklus als Absicht, kurze Abstaende vs. echte
  Taktluecken), was ein Bericht sagen muss und was nicht. Ausloeser: „Bericht",
  „wie laeuft <Spur>".
- `references/neue-spur-ende-zu-ende.md` — Spur von Null bis GUI aufbauen:
  abgebrochene Aufgabe verifizieren (nichts annehmen), Vorbilder lesen, drei
  Kerndateien bauen, an fuenf Faeden verdrahten, Nachweis-Kette,
  Dauerlauf-Neustart, GUI-Start und -Verifikation.
- `references/auswertung-und-optimierung.md` — Journale in eine belegte Aenderung
  uebersetzen: Runden zaehlen (Testlaeufe aussortieren), Kosten aus der Zeile,
  Geometrie-Gegenprobe, Ausstiegsgruende, Gruppen mit Stichproben-Disziplin, die
  eine Aenderung samt drei Ablageorten, und was eine duenne Stichprobe NICHT
  hergibt. Ausloeser: „werte die Daten aus", „optimiere die Strategien".
- `references/fremdarbeit-mitnehmen.md` — uncommittete Arbeit einer anderen
  Sitzung erkennen, liegen lassen, mitnehmen wenn fertig:
  Wachstums-/mtime-Kriterium, `reset --soft` zum Nachtrennen, Waechter als
  `no_agent`-Cron mit Ruhezeit und Merker, Commit nur der Quelldateien mit
  ehrlicher Nachricht. Skript: `scripts/fremdarbeit_waechter.py`.
- `references/xperp-rollover-2026-09-14.md` — XPERP-Kontrakt-Rollover (51001),
  Tests schreiben nie ins echte Journal, hartdatierte Tests, seite im
  Positions-Dict.
- `references/spuren-einzeln.md` — die datierten Kapitel je Spur (SWAP
  anbinden, Omniquant, Kraken wieder im Dauerlauf, Gitter, Nautilus,
  ORB-Grundregel). Ausgelagert, weil SKILL.md sonst ueber das
  100.000-Zeichen-Limit laeuft und gar nicht mehr patchbar ist. Nur laden,
  wenn genau diese Spur ansteht.
