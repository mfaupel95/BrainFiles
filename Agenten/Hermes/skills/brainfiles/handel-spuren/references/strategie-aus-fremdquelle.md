# Strategie aus einer Fremdquelle (Video, Reel, Post, Bild)

## Wann
Max schickt einen Clip, ein Reel, einen Screenshot oder einen Link und will
"daraus eine Strategie". Reihenfolge: Quelle auswerten -> Datenquelle
verifizieren -> Behauptung in Bausteine zerlegen -> JEDEN Baustein nachrechnen
-> Ergebnis mit der offenen Luecke melden. Eine Strategie ist erst fertig, wenn
die Zahlen aus echten Daten dahinter stehen - nicht, wenn der Code laeuft.

## 1. Quelle auswerten, Textebene zuerst
- Datei zuerst messen: `ffprobe -v error -show_entries format=duration,size
  -show_entries stream=codec_type,codec_name,width,height in.mp4`. Die
  Bildgroesse sagt, ob Zahlen ueberhaupt lesbar sein koennen (Hochkant-Handyclip
  = klein).
- Dann `video_analyze` auf die DATEI mit dem Auftrag "Transkribiere JEDEN
  sichtbaren Text und die gesprochenen Worte, zeige den Aufbau Bild fuer Bild -
  nicht zusammenfassen". Die eingeblendeten Textzeilen (Overlays) sind die
  eigentliche Spezifikation; sie kommen als Folge von Einzelwoertern zurueck und
  ergeben im Zusammenhang den Satz.
- Zahlen, Achsen und Legenden stehen oft nur klein im Bild: Frames ziehen
  (`ffmpeg -v error -i in.mp4 -vf "fps=2,scale=<2x Bildbreite>:<2x Hoehe>:
  flags=lanczos" -q:v 2 frames/f_%03d.png`) und die Frames mit `vision_analyze`
  lesen. Ein Serverfehler auf EINEM Frame ist voruebergehend - anderen Frame
  nehmen, nicht den Weg verwerfen. Die Frames danach loeschen (Wegwerfware).
- Reicht die Textebene nicht, weil der Clip mitten im Satz abbricht: nach einem
  WOERTLICHEN Satzstueck web-suchen. Die Trefferkurzbeschreibungen der
  Plattformseiten enthalten die vollstaendigen Caption-/OCR-Texte des Clips -
  auch dann, wenn `web_extract` die Seite selbst verweigert (Instagram und
  TikTok blocken den Direktabruf).
- Kein Ton-Transkript per Modell: vorher pruefen, ob ueberhaupt eines lokal
  bereitliegt (`python -c "import faster_whisper"`, `which whisper`). Fehlt es,
  nicht installieren, sondern mit der Textebene arbeiten und die Luecke im
  Bericht nennen.
- Fehlendes NICHT erfinden. Ein 16-Sekunden-Ausschnitt liefert selten die
  Einstiegsregel - die Luecke wird benannt, nicht ueberbrueckt.

## 2. Datenquelle verifizieren, BEVOR die erste Zeile Strategie entsteht
- Fuer jede Groesse EINE echte Anfrage und die Antwort zeigen (Indexpreis,
  Volatilitaetsindex, Kerzen, Optionskette). Erst wenn die Felder vorliegen, ist
  klar, was die Rechnung ueberhaupt benutzen kann. Endpunkte und Grenzen:
  `references/boersen-datenzugriff.md`.
- Die TIEFE messen, nicht annehmen (aelteste Kerze, Tage im Volatilitaetsindex).
  Ein Abruf, der still weniger liefert als angefordert, sieht wie ein volles
  Fenster aus.
- Alle Antworten in einen Zwischenspeicher (`daten/`) legen und diesen Ordner in
  die Sperrliste der `.gitignore` eintragen - sonst wandert ein Megabyte
  Rohdaten in den Verlauf.

## 3. Behauptung in Bausteine zerlegen, jeden Baustein einzeln messen
- Jeder Teil der Fremdstrategie wird eine eigene Funktion (Signalquelle,
  Spanne/Risikomass, Ein- und Ausstieg, Filter) - nur so bleibt bei einem
  Verlust zuordenbar, welcher Baustein schuld war.
- Wo die Quelle eine Zahl verspricht ("90 %"), die eigene Messung daneben
  stellen. Eine Abweichung ist ein BEFUND, kein Fehler: eine zugesagte
  90-%-Decke hielt auf 400 Tagen 82 % der Tage, per Schlusskurs 92,8 % - damit
  taugt sie zum Dosieren, nicht als Versprechen.
