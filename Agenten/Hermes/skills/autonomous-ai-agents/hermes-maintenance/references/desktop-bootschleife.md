# Desktop kommt nicht hoch - Zeugen, Mechanik, Reparatur

Detail zum Abschnitt „Desktop kommt nicht hoch" in SKILL.md. Alles hier ist an einem
konkreten Ausfall (30.09.2026, 73 min) gemessen, nicht aus der Doku abgeleitet.

## 1. Wie die App ihren Backend findet

Die Electron-App (`apps/desktop/.../electron-main.mjs`, Modul `backend-discovery` /
`host-backend-attach`) macht bei jedem Start Folgendes:

1. Sie liest `spawn-ledger.json` im Hermes-Home. Verwertbar sind nur Eintraege mit
   `purpose` in `{dashboard, serve}`, einem Port 1-65535, `isolated != true` und einem
   Loopback-Host. Von diesen nimmt sie den JUENGSTEN (`registered_at`).
2. Sie validiert ihn: Token holen (vom Backend veroeffentlicht, sonst der publizierte
   Token des Eintrags), auf Bereitschaft warten, dann `ws://…/api/ws?token=…` proben
   (10 s Budget). Scheitert das, probiert sie die naechsten Eintraege.
3. Erst wenn KEINER validiert, startet sie einen eigenen Backend:
   `hermes serve --host 127.0.0.1 --port 0` (aus dem Hermes-Checkout).
4. Auf den Port wartet sie **90 s** (`Timed out waiting for Hermes backend port
   announcement (90000ms)`). Ist er dann nicht da, gilt der Start als gescheitert und
   sie beginnt von vorn - im Log sichtbar als Wiederholung des Blocks.

`HERMES_DESKTOP_ISOLATED_BACKEND=1` erzwingt Schritt 3 (eigener Backend, nie anhaengen) -
kein Hausstandard, aber ein sauberer Ausweg, wenn ein fremder Backend die App blockiert.

Folge fuer die Diagnose: ein Eintrag im Ledger, der NICHT antwortet, kostet jedes Mal die
10-Sekunden-Probe, bevor die App auf ihren eigenen Backend wechselt. Ein Dashboard, das
unter Last 30 s pro Anfrage braucht, laesst die App also scheinbar grundlos haengen -
waehrend `curl http://127.0.0.1:9119/api/health` spaeter 200 in 0,04 s liefert.

## 2. Die Log-Zeilen, die es verraten

`$HERMES_HOME/logs/desktop.log`:

    [hermes:api GET /api/config?include_defaults=false] Error: Timed out connecting to Hermes backend after 30000ms
    [attach] http://127.0.0.1:9119 (pid 2176) rejected the session token on /api/ws: Timed out after 10012ms waiting for the WebSocket to open
    [bootstrap] repair requested by renderer; forcing reinstall + clearing latched failure (attempt=1/3, primaryBackendAlive=false …)
    [boot] Starting Hermes backend via Hermes at <checkout>
    hermes: finishing an interrupted source update...
    [hermes:api GET /api/config] Error: Hermes backend: exited before port announcement (1)
    HERMES_BACKEND_READY port=52165
    [boot] Hermes backend is ready. Finalizing desktop startup

Die letzten zwei Zeilen sind der Erfolg. `exited before port announcement (1)` heisst: der
Launcher hat sich beendet, statt einen Backend zu starten - fast immer wegen der
Update-Obligation (Abschnitt 3).

