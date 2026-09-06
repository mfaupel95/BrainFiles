"""TP3 Teil 1: Kandidatenraum und seine Grenzen.

Ein *Kandidat* ist die Form aus Task 6 (siehe ``ruecktest.simuliere``):

    {
      "gates": {"mindest_score", "max_volatilitaet_pa", "mindest_chance_risiko",
                "stop_min", "stop_max", "abklingzeit_tage",
                "max_offene_positionen", "max_gesamt_usd", "max_pro_trade_usd"},
      "gewichte": {"chance": {...5...}, "risiko": {...4...}},
      "watchlist": [...],
      "sizing": "flach" | "score-linear" | "vola-invers",
    }

Dieses Modul liefert drei Bausteine fuer die Suche in Task 9:

* ``basis_kandidat`` - baut den Start-Kandidaten aus ``wachen.json`` und den
  beiden Gewichtskonstanten aus ``bewertung``.
* ``nachbarn`` - erzeugt deterministisch die bounded Nachbarschaft: je Gate
  ein Schritt auf und ab (an ``grenzen`` geklemmt), je Gewicht +-0,05 mit
  Renormierung der Gruppe, die beiden anderen ``sizing``-Werte und je einen
  watchlist-Drop.
* ``im_rahmen`` - prueft, ob ein Kandidat noch vollstaendig innerhalb
  ``grenzen`` und der Deckel des Basis-Kandidaten liegt.

Die *Deckel* (``max_pro_trade_usd``, ``max_gesamt_usd``,
``max_offene_positionen``) sowie die harten Sicherheitsschalter stehen auf der
``DENYLIST`` und werden nie variiert - sie sind im Kandidat nur zum Rechnen.
"""

import copy

# Schluessel, die ein Vorschlag nie anfassen darf. Deckel plus die vier
# Sicherheitsbedingungen aus Wissen/Schutzregeln.md. Task 9 filtert damit den
# Suchraum, unabhaengig davon, was in spuren.json als aenderbar steht.
DENYLIST = frozenset({
    "handel_erlaubt", "freigabe", "drawdown_halbierung_prozent",
    "kill_switch_gesamt_usd", "herzschlag_max_minuten", "journal_zweitziel",
    "max_pro_trade_usd", "max_gesamt_usd", "max_offene_positionen",
})

# Schrittweiten je durchsuchbarem Gate. Ein Nachbar bewegt genau ein Gate um
# genau einen Schritt.
GATE_SCHRITT = {
    "mindest_score": 2.5,
    "max_volatilitaet_pa": 0.1,
    "mindest_chance_risiko": 0.1,
    "stop_min": 1.0,
    "stop_max": 1.0,
    "abklingzeit_tage": 1,
}

# Grenzen fuer ein einzelnes Gewicht, bevor die Gruppe renormiert wird.
_GEWICHT_SCHRITT = 0.05
_GEWICHT_MIN = 0.0
_GEWICHT_MAX = 0.5

_SIZING_WERTE = ("flach", "score-linear", "vola-invers")

# Mindestlaenge der watchlist nach einem Drop.
_WATCHLIST_MIN = 3


def basis_kandidat(wachen, chance_g, risiko_g):
    """Start-Kandidat aus ``wachen.json`` plus den Gewichtskonstanten.

    Die Stop-Grenzen heissen in ``wachen.json`` ``pflicht_stop_prozent_min`` /
    ``pflicht_stop_prozent_max``; im Kandidat und in ``grenzen`` heissen sie
    ``stop_min`` / ``stop_max`` (dieselbe Umbenennung nimmt der Orchestrator in
    Task 9 aus ``spuren.json`` vor). Die uebrigen Gates und die Deckel werden
    unveraendert uebernommen.
    """
    gates = {
        "mindest_score": wachen["mindest_score"],
        "max_volatilitaet_pa": wachen["max_volatilitaet_pa"],
        "mindest_chance_risiko": wachen["mindest_chance_risiko"],
        "stop_min": wachen["pflicht_stop_prozent_min"],
        "stop_max": wachen["pflicht_stop_prozent_max"],
        "abklingzeit_tage": wachen["abklingzeit_tage"],
        "max_offene_positionen": wachen["max_offene_positionen"],
        "max_gesamt_usd": wachen["max_gesamt_usd"],
        "max_pro_trade_usd": wachen["max_pro_trade_usd"],
    }
    return {
        "gates": gates,
        "gewichte": {
            "chance": copy.deepcopy(dict(chance_g)),
            "risiko": copy.deepcopy(dict(risiko_g)),
        },
        "watchlist": list(wachen["watchlist"]),
        "sizing": "flach",
    }


def _durchsuchbare_gates(grenzen):
    """Gate-Schluessel, die in ``grenzen`` mit einem [min, max]-Paar stehen und
    eine bekannte Schrittweite haben. ``watchlist`` (Wert ``"liste"``) und
    alles auf der DENYLIST bleibt aussen vor."""
    raus = []
    for schluessel, bereich in grenzen.items():
        if schluessel in DENYLIST:
            continue
        if not isinstance(bereich, (list, tuple)) or len(bereich) != 2:
            continue
        if schluessel not in GATE_SCHRITT:
            continue
        raus.append(schluessel)
    return raus


def _klemme(wert, lo, hi):
    return max(lo, min(hi, wert))


