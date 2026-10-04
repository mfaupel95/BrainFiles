# Config gegen die Wirklichkeit pruefen (deklariert vs. real)

Anlass: "optimier meine Config" / "warum greift die Einstellung nicht" / nach einem
Update oder einer Fremdsitzung. Das Ergebnis ist ein Bericht mit Belegen, keine
Meinung - und die Reparatur nur an Stellen, die EINDEUTIG sind.

## Kernsatz

**Eine Config ist eine Sammlung von Behauptungen.** Jede Zeile sagt: dieser Pfad
existiert, dieser Dienst laeuft auf diesem Port, dieses Modell liegt im Store.
Faellt eine davon aus, meldet **nichts** einen Fehler - die Zeile wird erst
gebraucht, wenn der Hauptweg schon weggebrochen ist, und dann ist sie der letzte
Ausweg. Deshalb wird jede Behauptung EINMAL gegen die Wirklichkeit gehalten
(laufender Dienst, Dateisystem, offener Port), nicht gegen die Erinnerung und
nicht gegen die Nachbardatei.

## Ablauf

1. **Bestand aufnehmen, nicht raten.** Welche Config liest wer? `hermes config path`
   (CLI-Sicht), Prozess-Kommandozeile des Dienstes, `HERMES_HOME` als Benutzer- und
   als Prozessvariable. Bei Profilen: `profiles/*/config.yaml` mitzaehlen.
2. **Gegenprobe fahren (rein lesend):**

       cd Agenten/Hermes
       python scripts/config-gegenprobe.py          # Bericht, exit 1 bei Befund
       python scripts/config-gegenprobe.py --json

   Geprueft werden drei Dinge: `command:`-Pfade der `mcp_servers` gegen das
   Dateisystem, jede lokale Adresse (`127.0.0.1`/`localhost` mit Port) in Hauptconfig
   UND Profilen gegen einen echten TCP-Port, und jeder lokale Modellname (Provider
   `ollama-launch`, samt `models:`-Liste) gegen `/api/tags` des laufenden Ollama.
3. **Selbstpruefung des Werkzeugs im richtigen Kontext:** `hermes doctor` (Funde
   gegengliedern, nicht blind uebernehmen - die vorgeschlagenen Fixes zeigen oft auf
   eine andere Ursache), `hermes config check` (Exit 0 = YAML sauber),
   `hermes mcp test <name>` je Server, `hermes fallback list` je Profil.
4. **Eindeutiges selbst reparieren** (Pfad falsch, Wert ausserhalb des Bereichs,
   Modellname existiert nicht, Variable am falschen Ort) - mit Sicherung und Beleg.
5. **Strukturelles vorlegen** (Instanzen zusammenfuehren, Feature abschalten,
   Presets umbauen, Guthaben/Kosten) - als Tabelle Ist-Zustand + Plan + gebuendelte
   Frage. "Wenn du die Aenderung nicht in einem Satz begruenden kannst, ohne
   'vermutlich' zu sagen, gehoert sie in die Vorlage."
6. **Wache anschliessen, sonst ist die Gegenprobe wertlos.** Ein Nachweis, den
   niemand von selbst aufruft, ist keine Wache:

       python Agenten/Hermes/scripts/config-gegenprobe-wache.py --alle
       hermes cron create "every monday 7:40am" --name config-gegenprobe \
         --script config-gegenprobe-wache.py --no-agent --deliver telegram

   Sie meldet **nur Aenderungen** (neuer fehlender Pfad, neu tote Adresse, Modell aus
   dem Store gefallen), Merker in `cache/config-gegenprobe-wache.json`, leere Ausgabe
   = nichts senden. Beleg nach dem Anlegen: `hermes cron run <id>` + `hermes cron tick`,
   dann `hermes cron list` (Status ok).
7. **Doku nachziehen:** Wiki-Seite `MaxHirn/Wiki/Werkzeuge/config-gegenprobe.md`,
   Lektion in `Wiki/Lektionen/Wahrheit-pruefen.md`, offene Punkte als Tasks in
   `MaxHirn/Archiv/TASKS.md` (IDs fortlaufend).

## Was ein Befund ist - und was nicht

