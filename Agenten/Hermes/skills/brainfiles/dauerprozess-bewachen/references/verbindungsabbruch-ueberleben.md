# Wenn die Verbindung des Dauerprozesses stirbt

Ein Prozess, der an einem Datenstrom haengt (WebSocket, Named Pipe, Socket),
ueberlebt einen Abbruch nur, wenn ZWEI Stellen mitspielen: der Leseteil baut
neu auf, und der Verbraucher merkt, dass nichts mehr kommt. Fehlt eine der
beiden, sieht der Prozess gesund aus und arbeitet nie wieder.

## Der Mechanismus (warum es still bleibt)

- Der Leseteil bricht bei einem Fehler oft nur sich selbst ab (`break` im
  `match`, kein Reconnect). Die Task endet, der Prozess lebt.
- Der Kanal zum Verbraucher bleibt dabei OFFEN, weil ein Sender-Klon weiterlebt
  (Router, Broadcast, Queue). `recv()` liefert deshalb nie `None`, und die
  Abbruchbedingung `None => break` im Verbraucher ist unerreichbar.
- Ergebnis: Empfangen wartet ewig, CPU-Zuwachs nahe null, Zustandsdatei bleibt
  auf `running` stehen (sie wird je Ereignis geschrieben, nicht je Sekunde).

Die Wartestelle im Code lesen und fragen: WELCHES Ereignis beendet sie, und
kann dieses Ereignis nach dem Abbruch ueberhaupt noch eintreten?

## Fix-Form im Client

1. Aufbau und Lesen TRENNEN: eine Funktion `verbinde(url, abos) -> (Sender,
   Leser)`, die verbindet UND die Abo-Nachrichten schickt. Sie wird an zwei
   Stellen gerufen: beim ersten Aufbau (Fehler darf nach oben) und im
   Neuaufbau (Fehler wird wiederholt).
2. Die Lesetask endet nur noch bei Abschalt-Signal oder wenn der Verbraucher
   weg ist (`raw_tx.send(...).is_err()`). Jeder andere Ausgang - Lesefehler,
   Close-Frame, fehlgeschlagener Ping - fuehrt in den Neuaufbau.
3. Backoff als reine Funktion (`1, 2, 4, 8, 16, 30 s`, gedeckelt), damit sie
   ohne Netz testbar ist. Erfolg setzt den Zaehler auf 0; es gibt KEINE
   Obergrenze an Versuchen - ein toter Datenstrom soll weiter versuchen, nicht
   aufgeben.
4. Das Warten auf den naechsten Versuch muss das Abschalt-Signal mitbeachten
   (`select!` aus `sleep` und Shutdown), sonst haengt `disconnect()`.

## Fix-Form im Verbraucher

- **Funkstille-Waechter**: die Schleife hat meist schon einen Sekundentakt
  (Not-Aus-Pruefung). Dort die Zeit seit der letzten Nutzlast messen: laenger
  als 3 Intervalle, mindestens 60 s = still.
- **Startwert ist der Schleifenstart, nicht die Vorwaerm-Kerze.** Historische
  Daten sind per Definition alt; mit ihrem Zeitstempel laedt jeder Start sofort
  unnoetig nach und das Log zeigt einen Ausfall, den es nicht gab.
- **Nachladen baut den ZUSTAND neu auf, es spielt keine Handlungen nach.** Aus
  dem REST-Abruf den Puffer/Indikatorstand ersetzen und einmal je Luecke
  warnen; vergangene Kerzen duerfen keine Order ausloesen.
- Einmal je Luecke (`rest_nachgeladen`-Flag), sonst feuert der Nachlader jede
  Sekunde.
- Rueckfallweg als Trait-/Interface-Methode mit Fehler als VORGABE anlegen,
  damit jeder Client ihn nutzen kann und ein nicht unterstuetzender ehrlich
  scheitert statt still zu schweigen.

## Beweis, der etwas beweist

