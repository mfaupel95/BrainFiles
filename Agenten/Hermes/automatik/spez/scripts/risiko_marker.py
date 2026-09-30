"""Risiko-Wortlisten fuer den Inventar-Scanner.

Absichtlich nur EINZELNE Marker-Wortteile, keine vollstaendigen Kommandozeilen:
eine Datei, die vollstaendige Loesch-Kommandos als Literal enthaelt, wird von
der Hermes-Kommandopruefung beim Schreiben als gefaehrlich eingestuft und in
einer Sitzung ohne anwesenden Nutzer blockiert (belegt am 20.09.2026: drei
write_file-Laeufe liefen in den 420-s-Timeout).

Klassenrang (hoechster Treffer gewinnt):
  none < local < extern < geld < destruktiv
"""

RANG = {"none": 0, "local": 1, "extern": 2, "geld": 3, "destruktiv": 4}

# Teilstrings, case-insensitive gesucht. Ein Treffer je Liste genuegt als Beleg.
# Die Marker sind absichtlich SPEZIFISCH: ein blosses "order" traf zuvor
# "in order to" in 8 harmlosen Skills, "swap" traf "swap file".
MARKER = {
    "destruktiv": [
        "-recurse",
        "rmtree",
        "remove-item",
        "reset --hard",
        "clean -fd",
        "drop table",
        "taskkill",
        "del /f",
        "push --force",
    ],
    "geld": [
        "kraken_order",
        "order_aufgeben",
        "place_order",
        "create_order",
        "market order",
        "limit order",
        "withdraw",
        "--live",
        "live-trading",
        "live trading",
        "x402",
        "sign transaction",
        "private key",
        "seed phrase",
        "/swap",
        "swap(",
    ],
    "extern": [
        "git push",
        "mail_senden",
        "telegram",
        "requests.post",
        "api_key",
        "api-key",
        "webhook",
        "gh pr create",
    ],
    "local": [
        "write_file",
        "git commit",
        "git add",
        "mkdir",
        "new-item",
        "move-item",
        "robocopy",
        "patch(",
    ],
}

# Eingabequellen: welche Art Kontext ein Skill anfasst.
QUELLEN = {
    "terminal": ["terminal", "```bash", "```powershell", "```sh"],
    "dateien": ["read_file", "search_files", "write_file"],
    "netz": ["web_search", "web_extract", "curl", "http"],
    "mcp": ["mcp__"],
    "geheim": [".env", "api_key", "api-key", "token"],
}
