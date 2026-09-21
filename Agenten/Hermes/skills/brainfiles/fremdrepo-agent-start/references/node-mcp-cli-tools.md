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
