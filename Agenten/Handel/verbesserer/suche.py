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
    # Spur 3 (Kraken) nennt dieselben Deckel mit EUR-Endung (teils
    # historisch falsch "_usd", siehe kraken/wachen.json-Kommentar) - zweite
    # Verteidigungslinie zusaetzlich zur Whitelist in spuren.json.
    "max_pro_trade_eur", "max_gesamt_eur", "drawdown_halbierung_usd",
    "kill_switch_gesamt_eur",
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


_DECKEL_FELDER_DEFAULT = {
    "max_pro_trade_usd": "max_pro_trade_usd",
    "max_gesamt_usd": "max_gesamt_usd",
}


def basis_kandidat(wachen, chance_g, risiko_g, deckel_felder=None):
    """Start-Kandidat aus ``wachen.json`` plus den Gewichtskonstanten.

    Die Stop-Grenzen heissen in ``wachen.json`` ``pflicht_stop_prozent_min`` /
    ``pflicht_stop_prozent_max``; im Kandidat und in ``grenzen`` heissen sie
    ``stop_min`` / ``stop_max`` (dieselbe Umbenennung nimmt der Orchestrator
    aus ``spuren.json`` vor). Die uebrigen Gates werden unveraendert
    uebernommen.

    ``deckel_felder`` mappt die candidate-internen Deckel-Schluessel
    (``max_pro_trade_usd``/``max_gesamt_usd`` - eine Namenskonvention fuer
    "Geld-Deckel", nicht woertlich US-Dollar) auf den tatsaechlichen
    ``wachen.json``-Feldnamen der Spur. Default liest dieselben Namen
    (Spur 1); Spur 3 (Kraken, EUR) uebergibt z. B. ``{"max_pro_trade_usd":
    "max_pro_trade_eur", "max_gesamt_usd": "max_gesamt_eur"}``.
    """
    deckel_felder = deckel_felder or _DECKEL_FELDER_DEFAULT
    gates = {
        "mindest_score": wachen["mindest_score"],
        "max_volatilitaet_pa": wachen["max_volatilitaet_pa"],
        "mindest_chance_risiko": wachen["mindest_chance_risiko"],
        "stop_min": wachen["pflicht_stop_prozent_min"],
        "stop_max": wachen["pflicht_stop_prozent_max"],
        "abklingzeit_tage": wachen["abklingzeit_tage"],
        "max_offene_positionen": wachen["max_offene_positionen"],
        "max_gesamt_usd": wachen[deckel_felder["max_gesamt_usd"]],
        "max_pro_trade_usd": wachen[deckel_felder["max_pro_trade_usd"]],
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


def nachbarn(kandidat, grenzen, gewichte_durchsuchbar=True,
             watchlist_aenderbar=True):
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
            # Gleitkomma-Rauschen aus der Schrittaddition (1.2 + 0.1 ->
            # 1.3000000000000003) gaebe sonst ein vorschlag._als_json per repr
            # so in die handgepflegte wachen.json weiter. Auf vier Stellen
            # runden - feiner ist keine Schrittweite hier.
            neu = round(_klemme(alt + richtung, lo, hi), 4)
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
    #
    # gewichte_durchsuchbar=False (Spur 3): bewertung.py ist mit Spur 1
    # geteilt, ein Kraken-Befund darf dessen Live-Scoring nicht mitaendern.
    for gruppe in ("chance", "risiko") if gewichte_durchsuchbar else ():
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
    # watchlist_aenderbar=False: das Live-Universum ist der ganze Markt
    # (wachen.json universum.modus "alle"), die Watchlist dort nur Rueckfall.
    # Ein Drop waere ein Vorschlag, den der Live-Scanner nie liest.
    liste = kandidat["watchlist"]
    if watchlist_aenderbar and len(liste) - 1 >= _WATCHLIST_MIN:
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


# --- Koordinatenabstieg und Overfitting-Sperre (TP3 Teil 2) -------------

# Kandidat-Gate -> Name in wachen.json. Nur diese Felder wandern als Diff in
# ``aenderungen``; Deckel und Gewichte stehen nicht in wachen.json.
_GATE_NACH_WACHEN = {
    "mindest_score": "mindest_score",
    "max_volatilitaet_pa": "max_volatilitaet_pa",
    "mindest_chance_risiko": "mindest_chance_risiko",
    "stop_min": "pflicht_stop_prozent_min",
    "stop_max": "pflicht_stop_prozent_max",
    "abklingzeit_tage": "abklingzeit_tage",
}


def _je_runde(wf):
    """netto_gv_je_runde im Aggregat eines walk_forward-Ergebnisses."""
    return wf["gesamt"]["netto_gv_je_runde"]


def besser(kandidat_wf, basis_wf):
    """(schlaegt_aggregat, anzahl_fenster_besser).

    ``schlaegt_aggregat``: Kandidat hat im Aggregat ein hoeheres
    ``netto_gv_je_runde`` als die Basis. ``anzahl_fenster_besser``: Zahl der
    Einzelfenster (paarweise nach Index, bis ``min`` der Laengen), in denen der
    Kandidat strikt hoeher liegt.
    """
    schlaegt_aggregat = _je_runde(kandidat_wf) > _je_runde(basis_wf)

    k_fenster = kandidat_wf["fenster"]
    b_fenster = basis_wf["fenster"]
    anzahl = 0
    for i in range(min(len(k_fenster), len(b_fenster))):
        if (k_fenster[i]["kennzahlen"]["netto_gv_je_runde"]
                > b_fenster[i]["kennzahlen"]["netto_gv_je_runde"]):
            anzahl += 1
    return schlaegt_aggregat, anzahl


def _aenderungen(kandidat, basis):
    """Flacher Diff Kandidat gegen Basis, Schluessel in wachen.json-Namen.

    Nur Gates aus ``_GATE_NACH_WACHEN`` und die watchlist. Gewichte bleiben
    aussen vor - sie landen spaeter in einem Patch fuer bewertung.py, nicht in
    wachen.json.
    """
    aus = {}
    for gate, wachen_name in _GATE_NACH_WACHEN.items():
        if kandidat["gates"][gate] != basis["gates"][gate]:
            aus[wachen_name] = kandidat["gates"][gate]
    if kandidat["watchlist"] != basis["watchlist"]:
        aus["watchlist"] = list(kandidat["watchlist"])
    return aus


def suche(basis, kerzen_je_inst, konfig, grenzen, bewerte=None, holdout_fn=None,
          gewichte_durchsuchbar=None, watchlist_aenderbar=True):
    """Koordinatenabstieg von ``basis`` aus mit Overfitting-Sperre.

    Von ``basis`` aus wird wiederholt die Nachbarschaft (``nachbarn``)
    ausgewertet und der Nachbar mit dem hoechsten Aggregat-``netto_gv_je_runde``
    genommen; schlaegt er das aktuelle Beste, wird er uebernommen und es geht
    weiter, sonst Abbruch. ``konfig["such_budget"]`` deckelt die Zahl der
    ``walk_forward``-Aufrufe (die Basis-Auswertung zaehlt mit); ist das Budget
    erreicht, werden keine neuen Auswertungen mehr angeboten.

    Nach dem Abstieg prueft die Overfitting-Sperre gegen ``basis_wf``: der
    Kandidat gilt nur, wenn er das Aggregat schlaegt UND in einer **Mehrheit**
    der Einzelfenster besser ist (mehr als ``fenster_anzahl // 2`` und
    mindestens ``overfit_min_fenster`` als Boden) UND das Aggregat
    ``>= overfit_min_runden`` OOS-Runden hat. Sonst ``kandidat=None`` mit
    ``grund``.

    Mit ``holdout_tage > 0`` kommt eine weitere Sperre hinzu: die letzten
    ``holdout_tage`` Tage werden vor Suche und Walk-Forward abgeschnitten, und
    der Sieger muss die Basis auf diesem nie gesehenen Block schlagen
    (``netto_gv_je_runde`` hoeher, ``n >= holdout_min_runden``). Sonst
    ``kandidat=None``, ``grund="Holdout nicht bestanden"`` und ``fast_kandidat``
    gesetzt. Reicht ``L - holdout_tage`` nicht fuer ``oos_training_tage`` plus
    ``overfit_min_fenster`` Testfenster: ``grund="zu wenig Historie fuer
    Holdout"``.

    Rueckgabe: ``{"kandidat", "basis_wf", "kandidat_wf", "auswertungen",
    "grund", "aenderungen", "holdout_basis", "holdout_kandidat",
    "fast_kandidat"}``. ``bewerte`` ersetzt ``ruecktest.walk_forward`` und
    ``holdout_fn`` ersetzt ``ruecktest.holdout`` (fuer Tests); ohne werden sie
    traege importiert.
    """
    if gewichte_durchsuchbar is None:
        gewichte_durchsuchbar = konfig.get("gewichte_durchsuchbar", True)

    if bewerte is None:
        import ruecktest
        bewerte = ruecktest.walk_forward

    holdout_tage = konfig.get("holdout_tage", 0)
    kerzen_holdout = kerzen_je_inst
    zu_wenig_historie = False
    if holdout_tage > 0:
        import ruecktest
        if holdout_fn is None:
            holdout_fn = ruecktest.holdout
        kerzen_je_inst, _hinw = ruecktest.ausrichten(kerzen_je_inst)
        kerzen_holdout = kerzen_je_inst
        laenge = min((len(k) for k in kerzen_je_inst.values()), default=0)
        noetig = (konfig["oos_training_tage"]
                  + konfig["overfit_min_fenster"] * konfig["oos_test_tage"])
        if laenge - holdout_tage < noetig:
            zu_wenig_historie = True
        else:
            kerzen_je_inst = {inst: k[:laenge - holdout_tage]
                              for inst, k in kerzen_je_inst.items()}

    if zu_wenig_historie:
        return {
            "kandidat": None, "basis_wf": None, "kandidat_wf": None,
            "auswertungen": 0, "grund": "zu wenig Historie fuer Holdout",
            "aenderungen": {}, "holdout_basis": None, "holdout_kandidat": None,
            "fast_kandidat": None,
        }

    budget = konfig["such_budget"]

    basis_wf = bewerte(kerzen_je_inst, basis, konfig)
    auswertungen = 1
    bestes = basis
    bestes_wf = basis_wf

    while auswertungen < budget:
        bester_nb = None
        bester_nb_wf = None
        for kand in nachbarn(bestes, grenzen, gewichte_durchsuchbar,
                              watchlist_aenderbar):
            if auswertungen >= budget:
                break
            kand_wf = bewerte(kerzen_je_inst, kand, konfig)
            auswertungen += 1
            if bester_nb_wf is None or _je_runde(kand_wf) > _je_runde(bester_nb_wf):
                bester_nb = kand
                bester_nb_wf = kand_wf
        if bester_nb_wf is None:
            break
        if _je_runde(bester_nb_wf) > _je_runde(bestes_wf):
            bestes = bester_nb
            bestes_wf = bester_nb_wf
        else:
            break

    agg, k_fenster = besser(bestes_wf, basis_wf)
    n_runden = bestes_wf["gesamt"]["n"]
    fenster_anz = bestes_wf.get("fenster_anzahl", len(bestes_wf["fenster"]))
    mehrheit = fenster_anz // 2

    if bestes is basis:
        kandidat = None
        grund = "kein besserer Kandidat gefunden"
    elif not agg:
        kandidat = None
        grund = "Aggregat nicht besser"
    elif not (k_fenster > mehrheit
              and k_fenster >= konfig["overfit_min_fenster"]):
        kandidat = None
        grund = (f"nur {k_fenster} von {fenster_anz} Fenstern besser "
                 f"(Mehrheit noetig: > {mehrheit}, mindestens "
                 f"{konfig['overfit_min_fenster']})")
    elif n_runden < konfig["overfit_min_runden"]:
        kandidat = None
        grund = (f"nur {n_runden} OOS-Runden "
                 f"(>= {konfig['overfit_min_runden']} noetig)")
    else:
        kandidat = bestes
        grund = (f"Vorschlag: schlaegt Basis im Aggregat und in {k_fenster} "
                 f"Fenstern ({n_runden} OOS-Runden)")

    # Zusaetzliche Sperre: der Sieger muss einen Block bestehen, den die Suche
    # nie gesehen hat. Kandidat und Basis auf demselben Holdout.
    holdout_basis = None
    holdout_kandidat = None
    fast_kandidat = None
    if kandidat is not None and holdout_tage > 0:
        holdout_basis = holdout_fn(kerzen_holdout, basis, holdout_tage)
        holdout_kandidat = holdout_fn(kerzen_holdout, kandidat, holdout_tage)
        bestanden = (holdout_kandidat["netto_gv_je_runde"]
                     > holdout_basis["netto_gv_je_runde"]
                     and holdout_kandidat["n"]
                     >= konfig.get("holdout_min_runden", 0))
        if not bestanden:
            fast_kandidat = kandidat
            kandidat = None
            grund = "Holdout nicht bestanden"

    return {
        "kandidat": kandidat,
        "basis_wf": basis_wf,
        "kandidat_wf": bestes_wf if kandidat is not None else None,
        "auswertungen": auswertungen,
        "grund": grund,
        "aenderungen": _aenderungen(kandidat, basis) if kandidat is not None else {},
        "holdout_basis": holdout_basis,
        "holdout_kandidat": holdout_kandidat,
        "fast_kandidat": fast_kandidat,
    }
