---
id: 20260921-handel-lektionen
title: 'Handel — Lektionen'
tags: [handel, lektion]
created: 2026-09-21
updated: 2026-10-08
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


## Eine Zwischenlagerung muss den GEHANDELTEN Kontrakt mitnehmen (25.09.2026)

`swap` bekam am Vormittag den XPERP-Zwilling als handelbares Instrument
(`kandidaten.handels_kontrakte()`), und `handeln.anlauf()` nahm ihn auch. Am
Mittag lief dieselbe Spur trotzdem wieder in den alten Fehler: die Vorschau
zeigte `XAU-USDT-SWAP` statt `XAU-USD_UM_XPERP-310502`.

Der Grund stand zwischen den beiden Stellen. `rangliste()` lagert den
Kennzahlenstand bis zu **zwei Stunden** in `zustand.json` zwischen und schrieb
dabei nur die *schlanken* Felder (Punkte, Vola, Umsatz) — der Zwilling
(`handels_instId`, `handels_instr`) fiel heraus. Damit griff in jedem Zyklus
innerhalb der Gueltigkeit der Rueckfall in `anlauf()`:

```python
instr = kandidat.get("handels_instr") or okxf.instrument(kandidat["instId"])
```

und der loeste den **Reihennamen** auf, also genau den Markt, den OKX mit `50124
does not have trading permission for the market` abweist. Der Fix wirkte so nur
auf den ersten Lauf nach dem Schreiben einer frischen Rangliste.

**Regel: ein Zwischenlager ist ein Vertrag.** Wer ein Ergebnis weglegt und
spaeter wieder einliest, muss ALLE Felder mitnehmen, die der Verbraucher
braucht — nicht nur die, die im Kopf der Anzeige stehen. Und die Gegenprobe
gehoert dazu: den Verbraucher mit einem Stand aus der DATEI fahren, nicht mit
einem frisch gebauten Dict im Speicher. Ein Test, der `anlauf()` mit
`handels_instr` direkt aufruft, war gruen, waehrend die laufende Spur den
falschen Markt handelte.

Zwei Sicherungen, die aus demselben Grund dazugehoeren:

- **Ein Stand aus altem Schema wird verworfen, nicht akzeptiert.** Fehlt in
  einer zwischengelagerten Zeile das neue Feld, wird neu geholt — sonst
  schleppt der alte Stand den Fehler bis zum Ablauf mit.
- **Der Rueckfall darf nie auf den unbrauchbaren Wert zeigen.** `anlauf()`
  holt sich den Zwilling notfalls frisch aus der Tabelle des Boersenzugs; gibt
  es keinen, entsteht KEIN Vorschlag (`kein XPERP-Zwilling, kein Anlauf`)
  statt einer Order, die nur abgewiesen wird.

## Eine Papier-Position blockiert den Live-Platz (25.09.2026)

Drei Spuren handeln auf Kraken und fuehren Papier und Live in EINEM Buch
(`kraken`, `nautilus_kraken`, `mosaic`). Eine Papier-Position ohne Order belegt
darin einen Platz — bei `max_offene_positionen 4` sind dann alle vier weg.

Gemessener Stand an diesem Tag:

| Spur | Papier | Plaetze | Wirkung |
|---|---|---|---|
| `kraken` | 4 | 4 | kein Neukauf moeglich |
| `nautilus_kraken` | 4 | 4 | **armiert** (handel_erlaubt/freigabe true), jeder Live-Zyklus lief in "Buch voll" — die Spur hatte die Aufraeumfunktion GAR NICHT |
| `mosaic` | 1 | 5 live | ein Live-Platz dauerhaft weg |
| `moondev_marktlage` | 1 | 1 | **nicht betroffen** — eigener Live-Zustand (`zustand.live.json`) |

**Regel: wer Papier und Live in einem Buch fuehrt, raeumt am ANFANG jedes
Live-Laufs die Positionen ohne echte Order aus** (Papier-Verkauf, Grund
`buchbereinigung`) — und zwar VOR der Stelle, die die Plaetze zaehlt
(`sammle_quoten` bzw. `live_einstiege`). Dahinter waere die Bereinigung fuer
diesen Zyklus wirkungslos.

Was man dabei falsch machen kann:

- **Den Live-Zustand nicht mit dem Papierzustand verwechseln.** Vor dem
  Aufraeumen pruefen, WER mit WEM dasselbe Buch teilt: `moondev_marktlage`
  fuehrt zwei Dateien, dort blockiert nichts.
- **Den Marker der Spur nehmen, nicht einen erfundenen.** `kraken` erkennt
  Altbestand an fehlendem `kauf_txid`, `nautilus_kraken`/`mosaic` an
  `modus != live`. Eine Position MIT Order (txid/ord_id) ist Bestand und bleibt.
- **Ohne Kurs wird nicht gebucht** — die Position bleibt stehen und wird
  gemeldet; lieber ein belegter Platz als eine Buchung ohne Preis.
- **Der Papierzweig fuellt die Plaetze im naechsten Zyklus wieder** (Signale
  der Kopier-Spur). Die Einmal-Bereinigung wirkt nur bis dahin; der dauerhafte
  Fix ist der Aufraeumschritt im Live-Lauf.
- **Nach dem Aufraeumen bleibt oft nur das Geld als Sperre** (Kraken-EUR frei
  0,71 EUR gegen `mindest_guthaben_eur` 60 bzw. 1,00). Das ist die ehrliche
  Lage — nicht die Papierposition war der letzte Grund.

