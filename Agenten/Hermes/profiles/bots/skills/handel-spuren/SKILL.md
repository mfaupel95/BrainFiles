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

- Deutet jede Spur mit eigenen/keinen Journal-Zahlen; die „Uebersicht".-Zeile fasst alles zusammen. Fange die volle Ausgabe in eine Datei ab (die bekommst du sonst nicht komplett auf einen Screen), auch für `--spur <einzelne>`.
- **Belastbar = ≥ 8 geschlossene Runden.** Darunter heißt es „zu wenige Runden — ein Befund, keine Messung". Über 8 Runden aus einer Zahl Entscheidungen abzuleiten ist Overfitting; sag das klipp und klar, statt daraus einen Tuningschritt zu bauen.
- Kern-Zahlen einer Spur liegen in ihrem `<spur>/wachen.json` und Journal; `--wachen` an das jeweilige `handeln.py` zeigt den Zustand (freigabe, kill, herzschlag, groessenfaktor).

Nicht jede Spur hat ein `handelsjournal.csv`, das über `pos_id` paar-bar ist — Altjournal-Zeilen tragen keine `pos_id` und fallen aus der Zählung. Sag es dazu, wenn du auf Grundlage gepaarter Zeilen rechnest.

### Eigene/LLM-Spuren getrennt auswerten

- Nach `auswertung_alle.py` auch dessen Abschlusszeile lesen: manche Spuren (eigene Evaluatoren, LLM-Signale oder abweichende Journalformate) fehlen bewusst in der Sammelrechnung. Für diese jeweils den ausgewiesenen Spur-Evaluator, Journal und `zustand.json` heranziehen; die Sammelübersicht nicht als vollständige Spur-Liste ausgeben.
- Eine Spur nur dann als LLM-gestützt bezeichnen, wenn der aktive Signalpfad tatsächlich das lokale/konfigurierte Sprachmodell aufruft — Namen wie `moondev_*` reichen nicht. Aktive `SPUREN` und ausführbaren `handeln.py`-Pfad gegenprüfen.
- Runden nur aus eindeutig gepaarten Einstiegs-/Ausstiegszeilen zählen. Offene Positionen und Ausstiege ohne Partner separat melden; sie sind keine geschlossenen Runden und kein realisiertes Ergebnis. Nicht verfügbare Backtest-Historie als nicht nachrechenbar kennzeichnen, nicht durch Schätzungen ersetzen.
- Ein kurzer Prompt-Sanity-Check belegt nur Antwortfähigkeit. Signalqualität braucht den festgelegten Vertrags-/Eval-Satz; ohne diesen keine Aussage aus zwei Beispielprompts ableiten. Es gelten weiter die Stichprobenschwellen aus *Auswerten*.

## Tunen: erst die Asymmetrie messen, dann den einen Stellhebel

Typischer Befund (liq_wand 10.2026): **hohe Trefferquote, aber netto negativ.** Ursache ist fast immer eine Gewinn/Verlust-Asymmetrie — Zielgewinne klein, Stops 3× größer. Rechnung aus dem Journal: durchschnittlicher Gewinn ÷ durchschnittlicher Verlust, gegen die Break-even-Schwelle `Verlustanteil / Gewinnanteil`. Liegt die Asymmetrie darunter, ist netto negativ, egal wie oft du triffst.

- Der eine Stellhebel, der diese Klasse von Spur korrigiert: **den Stop nah an die Realität der Zielgewinne ziehen** (`stop_prozent` in `wachen.json`), nicht das Ziel vergrößern — wenn das Ziel eine Marktstruktur ist (z. B. die Liquidationswand), ist es nicht beweglich.
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

