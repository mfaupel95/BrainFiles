"""Prueft die Form einer Rueckgabe der Handelskette gegen RUECKGABEN.md.

  python rueckgabe_pruefen.py <scanner|pruefer|disponent> <datei|->

Exitcode 0 = Form in Ordnung, 1 = Verstoss (Liste auf stdout), 2 = Aufruf falsch.
Prueft nur die Form (Statuszeile, Pflichtfelder, Zahlenformat), nie die Fachlichkeit.
"""
import re
import sys

STATUS = {
    "scanner": {"kandidaten", "heute-nichts", "eingabe-ungueltig"},
    "pruefer": {"geprueft", "eingabe-ungueltig"},
    "disponent": {"auftrag", "grenze-verletzt", "eingabe-ungueltig"},
}
KANDIDAT = ("paar", "richtung", "spur", "atr_pct", "warum", "dagegen")
PRUEFER = ("urteil", "tragende_zahl", "stichprobe_n", "zeitraum", "gegenszenario",
           "widerlegt_ab_kurs", "atr_pct", "nicht_geprueft")
DISPONENT = ("paar", "richtung", "spur", "einstieg", "stop", "stopweite_pct",
             "stopweite_atr", "positionswert", "margin", "hebel", "risikobetrag",
             "wachen", "befehl", "dagegen")
ZAHL = re.compile(r"^-?\d+([.,]\d+)?")


def felder(zeilen):
    d = {}
    for z in zeilen:
        m = re.match(r"^\s*-?\s*([a-z_]+):\s*(.*)$", z)
        if m:
            d.setdefault(m.group(1), m.group(2))
    return d


def pruefe(stufe, text):
    zeilen = text.strip().splitlines()
    fehler = []
    if not zeilen or not zeilen[0].startswith("status: "):
        return ["Zeile 1 ist nicht `status: <wert>`"]
    status = zeilen[0][8:].strip()
    if status not in STATUS[stufe]:
        return ["unbekannter status %r (erlaubt: %s)" % (status, ", ".join(sorted(STATUS[stufe])))]
    rest = zeilen[1:]
    if status == "eingabe-ungueltig":
        if "feld" not in felder(rest):
            fehler.append("eingabe-ungueltig ohne `feld:`")
        return fehler
    if stufe == "scanner":
        kand = [z for z in rest if re.match(r"^\s*-?\s*kandidat:", z)]
        if status == "heute-nichts" and kand:
            fehler.append("heute-nichts darf keine Kandidaten enthalten")
        if status == "kandidaten":
            if not 1 <= len(kand) <= 5:
                fehler.append("kandidaten braucht 1-5 `kandidat:`-Zeilen, gefunden %d" % len(kand))
            for z in kand:
                f = dict(re.findall(r"([a-z_]+)=([^;]*)", z.split("kandidat:", 1)[1]))
                for k in KANDIDAT:
                    if not f.get(k, "").strip():
                        fehler.append("Kandidat ohne %s: %s" % (k, z.strip()[:60]))
                if f.get("richtung", "").strip() not in ("long", "short"):
                    fehler.append("richtung nicht long|short: %s" % z.strip()[:60])
                if f.get("spur", "").strip() not in ("1", "2"):
                    fehler.append("spur nicht 1|2: %s" % z.strip()[:60])
                if not ZAHL.match(f.get("atr_pct", "").strip()):
                    fehler.append("atr_pct keine Zahl: %s" % z.strip()[:60])
    else:
        f = felder(rest)
        pflicht = PRUEFER if stufe == "pruefer" else DISPONENT
        for k in pflicht:
            if k not in f:
                fehler.append("Pflichtfeld fehlt: " + k)
        if stufe == "pruefer":
            if f.get("urteil") not in (None, "ja", "nein"):
                fehler.append("urteil nicht ja|nein")
            for k in ("widerlegt_ab_kurs", "atr_pct", "stichprobe_n"):
                if k in f and not ZAHL.match(f[k]):
                    fehler.append("%s keine Zahl" % k)
        else:
            for k in ("einstieg", "stop", "stopweite_pct", "stopweite_atr", "positionswert", "margin", "hebel"):
                if k in f and not ZAHL.match(f[k]):
                    fehler.append("%s keine Zahl" % k)
    return fehler


def main(argv):
    if len(argv) != 3 or argv[1] not in STATUS:
        print(__doc__)
        return 2
    text = sys.stdin.read() if argv[2] == "-" else open(argv[2], encoding="utf-8").read()
    fehler = pruefe(argv[1], text)
    print("\n".join(fehler) if fehler else "Form in Ordnung")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
