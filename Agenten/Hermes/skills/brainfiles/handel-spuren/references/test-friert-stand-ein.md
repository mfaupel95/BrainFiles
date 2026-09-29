# Ein Test darf einen STAND einfrieren

## Das Muster

Ein Test, der gegen einen Commit-Hash, eine Byte-Gleichheit oder eine feste
Anzahl prueft, meldet **Aenderung**, nicht **Fehler**. Er wird rot, sobald
jemand woanders korrekt arbeitet - und faellt dann als Rauschen durch, bis
ihn niemand mehr ernst nimmt. Das ist schlimmer als kein Test.

Drei Faelle aus BrainFiles, alle am selben Tag (21.09.2026):

| Test | Was er einfror | Was daran kaputtging |
|---|---|---|
| `Bus/tests/test_anbindung_handel.test_melder_bleibt_unveraendert` | `melder.py` byte-genau gegen Commit `3a9b6e5` | Nach der Telegram-400-Reparatur rot, obwohl die Spec unverletzt war |
| `tests/test_lage.test_holer_sind_vollzaehlig` | genau 28 Holer | Jede neue Spur macht ihn rot |
| `tests/test_risikovorfilter` | festes JETZT `2026-09-17 12:00` | Wurde mit dem Kalender falsch, nicht mit dem Code |
| `tests/test_omniquant_fassung` | Fixture-Stempel `erzeugt: 2026-09-24T09:01:00` neben der Regel "Alter < 26 h" | Kippte 26 h spaeter in `Bericht 123.0 h alt, Grenze 26 h` — ein Fixture mit ALTERSGRENZE ist eine Uhrzeitbombe, kein Standbild |

## Die Regel

**Pruefe die EIGENSCHAFT, die gelten soll - nicht den Zustand, in dem sie
gerade zufaellig steht.**

Die Spec hinter dem melder-Test lautete: *melder.py wird nur aufgerufen, nicht
zur Bus-Stelle umgebaut.* Das ist pruefbar, ohne einen Hash zu nennen:

```python
# schlecht - friert einen Stand ein
self.assertEqual(hashlib.sha256(quelle).hexdigest(), "3a9b6e5...")

# gut - prueft die Regel
self.assertNotIn("import ereignis", quelle)
self.assertNotIn("bus.py", quelle)
self.assertNotIn("8787", quelle)
```

Und statt einer festen Anzahl die Beziehung zur Quelle der Wahrheit:

```python
# schlecht
self.assertEqual(len(lage.HOLER), 28)

# gut - jede Spur aus dauerlauf.SPUREN hat einen Holer,
# Praefix erlaubt (xperp liest ueber spur_xperp_positionen)
for spur in dauerlauf.SPUREN:
    self.assertTrue(any(name.startswith("spur_" + spur)
                        for name in lage.HOLER))
```

Bei Zeitbezug: die Zeit als Parameter hereingeben, nie `datetime.now()` gegen
eine Konstante im Test stellen.

```python
# gut - der Test waehlt die Zeit, die Funktion rechnet
self.assertTrue(wx.wochenende_sperrt(W, _zeit(4, 19, 0)))   # Fr 19:00 UTC
self.assertFalse(wx.wochenende_sperrt(W, _zeit(0, 9)))      # Mo 09:00
```

## Der Fixture-Zeitstempel ist derselbe Fehler in klein

Ein Fixture, das einen ZEITSTEMPEL traegt (`erzeugt`, `letzter_lauf`, `stand`)
und von der geprueften Regel gegen eine ALTERSGRENZE gehalten wird, ist eine
Uhrzeitbombe: solange das Fixture juenger ist als die Grenze, gruen - danach
rot, ohne dass sich am Code etwas geaendert hat. Der Fehler faellt nicht beim
Bau auf, sondern Tage spaeter bei jemand anderem, und die Fehlermeldung zeigt
auf die FRIST statt auf den Test.

