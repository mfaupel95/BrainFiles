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
