# Node/TypeScript-MCP- und CLI-Tools aus Fremd-Repos starten

## Wann
Ein Repo aus der awesome-trading-agents-Liste (oder allgemein) ist ein
Node/TypeScript-Tool: MCP-Server, CLI, oder beides. Beispiel: okx/agent-trade-kit
(okx-trade-mcp + okx-trade-cli, v1.4.7).

## Die awesome-trading-agents-README ist eine kuratierte LISTE, kein Programm
~100 Projekte (Agents/MCPs/Skills), nur Markdown — es gibt kein "das Programm".
Erst ein Projekt auswaehlen (bei Max: passend zum Stack — OKX/Kraken,
Papier-zuerst, lokale Modelle), dann das Repo klonen. Nicht raten, welches
Projekt gemeint ist; bei fehlender Antwort den Stack-passenden Default nehmen
und im Bericht nennen.

## Vorgehen
1. **Repo klonen** nach Werkstatt/Repos/<name> (Hauskonvention).
2. **README lesen** — Quickstart. Zwei Wege: (a) npm-Globalinstall der
   veroeffentlichten Pakete (schnellster Weg, kein Build), (b) Build from
   source (`pnpm install && pnpm build`) nur fuer Entwicklung.
3. **npm-Globalinstall:** `npm install -g <pkg1> <pkg2>`. Node >= 18 noetig.
   Die `allow-scripts`-Warnung (postinstall-Skripte nicht ausgefuehrt) ist
   NICHT blockierend — die Binaries laufen trotzdem.
4. **Binaries auf PATH:** `export PATH="$PATH:$(npm prefix -g)/bin"` — die
   globalen Binaries liegen in AppData/Roaming/npm, nicht im MSYS-PATH.
5. **Ohne Keys verifizieren:** das Marktmodul braucht keine API-Keys.
   `okx market ticker BTC-USDT` liefert echte Daten → CLI laeuft.
6. **MCP-Server verifizieren (stdio):** JSON-RPC-Handshake per Pipe an den
   Server schicken und mit timeout begrenzen (er wartet sonst auf stdin):
   `echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 20 okx-trade-mcp --modules market`
   → antwortet mit serverInfo. Dann `tools/list` → Tool-Namen zaehlen.
7. **Keys:** NIE aus dem Vault lesen (Wissen/Zugaende.md ist gesperrt). Der
   Nutzer richtet Keys selbst ein (`okx config init`, interaktiv, lokal).
   Trading-Module erst nach expliziter Freigabe.

## Pitfalls
- **MCP-Toolnamen vs CLI-Subcommands unterscheiden:** MCP nutzt Unterstriche
  (`swap_place_algo_order`), CLI nutzt Leerzeichen (`okx swap algo place`).
  MCP-Identifikatoren NICHT in Bindestrich-CLI umwandeln (`okx swap place-algo`
  ist ungueltig).
- **`--read-only`-Flag** fuer reine Query-Nutzung; das Marktmodul ist von Haus
  aus ohne Auth nutzbar.
- **MCP-Server ist ein stdio-Prozess** — er wartet auf stdin; ein Test muss den
  Handshake per Pipe senden und mit timeout begrenzen, sonst haengt er.

## Ein veroeffentlichtes CLI-Paket installieren (nicht den Klon bauen)

Nennt die README den npm-Weg, ist das PAKET die Wahrheit, nicht der Klon. Zwei
Manifest-Eigenheiten des Autors entscheiden ueber Erfolg oder Abbruch:

- **`"os": ["darwin","linux"]` im Paket** laesst `npm install -g` mit
  `EBADPLATFORM` abbrechen. `--force` umgeht die Pruefung, und reine JS/WASM-
  Pakete laufen danach unter Windows. Vor der Aussage "laeuft" drei Belege
  fahren: `--version`, `--help` und einen Lauf, der echte Arbeit tut.
- **`devDependencies` mit `workspace:*` in der veroeffentlichten
  package.json** (Monorepo-Artefakt) laesst die Installation als PROJEKTWURZEL
  mit `EUNSUPPORTEDPROTOCOL` scheitern. Als ABHAENGIGKEIT installiert npm
  dasselbe Paket problemlos — npm liest devDependencies fremder Pakete nicht.

