# Eine Spur scharf schalten (Live-Weg freigeben)

Auftrag in der Art: „Spur X scharf schalten“, „handel erlaubt auf <Boerse>“,
„Strategie hoch fahren“. Fuenf Teile gehoeren zusammen, und nur der erste ist
Dateiarbeit.

## 1. Die zwei Schalter in der `wachen.json`

- `handel_erlaubt: true` und `freigabe.erfuellt: true` - der zweite ist die von
  Hand gesetzte Endabnahme, der Code rechnet nichts nach (`scanner/wachen_pruefung`
  liest nur den Haken).
- **Beides zusammen mit einem datierten Vermerk** (`_vermerk_scharf` o. ae.) in den
  Freigabe-Block: Auftraggeber, Datum, was unveraendert blieb. Ohne den Vermerk ist
  der Zustand beim naechsten Griff nicht mehr erklaerbar.
- **Groesse und Deckel NICHT mitziehen.** „hoch fahren“ heisst in diesem Haus
  „handeln duerfen“, nicht „mehr riskieren“ - wer den Einsatz mit erhoeht, hat eine
  zweite Entscheidung getroffen, die niemand beauftragt hat.
- Die Boerse der Spur steht in `boerse` (+ `guthaben_waehrung`); ein Wechsel der
  Boerse ist ein eigener Auftrag mit eigener Pruefung (`references/zweite-boerse.md`).
- **Die Schalter sind das LETZTE, nicht das erste.** Erst die fuenf Bedingungen
  lesen (`MAXHIRN_ROUTINE=1 <venv>/python handeln.py --wachen`), dann schreiben:
  eine reissende quantitative Bedingung nimmt `handel_erlaubt` innerhalb von
  Sekunden selbst wieder weg, und der Auftrag ist dann scheinbar erfuellt und
  trotzdem wirkungslos - Abschnitt 4.

## 2. Das Zeitfenster (Handelsregeln Punkt 3)

Ohne offenes Fenster bleibt der Live-Weg zu, egal was die Schalter sagen; die
Vorschau sagt dann `Live waere gesperrt durch: Freigabefenster zu` und der Zyklus
handelt Papier.

- Der Dauerlauf **stellt die Anfrage selbst**, wenn die Vorschau GENAU EINEN Grund
  nennt und dieser Grund das Wort `Freigabefenster` traegt (`nur_fenster_fehlt`).
- Steht die Spur in `dauerlauf.AUTO_FREIGABE`, bestaetigt er sofort selbst
  (`freigabefenster.oeffnen(spur, 12 h, "auto")`) - sonst wartet er auf ein `/ja`
  einer Sitzung am Bildschirm, und eine unbeantwortete Anfrage laeuft ab.
- **Ein ZWEITER Sperrgrund verhindert das Fenster - das ist richtig, kein Fehler.**
  Haengt die Spur am Guthaben, steht `nur X frei, noetig Y` daneben, die Auto-Freigabe
  greift nicht, und es entstehen keine Fenster fuer Laeufe, die nicht handeln koennen.
  Genau diese zwei Gruende sind der Normalfall bei einer frisch scharfen Spur.
- **Eine Spur in `AUTO_FREIGABE` aufzunehmen ist eine Aenderung am TREIBER**
  (`dauerlauf.py`) und wirkt erst nach dessen Neustart. Die Spur-Skripte selbst
  lesen ihre `wachen.json` je Zyklus - dort wirkt jede Aenderung sofort.

## 3. Der Nachweis, dass wirklich geschaltet ist

1. **Vorschau wie der Dauerlauf sie sieht:** `MAXHIRN_ROUTINE=1 <venv>/python.exe
   handeln.py --vorschau` muss genau einen Grund oder `nichts` nennen. Mehr als ein
   Grund heisst: noch nicht fahrbar, und die Gruende einzeln abarbeiten.
2. **Betriebslog:** nach dem naechsten Zyklus steht `Auto-Freigabe <spur> (720 min)`
   plus die Zykluszeile der Spur; die Fensterdatei traegt `freigegeben_von: auto`
   und `offen_bis` rund 12 h spaeter.
3. **Die Moduszeile ist kein Orderbeleg.** `(live) ok` sagt nur, welcher Modus
   ANGEFORDERT wurde - die Wahrheit steht im Journal (Live-Kaufzeile mit Kennung)
   oder an der Boerse (Position offen). Vor „es handelt“ beides lesen.
4. **Ein Boersen-Fenster braucht die richtige Herkunft.** Wird der Schluessel von
einem VPN-Ausgang abgewiesen, faellt die Order aus, obwohl alles geschaltet ist -
   vor dem Scharfstellen die Herkunft pruefen (`references/boersen-aufrufe.md`,
   Abschnitt „Reihenfolge beim Deuten einer Abweisung“).

