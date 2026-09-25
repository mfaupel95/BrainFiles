# Eine Spur scharf schalten (Live-Weg freigeben)

Auftrag in der Art: „Spur X scharf schalten“, „handel erlaubt auf <Boerse>“,
„Strategie hoch fahren“. Drei Teile gehoeren zusammen, und nur der erste ist
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

## 4. „Scharf“ heisst nicht „handelnd“

Jede Spur handelt erst bei ihrem EIGENEN Signal (frischer Kopier-Kauf, Score,
Gate). Nach dem Scharfstellen kann es Stunden oder Tage dauern, bis die erste
Buchung kommt - das ist kein Defekt und kein Grund, die Schalter wieder
umzulegen. Wer das Gefuehl „da passiert nichts“ beantworten will, prueft das
Signal-Gate mit Zahlen (`handeln.py --vorschau` nennt die gefilterten Kandidaten)
und legt einen Waechter auf die erste Buchung, statt nachzusteuern.
