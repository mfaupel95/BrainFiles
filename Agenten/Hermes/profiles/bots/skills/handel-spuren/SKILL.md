---
name: handel-spuren
category: software-development
description: Evaluate or improve Max's trading spurs in Agenten/Handel.
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

## Stilllegen: netto-negativ + nicht per Parameter behebbar

Wenn eine belastbare Spur netto negativ ist UND der Parametersuche nichts überlebt, ist der saubere Weg die **Stilllegung** — nicht weiter Daten erzeugen. Muster = wie spiegel („eh absolut nicht profitabel"):

1. In `dauerlauf.py` `SPUREN`: den Eintrag **auskommentieren** und daneben einen Kommentar mit Stilllegungsgrund + den Wieder-Anschalten-Schritten setzen (Journal bleibt als Vergleichsbuch stehen, wächst nicht weiter).
2. Gleichzeitig aus `AUTO_FREIGABE` entfernen, falls dort gelistet.
3. Vergisst man einen Schattenarm (`squeeze_eth` teilt sich den `squeeze`-Ordner), geht er mit raus — beide Einträge kommentieren.
4. Zugehörige Tests laufen lassen (`test_dauerlauf_ereignisse`, `test_stille_spuren`, `test_klassik_spuren`) und mit einem AST/Regex-Zähler bestätigen, dass der Name in keinem AKTIVEN (nicht auskommentierten) SPUREN-Eintrag mehr steht.
5. Eine `wachen.json`-Wertänderung ist Betriebskonfig und darf direkt auf master (Commit mit `--author="Hermes <hermes@local>"`); eine `dauerlauf.py`-Spurlisten-Änderung ebenso nach dem spiegel-Muster.

**Eine Stilllegung in `SPUREN` greift erst beim Neustart des Dauerlaufs** — das Dict wird einmal beim Import gelesen, laufende Zyklen sehen die alte Liste. Einen Dauerlauf-Neustart nicht ungefragt machen: er recycelt die Echtgeld-Spuren (scanner/xperp in mittel/hoch) und kann offene Positionen flachstellen. Committen und die Wirkung als „beim nächsten Neustart wirksam" vermerken, Max die Entscheidung über den Neustart überlassen.

## Leitstand ausbauen

Eine Anfrage „leitstand.py untersuchen/ausbauen" (Nautilus-/Prozesse-Reiter, Nodes einbinden) ist eine eigene Klasse innerhalb des Handel-Baums: Tk-Dashboard, kein Spur-Tuning, aber dieselbe Worktree-Regel und Stufe-1-Disziplin. Karte der Reiter-Schnittstelle, der Takt-Gruppen und der tatsaechlich handelnden Nautilus-Repos + Nodes: `references/leitstand.md`. Zusaetzlich zur Auswertung unten stehen die `.venv`-Grenzen (Nautilus-Spuren laufen NICHT unter `scanner/.venv`) dort.

## Codearbeit, nicht Betrieb — in den Worktree

Eine Code-Änderung (z. B. Intervall-Zuordnung in `omnitrade_start.py`) gehört **nicht in den Hauptbaum**, sondern in einen Worktree NEBEN `BrainFiles/` auf eigenem Zweig (`git worktree add ../Handel-<x> -b <agent>/<thema> master`), wenn die Änderung mehrere Spuren/Launchlogik betrifft.

Ist der Worktree neben `BrainFiles` (z. B. `C:/Users/faupe/Documents/Handel-omni1d`), **verweigern Hermes' File-Tools Schreibzugriffe außerhalb der `HERMES_WRITE_SAFE_ROOT`** — edit über Terminal/Python-Heredoc (`python - <<'PY' ... PY`), nicht über `patch`/`write_file`. Worktrees haben **kein `.venv`** (nicht versioniert): Tests/Aufrufe laufen über den Interpreter des Hauptbaums (`C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/scanner/.venv/Scripts/python.exe`).

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

Die Bereinigung braucht Max' Freigabe. Bei Freigabe eine `.bak`-Sicherung der Runtime-Dateien anlegen, die Position aus dem offenen Bestand entfernen und einen expliziten Buchabgleich mit `preis`, `wert_usd` und P&L leer/null protokollieren. Nicht `erledigt`/Verkauf verwenden, wenn kein Ausstiegspreis belegt ist: die GUI und Auswertungen können diese Felder als realisierte Rendite interpretieren. Journal und Zustand nach Änderung bytegenau zum `journal_zweitziel` spiegeln; einen laufenden Dauerlauf beachten, der die Dateien unmittelbar neu schreiben kann.

Für die dauerhafte Abhilfe Code im eigenen `.worktrees/`-Worktree und test-first ändern: Vor Stop-/Kurs-/Verkaufspfad jede gebuchte Live-Seite und Kontraktmenge mit `/openpositions` abgleichen. Bei Abfragefehler, fehlender Position oder Mengenabweichung alarmieren und **keine** Order senden, nichts automatisch ausbuchen und keine Rendite buchen; Exchange-/Buchdifferenzen erfordern menschliche Klärung. Regressionstests müssen beweisen, dass bei Geister- und Teilbestand weder Stop noch Market-Verkauf oder Kurs-Exit ausgelöst wird. Die Omniquant-Suite ausführen, committen, PR erstellen; der Fix wirkt erst nach Merge und dem betrieblichen Neustart.

## Fallen

- **Zwei Zeitzonen im selben Befund.** `dauerlauf.log` schreibt **Lokalzeit**, Journale und `zustand.json` (`letzter_lauf`) schreiben **UTC-Isoformat**. Eine Logzeile `23:54` und ein `letzter_lauf` von `21:54Z` sind derselbe Zyklus. Vor jeder Aussage „die Spur läuft nicht mehr" oder „der Zustand ist alt" beide auf eine Zone bringen — sonst erfindet man eine zweistündige Lücke.
- **Ein frischer `letzter_lauf` beweist nur den Zyklus, nicht die Buchung.** Der Zustand wird an jedem Zyklusende neu geschrieben, auch wenn nichts passierte. Dass eine Datei frisch ist, sagt nichts darüber, ob ein Ausstieg oder Nachsatz stattgefunden hat — das steht im Journal und an der Börse.
- **PowerShell über git-bash:** `$_.X` und ähnliche Ausdrücke werden von bash zerlegt → die Befehlszeile von Prozessen nicht so abfragen. Ein `.ps1`-File schreiben und mit `powershell -ExecutionPolicy Bypass -File` ausführen, oder ein Python-Skript für die Abfrage. (`wmic process get CommandLine` in bash funktioniert zugig.)
- **PowerShell-Befehl als Argument an `wmic`/`Get-CimInstance`** opfert zur Laufzeit, wenn bash Interpolation frisst — skript-file Umweg ist der stabile Pfad.
