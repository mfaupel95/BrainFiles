---
name: hermes-config-ops
description: "Hermes config.yaml/.env ändern — belegt, ohne Neustart."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, config, secrets, brainfiles, verifikation]
    related_skills: [skill-library-sync]
---

# Hermes' eigene Konfiguration ändern

Änderungen an `Agenten/Hermes/config.yaml` und `.env` so ausführen, dass kein
Geheimnis im Klartext in der Konfiguration steht, laufende Agenten unberührt
weiterlaufen und die Änderung mit einem echten Lauf belegt ist.

## Wann

- "da steht ein Schlüssel im Klartext", "der Token gehört da nicht rein",
  "fix das, ohne die Agenten zu stören"
- eine Einstellung in `config.yaml` soll anders sein (Arbeitsverzeichnis,
  Backend, Timeout)
- nach einem Update oder Setup, das Werte materialisiert hat

**Don't use for:** MCP-Server-Einträge zwischen Claude und Hermes (`mcp-sync`),
Skill-Kopien (`skill-library-sync`), Update/venv/SQLite (`hermes-maintenance`).

## Regeln (immer)

1. **Zwei Ablagen, klar getrennt.** Menschliche Ablage ist `Wissen/Zugaenge.md` —
   nie lesen, nie ausgeben, nie protokollieren. Maschinell gelesen wird
   `Agenten/Hermes/.env`. Einen Wert, den die `.env` schon hält, **nicht ein
   zweites Mal** ablegen: sonst gibt es zwei Stellen zum Rotieren.
   `config.yaml` enthält nur `${NAME}`-Verweise.
2. **Kein Geheimnis in einer Kommandozeile.** Werte in der Datei lesen, ausgeben nur
   Länge und SHA-256-Anfang. PowerShell gibt Argumente in Fehlermeldungen im
   Klartext aus — ein Secret in einem Befehl steht danach im Protokoll.
   Verglichen wird über Hashes, nie über Werte.
3. **Nie einen laufenden Agenten neu starten**, um eine Änderung wirksam zu machen.
   So ändern, dass der Prozess weiterläuft. Beleg: `hermes gateway status`
   (Aufgabe registriert, Prozess läuft) vor und nach der Änderung.
4. **Stufe 1:** vor jeder Änderung an `Agenten/Hermes/**`
   `Agenten/Hermes/.sicherung/<datei>.bak-JJJJMMTT`.
5. **Genau eine Zeile, wo eine Zeile gemeint ist.** Danach belegen, dass nur sie
   sich geändert hat: `Compare-Object` Sicherung gegen Datei — genau ein Zeilenpaar.
6. **Kodierung erhalten.** Vorher BOM und Zeilenenden bestimmen (LF vs. CRLF),
   schreiben mit `[System.IO.File]::WriteAllText($p,$t,(New-Object System.Text.UTF8Encoding($false)))`,
   danach gegenprüfen: `EF BB BF` (BOM) und `C3 83` (doppelt kodierte Umlaute) = 0.
7. **Vault-Notiz nachziehen** (`Wissen/Hermes.md`, Stufe 1 → vorher `.bak-JJJJMMTT`),
   dann `git -C <BrainFiles> commit --author="Hermes <hermes@local>" -- <pfad>` —
   nur benannte Pfade, nie `-A`. Liegt im selben File fremde uncommittete Arbeit,
   im Commit-Text benennen statt einen Urheber zu raten.

## Klartext-Geheimnis auf einen Verweis umstellen

1. **Fundstelle und Umfang** bestimmen: alle Zeilen mit `api_key|token|secret|password`
   in `config.yaml` auflisten, Werte redigieren (nur Länge ausgeben).
2. **Kandidat in der `.env` suchen**: SHA-256-Anfang jedes `NAME=WERT` gegen den Fund
   hashen. Treffer = Variablenname, fertig. Kein Treffer → sprechenden Namen in der
   `.env` anlegen. Hermes' eigene Namen (`HERMES_CUSTOM_<host>_<port>_API_KEY`) sind
   stabil, solange der Provider-Eintrag bleibt — der Verweis darf sie mitbenutzen.
