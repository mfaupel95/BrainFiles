"""SWAP-Universum: welche gewoehnlichen Perpetuals taugen wofuer.

Dieselbe Frage wie xperp/auswahl.py, aber fuer instType=SWAP. Die XPERP-Auswahl
findet nur ruleType=xperp unter FUTURES (okxf.instrumente), darum erreicht kein
SWAP-Wert je eine Rangliste.

Nichts wird kopiert, was schon da ist: Kennzahlen, Ruecklauf, Hebel-Deckel,
Bewertung und Tabellenausgabe kommen aus xperp/auswahl.py, der Kontraktzugang aus
xperp/okxf.py. Neu ist nur das Universum.

okxf.py bleibt unangetastet - die Datei traegt den Live-Pfad von xperp. Der
bestehende Abfrageweg wird mitbenutzt (okxf._mit_wiederholung, dieselbe Stelle,
die okxf.instrumente() fuer FUTURES nutzt). Sobald diese Spur mehr als Papier
ist, gehoert dieselbe Abfrage als oeffentliche Funktion instrumente_swap() nach
okxf.py - nicht als zweite Fassung hier.

Auf diesem Konto ist nur der XPERP-Zweig handelbar (gemessen am 25.09.2026: der
gewoehnliche XAU-USDT-SWAP antwortet auf eine Order mit OKX 50124 'does not have
trading permission for the market', waehrend XAU-USD_UM_XPERP-310502 am
24.09.2026 mit 93 Kontrakten gefuellt wurde). Die Rangliste bleibt deshalb beim
umsatzstaerkeren gewoehnlichen Perpetual - er ist die oeffentliche
Kennzahlenquelle und hat die laengere Kerzenhistorie -, gehandelt wird der
XPERP-Kontrakt derselben Familie (handels_kontrakte). Eine Reihe ohne Zwilling
faellt aus der Liste.

Diese Datei liest nur. Sie importiert keine Order-Funktion, und kein Test darf
je eine Order erreichen.

Aufruf:
    python kandidaten.py --zweck long
    python kandidaten.py --zweck grid --anzahl 20
    python kandidaten.py --wert CHIP

Geschwindigkeit: Das SWAP-Universum ist gross (478 lebende Reihen am
11.09.2026). Fuer jede Reihe kostet die Bewertung zwei Kerzenabrufe, und OKX
laesst rund 40 Anfragen je 2 s zu. Ein voller Durchlauf dauert also Minuten.
Daruer wird vorher nach Umsatz sortiert und nur die Spitze geholt
(--vorsortiert, Standard 60). Die Zahl steht im Kopf der Ausgabe, damit eine
kurze Liste nie wie ein leeres Universum aussieht.
"""

import argparse
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
XPERP = os.path.join(os.path.dirname(HIER), "xperp")
if XPERP not in sys.path:
    sys.path.insert(0, XPERP)

import auswahl                                                # noqa: E402
import okxf                                                   # noqa: E402

BAR = auswahl.BAR
MIN_KERZEN = auswahl.MIN_KERZEN
PRO_TAG = auswahl.PRO_TAG

# instCategory trennt auch bei SWAP die Familien - dieselben Codes wie unter
# FUTURES, siehe okxf.py oben. Unbekanntes wird als Krypto gefuehrt: lieber ein
# zu weites Tor als ein Wert, der still aus der Liste faellt.
FAMILIE = {okxf.KRYPTO: "krypto", okxf.AKTIE: "aktie", okxf.ROHSTOFF: "rohstoff"}

# Nur lineare USDT-Perpetuals. Inverse Kontrakte rechnen in der Muenze, haben
# eine andere ctVal-Form und gehoeren nicht in dieselbe Positionsrechnung.
QUOTE = "-USDT-SWAP"

VORSORTIERT = 60


def handels_kontrakte():
    """{Basiswert: XPERP-Kontrakt} - der handelbare Zwilling je Reihe.

    EINE Abfrage fuer alle Reihen statt einer je Kandidat. Nur ruleType=xperp
    unter instType=FUTURES: der gewoehnliche Perpetual desselben Basiswerts ist
    auf diesem Konto nicht handelbar (OKX 50124, siehe Kopf dieser Datei).
    Der volle Datensatz wird mitgegeben, damit handeln.anlauf() ctVal, tickSz
    und Hebel-Deckel des GEHANDELTEN Kontrakts nimmt.
    """
    d = okxf._mit_wiederholung("/api/v5/public/instruments?instType=FUTURES")
    m = {}
    for x in d:
        if x.get("ruleType") != "xperp" or x.get("state") != "live":
            continue
        m.setdefault(basiswert(x["instId"]), x)
    return m


def instrumente():
    """Alle lebenden linearen USDT-Perpetuals, nach instId sortiert."""
    d = okxf._mit_wiederholung(
        "/api/v5/public/instruments?instType=SWAP")
    xp = [x for x in d
          if x.get("state") == "live"
          and x.get("ctType") == "linear"
          and x.get("settleCcy") == "USDT"
          and x.get("instId", "").upper().endswith(QUOTE)]
    return sorted(xp, key=lambda x: x["instId"])


def basiswert(inst_id):
    """'CHIP-USDT-SWAP' -> 'CHIP'. Der Basiswert ist der Schluessel der Liste."""
    return inst_id.split("-")[0].upper()


def familie(x):
    """Familie aus instCategory, unbekannt = krypto."""
    return FAMILIE.get(x.get("instCategory"), "krypto")