Werkzeug: `Agenten/Handel/papierbuch_schliessen.py` (Vorschau Standard,
`--anwenden`, `--spur <name>`), ruft die Funktion DER SPUR, spiegelt nach Q:
und fasst keine Zustandsdatei an, die juenger als 300 s ist. Interpreter je
Spur beachten (`nautilus_kraken` im `nautilus/.venv`).

## Eine getrennte Rechnung ist noch keine getrennte Anzeige (25.09.2026)

**Regel.** Wenn eine Auswertung zwei Klassen trennt, muss die Anzeige BEIDE
nennen. Eine Zahl, die nur die eine Haelfte zeigt, ist keine gekuerzte Wahrheit,
sondern eine falsche Aussage — der Leser fuellt die Luecke mit dem guenstigsten
Fall.

**Belegter Fall.** Der Tagesbericht nennt fuer den scanner „7 Tage: 83 Runden,
+1801.08 USD, **Treffer 100 %**", direkt daneben „Ruecklauf 0.00 USD", waehrend
dieselbe Spur fünf offene Positionen fuehrt. Die Rechnung stimmte: `kennzahlen()`
nimmt seit dem 15.09.2026 alles heraus, was keine Handelsentscheidung ist
(`stoerungen.ist_stoerung`: herzschlag/zwangsschluss/notaus + buchbereinigung)
und weist es separat aus (`n_stoerung`, `stoerung_ergebnis`). Nachgezaehlt im
selben Fenster: **101 Runden, 99 Gewinner, 2 Verlierer** (beide
`grund=buchbereinigung`, −1,51 und −2,91 USD) → echte Trefferquote **97,9 %**.
Nur die Zeile nannte `n`/`treffer` und schwieg ueber die 18 daneben.

**Fix.** Die Zeile ist aus `_baue` herausgeloest (`tagesbericht.rundenzeile(s)`,
gleiches Muster wie `livezeile()` — eine Zeile, eine Funktion, eine Regel im
Test) und traegt den Zusatz:

`7 Tage: 83 Runden, +1801.08 USD, Treffer 100% | +18 Ausstiege ohne
Handelsentscheidung (+210.14 USD, nicht in der Quote)`

**Merksatz.** Eine korrekte Trennung im Rechenweg ist kein Schutz gegen eine
irrefuehrende Anzeige. Beim Pruefen einer Kennzahl zwei Fragen stellen: rechnet
sie richtig — UND nennt sie, was sie weggelassen hat? Die zweite Frage hat in
diesem Fall 1,5 Stunden gekostet, nicht die erste.

**Offen.** `anpassen` und `buch_nachgezogen_boerse` (Mengenabgleich des Buchs,
22.09.2026) zaehlen weiter als Runde, weil `stoerungen.BUCHHALTUNG` nur
`buchbereinigung` kennt. Sie liegen im Ergebnis nahe null; wer sie ebenfalls
herausnehmen will, aendert die Definition fuer ALLE Spuren.

Tests: `Agenten/Handel/tests/test_tagesbericht_rundenzeile.py` (8).

## Eine Position ausserhalb des Plans wird nie wieder angesehen (29.09.2026)

**Anlass.** Max: *"journal fuer IV_waelle bauen, andere journale ueberpruefen -
viele haben 0 runden, da stimmt doch etwas nicht. So verbessert sich das ganze
ja nicht."* Er hatte recht, und es war kein Rechenfehler der Auswertung.

**Befund.** Vier Indikatorspuren (macd_mtf, squeeze, wavetrend, supertrend)
prueften ihre Ausstiege ueber `w["instrumente"]`. Als die Wachen am 21.09.2026
von USDT- auf **USDC**-Paare umgestellt wurden (Commit ee647d5), lagen die
offenen Positionen noch auf `ETH-USDT`/`SOL-USDT`/`BTC-USDT`. Diese Instrumente
standen nicht mehr in der Liste - sie wurden also **nie wieder geprueft**, nie
geschlossen, und belegten alle Plaetze. Folge: kein Neuzugang, das Journal fror
ein (letzte Eintraege 20./21.09.), die Auswertung meldete "keine geschlossene
Runde". Eine Umstellung des Plans ist eine stille Loeschung des Ausstiegs.

**Fix.** Die Frage "wer wird geprueft" steht jetzt an EINER Stelle
(`scanner/wachen_pruefung.pruef_instrumente`: erst der Plan, dann die
**verwaisten** Instrumente aus `zustand["positionen"]`). Der **Einstieg** bleibt
auf den Plan begrenzt (`if inst in plan:`) - sonst handelt die Spur auf einem
Instrument, das sie nicht mehr fuehren soll. Verwaiste Instrumente werden
gemeldet. Nachweis: squeeze schloss im naechsten Zyklus zwei SOL-USDT-Positionen
am Stop (`verkauf`, grund `stop`) - die erste Journalzeile seit acht Tagen.

**Merksatz.** Wer ein Instrument aus dem Plan nimmt, muss sagen, was mit den
offenen Positionen darauf passiert. Zwei Listen sind noetig und duerfen sich
nicht verdecken: **pruefen** (Plan + Bestand) und **einsteigen** (nur Plan).

Tests: `Agenten/Handel/tests/test_verwaiste_instrumente.py` (9, Regel-Test auf
den Quelltext) + die vier Spuren-Suiten.

## Ein Tor, das kein Messfeld hat, ist kein Tor (29.09.2026)

