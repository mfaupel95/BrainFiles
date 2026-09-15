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
- **Der Sperrtext ist eine Schnittstelle.** `dauerlauf.nur_fenster_fehlt` liest
  die Zeile `Live waere gesperrt durch: …` und stellt nur dann eine
  Freigabe-Anfrage, wenn dort genau EIN Grund steht und dieser „Freigabefenster“
  enthält — kein `;` und kein `:` darin. Text ändern ohne die Leser zu suchen
  heisst: es wird nie gefragt, jedes `/ja` bleibt folgenlos. Vor jeder
  Textänderung nach den Verbrauchern greppen.
- **Diagnose in jedem Modus drucken, den ein Aufrufer parst.** Eine Zeile, die nur
  im `--live`-Zweig fällt, existiert für `--vorschau` nicht — und `--vorschau` ist
  genau das, womit der Dauerlauf die Lage prüft.
- **Gemeldet wird zeilenweise, nicht im Block.** Der Dauerlauf filtert die
  Ausgabe jeder Spur nach Stichwörtern (`verkauf`, `stop`, `KILL`, `gesperrt`)
  und schickt **nur die passende Zeile** nach Telegram. Jede Zeile, die eines
  dieser Wörter enthalten kann, muss Instrument und Seite selbst nennen; eine
  Fortsetzungszeile ohne Subjekt kommt unzuordenbar an. Jede neue Ausgabezeile
  auf Allein-Verständlichkeit prüfen — bei einer kurzen Seite wie `Liq über Stop,
  Ziel darunter` auch, ob sie ohne Richtung (`long`/`short`) wie ein Fehler
  aussieht.
- **Ein Ausstiegsgrund ausserhalb des Stichwortfilters meldet nichts.** Der Filter
  in `dauerlauf.py` kennt nur `verkauf`, `stop`, `KILL`, `gesperrt` — ein Ausstieg
  per **Ziel** oder **Zwangsschluss** ist still, obwohl er im Journal steht;
  „Dauerbeobachtung“ waere nur halb. Jede Ausstiegszeile traegt deshalb ein
  neutrales Filterwort (`AUSSTIEG (<grund>): <richtung> <inst>`), und der Filter
  wird damit erweitert. Die Filterliste steht im laufenden Prozess — die
  Erweiterung wirkt erst nach einem Dauerlauf-Neustart. Nachweis dreiteilig:
  1. **Gerendert, nicht gelesen:** Test sammelt stdout ein, prueft Filterwort +
     Richtung + Instrument.
  2. **Im laufenden System:** einer Papierposition das `ziel` unter den Kurs
     setzen (Zustandsdatei vorher sichern), naechsten Zyklus abwarten, verkaufte
     Zeile im Journal pruefen. Derselbe Zyklus kauft ueblich wieder ein — das Buch
     heilt sich, ein Ziel-Ausstieg setzt keine Abklingzeit.
  3. **Nicht im `dauerlauf.log`:** dort stehen nur Zyklus-Zeilen, Tagesbericht,
     Tracebacks. `melder.sende` schreibt gesendete Nachrichten NIRGENDS hin — wer
     die Meldung dort sucht, haelt einen funktionierenden Fix fuer kaputt. Beleg
     ist die Telegram-Nachricht selbst; Max fragen statt Logzeilen suchen.
  Bis 14.09.2026 druckten xperp, swap, scanner, spiegel weiter
  `ZU <inst> <seite> @ kurs (<grund>)` bzw. `NOT-ZU ...`. Der Filter matcht
  Substring + lower() auf die SPUR-Ausgabe — ein `(stop)`-Grund kam nur durch,
  weil der Grund selbst `stop` enthaelt; `ziel`, `herzschlag_alt`, `LIQUIDATION`
  blieben still (14.09.2026: FIL-Zieltreffer +89,77 USD um 07:50, im Journal, nie
  im Chat). Am 14.09.2026 auf `AUSSTIEG (<grund>): <richtung> <inst> @ kurs`
  gezogen in xperp, swap, scanner, spiegel (dort `[nur Vorschau]`, wenn nicht
  geschrieben wird) und kraken. Bei jeder Pruefung die GEDRUCKTE Zeile greppen
  (`grep -n "ZU \|NOT-ZU\|AUSSTIEG" <spur>/handeln.py`), nicht das Journal lesen
  — Nachweis als stdout-Test (`xperp/test_ausstieg.py`,
  `kraken/tests/test_handeln_papier.py`). Wird aus einer Marke wie `WAERE ZU` ein
  anderes Wort, gehoert der Test mit (`spiegel/tests/test_spiegel.py`,
  `test_vorschau_schreibt_nichts`). Der Fix in der SPUR-Zeile braucht keinen
  Neustart (Zeile kommt je Zyklus frisch aus dem Unterprozess).
- **Zwei Prozesse mit identischer Kommandozeile sind kein Doppellauf.** Ein
  venv-Start erzeugt ein Paar aus Launcher und echtem Interpreter, beide mit
  derselben `CommandLine`. Vor einer Doppellauf-Meldung: jede PID einzeln mit
  Startzeit und Eltern-PID ausgeben, Liste vollständig zeigen. **Die eigene Suche
  findet sich selbst:** `CommandLine -like '*dauerlauf.py*'` listet auch die
  aufrufende Shell — mehrere PIDs, davon null Dauerlaeufe. Gegenmittel:
  Prozessnamen mitpruefen (`Name -like '*python*'`), Treffer nach Eltern-PID und
  Startzeit gruppieren, Zahl gegen `Handel/dauerlauf.pid` halten. Ein Fehlalarm
  kostet mehr Vertrauen als die Prüfung Zeit — und muss, wenn er passiert ist,
  ausdrücklich zurückgenommen werden.
- **Erst nachsehen, wer den Ausstieg speist, bevor eine Marktart als unsicher
  gilt.** `pruefe_ausstiege` rechnet allein aus `zustand.json` und schliesst per
  instId; `okxf.positionen()`/`okxf.offene_orders()` sind FUTURES-fest, haben aber
  keinen einzigen Aufrufer im Handel-, Bus- und Testbaum. „Fuer SWAP gibt es keine
  Stop-Ueberwachung, weil positionen() FUTURES-gefiltert ist“ ist damit falsch.
  Vor jeder solchen Aussage die Aufrufer greppen.
- **Eine Uhrzeit ohne Datum und ohne Zone liest sich als Frist in der
  Vergangenheit.** `spiegel.py` druckte die Frist als `p["frist"][11:16]` — also
  die UTC-Stunde. Kopie PFCHAN am 13.09.2026 13:22 UTC eroeffnet, Frist 24 h
  spaeter; die Zeile sagte `Frist 13:22`, und Max (UTC+2) las eine seit zwei
  Stunden abgelaufene Frist. In einer Spur-Ausgabe gehoeren **Datum, lokale Zeit
  und die Kennzeichnung "lokal"** zusammen (`_lokal()` in spiegel.py, faellt bei
  unlesbarem Wert auf den Rohstring zurueck). Nachweis: Test, der die gedruckte
  Zeile rendert (stdout einsammeln), nicht den Quelltext liest.
- **Drei Uhren in derselben Pruefung: Journal = UTC, Log und Bus = lokal.** Am
  14.09.2026 stand im xperp-Journal `2026-09-14T05:50:04+00:00` — das ist 07:50
  Ortszeit. Wer die Zeile woertlich nimmt, sucht Log und Bus nach 05:50 ab und
  macht daraus einen "Lauf ausserhalb des Takts", der keiner war (der Bus trug
  07:50:03/07:50:09, umhüllt von `routine/xperp-handeln`). `handelsjournal.csv`
  und `zustand.json` schreiben `datetime.now(timezone.utc)`, `dauerlauf.log` und
  `Bus/journal/*.jsonl` Ortszeit. Befund erst, wenn beide Quellen in DERSELBEN
  Zone stehen.
- **Ein Test darf in keinen echten Zielpfad schreiben — auch der richtige Aufruf
  tut es sonst.** Ursache ist NICHT der Aufruf, sondern die Test-Wachen: eine
  Kopie der echten `wachen.json`, die das echte `journal_zweitziel` behaelt. Jeder
  Test, der `lauf("papier")` ruft, laesst den Zyklus seine TEMP-Dateien nach
  `Q:\Handel_Journal\<spur>` spiegeln — gemessen 14.09.2026 bei omniquant
  (Zustand UND Journal) und spiegel (Zustand, 13.816 -> 222 Byte), unter dem
  dokumentierten `discover -s tests`-Aufruf. Tests gruen, Dauerlauf gruen:
  Bedingung 4 war still verletzt, bis jemand die Kopie ausser Haus vergleicht.
  Fix im Setup JEDER Suite, die `lauf()` ruft:
  `w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")` — der
  Spiegelpfad bleibt getestet, trifft aber nichts Echtes; hat die Spur eine
  umgebogene Wachen-Konstante (spiegel: `sp.WACHEN`), wird auch die auf eine
  Temp-Kopie gelegt. Nachweis dreiteilig: (1) alle Suiten laufen lassen,
  (2) `spiegelstand.py` muss "gleich" melden, (3) Gegenprobe mit zurueckgenommenem
  Fix, der Schaden muss wieder auftreten. Wird eine Kopie doch getroffen, ist die
  lokale Fassung die Wahrheit: `cp <spur>/zustand.json <spur>/handelsjournal.csv
  /q/Handel_Journal/<spur>/`, mit `cmp` je Datei byte-gleich belegen. Immer
 `discover -s tests -t tests` aus dem Handelsordner, nie nackt: in einem
 Spurordner ohne `tests/` sammelt `discover` die `test_*.py` IM Spurordner ein,
 und manche davon fahren einen echten Zyklus.
 - **Eine NEUE Ausgabedatei macht BESTEHENDE Suiten zu Schreibern.** Kommt eine
   Modulkonstante mit eigenem Pfad dazu (`ABLEHNUNGEN`, ein zweites Journal, eine
   Merkliste), biegen die vorhandenen Tests sie nicht um — sie wurden geschrieben,
   als es die Datei nicht gab, und kennen nur `JOURNAL`/`ZUSTAND`. Jede Suite, die
   eine der schreibenden Funktionen ruft, legt sie ab jetzt im ECHTEN Spurordner
   an; das Symptom ist eine Datei, die nach `discover` im Spurordner steht,
   obwohl kein Zyklus lief. Zwei Greps, beide noetig: nach der schreibenden
   Funktion (`grep -l "<funktion>" <spur>/tests/*.py`) UND nach den schon
   umgebogenen Konstanten (`grep -n "h\.JOURNAL = \|h\.ZUSTAND = " tests/*.py`) —
   in JEDEM Treffer die neue Konstante im `setUp` auf den Temp-Ordner zeigen
   lassen, im `tearDown` zuruecksetzen. Nicht nur in der neuen Testdatei.
   Nachweis: Suite laufen lassen, dann pruefen dass die echte Datei NICHT
   entstanden ist.
 - **Erscheint die Datei nach einem Lauf, erst den Inhalt fragen, wer sie schrieb.**
   Das Symptom „Datei ist da, obwohl `--vorschau` lief" sieht wie ein kaputter
   Schreibschalter aus und war es hier nicht: die Zeilen stammten aus dem
   vorherigen Testlauf. Die Gruende IN der Datei zeigen den Verursacher — fehlt
   der Zaehler, den nur der echte Zyklus schreibt, war es nicht der Zyklus. Datei
   loeschen, Vorschau allein laufen lassen, erst dann urteilen.
