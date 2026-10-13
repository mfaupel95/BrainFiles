---
name: bot-interpool-steuerung
category: autonomous-ai-agents
description: Use when routing repo-bot work. Delegate serially, then verify the result.
---

# Interpool-Bot-Steuerung

Ich bin die Interpool (Profil `bots`) auf Telegram. Ich leite Auftraege an die
Repo-Bots (Profile unter `Agenten/Hermes/profiles/<bot>/`, Startverzeichnis
`Werkstatt/Repos/<repo>`) weiter und fuehre sie NICHT selbst aus. Start:
`hermes -p <bot> chat -q "<auftrag>"` aus `Agenten/Hermes/profiles`.

- **Binär-Pfad:** `hermes` ist NICHT `./hermes` im Profil-Ordner — der Aufrufer
  liegt unter `Agenten/Hermes/hermes-agent/.hermes/bin/hermes` (bzw. `hermes`
  im PATH). Ein Start mit `./hermes` bricht mit "No such file or directory"
  (exit 127) ab. Immer den vollen Pfad oder `hermes` aus dem PATH verwenden.

## Lektion: Immer als Hintergrundjob mit notify starten
- Repo-Bot-Kaltstart + Auftrag ueberschreitet hier regelmaessig das Foreground-
  Timeout (~7 min, terminal wird mit exit 0 timeout abgebrochen). Das Ergebnis
  geht dann verloren und der Bot-Daemon haengt weiter (nicht abgestuerzt).
- Start deshalb IMMER als: `terminal(background=true, notify=true,
  persist_on_release=true, command="cd profiles && env -u PYTHONHOME -u PYTHONPATH hermes -p <bot> chat -q ...")`.
  Ergebnis kommt als eigene Nachricht, sobald der Prozess endet. Persist on release,
  weil sonst ein vorzeitiges /new oder Timeout den laufenden Job killt.
- Nach Ende Exitcode und Ergebnis abwarten. Ist die Ausgabe abgeschnitten, den
  vorhandenen Prozess-Log mit `process_manage(action="log", session_id=...)`
  seitenweise holen — denselben Auftrag nicht neu starten; ein zweiter Prozess
  kann dieselben Dateien oder Ressourcen parallel bearbeiten.
- Fremdarbeit im gemeinsamen Repo-Baum nicht ueberschreiben oder mitcommitten:
  vor Weiterarbeit `git status` und Aenderungszeit pruefen, und nur den Bot
  starten, der den betreffenden Bereich verantwortet.
- Vor dem Start `ps aux | grep -i 'fomo-radar|hermes'` pruefen: haengt noch ein
  Prozess vom abgelaufenen Lauf, erst feststellen, ob er wirklich zum eigenen
  Auftrag gehoert; keinen fremden/aktiven Worker beenden und nie doppelt starten.

## Bot-Wahl: ein Modell, das in Schleifen laeuft, ist ein Wechsel-Grund
- Kollabiert ein delegierter Bot mit exit 1 / "Repetition Detected" (Modell-Loop),
  NICHT denselben Bot blind erneut starten — das Modell kollabiert wieder. Erst im
  Repo pruefen, was wirklich passiert ist (Commit da? Fenster offen? Position
  eingelegt?), dann den Auftrag an einen Bot mit stabilem Modell geben.
- Modell-Karte (gemessen): `recherche` = deepseek-v4-flash (stabil, auch fuer
  Handel-Baum-Analyse, cwd BrainFiles); `markt-recherche`/`lotse` = longcat
  (kollabiert bei offenen Such-/Bau-Aufgaben in Wiederholungsschleifen). Fuer
  Analyse/Recherche im Handel-Baum `recherche` bevorzugen, nicht den longcat-Bot.

## Lokale Modelltests delegieren

- Vor einem Modellstart den vorhandenen Modellserver und GPU-Belegung pruefen;
  Modell-Dateigroesse ist nicht gleich Runtime-VRAM. Niemals einen bestehenden
  Server entladen oder stoppen, um einen Test freizumachen.
