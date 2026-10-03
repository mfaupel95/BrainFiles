# Codex Remote Control unter Windows

## Kurzsatz

`codex remote-control` funktioniert auf Windows nicht. Der tragende Weg ist der
app-server-Prozess mit dem versteckten Schalter `--remote-control`; das Skript
`Agenten/Werkzeuge/codex-remote-control.ps1` startet ihn bei der Anmeldung.

## Zwei Fehler, die zuerststoeren

1. **Konfiguration kaputt.** `~/.codex/config.toml` began mit `model "auto/best-free"`
   (ohen `=`). Jeder codex-Aufruf brach danach mit
   `Error loading configuration: ... 1:7: key with no value, expected =` ab -
   auch `codex doctor` und `codex login status`. Zeile 1 ist auf
   `model = "auto/best-free"` korrigiert (Sicherung `config.toml.bak-20261003`).
2. **Der CLI-Befehl.** `codex remote-control`, `... start` und `... pair` geben
   alle `Error: codex app-server daemon lifecycle is only supported on Unix
   platforms`. Der Daemon-Lifecycle (fork/setsid, PID-Lock per flock) hat keine
   Win32-Entsprechung. Upstream-Issue: openai/codex#30372.

## Der Weg, der traegt

```
codex app-server --remote-control --listen ws://127.0.0.1:8766
```

`--listen off` genuegt auch (kein WebSocket noetig), der WebSocket-Transport
macht den Prozess aber von aussen pruefbar. Status und Pairing-Code kommen
ueber JSON-RPC auf diesem Port:

- `initialize` (mit `clientInfo`) -> `initialized`-Notification
- `remoteControl/status/read` -> `{"status": "connected", "serverName": ...}`
- `remoteControl/pairing/start` mit `manualCode: true` -> `manualPairingCode`

Beispiel-Client: `Agenten/Hermes/cache/scratch/rc_ws_probe.js` (Node, globales
`WebSocket` ab Node 22 - braucht kein npm-Paket).

## Status `errored` ist nicht immer ein Fehler

Der erste app-server lieferte `errored`, Grund aus `RUST_LOG=debug`:

```
failed to connect ... wss://chatgpt.com/backend-api/wham/remote/control/server
HTTP error: 409 Conflict   {"detail":"Remote app server already online"}
```

Ein zweiter app-server (hier: die Desktop-App) haelt die Verbindung - das ist
**kein** Fehler, sondern ein Duplikat. Es darf nur EIN app-server mit
`--remote-control` laufen. Vor dem Start also den alten per PID beenden.

## Was jetzt laeuft

- Geplante Aufgabe `MaxHirn-Codex-Remote-Control` (Anmeldung, +1 min, versteckt,
  Limited, IgnoreNew), fuehrt `powershell -File ...\codex-remote-control.ps1`.
- Das Skript: laeuft schon einer -> Exit 0; Port 8766 belegt -> Abbruch;
  sonst starten und 30 s `/readyz` pollen.
- Log: `Agenten/Routinen/logs/codex-remote-control.log`.
- Umgebung `env_e_6a862555c...`, Server-Name `MaksPC420`.

## Merksaetze

- Ein versteckter CLI-Schalter kann der Weg sein, wenn der sichtbare Befehl auf
  der Plattform nicht gebaut ist - die Fehlermeldung nennt die Einschraenkung
  selbst ("only supported on Unix platforms").
- `409 Conflict / already online` heisst: zwei app-server. Nicht Netz, nicht
  Anmeldung, nicht VPN.
- Die healthz-Zeile einer laufenden Dienstanwendung darf nicht als Beleg gelten;
  `remoteControl/status/read` ist der eigentliche Zustand.