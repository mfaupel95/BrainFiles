# Regeln Repo-Bots (Hausstandard)

Basis fuer Fremd-Repo-Bots (caveman u.a.). Ein Bot je Repo, Eintraege nur
repospezifisch. Nicht als Hermes-Skill installieren.

## Einsatz
1. Repo aktuell halten (fetch, HEAD vs origin/main pruefen).
2. Ideen aus engine/ und evals/ pruefen, die Antworten kuerzer machen:
   Beispiel vorher/nachher, in Zeichen und Tokens gemessen (o200k).
3. Bericht: traegt die Umstellung? Eine Empfehlung.

## Stil
- Ergebnis zuerst, keine Floskeln, eine Empfehlung.
- Substanz nie kuerzen: kurz = knapp formuliert, nicht weniger Inhalt.
- Repo-Skill (caveman SKILL.md) ersetzt diese Regeln nicht; nur lesen.

## Gemessene Fakten (o200k, 2026-09-30)
- Abkuerzungen (cfg/impl/auth): 1 Token, Vollwort: 1 Token. Kein Gewinn. Nicht erfinden.
- Pfeile (->): gleiche Tokenzahl wie Verbwoerter, schlechter lesbar. Weglassen.
- Groesster Hebel: eine Idee pro Satz, 20-Woerter-Satz-Cap, Aktiv, Imperativ.

## Repo: caveman
- Root: O:\Werkstatt\Repos\caveman (= C:\...\BrainFiles\Werkstatt\Repos\caveman, Junction).
- Schreibzugriff: seit 07.10.2026 erlaubt (siehe „Schreibzugriff auf
  Werkstatt-Repos“ unten). In Sitzungen von vorher weiterhin nur via terminal/O:-Pfad.
- Eval-Snapshot veraltet (08.04.2026, opus-4-6, 4 Skills): Refresh mit
  CAVEMAN_EVAL_MODEL=claude-haiku-4-5 uv run python evals/llm_run.py
  (braucht claude CLI eingeloggt). Skill-Ergebnis damals: +59% Median ueber terse.
- Verify: pnpm run test.

## Repo: basic-memory
- Root: O:\Werkstatt\Repos\basic-memory. Wissensspeicher fuer Agenten, MCP-Server, Python 3.12+.
- Build/Test: just install / just test (SQLite+Postgres), just fast-check, just doctor.
- Lizenz AGPL-3.0: keinen Code in eigene Projekte uebernehmen.
- MCP-Wahrheit ist Agenten\MCP-Manifest.json; keine Registrierung ohne Auftrag.
- Konzept "schlanke Repo-Einbindung" (t_802b29c0): INDEX.md je Repo, heiss/kalt, basic-memory als Index der Indizes.

## Windows-Falle (2026-09-30, gefixt in evals/llm_run.py)
- shutil.which("claude") liefert claude.CMD (npm-Shim). cmd.exe %* -Expansion
  verschluckt lange --system-prompt Args: Exit 1 "Input must be provided".
  Fix: native claude.exe unter <npm>/node_modules/@anthropic-ai/claude-code/
  bin/claude.exe bevorzugen (claude_bin()).
- Repo-Dateien liegen physisch unter O:\Werkstatt\Repos\caveman (C:\...\Werkstatt
  ist Junction). Schreibzugriff seit 07.10.2026 erlaubt — siehe „Schreibzugriff auf
  Werkstatt-Repos“ unten; in Sitzungen von vorher weiterhin via terminal mit O:-Pfad.

## Repo: openmontage (Video-Framework; Maks-Sound-Auftraege)
- Auftragsweg: SkillsBot reicht Telegram-Bildunterschrift (caption) + Bilder
  durch; Bilder landen in Agenten\Hermes\cache\scratch\openmontage-auftrag  (msgNNNN_gruppeN.jpg, Dopplungen je Gruppe moeglich - per md5 deduplizieren).