- Ein ausdruecklicher Testauftrag erlaubt nur den benoetigten Test, keine
  Downloads, Konfigwechsel oder Handelsaktionen. Smoke-Prompts belegen nur, dass
  ein Modell antwortet; fuer Signalqualitaet den vereinbarten Vertrags-/Eval-Satz
  ausfuehren und die Stichprobe nennen.
- Fehlen bei einem Repo die Checkpoints, Unit-/Routing-Tests von echter Inferenz
  trennen; keine Gewichte ohne ausdrueckliche Download-Freigabe nachladen.
- Hat der Bot selbst einen Testserver gestartet, PID/Endpoint notieren und den
  eigenen Prozess nach der Messung sauber beenden, sofern das erlaubt ist. Einen
  fremden Prozess nie beenden; wenn der eigene nicht sauber stoppbar ist, klar
  melden, dass er weiterlaeuft, und keinen sauberen Abschluss behaupten.

## fomo-radar Score-Workflow
- Ablauf: `score --export` -> Verdicts beurteilen (ok/skip, per LLM-Workflow des
  Bots oder im Chat) -> `score --import <results>`. Ein `--import` ohne neue
  Verdicts ergibt NICHTS.
- `pending_scores.json` liegt im Repo-Root. Struktur: dict mit
  `wallets` (52+), je Wallet: address, chain, source, fomo, indexer_stats
  (fills, buys, sells, closed_trades, wins, win_rate, realized/unrealized/net
  pnl, open_bags).
- Fallen: absurde unrealized-Betraege (Trillionen/Billionen) sind Datenfehler -
  skip, keine Trader. Leere Wallets (0 fills, 0 bags) sind nur Adressen, kein
  Scoring moeglich - skip. Aehnliche/schon bekannte Wallets (z. B. game_for_one)
  koennen schon gescort sein.
- GPU-Engpass: fremder llama-server kann die GPU halten; Scoring-Modell faellt
  von qwen3.5 auf gemma-e4b-8k-64k zurueck, wenn cudaMalloc failed (OOM).
- Repo-Pfad seit 2026-10-12: `O:\Werkstatt\Repos\fomo-robinhood-radar`. Der C:-Junction-Unterpfad `C:\Users\faupe\Documents\BrainFiles\Werkstatt\Repos\fomo-robinhood-radar` existierte zeitweise nicht (leeren Check nicht als "Repo weg" deuten, erst O: pruefen). Bots mit explizitem O:-Pfad im Auftrag abrufen.
- Keys nie ausgeben. Echte Zugaenge nur in `MaxHirn/Wissen/Zugaenge.md`.

## Gruppenchat mit Telegram-Forum-Topics seriell dispatchen

