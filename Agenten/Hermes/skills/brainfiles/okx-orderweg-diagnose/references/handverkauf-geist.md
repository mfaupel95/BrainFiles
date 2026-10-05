# Der Handverkauf wird als Geist gebucht: der teuerste Fall im Buch

Der Befund vom 05.10.2026 (Nacht 04./05.10.), gemessen an sechs echten OKX-
Live-Positionen. Er gehoert zu `buch-gegen-boerse.md` und ergaenzt Abschnitt 3
(Geister ausbuchen) um den Fall, den die Hausregel dort nicht kann.

## Der Befund in Zahlen

Vier echte Live-Positionen wurden ueber Nacht von Hand verkauft (Stops vom
Nutzer gesetzt). Das Haus buchte sie als `grund="buchbereinigung_geist"` mit
**Erlös 0.00** — weil ein Geist neutral gebucht wird (Einsatz zurueck, kein
erfundenes Ergebnis). Die Boerse fuehrte die Ergebnisse die ganze Zeit:

| Position | verkauft | Schnittskurs | `realizedPnl` | Journal |
|---|---|---|---|---|
| STRK long | 122.484 | 0,0537 | **+70,76** | 8.033 @ 0,05433 (Einstand) |
| QUANT short | 3.450 | 254,91 | **−18,47** | 641 @ 261,80 (Einstand) |
| NIGHT long | 1.550 | 0,0477 | — | 176 @ 0,05011 |
| SOL long | 668 | 121,42 | **+0,96** | 334 @ 121,21 |
| MON long | 3.992 | 0,0330 | — | 1.996 @ 0,0325 (echter `stop`) |

Der Verkaufspreis im Journal war ueberall der **EINSTAND**, nicht der
Marktpreis. Das ist das Kennzeichen: ein Geister wird neutral gebucht.

## Warum `_geist_erloes` danebenlag

Die Funktion fragt `/api/v5/account/positions-history` und liest dort den
Verkaufspreis. **Gemessen: `avgPx: None`.** Sie findet also den Eintrag,
bekommt aber keinen Preis, und bucht deshalb korrekt — aber ohne Ergebnis.

Der Verkaufspreis steht an genau EINER Stelle: **`/trade/fills` → `fillPx`.**

```
# der einzige Ort, an dem OKX den Ausfuehrungspreis fuehrt
okx._roh('/api/v5/trade/fills', signiert=True)
# Felder je Fuellung: instId, side, fillSz, fillPx, ts, accFillSz, ordId
```

Verifiziert am lebenden Konto:

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && \
./scanner/.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'scanner')
import okx, datetime, collections
r = okx._roh('/api/v5/trade/fills', signiert=True) or []
agg = collections.defaultdict(lambda: [0.0, 0.0])
for f in r:
    if (f.get('side') or '').lower() != 'sell': continue
    a = agg[f['instId']]
    a[0] += float(f['fillSz']); a[1] += float(f['fillSz'])*float(f['fillPx'])
for k,(m,v) in sorted(agg.items(), key=lambda x:-x[1][0]):
    print('%-30s %9.0f @ %.6g' % (k[:30], m, v/m))