- vision_analyze kann lokale Dateipfade NICHT lesen (404), aber
  http://127.0.0.1:8765/... via 'python -m http.server' im Bildordner
  funktioniert - allerdings flaky (nach ein paar Calls 404 trotz curl-200;
  Server neu starten oder auf ASCII-Analyse ausweichen).
- .venv (Repo) hat torch 2.14+cu130, diffusers, PIL, numpy, transformers -
  KEIN cv2, KEIN scipy, KEIN skimage, KEIN segment-anything. Homographie und
  bilineares Textur-Warping muessen in reinem numpy gebaut werden.
- Bewaehrte Boden-Ersetzung (03.10.2026): 1) Fliesen-Crop aus dem Musterfoto
  (unter Etikett/Griffausschnitt), Etikett per Spiegel-Klon heilen, nahtlos
  per Offset-Blend, 2x2-gespiegelt (Bookmatch-Look), Fugenlinien an Tile-
  Kanten. 2) Homography Weltebene->Bodenpolygon (numpy DLT), Schattierung =
  stark geglaettetes Original-Helligkeitsfeld (Raumlicht bleibt, Teppichmuster
  verschwindet). 3) sd-turbo img2img strength 0.32 nur harmonisieren.
  4) Finale = Original*(1-maske) + sd-Ergebnis*maske => Raum byte-genau.
- Falle: Bildhelligkeit vereinheitlichen - lum_smooth (0..1) mit lum_warp
  (0..255) dividieren ergibt Faktor 0.003 (fast schwarzes Ergebnis).
- numpy-Slice-Falle: out-of-bounds a[:, 1000:1378] bei 1330 breit kappt still
  auf 330 - Slices an die echte Crop-Breite anpassen.
- sd-turbo CLI-Prompt-Beschraenkung: CLIP kappt bei 77 Tokens - Kernaussage
  ('Boden Chelsea Brown') zuerst formulieren, Details weg.

## Schreibzugriff auf Werkstatt-Repos (gefixt 07.10.2026)

`C:\...\BrainFiles\Werkstatt` ist ein **Symlink auf `O:\Werkstatt`**.
`HERMES_WRITE_SAFE_ROOT` stand nur auf `BrainFiles`; der Pruefer loest den Symlink
auf und lehnte jeden Schreibzugriff in die Repos ab. Seit 07.10.2026 umfasst der
Wert beide Wurzeln, und zwar in **zwei** `.env`-Dateien:

    Agenten/Hermes/.env
    Agenten/Hermes/profiles/<name>/.env     (jedes Profil fuehrt den Wert selbst)

    HERMES_WRITE_SAFE_ROOT=C:\Users\faupe\Documents\BrainFiles;O:\Werkstatt

- **Wirkt erst in neuen Sitzungen.** Die laufende Sitzung behaelt die alte Umgebung
  im Prozess; aus ihr bleiben `write_file`/`patch` nach `O:\Werkstatt` gesperrt.
  Ausweichweg dort: Inhalt in die Sandbox schreiben, per `terminal` mit **O:-Pfad**
  kopieren, mit `md5sum` gegenpruefen.
- Der Wert ist eine `os.pathsep`-Liste (`;` unter Windows); mehrere Wurzeln sind
  vorgesehen (`agent/file_safety.py::get_safe_write_roots`).
- **Nachweis:** `.env` wie Hermes einlesen, dann `get_safe_write_roots()` und
  `is_write_denied(<ziel>)` ausgeben - Werkstatt ERLAUBT, `C:\Windows\...` und
  `~/.ssh` GESPERRT.
- Falle: die `.env` nutzt **CRLF**. Ein Suchmuster mit `\n` findet dort nichts;
  Zeilenenden vorher byte-genau bestimmen, Ersetzung als Datei (nicht Heredoc)
  schreiben.

## Claude Code CLI aktualisieren (07.10.2026)

