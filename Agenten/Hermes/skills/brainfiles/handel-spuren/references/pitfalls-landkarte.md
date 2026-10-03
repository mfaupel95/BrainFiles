# Pitfalls-Landkarte (109 Punkte, ein Satz je Punkt)

Aus `SKILL.md` ausgelagert (03.10.2026, T-322): die Landkarte stand mit
22.889 Zeichen bei 23 % der Datei und liess nur noch 912 Zeichen Luft - damit
wuerde jeder kuenftige `skill_manage`-Patch am Grenzwert abgewiesen, auch
eine Reparatur.

Die vollstaendigen Lektionen mit Begruendung und Messwerten stehen in
`pitfalls.md`, gleiche Nummer. Vor jeder Aenderung an einer Spur dort den
Punkt lesen, der greift - diese Kurzfassung ersetzt die Begruendung nicht.

Die **vollstaendigen** Lektionen stehen in `references/pitfalls.md` (alle Punkte
der Landkarte, gleiche Nummer, mit Begruendung und Messwerten). Hier nur die
Landkarte, ein Satz je Punkt.
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
48. **Anbinden heisst: JEDE Liste, die eine Spur nennt, mitziehen** — und die
Suiten nennen die vergessene (`test_lage`: Holer, `test_befehle`: `FAMILIE`).
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
69. **Eine geaenderte Signatur trifft auch die Aufrufer, die kein Test beruehrt** — und ein neuer OPTIONALER Parameter i
69a. **Der Testseam ist die LADEFunktion, nicht das geladene Modul.** Laedt ein
Wrapper sein Boersenmodul bei jedem Aufruf ueber den Pfad (`spec_from_file_location`),
gibt es zwei Instanzen; ein Patch auf der importierten erreicht die von ihm selbst
geladene nicht — der Test laeuft und die Attrappe wird nie benutzt. Die Ladefunktion
patchen und Antwort **je Endpunkt** liefern. Bleibt die Aufrufliste der Attrappe
leer, liegt die Naht falsch, nicht der Test.
69b. **„Die Suite war schon rot" ist eine Behauptung, keine Messung.** Beide
Zustaende mit derselben Suite fahren und die Fehlernamen differenzieren. Fuer die
Gegenprobe `git show HEAD:<pfad>` in die Datei schreiben statt `git checkout` — das
ueberschreibt uncommittete Fremdarbeit.n der MITTE laesst positionelle Aufrufer still in den falschen Slot rutschen: kein Fehler, ein leeres Ergebnis („nicht messbar"). Hinten anhaengen, Aufrufer greppen; Volltext in `references/spur-tests-und-auswertung.md`.
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

86. **Eine Whitelist fuer die Subprozess-Umgebung bricht ALLE Spuren** — die Spuren sind vertrauenswuerdiger eigener Code und brauchen die API-Schluessel in ihrer Umgebung; `_env_sicher()` reicht die volle Umgebung durch.

87. **Feste Zaehl-/Sollwert-Tests (`len(HOLER)`, `ERWARTET`-Dicts) sind eine LISTE, die eine Spur nennt** — beim Anschliessen mitziehen, sonst faellt die volle Suite rot, ohne dass etwas kaputt ist.

89. **Ein stiller `except`-Zweig behauptet einen Sachverhalt, den er gar nicht geprueft hat.** Faengt eine Funktion wie `zeitfenster_offen()` eine Ausnahme ab und gibt `False` zurueck, meldet sie "kein Zeitfenster" — obwohl das Fenster offen sein kann und der Importfehler die Ursache ist. Ausnahme-Zweige im Live-Pfad: nach `stderr` schreiben, nicht schweigen. Die MELDUNG muss den Fehler nennen (`Zeitfenster nicht lesbar`), nicht den Zustand (`Freigabefenster nicht offen`).

88. **Eine Skip-Wache auf den falschen Teil gesetzt macht die Routine dauerhaft wirkungslos.** Vor dem Einbauen einer Uebersprungs-Bedingung pruefen, was die Routine HEUTE noch tut — nicht was sie mal tat. Belegt: `marktscanner.ps1` sprang bei laufendem Dauerlauf ueber `scan.py` (harmlos, schreibt nur `berichte/*.json`), weil frueher auch `handeln.py` in der Routine stand. Folge: der Ranglisten-Bericht fror auf den Vortag ein, Spuren kauften zu alten Preisen. Alter des ERZEUGNISSES messen (Datei-Mtime von `berichte/neuester.json`), nicht den Exitcode der Routine.

90. **Ein Zwischenlager ist ein Vertrag.** Wer ein Ergebnis weglegt und spaeter
wieder einliest (Rangliste, Kennzahlenstand, Vorrat im `zustand.json`), muss
JEDES Feld mitnehmen, das der Verbraucher braucht - nicht nur die Felder der
Anzeige. Sonst faellt der Verbraucher in seinen Rueckfall, und der zeigt auf den
Wert, den es vor dem Umbau gab: die Aenderung wirkt dann nur auf den ersten Lauf
(Beleg: `swap` handelte nach dem Zwilling-Umbau wieder `XAU-USDT-SWAP`, OKX
50124). Dazu gehoeren zwei Sicherungen: ein Stand aus ALTEM Schema wird
verworfen und neu geholt statt bis zum Ablauf zu gelten, und der Rueckfall darf
nie auf den unbrauchbaren Wert zeigen (besser kein Vorschlag als eine Order, die
nur abgewiesen wird). Gegenprobe: den Verbraucher mit einem Stand aus der DATEI
fahren, nicht mit einem frisch gebauten Dict - ein Test mit `handels_instr` im
Speicher war gruen, waehrend die Spur den falschen Markt handelte.

91. **Eine Sperrzeile, die nur im Fehlerfall gedruckt wird, ist von "nicht
geprueft" nicht zu unterscheiden.** Und der Dauerlauf parst genau diese Zeile:
`if g: print("Live waere gesperrt durch: …")` laesst bei leerer Liste eine
Luecke, die wie ein abgebrochener Lauf aussieht. Immer drucken, leere Liste als
`nichts`. Dazu gehoert die zweite Haelfte: die Vorschau nennt den GEGENSTAND der
Order (das gehandelte Instrument), nicht den Zwischennamen, aus dem er
abgeleitet wurde.

92. **Eine Anzeige, die ihre Ausnahmen verschweigt, liest sich als fehlerfreier
Automat.** Zaehlt eine Kennzahl nur eine Teilmenge (echte Handelsrunden ohne
Zwangsschluss und Buchhaltungs-Korrektur), gehoert der Zusatz in DIESELBE Zeile -
sonst fuellt der Leser die Luecke mit dem guenstigsten Fall („Treffer 100 %" bei
drei Ausstiegen daneben). Vollen Text: `references/pitfalls.md`.

93. **Ein Kill-Switch-Ausstieg ist kein Beleg fuer eine Verlustposition.** Er
feuert auf den kumulierten Ruecklauf vom realisierten Peak, nicht auf die
aktuelle Position - gemessen 27.09.2026 bei xperp waren alle fuenf
Kill-Ausgaenge positiv (+0,4 bis +2,4 %). Vor der Deutung die Drawdown-Kurve
FIFO-gepaart nachrechnen und den Deckel gegen den je erreichten Ruecklauf
halten; ein Deckel weit darueber ist entschaerft, kein Fehler. Vollen Text:
`references/pitfalls.md`.
94. **Eine unbestaetigte Fuellung ist keine Null.** Wird die Boersenantwort sofort
nach dem Kauf gelesen, ist sie leer oder ein Bruchteil; `int(0.4)` = 0 und daraus
gehen Stop UND Rueckdrehung mit `size: 0` an die Boerse (`invalidArgument: 0`).
Die Rueckdrehung bleibt wirkungslos und wird als Erfolg protokolliert. Lesefunktion
warten und `(menge, bestaetigt)` zurueckgeben, nie auf 0 herunterrechnen
(`max(1, int(round()))`), einen Abfragefehler nie als Nullbefund lesen, und
unbestaetigt mit der BESTELLTEN Groesse weiterarbeiten. Vollen Text:
`references/live-order-und-buchpflege.md` Abschnitt 15. Die drei Fehler als KETTE
(inkl. Buch-gegen-Boerse mit drei Orders und einem Waisen-Stop 0,19 % unter dem
Kurs) in `references/orderweg-sicherheitskette.md`.
95. **Eine Rueckdrehung gilt erst, wenn die BOERSE die Position nicht mehr fuehrt.**
„Verkauf abgeschickt" ist keine Rueckdrehung — die Wirkung wird am Bestand
gemessen, nicht am Erfolg des eigenen Aufrufs. Bleibt die Position stehen, ist das
eine Lueckenmeldung und kein weiterer Einstieg. Ein Rueckweg, dessen Wirksamkeit
nicht gemessen wird, ist eine Annahme.
96. **Ein Einstiegs-Gate darf den Ausstieg nie sperren.** Eine Freigabe, die einen
NEUEN Markt eroeffnen soll, gehoert nicht auf den Ausstiegspfad: als modulweite
Variable, die nur der Einstiegszweig setzt, sperrt sie jeden Kursabruf und haelt
die Live-Position fest. Loesung: der Aufrufer sagt den Zweck
(`pf_markt(inst, fuer_ausstieg=True)`) — und JEDER Weg laedt die Vorbedingungen
(Marktliste, Kennung), die er zum Aufloesen braucht. Der Ausstieg umgeht die
Freigabepflicht, NIE den Beweis, dass es den Markt gibt. Merksatz: **ein
Ausstiegspfad ist die einzige Stelle, die IMMER funktionieren muss** — und er ist
meist die, die am spaetesten gebaut und am seltensten gelaufen ist; er braucht
keinen Freigabepflicht-Pfad, sondern einen eigenen.
**Und die Kurve selbst zerlegen, bevor ein Deckel angefasst wird.** Die
Kapitalkurve rechnet auf ALLEN Buchungen, also auch auf
Buchbereinigungs-zeilen, die keine Handelsrunde sind. Gemessen an einer Spur:
von 25 Buchungen seit dem Hoch waren 20 Bereinigungen mit −266 USD und nur
5 echte Runden mit −14 USD — der Deckel stand auf 280, davon waren rund 184
fiktiv. **Buchbereinigungs-zeilen gegen die realisierte PnL-Historie der
Boerse stellen (`/account/positions-history`, `closedPos`/`realizedPnl` je
Instinkt)**: die Belege mit derselben Kontraktzahl sind dieselbe Position, und
weicht der Erloes der Zeile deutlich ab, ist die Zeile falsch gebucht. Ein
Deckel, den man ueber eine noch nicht korrigierte Buchung hebt, verschiebt
nur den Tag, an dem man es merkt — die Korrektur kommt vorher.

94. **Ein gemeinsamer Kern, der die Sperrzeile nicht druckt, schaltet die
Auto-Freigabe fuer ALLE seine Spuren ab.** `dauerlauf.nur_fenster_fehlt()` liest
die `--vorschau`-Ausgabe der Spur; fehlt die Zeile „Live waere gesperrt durch:
…" ganz, kommt `None` zurueck — kein Fenster, kein Live-Lauf, und die Spur sieht
nur „still" aus. Die Sperrzeile gehoert in JEDEN Modus, den ein Aufrufer parst
(auch `--vorschau`), nicht nur in den Live-Zweig. Vollen Text:
`references/live-tor-und-einsatzgroesse.md`, Abschnitt 6.

96. **Ein Cache oder Validator, den niemand laedt, sieht aus wie „unbekannt".**
Wer eine Marktauflösung um eine Liste erweitert (Instrumentliste der Boerse,
Pair-Tabelle, Whitelist), muss den LADER aus dem Lauf aufrufen und danach den
Laufaufruf im Quelltext suchen. Ein `maerkte()`, das absichtlich nur den
bereits geladenen Stand zurueckgibt (kein Netzzugriff auf dem heissen Pfad),
liefert ohne Lader leer — und der Aufrufer meldet fuer JEDEN Namen
„unbekanntes Instrument". Das sieht nicht nach fehlendem Lader aus, sondern
nach einer falschen Zuordnung, und es kostet den Lauf still: die Spur ist
scharf, das Tor offen, und jeder Zyklus endet in einer Fehlerzeile. Merksatz:
**leerer Cache und unbekannter Name sind im Befund nicht unterscheidbar** —
im Zweifel die Cache-Groesse als eigene Zeile ausgeben, dann sieht man
sofort, ob geladen wurde.

97. **Ein Belegwerkzeug, das echte Ordern stellt, braucht einen BILLIGEN
Vorgabemarkt — und seine Groesse wird gerechnet, nicht angenommen.** Am
Futures-Weg war 1 Kontrakt = 1 Einheit der Basiswaehrung (1 Kontrakt BTC
rund 84.600 USD), das Werkzeug rechnete aber „1 Kontrakt = 1 USD" und haette
mit seiner Vorgabe acht Kontrakte fuer ueber 676.000 USD gekauft. Zwei Regeln:
Nennwert = Kontrakte × Kurs und der benoetigte Einschuss aus dem Margenplan
des Marktes, im Tor anzeigen (dann bricht die Sonde ab, statt zu kaufen);
und die Vorgabe auf einen Markt setzen, dessen 1 Kontrakt ein paar Cent
traegt. Dazu: **sobald die Order gesendet ist, ist der Schutz-Stop der
naechste Schritt und darf hinter keinem Schritt stehen, der werfen kann** —
ein Fill-Polling, das nach der Fuellung fehlschlug, liess die Position ohne
Stop offen. Eine Pruefung, die
NACH dem Schneiden laeuft, nennt das falsche Uebel: erst die Laenge auf der
PLATTE messen, dann schneiden, und beide Gruende getrennt benennen (Historie zu
kurz -> nachfuellen; Fenster zu klein -> Bedarf `mindest_kerzen + 20` nennen).
Und ein Lauf, der "0 Runden" melden kann, ohne je einen Schritt gerechnet zu
haben, ist ein stiller Ausfall, kein Messergebnis. Vollen Text:
`references/pitfalls.md`.

98. **Ein boolescher Existenztest wirft die MENGE weg — und die MENGE ist der
Schutz.** Die Abgleichstufen einer Live-Spur fragen alle „ob": ob die Position
da ist, ob die Kontraktzahl stimmt, ob EIN Schutzauftrag liegt. Keine fragt, wie
viele Kontrakte dieser Schutz abdeckt, und ein Treffer genuegt: `_stop_vorhanden()`
liefert `True`, sobald irgendein Auftrag gefunden ist. So standen 19 von 145
Kontrakten ohne Schutz, waehrend Spur, Bericht und Abgleich „ok" sagten. Wer eine
gehebelte Position schuetzt, misst `sum(sz)` der Schutzauftraege gegen den
BESTAND AN DER BOERSE (nicht gegen das Buch — ein Handgriff kann das Buch
verkleinert haben) und stellt nur die Restmenge nach. Als Schutz zaehlt ein
Auftrag nur mit `reduceOnly`, mit der Seite GEGEN die Position und mit einer
Ausloesung (`slTriggerPx` oder `tpTriggerPx` — ein Trailing traegt kein
`slTriggerPx`); der vorhandene Filter ist derselbe wie `okxf.ist_schutz_stop`,
nur ohne die Menge, und genau das ist der Unterschied. Bestehende Schuetzte
werden nie storniert und nie nachgezogen (T-278), ein nachgesetzter Stop ist
ein Vermerk im Zustand und KEINE Journalzeile (sonst entsteht eine Runde, die
nie stattfand), und ein Stop auf der falschen Seite ist kein Schutz: long-Stop
auf/ueber dem Kurs verkauft sofort, ein Stop auf/unter `liqPx` kommt nach der
Liquidation nie — beide verweigern und melden, statt eine scheinbare Deckung zu
bauen. Werkzeug `xperp/stopdeckung.py`: Vorschau Standard, und `--anwenden` OHNE
`--stop` stellt nichts — das Werkzeug rät keinen Schutzpreis. Volltext:
`references/live-order-und-buchpflege.md`, Abschnitt 5d.

99. **Eine neue Journal-Spalte braucht die Kopf-Migration im SELBEN Zug.** Der
Zeilen-Schreiber schneidet auf die Kopf-Laenge des Altfjournals
(`pos_kennung.zeile`), also verwirft ein Altjournal ohne die neue Spalte den
neuen Wert — oder schreibt ihn in den Slot der LETZTEN Spalte, wenn der
Schreiber die Spalte vor dem Schluss einfügt: gemessen stand der neue
Herkunft-Wert in der pos_id-Spalte und die echte pos_id war weg, bei einer
LIVE-Kaufzeile. Vorgehen: Kopf migrieren (csv-Roundtrip, Sicherung
`.bak-JJJJMMTT` vorher, alle Altzeilen auf die neue Laenge polstern),
Gegenprobe = Zeilenzahl unveraendert + einheitliche Laengenverteilung, und
verlorene Werte aus dem ZWEITEN Zeugen holen, bevor man sie als Verlust
akzeptiert (die pos_id der Position stand noch im Zustand). Zusätzlich:
einen Reweave-Ablauf NICHT inline in einen Heredoc schreiben — `open('w')`
kürzt die Datei VOR dem ersten `writerows`-Fehler, eine Ausnahme mitten in
der Migration hinterlässt eine halbe Datei; Skript in eine Datei legen,
Restaurierbarkeit (Backup) prüfen, erst dann laufen lassen.

100. **Ein abgestuerzter Kindprozess ist fuer einen Parser nicht von einer leeren
Antwort zu unterscheiden.** `sperrgruende.py` liest die Sperrzeile aus der
`--vorschau`-Ausgabe; ein Spur-Lauf, der mit `ModuleNotFoundError` stirbt,
liefert genauso wenig Text wie eine Spur, die nichts zu melden hat, und beide
erscheinen als `keine Sperrzeile`. Gemessen waren zwei Spuren „blind", die im
Quelltext die Zeile sehr wohl hatten - sie liefen nur mit dem venv des Nachbarn.
**Ein Werkzeug, das `handeln.py` mehrerer Spuren startet, braucht je Spur ihren
eigenen Interpreter** (Reihenfolge: die Spur selbst, dann Nachbarspuren, dann
der Standard); und **die Ausgabe eines Kindprozesses wird auf Fehler geprueft,
nicht nur geparst** - `returncode != 0` und eine leere Antwort sind zwei
verschiedene Befunde und muessen zwei verschiedene Zeilen sein. Merksatz: „nicht
geprueft" und „nichts gefunden" sehen in einer Tabelle gleich aus.

101. **Wenn keine Spur allein am Fenster haengt, ist die Auto-Freigabe nicht der
Hebel - die beiden Haken sind es.** `nur_fenster_fehlt()` verlangt **genau
einen** Sperrgrund; eine Spur mit drei Gruenden (beide Haken false plus kein
Fenster) wird nie gefragt, egal wie oft sie startklar waere. Der Befund
`Keine Spur haengt allein am Fenster` heisst also nicht „die Auto-Freigabe ist
kaputt", sondern „es steht nie eine Freigabe-Anfrage an". Weg: erst die beiden
Schalter auf die Spuren mit echtem Orderpfad, danach arbeitet die vorhandene
Mechanik von selbst - belegt daran, dass ein Fenster `freigegeben_von: auto`
traegt, ohne dass jemand es geoeffnet hat. **Und das Gegenteil gilt auch:**
`handel_erlaubt=true` auf einer Spur, deren einziger weiterer Grund ein KILL oder
ein negativer EV ist, oeffnet das Fenster - und der naechste Live-Lauf raeumt
das Buch. Der Schalter wird nie ohne Blick auf die restlichen Gruende gesetzt,
und der AUSSCHLIESSLICHE Grund - nicht der haeufigste - entscheidet.

102. **Die Strategie wird auf dem Instrument gemessen, das wirklich handelbar
ist - nicht auf dem, dessen Weg schon steht.** Bei der Wahl zwischen zwei
Maerkten kann dieselbe Regel eine Kante tragen oder keine, ohne dass die
Trefferquote es verraet: gemessen dieselbe Indikatorregel auf zwei Maerkten mit
nahezu gleicher Trefferquote (28,6 % gegen 29,6 %) und einem Ergebnis von
+755 USD gegen +1,61 USD. Wer den vorhandenen Weg nimmt, weil er schon steht,
baut die falsche Spur und nennt es eine Messung. **Vor dem Umbau beide
Kandidaten mit demselben Fenster, demselben Takt und derselben Gebuehr fahren
und das Ergebnis je Markt vergleichen** - und die Kerzendaten des schwachen
Kandidaten gegenpruefen (erstes/letztes/Extrem), bevor man die Regel verurteilt.

103. **Der Einstieg ist der Marktpreis von JETZT, nicht der Berichtspreis von gestern** - ein Tagesbericht ist ein Snapshot (schluss[-1] der 1D-Kerze). Liegt der Einstieg unter dem Kurs, ist das Ziel schon beim Kauf erfuellt. Gemessen am Scanner (T-322): 82 Scheinrunden an einem Tag, 97 von 105 Ausstiegen nach 0,25 h, +17,49 % und t=15,3 - die ehrlichen Runden brachten +1,99 %. Drei Alarme im Journal: Haltedauer im Zyklustakt, ein Instrument traegt die meisten Runden, hoeherer Score ergibt schlechteres Ergebnis. Volle Zahlen in references/pitfalls.md, Punkt 103.

104. **Eine Trefferquote ist kein Edge.** Was zaehlt, ist die EXCESS-Rendite: Rundenergebnis minus der Marktbewegung desselben Instruments ueber dieselbe Zeit (BUY & HOLD aus den gespeicherten Kerzen). Nahe 0 heisst, die Spur IST die Marktbewegung; negativ heisst, die Runden weglassen. Gemessen am Scanner (T-322): 93 % Treffer bei +19 % Mean, ehrlich 38 % bei +1,99 %. Und: eine Basislinie, die FEHLT, ist ein Befund - nicht ein Grund, sie wegzulassen. `historie_binance.PAARE` kannte 30 Journal-Namen, aber nur drei Basiswerte, deshalb war fuer jede Spur ausser BTC/ETH/SOL keine Edge-Messung moeglich; ein Mapping muss Basiswerte kennen, `spur_audit.basisform()` reduziert jeden Namen darauf. Werkzeug: `spur_audit.py` (alle Spuren in einem Durchgang, drei Alarme plus Excess). **Und die gefaehrlichste Form davon: eine Kennzahl, die nur fuer eine TEILMENGE berechenbar ist, meldet den Teil als das Ganze** - eine Runde von 15 Minuten hat keine volle Kerze im Fenster und damit keine Basislinie, und genau diese Runden sind die Scheinrunden; gemessen +16,6 % Excess auf den kurzen gegen +1,5 % auf den langen Runden. **Jede Kennzahl nennt die Zahl der gemessenen UND der ausgeschlossenen Runden und wird getrennt nach der Eigenschaft ausgewiesen, die den Verdacht traegt.** Volle Zahlen in references/pitfalls.md, Punkt 104, Verfahren in `references/edge-und-statistik-audit.md`.

105. **Ein leeres Ergebnis einer Liste ist ein AUSFALL, keine Messung — und wird als Messung ausgegeben, ist es eine erfundene Tatsache.** Ein Abruf mit vertauschten Argumenten lieferte 0 Eintraege; der Code meldete daraus fuer ALLE Namen „kein Spotmarkt", darunter welche mit Markt. Die Liste pruefen, BEVOR ueber ein Element geurteilt wird; leere Liste und Abruffehler sind zwei Befunde und muessen zwei Zeilen sein.

106. **Ein Pruefer, der seine eigene Voreinstellung als Befund ausgibt, sieht gesunde Spuren kaputt.** Fuenf Spuren wurden als „kein Kurs" gemeldet, weil der Pruefer bei JEDER Boerse sein eigenes Standardinstrument abfragte (`BTC-USDT-SWAP` statt BTC/EUR bzw. `PF_XBTUSD`). Das Instrument kommt aus der WACHE der Spur, nie aus einer Vorgabe des Pruefers; gibt die Wache nichts her, meldet er `kein Instrument konfiguriert` und laeuft weiter.

107. **Eine Merkdatei, die Tupel speichert, erkennt nie eine Aenderung — json gibt Listen zurueck.** Der Vergleich passte nie, die Meldung kam bei JEDEM Lauf erneut, und genau das schaltet eine Wache ab. In der Merkdatei nur Skalare ablegen, Sets und Tupel beim Lesen wieder bilden; Abnahme: derselbe Zustand zweimal, der zweite Lauf muss still sein.

108. **Kapital stapelt sich, Risiko nicht: die zwei Summen sind verschiedene Fragen.** Fuenf Schreibweisen einer Basis (`-USDT-SWAP`, `-USDC`, `-USDT`, `XBT-USD`, `-USD_UM_XPERP`) sind EINE Wette, und das Kapital darauf uebersteigt die groesste Einzelposition um ein Vielfaches. Beide Summen ausweisen (je Spur UND je Basis); die Differenz als „Doppelzaehlung" zu bezeichnen ist falsch — jedes Risiko hat seinen eigenen Stop und addiert sich korrekt, gestapelt ist das KAPITAL.