"
```

## Die Regel, die die Hauspruefung nicht kannte

`bueche_geister_aus()` kennt nur **zwei** Zustaende: die Position steht an der
Boerse, oder sie fehlt. Einen dritten gibt es nicht — *die war da und ist
kleiner geworden, weil verkauft wurde*.

Die Uhrzeit-Kette aus dieser Nacht:

```
18:43  Boerse 19.616  Buch 19.616  steht da   -> bleibt
18:58  Boerse 12.033  Buch 12.033  steht da   -> bleibt
22:32  Boerse  8.033  Buch  8.033  steht da   -> bleibt
23:00  Boerse      0  Buch  8.033  FEHLT     -> "Geister" -> 0.00 Erloes
```

Jede Welle wurde als `handanpassung` gebucht (Mengen-Korrektur), nie als
Verkauf. Am Ende blieb nur das Aufräumen.

## Zusaetzlich: die Groessenabgleich-Stufe stand falsch

`buche_abgleich()` rief erst die Geister (sie loeschen die Position) und DANACH
`bueche_groessen_abgleichen` (sie zieht das Buch auf die Boersengroesse). Bei
einer auf null gelaufenen Position hatte die erste Stufe schon alles entfernt —
die zweite konnte nichts mehr angleichen. **Die Reihenfolge war der Fix, nicht
das Fehlen einer Funktion.**

Geprueft wurde die Reihenfolge im Test ueber den Quelltext (drei Aufrufe, zwei
Indizes, `assertLess`), weil das ohne echten Boersezugriff der kleinste Weg
ist und genau dann greift, wenn jemand die Stufen vertauscht.

## Die Bruecke

Gebaut: `xperp/boersen_bruecke.py` (Plan) + `handeln.buche_verkaeufe_aus_boerse()`
(Buchung), aufgerufen **vor** beiden Abgleichstufen. Drei Faelle:

| Buch vs. Boerse | `fills` | Aktion |
|---|---|---|
| Buch groesser, Rest offen | bezeugt | `verkauf` der Differenz zum echten Kurs; Rest bleibt, auf die Boersengroesse gerechnet |
| Buch > 0, Boerse 0 | bezeugt in Menge der Differenz | `verkauf`, Position raus |
| Buch > 0, Boerse 0 | **kein Fill** | bleibt Geist, neutral, als neutral BENANNT |

Der dritte Fall ist die Regel: **ein Verkauf braucht den Kurs.** Ohne Zeugen
wird nichts behauptet — `grund=verkauf_ohne_zeuge_neutral`.

Zwei Grenzen, beide getestet: im Papierlauf (`live=False`) wird die Boerse
**nicht einmal abgefragt** (sonst laege am Ende eine Papierposition gegen den
echten Bestand gerechnet und stuende als „verkauft" da), und ein Netzausfall
gibt `None` zurueck — **keinen leeren Plan**, denn ein leerer Plan heisst
„alles stimmt" und wuerde den Ausfall als Bestaetigung lesen.

## Fallstricke, die die Suite fand

- **Der Kernfix fehlte in der ersten Fassung.** Eine GANZ verkaufte Position hat
  an der Boerse 0 — ein Test `ist >= 1e-9` stufte sie als Geist ein, **obwohl die
  Boerse den Verkauf bezeugt hatte.** Genau der Fehler, den die Bruecke
  schliessen sollte. Ein Kommentar am Fundort, weil die Zahl verfuehrt.
- **Ein Netzausfall flog durch** (`plan()` fing nichts ab) und wurde als leerer
  Plan lesbar — derselbe Fehler, den `bueche_geister_aus` schon einmal hatte
  („faellt eine Abfrage aus, bleibt das Buch unberuehrt").
- **Ein Test las die ECHTE Boerse**, weil die Attrappe nicht gesetzt war (0,0567
  statt 0,0537). Ein Test, der vom Boersenzugang abhaengt, prueft den
  Buchungspfad nicht.
- **Zwei Tests rechneten falsch.** `(0 - Einstand) * Menge` ergibt 167.813 USD
  statt der realen −4.422,90 — und verlangte eine Buchung fuer einen Fall, der
  gar nicht ihre Aufgabe ist (Geister gehoeren `bueche_geister_aus`). In allen
  drei Faellen wurde der TEST korrigiert, nicht die Rechnung.
- **Eine Gegenprobe ohne den Fix muss rot sein.** Ohne die Zeile
  `if aktion == "geister" and fills bezeugen die Differenz -> verkauf` faellt
  genau EIN Test um; mit ihr sind es zwei gruene. Das ist der Beleg, dass der
  Test den Fehler und nicht etwas anderes sieht.

## Was die Hausregel weiterhin richtig macht

`buchbereinigung_geist` **abschalten ist falsch.** Dann bleiben Positionen im
Buch stehen, waehrend die Boerse verkauft hat — und die Spur kauft beim
naechsten Signal in eine Position, die es nicht gibt. Die Regel ist richtig;
sie brauchte nur einen Vorgänger, der ihr die Faelle wegnimmt, die keine
Geister sind.

## Reihenfolge der Verantwortung, wenn Max von Hand handelt

1. Verkaeufe bezeugen (`/trade/fills`) und zum echten Kurs buchen — **vor** der
   Geisterpruefung.
2. Was danach wirklich fehlt, darf die Geisterpruefung ausbuchen.
3. Ueber den Arbeitstag sammeln: `grep -h ",live," handelsjournal*.csv | grep -v
   anpassen` — eine `anpassung` auf einer Live-Position ist fast immer ein
   Handverkauf, der keinen Verkauf darstellt.