def _renormiert(gruppe):
    """Gruppe (dict Name -> Gewicht) so skalieren, dass die Summe 1,0 ist."""
    summe = sum(gruppe.values())
    if summe <= 0:
        # Entartet - gleichverteilen statt durch 0 teilen.
        n = len(gruppe)
        return {name: 1.0 / n for name in gruppe}
    return {name: wert / summe for name, wert in gruppe.items()}


def nachbarn(kandidat, grenzen):
    """Deterministische bounded Nachbarschaft von ``kandidat``.

    * Je durchsuchbarem Gate ein Nachbar mit ``+Schritt`` und einer mit
      ``-Schritt``, an ``grenzen`` geklemmt. Aufgenommen nur, wenn der Wert
      sich tatsaechlich aendert und ``stop_min < stop_max`` erhalten bleibt.
    * Je Gewichtsgruppe und Gewicht ein Nachbar mit ``+0,05`` und einer mit
      ``-0,05`` (auf ``[0, 0.5]`` geklemmt), danach die ganze Gruppe auf
      Summe 1,0 renormiert. Die Gruppen bleiben immer vollstaendig.
    * ``sizing``: die beiden nicht aktuellen Werte.
    * ``watchlist``: je Instrument ein Nachbar ohne dieses Instrument, aber
      nur, wenn danach noch mindestens drei Instrumente bleiben.

    Deckel (``max_*``) werden nie variiert.
    """
    raus = []
    gates = kandidat["gates"]

    # --- Gates --------------------------------------------------------------
    for schluessel in _durchsuchbare_gates(grenzen):
        lo, hi = grenzen[schluessel]
        schritt = GATE_SCHRITT[schluessel]
        alt = gates[schluessel]
        for richtung in (schritt, -schritt):
            neu = _klemme(alt + richtung, lo, hi)
            if neu == alt:
                continue
            nb = copy.deepcopy(kandidat)
            nb["gates"][schluessel] = neu
            if nb["gates"]["stop_min"] >= nb["gates"]["stop_max"]:
                continue
            raus.append(nb)

    # --- Gewichte ---------------------------------------------------------
    # Ein Gewicht um +-0,05 verschieben, auf [0, 0.5] klemmen, dann die
    # Gruppe renormieren. Die Renormierung (Teilen durch ~1,05 bzw. ~0,95)
    # kann ein ohnehin hohes Gewicht knapp ueber 0,5 heben - solche Nachbarn
    # liegen nicht mehr im Rahmen und werden verworfen, damit jeder von
    # nachbarn() gelieferte Kandidat im_rahmen() erfuellt.
    for gruppe in ("chance", "risiko"):
        namen = list(kandidat["gewichte"][gruppe])
        for name in namen:
            for richtung in (_GEWICHT_SCHRITT, -_GEWICHT_SCHRITT):
                roh = dict(kandidat["gewichte"][gruppe])
                roh[name] = _klemme(roh[name] + richtung,
                                    _GEWICHT_MIN, _GEWICHT_MAX)
                neu = _renormiert(roh)
                if max(neu.values()) > _GEWICHT_MAX + 1e-9:
                    continue
                nb = copy.deepcopy(kandidat)
                nb["gewichte"][gruppe] = neu
                raus.append(nb)

    # --- sizing -----------------------------------------------------------
    for wert in _SIZING_WERTE:
        if wert == kandidat["sizing"]:
            continue
        nb = copy.deepcopy(kandidat)
        nb["sizing"] = wert
        raus.append(nb)

    # --- watchlist (nur Drops) ------------------------------------------
    liste = kandidat["watchlist"]
    if len(liste) - 1 >= _WATCHLIST_MIN:
        for inst in liste:
            nb = copy.deepcopy(kandidat)
            nb["watchlist"] = [x for x in liste if x != inst]
            raus.append(nb)

    return raus


def im_rahmen(kandidat, grenzen, basis):
    """True, wenn ``kandidat`` vollstaendig im erlaubten Raum liegt.

    Geprueft wird: jedes durchsuchbare Gate innerhalb ``grenzen``; jede
    Gewichtsgruppe summiert auf 1,0 (Toleranz 1e-9) und jedes einzelne
    Gewicht liegt in ``[0, 0.5]``; ``watchlist`` ist Teilmenge von
    ``basis["watchlist"]``; die Deckel ``max_pro_trade_usd``,
    ``max_gesamt_usd`` und ``max_offene_positionen`` sind unveraendert.
    """
    gates = kandidat["gates"]

    for schluessel in _durchsuchbare_gates(grenzen):
        lo, hi = grenzen[schluessel]
        wert = gates[schluessel]
        if wert < lo - 1e-9 or wert > hi + 1e-9:
            return False

    for gruppe in ("chance", "risiko"):
        werte = list(kandidat["gewichte"][gruppe].values())
        if abs(sum(werte) - 1.0) > 1e-9:
            return False
        for w in werte:
            if w < -1e-9 or w > 0.5 + 1e-9:
                return False

    if not set(kandidat["watchlist"]).issubset(set(basis["watchlist"])):
        return False

    for feld in ("max_pro_trade_usd", "max_gesamt_usd", "max_offene_positionen"):
        if gates[feld] != basis["gates"][feld]:
            return False

    return True
