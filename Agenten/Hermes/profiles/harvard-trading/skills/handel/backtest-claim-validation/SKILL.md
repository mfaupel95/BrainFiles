---
name: backtest-claim-validation
description: "Use when validating a backtest or strategy claim."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Backtest, Statistik, Regime, Mehrfachtestung, Papierhandel]
---

# Backtest- und Strategie-Aussagen statistisch pruefen

Use when a number, a filter, a parameter or a regime claim should become a rule. The
question is never "is the t-value big" — it is "how many independent observations stand
behind it, and does the effect exceed what that number can see at all".

## When to Use

- Ein Filter, ein Parameter, ein Regime oder ein "die Spur schneidet besser ab"-Ergebnis
  soll eine Regel werden (oder eine Spur scharf gehen).
- Jemand behauptet eine Kante und nennt nur einen t-Wert, ein p oder eine Sharpe.
- Eine Regime-/Marktlagen-Kennzahl wird gefordert — und die Frage ist, ob sie einen
  Schalter steuern darf.
- Eine Parameter-Suche "hat gefunden" — und geprueft werden muss, ob das mehr ist als
  der beste Ausreisser von N Versuchen.
- Ein Backtest-Ergebnis soll dokumentiert werden; die Aussage braucht eine Zahl mit
  Quelle (Kerzenfenster, Kosten, Rundenzahl).

## Grundregeln

- **Erst die effektive Beobachtungszahl, dann die Statistik.** Die Zahl ist die Anzahl
  unabhaengiger *Episoden/Wechsel*, nicht die Anzahl Kerzen, Fenster oder Runden.
- **Ein nicht-signifikantes Ergebnis bei kleinem n ist KEIN Gegenbeweis.** Es ist
  "untermaessig" (underpowered). Genau das melden, mit der Zahl.
- **Die Trial-Zahl ist `labels x fenster x parameter_kombinationen`.** Alpha wird mit
  diesem Produkt korrigiert (Bonferroni, oder Benjamini-Yekutieli bei korrelierten Tests).
- **Praezision des Labels ist nicht Praezision der Kante.** Ein Regime-Label, das auf
  zehntausend Bloecken gemessen wurde, hat ein schmales Konfidenzintervall und traegt
  trotzdem nichts, wenn die Kante pro Episode zaehlt.
- **Eine Trennung ohne Handelbarkeit ist kein Ergebnis.** Beide Seiten muessen genug
  Runden haben und die gute Seite muss nach Kosten ueber Null liegen.
- **Ohne Kostenmodell keine Aussage.** Netto je Runde, Gebuehr je Seite, Anzahl Runden.
- **Die Kostenannahme ist selbst eine zu pruefende Zahl.** Die **Break-even-Gebuehr je
  Seite** nennen — liegt die im Skript angenommene Gebuehr darueber, haengt das
  Vorzeichen der Aussage von der Annahme ab, nicht von der Strategie.
- **Die Kostenrate traegt eine Herkunft, und die Herkunft steht neben der Zahl.** Aus
  echten Fuells gemessen, als Annahme gesetzt, oder hart im Fremd-Repo hinterlegt? Ein
  hardcodierter `commission=` in einem Beispielskript ist eine ANNAHME, nie eine
  Messung — wer ihn als Messwert ausgibt, verfaelscht die Aussage. Die angenommene Rate
  zusaetzlich gegen den veroeffentlichten Gebuehrplan des Handelsplatzes halten
  (Taker/Maker, mit Quelle) und das Vielfache nennen: liegt die Annahme vielfach ueber
  dem realen Taker-Satz, ist genau das die fehlende Information, nicht der Sweep.
- **Papier zuerst, immer.** Kein Live-Pfad, keine Order, keine Schluessel. Ein Regelfund
  landet als Vorschlag, nicht als verdrahteter Schalter.

## Procedure

1. **Behauptung und Entscheidung benennen.** Welche Regel wuerde aus dem Ergebnis folgen?
   Ohne die Entscheidung ist das Ergebnis nicht bewertbar.
2. **Effektive Beobachtungszahl zaehlen.** Wechsel/Episoden, nicht Bars. Werkzeug:
   `scripts/regime_probe.py <kerzen.csv> --block-stunden 4 --quantil 0.5`.
3. **Mindest-detectablen Effekt rechnen** (Power 80 %, korrigiertes alpha) und gegen den
   beobachteten Effekt stellen. Liegt der beobachtete darunter, ist das Ergebnis
   "untermaessig" — nicht "kein Effekt".
4. **Alpha korrigieren** mit labels x fenster x parameter.
5. **Ergebnis je Fenster und je Seite getrennt ausweisen.** Schwellen nur auf dem
   Suchfenster bestimmen, dann auf das Prueffenster anwenden.
