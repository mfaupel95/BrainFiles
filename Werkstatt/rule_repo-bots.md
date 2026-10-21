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

## Repo: everything-claude-code
- Root `O:\Werkstatt\everything-claude-code` (= `C:\...\Werkstatt\everything-claude-code`,
  Junction). Fremd-Repo WorldFlowAI/everything-claude-code, MIT, geclont 06.09.2026 —
  liegt **seit dem Klon direkt unter `Werkstatt/`**, nie unter `Werkstatt\Repos\`.
  Keine Sitzung irgendeines Profils hatte jemals `cwd` unter `Repos\everything-claude-code`.
  Remote heisst `upstream` (WorldFlowAI), **kein `origin`**: `git fetch origin` scheitert
  mit "does not appear to be a git repository". Eigener Fork existiert
  (`mfaupel95/everything-claude-code`, isFork, HEAD = `432485b`), ist aber nicht
  als Remote eingetragen.
- Stand 21.10.2026: `main` = `upstream/main` = `432485b`, ahead 0 / behind 0, Working Tree
  sauber (nur untracked `.env.template`), `git worktree list` = 1 Eintrag, nur Zweig `main`.
  `.git/info/exclude` fuehrt `.projectatlas/`. Kein Build; Typecheck bei Bedarf
  `npx -y -p typescript@5.9.3 tsc -p <mod>/tsconfig.json`.
- Bot-Startverzeichnis steht in der Profil-Config (`terminal.cwd`), nicht im Repo:
  `C:\Users\faupe\Documents\BrainFiles\Werkstatt\everything-claude-code`.
- **Werkstatt-Index-Drift (21.10.2026):** `O:\Werkstatt` (19 Commits) traegt noch
  `Repos/rule_repo-bots.md` (Blob `f76b55aa`, 147 Zeilen = Stand 14.10.) und
  `Repos/.vscode/settings.json` im Index; die Dateien liegen nicht mehr auf Platte, daher
  4 ` D`-Zeilen in `git status`. Die aktuelle Regeldatei (297 Zeilen, inkl. Nachtrag
  21.10.) steht **untracked** unter `O:\Werkstatt\rule_repo-bots.md`. Ein
  `git checkout -- .` in `O:\Werkstatt` holt die 14.10-Version zurueck, die juengeren
  Nachtraege bestehen nur als untracked Datei. Aufloesen (erst mit Auftrag, die Datei
  wird von mehreren Bots geschrieben): die 4 Loeschungen committen oder die Dateien
  zurueckholen, und die Wurzel-Regeldatei ins Repo aufnehmen.

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

## Repo: one-skill-to-rule-them-all (task-observer, Fremd-Repo rebelytics)

- Root `O:\Werkstatt\one-skill-to-rule-them-all` (Meta-Skill, CC BY 4.0). Remote
  heisst `upstream`, NICHT `origin` - `git fetch origin` scheitert mit "does not
  appear to be a git repository". Bot-Zweck: Beobachtungsverfahren (session-start-scan,
  skill-load, weekly-review, validator) lesen und gegen unsere Skill-Pflege vergleichen,
  Luecken benennen. Keine fremden Dateien hierher kopieren, nur Konzepte uebernehmen.
  README-Eintraege ("Recommended by", "Listed in") pflegt der Upstream-Autor - nichts nachziehen.
- Stand 18.10.2026 nach `git pull --ff-only` auf **3.7.0**, 68 Commits (HEAD `3463c7c`,
  ahead 0 / behind 0, Working Tree sauber). Davor lag es zwei Tage hinterher, weil der
  Gateway tot war (siehe unten) - die Routine meldete trotzdem "Upstream: keine neuen
  Commits". Eine solche Zeile ist nur gueltig, wenn sie gemessen wurde: `git fetch
  upstream` und danach `git rev-list --count HEAD..upstream/main` ausgeben, nicht aus
  dem Gedaechtnis.
- **Ceilings (seit 3.7.0) - das Konzept fuer unser Groessenlimit:**
  `references/ceilings.txt`, eine Zeile je Datei
  (`<file.md> <ceiling> [<JJJJ-MM-TT> <Grund der letzten Anhebung>]`), geprueft von
  `scripts/validate-skill-bundle.py`. Regeln: ueber dem Ceiling wird eine Datei mit
  >12 Load-Triggern nach Episode aufgeteilt, eine mit <=12 gekuerzt oder das Ceiling
  mit datiertem Grund angehoben; liegt ein Ceiling >3 Zeilen ueber der Dateizahl, wird
  es auf die Zahl gesenkt. **Das ist die Antwort auf "bei Ergaenzungen immer das
  Groesenlimit beachten": begruendete, datierte Anhebung statt stiller Kuerzung.**
- Guards in 3.6.0: "files present, 0 parsed = broken command" - der Scan schweigt
  nicht still, wenn er kaputt ist.
- Der Bot-Chat-Engpass ist der eigene Cron-Lauf `24aaa3aedd15` (30 9 * * *):
  seine Auslieferung ist ein kompletter Agenten-Turn im Bot-Chat, begrenzt durch
  `cron.bot_chat_delivery_timeout_seconds` (Default 600). Bei >600 s bricht sie ab,
  die Kurzmeldung landet in `cron/bot_chat_pending/`, der volle Bericht bleibt in
  `cron/output/<job>/` - `hermes cron runs` zeigt nur den Versuch, nicht das
  Ergebnis. Profil-Config auf 1200 gesetzt; `load_config()` cached pro
  Dateisignatur, ein Gateway-Neustart ist nicht noetig.
- Ursache 18.10.2026 (gefunden, nicht geraten): das Gateway lief vom 15.10. 15:09
  bis 18.10. 17:11 nicht (`logs/gateway-exit-diag.log`: exit_nonzero, danach kein
  Autostart). Die Aufgabe `\Hermes_Gateway_2ef9d0b7` hat nur einen
  Logon-Trigger. Der Rechner bootete 16.10. 01:07; ohne interaktiven Login blieben
  alle Cron-Jobs zwei Tage aus (catch_up, 201001 s spaet). Beim Nachfeuern liefen
  viele Jobs gleichzeitig an -> 429-Sturm bei stepfun/step-5-preview:free und
  Kontexte von 160-256k Tokens -> Bot-Chat-Turn ueber 600 s.
- Folgerung: nach einem Reboot ohne Login sind alle Cron-Jobs tot, bis der Gateway
  von Hand startet. Boot-Autostart ist der eigentliche Fix, das Timeout nur das
  Symptom.

## Nachtrag 21.10.2026 (basic-memory: Sitzungen stehen nicht im Worktree)

- `O:\Werkstatt\Reposasic-memory` existiert nicht mehr; `O:\Werkstatt\Repos` hat nur
  `puter`. Aktuell: `O:\Werkstattasic-memory`, Branch `sync/upstream-2026-10-19` @ `ad9158af`
  = `upstream/main` (ahead 0 / behind 0), Working Tree sauber (nur untracked `.env.template`).
  `git worktree list` = genau 1 Eintrag, keine verwaiste Registrierung.
- Sitzungen liegen **pro Profil** in `Agenten/Hermes/profiles/<name>/state.db`, nicht im
  Repo-Pfad. basic-memory: 30 Sitzungen / 612 Nachrichten. Ueber alle Profile gemessen
  (`cwd`/`git_repo_root` LIKE `%Repos%`, `%worktree%`): keine Sitzung mit dem alten Pfad -
  nach dem Umzug 14.10.2026 ist nichts verwaist, es gibt nichts zu migrieren.
- Vorheriger Diskussions-Thread (19.10., Raum `rmv8if5lm-yvl2g`) griff basic-memory ueber
  `20261019_004609_95cd14` und `20261019_161058_7f3c3d`; aktuell `local-f9d618...` (bot_room).
- Altbestand an `Repos/`-Sitzungen gibt es ausgerechnet bei den Repos, die vor dem Umzug
  dort lagen: fomo-radar (20+), caveman (2), moon-dev-agents (1). copilot-worktrees lagen
  unter `Werkstatt/copilot-worktrees` und wurden 07.10.2026 nach
  `Ausgemustert/copilot-worktrees-20261007/` verschoben.

## Nachtrag 21.10.2026 (gbrain: der alte Pfad ist eine tote Datei, nicht nur Metadatum)

- `O:\Werkstatt\Repos\{fomo-robinhood-radar,caveman,moon-dev-ai-agents,gbrain}`
  liegen **alle nicht mehr** - nur `puter/` ist noch da (aktiver Docker-Stack,
  T-404). Zielseite vorhanden: fomo `0304082` (main), caveman `2fd153c6` (main),
  moon-dev `e3199dd` (main), gbrain `d3cefb494` (master).
- **36 Sitzungen haben einen `cwd`, der auf der Platte fehlt** - gemessen ueber
  **Existenz** (`os.path.isdir(cwd)`) ueber alle 838 Sitzungen aller Profile, nicht
  ueber ein Suchmuster. Eine Muster-Suche (`LIKE '%Repos%'`) faengt nur 34 und
  verfehlt die beiden maxtrade-Sitzungen unter
  `C:\Users\faupe\Documents\GitHub\mfaupel95\.worktrees\maxtrade`.
  Aufschluesselung: fomo-radar 31, caveman 2, moon-dev-agents 1,
  awesome-systematic-trading 2. `--resume` auf so eine Sitzung scheitert am
  fehlenden Startordner. Ankniepfen heisst deshalb: **neue Sitzung am neuen Ort**,
  nicht alte fortsetzen.
- **Korrektur meiner ersten Zahl:** "nur 2 Dateien nennen `Werkstatt\Repos`" war
  ein Muster-Artefakt. Richtig: **4** - historisch Tageschronik 2026-10-14 und
  `Hardware.md`, aktiv-veraltet `Wissen/Schutzregeln.md` Z. 181 (dort steht ein
  Zugang zu `(`Repos/`)`, nicht zu `Werkstatt\Repos`, deshalb faengt das Muster
  nichts) und die offenen `Repos/`-Pfade in `Archiv/TASKS.md`. Z. 181 ist als
  T-440 erfasst.
- gbrain ist auf dieser Maschine **nicht installiert** (kein `~/.gbrain`, kein
  `gbrain`-Binary; bun liegt unter `Agenten/Hermes/tools/bun`). Wer die gbrain-Ebene
  als Abrufschicht will, braucht zuerst `gbrain init --pglite --no-embedding` -
  Migration ist nicht der erste Schritt, Installation ist es.

## Nachtrag 21.10.2026, Nachmittag (task-observer: zwei Deckel-Mechanismen, gemessen)

- Repo-Stand gemessen 21.10.2026 ca. 11:30: `main` = `upstream/main` = `3463c7c` (3.7.0),
  ahead 0 / behind 0, Working Tree sauber, `references/` 9 Dateien, `scripts/` 5.
- 3.7.0 hat ZWEI Deckel-Mechanismen, beide in `scripts/validate-skill-bundle.py` geprueft:
  1. **Core-Ratsche** — `core_max_lines:` in der SKILL.md-Frontmatter oder `.core-ceiling`
     daneben. Laeuft in BEIDE Richtungen: ueber dem Ceiling = FAIL ("Move content to a
     reference file — do not raise the ceiling"); Slack > 3 Zeilen = auch FAIL ("lower it
     to the current count in this commit — a trim is locked in, not left as headroom").
     Dazu `TARGET_CORE_LINES = 500` als Zielmarke, nicht als Tor.
  2. **Referenz-Deckel** — `references/ceilings.txt`, eine Zeile je Datei
     (`<file.md> <ceiling> [<JJJJ-MM-TT> <Grund der letzten Anhebung>]`); liegt ein Ceiling
     >3 Zeilen ueber der Dateizahl, wird es auf die Zahl gesenkt.
- Unser Gegenstueck, gemessen: `MAX_SKILL_CONTENT_CHARS` = 100.000 Zeichen je SKILL.md und
  `MAX_SKILL_FILE_BYTES` = 1 MiB (Beleg `hermes-agent/tests/tools/test_skill_size_limits.py`).
  Ein globales, eine-Richtung-Tor ohne Datum, ohne Granularitaet je Referenzdatei, ohne
  Ratsche nach unten. Die Hausregel "Groesenlimit beachten" ist bei uns also nicht
  operationalisiert.
- **Die groesste Datei gehoert uns nicht:** `profiles/one-skill-to-rule-them-all/skills/
  research/research-paper-writing/SKILL.md` = 1627 Zeilen / 72 KB = 72% des Caps, dazu 10
  Referenzdateien. `author: Orchestra Research`, MIT, `version: 1.1.0` → fremd-maintained
  (Kategorie (b)): nie in place editieren, auch kein ceilings-Entwurf fuer fremde Dateien.
- **Konkreteste Luecke, gemessen am Skill-Prompt:** 20 `.sicherung-junctions/`-Kopien
  (`skills/<kat>/.sicherung-junctions/<skill>/SKILL.md`), 194,5 KB zusammen, stehen als
  EINTRAEGE im Prompt: 62 Eintraege, davon 20 (32%) Kopien = 9.336 Zeichen = 35% der
  Snapshot-Laenge. 19 tragen DEN SELBEN `skill_name` wie ihr Live-Zwilling (z.B. `claude-code`),
  und jede Kopie driftet (`claude-code` 756 Zeilen live vs. 754 in der Kopie). `chat` existiert
  zweimal (`chat/` und `.sicherung-junctions/chat/`) — deshalb kann `skill_view('chat')` nicht
  laden (doppelter Name UND Pfad, der System-Prompt warnt selbst). Folge: der Router sieht pro
  Skill zwei Eintraege mit gleichem Namen und gleicher Beschreibung, und die Kopie ist die
  aeltere Version, in der ein Fix am Live-Skill fehlt.
- **Curator vs. Beobachtungs-Review:** `hermes curator status` = ENABLED, 11 Laeufe, letzter
  21.10. 02:34, "auto: no changes; llm: skipped (consolidation off)", Intervall 7 Tage,
  stale nach 14 Tagen, archive nach 30 Tagen. Verwaltet 2 Skills (0 aktiv / 1 stale /
  1 archived); **20 unmanaged Skills ohne Provenance-Marker werden nie automatisch gestalet.**
  Der Curator beantwortet "welcher Skill ist ungenutzt", nicht "welche Beobachtung verdient
  welche Aenderung": es gibt keine nummerierte Beobachtungsqueue, keinen Status, kein
  `last-review-date.txt`. Die 3.7.0-Lektion "ein Scheduler-'succeeded' beweist nur, dass der
  Lauf startete" traegt direkt auf uns zu.
- **Auslieferung des Bot-Jobs:** Lauf 24aaa3aedd15 scheiterte 21.10. 11:05 mit "Provider has
  been unresponsive (no response received) for 5 consecutive stale attempts" — Provider-Stall,
  kein Repo-Defekt. `hermes cron list` zeigte danach "Execution: running" UND "Delivery still
  in progress ... bot-chat:(own) queued" (delivery_id `80bec740…`): der Job meldete FAILED,
  waehrend seine Auslieferung in `cron/bot_chat_pending/` lag. Nichts vergleicht gestartete mit
  bestaetigten Auslieferungen — dasselbe "staged vs. presented"-Gap wie in 3.7.0. Von Hand
  erneut gestartet lief derselbe Job durch (4m 28s, 64 Nachrichten, resumed
  `20261015_093103_e86ef0`).

## Repo: Harvard-Algorithmic-Trading-with-AI (moondevonyt, Lehrmaterial RBI)
- Root `C:\...\BrainFiles\Werkstatt\Harvard-Algorithmic-Trading-with-AI` (= Junction auf
  O:\Werkstatt). `origin` = mfaupel95-Fork, `upstream` = moondevonyt. Stand 21.10.2026:
  main = origin/main = upstream/main = 092560e, 0/0.
- **Beide Beispielskripte waren wie eingecheckt nicht lauffaehig** (gefixt am 21.10.2026):
  `data_path` war der harte macOS-Pfad `/Users/md/Dropbox/...` -> FileNotFoundError. Zusaetzlich
  benannte `template.py` Zeile 32 die 5 verbleibenden Spalten (index_col='datetime' loescht die
  erste) auf 6 Namen inkl. `Unnamed: 6` -> ValueError. `bb_squeeze_adx.py` Zeile 81 (5 Namen)
  war korrekt. **Kontrollfall:** die Zeile faengt den Fehler nicht, wenn man sie nur liest -
  die Spaltenzahl nach `index_col` muss gegengeprueft werden.
- **Seit 21.10.2026 tragen beide Skripte ein Kostenmodell** (`KOMMISSION_JE_SEITE = 0.002`,
  `SPREAD = 0.0005`, Ausweis ueber `kostenkopf()`: Kosten je Runde, Anzahl Runden, netto je Runde),
  rechnen Suchfenster/Prueffenster getrennt und setzen die gefundene Kombination auf dem
  Prueffenster. Dazu `backtest/KOSTEN.md` (Messwerte, Break-even, Ausreisser-Suche) und
  `backtest/tests/test_beispiele.py` (Standardbibliothek, `python -m unittest discover -s tests`).
- **Meine erste Falschangabe, korrigiert:** ich hatte in der Regeln notiert, `bb_squeeze_adx.py`
  benenne 6 Spalten auf 5 um (ValueError). Falsch - nur `template.py` hatte die falsche Zahl.
- `backtest/data/BTC-6h-1000wks-data.csv`: **12.903 Kerzen**, 2015-07-20 bis 2024-05-19,
  Kopfzeile `datetime,open,high,low,close,volume` (6 Spalten, KEINE `Unnamed: 6`;
  nach `index_col='datetime'` bleiben 5 Spalten, deshalb war die 6-Namen-Umbenennung in
  template.py der Fehler).
- **Kostensweep gegen die ECHTE Strategieklasse `BBSqueezeADX`** (217 Runden, Kommission je
  Seite): 0,0000 +82,22 % (0,379 %/Runde) · 0,0002 +74,58 % · 0,0010 +19,20 % · 0,0016
  +0,68 % · 0,0018 −4,41 % · **0,0020 −18,68 % (−0,086 %/Runde)** ·
  0,0040 −52,77 %. Break-even ~0,0016 je Seite = 0,32 % je Runde. Das hardcodierte
  `commission=0.002` kehrt das Vorzeichen um. `spread` (backtesting 0.6.6 kennt `spread`,
  NICHT `slippage`) ist im Skript nie gesetzt; mit spread=0,0005 wird 0,0020 zu −29,98 %.
- **`bt.optimize(maximize='Equity Final [$]')` ist eine Ausreisser-Suche, kein Beweis.**
  Gemessen am Gitter DER DATEI (160 Kombinationen, Kosten 0,5 % je Runde, 40er-Stichprobe):
  Mittel **−52,44 %**, sigma **15,67 %**, Minimum −76,67 %, Maximum −24,62 %, **0 von 40
  positiv** nach Kosten, Median 377 Runden. Der echte Optimierer-Fund des 160er-Gitters:
  **−6,34 %** bei 379 Runden — 2,9 sigma ueber dem Stichprobenmittel, also genau das Bild
  eines Maximums aus 160 Ziehungen. Geteilt: +2,29 % Suchfenster / −6,37 % Prueffenster.
  Korrelation Return H1 (2015-2019) gegen H2 (2020-2024) ueber 40 Kombinationen: **+0,173**
  — bei n=40 nicht von null zu unterscheiden (5-%-Grenze ~0,31), also keine tragfaehige
  Basis fuer einen Parameter. template.py sucht 1440 Kombinationen: bester Fund
  +175,36 % Suchfenster / −28,87 % Prueffenster.
- **KORREKTUR meiner ersten Falschangabe:** ich hatte 320 Kombinationen und Korrelation
  −0,197 gemeldet. Beides kam aus einem Gitter, das ich selbst gebaut hatte (ich hatte
  bb_window=15 mitgenommen, das die Datei nie sucht). Richtig ist das Gitter der Datei:
  160, und die Korrelation ist +0,173 (nicht signifikant).
- Werkzeug dafuer: `uv venv --python 3.14` in den Scratch, `uv pip install pandas numpy TA-Lib
  backtesting` (PyPI-Name `backtesting`, nicht `backtesting.py`). `exec` von Zeilen 1-7 + 11-78
  von bb_squeeze_adx.py liefert die echte Strategieklasse ohne den kaputten Datenladeteil;
  Parameter wie `optimize` setzen via `setattr(Klasse, k, v)` - `Backtest(**params)` wirft
  TypeError.
- `implement/bot.py` ist ccxt/Hyperliquid, modeliert ebenfalls keine Kosten. Kein Order-Pfad
  im Repo, nichts davon ist Spur-Arbeit.

## Repo: OpenTerminal

- Root `BrainFiles\Werkstatt\OpenTerminal` (liegt direkt unter `Werkstatt`, KEIN Junction).
  Fremd-Repo ErTasselli/OpenTerminal, MIT, Next.js 15 + Express + TypeScript, Workspaces
  `server/` + `web/`.
- **Start: `npm install` dann `npm run dev`** (concurrently: api + web). Ports: **Web 3000**,
  **API 4000** (`API_PORT`, bindet Default `127.0.0.1`, CORS nur `http://localhost:3000`).
  20128 (OmniRoute) und 8787 (Bus) sind fremd - nie belegen. Nichts doppelt starten.