## 4. Eine quantitative Bedingung nimmt den Schalter SELBST zurueck

`handel_erlaubt: true` ist keine Freigabe, sondern nur ein Eingang in die
Sperrenkette. Reisst eine der fuenf Bedingungen, ruft die Spur
`wachen_pruefung.sperre_zu()` und schreibt `handel_erlaubt` auf `false` zurueck -
**innerhalb desselben Aufrufs, der die Lage liest**. Der Merker
`_sperre_zu_ausgeloest` traegt Zeit und Grund und ist die einzige Spur davon.

Symptom: `handel_erlaubt` steht nach dem Setzen kurz auf `true`, und der
naechste `--wachen`- oder Zyklus-Aufruf meldet
`-> Bedingung 5: handel_erlaubt auf false gesetzt.` Die Vorschau nennt danach
weiter zwei Gruende, die Auto-Freigabe oeffnet kein Fenster, und die Spur sieht
aus wie eine, die nicht will.

**Regel: vor dem Setzen die Bedingungen einzeln lesen und die reissende benennen.**
Eine quantitative Bedingung (`rollierender_ev`, Ruecklauf, Runden) laesst sich
nicht "mitschalten" - sie ist eine eigene Entscheidung mit eigenem Vermerk
(`_<kriterium>_entfaellt`, datiert), und **das Aussetzen bleibt dem Nutzer**:
gehoert sie ihm, wird sie vorgelegt und nicht stillschweigend gecleart. Gehoert
sie nicht dazu, ist der ehrliche Abschluss "Schalter gesetzt, Bedingung X sperrt
weiter" - nicht ein zweiter Schreibversuch.

Zwei Nebenwirkungen, die man dabei mitnimmt:

- **`sperre_zu()` schreibt die `wachen.json` mit `Path.write_text` neu** - und
dreht dabei ein LF-Zeilenende auf CRLF. Der Diff zeigt danach die GANZE Datei
  (gemessen 111/104 statt der gewollten 10/3), obwohl inhaltlich nur die eigenen
  Schluessel dazukamen. Nach dem Lauf die Endungen aus der Vorversion
  wiederherstellen (`b.replace(b"\r\n", b"\n")`), sonst wandert eine
  Format-Aenderung in den Commit, die niemand beauftragt hat.
- **Eine Aufnahme in `dauerlauf.AUTO_FREIGABE` ist eine Aenderung am Treiber** und
  wirkt erst nach dessen Neustart (Abschnitt 2). Sie vorzubereiten ist richtig,
  auch solange die Bedingung noch sperrt - sie greift dann von selbst, sobald die
  Bedingung faellt.

## 5. Eine quantitative Bedingung AUSSETZEN statt loeschen

Entscheidet der Nutzer, dass eine reissende Bedingung nicht mehr gelten soll
(„Bedingung 5 entfaellt“), wird sie **abschaltbar gemacht, nicht entfernt**: ein
Feld in der `wachen.json`, dessen Vorgabe „gilt“ ist.

```json
"bedingung_5_aktiv": false,
"_bedingung_5_entfaellt": "<Datum> <wer>: <Grund>, beide Messungen, wie man es zuruecknimmt"
```

Die Lesefunktion (`bedingung_5_gilt(w)`) gibt bei FEHLENDEM Feld `True` zurueck —
nur ein ausdrueckliches `false` oeffnet. So bleibt die Bedingung fuer jede andere
Spur und fuer jede spaetere Fassung derselben Spur in Kraft, und der Weg zurueck
ist ein Zeichen.

**Die Bedingung wird an JEDER Stelle gelesen, an der sie wirkt — es sind zwei.**
Wer nur die Sperrliste umstellt, hat die Haelfte gemacht: der Sperrtext nennt den
Grund nicht mehr, `sperre_zu()` schliesst die Sperre aber weiter. Beide Stellen
pruefen (Sperrgrund UND Sperr-Schliessung) und die Anzeigezeile den Zustand
nennen lassen (`NEGATIV, Sperre ausgesetzt`), sonst sieht die Spur gesund aus und
sperrt sich beim naechsten `--wachen` wieder.

Nach dem Umlegen:

1. `handel_erlaubt` **erneut** auf `true` — `sperre_zu()` hat es beim vorigen
   Aufruf bereits auf `false` gestellt (Abschnitt 4), das ist kein neuer Fehler.
2. `--vorschau` muss **genau einen** Grund nennen (das Freigabefenster) oder
   `nichts`; erst dann greift `nur_fenster_fehlt` und die Auto-Freigabe oeffnet.
3. **Ein Test, der rot werden kann:** die Lesefunktion voruebergehend auf
   `return True` stellen, die Suite fahren — die Faelle „Sperre ausgesetzt“
   muessen fallen — und zuruecknehmen. Ohne diese Gegenprobe ist die Lockerung
   eine unsichtbare Codeverzweigung.
