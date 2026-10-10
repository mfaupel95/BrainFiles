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
- **Beleg, maschinell statt aus der Notiz:** alle `schliessen`/`kill_switch`-Zeilen
  mit `nominal_usd == margin_usd` heraussuchen (das ist der Fingerabdruck des
  Alt-Codes, der preis x Menge in BEIDE Felder schrieb). Eine datierte Notiz,
  die konkrete Zeilen nennt, ist eine Hypothese: am 05.-08.10.2026 nannte die
  Erinnerung drei `verkauf_von_hand`-Zeilen als Blase, gemessen war nur QUANT
  wirklich nominal==margin, die anderen beiden Phantome sassen in NIGHT und
  STRK. Immer gegen die JOURNALDATEI messen, nie gegen den Merkzettel.
- **Korrektur je Zeile (Hausregel):** hat die Boerse einen EINDEUTIGEN Zeugen
  fuer diese Position (`okxf.geschlossene_position(inst, seit_ms=...)` liefert
  realizedPnl einer geschlossenen Position), wird der Erloes auf
  `einsatz + realizedPnl` gezogen (QUANT: 224.93 - 32.30 = 192.63). Gehoert der
  Boersenwert zu einer ANDEREN (kuerzeren) Position derselben Serie, gibt es
  keinen Zeugen -> NEUTRAL buchen (Erloes = Einsatz). Ein Verkauf "zum
  Einstand" ist bei einer Handschliessung der Verdacht, nicht die Zahl.
- **Nach dem Schreiben sofort Q: nachziehen** (`wx.spiegele_journal([JOURNAL,
  ZUSTAND], w['journal_zweitziel'])`) - die Bedingung-4-Kopie traegt sonst die
  alten Phantom-Werte weiter und spiegelstand meldet Abweichung. Und einen
  lokalen `.bak` im Spurordner NICHT als Beweis nutzen: der Dauerlauf schreibt
  das Journal weiter, der `.bak` kann verschwinden; der dauerhafte Zeuge ist Q:.
- **Kurve danach pruefen:** Peak muss auf den realen Wert fallen (gemessen
  639.977 -> 690) und der Kill aufhoeren, Gewinner zu schliessen (0
  kill_switch-Ereignisse danach). Der Code-Fix selbst (Marge statt Nominal an
  den Schreibstellen von `verkauf_von_hand`) liegt in `_hand_erloes` - neue
  Zeilen koennen den Fehler nicht mehr erzeugen, nur alte Zeilen tragen ihn.

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
- **REGEL (Max, im Code):** `bueche_geister_aus` bucht NUR noch mit
  Boersenbeleg aus - `_geist_erloes` muss quelle="boerse" (realizedPnl aus
  positions-history) liefern. Liefert die Boerse keinen eindeutigen Zeugen,
  bleibt die Position als UNKLAR im Buch (Meldung im Zyklus, KEINE
  Journalzeile, KEIN Storno der offenen Order): eine Karteileiche blockiert
  hoechstens einen Platz, eine echte Position ohne Buch liefe unbewacht
  weiter. Ohne Beleg wird nie neutral ausgebucht - der Weg, der am 05.10.2026
  sechs echte Live-Positionen geloescht hat, ist damit zu. kraken/abgleich.py
  hatte diese Form schon ("ohne Zeugen bleibt die Position stehen und heisst
  unklar") - xperp folgt jetzt demselben Muster. Testseite: Tests, die das
  ALTE Verhalten einfroren ("ohne Boersensatz wird der Einsatz
  zurueckgebucht"), beim Regelwechsel INVERTIEREN statt nur erweitern
  (Unklar-Fall statt Geist-Fall; Umgebung stubbt `_geist_erloes` auf "boerse").
  Ein Test, der das gefaehrliche Altverhalten gruen laesst, zementiert es ein.
  Falle beim Umbau: der Test-Helfer `_pos()` hat in test_handeln_geister.py
  KEINEN `zeit`-Parameter (dort per `update` setzen), in
  test_abgleich_papier.py schon - vor dem Keyword-Argument die lokale
  Definition pruefen.

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
   heisst Phantom-Peak aus Blasenzeilen mit Nominal-Marge (Beleg 05.-08.10.2026:
   vier Zeilen mit `nominal_usd == margin_usd` - QUANT, NIGHT (2x), STRK -
   bauten den Hoechststand auf 639.977; nur QUANT hatte einen Boersenzeugen
   (realizedPnl -32.30), NIGHT/STRK wurden neutral gebucht).

Fuer den Boersenzeugen (`okxf.geschlossene_position` / positions-history):
OKX paginiert rueckwaerts - `after=<ts>` liefert AE...LTERE Eintraege,
`before=<ts>` die Juengeren. Wer "seit 05.10." mit `after` abfragt, bekommt die
Positionen vom 02./03.10. und denkt, die 06.10.-Position existiere nicht. Fuer
die JUNGSTE geschlossene Position reicht die Hausfunktion; fuer alle Eintraege
eines Fensters `before=<ende>`.

## Merksaetze

- Ein Kill, der GEWINNER schliesst, ist ein Messfehler der Kurve, kein
  Markturteil. Deckel erhoehen daempft nur - die Wurzel ist die Blasenzeile.
- "Position geoeffnet und direkt geschlossen" hat drei unabhaengige Ursachen;
  nur eine zu finden und zu reparieren laesst die anderen stehen.
- `modus=live` im Journal ist ein BUCHVERMERK, kein Orderbeleg - der Beleg ist
  die Order in der Boersen-Historie / `/account/positions`.
