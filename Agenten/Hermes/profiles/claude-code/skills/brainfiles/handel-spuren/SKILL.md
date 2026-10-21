---
name: handel-spuren
description: "Handelsspuren scanner/xperp/orb: Sperren, Freigabe, Tore."
category: brainfiles
---

# Handelsspuren

## Wann
Jede Änderung unter `Agenten/Handel/**`: eine Sperre ergänzen, eine Freigabe
verdrahten, ein neues Analysemodul bauen, Wachenwerte anfassen, Tests schreiben.
Auch beim Deuten einer Bus-Meldung, die eine Spur als „Ergebniscode 1“ meldet.
Auch bei „optimiere die Trading-Agenten" / Bestandsprüfung: welche Spur läuft,
 welche Wächteraufgabe scharf ist, was der Backtest sagt, wo der Platz geht.
Spuren: scanner, xperp (Hauptweg), orb, kraken, omnitrade_futures, nautilus_kraken, nautilus_kraken_futures, mosaic, swap, moondev_* (listingarb, topmovers, signalwelle, marktlage, whale, liquidation, sentiment, sniper, funding), klassik_* (sma, ema, macd, rsi, rsi2, bollinger, donchian, donchian_trend, pmax, supertrend, sr_breaks), iv_wand, iv_waelle, liq_wand, macd_mtf, squeeze, supertrend, trendwende_btc, wavetrend, prophet_signal, robinhood_radar, omniquant, omnitrade, gitter, spiegel, orbk, nautilus, nautilus_emacross, nautilus_rc5, ai4trade, scanner_quant, verbesserer, stand, kopier.

## Landkarte (nur was zum Arbeiten nötig ist)
- `Agenten/Handel/<spur>/` — je Spur `handeln.py`, `wachen.json` (die Grenzen;
nur gelesen, einzige Ausnahme `sperre_zu` true→false), `zustand.json`,
  `handelsjournal.csv`.
- `Agenten/Handel/dauerlauf.py` — 24/7-Treiber. Startet je Spur
  `handeln.py --live/--papier` als Unterprozess und **liest dessen Ausgabe**.
- `Agenten/Handel/freigabe.py` — Bestätigungsfenster am Bildschirm, je
  Vorschlag einzeln.
- `Agenten/Handel/freigabefenster.py` — Zeitfenster fürs Handy (`/ja`, `/nein`,
  `/stop`), eigener Zustand in `freigabe_fenster.json`, nie in wachen.json.
- `Agenten/Handel/prognose.py` — Beobachter über den ganzen Markt, stellt keine
  Order, kennt keine Spur, Tore in `prognose.json`.
- Interpreter immer `.venv\Scripts\python.exe` im Handel-Ordner, Aufruf aus dem
  jeweiligen Spurordner.

## Spur-Status prüfen
1. **wachen.json lesen** — `handel_erlaubt`, `freigabe.erfuellt`, `stillgelegt`, `journal_zweitziel`, `herzschlag_max_minuten`, `kill_switch_gesamt`, `drawdown_halbierung`. Diese Felder entscheiden, ob eine Spur live kann.
2. **zustand.json lesen** — offene Positionen, letzter Lauf, Modus, Buch-Abgleich (Geister/Waisen).
3. **handelsjournal.csv lesen** — Runden, Trefferquote, Netto-Summe, Zeitraum.
4. **freigabe_fenster.json lesen** — ob das Fenster für die Spur offen ist und wann es abläuft.
5. **dauerlauf.log lesen** — letzte Meldungen der Spur, ob der Dauerlauf sie als "ok" meldet.
6. **Dauerlauf-Betrieb prüfen — Aufgabenstand, nicht die PID-Datei.** Die
   `.pid`-Dateien sind **Sperren je Risikostufe** (Basis `dauerlauf.pid`,
   `dauerlauf.mittel.pid`, `dauerlauf.hoch.pid`), kein Gesundheitszeugnis: eine
   tote Sperre ist harmlos, `handel-dauerlauf.ps1` erkennt eine nicht lebende
   (und eine wiederverwendete, per Startzeit) PID und ersetzt sie. Die echte
   Lücke ist eine **deaktivierte Wächteraufgabe** — dann kommt ein gestorbener
   Lauf nicht zurück. Also `Get-ScheduledTask` fragen und die Prozessliste per
   `Get-CimInstance Win32_Process` holen (MSYS-`ps` sieht keine
   Windows-Prozesse). Befehle, Aufgabennamen und die Wiederbelebung:
   `references/dauerlauf-betrieb.md`.

