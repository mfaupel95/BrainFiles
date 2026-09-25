---
id: 20260921-handel-lektionen
title: 'Handel — Lektionen'
tags: [handel, lektion]
created: 2026-09-21
updated: 2026-09-25
related: ['[[Handel/Spuren-Uebersicht]]', '[[Lektionen/Wahrheit-pruefen]]']
summary: 'Die teuren Lehren aus dem Handelsteil: Buch und Boerse liefen auseinander, Papier mischte sich in Live-Buecher, Stoerungen sahen wie Runden aus, Preisregeln fehlten beim Notausstieg, ein Netzabbruch riss den ganzen Zyklus mit.'
---

# Handel — Lektionen

## 1. Ein Buch ist kein Beweis — die Boerse ist einer

**Belegter Fall (21.09.2026).** `xperp` fuehrte vier Positionen (ZEC, XAG, LINK, ETC) bei
Buchmodus live. An der Boerse existierten sie nicht: `/account/positions` kannte nur die
manuelle FIL-Position und einen XRP-Rest. Zweiter Zeuge: von 14 Live-Zeilen im Journal waren
**alle 14 `funding`** — kein Live-Kauf, kein Live-Verkauf. Die Positionen stammten aus dem
Papierlauf bei Buchmodus live. Am selben Tag dasselbe Muster bei `scanner`.

**Regel.** „Spur X ist live mit N Positionen" NIE aus `zustand.json` schliessen. Drei Zeugen:
Buch, Journal (**Live-Kaufzeilen muessen existieren**) und Boerse (`/account/positions`,
bei Kraken Balance + Open Orders).

**Fix (Muster fuer alle Spuren mit Live-Zweig).** Neue Positionen tragen `modus` (live/papier)
plus Orderkennung; am Anfang JEDES Live-Laufs bucht `bueche_papier_altlasten_aus()` Positionen
ohne Order als Papier-Verkauf mit Grund `buchbereinigung` aus.
`xperp` hat **kein** `kauf_ord_id`-Feld — dort ist der Massstab `modus`.

## 2. Nie im Papierlauf schliessen, was live offen ist

**Belegter Fall.** `flach_stellen`/`pruefe_ausstiege` schlossen im PAPIERLAUF auch Positionen
mit `modus=live` — aber nur im **Buch**, an der Boerse blieb die Position offen (HBAR:
„papier,schliessen,kill_switch" im Journal, 9,4 Kontrakte offen). Jetzt bleiben
`modus=live`-Positionen im Papierlauf stehen und werden gemeldet; geschlossen werden sie nur
vom Live-Lauf. Tests: `xperp/tests/test_handeln_geister`.

**Verwandt — und 23.09.2026 WIDERLEGT:** der Satz, `mosaic` habe den Waechter je Position,
galt nur fuer den LIVE-Zweig (`live_ausstiege`/`flach_stellen_live`). Der PAPIERzweig
(`pruefe_ausstiege`) hatte ihn nicht: als das Freigabefenster um 19:29 ablief, lief der Zyklus
**19:33:43 Papier** und buchte die echte BTC-Position mit `grund=ziel` aus dem Buch
(`papier,verkauf,BTC-USDC`, Kurs 84088.80). An der Boerse lagen `XXBT 0.00066027` und der
Stop `O3QKG4-P6QVQ-6SLH5V` unveraendert weiter — das Buch war flach, die Position nicht.

**Regel (gilt fuer JEDEN Zweig einer Spur mit gemeinsamem Buch).** Ein Papierlauf darf eine
Position mit `modus=live` **nie** ausbuchen — auch nicht beim Kill-Pfad. Er laesst sie stehen
und meldet sie. Belegt ist das erst, wenn der PAPIERZWEIG denselben Test hat wie der
Live-Zweig: `mosaic/tests/test_papier_laesst_live_stehen.py` (Ziel, Stop, Papier daneben,
Kill-Pfad). Bei `mosaic` ist die Regel in `nur_papier_verwerfen()` ausgelagert, damit sie
pruefbar ist statt als Zeile in `lauf()` zu stehen.

**Eine Luecke im Freigabefenster ist ein echter Betriebszustand, kein Randfall.** Zwischen
Ablauf (19:29) und Auto-Freigabe (19:36) lief genau ein Zyklus Papier — das reichte. Wer die
Modus-Trennung an einer Stelle prueft, prueft sie an der falschen; sie muss in beiden Zweigen
gelten.

**Werkzeug fuer den entstandenen Geist:** `mosaic/geist_zurueckbuchen.py` liest die
Falschbuchung im Journal, holt die Boersenwerte (Guthaben + offene Order-Algos) und bucht die
Position mit `modus=live` zurueck; die Falschbuchung wandert nach
`handelsjournal.verworfen-JJJJMMTT.csv`. Danach entscheidet der Live-Zweig wieder regulaer.
Trockenlauf ist Standard.

## 3. Eine Stoerung ist keine Runde

**Regel.** Ausstiege mit `herzschlag` im Grund sind Zwangsschluesse und werden in der
Auswertung **getrennt** gefuehrt. Die eine Definition liegt in `Handel/stoerungen.py`
(`ist_stoerung`, `teile_runden`); Wachen laden sie ueber den PFAD
(`scanner/wachen_pruefung.stoerungen_modul()`), weil eine Spur mit eigenem Ordner als
`sys.path[0]` startet.

**Belegte Groessen (15.09.2026):** 296 echte Runden, 21 Stoerungen (xperp 12, kraken 8,
swap 1) — xperp hatte damit **11 echte Runden statt 23**, kraken **2 statt 10**. Alle 21
zwischen 03.09. und 14.09., allein 7 am 12.09. — die Haeufung IST die Fehlersuche.
**Ueberraschend und wichtig:** bei kraken waren die Zwangsschluesse **+4,59 EUR positiv** und
die echten Runden -4,50 EUR negativ, bei xperp umgekehrt (-0,74 gegen +38,14 USD). Die
Richtung ist nicht vorhersagbar — deshalb beides getrennt ausweisen, nicht eines weglassen.

**Ursache war die Herzschlag-Grenze selbst** (30 min): jeder Rechnerneustart stellte flach und
buchte eine „Runde", die keine Entscheidung war. Deshalb 180 min (siehe
[[Handel/Gates-und-Freigabe]]).

