# Spec: Konfig-Doktor (Teilprojekt A) — 2026-10-04

Teil 1 von 3 (A Konfigurationsgesundheit → B Ordnung und Ballast → C Regelwerk und Prozess). Jedes Teil hat eigene Spec und eigenen Plan.

## Ziel

Ein wiederholbares, **rein lesendes** Prüfskript `Agenten/Routinen/konfig-doktor.ps1`. Es prüft, ob die deklarierte Konfiguration von BrainFiles zur Wirklichkeit passt, und schreibt eine priorisierte Befundliste nach `Werkstatt/konfig-doktor-<datum>.md`. Reparaturen erfolgen nie im Skript, sondern erst nach Freigabe durch Max.

Erfolg: ein Lauf dauert unter 60 s, ändert nichts, nennt je Befund Beleg und Einstufung (gesichert / Vermutung), und lässt sich aus `systempruefung.ps1` aufrufen.

## Nicht-Ziele

- Keine Reparatur, kein Löschen, kein Schreiben außerhalb des Berichts.
- Kein Umbau von Hermes, Handel oder Bus. Kein Aufräumen (das ist Teilprojekt B), keine Regeländerung (Teilprojekt C).
- Keine Key-Werte ausgeben; nur Vorhandensein und Länge.

## Bestand (gesichert durch Inventur, 04.10.2026)

- `Agenten/MCP-Manifest.json`: 12 Server. Eine erste Prüfung meldete mehrere Pfade als fehlend (`dist/index.js`, `src/run_stdio.py`). Vermutung: relative Pfade wurden gegen das falsche Verzeichnis geprüft, statt gegen das `cwd` des Eintrags. Der Doktor muss das korrekt lösen.
- `Agenten/mcp-sync-check.ps1` existiert und ist in `systempruefung.ps1` eingehängt: wird erweitert, nicht ersetzt.
- Hermes: `config.yaml` 36 KB gegenüber Altkopie 94 KB, `auth.json.corrupt` vom 03.10., über 25 Profile unter `profiles/`.
- Session-MCP: Vanguard, Definite, Desktop-Commander in dieser Sitzung fehlgeschlagen.
- Wurzel `CLAUDE.md` und `AGENTS.md` unterschiedlich groß (Vermutung: Zeilenenden).
- Git: lokale und Remote-Zweige `claude/*`, `maks.420` widersprechen der Regel „sonst keine weiteren Zweige".

## Aufbau: sechs Prüfmodule

Jedes Modul liefert eine Liste von Befunden `{id, modul, schwere, titel, beleg, status, vorschlag}`. Module sind unabhängig und einzeln aufrufbar (`-Modul <name>`).

| # | Modul | Prüft |
|---|---|---|
| 1 | `mcp-pfade` | Jeder Manifest-Eintrag: `command`/`args`-Pfade existieren, aufgelöst gegen das `cwd` des Eintrags; Abgleich mit `mcp-sync-check.ps1`; auffällige Starter (Netz-Pipes, Pfade außerhalb der Wurzel) |
| 2 | `hermes` | Effektives Home (`HERMES_HOME`), Hauptconfig gegenüber Profilen, Auth-Datei (`expires_at`, `.corrupt`-Reste), Selbstdiagnose nur mit bereinigter Umgebung (`PYTHONHOME`/`PYTHONPATH` entfernt), letzte Fehlerzeilen der Logs |
| 3 | `regelpaare` | `CLAUDE.md`=`AGENTS.md` in Wurzel, `MaxHirn/`, `Werkstatt/`; Vergleich zeilenendenunabhängig, Abweichung getrennt von reinem CRLF/LF-Unterschied melden |
| 4 | `git-regeln` | Zweige gegen die Zweigregel; ruhende, uncommittete Dateien (Alter); Besitz-Verstöße über `bereiche.py --register` |
| 5 | `ballast` | Nur Meldung von Dubletten und Altkopien (`*.bak`, `*.vor-*`, doppelte Skriptnamen, `.txt`-Zwillinge von Configs, Zusatzordner wie `Agenten/Werkstatt/`) — Aufräumen bleibt Teilprojekt B |
| 6 | `laufzeit` | Plattenplatz und Commit-Reserve (vorhandenes `plattenplatz-pruefen.ps1` aufrufen), Junctions `Modelle/` und `Werkstatt/` erreichbar, Docker/WSL-Zustand (nur Zustand, kein Start) |

