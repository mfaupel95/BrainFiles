"""KrakenModell: das Kostenmodell-Plugin (siehe ruecktest.SPOT_MODELL) fuer
Spur 3 (Kraken, Mehrwaehrung).

Zwei Abweichungen vom Spot-Default:

* gebuehr_pct liest gebuehr_taker LIVE aus dem uebergebenen wachen-Dict -
  die Kraken-Gebuehr hat sich seit 03.09.2026 mehrfach geaendert (siehe
  Spec-Risiken), ein zweiter hartcodierter Wert wie kosten.GEBUEHR_PCT waere
  dieselbe Falle, die Spur 1 schon einmal brauchte test_kosten_gleich.py zu
  vermeiden.
* in_basiswaehrung rechnet USDC-/EURC-Betraege am Tagesschlusskurs nach EUR.
  Ein fehlender FX-Tag ist ein Fehler (FXLuecke), kein 1,0-Naeherungswert -
  dieselbe Haltung wie ausrichten() gegenueber Kerzenluecken.

pruefe_ausstieg/laufende_kosten bleiben Spot-Verhalten (Kraken hat keine
Margin/Funding) - fuer Spur 2 (XPERP) wird eine eigene erzeuge()-Variante
mit abweichenden Hooks entstehen, eigene Spec.
"""

import ruecktest

_USDC_PRAEFIX_SUFFIX = "USDC"
_EURC_PRAEFIX_SUFFIX = "EURC"


class FXLuecke(Exception):
    """Kein Umrechnungskurs fuer diesen Tag - nicht mit 1,0 auffuellen."""


def _kurs_je_tag(fx_kerzen):
    return {k[0] // 86400000: k[4] for k in fx_kerzen}


def erzeuge(wachen, fx_kerzen_eur_usdc, fx_kerzen_eur_eurc):
    """``modell``-Dict fuer Spur 3. ``wachen`` ist das geladene
    kraken/wachen.json-Dict (dieselbe Referenz, nicht kopiert - ein spaeteres
    Neuladen von wachen aktualisiert die Gebuehr automatisch). Die beiden
    FX-Kerzenlisten sind Form wie kraken_kerzen.hole() (EUR/USDC bzw.
    EUR/EURC Tagesschlusskurse)."""
    eur_je_usdc = _kurs_je_tag(fx_kerzen_eur_usdc)
    eur_je_eurc = _kurs_je_tag(fx_kerzen_eur_eurc)

    def gebuehr_pct(inst, tag):
        return wachen["gebuehr_taker"]

    def in_basiswaehrung(betrag, inst, tag):
        if inst.endswith(_USDC_PRAEFIX_SUFFIX):
            kurs = eur_je_usdc.get(tag)
        elif inst.endswith(_EURC_PRAEFIX_SUFFIX):
            kurs = eur_je_eurc.get(tag)
        else:
            return betrag  # EUR-Paar - keine Umrechnung.
        if kurs is None:
            raise FXLuecke(
                "kein EUR-Umrechnungskurs fuer %s an Tag %d" % (inst, tag))
        # kurs ist Fremdwaehrung pro EUR (z.B. 1.08 USD je EUR) - der Betrag
        # steht in Fremdwaehrung, also wird durch den Kurs geteilt.
        return betrag / kurs

    return {
        "gebuehr_pct": gebuehr_pct,
        "pruefe_ausstieg": ruecktest.SPOT_MODELL["pruefe_ausstieg"],
        "laufende_kosten": ruecktest.SPOT_MODELL["laufende_kosten"],
        "in_basiswaehrung": in_basiswaehrung,
    }