## Schützen — jede Änderung an `wachen.json`

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
- **Live-Betrieb ⇒ `herzschlag_max_minuten` auf 45** (Regel: 45 fuer Spuren mit Handelserlaubnis, 180 fuer Papier), nicht mit 180 weiterlaufen lassen.
- **Live-Freigabe bricht den `test_wachen_json::test_start_gesperrt`-Zustandstest.** Er assertet den alten gesperrten Zustand (`handel_erlaubt=False` UND `freigabe.erfuellt=False`). Nach dem Umschalten auf live schlaegt genau diese Asserion fehl — kein Code-/Bau-Defekt, sondern die erwartete Folge des Schaltens. Den Test auf den neuen Live-Zustand aktualisieren (Name und beide Assertions auf `True`), damit die Suite gruen bleibt und der legitime Schwenk nicht als regressiver Fehler erscheint. Ein „vorbestehender Fehlschlag" kann genau dieser Zustandstest sein, der sich durch die Freigabe von selbst umkehrt — erst nach dem Schalten neu beurteilen, statt ihn als fremden Defekt zu registrieren.
- **Subagent-Live-Bau nach dem Selbstbericht selbst verifizieren** (Echtgeld): Diff der `handeln.py` lesen, die Tests mit dem Hauptbaum-Interpreter SELBST laufen lassen (nicht dem „alle gruen" des Berichts trauen), und den `--vorschau`-Output auf die exakte `Live waere gesperrt durch:`-Zeile pruefen. Die File-Mutations-Warnung des Berichts beantworten, indem man `git status`/Diff kontrolliert, dass nichts Fremdes landete (Scratch-Datei, `/tmp`-Abschrift).

## Anweisungs-Trade: vorbereiten ≠ scharfstellen (kein Auto-Weg)

Ein Anweisungs-Trade (Max nennt Kontrakt, Richtung, Hebel, Einsatz, Stop ueber den Chat) laeuft ueber `bot.py` und landert als **`vorbereitung`-Zeile im Journal** — das ist noch ***keine*** Order. Der Dauerlauf/AUTO_FREIGABE ordert **nur seine eigenen Ranglisten-Kandidaten**; eine manuell vorbereitete Journal-Position wird von keinem Zyklus automatisch aufgegriffen (`zustand.json` `wartende: []`). Es gibt **keinen dokumentierten Auto-Pfad**, der eine angewiesene `vorbereitung` in eine Live-Order verwandelt.

- Frei nach Handelsregeln: *„Das Absenden der scharfen Order tut die Sitzung selbst nicht — ausgeloest wird sie von Max oder von dem gebauten Skript (`handeln.py --live`)."* `handeln.py --live` ordert aber aus seiner Kandidaten-/Zonenlogik, nicht aus dem Journal.
- Offenes Freigabefenster (`AUTO_FREIGABE`, `handel_erlaubt:true`) bewoehrt die Spur — es schickt die angewiesene Position **nicht** automatisch.
- **Sauberer Weg:** Max eroeffnet die Position selbst an der Boerse mit den fuenf Werten; die Spur erkennt sie als Handposition (`herkunft=boerse_handgriff`, `handpositionen_automatisch_schliessen`) und verwaltet sie danach (Stop, Ziel, Trailing).
- **Verifiziere den Fenster- und Buchstatus selbst statt einer Bot-Behauptung zu trauen.** Der delegierte Bot meldete zuerst `handel_erlaubt:false`, dann `true`; die Fakten stehen in der Datei. Fenster-Status: `freigabefenster.py` (`alle()` gibt `Fenster`-Objekte mit `.offen`/`.text`, Zustand in `freigabe_fenster.json` pro Spur, `AUTO_FREIGABE_STUNDEN` in `dauerlauf.py`). Ob eine Position scharf ist, zeigt nur das echte undef wartende/offene Orderbild, nie eine vorbereitende Journal-Zeile.

**Ein delegierter Bot, der in eine Wiederholungsschleife laeuft, ist ein Mechanik-Verdacht, kein Transient.** `markt-recherche` kollabierte (exit 1, Repetition-Loop) genau im Suchen des nicht existierenden Anweisungs-Auto-Wegs. Nach so einem Abbruch nicht blind den gleichen Bot erneut starten — erst im Repo pruefen, was wirklich passiert ist (Commit vorhanden? Fenster offen? Position eingelegt?), und dann den fehlenden Weg als solchen melden statt ihn zu erfinden.

## Stilllegen: netto-negativ + nicht per Parameter behebbar

Wenn eine belastbare Spur netto negativ ist UND der Parametersuche nichts überlebt, ist der saubere Weg die **Stilllegung** — nicht weiter Daten erzeugen. Muster = wie spiegel („eh absolut nicht profitabel"):

1. In `dauerlauf.py` `SPUREN`: den Eintrag **auskommentieren** und daneben einen Kommentar mit Stilllegungsgrund + den Wieder-Anschalten-Schritten setzen (Journal bleibt als Vergleichsbuch stehen, wächst nicht weiter).
2. Gleichzeitig aus `AUTO_FREIGABE` entfernen, falls dort gelistet.
3. Vergisst man einen Schattenarm (`squeeze_eth` teilt sich den `squeeze`-Ordner), geht er mit raus — beide Einträge kommentieren.
4. Zugehörige Tests laufen lassen (`test_dauerlauf_ereignisse`, `test_stille_spuren`, `test_klassik_spuren`) und mit einem AST/Regex-Zähler bestätigen, dass der Name in keinem AKTIVEN (nicht auskommentierten) SPUREN-Eintrag mehr steht.
5. Eine `wachen.json`-Wertänderung ist Betriebskonfig und darf direkt auf master (Commit mit `--author="Hermes <hermes@local>"`); eine `dauerlauf.py`-Spurlisten-Änderung ebenso nach dem spiegel-Muster.

**Eine Stilllegung in `SPUREN` greift erst beim Neustart des Dauerlaufs** — das Dict wird einmal beim Import gelesen, laufende Zyklen sehen die alte Liste. Einen Dauerlauf-Neustart nicht ungefragt machen: er recycelt die Echtgeld-Spuren (scanner/xperp in mittel/hoch) und kann offene Positionen flachstellen. Committen und die Wirkung als „beim nächsten Neustart wirksam" vermerken, Max die Entscheidung über den Neustart überlassen.

## Ziplime — externer Backtesting-Engine

Eine Anfrage, Ziplime (Werkstatt/Repos/ziplime) fuer die Handelsoptimierung zu
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

## Dauerlauf-Neustart und Prozess-Wahrheit

Live-Schalten endet im Dauerlauf-Neustart. Der Neustart ist der Moment, in dem man den laufenden Betrieb am leichtesten kaputtmacht — vier Regeln:

- **Ein Dauerlauf hat ZWEI python-Prozesse.** Eine `dauerlauf.py --risiko <stufe>`-Instanz ist ein Wrapper + ein Loop-Kind (gleiche Startzeit, Kindes `ParentProcessId` = Wrapper). Zwei gleich aussehende `--risiko niedrig`-Prozesse sind also die normale Struktur, KEIN Duplikat. Vor jedem Prozess-Kill die Eltern-Kind-Beziehung pruefen (`Get-CimInstance Win32_Process`, `ParentProcessId` + `CreationDate`), nie nach der Commandline allein urteilen — sonst beendet man einen gesunden Dauerlauf und lässt den Betrieb unten.
- **Den Starter nie in einer Foreground-Shell laufen lassen, die Redirect nutzt.** Die Start-Routine (`Routinen/handel-dauerlauf.ps1`) startet das Kind mit `Start-Process -RedirectStandardOutput/-RedirectStandardError`; das haelt die PowerShell offen, bis das langlaufende Kind endet → der Aufruf haengt (>420 s) und ein Shell-Teardown nach Timeout nimmt das Kind mit. Stattdessen abgekoppelt starten: `Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','<routine>' -WindowStyle Hidden`, damit der Befehl sofort zurueckkommt und das Kind ueberlebt.
- **Schlaegt ein Neustart-Skript beim "start new process"-Schritt fehl, ist der Dauerlauf UNTEN** (alte Prozesse wurden schon beendet, der Neue nie gestartet) — nicht so stehen lassen und auf den Waechter hoffen. Sofort den echten Starter direkt ausfuehren und verifizieren, dass genau eine Instanz laeuft (Anzahl `--risiko <stufe>`-Prozesse pruefen).
- **Auto-Freigabe ist nicht momentan, sondern durch die Wiedervorlage-Frist getaktet.** `freigabefenster.neue_anfrage_erlaubt(spur)` ist `False`, solange eine fruehere (z. B. unbeantwortete) `/ja`-Anfrage in der Kuehltaste steckt (`WIEDERVORLAGE_MINUTEN` nach `anfrage_gestellt`, laenger nach Ablehnung). Eine gerade live geschaltete Spur kann deshalb erst nach Ablauf dieser Frist automatisch freigegeben werden — orb/orbk hingen an einer frueheren Anfrage, bevor der erste Dauerlauf die Auto-Freigabe kannte. Das ist der Antispam-Mechanismus, kein Bug: vor der Aussage "Auto-Freigabe feuert nicht" `neue_anfrage_erlaubt(spur)` pruefen und die Frist nennen, statt einen Defekt zu suchen.

## Risikostufen sind Skalierung, keine Strategien

Die drei Dauerlauf-Stufen (`niedrig`/`mittel`/`hoch`, Faktor 1/2/4 in `risikostufe.py` `FAKTOREN`) sind **dieselbe Strategie mit skalierten Betraegen** — kein anderes Tor, kein hoeheres CR, keine mehr Kandidaten. `risikostufe.live_erlaubt()` = `ist_basis()`: **nur die Basis (niedrig) darf live**, mittel/hoch sind strikt Papier-Datenlaeufe (eigene `zustand.mittel/hoch.json`, senden nie nach Telegram, fragen keine Freigabe).

- Wenn Max eine Stufe als "andere Risiko-Strategie mit leichterem Tor" beschreibt, ist das ein Missverstaendnis der Architektur — klaeren, bevor man baut. Eine echte "leichte Tor / mehr Kandidaten"-Variante waere ein neuer Bau mit eigenen Wachen-Schwellen, nicht die Stufen-Skalierung.
- "Guthaben auf X $ reduzieren" fuer den Scanner heisst **beide** Kapitalfelder in `scanner/wachen.json` aendern: `max_gesamt_usd` (Buch-Obergrenze) UND `budget_usd` (verfuegbares Kapital) — sie stehen unabhaengig und beide auf demselben Wert.

## Fallen

- **Das Umsatztor je Familie liegt in `familien.<familie>.umsatz_bezug_usd`, nicht in `min_umsatz_24h_usd`.** `min_umsatz_24h_usd` (top-level) ist ein Krypto-Wert; die Familien haben eigene Schwellen (`familien.aktie`/`krypto`/`rohstoff`). Wer das Aktien-Umsatztor senkt, aendert `familien.aktie.umsatz_bezug_usd` — und laesst `min_umsatz_24h_usd` und die anderen Familien unberuehrt. Vor dem Edit die drei Familienwerte per JSON-Read nebeneinander ausgeben, damit man den richtigen trifft.
- **Lange `wachen.json`-Vermerke nicht mit `patch` umschreiben.** Das Fuzzy-Matching des Patch-Tools verhunzt mehrzeilige deutsche Vermerke (fuehrt Einrueckungsfehler und Tippfehler ein, die es beim naechsten Patch wiederholt). Fuer gezielte Wert-/Vermerk-Aenderungen an JSON-Konfigs mit langen `_`-Kommentaren einen Python-Heredoc verwenden (`python - <<'PY' ... PY` mit `str.replace` auf exakte Zeilen), nicht `patch`.
- **Wer `patch` fuer JSON-Vermerke doch nutzt, muss die Folge-Diffs kontrollieren:** das Tool hat drei Zeilen mit 4-statt-2-Leerzeichen-Einrueckung und einen Tippfehler eingefuehrt und sich beim naechsten Patch darauf festgebissen. Nach jedem JSON-Patch die betroffenen Zeilen per `read_file` pruefen oder gleich den Python-Heredoc nehmen — die Einrueckung validiert JSON nicht (Wert bleibt korrekt), aber die Datei wird inkonsistent.
- **Zwei Zeitzonen im selben Befund.** `dauerlauf.log` schreibt **Lokalzeit**, Journale und `zustand.json` (`letzter_lauf`) schreiben **UTC-Isoformat**. Eine Logzeile `23:54` und ein `letzter_lauf` von `21:54Z` sind derselbe Zyklus. Vor jeder Aussage „die Spur läuft nicht mehr" oder „der Zustand ist alt" beide auf eine Zone bringen — sonst erfindet man eine zweistündige Lücke.
- **Ein frischer `letzter_lauf` beweist nur den Zyklus, nicht die Buchung.** Der Zustand wird an jedem Zyklusende neu geschrieben, auch wenn nichts passierte. Dass eine Datei frisch ist, sagt nichts darüber, ob ein Ausstieg oder Nachsatz stattgefunden hat — das steht im Journal und an der Börse.
- **PowerShell über git-bash:** `$_.X` und ähnliche Ausdrücke werden von bash zerlegt → die Befehlszeile von Prozessen nicht so abfragen. Ein `.ps1`-File schreiben und mit `powershell -ExecutionPolicy Bypass -File` ausführen, oder ein Python-Skript für die Abfrage. (`wmic process get CommandLine` in bash funktioniert zugig.)
- **PowerShell-Befehl als Argument an `wmic`/`Get-CimInstance`** opfert zur Laufzeit, wenn bash Interpolation frisst — skript-file Umweg ist der stabile Pfad.
