# Buch und Boerse abgleichen

Pruef- und Reparaturweg fuer die Frage "stimmen unsere Buecher mit den Boersen
ueberein". Gilt fuer jede Spur, die ein eigenes Buch fuehrt (zustand.json +
handelsjournal.csv) und an einer Boerse ordert. Merksatz: **das Buch ist eine
Behauptung, die Boerse ist die Wahrheit**.

## Nie aus dem Buch schliessen, was live ist

- Die Zahl der Positionen im Zustand sagt NICHTS ueber Live-Positionen: ein Buch
  kann Papier-Altlasten fuehren, waehrend live gehandelt wurde, und umgekehrt.
  Zwei unabhaengige Zeugen noetig: **(a)** die Boerse direkt
  (`/api/v5/account/positions` ueber alle `instType`, `/api/v5/trade/orders-algo-pending`,
  `/api/v5/trade/orders-pending`; bei Kraken Balance + OpenOrders) und **(b)** das
  JOURNAL - ein Live-Lauf muss Kauf-/Verkaufszeilen tragen, Verwaltungszeilen
  (`funding`, `rollover`, `zyklus`, `quotes`) sind kein Beleg.
- Positionswaehrung der POSITION pruefen, nicht die Waehrung im Kopf des Kontos:
  OKX fuehrt Margin in USDC (`isoEq`/`availEq`), eine Abfrage mit `ccy=USDT`
  liefert eine leere Liste, obwohl voll besicherte Positionen offen sind.
- Audit in dieser Reihenfolge, jede Stufe rein lesend: (1) Prozesse/Treiber,
  (2) Zeitplan per `ast.parse` aus der Treiberliste (kein Import, der startet
  Prozesse), (3) Buecher gegen Boersen, (4) Kreuzprobe Journal. Erst danach
  reparieren.

## Richtung 1: die Boerse hat eine Position, das Buch nicht

Ursache: der Nutzer kauft per Hand in der App, waehrend die Spur nur ihr eigenes
Journal liest. Erkennungsmerkmal ist das `tag`-Feld der Boersenposition: die
Hausspur tagt nicht, Handauftraege tragen den Tag der App.

- **Uebernahme in das Buch** in JEDEM Live-Zyklus (nicht als Einmalwerkzeug):
  Seite, Menge und Einstieg von der Boerse, Stop aus ATR, Ziel nach der eigenen
  Regel. **Stop nur stellen, wenn noch keiner existiert** - ein zweiter Stop auf
d  derselben Position risikiert einen Doppelverkauf.
- **Nur die EIGENE Kontraktfamilie uebernehmen.** Fremde Instrumente im selben
  Konto gehoeren einem anderen Zweig; der Vergleich der Kontraktzahl braucht eine
  Toleranz (Float), sonst gilt jede Position als "nicht vorhanden" und wird
  doppelt gebucht.
- Gegenprobe: nach dem Lauf steht die Position im Buch UND ein Stop liegt an der
  Boerse (`/trade/orders-algo-pending` bzw. der Auftrag selbst), mit der vollen
  Kontraktzahl.

## Richtung 2: das Buch hat eine Position, die Boerse nicht

Ursache: von Hand geschlossen, Liquidationsrest, oder die Order ist nie gefuellt
worden.

- **Neutral austragen, nie als Totalverlust.** Die Schliessen-Zeile liest die
  Drawdown-Kurve als EROES; wer `margin_usd=0.00` bucht, erzeugt einen
  Phantomverlust in Hoehe des Einsatzes und zieht die Notbremse nach. Massgeblich
  ist der Boersenstand: `realizedPnl` + Einsatz (`/account/positions-history`),
  bei groesserem Boersenstand ANTEILIG (Buchkontrakte / `closeTotalPos`); ohne
  Boersensatz NEUTRAL (Einsatz zurueck).
- **Geister-Frist kurz halten.** Die "Order ist noch nicht gefuellt"-Entschuldigung
  darf nur kurz nach dem Eroeffnen gelten (Minuten, nicht Stunden), sonst bleiben
  handgeschlossene Positionen als Karteileichen unsichtbar, weil die Order ja
  weiter `accFillSz > 0` hat.
