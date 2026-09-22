---
id: 20260921-handel-lektionen
title: 'Handel — Lektionen'
tags: [handel, lektion]
created: 2026-09-21
updated: 2026-09-22
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

**Verwandt:** `mosaic` ist die einzige Spur mit einem MODUS-Waechter je Position
(`if p.get('modus') != 'live': continue`) — Papier und Live liegen dort in EINEM Buch, ohne
sich zu stoeren. `scanner` hat diesen Waechter nicht; dort war die Bereinigung noetig.

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

**Belegte Messung (22.09.2026, `Werkstatt/intelligent-trading-bot`, BTCUSDT 1 h, SVC auf
SMA/Linearreg-Slope/Stddev, Fenster 1-672):**

| Lauf | Daten | AUC Auf | AUC Ab | Handelsergebnis (beste von 100 Parameterkombinationen) |
|---|---|---|---|---|
| in-sample (`train`+`predict` auf denselben 8.672 Zeilen) | 2025-09-26 bis 2026-09-22 | **0,83** | **0,85** | **-26,3 %** |
| Walk-Forward (4 Schritte, je 3.000 h, je neu trainiert) | 2025-05-10 bis 2026-09-22 | **0,51** | **0,46** | **-5,1 %** |

Die AUC faellt von 0,83 auf 0,51 (Muenzwurf) — das Modell hatte **keinen** Vorteil, es sah nur
die Antworten. Auch der Walk-Forward-Lauf ist in ALLEN 100 Kombinationen negativ (beste:
110 Transaktionen, 43,6 % profitabel, -5,1 % vor Gebuehren). Befund: SMA/Slope/Stddev +
SVC auf BTC 1 h traegt nicht aus dem Trainingsfenster heraus.

**Die Mechanik dahinter.** `simulate` (Parameterraster ueber Kauf-/Verkaufsschwellen) liest
`signals.csv`; `predict_rolling` schreibt die Vorhersagen aus nicht gesehenen Fenstern in
dieselbe Datei. Es ist derselbe Simulator, nur mit ehrlichem Input — genau deshalb ist der
Vergleich aussagekraeftig.

**Nachweis / Werkzeug.** Der Klon kann die ganze Kette (venv Python 3.13 ist fertig, alle
noetigen Bibliotheken vorhanden; `tsfresh` und `MetaTrader5` fehlen, beide optional):

```
cd Werkstatt/intelligent-trading-bot
./.venv/Scripts/python.exe -m scripts.download -c <config.json>
./.venv/Scripts/python.exe -m scripts.merge    -c <config.json>
./.venv/Scripts/python.exe -m scripts.features -c <config.json>
./.venv/Scripts/python.exe -m scripts.labels   -c <config.json>
./.venv/Scripts/python.exe -m scripts.train    -c <config.json>
./.venv/Scripts/python.exe -m scripts.predict  -c <config.json>
./.venv/Scripts/python.exe -m scripts.predict_rolling -c <config.json>
./.venv/Scripts/python.exe -m scripts.signals  -c <config.json>
./.venv/Scripts/python.exe -m scripts.simulate -c <config.json>
```

Ergebnisse landen unter `data_folder/<symbol>/` (`predictions.txt` = AUC/AP/F1,
`signal_models.txt` = Handelsergebnis je Schwellenpaar). `train_length: 0` haelt alle Zeilen,
`algorithms[0].params.length` ist das Trainingsfenster je Schritt, `rolling_predict`
(`prediction_size`, `prediction_steps`) der Walk-Forward. Kurse kommen oeffentlich von Binance
(`api_key: "dummy"` genuegt fuers Herunterladen).

**Merksatz.** Bevor eine Spur mit ML-Kennzahlen bewertet wird, zuerst fragen: **welche Zeilen
hat das Modell beim Vorhersagen schon gesehen?** Der Klon taugt als Pruefstand fuer diese eine
Frage — er ist NICHT in den Dauerlauf eingebunden und braucht dort auch nicht hin: seine
Ordner nutzen Binance und MetaTrader 5, waehrend der eigene Handel ueber OKX und Kraken laeuft.
