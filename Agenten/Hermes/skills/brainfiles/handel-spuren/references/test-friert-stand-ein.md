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

**Und innerhalb EINER Testdatei ist `mod.funktion = stub` ohne Ruecknahme derselbe
Fehler in klein.** Ein Test, der eine Modulfunktion per blosser Zuweisung ersetzt
(`gs._feld_setzen = lambda ...`), laesst den Stummel stehen: alle folgenden Tests
derselben Datei laufen gegen die Attrappe, und das Symptom zeigt auf den CODE statt
auf den Test (die geprueffte Funktion "setzt den Wert nicht", `KeyError` auf das
erwartete Feld). Gemessen: nach so einem Stummel meldeten sechs spaetere Tests
derselben Datei Fehler an einer Funktion, die in Ordnung war - und der erste Blick
ging auf die Funktion, nicht auf den Test.

```python
from unittest import mock

# falsch - der Stummel bleibt fuer den Rest der Datei stehen
gs._feld_setzen = lambda roh, feld, wert, quelle: (roh, None)

# richtig - der Kontextmanager nimmt ihn zurueck
with mock.patch.object(gs, "_feld_setzen",
                       lambda roh, feld, wert, quelle: (roh, None)):
    with self.assertRaises(RuntimeError):
        gs.anwenden()
```

Merksatz: **ein Stummel braucht IMMER einen Rueckweg** - `mock.patch.object`,
`addCleanup` oder `tearDown`. Die blosse Zuweisung ist nur scheinbar harmlos, weil
sie keinen Fehler wirft; sie faellt erst in den Tests auf, die NACH ihr laufen.

## Den kleinsten Eingabefall nehmen, nicht den realistischen

Ein Test, der eine REALISTISCHE Datei als Eingabe nimmt (echte `wachen.json`, 60
Zeilen), verdeckt genau die Randbedingungen, an denen Text-Werkzeuge scheitern: ist
der neue Schluessel der LETZTE vor der schliessenden Klammer (dann gehoert kein Komma
daran)? steht die Notizzeile schon da, der Wert aber nicht? ist die Zieldatei leer?
Gemessen: ein Werkzeug, das Felder per Zeilenersatz setzt, schrieb in jeder echten
Wache gueltiges JSON und erzeugte bei einer DREIZEILIGEN Testdatei
`Illegal trailing comma before end of object` - in den echten Dateien folgte auf den
neuen Schluessel immer noch ein weiterer.

Deshalb je Verzweigung des Werkzeugs eine MINIMALE Eingabe bauen (nur Notiz / nur
Wert / beides / keins / letzter Schluessel) und die echte Datei als zweiten Fall
nehmen. **Ein Test gegen die echte Datei prueft die Datei, nicht das Werkzeug.**

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

## Sechste Familie: der Test friert die ABWESENHEIT einer Faehigkeit ein

Die Umkehrung der dritten Familie. Ein Test, der belegt, dass eine Spur etwas
NICHT kann, prueft oft nur, dass ein WORT nicht vorkommt - und wird rot, sobald
die Faehigkeit gebaut wird. Gemessen: zwei Tests einer Papier-Spur verlangten
`assertNotIn("Freigabefenster", ausgabe)` mit der Begruendung "sonst fragt der
Dauerlauf eine Freigabe an, die nichts oeffnen kann". Als die Spur einen echten
Orderweg bekam, war genau das Gegenteil richtig: das Wort MUSS dastehen, sonst
findet `dauerlauf.nur_fenster_fehlt()` nichts und die Auto-Freigabe fragt nie.

**Regel: wer einer Spur eine Faehigkeit anbaut, dreht die Tests mit, die ihre
ABWESENHEIT festhalten - im selben Commit, mit dem neuen Vertrag als Kommentar.**
Zwei Fehler sind hier gleich teuer:

- den Test stehen lassen und ihn "gruen machen", indem man die Faehigkeit
  zurueckdreht (der Rueckbau ist dann der eigentliche Schaden);
- den Test loeschen statt umdrehen (die Pruefung verschwindet, obwohl die Regel
  weiter gilt - nur andersherum).

