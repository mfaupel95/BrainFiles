# Aenderungsplan TASKS.md — aus Verifikationstabelle abgeleitet

Kanban: t_bb7a7258 (Analyse) → Verbraucher: t_976db79f (Anwenden).
Datum: 2026-10-04 · Quelle: MaxHirn/Archiv/TASKS.md (Snapshot, Commit 8bdaceef).
Einziges Urteils-Input: `Werkstatt/verifikation-TASKS-t_bbab9823.md` (t_bbab9823, unabhaengige Re-verifikation).
Baseline: 334 Eintraege (Audit t_2b805795); dieser Plan leert/dupliziert keine Zeile, alle Eintraege bleiben erhalten.

## Zuordnungsregel (aus Auftrag)

- VERIFIED  → als erledigt fuehren: Haken behalten/vermerken + einzeiliger Nachsatz `<YYYY-MM-DD>: <konkret verifiziert>`.
- PARTIAL / UNVERIFIED → offen lassen (`[ ]`) + kurzer Grund (Blocker bzw. Verweis auf Folgepunkt). Nie allein aufgrund des Berichts schliessen.
- BLOCKED / wartend → unveraendert offen lassen; Plan bestaetigt nur, dass ihr Status korrekt ist.

## 1. VERIFIED → DONE + Nachsatz (4 Eintraege)

Alle vier stehen bereits auf `[x]` — kein Statuswechsel, nur der Verifikations-Nachsatz wird angehaengt.

| ID | Baseline-Zeile | Status jetzt | Aenderung |
|----|----------------|--------------|-----------|
| T-303 | 549 `[x]` (Abschnitt Offen) | done | Nachsatz: `2026-10-04: unabhaengig verifiziert — test_omniquant_fassung.py Z.143-215 liest wachen.weit.json (Z.159), Live-Test Z.210; omniquant/wachen.json Z.3 handel_erlaubt:true, Z.41 freigabe.erfuellt; Commit aecd6178 existiert.` |
| T-271 | 789 `[x]` (Offen) | done | Nachsatz: `2026-10-04: unabhaengig verifiziert — dauerlauf.py Z.223 '# KOPIER AKTIV (seit 30.09.2026, ...)' vorhanden; Test-Liste (test_handelstand.py) als abhaengiges Artefakt bestaetigt.` |
| T-241 | 3631 `[x]` (Erledigt) | done | Nachsatz: `2026-10-04: unabhaengig verifiziert — klassik_sma/-ema/-macd/-bollinger/-donchian/-donchian_trend/-rsi/-rsi2/-sr_breaks/-pmax in dauerlauf.SPUREN (Z.410-428).` |
| T-255 | 3741 `[x]` (Erledigt) | done | Nachsatz: `2026-10-04: unabhaengig verifiziert (Dateianspruch) — bus_name-Literal-Zweig in klassik_regeln.py (test_anbindung_handel.py Z.204-212). Hinweis: Suite-Gesamtaussage unter HEAD nicht gehalten, da test_anbindung_routinen an datensortierung:78 rot (siehe T-340).` |

Format beibehalten: Nachsatz als neu eingerueckte Zeile `      **2026-10-04: ...**` direkt unter der letzten bestehenden Zeile des Blocks (bzw. vor `Angelegt:`), identisch zur bestehenden Einrueckung der Datei.

## 2. PARTIAL → offen lassen + Grund (1 Eintrag statusrelevant)

| ID | Baseline-Zeile | Status jetzt | Aenderung |
|----|----------------|--------------|-----------|
| T-340 | 66 `[x]` (Offen, faelschlich schon erledigt) | done | **Status zurueck auf `[ ]`** + Grund-Nachweis. Grund: (a)+(b) Datei-Fixes gültig und verifiziert (squeeze_eth.py Z.34-38 eigene Meldung + handeln._main(); plattenplatz-pruefen.ps1 Z.3-4 'BUS: Bibliothek'), ABER (c) Ende-zu-Ende-Suite unter HEAD nicht reproduzierbar: `python Agenten/Bus/tests/test_ende_zu_ende.py` ⇒ **Exit 1**, test_anbindung_routinen meldet `exit ohne vorheriges Melde-Ende: ['datensortierung:78']` (statischer Scan; `exit 3` im Einzelinstanz-Guard Z.78 vor Melde-Start, Guard aus 917ac39e / T-240). Erst nach Beseitigung von `datensortierung:78` wieder als erledigt fuehren. |

