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
   **Die Profil-`.env` tragen echte Secrets im Klartext** (`ANTHROPIC_TOKEN`,
   `GITHUB_TOKEN`, `OPENROUTER_API_KEY`, `HF_TOKEN` u.a.), nicht Platzhalter. Bei
   Arbeiten daran: nur Laenge und Hash vergleichen, **nie** Werte ausgeben — auch
   nicht in eine Fehlermeldung oder ein Protokoll. Und daran denken, dass diese
   Dateien von `sichern.ps1` mitkopiert werden: die Secrets liegen damit auf jedem
   Sicherungsdatentraeger im Klartext. Beim Melden sagen, nicht selbst umbauen.
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
   danach gegenprüfen: `EF BB BF` (BOM) und `C3 83` (doppelt kodierte Umlaute) = 0.
   Fuer die Ein-Zeilen-Aenderung `scripts/zeile-ersetzen.py` nehmen (Trockenlauf,
   dann `--tun`) — es erhaelt Zeilenenden und BOM und bricht bei mehrdeutigem
   Treffer ab. PowerShell-Variante, wenn ohnehin in PowerShell gearbeitet wird:
   `[System.IO.File]::WriteAllText($p,$t,(New-Object System.Text.UTF8Encoding($false)))`.
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

## HERMES_WRITE_SAFE_ROOT (Schreib-Sandbox)

Nicht in der Registry und nicht in `config.yaml` — in der **`.env`**. Zeile 630 in
`config.yaml` ist nur ein Name in `terminal.docker_forward_env`, kein Wert.

- `Agenten/Hermes/.env` (Hauptablage) **und** `Agenten/Hermes/profiles/<name>/.env`
  (jedes Profil fuehrt den Wert selbst). **Alle Kopien nachziehen**, sonst wirkt die
  Aenderung nur im Hauptprofil. Vorher **und nachher** aufzaehlen — ein `grep` findet
  nur, was die Zeile schon hat:

  ```bash
  grep -rn "HERMES_WRITE_SAFE_ROOT=" Agenten/Hermes --include=.env
  ```

  Zwei Faelle, die das `grep` **nicht** findet und die man getrennt pruefen muss:
  eine `.env` **ohne** die Zeile (dann anlegen) und eine `.env` mit einem **zu
  kurzen** Wert (dann erweitern). Beide Faelle sind der Normalfall, nicht die
  Ausnahme: von 18 Profil-`.env` trugen zwei den Wert vollstaendig, 13 einen zu
  kurzen, drei gar keinen.
- **Nur die Profile pruefen, die den Pfad wirklich brauchen** — sonst wird die
  Wache zum Dauer-Alarm. Kennzeichen ist der Bezug im `SOUL.md` des Profils:
  die Datei nennt `Werkstatt`. Ein Profil ohne diesen Bezug braucht den
  Werkstatt-Pfad nicht; ein Profil **ohne** eigene `.env` erbt von der
  Haupt-`.env` und ist damit gesund.
- **Nach dem Setzen maschinell nachweisen**, dass jede Kopie stimmt: die `.env`
  wie Hermes einlesen, `get_safe_write_roots()` aufrufen, `is_write_denied(<ziel>)`
  je Ziel ausgeben. Gegenprobe, die den Wert wirklich traegt: eine Datei
  absichtlich zurueckdrehen und pruefen, dass die Pruefung anschlaegt.
- Trennzeichen ist `os.pathsep` (`;` unter Windows); mehrere Wurzeln sind vorgesehen
  (`agent/file_safety.py::get_safe_write_roots`, realpath + expanduser).
- **Wirkt nur in neuen Sitzungen.** Die laufende hat die alte Umgebung im Prozess;
  ein Schreibversuch aus ihr belegt die Grenze, nicht die Aenderung.
- **Nachweis** ohne Neustart: `.env` wie Hermes einlesen, dann
  `get_safe_write_roots()` und `is_write_denied(<ziel>)` je Ziel ausgeben —
  neue Wurzel ERLAUBT, `C:\Windows\...` und `~/.ssh` GESPERRT.
- Beim Setzen daran denken: `BrainFiles\Werkstatt` ist ein **Symlink auf `O:\Werkstatt`**.
  Der Pruefer loest auf, eine Sandbox auf `BrainFiles` allein sperrt also alle
  Werkstatt-Repos.

## Claude Code CLI aktualisieren (nicht Hermes)

Nicht der eigene Befehl, aber oft gefragt und mit zwei Fallen. Installationsart
pruefen: `claude doctor` sagt `native` oder `npm`.

- **`claude update` sagt "up to date", obwohl es Neueres gibt** - dann zuerst den
  **Kanal** pruefen, nicht den Schalter. Kanal steht in
  `C:\Users\faupe\.claude\settings.json` als `autoUpdatesChannel`.
- Kanaele direkt abfragen (der schnellste Beleg):
  `BASE=https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases`,
  dann `curl -sS "$BASE/stable"` und `"$BASE/latest"`. `beta`/`next` gibt es nicht.
- `autoUpdates: false` in `C:\Users\faupe\.claude.json` blockiert **auch** den
  ausdruecklichen Befehl. Fuer das Update voruebergehend auf `true`, danach zurueck.
- **Das laufende Binary muss nicht frei sein.** Es ist gesperrt, der Updater legt die
  neue Version nach `~/.local/share/claude/versions/` und schaltet den Launcher um -
  laufende Sitzungen und das Gateway laufen weiter, kein Neustart noetig.
- Ablauf: Launcher sichern -> `autoUpdates: true` -> Kanal `latest` -> `claude update`
  (~240 MB, im Hintergrund) -> **beide Schalter zurueck** auf `stable`/`false`.
- Erfolg belegen: `claude --version`, `claude doctor` (Version **und** `Commit:`
  gegen `manifest.json`), dann ein echter Lauf `claude -p "Antworte mit genau: OK"`.

## Fallen

- Die `.env` nutzt **CRLF**. Ein Suchmuster mit `\n` findet dort nichts ("Treffer: 0").
  Zeilenenden vorher byte-genau bestimmen (`raw.count(b"\r\n")` gegen `raw.count(b"\n")`),
  Ersetzung als Datei schreiben — ein Heredoc durch die Werkzeugschicht verstuemmelt die
  Backslash-Pfade. **Fertiges Werkzeug:** `scripts/zeile-ersetzen.py` ermittelt die
  Zeilenenden selbst, erzwingt genau einen Treffer und prueft die Laengenaenderung
  (Trockenlauf ohne `--tun`). Fuer jede Ein-Zeilen-Aenderung diesem Skript den Vorzug
  geben statt Handarbeit — die beiden Fallen oben sind sonst still.

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
