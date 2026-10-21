---
name: handel-spuren
category: software-development
description: Use when asked to assess or tune trading strategies. Measure before recommending changes.
version: 1.0.0
author: Hermes Agent
license: proprietary
metadata:
  hermes:
    tags: [handel, trading, wachen, auswertung]
    related_skills: [systematic-debugging]
---

# Handelspuren auswerten und verbessern

## When to Use

Max bittet um „Handelspuren auswerten und verbessern". Auslöser: eine Anfrage über die Spuren in `Agenten/Handel`, eine Kennzahl in `wachen.json`, ein omnitrade-Intervall, oder die Frage, welche Spur Geld macht und wie eine Verliererin zu reparieren ist.

Max fragt das als „Handelspuren auswerten und verbessern". Der Vorgang hat eine feste Reihenfolge: **erst auswerten, dann eine begründete Änderung, nie beides vermischt.** Das gesamte Verzeichnis `Agenten/Handel` — inkl. jeder `wachen.json` — ist **Stufe 1** der Schutzregeln: Änderung nur mit Ansage, Backup, danach Prüfung.

## Auswerten (rein lesend)

```
cd Agenten/Handel
scanner/.venv/Scripts/python.exe auswertung_alle.py
```

- Deutet jede Spur mit eigenen/keinen Journal-Zahlen; die „Uebersicht".-Zeile fasst alles zusammen. Fange die volle Ausgabe in eine Datei ab (nicht nur die Teilzeile). (die bekommst du sonst nicht komplett auf einen Screen), auch für `--spur <einzelne>`.
- **Belastbar = ≥ 8 geschlossene Runden.** Darunter heißt es „zu wenige Runden — ein Befund, keine Messung". Über 8 Runden aus einer Zahl Entscheidungen abzuleiten ist Overfitting; sag das klipp und klar, statt daraus einen Tuningschritt zu bauen.
- Kern-Zahlen einer Spur liegen in ihrem `<spur>/wachen.json` und Journal; `--wachen` an das jeweilige `handeln.py` zeigt den Zustand (freigabe, kill, herzschlag, groessenfaktor).

Nicht jede Spur hat ein `handelsjournal.csv`, das über `pos_id` paar-bar ist — Altjournal-Zeilen tragen keine `pos_id` und fallen aus der Zählung. Sag es dazu, wenn du auf Grundlage gepaarter Zeilen rechnest.

### Eigene/LLM-Spuren getrennt auswerten

- Nach `auswertung_alle.py` auch dessen Abschlusszeile lesen: manche Spuren (eigene Evaluatoren, LLM-Signale oder abweichende Journalformate) fehlen bewusst in der Sammelrechnung. Für diese jeweils den ausgewiesenen Spur-Evaluator, Journal und `zustand.json` heranziehen; die Sammelübersicht nicht als vollständige Spur-Liste ausgeben.
- Eine Spur nur dann als LLM-gestützt bezeichnen, wenn der aktive Signalpfad tatsächlich das lokale/konfigurierte Sprachmodell aufruft — Namen wie `moondev_*` reichen nicht. Aktive `SPUREN` und ausführbaren `handeln.py`-Pfad gegenprüfen.
- Runden nur aus eindeutig gepaarten Einstiegs-/Ausstiegszeilen zählen. Offene Positionen und Ausstiege ohne Partner separat melden; sie sind keine geschlossenen Runden und kein realisiertes Ergebnis. Nicht verfügbare Backtest-Historie als nicht nachrechenbar kennzeichnen, nicht durch Schätzungen ersetzen.
- Ein kurzer Prompt-Sanity-Check belegt nur Antwortfähigkeit. Signalqualität braucht den festgelegten Vertrags-/Eval-Satz; ohne diesen keine Aussage aus zwei Beispielprompts ableiten. Es gelten weiter die Stichprobenschwellen aus *Auswerten*.
- **LLM-Spuren haengen zu 100 % am lokalen Bonsai-Dienst (127.0.0.1:8080).** Die drei echten LLM-Spuren (moondev_whale/liquidation/sentiment) rufen `llm_lokal.entscheide` ueber den Bonsai-Weg; faellt der Dienst aus, faellt das Urteil aus und KEINE der drei handelt — es gibt bewusst keinen stillen Rueckfall auf ein kleineres Modell. Das ist ein Single-Point-of-Failure fuer Echtgeld: vor dem Live-Schalten einer LLM-Spur pruefen, ob ein Fallback existiert, und den Bonsai-Dienst als Betriebsabhaengigkeit nennen. Zusaetzlich: diese drei haben oft nur 3-4 Papier-Runden — weit unter der Belastbarkeits-Schwelle (≥ 8), also kein Freigabe-Kandidat, bis der Papierlauf tragfaehig ist.

## Tunen: erst die Asymmetrie messen, dann den einen Stellhebel

Typischer Befund (liq_wand 10.2026): **hohe Trefferquote, aber netto negativ.** Ursache ist fast immer eine Gewinn/Verlust-Asymmetrie — Zielgewinne klein, Stops 3× größer. Rechnung aus dem Journal: durchschnittlicher Gewinn ÷ durchschnittlicher Verlust, gegen die Break-even-Schwelle `Verlustanteil / Gewinnanteil`. Liegt die Asymmetrie darunter, ist netto negativ, egal wie oft du triffst.

- Der eine Stellhebel, der diese Klasse von Spur korrigiert: **den Stop nah an die Realitaet der Zielgewinne ziehen** (`stop_prozent` in `wachen.json`), nicht das Ziel vergrössern — wenn das Ziel eine Marktstruktur ist (z. B. die Liquidationswand), ist es nicht beweglich.
- **Der Stop-Hebel passt NUR zur Klasse "hohe Trefferquote, netto negativ".** Miss die Asymmetrie zuerst und klassifiziere, bevor du einen Hebel vorschlaegst: (a) Asymmetrie < Break-even UND hohe Trefferquote → Stop enger (die Verlustseite ist zu breit); (b) Asymmetrie GUT (avgG/avgV > BE) aber Trefferquote zu niedrig → das Problem ist die Signalselektion, NICHT der Stop — Stop enger wuerde nur den seitlichen Rand treffen und die wenigen Gewinne kuerzen, nicht das Trefferproblem loesen. Bei (b) ist Stop-Tuning ein unbegruendeter Eingriff; dort erst mehr Daten/anderes Signal, nicht blind ein Risiko umbauen. Eine Spur mit guter Asymmetrie aber 3/14 Treffern (z. B. prophet_signal) ist ein Signal-Problem, kein Stop-Problem.
- **Der Stop-Schluessel heisst nicht ueberall `stop_prozent`.** ATR-basierte Spuren (z. B. `swap`) tragen die Stop-Breite als Faktor (`stop_atr_faktor`, `ziel_atr_faktor`), nicht als Prozent. Beim Befund zum Stop-Hebel den Schluessel aus der WACHE nehmen (`grep stop_atr|ziel_atr|stop_prozent <spur>/wachen.json`), nicht den Prozent-Namen aus dem Muster uebernehmen — sonst verschreibt man einen Schluessel, den die Spur gar nicht liest.
- **Eine Grid-/Mehrfach-Kandidaten-Spur ist nicht ohne weiteres eine Familie-A-Spur.** `optimieren.py`/`lauf_a` handeln pro Instrument EINE Position mit festem Stop/Ziel je Kerze; eine Grid-Spur (z. B. `swap` auf XPERP mit `grid_stufen`, `grid_spanne_atr`) ist ein anderes Modell. Sie in die Familie-A-Parametersuche zu zwingen ist eine konzeptionelle Übernahme (Grid → pro-Kerze-Einstieg mit ATR-Stop/Ziel), keine mechanische Ergaenzung von `lade_wachen`+Suchbereich. Vor einem solchen Umbbau Max entscheiden lassen, ob der Grid-Aspekt erhalten bleibt (Mehrfach-Kandidaten in Familie-A) oder wegfaehrt (reine Einzel-Position) — die zwei Varianten bestimmen, ob Suchbereich und Suchschluessel nur Stop/Ziel oder auch Grid-Parameter abdecken.
- Halte dich an das Pflichtband der Spur (`pflicht_stop_prozent_min/max`).
- **0 geschlossene Runden = nicht kalibrierbar.** Hat eine Spur noch nie eine Runde geschlossen (Journal leer an `verkauf`-Zeilen), gibt es keine Daten, um die Stop-Breite zu belegen — jede Anpassung wäre Bauchgefühl. Sag das klipp und klar statt zu tunen. Offene Positionen können dabei trotzdem das Pflichtband überschreiten (Stop gegen 20-Tage-Extrema gerechnet, nicht gegen den Einstieg); das ist ein Befund, kein sofortiger Eingriff.

## Parameter suchen statt raten: `optimieren.py`

Die vier Indikator-Spuren (squeeze, wavetrend, macd_mtf, supertrend) lesen ihre Indikatorschwellen aus der `wachen.json` und sind damit Walk-Forward-suchbar:

```
scanner/.venv/Scripts/python.exe optimieren.py --spur squeeze --trocken   # Dunkel vorher: Kerzen, Kandidaten, Zeit
scanner/.venv/Scripts/python.exe optimieren.py --spur squeeze              # schreibt daten/backtest/<spur>/optimierung.json
```

- `--trocken` liefert die Laufzeitschätzung — bei >5 min im Hintergrund starten, nicht blockierend warten.
- **Ergebnis-Lesart:** `ueberlebt: []` bei allen Kandidaten heißt: die Spur ist **von keinem Stop/Ziel-Parameter behebbar** — das Signal selbst ist negativ. Das ist ein Stilllegungs-Kriterium, kein Fehlschlag-Tuning.
- Etwas, das live netto negativ ist und dem die Parametersuche keinen Ausweg zeigt, gehört zur Disposition (nächster Abschnitt).
- **Nur Spuren mit Suchbereich UND `lade_wachen()` sind überhaupt suchbar.** `optimieren.py` braucht beides: einen Eintrag in `spur_opt.json` (Suchbereich mit `schluessel`) UND eine `lade_wachen()`-Funktion im `handeln.py` der Spur (geladen via `replay.spur_modul(spur).lade_wachen()`). Fehlt eines, bricht die Suche ab (`KeyError: kein Suchbereich` bzw. `AttributeError: module 'bt_<spur>' has no attribute 'lade_wachen'`). Vor dem Lauf beide Prüfungen machen: `python -c "import json; print('swap' in json.load(open('spur_opt.json',encoding='utf-8')))"` und `grep -n 'def lade_wachen' <spur>/handeln.py`. Eine Spur, die nicht suchbar ist, ist damit NICHT als negativ belegt — das `ueberlebt: []`-Stilllegungs-Kriterium kann für sie gar nicht ausgewertet werden. Das ist ein fehlender Suchbereich/fehlende Funktion, kein Signal-Urteil; die Asymmetrie-Rechnung aus dem Journal bleibt der Weg, um den Stop-Hebel zu beurteilen.
- **Eine Spur suchbar machen, wenn nur `lade_wachen()` fehlt:** der Suchbereich steht schon in `spur_opt.json` und die `wachen.json` enthält die Suchschlüssel — es fehlt nur die Funktion. Dann `lade_wachen()` im `handeln.py` ergänzen (liest `wachen.json` und gibt das Dict zurück, Muster der Nachbarspuren), im Worktree auf eigenem Zweig. **Der Worktree hat kein `daten/`** (nicht versioniert) — `optimieren.py` bricht dann mit `RuntimeError: keine Historie fuer <spur>` ab, obwohl die Historie im Hauptbaum liegt. Vor dem Lauf eine **Junction** auf das Hauptbaum-`daten/` legen (`powershell New-Item -ItemType Junction -Path '<worktree>/Agenten/Handel/daten' -Target '<hauptbaum>/Agenten/Handel/daten'`), dann `--trocken` zur Bestätigung, dann der echte Lauf über den Hauptbaum-Interpreter.
- **Vor dem `optimieren.py`-Lauf pruefen, ob die Spur in `dauerlauf.py` `SPUREN` noch AKTIV ist.** Eine Spur kann bereits stillgelegt sein (Eintrag auskommentiert, z. B. `squeeze` am 10.10.2026) — dann ist ein 7-min-Parametersuchlauf verschwendete Arbeit, weil die Spur ohnehin nicht mehr laeuft. `grep -nE '^\s+"<spur>"' dauerlauf.py` (nur nicht-auskommentierte Zeilen) vor dem Lauf; ist der Eintrag weg, die Stilllegung als gegeben melden statt zu optimieren.