## 4. Die Rueckgabe des Kindprozesses ist nicht das Ergebnis

**Belegter Fall.** `nautilus`-Arme lieferten Rueckgabe 1 („keine Quote angekommen und
Kopier-Spur tot"), `0xC0000409` und 300-s-Timeouts. Ursache war **Speicherdruck**, nicht Logik.
Nach dem Aufraeumen liefen sie. Also: vor jeder Logikdiagnose den Speicher/Commit pruefen
([[Lektionen/Windows-Umgebung]]).

## 5. Ein Ziel, das strukturell unerreichbar ist

**Belegter Fall.** Die Nautilus-Arme stoppen bei -19,8 % und trailen ab **+30 %** mit 25 %
Abstand — in 4-6 Tagen **kein einziger Ausstieg**, weil +30 % fuer BTC in einer Woche nicht
kommt (Peak +8,5 %). Der wirkliche Ausstieg ist die **Frist (168 h)**. Zusatzbefund: die 4
Positionen eines Arms sind EINE Wette (Minuten auseinander, selbes Instrument).

**Merksatz.** Vor dem Einbau einer Ausstiegsgeometrie die gemessene Verteilung der Bewegung
pruefen (Geometrie-Gegenprobe: Break-even = Stop/(Stop+Ziel) gegen die Trefferquote). Positive
Gegenprobe heisst nur „nicht offensichtlich falsch".

## 6. Optimieren am Original, nie an einer Nachbildung

**Belegter Fall.** `gitter/backtest_gitter.py` faehrt `gitter/handeln.py` **selbst**
(`leiter_bauen`, `arme`, `walk` per importlib) — eine Nachbildung wuerde die Nachbildung
optimieren. Befund: 42 Parameterkombinationen spannen nur +0,17 bis +2,23 %, der Parameter ist
NICHT der Hebel; Korrelation Markt/Gitter +0,78 ueber 52 Wochen — das Gitter folgt der
Marktrichtung und verliert in steigenden Fenstern. Geaendert wurde nur, was out-of-sample
ueberlebte (`stufen` 12 → 6, ~1,4 pp). Zusatzfalle: die Leiter entsteht nur beim **Erstlauf**
und wird nie verschoben — ein neuer `stufen`-Wert wirkt nur auf eine frische Leiter.

## 7. Zahlen brauchen das Skript

Jede Kennzahl auf dieser Wiki-Seite ist mit dem genannten Werkzeug nachrechenbar
(`auswertung_alle.py`, `kosten_wendepunkt.py`, `stoerungen.py`, `spiegelstand.py`,
`pruefe_ratschen.py`). Eine Kennzahl ohne Werkzeug ist beim naechsten Mal eine Behauptung.

## 8. Jede Boerse hat Preisregeln — ein roher Rechenwert fehlt den Notausstieg

**Belegter Fall (22.09.2026, Zyklus 42, `mosaic` live auf Kraken).** Kauft `SOL-USDC`, will den
Stop setzen, Kraken antwortet `EOrder:Invalid price:SOL/EUR price can only be specified up to
2 decimals` — daraufhin verkauft die Spur die Position **sofort zurueck** (richtige Reaktion:
nie eine Position ohne Notausstieg halten). Kosten 0,605 EUR in gut einer Sekunde, ohne Handel.

**Ursache.** `kraken._add_order` schrieb `str(preis)` — der Stop-Preis kommt aus
`Einstieg x (1 - stop_pct)` und hat praktisch immer zu viele Stellen. Die erlaubte Stellenzahl
steht **je Paar** in `AssetPairs.pair_decimals` (SOLEUR/XETHZEUR 2, XXBTZEUR 1, AKEEUR 8,
KASEUR 5) — ein fester Formatstring waere fuer jedes andere Paar falsch. Bei OKX heisst dieselbe
Regel `tickSz` (`okx_spot.slTriggerPx` sendete ebenfalls roh).

**Fix.** `kraken.preis_gerundet(paar, preis, richtung="auf")` und das Gegenstueck
`okx_spot.preis_gerundet`; beide runden AUF (der Long-Stop liegt nie tiefer als gerechnet, das
Risiko wird also nicht groesser als die Wache erlaubt) und geben einen fertig formatierten
String zurueck (`str(float)` schreibt kleine Werte als `1e-08`, was ebenfalls abgelehnt wird).
Tests: `kraken/tests/test_preis_gerundet.py`, `mosaic/tests/test_preis_gerundet.py`.

**Merksatz.** Ein Orderpreis gehoert durch die Regeln der Boerse, bevor er rausgeht — und die
Regeln kommen aus der API des Paares, nicht aus einer Konstanten. Probe ohne Geld: `AddOrder`
mit `validate=true` nimmt den gerundeten Preis an und den rohen nicht.

## 9. Eine Ausbuchung darf kein Ergebnis erfinden

**Regel.** Wird eine Position nur aus dem BUCH genommen (kein eigener Verkauf), muss die
Verkaufszeile das **echte Ergebnis** tragen — oder **neutral** sein (Einsatz zurueck). Nie
eine Null, nie eine Schaetzung.

**Belegter Fall (21.09.2026, `xperp`).** `bueche_geister_aus` schrieb `margin_usd = 0.00`.
Die Wachen lesen die `schliessen`-Zeile als **Erloes** — eine von Hand geschlossene Position
zaehlte damit als **Totalverlust ihres Einsatzes**. HBAR kostete das **-16,84 USD** in
genau der Drawdown-Kurve, aus der der Kill-Switch liest (vier Minuten spaeter feuerte er).
Am 22.09. standen drei weitere Handschluesse an (BZ, CL, CRCL = 97 USD Einsatz) — mit dem
alten Code waere der Ruecklauf von 71,14 auf **168,22** gesprungen, der Deckel 100 gerissen
und die Spur **falsch** flachgestellt und gesperrt worden.

**Fix.** `_geist_erloes()` holt `realizedPnl` aus `/api/v5/account/positions-history` und legt
es auf den Einsatz; ohne Boersensatz (kein Eintrag, Netzfehler, unlesbare Zahl) wird NEUTRAL
gebucht. Stand die Boerse **groesser** als das Buch (Handaufstockung), wird das Ergebnis
**anteilig** gerechnet (Buchkontrakte / `closeTotalPos`) — sonst zaehlt die Runde Gewinne,
die ihr nicht gehoeren. Nachweis am laufenden Betrieb (22.09., Zyklus 10:43):
BZ 39,82 → 41,51 · CL 36,70 → 38,84 · CRCL 20,56 → 17,89; Ruecklauf 71,14 → 81,95 statt
168,22.

## 10. Eine Entschuldigung braucht ein Verfallsdatum

**Regel.** Eine Sonderregel, die einen Fehlerfall entschuldigt, muss zeitlich begrenzt sein —
sonst wird sie zur Dauerkarte.

**Belegter Fall (22.09.2026, `xperp`).** Die Geisterpruefung ueberspringt eine fehlende
Position, wenn ihre Order „gefuellt" ist (Wettlauf Order → Position, HBAR am 21.09.). Diese
Order bleibt aber **fuer immer** `accFillSz > 0` — auch nachdem ein Mensch die Position
laengst geschlossen hat. BZ, CL und CRCL blieben so zwei Zyklen lang **Karteileichen**: an
der Boerse weg, im Buch mit Platz, Stop und Ziel, und jeder neue Einstieg blockiert.
Der erste Fix (echtes Ergebnis) reichte nicht — der 10:24-Zyklus buchte die drei nicht aus.

**Fix.** Die Fuellung zaehlt nur im Grace-Fenster `_GEIST_FUELLUNG_GRACE_MIN = 10` Minuten
nach dem Eroeffnen. **Ohne** Eroeffnungszeit bleibt es konservativ (nicht ausbuchen) — eine
echte Position ohne Buch liefe unbewacht, das wiegt schwerer als eine Karteileiche.

## 11. Ein Handgriff aendert die GROESSE — nicht nur die Existenz

**Auftrag Max (22.09.2026):** „Auch zukuenftig moechte ich noch per Hand Positionen
veraendern koennen." Geprueft wurde bis dahin nur, OB eine Position existiert.

**Belegte Abweichungen.** CL Buch 20 / Boerse 19 · BZ 208 / 727 · HBAR 9,4 / 47,1.

**Warum die Richtung zaehlt.** Ein zu KLEINES Buch ist der gefaehrliche Fall: der Ausstieg
schloesst nur den Buchteil und laesst den Rest **unbewacht** an der Boerse stehen. Darum ist
die Boerse die Wahrheit und das Buch folgt ihr (`bueche_groessen_abgleichen`, beide
Richtungen, Journalzeile `aktion=anpassen`, `grund=handanpassung`).

**Grenzen, die bleiben.** Stop, Ziel und Einstieg werden NICHT angefasst (die
Handelsentscheidung bleibt die der Spur), es geht KEINE Order raus, und die Buchhaltung der
Runde bleibt unberuehrt — sie kommt aus der `eroeffnen`-Zeile im Journal, nicht aus dem
Zustand. Die neue Aktion ist fuer den Rundenleser unsichtbar; so entsteht aus einem Handgriff
keine erfundene Runde.

**Altlasten heilen sich nicht von selbst.** Frueher geschriebene Null-Zeilen bleiben in der
Kurve. `Handel/xperp/geister_nachziehen.py` zieht sie auf den echten Wert (Vorschau Standard,
Kopie `handelsjournal.bak-JJJJMMTT.csv`); der Cron **`geister-zeilen-wache`** (alle 6 h,
`no_agent`) ruft das Werkzeug und schweigt, wenn nichts zu tun ist. Er fasst kein Journal an,
das juenger als 5 Minuten ist — das Werkzeug liest und schreibt die ganze Datei, mitten in
einen Zyklus ginge eine frische Zeile verloren.

Angriffspunkte in einer neuen Spur: `handeln.py` (`bueche_geister_aus`,
`bueche_groessen_abgleichen`), `okxf.geschlossene_position()`, Tests
`xperp/tests/test_handeln_geister.py` + `test_geister_nachziehen.py` (70 gruen).

## 12. Ein Netzfehler ist kein Fehler der Spur

**Regel.** In der Datenschicht einer Spur wird nur gefangen, was man kennt — alles andere
reisst den ganzen Zyklus mit. Jeder Abruf, der an einer Boerse oder einem fremden Server
haengt, braucht einen Zweig fuer **Verbindungsabbruch, Zeitueberschreitung und
abgeschnittene Antwort**: einmal nachfassen, dann `None` — wie beim bekannten HTTP 429.
Gibt die Spur an `zyklus()` eine Fehlerliste zurueck, steht das Ereignis im Bericht, statt
als Rueckgabe 1 beim Bus zu landen.

**Belegter Fall (22.09.2026, `moondev_sniper`).** `moondev_daten.pump_letzter_preis` fing
**nur** `HTTPError` (429). Ein Abbruch der Verbindung — `WinError 10054`, „vorhandene
Verbindung wurde vom Remotehost geschlossen" — flog durch `quelle()` bis in den Dauerlauf:
`Rueckgabe 1`, Bus-Alarm „Ergebniscode 1 - URLError: <urlopen error [WinError 10054] …>",
**dreimal an einem Tag** (02:07, 10:38, 12:11) bei rund 160 Zyklen. Der naechste Zyklus lief
jedes Mal normal — es war ein Netzfehler, kein Spurenfehler, und er kostete trotzdem einen
ganzen Zyklus.

**Fix (Muster fuer jede Datenschicht).** `except (urllib.error.URLError, OSError, ValueError)`
— `OSError` deckt Zeitueberschreitung, `ValueError` die mitten im Rumpf abgeschnittene
Antwort (`JSONDecodeError`). Zusaetzlich umschliesst die Spur **jeden einzelnen**
Kursabruf: ein Mint, der nicht antwortet, darf nicht die anderen mitreissen.

**Merksatz.** Ein `except` auf einen Statuscode ist ein halber Fang. Wer ein `except`
schreibt, muss sagen, was im NICHT gefangenen Fall passiert — hier: der Zyklus stirbt.
Nachweis: `Handel/tests/test_moondev_daten.py` (9) und
`moondev_sniper/tests/test_moondev_sniper.py` (`ZyklusBeiNetzabbruchTest` prueft die
Rueckgabe des GANZEN Papierlaufs, nicht nur die Ausnahme).

## 13. In-sample luegt — jede ML-Kennzahl braucht den Walk-Forward

**Regel.** Eine Trefferquote oder AUC aus einem Lauf, in dem das Modell auf DENSELBEN Daten
vorhersagt, auf denen es trainiert wurde, ist keine Messung. Der ehrliche Wert entsteht erst,
wenn zwischen Training und Vorhersage eine Zeitgrenze liegt und das Modell danach neu
trainiert wird (**Walk-Forward**). Der Abstand zwischen beiden Zahlen ist bei Kursdaten kein
Detail, sondern das ganze Ergebnis.

**Belegte Messung (25.09.2026, `Werkstatt/intelligent-trading-bot`, BTCUSDT 1 h, SVC auf
SMA/Linearreg-Slope/Stddev, Fenster 1-672):**

| Lauf | Daten | AUC Auf | AUC Ab | Handelsergebnis (beste von 100 Parameterkombinationen) |
|---|---|---|---|---|
| in-sample (`train`+`predict` auf denselben 8.000 Zeilen) | 2025-10-26 bis 2026-09-24 | **0,837** | **0,849** | **-22,7 %** |
| Walk-Forward (4 Schritte, je 3.000 h, je neu trainiert) | 2025-05-12 bis 2026-09-24 | **0,508** | **0,462** | **-4,8 %** |

Die AUC faellt von 0,837 auf 0,508 (Muenzwurf) — das Modell hatte **keinen** Vorteil, es sah nur
die Antworten. Auch der Walk-Forward-Lauf ist in ALLEN 100 Kombinationen negativ (beste:
107 Transaktionen, 40,2 % profitabel, -4,8 % vor Gebuehren). Befund: SMA/Slope/Stddev +
SVC auf BTC 1 h traegt nicht aus dem Trainingsfenster heraus. Zwei Laeufe an verschiedenen
Tagen (22.09. und 25.09.) liegen bei denselben Aussagen — die Kette ist reproduzierbar.

**Die Mechanik dahinter.** `simulate` (Parameterraster ueber Kauf-/Verkaufsschwellen) liest
`signals.csv`; `predict_rolling` schreibt die Vorhersagen aus nicht gesehenen Fenstern in
dieselbe Datei. Es ist derselbe Simulator, nur mit ehrlichem Input — genau deshalb ist der
Vergleich aussagekraeftig.

**Nachweis / Werkzeug.** Der Klon kann die ganze Kette (venv Python 3.13 ist fertig, alle
noetigen Bibliotheken vorhanden; `tsfresh` und `MetaTrader5` fehlen, beide optional). Zwei
fertige Konfigurationen liegen im Klon — der in-sample-Lauf und die ehrliche Gegenprobe:

```
cd Werkstatt/intelligent-trading-bot
K=configs/config-hermes-walk-forward.json     # oder config-hermes-in-sample.json
./.venv/Scripts/python.exe -m scripts.download -c $K      # Binance, oeffentlich, ~60 s
./.venv/Scripts/python.exe -m scripts.merge    -c $K
./.venv/Scripts/python.exe -m scripts.features -c $K
./.venv/Scripts/python.exe -m scripts.labels   -c $K
./.venv/Scripts/python.exe -m scripts.train    -c $K      # nur in-sample
./.venv/Scripts/python.exe -m scripts.predict  -c $K      # nur in-sample
./.venv/Scripts/python.exe -m scripts.predict_rolling -c $K   # nur Walk-Forward, ~2 min
./.venv/Scripts/python.exe -m scripts.signals  -c $K
./.venv/Scripts/python.exe -m scripts.simulate -c $K
```

Der ganze Stand steht danach in einer Zeile: `.venv/Scripts/python.exe itb_pruefstand.py`
(braucht kein Netz, aendert nichts) — dieselbe Zeile ist der Startbefehl im Startfenster
`Agenten/Werkzeuge/repos-zentrale`. Der Klon haengt dort als Verknuepfung
`Werkstatt/Repos/intelligent-trading-bot` -> `Werkstatt/intelligent-trading-bot`, damit die
absoluten Pfade im venv gueltig bleiben.

**Zwei Fallen beim Nachrechnen.** (1) `predictions.txt` und `signal_models.txt` werden
**angehaengt**: jeder Lauf schreibt einen Block, getrennt durch eine Leerzeile, der letzte
Block ist der laufende Stand. Der in-sample-Stand liegt als `predictions.in-sample.txt` /
`signal_models.in-sample.txt` daneben, sonst ist er beim naechsten Lauf weg. (2) Die Daten
liegen unter `DATA/` **im Klon** (das Repo ignoriert `/DATA/` und `/MODELS/` selbst) — ein
Arbeitsordner unter `Agenten/Hermes/cache/scratch` ist nach 24 h Ruhe geleert, und mit ihm das
Ergebnis (so passiert nach dem ersten Lauf am 22.09.).

Ergebnisse landen unter `data_folder/<symbol>/` (`predictions.txt` = AUC/AP/F1,
`signal_models.txt` = Handelsergebnis je Schwellenpaar). `train_length: 0` haelt alle Zeilen,
`algorithms[0].params.length` ist das Trainingsfenster je Schritt, `rolling_predict`
(`prediction_size`, `prediction_steps`) der Walk-Forward. Kurse kommen oeffentlich von Binance
(`api_key: "dummy"` genuegt fuers Herunterladen).

**Merksatz.** Bevor eine Spur mit ML-Kennzahlen bewertet wird, zuerst fragen: **welche Zeilen
hat das Modell beim Vorhersagen schon gesehen?** Der Klon taugt als Pruefstand fuer diese eine
Frage — er ist NICHT in den Dauerlauf eingebunden und braucht dort auch nicht hin: seine
Ordner nutzen Binance und MetaTrader 5, waehrend der eigene Handel ueber OKX und Kraken laeuft.

## Ein Ziel-Ausstieg ist kein Kaufsignal (23.09.2026)

ZEC wurde live im Ziel verkauft (1618,36) und **acht Sekunden spaeter** zum fast selben Kurs neu
gekauft (1619,38) — 1,2 % Gebuehren fuer dieselbe Bewegung. Der Kandidat stand weiter auf der
Rangliste, weil sein Signal nicht verschwunden war, sondern gerade **erfuellt** wurde.

- Nach einem Ausstieg mit Grund `ziel` gilt jetzt `sperrfrist_nach_ziel_stunden` (scanner: 2,0;
  Zahl in der Wachen, 0 = aus). Gemerkt wird der Zeitpunkt je Instrument in
  `zustand.json → letzte_ziele`; der Kandidat wird mit Grund „Sperrfrist nach Ziel-Ausstieg"
  abgelehnt.
- **Nach einem STOP gilt die laengere Abklingzeit** (`abklingzeit_tage`, scanner 4) — ein
  gescheiterter Versuch ist ein anderer Grund als ein gelungener. Zwei Mechanismen, zwei
  Zeitraeume, beide in der `wachen.json`.
- Merksatz: **Ein Ausstieg, der das Ziel erreicht, hat das Signal verbraucht.** Wer sofort
  wieder einsteigt, bezahlt die Gebuehr fuer eine Information, die schon bezahlt war.
- Der Test dazu darf nicht nur „Sperre greift" pruefen: die Gegenprobe (nach 2,5 h wird wieder
  gekauft) ist der Teil, der eine kaputte Sperre findet, die nie aufgeht.