| Beobachtung | Urteil |
|---|---|
| Modellname im lokalen Provider steht nicht in `/api/tags` | **Befund** (Rueckfall greift nicht) |
| Adresse im Config-Block, Dienst dahinter tot, aber der zugehoerige Server arbeitet | **kein Befund** - Rest ohne Wirkung, nur aufraeumen |
| Adresse in `fallback_providers`/`providers` zeigt auf einen toten Port | **Befund** (der Weg wird gebraucht) |
| Port antwortet mit HTTP 200, aber es ist eine FREMDE Anwendung | **Befund** (falsche Zahl, der Dienst laeuft woanders) |
| Zwei Stellen behaupten dasselbe (Vorgabe `model:` und `models:`-Liste) | beide pruefen - eine richtig, eine falsch ist der Normalfall |
| Ein Aufruf scheitert mehrfach, der Turn endet aber trotzdem mit einer Antwort | **Befund mit Tarnung** - die Fallback-Kette hat ihn gerettet, der Nutzer sieht nichts (siehe *Abnahme*) |
| Ein Config-Wert benennt eine lokale Ressource (Schriftart, Modellname, Pfad, Port), die auf dieser Maschine nicht existiert | **Befund** - eine still falsche Zeile; der Leser faellt zurueck, ohne zu melden |
| Ein Auflisting zeigt die Konfiguration korrekt, der geaenderte Pfad lief aber nie durch | **kein Beleg** - das Listing liest die Datei, nicht den Weg (siehe *Nachweisstufen*) |

## Fallen (alle selbst erlebt)

- **Ein top-level Block erbt die Einstufung des vorigen.** Der erste Lauf meldete
  `auto/coding:free` als "nicht im Store", weil `fallback_providers:` in Spalte 0 die
  Einstufung "lokaler Provider" vom letzten `providers:`-Block geerbte. Fix im Pruefer:
  jede Zeile in Spalte 0 setzt die Einstufung zurueck. **Ein Pruefer ohne Gegenprobe
  erzeugt Reparaturen an gesunden Dateien** - immer einen Fall bauen, der rot werden
  MUSS, und einen, der gruen bleiben muss.
- **Der Port stimmt, der Dienst nicht.** `providers.bonsai` zeigte auf 8080; dort
  antwortete HTTP 200 - aber von der FreqTrade-Oberflaeche. Der Startbaustein hat 8081
  als Vorgabe. Zwei Zahlen fuer dieselbe Sache: die Zahl aus dem STARTER nehmen und
  die Antwort identifizieren, nicht nur den Statuscode.
- **Tote Modellnamen fallen erst im Notfall auf.** Vier Namen (`qwen3.8:27b`,
  `qwen3.8:latest`, `huihui_ai/qwen3-abliterated:32b`, `kimi-k2.7-code:cloud`) standen
  in `models:` von Hauptconfig + 17 Profilen; der Vorgabewert war am selben Abend schon
  gerichtet. Werkzeug: `Agenten/Hermes/scripts/lokale-modellliste-richten.py`
  (Trockenlauf Standard, `--anwenden`, `--zuruecknehmen`, je Datei `.bak`); es traegt
  nur Namen ein, die `/api/tags` bestaetigt.
- **Nicht jeder "unbekannte" Config-Schluessel ist ein Fehler, aber jeder ist eine
  Behauptung.** `hermes config get moa.enabled` antwortet "is not a recognized config
  key", `hermes moa list` meldet "Active in config: (off)" - die Top-Level-Schluessel
  des `moa:`-Blocks sind damit toter Text, gelesen werden `presets`/`default_preset`.
  Vor dem Entfernen in `hermes_cli/config_defaults.py` nachsehen, welche Schluessel die
  laufende Version liest; ein Preset, das einen toten Aggregator nennt, ist ein echtes
  Risiko (die ganze Werkzeugschleife laeuft dort).
- **Ein zu kleines `max_tokens` macht ein Denkmodell stumm - und den Pruefer blind.**
  Am 29.09.2026 lieferten `gemma-e4b-8k:latest`, `gemma-e4b-8k:cpu` und `deepseek-chat:latest`
  ueber Ollamas `/v1` bei `max_tokens: 90` einen LEEREN `content` mit `finish_reason: length`
  und dem Text im Feld `reasoning`. Mit `max_tokens: 2000` kam bei allen dreien sauberer
  `content` mit `finish_reason: stop` (gemma ganz ohne Denkanteil). Der Befund war ein
  **Artefakt meiner eigenen Sonde**, nicht ein Defekt der Konfiguration - haette ich ihn
  gemeldet, waere daraus eine Massenreparatur an 20 Profilen geworden. Regel: einen Aufruf
  immer mit realistischen Parametern messen (`max_tokens` wie im Betrieb), und eine
  Auffaelligkeit erst nach der Gegenprobe mit anderen Parametern als Befund ausgeben.