```python
# falsch - das Datum ist eine Frist, die abgelaufen ist
json.dump({"erzeugt": "2026-09-24T09:01:00+00:00", "treffer": []}, f)

# richtig - relativ zu jetzt, die Grenze bleibt pruefbar
jetzt = datetime.now(timezone.utc) - timedelta(hours=1.0)
json.dump({"erzeugt": jetzt.isoformat(), "treffer": []}, f)
```

Und **die Gegenprobe gehoert dazu**: ein frisches Fixture belegt nur, dass der
Bericht genommen wird - nicht, dass die Grenze greift. Zweiter Fall mit
`stunden_alt=27.0` bei Grenze 26, der abgelehnt werden MUSS. Eine Grenze, die nur
in eine Richtung geprueft wird, ist zur Haelfte ungeprueft (dasselbe Muster wie
ein Schwellwert, der nie ausloest).

## Zweite Familie: der Test legt nur die HALBE Umgebung still

Nicht der eingefrorene Wert ist hier das Problem, sondern der **echte
Betriebszustand, der mitentscheidet**. Der Test ersetzt einen Eingang, den die
geprueffte Regel liest - aber nicht alle.

| Test | stillgelegt | vergessen | Folge |
|---|---|---|---|
| `test_sperre_ohne_freigabefenster` | `sitzung_da()` | `zeitfenster_offen()` | Bei offenem Fenster fehlt der Sperrgrund ZU RECHT -> rot genau dann, wenn die Spur korrekt live faehrt |
| `test_ohne_modul_false` | `sys.modules[...]` | das Modul wird ueber den DATEIPFAD geladen und als **Modulattribut** gehalten | Der Stub erreicht die Spur nie; der Test prueft nichts |

**Regel: vor dem Stilllegen auflisten, was die Regel liest, und JEDE dieser
Quellen stilllegen - nicht nur die, die im Rueckgabewert sichtbar wird.** Ein
Test, der gegen den echten Betriebszustand mitrechnet, ist gruen, solange
niemand arbeitet, und rot, sobald die Spur tut, was sie soll: er erzeugt genau
dann Fehlalarm, wenn das System gesund ist.

Rezept fuer zustandslesende Funktionen: die **Pfad-Konstante** des Moduls auf
einen Temp-Ordner zeigen lassen (`mod.HIER = tmp`, zurueck per
`addCleanup(setattr, ...)`), dort die Varianten anlegen (frisch / alt / kaputt /
fehlend) und alle Faelle in einem Test durchspielen. So wird die Regel geprueft,
ohne die echten Dateien anzufassen - und der Test belegt die Rangfolge
(z. B. "frischester Stand gewinnt"), nicht nur einen Einzelwert.

## Dritte Familie: der Test behauptet einen SCHALTER, nicht die Regel

Ein Test, der ein Konfigfeld gegen seinen AKTUELLEN Wert prueft, ist derselbe
Fehler wie ein eingefrorener Stand — nur friert er eine Entscheidung des Nutzers
statt einen Commit ein. Gemessen: `test_kein_live_und_keine_freigabe` verlangte
`handel_erlaubt == False` und `freigabe.erfuellt == False`. Ein Sammelauftrag
("schalte alle Spuren scharf") setzte beide Felder in JEDER `wachen.json` auf
true — der Test war rot, ohne dass irgendetwas kaputt war, und die Versuchung
ist, ihn "zu reparieren", indem man den Schalter zurueckdreht.

**Regel: die Eigenschaft pruefen, die gelten soll — hier "diese Spur hat keinen
Orderweg" — nicht die Stellung des Schalters.**

```python
# schlecht - behauptet eine Entscheidung
self.assertFalse(W["handel_erlaubt"])
self.assertFalse(W["freigabe"]["erfuellt"])

# gut - prueft die Eigenschaft, die den Schalter wirkungslos macht
modus, meldung = h.live_gate("live")
self.assertEqual(modus, "papier")
self.assertIn("Orderaufruf", meldung)
```