**Nicht global installieren.** Das globale Prefix ist hier der Hermes-eigene
`tools/node-*`-Baum, den ein `hermes update` ersetzt — das Binary verschwindet
dann still. Hausform: eigener Ordner `Agenten/Werkzeuge/<name>/` mit gepinnter
Version (`npm install <paket>@<version> --force`), dazu ein Aufrufer
`<name>.cmd` (CRLF, ruft nur `node` aus dem PATH und meldet klar, wenn Node
fehlt) und ein Wurzel-Aufrufer `/<name>.cmd` nach dem Muster `omnitrade.cmd`.

**Zweite Hausform fuer ein CLI, das man mit NAMEN aufruft:**
`npm install -g --prefix "C:/Users/faupe/.local/npm" <paket>@<version>` — npm
legt seine Shims (`<name>`, `<name>.cmd`, `<name>.ps1`) direkt in den Prefix,
der Prefix kommt in den Benutzer-PATH (Rezept unten), und es bleibt ein echter
npm-Baum: `npm install -g --prefix <derselbe> <paket>@latest` aktualisiert ihn.
Beide Formen sind richtig; falsch ist nur der Hermes-eigene `tools/node-*`-Baum.
In `.gitignore` die eigenen Dateien freigeben (Aufrufer, README, Test,
package.json/-lock) und `node_modules` sperren; je Pfad mit
`git check-ignore -v` gegenproben.

**Den Aufrufer aus der MSYS-Bash mit NATIVEM Pfad testen:**
`cmd /c "C:/.../jevgrep.cmd --version"` und den Exitcode pruefen. Die
MSYS-Schreibweise `cmd //c "name.cmd --version"` gibt nur den cmd-Banner aus,
OHNE den Befehl auszufuehren — das sieht wie ein kaputter Aufrufer aus, ist aber
nur die Aufrufweise. Nach dem Bau ausserdem die Datei auf CRLF bringen
(`write_file` schreibt LF; ohne CRLF brechen Sprungmarken und Bloecke).

## Ohne Schluessel verifizieren: den Dienst attrappieren

Ein Werkzeug, das ein fremdes Modell/einen fremden Dienst befragt, ist ohne
Kauf vollstaendig nachweisbar — Attrappe lokal starten, Werkzeug dagegen
zeigen, echte Ausgabe lesen:

1. Protokoll aus dem Code lesen (Endpunkt-Pfad, Koerperform, erwartete Antwort)
   und einen stdlib-HTTP-Server bauen, der jede Anfrage beantwortet und
   mitprotokolliert (Pfad, Modell, Fragezahl, Groesse der Nutzlast, Auth-Kopf).
2. **Die Konfigurationsablage des Werkzeugs umbiegen** (`XDG_CONFIG_HOME` auf
   einen Tempordner), sonst schreibt der Test seine Attrappen-Anmeldung in die
   ECHTE Ablage des Nutzers; danach pruefen, dass die echte unberuehrt ist.
3. Die Attrappe braucht einen Testfall, der ohne sie ROT wird: Anfragen
   ZAEHLEN und Inhalt pruefen (Pfad, Bearer-Kopf, mitgeschickte Nutzlast) —
   sonst belegt der gruene Lauf nur, dass nichts abstuerzt.
4. Attrappen-Anmeldung und Cache nach dem Nachweis LOESCHEN, damit kein
   Scheinzustand liegenbleibt.

## Kosten und Anbieter VOR der Empfehlung pruefen

- **Den vorgegebenen Anbieter gegen den echten Katalog stellen.** Ein Preset
  kann auf ein Modell zeigen, das der Anbieter nicht fuehrt. Der Modellkatalog
  ist oeffentlich lesbar — vor jeder Kaufempfehlung nachsehen.
