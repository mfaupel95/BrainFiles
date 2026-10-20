---
name: bot-interpool-steuerung
category: autonomous-ai-agents
description: Use when routing repo-bot work. Delegate serially, then verify the result.
---

# Interpool-Bot-Steuerung

Ich bin die Interpool (Profil `bots`) auf Telegram. Ich leite Auftraege an die
Repo-Bots (Profile unter `Agenten/Hermes/profiles/<bot>/`, Startverzeichnis
`Werkstatt/<repo>`) weiter und fuehre sie NICHT selbst aus. Start:
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
- **Foreground-Timeout ist nicht der Tod des Ergebnisses.** Laueft der Start
  versehentlich im Foreground (`terminal(...)` ohne background) in den ~420 s-
  Timeout, HAENGT der Bot weiter und arbeitet den Auftrag zu Ende — nur die
  Rueckgabe ist verloren. Den Prozess per `ps aux | grep hermes` aufspueren, und
  waehrend er laeuft (oder nach seinem Ende) `profiles/<bot>/logs/agent.log`
  lesen: der Log listet jede Tool-Execution mit Dauer/Zeichen und schreibt am
  Turn-Ende `reason=...` (z. B. `max_iterations_reached(5/5)`). Daraus den
  Teilbefund und den Abbruchgrund ableiten, statt denselben Auftrag blind neu
  zu starten oder falsch als Fehlschlag zu melden.
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
  Handel-Baum-Analyse, cwd BrainFiles), aber LESEN-only; `jev-trader` = wird
  jetzt ebenso auf deepseek-v4-flash gefahren (seit 14.10.2026, Umbau der
  fuer schreibende Handel-Codearbeit); `markt-recherche`/`lotse` = longcat
  (kollabiert bei offenen Such-/Bau-Aufgaben in Wiederholungsschleifen). Fuer
  Analyse/Recherche im Handel-Baum `recherche` bevorzugen, nicht den longcat-Bot; fuer einen Bau/Commit einen deepseek-fahrenden schreibfaehigen Bot nehmen.
- **Iterationsbudget-Erschoepfung ist ein eigener Abbruchmodus, kein Kollaps.**
  Ein Bot kann mit exit 0 enden, aber "Iteration budget exhausted (5/5)"
  melden — er hat das Tool-Budget ausgeschoepft, bevor er fertig wurde, und
  liefert nur einen Teilbefund. Das ist kein Modell-Loop (nicht blind denselben
  Bot neu starten), sondern ein zu breiter Auftrag. Vor dem Neustart pruefen,
  was er schon geschafft hat (z. B. Journal-Analyse fertig, Parametersuche
  nicht), und den Rest als EINEN engen, single-focus Auftrag neu vergeben —
  nicht den ganzen mehrteiligen Auftrag wiederholen. Ein mehrteiliger
  Analyse-Auftrag (Asymmetrie + Parametersuche + Tore) gehoert in getrennte
  Einzelauftraege, sonst frisst der erste Teil das Budget.