- Max bevorzugt einen einzigen Eingang und serielle Bearbeitung: kein Fan-out an mehrere Profile gleichzeitig. Bei einer fachlichen Gruppenanfrage zuerst genau eine Recherche beauftragen, deren Ergebnis abwarten, dann maximal einen passenden Fachbot bestimmen und erst danach starten.
- `gateway.profile_routes` waehlt fuer ein einzelnes Inbound-Ereignis genau ein Runtime-Profil; es ist kein Recherche->Dispatcher-Workflow. Soll Recherche pruefen und ein Dispatcher danach handeln, route die Gruppe an den Dispatcher und verankere die serielle Weitergabe in dessen Arbeitsanweisung. Route ein Topic direkt zu Recherche, wenn es selbst antworten soll, nicht wenn danach automatisch ein zweites Profil erwartet wird.
- Forum-Themen lassen sich nach `platform` + `chat_id` + `thread_id` routen; vor Topic-Routen die effektive `gateway.profile_routes` lesen und jedes Zielprofil gegen `profiles/<name>/config.yaml` pruefen. Topic-Links koennen Nachrichten-IDs enthalten: niemals die letzte URL-Zahl ungeprueft als `thread_id` einsetzen. Nimm die empfangene `message_thread_id`/SessionSource-`thread_id` aus einer echten Nachricht oder verifiziere sie in der Session-Datenbank.
- Eine Chat-weite Route und spezifische Topic-Routen koennen nebeneinander bestehen; spezifischere Routen gewinnen (thread_id-Spezifitaet 8 > chat_id 4). Nach dem Edit die effektive Route fuer alle Topics aufloesen und nachweisen, dass jedes Inbound-Event nur ein Zielprofil trifft — `parse_profile_routes`/`match_profile_route` aus `gateway/profile_routing.py` gegen die config laufen lassen (Sim je thread_id), bevor der Gateway neu startet.
- **Thread-IDs verifizieren, nicht raten:** Eine `t.me/c/<gruppe>/<id>`-URL kann eine Nachrichten-ID enthalten; sie beweist nicht allein die Topic-`thread_id`. Nutze die tatsaechliche Telegram-`message_thread_id` aus einem eingegangenen Update oder einem gespeicherten Session-Eintrag (`sessions.thread_id` fuer dieselbe `chat_id`). Topic-Namen den IDs nur zuordnen, wenn der Nutzer sie benennt oder die Topic-Metadaten das belegen; sonst nachfragen.
- **Ein Topic = genau EIN Profil.** `profile_routes` kann pro (chat,thread) nur ein Zielprofil haben. Eine Zuordnung mit mehreren Bots pro Topic (z. B. 6 Handel-Bots) ist nicht abbildbar — vor dem Bau die federfuehrenden Bots je Topic mit Max klaeren; die uebrigen bleiben ueber `/bot NAME` im Dispatch erreichbar. Ziel-Profile muessen existieren und ein gueltiges `model.default`/`provider` haben (Multiplex laedt sie).
- Eine SOUL-/Profilregel-Aenderung beweist nicht, dass bereits laufende Topic-Sitzungen sie geladen haben: erst in einer neuen Sitzung pruefen; keinen Gateway-Neustart ausloesen, wenn er alle laufenden Profile beeintraechtigen kann.

## Systempruefung (systempruefung.ps1)

`Agenten/Routinen/systempruefung.ps1` ist die taegliche Diagnose (~7 min).

- **Immer im Hintergrund mit notify starten** — der Foreground-Timeout (300 s) reicht nicht; der Lauf schreibt erst am Ende den Bericht. `terminal(background=true, notify=true, command="powershell -NoProfile -ExecutionPolicy Bypass -File Agenten/Routinen/systempruefung.ps1 -NurPruefen")`.
- **`-NurPruefen` fuer Handlaeufe** (kein Auto-Aufraeumen); der volle Lauf raeumt eindeutig reproduzierbare Orphans selbst weg.
- **Bericht:** `Agenten/Routinen/logs/systempruefung-letzter-lauf.md` (strukturiert: Seit gestern neu / Selbst erledigt / Zu entscheiden / Zur Kenntnis). Vollprotokoll: `logs/systempruefung-<datum>.log`.
- **Kann in der Git-Pruefung haengen** (git-Prozesse bleiben stehen, kein Bericht). Haengt ein eigener Lauf >10 min ohne Bericht, den eigenen Lauf beenden und den letzten Bericht lesen statt weiter zu warten.

## Sonstiges
- Cron-Jobs, die ich erstellt habe (z. B. `fomo-radar Loop`), koennen mit dem
  cronjob-Tool gepauajt/weiterverwaltet werden - der fomo-radar Bot selbst kann
  das nicht (anderes Profil). `/loop` ist reiner Chat-Befehl, kein CLI-Weg.
- TASKS.md-Punkte (T-0xx): Nummer = Auftrag an den passenden Bot. Im Zweifel
  Bot-Liste pruefen (`profiles/`) statt selbst anzufangen.
