"""Der Tagesschnappschuss - nur was die Journale nicht hergeben.

Vier Felder je Spur: offene Positionen, Sperrenlage, Rundenzaehler der
Wachen, Stillgelegt-Merker. Alles andere waere eine zweite Wahrheit; Bilanz
und Trefferquote werden aus den Journalen gerechnet, jedes Mal neu.

Die Feldnamen der Erhebung (schluessel, positionen, sperren, wachen,
stillgelegt) kommen aus lage.zu_lage() - EINE Quelle. Diese Datei schreibt
sie nicht ein zweites Mal auf, sie liest nur heraus, was sie braucht.

Ein verlorener Schnappschuss ist unwiederbringlich. Das ist bewusst in Kauf
genommen: ein fehlender Vortagsvergleich ist eine Unbequemlichkeit, ein
falsch gespiegeltes Buch ein Schaden. Deshalb liegt der Stand zentral unter
stand/ und nicht je Spurordner - spiegelstand.py prueft genau zwei
Dateinamen je Spur, und ein dritter dort waere ein Eingriff in einen
Schreibpfad, den dieser Umbau nicht braucht.
"""
import datetime as dt
import json
import os
import re

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "stand")

# Aufbewahrung. Darstellungsgroesse, keine Handelsgroesse - der Vergleich
# reicht nie weiter zurueck als der Wochenbericht schaut.
AUFBEWAHRUNG_TAGE = 90

_DATEINAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def baue(erhebung, heute=None):
    """Aus der Erhebung den duennen Stand bauen."""
    heute = heute or dt.date.today()
    spuren = {}
    for e in erhebung:
        schluessel = e.get("schluessel") or e.get("name")
        wachen = e.get("wachen") or {}
        spuren[schluessel] = {
            "positionen": [{"name": p.get("name"),
                            "wert": p.get("wert"),
                            "einstieg": p.get("einstieg")}
                           for p in e.get("positionen", [])],
            "sperren": list(e.get("sperren", [])),
            "runden": wachen.get("runden_gesamt") if "fehler" not in wachen else None,
            "stillgelegt": bool(e.get("stillgelegt")),
        }
    return {"datum": heute.isoformat(),
            "gebaut": dt.datetime.now().isoformat(timespec="seconds"),
            "spuren": spuren}


def schreibe(stand, ordner=ORDNER):
    """Den Stand ablegen und danach aufraeumen. Gibt den Pfad zurueck.

    Geschrieben wird in eine Nebendatei, erst danach kommt der Datumsname
    per os.replace() dran - unter Windows wie unter POSIX ein atomarer
    Schritt. Bricht das Serialisieren ab, existiert die Zieldatei entweder
    gar nicht oder noch mit dem alten, vollstaendigen Inhalt - nie mit
    einer halb geschriebenen JSON. Der Name der Nebendatei beginnt mit
    einem Punkt und traegt die PID: weder aufraeumen() noch lade() lesen
    ihn als Schnappschuss, das Datumsmuster passt nicht.
    """
    os.makedirs(ordner, exist_ok=True)
    pfad = os.path.join(ordner, "%s.json" % stand["datum"])
    neben = os.path.join(ordner, ".%s.json.tmp-%d" % (stand["datum"], os.getpid()))
    try:
        with open(neben, "w", encoding="utf-8") as f:
            json.dump(stand, f, ensure_ascii=False, indent=1)
        os.replace(neben, pfad)
    except BaseException:
        try:
            os.remove(neben)
        except OSError:
            pass
        raise
    aufraeumen(ordner=ordner)
    return pfad


def lade(datum, ordner=ORDNER):
    """Der Stand eines Tages, oder None. Ein fehlender Stand ist kein Fehler."""
    if hasattr(datum, "isoformat"):
        datum = datum.isoformat()
    try:
        with open(os.path.join(ordner, "%s.json" % datum), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def aufraeumen(ordner=ORDNER, tage=AUFBEWAHRUNG_TAGE):
    """Staende aelter als 'tage' entfernen. Nur Dateien im Datumsformat -
    was sonst in dem Ordner liegt, gehoert jemand anderem."""
    grenze = dt.date.today() - dt.timedelta(days=tage)
    weg = 0
    try:
        namen = os.listdir(ordner)
    except OSError:
        return 0
    for name in namen:
        treffer = _DATEINAME.match(name)
        if not treffer:
            continue
        pfad = os.path.join(ordner, name)
        if not os.path.isfile(pfad):
            continue
        try:
            wann = dt.date.fromisoformat(treffer.group(1))
        except ValueError:
            continue
        if wann < grenze:
            try:
                os.remove(pfad)
                weg += 1
            except OSError:
                pass
    return weg


def unterschiede(heute, gestern):
    """Was sich seit gestern geaendert hat, je Spur.

    Fehlt der Vorgaenger, ist das Ergebnis leer - der Bericht schreibt dann
    einen Satz und baut trotzdem.
    """
    if not gestern:
        return {}
    aus = {}
    for name, h in heute.get("spuren", {}).items():
        g = gestern.get("spuren", {}).get(name)
        if g is None:
            continue
        alt_pos = {p["name"] for p in g["positionen"]}
        neu_pos = {p["name"] for p in h["positionen"]}
        alt_sperre, neu_sperre = set(g["sperren"]), set(h["sperren"])
        d = {
            "position_neu": sorted(neu_pos - alt_pos),
            "position_weg": sorted(alt_pos - neu_pos),
            "sperre_neu": sorted(neu_sperre - alt_sperre),
            "sperre_weg": sorted(alt_sperre - neu_sperre),
            "runden_mehr": (h["runden"] or 0) - (g["runden"] or 0),
            "stillgelegt_neu": h["stillgelegt"] and not g["stillgelegt"],
        }
        if any(d[k] for k in d):
            aus[name] = d
    return aus