Dieselbe Form gilt fuer jeden "ist abgeschaltet"-Test: nicht das Flag lesen,
sondern den Weg, der ohne das Flag scharf waere (Orderaufruf, Schreibpfad,
Netzaufruf) — und pruefen, dass er nicht erreicht wird. Ein Flag ist eine
Absicht, kein Verhalten.

## Vierte Familie: der Test kann den ECHTEN Weg erreichen

Seit eine Spur scharf gestellt werden kann, ist die gefaehrlichste Testart nicht
mehr der rote, sondern der **gruene, der eine echte Order ausloest**. Ein Test,
der den Live-Zweig fahrt (weil die Wachen inzwischen `handel_erlaubt: true` und
ein offenes Freigabefenster tragen), schickt Geld an die Boerse - und die Suite
meldet danach "ok".

Regel: **Tests duerfen Konstruktoren, Sperrenketten, Vorschau und Ausstiegslogik
fahren - nie den Orderweg.** Beleg das ueber die QUELLE des Testmoduls:

```python
text = open(__file__, encoding="utf-8").read()
verboten = "--" + "live"          # aus Teilen bauen!
self.assertNotIn(verboten, text)
self.assertNotIn("markt_kauf", text)      # bzw. der Orderaufruf des Hauses
self.assertNotIn("stop_setzen", text)
```

**Den verbotenen Suchtext aus TEILEN bauen** (`"--" + "live"`): steht er ganz im
Testmodul, findet der Test sich selbst und ist immer rot - oder, schlimmer, er
wird "repariert", indem die Pruefung weich gemacht wird.

Wo der Live-Weg trotzdem geprueft werden soll, pruefe ihn ueber
**eingeschleuste Attrappen** (Seam-Bindung des Moduls, `validate=true`-Probe ohne
Geld) statt ueber den echten Aufruf - und die Seam-Bindung muss VOR der ersten
Sperrenpruefung passieren, sonst laeuft der Zweig ungebunden.

Dieselbe Familie, harmlosere Form: ein Test, der den Vorschau-/Sperrtext gegen
den Zustand von HEUTE prueft (`assertIn("handel_erlaubt", text)`). Er wird rot,
sobald die Spur (korrekt) scharf geht. Richtig ist die Pruefung gegen die QUELLE
- die Menge der Sperrgruende muss der Menge der Gruende in der `wachen.json`
entsprechen, und ein Grund muss aus dem Zustand folgen, nicht zitiert sein.

## Modulglobale zwischen Testdateien: sichern und zuruecklegen

Ein Modulglobal, das ein Test umbiegt (`VENUE`, `SCHREIBEN`, `HIER`, ein
Boersenmodul-Attribut), leckt in die naechste Testdatei derselben Suite. Symptom:
ein Test, der allein gruen ist, faellt im Gesamtlauf (oder umgekehrt), und die
Reihenfolge der Dateien entscheidet ueber das Ergebnis.

```python
def setUp(self):
    self._alt = handeln.VENUE          # vor dem Umbiegen merken
    handeln.VENUE = self._okx

def tearDown(self):
    handeln.VENUE = self._alt          # zuruecklegen, nicht auf den
                                       # "erwarteten" Wert setzen
```

Ein Modul, das einen Schalter selbst beim IMPORT setzt, braucht zusaetzlich eine
Klasse, die den Import isoliert. Und die Reihenfolge nicht als Schutz benutzen:
eine Suite, die nur in EINER Reihenfolge gruen ist, ist eine Zeitbombe.

