# Desktop-App zeigt nur das default-Profil (multiplex_profiles)

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

#### Gegenrichtung: multiplex + Profil-`gateway:`-Bloecke = Absturzkreislauf

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
