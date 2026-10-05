# Den Stop nachziehen: einen Schutzauftrag AENDERN, ohne die Position zu schliessen

Muster fuer: "Stop-Loss an den gehebelten Positionen nachziehen", "intelligent
anpassen bei Gelegenheit", "Trailing fuer die Spuren mit 1-3R Take-Profit".
Rechnung in `Agenten/Handel/trailing.py` (eine Datei fuer alle Spuren, ohne
Netzzugriff), Boersenamt in `okxf.stop_nachziehen()`.

## Das Problem, das der Trailing loest

Eine Position mit festem Stop gibt Ertrag auf dem Papier auf, den es real nicht
gibt: gewinnt der Markt 2R, steht der alte Stop 2R tiefer weiter offen — und
mit ihm jeder Zwischenstand. Ein Gewinn von 1,6R wird pauschal riskiert, weil
der Schutz erst am Ziel greift.

## Der Auftrag "1-3 Takeprofit" ist als FILTER falsch

R ist Ausstiegs**geometrie**, kein Zustand einer offenen Position. Eine Position
mit 1,5R-Ziel und 7 % Stop und eine mit 2,0R-Ziel und 5 % Stop brauchen
denselben Trailing; bei +1,6R hat die erste ihren Stop schon im Plus, die zweite
noch nicht. Nach `ziel_r` zu filtern schliesst genau die Spuren aus, die am
meisten davon haetten. Der Test haelt beide Positionen GEGEN: bei gleichem
Kurs bekommen sie denselben Stop (`assertAlmostEqual(k15["stop"],
k20["stop"])`).

Der Weg haengt stattdessen an zwei unabhaengig abfragbaren Groessen:

| Groesse | Frage | Vorgabe |
|---|---|---|
| `trailing_trigger_r` | Ab wie viel R darf ueberhaupt nachgezogen werden | 1,0 |
| `trailing_stop_prozent` | wie weit hinter dem erreichten Hochstand bleibt der Stop | 0,40 |
| `trailing_abstand_floor_pct` | Mindestabstand Stop zu Kurs (Marktrauschen) | 0,25 |
| `trailing_min_hub_r` | Mindestgewinn je Verlegung (ein Tick kostet eine Order) | 0,25 |
| `trailing_max_halten_pct` | nie weiter als das hinter den Hochstand | 5,0 |

Diese sind **Hauswerte, keine Messung**: die Tests pruefen ihre FORM
(vollstaendig, positiver Wert, Wache schlaegt Vorgabe), nicht ihren Betrag.
Geaendert wird ueber die Wache.

## DREI Tore, ohne die der Trailing schaedlich waere

Jedes Tor traegt eine Meldung ins Journal, nicht nach stdout — eine stille
Auslassung ist von einem geprueften Nicht-Ausloesen nicht zu unterscheiden.

1. **`trailing_aktiv` fehlt in der Wache -> nichts passiert.** Ohne diese
   Schranke zieht jede Spur durch ein vergessenes Feld ploetzlich nach.
2. **MEHR ALS EIN Boersen-Stop auf einer Position -> kein Trailing.** Drei
   Auftraege auf eine Position (33+22+12 Kontrakte auf 67, gemessen) ist kein
   Trailing-Fall: der engste Stop feuert beim naechsten Tick, die anderen
   bleiben als Waisen liegen. Drei einzelne Verlegungen wuerden die Position
   schliessen und zwei Schutzauftraege zuruecklassen — genau die Lektion aus dem
   ZEC-Fall. Solche Positionen sagt der Weg ab und nennt das Werkzeug, das sie
   zusammenfuehrt. **Genau EIN Stop ist der gesunde Fall**, und die Grenze darf
   ihn nicht mitaussperren (Test dafuer).
3. **Keine Stop-Kennung in der Position -> kein Trailing.** Der Weg erfindet
   keinen Stop; er nennt stattdessen das Werkzeug, das den fehlenden setzt.

Ein Trailing, der NICHT ausloest (vor dem Trigger, Hub zu klein), schreibt
**keine** Journalzeile — sonst wuende sich die Auswertung mit jedem Zyklus.

## Die vier Fallen, die beim Bauen je einmal passiert sind