- **Eine lebende Adresse kann durch eine irrefuehrende Antwort tot aussehen.**
  `auto/best-free` antwortete ohne Authorization mit 403 ("OpenCode free tier only"),
  mit dem Hausschluessel mit 200 (bedient von claude-haiku-4-5). Vor "der Weg ist tot"
  den Aufruf MIT dem Schluessel aus der `.env` wiederholen - und den Schluessel nie
  ausgeben (`grep -E "^NAME=" .env | cut -d= -f2-` in eine Shell-Variable, nicht in
  die Kommandozeile).
- **Ein Modellname traegt keine Fensterzahl - sie ist eine Eigenschaft des Modells,
  und dieselbe Familie kann zwei verschiedene haben.** `gemma-e4b-8k` sah im
  `model_metadata` nach 8.192 aus, `/api/show` meldete fuer dieselbe Familie
  131.072. Ein Urteil ueber "zu kleines Fenster" faellt deshalb NIE aus dem
  Namen und NIE aus einer einzigen Quelle: Cloud-Modelle ueber
  `agent/model_metadata.py::get_model_context_length`, lokale ueber
  `/api/show` (Schluessel im `model_info` nach dem Muster `context` filtern,
  der heisst je nach Familie `gemma4.context_length`, `llama.context_length`, ...).
- **Ein unbekannter Modellname liefert eine VERMUTUNG, keine Messung.** Der Loader
  gibt eine Fallback-Zahl zurueck und schreibt eine Warnung auf stdout
  ("Could not determine context length ... falling back to 256,000") - die Zahl im
  Ergebnistext ist dann geraten. Ein unbekannter Name gegen einen bekannten
  Nachbarn aus derselben Familie pruefen, bevor er in eine Tabelle wandert.
- **Zeilenenden sind ein Beleg, kein Nebenschauplatz.** Nach jeder Massenaenderung
  `git diff --numstat` JE DATEI: 6/6 ist die gewollte Ersetzung, hunderte Zeilen heissen
  gekippte Enden. Fuer die Gegenprobe `read_bytes()`/`write_bytes()` nehmen und zaehlen:
  `b.count(b'\r') == b.count(b'\n')` in Arbeitsbaum UND `git show HEAD:<pfad>`.
  (Eine `grep -c $'\r'`-Zaehlung im MSYS-Terminal lieferte hier 0 fuer eine CRLF-Datei -
  nicht darauf bauen, Bytes zaehlen.)
- **`hermes config set` kann die Datei nicht zerschiessen, aber den Schwellenwert
  verstecken.** Nach jedem Set den Wert zuruecklesen UND die betroffene Zeile im
  Diff pruefen; `config set` schreibt die Datei neu (Kommentar-Schluss-Falle in
  references/fallen.md).

## Abnahme: eine fremde Config-Session pruefen ("funktioniert jetzt alles wie gewollt?")

Anlass: eine fruehere Sitzung hat die Config umgebaut, jetzt soll der Zustand
verifiziert werden. Das Ergebnis ist eine **Tabelle Behauptung -> Messung**, nicht
die Commit-Meldung.

1. **Die Sitzung ist ein Commit.** `git log --oneline -5`, dann
   `git show --stat <hash>` fuer die Dateiliste und `git show <hash> -- <pfad>` fuer
   jede Aenderung. Die Commit-Meldeliste ist eine **Absichtserklaerung, kein Beleg** -
   sie sagt, was gewollt war, nicht was traegt.
2. **Je Zeile einzeln messen.** `config get <schluessel>` pro geaendertem Schluessel,
   das Auflisting des betroffenen Blocks (`moa list`, `fallback list`, `profile list`,
   `cron list`), und EIN echter Aufruf durch den Hauptpfad. Eine Sammelpruefung
   ("config check exit 0") deckt nur die YAML-Syntax ab - sie sagt nichts darueber,
   ob ein Wert gelesen wird.
3. **Maskierung pruefen - der wichtigste Punkt.** Ein geaenderter Pfad kann
   vollstaendig tot sein, ohne dass es auffaellt, wenn eine Rueckfallkette die Antwort
   liefert. Der Beweis ist die **Fehlschlagspur im Log, nicht die Antwort**:
   `grep -E "provider=<geaendert>|error=" logs/agent.log` und die Zeilen danach lesen.
   Ein Aufruf, der dreimal mit Retry scheitert, den geaenderten Aggregator also nie
   erreicht, endet trotzdem mit einer guten Antwort auf dem Fallback - im Protokoll
   steht kein Fehler, den der Nutzer sieht. Ein geaenderter Pfad gilt erst als
   belegt, wenn er **einen Turn selbst vollendet** hat; ein Auflisting, das die
   Presets korrekt zeigt, beweist nur, dass die Datei lesbar ist.