- **Erst nach einer GRATIS-Variante DESSELBEN Modells beim Anbieter suchen,
  bevor „braucht einen bezahlten Schluessel" berichtet wird.** Anbieter fuehren
  neben der bezahlten ID oft eine kostenlose unter DEMSELBEN Protokollpfad
  (Muster `<modell>-free`), und der Preset des Werkzeugs zeigt regelmaessig auf
  die bezahlte. Dann den EIGENEN Endpunkt anmelden statt zu kaufen:
  `--provider custom --base-url <pfad-des-presets> --model <modell>-free`.
  Zwei Belege vor der Aussage: der Protokollpfad in der Anbieter-Dokumentation
  ist derselbe, den der Preset nutzt, und die Preistabelle des Anbieters nennt
  die freie ID in Ein- UND Ausgabe als frei. Ein Werkzeug, das ohne Schluessel
  nur seine Zaehlfunktion kann, ist damit trotzdem vollstaendig nutzbar.
- **Preis je Lauf aus dem EIGENEN Probelauf rechnen**, nicht aus dem Datenblatt:
  Anfragen x Nutzlast-Token x Listenpreis. Die Wurzel ist die Stellschraube,
  nicht die Frage.
- **Ein lokales Modell als Ersatz vorher durchrechnen**, statt es zu bauen:
  Prompt-Token je Lauf / Prompt-Durchsatz (t/s) = Laufzeit. Ergibt das Stunden,
  ist der Gratisweg keine Option; ein Klassifikator mit kleinem Kontext passt
  schon von der Laenge nicht. Die Rechnung ersetzt den Bauversuch.
- **Datenschutz-Tor vor dem ersten echten Lauf:** bei einem Werkzeug, das
  Quelltext an einen Dienst schickt, zuerst dessen eigene Zaehlfunktion laufen
  lassen (kostenlos, kein Netz), Ausschlussmuster setzen, Wurzel bewusst
  waehlen. Vault und Schluesselordner gehoeren nicht hinein — die Filter des
  Herstellers sind keine Garantie.
- **Fremde SKILL.md nicht in die Hermes-Bibliothek importieren.** Ein
  mitgeliefertes Installationskommando dafuer NICHT ausfuehren; den Text im
  Paket benennen und das Wissen in einer Wiki-Seite ablegen.

## Ein Client mit eigenem Modell-Protokoll: die eigene Bruecke

Manche Werkzeuge fragen keinen Chat-Endpunkt, sondern einen **Richter**: sie schicken
einen Zustand plus typisierte Fragen und erwarten je Frage einen Wert (Muster: `POST
<basis>/systemone`, `{state, questions:{id:{type:"noul"}}} ->
{answers:{id:{type:"noul", noul:0..1}}}`). Solch einen Vertrag bedient ein kleiner
lokaler stdlib-Server, der ihn auf ein beliebiges OpenAI-kompatibles Modell uebersetzt
(lokal, gekaufter Anbieter, eigener Router). Damit wird der Client unabhaengig vom
Anbieter, den sein Preset vorsieht.