6. **Kostenachse sweepen und Break-even nennen.** Gebuehr je Seite von 0 bis deutlich
   ueber die angenommene Hoehe fahren, dazu `spread`, wenn die Engine das kann; je Stufe
   Return **und Rundenzahl** ausgeben (eine Kostenaenderung ist nicht immer additiv —
   sie kann Orders abbrechen und damit die Rundenzahl verschieben). Netto je Runde
   ausweisen.
7. **Selektionsstatistik statt Ergebnis.** Kommt die Zahl aus `optimize(maximize=...)`,
   ist sie der Maximumwert von N Versuchen: aus dem Gitter eine Stichprobe ziehen, Mittel
   und Sigma messen, danebenstellen, wo der erwartete Bestwert liegt, und den Return
   zwischen zwei Fensterhaelften korrelieren. Korrelation nicht deutlich ueber Null ->
   kein Parameter traegt, egal was das Gitter gemeldet hat. Rezept:
   `references/backtesting-py.md`.
8. **Bericht in dieser Reihenfolge:** Wechselzahl -> Mindest-detectabler Effekt ->
   korrigiertes alpha -> Break-even-Gebuehr je Seite -> beobachteter Effekt -> Verdikt
   -> Entscheidung.
9. **Den echten Strategie-Code fahren**, nie eine Nachbildung. Ein Test, der die Spur
   selbst faehrt, prueft die Spur; eine Nachbildung prueft die Nachbildung. Laeuft das
   Beispielskript beim Import schon fertig (Daten laden, Backtest fahren), die Klasse
   per `exec` aus Kopfzeilen + Klassendefinition holen und den Datenladeteil selbst
   ersetzen — siehe `references/backtesting-py.md`. Harte absolute Datenpfade
   (`/Users/...`) heissen: das Beispiel ist wie eingecheckt nicht lauffaehig. Den Pfad
   ersetzen und die Luecke als Befund melden, das Beispiel nicht aufgeben.
10. **Den Fund als Messprotokoll und Test in das Repo schreiben.** Reicht die Aussage als
    Bericht, fehlt die Nachvollziehbarkeit: ein Dokument neben dem Code, das Kostensatz,
    Fenster, Kerzenzahl, Rundenzahl, Break-even und Gittergroesse traegt, dazu ein Test,
    der die Invarianten festhaelt (Kopfzeile und Zeilenzahl der CSV, Kostenkonstanten im
    Code, keine harten Pfade). Damit ist eine spaetere Aenderung am Kostensatz oder am
    Datenbestand sofort als Diff sichtbar. Committen und in den eigenen Fork pushen — nie
    in den Upstream des Fremd-Repos — und am Ende nennen, was absichtlich NICHT angefasst
    wurde. Steht keine globale Git-Identitaet, je Commit mit
    `git -c user.name=<bot> -c user.email=<bot>@users.noreply.github.com commit`; pushen
    nur nach `origin` (eigener Fork).

## Pitfalls

- **Nicht-signifikant heisst nicht "kein Effekt".** Bei 12 Fenstern ist der kleinste
  sichtbare Korrelationskoeffizient rund 0.73. Alles darunter ist unsichtbar — ein
  Nullresultat dort hat keine Aussagekraft und darf nicht als Gegenbeweis gelesen werden.
- **Best-of-many-Fenster waehlt das gluecklichste Fenster.** Dafuer CSCV bzw. stationaeren
  Bootstrap; sonst ist das beste Fenster eine Ausreisser-Suche.
- **Eine Parameter-Suche ueber 'Equity Final' ist eine Ausreisser-Suche.** Der erwartete
  Bestwert von N Ziehungen liegt bei `Mittel + Blom(N) * Sigma`; der gemeldete
  Optimalfund ist deshalb immer besser als die Strategie — und das ist kein Beweis.
  Messen statt glauben: Stichprobe aus dem Gitter, Mittel/Sigma, Halbzeit-Korrelation.
- **Die Gittergroesse ausrechnen, nicht aus den `range()`-Grenzen ablesen.**
  `range(10, 15, 5)` liefert EINEN Wert, `range(10, 20, 5)` zwei — die Anzahl steht nicht
  in den Grenzen. Jede Achse mit `len(...)` zaehlen, multiplizieren, das Ergebnis
  ausgeben, und erst dann ein N in eine Formel setzen. Ein falsch abgelesenes N
  verfaelscht gleichzeitig die Trial-Korrektur und den erwarteten Bestwert.
- **Vollsweep nur in EINEM Prozess.** Mehrere parallele Backtest-Laeufe auf einem
  ausgelasteten Rechner werfen `MemoryError` mitten im Sweep (gemessen: 63,7 GB RAM,
  unter Last ~15 GB frei, drei parallele Optimierer -> Abbruch). Mittel/Sigma aus einer
  Stichprobe von 40 genuegt; den Vollsweep ohne Konkurrenz fahren.