## Ein trockener Zulauf ist keine tote Spur (23.09.2026)

Die `stille-spuren-wache` meldete **robinhood_radar TOT — Zustand 6,8 h alt**, waehrend der
Dauerlauf alle 15 Minuten `robinhood_radar (papier) ok` schrieb. Beides stimmte: der Zyklus lief,
aber er schrieb nichts.

- Ursache: `spur_buch.zyklus()` kehrte im Zweig **„keine Daten"** ohne `schreibe_zustand()`
  zurueck. Damit fror `letzter_lauf` ein — und die Wache liest genau dieses Feld. Jetzt wird der
  Zustand auch dann geschrieben und gespiegelt (Bedingung 4 gilt fuer **jeden** Ausgang); in
  `--vorschau` weiterhin nicht.
- **Der Grund gehoert in den Zustand.** Neu steht je Zyklus `datenlage` darin, z. B.
  `{"keine_daten": true, "grund": "keine Instrumente", "hinweis": {"zu wenige bewertete Kaeufer": 2}}`.
  Die Zaehler liefert die Spur ueber den optionalen `datenlage=`-Haken an `zyklus()` (robinhood_radar
  reicht die Ablehnungsgruende aus `_kennzahlen` durch). Vorher rechnete die Spur diese Zaehler und
  **niemand sah sie** — Stille war von einem Defekt nicht zu unterscheiden.
