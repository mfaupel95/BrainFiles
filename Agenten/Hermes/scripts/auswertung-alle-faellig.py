"""Faehrt die Auswertung ALLER Handelsspuren, sobald sie faellig ist.

Schwester von spiegel-auswertung-faellig.py, aber fuer den ganzen Baum:
auswertung_alle.py deckt 25 Spuren ab (Kern-, Indikator- und Bot-Spuren).

Faellig ist eine Spur, wenn seit dem letzten Lauf mindestens
NEUE_RUNDEN geschlossene Runden dazugekommen sind. Gemessen wird ueber
auswertung_alle.kennzahlen_fuer() - dieselbe Funktion, die auch die
Auswertung selbst benutzt. Einen eigenen Ausstiegsbegriff nachzubauen
waere ein zweiter, der irgendwann auseinanderlaeuft.

Warum nicht taeglich stur durchlaufen: der volle Lauf dauert ueber sieben
Minuten, weil er Kurse holt. Eine Auswertung auf unveraenderter Datenlage
wiederholt nur ihr eigenes Ergebnis.

Watchdog-Muster: leere Ausgabe = nichts senden.
Der Stand steht in auswertung-alle-stand.json neben diesem Skript.
Ein fehlgeschlagener Lauf bewegt den Stand NICHT.

MELDUNG: Nur die faelligen Spuren werden genannt, nicht alle 25 - eine
Telegram-Nachricht mit 25 Bloecken liest niemand. Wer den ganzen Bericht
will, faehrt auswertung_alle.py selbst.
"""
import json
import os
import subprocess
import sys

# Ab wievielen NEUEN geschlossenen Runden je Spur eine Auswertung lohnt.
# 5 ist bewusst niedriger als die 25 der Spiegel-Automatik: die meisten
# Spuren hier haben zweistellige Rundenzahlen, nicht vierstellige. Bei 25
# wuerden sie nie ausgewertet.
NEUE_RUNDEN = 5

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.abspath(os.path.join(HIER, "..", "..", "Handel"))
PYTHON = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")
STAND = os.path.join(HIER, "auswertung-alle-stand.json")


def lade_stand():
    try:
        with open(STAND, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return {}


def schreibe_stand(stand):
    with open(STAND, "w", encoding="utf-8") as fh:
        json.dump(stand, fh, indent=2, ensure_ascii=False)


def runden_je_spur():
    """Geschlossene Runden je Spur, ueber die Auswertung selbst gemessen.

    Laeuft in einem eigenen Prozess mit dem Handel-venv: auswertung_alle
    importiert Spur-Module, die nicht in die Hermes-Umgebung gehoeren.
    """
    code = (
        "import json, sys\n"
        "sys.path.insert(0, %r)\n"
        "import auswertung_alle as a\n"
        "aus = {}\n"
        "for s in a.SPUREN:\n"
        "    try:\n"
        "        k = a.kennzahlen_fuer(s)\n"
        "        aus[s] = int(k.get('n', 0)) if k else 0\n"
        "    except Exception:\n"
        "        aus[s] = 0\n"
        "print(json.dumps(aus))\n" % HANDEL
    )
    p = subprocess.run([PYTHON, "-c", code], cwd=HANDEL,
                       capture_output=True, text=True, timeout=900)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "")[-400:])
    for zeile in reversed((p.stdout or "").strip().splitlines()):
        zeile = zeile.strip()
        if zeile.startswith("{"):
            return json.loads(zeile)
    raise RuntimeError("keine Zaehlung erhalten")


def auswertung_einer_spur(spur):
    """Der Auswertungsblock EINER Spur, wie auswertung_alle.py ihn druckt."""
    p = subprocess.run([PYTHON, "auswertung_alle.py", "--spur", spur],
                       cwd=HANDEL, capture_output=True, text=True, timeout=900)
    if p.returncode != 0:
        return "FEHLGESCHLAGEN - " + (p.stderr or p.stdout or "").strip()[-300:]
    zeilen = []
    for z in (p.stdout or "").splitlines():
        s = z.strip()
        if not s or s.startswith("==="):
            continue
        zeilen.append("  " + s)
        if len(zeilen) >= 7:
            break
    return "\n".join(zeilen)


def main():
    if not os.path.exists(PYTHON):
        print("Auswertung-alle: venv fehlt (%s)" % PYTHON)
        return
    stand = lade_stand()
    try:
        jetzt = runden_je_spur()
    except Exception as e:
        print("Auswertung-alle: Zaehlung fehlgeschlagen - %s" % e)
        return

    faellig = [(s, stand.get(s, 0), n) for s, n in sorted(jetzt.items())
               if n - stand.get(s, 0) >= NEUE_RUNDEN]
    if not faellig:
        return  # nichts Neues - schweigen

    teile = []
    for spur, vorher, n in faellig:
        block = auswertung_einer_spur(spur)
        teile.append("%s (%d -> %d Runden):\n%s" % (spur, vorher, n, block))
        if not block.startswith("FEHLGESCHLAGEN"):
            stand[spur] = n

    for spur, n in jetzt.items():
        stand.setdefault(spur, 0)
    schreibe_stand(stand)

    print("Spur-Auswertung faellig und gefahren (%d Spur(en)):\n\n%s"
          % (len(faellig), "\n\n".join(teile)))


if __name__ == "__main__":
    main()