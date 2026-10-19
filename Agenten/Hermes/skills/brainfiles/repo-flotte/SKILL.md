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
   und danach ZWEI `config set`-Aufrufe: `terminal.cwd <repo-pfad>` UND
   `terminal.backend local` - ohne den zweiten erbt der Klon `docker` und sieht
   das Repo nicht (Falle unten). Danach `git add --dry-run
   Agenten/Hermes/profiles/<name>/` gegenpruefen: nur `SOUL.md`, `config.yaml`,
   `profile.yaml` duerfen erscheinen. `--clone`
 uebernimmt Modell, Werkzeuge und Skills des Startprofils, `--description`
 landet in `profile.yaml` und wird vom Kanban-Orchestrator zum Sortieren benutzt.
 Danach die zwei Hausskripte fahren: `bot-modell-auf-router.py --anwenden`
 (idempotent, stellt nur den Neuen auf den Router um - „1 Profil umgestellt,
 N uebersprungen") und `profil-kanaele-bereinigen.py --anwenden` (bei einem
 Klon nach der 18.09.-Bereinigung erwartbar „Nichts zu tun", trotzdem laufen
 lassen und 0 Warnungen in `hermes profile list` belegen).
 *Fertig, wenn* `hermes profile list` jeden Bot fuehrt. Danach der Skill-Trim:
   `diff <(ls profiles/<neu>/skills) <(ls profiles/<alt-getrimmt>/skills)` - leer
   = identisch; leere Klon-Ordner entfernen (siehe Falle unten).
   **Neuer Bot in den Repo-Betrieb eintragen:** `Agenten/Werkzeuge/repos-zentrale/-
   repos-zentrale.json` um einen Eintrag ergaenzen (`ordner`, `art`, `bot`,
   `notiz`); `art: "doku"` solange kein Startbefehl belegt ist (Gruppe NUR
   DOKU), erst wenn ein Start echter Laeufe belegt ist, auf node/python/rust
   hochstufen. Dazu die Flotten-Doku `MaxHirn/Wissen/Repo-Bots.md` (Zahl +
   Tabelle) aktualisieren. `/bots` liest Profile von der Platte - kein
   SkillsBot-Neustart noetig (der ist nur fuer NEUE Befehle).