**Befund.** `iv_waelle` hatte seit dem 19.09.2026 kein einziges Geschaeft - und
deshalb kein Journal. Gemessen mit der eigenen Sonde (29.09.2026, echte
Deribit-Kette): BTC 83.467, Tagesbasis 84.470, Tagessigma 1.765. Call-Wand
90.000 = **3,13 Sigma** (7,8 % weg), Put-Wand 60.000 = **13,9 Sigma** (28 % weg).
Das Tor verlangt eine Wand hoechstens **0,5 %** neben dem Kurs und im Band
Grenze..3 Sigma. OI-Waende sitzen an runden Zahlen (80.000/90.000/100.000), die
Tagesspanne ist wenige Prozent breit - der geforderte Abstand ist ein Vielfaches
des Moeglichen. Das Tor konnte nie aufgehen, und weil es nie aufging, hat es
auch nie jemand gemessen.

**Was daraus folgt.** Nicht die Spur abschalten und nicht das Tor aufweichen,
sondern den **gemessenen** Weg einbauen: der Fade an der Spannengrenze
(`signal_an_der_spanne`, k=1,0 / Stop 0,5 Sigma / Ziel halber Rueckweg zur
Tagesmitte) ist ueber 400 Tage gemessen - **+0,276 % je Runde**, 204 von 400
Tagen mit Signal, beide Haelften und beide Seiten positiv. Der ungemessene
Wandweg bleibt erster Weg (er hat Vorrang, wenn er greift), der gemessene
Spannenweg ist der zweite. Jede Position traegt ihren `ausloeser`
(`wand`/`spanne`), sonst waere ein Gewinn dem falschen Weg zugeschrieben.

**Merksatz.** Eine Spur mit 0 Runden nach Tagen ist ein Befund, kein Zufall:
dann gehoert gemessen, wie weit der Kurs vom Tor entfernt ist (eigene Sonde,
echte Daten) - nicht der Schalter umgelegt.

Tests: `Agenten/Handel/iv_waelle/tests/test_spanne_weg.py` (16, mit einem vollen
Papierzyklus in einen Temp-Ordner: Journal entsteht, Runde wird zaehlbar).

## Die Zeile muss sagen, WELCHE Null sie meint (29.09.2026)

**Anlass.** Dieselbe Beschwerde wie oben, andere Haelfte: "viele haben 0
runden". Fuer **drei** verschiedene Lagen stand derselbe Satz in der Auswertung:
"keine geschlossenen Runden im Journal".

**Befund.** Am 29.09.2026 gleichzeitig im Bestand: `macd_mtf` und `supertrend`
mit je vier **offenen Positionen** (die Spur arbeitet, ihr Stop ist nur noch
nicht erreicht), `nautilus_kraken` mit vier **Ausbuechern**
(`buchbereinigung` - keine Handelsrunde, aber auch kein leeres Journal),
`iv_waelle` mit einem **leeren** Journal (wartet auf das erste Signal) und
`robinhood_radar` mit einem Journal, das noch nie etwas gesehen hat. Wer liest
"keine geschlossene Runde", kann diese vier Faelle nicht unterscheiden - und
sucht an einem Fehler, der keiner ist.

**Fix.** `auswertung_alle.offene_positionen(spur)` liest `zustand.json`
(tolerant: fehlende Datei, kaputtes JSON und fehlendes `positionen`-Feld geben
`None`) und `zeige()` nennt die Lage im Klartext: "aber 4 offene Position(en) im
Buch - die Spur arbeitet, Stop/Ziel ist noch nicht erreicht." / "daneben 4
Ausstiege ohne Handelsentscheidung (Buchhaltung/Zwang)" / "wartet auf ihr erstes
Signal".

**Merksatz.** Eine Null ist erst dann eine Aussage, wenn dabeisteht, was sie
zaehlt. Beim Bauen einer Kennzahl die Gegenfrage stellen: welche Zustaende
fallen alle auf denselben Text?

Tests: `Agenten/Handel/tests/test_auswertung_offene_positionen.py` (9).

## Ein Test gegen die Quelltextzeile meldet Umbauten, keine Fehler (29.09.2026)

`tests/test_indikator_auswertung.py` prueft `inspect.getsource(kennzahlen_fuer)`
darauf, dass die Zuordnung Spur -> Rechenweg dort steht. Am 29.09.2026 wurde
diese Zuordnung nach `runden_fuer()` verlagert (eine Stelle fuer beide Aufrufer,
`kennzahlen_fuer` ruft sie jetzt) - der Test wurde rot, ohne dass sich am
Verhalten etwas geaendert hatte. Er prueft die Regel jetzt so, wie sie gelten
soll: die Zuordnung steht in `runden_fuer`, und `kennzahlen_fuer` benutzt sie.
Merksatz: pruefe die Eigenschaft, nicht die Zeile, in der sie gerade steht.

## Ein Stop, den die Boerse storniert, verschwindet still (30.09.2026)

Drei Live-Positionen von `mosaic` auf Kraken (BTC, ETH, SOL, zusammen rund
258 EUR) standen am 30.09.2026 ohne Notausstieg an der Boerse: die drei
Stop-Loss-Auftraege trugen bei Kraken den Status `canceled`, waehrend das Buch
weiter `boersen_stop_fehlt: false` meldete und die Kennungen
(`O6WWXX-N5HKS-LYTO7N`, `OSCAY5-JB4KW-LTRGMW`, `OBY2UV-FGFGC-UEAFDK`) fuehrte.
Gefunden wurde es nur, weil `kraken/spot_stops.py` die Bestaende gegen die
offenen Orders haelt - **nicht** durch einen Waechter der Spur.