- Reine Anzeige, kein Orderpfad, keine Schluessel: `server/src/routes/market.ts` proxyt nur
  freie Quellen (Yahoo/Nasdaq/Stooq/Binance/CoinGecko/FRED/SEC/FINRA/EconCalendar),
  `marketRouter` OHNE API-Key, 240 req/min je IP. `/api/portfolios` und `/api/ai` brauchen
  den Key aus `data/.api-key`. Im Repo liegt nur `.env.template`.
- **Marktbreite/Makro kostenlos fuer Regime-Merkmale** (keyless, mit Fallback-Kette):
  `/api/crypto/global` (CoinGecko total market cap + BTC/ETH-Dominanz, Cache 120 s,
  Fallback Binance), `/api/macro` (Renditekurve, VIX, Index-/Rohstoff-Proxies),
  `/api/screener` (gesamter US-Aktienmarkt), `/api/crypto` (Top 50).
- **Regime-Fenster gehoeren NICHT in dieses Repo:** die Fenster liefert
  `Agenten/Handel/gitter/regime_gitter.py` (Defaults `--fenster 8 --schritt 1` = 8 Wochen
  Fenster, 1 Woche Schritt, also 7/8 Ueberlappung), Daten
  `Agenten/Handel/kerzen_BTC-USDT_1H_8760.json` = 8760 h = 52,1 Wochen -> **45 Fenster,
  nicht 12**. Live-Spur `gitter/handeln.py` = 1h-Leiter, 300 Kerzen,
  `handel_erlaubt=false`; `dauerlauf.py` kennt kein Messfenster (nur das Freigabefenster).
  Die Fensterzahl waechst deshalb von selbst NICHT - die Historie-Datei ist statisch.

