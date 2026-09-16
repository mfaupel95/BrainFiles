---
name: hermes-config-ops
description: "Hermes-Config, .env, Benutzervariablen und Ausgabestil (SOUL.md) ändern — belegt."
version: 0.1.0
author: Hermes Agent
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
3. **Der Anmeldeschritt gehoert dem Nutzer.** OAuth laeuft im Browser gegen
   SEIN Konto und laesst sich von einem Agenten nicht abschliessen — als
   offenen Schritt melden („Kandidat, ein Klick fehlt"), nie als erledigt.
4. **Im Ergebnis trennen, was live geprueft ist und was aus der Doku stammt.**
   Handschlag und Werkzeugliste sind pruefbar; Metriknamen, Feldlisten und
   Tarifgrenzen stehen oft nur in der Anbieter-Doku. Beides ausdruecklich
   benennen — ein „funktioniert" ohne diese Trennung ist eine Behauptung.
5. **Erst danach der Manifest-Eintrag**, und als Kandidat mit Begruendung:
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

**Nachweis:** `git diff --stat` muss additiv aussehen (viele Zeilen rein, nur
die eigene Ersetzung raus). Ein Diff, der mehr loescht als hinzufuegt, hat
fremde Arbeit verschluckt. Danach `hermes config get` fuer jeden angefassten
Schluessel, und die Datei einmal als YAML parsen lassen, BEVOR sie geschrieben
wird — bei einer Config gibt es keinen `ast.parse`, aber `yaml.safe_load` auf
dem neuen Text im Speicher leistet dasselbe (dazu die erwarteten Invarianten
als `assert`: Typ der Liste, Zahl der Eintraege, kein toter Schluessel mehr).

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

- **Ein Umgebungsvariablen-Namen kann ein Tippfehler sein — Namen aus der Registry lesen, nicht eine Kandidatenliste abfragen.** Im Ist-Stand stand `#ANTHROPIC_API_KEY` (mit Rautenzeichen!) und `ANTHROPIC_API_KEY_BILLING`; der kanonische `ANTHROPIC_API_KEY`, den Hermes' Provider-Profil liest, fehlte. Eine Abwesenheitsmeldung ist erst gueltig, wenn die Namen aufgelistet wurden: `(Get-Item HKCU:\Environment).GetValueNames()`, dann je Name Laenge und SHA-256-Anfang der Kandidaten vergleichen — gleicher Hash = derselbe Wert, und das Setzen ist ein Umbenennen, kein neues Geheimnis.
- **Ein Provider braucht oft keinen Block in `providers:`.** Hermes' eingebaute Model-Provider-Profile (`hermes-agent/plugins/model-providers/<name>/__init__.py`) bringen `base_url`, `api_mode` und `env_vars` selbst mit — fuer Anthropic sind das `https://api.anthropic.com`, `anthropic_messages` und `(ANTHROPIC_API_KEY, ANTHROPIC_TOKEN, CLAUDE_CODE_OAUTH_TOKEN)`. Ist die Variable gesetzt, ist der Provider da; ein zusaetzlicher Eintrag in `config.yaml` ist hoechstens eine zweite Wahrheit.
- **Fuer Provider-Anmeldedaten braucht das laufende Gateway KEINEN Neustart.** Sie kommen aus dem Credential-Pool (`auth.json`) und der `.env` des Profils, nicht aus der Prozessumgebung: ein `delegate_task`-Kind lief sofort mit `provider=anthropic model=claude-opus-5` (Logzeile `platform=subagent … id=msg_…`). Wer „greift erst nach Neustart" behauptet, muss diesen Unterschied zeigen — er gilt nur fuer `${env:NAME}`-Verweise.
- **`patch` und `write_file` auf `config.yaml` sind gesperrt** („Refusing to write to Hermes config file", bei der AppData-Config zusaetzlich `HERMES_WRITE_SAFE_ROOT`). Zwei Wege bleiben, und sie sind nicht gleichwertig: `hermes config set …` fuer den EINZELNEN Wert (auch fuer Listen — der Wert wird als YAML/JSON geparst, `'[{"provider":"omniroute","model":"auto/best-coding"}]'` funktioniert), und ein Wegwerf-Skript unter `Agenten/Hermes/cache/`, das die Datei binaer liest, chirurgisch ersetzt und zurueckschreibt — fuer eine Zusammenfuehrung mit mehreren Hunks. Das Skript ist dort das BESSERE Mittel, weil `hermes config set` die Datei neu schreibt und dabei den Kommentar-Schluss abschneidet (naechste Falle). Fuer das Skript gelten dieselben Regeln wie fuer jede Textaenderung: Zeilenenden binaer feststellen (`b"\r\n" in raw`) und erhalten, je Ersetzung `count == 1` asserten, den NEUEN Text vor dem Schreiben mit `yaml.safe_load` pruefen, vorher `.bak-JJJJMMTT`.
- **`hermes config set` schneidet den Kommentar-Schluss der Datei ab.** Es schreibt die ganze Datei neu; ein Dokumentationsblock am Dateiende (Beispiele fuer `security:`, `fallback_model:`) ist danach weg — funktional harmlos, aber eine stille Aenderung an der Datei des Nutzers. Nach **jedem** `config set` diffen und den Block zurueckholen (`Agenten/Hermes/cache/config-schluss-wiederherstellen.py --tun`), sonst waechst bei jeder Aenderung eine unsichtbare Differenz. Die Aenderung selbst sieht im Diff wie eine Zeilenersetzung aus — genau pruefen, ob noch mehr fehlt.

## Nachweis (Abschluss)

- `scripts/config-wert-pruefen.py` meldet denselben `sha8` wie vorher.
- `Compare-Object` Sicherung ↔ Datei: genau eine geänderte Zeile.
- `hermes gateway status`: Aufgabe registriert, Prozess läuft — ohne Neustart.
- `Wissen/Hermes.md` nennt Änderung, Prüfweg, Sicherungspfad und Falle; committet.
