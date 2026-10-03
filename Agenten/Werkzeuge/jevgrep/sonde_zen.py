"""Sonde: antwortet OpenCode Zen (Jev) ueberhaupt, und wie lange braucht es?

Der Schluessel kommt aus der Windows-Benutzervariable und wird NIE ausgegeben.
Nur Standardbibliothek, damit die Sonde unabhaengig von jevgrep laeuft.
"""
import json
import os
import time
import urllib.error
import urllib.request

NAMEN = ("OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY", "ZEN_API_KEY")


def schluessel():
    for n in NAMEN:
        w = os.environ.get(n)
        if w:
            return w.strip(), "Prozessumgebung " + n
    try:
        import winreg
    except ImportError:
        return None, ""
    for wurzel in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(wurzel, "Environment") as k:
                w, _ = winreg.QueryValueEx(k, "OPENCODE_API_KEY")
        except OSError:
            continue
        if isinstance(w, str) and w.strip():
            return w.strip(), "Windows-Benutzervariable OPENCODE_API_KEY"
    return None, ""


def frage(modell, frist=60, ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64)", fragen=1):
    key, quelle = schluessel()
    if not key:
        print("kein Schluessel gefunden")
        return
    q = {"q%d" % i: {"type": "noul", "instructions": "Ist das relevant?"} for i in range(1, fragen + 1)}
    koerper = json.dumps({
        "model": modell,
        "state": "Die Datei handeln.py schliesst eine Position, wenn der Stop erreicht ist.",
        "questions": q,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://opencode.ai/zen/v1/systemone", data=koerper,
        headers={"authorization": "Bearer " + key, "content-type": "application/json",
                 "user-agent": ua},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=frist) as r:
            roh = r.read().decode("utf-8", "replace")
            print("%-18s HTTP %s in %.1f s" % (modell, r.status, time.time() - t0))
            print("   Antwort:", roh[:200])
    except urllib.error.HTTPError as e:
        print("%-18s HTTP %s in %.1f s" % (modell, e.code, time.time() - t0))
        print("   Koerper:", e.read().decode("utf-8", "replace")[:200])
    except Exception as e:
        print("%-18s Fehler nach %.1f s: %s: %s" % (modell, time.time() - t0, type(e).__name__, e))
    print("   Schluessel aus:", quelle, "(%d Zeichen)" % len(key))


if __name__ == "__main__":
    for m in ("jev-1.13-free", "jev-1.13"):
        frage(m)