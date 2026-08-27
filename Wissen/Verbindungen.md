# Verbindungen

Welche Dienste das Betriebssystem erreichen kann. Ein Dienst nützt erst etwas,
wenn er **authentifiziert** ist — eingerichtet allein reicht nicht.

## Stand 2026-08-19

Die MCP-Server waren Desktop-Extensions unter `%APPDATA%`. **Seit 13.08.2026
startet Claude sie aus [MCP-Server/](../MCP-Server/README.md)** — eingetragen
als `mcpServers` in `claude_desktop_config.json`, die Erweiterungen dazu
abgeschaltet. Geprüft am 19.08.2026: alle 14 Erweiterungen stehen auf
`isEnabled: false`, alle Einträge in der Konfiguration zeigen auf vorhandene
Dateien. Seit dem 19.08.2026 sind es **10 Server** — `filesystem` ist raus.
Die Werkzeugschicht läuft aus dem Vault heraus.

Fünf Server sind **nicht eingetragen** und damit inaktiv: Apify, Metabase,
Socket (alle drei ohne Zugangsdaten), Stats Compass und Perseus Vault. Sie
liegen einsatzbereit im Ordner. (Bis 19.08.2026 stand hier fälschlich „aktiv".)

| Dienst | Zweck | Status (19.08.2026 einzeln geprüft) |
|---|---|---|
| Google Kalender | Termine lesen, anlegen | **aktiv** — 4 Kalender lesbar |
| Gmail | Mails suchen, Entwürfe anlegen | **aktiv** — 19 Label, 1776 Mails im Posteingang |
| Google Drive | Dateien suchen und lesen | **aktiv** — Dateiliste lesbar |
| Archiv-Suche (`archiv`) | eigenes Dateiarchiv | aktiv — 7631 Dateien, Index vom 19.08.2026 |
| Desktop Commander | Dateisystem, Prozesse, Terminal | aktiv |
| Windows-MCP | Desktop steuern, PowerShell | aktiv |
| ToolUniverse | wissenschaftliche Werkzeuge | aktiv — 818 Werkzeuge in 118 Kategorien |
| pdf-vault | PDFs anzeigen, ausfüllen, signieren | Konfiguration nachweislich richtig, **Werkzeug meldet trotzdem nichts** — siehe unten |
| Filesystem | Dateizugriff (Anthropic) | **am 19.08.2026 gestrichen** — war defekt, siehe unten |
| MCP Memory | Langzeitgedächtnis über Werkzeuge hinweg | Schlüssel am 19.08. eingetragen, greift nach Neustart |
| Kraken | Kurse, Guthaben, Orders, Ledger | **aktiv** — geprüft 20.08.2026, 24 Positionen lesbar |
| Revolut X | Kurse, Bestände, Backtests (nur lesend) | Schlüssel **vorhanden** (25.08.), scheitert an der **IP-Freigabe** — siehe unten |
| Blender | 3D-Szenen | aktiv, aber nur wenn Blender läuft (19.08. nicht gestartet) |
| Affinity | Affinity-Dokumente skripten | aktiv, aber nur wenn Affinity läuft (`http://localhost:6767/sse`) |
| Apify, Metabase, Socket, Stats Compass, Perseus Vault | — | **nicht eingetragen**, inaktiv |

## Zwei Agenten, dieselben Server (Stand 23.08.2026)

Seit dem 23.08.2026 nutzt **[[Hermes]]** dieselben 11 MCP-Server. Sie sind dort
ein zweites Mal eingetragen — als `mcp_servers:` in
`MaxHirn/Hermes/config.yaml`, im gleichen Format (`command` / `args` / `env`).
Die Serverprogramme selbst liegen weiterhin nur einmal unter `MCP-Server/`;
jeder Agent startet sie als eigenen Unterprozess.

**Folge fürs Pflegen:** Ändert sich ein Server (Pfad, Argument, Variable), muss
er an **beiden** Stellen nachgezogen werden — `claude_desktop_config.json` und
`Hermes/config.yaml`. Wird das vergessen, arbeitet ein Agent still mit einem
veralteten Aufruf weiter.

Ein Unterschied: Hermes löst `${env:…}` in seiner Konfiguration **nur aus der
Prozessumgebung** auf, nicht aus seiner `.env` — die Konfiguration wird vorher
gelesen. Wer dort einen Schlüssel braucht, setzt ihn als Windows-Benutzervariable
(Weg 1 unten), so wie Kraken es macht. Betrifft aktuell nur `mcp-memory`.

## Die laufende App überschreibt ihre eigene Konfiguration

**`claude_desktop_config.json` von außen zu ändern, während Claude läuft, ist
wirkungslos.** Gemessen am 19.08.2026: Ein entfernter Servereintrag und ein
ergänztes Argument waren sechs Minuten später wieder im alten Zustand — die App
schreibt die Datei aus ihrem eigenen Speicher neu.

Änderungen an dieser Datei deshalb **immer bei geschlossener App** vornehmen
(auch aus dem Infobereich neben der Uhr beenden), danach starten — und
hinterher aus der geschriebenen Datei gegenprüfen, nicht aus dem Gedächtnis.
Die Änderungen vom 19.08.2026 haben den zweiten Anlauf überstanden und sind
seit dem App-Neustart wirksam.

## Der MCP-Client reicht Benutzervariablen nicht durch

**Das ist die Ursache hinter mehreren „fehlt"-Meldungen.** Gemessen am
19.08.2026: `KRAKEN_API_KEY` steht in der Registry unter `HKEY_CURRENT_USER`,
`Environment` (56 Zeichen) und ist auch im Claude-Prozess selbst sichtbar — in
einem von Claude gestarteten MCP-Server-Prozess ist die Variable **leer**. Der
Client startet Serverprozesse mit einer bereinigten Umgebung.

Wer also einen eigenen Server baut, der Zugangsdaten braucht, hat drei Wege:

1. **Registry direkt lesen** (`winreg`, Schlüssel `HKEY_CURRENT_USER`,
   Unterschlüssel `Environment`) — hält die Zugangsdaten aus jeder
   Konfigurationsdatei heraus. So macht es Kraken seit 19.08.2026.
2. `env`-Block in `claude_desktop_config.json` — funktioniert, schreibt die
   Zugangsdaten aber im Klartext neben die Konfiguration.
3. Eigene Schlüsseldatei außerhalb des Vaults, vom Server gelesen.

## Kraken

Selbst gebauter MCP-Server unter [MCP-Server/kraken/](../MCP-Server/kraken/README.md),
registriert am 14.08.2026 in `claude_desktop_config.json` (Sicherung daneben als
`.bak-20260814`).

Zugangsdaten liegen **ausschließlich** in den Windows-Benutzervariablen
`KRAKEN_API_KEY` und `KRAKEN_API_SECRET` — nicht im Vault, nicht in der
Claude-Konfiguration. Sie sind gesetzt (56 bzw. 88 Zeichen, geprüft 19.08.2026);
die frühere Notiz „noch Platzhalter" war falsch.

Weil der Client die Variablen nicht durchreicht (siehe oben), meldete
`kraken_status` trotzdem „Variablen fehlen". Am 19.08.2026 hat
`kraken_mcp.py` deshalb einen **Registry-Rückfall** bekommen (`_variable()`,
Sicherung `kraken_mcp.py.bak-20260819`). Der Rückfall ist geprüft und liefert
beide Werte. **Er greift erst nach einem Neustart von Claude** — der laufende
Serverprozess hat noch den alten Code. Ob Kraken die Schlüssel auch akzeptiert,
zeigt danach `kraken_status`; das ist noch nicht verifiziert.

Der Server hat bewusst **kein Auszahlungs-Werkzeug**. `kraken_order_aufgeben`
prüft standardmäßig nur (Kraken-`validate`), platziert also nichts; echtes
Aufgeben verlangt einen ausdrücklichen Schalter und bleibt Max' Schritt.

## Offene Baustellen (Stand 19.08.2026)

Am 19.08.2026 behoben (wirksam nach dem nächsten Claude-Neustart):

| Behoben | Wie |
|---|---|
| Kraken sah seine Zugangsdaten nicht | Registry-Rückfall in `kraken_mcp.py`. **Nachgeprüft:** `kraken_status` meldet `verbindung: ok`, 23 Positionen |
| Filesystem-Server defekt (`server-filesystem` 2026.7.10 liefert `outputSchema` als draft-07, der Client kann nur 2020-12 — **jeder** Aufruf scheiterte) | Eintrag aus `claude_desktop_config.json` gestrichen; Desktop Commander deckt dasselbe ab. Sicherung: `claude_desktop_config.json.bak-20260819` |
| MCP Memory ohne Schlüssel | `MNEMOVERSE_API_KEY` als `env`-Block bei `mcp-memory`. **Nachgeprüft:** `memory_stats` antwortet (0 Einträge, Domäne `general`) |
| Desktop Commander dreifach, pdf-viewer doppelt geladen | Inline-Plugins abgeschaltet: `"enabledPlugins": {"desktop-commander@inline": false, "pdf-viewer@inline": false}` in `~/.claude/settings.json`. Sicherung: `settings.json.bak-20260819` |

Noch offen — braucht Max:

| Problem | Was fehlt | Weg |
|---|---|---|
| Dritter Desktop-Commander-Klon | Connector `Desktop_Commander` steht in keiner lokalen Datei, sondern in den claude.ai-Connector-Einstellungen | auf claude.ai unter Einstellungen → Connectors entfernen |
| pdf-vault meldet `allowedDirectories: []` | **Liegt nicht an der Konfiguration.** Alles daran ist einzeln nachgemessen (19.08.2026): der Eintrag hat den Ordner als drittes Argument; der laufende Prozess ist ein Kind von `claude.exe` und trägt das Argument in seiner Kommandozeile; und derselbe Server, direkt über stdio angesprochen, meldet den Ordner und findet **500 PDFs**. Nur über die App bleibt die Liste leer. Auffällig: die App startet **zwei** identische Instanzen. | Zuerst Claude vollständig neu starten und `list_pdfs` erneut aufrufen. Bleibt es leer, ist es ein Fehler im MCP-Hosting der App, nicht in dieser Einrichtung — dann nichts weiter daran drehen |
| Revolut X: `API key can only be used for authentication from whitelisted IP` | **Nicht mehr der fehlende Schlüssel** — der ist seit spätestens 25.08.2026 eingetragen und wird akzeptiert. Der Server meldet auf `check_auth_status`: „Authentication is configured", die Verbindung scheitert erst an der Herkunftsadresse. Im Revolut-X-Portal die aktuelle öffentliche IP für den API-Schlüssel freigeben | Portal-Schritt, geht nicht aus der Sitzung. Bei wechselnder IP (DSL-Zwangstrennung) nach jedem Wechsel erneut nötig |

Der Mnemoverse-Schlüssel steht seit 19.08.2026 als `env`-Block beim
vorhandenen Server `mcp-memory` — **nicht** als zweiter Eintrag über
`claude mcp add mnemoverse … npx …@latest`. Das hätte eine Dublette angelegt
und den Server bei jedem Start aus dem Netz geladen, statt die Fassung in
`MCP-Server/` zu benutzen. Der Schlüsselwert steht nur in
`claude_desktop_config.json`, nicht im Vault.

## Nicht über MCP: OKX Onchain OS

Läuft nicht als MCP-Server, sondern über die CLI `onchainos.exe`
(`C:\Users\faupe\.local\bin\`) plus zehn Skills unter `~/.claude/skills/okx-*`.

| Punkt | Stand 14.08.2026 |
|---|---|
| CLI installiert | ja |
| Wallet angemeldet | ja — Apple-Login, `faupel3107@icloud.com`, 1 Konto |
| Guthaben | 0,00 USD (Stand 14.08.2026) |
| Ausgabenlimits | **gesetzt** — je Transaktion 50 USD, Transfers 200 USD/Tag, Swaps 500 USD/Tag |
| Transfer-Whitelist | nicht prüfbar aus der Sitzung (nur im Portal sichtbar) |

Die Limits werden **nur im Web-Portal** gesetzt, nicht per CLI:
`https://web3.okx.com/portfolio/agentic-wallet-policy`. Tageslimits setzen um
**00:00 UTC** zurück (02:00 deutsche Sommerzeit).

Bekannte Grenzen dieser Limits: Der UTC-Reset lässt sich umgehen, indem man ihn
überspannt; Token-Freigaben (ERC-20-Approvals) zählen vermutlich weder als
Transfer noch als Swap (**nicht verifiziert**); ein Swap in einen wertlosen
Token ist limitkonform und trotzdem Totalverlust. Dagegen helfen nur
Sicherheitsscan vor dem Kauf und regelmäßiges Widerrufen offener Freigaben.

Das Auslösen von Geldbewegungen bleibt laut globaler Arbeitsanweisung beim
Nutzer — Claude bereitet nur vor.

### Doch über MCP: OKX Agent Trade Kit (seit 25.08.2026)

Die Überschrift oben stimmt seit dem 25.08.2026 nicht mehr vollständig. Max hat
zusätzlich zur CLI einen **HTTP-MCP-Server** eingetragen:

| Punkt | Stand 25.08.2026 |
|---|---|
| Name | `okx-agent-trade-kit` |
| Adresse | `https://www.okx.com/api/v1/mcp/trading-oauth` |
| Transport | HTTP |
| Eingetragen in | **drei** Dateien — `~/.claude.json` (Benutzer, nicht versioniert), `.mcp.json` und `Claude/.mcp.json` (versioniert, `80e2ec9` / `f0c9699`) |
| Status | **aktiv** — `claude mcp list` meldet `✔ Connected` (27.08.2026), 165 Werkzeuge |

**Warum dreifach.** Ein reiner Projekt-Eintrag ist nur sichtbar, wenn die
Sitzung im Vault wurzelt. Wer `claude` im Heimatverzeichnis startet, findet
den Server dort nicht — genau das ist am 25.08.2026 passiert und hat Zeit
gekostet. Der Benutzer-Eintrag macht ihn überall sichtbar, die beiden
`.mcp.json` halten ihn versioniert und umzugsfest. Das ist bewusst
redundant, kein Versehen.

**Gemessen, keine Doppelung:** Trotz dreier Einträge listet
`claude mcp list` den Server genau einmal — der Benutzer-Eintrag hat
Vorrang. Bei einer Adressänderung müssen trotzdem alle drei Dateien von
Hand nachgezogen werden.

**Die Anmeldung ist erteilt** (27.08.2026). Sie geht nur in einer
interaktiven Sitzung (`claude` starten, dort `/mcp`), nicht aus einer
laufenden Sitzung heraus. Ein Umzug zwischen den Ebenen verliert sie: Der
Server war am 25.08. schon einmal verbunden, nach dem Wechsel auf die
Projekt-Ebene musste sie neu erteilt werden.

**Der erste Anlauf schlug fehl** — die Oberfläche meldete „Verbindung zu
konnte nicht hergestellt werden. Bei der Verbindung mit dem KI-Agenten ist
ein Fehler aufgetreten." (mit der Lücke hinter „zu", der Servername fehlte).
Der zweite Versuch lief durch. Der Endpunkt selbst war zu diesem Zeitpunkt
erreichbar und antwortete regulär mit `HTTP 401` auf einen unauthentifizierten
Aufruf. **Also einfach noch einmal versuchen, bevor man die Konfiguration
umbaut.**

Der Zugangsschlüssel liegt in `~/.claude/.credentials.json`, **nicht** neben
dem Servereintrag. Die Einträge selbst bestehen nur aus Name, Typ und
öffentlicher Adresse — sie enthalten kein Geheimnis. Deshalb sind sie
gefahrlos versionierbar.

**Zwei Dateien, ein Server.** Der Eintrag steht doppelt: `Claude/.mcp.json`
gilt für Sitzungen, die in `Claude/` wurzeln (dort liegt auch `archiv`),
`.mcp.json` in der Vault-Wurzel für Sitzungen, die dort starten. Beide
müssen bei einer Adressänderung von Hand nachgezogen werden.

**Ein Eintrag auf Benutzer-Ebene kann in der Projekt-Konfiguration
auftauchen.** Beobachtet am 25.08.2026: Der Server wurde mit
`--scope user` angelegt, die CLI meldete ausschließlich `~/.claude.json`.
Rund zwei Minuten später stand derselbe Eintrag zusätzlich in
`Claude/.mcp.json`, und die `archiv`-Argumente darin waren neu formatiert.
Kein Sitzungsbefehl hat das geschrieben — zwei parallele Sitzungen haben
die Urheberschaft auf Nachfrage ausgeschlossen, eine davon sah die
OKX-Werkzeuge im selben Zeitfenster unaufgefordert in ihrer Werkzeugliste
erscheinen.

Die Messwerte, damit es nachprüfbar bleibt:

| Datei | geschrieben | Eintrag drin |
|---|---|---|
| `~/.claude.json.bak-20260824` (vor dem Befehl) | Sitzungsbeginn | nein |
| `~/.claude.json.bak-20260825` (nach dem Befehl) | 17:33 | **ja** |
| `Claude/.mcp.json` | 17:32:48 | ja — von keinem Befehl |
| `MaxHirn/.mcp.json` | 17:34:31 | ja — `--scope project` |
| `~/.claude.json` | 17:47:10 | nein, weil um 17:35 entfernt |

**Falle beim Nachprüfen:** Wer heute die laufende `~/.claude.json` durchsucht,
findet nichts und schließt daraus, `--scope user` habe nie dorthin
geschrieben. Das ist falsch — der Eintrag wurde dort angelegt und später
bewusst wieder entfernt. Die beiden datierten Sicherungen sind das
Gegenpaar, das den Unterschied belegt. Eine parallele Sitzung ist genau in
diese Falle getappt.

Wahrscheinlichste Erklärung für den Eintrag in `Claude/.mcp.json` ist eine
Spiegelung durch die App nach erfolgreicher OAuth-Anmeldung. **Das ist nicht
reproduziert und damit unbestätigt** — belegt sind nur die Zahlen oben.
Festgehalten wird hier vor allem die Beobachtung: Wer nach einer `mcp
add`-Aktion einen unerklärlichen Eintrag in `.mcp.json` findet, muss nicht
nach einer fremden Sitzung suchen. Drei parallele Sitzungen haben die
Urheberschaft nacheinander ausgeschlossen, bevor das klar war.

**Der Server kann handeln, nicht nur lesen.** Neben Kursen, Kerzen, Nachrichten
und Positionen bringt er Werkzeuge zum Aufgeben, Ändern und Stornieren von
Orders mit (Spot, Futures, Swap, Optionen, Grid, DCA) sowie
`account_transfer`. Damit gilt hier die Regel aus der globalen
Arbeitsanweisung unverändert und besonders scharf: **das Auslösen bleibt bei
Max**, Claude bereitet nur vor. Lesen und Vorbereiten dagegen vollständig.

## Anmeldung nachholen

Anmeldungen lassen sich **nicht** aus einer laufenden Sitzung heraus erledigen —
es braucht den OAuth-Ablauf im Browser:

- **claude.ai-Connectors:** in den Connector-Einstellungen auf claude.ai
  verbinden. Die Google-Dienste sind darüber seit spätestens 19.08.2026
  verbunden.
- **Eigene MCP-Server:** in einem interaktiven Terminal `claude` starten und
  dort `/mcp` aufrufen.

Danach diese Tabelle aktualisieren.

## Einen Server prüfen

Was ein Server wirklich anbietet, zeigt der MCP-Inspector im Browser —
Aufruf und Portwahl stehen in [MCP-Server/README.md](../MCP-Server/README.md).

Schneller geht der Praxistest aus der Sitzung: ein billiges, lesendes Werkzeug
jedes Servers aufrufen (`archiv_statistik`, `kraken_status`, `list_calendars`,
`list_pdfs` …). **Dass ein Server in der Werkzeugliste auftaucht, heißt nur,
dass der Prozess startet — nicht, dass er funktioniert.** Filesystem und MCP
Memory standen beide in der Liste und scheitern bei jedem Aufruf.

## Kandidaten für später

- **GitHub** — sobald das System versioniert werden soll
- **Google Workspace CLI** — Alternative zu den Connectors, läuft lokal