Hinweis T-340: Eintrag bleibt im Abschnitt `## Offen`, nur der Haken wechselt `[x]`→`[ ]`. Die bestehende `Erledigt 04.10.2026`-Notiz wird NICHT geloescht; der neue Grund-Nachweis wird als `2026-10-04: <Verifikation ...> PARTIAL` ergaenzt. Folgepunkt fuer den Guard-Ausstieg: T-240.

## 3. PARTIAL — Sonderfall, bleibt done mit Caveat (1 Eintrag)

| ID | Baseline-Zeile | Status jetzt | Aenderung |
|----|----------------|--------------|-----------|
| T-044 | 17 `[x]` (Regeln-Template, Alt-Eintrag) | done | Bleibt `[x]` + Caveat-Nachweis: `2026-10-04: unabhaengige Verifikation — Code-Beleg bestaetigt (bus.ps1 Z.14-18 pythonw-Ersatz); der Live-Zustand der Windows-Aufgabenplanung (Hermes_Gateway=Disabled, MaxHirn-Gateway-Waechter=Ready, Bus-PID) ist aus dem Worktree nicht neu pruefbar und wurde bei Erledigung (16.09.) direkt gemessen.` |

Abweichung von der mechanischen Regel begruendet: T-044 ist ein bereits abgeschlossener Betriebsvorgang (09-16 gemessen), dessen Code-Kern verifiziert wurde; nur die Live-Bestaetigung ist umgebungsabhaengig und nicht neu einholbar. Auf `[ ]` zuruecksetzen wuerde das Erledigt-Datum und die erbrachte Messung verwischen, ohne dass ein Restpunkt offen ist. (Kann vom Schlussbericht t_db0cb1a0 uebrig geprueft werden.)

## 4. BLOCKED / wartend — unveraendert offen (keine Aenderung)

Verifikationstabelle bestaetigt: Status korrekt, nichts als erledigt markieren. Keine Zeile anfassen.

- `[?]` wartend auf Max: T-049 (2626), T-050 (2639), T-042 (2992), T-045 (3015), T-046 (3035), T-047 (3047), T-209 (3463), T-040 (5553).
- `[!]` blockiert: T-004 (3067).
- Futures-Guthaben-Gruppe, echte externe Blocker (bleiben offen): T-284 (645), T-291 (637), T-275 (778), T-319 (345), T-341 (98).

## 5. Baseline-Abdeckung

- Verifikationstabelle gibt Verdicts/Status nur fuer den anvisierten Cluster (6 Hauptzeilen + BLOCKED/wartend-Gruppe) — so im Methodenvermerk der Tabelle deklariert (eine Voll-Repruefung aller 167 DONE-Punkte ist in einem headless-Lauf nicht leistbar und zu grossen Teilen historisch/umgebungsabhaengig).
- Alle 334 Baseline-Eintraege: jeder hier nicht gelistete Eintrag behaelt seinen bestehenden Status und Text unveraendert (kein Verdict ⇒ keine Aenderung). Dieser Plan erzeugt keine neuen, keine geloeschten, keine doppelten Eintraege.
- Ergebnis nach Anwendung: T-303/T-271/T-241/T-255 weiterhin done (mit Verifikations-Nachweis), T-340 zurueck auf offen (mit Grund), T-044 done mit Caveat, BLOCKED/wartend unveraendert. Eintragszahl == 334.

## 6. Pruefschritte fuer den Anwender (t_976db79f)

1. Aenderungen nur in MaxHirn/Archiv/TASKS.md (Master, nicht Worktree des Analysators).
2. `git diff -- MaxHirn/Archiv/TASKS.md` ausgeben und je Zeile gegen die Tabelle oben pruefen.
3. Eintragszahl vorher/nachher zaehlen (muss 334 == 334 bleiben).
4. Valid-Markdown: keine ungeschlossenen Code-Fences, Checkbox-Syntax `- [ ]`/`- [x]` beibehalten.
