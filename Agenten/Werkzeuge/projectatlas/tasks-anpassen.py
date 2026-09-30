# Historischer Einmal-Ersatz in TASKS.md (CRLF erhalten), angewandt am 13.09.2026.
# Der Pfad lokalisiert sich selbst: Hermes-Werkzeuge starten in Agenten/Hermes,
# ein relatives "MaxHirn/..." traefe von dort aus nichts.
from pathlib import Path
p = Path(__file__).resolve().parents[3] / "MaxHirn" / "Archiv" / "TASKS.md"
raw = open(p, "rb").read()

alt = (
    "      Wartet auf: Credentials f\u00fcr Provider `codex` in OmniRoute\r\n"
    "      Angelegt: 2026-09-07 \u00b7 Zuletzt: 2026-09-07"
).encode("utf-8")

neu = (
    "      Wartet auf: Credentials f\u00fcr Provider `codex` in OmniRoute\r\n"
    "      **Key-Verweis (13.09.2026):** Der Admin-Schl\u00fcssel f\u00fcr die OmniRoute-Config steckt\r\n"
    "      nicht im Router-Prozess. Lesbar sind die Benutzervariablen\r\n"
    "      `OMNIROUTE_ADMIN_API_KEY` (Admin-/Config-API `/api/*`) und `OMNIROUTE_API_KEY`\r\n"
    "      (Modell-API `/v1/*`) direkt aus `HKCU\\Environment` - der Prozess erbt frisch\r\n"
    "      gesetzte Variablen nicht, also aus der Registry lesen statt env. Der Klartext\r\n"
    "      selbst liegt nur in [[Zugaenge]] (Stufe 0): dorthin sehen, nie in Notizen\r\n"
    "      kopieren.\r\n"
    "      Angelegt: 2026-09-07 \u00b7 Zuletzt: 2026-09-13 (Key-Verweis erg\u00e4nzt)"
).encode("utf-8")

assert raw.count(alt) == 1, f"Anker {raw.count(alt)}x"
open(p, "wb").write(raw.replace(alt, neu))
print("OK: TASKS.md gepatcht (CRLF erhalten)")