Dasselbe Muster wie am 26.09.2026 (xperp, vier Stops). Zwei Lehren:

1. **Eine Order-Kennung im Buch beweist nichts.** `order_details(txid)` fragen
   und auf `status == "open"` pruefen. `boersen_stop_fehlt: false` heisst nur:
   beim Einstieg wurde ein Stop bestellt.
2. **Jede Spur mit Boersen-Stop braucht den Abgleich, den der scanner hat.**
   `scanner/boersenstops.py` laeuft seit 28.09. im Live-Zyklus; mosaic, kraken
   und die Nautilus-Arme haben ihn nicht. Ein Stop, den niemand nachprueft, ist
   eine Annahme, kein Schutz.

Nachgetragen am selben Tag: die drei Stops neu gesetzt (`OL2N6C-OIVXN-EY43U6`,
`OJHLDO-QUBRE-HNPCA5`, `O5CFAP-FQD2X-J3ELGS`), Buch nachgezogen. Der Grund der
Stornierung ist weiter offen.

## Kraken gehoert ab 30.09.2026 omnitrade allein (30.09.2026)

Auftrag Max: *"nur noch omnitrade auf kraken handel erlaubt"*. Umgesetzt:
`kraken` und `moondev_marktlage` auf `handel_erlaubt=false` +
`freigabe.erfuellt=false`, `mosaic` auf `boersen: ["okx"]` gekuerzt (OKX bleibt),
alle vier Kraken-Spuren aus `dauerlauf.AUTO_FREIGABE` entfernt.

Zwei Dinge, die daran haengen und leicht untergehen:

* **Der Entzug trifft das Kapital, nicht die Positionen.** Die sieben offenen
  Kraken-Positionen bleiben stehen; geschuetzt sind sie nur noch durch ihre
  Boersen-Stops. Wer eine Spur abschaltet, muss vorher pruefen, dass die Stops
  liegen - sonst schaltet er den Waechter ab, der die Position ohnehin nicht
  mehr bewacht haette.
* **`handel_erlaubt=false` wirkt sofort, `AUTO_FREIGABE` erst nach einem
  Neustart des Dauerlaufs.** Weil die Sperrliste dieser Spuren jetzt mehrere
  Gruende nennt, oeffnet die Auto-Freigabe ohnehin kein Fenster mehr
  (`nur_fenster_fehlt` verlangt GENAU einen Grund).

## Quantpedia: die Zahlen der Paper sind keine Handelszahlen (30.09.2026)

**Regel.** Eine fremde Strategie wird erst geglaubt, wenn sie auf den EIGENEN
Kerzen mit den EIGENEN Gebuehren nachgerechnet ist. Bei kurzen Haltedauern
entscheidet die Gebuehr, nicht die Guete des Signals — die Kosten wachsen mit
der Rundenzahl, der Ertrag nicht.

