"""Prueft stuendlich EINMAL, ob das Kraken-Konto wieder erreichbar ist.

Hintergrund: am 20.09.2026 hat Kraken den API-Schluessel nach einer
Serie fehlgeschlagener nonce-Versuche gesperrt (EGeneral:Temporary
lockout). Die Sperre loest sich von selbst - aber jeder weitere Versuch
kann sie verlaengern. Deshalb GENAU EIN Aufruf je Lauf, nicht mehr.

Watchdog-Muster: leere Ausgabe = nichts senden. Gemeldet wird nur der
Uebergang: sobald das Guthaben wieder abrufbar ist, kommt eine Meldung
und der Job traegt das in seinem Stand ein, damit er danach schweigt.

Stand: kraken-lockout-stand.json neben diesem Skript.
"""
import json
import os
import subprocess

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.abspath(os.path.join(HIER, "..", "..", "Handel"))
KRAKEN = os.path.join(HANDEL, "kraken")
PYTHON = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")
STAND = os.path.join(HIER, "kraken-lockout-stand.json")

# Ein einziger Aufruf, im eigenen Prozess mit dem Handel-venv.
CODE = (
    "import sys, json\n"
    "sys.path.insert(0, %r)\n"
    "import kraken\n"
    "try:\n"
    "    print(json.dumps({'ok': True, 'eur': kraken.guthaben('ZEUR')}))\n"
    "except Exception as e:\n"
    "    print(json.dumps({'ok': False, 'fehler': str(e)[:200]}))\n"
)


def lade_stand():
    try:
        with open(STAND, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return {}


def main():
    if not os.path.exists(PYTHON):
        return
    p = subprocess.run([PYTHON, "-c", CODE % KRAKEN], cwd=KRAKEN,
                       capture_output=True, text=True, timeout=120)
    ergebnis = None
    for zeile in reversed((p.stdout or "").strip().splitlines()):
        zeile = zeile.strip()
        if zeile.startswith("{"):
            ergebnis = json.loads(zeile)
            break
    if ergebnis is None:
        return  # kein verwertbares Ergebnis - schweigen, nicht raten

    stand = lade_stand()
    war_offen = bool(stand.get("offen"))

    if ergebnis.get("ok"):
        stand["offen"] = True
        stand["eur"] = ergebnis.get("eur")
        with open(STAND, "w", encoding="utf-8") as fh:
            json.dump(stand, fh, indent=2, ensure_ascii=False)
        if not war_offen:
            print("Kraken-Konto ist wieder erreichbar. Guthaben: %.2f EUR. "
                  "Der nonce-Pool kann jetzt zum ersten Mal echt geprueft "
                  "werden." % (ergebnis.get("eur") or 0.0))
        return

    # Weiterhin gesperrt: Stand fortschreiben, aber nur beim WECHSEL melden.
    stand["offen"] = False
    stand["letzter_fehler"] = ergebnis.get("fehler")
    with open(STAND, "w", encoding="utf-8") as fh:
        json.dump(stand, fh, indent=2, ensure_ascii=False)
    if war_offen:
        print("Kraken-Konto antwortet nicht mehr: %s"
              % ergebnis.get("fehler"))


if __name__ == "__main__":
    main()