- Nebenbefund derselben Meldung: `stille_spuren._zustand()` las nur `zustand.json`. Eine live
  laufende Spur schreibt den Papierzweig nicht mehr (dieselbe Falle wie beim Herzschlag) — jetzt
  gewinnt der **frischste** der beiden Staende, Papier oder Live.
- Merksatz: **Ein Zyklus, der nichts bucht, ist trotzdem gelaufen.** Wer den Herzschlag nur im
  Erfolgsfall schreibt, baut sich eine Wache, die den eigenen Betrieb als Ausfall meldet.
- Nachweis: robinhood_radar von „TOT" auf **HAELT** (2 Positionen), moondev_marktlage auf
  **LAEUFT** (2 echte Ausstiege), die echte Wache gibt nichts mehr aus (leer = gesund).
  Tests: `tests/test_spur_buch_trocken.py` (5) + `tests/test_stille_spuren_werkzeug.py` (11).

## Ein Bot, der nicht mehr nachkaufen kann, hat keinen Stop (23.09.2026)

Future-DCA und Future-Grid kaufen nach, solange der Kurs faellt. Ist die letzte
Stufe gefuellt, endet das - und dann haelt der Bot nur noch und laeuft in die
Liquidation. Bei allen fuenf laufenden DCA-Bots war `slPx` leer, also schuetzte
niemand: UNI 5,6 % und ARB 5,0 % vor der Liquidation, Munition 0/11 bzw. 0/8.