def umsatz_je_reihe(tick):
    """24h-Umsatz in USD je instId, zum Vorsortieren.

    volCcy24h ist bereits Basiswaehrung (Kontrakte x ctVal). Wer hier nochmal
    mit ctVal multipliziert, meldet BONK mit Billionen - derselbe Fehler wie in
    auswahl.sammle(), dort steht der Vermerk.
    """
    return {iid: float(t.get("volCcy24h") or 0) * float(t.get("last") or 0)
            for iid, t in tick.items()}


def sammle(werte=None, still=False, familien=None, vorsortiert=VORSORTIERT):
    """Kennzahlen der SWAP-Reihen, gleiche Form wie auswahl.sammle().

    werte       - Liste von Basiswerten, None = alle
    familien    - Liste aus ('krypto', 'aktie', 'rohstoff'), None = alle
    vorsortiert - nur die umsatzstaerksten N Reihen bewerten
    """
    tick = okxf.tickers("SWAP")
    umsatz24 = umsatz_je_reihe(tick)
    kontrakte = handels_kontrakte()

    instr, familie_je_basis = {}, {}
    for x in instrumente():
        fam = familie(x)
        if familien and fam not in familien:
            continue
        instr[x["instId"]] = x
        familie_je_basis[x["instId"]] = fam

    if werte:
        gesucht = {w.upper() for w in werte}
        instr = {iid: x for iid, x in instr.items()
                 if basiswert(iid) in gesucht}
        vorsortiert = None

    if vorsortiert:
        geordnet = sorted(instr, key=lambda i: -umsatz24.get(i, 0.0))
        instr = {i: instr[i] for i in geordnet[:vorsortiert]}

    ergebnis = []
    ohne_kontrakt = 0
    for i, (iid, x) in enumerate(sorted(instr.items()), 1):
        if not still:
            print("  %3d/%d %-10s" % (i, len(instr), basiswert(iid)), end="\r",
                  file=sys.stderr)
        try:
            k = okxf.kerzen(iid, BAR, 300)
        except Exception:                                     # noqa: BLE001
            continue
        if len(k) < MIN_KERZEN:
            continue
        z = auswahl.kennzahlen(k)

        # Hebel-Deckel aus TAGESkerzen, nicht aus den 4H-Kerzen: 300 4H-Kerzen
        # sind 50 Tage, 300 Tageskerzen sind 300. Begruendung steht in
        # auswahl.sammle(), sie gilt hier unveraendert.
        try:
            kt = okxf.kerzen(iid, "1D", 300)
            if len(kt) >= 14:
                z["mae_long"], z["mae_short"] = auswahl.mae_tage(kt, 7)
                z["tage_gemessen"] = len(kt)
            time.sleep(0.06)
        except Exception:                                     # noqa: BLE001
            z["tage_gemessen"] = len(k) / PRO_TAG

        fam = familie_je_basis[iid]
        kat = auswahl.KATEGORIEN[fam]
        umsatz = umsatz24.get(iid, 0.0)

        # Gehandelt wird der XPERP-Zwilling, nicht der gewoehnliche Perpetual:
        # nur der XPERP-Zweig ist auf diesem Konto handelbar. Ohne Zwilling
        # faellt die Reihe aus der Liste - ein Vorschlag, den die Boerse mit
        # 50124 abweist, ist kein Vorschlag. Die Kennzahlen bleiben am
        # umsatzstaerkeren Perpetual gemessen (laengere Kerzenhistorie).
        twin = kontrakte.get(basiswert(iid))
        if not twin:
            ohne_kontrakt += 1
            continue
        z.update(basis=basiswert(iid), instId=iid,
                 handels_instId=twin["instId"], handels_instr=twin,
                 umsatz=umsatz, kategorie=fam, vola_tor=kat["vola_tor"],
                 max_lever=float(twin.get("lever") or 0),
                 punkte=auswahl.bewerte(z, umsatz, kat["umsatz_bezug"]))
        ergebnis.append(z)
        time.sleep(0.06)
    if not still:
        print(" " * 30, end="\r", file=sys.stderr)
        if ohne_kontrakt:
            print("  %d Reihe(n) ohne XPERP-Zwilling uebersprungen"
                  % ohne_kontrakt, file=sys.stderr)
    return ergebnis


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zweck", choices=("long", "short", "grid", "alle"), default="alle")
    p.add_argument("--wert", help="ein Basiswert im Detail, z.B. CHIP")
    p.add_argument("--anzahl", type=int, default=12)
    p.add_argument("--familie", choices=tuple(auswahl.KATEGORIEN) + ("alle",), default="alle")
    p.add_argument("--vorsortiert", type=int, default=VORSORTIERT,
                   help="so viele der umsatzstaerksten Reihen bewerten")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    fams = None if a.familie == "alle" else [a.familie]

    if a.wert:
        d = sammle([a.wert.upper()], familien=fams)
        if not d:
            print("kein lebender SWAP zu %r (oder zu wenig Historie)" % a.wert)
            return 1
        auswahl.detail(d[0])
        return 0

    gesamt = len(instrumente())
    print("SWAP-Universum: %d lebende USDT-Perpetuals, bewertet werden die %d "
          "umsatzstaerksten (%s-Kerzen)"
          % (gesamt, a.vorsortiert, BAR), file=sys.stderr)
    d = sammle(familien=fams, vorsortiert=a.vorsortiert)
    print("%d SWAP-Werte bewertet, %s" % (len(d), time.strftime("%Y-%m-%d %H:%M")))
    for zweck in (("long", "short", "grid") if a.zweck == "alle" else (a.zweck,)):
        auswahl.tabelle(d, zweck, a.anzahl)
    print()
    print("Tore je Familie wie in der XPERP-Auswahl - dieselben Massstaebe, "
          "damit die Listen vergleichbar bleiben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