## Dauerlauf-Modus prüfen (Papier vs. Live)
- **Freigabefenster aller Spuren lesen**, nicht nur eine: In
  `freigabe_fenster.json` steht `offen_bis`. Ist kein Fenster offen, läuft der
  Basislauf auf Papier — auch wenn `wachen.json` `handel_erlaubt: true` trägt.
- **Stufenläufe (mittel/hoch) sind immer Papier**, nie `--live` — der Code
  (`dauerlauf.py`, Kommentar „DATENSAMMLER") erzwingt das. Nur der Basislauf
  (Stufe `niedrig`) kann über ein Freigabefenster live werden.
- **„Nicht zu leistungsintensiv“ prüfen, nicht behaupten:** CPU-Last und freier
  RAM vorher messen (`Win32_Processor.LoadPercentage`, `Win32_OperatingSystem.FreePhysicalMemory`).

## Spur live schalten
1. **Sichern** (Stufe 1): `.bak-JJJJMMTT` für jede wachen.json, die angefasst wird.
2. **wachen.json ändern:**
   - `handel_erlaubt`: false → true
   - `freigabe.erfuellt`: false → true (mit Vermerk im `_erfuellt_vermerk`)
   - `stillgelegt`: true → false (falls vorhanden)
3. **Freigabefenster öffnen:** In `freigabe_fenster.json` den Eintrag für die Spur setzen — `anfrage_gestellt`, `offen_bis` (aktuelle Zeit + Dauer), `freigegeben_von: "auto"`, `freigegeben_am`.
4. **AUTO_FREIGABE prüfen:** In `dauerlauf.py` die Liste `AUTO_FREIGABE` — die Spur muss enthalten sein, sonst öffnet der Dauerlauf das Fenster nicht automatisch.
5. **Verifikation:** Beide wachen.json lesen (handel_erlaubt + freigabe.erfuellt = true), freigabe_fenster.json lesen (offen_bis in der Zukunft), dauerlauf.log prüfen.
6. **Voraussetzungen prüfen:** Freies Guthaben über `mindest_guthaben` (je Spur unterschiedlich), `journal_zweitziel` gesetzt, `herzschlag_max_minuten` ≥ 180.

## Prozedur
1. **Lage lesen, nicht erinnern.** `handeln.py --vorschau` mit
   `MAXHIRN_ROUTINE=1` läuft ohne Fenster und nennt jede geschlossene Sperre.
   Die Sperrliste im Code lesen (`sperren_live`), nicht aus dem Gedächtnis.
2. **Sichern** (Stufe 1): `.bak-JJJJMMTT` für jede Datei, die angefasst wird —
   auch `wachen.json` und `zustand.json`, wenn ein Testlauf sie berühren kann.
3. **Ändern:** Sperren gehören in `sperren_live()` bzw. die gleichnamige
   Funktion der Spur, nicht verstreut in den Rumpf von `lauf()`.
4. **Ohne Broker testen.** `cd <spur> && python -m unittest discover -s tests`.
   Für den Live-Pfad `pruefe_einstiege`/`pruefe_ausstiege` per Lambda stilllegen,
   das Fenster regulär öffnen, den Lauf starten und die Zustandsdateien
   vorher/nachher per Hash vergleichen. Ein Test darf `markt_kauf` nie
   erreichen. Eine geänderte Ausgabezeile zusätzlich **rendern statt lesen**:
   die `print`-Anweisung per `ast.get_source_segment` aus der Datei holen, mit
   `ast.parse`/`compile` übersetzen und mit Beispieldaten ausführen — dann steht
   schwarz auf weiß da, was der Nutzer zu sehen bekommt. Eine Formatprüfung im
   Kopf ist kein Nachweis, und `ast.parse` allein prüft nur die Syntax.
5. **Versionieren.** `.gitignore` ist eine **Whitelist** (erst alles ignorieren,
   dann einzeln freigeben). Jede neue `.py`/`.json`/Testdatei braucht eine
   eigene `!`-Zeile, sonst landet sie still nicht im Verlauf. Gegenprobe:
   `git check-ignore -v <pfad>`.

## Backtest-Ergebnisse auswerten
- **Mit den Hausfunktionen rechnen, nie mit einer eigenen Formel.**
  `auswertung_alle.runden_indikator(zeilen)` paart kauf/verkauf über
  `journalpaarung` — bei skalierten Positionen gilt die LETZTE Kaufzeile, weil
  `einsatz_usd` dort **kumulativ** ist. `auswertung_alle.kennzahlen(runden,
  einheit, gebuehr, brutto)` liefert Treffer, Median, Gründe und trennt
  Störungen ab. Eine Eigenbau-Formel ist eine zweite Wahrheit und lag im
  Zweifel um Größenordnungen daneben.
- **Journal über `journalpaarung.zeilen(pfad)` lesen** (utf-8, `newline=""`),
  nicht per Hand — sonst gehen BOM und CRLF schief.
- **`daten/backtest/<spur>/<lauf>/` ist die Messgrundlage, nicht Ablage.**
  `auswertung_alle.backtest_stand(spur)` wählt je Spur den Lauf mit den
  meisten Journal-Zeilen und füllt damit den Leitstand-Reiter *Backtest*; wer
  die Ordner verschiebt oder aufräumt, lässt dort `kein Lauf` stehen.
- **Ein Fenster ist kein Befund.** `optimieren.py` schreibt
  `daten/backtest/<spur>/optimierung.json` mit dem Feld `ueberlebt` — nur
  Kandidaten, die ALLE Fenster bestehen, zählen. Positiv aussehende
  Einzelordner (Hash-Namen) sind Ein-Fenster-Läufe und tragen nichts.
- **Brutto ist nicht netto.** Die Indikator- und Klassik-Bücher schreiben
  keine Kosten in die Zeile; die Gebühr steht als `gebuehr_taker` in der
  `wachen.json` und ist je Börse und je Seite zu rechnen.

## Pitfalls
- **Der Sperrtext ist eine Schnittstelle.** `dauerlauf.nur_fenster_fehlt` liest
  die Zeile `Live waere gesperrt durch: …` und stellt nur dann eine
  Freigabe-Anfrage, wenn dort genau EIN Grund steht und dieser
  „Freigabefenster“ enthält — kein `;` und kein `:` darin. Die Formulierung
  ändern, ohne die Leser zu suchen, heißt: es wird nie gefragt, und jedes `/ja`
  bleibt folgenlos. Vor jeder Textänderung nach den Verbrauchern greppen.
- **Diagnose in jedem Modus drucken, den ein Aufrufer parst.** Eine Zeile, die
  nur im `--live`-Zweig fällt, existiert für `--vorschau` nicht — und
  `--vorschau` ist genau das, womit der Dauerlauf die Lage prüft.
- **Gemeldet wird zeilenweise, nicht im Block.** Der Dauerlauf filtert die
  Ausgabe jeder Spur nach Stichwörtern (`verkauf`, `stop`, `KILL`, `gesperrt`)
  und schickt **nur die passende Zeile** nach Telegram. Jede Zeile, die eines
  dieser Wörter enthalten kann, muss Instrument und Seite selbst nennen; eine
  Fortsetzungszeile ohne Subjekt kommt unzuordenbar an. Bei jeder neuen
  Ausgabezeile prüfen, ob sie allein verständlich ist — und bei einer kurzen
  Seite wie `Liq über Stop, Ziel darunter` auch, ob sie ohne die Richtung
  (`long`/`short`) wie ein Fehler aussieht.
- **Zwei Prozesse mit identischer Kommandozeile sind kein Doppellauf.** Ein
  venv-Start erzeugt ein Paar aus Launcher und echtem Interpreter, beide mit
  derselben `CommandLine`. Bevor ein Doppellauf gemeldet wird: jede PID
  einzeln mit Startzeit und Eltern-PID ausgeben und die Liste vollständig
  zeigen. Ein Fehlalarm kostet mehr Vertrauen als die Prüfung Zeit — und muss,
  wenn er passiert ist, ausdrücklich zurückgenommen werden.
- **Eine Sperre muss auch aufgehen können.** Ein Tor, das nie öffnet, sieht wie
  Sicherheit aus und ist ein Fehler: `references/tor-kalibrierung.md`.
- **Zwei Fassungen derselben Sperre, eine Wahrheit.** Neue Spuren nach dem
  Muster einer bereits richtigen Spur bauen, nicht eine dritte Variante
  erfinden (xperp war beim Freigabe-Weg zuerst richtig).
- **Zustandsdateien vergiften sich.** `zustand.json` wächst bei jedem echten
  Lauf; sichern statt reparieren.
- **Zahlen in `wachen.json` sind in `_..._vermerk`-Feldern begründet — vor
  jeder Zahlenänderung die Vermerke lesen.** Ein Wert, der in einer
  Übersichtstabelle wie ein Ausreißer aussieht, ist oft Absicht: ein
  `max_gesamt_usd` kann der **Nominalwert** der kleinsten handelbaren
  Kontraktgröße sein (deshalb groß), ein erhöhtes `risiko_je_position_usd`
  eine ausdrückliche Anordnung. Ein „Harmonisieren" auf einen gefühlten
  Mittelwert zerschießt eine laufende Spur. Wer nur die Zahl sieht, hält
  Absicht für Schlamperei.
- **`.env`, `Wissen/Zugaenge.md`, `proxy.yaml` sind tabu** — nie lesen,
  ausgeben oder protokollieren.

## Werkzeugfallen am Host
- **MSYS-`ps aux` sieht KEINE Windows-Prozesse.** „Es läuft nichts" ist damit
  keine Aussage über den Handel — `dauerlauf.py` und die Spuren erscheinen dort
  nie. Prozesse immer über `Get-CimInstance Win32_Process` (mit `CommandLine`,
  `ProcessId`, `ParentProcessId`) prüfen, bevor etwas als tot gemeldet wird.
- **Eine Volltextsuche über `Agenten/` im Terminal reißt die 180-s-Grenze.**
  Der Baum trägt `.venv`, `OpenAlice`, `nautilus-rust`; dafür `search_files`
  nehmen (ripgrep, respektiert `.gitignore`).
- Das Host-PowerShell-Werkzeug hat eine harte Zeitgrenze (~300 s). Eine
  rekursive Größenmessung über einen großen Baum reißt sie. Stattdessen
  vorher/nachher `Win32_LogicalDisk.FreeSpace` messen oder je Ordner einzeln —
  der Zuwachs ist die belastbare Zahl.
- Windows begrenzt die Kommandozeile (~32k Zeichen): ein großer
  PowerShell-Here-String scheitert mit `WinError 206`. Lange Dateien in Teilen
  schreiben (`Set-Content`, dann `Add-Content`) oder einen kleinen Applier
  lesen lassen, der die Nutzlast aus einer Datei holt.
- Geschriebene `.py`/`.json` danach prüfen statt annehmen: `ast.parse` bzw.
  `json.loads`, dazu kein BOM und kein `\r`. Beim Weg über einen
  PowerShell-Here-String mit `utf-8-sig` einlesen, `\r` entfernen, dann mit
  `newline=""` schreiben.

## References
- `references/freigabe-kette.md` — Punkt 3 der Handelsregeln in beiden
  Fassungen: Bildschirmfenster und Zeitfenster, wer wann öffnet, was eine
  Freigabe nicht kann.
- `references/tor-kalibrierung.md` — Schwellen setzen, ohne dass sie entweder
  nichts filtern oder nie aufgehen.
- `references/dauerlauf-betrieb.md` — die drei Risikostufen, ihre Sperr- und
  Buchdateien, die vier geplanten Aufgaben, der Unterschied zwischen toter
  Sperre und deaktiviertem Wächter, und wie eine Stufe wiederbelebt wird.
