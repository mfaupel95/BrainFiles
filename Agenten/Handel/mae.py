"""MAE/MFE nachtragen - die Kennzahl, ohne die kein Stop begruendbar ist
(Auftrag Max 03.10.2026).

BEFUND, aus dem die Aufgabe entstand: `strategie_kennzahlen.py` meldete fuer
ALLE Spuren ausser dem scanner "MAE ungefuehrt". Der Stop-Vorschlag aus dem
90-%-Quantil der MAE der Gewinner ist damit nur fuer eine einzige Spur
rechenbar. Ueberall sonst wird die Stop-Breite geraten.

WAS GEMESSEN WIRD: MAE (Maximum Adverse Excursion, der groesste Gegenlauf in
Prozent des Einstiegs) und MFE (der groesste Vorlauf). Zusammen beantworten
sie die eine Frage, die kein Trefferquotenwert beantwortet: Lief die Position
erst ins Plus und drehte dann um (Stop zu eng), oder lief sie sofort gegen
den Einstieg (Signal falsch)? Ein Haus mit 40 % Treffer und 0 % MAE hat
einen zu engen Stop; eines mit 40 % Treffer und −6 % MAE hat ein falsches
Signal.

ZWEI DINGE, DIE DIESES MODUL VOM SCANNER UNTERSCHEIDET:

1. **Der Richtungsfaktor.** Der scanner ist long-only, seine Formel
   braucht ihn nicht. Die uebrigen Spuren handeln auch short - dort ist
   `bewegung = (kurs - einstieg) / einstieg * 100 * (+1 long / -1 short)`.
   Ohne den Faktor bekommt eine Short-Position bei fallendem Kurs eine
   negative MAE und damit das falsche Vorzeichen.
2. **Die Untergrenze bleibt eine Untergrenze.** Gemessen wird an den
   Zykluspunkten; die echten Extreme dazwischen liegen weiter aussen. Das
   steht so im Journal, damit niemand die Zahl fuer eine Schluesselung
   haelt (T-119).

Altbestand ohne die Felder faellt ueber .get() auf 0.0 zurueck und wird ab
dem naechsten Zyklus mitgemessen - rueckwirkend wird nichts rekonstruiert.
"""
from datetime import date

FELDER = ("mfe_pct", "mae_pct", "haltetage")


def richtung_faktor(p):
    """+1 long, -1 short. Fehlt das Feld, gilt long.

    ZWEI Schreibweisen im Haus: die Indikatorspuren fuehren `seite`, die
    orb-Spuren fuehren `richtung`. Beide zu lesen ist billiger als zwei
    Formeln zu pflegen - und eine Position ohne erkannte Richtung
    bekam sonst stillschweigend das Vorzeichen von long.
    """
    feld = p.get("seite") or p.get("richtung") or "long"
    return -1.0 if str(feld).lower().startswith("short") else 1.0


def merke_extrem(p, kurs):
    """MFE und MAE der Position fortschreiben. Gibt (mfe, mae) zurueck."""
    try:
        einstieg = float(p.get("einstieg"))
        kurs = float(kurs)
    except (TypeError, ValueError):
        return p.get("mfe_pct"), p.get("mae_pct")
    if not einstieg:
        return p.get("mfe_pct"), p.get("mae_pct")

    bewegung = (kurs - einstieg) / einstieg * 100.0 * richtung_faktor(p)
    try:
        mfe = float(p.get("mfe_pct") or 0.0)
        mae = float(p.get("mae_pct") or 0.0)
    except (TypeError, ValueError):
        mfe = mae = 0.0
    # Ein Vorlauf ist nie negativ, ein Gegenlauf nie positiv.
    p["mfe_pct"] = max(mfe, bewegung, 0.0)
    p["mae_pct"] = min(mae, bewegung, 0.0)
    return p["mfe_pct"], p["mae_pct"]


def haltetage(p, heute=None):
    """Kalendertage seit dem Einstieg. Leerer String, wenn unbekannt -
    Altbestand wird nicht geraten."""
    # orb fuehrt den Einstiegstag als `tag` (ein ISO-Datum).
    eroeffnet = (p.get("eroeffnet_zeit") or p.get("eroeffnet")
                or p.get("tag") or "")
    if isinstance(eroeffnet, str):
        eroeffnet = eroeffnet[:10]
    if not eroeffnet or len(str(eroeffnet)) != 10:
        return ""
    try:
        von = date.fromisoformat(str(eroeffnet))
    except ValueError:
        return ""
    heute = heute or date.today()
    if isinstance(heute, str):
        try:
            heute = date.fromisoformat(heute[:10])
        except ValueError:
            heute = date.today()
    return max(0, (heute - von).days)


def felder(p, heute=None):
    """Die drei Spalten fuer eine Ausstiegszeile."""
    return {
        "mfe_pct": "%.4f" % float(p.get("mfe_pct") or 0.0),
        "mae_pct": "%.4f" % float(p.get("mae_pct") or 0.0),
        "haltetage": haltetage(p, heute),
    }


def kopfzeile_ergaenzen(felder_liste):
    """Die Journal-Kopfzeile um die drei Spalten ergaenzen, ohne Dopplung."""
    raus = list(felder_liste)
    for f in FELDER:
        if f not in raus:
            raus.append(f)
    return raus