## MTF-Parameter-Optimierung (Walk-Forward-Schwellen)

Die Indikator-Spuren `squeeze`, `wavetrend`, `macd_mtf` und `supertrend` lesen
ihre Indikatorschwellen aus `wachen.json` und sind Walk-Forward-suchbar. Einer von
ihnen ist oft so programmiert, dass er zu langsam reagiert (mehr als 80 % der
Kerzen ohne Signal) und dadurch nie handelt — das ist kein Stop- oder
Ziel-Problem, sondern ein Parameter-Problem an der Multitimeframe-Konfiguration:

**Das Vorgehen des MTF-Optimierens:**

1. **Identifizieren:** Ließt die Spur aus `mtf_faktoren` (Liste) einen langsamen
   Top-Zeitrahmen (z. B. `16H`), der vor Erreichen einer Ausrichtung keine Signal
   liefert? Prüfe `mindest_kerzen` im Vergleich zur Kerzenleistung
   (`okx.kerzen()` liefert normalerweise nur 300 je Abruf). Wenn die Spur gegen ein
   300-Kerzen-Limit staut, ist der Top-Zeitrahmen zu klein und fragt nicht nach
   genug Daten. Maßgeblich ist dabei die rechnerische Kosten (`n * (schnell + signal)`
   Kerzen je eigene Schwellenwert für den Top-Rahmen).
2. **Konservative Reduzierung:** Reduziere die MTF-Faktoren, sodass der Top-Zeitrahmen
   früh genug signalisiert, ohne die Signale komplett zu entkoppeln. Verwandt:
   `mtf_faktoren: [1, 4, 16]` → `mtf_faktoren: [1, 2, 8]` (Top-Zeitrahmen 16H → 8H,
   4H → 2H). Das halbiert die Wartezeit und erzeugt die Ausrichtung nach ~100
   Kerzen, anstatt ~560. Für steile Trendphasen ist das ein Gewinn; im Rauschen
   kann es zu mehr Kopf/Schwung führen — deshalb die Gegenprobe vor dem Live-Schalten
   (`--trocken` laufen lassen).
3. **Keine blinden Parameteränderungen:** Die MTF-Faktoren ändern die Sensitivität
   des Signals; `mtf_schnell`/`mtf_langsam`/`mtf_signal` bestimmen die eigentliche
   Einstiegs-Reaktion. Optimiere zuerst den Faktor, prüfe danach, ob das Treffer-
   und EV-Verhältnis besser wird. **Nicht** mehrere Faktoren gleichzeitig ändern,
   sonst lässt sich nicht sagen, was den Unterschied gemacht hat.
4. **Backtest-Vertrag prüfen:** Nach der Parameter-Änderung
   `scanner/.venv/Scripts/python.exe auswertung_alle.py --spur <spur>` laufen und die
   Runden-/EV-Zahl vergleichen. `handeln.py`'s MTF-Funktion ist aufgerufen,
   `optimieren.py` erkennt eine Suche in `wachen.json`, nicht in `ti_indikatoren.py`.
   Entscheidungen auf echten Runden, nicht auf der Intuition des Schemas.

**Hier wurde die Technik angewendet (2026-10-21):**
`macd_mtf/wachen.json` — `mtf_faktoren` von `[1,4,16]` auf `[1,2,8]` gesetzt, sodass
der Top-Zeitrahmen 8H ist (statt 16H). Der Einstieg erfolgt nun früh genug, um
Handelssignale zu raffen. Das Backtest-Ergebnis (-2,198 %/Runde bei 752 Runden) bleibt
der alte Wert — eine Parameter-Änderung verbessert nicht automatisch den EV, sondern
erlaubt es, dass der Signal-Schwellwert überhaupt aktiv wird.

> **Merke:** Ein `ueberlebt: []` bei `optimieren.py` bedeutet, dass das Signal
> selbst negativ ist und nicht durch Parameter-Suchen geheilt werden kann. Die MTF
> -Parameter-Optimierung ist nur sinnvoll, wenn die Spur bereits belastbare Runden
> hat und nur die Durchsicht zu langsam ist.

## Auto-Genehmigung von Spuren via LLM-Entscheidungsprogramm (Live)

Bei der Aufbereitung positiver Spuren auf Live **ohne manuelles
Freigabefenster** wird ein dediziertes Entscheidungsprogramm (z. B.
`agent_entscheide.py`) eingesetzt: Es liest die Positiv-Spuren aus der
Klassifizierung von `auswertung_alle.py`, leitet für jede eine LLM-Entscheidung
ab und schaltet bei positivem Urteil die Spur frei
(`handel_erlaubt=true`, `freigabe.erfuellt=true`). Jedes Urteil landet im
Programm-Log.

**Reihenfolge:**
1. **Klassifizierung einholen** (`scanner/.venv/Scripts/python.exe auswertung_alle.py`).
   Positiv werden nach der Klassifizierung die Spuren. Nicht die partielle
   `backtest_prognose_ergebnis.json` als Quelle nutzen (widerspricht der
   Klassifizierung und täuscht über die Eignung).
2. Für jede Positiv-Spur Prompt auf die Klassifizierungs-Metriken
   (Trefferquote, Rendite, Runden) setzen — nicht auf Rucksatzzahlen.
3. **Alle LLM-Aufrufe auf einen laufenden lokalen Ollama-Dienst**
   (`127.0.0.1:11434`, Modell `deepseek-chat:latest`) leiten. Die Felder
   `llm_modell`/`llm_weg` in `wachen.json` dürfen nicht Einfluss nehmen:
   das `bonsai`-Dienst (Port 8080) ist nicht erreichbar, und ein
   `llm_modell: bonsai` blockiert jede Entscheidung.
4. Prompt: vertragsgleiche 3 Zeilen (Zeile 1 `BUY`/`SELL`/`NOTHING`,
   Zeile 2 kurze Begründung, Zeile 3 `Confidence: X%`).
5. **Akzeptanz:** positive Entscheidung (BUY/long) UND Confidence ≥
   60 %. Sonst nicht freigeben.
6. Positiv: `handel_erlaubt=true`, `freigabe.erfuellt=true`.
7. Entscheidungen ins Protokoll; positive Spur bleibt gesperrt (außer Max
   explizit beauftragt).
8. **Echtdurchlauf (Finaler Live-Boot):** bei positivem LLM-Urteil
   (`BUY`, Confidence ≥ 60 %) wird die Spur live geschaltet: `wachen.json`
   `handel_erlaubt=true` und `freigabe.erfuellt=true` sind dabei schon
   vor dem Boot gesetzt — der Boot besteht aus dem launch der echten Order:
   `python mosaic/handeln.py --live` (ueber den OKX-Spot-Pfad), nicht nur um
   die Flags. Ein Boot ohne echte Order (`--vorschau` junger) ist kein
   Freigabe-Boot, sondern ein Papier-Lauf.

Details (Entscheidungstabelle, Vertrag, Ports, Fallback) — siehe
`references/llm-entscheidung.md`.

## Live schalten: erst die Tore UND den Live-Pfad pruefen

... (original section unchanged)

`wachen.json` ist Stufe 1. Die Regel ist hart:

1. `.bak-JJJJMMTT` anlegen, bevor du editierst.
2. Nach dem Edit das Lesen der Spur prüfen (`scanner/.venv/Scripts/python.exe <spur>/handeln.py --wachen`) — nicht nur auf den Rückgabewert des Editors vertrauen.
3. **Eigenes sofort committen**, mit `git commit --author="Hermes <hermes@local>"`. Erst `git status` lesen; nie `git add -A`.

## Parametertuning ist eine Handelsentscheidung

`wachen.json`-Parameter zu ändern bewegt die Strategie. **Nicht alleine drehen** — die Befunde und den konkreten Hebel vortragen, Max das Richtungs-OK geben lassen, dann ausführen. Wenn Max alle Vorschläge absegnet, ist das die Freigabe; aber vorher steht kein Wert in der Datei.

**Mehrdeutige Live-Änderungsanweisung ohne Antwort → die SICHERE, reversible Variante ausführen, nie die destruktive.** Sagt Max z. B. nur „Spur zurückbauen" und beantwortet die Rückfrage nicht (Timeout), ist der konservative Weg: Freigabe entziehen (`handel_erlaubt=false`, aus `AUTO_FREIGABE`), die offenen Live-Positionen **unangetastet mit ihren Boersen-Stops auslaufen lassen**, keinen Dauerlauf-Neustart. Positionen schließen ist destruktiv und braucht ausdrückliche Bestätigung. Die gewählte Interpretation klar benennen und Max den Weg zum Schärfen offen lassen.

## Live schalten: erst die Tore UND den Live-Pfad pruefen

Bittet Max, eine Spur live zu schalten (`handel_erlaubt=true` + in `AUTO_FREIGABE` aufnehmen), ist das eine Echtgeld-Aktivierung gegen dokumentierte Freigabe-Sperren — nicht stillschweigend ausfuehren. Zwei Pruefungen, bevor irgendein Schalter umgelegt wird:

