# Stille Spuren deuten (bucht wenig oder nichts - Defekt oder Strategie?)

Ausloeser: "Welche Spuren sind still?", "warum steigt die nie aus?", eine
Uebersicht zeigt 0 Ausstiege, oder `auswertung_alle.py` meldet "nur N Runden:
das ist ein Befund, keine Messung".

Abgrenzung: geht es um eine Spur, die GAR NICHT bucht, obwohl `zustand.json`
frisch ist -> `betriebsfehler-spuren.md` (kaputtes wachen.json, Absturz im
Zyklus, `signal()` bildet nie ein Signal). Hier geht es um den haeufigeren
Fall: die Spur arbeitet, sieht aber still aus.

## Vier Lagen - nur eine ist ein Befund

| Lage | Merkmal | Urteil |
|---|---|---|
| wartet auf das erste Signal | kein Journal, `zustand.json` frisch (< 2 h) | gesund |
| haelt Positionen | Einstiege > 0, Ausstiege = 0, Stop+Ziel gesetzt, Position jung | gesund |
| Ausstiegsschwelle unerreichbar | Positionen alt, Peak weit unter der Trailing-Schwelle | **Befund** |
| laeuft nicht | kein Journal, Zustand alt oder fehlt | **Betriebsfehler** |

## Reihenfolge

1. **Spurliste aus `dauerlauf.SPUREN` lesen, nie aus dem Kopf.** Es ist ein
   dict `{name: {"ordner":..., "skript":...}}` und enthaelt Funktionsaufrufe
   (`os.path.join` fuer eigene venvs) - `ast.literal_eval` auf den ganzen
   Knoten scheitert mit `malformed node`. Schluessel und `ordner`/`skript`
   einzeln aus dem AST ziehen. Mehrere Spuren teilen sich einen Ordner
   (`nautilus_kraken` und `nautilus_kraken_futures`): der ORDNER zaehlt fuer
   die Dateien, der NAME fuer die Meldung.

2. **Journal zaehlen - aber nicht jede Spur schreibt `aktion`.** Einstiege
   `kauf/eroeffnen/KAUF/EINSTIEG`, Ausstiege `verkauf/schliessen/AUSSTIEG/
   ausgang`. `orbk` und `orb` haben GAR KEINE aktion-Spalte, sondern je Runde
   eine Zeile mit Ausgangsgrund (`...,ziel,...` / `...,stop,...`). Eine
   Zaehlung ueber `aktion` weist sie faelschlich als "still" aus, obwohl sie
   abgeschlossene Runden haben. Vor jedem Stille-Urteil die letzten Zeilen des
   Journals ansehen - das Format ist je Spur verschieden.

3. **Bei offenen Positionen die ECHTE Ausstiegsfunktion befragen**, nicht die
   Formel nachbauen (sonst prueft man die Nachbildung):
   `trailing_stop_strategie.ausstiegsgrund(p, kurs, jetzt, w)`.
   Braucht das nautilus-venv: `Agenten/Handel/nautilus/.venv/Scripts/python.exe`
   - mit dem scanner-venv scheitert schon der Import (`nautilus_trader`).

4. **Feldnamen aus dem Zustand lesen, nicht raten.** Die nautilus-Arme fuehren
   `preis_einstieg`, `letzter_kurs`, `hoechster_kurs`, `stop_preis`, `frist`,
   `eroeffnet` - NICHT `einstieg`/`hoch`. Ein geratener Name liefert `0`, und
   daraus wird ein Scheinbefund ("alle Positionen bei 0, Ausstieg kaputt"),
   der in Wahrheit nur ein Tippfehler ist. Einmal `zustand.json` roh ansehen,
   dann rechnen.

5. **Erst jetzt urteilen.** Aussagekraeftig sind drei Abstaende je Position:
   Gewinn gegen Einstieg, Peak gegen die Trailing-Aktivierung, Kurs gegen
   Stop, dazu die Restfrist.

## Der wiederkehrende echte Befund: unerreichbare Trailing-Schwelle

Gemessen 21.09.2026 an 8 offenen Positionen der nautilus-Arme: alle im Plus
(+5,9 bis +11,6 %), 32-39 % ueber dem Stop, Peak +6,2 bis +12,0 % - die
Trailing-Aktivierung steht bei +30 %. Keine Bedingung greift, also passiert
korrekt nichts. Der wirkliche Ausstiegsmechanismus ist die FRIST.

Das ist kein Defekt, aber auch kein gewollter Zustand: eine Schwelle, die das
Instrument in der Haltedauer nie erreicht, ist wirkungslos. Pruefen mit der
eigenen Historie (welchen Peak erreichen die Positionen tatsaechlich?), dann
die Schwelle an die gemessene Bewegung setzen - nicht an die erhoffte.

Merksatz: eine Ausstiegsregel, die nie ausloest, ist keine Regel. Wenn alle
Runden ueber die Frist enden, ist die Frist die Strategie - dann gehoert sie
ausgesprochen oder die Schwelle gesenkt.
