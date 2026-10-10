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
Spuren: scanner, xperp (Hauptweg), orb, kraken (stillgelegt).

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
- **`.env`, `Wissen/Zugaenge.md`, `proxy.yaml` sind tabu** — nie lesen,
  ausgeben oder protokollieren.

## Werkzeugfallen am Host
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