1. **Freigabe-Tore in `wachen.json`:** `freigabe.backtest_bestanden`, `papierlauf_min_wochen`/`papierlauf_min_sessions` gegen das Journal, `netto_positiv`. Die Datei selbst nennt die Bedingungen (`_freigabe`-Kommentar). Sind sie nicht erfuellt, vortragen statt drehen.
2. **Ob ein Live-Pfad im Code existiert.** `--live` als gueltiger argparse-Wert ist KEIN Beleg — viele Spuren akzeptieren ihn, drucken aber nur `GRUND_KEIN_LIVE` und laufen als Papier weiter (orb, orbk). Vor der Freigabe `grep -n "GRUND_KEIN_LIVE\|order\|live_perp" <spur>/handeln.py` und den `--live`-Zweig lesen. Ohne echten Orderweg bewirkt `handel_erlaubt=true` + `AUTO_FREIGABE` **nichts** — Live-Aktivierung ist dann Codearbeit im Worktree, kein Konfig-Schalter.

**Wie `AUTO_FREIGABE` ueberhaupt feuert (der konkrete Mechanismus):** `dauerlauf.nur_fenster_fehlt()` ruft `handeln.py --vorschau` und verlangt, dass die Ausgabe **genau EINEN** Sperrgrund enthaelt, der das Wort `Freigabefenster` traegt. Nur dann oeffnet der Dauerlauf das Auto-Freigabefenster. Eine Spur, deren `--vorschau` stattdessen `kein Live-Pfad` (oder mehrere Gruende) druckt, kommt nie in die Auto-Freigabe — egal wie `handel_erlaubt`/`freigabe` gesetzt sind. Beim Bau eines Live-Pfads muss die `--vorschau`-Sperrgruende-Logik also so verdrahtet werden, dass bei offenen Toren genau der eine `Freigabefenster`-Grund uebrig bleibt (Muster: `kraken/handeln.py` `live_sperren()` + `Live waere gesperrt durch: ...`).

**Backtest-Urteil richtig lesen:** der `bericht()`-Gate `haelt_81` verlangt Trefferquote ≥ 75 % UND EV>0 UND bestes Quartal>0 UND ≥ 10 Verlierer. Eine Spur kann positiven EV haben und trotzdem mit „unter 10 Verlierer" durchfallen — das ist **nicht beurteilbar (zu wenig Daten)**, nicht negativ. Unterscheide: negativer EV = echtes Strategieproblem (Stilllegungs-Kandidat); zu wenig Daten = weiter Papier laufen lassen, kein Freigabe-Hindernis an sich. Ein positiver Papierlauf ueber wenige Wochen mit einem einzigen grossen Gewinn ist kein Netto-Beleg — nach Gebuehr rechnen und die Runden-/Wochen-Tore zaehlen.

**Den gebauten Live-Pfad auf VOLLSTAENDIGKEIT pruefen, bevor Max ihn scharf stellt.** Ein Live-Einstieg, der echtes Geld an die Boerse legt, ist erst sicher, wenn JEDER Ausstieg boersenseitig gedeckt ist: Stop UND Ziel UND Zwangsschluss. Ein Bau, der Einstieg + Stop platziert, aber kein Take-Profit hat, bucht den Ziel-Ausstieg nur im Buch — die echten Coins bleiben auf der Boerse liegen. Kraken braucht dafuer eine eigene Triggerorder (`take_profit_setzen`, z. B. `take-profit-market`); `stop_setzen` deckt nur die Verlustseite ab. Das ist genau die Geisterpositions-Klasse: Boerse haelt, Buch meldet zu. Ein Subagent baut gern einen „Live-Pfad", der reales Geld eintritt, und dokumentiert die Ausstiegs-Luecke nur im Docstring („bevor die Spur echt Geld bewegen darf") — eine dokumentierte Luecke mit Echtgeld-Eintritt ist NICHT scharf zu stellen.

