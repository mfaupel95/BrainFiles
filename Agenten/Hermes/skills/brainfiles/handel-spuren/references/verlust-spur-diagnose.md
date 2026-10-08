# Diagnose: eine Spur macht nur Verlust / Positionen werden geoeffnet und direkt geschlossen

Symptom von Max: "Irgendwas macht nur Verlust, es werden Positionen geoeffnet und
sofort wieder geschlossen." Das ist fast nie eine Strategie-Frage - es sind drei
BUCHFUEHRUNGS-Mechanismen, die Positionen schliessen oder verschwinden lassen.
Vor jeder Strategie- oder Parameter-Diskussion alle drei pruefen; der Markt ist
der letzte Verdaechtige.

## Die drei Ursachen, in dieser Reihenfolge pruefen

### 1. Kill-Switch / Ratsche misst gegen einen PHANTOM-Hoechststand

Der Kill-Switch und die Drawdown-Ratsche lesen ihren Ruecklauf aus der
KUMULIERTEN realisierten Kurve (`ruecklauf = hoechststand - kum`). Jede
Schliessen-Zeile, die `margin_usd = NOMINAL` statt der echten Marge traegt
(typisch `verkauf_von_hand` / `verkauf_ohne_zeuge_neutral`), blaeht diesen
Hoechststand auf Phantom-Werte - und der Kill feuert dann gegen GEWINNER, weil
jeder kleine echte Ruecklauf gegen den riesigen Phantom-Peak misst.

- **Erkennung:** `--wachen` zeigt "Ruecklauf X USD von Hoechststand Y". Ist Y
  absurde Gross (z.B. 639.977 bei einem Konto von ~900), ist es ein Phantom-Peak.
- **Beleg:** Journal-Zeilen, bei denen `nominal_usd == margin_usd` steht, obwohl
  es kein Geist-zu-Einstand ist; sie tragen Grund `verkauf_von_hand` o.ae.
- **Fix:** die Blasenzeilen als `buchbereinigung` mit ECHTER Marge nachbuchen,
  die Bahnkurve ohne den Phantom-Peak neu aufsetzen (Werkzeug
  `xperp/geister_nachziehen.py`), UND an den Schreibstellen von
  `verkauf_von_hand` die Marge statt des Nominalwerts buchen.

### 2. Geister-Ausbuchung loescht echte LIVE-Positionen aus dem Buch

`buchbereinigung_geist` (Zeilen mit `modus=papier, aktion=schliessen`,
`grund=buchbereinigung_geist`, Preis = EINSTAND) bucht Positionen aus dem Buch,
weil die Boersenabfrage sie nicht findet - das Buch ist die Position los,
waerhend die Boerse sie weiter haelt. Eine frisch geoeffnete Live-Position, die
im naechsten Zyklus als Geist verschwindet, IST das Symptom "geoeffnet und
direkt geschlossen".

- **Erkennung:** Journal hat `eroeffnen` (live) und kurz danach
  `schliessen` (papier, `buchbereinigung_geist`) - der Preis ist der Einstand,
  NICHT ein Marktpreis. Echte Verkaeufe tragen `stop`/`ziel`/`limit_wartet` als
  Grund, nie `buchbereinigung_geist`.
- **Regel:** Eine Geister-Ausbuchung auf eine Position mit `modus=live` ist der
  Verdacht, nicht der Normalfall. Erst pruefen, ob die Boerse die Position
  wirklich nicht mehr fuehrt (`/account/positions`), bevor das Buch ihr folgt.

### 3. Buch-Stop und Boersen-Stop sind nicht synchronisiert

Das Buch fuehrt einen Stop (z.B. 82.800), an der Boerse liegt der Schutz-Stop
aber woanders (z.B. 76.061) oder schuetzt nur einen Teil der Kontrakte. Dann
laeuft die Position tiefer in den Verlust, als das Buch glaubt - "nur Verlust"
ohne dass ein Stop ausloest.

- **Erkennung:** Buch-Stop der Position gegen `okxf.schutz_stops(inst)` stellen;
  vergleiche TriggerPreis UND Menge. 336 Kontrakte im Buch mit 2 Stops ueber je
  261 = 75 ungeschuetzt.
- **Regel:** `_ist_handposition(p)` (herkunft `boerse_handgriff`) laesst
  pruefe_ausstiege die Position NICHT schliessen - der Buch-Stop dort ist Deko,
  der echte Schutz liegt an der Boerse. Fuer solche Positionen ist der
  Boersen-Stop die einzige Wahrheit.

## Ablauf

1. `--wachen` der Spur: Hoechststand/Ruecklauf/Groessenfaktor lesen
   (Phantom-Peak? Faktor 0.50 trotz frischem Buch = Ratsche klemmt).
2. `okx_positionen_live.py` (rein lesend): was die Boerse WIRKLICH fuehrt,
   gegen das Buch stellen.
3. Journal nach `eroeffnen`-`schliessen`-Paaren unter 2 h durchsuchen und je
   Paar den Grund lesen (kill_switch? geist? verkauf_von_hand?).
4. `schutz_stops(inst)` gegen Buch-Stop und -Menge abgleichen.
5. Grundverteilung der Schliessen-Zeilen: ein Kill, der GEWINNER schliesst,
   heisst Phantom-Peak aus Blasenzeilen mit Nominal-Marge (Beleg 06.10.2026:
   drei `verkauf_von_hand`-Zeilen bauten den Hoechststand auf 639.977).

## Merksaetze

- Ein Kill, der GEWINNER schliesst, ist ein Messfehler der Kurve, kein
  Markturteil. Deckel erhoehen daempft nur - die Wurzel ist die Blasenzeile.
- "Position geoeffnet und direkt geschlossen" hat drei unabhaengige Ursachen;
  nur eine zu finden und zu reparieren laesst die anderen stehen.
- `modus=live` im Journal ist ein BUCHVERMERK, kein Orderbeleg - der Beleg ist
  die Order in der Boersen-Historie / `/account/positions`.