- **Ein Beispielskript, das beim Import durchlaeuft, ist nicht importierbar — aber seine
  Klasse ist es.** Kopfzeilen + Klassendefinition per `exec`, Datenladeteil selbst
  bauen. Wer das weglaesst, optimiert still eine Nachbildung.
- **Vorhersagen ueber die Engine pruefen, nicht behaupten.** Bevor gesagt wird, ein
  Kostenknopf existiere nicht, `inspect.signature` ausgeben: die Bezeichnung
  unterscheidet sich je nach Bibliothek (`spread` vs. `slippage`), und ein Fehler dort
  landet als falsche Aussage im Bericht.
- **Ein selbst gebautes Gitter ist ein anderes Gitter.** Wer die Achsen selbst
  zusammensetzt, nimmt leicht Parameterwerte mit, die die Datei nie sucht. Mittel, Sigma
  und Korrelation aus so einem Gitter sind dann nicht die Zahlen des Repos — und
  veroeffentlicht als solche muessen sie zurueckgenommen werden. Stichprobe IMMER aus dem
  Gitter ziehen, das der Code wirklich durchsucht, und die Gittergroesse aus der Ausgabe
  des Skriptes uebernehmen statt nachzurechnen.
- **Ein umgestuerztes Vorzeichen ist eine Ruecknahme, kein Fussnotenanhang.** Wird eine
  bereits gemeldete Aussage durch eine besser belegte Kostenrate falsch, die Aussage
  zuruecknehmen und nennen, welche Zahl sie stuetzte — nicht darueber schreiben und nicht
  nur einen Nachtrag haengen.
- **Ueberlappende Fenster sind keine unabhaengigen Beobachtungen.** Schritt >= Fensterlaenge.
- **Median-Split-Labels auf kurzen Zeitrahmen sind eine Muenze.** Wechselquote nahe 0,5
  heisst: das "Regime" hat die Periodendauer der Blockgroesse. `p_hat` und mittlere
  Episodendauer melden; ist die Episode kuerzer als der Handels-Takt, ist das Label
  unbrauchbar.
- **Eine grosse Differenz kann trotzdem unsichtbar sein.** Eine 40-%-gegen-80-%-Trennung
  braucht rund 20 Runden je Regime; darunter ist selbst sie nicht von Zufall zu
  unterscheiden.
- **Erwartungswerte vorher nennen.** Bei N Tests und alpha = 5 % sind N * 0,05 Treffer
  erwartbar. 1-3 konsistente Treffer bei 16 Tests sind das Nullresultat.
- **Replay-Optimierung optimiert die Nachbildung.** Den echten Code-Pfad fahren.
- **Ein Filter, der eine strukturell verlierende Spur nur halbiert, macht sie nicht
  handelbar.** Beide Seiten muessen nach Kosten ueber Null kommen.

## Werkzeug / Umgebung

- `scripts/regime_probe.py` braucht `pandas` + `numpy`. Sind sie im Interpreter nicht
  da: bevorzugt einen eigenen Interpreter in den Scratch-Ordner und damit die Pfadfallen
  umgehen — `uv venv --python 3.14 <scratch>/venv`, dann
  `uv pip install --python <scratch>/venv/Scripts/python.exe pandas numpy` und
  `<scratch>/venv/Scripts/python.exe <skript>`. Ohne `uv`:
  `python3 -m pip install --target <scratch>/pylibs pandas numpy` plus
  `PYTHONPATH=<scratch>/pylibs python3 <skript>`.
  In beiden Faellen **Windows-Pfade** (`C:/Users/<user>/...`) verwenden, nie MSYS-`/tmp`-
  Pfade — native Windows-Programme lesen `/tmp` nicht.
- Fuer Backtests mit Indikatoren: `TA-Lib` (native Binary) und `backtesting`. Der
  PyPI-Name ist `backtesting`, NICHT `backtesting.py`.
- CSV-Exporte von yfinance/Export tragen kleingeschriebene Spalten; Skripte muessen sie
  normalisieren (`df.columns = [c.capitalize() for c in df.columns]`), sonst heisst es
  `KeyError: 'Close'`.

## Quick Reference

- Probe: `scripts/regime_probe.py <kerzen.csv> --block-stunden 4 --quantil 0.5 --takt-stunden 24`
- Mehrfachtestung und benannte Verfahren: `references/mehrfachtestung.md`
- Regime-Tests im Detail: `references/regime-tests.md`
- Kostenmodell, Gitter-Ausreisser, Skripte ohne Import: `references/backtesting-py.md`