3. **Sichern, dann die eine Zeile ersetzen:** `token: ${NAME}`. Regex mit
   `MatchEvaluator`, **nicht** mit Ersatzstring — `$` und `${…}` im Ersatz würden sonst
   als Gruppenreferenz gedeutet.
4. **Auflösung belegen:**
   `scripts/config-wert-pruefen.py --pfad <punktpfad>` — Länge und `sha8` müssen dem
   Vorher-Wert entsprechen (identischer Wert = der Dienst läuft unverändert weiter).
5. **Speicher-Rundlauf belegen** (derselbe Aufruf mit `--speicherprobe`): kopiert die
   `config.yaml` in ein Temp-`HERMES_HOME`, belegt die Variable mit einem Dummy, speichert
   und zeigt, dass danach weiter `${NAME}` in der Datei steht. Erst damit ist belegt, dass
   die laufende App den Klartext nicht beim nächsten Speichern zurückholt.
6. Erst dann Notiz und Commit.

## Fallen

- **`${NAME}` ist kein Klartext.** Wer eine Datei nach Zugangswerten durchsucht,
  muss Verweis und Wert am `$` unterscheiden - nicht nur `${env:…}` ausnehmen.
  Ein Zaehler, der `${HERMES_CUSTOM_…_API_KEY}` als "gesetzt, 40 Zeichen"
  meldet, erzeugt einen Fehlalarm ueber 13 Dateien, und ein Fehlalarm kostet
  mehr Vertrauen als die Pruefung Zeit. Bei jeder Meldung die Fundstelle je
  Datei einzeln nachsehen: ein leerer Treffer kann auch heissen, dass der Block
  fehlt (das Profil `nous` hat gar kein `a2a_agents`).
- `hermes config get <pfad>` kennt nur Schlüssel aus `DEFAULT_CONFIG`; eigene Blöcke
  (z. B. `a2a_agents`) melden fälschlich „Config key not set". Kein Fehler — über
  `load_config()` prüfen.
- `hermes config set` schreibt die ganze Datei neu und kennt dieselbe Grenze. Für eine
  einzelne Zeile ist der chirurgische Ersatz nachvollziehbarer: eine Zeile geändert,
  `Compare-Object` beweist es.
- Auflösung passiert beim **Laden**: `${VAR}` und `${env:VAR}` werden in allen
  String-Werten ersetzt (`hermes_cli/config.py::_expand_env_vars`). Ein nicht auflösbarer
  Verweis bleibt als Text stehen und warnt — `istVerweis: true` in der Prüfausgabe heißt
  also **Variable fehlt**, nicht „Mechanik kaputt".
- Beim Speichern bleibt die Vorlage erhalten (`_preserve_env_ref_templates`). Die Sorge
  „der Klartext kommt zurück" ist damit widerlegt — `--speicherprobe` ist der Beleg.
- `HERMES_HOME` **vor dem ersten Import** setzen (`$env:HERMES_HOME='…\Agenten\Hermes'`):
  Kindprozesse erben die Benutzervariable nicht zuverlässig, sonst zeigt der Lauf auf das
  Standardprofil und liest eine andere `config.yaml`.
- PowerShell-Helfer nie `H` nennen (Alias von `Get-History`) — der Fehler gibt dann
  Argumente im Klartext aus. Umlaute und mehrzeilige Blöcke nicht über die Kommandozeile
  transportieren: mehrzeiligen Text als Datei schreiben oder als Array mit
  `-join [char]10` bauen.

## Nachweis (Abschluss)

- `scripts/config-wert-pruefen.py` meldet denselben `sha8` wie vorher.
- `Compare-Object` Sicherung ↔ Datei: genau eine geänderte Zeile.
- `hermes gateway status`: Aufgabe registriert, Prozess läuft — ohne Neustart.
- `Wissen/Hermes.md` nennt Änderung, Prüfweg, Sicherungspfad und Falle; committet.