- **Groessendifferenz angleichen, nicht ignorieren:** Buch auf die
  Boersen-Kontraktzahl ziehen (beide Richtungen), Journalzeile mit Grund
  (`handanpassung`), Stop/Ziel/Einstieg unangetastet, keine Order.
- Der eigene Reparaturweg dafuer ist ein Werkzeug mit Trockenlauf als Standard
  und einer Kopie des Journals vor dem Schreiben (`.bak-JJJJMMTT`) - das Werkzeug
  liest und schreibt die GANZE Datei, mitten in einen Zyklus ginge eine frische
  Zeile verloren (deshalb: Dateien juenger als ein paar Minuten nicht anfassen).

## Papier darf nie eine echte Position schliessen

Fuehrt eine Spur EIN Buch fuer Papier und Live (typisch beim Scanner), schliesst
der Papierzyklus beim Stop-/Zielkurs sonst die Buchzeile, waehrend die Position an
der Boerse offen bleibt - Schaden ohne jede Order.

- **Marker beim Einstieg setzen** (`modus: live|papier`, `kauf_ord_id`,
  `kauf_txid`) und im Ausstiegspfad pruefen: eine Position mit Live-Marker bleibt
  im Papierlauf STEHEN und wird gemeldet.
- Der Notaus/Kill-Pfad braucht eine eigene Funktion (`nur_papier_verwerfen`),
  damit pruefbar ist, dass er beides trennt.
- Ist es passiert: Falschbuchung in eine `handelsjournal.verworfen-<datum>.csv`
  legen, die Position mit einer `anpassen`-Zeile (`buch_nachgezogen_boerse`)
  zurueckbuchen - die Zeile in der Drawdown-Kurve nicht einfach loeschen.

## Guthaben und Bestaende: der Name ist die halbe Antwort

- **Kraken fuehrt Krypto unter dem NACKTEN Code.** `guthaben('ALGO')` liefert den
  Bestand, `guthaben('ZALGO')` liefert 0,0 - die `Z`-Form gilt fuer Fiat- und
  Staking-Zeilen, nicht fuer Spot-Bestaende. Eine 0,0 ist damit eine Aussage
  ueber den NAMEN, nicht ueber die Position. Beide Schreibweisen gegenproben,
  bevor "kein Bestand" gemeldet wird; sonst steht neben vier offenen
  Stop-Orders die Behauptung, das Konto sei leer.
- **`guthaben()` ohne Argument gibt den FIAT-Betrag als ZAHL zurueck, kein
  Dict.** Wer darueber wie ueber ein Woerterbuch laeuft (Werte filtern, Nullen
  ausblenden), erhaelt ein leeres Ergebnis, das wie "nichts vorhanden" aussieht.
  Vor jeder Schleife die Signatur lesen (`grep '^def '`), nicht die Form raten.
- Bestaende je Waehrung einzeln abfragen und gegen die Buchmenge stellen: die
  Differenz ist der Befund. Eine GROESSERE Boersenmenge als im Buch heisst, es
  wurde mehrfach gekauft (Mechanik: `beleg-und-hand.md`).

## Wer hat das gekauft? Erst zuordnen, dann urteilen

Auf einem Konto, das mehrere Akteure benutzen (parallele Sitzung, Handkauf,
mehrere Spuren), ist ein Trade erst dann "unserer Spur" zuzuordnen, wenn die
GROESSE zu ihrer eigenen Orderregel passt. Gemessen: zwei Kaeufe ueber 277 EUR
auf einem Paar, das die Spur nur in 50-EUR-Belegschritten kauft - ein Handkauf,
kein Spurausfall. Ohne diese Pruefung schreibt man einer Spur einen Fehler zu,
den sie nicht hat, und uebersieht den echten (vier Kaeufe zu je 50 EUR).

Zeuge ist die Auftragsliste der Boerse (Paar, Menge, Kurs, Zeit), nicht die
Kontobewegung: Umbuchungen zwischen eigenen Konten sehen wie Handelsaktivitaet
aus.

## Den Tagesbericht als Verdachtsgenerator lesen