**Die Positionsform gehoert in den Modulkopf, nicht ins Gedaechtnis.** Die
MENGE heisst je Spur anders: `menge` bei den Buch-Spuren, `kontrakte` bei den
XPERP-Spuren, `groesse`/`size` woanders. Nur `menge` zu lesen hiesse: der
Trailing greift bei dieser Spur nie, es faellt nicht auf, der Weg meldet
"keine Menge in der Position" und die Spur laeuft weiter. **Ein Werkzeug, das
Positionsfelder liest, probiert die Kandidatenfelder der Reihe nach** und
nennt im Fehlerfall, welche es gesehen hat — dann ist der Befund eine
Feldnamenfrage und nicht ein Defekt.

**Eine Funktion, die je nach Zweig einen anderen TYP zurueckgibt, taetet jeden
Aufrufer.** `kandidat()` gab mal `(wert, grund)` und mal ein nacktes Dict
zurueck. Jeder Aufrufer brauchte daraufhin einen `isinstance`-Zweig, und sieben
echte Fehler erschienen als Testfehler statt als Codefehler. **Konvention:
`(wert, grund)` immer, auch im Erfolgsfall.**

**Nach einer geaenderten Rueckgabeform JEDE Aufrufstelle pruefen.** Als
`kandidat()` auf das Tupel umgestellt wurde, lief `nachziehen()` noch auf der
alten Form und scheiterte an einem Indexfehler. Der Aufrufer einer geaenderten
Funktion ist nicht durch die Suite geprueft, wenn er selbst kein Test ist.

**Ein Trockenlauf, der den echten Weg ruft, ist gefaehrlicher als keiner.** Er
sieht aus wie ein Erfolg und hat trotzdem gehandelt. Der Trockenlaufpfad ruft
den Börsenweg **nicht**; ein Test belegt das ueber eine leere Aufrufliste der
Attrappe.

## Was der Trailing nicht tun darf

- **Eine Position schliessen.** Er aendert nur den Schutzpreis. Der
  Ausstiegszweig bleibt unberuehrt und wird VOR dem Trailing geprueft.
- **Zurueck wandern.** Der Stop folgt dem **Hochstand**, nicht dem aktuellen
  Kurs — sonst holt ein Ruecksetzer ihn wieder ins Minus und der Trailing ist
  am Ende schaedlicher als keiner. Getestet ueber eine ganze Kurve mit
  Ruecksetzer, nicht ueber einen Punkt.
- **Zu nah an den Kurs.** Ein Stop am Markt wird vom naechsten Tick erreicht;
  dafuer ist der Mindestabstand da.
- **Hinter die Liquidationsmarke rutschen.** `stop_vor_liq` verweigert dann —
  ein solcher Stop ist keine Absicherung, sondern eine Illusion. Die Rechnung
  ist eine Funktion aus Hebel und Wartungsmarge, dieselbe wie beim Einstieg
  (`liq < stop < einstieg`, Short spiegelbildlich).

## Der Boersenweg

`okxf.stop_nachziehen(algo_id, inst, preis)` aendert den Stop eines
BESTEHENDEN Algo-Auftrags ueber `amend-algos` (Aufruf und Felder in
`references/boersen-aufrufe.md`). Das ist etwas voellig anderes als stornieren
und neu setzen: dort gaebe es zwischen beiden Aktionen ein Fenster OHNE
Schutz. Der Weg leiht Signatur, Schluessel und Takt aus `xperp/okxf.py`, damit
nicht jede Spur ihre eigene Boersenlogik baut.

**Die Probe ohne Geld: denselben Wert zurueckschreiben.** Ein bestehender Stop
bekommt exakt seinen jetzigen Preis — nach der Aenderung muessen algoId,
Marke und Menge unveraendert dastehen. Haette die Route nicht gegriffen, waere
der Stop weg; so ist der Erfolg am Bestand ablesbar statt behauptet.

## Reihenfolge des Einbaus

1. Rechnung bauen (ohne Netz, ohne Order) und die drei Tore testen.
2. Boersenamt bauen und am ECHTEN Konto mit dem zurueckgeschriebenen Wert
   belegen.
3. In `pruefe_ausstiege` einhaengen, Live-Zweig only — ein Papierlauf aendert
   keinen Boersen-Auftrag.
4. Den Hochstand VOR der Aktivitaetspruefung pflegen: sonst fehlt er bei der
   ersten echten Ausloesung, weil die Spur den Trailing noch nicht freigeschaltet
   hatte.
5. Wachen **nicht** voreilig umstellen. `trailing_aktiv` gesetzt wird erst,
   wenn der Weg gebaut und getestet ist.