Die Suchform ist immer dieselbe: `assertNotIn(<wort>, <text>)`,
`assertFalse(<schalter>)`, "kein Orderaufruf im Code" - jede Zusicherung, die
eine NEGATIVE Aussage ist, ist ein Kandidat. Vor dem Umbau
`grep -n "assertNotIn\|assertFalse" <spur>/tests/` laufen lassen und die Treffer
einzeln durchgehen; der neue Vertrag steht danach in derselben Zeile.

## Siebte Familie: der Test friert eine GEMESSENE ZAHL ein

Ein Test, der je Spur einen gemessenen Wert als Paar auflistet
(`("scanner", 0.0005), ("orbk", 0.006), …`), ist ein Standbild einer Messung:
sobald jemand genauer misst, wird er rot, ohne dass der Code falsch waere.
Gemessen am 01.10.2026, als die Gebuehrensatze an echten Fuellungen belegt wurden
(scanner handelt OKX-SPOT und damit 0,10 %/Seite = `0.001`, nicht `0.0005`) und
`test_kosten_wendepunkt` genau daran scheiterte — der Test sah wie ein Codefehler
aus, war aber eine veraltete Messung.

Die Zahl ist nicht das Gesetz, sondern eine FOLGE des Marktes. Also den Markt je
Spur festhalten und den Satz daraus ableiten:

```python
MAERKTE = {"scanner": "okx_spot", "orb": "okx_perp", "orbk": "kraken_spot",
           "mosaic": "kraken_spot", "liq_wand": "okx_perp"}
SAETZE  = {"okx_spot": 0.001, "okx_perp": 0.0005, "kraken_spot": 0.006}

self.assertEqual(SAETZE[MAERKTE[spur]], w["gebuehr_taker"],
                 "%s (%s): Gebuehrenfeld fehlt oder hat den falschen Wert"
                 % (spur, MAERKTE[spur]))
```

Dazu die zweite Zusicherung, die den Wert ueberhaupt pruefbar macht: **jeder Satz
traegt seine Quelle** — `[k for k in w if k.startswith("_gebuehr")]` darf nicht
leer sein (aeltere Wachen fuehren sie unter `_gebuehren` bzw.
`_gebuehren_abo_widerlegt`, neue unter `_gebuehr_quelle`). Ein Wert ohne Notiz ist
nicht nachpruefbar, auch wenn er richtig aussieht.

Der Markt ist die Eigenschaft, die zaehlt: wechselt eine Spur die Boerse, MUSS
der Test das zeigen (der Fehlertext nennt den Markt), waehrend ein neuer Messwert
allein die Ableitung nicht kippt.

## Achte Familie: der Test verlangt ein Feld in der FALSCHEN Datei

Gemessen: ein Test verlangte ein Konfigurationsfeld in der **Wachen des
Schattenarms**, obwohl das Feld im **Hauptbuch** gesetzt wird und dort
entscheidet — der Code liest es aus der geladenen Wache und faellt sonst auf
seine dokumentierte Voreinstellung zurueck. Zwei Symptome, beide harmlos
ausssehend: der Test wurde nach der Sichtbarkeit eines Auftrags rot, und der
Arm lief still auf der falschen Datenlage.

**Regel:** ein Test, der ein Feld verlangt, muss sich fragen, **welche Datei**
das im Betrieb liest — nicht, welche Datei thematisch dazugehoert. Ein
Feld, das der Betrieb aus dem Hauptbuch liest, wird dort geprueft, und im Arm
wird die **Eigenschaft** geprueft (der Arm handelt nicht, das Hauptbuch traegt
die Fassung).

## Neunte Familie: der Test bekommt Daten aus dem VORHERIGEN Lauf

Das ist die haeufigste Ursache dafuer, dass eine Testdatei **allein** gruen und
im Gesamtlauf rot ist — und sie sieht aus wie ein Fehler in der gepruefften
Logik. Zwei Caches, beide gemessen:

- Ein **Modul-Cache** auf Basis einer Liste, der nur bei **leerem** Inhalt neu
  geladen wird. Ein Test, der das echte Universum einmal geladen hat,
  hinterlaesst diese Liste fuer den ganzen Prozess. Jeder folgende Test legt
  seine Attrappen in einen Temp-Ordner, bekommt die alte Liste, findet sein
  Symbol nicht, leert die Menge und meldet „0 Buchungen" — ohne Fehler.