Der Bericht ueber alle Stufen ist der ANFANG der Pruefung, nicht das Urteil.
Was sich lohnt:

- **Ein Posten, dessen Groesse nicht zum Instrument passt** ("1 EUR" bei einem
  Paar, das die Spur in 50-EUR-Schritten kauft) - meist ein Buchposten ohne
  Einstiegspreis, siehe `beleg-und-hand.md`.
- **"Stop gerissen", das BLEIBT:** im laufenden Zyklus normal (der naechste
  schliesst), ueber zwei Zyklen ein echter Befund.
- **Negativer Zuwachs ("-159 Runden seit gestern")** ist kein Rechenfehler,
  sondern eine Buchbereinigung (Papier-Altlasten wurden ausgebucht): nennen,
  nicht als Alarm behandeln.
- **Dieselbe Spur in zwei Stufen mit gegensaetzlichem Vorzeichen** belegt, dass
  die Stufen keine Skalierung derselben Geschaefte sind - kein Summenvergleich.
- **Ein Kill-Switch, der in den skalierten Stufen ausloest und in der Basis
  nicht**, ist die Folge des Faktors, nicht ein Fehler der Basis.
- **Vor jedem Urteil die Zahlen an der Boerse nachziehen** (Positionen, offene
  Auftraege, geschlossene Auftraege) und die Zeilen, die die Spur selbst
  schreibt, als zweiten Zeugen daneben halten.

## Stops: anhaengend oder als eigener Auftrag

- An einen Auftrag **angehaengte** Stops (`attachAlgoOrds`) stehen im Auftrag,
  nicht in der Liste der offenen Algo-Auftraege. Fehlt dort ein Stop, heisst das
  NICHT, dass keiner existiert - erst den Auftrag lesen, dann urteilen.
- Stop stornieren braucht `instId`: ohne es antwortet OKX mit einem
  Parameterfehler (der Stop laesst sich nie abbestellen), mit ihm kann fuer eine
  bereits erledigte Order "existiert nicht mehr" kommen - das ist ERLEDIGT und
  kein Fehler.
- Bestandsaufraeumer fuer Waisenstops und fuer DUPLIKATE im Buch: ein Merker, der
  nur beim Erfolg faellt, sammelt sonst bei jedem Zyklus dieselbe Kennung (eine
  Zustandsdatei trug 23 Kopien desselben Stops).

## Beleg-Tor (der einzige echte Orderweg)

- Eine zentrale Beleg-/Freigabefunktion muss das **Fensterobjekt** fragen
  (`freigabefenster.lade(spur).offen()`), nicht das Modul (`fenster.offen(spur)`).
  Ein falscher Aufruf schliesst den einzigen sanktionierten Orderweg STILL,
  waehrend alle Tests gruen bleiben, weil sie das Tor mocken. Gegenprobe: ein
  echter `schreibe()`-Aufruf bei offenem Fenster, danach `verbrauche()`.
- Ein Beleg ist einmalig und wird VOR der Order verbraucht - bleibt er liegen,
  kann die Hand dieselbe Order ein zweites Mal ausfuehren.

## Spiegelung (Kopie ausser Haus)

Jeder schreibende Ausgang spiegelt: Zyklusende, Herzschlag-/Fristausstieg,
Vorschau-Sperren. Ein frueher `return` vor der Spiegelung laesst die Kopie
still veralten - das ist der Fehler, den ein Vergleich als ABWEICHUNG zeigt, ohne
dass jemand ihn ausloest. Deshalb `spiegelstand` als Gegenprobe nach JEDER
Aenderung an einem Buchpfad, und die Regel im Test festnageln (vor jedem `return`
im Lauffenster muss die Spiegelung stehen).

## Bericht an Max

Was jetzt konkret funktioniert (mit Boersen-Beleg: Kennung, Menge, Stop), was
absichtlich NICHT angefasst wurde (laufende Zyklen, Hand-Positionen, Fremdarbeit)
und welche Entscheidung offen ist. Nie "Spur X ist live" aus dem Zustand
schliessen - die Zahl kommt aus der Boersenabfrage, sonst in den Bericht als
ungeprueft markieren.
