"""Position vergroessern statt zu doppeln (Auftrag Max 03.10.2026).

GEMESSEN, warum ueberhaupt: vier Spuren stapeln - macd_mtf haelt 4 lange
ETH-Positionen, supertrend 4 kurze BTC, wavetrend 3, kopier1zu1 5 auf zwei
Memecoins. Jedes Signal eroeffnet eine EIGENE Position, obwohl das Signal
dasselbe ist. Der Platzzaehler (max_offene_positionen) zaehlt dann die
Positionsanzahl statt des eingesetzten Kapitals - vier halbe Positionen
sind fuer das Risiko dasselbe wie eine volle, aber fuer den Platzzaehler
viermal so teuer.

DIE REGEL: gleiches Instrument UND gleiche Seite, aber ein NEUES Signal =>
die bestehende Position vergroessern. Der Einstieg wird der gewichtete
Mittelpreis, Stop und Ziel entstehen NEU aus diesem Einstieg und demselben
Prozentsatz (nicht aus dem alten Preis), damit Stop, Ziel und Groesse nicht
auseinanderlaufen. Der Platzzaehler steigt nicht.

NICHT GEAENDERT: die Seitenzahl der Quelle bleibt dieselbe Position. Eine
Gegenposition auf demselben Instrument (Seitenwechsel) ist KEIN Skalieren,
sondern ein neues Signal mit eigener Richtung.

DIE JOURNALFORM ist die entscheidende Stelle. Eine Skalierung ist eine
zweite Kaufzeile mit DERSELBEN pos_id und mit KUMULATIVEM Einsatz und
gewogenem Preis. `auswertung_alle.runden_indikator` laesst darum bei
mehreren Kaufzeilen derselben pos_id die LETZTE gelten - die ist per
Konstruktion der aktuelle Stand der Position. Ohne diese eine Zeile waere
die Runde mit dem ersten, zu kleinen Einsatz gerechnet.
"""

VZ = {"long": 1, "short": -1}


def gleiche_richtung(position, seite):
    """Stimmt die offene Position in Instrument UND Seite?"""
    if not isinstance(position, dict):
        return False
    if (position.get("seite") or "long") != (seite or "long"):
        return False
    return True


def finde_offene(positionen, inst, seite):
    """Die offene Position fuer dieses Signal, oder None."""
    for p in positionen or []:
        if (p or {}).get("inst") != inst:
            continue
        if gleiche_richtung(p, seite):
            return p
    return None


def skaliere(position, einstieg, nominel, stop_pct, r):
    """Die offene Position vergroessern. Gibt die Journal-Felder zurueck.

    `stop_pct` ist der bereits in den Pflichtrahmen gezogene Prozentsatz,
    `r` das Zielvielfache. Beides kommt vom Aufrufer und ist fuer alt und
    neu DASSELBE - deshalb bleiben Stop und Ziel vergleichbar.
    """
    alt_nominal = float(position.get("nominal") or 0.0)
    alt_einstieg = float(position.get("einstieg") or einstieg)
    neu_nominal = alt_nominal + float(nominel)
    if neu_nominal <= 0 or alt_nominal <= 0:
        return None

    # Gewichteter Einstieg: jede Seite traegt ihr Gewicht.
    ein = (alt_einstieg * alt_nominal + float(einstieg) * float(nominel)) / neu_nominal

    vz = VZ.get(position.get("seite") or "long", 1)
    abstand = ein * (float(stop_pct) / 100.0)
    position["einstieg"] = ein
    position["nominal"] = neu_nominal
    position["stop"] = ein - vz * abstand
    position["ziel"] = ein + vz * float(r) * abstand
    position["stop_pct"] = float(stop_pct)
    position["skalierungen"] = int(position.get("skalierungen") or 0) + 1

    return {
        "preis": ein,
        "einsatz_usd": neu_nominal,
        "stop": position["stop"],
        "ziel": position["ziel"],
        "stop_pct": float(stop_pct),
        "nominal": neu_nominal,
        "alt_nominal": alt_nominal,
        "skalierungen": position["skalierungen"],
    }


def letzter_einstieg(zeilen, pos_id):
    """Die gueltige Einstiegszeile einer Position: bei mehreren die LETZTE.

    Sie traegt nach der Skalierungsregel den kumulativen Einsatz und den
    gewogenen Einstieg - also den Stand, den die Runde rechnen muss. Steht
    nur eine, ist das Verhalten unveraendert.
    """
    treffer = [z for z in zeilen if (z.get("pos_id") or "") == (pos_id or "")
               and (z.get("aktion") or "").lower() in ("kauf", "eroeffnen")]
    if not treffer:
        return None
    if len(treffer) == 1:
        return treffer[0]
    # Gleiche Zeitstempel: die spaeter geschriebene Zeile gewinnt, sonst
    # entscheidet die Reihenfolge im Journal (das ist die Schreibreihenfolge).
    return treffer[-1]