## Nachtrag 21.10.2026, Abend (Codex-CLI / ChatGPT-Desktop / claude-unlimited, gemessen)

- **claude-unlimited kann den Codex-CLI NICHT bedienen.** Der Pool (127.0.0.1:4317)
  spricht ausschliesslich Anthropic Messages: `gateway.py` "Only /v1/messages is bridged
  for real", README "Anything that speaks the Anthropic Messages API". Der Codex-CLI
  spricht OpenAI Responses - Wire-Format passt nicht, "claude-unlimited auf codex cli"
  ist deshalb nicht umsetzbar. Umgekehrt funktioniert es: Claude Code nutzt die
  ChatGPT/Codex-Accounts. Installiert ist 1.2.7 (`AppData\Roaming\Python\Python314\
  site-packages\claude_unlimited`), `cu doctor` = READY, `/v1/models` = 200, Pool:
  1x Claude-Pro-OAuth (`faupel3107@googlemail.com`) + 2x codex (`free`, `go`).
- **Claude Desktop ist auf den Pool geschaltet** (3p-Profil `Claude-3p`, `appliedId` =
  "Claude Unlimited", `inferenceGatewayBaseUrl` = `http://127.0.0.1:4317`). Rueckgaengig
  mit `claude-unlimited desktop --revert`. Claude-Code-CLI selbst ist NICHT geroutet
  (`~/.claude/settings.json` hat kein `env`); pro Sitzung geht es ueber `cu code`.