## 3. Zeuge 1: die Update-Obligation

    ls "$HERMES_HOME/installs"/*/source-completion-pending
    cat "$HERMES_HOME/.hermes-update-in-progress"     # "<pid>\n<unixtime>"
    python -c "import json;from hermes_constants import get_hermes_home;print(get_hermes_home())"

Ist `source-completion-pending` da, faehrt JEDER `hermes`-Start erst den Schwanz
(Node, TUI, Web-UI, Desktop bauen). Fertig ist er erst, wenn der Marker weg ist UND im
Schwanz-Log `✓ Update complete!` steht. Details und der Retry-Befehl:
Abschnitt „Abgebrochener Update-Schwanz" in SKILL.md.

Nach SECHS fehlgeschlagenen Versuchen schweigt die Selbstheilung 15 min
(`COMPLETION_RETRY_BACKOFF_SECONDS`) - ein Launcher-Start zeigt dann GAR KEINE Meldung mehr,
obwohl der Marker noch steht. Das ist kein neuer Fehler.

## 4. Zeuge 2: die Dateisperre

    powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'Hermes.exe' } | Select-Object ProcessId,CreationDate"

Der laufende Desktop haelt `apps/desktop/release/win-unpacked`; der Austausch scheitert dann
mit:

    desktop promotion rename win-unpacked -> win-unpacked.previous hit a file lock (attempt 1/5), retrying in 0.5s: [WinError 5] Zugriff verweigert
    desktop stage-and-swap failed, live app kept
    ✗ Could not install the rebuilt desktop app into <…>\apps\desktop\release
    RuntimeError: Could not publish the desktop build.   ↩ The previous desktop app was left untouched and still works.

Erst die App schliessen, dann erneut bauen. Ein laufendes `Hermes.exe` ist an der Zahl der
Kindprozesse zu erkennen (`--type=gpu/utility/renderer`), der Hauptprozess traegt keinen
`--type`-Schalter.

## 5. Zeuge 3: der Plattenplatz

    powershell -NoProfile -Command "'{0:N1} GB frei' -f ((Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\").FreeSpace/1GB)"

Der Desktop-Build braucht rund 20 GB transient (Staging-Kopie + node_modules + electron-
builder). Bei 0,1 GB frei bricht der Schwanz ab:

    OSError: [Errno 28] No space left on device

Die Reserve wird vom Haus selbst gehalten (`platz-wache.py`, 30 GB, taeglich) - siehe SKILL.md.
Schnelle Notposten von Hand: `uv cache clean` (2026: 9,2 GB), `AppData\Local\Temp` leeren,
`.dist-build-*` und `release/win-unpacked.bak` unter `apps/desktop/`.

## 6. Zeuge 4: der Ledger-Eintrag

    python -c "import json;d=json.load(open(r'<HERMES_HOME>/spawn-ledger.json',encoding='utf-8'));print([(e.get('purpose'),e.get('port'),e.get('profile'),e.get('pid')) for e in d][:5])"

Interessant sind Eintraege mit `purpose` `dashboard`/`serve`. Ein Dashboard-Eintrag, dessen
Prozess laeuft, aber nicht antwortet, ist der klassische Blocker. Kein Hausstandard: den
Ledger von Hand putzen - die App faellt von selbst auf den naechsten Eintrag oder startet
ihren eigenen Backend; nur wenn JEDER Start 10 s Probe + 90 s Warten kostet, lohnt der Blick.

## 7. Reparatur, in dieser Reihenfolge

    # 1) App schliessen (Dateisperre loesen)
    powershell -NoProfile -Command "Get-Process Hermes -ErrorAction SilentlyContinue | Stop-Process -Force"
    # 2) Reserve herstellen und MESSEN
    uv cache clean ; rm -rf "$LOCALAPPDATA/Temp"/*
    # 3) Schwanz zu Ende fahren (losgeloest, nie mit eigenem Zeitlimit) - Rezept in SKILL.md
    # 4) Dienste starten
    schtasks /run /tn Hermes_Gateway_2ef9d0b7
    powershell -NoProfile -Command "Start-Process -FilePath '<…>\win-unpacked\Hermes.exe' -WorkingDirectory '<…>\win-unpacked'"

## 8. Nachweis (drei Zeilen, keine Behauptung)

    curl -s -w ' HTTP %{http_code}\n' http://127.0.0.1:<port>/api/health      # {"ok":true,"version":"…"} HTTP 200
    python -c "import json;d=json.load(open('gateway_state.json'));print(d['gateway_state'],[k for k,v in d['platforms'].items() if v['state']=='connected'])"
    tail -3 logs/desktop.log        # '[boot] Hermes backend is ready. Finalizing desktop startup'

Der Gateway braucht 50-90 s, bis Ports 9900 (A2A) und 8644 (Webhook) hoeren; in dieser Zeit
NICHT erneut starten (sonst laeuft eine zweite Instanz). `photon` darf `retrying` zeigen.

## 9. Fallen

- **Einen Launcher-Lauf nie mit eigenem Zeitlimit im Vordergrund killen.** Genau so entsteht
die Obligation (hier: ein `hermes config unset` im 180-s-Fenster). Losgeloest starten, Log
lesen.
- **`hermes desktop` aus einer Sitzung heraus nimmt die Update-Sperre** und faehrt den Schwanz
selbst - der Aufruf blockiert minutenlang und ist kein Fehler.
- **Der Erfolg eines Zyklus ist kein Beleg fuer Ordnung:** `✓ Update complete!` kann fehlen,
waehrend der Baum lauffaehig ist ("running with the previous dependencies"). Was zaehlt, ist
der verschwundene `source-completion-pending`-Marker UND ein Desktop mit `/api/health`.
- **Konfigurationsfragen gehoeren nicht hierher:** Werte auf Hermes-Standard bringen,
Abweichungen auflisten und `config set`-Fallen stehen in `hermes-config-ops`
(`scripts/config-abweichungen.py` gegen `DEFAULT_CONFIG`).
- **Nach der Reparatur die Buchhaltung**: Wiki-Seite, offene Punkte als Task
(`MaxHirn/Archiv/TASKS.md`), Commit nur der eigenen Pfade - ein Ausfall ohne Aufzeichnung
wiederholt sich.
