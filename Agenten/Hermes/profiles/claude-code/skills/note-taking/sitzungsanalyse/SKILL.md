---
name: sitzungsanalyse
version: 1.0.0
description: 'Use when analyzing past agent sessions into vault notes.'
---

# Sitzungsanalyse (Transkripte → Vault)

Analyse von Claude-Transkripten und Hermes-Sitzungsdaten über mehrere Sitzungen
mit Integration der Ergebnisse als Vault-Notiz.

## Quellen

- Claude-Transkripte: `~/.claude/projects/**/*.jsonl`. Nur Einträge mit
  `type == "user"` lesen; `content` als String, filtere Einträge die mit `<` oder
  `[{` beginnen (System-/Tool-Nachrichten). Zeilenweise JSON, je Datei try/except.
- Hermes-Sitzungen: `Agenten/Hermes/profiles/*/state.db` (Tabelle messages).
- **Offene Punkte und Fehler-Klassen stehen bereits in `Archiv/TASKS.md`** —
  diese Datei lesen statt Fehlermuster aus Transkripten zu raten. `Wissen/INDEX.md`
  nennt die bestehenden Notizen; deren `summary`-Felder liefern die Erfolgsspalte.

## Vorgehen

1. `TASKS.md` und `Wissen/INDEX.md` zuerst lesen — das sind die kuratierten
   Quellen für offene Punkte, Fehlerklassen und Erfolge. Transkripte nur für
   das ergänzen, was dort fehlt.
2. Transkripte in EINEM execute_code-Durchlauf einlesen (Zeitstempel oben,
   User-Nachrichten mit `timestamp` und `content[:300]` sammeln).
3. Themen-Klassifizierung mit KOMPAKTEN Keyword-Listen (max ~40 Stichwörter
   pro Cluster, klein geschrieben, auf `content.lower()` prüfen).
4. Ergebnisse als Vault-Notiz `Wissen/Sitzungsanalyse-<JJJJ-MM-TT>.md` schreiben:
   Frontmatter (`id: JJJJMMTT-slug`, `title`, `tags`, `created`, `updated`,
   `related`, `summary`), Themencluster, Fehlerklassen (Muster + Ursache,
   KEINE Task-IDs als Inhalt), offene Punkte, Erfolge mit Messzahlen.
5. Registry-Eintrag in `Wissen/INDEX.md` im selben Arbeitsschritt nachziehen
   (dort unter `### Verfahren` anhängen) — ohne Index-Eintrag ist die Notiz
   für andere Agenten unsichtbar.
6. Ziel abschließend mit GEZIELTEM Einzelfall-Check verifizieren:
   `wc -l <datei>` und `grep -n <id> Wissen/INDEX.md`. Kein `ls | head`
   als Beweis — seine Ausgabe kann transient leer aussehen.

## Fallstricke

- Baue KEINE Keyword-Listen mit hunderten Einträgen im Code-Editor — der
  Code wird unlesbar, bricht die Zeilenlängen des Kernels und eine einzige
  vergessene Klammer kostet einen ganzen Ausführungsversuch.
- Keine rekursiven `glob(..., recursive=True)`-Scans über `~/Documents` oder
  das gesamte Home — dort liegen `.claude/projects`, Docker-Profile und
  Bibliotheksordner mit Millionen Dateien; die Suche läuft in den Timeout.
  Immer einen konkreten Unterordner als Startpunkt nehmen.
- Eine `write_file`-Meldung `verified: true` gilt — eine darauffolgende
  single-shot `ls`-Prüfung kann transient fehlschlagen. Erst mit Suchtool
  (`search_files`, `wc -l`) gegenprüfen, dann dem verified-Ergebnis trauen,
  nicht dem einen Shell-Befehl.