- **Die Grenze ist messbar, nicht zu schaetzen.** Tiefste Kauforder aus
  `/tradingBot/dca/orders` (cycleId aus `cycle-list`) - und die Planrechnung
  `initPx * (1 - maxSafetyOrds * pxSteps)` ergab beim echten Bot denselben Wert
  (9,613). Zwei unabhaengige Wege, ein Ergebnis: erst dann darf eine Grenze in
  eine Wache.
- **Ein Bot-Zustand ist kein Konto-Zustand.** `fillSafetyOrds` gegen
  `maxSafetyOrds` sagt, ob noch gekauft werden kann; das steht in keiner
  Position und in keinem Guthaben.
- **Ein Stop-Loss, den die Boerse nicht kennt, ist keiner.** Die Bots haben
  kein `slPx`; ein Waechter, der nicht laeuft, schuetzt nichts. Deshalb setzt ein
  NEUER Bot bei uns seinen Stop gleich mit (`slPct` bzw. `slTriggerPx = minPx`).
- Handwerkszeug: `Agenten/Handel/okx_bot_waechter/`, Meldung per Cron
  `okx-bot-wache` (30 min, nur Neues). Gestoppt wird nur mit `stop_erlaubt=true`
  UND `--anwenden` - zwei Tore, wie bei den Spuren.