- Ein **Werten-Cache im Aufrufer**: der Messweg aendert eine fluechtige Kopie,
  waehrend die aufgerufene Funktion ihre Konfiguration selbst aus der Datei
  laedt. Der Fix wirkt dann nicht, obwohl er richtig aussieht.

**Regel:** ein Test, der seinen Zielpfad umbiegt, muss auch **jeden Cache**
mitnehmen, den die geprueffte Kette liest — und der Cache gehoert so
umgebogen, dass er den **aktuellen** Pfad befragt, statt einen
stehengebliebenen Zustand zu uebernehmen. Der Nachweis: derselbe Test muss
allein und in der Suite identisch laufen; ein Unterschied ist ein Cache.

Zusaetzlich: die Doppelsperre aus zwei Familien ist bei Tests mit Zielpfad
Pflicht — Schreibmodus aus **und** Pfad umbiegen (siehe oben). Und im `tearDown`
erst loeschen, dann zuruecksetzen: die umgekehrte Reihenfolge laescht die echte
Datei, weil der Pfad dann schon auf den Tempordner zeigt, auf dem die
Originaldatei nachgebildet wurde.

## Wann ein eingefrorener Stand DOCH richtig ist

Wenn die Unveraenderlichkeit selbst der Vertrag ist und es keine formulierbare
Eigenschaft gibt - etwa bei einer Fixture-Datei, deren Inhalt eine gemessene
Realitaet festhaelt (`kerzen_BTC-USDT_1H_8760.json`). Dann gehoert in den Test
eine Zeile, die sagt WARUM eingefroren wird, und wer ihn erneuern darf.

## Gegenprobe beim Umbau

Nach dem Umbau muss der Test den urspruenglichen Fehler noch fangen. Also:
Regel verletzen (z. e. B. `import ereignis` testweise in `melder.py` schreiben),
Test laufen lassen, rot sehen, zuruecknehmen. Ein umgebauter Test, der nichts
mehr faengt, ist ein geloeschter Test mit Zeremonie.

**Die Gegenprobe kann gruen bleiben, obwohl der Test richtig ist — dann prueft
er die Faelle, in denen der alte Code richtig lag.** Das ist der subtilste
Fehler der ganzen Reihe, weil er erst nach der Probe auffaellt und die
Erfolgsmeldung klingt. Gemessen an einer Zielrichtung: der erste Test pruefte
die beiden „normalen“ Faellen einer Liquidationswand, und in beiden lag der
blind uebernommene Rohwert zufaellig richtig — die Gegenprobe blieb gruen. Als
Beleg galt nur, dass der Test existiert; in Wahrheit war er blind gegen genau
den Fall, den der Fix repariert.

**Regel: bei jeder „liegt richtig herum“-Regel die Falle waehlen, in der der
Vorher-Zustand FALSCH war.** Das ist die Richtung, die der Fix repariert, und
damit die einzige, die nur mit ihm ausfaellt. Also **jede Kombination**
kreuzen, nicht die beiden plausibel aussehenden:

```python
# blind - deckt nur ab, was der alte Code schon richtig machte
for d in (wand_ueber_spot, wand_unter_spot): ...

# sichtend - kreuzt Rohwert-Lage x Handelsrichtung
for wandpreis in (unter_spot, ueber_spot):
    for seite in ("long", "short"): ...
```

Ergaenzend, weil beide Nachbarfehler dieselbe Ursache haben: (a) ein Test, der
die Ausgabe REIZT statt die Regel zu pruefen, bleibt gruen, wenn die Funktion
nie aufgerufen wird; (b) ein Test, der nur den neuen Pfad kennt, bleibt gruen,
wenn der alte Pfad daneben bestehen bleibt. Auch diese beiden fallen nur unter
derselben Probe.

**Und eine Medianregel braucht mehrere Ausreifer, um ueberhaupt sichtbar zu
werden.** „Der Median schliesst den heutigen Tag aus“ ist im Einzelfall nicht
unterscheidbar: bei 30 Werten mit EINEM Ausreiser liegen die beiden mittleren
weiterhin auf dem Normalwert. Der Test setzt deshalb **mehr als einen**
abweichenden Tag an und rechnet die Erwartung aus den tatsaechlich gesetzten
Werten — sonst stellt der Test die eigene Annahme in Frage („alle Tage
gleich“) statt den Code zu pruefen, und bleibt gruen, weil die Annahme nach
dem Setzen nicht mehr stimmt.