- **TASKS.md-Beschreibungen koennen veraltet sein — vor dem Delegieren den
  IST-Stand verifizieren, nicht den Text glauben.** Ein Eintrag kann einen
  Punkt als "blockiert"/"offen" beschreiben, der laengst erledigt ist (z. B.
  T-396: Vorschlag als blockiert gelistet, war aber schon angewendet, Commit
  vorhanden, Werte in der wachen.json korrekt). Erst `git log`/`git show` auf
  den vermuteten Commit und die betroffene Konfig lesen; ist der Punkt faktisch
  erledigt, das in der Rueckmeldung sagen statt einen Auftrag dafuer zu
  starten oder einen Fachbot blind auf den TASKS-Text loszulassen.
- **Ein delegierter Bot kann Arbeit MELDEN, die nie passiert ist — vor dem
  Weitergeben/Verifizieren auf der Platte pruefen, nicht dem Bericht glauben.**
  Ein Bot kann einen Zweig, Commit, Testlauf und "working tree clean"
  behaupten, obwohl nichts davon existiert (Modell-Halluzination). Vor der
  Rueckmeldung an den Nutzer belegen: `git branch -a | grep <zweig>`,
  `git log --oneline -1 <zweig>`, `git diff master..<zweig> -- <pfad>`,
  `git status --short <pfad>`. Ist nichts da, den Auftrag an einen stabilen
  Bot (z. B. `recherche`) neu vergeben mit expliziter Anweisung, die Aenderung
  WIRKLICH auf der Platte zu machen und mit Commit-Hash + diff zu belegen.
- **Nach einem delegierten Commit den ZIEL-ZWEIG pruefen, nicht nur die
  Dateien.** Ein Bot committet auf dem Zweig, den der geteilte Arbeitsbaum
  gerade haelt — das kann der fremde aktive Zweig einer anderen Sitzung sein
  (z. B. `claude/...`), nicht `master`. Betriebskonfig-Aenderungen
  (`wachen.json`-Werte, `dauerlauf.py` SPUREN/AUTO_FREIGABE) gehoeren auf
  `master`. Nach dem Bot-Bericht `git log --oneline -1 <commit>` UND
  `git branch --show-current` pruefen; liegt der Commit auf einem fremden
  Zweig, sag es dem Nutzer und biete an, ihn auf `master` zu bringen.
  - *Auf master bringen ohne `git switch` im geteilten Hauptbaum:* temporaeren
    Worktree auf dem Zielzweig (`master`) anlegen
    (`git worktree add .worktrees/<thema> -b <agent>/<thema> master`), dort
    `git cherry-pick <commit>`, das Ergebnis pruefen, dann per PR einbringen:
    `git push origin <agent>/<thema>`, `gh pr create --base master --head
    <agent>/<thema>`, und erst NACH dem Merge aufraeumen
    (`gh pr merge <n> --merge --delete-branch`, `git worktree remove
    .worktrees/<thema> --force`, `git worktree prune`). Kein direkter
    Fast-forward-Merge auf `master` — die Repo-Regel ist "gemergt per PR".
  - Vor dem Cherry-pick pruefen, dass das Legacy-Commit nur die eine
    Konfig/Datei anfasst und deren Kontextanchor auf dem Zielzweig identisch
    ist (`git show --stat <commit>`, `git show <zielzweig>:<pfad> | grep
    <anchor>`); das macht den Port konfliktfrei, statt blind zu portieren.
  - Nach dem Port den Inhalt validieren, BEVOR gepusht wird — bei YAML z. B.
    `python -c "import yaml; yaml.safe_load(open('...',encoding='utf-8'))"`
    und die Werte (Routen/Profile) ausgeben, nicht nur die Dateigroesse.    
  - Der urspruengliche Commit bleibt auf dem fremden Zweig liegen; kommt der
    spaeter nach `master`, gibt es einen Konflikt (identischer Inhalt) — den
    Hinweis in der Rueckmeldung nicht verschweigen. Der fremde Zweig ist der
    gerade aktive des geteilten Arbeitsbaums und traegt oft noch uncommittete
    Arbeit der parallelen Sitzung: dort kein `git switch`/Rebase/Reset
    ausfuehren, nur der temporaere Worktree wird beruehrt.