## Eine Nachkauf-Leiter wird in ATR-Einheiten gebaut, nicht in Prozent (23.09.2026)

Fuenf Future-DCA-Bots, fuenf leere Leitern. Aus den eigenen Tageskerzen gemessen: die
Stufen reichten 4,16 bis 8,40 % unter den ersten Kauf - die Instrumente laufen aber
8,6 bis 13,2 % pro Tag und fielen in 90 Tagen 21 bis 28 % vom Hoch. Eine Leiter, die
nicht weiter reicht als die Tagesspanne, ist nach einem Tag verbraucht: dann kauft
nichts mehr nach, und die Position laeuft ungebremst in die Liquidation.

- **Die Einheit ist der Fehler, nicht der Wert.** 0,72 % Abstand sieht bei einer
  Aktie vernuenftig aus und ist bei einem Wert mit 12 % Tagesspanne Rauschen. Regel:
  Tiefe >= 3 x ATR, Abstand 0,15-0,5 x ATR und nie unter 2,5 %.
- **Der Engpass sind die Stufen, nicht die Tiefe.** `maxSafetyOrds` deckelt, was
  ueberhaupt erreichbar ist (12 Stufen a 2,5 % = 30 %). Will man mehr Tiefe, muss man
  die Stufenzahl erhoehen - die Analyse nennt die noetige Zahl.