**Und die eigene NEUE Testdatei setzt einen Schalter nie modulweit (Importzeit).**
`handeln.SCHREIBEN = False` auf Modulebene legt die Journale der NACHBARdateien
derselben Suite still: der eigene Test ist gruen, ein FREMDER faellt mit
`0 != 1`. Setzen und zuruecklegen gehoert in `setUp`/`tearDown`. Kennzeichen fuer
die Ursachensuche: wird eine Suite rot an einem Test, den man nicht angefasst hat,
zuerst die neu hinzugefuegte Testdatei auf Importzeit-Nebenwirkungen pruefen -
nicht den fremden Test "reparieren".

## Fuenfte Familie: der Test schreibt einen LIVE-Wert in die Behauptung

Dieselbe Falle in klein: eine Zusicherung auf einen **gerechneten Text**, der aus
einem Kurs entsteht. Eine Meldung wie `handelbar()` nennt Einschuss und freies
Guthaben - beide werden ohne Argument aus dem LEBENDEN Konto gelesen, der Text
kippt also mit jedem Kurs. Der Test darf dann nicht gegen eine ausgedachte Zahl
pruefen ("8451"), sondern muss die QUELLE stilllegen und den Text aus den
stillgelegten Werten erwarten:

```python
with patch.object(kf, "instrument", return_value=MARGENPLAN), \
     patch.object(kf, "letzter_kurs", return_value=84485.0):
    self.assertEqual(kf.handelbar("PF_XBTUSD", 1, frei=141.58),
                     "1 Kontrakt PF_XBTUSD braucht 8448.50 USD Einschuss, "
                     "frei sind 141.58 USD")
```

Regel: **jede Funktion, die ihre Eingaben selbst beschafft (Kurs, Guthaben,
Instrument), wird im Test entweder mit dem Wert AUFGERUFEN oder an ihrer Quelle
gepatcht - nie mit einem Literal verglichen.** Ein Literal gegen einen
Live-Abruf meldet Kursbewegung, nicht Codefehler (und faellt in einer Woche
zufaellig wieder gruen aus). Wer dabei ein Instrument fuer ALLE Symbole patcht,
muss beachten, dass auch die Gegenprobe denselben Wert sieht - die
"geht-durch"-Zeile braucht groesseres `frei`, nicht einen anderen Kurs.

## Quelltext-Pruefer: den AUFRUF ankern, nicht die Definition

Ein Test, der eine Regel im Quelltext nachweist (`assertLess(aufraeumen, kaufen)`),
sucht zwei Stellen per `quelle.index(...)`. Ein kurzer Anker trifft zuerst die
`def`-Zeile derselben Funktion:

```python
# falsch - "live_ausstiege(z, w)" steht in der Definition, lange vor dem Aufruf
kaufen = quelle.index("live_ausstiege(z, w)")

# richtig - ab der Funktion suchen, in der der Aufruf stehen soll
kaufen = quelle.index("live_ausstiege(z, w)", quelle.index("def lauf(modus)"))
```

Dasselbe fuer die Reihenfolge zweier Aufrufe: den Anker MIT Klammern und
Argumenten waehlen (nie den blossen Funktionsnamen), und den Test einmal mit
vertauschter Reihenfolge gegenproben - ein Quelltext-Test, der auch bei falscher
Reihenfolge gruen bleibt, prueft nichts.

## Wann ein eingefrorener Stand DOCH richtig ist

Wenn die Unveraenderlichkeit selbst der Vertrag ist und es keine formulierbare
Eigenschaft gibt - etwa bei einer Fixture-Datei, deren Inhalt eine gemessene
Realitaet festhaelt (`kerzen_BTC-USDT_1H_8760.json`). Dann gehoert in den Test
eine Zeile, die sagt WARUM eingefroren wird, und wer ihn erneuern darf.

## Gegenprobe beim Umbau

Nach dem Umbau muss der Test den urspruenglichen Fehler noch fangen. Also:
Regel verletzen (z. B. `import ereignis` testweise in `melder.py` schreiben),
Test laufen lassen, rot sehen, zuruecknehmen. Ein umgebauter Test, der nichts
mehr faengt, ist ein geloeschter Test mit Zeremonie.