- **Ein Wegwerfskript laedt die Spur ueber den DATEIPFAD, nicht per `import`.**
  `import handeln` holt das erste `handeln.py` aus dem Suchpfad (xperp, scanner,
  swap, gitter liegen im Handelsordner) — die Probe misst eine andere Spur und
  meldet `AttributeError`.
  `importlib.util.spec_from_file_location("<spur>_handeln", <spur>/handeln.py)`
  ist der Weg; die internen Importe der Spur versorgen sich ueber ihren eigenen
  `sys.path`-Block.
- **Eine Stoerung gehoert aus der KENNZAHL, nicht aus der Kapitalkurve.** Ein
  Herzschlag-Zwangsschluss ist keine Handelsentscheidung: er zaehlt in keiner
  Rundenzahl, keiner Trefferquote und keinem Erwartungswert mit - sonst zaehlt
  die Freigabebedingung (50 Runden) Stoerungen statt Strategie. Die EINE Fassung
  des Merkmals steht in `Agenten/Handel/stoerungen.py` (`ist_stoerung`,
  `teile_runden`); Wachen holen sie ueber `basis.teile_runden`, Auswertungen
  per `import stoerungen` - keine zweite Wortliste bauen. Was NICHT gefiltert
  wird: `drawdown()`/Ratsche/Kill-Switch rechnen auf ALLEN Buchungen, eine
  Stoerung ist gebucht und hat Geld bewegt. Die Richtung der Verzerrung ist
  nicht vorhersagbar (kraken: Zwangsschluesse positiv, echte Runden negativ),
  deshalb werden beide Zahlen gezeigt, keine weggelassen. Tests: `Handel/tests/
  test_stoerungen.py` (Merkmale inklusive der Faelle, die NICHT treffen duerfen
  - `stop`, `ziel`, `LIQUIDATION`; alle vier Wachenfassungen; Kurve ungefiltert;
  gedruckte Zeilen gerendert, nicht im Quelltext gelesen).
- **Zahlen im Quelltext sind Behauptungen.** Beispielwerte in einem Docstring
  ("bei xperp -0,74 gegen +38,14 USD") gehoeren nachgerechnet, bevor sie in
  eine Notiz oder einen Bericht wandern - hier trugen sie die Messung nicht.
  Gegenprobe ueber die Runden selbst (`sum(r["gv"])` je Gruppe), nicht ueber
  eine Schaetzung.
- **Plan (Stufe 1) fuer jede angefasste Datei** — `.bak-JJJJMMTT` auch fuer
  `dauerlauf.py`, `tagesbericht.py`, `Bus/handel_befehle.py`. Danach
  `git diff --stat`: eine Zeilenaenderung darf nicht als ganzes Dateidiff
  erscheinen (Zeilenenden erhalten, hier LF). Liegt der Vorher-Stand schon
  committet vor (zweite Aenderung am selben Tag), gilt
  `git show HEAD:<pfad> > <pfad>.bak-JJJJMMTT-<grund>` als Sicherung.
- **Code-Ersetzungen an Dateien mit `\n` im Quelltext:** Muster als RAW-Strings
  schreiben (r'''...'''), sonst interpretiert Python das `\n` im Muster als
  Zeilenumbruch, waehrend die Datei die zwei Zeichen Backslash-n enthaelt — die
  Ersetzung greift ins Leere. Dasselbe fuer JEDEN Backslash: ein normaler String
  macht aus zwei Backslashes einen, ein Raw-String nicht (`'''..\\scanner'''`
  trifft einen Backslash, `r'''..\\scanner'''` deren zwei). Eine Docstring-Zeile
  mit `..\\scanner\\` braucht im Muster einen Raw-String MIT zwei Backslashes —
  und die Zahl liefert nur `repr()` der Rohzeile
  (`open(p, "rb").read().split(b"\n")[i]`), nie der gerenderte Tool-Text, nie die
  geratene Zahl. Solche Muster sind die haeufigste Ursache fuer „Muster nicht
  gefunden“: den Fixer so bauen, dass er bei `text.count(muster) == 0` NICHTS
  schreibt und bei `!= 1` abbricht, und nach zwei Fehlversuchen die Zielzeile
  ausgeben lassen statt weiter zu raten. Der Fixer muss die Zeilenenden des
  Originals erhalten und sie **binaer** feststellen: `raw = open(p, "rb").read()`,
  dann `b"\r\n" in raw`. Textmodus (`open(p, encoding=...)`) normalisiert CRLF
  beim Lesen zu LF, die Pruefung meldet faelschlich LF, der Fixer schreibt LF in
  eine CRLF-Datei — aus einer Zeilenaenderung wird ein Volltext-Diff.
- **Eine Sperre muss auch aufgehen können.** Ein Tor, das nie öffnet, sieht wie
  Sicherheit aus und ist ein Fehler: `references/tor-kalibrierung.md`
- **Zwei Fassungen derselben Sperre, eine Wahrheit.** Neue Spuren nach dem Muster
  einer richtigen Spur bauen, keine dritte Variante erfinden (xperp war
  beim Freigabe-Weg zuerst richtig). Dasselbe fuer die **Gegenrichtung einer
  Bewertung**: aus DERSELBEN Funktion gespiegelt (Komponente fuer Komponente,
  gleiche Gewichte), alte Richtung als Default — vorhandene Aufrufer bleiben
  unveraendert, keine zweite Rechenformel, nur ein zweiter Aufruf.
- **Zustandsdateien vergiften sich.** `zustand.json` wächst bei jedem Lauf;
  sichern statt reparieren.
