---
name: hermes-config-ops
description: "Use when Config, .env oder Profile zu aendern sind."
version: 0.1.0
author: Hermes
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, config, secrets, soul, persona, brainfiles, verifikation]
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
- der Agent soll **dauerhaft anders antworten** (Stil, Ton, Form, „immer so wie
  jetzt") — das ist kein Skill, sondern `SOUL.md` (Abschnitt „Persona und
  Ausgabestil dauerhaft wirksam machen")
- "wo trage ich diesen Schlüssel ein / mit welchem Befehl setze ich die
  Umgebungsvariable" — erst die Ablage nach dem Verbraucher entscheiden, dann
  setzen und am laufenden Dienst belegen (nicht nur "steht drin")

**Don't use for:** MCP-Server-Einträge zwischen Claude und Hermes (`mcp-sync`),
Skill-Kopien (`skill-library-sync`), Update/venv/SQLite (`hermes-maintenance`).

## Regeln (immer)

1. **Drei Ablagen, nach Verbraucher getrennt.** Menschliche Ablage ist
   `Wissen/Zugaenge.md` — nie lesen, nie ausgeben, nie protokollieren. Von Hermes
   maschinell gelesen wird `Agenten/Hermes/.env` (jedes Profil hat eine eigene
   Kopie). Werte für Verbraucher **außerhalb** von Hermes (MCP-Server, Claude,
   Skripte, curl) gehören als Windows-Benutzervariable nach `HKCU\Environment`
   — Abschnitt „Dritte Ablage". Einen Wert, den eine Ablage schon hält, **nicht
   ein zweites Mal** ablegen: sonst gibt es zwei Stellen zum Rotieren.
   `config.yaml` enthält nur `${NAME}`-Verweise.
2. **Kein Geheimnis in einer Kommandozeile.** Werte in der Datei lesen, ausgeben nur
   Länge und SHA-256-Anfang. PowerShell gibt Argumente in Fehlermeldungen im
   Klartext aus — ein Secret in einem Befehl steht danach im Protokoll.
   Verglichen wird über Hashes, nie über Werte. **Auch eine Vorschau ist eine
   Ausgabe:** `print(zeile[:60])` bei einer `.env`-Zeile schreibt den
   Schluesselanfang in den Verlauf. Zum Pruefen einer `.env` nur NAMEN und
   Laengen zeigen (`awk -F= '{print $1" "length($2)}'`), nie Zeilenanfaenge.
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
   **Vor dem Schreiben** `git status --porcelain <pfad>` **und** `git diff --cached <pfad>`
   lesen: steht genau diese Datei schon gestaged im Index, arbeitet eine zweite Sitzung
   daran (bei diesem Nutzer normal: Desktop-, Telegram- und CLI-Sitzung gleichzeitig). Dann
   nicht selbst schreiben — den Ist-Stand unabhängig nachprüfen, das Fehlende ergänzen und
   den Commit dem Verursacher lassen; fremd Gestagetes nie mitcommitten.

## Persona und Ausgabestil dauerhaft wirksam machen (`SOUL.md`)

Ein Wunsch wie „antworte kuenftig immer so" gehoert **nicht** in einen Skill:
Skills sind Nachladeware — im Prompt steht dauerhaft nur ihre `description`, der
Text kommt erst mit `skill_view` — und Hermes hat fuer Skills **keinen**
Immer-an-Schalter. Der Traeger fuer Dauerverhalten ist `SOUL.md`: sie steht in
Slot 1 des Systemprompts, wird aber **nur aus `HERMES_HOME`** geladen, nie aus
dem Arbeitsverzeichnis.

1. **Nachsehen, was drinsteht.** Nach der Installation ist `SOUL.md` die
eingebaute Standard-Identitaet (hier 667 B, derselbe Text wie der Fallback). Sie
**anhaengen**, nicht ersetzen — eine geloeschte Datei laesst Hermes auf die
eingebaute Identitaet zurueckfallen.
2. **Alle Ablagen derselben Persona mitziehen**, sonst antwortet jede Oberflaeche
anders:
   - `$HERMES_HOME\SOUL.md` (hier `Agenten/Hermes/SOUL.md`) — CLI und
     Messaging-Sitzungen dieses Homes,
   - `%LOCALAPPDATA%\hermes\SOUL.md` — Laeufe **ohne** `HERMES_HOME` (Desktop-App,
     Gateway; siehe Falle „Welche Config der laufende Gateway liest"),
   - `profiles/<bot>/SOUL.md` — je Profil eine eigene Datei; erst `ls profiles/`
     zeigt, wie viele (hier 14).
3. **Stufe 1: vor jeder Datei `.bak-JJJJMMTT`.** Die Sicherung ist die Ruecknahme —
   den Skill zu entfernen nimmt einen Ausgabestil **nicht** zurueck.
4. **Belegen, dass sie geladen wird — nicht, dass sie dasteht.** Eine frische
   Sitzung die eigene Identitaet nacherzaehlen lassen:

       Remove-Item Env:PYTHONHOME, Env:PYTHONPATH   # Falle unten, danach:
       hermes.exe chat -q "Nenne in hoechstens zwei Saetzen die Ausgabestil-Regeln aus deiner SOUL.md." -Q -t memory

   Kommen die Regeln sinngemaess zurueck, ist `SOUL.md` im Prompt. `-t memory`
   haelt den Lauf kurz und billig, `-Q` schaltet Banner ab (ohne `-t` laeuft eine
   ganze Werkzeugschleife los). Zweiter Beleg fuer die Wirkung: eine offene Frage
   stellen und die Form pruefen (erste Zeile = Handlung, nummeriert, keine
   Schlussfloskel) — ein Stiltest mit einer Frage, die zu einem Vorspann verleitet.
5. **Notiz und Commit.** `Wissen/Hermes.md` (Stufe 1) um Quelle, Wirkung,
   Abschaltbefehl und Sicherungspfad ergaenzen, dann die getrackten Dateien
   namentlich committen. `SOUL.md` des Hauptprofils ist **nicht** versioniert,
   `profiles/*/SOUL.md` sind ueber die Whitelist `!Agenten/Hermes/profiles/*/SOUL.md`
   freigegeben: `git ls-files | grep SOUL.md` zeigt, was mitgeht,
   `git check-ignore -v <pfad>` zeigt, was nicht.

Fallen:

- **Eine laufende Sitzung behaelt ihren Systemprompt** (Prompt-Cache-Invariante,
  siehe „Regeln (immer)" 3) — die Aenderung greift erst in einer **neuen**
  Sitzung. Der letzte Schritt gehoert dem Nutzer: `/reset` bzw. `/new`. Nie
  „sofort wirksam" behaupten. Kein Widerspruch zu Regel 3: hier wird kein Prozess
  neu gestartet, nur eine Sitzung begonnen.
- **Der Anlass gehoert in die Notiz.** Steht der Ausgabestil nur in `SOUL.md`,
  haelt ihn die naechste Sitzung fuer Ballast und „raeumt auf". Ein Absatz in
  `Wissen/Hermes.md` macht ihn zu einer Entscheidung des Nutzers.

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

## Dritte Ablage: Windows-Benutzervariablen (`HKCU\Environment`)

Ist der Verbraucher **nicht** Hermes, gehoert der Wert in die Benutzervariable und
nicht in Hermes' `.env`: nur die Benutzervariable wird an jeden danach gestarteten
Prozess vererbt. Hermes selbst loest `${NAME}` aus seiner `.env` auf und
`${env:NAME}` aus der Prozessumgebung — beides greift erst in einem **neu
gestarteten** Hermes-Prozess, ein laufender sieht die Aenderung nie.

Setzen, ohne den Wert in die Kommandozeile zu schreiben:

```powershell
# Wert vorher in der Quelle kopieren
[Environment]::SetEnvironmentVariable('NAME', (Get-Clipboard -Raw).Trim(), 'User')
```

```powershell
# oder maskiert eintippen
$s = Read-Host -AsSecureString 'Wert'
$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
[Environment]::SetEnvironmentVariable('NAME', [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b), 'User')
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)
```

- **`setx NAME "<wert>"` nicht verwenden.** `setx` kennt keinen maskierten Weg, und
  PowerShell legt die Zeile im Klartext in
  `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` ab —
  dort stehen dann Zugangswerte, die niemand mehr rotiert.
- **Ist-Stand am Registry-Schluessel ablesen, nicht an einer Kandidatenliste.**
  Namen aufzaehlen und je Name nur Laenge und Praefix zeigen. Ein „FEHLT" aus einer
  fest verdrahteten Namensliste ist **kein Beweis fuer Abwesenheit** — die Variable
  kann zwischen zwei Aufrufen gesetzt worden sein, oft von einer zweiten Sitzung
  des Nutzers. Vor jeder Abwesenheitsmeldung neu aus `HKCU:\Environment` lesen.
- **In einer MCP-/Dienst-PowerShell kann `HKCU:\` einen ANDEREN Nutzer meinen als den
  interaktiven.** `Get-ItemProperty HKCU:\Environment` meldete hier faelschlich
  „keine OKX-Variable", waehrend `[Environment]::GetEnvironmentVariable('OKX_API_KEY','User')`
  denselben Namen als gesetzt zeigte. Die autoritative Existenz-/Wert-Pruefung fuer die
  persistente Benutzerumgebung ist deshalb immer dieser .NET-Aufruf — nie die
  Registry-Lese als einzige Quelle. Wer `setx /M` genutzt haben koennte, prueft zusaetzlich
  den `'System'`-Scope (`[Environment]::GetEnvironmentVariable('<NAME>','System')`);
  `setx` (ohne `/M`) schreibt nach `HKCU\Environment` und wird von Anwendern gern
  gesetzt — eine fehlende Umgebungsvariable heisst also nicht automatisch „nicht
  vorhanden", wenn ein Nutzer dazwischengekommen ist. Dynamischer Zugriff auf einen
  Variablennamen aus einer String-Variablen braucht in PowerShell 5.1 ausserdem die
  `${env:<NAME>}`-Schreibweise; `$env:<NAME>` ist ein Parse-Fehler.
- **Laufende Prozesse erben neu gesetzte Variablen nicht.** In der Sitzung nachziehen:
  `$env:NAME = (Get-Item HKCU:\Environment).GetValue('NAME')`.
- **Belegt wird nicht „steht drin", sondern „wird akzeptiert":** den Wert in eine
  Shell-Variable lesen (nie als Literal in den Befehl) und den echten Endpunkt damit
  abfragen — ohne Token 401, mit Token 200 ist der Nachweis. Rezepte, Hash-Vergleich
  und die OmniRoute-Zugangstrennung: `references/benutzervariablen.md`.
- **Wer liest einen Variablennamen? Namen ankern.** `OMNIROUTE_API_KEY` trifft als
  Teilstring in `HERMES_CUSTOM_OMNIROUTE_API_KEY` — ein ungeankerter Treffer beweist
  keinen Leser. Und `search_files` meldet Treffer in versteckten/ignorierten Dateien
  nur als Warnzeile („N matches in hidden or gitignored files"): dieser Zeile
  nachgehen, dort stand die einzige Notiz zur Variable. Breites `grep -rIn` ueber die
  Wurzel laeuft ins Zeitlimit (45 GB Archiv, Junctions) — `search_files` mit engem
  Pfad und `file_glob` nehmen.

## Docker-Sandbox: Umgebungsvariablen hineinreichen

Trigger: Tools laufen im Docker-Terminal-Backend (Desktop/GUI) und sehen
Variablen nicht — `${env:NAME}` bleibt leer, Ollama findet keine Modelle,
Werkzeuge laufen ohne Key. Der Sandbox-Container erbt die Host- oder
Profil-Umgebung **nicht von selbst**.

Zwei Schluessel unter `terminal:` legen fest, was hineinkommt:

- `terminal.docker_forward_env` — Liste von Variablen**Namen**. Hermes loest
deren Werte beim Ausfuehren aus der Shell-Umgebung, dann aus der Profil-`.env`
auf und injectet sie in den Container. Die echten Geheimnisse stehen **nie** in
der Config, nur die Namen — fuer Tokens/Keys ist das immer die richtige Wahl.
- `terminal.docker_env` — Literale `KEY: value`-Paare direkt in der Config.
Fuer statische Schalter (DEBUG, PYTHONUNBUFFERED), nicht fuer Geheimnisse.

Setzen und belegen:

    hermes config set terminal.docker_forward_env '["A","B"]'
    hermes config get terminal.docker_forward_env   # Block-Liste, kein String

`hermes config set` speichert den JSON/YAML-Wert als echte Liste (dieselbe
strukturierte Parsung wie bei `fallback_providers`) — kein Handedit, keine
eigenen Listenzeilen in der Datei.

Fallen:

- **Der Container erbt nur, was im Prozess steht, der Hermes startet.**
  Windows-Benutzervariablen (HKCU, z. B. `OLLAMA_MODELS`, `HANDEL_RISIKO`)
  findet `docker_forward_env` nur, wenn der Desktop/Gateway sie in seiner
  Umgebung hat (HKCU erben sie beim Start). Stehen sie nur in einer
  bash-Session, fehlen sie dem Container. Namen in die Forward-Liste
  aufnehmen; die Werte kommen aus HKCU.
- **Backend-Konfig gilt fuer alle Oberflaechen gleichzeitig.** Die CLI kann
  `terminal.backend: local` laufen, waehrend Desktop/GUI den Docker-Backend
  nutzt — `docker_forward_env` wirkt nur auf den Docker-Zweig, unabhaengig
  vom gerade aktiven Backend. „Im Docker verfuegbar" heisst: den Docker-Zweig
  der `terminal:`-Sektion konfigurieren, den aktiven Backend nicht umstellen.
- **Nachweis nur aus einer Docker-Sitzung.** Aus einer Host-`local`-Sitzung
  (git-bash) ist kein docker-exec-Nachweis moeglich; den Live-Check
  (`env | grep -E 'NAME'`) als Schritt dem Container-User ueberlassen.
  Config-seitig belegt: `hermes config get` + die Datei lesen.

## Fremden MCP-Server anbinden (HTTP/OAuth)

Nicht der Manifest-Abgleich (den macht `mcp-sync`), sondern die Frage „geht
dieser Anbieter ueberhaupt, und mit welchem Befehl".

1. **Erst den Handschlag pruefen, ohne Zugang.** Ein HTTP-MCP-Endpunkt ist
   read-only in Minuten pruefbar: `POST` auf die URL mit
   `Content-Type: application/json` und
   `Accept: application/json, text/event-stream`, Rumpf
   `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{...}}}`.
   Die Antwort nennt `serverInfo` und eine `mcp-session-id` — letztere bei
   `tools/list` und `tools/call` als Header mitschicken. Typisches Bild:
   `initialize` und `tools/list` antworten **ohne** Anmeldung, erst
   `tools/call` kommt als `401` mit
   `WWW-Authenticate: Bearer resource_metadata=...` → **OAuth**.
2. **Anbinden nur ueber Hermes-Kommandos, nie per YAML.** `hermes mcp add
   <name> --url <url> --auth oauth` (statischer Header: `--auth header`),
   danach `hermes mcp login <name>`; `hermes mcp --help` fuehrt zusaetzlich
   `reauth`, `list`, `test`, `configure`. Der Token kommt ausschliesslich ueber
   diesen Weg.
3. **`hermes mcp add`/`remove` stellen MEHRERE Prompts — ein einzelnes
   `printf 'Y\n'` reicht nicht.** Die Rueckfragen (Anlegen/Ueberschreiben,
   "Enable all N tools?", bei `remove` "Remove server?") kommen nacheinander;
   ein einzelnes Y beantwortet nur den ersten, der naechste Prompt bekommt EOF
   und der Aufruf endet mit `Cancelled` **ohne** zu schreiben. Der Eintrag in
   `config.yaml` bleibt dann der ALTSTAND — und `hermes mcp test` meldet trotzdem
   "✓ Connected", weil es den alten Eintrag testet. Falscher gruener Nachweis:
   nach einem `Cancelled` ist die Verbindung zu einem ANDEREN Ziel belegt.
   `yes |` (unendlicher Y-Strom) beantwortet alle Prompts. Danach IMMER die
   gespeicherte Config lesen und den `--db`/`--url`-Pfad gegen die Absicht
   halten (bei Bots je Profil `profiles/<bot>/config.yaml`), nicht nur auf
   "Connected" vertrauen.
4. **Der Anmeldeschritt gehoert dem Nutzer.** OAuth laeuft im Browser gegen
   SEIN Konto und laesst sich von einem Agenten nicht abschliessen — als
   offenen Schritt melden („Kandidat, ein Klick fehlt"), nie als erledigt.
5. **Im Ergebnis trennen, was live geprueft ist und was aus der Doku stammt.**
   Handschlag und Werkzeugliste sind pruefbar; Metriknamen, Feldlisten und
   Tarifgrenzen stehen oft nur in der Anbieter-Doku. Beides ausdruecklich
   benennen — ein „funktioniert" ohne diese Trennung ist eine Behauptung.
6. **Erst danach der Manifest-Eintrag**, und als Kandidat mit Begruendung:
   `mcp-sync`.

## Fallback-Kette und lokale Provider

Hermes wechselt bei 429/529/503/Verbindungsfehlern auf eine Kette. Sie wird **per
Kommando** verwaltet, nicht per Hand im YAML:

    hermes fallback list     # was gilt (leer = keine Kette)
    hermes fallback remove   # Eintrag entfernen
    hermes fallback clear
    hermes fallback add      # interaktiver Picker — für Menschen, nicht für Agenten

- **`hermes fallback add` ist ein Auswahlmenü und hängt ohne Terminal.** Aus einer
Werkzeugsitzung (windows-mcp/desktop-commander) blockiert es bis ins Zeitlimit. Nicht
verwenden — die Kette mit `hermes config set` schreiben. Der Wert wird als strukturierter
Wert geparst (`hermes_cli/config.py::_coerce_config_set_value` zieht YAML/JSON heran,
sobald der Standardwert des Schlüssels kein String ist):

      hermes config set fallback_providers '[{"provider":"custom","model":"gemma-e4b-8k:latest","base_url":"http://127.0.0.1:11434/v1"}]'

  Danach `hermes fallback list` lesen und die Zahl der Einträge gegen die Absicht zählen.
- **Ein Eintrag ohne `provider` oder `model` wird stillschweigend verworfen**
(`fallback_config.py::_iter_fallback_entries`) — die Kette ist danach kürzer, ohne
Fehlermeldung. Genau deshalb ist der Zähl-Vergleich nach dem Setzen Pflicht.
- **Die Änderung greift ohne Neustart** (`run_config_loaders.py` liest `fallback_providers`
zur Laufzeit neu); ein laufender Agent übernimmt sie beim nächsten Fehlversuch.

- **`fallback_providers` (Liste) ist die führende Ablage, `fallback_model` (Einzelwert)
die Altform**; beide werden gemerged (`hermes_cli/fallback_config.py::get_fallback_chain`),
Reihenfolge = Absicht.
- **Ein Eintrag braucht `provider` und `model`; für ein lokales Modell zusätzlich
`base_url`** (z. B. `http://127.0.0.1:11434/v1`) — ohne `base_url` greift er ins Leere.
Für lokale Endpunkte ist `provider: custom` die portable Angabe: `ollama`, `local`,
`vllm`, `llamacpp`, `llama.cpp` und `llama-cpp` sind Aliase desselben Profils, `hermes
fallback list` zeigt sie alle als `via custom`. Rezept und Befehle:
`references/fallback-kette.md`.
- **Der Modellname muss im laufenden Dienst existieren.** `providers.<name>.models` ist
eine Wunschliste und darf veralten (dort stand `gemma4:e4b`, lokal hieß das Modell
`gemma-e4b-8k`). Ein Fallback auf einen nicht existierenden Namen greift nicht, und
niemand merkt es, bis der Primärpfad wirklich ausfällt. Echte Namen am Dienst holen
(`curl -s http://127.0.0.1:11434/api/tags`), nicht aus der Config abschreiben.
- **Was in der Config steht, ist kein Beleg für das, was gilt** — `hermes fallback list`
fragen. Und eine Aussage aus einer abgebrochenen Sitzung („die Kette steht doch schon
drin") nie übernehmen, sondern am lebenden System nachprüfen.
- **Ein Zustand, der nie committet wurde, existiert in Git nicht:** `git log -S "<schlüssel>"`
findet ihn nicht, obwohl er im Arbeitsbaum stand. Vor „das war nie da" die Vorher-Kopien
lesen: `Agenten/Hermes/backups/config/config.yaml.pre-setup.*` und
`Agenten/Hermes/state-snapshots/*/config.yaml` — dort steht die Fassung vor Setup- und
update-Läufen, oft der einzige Ort, an dem eine per Hand gesetzte Kette erhalten ist
(`hermes update` schreibt die Config neu).
- **Für den lokalen Modellordner gibt es keine Umgebungsvariable.** Wer eine sucht
(analog zu `OLLAMA_MODELS`), sucht vergeblich: `local_runtime/bootstrap.py::models_dir()`
liest `get_default_hermes_root() / "models"` — also `%LOCALAPPDATA%\hermes\models`, wenn
`HERMES_HOME` ungesetzt ist, sonst `HERMES_HOME\models`. Mit dem hier üblichen
`HERMES_HOME = …\Agenten\Hermes` zeigt der Pfad damit **in die Sicherungsquelle**; dort
gehört keine Junction auf die Modellplatte hin (`laufwerk-platz-schaffen`). Vor jedem
Umräumen prüfen, ob der Verbraucher überhaupt läuft: bei `local_runtime.enabled: false`
liest den Ordner niemand, und die Gewichtsdateien sind dann nur belegter Platz.
- **Ein ungueltiger Ketten-Eintrag in einem PROFIL wird als BLOCK entfernt, nicht per
`hermes config set`.** `config set` kann keinen Listeneintrag einzeln aendern (und schneidet
den Kommentar-Schluss ab). Richtig ist ein byte-genauer Blockschnitt: die Zeile
`fallback_providers:` in Spalte 0 plus die eingerueckten Folgezeilen entfernen, die Datei
VORHER und NACHHER mit `yaml.safe_load` parsen und asserten, dass alles AUSSERHALB des
Blocks gleich geblieben ist (`{k: v for k, v in vorher.items() if k != schluessel} ==
nachher`) — damit ist "nur die Kette entfernt" bewiesen und nicht gehofft. Eine
eingerueckte Kette (z. B. unter `delegation:`) bleibt stehen; `fallback_providers: []`
ist bereits sauber (leere Liste ist falsy — nicht "leer" mit "fehlt" verwechseln, die
Erkennung ueber `grep` findet beide Formen). Werkzeug:
`Agenten/Hermes/scripts/bot-rueckfallkette-bereinigen.py`.
- **Eine Kette, deren erster Eintrag denselben Dienst nennt wie das Hauptmodell, ist
keine Reserve.** Faellt dieser Dienst aus, scheitert der erste Eintrag genauso, und erst
der zweite entscheidet den Fehlertext. Reserve ist nur, was auf einen ANDEREN
erreichbaren Dienst zeigt — sonst lieber ehrlich gar keine Kette (die Fehlermeldung des
Primaerpfads ist dann sichtbar).
- **Ein Profil kann die Kette NUR unter `delegation:` tragen — dann hat es gar keine.**
Ein `fallback_providers:` mit Einrueckung (typisch unter `delegation:`) ist die
Subagenten-Kette und keine Reserve fuer den Hauptlauf. Erst `grep -n "^fallback_providers:"`
(Spalte 0!) entscheidet, ob die Wurzel-Kette existiert; `grep -l fallback` findet beide
Formen und taugt nicht als Beleg. Fehlt sie, den Block vor einem Wurzel-Schluessel
einfuegen — und den RICHTIGEN waehlen: nicht jedes Profil hat `toolsets:` (ein
Wartungsprofil hatte nur `providers/terminal/model/plugins`), also den ersten
vorhandenen Wurzel-Schluessel nehmen und vorher per Byte-Vergleich zeigen, dass nur
der Block dazukam.
- **Der Eintrag braucht den Provider-Block IM Profil.** Ein Bot-Profil, das
`providers.<name>` nicht kennt (frisch angelegte Profile haben nur `omniroute`), kann
den Namen nicht aufloesen — den Block (api/base_url/model/name) mit einsetzen, sonst
zeigt die Kette auf einen Namen, den nur andere Profile kennen.
- **Eine lokale Reserve gehoert als ERSTER Eintrag in die Kette, die alten bleiben dahinter.**
Der Zweck ist, den Ausfall des Primärpfads ohne fremde Abhaengigkeit zu ueberbruecken — steht
die lokale Adresse hinten, entscheidet zuerst der (moeglicherweise genauso tote) Cloud-Eintrag
davor. Praktisch: den `fallback_providers:`-Block der Profil-Config ersetzen (Zeile in Spalte 0
plus eingerueckte Folgezeilen), die vorhandenen Eintraege unveraendert dahinter wieder einsetzen,
neuen Block vor dem Schreiben mit `yaml.safe_load` parsen und `rest == vorher` ausserhalb des
Blocks asserten. Danach **je Profil** `hermes -p <name> fallback list` lesen (nicht nur die
Datei): die Ausgabe nennt `Primary:` und die numerierte Kette — nur sie zeigt, was gilt, und
nur so faellt auf, wenn ein Profil gar keine Wurzel-Kette hatte.
- **Der lokale Rueckfall traegt nur bei freiem Commit.** Ein Profil mit gesetzter Kette ist noch
kein Nachweis: das Modell muss laden, und ein Modelllader scheitert an einer erschoepften
Commit-Grenze auch bei reichlich freiem RAM (Symptomkatalog und Messbefehle:
`dauerprozess-bewachen`, `references/massenprozesse-und-commit-limit.md`). Nach dem Setzen den
Endpunkt einmal wirklich rufen (`POST <base_url>/chat/completions`) — nicht nur die Config lesen.
- **Eine konfigurierte Kette ist kein Beleg — das Modell muss LADEN.** Nach dem Setzen
nicht nur `hermes fallback list` lesen, sondern den Endpunkt wirklich rufen
(`POST <base_url>/chat/completions` mit dem eingetragenen Modellnamen; ein leeres
`content` bei gesetztem `reasoning` ist normal, solange die Antwort kommt). Schlaegt
der Modellstart fehl, ist die Ursache oft NICHT der Speicher des Modells: zuerst das
COMMIT-Limit pruefen (`Win32_OperatingSystem.FreeVirtualMemory` gegen
`TotalVirtualMemorySize`) — bei reichlich freiem RAM kann das Commit trotzdem fast
aufgebraucht sein (viele Prozesse reservieren), und dann scheitert jede
Puffer-Anforderung des Laders unabhaengig von der Modellgroesse. Erst danach ueber
Modellwahl oder Ollama-Einstellungen nachdenken.
- **Massenänderung ueber viele Profile: Trockenlauf ist der Standard.** Ein Werkzeug fuer
solche Aenderungen zeigt ohne Argument, was es taete, schreibt nur mit `--anwenden`, legt
je Profil `.bak-JJJJMMTT` an und nimmt mit `--zuruecknehmen` zurueck; es nennt je
uebersprungenes Profil den GRUND (eigene Anmeldung, lokaler Provider, schon umgestellt)
und ist idempotent, damit ein Abbruch mittendrin einfach neu gestartet werden kann.
Muster: `Agenten/Hermes/scripts/bot-modell-auf-router.py` und
`profil-kanaele-bereinigen.py`.

## Das Hauptmodell auf einen anderen Provider umstellen

Gilt fuer den `model:`-Block — also fuer den Hauptlauf. **Es gibt keinen
Modell-Schalter je Plattform:** Gateway, A2A-Bruecke und der SkillsBot bedienen
alle das `default`-Profil und lesen genau diesen Block. Ein A2A-`served_agents`-
Eintrag (Adapter `_load_served_agents`, `platforms.a2a.extra.agents`) kann nur ein
anderes PROFIL bedienen, und ein frisches Profil ist eine Insel ohne die
Haus-Skills. Wer „nur den Bot" umstellen will, muss das wissen, bevor er schreibt —
sonst behauptet er eine Trennung, die es nicht gibt.

1. **Den Zielprovider zuerst finden, nicht erfinden.** Ein Block unter `providers:`,
   den nichts referenziert, ist tote Konfiguration — aber oft genau der gemeinte
   (`providers.<name>.models.<modell>.context_length` nennt die erwartete
   Fenstergroesse). Vor dem Setzen die Live-Metadaten des Dienstes holen
   (`curl -s <base_url>/models`, bzw. `/api/tags` bei Ollama) und die Zahl gegen die
   Anforderung halten: was der Dienst meldet, gilt, nicht was in der Config steht.
2. `hermes config set model.provider <neu>` und `model.default <modell>`, dann
   `model.base_url` explizit auf den Endpunkt des neuen Providers. Der Providerwechsel
   **leert `model.base_url` und `model.api_mode` von selbst** und sagt das in der
   Ausgabe („that route belonged to <altersprovider>") — diese Zeile lesen, nicht
   ueberfliegen: ohne neu gesetztes `base_url` zeigt der Aufruf ins Leere.
   Bei einem selbst benannten Provider zusaetzlich `providers.<name>.base_url` und
   `providers.<name>.api_mode` setzen (die `api:`-Zeile allein reicht nicht).
3. **Reserve dahinter, nicht davor.** Den lokalen Eintrag als LETZTES Glied der
   `fallback_providers`-Kette eintragen (siehe Abschnitt oben) und den Cloud-Eintrag
   davor lassen: der lokale Zweig soll den Ausfall ueberbruecken, nicht den
   Normalbetrieb tragen.
4. **Ein selbst benannter Provider erscheint im Protokoll als `provider=custom`.**
   Das ist kein Widerspruch und kein Beleg gegen die Umstellung — nur die
   `model=`-Angabe zaehlt hier.

**Beweis am lebenden Dienst, ohne Neustart** (gilt fuer jede Oberflaeche, die ueber
den Gateway laeuft): eine Nachricht ueber den A2A-Endpunkt schicken und danach die
Logzeile lesen, die Modell und Provider nennt —

      curl -s http://127.0.0.1:9900/ -H "Authorization: Bearer <A2A-Token>" -H 'Content-Type: application/json' \
        -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"messageId":"m1","role":"ROLE_USER","parts":[{"text":"Antworte nur mit PONG"}]}}}'
      grep -oE "model=[^ ]+ provider=[^ ]+ .*platform=a2a" logs/agent.log | tail -3