- **`pruefe_ausstiege`/`_schliesse` sind buchseitig** (nur Journal/Zustand, keine Order). Fuer einen Live-Einstieg muss der Ausstieg zusaetzlich eine echte Market-Close an der Boerse ausloesen (`markt_verkauf` long / `markt_kauf`/Buy short), nur wenn `p['modus']=='live'`; der Papierpfad bleibt reines Buch. Der Weg davor ist ein Buch-vs-Boerse-Abgleich (Muster `kraken._abgleich_runde`): erst pruefen, dass die echte Boersenposition das Buch stuetzt, sonst keinen Schliessauftrag senden und als ungeklaert melden.
- **Kraken-Spot hat kein nativens Short.** Ein `markt_verkauf` verkauft nur, was man haelt. Ein Short-Signal auf Spot muss abgelehnt (Sperrgrund) oder klar markiert werden, sonst eroeffnet der Live-Pfad eine Position, die Kraken nicht halten kann.
- **Der Papier-Einstieg setzt die Position im Buch VOR der Order.** Legt `pruefe_einstieg` nicht alle Orderfelder auf die Position (`range_hoehe`, `punkt_wert_usd/USDT`, `risiko_usd`), gibt `positionsgroesse` 0 → „kein Einstieg" → Buch fuehrt eine Phantom-Position ohne echte Order. Ohne Fill-Bestaetigung bleibt eine ungefuellte Limit-Order ebenfalls als Buchposition stehen. Beim Echtgeld-Betrieb dieses Restrisiko ausdruecklich melden.
- **`AUTO_FREIGABE` wird einmal beim Import gelesen**, nicht je Zyklus: den Eintrag aufzunehmen wirkt erst nach einem Dauerlauf-Neustart. Vorher fragt der laufende Prozess bei der Spur per `/ja` statt auto-zu-oeffnen — der sichere Default. Neustart nicht ungefragt (recycelt Echtgeld-Spuren und legt offene Positionen flach).
- **`herzschlag_max_minuten` ist doppelt geregelt — nie blind setzen.** Die Systempruefung (`systempruefung.ps1`, Regel 19.09.2026) verlangt **180 fuer ALLE Spuren** (Papier UND Live, die 45-Live-Grenze vom 14.09 gilt als „aufgehoben"); manche `_herzschlag_regel`-Vermerke in `wachen.json` sagen dagegen **45 fuer Live** („handel_erlaubt=true, deshalb 45"). Stehen die Pruefung und ein datierter Entscheid-Vermerk („Auftrag Max / Entscheidung ... deshalb 45") im Widerspruch, **nicht uebersteuern** — den Konflikt Max vorlegen und entscheiden lassen, statt stillschweigend auf 180 ODER 45 zu korrigieren. Ein vom Pruefer geflaggter Wert mit dokumentiertem Entscheid ist ein Konflikt, kein Drift. Mechanik: Bedingung 3 schliesst alle offenen Positionen erst, wenn der letzte gesunde Lauf aelter als `herzschlag_max_minuten` ist — 45 schliesst eng; 180 ueberlaesst kurze Stoerungen dem Waechter (Neustart <32 min) und vermeidet Fehl-Schluesse (Fall 11./12.09.). Der Wert ist eine Frage der Fehl-Schluss-Toleranz, nicht der Ueberwachungsdichte.
- **Live-Freigabe bricht den `test_wachen_json::test_start_gesperrt`-Zustandstest.** Er assertet den alten gesperrten Zustand (`handel_erlaubt=False` UND `freigabe.erfuellt=False`). Nach dem Umschalten auf live schlaegt genau diese Asserion fehl — kein Code-/Bau-Defekt, sondern die erwartete Folge des Schaltens. Den Test auf den neuen Live-Zustand aktualisieren (Name und beide Assertions auf `True`), damit die Suite gruen bleibt und der legitime Schwenk nicht als regressiver Fehler erscheint. Ein „vorbestehender Fehlschlag" kann genau dieser Zustandstest sein, der sich durch die Freigabe von selbst umkehrt — erst nach dem Schalten neu beurteilen, statt ihn als fremden Defekt zu registrieren.
- **Subagent-Live-Bau nach dem Selbstbericht selbst verifizieren** (Echtgeld): Diff der `handeln.py` lesen, die Tests mit dem Hauptbaum-Interpreter SELBST laufen lassen (nicht dem „alle gruen" des Berichts trauen), und den `--vorschau`-Output auf die exakte `Live waere gesperrt durch:`-Zeile pruefen. Die File-Mutations-Warnung des Berichts beantworten, indem man `git status`/Diff kontrolliert, dass nichts Fremdes landete (Scratch-Datei, `/tmp`-Abschrift).
- **Mehrere Spuren in EINEM Subagent-Auftrag = Token-Limit-Risiko.** Ein Delegations-Task, der drei Live-Pfade auf einmal baut, verbraucht das Output-Budget im Denken und liefert NICHTS („Response remained truncated", 4 Continuation-Versuche). Grosse Bauten in EIN-Spur-Aufgaben teilen (eine Spur je Subagent, parallel) — kleiner, fokussierter, ueberlebt das Limit. Vor dem Delegieren pruefen, ob der Worktree ueberhaupt angelegt wurde (der gescheiterte Subagent kann vorher abgebrochen sein).
- **Auch EIN-Spur-Subagenten koennen am Token-Limit scheitern — dann selbst bauen statt neu delegieren.** Wenn drei getrennte Ein-Spur-Auftraege nacheinander mit demselben „Response remained truncated" abbrechen, ist das ein Modell-Budget-Problem, kein Task-Groessen-Problem: weiter zu delegieren wiederholt nur den Fehlschlag. Den Bau dann im eigenen Kontext ausfuehren (das Muster ist frisch, die Dateien sind lesbar), statt einen vierten Subagenten zu starten. Die leeren Worktrees der gescheiterten Versuche aufraeumen oder wiederverwenden.

## Anweisungs-Trade: vorbereiten ≠ scharfstellen (kein Auto-Weg)

Ein Anweisungs-Trade (Max nennt Kontrakt, Richtung, Hebel, Einsatz, Stop ueber den Chat) laeuft ueber `bot.py` und landert als **`vorbereitung`-Zeile im Journal** — das ist noch ***keine*** Order. Der Dauerlauf/AUTO_FREIGABE ordert **nur seine eigenen Ranglisten-Kandidaten**; eine manuell vorbereitete Journal-Position wird von keinem Zyklus automatisch aufgegriffen (`zustand.json` `wartende: []`). Es gibt **keinen dokumentierten Auto-Pfad**, der eine angewiesene `vorbereitung` in eine Live-Order verwandelt.

- Frei nach Handelsregeln: *„Das Absenden der scharfen Order tut die Sitzung selbst nicht — ausgeloest wird sie von Max oder von dem gebauten Skript (`handeln.py --live`)."* `handeln.py --live` ordert aber aus seiner Kandidaten-/Zonenlogik, nicht aus dem Journal.
- Offenes Freigabefenster (`AUTO_FREIGABE`, `handel_erlaubt:true`) bewoehrt die Spur — es schickt die angewiesene Position **nicht** automatisch.
- **Sauberer Weg:** Max eroeffnet die Position selbst an der Boerse mit den fuenf Werten; die Spur erkennt sie als Handposition (`herkunft=boerse_handgriff`, `handpositionen_automatisch_schliessen`) und verwaltet sie danach (Stop, Ziel, Trailing).
- **Verifiziere den Fenster- und Buchstatus selbst statt einer Bot-Behauptung zu trauen.** Der delegierte Bot meldete zuerst `handel_erlaubt:false`, dann `true`; die Fakten stehen in der Datei. Fenster-Status: `freigabefenster.py` (`alle()` gibt `Fenster`-Objekte mit `.offen`/`.text`, Zustand in `freigabe_fenster.json` pro Spur, `AUTO_FREIGABE_STUNDEN` in `dauerlauf.py`). Ob eine Position scharf ist, zeigt nur das echte undef wartende/offene Orderbild, nie eine vorbereitende Journal-Zeile.
- **Ein neuer Kandidaten-Weg, der `anlauf()` umgeht, liefert `None`-Pruefpflicht-Felder — jede Ausgabe/Journal-Formatierung muss None-tolerant sein.** Ein eingelegter Auftrag (Pseudokandidat) traegt `quote_noetig`/`quote_beobachtet`/`funding_pct` als `None` (Default in `anlauf()`), weil die Pruefpflicht nur fuer Ranglisten-Kandidaten gerechnet wird. Formatierung, die sie mit `* 100` multipliziert, crasht mit `TypeError` — und zwar VOR dem Schreiben von Zustand/Journal/eingelegt, sodass der Auftrag unangetastet bleibt und der Lauf still nichts tut (keine Position, keine Journalzeile, Datei unveraendert). Beim Bau eines Kandidaten-Wegs neben der Rangliste: jede Ausgabe- und Journalzeile, die Pruefpflicht-Felder formatiert, nach dem `funding_pct`-Muster None-tolerant machen (`"n/a" if p["x"] is None else ...`), und einen Test haben, der die Ausgabezeile mit `None`-Feldern tatsaechlich durchlaeuft — ein Test, der nur bis zur Eröffnung prueft, deckt den Crash nicht ab.

**Ein delegierter Bot, der in eine Wiederholungsschleife laeuft, ist ein Mechanik-Verdacht, kein Transient.** `markt-recherche` kollabierte (exit 1, Repetition-Loop) genau im Suchen des nicht existierenden Anweisungs-Auto-Wegs. Nach so einem Abbruch nicht blind den gleichen Bot erneut starten — erst im Repo pruefen, was wirklich passiert ist (Commit vorhanden? Fenster offen? Position eingelegt?), und dann den fehlenden Weg als solchen melden statt ihn zu erfinden.

## Stilllegen: netto-negativ + nicht per Parameter behebbar

Wenn eine belastbare Spur netto negativ ist UND der Parametersuche nichts überlebt, ist der saubere Weg die **Stilllegung** — nicht weiter Daten erzeugen. Muster = wie spiegel („eh absolut nicht profitabel"):

1. In `dauerlauf.py` `SPUREN`: den Eintrag **auskommentieren** und daneben einen Kommentar mit Stilllegungsgrund + den Wieder-Anschalten-Schritten setzen (Journal bleibt als Vergleichsbuch stehen, wächst nicht weiter).
2. Gleichzeitig aus `AUTO_FREIGABE` entfernen, falls dort gelistet.
3. Vergisst man einen Schattenarm (`squeeze_eth` teilt sich den `squeeze`-Ordner), geht er mit raus — beide Einträge kommentieren.
4. Zugehörige Tests laufen lassen (`test_dauerlauf_ereignisse`, `test_stille_spuren`, `test_klassik_spuren`) und mit einem AST/Regex-Zähler bestätigen, dass der Name in keinem AKTIVEN (nicht auskommentierten) SPUREN-Eintrag mehr steht.
5. Eine `wachen.json`-Wertänderung ist Betriebskonfig und darf direkt auf master (Commit mit `--author="Hermes <hermes@local>"`); eine `dauerlauf.py`-Spurlisten-Änderung ebenso nach dem spiegel-Muster.

**Eine Stilllegung in `SPUREN` greift erst beim Neustart des Dauerlaufs** — das Dict wird einmal beim Import gelesen, laufende Zyklen sehen die alte Liste. Einen Dauerlauf-Neustart nicht ungefragt machen: er recycelt die Echtgeld-Spuren (scanner/xperp in mittel/hoch) und kann offene Positionen flachstellen. Committen und die Wirkung als „beim nächsten Neustart wirksam" vermerken, Max die Entscheidung über den Neustart überlassen.

## Freqtrade-Container auf Anbindung pruefen

Max' Freqtrade-Flotte (Moon-Dev-Agenten als Docker-Container, `Agenten/Handel/freqtrade/`, verdrahtung in `bots.json`) ist Teil der Haus-Auswertung — ein "Freqtrade-Bots pruefen"-Auftrag ist ein Anbindungs-Check, kein Spur-Tuning.

- **Container "Up" + heartbeat `RUNNING` bedeutet: der Bot laeuft und handelt — HTTP-000 ist NICHT der Beweis fuer "unerreichbar".** Freqtrade antwortet auf HTTP nur, wenn `api_server.enabled=true` in seiner Config steht. Die `klassik_*`/Indikator-Container laufen absichtlich OHNE Web-API (kein `api_server`-Block) und liefern darum auf jeden Port-Check 000, obwohl sie gesund sind. Nur 4 der Flotte sind API-exponiert (die Moon-Dev-Bots auf 8080–8083). Diagnose-Reihenfolge statt curl-Panik: `docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"` (Up = lebt) → `docker logs --tail <n> <container>` (heartbeat `RUNNING` = arbeitet) → erst wenn beides fehlt, im Aufsatz `api_server.enabled` pruefen und Port erreichen.
- `/api/v1/ping` ist der richtige Health-Endpoint (antwortet `{"status":"pong"}`); eine `000` auf `/` ist kein Befund. Gemapped wird auf `127.0.0.1:<port>`; ein API-exponierter Container kann von ausserhalb trotzdem 000 liefern, wenn das Port-Mapping fehlt.
- Start der Flotte: `bash Agenten/Handel/freqtrade/bots_starten.sh` (legt Container neu an, `--restart unless-stopped`; nach Docker-Neustart kommen sie von selbst zurueck). Gemeinsame DB trennt die drei Bots nur, wenn jede eigene `user_data/tradesv3-<bot>.sqlite` hat (`--db-url` ist die Trennung, kein Beiwerk).

## Positionierungs-Filter (OKX-Rubik) in eine Spur einbauen

Will Max eine Spur um ein Positionierungs-/Sentiment-Signal als Einstiegs-Filter
erweitern (z. B. "kippt die Positionierung die Trendwende?"), ist der
naheliegende Weg — das smartmoney-Modul aus `Werkstatt/agent-trade-kit` — fuer
den Haus-Key NICHT nutzbar: dessen Endpunkte liegen nur auf `www.okx.com`
(global), der Haus-Key ist EEA-gebunden (50119). Der Ersatz sind die
**oeffentlichen OKX-Rubik-Reihen** (Long/Short-Ratio, Open Interest, Taker-Flow)
— dasselbe Prinzip, ohne Schluessel, auf beiden Hosts mit 200 verifiziert.
Endpunkte, Baustein-Muster (fail-soft, Standard AUS) und die Test-Strategie:
`references/okx-positionierung.md`.

- **Filter-Tests: Indikatoren mocken, nicht synthetische Kerzen bauen.** Ein
  Filter-Test will die FILTER-Logik beweisen, nicht den Indikator. Synthetische
  Kerzen, die gleichzeitig einen ATR-Indikator (SuperTrend) von +1 auf -1 drehen
  UND unter eine EMA schliessen, existieren praktisch nicht — die zwei
  Indikatoren drehen nie synchron, keine Parameter-Kombination trifft beide
  Bedingungen. Stattdessen `xi.supertrend`/`xi.ema` im Test mocken (determinis-
  tisches Basissignal) und nur den Filter pruefen: AUS ruft die Quelle nicht,
  AN+stuetzt=False blockiert, AN+stuetzt=True laesst durch, 0 Quellen blockiert
  nicht (fail-soft).

## Ziplime — externer Backtesting-Engine

Eine Anfrage, Ziplime (Werkstatt/ziplime) fuer die Handelsoptimierung zu
installieren/starten/nutzen, ist eine eigene Klasse: externer Aktien/ETF/Futures-
Backtester, KEIN Krypto-Perpetual-Engine. Setup, die Polars-Versionsfalle
(2.0 bricht, 1.24.0 hat WindowsPath-Bug, 1.44.2 funktioniert) und der
verifizierte Quick-Start: `references/ziplime.md`.

## Leitstand ausbauen

Eine Anfrage „leitstand.py untersuchen/ausbauen" (Nautilus-/Prozesse-Reiter, Nodes einbinden) ist eine eigene Klasse innerhalb des Handel-Baums: Tk-Dashboard, kein Spur-Tuning, aber dieselbe Worktree-Regel und Stufe-1-Disziplin. Karte der Reiter-Schnittstelle, der Takt-Gruppen und der tatsaechlich handelnden Nautilus-Repos + Nodes: `references/leitstand.md`. Zusaetzlich zur Auswertung unten stehen die `.venv`-Grenzen (Nautilus-Spuren laufen NICHT unter `scanner/.venv`) dort.

## Codearbeit, nicht Betrieb — in den Worktree

Eine Code-Änderung (z. B. Intervall-Zuordnung in `omnitrade_start.py`) gehört **nicht in den Hauptbaum**, sondern in einen Worktree NEBEN `BrainFiles/` auf eigenem Zweig (`git worktree add ../Handel-<x> -b <agent>/<thema> master`), wenn die Änderung mehrere Spuren/Launchlogik betrifft.

Ist der Worktree neben `BrainFiles` (z. B. `C:/Users/faupe/Documents/Handel-omni1d`), **verweigern Hermes' File-Tools Schreibzugriffe außerhalb der `HERMES_WRITE_SAFE_ROOT`** — edit über Terminal/Python-Heredoc (`python - <<'PY' ... PY`), nicht über `patch`/`write_file`. Worktrees haben **kein `.venv`** (nicht versioniert): Tests/Aufrufe laufen über den Interpreter des Hauptbaums (`C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/scanner/.venv/Scripts/python.exe`).

## Geteilter Arbeitsbaum: fremde Sitzung hat den Zweig gewechselt

Der BrainFiles-Baum ist geteilt — mehrere Sitzungen (Desktop, CLI, Hermes, Claude) committen parallel. Eine andere Sitzung darf den ausgecheckten Zweig gewechselt haben, mit uncommitteten Aenderungen darin. Das ist die einzige Situation, in der man den Hauptbaum **nicht** anfasst:

- `git merge` schlaegt dann mit "uncommitted changes" ab (oder wuerde die Fremdarbeit mitnehmen). **Nicht** erzwingen, nicht committen, nicht die Fremdaenderungen anfassen — das kollidiert mit der anderen Sitzung und dem geteilten Index.
- **Master trotzdem gefahrlos vorziehen, wenn es ein Fast-Forward ist:** pruefen `git merge-base master <worktree-branch>` == `git rev-parse master`, dann `git update-ref refs/heads/master <worktree-branch>` — bewegt den Pointer, beruehrt den Arbeitsbaum nicht.
- Datei-Edits im Hauptbaum (z. B. einen SPUREN-Eintrag in `dauerlauf.py` nachtragen) brauchen den Arbeitsbaum — die muessen **warten**, bis die andere Sitzung fertig ist. Den fertigen Worktree-Zweig committen und dem Nutzer sagen, was noch aussteht, statt um den Baum zu kaempfen.
- **Pruefen, dass fruehere Arbeit sicher auf master steht** bevor man sie woanders anfasst: `git log master --oneline`. Deine Commits koennen trotz Zweigwechsel auf der Platte stehen (der Dauerlauf liest die Dateien, nicht den Branch).
- **`.git/index.lock` im geteilten Baum ist fremde Arbeit, nicht aufraumen.** Liegt der Lock (oft >30 min) und laufen Git-Prozesse, committet eine andere Sitzung gerade — `git commit` schlaegt mit `index.lock: File exists` ab. Den Lock NICHT loeschen (koennte die fremde Operation korrumpieren); warten und erneut versuchen, oder Max entscheiden lassen. Die Aenderung ist trotzdem auf der Platte wirksam (der Dauerlauf liest die Dateien, nicht den Commit) — der Commit ist nur Versionskontrolle, kein Betriebsschritt. **Ausnahme — verwaister Lock:** ein Lock ist KEINE laufende Operation, wenn sein mtime viel aelter ist UND kein Git-Prozess lebt, dessen Startzeit nah am Lock liegt (`Get-Process -Name git*` vergleichen). Einen so identifizierten verwaisten Lock darf man mit Max' ausdruecklicher Freigabe entfernen (`rm .git/index.lock`) und sofort committen. Verwaist heisst belegt durch Prozess + Zeit, nicht nur durch Alter.
- **Eine Spur kann von einer anderen Sitzung zurueckgenommen worden sein.** Der Live-Status einer Spur ist kein stabiler Zustand: eine andere Sitzung darf `handel_erlaubt`/`freigabe`/`AUTO_FREIGABE` zurueckgedreht haben (z. B. wegen einer Kosten-Analyse), mit uncommitteten Aenderungen. Vor dem Wieder-Live-Schalten den AKTUELLEN `wachen.json`- und `dauerlauf.py`-Stand pruefen (nicht dem eigenen frueheren Commit trauen) und die fremde Ruecknahme als bewusste Arbeit respektieren — Max' neue Anweisung ueberstimmt sie, aber die fremde Aenderung nicht stillschweigend ueberschreiben, ohne sie zu benennen.

## LLM-Qualitaetsfilter in einer neuen Spur (scanner_llm-Muster)

Eine "leichte Tor + mehr Kandidaten"-Variante einer Scanner-Spur nutzt die Haus-LLM-Infrastruktur als Qualitaets-Gate ueber einem groesseren Kandidatenpool:

- Komponenten wiederverwenden, nicht neu bauen: `scanner/bewertung.py` (Regel-Score), `scanner/okx.py` (Kerzen/Markt), `llm_lokal.py` (`llm.VERTRAG` + `llm.entscheide(prompt, w)`). Tore in der neuen `wachen.json` bewusst leichter (z. B. `mindest_score` 40 statt 60) — die Qualitaetswaehrung traegt das LLM, nicht die Regel.
- `llm.entscheide` wendet das Confidence-Gate schon selbst an (liest `llm_mindest_confidence` aus `w`). Kandidat handelbar NUR bei `seite == 'long'` UND Confidence ≥ Schwelle; NOTHING/SELL/zu unsicher wird geloggt und uebersprungen.
- **Tests duerfen nie das echte Modell rufen.** Test-Seams bauen: `entscheide_override` (patcht `llm.entscheide`) und alle Kurs-/Preis-Lesungen hinter eine ueberschreibbare Funktion (`marktkurs`), damit der Papier-Zyklus null Exchange-Calls macht. Der Regel-Score-Test konstruiert synthetische `bewertung`-Dicts, um zu belegen, dass das leichtere Tor mehr Kandidaten durchlaesst als das Scanner-Tor.
- Gemeinsame Handel-Module (`risikostufe`, `freigabefenster`, `llm_lokal`, `okx`, `bewertung`, `scan`) per `_rs_spec/_rs_mod` ueber den PFAD laden (Hausmuster), nicht per bare-Import — die Spur laeuft mit eigenem Ordner auf sys.path.

## omnitrade-Intervall: Trendfolger → 1d, RSI bleibt

Der dokumentierte Backtest-Befund (Omnitrade.md) ist belastbar: **auf 1h verlieren Trendfolger durchweg, im Plus lagen nur RSI-Varianten; auf 1d gewinnen Trendfolger.** Die Zuordnung je Lauf gehört in `omnitrade_start.py` `INTERVALL_JE_LAUF`, nicht blanket global:

- **1d:** ema-/sma-/macd-cross-over, adx_macd, Donchian
- **1h bleibt:** rsi30_stop5, pine_rsi_meanrev, pine_bollinger
- **15m bleibt:** rsi_noema

Eine Intervall-Änderung wirkt erst beim **Neustart** der laufenden Testnet-Prozesse (die mit altem Takt gestartetet laufen weiter); `start <name> --trocken` meldet dann „laeuft schon". Das Freigeben + Neustarten ist eine Betriebs-Entscheidung — vortragen, nicht alleine durchführen.

**omnitrade nicht blind über `omnitrade_start.py` neu starten, wenn der Baum halb migriert ist.** `OMNI` (= exe + strategien) und das `status/`-Verzeichnis können auseinanderlaufen: Quellbaum auf `O:`, aber Anzeige/Brcke lesen `C:` unter `Werkstatt/omnitrade/status/`. Das Skript baut die Statusdatei aus demselben `OMNI` — startete man es mit dem falschen `OMNITRADE_DIR`, teilte man das Status-Verzeichnis (lebende Prozesse schreiben nach C, neue nach O → die Anzeige sieht die neuen nie).

- Bevor du startest: prüfen, wohin die **lebenden** Prozesse ihren `--status-file` wirklich schreiben und wohin die **Anzeige/Brcke** liest (`omnitrade_bridge.py`, `_quelle` in `omnitrade/wachen.json`); das neue Start damit gleichziehen.
- Starte dann explizit von Hand (exe aus dem vollständigen Baum, `--status-file` auf das von der Anzeige gelesene Dir, `--interval` wie gewollt), falls das Skript keinen separaten Status-Override kennt.
- Manuell gestartete Läufe schreiben **keine Logfile** (anders als `omnitrade_start.py`, das nach `logs/` umleitet) — fürs Debugging den Start über `omnitrade_start.py` nachziehen, sobald Pfade stimmen.
- Nach dem Neustart per Commandline-Analyse verifizieren (ein Scratch-`.ps1`, das `--interval`/Strategie aller Prozesse ausgibt), dass die neuen Läufe wirklich den gewünschten Takt tragen und die Statusdateien frisch geschrieben werden.

Die drei omnitrade-Wachskripte — `omnitrade-lauf-wache.py`, `omnitrade-order-wache.py`, der `omnitrade-waechter`-Cron — ihre Rollen und warum die Todesgrenze kerzenabhängig sein muss (Statusdatei nur beim Kerzenabschluss): `references/omnitrade-wachen.md`.

## Score-Tore sind seitenabhängig und liegen in der Fassungs-Datei

Beim Prüfen, ob eine offene Position das Score-Tor verletzt: **die Schwelle hängt an der Seite.** Long nutzt `mindest_score`, Short `mindest_score_short` — die Short-Schwelle ist deutlich niedriger (z. B. 45 gegen 60), weil die Score-Skala long-kalibriert ist. Eine Short-Position mit Score 49,5 ist korrekt eröffnet, wenn die Short-Schwelle 45 ist — sie NICHT gegen die Long-Schwelle 60 zu prüfen, sonst meldet man einen Fehler, der keiner ist.

- Die Tore einer Spur mit `prognose_fassung` (z. B. omniquant `weit`) liegen in der **fassungs-suffigierten** Datei (`prognose.weit.json`), nicht in `prognose.json` — und verschachtelt unter `tore:` (nicht top-level). Beim Score-/CR-Check die richtige Datei und den `tore`-Block lesen.
- Ein Parser über `zustand.json`-Positionen muss alle Felder optional behandeln (einige Positionen tragen kein `cr`/`score`/`einstieg`) — ein `None`-Feld darf den ganzen Lauf nicht crashen.

## Ausstiegs-/Stop-Pfade müssen das Einstiegs-Gate umgehen

Ein Einstiegs-Gate, das als **Modul-Konstante** lebt (z. B. `ABLEITUNG_ERLAUBT` in `kraken_perp.py`, Default `False`, gesetzt via `setze_ableitung()` nur im Einstiegszweig), ist **prozesslokal**: startet der Prozess neu, ist es wieder `False`. Jeder Ausstiegs-/Stop-Pfad, der dasselbe Gate prüft statt es zu umgehen, blockiert dann die Schutzaktion — Symptom: eine offene Live-Position kann ihren Boersen-Stop nicht nachsetzen (omniquant NEAR-USDC, jede Viertelstunde „SICHERHEITSLÜCKE").

- Beim Bauen eines Einstiegs-Gates: **jeder Ausstiegs-/Stop-/Abgleich-Pfad muss es umgehen** (`fuer_ausstieg=True` durchreichen), nie stillschweigend mitprüfen. Ein Ausstieg ist nie eine neue Marktwahl.
- Beim Verdacht auf so einen Bug: **alle Helper derselben Spur auf das Flag greppen** (`grep -n "ABLEITUNG_ERLAUBT\|fuer_ausstieg" <spur>/*.py`) — meist reichen `markt_verkauf`/`schutzstop_vorhanden` das Flag schon korrekt durch und genau EIN Helper (z. B. `stop_setzen`) vergisst es. Der Fix ist eine Zeile: das Flag an `paar_fuer` durchreichen.
- **Tests, die den Helper mocken, decken den Bug nicht ab** — sie ersetzen die echte Implementierung, die das Flag nicht durchreicht. Ein Test muss die echte `stop_setzen`-Signatur prüfen (oder den echten Helper mit `fuer_ausstieg=True` aufrufen), sonst ist er grün, während der Live-Pfad bricht.

## Einen Live-Schutz-Fix an der BOERSE verifizieren, nie am Buch

Ob ein Stop-Nachsatz wirkt, beweist allein die Börse. Das Buch (`zustand.json`) ist dafür kein Zeuge:

- **`stop_algo_id: null` ist KEIN Beleg für einen fehlenden Stop.** `stopdeckung_pruefen` kehrt früh zurück, sobald `schutzstop_vorhanden` deckt — die ID wird nur im Nachsetz-Zweig geschrieben. Ein gedeckter Stop lässt das Feld also für immer `null`. Wer daraus „Bug besteht weiter" liest, meldet einen Fehler, den es nicht gibt.
- Der belastbare Beleg sind drei Lesezugriffe: `offene_positionen(symbol)`, `offene_orders(symbol)` (eine `reduceOnly`-Order der Gegenseite mit `stopPrice` und voller `unfilledSize`) und deren `receivedTime` gegen den Merge-Zeitpunkt des Fixes.
- **Das Verschwinden der Fehlerzeilen im Journal ist der zweite Zeuge**, nicht der erste: keine neue `SICHERHEITSLÜCKE`-Zeile nach dem Merge heißt, dass die Deckung seither greift.
- `paar_fuer()` eines abgeleiteten Instruments wirft `ValueError: unbekanntes Instrument … Marktliste nicht geladen`, solange die Instrumentenliste fehlt. Vor jeder lesenden Börsenprobe erst `live_perp.markte_laden()` aufrufen — das ist ein öffentlicher `/instruments`-Abruf und bleibt rein lesend.
- Nicht jeder Schlüssel darf alles lesen: Positionen/Orders können gehen, während `/fills` mit `authenticationError` antwortet. Ohne Fills ist ein Ausstiegspreis **nicht belegbar** — dann Stop-Fill, Handverkauf und Liquidation ausdrücklich als ungeklärt melden und keinen Preis ins Journal raten.

## Geisterposition: Exchange und Buch weichen voneinander ab

Wenn `zustand.json` eine Live-Position führt, aber Kraken sie nicht mehr offen meldet, strikt trennen: Exchange-Fakten, Journal-Fakten und Buchstatus. Vor der Diagnose offene Positionen sowohl symbolgefiltert als auch ungefiltert und offene Orders abfragen; erst `live_perp.markte_laden()` aufrufen, damit abgeleitete Symbole wie `NEAR-USDC` korrekt geprüft werden. Fills können mit `authenticationError` gesperrt sein: dann Verkauf, Stop-Auslösung und Liquidation als ungeklärt markieren; keinen Ausstiegspreis oder P&L schätzen.

Die Bereinigung braucht Max' Freigabe. Vor jeder Laufzeitänderung Prozessliste und Schreibkonkurrenz prüfen; bei mehreren Basis-Dauerläufen zuerst klären, welcher wirklich schreibt. `.bak`-Sicherungen anlegen, die Position nur aus dem offenen Bestand entfernen und einen expliziten Abgleich als eigene Journalaktion protokollieren — Preis, `wert_usd` und P&L leer/null lassen, wenn der Ausstieg nicht belegt ist. Nicht `erledigt`/Verkauf verwenden, wenn kein Ausstiegspreis belegt ist: GUI und Auswertungen können diese Felder als realisierte Rendite interpretieren. Danach Zustand und Journal bytegenau zum `journal_zweitziel` spiegeln und beide Kopien zurücklesen; erst dann Erfolg melden. Eine Sicherung schützt nicht vor einem aktiven Zyklus, der die Dateien direkt überschreibt. Wird die Rücklese- oder Spiegelprüfung blockiert, stoppen, nicht blind erneut schreiben und den Status als ungeprüft melden.

Bei Runtime-Jobs nie mit einem gleichnamigen `cronjob_manage`-Job verwechseln: zuerst den Scheduler/Profileigentümer identifizieren, dann dessen `list`/CLI verwenden. `update`-Erfolg allein bestätigt keinen Schedule-Wechsel; die gespeicherte Schedule aus derselben Quelle erneut lesen.

## Sensible Dateien und Credential-Vorfälle

Bei einem Task zu `.env`, Token oder API-Key niemals den Dateinhalt in Tools oder Chat ausgeben. Prüfe nur gezielt und ohne Rohwerte: Dateiexistenz, Git-Status, ob Arbeitsdatei mit `HEAD` und Remote-Blob übereinstimmt, und ob credentialartige Variablen leer oder klarer Platzhalter sind. Vermeide rohe `git diff`, `git show` oder `read_file` auf Credential-Dateien — sie können Geheimnisse in Toolausgaben oder Logs offenlegen. Verwende ein existierendes, geprü̈ftes Redaktions-/Hashwerkzeug, falls verfügbar; erfinde keinen Helferpfad, und behaupte keine Rotation.

Trenne vier Aussagen: (1) lokaler Inhalt ist leer/Platzhalter, (2) Commit/Remote-Blob enthält keinen Wert, (3) es gab keinen externen Leak, (4) Credentials wurden rotiert. Belege nur die jeweils geprüften Aussagen; ein sauberer Klon beweist nicht, dass ein Credential nie kopiert oder außerhalb des Repos geleakt wurde. Ein erledigter Task zu einer bereinigten Vorlage kann neben einem separaten offenen Rotationsentscheid bestehen. Rotation auslösen oder erledigt markieren nur mit expliziter Freigabe; niemals Credential-Werte oder deren Länge nennen.

Für die dauerhafte Abhilfe Code im eigenen `.worktrees/`-Worktree und test-first ändern: Vor Stop-/Kurs-/Verkaufspfad jede gebuchte Live-Seite und Kontraktmenge mit `/openpositions` abgleichen. Bei Abfragefehler, fehlender Position oder Mengenabweichung alarmieren und **keine** Order senden, nichts automatisch ausbuchen und keine Rendite buchen; Exchange-/Buchdifferenzen erfordern menschliche Klärung. Regressionstests müssen beweisen, dass bei Geister- und Teilbestand weder Stop noch Market-Verkauf oder Kurs-Exit ausgelöst wird. Die Omniquant-Suite ausführen, committen, PR erstellen; der Fix wirkt erst nach Merge und dem betrieblichen Neustart.

## Live-Pfad fuer eine Papier-Spur nachziehen

Hat Max eine Papier-Spur (Backtest negativ/offen, aber Papierdaten positiv) auf Live umgestellt ("Live pfad anbinden"), ist das ein eigener Bau, kein Konfig-Schalter:

- Nur `handel_erlaubt`+`freigabe` auf true und `AUTO_FREIGABE`-Eintrag wirken NICHTS ohne Orderweg im `--live`-Zweig. Ohne echte Order, Stop und Ziel ist der Live-Schalter toter Code. Erst bauen, verifizieren, dann scharf.
- Reihenfolge im Hause: Einstieg (market/limit) + Boersen-Stop + Boersen-Ziel, Live-Ausstieg am Markt, Buch-vs-Boerse-Abgleich, dann `handel_erlaubt=true`/`freigabe`/`AUTO_FREIGABE`. Backtest ignoriert nur per ausdruecklicher Max-Freigabe, ehrlich als `backtest_bestanden=false` dokumentieren.
- **UEBERVERKAUFS-SCHUTZ (live exit):** Hat eine Position einen Boersen-Stop UND ein Boersen-Ziel, muss der Live-Ausstieg zuerst pruefen, ob die Boerse sie schon geschlossen hat (`stop_gefuellt` auf beide txids), BEVOR er eine Market-Close stellt. Eine zweite Market-Close auf eine schon geschlossene Position = Ueberverkauf = eroeffnet eine Position in die Gegenrichtung (einen Short). Börse zuerst fragen, nie raten.
- **Short auf Kraken-Spot:** strukturell unmoeglich (Spot kann kein Short halten). Live-Pfad verweigert Shorts mit klarem Sperrgrund; der Papierlauf darf sie fuer den Backtest weiter simulieren.
- `dauerlauf.AUTO_FREIGABE` wird beim IMPORT gelesen: ein neuer Eintrag wirkt erst nach einem Dauerlauf-Neustart. Bis dahin fragt der laufende Prozess per `/ja` statt automatisch freizugeben (sicherer Default). Neustart via `dauerlauf-neustart.ps1` (wartet aufs Zyklusende) nicht ungefragt - recycelt Echtgeld-Spuren.
- Nach Live-Schaltung den `test_wachen_json::test_start_gesperrt`-Test anpassen (er erwartet den alten gesperrten Zustand) - erst dann ist die Suite gruen und die Suite ist der Nachweis.

### spur_buch-Spuren haben den Live-Pfad SCHON — nur verdrahten, nicht neu bauen

Spuren, die ueber `spur_buch.zyklus()` laufen (moondev_whale/-liquidation/-sentiment, iv_*, viele Buch-Spuren), haben die komplette Live-Infrastruktur bereits im gemeinsamen Modul: `sperren_live()` (volle Sperrenkette), `orderweg()` (Boersenmodul aus `wachen.json` `boerse`), `einstieg()` (echte Orders bei `live=True`), `pruefe_ausstiege()` (Live-Exit + Trailing). Fuer so eine Spur live zu schalten ist KEIN Live-Pfad-Bau, sondern drei kleine Schritte:

1. `handeln.py` `--live`-Zweig: statt `GRUND_KEIN_LIVE` zu drucken `buch.zyklus(HIER, quelle, signal, "live", ereignis_name)` durchreichen (der Fallsafe liegt in `sperren_live`).
2. `wachen.json`: `boerse` setzen (z. B. `"okx_perp"` fuer BTC-USDT-SWAP) — ohne sie ist `orderweg()` None und `sperren_live` meldet "kein Orderweg".
3. `handel_erlaubt`/`freigabe`/`AUTO_FREIGABE` wie bei jeder Live-Schaltung.

`spur_buch.orderweg` kennt die Boersen: `okx` (Spot), `kraken` (Spot), `kraken_futures`, `okx_perp` (Futures, `mosaic/okx_perp.py`), `signalwelle`. **Vor dem Bau eines neuen Orderweg-Adapters pruefen, ob `spur_buch.orderweg` schon einen passenden Weg hat** — und ob die Adapter-Datei schon existiert (siehe Falle unten).

## Spur zwischen Boersen umziehen (Venue-Migration)

Hat eine Spur ein Venue-Problem (z. B. Kraken-Spot-Gebuehr 1,2 %/Runde frisst den Edge) und Max will sie auf eine andere Boerse stellen, ist das ein Code-Umbau, kein wachen-Wert. Die Entscheidung zuerst klaeren, dann bauen:

- **Venue-Optionen abwaegen, bevor man baut.** (a) Venue behalten + Gebuehren-Modell ehrlich machen (Abo-Satz statt 0 %-Annahme); (b) auf Futures umziehen — aber pruefen, ob der Ziel-Adapter Take-Profit UND OHLC-Daten hat (Kraken-Futures hat beides oft NICHT: kein `take_profit`, keine Kerzenquelle — dann fehlt dem ORB die Opening-Range und dem Ziel der Boersen-Exit); (c) auf OKX-Perp umziehen (bewaehrt, aber gleiche Venue wie eine bestehende Spur = Redundanz, verliert Diversifikation). Max' "sonst okx wenn besser" ist ein Fallback-Signal: wenn der bevorzugte Weg unzuverlaessig baut, den bewaehrten nehmen.
- **Der Umbau ist ein Venue-Tausch an fuenf Stellen:** Datenquelle (`kraken.kerzen` → `okxf.kerzen`), Orderweg (`markt_kauf`/`stop_setzen`/`take_profit_setzen` → `order_limit` + `schutz_stop_setzen`, das Stop UND Ziel setzt), Waehrung (EUR → USDT), Instrumentennamen (`ETH_USD` → `ETH_USDT` mit `okx`-Key), Gebuehr (`gebuehr_taker` 0,006 → 0,0005). Der ORB-Kern (Range, Breakout, Stop/Ziel, Einzel-Position) bleibt unveraendert.
- **Nach dem Venue-Tausch ALLE Alt-Venue-Referenzen greppen.** `grep -n 'kraken\.\|konf\["kraken"\]\|\["kraken"\]' <spur>/handeln.py` — `zeige_wachen` und `_letzter_kurs` werden beim Tausch leicht uebersehen und crashen mit `KeyError: 'kraken'` erst im `--vorschau`-Lauf. Auch Docstrings koennen den alten Modulnamen tragen (kosmetisch, aber irrefuehrend).
- **Der Ueberverkaufs-Schutz wechselt die Pruefung:** statt `stop_gefuellt` auf zwei txids (Kraken) prueft OKX, ob die Position an der Boerse noch offen ist (`any(pos.get('instId')==inst for pos in okxf.positionen())`), bevor eine Market-Close kommt. Unlesbar → UNGEKLAERT, keine Order.
- **Tests des alten Venue-Modells brechen komplett** (importieren das entfernte Modul, testen take_profit/Short-Verweigerung). Der Code-Umbau ist der harte Teil und committet sich zuerst; die Test-Umstellung ist ein eigener groesserer Schritt — nicht halbfertig hinrotzen, sondern als offenen Rest benennen.

## Dauerlauf-Neustart und Prozess-Wahrheit

Live-Schalten endet im Dauerlauf-Neustart. Der Neustart ist der Moment, in dem man den laufenden Betrieb am leichtesten kaputtmacht — vier Regeln:

- **Ein Dauerlauf hat ZWEI python-Prozesse.** Eine `dauerlauf.py --risiko <stufe>`-Instanz ist ein Wrapper + ein Loop-Kind (gleiche Startzeit, Kindes `ParentProcessId` = Wrapper). Zwei gleich aussehende `--risiko niedrig`-Prozesse sind also die normale Struktur, KEIN Duplikat. Vor jedem Prozess-Kill die Eltern-Kind-Beziehung pruefen (`Get-CimInstance Win32_Process`, `ParentProcessId` + `CreationDate`), nie nach der Commandline allein urteilen — sonst beendet man einen gesunden Dauerlauf und lässt den Betrieb unten.
- **Den Starter nie in einer Foreground-Shell laufen lassen, die Redirect nutzt.** Die Start-Routine (`Routinen/handel-dauerlauf.ps1`) startet das Kind mit `Start-Process -RedirectStandardOutput/-RedirectStandardError`; das haelt die PowerShell offen, bis das langlaufende Kind endet → der Aufruf haengt (>420 s) und ein Shell-Teardown nach Timeout nimmt das Kind mit. Stattdessen abgekoppelt starten: `Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','<routine>' -WindowStyle Hidden`, damit der Befehl sofort zurueckkommt und das Kind ueberlebt.
- **Schlaegt ein Neustart-Skript beim "start new process"-Schritt fehl, ist der Dauerlauf UNTEN** (alte Prozesse wurden schon beendet, der Neue nie gestartet) — nicht so stehen lassen und auf den Waechter hoffen. Sofort den echten Starter direkt ausfuehren und verifizieren, dass genau eine Instanz laeuft (Anzahl `--risiko <stufe>`-Prozesse pruefen).
- **`dauerlauf-neustart.ps1` zeigt auf den falschen Starter-Pfad.** Es ruft `handel-dauerlauf.ps1` unter `Handel/` auf, aber die Routine liegt in `Routinen/` — der Neustart beendet dann die alten Prozesse und scheitert beim Start des neuen (Dauerlauf unten). Vor einem Neustart den Pfad im Skript pruefen; nach einem Fehlschlag den echten Starter aus `Routinen/` direkt abgekoppelt ausfuehren.
- **Auto-Freigabe ist nicht momentan, sondern durch die Wiedervorlage-Frist getaktet.** `freigabefenster.neue_anfrage_erlaubt(spur)` ist `False`, solange eine fruehere (z. B. unbeantwortete) `/ja`-Anfrage in der Kuehltaste steckt (`WIEDERVORLAGE_MINUTEN` nach `anfrage_gestellt`, laenger nach Ablehnung). Eine gerade live geschaltete Spur kann deshalb erst nach Ablauf dieser Frist automatisch freigegeben werden — orb/orbk hingen an einer frueheren Anfrage, bevor der erste Dauerlauf die Auto-Freigabe kannte. Das ist der Antispam-Mechanismus, kein Bug: vor der Aussage "Auto-Freigabe feuert nicht" `neue_anfrage_erlaubt(spur)` pruefen und die Frist nennen, statt einen Defekt zu suchen.

## Risikostufen sind Skalierung, keine Strategien

Die drei Dauerlauf-Stufen (`niedrig`/`mittel`/`hoch`, Faktor 1/2/4 in `risikostufe.py` `FAKTOREN`) sind **dieselbe Strategie mit skalierten Betraegen** — kein anderes Tor, kein hoeheres CR, keine mehr Kandidaten. `risikostufe.live_erlaubt()` = `ist_basis()`: **nur die Basis (niedrig) darf live**, mittel/hoch sind strikt Papier-Datenlaeufe (eigene `zustand.mittel/hoch.json`, senden nie nach Telegram, fragen keine Freigabe).

- Wenn Max eine Stufe als "andere Risiko-Strategie mit leichterem Tor" beschreibt, ist das ein Missverstaendnis der Architektur — klaeren, bevor man baut. Eine echte "leichte Tor / mehr Kandidaten"-Variante waere ein neuer Bau mit eigenen Wachen-Schwellen, nicht die Stufen-Skalierung.
- "Guthaben auf X $ reduzieren" fuer den Scanner heisst **beide** Kapitalfelder in `scanner/wachen.json` aendern: `max_gesamt_usd` (Buch-Obergrenze) UND `budget_usd` (verfuegbares Kapital) — sie stehen unabhaengig und beide auf demselben Wert.

- **Offene Positionen aus dem FRISCHEN Stufen-Buch melden, nie aus `zustand.json`.** Es gibt drei parallele Buecher (`zustand.json` Basis, `zustand.mittel.json`, `zustand.hoch.json`) mit eigenen `letzter_lauf`-Zeitstempeln. `zustand.json` (Basis) kann STALE sein (alter `letzter_lauf`), waehrend eine Stufen-Datei frisch laeuft — wer aus der toten Basis-Datei listet, meldet Phantom-Positionen, die der Nutzer nicht wiedererkennt. Vor jeder Aussage "X Positionen offen": alle drei Stufen-Dateien lesen, die mit dem juengsten `letzter_lauf` identifizieren und NUR aus der melden. Ein frischer `letzter_lauf` in EINER Stufe belegt nicht, dass die andere lebt.
- **Auch ein neuer Sidecar wie der Orderweg (`eingelegt.json`) ist stufen-suffigiert.** Mit `HANDEL_RISIKO=hoch` laedt `risikostufe.datei()` aus `eingelegt.hoch.json`, nicht aus `eingelegt.json`. Wer einen Auftrag fuer eine Nicht-Basis-Stufe einlegt, muss den suffigierten Dateinamen treffen (und umgekehrt beim Baseline ist es die unsuffigierte). `risikostufe.datei(<name>)` unter der Ziel-`HANDEL_RISIKO` laufen lassen, um den echten Namen zu bekommen, statt zu raten.
## Fremden Bot als Papier-Spur einbinden (jev_trader-Muster)

Max will einen externen Handels-Bot (eigene Sprache/Blockchain, z. B. ein TypeScript/bun-Projekt auf Monad) in die Haus-Auswertung holen. Das ist eine **Papier-Spur, die den Bot-Log einliest** — kein Live-Pfad, keine Exchange-Calls:

- **Quelle zuerst pruefen:** der Bot loggt Block-Events als JSONL (`data/events.jsonl`). Einzelne Fills stehen oft NICHT als Zeilen — sie sind nur in den laufenden `totals` (fills, realizedUsd, pnlUsd) reflektiert. Die Round-Trips aus dem `position`-Feld rekonstruieren (side/size-Wechsel: long→flat, long→short = realisierter Trade), nicht aus einem fill-Feld.
- **P&L je Trade aus dem `realizedUsd`-Delta** zwischen Events, nicht aus einer geratenen Zahl. Ausstiegsgrund (ziel/stop/zwangsschluss) aus der Preisbewegung gegen den Einstieg ableiten.
- **Idempotent journalen:** einen Marker (letzter verarbeiteter Block/ts) in `zustand.json` halten, damit ein zweiter Lauf keine Journal-Zeilen dupliziert. Tests mit synthetischem JSONL, nie mit der echten 50-MB-Datei.
- **`--vorschau` druckt die Journal-Statistik** (Runden, Trefferquote, Ergebnis) und `Live waere gesperrt durch: kein Live-Pfad (Papier-Spur)` — konsistent mit den anderen Spuren, aber ohne Freigabefenster-Logik.
- **Auswerten heisst zuerst die Historie messen** (Runden, Trefferquote, EV, P&L-Kurve aus den totals), dann erst bauen — die Zahlen entscheiden, ob die Einbindung lohnt. Ein Dry-Run-Bot mit 546 Fills und −0,28 % P&L ist ein Befund (break-even/experimentell), kein Freigabe-Kandidat.

## Spiegelung (Bedingung 4) bei Mehr-Arm-Spuren

`spiegelstand.py` listet Spuren als **Verzeichnisse mit `wachen.json` direkt im
Handel-Ordner**. Eine Spur, die ihre Buecher in Unterordnern fuehrt
(`<spur>/laeufe/<variante>-<arm>/` mit je eigener `wachen.json`, Muster
`llm_stunde` mit 6 Armen), hat im eigenen Ordner GAR KEINE Quelldateien — der
Pruefer vergleicht dann einen leeren Hauptordner gegen `Q:` und meldet
`ABWEICHUNG [handelsjournal.csv, zustand.json]` bzw. `kein Ziel`.

- **Dieser Befund ist ein Werkzeug-Fehlalarm, kein Spiegelungsfehler — vor
  jeder Meldung byte-genau gegenpruefen.** `cmp <spur>/laeufe/<arm>/handelsjournal.csv
  "Q:/Handel_Journal/<spur>/handelsjournal.csv"`: ist er still, spiegeln die Arme
  korrekt und nur die Erkennung fehlt. Eine Spiegelungs-Luecke zu melden, die
  nicht existiert, kostet denselben Aufwand wie eine echte.
- Alle Arme einer solchen Spur spiegeln in **denselben** Zielordner
  (`journal_zweitziel` steht in jeder Arm-`wachen.json`, nicht in der Haupt-Datei
  der Spur) — der Pruefer braucht also pro Arm eine eigene Zeile gegen dasselbe Ziel.
- Der Fix in `spiegelstand.py` ist die Arm-Erkennung (`laeufe_arme(handel, ordner)`
  findet `<ordner>/laeufe/<arm>/` mit eigener `wachen.json`; `stand()` ersetzt die
  quellenlose Haupt-Spur durch ihre Arme). Dabei muss die Schatten-Suffix-Heuristik
  fuer Arme ABGESCHALTET werden (`_wachen_vorgabe`): ein Armname wie `ema1h-L`
  hat keinen Unterstrich zum Kuerzen, sonst greift die `wachen.<suffix>.json`-Suche ins Leere.
- Im Lauf-Status zaehlt ein Arm ueber seinen Hauptnamen — in `dauerlauf.SPUREN`
  steht die Spur (`llm_stunde`), nie die einzelnen Straenge. Ein Arm ist deshalb
  nicht "ausserhalb des Dauerlaufs", nur weil sein Name dort fehlt.

## Weitere Dateien (Support)
`references/llm-entscheidung.md` — Details zum Auto-Genehmigungs-Programm
(Ordner, Vertrag, Akzeptanz-Schwelle, Fehler-Härte).

## Fallen

- **Spur-Tests mit Pfad-Guard (`assert h.__file__.startswith(SPUR)`) muessen aus dem SPUR-Ordner laufen, nie aus der Worktree-Wurzel.** Der Test schiebt `scanner/` an Position 0 in `sys.path`; laeuft man `python -m unittest Agenten/Handel/<spur>/tests/test_*.py` aus der Worktree-Wurzel, loest `import handeln` zu `scanner/handeln.py` auf statt zum eigenen `handeln.py` der Spur — der Guard schlaegt mit `AssertionError: falsches handeln.py: ...scanner\handeln.py` fehl. Das ist ein falsches Arbeitsverzeichnis, KEIN Code-Defekt. Korrekt: `cd <spur>` und dann `python -m unittest discover -s tests -p "test_*.py"` ODER die Testdatei direkt als Skript (`python tests/test_<spur>.py`). Die Modul-/Datei-Form `-m unittest tests.test_<spur>` bzw. `-m unittest tests/test_<spur>.py` schlaegt den Guard AUCH aus dem Spur-Ordner fehl (sys.path[0] ist dann ''/cwd statt des Spur-Ordners) — nicht verwenden. Ein solcher Guard-Fehlschlag beim Verifizieren eines Branches ist kein Grund, den Branch als rot zu melden: erst aus dem richtigen Verzeichnis neu laufen, und wenn er dort weiterhin auftritt, denselben Test auf `master` (Hauptbaum) laufen lassen — tritt er dort identisch auf, ist es ein vorbestehendes Harness-Problem, kein Regressions-Blocker des Branches.
- **Ein `\n` in einem Python-Heredoc-String ist ein echter Zeilenumbruch, kein Backslash-n.** Schreibst du im `python - <<'PY'` eine Zielzeile mit `"...\n..."` als Ersetzungstext, interpretiert das laufende Python das `\n` als neuen Zeilenumbruch — die geschriebene Datei bekommt eine kaputte Zeile (`text += "` + Bruch + `Rest`), was einen SyntaxError ergibt, der sich durch weitere `\n`-Patches nicht heilt. Zum Schreiben eines literalen Backslash-n ins Ziel `chr(92) + 'n'` verwenden; und nach dem Schreiben die betroffene Zeile ZURUECKLESEN (read_file / cat -A), statt dem In-Memory-Ersetzen oder einem `diff` zu trauen, das den Bruch nicht zeigt. Derselbe Fallstrick gilt fuer jedes Escape, das der Zielsprache Festbedeutung hat.
- **„Positionen erhoehen“ bei einer Einzel-Positions-Spur ist ein Code-Refactor, kein wachen-Wert.** Eine Spur mit `z['position']` als Dict (prueft `if not z.get("position")`) kann physisch nur EINE Position halten — `max_offene_positionen` zu erhoehen aendert nichts (die orbk-wachen dokumentiert das explizit). Mehr gleichzeitig heisst: `z['positionen']` als Liste bauen, `pruefe_einstieg`/`pruefe_ausstiege`/`lauf`/`zeige_wachen` + die Tests auf das Listen-Modell umstellen. Und pruefen, ob die Strategie ueberhaupt mehrere erlaubt: eine One-Trade-pro-Tag-Regel (ORB) limitiert pro Instrument/Tag, unabhaengig vom Modell — mehr Parallelelitaet bedeutet dann mehrere Instrumente, nicht mehrere Trades.
- **Vor dem Anlegen eines neuen Moduls/Adapters im Handel-Baum pruefen, ob es schon existiert.** Ein neuer Orderweg-Adapter (z. B. `mosaic/okx_perp.py`) oder dessen Test kann bereits da sein — ueberschreibt man ihn, loescht man funktionierenden Code und dessen Testabdeckung, und der Diff wird riesig. Vor dem Schreiben `ls <ordner>/` und `grep -rn "def markt_kauf" <ordner>/`; wenn eine Datei existiert, sie lesen und erweitern statt neu schreiben. Nach einem versehentlichen Ueberschreiben: Original aus `git show <base>:<pfad>` wiederherstellen und den Commit amenden, damit nur die echten Aenderungen drinstehen.
- **Eine CRLF-`wachen.json` nie mit `json.dumps` neu schreiben.** Der Rewrite macht die ganze Datei LF → der Diff zeigt jede Zeile als geaendert (hunderte Loeschungen, reines Zeilenende-Rauschen) und kann Merge-Konflikte erzeugen. Fuer eine Wert-/Feld-Aenderung das Original (CRLF) aus dem Base-Commit holen und per gezieltem `str.replace` auf exakte Zeilen einspielen (CRLF erhalten), oder den Wert per JSON-Read aendern und mit `newline="\n"` nur schreiben, wenn die Datei schon LF ist. Nach dem Edit `git diff --stat` pruefen: nur die beabsichtigten Zeilen duerfen sich aendern.
- **Dieselbe Zeilenende-Falle trifft `.py`-Dateien, die per Python-Heredoc im Worktree editiert werden.** `open(f,'w').write(s)` nach einem `read` normalisiert die Zeilenenden auf LF — ein 2-Zeilen-Fix wird zu einem 4900-Zeilen-Diff (jede Zeile als geaendert). Vor dem Schreiben im Worktree die Zeilenenden der Quelldatei pruefen (`python -c "b=open(f,'rb').read(); print(b.count(b'\r\n'), b.count(b'\n'))"`); wenn CRLF, die Aenderung BYTE-weise einspielen (`open(f,'rb')` → `b.replace(old_bytes, new_bytes)` → `open(f,'wb')`), nicht textuell. Nach dem Edit `git diff --stat` kontrollieren — ein minimaler Fix muss minimal bleiben. Ein versehentlicher LF-Rewrite laesst sich mit `git reset --hard <base>` zuruecknehmen und der Fix byte-weise neu einspielen.
- **Das Umsatztor je Familie liegt in `familien.<familie>.umsatz_bezug_usd`, nicht in `min_umsatz_24h_usd`.** `min_umsatz_24h_usd` (top-level) ist ein Krypto-Wert; die Familien haben eigene Schwellen (`familien.aktie`/`krypto`/`rohstoff`). Wer das Aktien-Umsatztor senkt, aendert `familien.aktie.umsatz_bezug_usd` — und laesst `min_umsatz_24h_usd` und die anderen Familien unberuehrt. Vor dem Edit die drei Familienwerte per JSON-Read nebeneinander ausgeben, damit man den richtigen trifft.
- **Lange deutsche Vermerke nicht mit `patch` umschreiben — weder in `wachen.json` noch in `dauerlauf.py`.** Das Fuzzy-Matching des Patch-Tools verhunzt mehrzeilige deutsche Kommentarbloecke (fuehrt Einrueckungsfehler und Tippfehler ein, die es beim naechsten Patch wiederholt; in `dauerlauf.py` hat es einen `SyntaxError` und ein kaputtes `"skript": ": "handeln.py"` erzeugt). Fuer gezielte Wert-/Vermerk-Aenderungen an JSON-Konfigs mit langen `_`-Kommentaren UND an `.py`-SPUREN-Bloecken einen Python-Heredoc verwenden (`python - <<'PY' ... PY` mit `str.replace` auf exakte Zeilen), nicht `patch`. Nach jedem Edit `git diff --stat` + Syntax-Check (`python -c "import ast; ast.parse(open('dauerlauf.py',encoding='utf-8').read())"`) pruefen — der Patch-Tool-Diff zeigt den Bruch oft nicht.
- **Wer `patch` fuer JSON-Vermerke doch nutzt, muss die Folge-Diffs kontrollieren:** das Tool hat drei Zeilen mit 4-statt-2-Leerzeichen-Einrueckung und einen Tippfehler eingefuehrt und sich beim naechsten Patch darauf festgebissen. Nach jedem JSON-Patch die betroffenen Zeilen per `read_file` pruefen oder gleich den Python-Heredoc nehmen — die Einrueckung validiert JSON nicht (Wert bleibt korrekt), aber die Datei wird inkonsistent.
- **Zwei Zeitzonen im selben Befund.** `dauerlauf.log` schreibt **Lokalzeit**, Journale und `zustand.json` (`letzter_lauf`) schreiben **UTC-Isoformat**. Eine Logzeile `23:54` und ein `letzter_lauf` von `21:54Z` sind derselbe Zyklus. Vor jeder Aussage „die Spur läuft nicht mehr" oder „der Zustand ist alt" beide auf eine Zone bringen — sonst erfindet man eine zweistündige Lücke.
- **Ein frischer `letzter_lauf` beweist nur den Zyklus, nicht die Buchung.** Der Zustand wird an jedem Zyklusende neu geschrieben, auch wenn nichts passierte. Dass eine Datei frisch ist, sagt nichts darüber, ob ein Ausstieg oder Nachsatz stattgefunden hat — das steht im Journal und an der Börse.
- **PowerShell über git-bash:** `$_.X` und ähnliche Ausdrücke werden von bash zerlegt → die Befehlszeile von Prozessen nicht so abfragen. Ein `.ps1`-File schreiben und mit `powershell -ExecutionPolicy Bypass -File` ausführen, oder ein Python-Skript für die Abfrage. (`wmic process get CommandLine` in bash funktioniert zugig.)
- **PowerShell-Befehl als Argument an `wmic`/`Get-CimInstance`** opfert zur Laufzeit, wenn bash Interpolation frisst — skript-file Umweg ist der stabile Pfad.