- **Die Barriere muss unter dem letzten Tief liegen**, sonst endet die Leiter, bevor
  der Markt dort war. Die Analyse vergleicht Planboden mit dem 90-Tage-Tief.
- **Der Wochenchart des Kontrakts luegt.** XPERP-Kontrakte haben 7-26 Wochenkerzen -
  eine Trendaussage daraus ist geraten. Der Trend kommt vom Spot-Paar.
- Merksatz: **Ein Vorrat, der in einem Tag leer ist, ist kein Vorrat.**

## Eine Liquidationswand liegt hinter dem Kurs, nicht davor

Gemessen am 24.09.2026 an 100 echten Zwangsschluessen (oeffentliche OKX-Daten,
BTC, Werkzeug `Agenten/Handel/liq_wand/probe_seiten.py`):

* Die 100 Eintraege decken nur **1,8 bis 14,7 Minuten** ab, der juengste war
  0,6 bis 26 Minuten alt. Der Strom ist ein Ausschnitt der letzten Bewegung.
* In beiden Messungen waren **100 von 100 Liquidationen Longs** (fallender
  Kurs). Die Seite eines Bandes ist keine Eigenschaft des Bandes, sondern der
  Richtung des letzten Laufs: Longs sterben beim Fallen, Shorts beim Steigen.
* Das groesste Band lag **0,25 % UEBER dem Spot** und bestand ganz aus
  liquidierten Longs - die Verkaeufe sind durch das Band gelaufen, der Kurs war
  schon darunter.

Merksatz: **ein Band entsteht dort, wo der Kurs gerade war, nicht dort, wo er
hinwill.** Wer verlangt, dass die Wand VOR dem Kurs liegt, verlangt etwas, das
der Datenstrom fast nie hergibt - die Spur meldet dann "falsche Seite" und
schweigt. Richtig ist eine Toleranz hinter dem Kurs
(`hinter_dem_spot_prozent`, 0.5 %), damit der Cluster als Beschleuniger zaehlt;
die Entfernungsgrenze (`max_abstand_prozent`) bleibt der Deckel.

## Ein Schalter, der ueberall an ist, sagt nichts mehr