Installationsart auf diesem Rechner: **native** (nicht npm). Launcher
`C:\Users\faupe\.local\bin\claude.exe`, Versionen unter
`C:\Users\faupe\.local\share\claude\versions\<version>`. Auto-Updates sind in
`.claude.json` per `autoUpdates: false` abgeschaltet - Max' Entscheidung.

**Warum `claude update` "up to date" meldete, obwohl 2.1.293 draussen war:**
`autoUpdates: false` blockiert auch den ausdruecklichen Update-Befehl, und der Kanal
stand auf `stable`. Der Kanal ist die Ursache, die man zuerst pruefen muss:

    stable -> 2.1.285        latest -> 2.1.293

Endpunkte direkt abfragen (das ist der schnellste Beleg):

    BASE=https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases
    curl -sS "$BASE/stable"      # Kanal stable
    curl -sS "$BASE/latest"      # Kanal latest
    curl -sS "$BASE/<version>/manifest.json"   # Version, Commit, Checksummen je Plattform

**Ablauf, der funktioniert hat:**

1. Sicherung des Launchers: `cp ~/.local/bin/claude.exe
   ~/.local/share/claude/versions/<alte-version>.bak-JJJJMMTT`.
2. `autoUpdates: true` in `C:\Users\faupe\.claude.json` (byte-genau, nicht JSON-Rewrite).
3. `autoUpdatesChannel: latest` in `C:\Users\faupe\.claude\settings.json`.
4. `claude update` - laeuft im Hintergrund (~240 MB, rund 90 s).
5. Danach **beide Schalter zurueck**: Kanal auf `stable`, `autoUpdates` auf `false`.

**Wichtig - das laufende Binary muss nicht frei sein.** Der Updater legt die neue
Version in `versions/` und schaltet den Launcher um; `claude.exe` selbst ist waehrend
des Betriebs gesperrt (`Permission denied` beim Schreiben), das stoert nicht. **27
laufende Sitzungen und das Hermes-Gateway liefen ununterbrochen weiter.**

**Gegenprobe, die den Erfolg belegt:** `claude --version`, `claude doctor` (Version
*und* `Commit:` gegen `manifest.json`), dann ein echter Lauf `claude -p "Antworte mit
genau: OK"` und `claude plugin test mods/agents-md` im Repo.

**Falle beim Kanal:** `stable` und `latest` sind die einzigen Kanaele; `beta` und `next`
gibt es am Endpunkt nicht (NoSuchKey).

