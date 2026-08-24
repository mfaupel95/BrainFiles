# Arbeitsanweisung für Agenten (Hermes u. a.)

Diese Datei gilt für Agenten, die `AGENTS.md` lesen — allen voran **Hermes**.
Claude liest stattdessen `CLAUDE.md`. Beide arbeiten im selben Vault, auf
denselben Dateien und über dieselben MCP-Server. Damit sie nicht
auseinanderlaufen, gelten die Regeln unten für beide.

## Zuerst lesen, was schon da ist

Vor dem ersten Werkzeugaufruf prüfen, welches Wissen bereits vorliegt. Diese
beiden Dateien sind **verbindlich** und vor der Arbeit zu lesen:

- [CLAUDE.md](CLAUDE.md) — Aufbau des KI-Betriebssystems, Modulübersicht
- [Claude/CLAUDE.md](Claude/CLAUDE.md) — Regeln fürs Archiv, Posteingang,
  beschädigte Dateien, sparsamer Umgang mit Ausgaben

Was dort steht, wird **nicht neu erhoben**. Eine Zahl, die schon in einer
dieser Dateien steht, wird nachgeschlagen und nicht noch einmal gemessen.

## Reihenfolge bei jeder Anfrage

1. **`Wissen/` zuerst.** Persönlicher Kontext: Profil, Projekte, Fristen,
   Verbindungen. Beantwortet viele Fragen ohne jeden Werkzeugaufruf.
2. **Dann das Archiv.** Eigene Rechnungen, Verträge, Notizen, Fotos,
   Anleitungen? Dann den MCP-Server `archiv` benutzen — nicht das Internet,
   und nicht das Dateisystem durchsuchen.
3. **Erst danach Internet.** Für allgemeines Weltwissen.

## Gedächtnis: `Wissen/` ist die einzige Wahrheit

Es gibt in diesem System mehrere Gedächtnisse. Damit kein Widerspruch entsteht,
ist die Zuständigkeit fest verteilt:

| Ablage | Rolle |
|---|---|
| `Wissen/` (Markdown im Vault) | **einzige Wahrheit.** Was dauerhaft gilt, steht hier. |
| `Hermes/memories/` | Arbeitsspeicher für laufende Sitzungen. **Nie als Beleg zitieren.** |
| `mcp-memory`-Server | werkzeugübergreifende Notizen, ebenfalls nachrangig |

Erkenntnisse, die über die Sitzung hinaus gelten, gehören als Markdown-Datei
nach `Wissen/`, verlinkt mit `[[Dateiname]]`. Kurzlebiges — Zwischenstände,
Ausgaben eines einzelnen Laufs — gehört **nicht** in den Vault.

Fällt auf, dass eine Datei in `Wissen/` einen überholten Stand behauptet
(Zahlen, Dateilisten, „noch offen"): sofort korrigieren und die Korrektur
melden, auch wenn es nicht zur Aufgabe gehört. Diese Dateien werden in jeder
Sitzung als Wahrheit gelesen — eine falsche Zahl darin ist teurer als eine
fehlende.

## Antworten

- **Auf Deutsch**, außer Max schreibt auf Englisch.
- **Ergebnis zuerst.** Was ist herausgekommen, was funktioniert, was nicht —
  in den ersten drei Zeilen. Begründung und Details danach.
- **Zahlen sind gemessen, nicht geschätzt.** Ist eine Zahl geschätzt, steht das
  dabei.
- **Was nicht erledigt wurde, ausdrücklich benennen** — nicht durch Weglassen
  andeuten.

## Zwei Striche am Satzende: persönliche Bemerkung

Hängt Max an einen Satz `--` an, folgt danach eine **persönliche Bemerkung,
Anweisung oder ein Hinweis zu genau dem davorstehenden Text** — nicht zur
Nachricht als Ganzes.

> Bau das Skript wie letztes Mal. -- diesmal aber ohne Protokollausgabe

Der Teil vor `--` ist die Aussage oder Aufgabe, der Teil danach steuert sie
fein. **Widerspricht er ihr, gilt der Teil nach `--`.**

Stehen mehrere `--` in einer Nachricht, bezieht sich jedes auf den Satz
unmittelbar davor — nicht auf alles Vorherige.

Was dabei schiefgehen kann, in beide Richtungen:

- Den Teil nach `--` als **eigene neue Aufgabe** lesen und getrennt abarbeiten.
  Er gehört zum Satz davor.
- Ihn **überlesen**, weil er kurz und beiläufig wirkt. Er ist die Stelle, an
  der Max die Aufgabe zuschneidet — der wichtigste Teil des Satzes.

## Grenzen

- **Schreiben nur innerhalb dieses Vaults.** Durchgesetzt über
  `HERMES_WRITE_SAFE_ROOT`. Lesen ist überall möglich.
- **Keine Geldbewegung auslösen.** Senden, tauschen, kaufen, verkaufen,
  freigeben (Approval), ein- und auszahlen macht Max selbst. Kurse, Guthaben,
  Positionen und Sicherheitsprüfungen lesen und einen Vorgang bis zur
  Bestätigungsseite vorbereiten ist erlaubt.
- **Sensible Dateien** (Passwort-Exporte, Zertifikate, Schlüssel) nie
  automatisch verschieben oder archivieren — melden und liegen lassen.
- **Vor destruktiven Aktionen** Testlauf, danach prüfen. Erfolgsmeldungen von
  Löschbefehlen nicht ungeprüft glauben.
- **Vor Eingriffen ins System** (Software installieren, Konfiguration außerhalb
  des Vaults ändern, geplante Aufgaben anlegen, Massenoperationen) erst
  ansagen, was genau passiert, dann die Bestätigung abwarten.

- **Mehrere Sitzungen gleichzeitig.** Max hat mehrere Chats offen, dazu Hermes —
  alle schreiben in denselben Vault. **Git schützt nur, was committet ist.**
  Deshalb: nur committen, was man selbst geändert hat (`git add <pfad>`, nie
  `-A`, `.` oder `commit -a`); **nie** `git reset --hard`, `checkout -- <datei>`,
  `restore`, `stash` oder `clean` — sie löschen die uncommittete Arbeit anderer
  Sitzungen unwiederbringlich; Eigenes zügig committen; `index.py`,
  `sort_inbox.py`, `sichern.ps1`, `zweitkopie.ps1` nie doppelt starten.
  Vollständig: [[Schutzregeln]].
## Verwandte Notizen

- [[Hermes]] — Pfade, Anmeldeweg, offene Punkte dieser Einbindung
- [[Verbindungen]] — welche MCP-Server es gibt und ob sie angemeldet sind
- [[Projekte]] — was gerade läuft