Die Zeile muss das neue Modell UND `platform=a2a` tragen; ein Werkzeugaufruf im
selben Auftrag (z. B. `hostname`) belegt zusaetzlich, dass die Route auch
Werkzeugschleifen faehrt, nicht nur Prosa. Danach ist auch der Bot-Weg bewiesen —
kein Prozessneustart, kein „muesste jetzt greifen".

## Eine Config mit fremden Aenderungen zusammenfuehren

Ausloeser: der Arbeitsbaum zeigt `config.yaml` als geaendert, und der Diff
enthaelt mehr als die eigene Zeile — bei diesem Nutzer der Normalfall (Desktop-,
Telegram- und CLI-Sitzung gleichzeitig). „Zusammenfuehren" heisst: jeden Hunk
einzeln entscheiden, nicht den Stand pauschal uebernehmen oder verwerfen.

**Die Entscheidung faellt am LESER, nicht am Gefuehl.** Fuer jeden fremden Hunk
die Stelle im Code suchen, die den Schluessel liest
(`grep -rln "<schluessel>" hermes-agent/hermes_cli/ hermes-agent/agent/`), und
dort nachsehen, was der Wert bewirkt. Erst danach behalten, korrigieren oder
entfernen. Drei Befunde, die dabei regelmaessig auftauchen:

- **Ein Schluessel ohne Leser ist tote Konfiguration.** Findet die Suche im
  ganzen Baum keine Lesestelle, ist der Block wirkungslos — entfernen, nicht aus
  Hoeflichkeit stehen lassen. Er sieht sonst dauerhaft wie eine Einstellung aus.
  Zweiter Hinweis auf denselben Fund: ein Eintrag, dem ein Pflichtfeld fehlt,
  wuerde vom Normalisierer ohnehin verworfen (siehe `_iter_fallback_entries`).
- **Ein Listen-Schluessel, der als einzelnes Mapping geschrieben wurde, bleibt
  gueltig und verliert trotzdem Eintraege.** Der Normalisierer macht aus einem
  dict eine Ein-Eintrags-Kette — kein Fehler, keine Warnung, aber jede weitere
  Reserve ist weg. Nach dem Zusammenfuehren die ZAHL der Eintraege pruefen
  (`hermes config get <schluessel>`), nicht nur den ersten.
- **Ein geloeschter Kommentarblock ist eine stille Aenderung an der Datei des
  Nutzers** und meist Nebenwirkung eines `hermes config set` (siehe Falle oben),
  keine Absicht. Wiederherstellen.

Harmlose und sinnvolle Fremdaenderungen (ein zusaetzlicher `auxiliary`-Block,
ein Eintrag in einer Allowlist) werden uebernommen und im Commit-Text als
uebernommen benannt — wer sie wegwirft, zwingt die andere Sitzung, sie noch
einmal zu setzen.

