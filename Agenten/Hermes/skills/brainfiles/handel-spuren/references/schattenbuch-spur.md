# Schattenbuch-Spur (Varianten einer bestehenden Spur)

Wann: dieselbe Signalquelle soll mit ANDEREN Parametern parallel laufen, ohne
das Hauptbuch anzufassen - Vergleichsstudie der Ausstiegsgeometrie
(spiegel_knapp/spiegel_weit, 19.09.2026). Das Hauptbuch bleibt die
Vergleichsgrundlage; die Varianten sind Schattenbuecher.

Abgrenzung: eine NEUE Spur mit eigener Signalquelle ist der andere Weg
(`references/neue-spur-ende-zu-ende.md`). Hier teilen sich alle Varianten den
Kern und die Signalquelle, nur die Parameter und die Dateien sind getrennt.

## Mechanik: ein Suffix, das durch alle Datei-Konstanten laeuft

1. **`_buch_datei()` haengt ein Suffix vor die Endung.** Eine Umgebungsvariable
   (z. B. `HANDEL_BUCH`) steuert es: leer = Hauptbuch, sonst `.knapp`/`.weit`.
   Die fuenf Datei-Konstanten (zustand, journal, ablehnungen, ...) laufen
   dadurch ALLE durch - eine Konstante, die den Suffix nicht bekommt, schreibt
   ins Hauptbuch und vergiftet die Vergleichsgrundlage.
2. **Launcher je Arm setzen die Variable und rufen den Kern.**
   `spiegel_knapp.py`/`spiegel_weit.py` setzen `HANDEL_BUCH` und rufen die
   Kern-`_main()` mit eigener Bus-Meldung (`handel/spiegel_knapp`). Der Kern
   bleibt unveraendert; die Launcher sind die einzige neue Einstiegsdatei.
3. **Arm-Wachen je Variante** (`wachen.knapp.json`/`wachen.weit.json`) mit den
   abweichenden Parametern. Der Kern liest die Wachen-Datei ueber den
   Suffix-Pfad, nicht die Haupt-Wachen.

## Verdrahtung (die Stellen, die eine Variante mitzieht)

- `dauerlauf.SPUREN` + `NUR_BASIS`: beide Arme nur im Basislauf (keine
  Risikostufe).
- `befehle.FAMILIE`: je Arm ein Eintrag.
- `lage.HOLER` + `spur_<arm>()`: je Arm ein Holer. Bei N gleichartigen Armen
  EINE gemeinsame Helferfunktion mit Suffix-Parameter, nicht N Abschriften
  (Vorbild `_spur_spiegel_arm(suffix)`). `_bilanz` braucht ordner+journal-Param.
- **`spiegelstand.py` muss die Arm-Dateinamen kennen.** Der Byte-Vergleich
  (Bedingung 4) baut die Dateinamen aus den Basisnamen - fuer die Arme muessen
  es die SUFFIXIERTEN sein (`zustand.knapp.json`, `handelsjournal.knapp.csv`),
  sonst vergleicht er die Hauptbuch-Dateien gegen die Arm-Ziele und meldet
  falsch. `spuren_ordner()` aus `dauerlauf` per `ast` lesen (Spurname !=
  Ordnername, wenn mehrere Spuren einen Ordner teilen).
- **Bus-Anbindungstest: je Spur NUR das zugehoerige `skript`-Feld pruefen.**
  Der Test, der ALLE Skriptnamen gegen ALLE Spuren haelt, schlaegt falsch-positiv
  bei geteilten Ordnern (die Arme teilen `spiegel/`).
- **Festzaehler-Tests mitziehen.** Ein Test, der `len(lage.HOLER) == 25`
  behauptet, bricht, sobald Arme dazukommen - die Zahl ist eine Behauptung,
  die mit jeder neuen Spur veraltet.

## Nachweis

- `spiegelstand.py` meldet N/N byte-gleich (Hauptbuch + alle Arme).
- Die Arme melden sich am Bus (`handel/spiegel_knapp`, `handel/spiegel_weit`)
  und erscheinen im Bericht.
- Dauerlauf-Neustart noetig (SPUREN wird beim Import gelesen); die Arme
  erscheinen erst nach dem ersten Zyklus des neuen Laufs.

## Einen Arm (oder alle) ABSCHALTEN - und wieder anschalten

Dieselbe Stelle, zwei Richtungen. Ein Arm steht in zwei Listen: im
`SPUREN`-Dict (Start) und in `NUR_BASIS` (nur Basislauf, nicht in den
Risikostufen). Wer ihn abschaltet, nimmt ihn aus BEIDEN - sonst schreibt die
Stufe weiter in dieselben Buchdateien. Wird `NUR_BASIS` dabei leer, ist das in
Ordnung (`()`, die Pruefung `if self.stumm and spur in NUR_BASIS` traegt das).

Die Zeilen nicht loeschen, sondern auskommentieren und an beiden Stellen
darueber schreiben, wie sie wieder hineinkommen - die Abschaltung ist meist
„erstmal", und die Buecher bleiben als Vergleichsgrundlage liegen.

**Die Falle sitzt beim WIEDEREINSCHALTEN, nicht beim Abschalten.** Ein Arm, der
laenger als `herzschlag_max_minuten` (180) nicht gelaufen ist, hat ein altes
`letzter_lauf` in seiner `zustand*.json`. Der erste Zyklus danach liest das als
Stoerung und ruft `flach_stellen(..., "herzschlag_alt")` - alle offenen
Papierpositionen sind dann weg, und zwar als Zwangsschluss gebucht, nicht als
Handelsentscheidung. Vor dem Wiedereinschalten deshalb `letzter_lauf` in jeder
`zustand`-Datei des Arms auf jetzt setzen (nur dieses Feld) und erst danach den
Dauerlauf neu starten. Fuer den Hauptarm gilt dasselbe.

Nachweis nach dem Abschalten: der naechste volle Zyklus im `dauerlauf.log`
zaehlt genau die verbliebenen Spuren, und `spiegelstand.py` faellt auf die
kleinere Zahl zurueck und fuehrt das Hauptbuch als „ausserhalb des Dauerlaufs
mitgeprueft" mit (Bedingung 4 bleibt fuer es bestehen).

## Auswertung

Erst ab genug Ausstiegen je Arm (z. B. 30) gegen das Hauptbuch vergleichen:
`auswertung.py --pfad handelsjournal.knapp.csv`. Die Parameter des Hauptbuchs
erst nach diesem Beleg aendern (Stufe-1-Wechsel).

**Vor dem Vergleich die Ausstiege je Arm ZAEHLEN und die Mindestbesetzung
pruefen.** Fordert der Nutzer die Auswertung, bevor die Arme genug Ausstiege
haben, ist die ehrliche Antwort der IST-Stand, keine Vergleichstabelle: die
Zahl je Arm nennen, dass es statistisch wertlos ist (n=1 Token, wenn alle
Ausstiege denselben Token betreffen), und dass ein Vergleich gegen das
Hauptbuch nur moeglich ist, wenn das Hauptbuch im SELBEN Zeitfenster
Ausstiege hat (hat es 0, gibt es nichts zu vergleichen). Eine duenne
Stichprobe NICHT als Ergebnis ausgeben - sie ist ein Zwischenstand, kein
Befund. Die Arme laufen erst seit dem letzten Dauerlauf-Neustart; die
Mindestbesetzung ist in Tagen erreichbar, nicht in Minuten.
