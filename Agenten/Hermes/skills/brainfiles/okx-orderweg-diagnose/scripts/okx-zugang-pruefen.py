"""Rein lesende Sonde fuer den OKX-Zugang einer Live-Spur.

BEANTWORTET in EINEM Lauf die Fragen, die eine gescheiterte Order aufwirft:
welcher HOST wird angesprochen, ist der Schluessel da, darf er HANDELN, wieviel
ist von der Quote-Waehrung FREI, und steht fuer jede Live-Position ein
NOTAUSSTIEG an der Boerse. Setzt KEINE Order, verschiebt kein Guthaben, liest
keine Schluesselwerte aus.

Aufruf (aus einem beliebigen Ordner), mit dem venv der Spur:
    Agenten/Handel/scanner/.venv/Scripts/python.exe \\
        Agenten/Hermes/skills/brainfiles/okx-orderweg-diagnose/scripts/okx-zugang-pruefen.py \\
        [spur-ordner]            # Standard: scanner

Rueckgabe 0 = alles lesbar. 1 = ein Abruf ist gescheitert (Text sagt welcher).
"""

from __future__ import annotations

import os
import sys

# --- Spurordner und Haus-Modul finden (keine absoluten Benutzerpfade) --------
HIER = os.path.dirname(os.path.abspath(__file__))
for _ in range(6):                     # scripts -> skill -> brainfiles -> skills
    HIER = os.path.dirname(HIER)       # -> Hermes -> Agenten -> BrainFiles
WURZEL = HIER
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")
SPUR = sys.argv[1] if len(sys.argv) > 1 else "scanner"
SPURORDNER = os.path.join(HANDEL, SPUR)

if not os.path.isdir(SPURORDNER):
    print("Spurordner nicht gefunden: %s" % SPURORDNER)
    sys.exit(1)

sys.path.append(SPURORDNER)            # ans ENDE: nichts verdraengen
import okx  # noqa: E402

probleme = []


def zeige(titel: str, wert) -> None:
    print("%-34s %s" % (titel + ":", wert))


print("Sonde fuer Spur '%s'" % SPUR)
print("-" * 60)

# 1) Host und Schluessel: BEIDE gehoeren zu einem Zugang.
print("1) Zugang")
zeige("angesprochener Host", okx._live_basis())
zeige("Schluessel vorhanden", okx.schluessel_vorhanden())
zeige("Registry-Host", os.environ.get("OKX_BASE") or "(nicht in der Prozessumgebung)")
if not okx.schluessel_vorhanden():
    probleme.append("Schluessel fehlen (Key/Secret/Passphrase)")

# 2) Handelsrecht und IP-Sperre.
print("\n2) Recht des Schluessels")
try:
    r = (okx._roh("/api/v5/account/config", "GET", signiert=True) or [{}])[0]
    zeige("Kontolevel (acctLv)", r.get("acctLv"))
    zeige("Rechte (perm)", r.get("perm"))
    zeige("Positionsmodus", r.get("posMode"))
    zeige("IP-Sperre (ip)", r.get("ip") or "(leer = keine Sperre)")
    if "trade" not in str(r.get("perm") or ""):
        probleme.append("Schluessel darf NICHT handeln (perm ohne 'trade')")
except Exception as e:                                              # noqa: BLE001
    probleme.append("account/config nicht lesbar: %s" % e)
    print("   FEHLER: %s" % e)

# 3) Freie Quote-Waehrung je Waehrung (was koennte ein Kauf bezahlen).
print("\n3) Guthaben (availEq = frei)")
try:
    b = okx._roh("/api/v5/account/balance", "GET", signiert=True) or [{}]
    for det in (b[0].get("details") or []):
        frei = float(det.get("availEq") or 0)
        ganz = float(det.get("eq") or 0)
        if frei or ganz:
            zeige("  " + str(det.get("ccy")),
                  "frei %.8g | gesamt %.8g | gesperrt %.8g"
                  % (frei, ganz, ganz - frei))
except Exception as e:                                              # noqa: BLE001
    probleme.append("balance nicht lesbar: %s" % e)
    print("   FEHLER: %s" % e)

# 4) Offene Auftraege und Notausstiege: fehlt ein Stop, ist das ein Risiko.
print("\n4) Offene Auftraege")
try:
    offen = okx._roh("/api/v5/trade/orders-pending?instType=SPOT",
                     "GET", signiert=True) or []
    zeige("  wartende Orders", len(offen))
    for o in offen:
        zeige("    " + str(o.get("instId")),
              "%s sz=%s" % (o.get("side"), o.get("sz")))
except Exception as e:                                              # noqa: BLE001
    probleme.append("orders-pending nicht lesbar: %s" % e)

print("\n   Notausstiege (conditional)")
try:
    algos = okx._roh("/api/v5/trade/orders-algo-pending?ordType=conditional",
                     "GET", signiert=True) or []
    geschuetzt = set()
    for a in algos:
        geschuetzt.add(str(a.get("instId")))
        zeige("    " + str(a.get("instId")),
              "Stop %s sz=%s algoId=%s"
              % (a.get("slTriggerPx") or a.get("triggerPx"), a.get("sz"),
                 a.get("algoId")))
    if not algos:
        print("    keine - eine Live-Position ohne Stop laeuft bis zur Liquidation")
except Exception as e:                                              # noqa: BLE001
    geschuetzt = None
    probleme.append("orders-algo-pending nicht lesbar: %s" % e)

# 5) Buch der Spur dagegen halten (Positionen ohne Boersen-Stop sind der Fund).
try:
    import json
    with open(os.path.join(SPURORDNER, "zustand.json"), encoding="utf-8") as f:
        z = json.load(f)
    print("\n5) Buch der Spur")
    for p in z.get("positionen", []):
        lebt = str(p.get("modus") or "") == "live" or "kauf_ord_id" in p
        ohne = (geschuetzt is not None and lebt
                and str(p.get("inst")) not in geschuetzt)
        zeige("  " + str(p.get("inst")),
              "%s%s" % (p.get("seite") or "?",
                        "  OHNE BOERSEN-STOP" if ohne else ""))
        if ohne:
            probleme.append("%s lebt und hat keinen Stop an der Boerse"
                            % p.get("inst"))
except FileNotFoundError:
    print("\n5) Buch: zustand.json fehlt (noch nie gelaufen)")

print("\n" + "-" * 60)
if probleme:
    print("BEFUNDE:")
    for p in probleme:
        print("  - %s" % p)
    sys.exit(1)
print("kein Befund - Zugang, Quote und Stops sind in Ordnung")
sys.exit(0)