Ein Unit-Test der Backoff-Zahlen belegt nur die Arithmetik. Der Reconnect
selbst braucht einen Server, der sich schlecht benimmt:

1. Lokalen Server auf `127.0.0.1:0` binden, je Verbindung EINE Nutzlast schicken,
   danach den Socket OHNE Close-Frame fallen lassen (harter Abbruch).
2. Client gegen diese Adresse zeigen, erste Nutzlast abwarten, dann die ZWEITE
   mit Zeitgrenze abwarten - sie kommt nur nach einem Neuaufbau.
3. Verbindungszaehler (`AtomicUsize`) pruefen: `>= 2`.

Zwei Fallen beim Bauen der Attrappe:

- **Der Abbruch darf nicht sofort nach dem Senden kommen** - ohne kurze Pause
  (200 ms) ist die Nutzlast auf Loopback weg und der Test scheitert am ersten
  Empfang, nicht am Reconnect.
- **Die Nutzlast muss dem Parser entsprechen**, nicht dem Wunsch: ein
  Zeitstempel als JSON-Zahl, wo der Parser `as_str()` liest, faellt still durch
  und der Test meldet "keine erste Nutzlast". Die Felder aus dem vorhandenen
  Router-/Parser-Test abschreiben.

**Gegenprobe ist Pflicht**: im Neuaufbau ein `return` statt des Reconnects
setzen, denselben Test fahren (muss mit genau dem Symptom fallen), dann
zuruecksetzen und erneut gruen sehen. Ohne Gegenprobe weiss niemand, ob der
Test den Pfad ueberhaupt beruehrt.

## Ausrollen (Windows, laufender Prozess)

- Die laufende `.exe` ist gesperrt - `cargo build --release` scheitert mit
  `Zugriff verweigert (os error 5)`. Reihenfolge: Prozess beenden (PID aus der
  Kommandozeile bestaetigen, nicht aus dem Namen), bauen, starten.
- Vor dem Beenden **Flachstand belegen** (`net_quantity == 0` im Statusfile),
  sonst ist eine offene Position ohne ihren Prozess ein Notfall.
- **stdout nicht abschneiden.** `Start-Process -RedirectStandardOutput` und `>`
  ueberschreiben je Start: nach einem Neustart existiert nur der letzte Lauf,
  und "dieser Fehler kam genau einmal" ist ein Artefakt der Datei. Anhaengen
  (mit Zeitstempel) oder rotieren.
- Der Start ueber ein Skript kann die Doppelstart-Sperre ausloesen, solange der
  haengende Prozess noch lebt (er traegt das Instrument in seiner
  Kommandozeile) - deshalb erst beenden, dann starten.
- **Das Startskript im Hintergrund fahren, nicht in der Vorderrunde.** Ein
  `.ps1`, das einen Prozess startet, kann die Werkzeug-Frist reissen, obwohl der
  Kindprozess laengst laeuft (`Start-Process … -PassThru` kehrt nicht immer
  zurueck). Aufruf als `(powershell -NoProfile -File <skript.ps1> > <log> 2>&1 &)`,
  danach PID und Statusdatei pruefen - nicht die Ausgabe des Skripts als Beweis
  nehmen.
- Nach dem Start drei Zeugen: Prozess-PID frisch, Statusdatei juenger als eine
  Ereignisperiode, und im Log die Verbindungszeile des NEUEN Standes (nicht nur
  "gestartet").

## Wache: melden oder neu starten

Eine Wache, die einen Haenger nur MELDET, ist eine bewusste Entscheidung mit
Preis: bis zum Eingreifen eines Menschen laeuft nichts, und bei einem
Minutentakt sind das schnell Stunden. Diesen Preis in die Aufgabe schreiben
(Zeile, Schwelle, wer entscheidet) und nicht als "Wache vorhanden" verbuchen.
Ein automatischer Neustart braucht davor: Startschleifen-Sperre, Flachstands-
Pruefung und eine Meldung, die auch beim erfolgreichen Neustart kommt.