- **Ein neues Feld je Position bekommt einen Altbestand-Rueckfall, sonst kippt
  das lebende Buch.** Neue Ausstiegsformen (`stop_usd` statt `stop_pct`, ein
  zweites Ziel, ein Trailing-Parameter) muessen in ZWEI Formen im
  Position-Dict koexistieren: das neue Feld wird beim EROEFFNEN mitgeschrieben,
  der Ausstiegspfad prueft es ZUERST (mit `p.get("neu") is not None`); ohne das
  Feld faellt eine ALTE Position auf den alten Zweig zurueck. Ein Rewrite des
  alten Feldes auf allen offenen Positionen ("stop_preis anhand des neuen
  Wertes neu setzen") aendert stillschweigend die Regeln fuer jede Position,
  die vor dem Wechsel gebucht wurde — die Auswertung vergleicht danach zwei
  Buecher unter einem Namen. Nachweis dreiteilig: (1) Test, dass eine Position
  mit nur alten Feldern den alten Zweig nimmt (`stop_preis` reisst, `stop_usd`
  fehlt); (2) Test, dass eine neue Position das neue Feld traegt; (3) im
  wachen.json-Erklaerfeld beide Formen dokumentieren ("stop_pct bleibt als
  Rueckfall fuer Altbestand"). Denselben Regel-Rueckfall in die Auswertung
  ziehen, wenn die Zeile das neue Feld nicht traegt (aus dem `handelsjournal`
  ist es nicht rekonstruierbar) — sonst haengt jede Bilanz vom Migrationsdatum
  ab.
- **Eine Ablehnung darf nicht gleich wieder gefragt werden.** Die Antwortfrist
  (`ANTWORT_FRIST_MINUTEN`, 30 min) bestimmt nur, wie lange eine Anfrage
  offensteht — nicht, wann erneut gefragt wird. Ohne eigene Frist stand hier alle
  30 Minuten dieselbe Frage, auch 15 Minuten nach einem `/nein`.
  `freigabefenster.neue_anfrage_erlaubt()` haelt zwei Wiedervorlage-Fristen: 2 h
  nach unbeantworteter Anfrage, 12 h nach Ablehnung (`/nein`, `/stop`); Grundlage
  sind `anfrage_gestellt` und `zuletzt_geschlossen` der eigenen Zustandsdatei,
  keine zweite Merkdatei. Keine Sperre — scharfgeschaltet wird weiter am
  Bildschirm oder per Antwort auf die naechste Anfrage. Nachweis:
  `tests/test_telegram_freigabe.py`, `WiedervorlageTest` +
  `WiedervorlageImLaufTest` (prueft, dass die Frist im Dauerlauf ankommt).
- **Vor jeder Aenderung an `SPUREN` erst nachsehen, was schon laeuft.** Ein
  Handstart neben dem Dienst ist kein zweiter Lauf derselben Sache: zwei Poller
  an einem Telegram-Token nehmen sich gegenseitig die Nachrichten weg (409), und
  der Handstart laeuft oft mit anderem Interpreter (System-Python statt
  `scanner/.venv`). Alle `python*dauerlauf*`-Prozesse mit Startzeit und
  Eltern-PID auflisten, dann genau einen ueber `Routinen/handel-dauerlauf.ps1`
  starten — der setzt `dauerlauf.pid` und raeumt eine verwaiste Sperre auf.
- **Eine zweite Aufgabe auf derselben Spur ist ein zweiter Schreiber — auch wenn
  sie nur einmal am Tag laeuft.** Am 14.09.2026 stand im xperp-Journal ein
  vollstaendiger Zyklus, den der Dauerlauf nicht kannte (kein Log-Eintrag, im Bus
  nur `routine/xperp-handeln`): die Alt-Aufgabe `MaxHirn-XPERP-Spur2` aus der Zeit
  vor dem Dauerlauf. Ebenso fuhren `marktscanner.ps1` und `kraken-scanner.ps1` je
  einen eigenen `handeln.py --papier`-Aufruf. Ein Zyklus ausserhalb des Takts
  macht jede Zustandsaussage mehrdeutig und ist im Dauerlauf-Log unsichtbar.
  Regel: **je Spur ein Schreiber.** Wer eine Spur in `dauerlauf.SPUREN` fuehrt,
  reduziert ihre Aufgabe auf den Scan (Rangliste) — und haengt an den Wrapper eine
  Sperre, die bei lebendem `Handel/dauerlauf.pid` mit einer Logzeile aussteigt.
  Ist die Aufgabe ganz ueberfluessig, loeschen (`Unregister-ScheduledTask`), nicht
  deaktivieren: Block 9 der Systempruefung meldet JEDE deaktivierte Aufgabe als
  "zu entscheiden".
- **Die Herzschlag-Grenze folgt der Selbstheilungszeit, nicht dem Gefuehl.** Der
  Waechter (`MaxHirn-Handel-Dauerlauf-Waechter`, 30-Minuten-Takt) startet einen
  toten Dauerlauf neu, ein Zyklus dauert 1-2 Minuten — eine Stoerung heilt nach
  spaetestens rund 32 Minuten von selbst. Der Wert ist eine Entscheidungsschwelle,
  kein Abfrageintervall: geprueft wird nur am ANFANG eines Laufs (`letzter_lauf`
  beim Start geschrieben, geprueft vor dem ersten Handel) — 45, 30 und 15 Minuten
  flachen zur SELBEN Minute ab. Kleiner heisst nicht frueher, nur haeufiger ohne
  Anlass; jede Grenze darunter stellt bei JEDER Stoerung flach und bucht eine
  Runde ins Journal, die keine Handelsentscheidung war (11./12.09.2026 mit 30
  Minuten in xperp/swap). Regel seit 14.09.2026: **180 Minuten fuer Papier-Spuren,
  45 Minuten fuer Spuren mit `handel_erlaubt: true`** — bei echtem Geld ist die
  unbewachte Position das groessere Uebel. Sie steht als `_herzschlag_regel` in
  jeder `wachen.json` und gilt fuer ALLE Spuren mit `wachen.json` — auch fuer eine
  ruhende Konfiguration (`orb`: kein `zustand.json`, keine Aufgabe), damit die
  Regel keine stillen Ausnahmen hat. Die Erklaerfelder, die den alten Wert
  begruenden (`_herzschlag_folge` in xperp/swap, `_herzschlag` in kraken), im
  SELBEN Zug korrigieren. Wer eine Spur auf live nimmt, setzt 45, BEVOR
  `handel_erlaubt` auf true geht. Der Wert wirkt ohne Neustart (jeder Zyklus liest
  die Datei frisch).
- **Eine Regel ohne Messung verfaellt.** So entstanden die neun verschiedenen
  Herzschlag-Zahlen (30/45/90/180/2880): jeder Wert war einmal
  begruendet, nachgemessen hat ihn niemand, und die Spur mit
  `handel_erlaubt: true` trug am Ende den lockersten Wert. Jede Regel dieser Art
  bekommt einen Block in `Routinen/systempruefung.ps1` (Muster Block 11b:
  Soll-Wert je Spur aus deren `wachen.json` rechnen, Abweichung als `Entscheiden`,
  sonst EINE `Info`-Zeile "n von m konform") UND einen **Gegentest**: kuenstlich
  falschen Wert setzen, pruefen dass GENAU EIN Punkt erscheint, zuruecksetzen,
  pruefen dass es wieder still ist. Pflicht — ein Pruefer, der nie feuert, sieht
  wie Zustimmung aus, und "0 zu entscheiden" vor und nach dem Einbau beweist
  nichts.
- **Erst die Geometrie rechnen, dann Parameter drehen.** Fuer jede Spur steht vor
  jeder Aenderung die Frage: welche Trefferquote traegt ihre Kosten (Break-even =
  Stop / (Stop + Ziel))? Liegt die gemessene Quote darueber, ist die Geometrie in
  Ordnung und ein Parameterwechsel waere geraten. Geprueft 14.09.2026: xperp/swap
  33 % noetig / 55 % gemessen, scanner 40/64, orbk 40/53, spiegel 29/39 — keine
  Spur negativ.
- **Festes Nominal bei variablem Stop heisst ungleiches Risiko je Platz.** Bindet
  jede Position denselben Betrag, waehrend ihr Stop-Abstand schwankt, riskiert
  die eine ein Vielfaches der anderen bei identisch gebundenem Kapital — wer mehr
  riskiert, belegt denselben Platz wie der, der weniger riskiert. Richtig ist
  festes RISIKO: `nominal = risiko_je_position_usd / (stop_pct / 100)`, gedeckelt
  auf `max_pro_trade_usd`. Vier Regeln dazu, jede einzeln belegbar:
  - **Den Risikobetrag auf den bisherigen DURCHSCHNITT setzen**, nicht hoeher:
    dann bleibt die Risikosumme des Buchs gleich und nur ihre Verteilung aendert
    sich. Ein groesserer Wert ist eine stille Risikoerhoehung, die sich als
    Aufraeumarbeit tarnt.
  - **Der Deckel wird GERECHNET, nicht gegriffen.** Solange
    `max_pro_trade_usd < risiko / (pflicht_stop_prozent_min/100)`, kappt er genau
    die engen Stops: sie behalten ihr altes, zu KLEINES Risiko, waehrend weite
    sauber normiert werden — die Normierung wirkt nur nach unten und ist halb.
    Der richtige Wert ist der Quotient selbst; ab da setzt die Stop-Hausregel die
    Obergrenze und nicht mehr der Deckel. Eine gerundete Zahl daneben („nimm
    130") laesst Luft, die keine Regel deckt.
  - **Der Test haelt die HERLEITUNG fest, nicht den Wert:**
    `assert max_pro_trade_usd >= risiko / (pflicht_stop_prozent_min/100)`, mit der
    noetigen Zahl in der Fehlermeldung. Wer spaeter den Risikobetrag aendert und
    den Deckel vergisst, sieht sofort welchen Wert er braucht. Ein Test auf „120"
    waere ein Change-Detector.
  - **Nach dem Einbau die Spannweite MESSEN**, nicht die Vereinheitlichung
    annehmen: Risiko je Vorschlag ausrechnen und die Spanne zeigen (`min` bis
    `max`). Bleibt sie breit, kappt noch etwas — das ist ein Befund fuer den
    Bericht, kein geloester Punkt. Und die gemessene Spanne gegen die eigene
    frueher genannte Schaetzung halten: war sie zu dramatisch, wird sie im
    Bericht korrigiert, nicht stillschweigend uebernommen.
  Altbestand-Rueckfall wie bei jedem neuen Feld: fehlt `risiko_je_position_usd`
  oder steht es auf null, bleibt es beim festen Nominal; `stop_pct <= 0` gibt den
  Deckel zurueck, sonst entstuende eine unbegrenzte Position. Offene Positionen
  behalten ihr altes Nominal — ein Rewrite waere ein zweites Buch unter einem
  Namen.
- **Ein erhoehtes Limit kann wirkungslos sein — vorher nachrechnen, WELCHES Limit greift.**
  `scanner` hat vier Limits, die sich gegenseitig verdecken: `max_pro_trade_usd`
  (je Position), `max_gesamt_usd` (gebundenes Kapital), `max_offene_positionen`
  (Plaetze) und `risiko_je_position_usd`. Bei risiko-normiertem Sizing ist das
  groesstmoegliche Buch `max_offene_positionen x risiko / pflicht_stop_prozent_min`
  = 6 x 120 = 720 USD. Ein Deckel von 1000 bindet damit NIE und die 280 USD Luft
  decken keine Regel ab — Erhoehung wirkungslos, das Ablehnungsprotokoll zeigt
  weiterhin 'Buch voll'. Vor jeder Limit-Aenderung: die Obergrenze des JEWEILS
  anderen Limits ausrechnen und das Ergebnis nennen, statt die Erhoehung als
  Wirkung zu verbuchen. Latente Nebenwirkungen mitsuchen: die Drawdown-Ratsche
  (`wachen_pruefung.py`, `drawdown_halbierung_prozent/100 * max_gesamt_usd`)
  haengt am Gesamtdeckel und lockert sich mit — von 60 auf 150 USD Ruecklauf.
- **Der Abnahme-Nachweis laeuft am ECHTEN Zyklus, nicht am Testaufruf.** Bei
  laufendem Dauerlauf ist `handeln.py --papier` ein ZWEITER Schreiber neben der
  laufenden Spur. Stattdessen die Laufzeitdateien lesen und gegen die Rechnung
  halten: neue Positionen in `zustand.json`/`handelsjournal.csv` muessen exakt die
  berechneten Werte tragen (SOL-USDC 96.77 bei 6,2 Prozent Stop, ETH-USDT 103.45
  bei 5,8 — beide 6,00 USD Risiko), waehrend ALTBESTAND unangetastet bleibt.
  Offene Positionen werden nie rueckwirkend umgerechnet.
- **Ein Schwellwert aus einer FREMDEN Groesse ist ein latenter Defekt.** Die
  Drawdown-Ratsche rechnete `drawdown_halbierung_prozent/100 * max_gesamt_usd`,
  misst aber den Ruecklauf der realisierten GEWINNKURVE. Als der Kapitaldeckel
  von 400 auf 1000 ging, wanderte die Schwelle von 60 auf 150 USD, waehrend der
  hoechste je erreichte Gewinnstand 140.24 USD war.

  **Das war NICHT 'abgeschaltet' - und wer das behauptet, baut einen Test auf
  eine Regel, die es nicht gibt.** `drawdown()` rechnet `hoch - kum`, und die
  kumulierte Gewinnkurve darf INS MINUS laufen: der Ruecklauf waechst ueber den
  Hoechststand hinaus und ist nach unten nicht begrenzt. Die 150 haetten
  gegriffen, sobald die Spur bei -9.76 USD stand, also erst nach mehr Verlust
  als ihrem gesamten Hoechstgewinn. Erst dann haette die Halbierung keinen
  GEWINN mehr geschuetzt, sondern nur einen Nettoverlust gefangen - dafuer ist
  der Kill-Switch da. Wer 'Schwelle > Hoechststand' prueft, prueft also einen
  echten Mangel, aber die richtige Beschreibung ist 'greift erst nach Verlust
  ueber den Nullpunkt', nicht 'unerreichbar'. Der Unterschied entscheidet, ob
  die Korrektur eine Zahl aendert oder ein ganzes Sicherungskonzept.

  Regel: Sicherungen in ABSOLUTEN Betraegen fuehren (hier
  `drawdown_halbierung_usd`), Prozentsaetze nur als Rueckfallwert; bei jeder
  Nenner-Aenderung nachrechnen, ob die Halbierung noch INNERHALB DES GEWINNS
  greifen kann. Zwei Tests halten das: beide Wege ergeben denselben Betrag, und
  die Schwelle darf den Hoechststand nicht uebersteigen. Die Erreichbarkeit
  haengt NUR am Hoechststand, nie am aktuellen Ruecklauf - sonst meldet die
  Anzeige die Warnung neben 'Faktor 0.50', die sich selbst widerspricht.
- **Eine Sicherung, die man nicht sieht, kann man nicht pruefen.** Die tote
  Ratsche blieb monatelang unbemerkt, weil die Wachen-Anzeige nur Ruecklauf und
  Faktor druckte. Schwellwert, Erreichbarkeit und eine Warnzeile gehoeren in
  dieselbe Ausgabe wie der Rest — und die Anzeige darf beim Nachrechnen nicht
  abstuerzen (alte Zustandsdatei), also `.get()` mit Vorgabe statt `[...]`.
- **Ungepruefte Funktionen sind der Ort, an dem solche Defekte ueberleben.**
  `groessenfaktor()` hatte null Tests, obwohl es Bedingung 2 durchsetzt. Beim
  Anfassen einer Hausregel zuerst pruefen, ob sie ueberhaupt getestet ist
  (`grep -ln "<funktionsname>" tests/*.py`) — und bei einem Schwellwerttest den
  echten Journalpfad lesen, nicht eine Attrappe, sonst bleibt der Befund stumm.
- **Erst der Import-Kette folgen, dann "kein Code liest das" behaupten.** `swap`
  sah wie tote Konfiguration aus, weil in `swap/*.py` kein `drawdown`-Wort
  vorkam - die Spur erbt die Wachen aber ueber `import wachen_xperp`. Ein
  `grep ... | head -20` hatte die Fundstelle zusaetzlich abgeschnitten. Zwei
  getrennte Fehler, dieselbe falsche Aussage im Commit. Vor dem Urteil die
  Imports der Datei ansehen und ohne `head` zaehlen.
- **Ein Schwellwert aus einer FREMDEN Groesse ist ein latenter Defekt.** Die
  Drawdown-Ratsche mass den Ruecklauf der Gewinnkurve, war aber als Prozentsatz
  des Kapitaldeckels formuliert. Wer `max_gesamt_usd` anhebt, verschiebt lautlos
  eine Schutzschwelle. Die richtige Skala ist das BUCHRISIKO (Risiko je Position
  x Hoechstzahl Positionen): sie waechst mit Positionszahl und Positionsrisiko,
  der Kapitaldeckel kommt darin nicht vor. Eine Schutzschwelle gehoert als
  BETRAG in die Konfiguration, nicht als Quote.
- **"Unerreichbar" ist bei einem Drawdown-Schwellwert das falsche Wort.**
  `drawdown()` rechnet `hoch - kum`, und die kumulierte Kurve darf ins Minus
  laufen - der Ruecklauf waechst also ueber den Hoechststand hinaus. Eine
  Schwelle ueber dem Hoechststand ist NICHT unerreichbar; sie greift nur erst,
  nachdem die Spur mehr verloren hat als sie je gewonnen hatte, und schuetzt
  dann keinen Gewinn mehr, sondern faengt einen Nettoverlust - dafuer ist der
  Kill-Switch da. Vor solchen Aussagen die Rechnung zeigen (hier: Schwelle 150
  haette bei einem Stand von -9.76 USD gegriffen).
- **Eine geteilte Umsetzung ueber den PFAD laden, nicht ueber `sys.path`.**
  Spuren starten mit ihrem eigenen Ordner als `sys.path[0]`; ein Eintrag auf
  `Handel/` koennte gleichnamige Spurenmodule verdecken (`gitter/` hat ein
  eigenes `grid.py`, daneben liegt `Handel/grid.py`). `spec_from_file_location`
  umgeht das. Und: erst die eigene `wachen.json` lesen, dann weitergeben -
  `lage({}, ...)` wirft `KeyError`, eine leere Konfiguration ist keine gueltige.
- **Ein neuer Konfigurationsschluessel wirkt erst, wenn die ABLEITUNG ihn kennt.**
  Soll ein Wert aus dem Buchrisiko hergeleitet werden statt hingeschrieben,
  reicht es nicht, die fehlende Zahl in die `wachen.json` zu setzen: die
  Herleitung liest ein festes PAAR von Schluesseln in einer eigenen Tabelle
  (`ratschen.BUCHRISIKO_PAARE`). Ohne den Eintrag meldet `pruefe_ratschen.py`
  weiter „nicht herleitbar" — der Schluessel steht da und niemand liest ihn.
  Nachweis ist der Lauf des Pruefskripts („1.0x ja"), nicht das gesetzte Feld.
- **Eine Schutzschwelle nimmt den HOECHSTEN Fall, nicht den Mittelwert.**
  Bei festem Nominal und variablem Stop ist das Risiko je Position keine
  einzelne Zahl, sondern eine Spanne — der Deckel auf den Stop bestimmt den
  oberen Rand. Ein Mittelwert liesse die Schutzschwelle spaeter ausloesen; eine
  Ratsche soll im Zweifel frueher greifen. Den oberen Rand aus den GENANNTEN
  Zahlen rechnen und die Rechnung in den Kommentar schreiben.
- **Eine STRUKTURELLE Grenze ist ein Beleg, keine erfundene Zahl — und der
  Kommentar muss sagen, wer sie liest.** Fuehrt eine Spur nur EINEN Platz
  (`z["position"]` als Dict, `z.pop("position")` statt einer Liste), ist
  `max_offene_positionen: 1` die Beschreibung dieser Bauart; der Wert dient der
  Herleitung und wird von der Handelslogik NICHT gelesen. Genau das ins
  Erklaerfeld schreiben, sonst liest sich der Schluessel wie eine durchgesetzte
  Grenze, die es nicht gibt — und wer sie spaeter auf 2 stellt, aendert nichts.
- **Fehlt eine Schwelle, darf nichts erfunden werden** - aber sie darf auch
  nichts drosseln. Ohne konfigurierte Ratsche `halbierungsschwelle() -> None`
  und `groessenfaktor` 1.0, sichtbar gemeldet. Eine stillschweigende
  Ersatzschwelle sieht aus wie Schutz und ist keiner.
- **Die Zahlen aller Spuren ohne eigene `auswertung.py` liefert
  `Agenten/Handel/auswertung_alle.py`** (aus dem Handel-Ordner starten). Paart
  Einstieg und Ausstieg je Instrument, rechnet mit den Kosten aus der Zeile, nicht
  mit einer Schaetzung. Unter 8 Runden ist das ein Befund, keine Messung —
  dieselbe Schwelle wie `buchauswertung.MIN_AUSSTIEGE`.
- **Zwangsschluesse sind keine Runden.** Ein Ausstieg mit `herzschlag` im Grund
  ist die Folge eines Ausfalls (der Waechter stellt flach, weil der Dauerlauf zu
  lange stand), keine Handelsentscheidung — er steht trotzdem im Journal und
  wurde von jeder Zaehlung als Runde mitgezaehlt. `Handel/stoerungen.py`
  (`ist_stoerung()`) trennt beides; `auswertung_alle.kennzahlen` rechnet auf den
  echten Runden und weist die Zwangsschluesse darunter separat aus
  (`n_stoerung`, `stoerung_ergebnis`, `runden_gesamt`). Vorher/nachher:
  xperp 23 -> 11 echte Runden, kraken 10 -> 2, swap 5 -> 4; 21 Zwangsschluesse
  insgesamt, alle in EINEM Vorfallsfenster — die Haeufung nach Tag ist die
  Fehlersuche.
  - **Nicht einfach wegwerfen: die Richtung der Verzerrung ist nicht
    vorhersagbar.** Bei kraken waren die Zwangsschluesse mit +4,59 EUR POSITIV,
    waehrend die zwei echten Runden -4,50 EUR verloren — sie haben das Bild dort
    geschoent, bei xperp getruebt (-0,74 gegen +38,14 USD). Beides ausweisen,
    keines weglassen; sonst haengt die Bilanz davon ab, welchen Vorfall es gab.
  - Aktionen je Spur: Ausstieg `schliessen`/`verkauf`/`AUSSTIEG`, Einstieg
    `eroeffnen`/`kauf`/`KAUF`/`EINSTIEG`, kein Handel `funding`/`rollover`/
    `zyklus`/`quotes`; orbk hat keine `aktion`-Spalte (nutzt `ausgang`). Wer die
    Zeilen als Runden gegen `papierlauf_min_runden` zaehlt, misst Stoerungen
    statt Strategie.
- **Ein Backtest, der die Spur nachbaut, optimiert die Nachbildung.** Bei einer
  Parameter-Optimierung die ECHTE Logik fahren: `gitter/backtest_gitter.py` laedt
  `gitter/handeln.py` ueber `spec_from_file_location` und ruft dessen
  `leiter_bauen()`, `arme()` und `walk()` auf historischen Kerzen — aufgebaut wie
  `gitter/tests/test_gitter.py`, das dieselbe Zustandsstruktur vorlegt. Der
  Filter-Haken sitzt auf dem Modulglobal (`h.arme`), das `walk()` ohnehin aufruft,
  also genau an der Stelle, an der eine echte Spur ihre Stufen belegt. Eine zweite
  Umsetzung daneben ist eine zweite Wahrheit: gemessen wird dann die Nachbildung.
- **Erst trennen (suchen/pruefen), dann urteilen — sonst ist der Befund
  Auswendiglernen.** Parameter auf EINEM Fenster suchen, auf einem Fenster DANACH
  pruefen, ohne Ueberlappung; nur was auf beiden haelt, ist eine Verbesserung.
  Acht Wochen sind EIN Marktzustand. Bei gealterter lokaler Reihe: Suchfenster
  aus der Datei, Prueffenster live — und die Ueberlappung explizit nachrechnen.
- **Spannt der ganze Parameterraum fast nichts, ist der Parameter nicht der
  Hebel.** 42 Kombinationen aus Spanne und Stufenzahl lagen zwischen +0,17 % und
  +2,23 %; dann gehoert nicht weiter gedreht, sondern gemessen, wovon das Ergebnis
  abhaengt (hier Korrelation Markt/Gitter +0,78 ueber 12 Fenster: das Gitter folgt
  der Marktrichtung, gewinnt in fallenden Fenstern, verliert in starken) und der
  Marktzustand als Filter geprueft. Ein Filter, der auf dem Suchfenster gewinnt
  und ungesehen schlechter ist als gar keiner, wird NICHT eingebaut. "Optimiere
  bis positiv" laesst sich dann nicht ehrlich liefern — das gehoert gesagt, statt
  so lange zu drehen, bis ein Fenster positiv ist; die bleibende Einschraenkung
  (Mittel ueber alle Fenster weiter negativ) gehoert in den Bericht.
- **Ein Befund eines Subagenten ist ein Hinweis, keine Tatsache.** Gemeldet war,
  `max_gesamt_risiko_usd` binde nichts — tatsaechlich wird der Wert als
  Kill-Switch gelesen UND `verluste_usd` daneben erhoeht. Vor jeder Uebernahme die
  konkrete Behauptung greppen (Symbol im Leser, Schreibpfad daneben) und das
  Ergebnis im Bericht richtigstellen. Die Kartierung bleibt nutzbar, die
  widerlegte Stelle nicht.
- **Vor jeder Deutung eines Journals pruefen, ob die Runden aus eigenen
  Testlaeufen stammen.** 14.09.2026: von 9 Kraken-Ausstiegen waren 4 vom Testlauf
  am 12.09. und 4 vom Verifikationslauf am 14.09. (16:44) — das Buch sah nach
  "8 von 9 Herzschlag-Ausstiegen" aus und war fast leer. Datum und Grund gegen die
  eigene Sitzung halten, bevor eine Strategie bewertet wird.
- **Testfallen in den Spuren:** `omniquant/gui.py` legt beim Import den
  scanner-Ordner auf `sys.path` (fuer okx/wachen_pruefung). Bei Einzelaufruf
  (`python tests/test_gui_bindung.py`) zieht `import handeln` scanner/handeln.py
  statt der eigenen Datei — der Test prueft still die falsche Spur, unter
  `-m unittest discover` faellt es nicht auf. Herkunft des Moduls pruefen
  (`h.__file__`).
- **Ein Papier-Umfang darf groesser sein als das Muster - das ist kein
  Verstoss.** `spiegel.py` haelt `PAPIER_UMFANG`
  (`max_offen` -> `max_offen_papier`, `kill_switch_gesamt_usd` ->
  `..._papier`) und `_umfang(w, modus)`; solange die Spur Papier ist, gilt der
  groessere Wert (60 Plaetze), live gilt das Muster (20). 60 offene Positionen
  bei `max_offen: 20` sind also gewollt: das Papierbuch sammelt Runden, ohne
  eine Bedingung zu aendern. Vor jedem Befund "Deckel haelt nicht"
  `_umfang()`/`PAPIER_UMFANG` in der Spur lesen.
- **Anbinden heisst: JEDE Liste, die eine Spur nennt, mitziehen.** Bei kraken
  (15.09.2026) fehlte nach dem Eintrag in `dauerlauf.SPUREN` die Zeile in
  `Bus/handel_befehle.SPUREN` - die Spur lief, war aber in `/status` nicht
  sichtbar. Ebenso hat die Handelszentrale eine eigene Kursquellen-Liste
  (`QUELLE`): eine Feed-Spur (spiegel, kopier, kopier1zu1) ohne Eintrag wird
  als `okx` gelesen und der Chart laeuft mit der Token-Adresse als Instrument
  ins Leere. Die Nulllinie ist der Matrix-Audit: dauerlauf.SPUREN x Bus.SPUREN x
  tagesbericht (`spur_*` UND das Tupel in `baue()`) x `spiegelstand.ZUSATZ` x
  `QUELLE` x `ereignis.lauf` - die Differenz ist der Auftrag.
- **Backtest-Urteile: der Sammler ist `Handel/backtest_urteile.py`, die Felder
  gehoeren in die `freigabe`.** Drei Spuren haben einen eigenen Motor (gitter,
  orbk, nautilus); der Sammler faehrt ihn mit den WERTEN DER SPUR und schreibt
  NUR `backtest_bestanden`, `backtest_urteil`, `backtest_geprueft_am` in die
  `wachen.json` - `handel_erlaubt` und `freigabe.erfuellt` bleiben unberuehrt,
  und bei einem Motorausfall bleibt der alte Wert stehen. Massstab: Gitter =
  besser als Buy-and-Hold (so steht es im Motor selbst), ORB = mindestens ein
  Instrument mit eigenem `URTEIL: Ja` ("unter 10 Verlierer" heisst zu wenig
  Daten, nicht schlechte Strategie). Der Wochenlauf
  (`Routinen/handel-wachen.ps1`) ruft ihn nach den beiden `--wachen`-Laeufen auf.
  Zwei Fallen: (1) Beim Gitter gilt die im Zustand gesetzte Leiter - weicht der
  Wert in der `wachen.json` ab, rechnet ein Backtest mit ihr eine ANDERE
  Strategie (Befund 15.09.2026: wachen 6 Stufen, laufende Leiter 12). Der Motor
  braucht `--stufen`/`--spanne-prozent`, sonst bewertet er die Vorgaben des
  Skripts. (2) Eine Spur mit eigenem Git-Repo (nautilus) bekommt ihre Aenderung
  dort committet - auch ein Aenderungs-Skript, das die wachen.json anfasst.
- **Vier Indikator-Spuren sind seit dem 15.09.2026 angeschlossen** (`macd_mtf`,
  `squeeze`, `supertrend`, `wavetrend`; angelegt am selben Tag, Commit
  `a3932f1`). Sie haengen an allen fuenf Stellen: `dauerlauf.SPUREN`,
  `Bus/handel_befehle.SPUREN`, je `tagesbericht.spur_*` **und** das Tupel in
  `baue()` (eine gemeinsame `_spur_indikator()`-Funktion fuer alle vier),
  `ereignis.lauf("handel/<spur>")` in jeder `handeln.py` (Wrapper um `main()`;
  die Tests rufen `lauf()`, nicht `main()` - die Bus-Meldung stoert sie nicht)
  und die Spiegelung. Vier Dinge, die beim Anschliessen wirklich weh taten:
  1. **Die Zielordner auf Q: muessen existieren** (`mkdir -p
     Q:/Handel_Journal/<spur>`), sonst ist die Kopie still kaputt.
  2. **`spiegeln()` braucht den Nachzug nach dem Vermerk** (`if vermerke_spiegelung(
     ...) and ok: spiegele_journal([ZUSTAND], ziel)`) - ohne ihn meldet
     `spiegelstand.py` in jedem Zyklus "ABWEICHUNG", weil der Vermerk juenger ist
     als die Kopie (die vier hatten die kurze Fassung).
  3. **Journal-Spaltentoleranz im geteilten Leser:** `wachen_pruefung.
     runden_aus_journal()` las nur `usd`; die Indikator-Spuren schreiben
     `einsatz_usd` -> `KeyError: 'usd'`. Der Fehler zeigt sich erst im ZWEITEN
     Zyklus (der erste hat noch keine Runde). Jetzt liest der Leser beide
     Spalten - additiv, die alten Spuren bleiben unveraendert.
  4. **Warteschlangen-Probe vor dem Neustart** (`dauerlauf_neustart_probe.py`:
     0 ungelesen, keine offene Freigabe), danach muss der erste Zyklus JEDE Spur
     als "(papier) ok" listen (hier 15; gut 2,5 min) - fehlt eine, lief noch der
     alte Code.
- **Der richtige Testaufruf steht im Testkopf, nicht in der Gewohnheit.**
  `grep` ueber die Testausgabe verschluckt sich an CRLF: die Zusammenfassung
  kommt als `Ran N tests\r`, ein `grep -E "^(Ran|OK)"` in einer Schleife liefert
  dann scheinbar nichts, obwohl die Suite gruen ist. Immer den Exit-Code
  mitnehmen (`echo $?`) statt nur die Zeilen zu filtern.
  `discover` aus dem SPURORDNER zieht je nach Spur ein fremdes `handeln`
  (Symptom: `AttributeError: module 'handeln' has no attribute 'pruefe_einstieg'.
  Did you mean: 'pruefe_einstiege'?` - dann lief der Test gegen eine andere
  Spur) oder bricht mit `Start directory is not importable: 'tests'` ab. Beides
  ist kein Befund, sondern der falsche Aufruf. Bewaehrt: aus dem Spurordner
  `<venv>/python -m unittest discover -s tests -t . -p "test_*.py"` (orbk: 54
  Tests), bei den Indikator-Spuren `cd <spur>/tests && python -m unittest
  test_<spur>`, bei nautilus `test_grid.py` mit dem nautilus-eigenen venv. Vor
  jeder Meldung "Tests rot" den Aufruf aus dem Testkopf der Datei nehmen.
- **Vier Indikator-Spuren liegen gebaut, aber unangeschlossen** (15.09.2026,
  Commit `a3932f1`): `macd_mtf`, `squeeze`, `supertrend`, `wavetrend` - je
  `handeln.py` + `wachen.json` (BTC/ETH/SOL-USDT, `handel_erlaubt: false`), Tests
  mit dem dokumentierten Aufruf gruen, aber NICHT in `dauerlauf.SPUREN`, nicht in
  `Bus/handel_befehle.SPUREN`, ohne `tagesbericht.spur_*`, ohne
  `ereignis.lauf("handel/<spur>")` und ohne Spiegelaufruf. Sie laufen auch nicht
  "schon mal so": ohne Zustandsdatei haben sie nie gehandelt. Anschliessen heisst
  alle fuenf Stellen (Anbindungs-Audit) plus Dauerlauf-Neustart mit
  Warteschlangen-Probe - und vorher klaeren, ob sie in den Takt sollen, statt es
  nebenbei mitzunehmen.
- **Keine absoluten Benutzerpfade in Skripten** - auch nicht in einem
  Wegwerfskript, das "nur mal schnell" wo liegt. `Agenten/Hermes/scripts/
  spiegel_fremdcommit.py` trug `C:\\Users\\faupe\\Documents\\BrainFiles` und
  wurde von der Systempruefung (Block 5, Portabilitaet) als offener Punkt
  gemeldet. Richtig: die Wurzel aus der Lage der Datei ableiten
  (`Path(__file__).resolve().parents[3]`) oder als Argument nehmen.
- **Nur `dauerlauf.py` selbst braucht einen Neustart.** Jede Spur laeuft als
  Unterprozess (`subprocess.run([PYTHON, SPUREN[spur].get("skript",
  "handeln.py"), modus])`) — eine Aenderung an `handeln.py`, `wachen.json` oder
  einem Spurmodul greift schon im naechsten Zyklus. Die Wirkung NICHT schlafend im
  Vordergrund abwarten (Timeout!): als Hintergrund-Skript starten (`terminal` mit
  `background=true, notify=true`, sleep-bis-Zeit, Beweis-Dump aus
  zustand.json/Ablehnungslog/Journal). Was im laufenden Prozess steht (`SPUREN`,
  `pruefe_anfragen`, die Aufrufe von `tagesbericht`), wirkt erst nach Neustart —
  und der Lauf schickt danach sofort einen Tagesbericht, weil sein Merker leer ist
  (12.09.2026: zwei Berichte an einem Abend).
  - Neustart: laufendes Paar beenden (ALLE PIDs der venv-Kette),
    `dauerlauf.pid`-Sperre entfernen (der Wrapper raeumt nur eine VERWAISTE Sperre
    auf — lebt der eingetragene Prozess, meldet er „laeuft bereits" und tut
    nichts), dann einmal `Routinen/handel-dauerlauf.ps1` starten.
  - Belegen am `dauerlauf.log`: der erste Zyklus muss JEDE Spur als „(papier) ok"
    listen — fehlt die neue Spur, lief noch der alte Code.
  - **Vorher die Warteschlange PEEK-en, nicht raten:** `start()` ruft
    `melder.leeren()` und wirft alles Ungelesene weg (ein `/ja` von gestern ist
    keine Freigabe fuer heute). `melder.hole(seit=None, warten=0)` liest OHNE
    offset und damit ohne Ack — Telegram behaelt die Nachrichten, bis ein offset
    sie bestaetigt. Zeigt die Probe 0 ungelesene und ist fuer alle Spuren
    `freigabefenster.lade(s).anfrage_offen()` False, ist der Neustart verlustfrei;
    sonst erst Max die wartende Nachricht beantworten lassen.
  - Beides in einem Wegwerfskript unter `Agenten/Hermes/cache/`
    (`dauerlauf_neustart_probe.py`), das auch die SPUREN-Schluessel aus dem Code
    liest und die `journal_zweitziel` jeder Spur zeigt. Danach zweimal
    `spiegelstand.py` (vor und nach dem Neustart) — byte-gleich.
- **Tests dürfen keinen Konfigurationswert behaupten.** Ein Test, der auf den
  heutigen Inhalt von `wachen.json` baut (z. B. „Kraken ist stillgelegt“), bricht,
  sobald Max den Schalter umlegt — und wird dann abgeschwächt statt ernst
  genommen. Die echte Datei als **Form** nehmen (Felder vorhanden, Typ stimmt),
  die Behauptung über eine Kopie mit ausdrücklich gesetzten Werten führen: die
  Mechanik prüfen, nicht den Stand. Eine WERTaenderung genauso — in-process, nie
  am lebenden Buch: die Einstiegsfunktion mit der geladenen Wachen-Kopie und einem
  Temp-Journal aufrufen (`pruefe_einstiege(z, [vorschlag], w, False)` mit
  `menge_fuer` und `letzter_kurs` als Lambda) und die ZEILE pruefen, die entsteht
  (Kaufzeile 50.00 bei Satz 0, 50.20 bei 0,004). Der Test prueft beide Werte:
  faellt der Satz zurueck, bleibt er gruen und zeigt die alte Rechnung. Eine echte
  Order oder eine erfundene Position ist kein Nachweis, sondern ein Eingriff ins
  Buch. Dasselbe fuer erwartete GEDRUCKTE Zeilen: ein
  `assertIn("... aelter als 12 h", ...)` bricht beim naechsten Wertwechsel — die
  erwartete Zeile aus demselben Wert formatieren, den der Lauf liest (z. B.
  `json.load(io.open(sp.WACHEN))["verfolgte_max_alter_stunden"]`).
- **`.env`, `Wissen/Zugaenge.md`, `proxy.yaml` sind tabu** — nie lesen, ausgeben,
  protokollieren.
- **Ein Buch, das nur Buchungen protokolliert, kann "Tor" und "voller Platz" nicht
  unterscheiden.** Das Journal sagt nur, WAS gebucht wurde — nicht, wie viele
  Kandidaten an welchem Tor haengen blieben; volles Buch und zu strenges Tor sehen
  identisch aus ("keine neue Kopie"). Jede Spur mit Kandidatenstrom schreibt ein
  **Ablehnungsprotokoll daneben** — eigene Datei, NIE ins Journal: dessen Leser
  zaehlen Zeilen als Buchungen (`bilanz()` rechnet jede Nicht-eroeffnen-Zeile als
  Runde, `buchauswertung` je Aktion), eine Ablehnung waere eine erfundene Runde.
  - Schema (spiegel/ablehnungen.csv): je Zyklus eine Zeile pro Grund mit `anzahl`
    (Lage ueber ALLE Signale, billige Tore ohne Abruf) plus die Entscheidungen der
    bewerteten Kandidaten; Einzelkandidaten mit Kennung NUR fuer die, die bis zur
    teuren Pruefung kamen — 700 Signale je Zyklus einzeln liest niemand.
  - Sperre je (Transaktion, Grund): dasselbe Signal steht Stunden im Feed, sonst
    zaehlt man es alle 15 Minuten erneut.
  - Zaehlung aus DERSELBEN Funktion wie das Tor (`_vorpruefung`), sonst zwei
    Fassungen einer Grenze; ein Test belegt, dass ein billiges Tor keinen Abruf
    kostet.
  - **Jedes Signal in GENAU EINEN Lage-Zaehler** — erst Zugehoerigkeit (Wallet
    verfolgt?), dann die billigen Tore; sonst stehen dieselben Kandidaten in zwei
    Zaehlern und die Kontrollzeile geht nicht auf.
  - Kontrollzeile (`kaufbar = bewertet + nicht mehr erreicht`) gehoert in den
    Leser, samt "Achtung"-Zeile bei Schieflage: die Kapazitaets-Zaehler (Buch
    voll, Zyklusdeckel) zaehlen EREIGNISSE je Zyklus, nicht Kandidaten, und
    gehoeren nicht in die Kandidatensumme.
  - **Ein Kapazitaets-Zaehler im SCHLEIFENRUMPF feuert je Kandidat, nicht je
    Zyklus.** Der Abbruch (`break` bei vollem Buch) zaehlt von selbst einmal —
    ein `continue`-Zweig dagegen (Gesamtdeckel erreicht) laeuft fuer JEDEN
    verbleibenden Kandidaten durch und schrieb 18 Zeilen, wo ein einziger
    ausgeschoepfter Einsatz gemeint war; die Lage liest sich dann wie 18
    verschiedene Ablehnungen. Solche Zweige mit einem Merker je Lauf deckeln
    (`if not deckel_gemeldet: protokolliere(...); deckel_gemeldet = True`).
    Erkennbar am ECHTEN Zyklus, nicht am Test: die Zahl muss gegen die Zahl der
    Zyklen stehen, nicht gegen die der Kandidaten.
  - **Die Frage, die das Protokoll beantwortet, ist die Durchsatzfrage — und die
    Antwort widerlegt oft die Vermutung.** Erster echter Lauf des scanner-Buchs:
    39 bewertete Maerkte, 21 am Score gescheitert, 18 kaufbar — und ALLE 18 am
    Gesamtdeckel, bei vollem Kapital und nur 4 von 6 Plaetzen belegt. Das Tor war
    nicht zu streng, das Geld war alle. Wer vorher an den Toren gedreht haette,
    haette eine andere Strategie gemessen und den Engpass nicht angefasst.
  - Die Datei gehoert in die Spiegelung (Bedingung 4) UND als **ZUSATZ-Map je
    Spur** in `spiegelstand.ZUSATZ` — nicht in die globale `DATEIEN`-Liste, sonst
    melden alle anderen Spuren eine Abweichung. Vorschau schreibt nichts.
  - **Der erste echte Zyklus gehoert zum Nachweis:** mit synthetischen Signalen
    war die Zaehlung gruen, die Schieflage zeigte erst der Lauf mit echten
    Feed-Zahlen — Kontrollzeile und byte-genauen Vergleich gegen Q: von Hand lesen.
  - Vorbild `spiegel/spiegel.py --ablehnungen`, Tests
    `spiegel/tests/test_ablehnungen.py`, Rezept
    `references/fremdfeed-papierbuch.md`, Abschnitt "Tore vor jeder Buchzeile".
- **Ein volles Buch ist ein Durchsatz-Problem, kein Tor-Problem — und der Umfang
  gehoert getrennt fuer Papier und live.** Der Zyklus bricht beim ersten
  Platzmangel ab (`if len(z["positionen"]) >= w["max_offen"]: break`); alles
  danach zaehlt als "kaufbar, aber nicht mehr erreicht" — liest sich wie ein zu
  strenges Tor, ist aber Kapazitaet: **Runden je Tag = Plaetze x Umschlaege je
  Platz und Tag** (14.09.2026 bei spiegel: 20 Plaetze, 30-55 geschlossene
  Runden/Tag). Wer Daten sammeln will, hebt die KAPAZITAET, nicht die Tore — sonst
  misst er eine andere Strategie. Richtig: zwei Wertepaare in `wachen.json`
  (`max_offen` / `max_offen_papier`) und eine Funktion, die den Umfang anwendet
  (`spiegel._umfang`), **gekoppelt an den Schalter, der die Spur auf Geld stellt**
  (`handel_erlaubt: true` oder `--live`). Die Notbremse im SELBEN Anteil mitziehen
  (10 % des Nominalwerts), sonst stellt sie das Papierbuch selbst flach. Und die
  neue Zeile darf **kein Filterwort** tragen: "Kill-Switch" faellt unter `kill`
  und ginge jeden Zyklus nach Telegram (im Druck heisst es "Notbremse").
- **Ein Signal-Feed ist ein FENSTER, kein Stammbuch: die Wallet-Liste altert in
  Stunden.** Wallets, die vor zwei Tagen handelten, handeln heute oft nicht mehr —
  und die Wallet, die JETZT handelt, steht nicht in der Liste. Gemessen bei
  spiegel am 14.09.2026: Liste vom 12.09. mit 305 Wallets, im Feed handelten 206
  Wallets, davon **154 nicht in der Liste** — 472 von 706 Signalen je Zyklus
  fielen als "Wallet nicht verfolgt" aus, zwei Drittel des Feeds; im Journal
  unsichtbar. Fix: der Zyklus baut die Liste SELBST neu, sobald ihr Stand aelter
  ist als `verfolgte_max_alter_stunden` in `wachen.json` — **nur im schreibenden
  Lauf**: die Aufbau-Funktion (`waehlen`) schreibt die Datei direkt und kennt den
  modulweiten Schreibschalter NICHT, in der Vorschau ausdruecklich aussperren
  (Test: Liste unveraendert nach `lauf("vorschau")`). Nebenwirkung: jede Suite,
  die `lauf("papier")` ruft, holt den ECHTEN Feed in den Testlauf — `waehlen` im
  `setUp` stilllegen, sonst haengt sie am Netz.
- **Ein Test, der eine Grenze aus der Datei liest, misst nach einer
  Umfangs-Aenderung an der falschen Stelle.** Befund beim Einbau: `max_offen`
  stand auf 60 (Papier), der Test fuellte das Buch nach `self.w["max_offen"]` = 20
  und traf damit nie die Abbruchstelle — gruen, aber blind. Die Grenze aus
  DERSELBEN Funktion holen, die der Lauf benutzt (`sp._umfang(self.w,
  "papier")["max_offen"]`).
- **Ein modulweiter Schreibschalter leckt zwischen Testdateien.**
  `spiegel.SCHREIBEN` steht nach `lauf("vorschau")` auf False; eine danach
  gelaufene Testdatei, die `eroeffne()`/`journal()` direkt aufruft, schreibt still
  nichts (Symptom: "Journal hat 0 Zeilen", obwohl der Code stimmt — nur die
  Reihenfolge der Dateien entscheidet). In `setUp` den Wert merken und auf True
  stellen, in `tearDown` zuruecksetzen. Und die `wachen.json` im Test auf einen
  Temp-Ordner umbiegen (inkl. `journal_zweitziel`): sonst ueberschreibt jeder
  Papier-Testlauf die Kopie ausser Haus mit seinem Temp-Zustand — die Tests laufen
  gruen und Q: ist danach leer bzw. falsch.
- **Eine neue Spur muss in die Meldungen, sonst meldet sie niemand.** Fuenf
  Stellen, alle fuenf noetig:
  1. `dauerlauf.SPUREN` (mit `"skript"`, wenn die Einstiegsdatei nicht
     `handeln.py` heisst — sonst startet der Lauf `handeln.py` im Spurordner, und
     `<spur> Rueckgabe 2` heisst nichts anderes als „Datei nicht gefunden“).
  2. `Bus/handel_befehle.SPUREN` (fuer `/status`).
  3. `tagesbericht.spur_<name>()`. 4. Eintrag im Tupel in `baue()`.
  5. **Bus-Anbindung im Skript selbst**: Hauptlauf in
     `with ereignis.lauf("handel/<spur>")`, `main()` als Wrapper um den bisherigen
     Body, Bus-Ordner auf `sys.path` (Vorbild `xperp/handeln.py`). Ohne sie steht
     im Journal kein Start/Ende, „hat die Spur gelaufen?" ist unbeantwortbar.
  Nachweis je Spur: `--vorschau`-Lauf und
  `grep '"wer": "handel/<spur>"' Agenten/Bus/journal/<JJJJ-MM-TT>.jsonl` — dort
  muessen `start` und `ende` mit `code: 0` stehen.
  Sechste Stelle: **Kopie ausser Haus (Bedingung 4)**. `journal_zweitziel` in
  `wachen.json` spiegelt nichts — kopiert wird nur, wo ein Zyklus
  `spiegele_journal` aufruft (`wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)`).
  Beim Anbinden BEIDES setzen, Ziel UND Aufruf — in ALLEN Zyklenpfaden, auch im
  Notausstieg (Kill-Switch, alter Herzschlag). Seit 13.09.2026 spiegeln alle
  Spuren; Ziele je Spur in `Q:\Handel_Journal\<spur>` (scanner direkt in der
  Wurzel). Den Vermerk `journal_zweitziel_ok` schreiben seit 14.09.2026 ALLE
  Spuren im Dauerlauf; xperp und kraken riefen bis dahin nur `spiegele_journal`
  und nicht `vermerke_spiegelung` — kein Spiegeldefekt, solange
  `spiegelstand.py` "gleich" meldete, aber unsichtbar, ob der Zustand von der
  Kopie weiss. Muster (swap/handeln.py, `spiegeln`):
  `vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand)`, danach einmal
  `spiegele_journal([ZUSTAND], ziel)` nachziehen, wenn wirklich geschrieben wurde
  — sonst ist die Kopie genau in dem Zyklus aelter, in dem sich der Vermerk
  aendert. Nachweis ist der **byte-genaue Vergleich** (`cmp` je Datei bzw.
  `spiegelstand.py`), nicht der Rueckgabecode: bei Code 0 protokolliert der
  Dauerlauf nur "ok". Komplettpruefung `Agenten/Handel/spiegelstand.py`
  (byte-genau, Code 0/1) — dieselbe Rechnung liefert "Journal ausser Haus" im
  Tagesbericht und Block 11 der Systempruefung. Ausrollweg:
  `references/spur-weite-aenderung.md`.
- **Bus und Tagesbericht lesen feste Feldnamen — eine Spur mit anderer
  Zustandsform liest sich dort als leer.** `handel_befehle.status()` zaehlt
  `d.get('positionen')` als Liste und beschriftet mit `p.get('seite')`; eine Spur,
  die EINEN Eintrag unter `position` fuehrt, `richtung` statt `seite` schreibt und
  kein `modus` kennt, erscheint als „Modus unbekannt, 0 gespeicherte Positionen" —
  waehrend eine Position offen ist: eine falsche Aussage, kein
  Schoenheitsfehler. Beim Anbinden die eigene `zustand.json`-Form gegen die
  Erwartung des Lesers halten und den Leser die Varianten mitlesen lassen
  (`position` ODER `positionen`, `seite` ODER `richtung`, `modus` mit Vorgabe —
  und `modus` beim Schreiben der Spur mitpflegen). Nachweis: Leser laufen lassen,
  gezaehlte Positionszahl gegen den echten Zustand stellen; „die Zeile erscheint"
  belegt nichts.
- **Ein richtiger Feldname kann die falsche GROESSE tragen — Einheit pruefen, nicht
  nur Existenz.** Der gefaehrlichste Lesefehler ist nicht der erfundene Name,
  sondern der vorhandene mit anderer Dimension: ein Feld `stop_usd` ist ein
  VERLUSTBETRAG (der Schreiber prueft `einsatz_usd - erloes >= stop_usd`), kein
  Preis. An `zeile_position` gereicht, die daraus `kurs/stop - 1` rechnet, ergibt
  ein USD-Betrag neben einem Token-Kurs von 0,000136 einen Abstand von rund
  -100 % — der Bericht meldet „Stop gerissen" fuer jede gesunde Position. Regel:
  bei jedem gelesenen Zahlenfeld die Stelle im Schreiber aufsuchen, die es
  VERGLEICHT, und die Einheit von dort nehmen. Braucht der Leser eine andere
  Groesse, wird sie aus DERSELBEN Bedingung zurueckgerechnet, die der Schreiber
  prueft, mit dessen eigener Kostenfunktion (Probe mit Kurs 1 liefert den Faktor)
  — keine zweite Formel danebenstellen. Nachweis ist die Umkehrprobe: bei dem
  abgeleiteten Preis muss der Verlust exakt den Schwellwert ergeben. Fehlt eine
  Zutat (Buch nicht ladbar, Feld nicht da), `None` zurueckgeben — die Zeile ohne
  Marke ist besser als eine geratene.
- **„Rueckgabe N“ nach Spur-Neueintrag: die Spur selbst crasht, nicht die
  Verdrahtung.** Der Dauerlauf loggt nur `<spur> (papier) Rueckgabe 1` — die
  Ursache steht im Traceback der Spur. Sofort `handeln.py --papier` im Spurordner
  von Hand aufrufen und den Traceback lesen, statt an SPUREN oder Wrapper zu
  drehen. Haeufigste Ursache: **Zustands-Roundtrip** — `zustand.json`
  serialisiert alles zu Strings, `p["tag"]` ist beim naechsten Lauf ein ISO-String
  und kein `date`; ungeparst an `sess.zwangsschluss()` gibt es einen TypeError.
  Schreiben: `tag.isoformat()`; Lesen:
  `tag if isinstance(tag, date) else date.fromisoformat(tag)` — der Fehler
  erscheint erst im ZWEITEN Zyklus (erster Lauf hat keine Position).
- **`handeln.py` muss `--papier` als Flag UND als Positional akzeptieren.** Der
  Dauerlauf ruft `[PYTHON, skript, "--papier"]`; ein argparse-`choices`-Eintrag
  `"--papier"` allein reicht nicht (argparse liest `--papier` als Option, nicht als
  Positional → `unrecognized arguments`, Exit 2). Beides aufnehmen: Positional
  `papier` plus `add_argument("--papier", action="store_true")`, dann den Modus
  normalisieren.
- **Datenquelle als Test-Seam austauschbar machen.** Ein Modul, das im
  Einstiegspfad live Kerzen holt, macht die Logik untestbar: Modulvariable
  `kerzen_quelle = None` (None → echte Kraken/OKX-Kerzen), Tests setzen eine
  Lambda mit synthetischen Kerzen, `tearDown` setzt `None` zurueck — gleiche
  Mechanik wie die Order-Stilllegung per Lambda.
- **Erweiterst du die Signatur einer ersetzten Funktion, muessen die Doubles mit.**
  Ein handgeschriebenes `lambda k: …` baut die alte Signatur nach und bricht,
  sobald die Funktion einen Parameter dazubekommt (`richtung=`, `stat_id`) — in
  dem Testlauf, den du gerade nicht ausgefuehrt hast. Vor dem Lauf den Testbaum
  nach dem Symbol greppen, Doubles dieselbe Signatur annehmen lassen.
- **Eine geaenderte Signatur trifft auch die Aufrufer, die kein Test beruehrt.**
  Zieht eine geteilte Funktion jetzt einen instId statt einer Kerzenliste
  (`bot.hebel_deckel` nach Umstellung auf Tageskerzen), bleiben alle Tests gruen,
  weil sie eigene Stummel stellen — das Nachbartool ohne Test
  (`xperp/stopwahl.py`) gibt die alte Form weiter und bricht erst zur Laufzeit
  (Kerzenliste in der URL -> HTTP 414 „URI Too Long“). Nach jeder Aenderung an
  einer geteilten Funktion `grep -rn "<symbol>("` ueber ganz `Handel/` (auch
  Nachbartools) und jede Fundstelle mit der neuen Form versorgen.
- **Ein Stummel im Testbaum kann den geaenderten Aufruf verbergen — am echten
  Aufruf beweisen.** Ersetzen die Tests den AUFRUFER durch einen Stummel
  (`h.anlauf = anlauf_stummel`), prueft kein Test, ob der echte Aufrufer den neuen
  Parameter durchreicht. Dieselbe Luecke entsteht ohne jeden Stummel, wenn eine
  neue Hilfsfunktion nur ISOLIERT geprueft wird: sie rechnet richtig, ihr Test ist
  gruen — und der Leser ruft sie gar nicht auf, sondern reicht weiter den alten
  Rohwert durch. Die Gegenprobe (Fix zurueckbauen, Testlauf muss rot werden)
  entlarvt das sofort und gehoert zu JEDEM solchen Fix: bleibt sie gruen, prueft
  der Test die Mechanik statt die Verdrahtung. Der tragende Test geht deshalb
  ueber den echten Einstiegspunkt (`spur_<name>()` → `zeile_position()`), nicht
  ueber die Hilfsfunktion, und behauptet beides: der gelieferte Wert ist NICHT
  mehr der Rohwert, und die gerenderte Zeile enthaelt die Fehlmeldung nicht.
  Nachweis mit einem **Mitschreiber**: Zielfunktion durch
  einen Wrapper ersetzen, der die kwargs mitschreibt und durchruft
  (`indikatoren.lage = mitschreiber`), echten Aufruf ausfuehren, Parameter zeigen.
  Gleichnamige Module zweier Spuren ueber den Dateipfad laden
  (`importlib.util.spec_from_file_location`).
- **Ein Pruefer, der Quelltext parst, erblindet still, wenn sich die Form aendert.**
  Ein AST-Test, der gestartete Dateinamen als Literale in der
  `subprocess.run`-Liste sucht, findet nach einem Umbau auf eine Variable
  (`SPUREN[spur].get("skript", "handeln.py")`) nichts mehr: er bricht mit
  „keine … gefunden“ ab, statt zu pruefen — und faellt nicht auf, weil er in einer
  Sammelsuite steckt. Nach jeder Aenderung an einer Form, die ein fremder Pruefer
  liest, genau diesen Pruefer einzeln laufen lassen und die Fundstellen aus ALLEN
  Quellen nachziehen (Dict-Schluessel, `get`-Default, Listenelemente). Dasselbe
  gilt fuer Bus und Tagesbericht, die Feldnamen aus `zustand.json` lesen. Eine
  **Namensliste** im Pruefer altert genauso: zeigt sie auf eine Datei, die es
  nicht mehr gibt (Spur umbenannt), bricht sie mit `FileNotFoundError` ab. Ist ein
  solcher Pruefer erst repariert, mit einer **Kette** weiterer
  Vorbestands-Befunde rechnen — alles, was in der Sammelsuite hinter ihm stand,
  lief seit dem Umbau nie; in einem Zug abarbeiten.
- **Eine Papier-Position in `zustand.json` ist der zweite Zyklus-Test.** Der erste
  Lauf ohne Position prueft nur den Einstiegspfad; Ausstiege
  (Stop/Ziel/Zwangsschluss) laufen erst mit Position. Nach dem ersten
  Papier-Einstieg einen weiteren Zyklus abwarten, bevor die Spur als lauffaehig
  gilt.
- **Keine Behauptung ueber eine andere Spur im Code.** Ein Satz wie „SWAP:
  Papierpfad, kein Live-Zweig“ oder ein Flag `papierfest` altert in Minuten: SWAP
  bekam in derselben Sitzung einen Live-Pfad, `/status` und Tagesbericht logen
  danach. Was gemeldet wird, wird aus `wachen.json`/`zustand.json` der Spur
  **gelesen** — und vor jeder Aussage ueber fremde Spuren erst
  `git log --oneline -5`: an diesem Baum arbeiten mehrere Sitzungen gleichzeitig.
- **Wachen-Module liegen nicht immer im eigenen Ordner.** Liegt das `pruefmodul`
  woanders (SWAP liest `xperp/wachen_xperp.py`), muss der Pfad dorthin auf
  `sys.path` — sonst schreibt der Bericht „Wachen nicht lesbar“, obwohl nur der
  Import fehlte. Fester Modulpfad aus `__file__`, nicht aus einer in Tests
  umgebogenen Konstante.
- **Ausstiegsgruende nach Schwere pruefen, nicht nach Naehe.** Die
  Liquidationsschwelle liegt immer hinter dem Stop: Stand der Stop zuerst im `if`,
  war der Liquidationszweig toter Code, und ein Gap bis hinter die Liq meldete
  „stop" statt „LIQUIDATION". Beide Spuren pruefen die Liq zuerst
  (`xperp/handeln.py`, `swap/handeln.py`); Nachweis `xperp/test_ausstieg.py`
  (9 Tests, Long und Short, Kurs genau auf der Schwelle; `okxf.markt_schliessen`
  durch einen Werfer ersetzt, damit kein Test den Order-Pfad erreicht). Am Geld
  aendert die Reihenfolge nichts; falsch war nur das Journal-Etikett.
- **Ausgabe testen, nicht Quelltext.** Wer eine gedruckte Zeile pruefen will, darf
  nicht die Datei durchsuchen: Modulkopf und Kommentare enthalten dieselben
  Woerter. Die `print`-Argumente per `ast` holen und genau die Zeichenkette
  pruefen, die der Verbraucher liest. Gegenrichtung: manche Pruefungen sehen
  **absichtlich** in den Quelltext — `spiegel.py` wird darauf geprueft, dass das
  Wort `subprocess` nicht vorkommt (kein CLI-Aufruf aus der Papierspur). Vor dem
  Einbauen fremder Verdrahtung deren Pruefungen lesen: ein Kommentar mit dem
  falschen Wort reisst den Test, obwohl der Code stimmt.
- **„Prognose: Exit-Code 1” ist normal, aber nur der volle Lauf ist ein
  Markturteil.** `prognose.py` endet mit Code 1, wenn kein Markt alle Tore
  passiert — der gewollte „nichts gefunden”-Abschluss (Code 0 = mindestens ein
  Treffer, 1 = keiner; steht so im README). Wer „gibt es heute einen Einstieg?”
  beantworten will, darf sich nicht auf `/prognose [N]` im SkillsBot verlassen:
  der Weg läuft immer mit `--kurz`, schreibt weder Bericht noch Telegram-Meldung
  und sieht nur die N umsatzstärksten Märkte — „0 günstig” dort ist eine
  Stichprobe, kein Urteil. Der volle Lauf aus `Agenten/Handel`
  (`scanner/.venv/Scripts/python.exe prognose.py`) scannt das ganze Universum,
  legt `prognose_berichte/JJJJ-MM-TT.json` + `neuester.json` an und sendet die
  Meldung; fehlt die Tagesdatei, ist nur der `--kurz`-Weg gelaufen. Die Marktzahl
  im Kopf schwankt mit dem 24h-Umsatzfilter (20 vs. 34 in aufeinanderfolgenden
  Läufen) — kein Bug, nur die Tagesauswahl; Kopfzeile und Trefferzahl gehören
  zusammen interpretiert. **Jede Zeile nennt ihre Richtung:** Spalte `Richt` in
  der Tabelle, `LONG`/`SHORT` in der Meldung, `richtung` im Bericht — Stop und
  Ziel allein lassen offen, ob sie ueber oder unter dem Einstieg liegen. Beide
  Richtungen in dieselbe Ansage, jede mit ihrer **eigenen, an ihrer eigenen
  Verteilung kalibrierten** Schwelle: `references/tor-kalibrierung.md`, Regel 9.
- **Der Boersen-Stop ist eine Order mit eigenem Leben: jeder Ausstieg muss ihn
  abraeumen UND nachsehen.** Ein Notausstieg, der mit der Order zum Handelsplatz
  geht (`okx.stop_setzen`, `kraken.stop_setzen`), existiert weiter, wenn die Spur
  ihn vergisst: ohne gemerkte `algoId`/`txid` weder stornierbar noch abfragbar —
  und er verkauft spaeter eine NEUE Position desselben Instruments zum alten
  Stoppreis. Feste Reihenfolge: **Stop stornieren -> verkaufen -> bei Fehlschlag
  nachsehen, ob der Boersen-Stop gefuellt hat** (dann ist die Position weg und
  wird als `stop (boerse)` mit dem Stoppreis gebucht, statt als Karteileiche
  weiterzulaufen). Ein nicht stornierbarer Stop (schon ausgeloest, schon
  storniert) darf den Verkauf NICHT abbrechen — genau daran blieben Positionen im
  Buch stehen, die am Markt laengst verkauft waren; bleibt ein Stop offen, gehoert
  seine Kennung in `offene_stops` und im naechsten Live-Lauf erneut storniert.
  Beim EINSTIEG dasselbe: scheitert das Stop-Setzen nach dem Kauf, wird
  zurueckverkauft; geht auch das schief, wird die Position gebucht und als
  `boersen_stop_fehlt` markiert (eine Position am Markt, die im Buch fehlt, ist
  der schlimmere Zustand) — ein Kauf ohne Fuellung (`accFillSz`/`vol_exec` = 0)
  wird gar nicht gebucht. Nachweis: Attrappe statt Netz, die die
  Aufruf-REIHENFOLGE prueft (storno vor verkauf) und die drei Fehlerwege einzeln
  faehrt (Stop nicht setzbar, nicht stornierbar, Boersen-Stop hat ausgeloest).
  Checkliste: `references/spur-haerten.md`, Muster 9.
- **Eine Vorschau, die schreibt, ist keine Vorschau.** Laeuft in `--vorschau` der
  Ausstiegspfad mit, schliesst sie Kopien im Journal und schreibt den Zustand
  nicht — danach sagen Journal und Zustand Verschiedenes, und die naechste Runde
  schliesst dieselbe Position ein zweites Mal. Richtig ist ein Schalter an
  **einer** Stelle (modulweites `SCHREIBEN`, das `journal()` und
  `schreibe_zustand()` gemeinsam pruefen), nicht ein `if modus == "vorschau"` je
  Aufrufer; Vorschau-Ausgabezeilen markieren sich als „WAERE ZU“. Nachweis: Test
  mit offener Position — Journal bleibt leer, Zustandsdatei wird nicht angelegt.

- **Die Befehls-Ebene ist eine eigene Naht - und `/lage` darf nicht `/bericht`
  sein.** Bis 15.09.2026 rief der Handelsbot fuer beide `tagesbericht.baue(...)`
  auf; unterschieden hat sie nur `mit_xperp`. Wer den Handelsstand nach aussen
  zeigt, trennt die Sichten: JETZT (Positionen, Live-Tore, Freigaben) / GESCHICHTE
  (Bericht) / EINE SPUR in der Tiefe / BILANZ aller Spuren / GRUPPE (Indikatoren) /
  MARKT. Der Text steht in EINEM Modul (`Handel/befehle.py`), nicht in jedem Bot:
  zwei Fassungen von `/lage` zeigen nach dem ersten Fix Verschiedenes.
  - **HTML vs. Klartext ist der einzige Unterschied der zwei Bots.** Der
    Handelsbot sendet mit `parse_mode=HTML`, der SkillsBot ohne: derselbe Text
    braucht dort ein `klartext()` (entfernt `<b>`), sonst stehen die Marken
    woertlich in der Nachricht. Ein neuer Meldetext gehoert auf beide Wege
    geprueft - und die Hilfe des SkillsBot selbst ohne Marken geschrieben.
  - **Ein neuer Befehl braucht keine zweite Zahlenformel.** Runden, Treffer und
    Ergebnis kommen aus der Quelle, die die Spur schon hat
    (`auswertung_alle.kennzahlen_fuer(spur)`, `kernzeile()` der Spur ueber
    `tagesbericht.bilanz`). Hat eine Spur keine Auswertung, steht das da
    ("keine geschlossene Runde (n Einstiege, m Ausstiege)") - eine hier
    gerechnete Zahl waere eine zweite Wahrheit.
  - **Geteilte Aufzaehlungen wandern in eine Konstante.** Die Spur-Reihenfolge
    des Berichts liegt in `tagesbericht.HOLER`, die Spurliste wird per AST aus
    `dauerlauf.SPUREN` gelesen, die Strategie-Zuordnung in `befehle.FAMILIE`
    (Test: jede Spur hat eine Familie UND einen Leser). Eine abgeschriebene
    Liste faellt erst beim naechsten neuen Spurordner auf.
  - **Jede Auskunft nennt die Einheit und den Zustand, nicht nur die Zahl.**
    Ratsche mit Schwelle und "im Gewinn ja/nein", Ruecklauf mit Waehrung aus dem
    Feldnamen, Ausstiegsgruende als Zaehlung, Modus aus `zustand.json` (in
    `wachen.json` steht er nicht).
- **Ein neuer Spurordner ist in `.gitignore` nur freigegeben, nicht entsorgt.**
  `!Agenten/Handel/<spur>/*.json` gibt ALLES frei - auch `zustand.json`, also das
  laufende Buch. Die Sperrliste weiter unten nennt die Spuren einzeln; fehlt der
  neue Ordner dort, zeigt `git status` seine Zustandsdatei als `??` und der
  naechste `git add -A` nimmt Live-Stand mit. Gegenprobe nach jedem Anschliessen:
  `git check-ignore -v Agenten/Handel/<spur>/zustand.json` muss die Sperrzeile
  nennen (nicht die Freigabezeile).

## Welche Daten eine Sperre liest

Jede Bedingung, die eine Spur sperrt oder entsperrt, legt ausdr\u00fccklich fest,
auf welcher Datenmenge sie rechnet — das ist eine Entscheidung, keine
Nebenbedingung. Geltende Regel: eine **Betriebsstoerung** (Herzschlag-
Zwangsschluss, Notaus) ist keine Handelsentscheidung und darf eine
Erwartungswert-Sperre nicht ausl\u00f6sen. Die **Kapitalkurve** (Drawdown, Ratsche,
Halbierung, Kill-Switch) rechnet weiter auf ALLEN Buchungen — eine Stoerung ist
eingetragen und hat Geld bewegt.

- **Genau EIN Feld tr\u00e4gt die Zahl, auf der die Sperre beruht.** Hei\u00dft es
  `rollierender_ev`, dann ist das die Zahl der Bedingung; die Zahl \u00fcber alle
  Buchungen bekommt einen eigenen Namen (`rollierender_ev_alle`). Ein Feld mit
  zwei Bedeutungen ist der Fehler: Anzeige und Sperrtext lesen dasselbe Feld,
  und hinterher kann niemand sagen, worauf gesperrt wurde.
- **Die Umstellung geh\u00f6rt in ALLE Wachenfassungen** (scanner, xperp, kraken,
  orbk) — jede hat ihre eigene `lage()`. Eine vergessene Fassung sieht nicht
  wie ein Fehler aus, sondern wie eine Spur mit anderen Zahlen.
- **Ein Test ohne Gegenprobe bleibt stillschweigend gr\u00fcn.** Der Test muss so
  gebaut sein, dass er mit der ALTEN Rechnung fehlschl\u00e4gt: mehrere echte
  Runden mit Gewinn gegen eine Handvoll Zwangsschl\u00fcsse mit Verlust, so dass
  die alte Zahl negativ und die neue positiv ist — plus eine Zusicherung auf
  den alten Wert (`assertLess(s["rollierender_ev_alle"], 0)`).
- **Am lebenden System nachweisen, nicht nur im Test:** je Spur
  `handeln.py --wachen` fahren und die Zeile der Bedingung aus dem echten
  Journal zeigen (Spur, Zahl, ob gesperrt). Erst das belegt, dass die
  Umstellung wirkt — und deckt auf, wo eine Spur unter der Messgrenze liegt
  (`n/a`, zu wenig Handelsrunden).

Rezept mit Testger\u00fcst, Journal-Formen je Spur und Pr\u00fcfkommandos:
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