**Ausgangslage.** Quantpedia hat genau ZWEI freie Krypto-Strategien (#0701
Rebalancing Premium in Cryptocurrencies, #0753 Overnight Seasonality in Bitcoin);
alles andere Krypto ist Premium. Und der Paperwert ist nicht der Handelswert:
zu #0701 liefert die mitgelieferte QuantConnect-Gegenprobe Sharpe -0,5,
CAGR -18,76 %, Rueckgang 63 % gegen 7,65 % im Paper.

**Nachgerechnet (#0753, Binance BTC 1H 2021-01..2026-09, 50.223 Kerzen).** Die
Richtung stimmt: die UTC-Stunden 21 und 22 sind auch bei uns die staerksten
(t +2,45 / +2,13; je Stunde hochgerechnet +12,9 % / +10,5 % p.a.).

Die handelbare Regel traegt trotzdem nicht:

| Fenster (UTC) | Mittel/Tag | brutto p.a. | 0,05 %/Seite | 0,6 %/Seite (Kraken) |
|---|---|---|---|---|
| 21:00 -> 23:00 (Blog-Fassung) | +0,014 % | +3,7 % | -28,0 % | -98,7 % |
| 22:00 -> 23:00 (Original) | -0,014 % | -5,5 % | -34,5 % | -98,9 % |
| 21:00 -> 22:00 (bestes) | +0,027 % | +9,8 % | -23,8 % | -98,6 % |

Ursache: rund 0,03 % Kante je Tag gegen mindestens 0,1 % Rundlauf. Der Befund
ist stabil ueber beide Haelften (t +1,40 / +1,69) — es fehlt nicht die Datenmenge,
es fehlt die Groesse.

**Die eine Familie, die unsere Gebuehren ueberlebt** ist der Tagesausbruch
(Donchian) auf BTC 1D, netto 0,1 %/Seite:

| Variante | Signale/Jahr | netto p.a. | max. Rueckgang | Tage im Markt |
|---|---|---|---|---|
| Donchian(20) | 6,3 | +15,0 % | -56 % | 52 % |
| Donchian(30) | 3,9 | +17,8 % | -43 % | 54 % |
| Buy & Hold | — | +20,2 % | -77 % | 100 % |
| MAX(10), 1 Tag Halten | 65,7 | -6,0 % | — | — |

Das ist **keine hoehere Rendite, sondern ein halbierter Rueckgang** (Calmar
0,41 gegen 0,26) — und mit t = 1,25 bei 34 Runden ein Kandidat, kein Beweis.

**Nachrechnen** (aus `Agenten/Handel`, Daten aus `daten/historie/`):

```
.venv/Scripts/python.exe quantpedia_probe.py stunde
.venv/Scripts/python.exe quantpedia_probe.py fenster 21 22
.venv/Scripts/python.exe quantpedia_probe.py donchian
.venv/Scripts/python.exe quantpedia_probe.py vergleich
```

## TSMOM (#0118) auf eigenen Kerzen: ein Kandidat, aber BTC-only (01.10.2026)

**Regel (T-210).** Der zweite Quantpedia-Kandidat, Time Series Momentum
(#0118, 12-Monats-Rendite je Instrument, Positionsgroesse invers zur
Volatilitaet, monatliche Neuverteilung), ist jetzt auf den EIGENEN 1D-Kerzen
nachgerechnet. Zwei Massstaebe entscheiden, ob eine fremde Strategie Haus-Tauglich
ist: die Gebuehr (monatliche Neuverteilung = 2 Seiten pro Monat = ~24 Seiten/Jahr)
und der Rueckgang gegen Buy & Hold.

**Messung (tsmom_probe.py, BTC/ETH/SOL 1D 2021-01..2026-09, 56 Monate):**

| Instrument | Mittel/Monat | Treffer | t-Stat | Sharpe p.a. | brutto p.a. | max. Rueckgang | 0,1 %/Seite |
|---|---|---|---|---|---|---|---|
| BTC | +1,05 % | 34 % | +1,68 | +0,78 | +12,3 % | -14 % | +9,5 % |
| ETH | +0,32 % | 25 % | +0,58 | +0,27 | +3,0 % | -15 % | +0,5 % |
| SOL | +0,42 % | 29 % | +0,74 | +0,34 | +4,2 % | -22 % | +1,6 % |
| Buy & Hold BTC | — | — | — | — | +20,2 % | -77 % | — |

**Lesart.** TSMOM auf BTC ist der dritte Kandidat, der unsere Gebuehren
ueberlebt: netto 0,1 %/Seite noch +9,5 % p.a., und der Rueckgang ist mit -14 %
gegen -77 % Buy & Hold drastisch kleiner (Calmar 0,68 gegen 0,26 — besser als
Donchian(30) mit 0,41). Aber das Signal lebt NUR von BTC: ETH und SOL sind
netto 0,1 %/Seite praktisch Null (t +0,58/+0,74, 25 %/29 % Treffer). Eine
TSMOM-Papierspur waere also eine BTC-Strategie mit Monats-Rhythmus — kein
Portfolio. Die QuantConnect-Gegenprobe im Paper (Sharpe 0,3 / CAGR 7,29 %) wird
von BTC (0,78 / 12,3 %) uebertroffen, von ETH/SOL nicht erreicht — konsistent.

**QQQ/BTC-Rotation (T-210, zweiter Teil):** nicht messbar. Die Blog-Studie
('Tactical Asset Rotation Between NASDAQ-100 and Bitcoin') braucht QQQ-Tageskerzen
2019..2026; im feed liegen nur 92 Kerzen ab 2026-06-30 (QQQBUSDT_1D.json). Ohne
QQQ-Historie bleibt die Rotation eine Datenluecke, kein Messergebnis.

**Nachrechnen** (aus `Agenten/Handel`, Daten aus `daten/historie/feed/`):

```
.venv/Scripts/python.exe tsmom_probe.py tsmom
.venv/Scripts/python.exe tsmom_probe.py qqq
.venv/Scripts/python.exe tsmom_probe.py vergleich
```

## Ein Buch, das der Boerse widerspricht, ist keine Position (30.09.2026)

**Regel.** Was die Boerse weiss, weiss das Buch nicht von selbst. Jede Spur, die
ihren Bestand selbst fuehrt, braucht einen Abgleich gegen die Boerse - und zwar
im Zyklus, nicht auf Zuruf. Ein Nachweis, den niemand aufruft, ist keine Wache.

**Der Fall.** `kraken/zustand.json` fuehrte DOTEUR mit 45,9896983 DOT. Am Konto
lagen 0,0000000000 DOT: der Stop O2YTEL-7R6ZT-ULOXRN hatte die Position am
29.09. um 01:36 verkauft (45,99 DOT, 46,16 EUR brutto, 45,89 EUR nach Gebuehr).
Die Spur merkte es nicht, weil `pruefe_ausstiege` Stop und Ziel nur gegen den
LEBENDEN Kurs prueft - steigt der Kurs nach dem Ausloesen wieder ueber den Stop,
sieht niemand mehr hin. Der Geist stand zwei Tage im Buch und rechnete in
Ratsche, Ruecklauf und Auswertung mit.

**Zweiter Befund derselben Pruefung.** Zwei SUIEUR-Auftraege sahen wie Waisen
aus (Spot-Guthaben 0 SUI), waren aber gedeckt: 274,64 SUI lagen in vier
MARGIN-Positionen. Ursache war ein Fehler in `waisen_stops.lage()`: es las
`OpenPositions` als `{...}.get("open")`, waehrend Kraken die Positionen OHNE
diese Huelle liefert (`OpenOrders` hat sie). Ergebnis: die Funktion sah NIE eine
Position und hielt jeden Schutzauftrag fuer eine Waise. Ein Guthaben von 0 heisst
nicht, dass keine Position da ist - Margin zaehlt zum Bestand.

**Dritter Befund.** `beleg_hand.py` schrieb als Einsatz den STUECKPREIS
(`eintrag["preis_max"]`) statt des Betrags. Vier ueber die Hand ausgefuehrte
Belege standen deshalb mit 0,21 / 0,95 / 1,15 / 1,61 EUR im Journal, gemeint
waren je ~50 EUR. `eingesetzt` war um Faktor 30 zu klein, jede dieser Runden
haette einen Scheingewinn von ~+49 EUR gezeigt, und der Gesamtdeckel konnte nie
binden. Der Einsatz ist GELD: Menge x Kurs.

**Was den Geist erkennt.** `kraken/abgleich.py` liest Bestand (BalanceEx),
Margin-Positionen und offene Auftraege und vergleicht sie mit dem Buch:
GEIST (Position im Buch, an der Boerse nicht mehr da), TEILS (nur ein Rest da),
WAISE (Schutzauftrag ohne Bestand). Ausgebucht wird nur mit einem ECHTEN
Boersenerloes (ClosedOrders der Stop-Order, sonst Ledger mit Gegenbuchung) -
ohne Zeugen bleibt die Position stehen und der Befund heisst "unklar". Der
Abgleich laeuft im Zyklus VOR den Ausstiegen; eine zweite Ausbuchungszeile
verhindert `schon_gebucht()`.

**Nachrechnen** (aus `Agenten/Handel/kraken`):

```
../.venv/Scripts/python.exe abgleich.py              # Vorschau
../.venv/Scripts/python.exe abgleich.py --anwenden   # ausbuchen
../.venv/Scripts/python.exe einsatz_nachziehen.py    # Einsatzpruefung
../.venv/Scripts/python.exe waisen_stops.py          # Schutzauftraege
```

## Lektion: paare je POSITION, nicht je Instrument (T-095, 30.09.2026)

Ein Dict `offen[inst]` als Zuordnung von Einstieg zu Ausstieg ist ein
stiller Verlust: zwei gleichzeitige Positionen im selben Instrument
ueberschreiben einander, der ueberschriebene Einstieg ist weg und seine
Ausstiegszeile findet keinen Partner. Gemessen kostete das im Backtest
ueber 5,7 Jahre 30 % der Runden (squeeze 759 statt 1088, macd_mtf 774 statt
1209, wavetrend 1128 statt 1506; ueber alle Journale 23.999 statt 29.414).
Und der Verlust ist nicht zufaellig - gleichzeitige Positionen im selben
Instrument sind eher gleichgerichtet, die ausgewertete Teilmenge also
schoen gerechnet.

Die Zuordnung gehoert EINMAL ins Haus (`journalpaarung.py`), nicht je
Auswertung neu. Sie braucht eine Kennung in der Zeile (`pos_id`), und der
Rueckfall auf den Altbestand darf NICHT raten: mehrere offene Einstiege ohne
Kennung werden ueber die kopierten Positionsmerkmale gepaart, und was
zweideutig bleibt, wird als unpaarig GEZAEHLT und ausgewiesen. Weniger Runden
sind dort die ehrlichere Zahl - `scanner` 167 -> 156, `swap` 14 -> 11,
`xperp` 77 -> 71.

Drei Fallen beim Einbau:

1. **Der Kopf der DATEI entscheidet, nicht die Liste im Code.** Ein
   `csv.DictWriter` mit `fieldnames=SPALTEN` schreibt positionell: in einem
   Altjournal ohne die neue Spalte wandert jeder Wert einen Platz nach links.
   Richtig ist `pos_kennung.spalten(JOURNAL, SPALTEN)` - ein Feld ohne Spalte
   wird verworfen (`extrasaction="ignore"`) statt verschoben.
2. **Ein stiller Rueckfall sieht aus wie ein Erfolg.** Ein Journal ohne
   `pos_id` meldet sich darum einmalig auf stderr, und die Auswertung fuehrt
   `ohne_kennung`/`zweideutig` im Stand mit.
3. **Ein Test, der eine Spaltenzahl oder eine feste Anzahl einfriert, meldet
   Aenderung statt Fehler.** Nach dem Anbau der Spalte mussten zwei
   Zeilentests angefasst werden (scanner: 12 -> 13 Spalten; omniquant: ein
   festes Datum im Fixture wurde zur Zeitbombe, jetzt relativ zu `jetzt`).

**Nachrechnen:**

```
.venv/Scripts/python.exe journal_pos_id_nachziehen.py            # Vorschau
.venv/Scripts/python.exe journal_pos_id_nachziehen.py --anwenden # nachziehen
python Agenten/Hermes/cache/scratch/gegenprobe_alt_neu.py        # alt vs. neu

```

## Eine stillgelegte Spur kurz wieder anzuschalten wickelt ihre alten Positionen ab

**Befund (01.10.2026, Spiegel-Arme):** Die drei Arme standen seit dem 21.09.
still, ihre Buecher trugen je 60 offene Papierpositionen (10 Tage alt). Auftrag
war, sie "zumindest auf Papier" wieder laufen zu lassen - also wurden die
Eintraege in `dauerlauf.SPUREN` aktiviert UND vorher `letzter_lauf` in allen
`zustand*.json` auf jetzt gesetzt (ohne das haette der erste Zyklus alles als
`herzschlag_alt` flachgestellt). Sechs Minuten spaeter kam "spiegel komplett raus".

**Was in diesen sechs Minuten passierte:** Ein Zyklus hat die 10 Tage alten
Positionen an ihren Stops und Zielen abgewickelt (66 neue Journalzeilen) und
NEUE eroeffnet. Danach standen 6/3/3 statt 60/60/60 im Buch - und diese neuen
Positionen konnte niemand mehr schliessen, weil die Arme wieder aus waren.

**Regel:** Das ALTER der Positionen gehoert zur Entscheidung. Wer eine
stillgelegte Spur wieder anschaltet, muss mit einem Schlag rechnen: alte
Positionen werden gegen die inzwischen gelaufenen Kurse abgewickelt, nicht gegen
den Stand vom Stilllegungstag. Ist die Spur nur zum Nachsehen gedacht, gehoert
sie gar nicht in `SPUREN`.

**Rueckweg-Werkzeug:** `spiegel/buecher_aufloesen.py` traegt offene Karteileichen
aus (Trockenlauf Standard, `--anwenden` schreibt): je Position eine Journalzeile
`schliessen / buchbereinigung` mit dem EINSTIEGSPREIS - neutral, damit die
Bereinigung die Bilanz nicht veraendert.

## Brutto und netto gehoeren nicht in dieselbe Summe (01.10.2026)

**Befund (T-192):** Die Live-Spuren rechnen ihre Gebuehr im Journal ein
(scanner/kraken im Betrag der Ausstiegszeile, xperp/swap ueber
`gebuehr_pct`/`funding_pct`), die Papierbuecher nicht. Beide standen im Bericht
unter derselben Zeile, und bei den Papierbuechern stand "Kosten 0.00 %" - eine
Zahl, die nicht gemessen, sondern nur nicht vorhanden war. Dazu fuehren orb und
orbk ein PUNKTE-Buch: `gv_usd` ist die Kursstrecke mal `punkt_wert_usd` (1:1),
also der Gewinn JE EINHEIT. Ohne Einsatz gibt es keinen Prozentwert - die Zeile
zeigte trotzdem "(+0.00 %)".

**Regel 1 - eine Auswertung sagt, was ihre Zahl bedeutet.**
`kennzahlen()` liefert `brutto`/`gebuehr`/`kosten_netto`/`netto`/`netto_pct`, die
Zeile "Brutto/Netto" nennt den Satz und die Nettosumme. `GEBUEHR_SCHON_DRIN`
(xperp/swap/scanner/kraken) verhindert das ZWEIMALIGE Abziehen - zweimal abziehen
ist so falsch wie gar nicht. Steht keine Gebuehr in der wachen.json, heisst es
"BRUTTO und UNBEKANNT" und nicht "0.00 %". Gemessen aendert das Urteile:
mosaic +10.82 -> +9.62 USD, moondev_marktlage -5.02 -> -6.02,
moondev_signalwelle +38.85 -> +37.92, iv_wand +2.30 -> +2.00.

**Regel 2 - fuer ein Buch ohne Einsatz gehoert ein groessenunabhaengiges Mass
daneben, kein erfundenes Nominal.** `runden_orbk` rechnet
`gv / |einstieg - stop|` (Ergebnis in R). Das ergab die erste ehrliche Zahl
dieser beiden Spuren: orbk +2.18 R, orb -0.46 R - und die Einheit heisst jetzt
"Punkte" statt "USD". Ein Einsatz aus `risiko_pro_trade / stop_abstand` (SPEC.md)
waere bei der Range-Hoehe als Stop ein Nominal von einigen tausend USD: eine
Design-Entscheidung, keine Reparatur.

**Nebenbei gefunden:** `orb` fehlte in der Auswertung ganz (nur `orbk` stand in
`SPUREN`); 18 von 41 Spuren haben noch keine Gebuehr (T-264).

## Eine vierte Abgleichsstufe: die Deckung, nicht die Existenz (05.10.2026)

**Regel: „ein Stop liegt an der Boerse" ist keine Aussage ueber die MENGE.**
Bis zum 05.10.2026 pruefte der Abgleich drei Dinge: gibt es die Position, stimmt
die Kontraktzahl, ist die gemerkte Stop-Kennung an der Boerse wirksam. Die
vierte Frage — **wie viel** ist gedeckt — fehlte, und genau dort lag der Befund.

Gemessen am echten Konto (xperp zuerst, danach mosaic): BTC-USDC Buch
0,00065270, Stop an der Boerse 0,00064984. Die Luecke 2,86e-06 (rund 0,20 EUR
bei 70.047 EUR/Stueck) laeuft bis zur Liquidation: der Stop war wirksam, die
Position nicht. ETH-USDC 3,9e-07, SOL-USDC gedeckt.

**Die Paarauflosung fand nichts (der zweite, zuerst unsichtbare Befund).**
Kraken fuehrt dasselbe Paar in zwei Schreibweisen: `AssetPairs` nennt
`XXBTZEUR`, `OpenOrders` nennt `XBTEUR`. Ein Lookup auf den Paarnamen liefert
`base=None` und damit NULL Treffer — was sich wie „kein Stop an der Boerse"
liest. Vor der Korrektur zeigten BTC und ETH je **0 Stops**, obwohl je einer
lag.

Merksatz: **wenn eine Abfrage ALLES leer liefert, ist die Abfrage der Befund,
nicht der Bestand.** Die Aufloesung gehoert an EINE Stelle
(`spot_stops.muenze_aus_paar()`), eine eigene Regel im Abgleich waere die
dritte Fassung derselben Wahrheit. Und sie ist nicht vollstaendig: `_PRAEFIX`
fuehrt `XXBT, XBT, XETH, XXLM, XXRP, XZEC, XDG` — `XADA` bleibt `XADA`, wer die
Kurzform fuer die richtige Form haelt, bekommt bei jeder zweiten Muenze einen
leeren Befund.

**Drei Regeln, die dazugehoeren:**

1. **Die Stufe muss auch im gesunden Zweig haengen.** Die Deckungsmessung stand
   zuerst hinter `if wirksam: continue` — also genau in dem Zweig nicht, den der
   Betrieb nimmt. Eine Regel gehoert an *jeden* Weg, der dieselbe Sache
   entscheidet.
2. **Fremde Auftraege zaehlen zur Deckung und werden nie angefasst.** An Kraken
   lagen fuenf Stops auf SOL (zusammen 9,539 gegen 0,481 im Buch), vier davon
   von Nachbarspuren. Die Position gilt als gedeckt; die vier bleiben
   unberuehrt, das ist Sache von `waisen_stops`. Ein Abgleich, der fremde Stops
   anfasst, ist ein Aufraeumer mit Boersenzugriff.
3. **Ein geratener Notausstieg ist teurer als eine gemeldete Luecke.** Die
   Zyklus-Stufe liest und meldet; `stops_nachziehen.py` **stellt nichts** ohne
   `--stop`, denn ein Notausstieg ist eine Order und ein geratener Schutzpreis
   eine, die niemand bestellt hat.

**Nachweis.** Suite mosaic 158 Tests (14 neue). Gegenproben: Aufruf im gesunden
Zweig entfernt -> 2 Tests rot; Mengenvergleich vereinfacht -> 3 rot. Echter
Abgleich in der Vorschau: 3 geprueft, 3 ok, 2 ungeschuetzt, 0 unklar —
BTC 2,86e-06, ETH 3,9e-07. `spiegelstand.py` meldet `gleich`, Journal und
Zustand byte-gleich.

## Eine Erweiterung zurueckgenommen, mit Protokoll (05.10.2026)

**Regel: wenn ein Auftrag eine Zahl erhoehen soll, gehoert die Gegenprobe an
die Boerse, nicht an die Konfiguration.** Auftrag Max: „maerkte und werte
erhoehen". Erster Versuch: den Quote-Filter geloest (62 Paare statt 50 ueber
3 Mio USD Umsatz). Die 12 neuen Paare waren **alle** Fiat (TRY, BRL, EUR) und
fallen am C/R-Tor durch (0,02 bis 0,62) — ohne Fiat bleiben exakt 50. Der
Filter kostete also keinen Kandidaten; die Erweiterung haette nur Krypto-Markt
gegen ueberhitzte Wechselkurs-Paare gestellt.

Zurueckgenommen mit Protokoll in `prognose.json` unter `_maerkte` und als
Datensatz in `prognose.py` — **nicht** nur als Kommentar, weil der Fehler in die
Zahl ging. Merksatz: eine zurueckgenommene Aenderung gehoert an die Stelle, an
der die Zahl steht; wer sie nur im Kommentar begruendet, liest sie beim
naechsten Mal nur am Kommentar vorbei.
## Ein "nur Verlust"-Symptom ist meist Buchhaltung, nicht Strategie (08.10.2026)

Drei unabhaengige Mechanismen lassen Spuren "nur Verlust machen" bzw. Positionen
"oeffnen und sofort schliessen". Vor jeder Parameter-Diskussion alle drei
pruefen - der Markt ist der letzte Verdaechtige. Die vollstaendige Anleitung
steht in der Skill-Referenz `handel-spuren/references/verlust-spur-diagnose.md`.

1. **Kill/Ratsche misst gegen einen PHANTOM-Hoechststand.** Eine
   Schliessen-Zeile mit `margin_usd = NOMINAL` statt echter Marge (typisch
   `verkauf_von_hand`; Beleg 06.10.2026: drei Zeilen bauten den Hoechststand auf
   639.977 auf) blaht die kumulierte Kurve auf - der Kill feuert gegen GEWINNER,
   weil jeder kleine echte Ruecklauf gegen den Phantom-Peak misst. Fix:
   Blasenzeilen als `buchbereinigung` mit ECHTER Marge, Bahnkurve neu aufsetzen,
   Schreibstelle korrigieren (`xperp/geister_nachziehen.py`). Deckel erhoehen
   daempft nur.
2. **Geister-Ausbuchung loescht echte LIVE-Positionen.** `buchbereinigung_geist`
   (Preis = EINSTAND, modus=papier) bucht aus, was die Boerse noch fuehrt - das
   ist "geoeffnet und direkt geschlossen" in einem Zyklus. Echte Verkaeufe tragen
   `stop`/`ziel`/`limit_wartet`, nie `buchbereinigung_geist`; erst
   `/account/positions` pruefen, bevor das Buch der Boerse folgt.
3. **Buch-Stop und Boersen-Stop sind desynchron.** Das Buch fuehrt einen Stop
   (z.B. 82.800), an der Boerse liegt ein anderer (z.B. 76.061) oder nur ein
   Teil der Kontrakte ist gedeckt (gemessen: 336 Kontrakte im Buch, 2 Stops ueber
   je 261 = 75 ungeschuetzt). `_ist_handposition` (herkunft `boerse_handgriff`)
   laesst pruefe_ausstiege die Position NICHT schliessen - dort ist der
   Boersen-Stop die einzige Wahrheit.

Merksatz: `modus=live` im Journal ist ein BUCHVERMERK, kein Orderbeleg. Ein
Kill, der Gewinner schliesst, ist ein Messfehler der Kurve, kein Markturteil.