6. **Zaehlen, welche Bots fehlen, gegen die Platte:** `ls Werkstatt/` gegen
   `ls Agenten/Hermes/profiles/` halten — ein Ordner in profiles/ mit config.yaml
   ist ein Bot. Ein Verzeichnis unter Repos/ OHNE `.git` (z. B. eine
   Worktree-Sammlung) ist keine Repo und bekommt keinen Bot. Die Zaehlung als
   dauerhafte Notiz ablegen (z. B. Wissen/Repo-Bots.md), mit dem Hinweis, dass
   die Platte die Wahrheit bleibt und die Notiz altert.
   **Und die Frage „welche Repos sind noch nicht fertig?" ist eine Abfrage des
   MANIFESTS, kein Blick ins Fenster.** `Agenten/Werkzeuge/repos-zentrale/
   repos-zentrale.json` je Zeile auszaehlen: `wurzel` (leer = REPOS, sonst
   `handel`/`werkstatt`/`projekte`), `gruppe` (`doku`/`kein_start`/leer), `start`,
   `warnungen`. **Drei Zahlen nennen** - Zeilen gesamt, mit Startbefehl, ohne -
   und die „ohne" aufteilen: der groesste Teil ist Ablage/Doku und in Ordnung,
   als Luecke zaehlt nur, was startbar sein SOLL und es nicht ist (venv oder
   Pflichtpfad fehlt, ein Werkzeug mit eigenem Einstieg und ohne belegten
   Aufruf). Die rohe Zahl liest sich als „85 Sachen sind kaputt", von denen rund
   77 keine sind. **Zweite Liste:** Ordnernamen der Wurzel gegen die
   Manifest-Ordner diffen - was fehlt, ist ein FEHLT-Kandidat, und oft ist es
   keiner (Worktree-Sammlung ohne `.git`, Editor-Ordner). **Dritte Liste:**
   `warnungen`, die Einzige, die auf einen toten Knopf zeigt („Bot-Profil wurde
   entfernt" = der Bot-Knopf fuehrt ins Leere). Der Rest der offenen Punkte steht
   in `MaxHirn/Archiv/TASKS.md`, nicht im Manifest.
   **Aufraeumkandidaten erst auf EIGENEN Inhalt pruefen, nie auf das Alter:**
   `git worktree list` und je Zweig
   `git rev-list --left-right --count master...<zweig>` - `N 0` heisst, der Zweig
   traegt nichts, was master nicht hat (wegwerfbar), `0 N` traegt eigene Commits
   und wird gemergt, nicht geloescht.
   **Rest-Ordner eines Anlegevorgangs zaehlen mit — und nach dem Alter beurteilen.**
   `hermes profile create` laesst bei einem Abbruch oder einer Umbenennung einen
   Punkt-Ordner `.<name>.staging-<pid>` in `profiles/` stehen; er traegt eine
   `config.yaml` und galt damit als Bot (Phantom in `/bots`;
   `skillsbot.bot_namen()` ueberspringt seit 23.09.2026 Punkte-Ordner, die
   Gegenprobe bleibt `ls profiles/ | grep '^\\.'`). Im Bericht nennen. Dann die
   Frage, ob er noch jemandem gehoert: laeuft kein `profile create`-Prozess mehr
   (`Get-CimInstance Win32_Process`, Kommandozeile), ist der Ordner tot und
   gehoert weg — er ist nicht nur Platz, sondern eine VOLLE Kopie des
   Startprofils samt `.env` (Kanalzugangsdaten) und Sessions (gemessen 599 MB),
   also eine zweite Ablage derselben Kennung, die die Bereinigung der Kanaele
   gerade beseitigt hat. Einen MINUTEN alten Ordner dagegen liegen lassen: dann
   schreibt eine parallele Sitzung noch.
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
- **Nach jedem frischen Klon zaehlen, was LESBAR ist — nicht was auf der Platte liegt.**
  Der Virenscanner greift Dateien eines Klons an (Exploit-Muster, Webshell-Signaturen,
  Makros) und laesst sie danach als Datei stehen, sperrt aber das Oeffnen: `ls` und
  `Get-Item` zeigen Groesse und Datum, jeder Lesevorgang scheitert mit „Datei enthaelt
  einen Virus", und ein Index/Test ueberspringt sie STILL (`git ls-files` kennt sie
  weiterhin). `git checkout -- .` holt Geloeschtes zurueck, die Lesesperre bleibt.
  Beleg der Sperren: `Get-MpThreatDetection | Sort-Object InitialDetectionTime
  -Descending`. Betroffene Dateien namentlich melden und die Ausnahme als
  Nutzerentscheidung anbieten — nie selbst eine Scanner-Ausnahme setzen. Rezept:
  `fremde-skill-sammlung-einbinden`.
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
- **Nur drei Dateien je Profil sind versioniert.** Die `.gitignore`-Whitelist
  gibt je `profiles/<name>/` genau `SOUL.md`, `config.yaml`, `profile.yaml`
  frei — state.db, sessions, credentials bleiben unversioniert, wie gewollt.
  Nach dem Anlegen wirkt der ganze Ordnername als `??`; `git add` des Ordners
  nimmt trotzdem nur die drei freigegebenen Dateien auf (Vorabkontrolle mit
  `git add --dry-run <profilordner>`). Steht etwas anderes im Dry-Run, ist die
  Whitelist falsch — nicht stumm aufraeumen, sondern die Freigabe pruefen.
- **`profile create` OHNE `--clone` legt nur eine 45-Zeilen-`config.yaml` an — kein `profile.yaml`, keine Beschreibung, keine Skills, und die `.env` fehlt ganz.** Der schlanke Weg ist trotzdem richtig (kein Skill-Ballast), er verlangt aber drei Nacharbeiten, sonst ist der Bot halb: (a) Vorlagendateien eines anderen Bots kopieren bringt dessen ROLLE mit — die Beschreibung nach `hermes profile describe <name> --text "…"` neu setzen und `hermes profile describe <name>` gegenlesen; (b) die `.env` des Startprofils uebernehmen, sonst fehlen die Providers-Schluessel; (c) `providers:`-Block und `model.provider`/`model.default` in die eigene `config.yaml` schreiben bzw. aus einem fertigen Bot kopieren. Nachweis: `hermes profile describe <name>` zeigt die eigene Rolle, `hermes -p <name> fallback list` die Kette, und ein echter `/bot`-Aufruf antwortet aus dem richtigen Repo. Ein Bot, der antwortet, ist noch kein Beleg fuer das RICHTIGE Modell — er kann komplett ueber den lokalen Rueckfall laufen; das im Bericht sagen, wenn die Primaeranmeldung noch fehlt.
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
- **Ein Klon, dessen `origin` aufs ORIGINAL zeigt, ist KEIN Flotten-Klon.**
  Kommt ein Repo als Direkt-Klon des Upstreams an, nachtraeglich auf die
  Flotten-Form bringen: `gh api -X POST "repos/<upstream>/forks"`, in einer
  Schleife abfragen bis der Name aufloest, `git remote set-url origin
  https://github.com/<konto>/<name>.git`, `git remote add upstream <original>`,
  dann `git push -u origin <branch>`. GitHub spiegelt die Branches beim Fork
  automatisch — der Push meldet oft „Everything up-to-date“, das ist kein
  Fehler; Nachweis ueber `gh api repos/<konto>/<name>/commits/<sha>` (Fork
  enthaelt den Commit) plus `git remote -v`. Den Branch-Namen der Fremd-Repo
  respektieren (z. B. `github-main` statt `master`/`main`) — nicht auf den
  Hausnamen umbenennen.