- Bausteine, die die Quelle nur erzaehlt, weil sie eine gekaufte Kennzahl
  braucht (Wandauswahl aus offenem Interesse), sind nicht rueckwirkend pruefbar:
  das wird VOR dem Bauen gesagt, nicht nach dem Backtest entdeckt.

## 4. Backtest-Regeln
Vollstaendig in `references/auswertung-und-optimierung.md`, Abschnitt "Backtest
einer NEUEN Strategie auf Fremddaten": kein Blick nach vorn, Stop vor Ziel im
selben Balken, Gebuehr je Seite, Raster ueber Nachbarn + Stichprobe halbieren +
Seiten trennen. Ein einzelnes positives Feld ist Zufall.

## 5. Endzustand ohne Verdrahtung ist gueltig
- Eine gepruefte, NICHT verdrahtete Spur ist ein ordentliches Ergebnis: Ordner
  mit Kernrechnung, Datenzugriff, Gueteproben, `wachen.json`
  (`handel_erlaubt: false`, Ratsche als BETRAG = 1,0 x Buchrisiko), `NOTIZ.md`,
  Tests offline (Fixture-Ketten selbst bauen, kein Netz, kein Orderpfad).
- Fuer diesen Zustand reichen in der `.gitignore` Whitelist (`*.py`, `*.md`,
  `wachen.json`, `tests/*.py`) + Sperrliste (Datenordner, Backtest-Ergebnis).
  Die Eintraege in `dauerlauf.SPUREN`, Tagesbericht und Bus kommen erst beim
  Anschliessen - und das ist eine Entscheidung von Max, nicht Teil dieses
  Auftrags.
- `NOTIZ.md` traegt: Quelle mit woertlichen Belegzeilen, Datenumfang, die
  Messzahlen je Baustein, was unmessbar bleibt, was offen ist. Zahlen in Bericht
  und Notiz immer aus dem eigenen Lauf, nie aus dem Kopf der Quelle.
- Melden: was jetzt laeuft (mit Nachweisbefehl), was absichtlich NICHT angefasst
  wurde (laufender Dauerlauf, fremde Profile, Laufzeitstaende), und was eine
  Entscheidung braucht. Commit + Push wie jeder andere Auftrag.

## 6. Fremdstrategie, die als CODE vorliegt (Repo statt Clip)
- Original-Code nehmen, nicht nachbauen: nur Datenpfad und Gebuehr
  parametrisieren, den Rest unveraendert lassen. Der Mac-Pfad im Original bleibt
  stehen, der eigene Lauf liest die lokale CSV.
- Zweimal fahren, mit 0,05 % und 0,20 % je Seite. Erst der Unterschied zeigt, ob
  die Strategie einen Vorteil hat oder nur von Gebuehrfreiheit lebt. Beispiel
  21.09.2026 (TTM-Squeeze+ADX, neun Jahre BTC 1h): +158 % bei 0,05 %, -60 % bei
  0,20 %, auf frischen Hausdaten auch ohne Gebuehrdruck negativ.
- Ergebnis gegen `Handel/kosten_wendepunkt.py` halten: dessen f_max ist die
  Gebuehr je Runde, bei der nur noch die Nullinie getroffen wird, und damit
  direkt mit der Fremdstrategie vergleichbar (dort ~0,10 %, Haus-Scanner
  9,98 %). Eine Fremdstrategie, deren f_max unter dem der schwaechsten eigenen
  Spur liegt, wird nicht uebernommen - Parameter-Optimierung aendert daran
  nichts.
- Fremd-Repos bringen oft die KURS DATEN mit, die im Haus fehlen: neun Jahre
  BTC-Stundenkerzen liegen unter
  `Werkstatt/Repos/Harvard-Algorithmic-Trading-with-AI/backtest/data/`, dazu
  BTC-6h, ETH-1d, SOL-1d.
- Lauffaehige Fremd-Backtester mit fertigem venv: `Werkstatt/freqtrade` (ccxt,
  `user_data/data` muss erst gefuellt werden), `FinRL`, `RLTrader`,
  `intelligent-trading-bot`. talib + backtesting.py liegen im venv von
  `Werkstatt/Repos/moon-dev-ai-agents`.
- Ausgemusterte Skills liegen unter `Agenten/Hermes/skills/.archive/` und sind
  dort mit `read_file` lesbar - **ohne** sie in die Bibliothek zu laden. Nur
  zurueckholen, was wirklich laeuft (`hermes curator restore <name>`); ein Skill,
  der auf ein fehlendes Werkzeug zeigt (z. B. `marktbriefing` -> `traderhub`
  nicht installiert), bleibt liegen.
- Belegnotiz: `Wissen/Archiv-Trading-Skills.md`, Skript
  `Agenten/Handel/backtest_archiv_strategie.py`.