`handel_erlaubt` und `freigabe.erfuellt` stehen seit dem Auftrag vom
21./22.09.2026 in JEDER Spur auf true. Eine Live-Sperre, die nur diese beiden
liest, laesst `--live` durch - und eine Spur ohne Orderaufruf schreibt dann ein
Buch mit `modus=live`, das an keiner Boerse existiert (der Fehler "Buch war
Fiktion" vom 21.09. bei xperp und scanner). Die Sperre muss am **Orderweg**
haengen (`LIVE_ORDERWEG`), nicht am Schalter; liq_wand macht das seit
24.09.2026 ueber `live_gate()`.

## Ein Test darf `--live` nie fahren, sobald eine Spur freigegeben ist

`nautilus_kraken/test_handeln.py` rief `--live` auf, um die Papier-Sperre zu
zeigen. Solange `handel_erlaubt=false` stand, war das harmlos. Mit der
Freigabe vom 24.09.2026 haette derselbe Testlauf bei offenem Freigabefenster
und Guthaben **echte Orders** ausgeloest — ein Test, der Geld bewegt.
Die Suite prueft die Sperrenkette jetzt mit Attrappen (`test_sperrenkette.py`)
und sichert die Regel in einem eigenen Test.

## Tests auf die Regel stellen, nicht auf den Zustand

Zwei Tests verlangten den Textbaustein „handel_erlaubt=false" in der Vorschau.
Beim Freischalten wurden sie rot, obwohl der Code stimmte — sie froren einen
Stand ein. Richtig ist: den Wert aus der `wachen.json` lesen und pruefen, dass
die Ausgabe genau die Gruende nennt, die dort stehen (und keinen erfundenen).

## Eine Meldung ohne Geschehen ist kein Bericht (25.09.2026)

Die Zyklusmeldung der Basis schickte fuenf Zeilen, von denen keine ein Ereignis
war: zwei Spaltenueberschriften (`- Ausstiege -`), die Fortsetzungszeile einer
frisch eroeffneten Anlage (`XAU-USDT-SWAP short Stop 4318.2 …` — das Instrument
steht nur in der ersten Zeile) und dreimal derselbe Hinweis (`3 Live-Position(en)
bleiben stehen …`). Der alte Filter im Dauerlauf suchte Woerter wie `stop` und
`verkauf` und traf damit Ueberschriften und Tabellenspalten.

Zwei Regeln, an EINER Stelle im Code (`dauerlauf.ereigniszeilen`): eine gemeldete
Zeile muss ein GESCHEHEN aussprechen (Ausstieg, Eroeffnung, Notaus, Kill,
Fehlschlag) UND ihr Subjekt selbst nennen. Dazu ein Gedaechtnis je Spur: eine
Zeile, die im vorigen Zyklus schon stand, wird nicht wiederholt — sonst fuellt
eine Dauerzeile jede Meldung.

Die dreifache Zeile hatte eine eigene Ursache: die Funktion laeuft je Instrument
ueber ALLE Positionen und druckte jedes Mal. Wer in einer solchen Schleife
druckt, druckt N mal; richtig ist ein Rueckgabewert und EINE Meldung im Aufrufer.
Und: die Aenderung wirkt erst nach einem Neustart des BASIS-Laufs — nur er sendet,
die Stufenlaeufe laufen stumm mit altem Code weiter.

## Ein gemeinsames Buch braucht die Herkunft an jeder Position (25.09.2026)

Die swap-Spur fuehrt Papier und Live in EINEM Buch. Ohne `modus`-Feld an der
Position entstand eine Schleife: der Papierzweig legte eine Position an, der
naechste Live-Zyklus hielt sie fuer eine Altlast und buchte sie aus, der naechste
Papierzweig legte sie wieder an (Journal 22.-24.09.2026 dreimal, jeweils 13 bis 28
Minuten auseinander). Die Papierstrecke kam so nie an Stop oder Ziel — ihre Zahlen
taugen nicht. Die teurere Richtung waere ein Live-Ausstieg auf eine Position, die
es an der Boerse nie gab.

Deshalb: jede Position traegt `modus`; `pruefe_ausstiege()` und `flach_stellen()`
fassen nur den eigenen Zweig an; die Plaetze- und Margin-Tore zaehlen nur den
eigenen Zweig (sonst blockiert der Papierlauf den Live-Lauf); und die Bereinigung
raeumt nur noch ALTBESTAND ohne Feld. Belegt wird das im JOURNAL, spaltenweise
gelesen — Zustand und Log zeigen die Schleife nicht.

## Ein Grid ist ein Hebelgeschaeft, kein Netz (25.09.2026)

62 geschlossene OKX-Grids, vollstaendig gemessen (Methode und Zahlen:
[[okx-bot-waechter]]): Netzgewinn **+305,64**, Richtungsgewinn **-392,99**,
Gebuehren und Funding -45,64 -> **-77,01 auf 7.072,87 USDC Einsatz**. 30 Gewinner,
28 Verlierer, mittlere Lebensdauer 1,3 Tage. Lief der Markt waehrend der
Lebensdauer in Richtung des Grids, waren 82 % Gewinner; lief er dagegen, 21 %.

Merksatz: **das Netz verdient klein und zuverlaessig, die Position verliert gross
und selten.** Ein einziges lange laufendes Long-Grid (BICO, -19,3 % Markt in
1,66 Tagen) verlor -304,33 USDC - viermal der Gewinn aller 62 Grids zusammen.

Was daraus folgt: der Stop gehoert an die untere Netzkante (`slTriggerPx = minPx`),
und die **Richtung** entscheidet, nicht die Feinheit des Netzes (Hebel, Netzzahl
und Bandbreite trennten Gewinner und Verlierer messbar nicht). Die zwei
Vorzeige-Bots des Kontos waren genau deshalb erfolgreich: PUMP (+109,53) zu 96 %
aus Richtung und mit automatischem Stop, ZEC (+46,76) zu 75 % aus Oszillation -
beide im Plus gestoppt, keiner auslaufen gelassen.

## Ein Markt hat zwei Namen — und eine Sperre muss ihre Boerse nennen (25.09.2026)

**Fall 1 — `swap` handelte den falschen Kontrakt.** Jede Runde meldete
`Eroeffnen XAU-USDT-SWAP fehlgeschlagen: OKX 50124: This API Key does not have
trading permission for the market`. Der Schluessel war einwandfrei
(`/account/config`: `perm: read_only,trade`, `acctLv: 2`). Die Ursache war der
NAMENSRAUM: derselbe Markt liegt auf diesem EEA-Konto handelbar nur als
XPERP-Kontrakt (`instType=FUTURES`, `XAU-USD_UM_XPERP-310502`), nicht als
gewoehnlicher Perpetual (`instType=SWAP`). Der oeffentliche Instrumentenabruf
listet beide — **sichtbar heisst nicht handelbar**. Beleg ohne Order: die
Orderhistorie des Zwillings (93 Kontrakte, gefuellt am 24.09.2026) und
`/account/positions?instType=SWAP` = leer gegen `instType=FUTURES` = die echten
Positionen. `swap/kandidaten.handels_kontrakte()` bildet jetzt je Basiswert auf
den Zwilling ab (eine Abfrage), `handeln.anlauf()` handelt ihn, eine Reihe ohne
Zwilling faellt aus der Liste. **Regel: erst den Namensraum pruefen, dann die
Rechte — ein `50124` bei einem oeffentlich gelisteten Markt ist eine falsche
Kennung, kein toter Schluessel.**

**Fall 2 — die Sperre verschwieg, wen sie fragte.** `mosaic` meldete
`nur 0.71 EUR frei, noetig 60.00`; gelesen wurde das als OKX (dort liegen USDC),
gemeint war Kraken (EUR) — und OKX hatte ebenfalls kein Geld (0,15 USDC frei).
Die Meldung war richtig und trotzdem irrefuehrend. **Regel: der Guthaben-Grund
nennt Boerse und Waehrung, und bei mehreren Boersen in der Liste stehen die
uebrigen Gruende daneben** (`kraken: nur 0.71 EUR frei, noetig 60.00 - dazu okx:
nur 0.15 USDC frei, noetig 60.00`). Sonst sieht eine geprueft-leere Boerse wie
eine uebersprungene aus.

**Was beide Faelle verbindet:** eine Fehlermeldung der Boerse beschreibt ihren
Namensraum, nicht unsere Absicht. Wer sie deutet, bevor er die eigene Kennung
und die eigene Frage geprueft hat, baut am falschen Ende.