- **Repo-Bot ist kein Handel-Spur.** Der Handels-Dauerlauf (`dauerlauf.SPUREN`)
  und `/bericht` zaehlen ausschliesslich Handelsspuren (Papier-/Live-Strategien
  mit eigenem Buch); ein Repo-Bot (MCP-Server, Tool, Referenzsammlung) gehoert
  dort bewusst NICHT hinein, auch wenn er "trade" im Namen traegt. Sein
  Betrieb ist der Repo-Betrieb (repos-zentrale-Manifest, Flotten-Doku) und die
  Abfrage ueber `/bot`. Den Unterschied beim "Bot hinzufuegen"-Auftrag offen
  benennen statt einen Werkzeug-Klon in den Handelszyklus zu ziehen.
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
- **Kanalzugangsdaten gehoeren nur ins Profil `default` (18.09.2026).** Ein
  Telegram-/Photon-Token gehoert genau einem Profil. 17 Bot-Profile trugen die
  Kennung des Startprofils, `hermes profile list` warnte je Profil, und ein
  Bot-Gateway auf demselben Token nahm dem Hauptgateway die Nachrichten weg
  (projectatlas hatte am 18.09. um 01:18 Telegram-Sitzungen, obwohl das
  Hauptgateway nur `default` bedient). Aufraeumen:
  `Agenten/Hermes/scripts/profil-kanaele-bereinigen.py` - ohne Argument nur
  zeigen, `--anwenden` schreibt (je Profil erst `.env.bak-JJJJMMTT`, Zeilen-
  enden bleiben), `--zuruecknehmen` holt die Sicherung zurueck. Welche Zeile
  ein Kanal ist, entscheidet `hermes_cli.profile_channels.ChannelKeyIndex`,
  nicht eine eigene Liste. Gegenprobe: `hermes profile list` zeigt 0 Warnungen.
- **Die Bots fahren auf dem Nous-Portal, nicht ueber den lokalen Router.** Profile
  sind Inseln und lesen nur ihr eigenes `auth.json`/`.env`; ohne Anmeldung endet
  jeder `/bot`-Aufruf mit "Hermes is not logged into Nous Portal", und eine
  geerbte `fallback_providers`-Kette verdeckt das mit einem Kontextfenster-Fehler.
  Stand: `model.provider=nous`, `model.default=deepseek/deepseek-v4-flash-0731`,
  Werkzeug `Agenten/Hermes/scripts/bot-modell-auf-nous.py` (Trockenlauf,
  `--anwenden`, `--zuruecknehmen`). Der Router war nur Zwischenloesung: faellt
  seine Combo auf einen toten Zweig (Gratisstufe), stehen ALLE Bots gleichzeitig
  still — darum haengt die Flotte nicht mehr daran. Unberuehrt bleiben Profile mit
  eigener Anmeldung (`basic-memory`, `awesome-systematic-trading`) und eigene Wege
  (`openmontage` = llamacpp). Vor "Bot geht nicht" also erst die Modellkennung
  pruefen, nicht die Kanaele.
