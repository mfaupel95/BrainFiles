"""Die 13 verwaisten Limit-Auftraege der xperp-Spur stornieren.

Sie sind das Ergebnis des heute behobenen Fehlers: pruefe_einstiege() zaehlte
wartende Auftraege nicht als belegten Platz, also legte jeder Zyklus fuer
denselben Basiswert nach (CL sechsmal, XAU fuenfmal, BZ und CRCL je einmal).

Regel fuer das Aufraeumen: je Basiswert bleibt der JUENGSTE Auftrag stehen -
er traegt den aktuellsten Zonenpreis -, alle aelteren werden storniert. Damit
verliert die Spur keine Gelegenheit, nur die Dubletten.

Ohne --anwenden wird nur gezeigt, was geschehen wuerde.
"""

import json
import sys
from pathlib import Path

# Pfad relativ zur eigenen Datei (SSD-umzugsfaehig, kein absoluter Benutzerpfad).
HANDEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HANDEL / "xperp"))
import okxf                                                        # noqa: E402

ANWENDEN = "--anwenden" in sys.argv

offen = okxf._mit_wiederholung(
    "/api/v5/trade/orders-pending?instType=FUTURES", signiert=True)
print("Offene Auftraege an der Boerse: %d" % len(offen))

nach_inst = {}
for o in offen:
    nach_inst.setdefault(o.get("instId"), []).append(o)

storno, behalten = [], []
for inst, liste in sorted(nach_inst.items()):
    liste.sort(key=lambda o: int(o.get("cTime") or 0), reverse=True)
    behalten.append(liste[0])
    storno.extend(liste[1:])
    print("  %-26s %d Auftrag/Auftraege -> 1 behalten, %d stornieren"
          % (inst, len(liste), len(liste) - 1))

print()
print("Behalten (juengster je Basiswert):")
for o in behalten:
    print("  %-26s %s sz=%s px=%s ordId=%s"
          % (o.get("instId"), o.get("side"), o.get("sz"), o.get("px"),
             o.get("ordId")))
print()
print("Stornieren: %d" % len(storno))

if not ANWENDEN:
    print("\n(Trockenlauf - mit --anwenden wird wirklich storniert)")
    raise SystemExit(0)

fehler = 0
for o in storno:
    # FALLE: _roh() macht json.dumps(body) selbst - hier ein DICT uebergeben,
    # kein fertiger JSON-String, sonst wird doppelt kodiert und OKX antwortet
    # mit HTTP 400 (gemessen 21.09.2026: neunmal hintereinander).
    try:
        okxf._mit_wiederholung("/api/v5/trade/cancel-order", methode="POST",
                               body={"instId": o.get("instId"),
                                     "ordId": o.get("ordId")},
                               signiert=True)
        print("  storniert: %-26s %s" % (o.get("instId"), o.get("ordId")))
    except Exception as e:                                         # noqa: BLE001
        fehler += 1
        print("  FEHLER bei %s %s: %s" % (o.get("instId"), o.get("ordId"), e))

rest = okxf._mit_wiederholung(
    "/api/v5/trade/orders-pending?instType=FUTURES", signiert=True)
print("\nNachher offen: %d (Fehler: %d)" % (len(rest), fehler))
for o in rest:
    print("  %-26s %s px=%s" % (o.get("instId"), o.get("side"), o.get("px")))