## Priorisierung der Befunde

Vier Stufen, feste Zuordnung je Befundart:

- **KRITISCH** — etwas Deklariertes funktioniert nachweislich nicht oder gefährdet Daten (Manifest-Pfad fehlt, Auth-Datei defekt, Junction tot, Commit-Reserve unter Schwelle).
- **WARNUNG** — Regel verletzt, aber nichts bricht (Zweig-Regelverstoß, Paar-Abweichung im Inhalt, Besitz-Verstoß).
- **HINWEIS** — Ballast, Dubletten, Altkopien.
- **UNKLAR** — nicht belegbar; steht mit der Information, die zur Entscheidung fehlt. Wird nie als Fehler gewertet.

Jeder Befund trägt **gesichert** (Kommando und Ausgabe liegen vor) oder **Vermutung**. Sortierung im Bericht: Stufe, dann Hebelwirkung.

## Fehlerverhalten

- Ein Modul, das scheitert, erzeugt einen Befund `PRUEFUNG-FEHLGESCHLAGEN` und stoppt die anderen nicht.
- Zeitlimit je Modul 20 s; Überschreitung wird als UNKLAR gemeldet, nicht als Fehler. Kein rekursives Durchlaufen von `Agenten/Hermes/installs` und `profiles` (439.037 und 126.099 Dateien, hat zuvor ein Zeitlimit gerissen): nur gezielte Abfragen.
- `ErrorActionPreference='Continue'`; Git-Aufrufe über Exit-Code, nicht über stderr (bekannte NativeCommandError-Falle).
- Keine Annahme über das Arbeitsverzeichnis: alles wird aus `$PSScriptRoot` zur Wurzel aufgelöst.
- In einem Linux-/Cloud-Checkout (Junctions fehlen) werden Module 2 und 6 als UNKLAR übersprungen, nicht als Fehler.
- Exit-Code: 0 = keine KRITISCH, 1 = mindestens ein KRITISCH, 2 = Doktor selbst defekt.

## Ausgabe

- Bericht `Werkstatt/konfig-doktor-<yyyy-MM-dd>.md`: Zusammenfassung (Anzahl je Stufe), Befundtabelle `# | Befund | Belegt durch | Status | Vorschlag`, Abschnitt „nicht prüfbar".
- Konsole: eine Zeile je Stufe plus Pfad zum Bericht. `systempruefung.ps1` zeigt nur die Zählung.
- Der Bericht enthält nie Key-Werte oder Auth-Inhalte.

## Tests

- Kein Test-Framework (Hausstil wie bei den Bus-Tests): Tests als ausführbares PowerShell-Skript `Agenten/Routinen/tests/konfig-doktor.test.ps1` im Stil der Bus-Tests: endet mit „konfig-doktor bestanden".
- Jedes Modul bekommt Fixtures in einem Temp-Ordner (Mini-Manifest mit vorhandenem und fehlendem Pfad, zwei Regeldateien mit nur-CRLF- und inhaltlicher Abweichung, Fake-Auth-Datei) und wird gegen diese geprüft: positiver Fall, negativer Fall, Modulfehler wird isoliert.
- Gegenprobe gegen die echte Wurzel: Lauf ändert `git status` nicht (Vorher/Nachher-Vergleich).
- Der echte Lauf darf die zu Beginn bekannten Befunde finden (Zweige, `auth.json.corrupt`, Doppelskripte); ob die Manifest-Pfade wirklich fehlen, klärt Modul 1 erst mit korrektem `cwd`.

## Einbindung

- `systempruefung.ps1` ruft `konfig-doktor.ps1 -Kurz` auf (nur Zählung, kein Bericht). Änderung dort gezielt, kein Neuschreiben (Zeilenenden-Regel).
- Dokumentation: kurzer Eintrag in `MaxHirn/Wissen/Routinen.md` (Bereich `wissen`). Besitz-Konflikte werden als BEFUND gemeldet.
- Commit direkt auf `master`, keine eigenen Zweige. Ausführung per Teilplan, jede Aufgabe mit eigenem Test.

## Offene Punkte (klärt der Doktor selbst oder Max)

- Ist das Schrumpfen der Hermes-Config von 94 auf 36 KB gewollt? (Doktor meldet UNKLAR; Entscheidung Max.)
- Welche der fehlgeschlagenen Session-MCP-Server sind absichtlich ohne Anmeldung? (Wird gemeldet, nicht entschieden.)