- **Ohne eigene `auth.json` antwortet ein Profil nicht — Sitzung per SYMLINK, nicht
  per Kopie.** `Agenten/Hermes/scripts/auth-verknuepfen.ps1` (erhoehte Shell, ein
  UAC-Prompt) verweist `profiles/<bot>/auth.json` auf
  `Agenten/Hermes/auth.json`. Von Hand braucht der Link NICHT die Erhoehung:
  `pwsh` 7 legt ihn direkt an (`New-Item -ItemType SymbolicLink`), waehrend
  `powershell.exe` 5.1 mit „Administratorrechte erforderlich" abbricht — den
  Admin-Weg also nicht als Bedingung melden, sondern das Werkzeug waehlen.
  Von Hand, ohne Erhoehung, in EINER Zeile (Beispiel fuer ein neues Profil):
  `pwsh -NoProfile -Command "New-Item -ItemType SymbolicLink -Path '<...>\profiles\<bot>\auth.json' -Target '<...>\Agenten\Hermes\auth.json'"` —
  danach gegenpruefen (`Get-Item <pfad> -Force | Select LinkType, Target`), denn
  ein Symlink, der nach einem fehlgeschlagenen Versuch NICHT angelegt wurde,
  sieht im Profil wie ein fehlender Schluessel aus und der Bot antwortet still
  ueber die Fallback-Kette weiter. Eine Kopie waere dieselbe Refresh-Kennung in vielen
  Dateien, und die erste Rotation entwertet alle anderen. `NOUS_API_KEY` in der
  Benutzerumgebung genuegt NICHT — der Gate verlangt den Provider-State im
  `auth.json` des Profils. Ein frisch aus `profiles/.deleted/` zurueckgeholtes
  Profil hat noch keine Sitzung und faellt sofort durch.
- **`profiles/.deleted/` sind keine Bots.** Weggelegte Profile zaehlen bei keiner
  Flottenzaehlung mit (sonst stimmt `ls profiles/` gegen `ls Werkstatt/`
  nicht) und sind per `/bot` nicht erreichbar. Bei "Bot fehlt" zuerst hier
  nachsehen, bevor ein Profil neu angelegt wird.
- **`hermes config set` schneidet den Kommentar-Schluss der `config.yaml` ab.**
  In 6 Profilen fehlten danach 38 Zeilen Doku am Dateiende (nur Kommentare, kein
  Schaden an Werten). Der Fix ist nicht "Block anhaengen", sondern die Ziel-Fassung
  exakt bauen: die Sicherung/HEAD-Fassung BYTE-genau nehmen und nur den `model:`-Block
  ersetzen - beim Schreiben `newline=""` setzen, sonst wandelt `read_text()` die
  CRLF-Datei still nach LF um und der Diff zeigt plotzlich die ganze Datei.
  `bot-modell-auf-router.py` macht das von selbst.
- **Skill in ein Profil legen: erst auf Namenskollision pruefen.** Ein Skill-Name, der schon als offizieller/bundled Skill existiert (z. B. `grill-me` unter `software-development/`), shadowed die eigene Kopie — sie wird weder gelistet noch geladen, obwohl sie auf der Platte liegt. Vor dem Anlegen `hermes skills list | grep <name>` und `hermes skills inspect <name>`; existiert der Name schon, entweder einen eindeutigen Namen verwenden oder das Duplikat entfernen und die vorhandene Fassung nutzen. `hermes skills inspect <name>` loest auch aus dem offiziellen Katalog auf — ein Treffer dort heisst nicht, dass der Skill installiert ist. Der Auftrag „Skill auch ins Default-Profil" ist oft schon erfuellt, weil die Adaption dort bereits liegt — erst pruefen, dann duplizieren.
- **repos-zentrale.json nie mit json.dumps neu schreiben.** Ein `json.dumps(indent=1)` formatiert die ganze ~3400-Zeilen-Datei um (6764-Zeilen-Diff statt 8) und erzeugt Rauschen im Commit. Einen Eintrag byte-exakt einfuegen: Original per `git checkout <vorheriger-commit> -- <datei>` zurueckholen, dann per Python `s.replace(anchor, anchor_mit_eintrag)` mit `assert s.count(anchor) == 1` und `newline=''` schreiben — der Anker ist der Block des Nachbarn (z. B. `    },\n    {\n      "ordner": "Harvard-..."`). Danach `git diff --stat` muss die Zahl der eigenen Zeilen zeigen.
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
- Profil-Zugangsdaten (Kanalzeilen strippen, Modellkennung und Router, `hermes config set`
  mit seinen Fallen) und der Weg einer Einstellung ueber ALLE Profile:
  `hermes-config-ops`, dort `references/profil-kanalzugangsdaten.md`