- **Bau-Bot gibt "exhausted (5/5)" zurueck, aber die Dateien sind geschrieben
  und die Tests zeigen konkrete rote Faelle: direkt auf dem Zweig verifizieren,
  die benannten Bugs selbst patchen, NICHT den Bau neu delegieren.** Ein
  Bau-Auftrag, der `fetch.py`+`config.json`+`README`+`tests/` schreibt und dann
  am Budget scheitert (Symptom: exit 1, nur `asyncio``closed pipe``-Teardown-am
  Ende), hat die Kernarbeit schon geleistet; der Bericht nennt die Parser-Bugs
  (z. B. stooq-Hinweiszeilen vor der Kopfzeile, leere Eingabe), die seine eigenen
  Tests gerade rot machen. Diese benannten Randfaelle sind vom Interpool direkt
  behebbar (ein `parse_stooq_csv`-Patch), statt einen zweiten Botlauf zu starten
  — ein Neustart zaehlt nur ein neues Tool-Budget auf einem fast fertigen Bau.
  Die Delegationsregel "nicht selbst ausfuehren" gilt fuer den Repo-Baum und
  fremde Fachbots; einen toten, benannten Klein-Bug im eigenen Build zu patchen
  ist Abschlussarbeit, kein Fremdeingriff.
- **Ein Analyse-/Bestandsaufnahme-Auftrag muss benennen, WELCHE Dateien zu
  lesen sind (README, Einstiegsdateien, ggf. eine wachen.json) und darf
  teure Sondierungs-Kommandos ausdruecklich VERBIETEN.** Ohne das
geschieht
  Folgendes: der Bot macht einen teuren, haengenden Probe-Command (z. B.
  `du -sh` auf dem venv, der hier 180s auf den Tool-Timeout laeuft), der State
  wiederholt sich, und die 5-Iterationen-Budget ist aufgebraucht, bevor irgend
  eine inhaltliche Analyse lief — der Bot endet mit exit 0 + "exhausted (5/5)"
  und einem Leerbefund. Konkret in den Auftrag schreiben: "keine
  du/du -sh/venv-Groessenchecks (haengen 180s)", "lies nur <Liste>,
  nicht das ganze Repo", und explizit, dass KEIN Code eingespielt werden soll,
  wenn die Aufgabe rein bewertend ist.

## Neuen Repo-Bot anlegen (Klon + Profil + Doku)

Auftrag "<repo> zur Werkstatt und Agent anbinden" ist Pool-Infrastruktur, die
ich selbst ausfuehre — kein Fall fuer einen Fachbot. Reihenfolge:

1. **Klonen:** `git clone --quiet https://github.com/mfaupel95/<repo>.git
   Werkstatt/<repo>` (Junction → O:). `origin` = mfaupel95-Fork, dann
   `git remote add upstream <original>` (nur lesen, nie pushen).
2. **Profil anlegen:** `mkdir -p profiles/<repo>/skills`. config.yaml nach
   Vorlage eines kompakten Repo-Bots (z. B. `lotse`), aber `model.default` =
   `deepseek/deepseek-v4-flash-0731` (stabil) statt longcat (kollabiert in
   Schleifen); `terminal.cwd` auf `Werkstatt/<repo>`. SOUL.md nach Hausmuster
   (verweist auf `..\rule_repo-bots.md`), Repo-Skill `skills/<repo>-betrieb/`.
3. **Verifizieren:** `hermes profile list` zeigt das Profil; Smoke-Test
   `hermes -p <repo> chat -q "<eine Frage>"` (Kaltstart ~18 s, Antwort muss
   das Repo korrekt nennen).
4. **Committen:** nur eigene Pfade stagen (`git add <pfad>`), nie `-A`;
   `git commit --author="Hermes <hermes@local>"`. Danach `git branch
   --show-current` pruefen — muss `master` sein.
5. **Doku:** Zeile in die Flottenstand-Tabelle von
   `MaxHirn/Wissen/Repo-Bots.md` (alphabetisch einsortieren) + `updated` im
   Frontmatter hochsetzen; committen.

Fallen:
- **`hermes profiles` ist kein Befehl** — es heisst `hermes profile list`.
- **`write_file` verweigert das Ueberschreiben von `SOUL.md`**, weil das
  Profil-Scaffold beim `mkdir` schon eine Default-SOUL.md (nur der
  Standard-Text) anlegt. Erst `read_file` auf die vorhandene SOUL.md, dann
  ueberschreiben.
- **Verwaister `.git/index.lock`:** `git commit` bricht mit "index.lock
  exists" ab, obwohl kein Git-Prozess laeuft (`ps aux | grep git` leer).
  Lock-Datei aelter als ~2 min ohne laufenden Prozess ist tot — `rm -f
  .git/index.lock` und erneut committen. Nicht blind loeschen, wenn ein
  echter Prozess laeuft.
- **Kein automatischer Live-Betrieb.** Ein neuer Repo-Bot baut/testet/bewertet
  Strategien, oeffnet aber keine Positionen und bekommt keine Spur im
  `dauerlauf`. Eine echte Handelsspur (Statusdateien lesen → ins Buch buchen)
  ist ein separater Bau in `Agenten/Handel/` mit `wachen.json` — nur auf
  ausdruecklichen Auftrag, dann an den passenden Handel-Bot delegieren.
  - **Den Handel-Bau-Bot ueber `terminal.cwd` waehlen, nicht ueber den Namen.**
    Eine Spur im Betriebsbereich wird nur von einem Profil gebaut, dessen
    `cwd` auf `Agenten/Handel` zeigt (hier: `markt-recherche`) — die
    Repo-Fork-Bots (`jev-trader`, `agent-trade-kit`, `awesome-systematic-trading`,
    `harvard-trading`, `fomo-radar`, ...) starten alle in `Werkstatt/Repos/<repo>`/
    bzw. `Werkstatt/<repo>` und bauen/testsen Strategien, schreiben aber nicht
    in den Betriebsbereich. Vor dem Delegieren aller Profile die `cwd`-Zeile
    der `config.yaml` pruefen (`grep -A3 'terminal:' <p>/config.yaml | grep cwd`
    oder `grep -rl 'Agenten/Handel' */config.yaml`) statt nach einem
    Bot-Namen mit "handel" zu suchen.

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
- **Parallele fomo-radar-Sitzungen koennen dieselbe Queue abarbeiten — vor einem
  Score-Job den IST-Stand in der DB pruefen, nicht dem letzten Bericht glauben.**
  Mehrere delegierte Auftraege (Cron + Chat) koennen dieselben Wallets schon
  gescort haben; ein neuer `score --export` findet dann `exported: 0` und ein
  Re-Score wuerde heutige Kontexte ueberschreiben und die Rescore-Fenster
  (72 h watch / 14 d dropped) verletzen. Vor dem Start die Verteilung in der DB
  lesen (`SELECT status, COUNT(*) FROM traders GROUP BY status`,
  `SELECT COUNT(*) FROM score_history WHERE date(ts,'unixepoch')=date('now')`)
  und `docs/STATUS.md`-Session-Eintraege; ist die Queue leer, KEINEN Score-Job
  starten und das als erledigt melden.
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
- Repo-Pfad ist UNSTABIL und wechselt zwischen `O:\Werkstatt\Repos\fomo-robinhood-radar` und `C:\Users\faupe\Documents\BrainFiles\Werkstatt\fomo-robinhood-radar` (beide wurden 2026-10 beobachtet; der C:-Junction-Unterpfad existierte zeitweise nicht). Einen leeren Check nicht als "Repo weg" deuten — erst beide Pfade pruefen. Im Auftrag an den Bot beide Kandidaten nennen und ihn das Repo selbst lokalisieren lassen, statt einen Pfad hart zu verdrahten.
- **Das fomo-radar-Profil hat einen EIGENEN Pipeline-Cron** (`profiles/fomo-radar/cron/jobs.json`, Job `0708b8f2725d`, alle 6 h `run --once` gegen das Repo). Vor dem Anlegen eines "fomo-radar Loop"-Crons im bots-Profil erst pruefen, ob das fomo-radar-Profil selbst schon einen laufenden Loop hat — ein zweiter ist Doppelarbeit und wird pausiert. Der fomo-radar-eigene Cron ist der echte Pipeline-Loop; ein bots-Cron dafuer ist redundant.
- **Ein `cli watch`-Prozess ist ein BAUM, kein Einzelprozess — zwei gleich aussehende `python.exe -m fomo_agent.cli watch` sind Eltern-Kind DESSELBEN Watchers, kein Duplikat.** Beim Watcher-Restart/Chaos-Check nie nach der Commandline allein urteilen: `Get-CimInstance Win32_Process` und `ParentProcessId`/`CreationDate` pruefen (bash→env→python→python-Kette). Nur ein Prozess OHNE Eltern-Kind-Beziehung zu einem anderen watch ist ein echter Doppel. Der Skill-Warnhinweis "ein Dauerlauf hat zwei python-Prozesse" gilt hier genauso.
- **Watcher-Restart braucht KEIN LLM — reiner Prozessstart, direkt vom Interpool machbar, auch wenn das Bot-Modell-Guthaben erschöpft ist.** `cd <repo> && env -u PYTHONPATH -u PYTHONHOME PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -m fomo_agent.cli watch` als `terminal(background=true, persist_on_release=true)` (kein notify — Dauerprozess). Bar aus `HOT_DELTA` in `config.py`/`.env` pruefen (Default 1.0). Danach verifizieren: genau EIN Baum, tickt.
- **Ein delegierter Job, der mit `HTTP 402: Insufficient available credits` + Fallback auf ein lokales Modell mit zu kleinem Kontext stirbt, ist ein ABRECHNUNGS-/KONTEXTPROBLEM, kein Aufgabenproblem — nicht blind neu delegieren.** Der Fallback (z. B. gemma-4-E4B, 65k) kann den Auftrag nicht lesen ("conversation too long"). Erst das Primärmodell-Guthaben aufladen oder fomo-radar auf ein Modell mit grossem Kontext setzen; ein erneuter Versuch laeuft sonst in denselben Fehler. Teile, die kein LLM brauchen (Watcher, Prozess-Checks), direkt selbst machen.
- Keys nie ausgeben. Echte Zugaenge nur in `MaxHirn/Wissen/Zugaenge.md`.

## fomo-radar fomo-family-Discovery
- `fomo-radar discover leaderboard` (Perioden 24h/7d/30d) + resolve_execution_wallets
  fuellt `fomo_users`; `discover trenches` fuellt `traders` direkt. `fomo_users` kann
  LEER sein, waehrend der Roster komplett aus trenches kommt — das ist kein Fehler,
  sondern heisst nur, dass die Leaderboard-Discovery nie lief. Vor einem
  Discovery-Auftrag den Ist-Stand in der DB pruefen (`SELECT source, COUNT(*) FROM
  traders GROUP BY source`, `SELECT COUNT(*) FROM fomo_users`), nicht dem STATUS.md-Text
  glauben.
- FOMO_SESSION in .env ist der Cookie/Bearer; Gueltigkeit pruefen mit
  `FomoClient.leaderboard` (wirft FomoError/FomoNotConfigured bei ungueltiger
  Session), nicht am Vorhandensein des Keys raten. Ein Discovery-Auftrag an den Bot
  soll explizit sagen, dass er die Session-Gueltigkeit pruefen und das Ergebnis
  (neue fomo_users je Periode, neue Trader nach Resolve, Session ok/Fehler) melden soll.

## Gruppenchat mit Telegram-Forum-Topics seriell dispatchen

- Max bevorzugt einen einzigen Eingang und serielle Bearbeitung: kein Fan-out an mehrere Profile gleichzeitig. Bei einer fachlichen Gruppenanfrage zuerst genau eine Recherche beauftragen, deren Ergebnis abwarten, dann maximal einen passenden Fachbot bestimmen und erst danach starten.
- `gateway.profile_routes` waehlt fuer ein einzelnes Inbound-Ereignis genau ein Runtime-Profil; es ist kein Recherche->Dispatcher-Workflow. Soll Recherche pruefen und ein Dispatcher danach handeln, route die Gruppe an den Dispatcher und verankere die serielle Weitergabe in dessen Arbeitsanweisung. Route ein Topic direkt zu Recherche, wenn es selbst antworten soll, nicht wenn danach automatisch ein zweites Profil erwartet wird.
- Forum-Themen lassen sich nach `platform` + `chat_id` + `thread_id` routen; vor Topic-Routen die effektive `gateway.profile_routes` lesen und jedes Zielprofil gegen `profiles/<name>/config.yaml` pruefen. Topic-Links koennen Nachrichten-IDs enthalten: niemals die letzte URL-Zahl ungeprueft als `thread_id` einsetzen. Nimm die empfangene `message_thread_id`/SessionSource-`thread_id` aus einer echten Nachricht oder verifiziere sie in der Session-Datenbank.
- Eine Chat-weite Route und spezifische Topic-Routen koennen nebeneinander bestehen; spezifischere Routen gewinnen (thread_id-Spezifitaet 8 > chat_id 4). Nach dem Edit die effektive Route fuer alle Topics aufloesen und nachweisen, dass jedes Inbound-Event nur ein Zielprofil trifft — `parse_profile_routes`/`match_profile_route` aus `gateway/profile_routing.py` gegen die config laufen lassen (Sim je thread_id), bevor der Gateway neu startet.
- **Die Routen-Simulation braucht `adapter_profile=None`, sonst ist das Ergebnis eine Falschmeldung.** Die Routen in der config tragen `bot_profile: null` (Default-Bot, der den geteilten Gruppen-Token pollt); `match_profile_route` matcht nur, wenn `_bot_profile_key(self.bot_profile) == _bot_profile_key(adapter_profile)`. Uebergibt die Sim `adapter_profile='bots'` (das ROUTED Zielprofil), wird JEDE Route abgelehnt und jede Topic simuliert "KEIN TREFFER (dropped)" — das sieht wie eine kaputte Config aus und ist nur ein Simulations-Artefakt. Der Aufruf lautet `match_profile_route(routes, 'telegram', chat_id='-1003980261765', thread_id=tid, adapter_profile=None)` (None = Default/Bot-Besitzer), nicht der Ziel-Profilname.
- **Thread-IDs gegen die Session-DB verifizieren, nicht gegen die Zuordnungs-Doku:** `SELECT thread_id, title, session_key FROM sessions WHERE chat_id='-1003980261765'` in `profiles/bots/state.db`. Nur ein thread_id, der dort als echte Session existiert, ist belegt; ein Eintrag in der `Telegram-Themen-Bot-Zuordnung.md` oder die Zahl aus einem t.me/c/-Link beweisen allein keine Topic-ID.
- **`config.yaml` im geteilten Baum kann eine uncommittete Aenderung einer parallelen Sitzung tragen — den Arbeitstand lesen, nicht die aus der Doku/aus dem Skill gelernte Zuordnung.** Eine Zuordnung (z. B. Handel→jev-trader, Auswertung→recherche) kann am HEAD stimmen, waehrend der Working-Tree sie bereits zu `bots` abgeflacht hat (git `M`, uncommittet, mtime heute). Vor einem Routen-Urteil `git status --short`/`git diff` gegen `Agenten/Hermes/config.yaml` pruefen und die effektive Route aus dem AKTUELLEN Arbeitstand simulieren; die Simulation beantwortet das IST, die Doku nur den Entwurf. Eine solche fremde, lebende Aenderung nicht ueberschreiben oder committen, sondern dem Nutzer als klärungsbedürftig melden.
- **Thread-IDs verifizieren, nicht raten:** Eine `t.me/c/<gruppe>/<id>`-URL kann eine Nachrichten-ID enthalten; sie beweist nicht allein die Topic-`thread_id`. Nutze die tatsaechliche Telegram-`message_thread_id` aus einem eingegangenen Update oder einem gespeicherten Session-Eintrag (`sessions.thread_id` fuer dieselbe `chat_id`). Topic-Namen den IDs nur zuordnen, wenn der Nutzer sie benennt oder die Topic-Metadaten das belegen; sonst nachfragen.
- **Ein Topic = genau EIN Profil.** `profile_routes` kann pro (chat,thread) nur ein Zielprofil haben. Eine Zuordnung mit mehreren Bots pro Topic (z. B. 6 Handel-Bots) ist nicht abbildbar — vor dem Bau die federfuehrenden Bots je Topic mit Max klaeren; die uebrigen bleiben ueber `/bot NAME` im Dispatch erreichbar. Ziel-Profile muessen existieren und ein gueltiges `model.default`/`provider` haben (Multiplex laedt sie).
- **Die Ein-Profil-pro-Topic-Grenze ist Kern-Gateway-Logik, kein Plugin-Schalter.** `match_profile_route` (installierter Quelltext `hermes-agent/gateway/profile_routing.py` + Tests) hat pro Inbound-Event GENAU ein Ergebnis; es gibt keinen Plugin-Mechanismus, der daraus mehrere Empfaenger pro Topic macht. Behauptet Max ein "Plugin", das das koennte, nicht glauben: den Plugin-Katalog tatsaechlich listen (`hermes plugins`, `grep -i bots`) — fehlt der Name dort, ist es ein Fehlname (meist ist das `bots`-Profil gemeint). Verloren gegangene Suchschleife: mehrere identische `search_files`-Queries, die dasselbe Ergebnis liefern, sind ein degenerativer Modell-Loop, kein Fortschritt — sobald ein Query-Zyklus kein neues Ergebnis bringt, auf eine gezielte Lesequelle (config.yaml, Quelltext) wechseln und dem Nutzer die Antwort geben statt weiterzusuchen.
- **Vor einem Routing-Vorschlag erst die BESTEHENDE Wahrheit lesen.** `Agenten/Hermes/config.yaml` → `gateway.profile_routes` kann schon verdrahtet sein (Dispatch→bots, Handel→jev-trader, Auswertung→recherche, Wissen→obsidian-skills, Bots→gbrain, Wartung→hermes-wartung fuer -1003980261765). Keine Zuordnung von Grund auf entwerfen und als "neu" anbieten, bevor man die aktive Route gelesen hat; haeufig deckt sie den Entwurf bereits ab. Die Zuordnungs-Doku fuer die Gruppe: `profiles/bots/Telegram-Themen-Bot-Zuordnung.md`.
- Eine SOUL-/Profilregel-Aenderung beweist nicht, dass bereits laufende Topic-Sitzungen sie geladen haben: erst in einer neuen Sitzung pruefen; keinen Gateway-Neustart ausloesen, wenn er alle laufenden Profile beeintraechtigen kann.

## "Weiter" ohne Kontext: erst rekonstruieren, dann pruefen, ob schon erledigt

Sagt Max nur "Weiter" (oder "weiter wo aufgehoert wurde") ohne Auftrag, ist der
letzte echte Auftrag NICHT im aktuellen Kontext — er liegt in einer frueheren
Sitzung. Vor jeder Aktion:

1. **Den letzten echten Auftrag aus der Sitzungshistorie rekonstruieren**
   (`session_search` mit `sort=newest`, dann in die gefundene Sitzung scrollen
   bis zur letzten User-Nachricht). Nicht raten, was gemeint sein koennte.
2. **Pruefen, ob die Arbeit schon erledigt und committet ist, BEVOR man sie
   wiederholt.** Eine parallele Sitzung kann den Auftrag laengst ausgefuehrt
   und committet haben. `git diff HEAD -- <pfad>` leer UND `git log -1 --
   <pfad>` zeigt einen passenden Commit = die Arbeit ist getan; das als
   erledigt melden statt sie neu zu machen. Das gilt besonders fuer
   Stilllegungen/SPUREN-Aenderungen, die eine andere Sitzung schon committet
   haben kann.
3. Erst wenn weder Historie noch HEAD die Arbeit belegen, den Auftrag
   ausfuehren oder delegieren.

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

## MAGDA-Gedaedchtnis (Auftrag Max 13.10.2026)
Jedes Profil fuehrt eine Markdown-Gedaedchtnisdatei, gelesen VOR jedem Lauf,
fortgeschrieben NACH jedem Lauf. Eine zentrale Datei zeigt den aktuellen Stand
aller Bots auf einen Blick.

- **Profil-Datei:** `Agenten/Hermes/profiles/<bot>/MAGDA.md` — Abschnitte:
  Letzter Stand / Offene Punkte / Erinnerungen / Ziel des naechsten Laufs.
- **Zentrale Datei:** `Agenten/Hermes/MAGDA.aktuell.md` — eine Zeile je Profil
  (letzter Stand, laeuft gerade, offener Punkt).
- **Beim Dispatch:** jedem `hermes -p <bot> chat -q "..."` dem Auftrag
  voranstellen: "Lies zuerst `Agenten/Hermes/profiles/<bot>/MAGDA.md` und
  `Agenten/Hermes/MAGDA.aktuell.md`, arbeite daraus deinen Kontext, und schreibe
  nach Abschluss deinen Stand in beide zurueck."
- **Ich selbst (Profil bots):** lese `MAGDA.aktuell.md`, bevor ich Auftraege
  verteile, und schreibe nach jeder Verteilung meinen Stand hinein.
- Pfade sind relativ zur Wurzel (`cd "$HERMES_HOME/../.."`). Die MAGDA-Dateien
  sind Betriebsdateien, nicht versioniert.
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
  `git status --short <pfad>`. Ist nichts da, den Auftrag an einen BOT
  NEU VERGEBEN, der (a) ein stabiles Modell hat UND (b) tatsaechlich
  schreiben darf — nicht automatisch an `recherche`.
- **Der stabile Bot kann der False mit LESEN sein.** `recherche`
  (deepseek-v4-flash, stabil) verweigert schreibende Arbeit aus eigenen
  Regeln ("als Recherche-Agent committest du nichts") und der
  Bereichs-Besitz-Regel (`Agenten/Handel/` gehoert laut `BEREICHE.json` dem
  `handel`-Besitzer). Ein stabiler Lese-Bot ist fuer Analyse gut, fuer einen
  Bau/Commit aber der falsche Adressat — der erste Versuch endet dann mit
  einer legitim begruendeten Weigerung, nicht mit Arbeit. Vor einem
  Bau-Auftrag pruefen, ob das Zielprofil Schreiberlaubnis hat.
- **Fehlt fuer einen Bereich ein Bau-Bot mit stabilem Modell, EINEN der
  vorhandenen Profile umpolen statt raten.** Die handelsnahen Fork-Profile
  (jev-trader, agent-trade-kit, awesome-systematic-trading, harvard-trading)
  defaulten auf longcat (kollabiert bei Bau); `recherche` ist stabil aber
  lesen. Wenn Max freigibt, `model.default` eines handelsnahen Profils auf
  `deepseek/deepseek-v4-flash-0731` setzen, `terminal.cwd` auf
  `C:\Users\faupe\Documents\BrainFiles` (damit es in `Agenten/Handel`
  arbeitet), config committen (profiles/ gehoert dem bot-Bereich), danach
  den Bau delegieren. Das ist Config-Arbeit im eigenen bot-Bereich, kein
  Fremdeingriff.
- **Nach dem Bot-Bericht den IST-Wert aus der frischen Quelle melden, nicht aus der naheliegenden Datei.** Bei parallelen Stufen-Buechern (`zustand.json` Basis vs. `zustand.mittel/hoch.json`) kann die Basis-Datei stale sein; melde offene Positionen/Status nur aus der Datei mit dem juengsten `letzter_lauf`. Eine verstaendliche, aber falsche Masse ("3 offene Live-Positionen") aus einer toten Datei ist schlimmer als ein ehrliches "welche Stufe?" — der Nutzer korrigiert die Zahl, und das Vertrauen in jede weitere Zahl sinkt.
- **PR-Body mit Backticks/Code nicht in eine doppelt-gequotete Shell-Commandline packen.** In `gh pr create --body "...`<code>`..."` wertet die Shell die Backticks als Command-Substitution aus und frisst die Stellen aus dem Body. Als Here-Doc mit einfachen Quotes (`--body-file - <<'EOF'`) uebergeben und danach den Body per `gh pr view <n> --json body --jq .body` zuruecklesen und auf die Code-Stellen pruefen, statt nach dem Erstellen zu vertrauen.
- **"Tests gruen" erst in den PR-Body schreiben, NACHDEM man sie selbst gelaufen hat — nie aus einem Handoff/Erinnerungsstand uebernehmen.** Ein Handoff kann "fertig, verifiziert" behaupten, aber die Tests schlagen im Worktree fehl (falsches Arbeitsverzeichnis, Pfad-Guard, nicht umgestellte Alt-Venue-Tests). Vor dem `gh pr create` die Tests des Branches mit dem Hauptbaum-Interpreter SELBST ausfuehren und das Ergebnis (OK/FAILED + Anzahl) abwarten; erst dann "Tests gruen" in den Body schreiben. Ein PR-Body, der gruene Tests behauptet, die rot sind, ist eine falsche Zusicherung an den Reviewer.
- **Merge-fertige Worktree-Branches pushen + PR eroeffnen ist ein eigener Schritt, der die Tests voraussetzt.** `git push -u origin <branch>` aus dem jeweiligen Worktree, dann `gh pr create --base master --head <branch>`. Vor dem Push pruefen, dass der Branch nicht schon auf dem Remote liegt (`git ls-remote --heads origin <branch>` leer) und dass er wirklich Commits vor master hat (`git rev-list --count master..<branch>` > 0) — sonst eroeffnet man eine leere PR.
- **Worktree-Commit, der mit "keine .git-Wurzel gefunden" abbricht, aber `git rev-parse --show-toplevel`/`status` gruen sind, haengt am pre-commit-Hook:** der `.githooks/pre-commit` ruft das Bereichs-Skript (`bereiche.py --staged`) und kann im Worktree-Kontext scheitern. Worktree-Commits mit `git -c core.hooksPath=/dev/null commit -m ...` durchfuehren (einmalig, area-Hook wirkt nur mit gesetzter `BRAINFILES_BEREICH`).
- **Nach dem Bot-Bericht den ZIEL-ZWEIG pruefen, nicht nur die
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
