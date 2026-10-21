# Eine Spur LIVE betreiben: Neustart, Schutz-Deckung, Wache

Gilt, sobald eine Spur einen echten Orderweg hat und laeuft: Parameter aendern,
Lauf neu starten, Schutz-Stop nachziehen, Deckel- und Abbruchregeln setzen.
Der Bau einer Spur steht im SKILL.md, die Papier-Sperren in
`references/schattenarm.md`.

## 1. Vor einem Neustart mit anderen Parametern: FLACH sein

- Ein Live-Lauf misst seine Position relativ zu seinem **Startbestand**
  (`start_base`, gesetzt beim ERSTEN geprueften Auftrag). Eine Position, die vor
dem Neustart schon offen war, ist fuer den neuen Prozess **Fremdbestand**: er
  kann sie nie schliessen, und ein Signal in die Gegenrichtung baut eine zweite
  Positionsseite daneben — netto kleiner, waehrend der Deckel nur die eigene
  Seite rechnet.
- Reihenfolge, jede Stufe mit Nachkontrolle: **Lauf beenden** → Schutz-Stops
  DIESER Richtung stornieren → Market schliessen (`reduceOnly`) → pruefen, dass
  die Position weg ist → bei Fehlschlag den alten Stop SOFORT wieder setzen.
- Schliessen als **Market**, nicht Limit: ein Limit, das im Stress nicht fuellt,
  ist kein Ausstieg. Hausfunktion `okxf.markt_schliessen(inst, kontrakte, seite)`
  (reduceOnly, Gegenrichtung der Position).
- Werkzeugmuster: `Agenten/Handel/omnitrade2/schliessen.py` (Vorschau ist die
  Vorgabe, `--anwenden` schreibt).
- Nach dem Storno **Stops nachzaehlen**: eine flache Position mit liegen
  gebliebenem Schutzauftrag ist ein Geist, der beim naechsten Wechsel auf eine
  fremde Position trifft.

## 2. Parameter haben EINE Quelle

- Die Parameterdatei (`lauf.json` o.ae.) ist die Wahrheit. Ein Startskript, das
  Werte FEST eintraegt, laeuft daran vorbei — und **zwei Startskripte fuer denselben
  Lauf** sind eine Falle: je nach Aufrufer startet der Lauf anders (verschiedene
  Menge, verschiedene Binary-Pfade), und das faellt erst beim Vergleich der
  laufenden Kommandozeile mit der Datei auf.
- Die Zweitkopie wird zur **Weiterleitung**, nicht gepflegt:

  ```powershell
  $echt = Join-Path $agenten "Handel\<spur>\start.ps1"
  if (-not (Test-Path $echt)) { Write-Output "Startskript fehlt: $echt"; exit 5 }
  & $echt; exit $LASTEXITCODE
  ```

- Nach dem Start gegen den **laufenden** Prozess pruefen:
  `Get-CimInstance Win32_Process` filtern, `--quantity`/`--interval` aus der
  Kommandozeile lesen und mit der Datei vergleichen. Die Wache soll das selbst
  tun (Parameterpruefung) — sonst beschreibt die Datei einen anderen Lauf als den,
  der laeuft.

## 3. Schutz-Deckung ist RICHTUNGSGEBUNDEN

- "Es liegt ein Stop" ist keine Deckung. Als Schutz zaehlt nur ein Auftrag mit
  `reduceOnly` UND Seite GEGEN die Position (Short → Kauf-Stop, Long →
  Verkaufs-Stop). Ein reiner Triggerpreis-Test meldet nach einem
  Richtungswechsel "gedeckt", waehrend der neue Schenkel **nackt** an der Boerse
  steht.
- Geschuetzte MENGE = **Summe** der passenden Stops, nicht der groesste; Stops
  der Gegenrichtung werden storniert.
- Zwei Stufen = zwei Stops: der Nachzieher stellt nur die **Luecke**
  (`|Position| - gedeckt`), nie einen zweiten gleich grossen Stop (zwei gleiche
  Stops sind ein doppelter Ausstieg).
