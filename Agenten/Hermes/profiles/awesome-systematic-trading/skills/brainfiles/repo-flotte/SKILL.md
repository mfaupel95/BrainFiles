---
name: repo-flotte
description: "Use when Repos wiederherstellen, Bots je Repo, Telegram."
category: brainfiles
---

# Repo-Flotte: Fremd-Repos einrichten und je Repo ein Bot

Fuer Arbeiten am Bestand aus Fremd-Repos: geloeschte Repos wieder auf den Account
bringen, lokal als arbeitsfaehige Klone einrichten und je Repo einen Hermes-Bot
(Profil) als Betreuer anlegen. Laeuft auf dem Host ueber `windows-mcp`; `gh` ist
dort angemeldet.

## Ablauf

1. **Soll-Liste gegen die Wirklichkeit halten.** Namen aus einem Screenshot, einer
   Notiz oder dem Gedaechtnis sind eine **Hypothese**. Je Name belegen: das
   Upstream-Repo existiert (`gh api repos/<owner>/<repo>`), oder der lokale Klon
   nennt ihn selbst (`Get-Content <dir>\.git\config` → `url =`). Ein Name, der
   nirgends aufloest, wird berichtet - nicht erfunden und nicht stillschweigend
   weggelassen. Loest ein Name auf **mehrere** Repos auf (z. B. „Open Terminal“
   = Trading-Dashboard und AI-Tool zugleich), erst nachfragen, welches gemeint
   ist: Kandidaten mit Sternen/Beschreibung nennen, eine Empfehlung voranstellen.
   Der Fork ist oeffentlich; das falsche Repo zu forken kostet Aufraeumen.
   *Fertig, wenn* jeder Name eine belegte Quelle hat.
   - Der Bild-Backend holt keinen Dateipfad; liegt ein Screenshot nur als Datei
     vor, den Text lokal auslesen: `tesseract` (bei Bedarf
     `apt-get install -y --no-install-recommends tesseract-ocr`), Bild vorher mit
     ImageMagick auf 300-500 % vergroessern, `--psm 6` und `--psm 11`
     gegeneinander halten. Die so gewonnenen Namen bleiben Hypothese (Schritt 1).
2. **Wiederherstellen als Fork des Originals.** Fuer oeffentliche Upstreams ist
   Re-Fork verlustfrei, solange im geloeschten Repo keine eigene Arbeit lag - das
   prueft man an den lokalen Klonen: zeigen deren `origin`-URLs auf die Upstreams,
   gab es kein Unikat. `gh api -X POST "repos/<upstream>/forks"`. Forks entstehen
   asynchron: in einer Schleife `gh api "repos/<konto>/<name>"` abfragen, bis der
   Name aufloest. Oeffentliche Upstreams ergeben oeffentliche Forks - private
   Forks von oeffentlichen Repos sind ohne Freigabe des Upstreams nicht moeglich.
3. **Bestand zaehlen, nicht Einzeltreffer feiern.** `gh api
   'user/repos?per_page=100&affiliation=owner' --jq '[.[] | select(.fork==true)
   | .full_name] | sort'` zaehlt **alle** Forks des Kontos, also auch die schon
   vorhandenen. Die Zahl gegen Erwartung **plus** Altbestand halten.
4. **Lokal arbeitsfaehig machen.** Ein Verzeichnis je Repo unter
   `Werkstatt/` (Fremd-Repos sind Durchgangsware, nie im Vault):
   `git clone --quiet --depth 1 https://github.com/<konto>/<name>.git <dir>`,
   danach `git -C <dir> remote add upstream https://github.com/<upstream>.git`.
   Shallow genuegt fuer Bot-Arbeitsplaetze; `git fetch --unshallow` holt die volle
   Historie nach. Liegt am Zielort schon ein Verzeichnis ohne `.git` (eine
   entpackte Kopie), es nach `<name>.vorher` verschieben statt hineinzuklonen.
5. **Ein Bot je Repo.** Bots sind Hermes-Profile:
   `hermes.exe profile create <name> --clone --description "<Rolle, 1-2 Saetze>"`
   und danach `hermes.exe -p <name> config set terminal.cwd <repo-pfad>`. `--clone`
   uebernimmt Modell, Werkzeuge und Skills des Startprofils, `--description`
   landet in `profile.yaml` und wird vom Kanban-Orchestrator zum Sortieren benutzt.
   *Fertig, wenn* `hermes profile list` jeden Bot fuehrt.