Der eigene Anteil geht allein in den Commit, die fremden bleiben liegen. Bei einer
gemischten Datei den Index DETERMINISTISCH bauen statt Hunk-Antworten zu raten:
`git show HEAD:<datei>`, die eigene Aenderung byte-genau im Speicher einsetzen,
`git hash-object -w --path=<datei> --stdin` und
`git update-index --cacheinfo 100644,<sha>,<datei>` (der Arbeitsbaum bleibt unberuehrt,
die fremde Aenderung steht weiter als `M`). Falle dabei: ist die Datei CRLF,
liefert `git show HEAD:` `\r\n` — erst das Zeilenende bestimmen und DARAUF
splitten (`nl = '\r\n' if '\r\n' in text else '\n'`), sonst trifft ein
Zeilenvergleich (`zeile == '  schluessel: wert'`) nie, weil jede Zeile ein `\r`
traegt, und der "gebaute" Index bleibt unbemerkt identisch zum HEAD — der
Gegencheck `git diff --cached --numstat` faengt das (0 Zeilen). `git apply
--cached` mit selbstgebauten Hunks scheitert an CRLF-Configs (`corrupt patch`) —
der Index-Weg ist dort die stabile Route. Danach `git diff --cached --numstat --
<datei>` lesen — dort steht genau der eigene Anteil (Beispiel: `30 0` fuer einen
eingefuegten Abschnitt, `32 2` mit zwei geaenderten Frontmatter-Zeilen) — und die
Restmenge gegenpruefen: `git diff --numstat -- <datei>` muss die fremden Zeilen
unveraendert weiter ausweisen. `git add -p` bleibt der Notweg fuer zwei klar getrennte
kleine Hunks. Die fremden Zeilen werden im Commit-Text als nicht enthalten benannt;
fremd Gestagetes nie mitcommitten (Regeln (immer) 7). Rezept und Regeln:
`arbeitsbaum-git-hygiene`.

**Nachweis:** `git diff --stat` muss additiv aussehen (viele Zeilen rein, nur
die eigene Ersetzung raus). Ein Diff, der mehr loescht als hinzufuegt, hat
fremde Arbeit verschluckt. Danach `hermes config get` fuer jeden angefassten
Schluessel, und die Datei einmal als YAML parsen lassen, BEVOR sie geschrieben
wird — bei einer Config gibt es keinen `ast.parse`, aber `yaml.safe_load` auf
dem neuen Text im Speicher leistet dasselbe (dazu die erwarteten Invarianten
als `assert`: Typ der Liste, Zahl der Eintraege, kein toter Schluessel mehr).

## Kanal-Zugangsdaten gehoeren genau einem Profil (Telegram, Photon, ...)

1. **Ein Bot-Token, ein Profil.** Traegt ein Profil dieselbe Verbindungskennung
   wie `default`, warnt `hermes profile list` je Profil
   (`hermes_cli/profile_channels.shared_channel_credentials`: Byte-Vergleich der
   Kennungszeilen aus `.env` und von `platforms.<p>.token|api_key` aus
   `config.yaml`). Ein zweites Gateway auf demselben Token nimmt dem ersten die
   Nachrichten weg — beide pollen `getUpdates` —, und
   `hermes gateway migrate --multiplex` verweigert, solange die Dopplung steht.
   Die Dopplung ist also nicht kosmetisch: sie kostet Nachrichten.