- **Codex-CLI und die ChatGPT-Desktop-App teilen `~/.codex/config.toml`.** `model` und
  `model_provider` daraus sind der Default fuer NEUE Threads der Desktop-App; die
  Desktop-App bietet zusaetzlich alle `[model_providers.*]` im Modell-Picker an.
  Stand 21.10.2026: `model_provider = "omniroute"`, `model = "auto/best-free"`.
  **Zurueckgesetzt** auf `model = "gpt-5.6-terra"`, kein `model_provider` (Backup
  `~/.codex/config.toml.bak-20261021-201915`, TOML geparst). OmniRoute bleibt als
  `[model_providers.omniroute]` im File und ist weiter waehlbar:
  `codex exec -c model_provider="omniroute" -c model="auto/best-free"`.
- **`gpt-6-sol` wird vom Codex-CLI mit ChatGPT-Konto abgelehnt** - HTTP 400 "The
  'gpt-6-sol' model is not supported when using Codex with a ChatGPT account." Es steht
  im Desktop-Picker (`composer-recent-model-configurations-v1`), im CLI nicht. Ohne
  `model`-Zeile nimmt der CLI `gpt-5.6-terra` (`provider: openai`) - mit echtem
  `codex exec` verifiziert (Antwort "OK").
- **OmniRoute `auto/best-free` ist 21.10.2026 gerade degraded** ("No target in combo
  auto/best-free supports tool calling", `poolSize: 0`) - Config daran unschuldig.
- Die Desktop-App liest `config.toml` beim Start; ein App-Neustart wirkt die Aenderung
  aus. Vor jeder Aenderung an `~/.codex/config.toml`: Sicherung `.bak-<JJJJMMDD-HHMMSS>`,
  danach TOML parsen und ein echter `codex exec` als Nachweis.