**Voraussetzungen messen, nicht annehmen** — und zwar an der Nutzlast des Clients:
Kontextfenster (der Client schickt schnell 20.000-54.000 Zeichen Zustand, also **32k+"),
Buendelung (mehrere Fragen je Anfrage), sauberes JSON, und die **Latenz gegen den Takt
des Aufrufers**. Gebuendelte Recherche vertraegt Sekunden je Anfrage; ein Takt von
Millisekunden (eine Entscheidung je Block) vertraegt sie nicht — dort gehoert der echte
Anbieter hin, nicht die Bruecke.

Drei Regeln, jede aus einer Messung:

- **Ein leeres Modell-Ergebnis NIE still als Standardwert durchreichen.** Antwortet das
  Modell nichts (zu kleines Kontextfenster, Abbruch), darf die Bruecke daraus kein
  „nicht relevant" machen — sonst meldet der Client ein sauberes Ergebnis, waehrend der
  Anbieter kaputt ist. Fehler je Anfrage protokollieren UND auf der Konsole warnen; dem
  Client trotzdem eine gueltige Antwortform liefern (er darf nie einen 5xx sehen).
- **Ein veralteter Modell-Tag ist derselbe Fehler.** Eine Vorgabe, die der Dienst nicht
  mehr fuehrt, ergibt `HTTP 404` bei JEDER Frage -> alle Ergebnisse fallen auf den
  Standardwert. Die Modellliste des Dienstes lesen (`GET /v1/models`), nicht dem eigenen
  Vorgabewert glauben.
- **Die Anmeldung des Clients ist EINFACH:** ein `auth`-Aufruf ERSETZT die gespeicherte
  Anmeldung samt Endpunkt, es gibt keine zwei Anbieter nebeneinander. Vor jedem
  Umstellen den Rueckweg als EINEN Befehl bereithalten (Hausform: ein
  Anmelde-Werkzeug mit `--anwenden`), sonst ist der alte Zugang weg.
- **Lokal als Richter vorher bemessen.** Mechanisch laeuft es oft, fachlich nicht:
  gemessen 51 s fuer 20.000 Zeichen Zustand und die FALSCHE Antwort auf eine Frage, zu
  deren Antwort die Datei genau passt — waehrend eine Einzelmessung desselben Modells
  vorher einen plausiblen Wert geliefert hatte. Mit ECHTER Nutzlast und einer Frage
  messen, deren Antwort man selbst kennt; eine Einzelmessung ist kein Urteil.

## Wenn der Hersteller einen eigenen Installer mitbringt

Manche CLIs haben einen eigenen Unterbefehl `install` ("managed install":
Payload-Store unter `~/.<name>/cli`, Shim in `~/.local/bin`, Ein-Befehl-Update,
Rollback, Hintergrunddienst). Unter Windows ist dieser Weg oft **nicht
benutzbar** — dann ist der npm-Weg nicht der Notausgang, sondern der einzige:

- **Ein Sperr-/Temp-Dateiname aus einem `:`-verbundenen Token ist unter Windows
  unmoeglich.** Der Installer baut den Namen aus `<pid>:<zeit>:<zufall>`
  (Unix-legal) und scheitert beim Anlegen mit `ENOENT: no such file or
  directory, open '...\.install.lock.<pid>:<zeit>:<zufall>.tmp'`. **Nicht
  Rechte, Pfad oder Virenscanner verdaechtigen** — die Ursache mit einem
  Zwei-Zeilen-Test beweisen: denselben `fs.writeFileSync` einmal MIT und einmal
  OHNE Doppelpunkt im Namen schreiben; ohne geht, mit kommt ENOENT. Danach ist
  die Frage entschieden und der Umweg begruendet.
- **Solche Stores sind zusaetzlich Unix-gepraegt** (Shim nach `~/.local/bin`,
  Block in `.bashrc`/`.zshrc`, Symlink `current`). Auch mit gefixtem Dateinamen
  bliebe es Arbeit — deshalb gar nicht erst dorthin umziehen.
- **KEINEN selbstgebauten Shim auf den Pfad legen, den der Hersteller fuer seine
  verwaltete Installation reserviert** (typisch `~/.local/bin/<name>`). Die
  werkzeug-eigene Diagnose zaehlt die blosse EXISTENZ dieses Pfades (neben
  `install.json`, `.managed-install`, `current`) als "verwaltete Installation
  vorhanden"; ein nackter Shim macht daraus eine halbe Installation und
  **blockiert den Start** ("Managed install artifacts exist but …install.json is
  missing" -> "Doctor found blocking issues. Not starting server."). Stattdessen
  den npm-Prefix selbst in den PATH legen.
- **PATH unter Windows anhaengen: `[Environment]::SetEnvironmentVariable('Path',
  $neu, 'User')`** — NICHT `setx`, das schneidet bei 1024 Zeichen ab. Den
  bestehenden Wert lesen, den eigenen Eintrag nur anhaengen, danach zuruecklesen
  und die Zugehoerigkeit pruefen. **Die laufende bash-Sitzung erbt den ALTEN
  PATH**: fuer eigene Aufrufe den vollen Pfad nehmen oder
  `export PATH="$PATH:<prefix>"`, und den Namen mit einem NEUEN Prozess
  gegenproben (`powershell.exe -NoProfile -Command "<name> --version"`,
  `cmd /c "<name> --version"`).
- **npm >= 11 fuehrt `postinstall`-Skripte nicht ohne Freigabe aus**
  (`allow-scripts`). Vor dem Nachinstallieren pruefen, ob das uebersprungene
  Skript ueberhaupt etwas taete — im belegten Fall war seine Eingabedatei eine
  leere Liste, das Skript also wirkungslos. Erst dann ist die Warnung harmlos;
  sonst einmal mit `--allow-scripts=<paket>` freigeben.
- **Der erste Start eines Werkzeugs mit eingebetteter Datenbank sieht wie ein
  Haenger aus** (initdb + Migrationen; gemessen ~3 min, nach "Starting …
  server…" kommt minutenlang nichts). **Fortschritt am DATENORDNER messen**
  (`db/PG_VERSION`, `db/pg_wal` entstehen), nicht am Log — und den Start erst
  als fertig melden, wenn die angekuendigte Adresse antwortet
  (`curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:<port>/` -> 200).
  Host, Port, PID und Dashboard-URL stehen in der Laufzeitdatei des Werkzeugs
  (`runtime-info.json`) — von dort lesen statt raten.
- **Ein Dienst-Schalter kann auf Windows grundsaetzlich fehlen** ("Service
  management is not supported on win32"): dann gibt es keinen Autostart, und der
  Bericht muss sagen, dass der Prozess mit dem Startenden endet — Wrapper plus
  geplante Aufgabe sind die Hausantwort.
- **Die Anmeldung ist ein eigener Schritt.** Nach dem Start hat die CLI noch
  keine Identitaet; die Diagnose darf gruen sein, waehrend jeder Datenbefehl
  verweigert. Der Weg hinein ist meist die Oberflaeche im Browser (Sign-up
  erlaubt) oder `connect`, und ein Token-Unterbefehl verlangt VORHER eine
  bestehende Sitzung. Das im Bericht als offenen Punkt nennen, nicht als Fehler.
- **Ein Schluessel, der zwischen zwei Werkzeugen wandert, wird nie angezeigt.**
  Hat das Quell-Werkzeug einen eigenen Login (`<cli> auth login`, Ablage z. B.
  `~/.local/share/<cli>/auth.json`), den Wert von DORT lesen, per stdin an die
  Anmeldung des Zielwerkzeugs reichen (`auth ... --stdin`) und nur die LAENGE
  melden. Ein kleines Hausskript dafuer: Trockenlauf als Standard, `--anwenden`
  zum Schreiben, `--datei`/`--basis` als Testnaht; ohne Quelle gibt es die
  Anleitung aus (welcher Befehl den Login anlegt), statt zu raten. Der Test
  prueft BEIDES — der Wert steht in der Zieldatei des Zielwerkzeugs UND in
  keiner Ausgabe, auch nicht in einer Fehlermeldung. Die Ablage des Zielwerkzeugs
  fuer den Test umbiegen (siehe Attrappen-Abschnitt), damit die echte Anmeldung
  des Nutzers unberuehrt bleibt.
- **Quelle kann auch eine Windows-BENUTZERVARIABLE sein** (der Nutzer legt den
  Schluessel als `<ANBIETER>_API_KEY` ab und will ihn von dort genutzt haben).
  Dann direkt aus der Registry lesen — `winreg.OpenKey(HKEY_CURRENT_USER,
  "Environment")` bzw. `HKEY_LOCAL_MACHINE`, dann `QueryValueEx`. **Nicht per
  `reg query`** (gibt den Wert im Klartext aus) und **nicht nur aus der
  Prozessumgebung**: ein frisch gesetztes `setx` sieht ein laufender Prozess
  nicht, die Registry-Ablage dagegen sofort. Reihenfolge im Werkzeug:
  Prozessumgebung -> Registry (HKCU, dann HKLM) -> Anmeldedatei des Quell-CLI.
- **Ein Quellen-Schalter ist Pflicht, sobald die echte Variable auf der Maschine
  steht.** Sonst liest jeder Test die ECHTE Variable statt seiner Attrappe und
  wird still falsch (der Test „keine Quelle vorhanden" scheitert, obwohl der
  Code stimmt). Form: `--quelle auto|umgebung|datei`; Tests fahren `datei`,
  und ein eigener Test setzt die Variable im KINDPROZESS und prueft, dass die
  Quelle „Prozessumgebung" gewinnt UND der Wert in keiner Ausgabe steht.

**Ein sofortiger Abbruch (Exit 1, leere Ausgabe) ist nicht an den Vordergrund
gebunden — wiederholen und die Wurzel verengen.** Gemessen: ein solcher Lauf kann
schon nach 0,2 s mit Exit 1 enden und als einzige Zeile `stdin is not a tty`
ausgeben (ein MSYS-Artefakt, das auch bei GELUNGENEN Laeufen erscheint, also nicht
die Ursache ist) — im Hintergrund, im Vordergrund und mit stdin aus `/dev/null` oder
einer Datei gleichermassen. Andere Wurzeln liefen im selben Zeitfenster
reproduzierbar durch, dieselbe Frage ueber eine andere Wurzel ebenfalls. Deshalb:
Ausgabe in eine Datei umleiten und die DATEI lesen, den Lauf einmal wiederholen und,
wenn er wieder abbricht, die Wurzel auf Reparse-Punkte pruefen (Junctions loesen sich
fuer den Dateilauf nicht auf) und auf einen echten Unterordner ausweichen. Fuer die
Belegzeile zaehlen Exit-Code UND Inhalt der Datei, nicht die Laenge des Logs.

**Die erste echte Suche ist der Nachweis, nicht der gruene Probelauf.** Ein
Werkzeug, das fremde Urteile einkauft, wird erst durch einen echten Lauf ueber
eine echte Wurzel bewiesen: Dauer, Exit-Code und die Namen der zurueckgegebenen
Dateien im Bericht nennen — und pruefen, ob die Treffer die Frage wirklich
treffen (eine Liste bekannter Dateien ist noch kein Urteil).

## Ein Werkzeug, das ein CLI per NAMEN startet (Adapter, Sonden, Test-Knopf)

Werkzeuge mit Adapter-/Sonden-Konzept (Paperclip, MCP-Clients, Test-Suiten)
loesen den CLI-Namen selbst auf — ueber `PATH` und `PATHEXT` des EIGENEN
Prozesses. Unter Windows trifft das **das npm-Shim `<name>.CMD`**, und
`child_process.spawn` ohne `shell:true` kann `.cmd`/`.bat` nicht starten: Node
wirft `EINVAL`, das Kind startet nie, und das Werkzeug meldet eine
nichtssagende Ursache (`nonzero_exit`, „The environment test failed“). **Nicht
die Logik des Werkzeugs debuggen, sondern den Start nachstellen:**

```js
const {spawnSync} = require('child_process');
const r = spawnSync('C:/Users/<user>/AppData/Roaming/npm/<name>.CMD', ['--version'],
                    {shell: false, env: {PATH: 'C:/Users/<user>/.local/bin;C:/Windows/System32'}});
console.log(r.status, r.error && r.error.code);   // status=null, error=EINVAL
```

**Fix: die native Fassung des CLIs installieren**, damit ein `.EXE` existiert
(`claude install stable` legt `~/.local/bin/claude.exe` ab). Die Aufloesung geht
die PATH-Verzeichnisse der Reihe nach durch und probiert je Verzeichnis die
Endungen in PATHEXT-Reihenfolge — ein `.exe` in einem FRUEHEREN Verzeichnis
gewinnt. Danach beides gegenproben:

- **Die Aufloesung nachbauen** statt die PATH-Reihenfolge anzunehmen: dieselbe
  Schleife (Verzeichnisse aus `PATH`, Endungen aus `PATHEXT`, `fs.accessSync`)
  in einem Zehn-Zeilen-Skript laufen lassen und den gefundenen Pfad ausgeben —
  sie muss die `.exe` liefern.
- **Die Sonde selbst nachfahren**, mit dem Minimal-Env, das das Werkzeug baut
  (oft nur `PATH`): dieselben Argumente, dieselbe stdin-Eingabe, Exitcode und
  das Ergebnis-Feld pruefen. Eine Umgebung, die „sauber“ gebaut wird, reicht nur
  wenige Variablen durch — eine Gegenprobe mit der eigenen vollen Shell beweist
  deshalb nichts.

Dieselbe Falle trifft **jeden** lokalen Adapter, dessen CLI nur als npm-Shim
vorliegt (codex, cursor, gemini, grok). Sagt die Oberflaeche nur
„fehlgeschlagen“: **den Meldungstext im ausgelieferten UI-Bundle suchen**
(`grep -rl "<Meldungstext>" --include=*.js .`) und die Bedingung dort lesen —
so ist belegt, ob eine WARNUNG ueberhaupt blockiert oder nur `status === "fail"`
beziehungsweise ein bestimmter Pruefcode.

## Das Arbeitsverzeichnis entscheidet ueber die Umgebung

**Symptom:** derselbe Befehl laeuft aus der eigenen Shell durch und im Werkzeug
scheitert er. **Erste Frage: was steht in der Prozessumgebung des Werkzeugs?**
Viele Werkzeuge laden beim Start eine `.env` aus ihrem ARBEITSVERZEICHNIS
(dotenv ohne Pfad) und reichen die Prozessumgebung an jedes Kind weiter (Sonde,
Adapter, Agent). Liegt im Startverzeichnis eine `.env` mit einem Schluessel, den
das Kind kennt (typisch `ANTHROPIC_API_KEY`), benutzt das Kind DIESEN statt der
angemeldeten Sitzung: 401, nichtssagender Exit-Code, „Umgebungstest
fehlgeschlagen“. Aus der eigenen Shell faellt das nie auf, weil die Shell keine
`.env` laedt.

- **Der Befund steht in der Meldung des Werkzeugs selbst.** Sonden melden
erkannte Konkurrenz-Variablen ausdruecklich („…API_KEY is set. … will use
API-key auth instead of subscription credentials“). Wer das liest, hoert auf zu
raten; wer nur den Exit-Code sieht, sucht tagelang am falschen Ende.
- **Ein `unset` vor dem Start hilft NICHT** — die Datei wird beim Start erneut
geladen. Der Fix ist das Arbeitsverzeichnis: aus einem Ordner ohne fremde
`.env` starten (`~/.<werkzeug>` bietet sich an), und den Start-Wrapper so bauen,
dass er dieses Verzeichnis setzt (`-WorkingDirectory` bzw. `cd` in der `.cmd`).
- **Gegenprobe als MATRIX**, nicht als Einzelmessung: dieselbe Sonde einmal aus
dem vergifteten Verzeichnis, einmal aus dem sauberen — und zusaetzlich einmal
mit dem Schluessel in der Rolle, in der er erwartet wird. Erst der Unterschied
zwischen den Zeilen belegt die Ursache.
- **Die `.env` im Home nicht anfassen** (sie traegt Schluessel des Nutzers): im
Bericht als Falle benennen, im Wiki festhalten. Jedes dort gestartete Werkzeug
erbt sie.

## Die Sonde des Werkzeugs selbst fahren, statt den Nutzer klicken zu lassen

Ein Werkzeug mit Test-Knopf ist ueber seine eigene Schnittstelle reproduzierbar —
das liefert die vollstaendige Pruefliste und macht jede Aenderung sofort
nachmessbar:

1. **Die Pruefungen im ausgelieferten Code lesen** (`node_modules/<paket>/…/server/`):
   dort steht, welchen Befehl, welche Argumente, welches Arbeitsverzeichnis und
   welche Umgebung die Sonde baut — und welche Pruefcodes als Fehler gelten
   (Warnungen blockieren meist nicht).
2. **Den Endpunkt aus der Schleife aufrufen.** Im Modus „nur lokaler Rechner“
   (`local_trusted`) nimmt so ein Dienst Anfragen von `127.0.0.1` OHNE Anmeldung
   an. Pfad und Koerperform aus der OpenAPI-Beschreibung des Werkzeugs nehmen
   (`grep -rn "<route>" --include=*.js`), die IDs (Firma, Umgebung) aus der
   eingebetteten Datenbank.
3. **In die eingebettete Datenbank sehen**, wenn die Oberflaeche Werte nicht
   zeigt — Port und Zugang stehen in der Konfiguration des Werkzeugs. Von einem
   Geheimnis **nur Laenge und Art ausgeben, nie den Wert**; ein Test-Token im
   Skript durch eine erkennbar falsche Zeichenkette ersetzen.
4. **Wegwerf-Sonden, die Geheimnisse lesen, danach LOESCHEN** — und vorher
   pruefen, dass kein Klartext in einer Datei liegen geblieben ist.