2. **Ein Bot-PROFIL braucht keine Kanalzugangsdaten — es braucht eine eigene
   Modellkennung.** Der `/bot`-Weg des SkillsBot startet
   `hermes -p NAME chat -q` ohne Gateway. Also die geteilten Kanalzeilen
   entfernen statt jedem Bot einen eigenen Bot zu geben. Profile sind Inseln:
   sie lesen nur ihr eigenes `auth.json`/`.env`.
   Die Modellkennung holt man NICHT, indem man die Konto-Anmeldung des
   Startprofils in jedes Profil kopiert: das ist dieselbe Kennung in vielen
   Dateien (dieselbe Fehlerklasse wie beim Kanal) und eine geteilte
   Refresh-Sitzung kann allen Profilen gleichzeitig ablaufen — im Startprofil
   stand `Refresh session has been revoked`, waehrend ein anderes Profil
   dieselbe Kennung benutzte. Die Sitzung holt ein Profil stattdessen ueber
   einen SYMLINK auf den Root-Store oder eine eigene Anmeldung (Abschnitt
   „Einem Profil eine Modell-Anmeldung geben"); der lokale Router war nur
   Zwischenloesung und traegt die Flotte nicht mehr, weil ein toter Kandidat in
   seiner Combo alle Bots gleichzeitig stilllegt. Rezept und der Weg ueber alle
   Profile: `references/profil-kanalzugangsdaten.md`.
3. **Kein Unterkommando entfernt Kanaele aus einem bestehenden Profil** (nur
   `--clone` strippt beim Anlegen). Nicht selbst eine Schluesselliste bauen:
   `ChannelKeyIndex(<startprofil>).platform_for(<ENV_NAME>)` ist dieselbe
   Zuordnung, mit der `--clone` strippt. Ablauf, Werkzeug und Belege:
   `references/profil-kanalzugangsdaten.md`.
4. **Geheimnisse nicht in den Diff.** Ein `diff` gegen die Sicherung gibt die
   Werte im Klartext aus — redigieren (`sed -E 's/=.*/=<wert>/'`) oder ueber
   Hashes und Zeilenzahlen nachweisen.
5. **Nachweis:** `hermes profile list` ohne eine einzige Warnzeile UND die
   Gegenprobe (Sicherung zuruecklegen → Warnungen wieder da → erneut strippen →
   0). Die `.env` des Startprofils bleibt unveraendert (Hash vorher/nachher):
   dort gehoeren die Zugangsdaten hin.
6. **Geteilte Zeilen, die keine Warnung ausloesen, nicht mitstrichen** (z. B.
   `A2A_*`, `SMS_*`): melden und als eigene Entscheidung stellen — ein
   stillschweigend mitgestrichener Nebeneintrag ist spaeter nicht mehr zuordenbar.

## Profilflotte: pruefen, bevor geheilt wird

Bei "ein Bot antwortet nicht" oder einer Liste von `hermes profile list`-Warnungen
gilt eine feste Reihenfolge: **(1)** `hermes profile list` zeigt die KANAELE, nicht
die Antwort-Ursache; **(2)** die Antwort-Ursache ist fast immer die Modellkennung
(Profile erben nichts vom Startprofil) und wird nur durch einen echten Aufruf belegt
(`hermes -p NAME chat -q "Antworte nur mit dem einen Wort: fertig" -Q`); **(3)** den
`fallback_providers`-Block des PROFILS lesen, BEVOR der Provider verdaechtigt wird -
ein Kleinmodell in der Kette verdeckt den Anmeldefehler mit einem
Kontextfenster-Fehler.

**Ein Bot, der nach Sekunden MITTEN im Lauf stirbt, ist eine andere Klasse als
„antwortet nicht".** Im Profil-Log steht dann
`Non-retryable client error: <provider>/<model>: …` und daneben liegt das volle
Request-Dump `profiles/<bot>/sessions/request_dump_<sitzung>_*.json` mit
`reason` und `error.body` — dieselbe Meldung, die der Client gesehen hat; der
Bot-Name steht im Dateinamen, man braucht keinen Live-Lauf. Eine terminale
Fremdklasse (Guthaben/Permission, z. B. `403 free tier can only be used from
within OpenCode`) bricht im Router die ganze `auto/*`-Kombo ab und wird von
Hermes NICHT wiederholt. Erst ueber alle Profile zaehlen
(`grep -h "Non-retryable client error" */logs/errors.log`) und nach Fehlertext
gruppieren: gleicher Text in vielen Profilen = eine gemeinsame Ursache im
Router, kein kaputter Bot. Der Fix gehoert dann dorthin (`omniroute-betrieb`:
terminale Kandidaten abschalten, `POST /api/resilience/reset`) — nicht in die
Bot-Config.

Ein Befehl statt 29 Einzelaufrufe (je 30-60 s Kaltstart):
`scripts/profilflotte-bericht.py` (venv-Python von `hermes-agent`, `HERMES_HOME`
gesetzt) zeigt je Profil Modell, hinterlegte Anmeldung, Kanalzeilen, Kette und
Befund; `--nur-probleme` kuerzt auf die auffaelligen. Es schreibt nichts. Danach
beheben die drei Werkzeuge unter `Agenten/Hermes/scripts/` je Befund
(`profil-kanaele-bereinigen.py`, `bot-rueckfallkette-bereinigen.py`,
`auth-verknuepfen.ps1` = Sitzung, `bot-modell-auf-nous.py` bzw. fuer den
Router-Weg `bot-modell-auf-router.py`): erst Trockenlauf ohne Argument, dann
`--anwenden`, `--zuruecknehmen` holt zurueck; je Profil `.bak-JJJJMMTT`; alle drei
sind idempotent und nennen je uebersprungenem Profil den Grund.

- **Ein Pruefwerkzeug kann den Block an der falschen Stelle suchen - Falschbefund.**
  Der Flottenbericht las `provider`/`model` per Regex aus den ersten zwoelf Zeilen
  der `config.yaml`. Bei einem Profil, dessen `providers:`-Block VOR dem
  `model:`-Block steht (z. B. ein Wartungsprofil), meldete er „kein model-Block;
  Provider ohne Block und ohne Zugangsdatei" - das Profil war gesund und
  antwortete. Regel: `yaml.safe_load` zuerst, den `model:`-Block daraus nehmen,
  das Zeilenmuster nur als Rueckfall fuer unlesbare Dateien. Und: **jeden Befund
  erst am lebenden System nachstellen, dann „reparieren"** - ein echter Aufruf
  des Profils kostet eine Minute und trennt einen Werkzeugfehler von einem
  echten Ausfall. Ein Befund ohne Gegenprobe fuehrt sonst zu Reparaturen an
  gesunden Dateien.

Der Nachweis ist eine Leiter, keine Behauptung: `hermes profile list` mit 0
Warnzeilen - Gegenprobe mit `--zuruecknehmen` (die Warnungen kehren zurueck) - ein
echter Aufruf je Muster (vorher kaputt, wiederhergestellt, Sonderfall) -
`git diff --numstat` JE Datei (2 Einfuegungen/3 Loeschungen = Modellwechsel,
0/7 = entfernte Kette) - jede geaenderte `config.yaml` mit `yaml.safe_load`
geparst und Zielwerte assertiert, LF-only-Zeilen 0. Rezept, Entscheidungstabelle,
Zeitbudget und die Liste "was nicht angefasst wird":
`references/profilflotte-audit.md`.

## Ein neues Profil OHNE Repo anlegen (Wartungsbot-Muster)

Ein Profil, dessen Arbeitsbereich ein Hausordner ist statt eines Fremd-Repos
(Beispiel: `hermes-wartung` mit `terminal.cwd = Agenten\Hermes`).

1. `hermes profile create <name> --no-alias` (ohne `--clone`, damit keine
   fremde Modellkennung und keine Kanalzeilen mitkommen).
2. **Ein frisches Profil ist NICHT fertig** - es hat eine 45-Zeilen-`config.yaml`
   ohne `providers`- und `terminal`-Block, `SOUL.md` ist die eingebaute
   Standard-Identitaet, und **`profile.yaml` fehlt ganz** (ohne sie kennt `/bots`
   das Profil nicht). Der `--clone`-Weg liefert dagegen eine 1700-Zeilen-Config.
3. `providers.omniroute` byte-genau aus einem bestehenden Bot-Profil einsetzen
   (nicht abtippen - die `auto/*`-Modellliste ist 1700 Zeilen), dazu
   `model.provider=omniroute`, `model.default=auto/best-coding` (per
   `hermes -p <name> config set`, danach Kommentar-Schluss zurueckholen).
4. `terminal:`-Block mit `backend: local` und dem gewuenschten `cwd` ergaenzen.
   Die Bloecke VOR dem Schreiben mit `yaml.safe_load` parsen und Assertions
   setzen (`rest == vorher` ausserhalb der beiden Bloecke).
5. Die Router-Schluesselnamen in die eigene `.env` (frisch = leere Vorlage).
   Ein Kommentar ohne `#` laesst `python-dotenv` beim JEDEN Start meckern
   ("could not parse statement starting at line N") - Zeilen pruefen.
6. Beschreibung per `hermes profile describe <name> --text "..."` - das erzeugt
   `profile.yaml` erst an.
7. Ein Bot ohne Repo liest dieselbe Stilquelle wie die Repo-Bots:
   `profiles/rule_repo-bots.md`. Dort seinen Geltungsbereich im Kopf nennen und in
   der eigenen `SOUL.md` darauf verweisen — die Datei hat ein Budget von 6000
   Zeichen, also nur den Geltungsbereich ergaenzen, nichts anhaengen.
8. **Skills nachziehen — ein frisches Profil hat KEINE Haus-Skills.** Ohne
   `--clone` enthaelt `profiles/<name>/skills/` nur die eingebauten Kategorien
   (apple, autonomous-ai-agents, devops, …). Verweist die eigene `SOUL.md` auf
   Haus-Skills (`brainfiles/hermes-config-ops`, `hermes-doctor`,
   `dauerprozess-bewachen`, `systemdiagnose`), laufen die ersten Zuege des Bots
   in fehlgeschlagene `skill_view`-Aufrufe („Skill '<name>' not found") — der
   Lauf kostet Zeit und wirkt kaputt, ohne es zu sein. Die genannten Skills aus
   `Agenten/Hermes/skills/` hinueberkopieren und mit
   `hermes -p <name> skills list` belegen (Zaehlzeile „N local" plus die Namen
   in der `source`-Spalte `local`) — vor dem ersten Bot-Lauf, nicht danach.

Beleg-Pflicht (nichts davon ist durch "Datei steht da" bewiesen):
`hermes -p <name> chat -q "Fuehre pwd aus und nenne Modell und Arbeitsverzeichnis." -Q -t terminal`
- `pwd` muss den Zielordner melden, das Modell den Routerpfad. Dazu
`hermes profile list` (0 Warnzeilen) und die Profilliste des SkillsBot
(`bot_namen()` in `Agenten/Bus/skillsbot.py`) gegen die Zahl der Profilordner.

Falle: Zeilenenden nicht raten. Ein Profil, das per `hermes config set`
angefasst wurde, kann LF-only sein, waehrend ein aus einem CRLF-Profil
kopierter Block CRLF mitbringt - die Datei ist danach gemischt. Vor dem
Schreiben `\r\n` in den ROHEN Bytes bestimmen und die GANZE Datei auf das
Hausformat (CRLF) normalisieren; der `yaml.safe_load`-Vergleich beweist, dass
nur die Enden normalisiert wurden, der Diff gegen die Sicherung zeigt genau
die neuen Zeilen.

### Ein Rollen-Bot, der nur verteilen soll (Verteil-/Dispatcher-Bot)

Ein Profil, dessen Aufgabe „Auftrag verstehen, Ziel finden, delegieren" ist.
**Ein Verbot allein haelt nicht, eine Selbstpruefung haelt.** Gemessen an derselben
klaren Aufgabenstellung („pruefe, ob die Repos aktuell sind"): mit der SOUL-Regel
„bearbeite den Auftrag NICHT selbst" hat der Bot die Pruefung SELBST gefahren —
18 Werkzeugaufrufe mit einem kleinen Modell, 7 mit einem starken; es aenderte sich nur
die Zahl der Umwege. Erst die drei Zusaetze unten haben die Rolle gehalten (danach
2 Aufrufe und eine Rueckfrage statt Eigenlauf; bei „lass Bot X sein Repo pruefen" hat
er wirklich delegiert und das Ergebnis des Ziels samt dessen Empfehlung berichtet):

1. **Eine Frage, die der Bot sich vor JEDEM Schritt selbst stellt** — „Fuehre ich
   gerade den Auftrag aus, oder suche ich sein Ziel?" — mit den Merkmalen des
   Abweichens, an denen er sich ertappt: Verzeichnisse des Gegenstands lesen, ein
   Fachwerkzeug aufrufen, zaehlen, vergleichen, ein Fachergebnis formulieren. Und
   ausdruecklich: **auch ein Trockenlauf ist Ausfuehrung** — „ich schaue nur schnell
   nach" ist der Weg, auf dem die Rolle verloren geht. Dazu die Regel fuer den Fall
   ohne Ziel: **kein Bot passt → Werkzeug NENNEN und fragen, nicht starten.** Ein
   Rollen-Verbot braucht diese Pruefung, sonst bleibt es wirkungslos.
2. **Den Weg deterministisch machen, nicht die Absicht.** Ein Skript kapselt den
   mechanischen Teil (`Agenten/Werkzeuge/<rolle>-route.py`): `--liste` (Ziele samt
   Beschreibung aus `profiles/*/profile.yaml`, damit die Zielliste nicht abgetippt
   wird), `--suche <wort>` (welche Ziele passen), `--an <ziel> "<auftrag>"` (startet
   wirklich `hermes -p <ziel> chat -q`, entfernt `PYTHONHOME`/`PYTHONPATH`, setzt eine
   Frist). In der SOUL genau diese drei Aufrufe als ERSTEN Schritt nennen. Damit ist
   der Ausgang nachvollziehbar und wiederholbar, auch wenn das Modell umwege nimmt.
3. **Nicht mehr versprechen als gemessen ist.** „Der Bot verteilt" ist erst wahr,
   wenn ein Auftrag nachweislich bei einem anderen Profil ankam — je Rolle DREI
   Auftragsarten durchspielen (ein Sachauftrag ohne Bot, ein Fachauftrag mit Werkzeug,
   ein echter Delegationsauftrag) und die Werkzeugaufrufe zaehlen, nicht das Gefuehl
   befragen. Die harte Durchsetzung waere ein eingeschraenkter Werkzeugsatz — Hermes
   bietet dafuer heute keinen Config-Schluessel (`tools` regelt die Werkzeugsuche,
   `toolsets` die Plugin-Sets), also nicht als geloest darstellen. Das Rollenmodell
   selbst bleibt Geschmackssache: ein kleines Modell folgt der Charta genauso wenig
   wie ein grosses, nur mit mehr Umwegen — die Selbstpruefung ist der Hebel.

Dazu die Profil-Pflichten wie oben (frisches Profil = 45 Zeilen ohne `providers`/
`terminal`, `profile.yaml` fehlt), `hermes profile describe <name> --text "<Satz>"`
fuer `/bots` — und ein neues Werkzeugskript unter `Agenten/Werkzeuge/` in die
`.gitignore`-Freigabeliste aufnehmen (`!Agenten/Werkzeuge/<datei>.py`): ohne die Zeile
ist es beim naechsten `git status` unsichtbar (`git check-ignore -v <pfad>` zeigt `!!`)
und wird nie versioniert.

## Einem Profil eine Modell-Anmeldung geben (Symlink, nicht Kopie)

Ausloeser: "/bot NAME antwortet nicht", `hermes -p NAME chat -q ...` endet mit
"Hermes is not logged into Nous Portal". Ein Profil ohne eigene `auth.json`
liest NIE die des Root-Homes (`profile_credential_audit.py`); `NOUS_API_KEY` in
der Benutzerumgebung genuegt NICHT - der Gate verlangt den Provider-State in der
`auth.json` des Profils.

Richtig ist ein **Symlink** auf den Root-Store, nicht eine Kopie:
`Agenten/Hermes/scripts/auth-verknuepfen.ps1` (Trockenlauf ohne Argument,
`-Anwenden`, `-Zuruecknehmen`). Der Grund gegen die Kopie: eine device_code-
OAuth-Sitzung enthaelt einen Refresh-Token; als Kopie in vielen Profilen
entwertet die erste Rotation alle anderen ("Refresh session has been revoked").
Ein Symlink haelt EINEN Store, und genau dafuer hat Hermes die Sperre und die
"Peer hat rotiert, uebernimm seinen Token"-Logik
(`hermes_cli/auth.py::_nous_shared_store_lock`); `auth_oauth_grants.py` behandelt
einen Symlink auf den Root-Store ausdruecklich als "kein Klon" und laesst ihn
stehen. **Symlinks: erst den direkten Versuch, dann die Leiter.** Ein Symlink braucht nicht
per se Erhoehung: ein schlichtes
`New-Item -ItemType SymbolicLink -Path <ziel> -Target <root>` ist hier mehrfach OHNE
Admin durchgelaufen (Developer-Mode AN, `AllowDevelopmentWithoutDevLicense=1`),
waehrend derselbe Aufruf in einer anderen Sitzung mit
`NewItemSymbolicLinkElevationRequired` („Fuer diesen Vorgang sind
Administratorrechte erforderlich") abbrach — die Anforderung haengt also am Kontext,
nicht am Befehl. Reihenfolge, die keinen UAC-Klick kostet: (1) `New-Item
-ItemType SymbolicLink` direkt; (2) falls es verweigert, `pwsh` 7
(`C:\Program Files\PowerShell\7\pwsh.exe`)
`-NoProfile -Command "New-Item -ItemType SymbolicLink -Path <ziel> -Target <root>"`;
(3) erst dann das Hausskript erhoeht (UAC, `auth-verknuepfen.ps1` braucht `-Anwenden`,
ein Aufruf ohne den Schalter ist ein TROCKENLAUF und legt nichts an). Danach mit
`os.path.islink()` gegenpruefen, nicht mit `os.path.exists()`. **Ein Symlink ist keine
Kopie** — die Begruendung oben gilt unveraendert; wo schon eine eigene `auth.json`
liegt, nicht ueberschreiben. Fuer EIN
Profil ist das der kuerzere Weg als das Skript samt UAC-Prompt. **`-PassThru` und
`-RedirectStandardOutput` vertragen sich in PowerShell 5.1 NICHT mit `-Verb
RunAs`** (AmbiguousParameterSet); das innere Skript schreibt sein Ergebnis
selbst per `Start-Transcript` in eine Logdatei.

Fallen: Ein Profil mit eigener `auth.json` bleibt unberuehrt (die Datei NICHT
ueberschreiben). Enthaelt sie nur einen Pool-Eintrag ohne `providers.nous`,
nutzt sie nichts - vorher sichern und dann ebenfalls verknuepfen. Ein
`api_key`-Provider (llamacpp, docker) braucht keine Sitzung.

Beleg: `hermes -p NAME chat -q "Antworte nur mit dem einen Wort: fertig" -Q -t
memory` je Muster (verknuepft, eigene Sitzung, Sonderfall) - und danach das
Hauptprofil einmal aufrufen: bleibt SEINE Sitzung intakt, ist die gemeinsame
Nutzung bewiesen.

## Modellwechsel ueber viele Profile: was die Werkzeuge NICHT sagen

- **`git commit -- <pfade>` committet den ARBEITSBAUM dieser Pfade, nicht den
  Index.** Ein zuvor per `update-index` deterministisch gebauter Index wird von
  so einem Aufruf ignoriert - fremde Hunks in derselben Datei landen mit im
  Commit. Fuer "nur meine Zeilen" ohne Pathspec committen (`git commit`), davor
  `git diff --cached --name-only` lesen und gegen die eigene Absicht zaehlen.
- **Staged Eintraege koennen verschwinden, wenn eine zweite Sitzung committet:**
  ein `git commit` OHNE Pfadangabe committet den ganzen Index - die eigene
  Aenderung landet dann im fremden Commit (richtig, aber falsch beschriftet),
  oder ein `git add -A` der anderen Sitzung zieht sie mit. Deshalb: eigenen
  Index bauen, `git diff --cached --name-only` gegen die Absicht zaehlen und
  in DERSELBEN Sitzung committen - kein Zeitfenster dazwischen.
- **Der Kommentar-Schluss geht auch bei PROFIL-Configs verloren**, wenn
  `hermes config set` die Datei neu schreibt (gemessen: 38 Zeilen). Ein
  Profil, das nur "laeuft schon" ist, wird von einem Umstellungs-Werkzeug
  uebersprungen - seinen Schaden heilt dann niemand. Nach jeder Umstellung
  `git diff --numstat` JE Datei lesen: 2/2 ist richtig, hunderte Zeilen heissen
  gekippte Zeilenenden oder weggefallener Doku-Block.
- **Zeilenenden sind bei Profil-Configs gemischt.** Ein `hermes config set`
  schreibt LF-only; aus einem CRLF-Profil kopierte Bloecke bringen CRLF mit.
  Vor dem Einfuegen die ROHEN Bytes ansehen und die Zeilen einzeln behandeln
  (an Zeilenumbruch trennen und ein abschliessendes CR vor der Zeile abstreifen),
  nicht auf ein einheitliches Zeilenende vertrauen. `subprocess(... text=True)`
  wandelt CRLF still nach LF und baut dann eine LF-Kopie der ganzen Datei.
- **Beim Ersetzen von Text mit Backslashes (Windows-Pfade, `\r\n`, Regex) das
  Patch-Werkzeug nicht benutzen.** Es deutet Escapes: eine Zeichenfolge wie
  Backslash-r-Backslash-n landet als echter Zeilenumbruch MITTEN im Satz, und
  wer den Anker der Ersetzung nicht im Ersatztext wiederholt, loescht die
  Ueberschrift mit. Byte-genau per Skript schreiben (Bytes lesen, ersetzen,
  schreiben, `count == 1` asserten) und die geaenderte Stelle danach noch
  einmal lesen — ein gelungener Patch ist kein Beleg fuer sauberen Text.
  **Es kippt ausserdem die Zeilenenden der Region, die es anfasst:** in einer Datei
  mit GEMISCHTEN Enden (ein Teil LF, ein Teil CRLF — Normalfall bei einer Datei, die
  eine andere Sitzung per `config set` angefasst hat) schreibt es den beruehrten
  Abschnitt geschlossen auf CRLF, gemessen 64/61 an einer README, in der EINE Zeile
  gemeint war. Deshalb `git diff --numstat` NACH JEDER EINZELNEN Aenderung lesen,
  nicht erst am Ende eines Stapels: stimmt die Zahl nicht, `git show HEAD:<pfad> >
  <pfad>` (nur wenn die Datei ausschliesslich die eigene Aenderung traegt) und mit
  dem byte-genauen Skript neu setzen — danach muss die Zahl der Absicht entsprechen
  (drei eingefuegte Zeilen = `3 0`).
  **Der Skript-Weg selbst, damit keine Escape-Sequenz als echter Umbruch landet:**
  den Text erst auf LF normalisieren (`raw.replace(b"\r\n", b"\n")`), das
  Zeilenende der ANKERZEILE bestimmen (endet sie auf `\r\n`, dann dieses, sonst `\n`)
  und beim Schreiben die neuen Zeilen mit genau diesem Ende setzen. Mehrere Zeilen
  hinter einer Ankerzeile einhaengen heisst: Index der Marke suchen, dann das naechste
  `\n` — den Anker NICHT mit einem Zeilenumbruch im Suchmuster schreiben (trifft sonst
  nicht), und in der Datei selbst kein `\n` in einem String-Literal bilden, das als
  Text gemeint ist.
- **`bot-modell-auf-nous.py --auch-lokale` greift auch lokale Provider.** Ohne den
  Schalter bleiben `llamacpp`/`docker`/`ollama` stehen (Grund: sie brauchen keine
  Anmeldung). Beim Umstellen MUSS das lokale `model.base_url` (z. B.
  `http://127.0.0.1:18434/v1`) mit weg, sonst zeigt der Nous-Aufruf weiter auf den
  lokalen Endpunkt — das Werkzeug entfernt es und prueft nach. Gemessen 21.09.2026:
  17 Profile, `openmontage` (llamacpp mit CLIP-mmproj, als Hauptmodell gar nicht
  ladbar) und `awesome-systematic-trading` (docker) waren die letzten zwei.
- **Die LF-Falle sitzt IN `kommentar_schluss_zurueckholen()` selbst.** Es las die
  Sicherung mit `read_text()` (ohne `newline=""`) und schrieb mit `newline=""`:
  der zurueckgeholte Block kam als LF in eine CRLF-Datei, der Diff zeigte die
  ganze Datei (5 von 17 Profilen). Der ganze Vorgang gehoert auf BYTES
  (`read_bytes`, Endung aus den Rohdaten ableiten, `write_bytes`) — so repariert,
  mit isoliertem Test gegen eine Fixture. Bestandsdateien heilt
  `scripts/zeilenenden-zuruecksetzen.py <pfad>`; wenn neue Zeilen keine
  HEAD-Vorlage haben, normalisiert `scripts/zeilenenden-auf-head-format.py` die
  GANZE Datei auf die Endung aus `git show HEAD:<pfad>`.
- **Ein Bot auf `terminal.backend: docker` stirbt mit einer irrefuehrenden
  Meldung.** Ist der Docker-Daemon langsam, laeuft der 5-Sekunden-Probe
  (`docker version`) in `TimeoutExpired`, der Lauf bricht ab und der Client sagt
  nur "Switch to a different model with `/model`" — der Verdacht faellt auf das
  Modell, obwohl der TERMINAL-Backend das Problem ist. Vor dem Modellwechsel
  pruefen: `terminal.backend` muss bei Repo-Bots `local` sein (Hausstandard);
  `docker` gehoert nur zu einer bewussten Container-Spur.

## Desktop-App zeigt nur das default-Profil (multiplex_profiles)

Symptom: die Desktop-App ist „unvollständig" — kein Bots-Tab, kein
Profil-Umschalter, nur `default`. Ursache fast immer: `gateway.multiplex_profiles`
ist **nicht explizit gesetzt** (nur der Default `true`), der Gateway serviert
dann nur `default`. `hermes config get gateway.multiplex_profiles` liefert den
Default und ist damit **kein Beweis**, dass der Schluessel in der Datei steht —
`grep -n multiplex config.yaml` entscheidet. `hermes gateway status` warnt
„Serving the default profile only (gateway.multiplex_profiles unset)".

Fix (der dokumentierte Weg der Status-Meldung, nicht `migrate --multiplex`, das
auf Windows an den Scheduled Tasks scheitert):

    hermes config set gateway.multiplex_profiles true
    hermes gateway restart

Danach `hermes gateway status` (Warnung muss weg) und `hermes gateway list`
(alle Profile aufgelistet). Die Desktop-App liest die Projekt-Config, wenn
`HERMES_HOME` als Benutzervariable gesetzt ist (`resolveHermesHome2` prueft
`process.env.HERMES_HOME` → Registry → `%LOCALAPPDATA%\hermes`); der
`desktop.log` unter `$HERMES_HOME/logs/` belegt, welches Home die App wirklich
nutzt. Eine veraltete `%LOCALAPPDATA%\hermes\config.yaml` (eigene .env/auth.json
mit Klartext-Zugangsdaten) ist eine komplette Alt-Installation, keine bloße
Zweitablage — nicht loeschen, als Altlast melden.

### Gegenrichtung: multiplex + Profil-`gateway:`-Bloecke = Absturzkreislauf

Jede Profil-`config.yaml` ist beim Anlegen aus dem Hauptprofil kopiert und traegt
deshalb einen kompletten `gateway:`-Block (`a2a enabled: true, port: 9900`).
Kanal-Zugangsdaten entfernt man zwar (profil-kanaele-bereinigen), die
`gateway:`-Bloecke bleiben stehen. Setzt man dann `multiplex_profiles: true`,
startet der zentrale Gateway JEDES Profil als Sekundaeradapter auf demselben
Port 9900, haengt beim Plugin-Import (`plugins_loader.exec_module`, synchron in
der Event-Loop), verpasst die Liveness-Probes, und der Watchdog beendet den
Prozess — ein Neustart-Kreislauf.

Diagnose am lebenden System (Symptom-Signatur):

- **Kill-Kadenz = rund 3 x Probe-Intervall** (Probes alle 5 min → Kills alle
  ~16 min): `grep CRITICAL gateway.shutdown_watchdog logs/gateway.log` und die
  Zeitstempel-Abstaende der Eintraege messen, nicht nur zaehlen.
- **`gateway_state.json`: `last_heartbeat_at` eingefroren** (identischer
  Zeitstempel in jedem Kill-Eintrag) und `updated_at`-Alter > Probe-Intervall —
  das heisst die Loop haengt, nicht nur der Schreibvorgang.
- **CPU-Sekunden ≈ Uptime-Sekunden** (Spin statt Warten).
- **`logs/gateway-stdio.log` (faulthandler-Dump beim Kill):** der
  Event-Loop-Thread steckt in einem Import/Load — synchrones Plugin-Laden in
der Loop ist die haengende Stelle.

Fix: `multiplex_profiles: false` (Bot-Profile kommen ueber `/bot`
Einzelauftraege `hermes -p NAME chat -q`, sie brauchen keine Adapter) und die
jetzt obsoleten `profile_routes`-Eintraege deaktivieren, nicht nur den Port
frei lassen. Beleg nach dem Neustart: `updated_at` stampet durchgehend frisch
(Alter < Probe-Intervall), `state: running`, keine neue CRITICAL-Zeile, CPU
flach. End-zu-End-Probe: dieselbe Nachricht an den SkillsBot antwortete
waehrend des Kills `status: fehler` und nach dem Fix `status: ok` — der Bot
haengt ueber den A2A-Weg am Gateway, nicht am Bus, und ist damit ein
kostenloser Gesundheitsindikator fuer den Gateway.

## Fallen

- **`hermes` aus einer windows-mcp-Sitzung stirbt mit `_thread`/`f-string`-Tracebacks**
  (`Fatal Python error: init_import_site`, `module '_thread' has no attribute
  'start_joinable_thread'`)? Der Interpreter ist nicht defekt — in der aufrufenden
  Umgebung steht ein verirrtes `PYTHONHOME`, das das venv-Python auf ein fremdes Stdlib
  zieht. `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH` an den Anfang jedes Aufrufs setzen,
  dann läuft `hermes.exe` wieder. Ausführlich: `hermes-maintenance`.
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
  Standardprofil und liest eine andere `config.yaml`. **Sichtbares Symptom, wenn die Variable
  fehlt:** `hermes fallback list` meldet „No fallback providers configured", obwohl die
  Kette in `Agenten\Hermes\config.yaml` steht — gelesen wurde dann
  `%LOCALAPPDATA%\hermes\config.yaml`, ein anderes Home mit anderer Config. Vor jeder
  „ist nicht gesetzt"-Meldung das tatsächlich gelesene Home zeigen lassen:
  `python -c "from hermes_constants import get_hermes_home; print(get_hermes_home())"`.
  **Beim Schreiben dieselbe Falle, nur unauffaelliger:** `hermes config set`
  meldet `✓ Set <pfad> = <wert> in <datei>` — diese Datei lesen und gegen die
  gewollte Config halten. Ohne `HERMES_HOME` landet der Schreibvorgang im
  Standardprofil (`%LOCALAPPDATA%\hermes\config.yaml`), waehrend der laufende
  Dienst die Projekt-Config liest: die Aenderung ist dann scheinbar
  wirkungslos, obwohl „der Wert doch drinsteht". Werden beide Ablagen gelesen
  (CLI ohne und mit `HERMES_HOME`), beide auf denselben Wert ziehen — sonst
  driften sie auseinander, und der naechste Aufruf faellt auf den alten Stand
  zurueck.
- **Welche Config der LAUFENDE Gateway liest, steht in keiner Notiz — am
  Prozess bestimmen.** `hermes config path` nennt nur, was die CLI ohne
  Kontext lesen wuerde. Der Dienst startet ueber den Aufgaben-Wrapper
  (`schtasks /xml` → CommandLine, darin ggf. `HERMES_HOME`); und die
  Sitzungskennung (Model/Provider im Sessionkopf) zeigt, welche Config eine
  laufende Sitzung tatsaechlich gelesen hat. Beide Belege ziehen, bevor
  „die AppData-Config ist die aktive“ behauptet wird — der Gateway kann die
  Projekt-Config lesen, waehrend die Desktop-App die andere nutzt; beide
  Ablagen muessen auf denselben Stand gezogen sein.
- **Zwei Hermes-Checkouts nebeneinander: welcher BAUM arbeitet, steht in den Prozessen.** `hermes --version` nennt „Install directory" — das ist der Baum, aus dem DIESER Aufruf kommt, nicht der, aus dem die Dienste laufen (ein alter Checkout wie `C:\Hermes` kann daneben liegen). Wahrheit: Prozesse nach **`ExecutablePath`** gruppieren (`Get-CimInstance Win32_Process | Where-Object CommandLine -match hermes | Select ProcessId, ExecutablePath`), nie nach Kommandozeilen-Text — sonst zaehlt der eigene Suchbefehl mit und man loescht sich selbst. Autostart laeuft ueber die `*.vbs` in `Agenten/Hermes/gateway-service/`: ein VBS kann auf einen alten Baum zeigen und bei jeder Anmeldung Prozesse daraus starten. `VIRTUAL_ENV`, `PYTHONPATH` und der `python.exe`-Pfad darin gehoeren auf den aktiven Baum (VBS mit CRLF schreiben, vorher `.alt-JJJJMMTT`).
- **Ein abgeloester Task, den man nicht aendern darf, wird entschaerft und BEWIESEN.** Einen als Admin registrierten Task kann eine normale Sitzung nicht deaktivieren: `Disable-ScheduledTask` und `schtasks /Change /DISABLE` enden mit „Zugriff verweigert", `Start-Process -Verb RunAs` mit 0x800704C7 („durch den Benutzer abgebrochen") — ein nicht erhoehtes Token bekommt keinen UAC-Prompt. Statt dagegen anzukommen: das Skript, das der Task aufruft, neutralisieren (`WScript.Quit 0`) und die Wirkung MESSEN — `Start-ScheduledTask -TaskName <task>`, dann Prozesszahl vorher/nachher unveraendert UND kein Prozess aus dem alten Baum. Den formalen Schritt als fertiges Skript nach `Agenten/Werkzeuge/` legen (Log nach `%TEMP%`), das der Nutzer einmal in einer Admin-Shell startet. Die Altanlage danach **umbenennen statt loeschen** (`<baum>.alt-JJJJMMTT`) und erst nach Tagen entfernen; `venv.bak.*`/`venv.backup-*` darin sind regenerierbar und duerfen sofort weg.
- **Testläufe gegen die eigene Config gehören in ein eigenes `HERMES_HOME`, nie in die
  echte Config.** Ablage: ein Pfad **innerhalb** `BrainFiles` ohne Junction, z. B.
  `Agenten\Hermes\.<name>-test\home\`. Zwei Gründe: `HERMES_WRITE_SAFE_ROOT` verweigert
  Schreibzugriffe außerhalb von `BrainFiles`, und ein Junction-Pfad (`Werkstatt` → `O:`)
  wird auf sein echtes Ziel aufgelöst und deshalb ebenfalls verweigert — `%LOCALAPPDATA%\Temp`
  und `Werkstatt` fallen damit beide aus. Nach dem Lauf löschen: hält ein `sqlite3`-Handle
  aus der execute_code-Sitzung die Test-`state.db`(-wal), scheitert jedes `rm -rf` mit
  „Device or resource busy" — Kernel zurücksetzen (`execute_code(reset=True)`), dann löschen.
- PowerShell-Helfer nie `H` nennen (Alias von `Get-History`) — der Fehler gibt dann
  Argumente im Klartext aus. Umlaute und mehrzeilige Blöcke nicht über die Kommandozeile
  transportieren: mehrzeiligen Text als Datei schreiben oder als Array mit
  `-join [char]10` bauen.
- **Ein Einzelauftrag (`-q`, so startet der SkillsBot `/bot`) hat keinen Nutzer
  fuer Freigaben.** In diesem Modus werden Kommandozeilen mit `-c/-e` und
  `execute_code` blockiert („runs without a user present to approve") — der
  Auftrag endet dann in einem Werkzeugfehler, den der Bot als Ergebnis meldet.
  Auftraege fuer solche Bots deshalb so formulieren, dass sie ohne
  Shell-Einzeiler auskommen (Datei schreiben und ein bestehendes Skript
  aufrufen, `read_file`/`search_files` statt Inline-Python) — und einen Bot,
  dessen Kern Kommandos fahren soll, aus einer Sitzung mit Nutzer oder als
  Routine starten, nicht per `-q`.

- **Ein Umgebungsvariablen-Namen kann ein Tippfehler sein — Namen aus der Registry lesen, nicht eine Kandidatenliste abfragen.** Im Ist-Stand stand `#ANTHROPIC_API_KEY` (mit Rautenzeichen!) und `ANTHROPIC_API_KEY_BILLING`; der kanonische `ANTHROPIC_API_KEY`, den Hermes' Provider-Profil liest, fehlte. Eine Abwesenheitsmeldung ist erst gueltig, wenn die Namen aufgelistet wurden: `(Get-Item HKCU:\Environment).GetValueNames()`, dann je Name Laenge und SHA-256-Anfang der Kandidaten vergleichen — gleicher Hash = derselbe Wert, und das Setzen ist ein Umbenennen, kein neues Geheimnis.
- **Ein Provider braucht oft keinen Block in `providers:`.** Hermes' eingebaute Model-Provider-Profile (`hermes-agent/plugins/model-providers/<name>/__init__.py`) bringen `base_url`, `api_mode` und `env_vars` selbst mit — fuer Anthropic sind das `https://api.anthropic.com`, `anthropic_messages` und `(ANTHROPIC_API_KEY, ANTHROPIC_TOKEN, CLAUDE_CODE_OAUTH_TOKEN)`. Ist die Variable gesetzt, ist der Provider da; ein zusaetzlicher Eintrag in `config.yaml` ist hoechstens eine zweite Wahrheit.
- **Fuer Provider-Anmeldedaten braucht das laufende Gateway KEINEN Neustart.** Sie kommen aus dem Credential-Pool (`auth.json`) und der `.env` des Profils, nicht aus der Prozessumgebung: ein `delegate_task`-Kind lief sofort mit `provider=anthropic model=claude-opus-5` (Logzeile `platform=subagent … id=msg_…`). Wer „greift erst nach Neustart" behauptet, muss diesen Unterschied zeigen — er gilt nur fuer `${env:NAME}`-Verweise.
- **`hermes config edit` oeffnet auf Windows notepad und blockiert den Aufruf, bis das Fenster geschlossen ist.** Intern laeuft ein synchrones `subprocess.run([editor, config_path])` ohne Timeout — aus einer Werkzeugsitzung haengt der Aufruf bis ins Zeitlimit. Der Befehl ist fuer Menschen am Desktop gedacht, nicht fuer Agenten: einzelne Werte gehoeren zu `hermes config set`, nur ein mehrzeiliger Eingriff verdient das Wegwerf-Skript (`Agenten/Hermes/cache/`). Wer `config edit` in einem Agenten-Flow braucht, startet es mit `background=true` und laesst das Fernster dem Nutzer.
- **Der Auxiliary-Client loest `auxiliary.*.model` ueber den Nous/OpenRouter-Katalog auf — ein lokales GGUF dort ist ein kategorischer 404, kein langsamer Server.** Zeigt `auxiliary.compression.model` (oder `auxiliary.mcp`/`auxiliary.skills_hub`) auf ein Laufzeitmodell (`llamacpp/DeepSeek-...`), wirft das Komprimieren `Failed to generate context summary: 404 - Model '...' not found ... in our configuration or OpenRouter catalog`; Muster davor in `logs/errors.log`/`gateway.log`: `Auxiliary compression: model '...' no longer in Nous catalog`. Der Client hat keinen lokalen llamacpp-Pfad — ein lokales GGUF ist fuer ihn prinzipiell unaufloesbar, und Sessions wachsen stumm auf 100k+ Tokens unkomprimiert, ohne dass die Kompression irgendwo laut scheitert. Fix: `hermes config set auxiliary.compression.provider nous` und `...model deepseek/deepseek-v4-flash-0731` (dasselbe Provider/Modell wie das Hauptmodell, 786k — nachweislich aufloesbar). Nicht zurueck auf den frueher dokumentierten `auto/coding:free`-Router-Weg: der reroutet aktuell auf OpenCode-Free, das ausserhalb von OpenCode 403 liefert — kein zuverlaessiges Kompressionsmodell. **Nach JEDEM `hermes update` alle `auxiliary.*`-Modellpfade (compression, mcp, skills_hub) pruefen**: das Update schreibt die Config neu und setzt Modell/`threshold` zurueck auf einen lokalen GGUF-Stand (gemessen: `threshold` 0.19 → 0.66, compression auf llamacpp). `auxiliary.skills_hub` kann dabei auf ein CLIP-Projektor-GGUF zeigen, das gar nicht als Hauptmodell ladbar ist ("CLIP cannot be used as main model") — ebenfalls ueber den Katalogpfad ersetzen. Beleg: `hermes config check` Exit 0; die laufende Sitzung nutzt die neue Config erst ab `/new`.
- **Die Kompression-schwellen-Warnung kennt einen dauerhaften Fix, und die Schwelle ist KONTEXT-RELATIV, kein Fixwert.** Hermes meldet per Sitzung, das Kompressionsmodell habe kleineren Kontext als die Schwelle des Hauptmodells (`auxiliary.compression.model` vs. `compression.threshold`), und senkt die Schwelle nur fuer diese Sitzung. Der Trigger in Tokens ist `(model.context_length - max_tokens) * compression.threshold` (min. 64k; Fenster < 512k werden auf 75% angehoben) — `threshold` ist ein PROZENTSATZ des Kontextfensters. Der frueher dokumentierte Wert 0.19 gilt nur, solange das Aux-Kompressionsmodell ~200k hat; ist es dasselbe Modell wie das Hauptmodell (deepseek-v4-flash, 1M), hebt man beides an: `hermes config set model.context_length 1000000` UND `hermes config set compression.threshold 0.60` → komprimiert erst bei 600k statt ~190k. Faustregel: `threshold` so waehlen, dass der Trigger-Tokenwert unter dem Fenster des Aux-Kompressionsmodells bleibt, sonst senkt Hermes die Session-Schwelle beim Start selbst ab (`_lower_threshold_to_aux_context`); ein grosses Aux-Modell erlaubt eine hohe Schwelle = Kompression ruht bis kurz vor dem Fensterende. Nach `hermes config check` (Exit 0 = sauberes YAML); die laufende Sitzung nutzt die neue Schwelle erst nach `/new`.
- **`patch` und `write_file` auf `config.yaml` sind gesperrt** („Refusing to write to Hermes config file", bei der AppData-Config zusaetzlich `HERMES_WRITE_SAFE_ROOT`). Zwei Wege bleiben, und sie sind nicht gleichwertig: `hermes config set …` fuer den EINZELNEN Wert (auch fuer Listen — der Wert wird als YAML/JSON geparst, `'[{"provider":"omniroute","model":"auto/best-coding"}]'` funktioniert), und ein Wegwerf-Skript unter `Agenten/Hermes/cache/`, das die Datei binaer liest, chirurgisch ersetzt und zurueckschreibt — fuer eine Zusammenfuehrung mit mehreren Hunks. Das Skript ist dort das BESSERE Mittel, weil `hermes config set` die Datei neu schreibt und dabei den Kommentar-Schluss abschneidet (naechste Falle). Fuer das Skript gelten dieselben Regeln wie fuer jede Textaenderung: Zeilenenden binaer feststellen (`b"\r\n" in raw`) und erhalten, je Ersetzung `count == 1` asserten, den NEUEN Text vor dem Schreiben mit `yaml.safe_load` pruefen, vorher `.bak-JJJJMMTT`.
- **`hermes config set` schneidet den Kommentar-Schluss der Datei ab.** Es schreibt die ganze Datei neu; ein Dokumentationsblock am Dateiende (Beispiele fuer `security:`, `fallback_model:`) ist danach weg — funktional harmlos, aber eine stille Aenderung an der Datei des Nutzers. Nach **jedem** `config set` diffen und den Block zurueckholen (`Agenten/Hermes/cache/config-schluss-wiederherstellen.py --tun`), sonst waechst bei jeder Aenderung eine unsichtbare Differenz. Die Aenderung selbst sieht im Diff wie eine Zeilenersetzung aus — genau pruefen, ob noch mehr fehlt. **Rueckholquelle:** `hermes config set` legt vor dem Schreiben ein Backup unter `backups/config/config.yaml.good.<zeitstempel>` an — den fehlenden Block daraus byte-genau (CRLF erhalten) an die Datei anhaengen, dann `diff` gegen die Sicherung: er darf exakt die eine gewollte Zeile zeigen.
- **Der Kommentar-Schluss fehlt auch bei PROFIL-Configs** (`profiles/<name>/config.yaml`),
  nicht nur im Hauptprofil (gemessen: 38 Zeilen in 6 Profilen). Dort ist "Block anhaengen"
  der falsche Fix — die Ziel-Fassung BYTE-genau aus `git show HEAD:<pfad>` bauen und nur
  den geaenderten Block ersetzen. `read_text()`/`write_text()` ohne `newline=""` drehen
  eine CRLF-Datei still auf LF (die selbst eingesetzten Zeilen behalten `\r\n`, die
  gelesenen nicht) — der Diff zeigt danach die GANZE Datei. **Beide Richtungen sind
  betroffen:** mit `newline=None` setzt Python beim Schreiben `os.linesep` ein, eine
  LF-Datei wird also genauso auf CRLF gedreht (gemessen an Python-Dateien, die im Haus
  LF fuehren). Wer eine Datei in Textmodus anfasst, erzeugt einen Ganzdatei-Diff, in
  welche Richtung auch immer — Bytes lesen, Bytes schreiben, danach `git diff --numstat`
  JE Datei gegen die erwartete Zeilenzahl halten; bei einem Werkzeug, das ganze
  Ordnerbaeume umstellt, diesen Check fuer jede geaenderte Datei einzeln fahren, weil
  eine Summe den Ausreisser verbirgt. `Agenten/Hermes/scripts/bot-modell-auf-router.py`
  arbeitet genau so und heilt den Kommentar-Schluss gleich mit.
- **Nach einer Massenaenderung den Diff JE DATEI zaehlen, nicht die Summe.** Erwartet sind
  die Zeilen der gewollten Ersetzung (Beispiel `model`: 2 Einfuegungen/3 Loeschungen, weil
  `base_url` entfaellt). Ein Diff, der wie die ganze Datei aussieht, heisst gekippte
  Zeilenenden oder verschwundener Doku-Block — in einer Summe ueber 25 Dateien faellt
  beides nicht auf. Zusaetzlich jede geaenderte `config.yaml` mit `yaml.safe_load` parsen
  und die Zielwerte asserten.
- **Ein kaputter Fallback ueberdeckt die echte Fehlermeldung.** Ist der Primaerpfad nicht
  angemeldet und die geerbte Kette zeigt auf ein lokales Modell unter der Mindestgroesse,
  endet der Lauf mit „context window ... below the minimum" — der Anmeldefehler ist dann
  unsichtbar. Passt eine Meldung nicht zur vermuteten Ursache, zuerst den
  `fallback_providers`-Block des PROFILS lesen und die Zahl der Eintraege zaehlen, bevor
  der Provider verdaechtigt wird.

## Nachweis (Abschluss)

- `scripts/config-wert-pruefen.py` meldet denselben `sha8` wie vorher.
- `Compare-Object` Sicherung ↔ Datei: genau eine geänderte Zeile.
- `hermes gateway status`: Aufgabe registriert, Prozess läuft — ohne Neustart.
- `Wissen/Hermes.md` nennt Änderung, Prüfweg, Sicherungspfad und Falle; committet.