- Stoppreis richtungsabhaengig: Short-Stop UEBER, Long-Stop UNTER dem
  Durchschnittseinstieg (`avgPx` der Boersenposition — nicht der letzte
  Orderpreis, sonst wandert der Stop mit jedem Nachlegen).

## 4. Deckel-Ablehnungen sind NORMAL

- Eine Strategie, die ihr Signal je Kerze wiederholt, und ein Notional-Deckel
  erzeugen dauerhaft "Order rejected: Positionsdeckel". Das ist die Regel, die
  arbeitet, kein Defekt.
- Die Meldung traegt den gerechneten Notional-Wert IM Text; jede Ablehnung sieht
  damit wie eine NEUE Meldung aus (Entdopplung per String scheitert). Also nach
  KLASSE entdoppeln: zaehlen, hoechstens eine Zeile pro Tag; gemeldet wird nur,
  was fehlt (Position ohne Stop, Lauf tot, Order ohne Fill, Mengendrift).
- Abgelehnt heisst nicht gefuellt: Gebuehren entstehen nur an Fuellungen. Wer aus
  der Zahl der Ablehnungen auf Kosten schliesst, rechnet gegen den Log statt
  gegen das Konto.

## 5. Abbruchkriterium VOR dem Start festlegen

- Ohne Kriterium entscheidet der Zufall. Bewaehrt: Frist (z. B. 48 h) plus zwei
  harte Ausloeser (kumuliert −X USD, N Verlustrunden in Folge). Die Wache MELDET,
  gestoppt wird von Hand — ein Automat, der sich selbst abschaltet, nimmt sich die
  Stichprobe weg.
- Gemessen wird an der BOERSE (`positions-history`, `realizedPnl` seit
  `started_ms`), nicht am Status des Laufs: der fuehrt kein Ergebnis. Der
  Feldname ist `realizedPnl` (nicht `pnl`, das ist der Faktor).
- Gebuehren relativ denken: eine Runde kostet 2 × Gebuehr je Seite des
  NOMINALWERTS, unabhaengig von der Stufengroesse — eine groessere Stufe
  vergroessert den absoluten Verlust, nicht den prozentualen Vorteil.
- Kriterium als datierten `_vermerk` in die Parameterdatei UND als Aufgabe mit
  Datum ablegen; ein Kriterium, das nur im Chat stand, ist beim naechsten Mal weg.

## 6. Nachweis eines Neustarts

- Prozess: `--quantity` in der Kommandozeile, PID lebt (Programmnamen pruefen,
  Windows vergibt PIDs neu).
- Status: `updated_ms` juenger als 2–3 Kerzen; `net_quantity` in BASIS-Einheiten,
  die Boerse fuehrt KONTRAKTE — Umrechnung ueber `ctVal`, sonst meldet jeder
  Vergleich Drift.
- Boerse: Position flach bzw. passend, Deckung vollstaendig, keine Waisen-Stops.
- Wache **einmal von Hand** laufen lassen: leere Ausgabe = nichts zu melden ist
  der Beweis, dass sie nicht spammt.
- Kein Fill ist kein Fehler: eine Pullback-Regel kann stundenlang `hold` sein. Der
  Live-Beleg "Stufe + Stop" kommt mit dem ersten Signal — bis dahin ist nur die
  Kette belegt, nicht der Handel.

## Fallen

- Eine Meldung wie `Positionsdeckel ueberschritten: 40.36 > 25.00 (Laufposition
  -0.3800)` nennt die Position **NACH** dem Auftrag, nicht den Bestand. Wer sie
  als Bestand liest, diagnostiziert einen Doppelzaehl-Fehler, den es nicht gibt.
- `sz: 0` schuetzt nichts, existiert aber und kann beim Nachkauf auf eine fremde
  Position treffen.
- Nach dem Zuruecksetzen von Parametern die Merkdatei der Wache loeschen
  (`orders_seen`, `rejected_seen`, Tagesbudget) — sonst vergleicht sie den neuen
  Lauf mit dem alten oder schweigt, weil ihr Tagesbudget verbraucht ist.
