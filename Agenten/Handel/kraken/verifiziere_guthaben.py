import sys, os, time
from pathlib import Path

# Pfad relativ zur eigenen Datei (SSD-umzugsfaehig, kein absoluter Benutzerpfad).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kraken

# Quelle der Schlüssel anzeigen (ohne Werte):
src_key = "os.environ" if os.environ.get("KRAKEN_API_KEY") else "Registry(HKCU\\Environment)"
src_sec = "os.environ" if os.environ.get("KRAKEN_API_SECRET") else "Registry(HKCU\\Environment)"
print("Key-Quelle :", src_key)
print("Secret-Quelle:", src_sec)
print("schluessel_vorhanden:", kraken.schluessel_vorhanden())

ok = False
for i in range(3):
    try:
        r = kraken.guthaben("ZEUR")
        print("GUTHABEN OK  ZEUR=%.4f" % r)
        ok = True
        break
    except Exception as e:
        print("Versuch %d: %s" % (i + 1, str(e)[:60]))
        time.sleep(1.0)

if ok:
    print("ERGEBNIS: GUTHABEN-ABRUF FUNKTIONIERT")
else:
    print("ERGEBNIS: GUTHABEN-ABRUF WEITERHIN FEHLERHAFT")