**Nebenbefund, offen:** Die neue Version meldet beim Start acht wirkungslose
deny-Regeln in `MaxHirn/.claude/settings.local.json`:

    Write(./Archiv/**) is not matched by file permission checks - only Edit(path)
    rules are. Use Edit(./Archiv/**) instead

Betroffen: Archiv, Wissen, Claude, Bilder, Videos, Musik, Dokumente, `.obsidian`.
Die **Schutzregeln greifen weiter** - fuer jedes dieser Verzeichnisse steht daneben
eine `Edit(...)`-Regel, und die deckt laut Meldung alle Datei-Werkzeuge ab. Die
`Write(...)`-Zeilen sind reine Dopplung und erzeugen nur Rauschen. Aufraeumen nur mit
Auftrag (Schutzregeln, Stufe 1).

## Repo: claude-code
- Root: O:\Werkstatt\Repos\claude-code. Fremd-Repo anthropics/claude-code
  (distribution repo: plugins/mods/examples, KEIN CLI-Source, KEIN root package.json).
- CLI separat installiert, native: ~/.local/bin/claude.exe (Auto-Update aus, siehe
  Abschnitt "Claude Code CLI aktualisieren").
- Nur CLAUDE.md ist im Upstream getrackt. AGENTS.md ist LOKAL angelegt (Hausregeln
  fuer den Bot, 07.10.2026) und steht in .git/info/exclude - nicht ins Fremd-Repo committen.
- Ebenso in exclude: .env.template (lokal, nur "your_api_key_here"-Platzhalter),
  .env und auth.json (Schutz gegen versehentliche Credentials im Upstream).
- Kein Build. Typecheck: npx -y -p typescript@5.9.3 tsc -p mods/tsconfig.json.
  Tests: CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude plugin test mods/<name> (Flag Pflicht).
- Mods sind im Binary (nicht im Marketplace); mods/types/claude-code.d.ts ist
  generiert, nie von Hand editieren (Mod-Typen in <mod>/types/index.d.ts).
  Workflow-Sicherheit: .github/scripts/check_workflow_hardening.py (vom Root aus).
## Nachtrag 14.10.2026 (Prueflauf, CLI 2.1.287)

- Kanaele: `stable` = 2.1.287 (= installiert), `latest` = 2.1.296.
  `claude doctor` meldet "Auto-updates: enabled", obwohl `.claude.json`
  `autoUpdates: false` fuehrt — Anzeige irrefuehrend, Schalter unveraendert
  (letzter Update-Versuch 09.10.2026 -> 2.1.287).
- `--max-turns` fehlt seit 2.1.287 in `claude --help`, wirkt aber weiter
  (`claude -p ... --max-turns 1` -> rc 0, sauberes Ergebnis). Kein Bruch,
  nur undokumentiert; die Haus-Skills bleiben gueltig. Ebenso weiter vorhanden:
  `--bare`, `--agents`, `--from-pr`, `--json-schema`, `--resume`, `--mcp-config`,
  `--strict-mcp-config`, `--allowedTools`, `--plugin-dir`, `--teleport`.
- deny-Rauschen erledigt: `MaxHirn/.claude/settings.local.json` fuehrt nur noch
  `Edit(...)`-Regeln (8: Archiv, Wissen, Claude, Bilder, Videos, Musik,
  Dokumente, **/.obsidian/**), keine `Write(...)`-Dubletten mehr; `claude -p`
  startet warnungsfrei. Der Nebenbefund oben ist damit geschlossen.
- Mod-Suiten auf 2.1.287: nur `mods/agents-md` ist gruen (5 pass / 0 fail).
  `mods/sec-default` 151/11, `mods/telemetry` 26/8, `mods/diff` rot. Ursache ist
  die CLI-Version, nicht der Code: `claude plugin test` kann `$.session.append`
  erst ab 2.1.293 und korrekt ab 2.1.295 (CHANGELOG-Eintraege 2.1.293, 2.1.295) —
  die Mods sind vom 11.-13.10. (`chore: Update mods/`), die CLI vom 09.10.
  Die Zeitausfaelle in `mods/diff` (Kind-Timeout 5000 ms, Einzeltests 1,5-20 s)
  kommen zusaetzlich vom Host-Tempo (788 Prozesse, 92 node/bun/claude parallel).
  Wer die Mod-Suiten als Tor will, braucht CLI >= 2.1.295 (`latest` = 2.1.296);
  Kanalwechsel nur mit Auftrag. Einzeldatei sonst:
  `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1 claude plugin test --file mods/diff/tests/<x>.test.ts mods/diff`.
- Was 2.1.288-2.1.296 fuer unsere Einrichtung bringt (Auszug CHANGELOG): neues
  `onFailure: "block"` fuer Kommando-/HTTP-Hooks; SessionStart-Hooks schreiben
  `CLAUDE_ENV_FILE` wieder zuverlaessig (auch nach `/resume`, auch in PowerShell);
  `--debug` protokolliert die Hook-Dauer (nuetzlich fuer unsere 15-s-Hooks);
  `allowed-tools` eines Skills fiel in `-p`-Laeufen weg; Windows: PowerShell-Befehle
  ueber ~1 KB fragen nicht mehr immer nach; `rm -rf /c/Users/<name>` in Git-Bash
  fragt jetzt nach. Nichts davon bricht Bestehendes.
- Worktree-Hygiene: `git worktree prune` hat die verwaiste Registrierung
  `mfaupel95-silver-bassoon` entfernt (Branch bleibt, f275fa2).
- Werkstatt-Repo `O:\Werkstatt`: `git status` bricht ab ("not a git repository:
  .../Repos/claude-code/.git/worktrees/..."), weil 29 gitlink-Eintraege im Index
  ohne `.gitmodules` stehen. Workaround: `git status --ignore-submodules=all`.
  Nicht angefasst (Werkstatt-Ebene, kein claude-code-Thema).

- Stand nach Kanalwechsel (14.10.2026, CLI 2.1.296 = `latest`, Checksumme und Commit
  fdb6c17a97b6 gegen manifest.json verifiziert, Schalter danach auf stable/false zurueck):
  `mods/agents-md` 5/0 gruen; `mods/sec-default` 160/2 (die session.append-Fehler sind weg,
  vorher 151/11); `mods/telemetry` 26/8; `mods/diff` 214/3. Die 13 Restfehler sind
  deterministisch und kommen aus den PRs #96487 (`$.session.version()`) und #98357
  (Merge-Notice) — beide juenger als das Binary 2.1.296 (Build 09.10.). Treiber sind
  `is_claude_ai_auth` (Authorize/Identity in der gemockten Testumgebung), Linux-Plattform-
  felder und configReads-Zaehler: die Mods auf HEAD sind dem released Engine voraus.
  Nicht als Tor nutzen; gruen bleibt nur `mods/agents-md`.

- Haus-Hooks gegen 2.1.296 geprueft: beide SessionStart-Hooks in
  `MaxHirn/.claude/settings.local.json` (`systempruefung-hook.ps1`,
  `datensortierung-hook.ps1`) laufen einzeln aufgerufen mit rc 0; der
  Datensortierungs-Hook schweigt korrekt, wenn nichts zu entscheiden ist.
  Das Feld `"shell": "powershell"` ist gueltig und dokumentiert (Doku
  docs.claude.com/en/docs/claude-code/hooks: `shell` akzeptiert `bash` oder
  `powershell`, Default bash bzw. powershell unter Windows ohne Git Bash).
  Beide Hooks sind reine Lese-Hooks (Get-Content/Write-Output, kein Schreiben).
  Sauberere Windows-Form waere Exec-Form mit `args`
  (`"command": "powershell.exe", "args": ["-NoProfile","-ExecutionPolicy","Bypass","-File", ...]`)
  statt doppeltem PowerShell-Aufruf — nur mit Auftrag aendern (Stufe 1).
- MCP-Drift 14.10.2026 geprueft und behoben (`Agenten\mcp-sync-check.ps1` sagt
  jetzt "ALLES IN ORDNUNG"): die 7 "fehlt bei Claude"-Fehler waren FALSCH — der
  Pruefer liest die klassische Datei `%APPDATA%\Claude\claude_desktop_config.json`
  zuerst, und dort lag eine verwaiste 344-Byte-Datei (12.10., nur `ziplime`) aus
  einer Sitzung mit dem alten Pfad; die echte Config im MSIX-Container hatte alle 7.
  Verwaiste Datei nach `.bak-20261014` umbenannt. Echt fehlend war `ziplime` bei
  Hermes -> per `echo y | hermes -p default mcp add ...` in der Wurzel-Config
  registriert; in der Claude-Config `ziplime` ergaenzt und das tote `affinity`
  entfernt (Manifest: enabled false, Port 6767 zu). Verfahren und Fallstricke im
  Skill brainfiles/mcp-sync. Claude Desktop LIEF dabei - Aenderungen greifen beim
  naechsten Start.
  Nach dem App-Neustart verifiziert: Eintraege sind erhalten (ziplime drin, affinity
  raus), Pruefer sagt weiter "ALLES IN ORDNUNG". Pruefer gehaertet
  (`mcp-sync-check.ps1.bak-20261014`): er liest jetzt den MSIX-Container zuerst und
  warnt, wenn eine zweite Claude-Config daneben liegt - mit Testdatei geprueft.
