# Sitzung 05.10.2026 — Telegram-Bruecke: Ausfallbild und Belegkette

Material aus einer Diagnose, die **stimmte** und trotzdem zwei eigene Fehler
hervorbrachte. Die Regeln stehen in `messwerkzeug-gegenprobe` (Aggregation,
Gegenlauf-Pfad) und `trugschluesse` (Schleife, Lint, Belegpflicht); hier steht
der konkrete Befund mit Zahlen.

## Der Ausfall

Der Gateway-Prozess startete um 01:36 ohne Telegram-Adapter und blieb es bis
zum kontrollierten Neustart um 06:50.

| | |
|---|---|
| Ausfall von | 01:36 |
| `error_code` | `adapter_unavailable` |
| `error_message` | `No adapter available for enabled telegram; check the plugin, dependencies, and credentials.` |
| Reconnect-Versuche | 41, alle 300 s, letzter 06:48 |
| Dauer der Schleife | 5 h 12 min |
| Beleg | `logs/gateway.log:1772` (erstes `No adapter available for telegram`) |

Die Zeile um 05:37 ist die Pointierung:

    WARNING gateway.run: telegram has been failing/reconnecting continuously
    for 2.0 hours (26 attempts) — flagging NEEDS_ATTENTION. Retries continue,
    but this usually means a permanent problem (revoked credentials, missing
    intents, broken sidecar). Check `hermes status` / `/platform list`.

Die Meldung nennt vier Ursachen. **Alle vier wurden widerlegt** — und keiner
war es.

## Die vier widerlegten Hypothesen

### 1. „Paket fehlt" — widerlegt
```
C:/…/tools/python-3.14.7+20260901-win32-x64/python.exe -c "import telegram"
→ OK telegram 22.8  C:/…/installs/bf59c98340a908a8/environments/aadf10e4e…/venv/Lib/site-packages/telegram/__init__.py
```
Der `site-packages`-Ordner **dieses** Python enthaelt nur `pip`. Die
Fremdpakete kommen aus dem gestagten Umfeld via `hermes_bootstrap` →
`pm/environments.py::activate_dependencies` (liest `committed_venv`, setzt
`sys.path`). Eine Verzeichnisliste ist hier kein Befund.

### 2. „Credentials falsch" — widerlegt
`TELEGRAM_BOT_TOKEN` in `<HERMES_HOME>/.env`, 46 Zeichen. Kein User-Store-
Eintrag — richtig und harmlos. Ein echter Credential-Fehler zeigt sich als
`failed to connect` mit Telegram-HTTP-Fehler, nicht als `adapter_unavailable`.

### 3. „Plugins nicht geladen" — widerlegt
`gateway/run_startup.py:1061-1064` ruft `discover_plugins()` ausdruecklich und
vor der Adapter-Schleife. Eine Probe mit exakt diesem Weg registriert
`telegram` in `platform_registry`, `check_fn` und `ensure_deps_fn` liefern beide
`True`.

### 4. „Rechnerausfall" — widerlegt
Speicherdruck, 13 Gateway-Neustarts am 04./05.10., `FreeVirtualMemory` zeitweise
1,94 GB. Das Aufraeumen brachte nichts — der Zustand blieb bis zum Neustart.

## Die Quelle des Fehlbilds

`gateway/run_startup.py:1213-1234`:

```python
adapter = self._create_adapter(platform, platform_config)
if not adapter:
    if platform.value in {m.value for m in Platform.__members__.values()}:
        logger.warning("No adapter available for %s", platform.value)
    ...
    heals = self._adapter_may_heal(platform, platform_config)
    self._update_platform_runtime_status(
        platform.value, platform_state="retrying" if heals else "fatal",
        error_code="adapter_unavailable",
        error_message=_adapter_unavailable_message(platform, retrying=heals),
        needs_attention=True)
    if heals:
        self._failed_platforms[platform] = self._startup_retry_entry(platform, None, platform_config)
```

`_create_adapter` → `_instantiate_adapter` (run_adapters.py:1858-1884): erst
`platform_registry`, dann `_instantiate_builtin_adapter`. Beide Wege gaben im
Prozess `None`, waehrend dieselben Wege von Hand den Adapter liefern.

**Der Grund ist nicht belegt.** Er ist als offenes Feld weitergegeben — in die
Skill-Regel „Ein nicht gefundener Grund wird als offenes Feld gefuehrt".

## Der heilende Neustart

```
Stop-Process -Id 24872 -Force
schtasks /run /tn Hermes_Gateway_2ef9d0b7
```

Nach ~5 min Hochlauf:

```
06:55:21,119 [Telegram] Telegram polling confirmed healthy: getUpdates progressing (generation 1)
06:55:21,124 [Telegram] Connected to Telegram (polling mode)
06:55:26,134 ✓ telegram connected
06:55:44,030 ✓ telegram connected (profile: bots)
```

Die Reihenfolge der Belege ist fest: **neue PID in `gateway_state.json`** →
**`✓ telegram connected`** → **`getUpdates progressing`** → **echte Zustellung**.

Nebenbefund, kein zweiter Befund: `lifecycle_ledger` meldete die alte Phase als
`exited UNCLEANLY (… a pkill/taskkill of the host interpreter image)` — das war
die eigene Beendigung.

## Der End-to-End-Beleg

```
{'success': True, 'platform': 'telegram', 'chat_id': '7648512088', 'message_id': '10888'}
Token-Laenge: 46 Zeichen (Wert nicht ausgegeben)
```

Ein echter Versand ueber genau den Sender, den der Dienst benutzt — nicht ueber
eine eigene Testfunktion. `status: connected` waere kein Weg-Beweis gewesen.

## Der Nebenbefund, den man nicht mitnehmen darf

`hermes_cli/observability/shared_metrics.py:176` ruft
`path.mkdir(parents=True, exist_ok=True, mode=mode)` auf einem Pfad, der als
**Datei** existiert → `FileExistsError: [WinError 183]` alle 20 s in
`errors.log`. Steht im selben Log wie die Diagnose, betrifft aber keinen
Plattform-Adapter.