6. **Zaehlen, welche Bots fehlen, gegen die Platte:** `ls Werkstatt/` gegen
   `ls Agenten/Hermes/profiles/` halten — ein Ordner in profiles/ mit config.yaml
   ist ein Bot. Ein Verzeichnis unter Repos/ OHNE `.git` (z. B. eine
   Worktree-Sammlung) ist keine Repo und bekommt keinen Bot. Die Zaehlung als
   dauerhafte Notiz ablegen (z. B. Wissen/Repo-Bots.md), mit dem Hinweis, dass
   die Platte die Wahrheit bleibt und die Notiz altert.
7. **Bots in Telegram anbinden (SkillsBot).** `Agenten/Bus/skillsbot.py` um
   zwei Befehle erweitern: `/bots` liest die Profile von der Platte
   (`profiles/<name>/config.yaml`), `/bot NAME NACHRICHT` startet einen
   frischen Einzelauftrag `hermes.exe -p NAME chat -q "TEXT" -Q` per
   `subprocess.run` (kein Gateway, kein A2A-Kontext; der Bot antwortet aus
   seinem eigenen Verlauf). Regeln, die sich bewaehrt haben:
   - Name gegen die Platte validieren - unbekannter Name und fehlende Nachricht
     enden OHNE Aufruf mit Syntax-Hinweis, sonst startet ein geratener Bot.
   - PYTHONHOME/PYTHONPATH aus der Umgebung entfernen und HERMES_HOME setzen,
     bevor hermes.exe startet (Falle aus MCP-Brueckensitzungen, siehe unten).
   - Kaltstart 30-60 s: vorher eine Zwischenmeldung senden („Spreche mit Bot X
     - das kann bis 5 min dauern"), sonst wirkt der Bot haengend.
   - `session_id:`-Zeile aus der Ausgabe entfernen - der Rest ist die Antwort;
     Fehlercode mit dem letzten stderr-Ausschnitt melden.
   - Beide Befehle in `hilfe_text()` aufnehmen.
   - Tests in `Agenten/Bus/tests/test_skillsbot_sicherheit.py`: `subprocess.run`
     mocken, NIE einen echten hermes.exe starten (Kaltstart 30-60 s schreibt
     echte Sessions). Pruefen: unbekannter Name -> kein Aufruf, fehlender Text,
     Subprozess-Form (-p NAME, -q TEXT), Umgebungsbereinigung.
   - SkillsBot-Task neu starten (`Stop-ScheduledTask`/`Start-ScheduledTask
     -TaskName 'BrainFiles-SkillsBot'`); ein neuer Befehl gilt erst danach.

## Steuerung: eine Regeldatei, individuelle SOUL.md

Ein Bot je Repo ist erst brauchbar, wenn er weiss, WAS er betreut. Zwei Ebenen,
sonst wird es Tokenlast:

- **Eine gemeinsame Regeldatei eine Ebene hoeher:**
  `Agenten/Hermes/profiles/rule_<name>.md` (Stil, Betriebsregeln, Gelerntes,
  eigenes Zeichen-Budget mit Messbefehl). Sie liegt ABSICHTLICH ueber den
  Profilordnern, damit N Bots EINE Quelle teilen.
- **Je Bot eine eigene `SOUL.md`** mit dem, was ihn unterscheidet: Repo-Pfad,
  was das Repo ist, Aufbau, Aufgaben, Grenzen — plus genau ein Verweis auf die
  Regeldatei. N wortgleiche `SOUL.md` sind reine Tokenlast und verdecken den
  Unterschied zwischen den Bots.
- **Den Repo-Inhalt wirklich lesen**, statt aus dem Profilnamen zu raten:
  README-Kopf, Top-Level-Ordner, vorhandene `.venv`, Fork/Upstream. Die
  Beschreibung in `profile.yaml` ist nur ein Anhaltspunkt (mehrere Bots tragen
  dort denselben Platzhalter „Moon-Dev-Repo-Bot: betreut Werkstatt/<repo>").
- **Die Zahl der Bots aus der Platte zaehlen**, nicht aus einer Notiz uebernehmen
  (`Get-ChildItem profiles/ -Directory` ohne Sonderprofil und ohne das eigene
  Profil) — eine Vorgabe „26" war real 27.
- **Die alte, wortgleiche Fassung sichern**, bevor N Dateien ersetzt werden:
  bei N identischen Dateien genuegt EINE Kopie plus ihr Hash als Beleg der
  Gleichheit (`profiles/.sicherung/SOUL-generisch-<JJJJMMTT>.md`).
- **Beleg ohne Modelllauf:** `profiles/<bot>/state.db`, Tabellen
  `sessions.system_prompt_hash` -> `system_prompts.hash`; der Prompt enthaelt die
  individuelle SOUL-Zeile und den Verweis, `--ignore-rules` laesst beides weg.
  Verfahren und Git-Freigabe: `hermes-config-ops`, Abschnitt „Viele gleichartige
  Profile, EINE Quelle".

## Nachweis

- `gh api "repos/<konto>/<name>" --jq '.full_name + " fork=" + (.fork|tostring)'`
  je Repo.
- `git -C <dir> remote -v` je Klon: `origin` = Fork, `upstream` = Original.
- `hermes profile list` fuehrt jeden Bot, `hermes profile describe <bot>` zeigt
  die gesetzte Rolle.
- `python tests/test_ende_zu_ende.py` aus `Agenten/Bus` endet mit
  „Ende-zu-Ende bestanden".
- `/bots` im SkillsBot zeigt jeden Bot mit Rolle; `/bot NAME PONG` einmal echt
  laufen lassen (Kaltstart 30-60 s) - die Antwort ist der Beleg.

## Fallen

- **Namen aus einem Screenshot sind oft falsch geschrieben - Konto und Repo GETRENNT pruefen.** Ein 404 von `gh api repos/<owner>/<repo>` heisst nur, dass DIESES Repo so nicht heisst; `gh api users/<owner>` klaert, ob das Konto existiert (Schreibweise!). Oft existiert das Konto und nur das Repo fehlt - umgekehrt wird sonst die ganze Flotte verworfen.
- **Ein 404 auf das erwartete Repo heisst nicht „geloescht".** Kanal-, Playlist- und Spiegel-Beschreibungen nennen den aktuellen Namen; ein Fork traegt das Original in `.parent.full_name` und `.source.full_name`. Bleibt das Original verschwunden ODER ist es privat (beides ergibt denselben 404), ist ein Nachbau die Quelle - dann im Klon und in der Doku ausdruecklich als Nachbau kennzeichnen, nie als Original ausgeben.
- **Fremd-Repo mit eigenem CLI: dessen eigenen Zustandsbefehl nutzen.** `<tool> doctor` (bzw. `install`) sagt, welche Kanaele/Abhaengigkeiten fehlen - das ist die Lage, die man sonst raten muesste. `skill --install` o.ae. NICHT aufrufen: das schreibt eine fremde SKILL.md in Agenten-Skill-Verzeichnisse und verstoesst gegen `skill-library-sync`. Statt dessen eine eigene, kurze Hausfassung schreiben (was es ist, wo es liegt, wie man es aufruft, was noch fehlt).
- **Ein Kanal ist erst fertig, wenn sein Backend auf dem PATH liegt — nicht in
  der Repo-venv.** Ein `pip install` in die venv laesst den `doctor` weiter
  „nicht installiert“ melden: er sucht den Befehl (`shutil.which`). Richtig ist
  die Installation in ein Verzeichnis, das schon im Benutzer-PATH steht
  (`uv tool install <paket>` → `~/.local/bin`) — den PATH umzuschreiben ist der
  schlechtere Weg. Nachmessen mit `Get-Command <befehl>`.
- **Zusatzkonfiguration gehoert zum Kanal, und das Tool nennt sie selbst.**
  Fehlt sie, meldet der Kanal nicht „nein“, sondern „installiert, aber nicht
  einsatzbereit“ (Beispiele: eine Config-Datei, die die JS-Laufzeit freischaltet;
  ein laufender Daemon PLUS verbundene Browser-Extension fuer Seiten mit
  Anmeldung). Die Meldung wortwoertlich lesen und den genannten Befehl
  ausfuehren — nichts selbst erfinden, und einen Kanal, der eine Extension im
  persoenlichen Browser braucht, als offenen Handgriff des Nutzers melden, nicht
  stillschweigend installieren.
- **Ein Repo ohne Software ist trotzdem integriert.** „Contains no software“, nur
  Dokumentation und Schemata: Fork, Klon und Bot laufen wie sonst, es gibt nur
  nichts zu bauen. Der Nutzen ist das Referenzmaterial — z. B. ein mitgeliefertes
  GraphQL-Schema, aus dem die Feldnamen kommen.
- **Ein Fremd-Repo ist erst fertig eingerichtet, wenn der Capability-Check des
  Repos selbst gruen ist — nicht wenn `pip`/`npm install` durchlief.** Ein
  Registry-/Doctor-Mechanismus im Repo prueft haeufig `shutil.which(<befehl>)`
  oder eine Config-Datei, nicht das Vorhandensein des Python-Pakets in der
  Repo-`.venv`. Nach jeder Installation den mitgelieferten Status-Aufruf
  laufen lassen (Registry-Dump, `<tool> doctor`) und JEDE neu verfuegbare
  Faehigkeit einzeln zaehlen (vorher/nachher), statt aus einem fehlerfreien
  `pip install` auf Einsatzbereitschaft zu schliessen. Schwere optionale
  Zusatzpakete (torch, whisper, GPU-Bildmodelle) nicht blind mitziehen — nur
  installieren, was auf der vorhandenen Hardware sinnvoll laeuft, und die
  ausgelassenen Faehigkeiten im Bericht namentlich nennen statt sie
  stillschweigend wegzulassen.
- **Ein Fremd-LLM-Agent hat oft ein hart codiertes Standardmodell, das lokal
  gar nicht existiert** (z. B. ein Cloud-Modellname als Default, obwohl das
  Repo auch einen lokalen Ollama-Pfad kennt). Vor dem ersten echten Lauf im
  Modell-Auswahlcode nach dem Default suchen und ihn auf ein tatsaechlich
  installiertes lokales Modell umstellen (per Registry-Eintrag oder Fallback-
  Kette, nicht durch Herunterladen des erwarteten Modells) — sonst laeuft
  jeder Aufruf sofort in einen Modellfehler, ohne dass der Rest der
  Integration das zeigt.
- **Fremd-Repo unter `Werkstatt/` liegt per Junction auf einem anderen Laufwerk.** Seine `.venv` belegt daher keinen Platz auf `C:` - die Meldung „Actual location" der venv lesen, bevor man Plattenplatz zurechnet. Und die venv heisst `.venv` (Hausstandard), auch wenn die Anleitung des Repos `venv` sagt.
- **`hermes.exe` aus einer MCP-Brueckensitzung** braucht davor
  `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH` und ein gesetztes
  `$env:HERMES_HOME`, sonst bricht es mit einem falschen „corrupt
  Python"-Fehler ab; Einzelheiten in `hermes-maintenance`.
- **Profilnamen werden klein geschrieben.** `profile create Scrapling` legt
  `scrapling` an; danach nur noch den kleinen Namen verwenden. Ein erneuter
  `create`-Aufruf auf ein vorhandenes Profil meldet einen Fehler, aendert aber
  nichts - Beschreibung und `terminal.cwd` gehoeren in eigene Aufrufe, dann laeuft
  der ganze Satz idempotent.
- **Je Profil sind nur benannte Dateien versioniert.** Die `.gitignore`-Whitelist
  gibt je `profiles/<name>/` `SOUL.md`, `config.yaml`, `profile.yaml` und
  `rule_maXtrade.md` frei; eine GEMEINSAME Regeldatei direkt in `profiles/`
  braucht ihr eigenes Muster `!Agenten/Hermes/profiles/*.md` (die
  Verzeichnis-Freigaben decken sie nicht ab). state.db, sessions, credentials
  bleiben unversioniert, wie gewollt. Nach dem Anlegen wirkt der ganze
  Ordnername als `??`; `git add` des Ordners nimmt trotzdem nur die
  freigegebenen Dateien auf (Vorabkontrolle mit `git add --dry-run
  <profilordner>`), die Gegenprobe fuer die Regeldatei ist
  `git check-ignore -v <pfad>` (die `!`-Zeile ist der Beleg). Steht etwas
  anderes im Dry-Run, ist die Whitelist falsch — nicht stumm aufraeumen,
  sondern die Freigabe pruefen.
- **`--clone` kopiert die ganze Skill-Bibliothek ins Profil.** Bei vielen Bots
  kostet das Plattenplatz und, sobald der Bot laeuft, die gleichen Tokens wie das
  Startprofil; ein Bot je Repo braucht nur einen Bruchteil davon.
- **Nach `--clone` gegen einen bereits getrimmten Bot abgleichen.** Der Klon
  schleppt leere Verzeichnisse mit, die im Flottenbestand nicht vorkommen
  (`diff <(ls profiles/<neu>/skills) <(ls profiles/<alt>/skills)`), und alle
  Bots sollen denselben getrimmten Stand haben. Leere Ordner ohne Inhalt
  entfernen; echte Abweichungen einzeln pruefen, nicht den Bot-Bestand neu
  ausduennen.
- **Ein Shallow-Klon laesst sich nicht pushen.** `--depth 1`-Klone enden beim
  `git push` in ein eigenes Remote mit `remote: fatal: did not receive expected
  object … index-pack failed` — dem Empfaenger fehlt die Vorgeschichte, nicht
  dem Klon. Vor jedem Push in ein eigenes Repo erst
  `git fetch --unshallow <upstream>` und die Tiefe gegenpruefen
  (`git rev-list --count HEAD`), dann laeuft der Push durch. Betrifft die ganze
  Flotte: die Klone unter `Werkstatt/` sind shallow angelegt.
- **Sichern ohne Veroeffentlichen: eigenes privates Repo statt Fork.** Soll ein
  Repo ausser Haus liegen, ohne dass eigene Arbeit oeffentlich wird, **keinen**
  Fork des oeffentlichen Upstreams anlegen (der waere zwingend oeffentlich),
  sondern ein privates Repo als `origin` und das Original als `upstream`:
  `gh repo create <konto>/<name> --private`, dann
  `git remote rename origin upstream`, `git remote add origin <neu>`,
  `git push -u origin --all`. Danach sind Sichern (`git push origin`) und
  Update-Holen (`git fetch upstream`) getrennte Wege — genau die Trennung, die
  ein Fork sonst mitliefert, aber um den Preis der Oeffentlichkeit.
- **Kein Symlink und kein Import aus Fremd-Repos.** Siehe `skill-library-sync`
  und `fundus-zugriff`.
- **Hilfsskripte gehoeren nicht nach `Agenten/Routinen/`.** Dort gilt jede `.ps1`
  als Routine und muss am Bus haengen, sonst reisst `tests/test_ende_zu_ende.py`
  mit „ohne Bus-Anbindung". Werkzeuge nach `Agenten/Werkzeuge/`.
- **Eine neue `.ps1` unter `Agenten/Routinen/` reisst die Bus-Suite, wenn sie
  ohne Anbindung liegt.** Eine Waechter-/Start-Routine braucht Melde-Start/
  Melde-Ende aus `Bus/Ereignis.ps1` (Muster `bus-integration`); ein
  Registrierungsskript mit `Register-ScheduledTask` wird vom Test generisch
  uebersprungen und bleibt ohne Anbindung (beides gemessen am
  gateway-waechter, 16.09.2026).
- **skillsbot.py ist CRLF; das Patch-Werkzeug vermurkst seine Einrueckung.**
  Mehrzeilige Ersetzungen im Python-Code enden mit verschobener Einrueckung
  (Syntax-Fehler). Nicht erneut patchen, sondern byte-genau per kleinem
  Python-Skript ersetzen (bytes lesen, `assert data.count(alt) == 1`, bytes
  schreiben) - Zeilenenden dabei unangetastet lassen.
- **Alle Bots erben die Telegram-/Photon-Credential des Startprofils.**
  `hermes profile list` warnt „shares its … credential with default". Solange
  die Bots ueber `/bot` angesprochen werden (der SkillsBot traegt den Token,
  nicht der Bot), ist das folgenlos; fuer ein Multiplex-Gateway muesste jeder
  Bot eine eigene Credential bekommen oder die geteilte entfernt werden -
  bewusst nicht anfassen, im Bericht nennen.
- **`terminal.backend: docker` macht Repo-Bots lahm (17.09.2026).** Mit
  `docker_mount_cwd_to_workspace: false` (Default) sieht der Bot das Repo
  NICHT: TERMINAL_CWD wird ignoriert, er arbeitet in /root eines Linux-
  Containers. Beim ersten echten Auftrag (caveman, /bot) grub er ueber den
  windows_mcp-Umweg auf den Host (172 s je Aufruf) und lief in den 300-s-
  Timeout des SkillsBot - „Bot X ist gescheitert". `hermes -p NAME config
  set terminal.backend local` stellt auf den Host-Arbeitsplatz um (wie die
  15 neueren Bots). Nach der Umstellung funktioniert der Bot (PONG in 10 s,
  ls/git log im Repo in 50 s). Alle 27 Profile sind seit 17.09.2026 local;
  `grep -l "backend: docker" profiles/*/config.yaml` muss leer sein. Neben-
  wirkung: `hermes config set` schreibt die Datei neu und entfernt den
  auskommentierten Vorlagen-Block am Ende - harmlos.

## Abgrenzung

- Host-Zugriff, PowerShell-Fallen, gezielter Dateiersatz: `windows-host-zugriff`
- Hermes-Installation reparieren (venv, PYTHONHOME, SQLite): `hermes-maintenance`
- Skill-Ablagen abgleichen und Fundus nutzen: `skill-library-sync`, `fundus-zugriff`
- Telegram-Bruecke, A2A, SkillsBot-Befehle: `a2a-telegram-skills`