4. **Fehlertext ohne Fundstelle im eigenen Baum ist fremd.** Bevor eine Aenderung
   verantwortlich gemacht wird: den Fehlertext im eigenen Quellbaum suchen. Kommt er
   dort nicht vor (weder Agent-Code noch SDK noch Relay), stammt er vom Endpunkt oder
   vom Transport - **nicht** von der just geaenderten Datei. Dann lautet das
   Ergebnis "die Konfiguration ist korrekt verdrahtet, der Weg scheitert extern",
   und die Massnahme ist eine Gegenprobe an einem anderen Pfad - nicht das Umstellen
   von Presets, die ein Listing gerade korrekt anzeigt.
5. **Beleg und Luecke getrennt melden.** Was gemessen wurde, gehoert in die Tabelle;
   was offen blieb, gehoert als **benannter offener Beleg** darunter, mit dem Lauf,
   der ihn liefert. Nie die offene Zeile in eine Tabelle schieben, deren Saetze alle
   mit "ja" enden.

## Beleg (Muster)

- `python scripts/config-gegenprobe.py` exit 0 bzw. 1 mit den offenen Punkten.
- `git diff --numstat` JE geaenderter Datei gegen die erwartete Zeilenzahl.
- `hermes fallback list` / `hermes -p <profil> fallback list` fuer jede Kette, die
  angefasst wurde.
- Fuer jedes "laeuft": den Endpunkt wirklich rufen (`POST <base_url>/chat/completions`)
  oder den Port oeffnen - nicht die Config zitieren.
- Wache: `hermes cron list` zeigt den Job mit Status ok; ein Lauf mit leerer Ausgabe
  ist der Beweis, dass sie schweigt, wenn nichts ist.

---

## Vollstaendiger Abschnitt aus dem SKILL.md-Rumpf

# Config gegen die Wirklichkeit pruefen (deklariert vs. real)


Trigger: "optimier meine Config", "warum greift die Einstellung nicht", nach einem
Update oder nach fremder Sitzungsarbeit. Der Befund kommt aus der Sache, nicht aus
der Datei.

**Kernsatz: eine Config ist eine Sammlung von Behauptungen** (Pfad existiert, Port
laeuft, Modell liegt im Store). Faellt eine aus, meldet NICHTS einen Fehler - sie wird
erst gebraucht, wenn der Hauptweg weggebrochen ist. Jede Behauptung einmal gegen die
Wirklichkeit halten, nie gegen die Erinnerung.

1. Gegenprobe fahren (rein lesend, exit 1 = Befund):

       cd Agenten/Hermes
       python scripts/config-gegenprobe.py            # Pfade, lokale Adressen, lokale Modellnamen

2. Eindeutiges selbst reparieren (toter Modellname, falscher Port, Wert ausserhalb des
   Bereichs), Strukturelles vorlegen (Feature abschalten, Presets umbauen, Instanzen
   zusammenfuehren).
3. Wache anschliessen - ein Nachweis, den niemand aufruft, ist keine Wache:

       hermes cron create "every monday 7:40am" --name config-gegenprobe \
         --script config-gegenprobe-wache.py --no-agent --deliver telegram

   Die Wache meldet nur AENDERUNGEN (leere Ausgabe = nichts senden).

Werkzeuge: `scripts/config-gegenprobe.py`, `scripts/config-gegenprobe-wache.py`,
`scripts/config-abweichungen.py` (rein lesend, mit dem venv-Python: listet jeden Wert, der
vom Hermes-Standard `DEFAULT_CONFIG` abweicht - die Tabelle, mit der eine "optimier meine
Config / setz das auf Standard"-Frage beantwortet wird, statt Werte zu raten),
`scripts/lokale-modellliste-richten.py` (Trockenlauf Standard, `--anwenden`,
`--zuruecknehmen`). Vollstaendiger Ablauf, Urteilstabelle und die Fallen (geerbte
Provider-Einstufung = Fehlalarm, HTTP 200 von einer FREMden Anwendung, toter Port der
harmlos ist, irrefuehrendes 403 ohne Schluessel): `siehe oben in dieser Datei`.