4. Das Fenster von Hand oeffnen ist erlaubt und wirkt sofort
   (`freigabefenster.anfrage_stellen(spur, 12*60)` + `oeffnen(spur, 12, "auto")`,
   genau der Weg, den der Dauerlauf geht) — die Aufnahme in `AUTO_FREIGABE`
   wirkt dagegen erst nach dessen Neustart.

## 6. „Auto-Freigabe optimieren“ heisst messen, nicht die Mechanik bauen

Auftrag in der Art: „Auto-Freigabe optimieren“, „die Spuren sollen von selbst
live gehen“. **Der Hebel ist fast nie die Auto-Freigabe, sondern die beiden
Schalter** — und das steht erst nach einer Messung fest.

`nur_fenster_fehlt` verlangt, dass die Vorschau **GENAU EINEN** Sperrgrund
nennt (Abschnitt 2). Also:

1. **Erst messen, dann bauen:** `Handel/sperrgruende.py` druckt je Spur die
   Zahl der Sperrgruende und markiert die Faelle „NUR das Fenster“. Kommt
   dort „Keine Spur haengt allein am Fenster“, ist die Auto-Freigabe nicht der
   Engpass — sie ist die **Vorbedingung**, nicht der Hebel.
2. **Der Hebel ist die Schalterzahl:** die typische frisch scharfe Spur hat
   DREI Gruende (`handel_erlaubt=false` · `freigabe.erfuellt=false` · kein
   Fenster). Setzt man die beiden Haken, bleibt genau einer übrig — und ab
   dann arbeitet die Auto-Freigabe von selbst, ohne dass an ihr eine Zeile
   geändert wurde. Vorher das Sperren zählen, danach den Bestand erneut
   zählen: derselbe Aufruf ist der Nachweis.
3. **Vor dem Setzen die reissende Bedingung suchen** (Abschnitt 4). Eine Spur
   auszunehmen ist Pflicht, wenn das Armieren selbst eine zerstoerende Kette
   ausloest: eine quantitative Sperre, deren einziger verbleibender Grund
   das Freigabefenster waere, schaltet beim ersten Live-Lauf durch — und eine
   Kill-Sperre schliesst dabei echte Positionen. Das ist beim Messen des
   Bestands zu sehen („2 Grund/Gruende“ bei einer Spur, deren erster Grund
   `handel_erlaubt=false` lautet) und gehoert als ausgenommene Spur in die
   Antwort, nicht in die Aktion.
4. **Ein Name im Werkzeug ist kein Beweis fuer einen Live-Pfad:** vorher per
   Endpunktsuche ueber `*/handeln.py` (ohne `tests/`) feststellen, welche
   Spuren ueberhaupt ordern koennen. Werkzeuge ohne Buch (etwa ein
   Bot-Waechter) fallen heraus, sonst wird eine Halbsache als Spur scharf
   gemeldet.
5. **Spuren ohne Sperrzeile sind blind.** Erscheint in der Messung
   „keine Sperrzeile“, liefert die Vorschau diese Zeile nicht, `nur_fenster_fehlt`
   bekommt `None`, und fuer diese Spuren wird nie ein Fenster geoeffnet — bei
   einem gemeinsamen Kern trifft das ALLE Spuren dieses Kerns (Pitfall 94).
   Geprueft wird die **Regel** (druckt jeder Spur dieser Weg dieselbe Zeile?),
   nicht die Liste der Namen; die Liste ist das Symptom.
6. **Abschluss je Spur mit Vermerk**, wie in Abschnitt 1 — inklusive „was
   unveraendert blieb“: kein Einsatz- und kein Deckelwert wird mitgezogen.

Der Nachweis ist eine Zeile im Betriebslog (`Auto-Freigabe <spur> (720 min)`)
plus die Fensterdatei mit `freigegeben_von: auto`. Wirkt die Aufnahme in
`AUTO_FREIGABE` erst nach dem Neustart des Treibers, ist das der Normalfall
(Abschnitt 2) — kein Fehler der Aenderung.

## 7. „Scharf“ heisst nicht „handelnd“

Jede Spur handelt erst bei ihrem EIGENEN Signal (frischer Kopier-Kauf, Score,
Gate). Nach dem Scharfstellen kann es Stunden oder Tage dauern, bis die erste
Buchung kommt - das ist kein Defekt und kein Grund, die Schalter wieder
umzulegen. Wer das Gefuehl „da passiert nichts“ beantworten will, prueft das
Signal-Gate mit Zahlen (`handeln.py --vorschau` nennt die gefilterten Kandidaten)
und legt einen Waechter auf die erste Buchung, statt nachzusteuern.
