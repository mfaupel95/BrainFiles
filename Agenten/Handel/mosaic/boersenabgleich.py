"""Buch gegen BOERSE: hat jede Live-Position ihren Notausstieg noch? (T-207)

Warum es das gibt (Befund 30.09.2026)
-------------------------------------
Die drei Kraken-Stops der Spur (BTC/ETH/SOL, rund 258 EUR) trugen an der
Boerse den Status ``canceled``, waehrend ``mosaic/zustand.json`` weiter
``boersen_stop_fehlt: false`` meldete. Gefunden wurde das nur ueber
``kraken/spot_stops.py`` - **mosaic prueft seine Boersen-Stops nicht nach**.
Ohne Stop ist eine offene Live-Position ungeschuetzt, und das Buch behauptet
das Gegenteil. Gleiche Klasse wie T-118 (xperp, 26.09.2026) und T-208
(kraken-Buch); die Vorlage ist ``scanner/boersenstops.py`` (28.09.2026).

Die REGELN sind von dort uebernommen, nicht der Code - und um die zweite
Boerse erweitert:

  1. Ist der Bestand noch da? Wenn nein: Stop gefeuert oder Handverkauf ->
     Position mit dem ECHTEN Ausstiegspreis ausbuchen.
  2. Ist der Notausstieg noch wirksam? Wenn nein und Bestand da -> neu setzen,
     und zwar ueber den TATSCHLICH gehaltenen Bestand.
  3. Kennt das Buch eine Stop-Kennung, die zu keiner Live-Position mehr
     gehoert, und steht sie an der Boerse noch offen -> Waisenstop, stornieren.
  4. Steht an der Boerse ein Stop, den das Buch NICHT kennt -> nur MELDEN,
     nie anfassen: das sind Max' von Hand gesetzte Stops (XLM, SUI, FIL,
     ATOM am 30.09.2026). Ein Storno waere hier ein Eingriff in fremde
     Absicherung.

Zwei Eigenheiten dieser Spur, die den Abgleich bestimmen
--------------------------------------------------------
  - mosaic fuehrt PAPIER und LIVE im SELBEN Buch. Angefasst werden nur
    Positionen mit ``modus == "live"`` - ein Papierlauf darf eine echte
    Position nicht ausbuchen (genau das ist am 23.09.2026 passiert).
  - Eine Position traegt ihre Boerse im Feld ``boerse`` (seit 23.09.2026);
    der Abgleich laeuft deshalb JE POSITION ueber deren Boerse, nicht ueber
    die gerade gebundene.

Ein Feld im Buch (``boersen_stop_fehlt``) wurde bisher nur beim KAUF gesetzt
und nie wieder geprueft - eine Behauptung, die altert.

Aufruf (aus ``Agenten/Handel/mosaic``):

    python boersenabgleich.py               # Vorschau, schreibt und ordert nichts
    python boersenabgleich.py --anwenden    # fehlende Stops setzen, Weggelaufenes buchen

Im Betrieb ruft ``handeln.py`` ``pruefe(z, anwenden=True)`` am Anfang jedes
Live-Zyklus (nach dem Buchabgleich, vor den Ausstiegen). Ist die Boerse nicht
lesbar, bleibt alles unangetastet: ein Netzfehler darf weder eine Position
loeschen noch einen Stop doppelt setzen.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
ZUSTAND = os.path.join(HIER, "zustand.json")
WACHEN = os.path.join(HIER, "wachen.json")

# Nicht in einen laufenden Zyklus schreiben (Muster scanner/boersenstops.py).
MIN_ALTER_S = 300
# Ein Bestand unter dieser Quote der Buchmenge gilt als "weg". Grosszuegig,
# weil Kraken die Order auf lot_decimals rundet und ein Haar stehen laesst.
WEG_QUOTE = 0.02
# Kraken-Ordertypen, die einen Notausstieg darstellen.
STOP_ARTEN = ("stop-loss", "stop-loss-limit")


def _lade(name, pfad):
    """Ein Hausmodul ueber den PFAD laden (nicht ueber sys.path)."""
    schluessel = "%s@%s" % (name, os.path.abspath(pfad))
    if schluessel in sys.modules:
        return sys.modules[schluessel]
    spec = importlib.util.spec_from_file_location(schluessel, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[schluessel] = modul
    spec.loader.exec_module(modul)
    return modul


def _jetzt():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _haltetage(p):
    try:
        d0 = datetime.strptime(p.get("eroeffnet_zeit") or p.get("eroeffnet")
                               or _heute(), "%Y-%m-%d")
    except ValueError:
        return ""
    return (datetime.now(timezone.utc).date() - d0.date()).days


def _ansage(text):
    """Diagnosezeile - der Dauerlauf liest die Ausgabe der Spur."""
    print("  " + text)


def _befund(bilanz, inst, boerse, lage, text=""):
    """Was der Abgleich zu EINER Position gesehen hat.

    Nicht fuer die Bilanz, sondern fuer den, der nachfragt: eine Wache muss die
    betroffene Position nennen koennen, ohne die Regeln nachzubauen.
    """
    bilanz.setdefault("befunde", []).append(
        {"inst": inst, "boerse": boerse, "lage": lage, "text": text})


def _deckung_messen(bilanz, b, inst, name, p):
    """Die vierte Stufe an EINER Position messen und melden.

    Eigene Funktion, weil sie an ZWEI Stellen geprueft wird: einmal im
    gesunden Zweig (der gemerkte Stop ist wirksam - **und kann trotzdem zu
    klein sein**) und einmal im Zweig, der einen Stop nachsetzt. Ein Inline-
    Block an der ersten Stelle waere an der zweiten eine zweite Wahrheit.

    Schreibt `deckung_luecke` in die Position, damit Vorschau, Bericht und
    eine Wache die Zahl sehen koennen, ohne die Regel nachzubauen.

    **Setzt nichts.** `mosaic/stops_nachziehen.py` traegt Kennungen nach und
    stellt KEINE Order; ein Nachsetzen braucht einen Schutzpreis, den
    niemand genannt hat. Der Befund nennt die Rechnung, nicht einen
    Aufruf, der sie erledigen wuerde.
    """
    gedeckt, soll_menge, auftraege = deckung(b, inst, p)
    if gedeckt is None:
        _befund(bilanz, inst, name, "unklar_deckung", "Deckung nicht lesbar")
        bilanz["unklar"] += 1
        return False
    fehlende_menge = max(0.0, soll_menge - gedeckt - MENGE_TOLERANZ)
    if fehlende_menge > 0:
        bilanz["ungeschuetzt"] = bilanz.get("ungeschuetzt", 0) + 1
        _befund(bilanz, inst, name, "ungeschuetzt",
                "Buch %.8f, geschuetzt %.8f, fehlt %.8f (%d Auftrag/-e)"
                % (soll_menge, gedeckt, fehlende_menge, len(auftraege)))
        _ansage("UNGESCHUETZT: %s - Buch %.8f, an der Boerse %.8f ueber "
                "%d Stop(s), es fehlen %.8f"
                % (inst, soll_menge, gedeckt, len(auftraege),
                   fehlende_menge))
        _ansage("    Nachsetzen: das Werkzeug setzt keine Order. Der "
                "Preis ist eine Freigabe - erst schliessen, dann "
                "ueber ../scanner/.venv/Scripts/python.exe "
                "kraken_spot.py mit einem genannten Stoppreis.")
        p["deckung_luecke"] = round(fehlende_menge, 12)
        return False
    p.pop("deckung_luecke", None)
    return True


def _stop_id(p):
    """Die gemerkte Stop-Kennung einer Position (beide Schreibweisen)."""
    return (p.get("stop_algo_id") or p.get("stop_txid")
            or p.get("stop_ord_id") or None)


# Rundung, nicht Handgriff: eine Bestandsmenge, die um Lot-Schritte abweicht,
# ist dieselbe Position. Kraken rechnet in lot_decimals (SOL 8, BTC 8,
# ETH 8); OKX in sz. 1e-9 ist darunter und damit unauffaellig.
MENGE_TOLERANZ = 1e-9


def deckung(b, inst, p):
    """Wie viele Stueck der Position sind an der BOERSE geschuetzt?

    Die vierte Abgleichsstufe (T-362, hier nach xperp gebaut). Die dritte
    fragt nur, OB die **gemerkte** Kennung wirksam ist - und genau daran
    scheitert sie zweifach:

    1. **Existenz ist keine Menge.** Eine Position mit 0,48 SOL und einem
       Stop ueber 0,47 ist kein geschuetzter Bestand, sondern ein Rest; die
       Luecke laeuft bis zur Liquidation.
    2. **Der gemerkte Auftrag ist nicht der einzige.** An Kraken lagen am
       05.10.2026 fuenf Stops auf SOL (zusammen 9,539 gegen 0,481 im Buch),
       vier davon von fremden Spuren (Solf, LME). Der Abgleich darf sie nicht
       als Deckung zaehlen UND darf sie nicht anfassen.

    **Die Basis wird aus beiden Schreibweisen aufgeloest.** Kraken nennt das
    Paar in `AssetPairs` als `XXBTZEUR`, in `OpenOrders` als `XBTEUR` - ein
    Register-Lookup auf den Paarnamen liefert `base=None` und damit **null
    Treffer**, was sich wie "kein Stop" liest (gemessen: BTC und ETH zeigten
    0 Stops, obwohl je eins an der Boerse lag). Die Aufloesung macht
    `spot_stops.muenze_aus_paar()`, die beide Formen kennt; eine zweite
    Wahrheit hier waere die dritte Fassung.

    Rueckgabe: (geschuetzt, soll, auftraege). `geschuetzt=None` heisst
    "nicht lesbar" und darf NICHT als "kein Stop" gelesen werden.
    """
    soll = _buch_menge(p)
    if soll <= 0:
        return None, 0.0, []
    try:
        basis = b.basis(inst)
        auftraege = b.schutz_auftraege(inst, basis)
    except Exception as e:                                     # noqa: BLE001
        _ansage("Deckung %s nicht abrufbar (%s) - unangetastet" % (inst, e))
        return None, soll, []
    gedeckt = sum(a["menge"] for a in auftraege)
    return gedeckt, soll, auftraege


def _buch_menge(p):
    """Menge der Position im Buch - gemeldete Menge, sonst aus nominal/einstieg."""
    m = float(p.get("menge") or 0)
    if m > 0:
        return m
    try:
        return float(p.get("nominal") or 0) / float(p.get("einstieg") or 0)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


# --- Kraken -----------------------------------------------------------------

class KrakenBoerse:
    """Der Kraken-Spot-Zugang fuer den Abgleich.

    Die Regeln der Namensgebung (XXBT -> BTC, '.S' fuer Gestaktes) liegen NICHT
    hier, sondern in ``kraken/spot_stops.py`` (norm) - eine zweite Fassung
    waere die zweite Wahrheit.
    """

    name = "kraken"

    def __init__(self, quote=None):
        self._spot = _lade("mosaic_kraken_spot",
                           os.path.join(HIER, "kraken_spot.py"))
        if quote:
            self._spot.setze_quote(quote)
        self._kraken = self._spot.kraken
        # EINE Instanz des Hausmoduls, zwei Namen daraus: `norm` fuer die
        # Basis und `muenze_aus_paar` fuer die Paarauflosung. Zweimal laden
        # waere eine zweite Modulinstanz und damit eine zweite Wahrheit ueber
        # dieselbe Regel.
        _stops = _lade("kraken_spot_stops",
                       os.path.join(HANDEL, "kraken", "spot_stops.py"))
        self._norm = _stops.norm
        self._muenze_aus_paar = _stops.muenze_aus_paar
        self._paare_roh = None
        self._konten = None
        self._details = {}

    # -- lesende Hilfen ------------------------------------------------------

    def _paare(self):
        if self._paare_roh is None:
            self._paare_roh = self._kraken._roh_oeffentlich("AssetPairs") or {}
        return self._paare_roh

    def _konten_alle(self):
        if self._konten is None:
            self._konten = self._kraken.kontostaende() or {}
        return self._konten

    def _paar(self, inst):
        return self._spot.paar_fuer(inst)

    def basis(self, inst):
        """Kraken-Code der Basiswaehrung ('XXBT', 'XETH', 'SOL')."""
        paar = self._paar(inst)
        info = self._paare().get(paar) or {}
        if not info.get("base"):
            raise ValueError("Kraken kennt das Paar %s nicht (fuer %s)"
                             % (paar, inst))
        return info["base"]

    def bestand(self, inst):
        """Freier Bestand der Basiswaehrung; fehlt der Posten, ist er 0."""
        soll = self._norm(self.basis(inst))
        for k, v in self._konten_alle().items():
            if self._norm(k) == soll:
                return float(v or 0)
        return 0.0

    def stop_details(self, txid):
        if txid not in self._details:
            self._details[txid] = self._kraken.order_details(txid) or {}
        return self._details[txid]

    def stop_wirksam(self, txid):
        """True/False, None = nicht lesbar (NICHT als 'fehlt' deuten)."""
        if not txid:
            return False
        d = self.stop_details(txid)
        if not d or not d.get("status"):
            return None
        if float(d.get("vol_exec") or 0) > 0:
            return False                       # ausgeloest oder teilgefuellt
        return str(d.get("status")).lower() == "open"

    def stop_gefuellt(self, txid):
        if not txid:
            return False
        return float(self.stop_details(txid).get("vol_exec") or 0) > 0

    def ausstieg(self, inst, txid):
        """Der ECHTE Ausstieg des Boersen-Stops: cost - fee, geteilt durch vol_exec.

        Kraken liefert ``cost`` (Gegenwert in der Quote-Waehrung) und ``fee``
        selbst - eine eigene Gebuehrenschaetzung waere ungenauer. Ohne Fuellung
        gibt es keinen Beleg und damit keine Buchung.
        """
        if not txid:
            return None
        d = self.stop_details(txid)
        menge = float(d.get("vol_exec") or 0)
        cost = float(d.get("cost") or 0)
        if menge <= 0 or cost <= 0:
            return None
        return {"menge": menge, "preis": cost / menge,
                "erloes": cost - float(d.get("fee") or 0),
                "art": (d.get("descr") or {}).get("ordertype"),
                "misc": d.get("misc")}

    def fremde_stops(self, bekannt):
        """Offene Stops, die das Buch NICHT kennt - nur zur Anzeige."""
        aus = []
        for txid, o in (self._kraken.offene_orders() or {}).items():
            if txid in bekannt:
                continue
            if "stop" not in (o.get("art") or "").lower():
                continue
            aus.append((txid, o))
        return aus

    def schutz_auftraege(self, inst, basis):
        """Offene Stop-Auftraege einer Basiswaehrung, mit ihrer MENGE.

        Neu (T-362): die Deckung wird ueber die **Menge** gemessen, und der
        Weg ist die offenen Orders des Kontos - nicht die gemerkte Kennung der
        Position. Zwei Gruende, beide am 05.10.2026 gemessen:

        * Ein Register-Lookup auf den Paarnamen findet nichts. `AssetPairs`
          nennt das Paar `XXBTZEUR`, `OpenOrders` nennt es `XBTEUR`; der
          Lookup liefert `base=None` und damit null Treffer. Die Aufloesung
          macht `spot_stops.muenze_aus_paar()`, das beide Formen kennt.
        * Ein gemerkter Auftrag ist nicht der einzige: fuenf Stops auf SOL,
          vier davon von fremden Spuren (Solf, LME). Sie decken diese Position
          mit, gehoeren ihr aber nicht - **anfassen tut der Abgleich keinen
          davon**, das ist Sache von `waisen_stops`.

        Als Schutz zaehlt nur, was wirklich schuetzt: `sell` (Gegenrichtung
        einer Long-Position) und `stop-loss`/`stop-loss-limit`.
        """
        if self._paare is None:
            self._paare = self._kraken._roh_oeffentlich("AssetPairs") or {}
        gesucht = self._norm(basis)
        aus = []
        for txid, o in (self._kraken.offene_orders() or {}).items():
            d = o or {}
            if "stop" not in str(d.get("art") or "").lower():
                continue
            if str(d.get("seite") or "").lower() != "sell":
                continue
            paar = d.get("paar")
            if self._muenze_aus_paar(paar, self._paare()) != gesucht:
                continue
            try:
                menge = float(d.get("menge") or 0)
            except (TypeError, ValueError):
                continue
            if menge <= MENGE_TOLERANZ:
                continue
            aus.append({"txid": txid, "menge": menge, "preis": d.get("preis"),
                        "paar": paar})
        return aus

    # -- schreibende Wege (nur im Live-Zyklus) -------------------------------

    def menge_gerundet(self, inst, menge):
        """Menge auf lot_decimals abrunden und gegen ordermin pruefen."""
        info = self._paare().get(self._paar(inst)) or {}
        stellen = info.get("lot_decimals")
        stellen = 8 if stellen is None else int(stellen)   # 0 ist gueltig!
        m = float(int(float(menge) * 10 ** stellen)) / 10 ** stellen
        if m <= 0 or m < float(info.get("ordermin") or 0):
            return None
        return m

    def stop_setzen(self, inst, menge, preis):
        """Notausstieg als Stop-Loss im Boersenbuch. Rueckgabe: txid oder None."""
        return self._spot.algo_stop_setzen(inst, menge, "long", preis)

    def stop_stornieren(self, inst, txid):
        return self._spot.algo_stornieren(inst, txid)


# --- OKX --------------------------------------------------------------------

class OkxBoerse:
    """Der OKX-Spot-Zugang - ueber ``scanner/okx.py`` (dort laeuft derselbe
    Abgleich seit 28.09.2026, die Funktionen sind also erprobt).

    ``fremde_stops`` gibt es hier nicht: OKX fuehrt Algo-Orders in einer
    eigenen Liste, deren Leseweg fuer den Abgleich nicht noetig ist. Die
    Anzeige unterbleibt, es wird nichts angefasst.
    """

    name = "okx"

    def __init__(self, quote=None):
        self._okx = _lade("scanner_okx", os.path.join(HANDEL, "scanner", "okx.py"))
        self._details = {}
        self._algo = None

    def basis(self, inst):
        return str(inst).split("-")[0]

    def bestand(self, inst):
        eq, _frei = self._okx.bestand(inst)
        return float(eq or 0)

    def stop_details(self, txid):
        if txid not in self._details:
            self._details[txid] = self._okx.stop_details(txid) or {}
        return self._details[txid]

    def stop_wirksam(self, txid):
        if not txid:
            return False
        d = self.stop_details(txid)
        if not d or not d.get("state"):
            return None
        if float(d.get("accFillSz") or 0) > 0:
            return False
        return str(d.get("state")).lower() in ("effective", "live")

    def stop_gefuellt(self, txid):
        if not txid:
            return False
        return float(self.stop_details(txid).get("accFillSz") or 0) > 0

    def ausstieg(self, inst, txid):
        f = self._okx.letzte_fuellung(inst, "sell")
        if not f:
            return None
        menge = float(f.get("accFillSz") or 0)
        kurs = float(f.get("avgPx") or 0)
        if menge <= 0 or kurs <= 0:
            return None
        return {"menge": menge, "preis": kurs,
                "erloes": menge * kurs * (1 - 0.0005), "art": "market",
                "misc": f.get("ordId")}

    def fremde_stops(self, bekannt):
        return None

    def schutz_auftraege(self, inst, basis):
        """Offene Schutz-Auftraege eines Instruments, mit ihrer MENGE.

        Neu (T-362), gleiche Regel wie bei Kraken: gedeckt ist, was die MENGE
        abdeckt. OKX fuehrt Stops je nach Anlageweg als `conditional` ODER
        `oco` - eine Abfrage nur auf `conditional` liest sich bei einer
        `oco`-Position wie "kein Stop" und wuerde einen zweiten Stop stellen.

        **Alle Algotypen fragen.** Der Weg ist derselbe signierte GET wie in
        `live_wache.boersenstops()`: `/api/v5/trade/orders-algo-pending` mit
        `ordType=conditional`.
        """
        if self._algo is None:
            self._algo = self._okx._roh(
                "/api/v5/trade/orders-algo-pending?ordType=conditional",
                "GET", signiert=True) or []
        aus = []
        for a in self._algo:
            if a.get("instId") != inst:
                continue
            if str(a.get("side", "")).lower() != "sell":
                continue
            if str(a.get("reduceOnly", "")).lower() not in ("true", "1"):
                continue
            # Als Schutz traegt ein Trailing kein slTriggerPx - es zaehlt
            # ueber tpTriggerPx (dieselbe Regel wie okxf.ist_schutz_stop).
            if not (a.get("slTriggerPx") or a.get("tpTriggerPx")):
                continue
            try:
                menge = float(a.get("sz") or 0)
            except (TypeError, ValueError):
                continue
            if menge <= MENGE_TOLERANZ:
                continue
            aus.append({"txid": a.get("algoId"), "menge": menge,
                        "preis": a.get("slTriggerPx") or a.get("tpTriggerPx"),
                        "paar": inst})
        return aus

    def menge_gerundet(self, inst, menge):
        m = self._okx.menge_gerundet(inst, menge)
        return m or None

    def stop_setzen(self, inst, menge, preis):
        return self._okx.stop_setzen(inst, menge, preis)

    def stop_stornieren(self, inst, txid):
        return self._okx.stop_stornieren(txid, inst)


BOERSEN = {"kraken": KrakenBoerse, "okx": OkxBoerse}


def lade_boersen(namen, quote=None):
    """{Name: Zugang} fuer die verlangten Boersen. Unbekannt -> None.

    Nur die Boersen, die im Buch wirklich vorkommen: jeder Zugang liest
    Guthaben und Paartabelle, also signierte Aufrufe. Eine unbekannte Boerse
    wird als None gefuehrt und je Position als 'unklar' gemeldet - ein
    Tippfehler darf nicht still das ganze Buch sperren.
    """
    aus = {}
    for n in namen:
        name = str(n or "").strip().lower()
        if name in aus:
            continue
        klasse = BOERSEN.get(name)
        aus[name] = klasse(quote=quote) if klasse else None
    return aus


# --- Abgleich ---------------------------------------------------------------

def pruefe(z, anwenden=False, journal=None, standard="kraken", laden=None,
           quote=None):
    """Eine Runde Buch <-> Boerse. Rueckgabe: Zahlen fuer den Bericht.

    ``anwenden=False`` (Vorschau) liest nur und sagt, was es taete.
    ``laden`` ist die Naht fuer Tests (kein Netz): eine Funktion
    ``namen -> {name: Zugang}``.
    """
    bilanz = {"geprueft": 0, "ok": 0, "nachgesetzt": 0, "fehlt_weiter": 0,
              "weg": 0, "ausgebucht": 0, "waisen": 0, "unklar": 0,
              "befunde": []}
    if laden is None:
        laden = lambda namen: lade_boersen(namen, quote=quote)   # noqa: E731

    positionen = z.get("positionen") or []
    live = [p for p in positionen if p.get("modus") == "live"]
    if not live:
        return bilanz                     # kein einziger Boersenabruf

    namen = []
    for p in live:
        n = str(p.get("boerse") or standard).strip().lower()
        if n not in namen:
            namen.append(n)
    try:
        boersen = laden(namen)
    except Exception as e:                                     # noqa: BLE001
        _ansage("Boersen nicht erreichbar (%s) - Buch unveraendert" % e)
        bilanz["geprueft"] = len(live)
        bilanz["unklar"] = len(live)
        return bilanz

    behalten = []
    weg_ids = []
    for p in positionen:
        if p.get("modus") != "live":
            behalten.append(p)      # Papier-Altlast: nicht Sache dieses Wegs
            continue
        bilanz["geprueft"] += 1
        inst = p.get("inst")
        name = str(p.get("boerse") or standard).strip().lower()
        b = boersen.get(name)
        if b is None:
            _ansage("%s: Boerse '%s' nicht unterstuetzt - unangetastet"
                    % (inst, name))
            _befund(bilanz, inst, name, "unklar_boerse",
                    "Boerse nicht unterstuetzt")
            bilanz["unklar"] += 1
            behalten.append(p)
            continue

        try:
            bestand = b.bestand(inst)
        except Exception as e:                                 # noqa: BLE001
            _ansage("Bestand %s nicht lesbar: %s - unangetastet" % (inst, e))
            _befund(bilanz, inst, name, "unklar_bestand", str(e))
            bilanz["unklar"] += 1
            behalten.append(p)
            continue

        sid = _stop_id(p)
        try:
            wirksam = b.stop_wirksam(sid)
            gefuellt = b.stop_gefuellt(sid)
        except Exception as e:                                 # noqa: BLE001
            _ansage("Stop %s nicht lesbar: %s - unangetastet" % (sid, e))
            _befund(bilanz, inst, name, "unklar_stop", str(e))
            bilanz["unklar"] += 1
            behalten.append(p)
            continue

        buch_menge = _buch_menge(p)
        schwelle = max(0.0, buch_menge * WEG_QUOTE)

        if bestand <= schwelle:
            grund = "boersen_stop" if gefuellt else "handverkauf_boerse"
            bilanz["weg"] += 1
            if not anwenden:
                _ansage("POSITION WEG an der Boerse: %s (Buch %.8f) - wuerde "
                        "als %s ausgebucht" % (inst, buch_menge, grund))
                _befund(bilanz, inst, name, "weg",
                        "Bestand %.8f, Buch %.8f" % (bestand, buch_menge))
                behalten.append(p)
                continue
            if sid and wirksam:
                try:
                    b.stop_stornieren(inst, sid)
                    _ansage("Waisenstop %s (%s) storniert" % (sid, inst))
                except Exception as e:                         # noqa: BLE001
                    _ansage("Waisenstop %s nicht stornierbar: %s" % (sid, e))
            a = None
            try:
                a = b.ausstieg(inst, sid)
            except Exception as e:                             # noqa: BLE001
                _ansage("Ausstiegspreis %s nicht lesbar: %s" % (inst, e))
            if not a:
                _ansage("WEG, aber kein Ausstiegspreis belegbar: %s - Buch "
                        "bleibt unveraendert (bitte von Hand pruefen)" % inst)
                _befund(bilanz, inst, name, "weg_ohne_beleg",
                        "kein Ausstiegspreis an der Boerse")
                bilanz["unklar"] += 1
                behalten.append(p)
                continue
            einsatz = float(p.get("nominal") or 0.0)
            gv = a["erloes"] - einsatz
            _ansage("AUSSTIEG (%s): %s %.8f Stueck @ %.6f  Erloes %.2f  "
                    "G/V %+.2f" % (grund, inst, a["menge"], a["preis"],
                                   a["erloes"], gv))
            if journal:
                journal(zeit=_jetzt(), modus="live", aktion="verkauf",
                        inst=inst, seite=p.get("seite", "long"),
                        preis="%.6f" % a["preis"],
                        einsatz_usd="%.2f" % a["erloes"],
                        stop="%.6f" % float(p.get("stop") or 0.0),
                        ziel="%.6f" % float(p.get("ziel") or 0.0),
                        stop_pct="%.2f" % float(p.get("stop_pct") or 0.0),
                        grund=grund)
            bilanz["ausgebucht"] += 1
            _befund(bilanz, inst, name, "ausgebucht",
                    "%s, Erloes %.2f" % (grund, a["erloes"]))
            if sid:
                weg_ids.append(sid)
            continue

        if wirksam is None:
            _befund(bilanz, inst, name, "unklar_stop", "Stop-Status unbekannt")
            bilanz["unklar"] += 1
            behalten.append(p)      # Zustand unbekannt: lieber nichts tun
            continue

        if wirksam:
            bilanz["ok"] += 1
            if p.get("boersen_stop_fehlt"):
                p["boersen_stop_fehlt"] = False
            _deckung_messen(bilanz, b, inst, name, p)
            behalten.append(p)
            continue

        # Vierte Stufe (T-362): die MENGE des Schutzes. Der gemerkte Auftrag
        # kann wirksam sein und trotzdem zu klein - eine Position mit 0,48
        # SOL und einem Stop ueber 0,47 ist kein geschuetzter Bestand.
        #
        # **Hier wird nichts gestellt.** `stops_nachziehen.py` traegt nur
        # Kennungen nach; ein Nachsetzen braucht einen Schutzpreis, den
        # niemand genannt hat. Ein geratener Notausstieg ist eine Order,
        # die jemand nicht bestellt hat.
        _deckung_messen(bilanz, b, inst, name, p)

        # Bestand da, Stop nicht (mehr) wirksam -> neu setzen. Gesichert wird
        # nur, was wirklich gehalten wird (nicht mehr als der Bestand).
        menge = b.menge_gerundet(inst, min(bestand, buch_menge) if buch_menge
                                 else bestand)
        if not menge:
            _ansage("%s: Bestand %.8f kleiner als die kleinste Ordergroesse - "
                    "kein Stop moeglich" % (inst, bestand))
            p["boersen_stop_fehlt"] = True
            _befund(bilanz, inst, name, "fehlt_weiter",
                    "Bestand %.8f unter der kleinsten Ordergroesse" % bestand)
            bilanz["fehlt_weiter"] += 1
            behalten.append(p)
            continue
        if not anwenden:
            _ansage("STOP FEHLT: %s - wuerde %.8f Stueck bei %.6f sichern"
                    % (inst, menge, float(p.get("stop") or 0.0)))
            p["boersen_stop_fehlt"] = True
            _befund(bilanz, inst, name, "stop_fehlt",
                    "wuerde %.8f Stueck ueber %.6f sichern"
                    % (menge, float(p.get("stop") or 0.0)))
            bilanz["fehlt_weiter"] += 1
            behalten.append(p)
            continue
        try:
            txid = b.stop_setzen(inst, menge, float(p.get("stop") or 0.0))
        except Exception as e:                                 # noqa: BLE001
            _ansage("Stop fuer %s liess sich NICHT setzen: %s" % (inst, e))
            txid = None
        if txid:
            p["stop_algo_id"] = txid
            p["stop_txid"] = txid
            p["boersen_stop_fehlt"] = False
            bilanz["nachgesetzt"] += 1
            _befund(bilanz, inst, name, "nachgesetzt",
                    "%.8f Stueck ueber %s" % (menge, p.get("stop")))
            _ansage("Stop nachgesetzt: %s %.8f ueber %s (Kennung %s)"
                    % (inst, menge, p.get("stop"), txid))
        else:
            p["boersen_stop_fehlt"] = True
            _befund(bilanz, inst, name, "fehlt_weiter",
                    "Stop liess sich nicht setzen")
            bilanz["fehlt_weiter"] += 1
        behalten.append(p)

    if anwenden:
        z["positionen"] = behalten

    # Waisenstops: das Buch kennt eine Kennung, die zu keiner Live-Position
    # mehr gehoert. Nur diese werden storniert - ein Stop, den das Buch nie
    # gefuehrt hat, ist fremde Absicherung (siehe Modulkopf, Regel 4).
    gefuehrt = {_stop_id(p) for p in behalten
                if p.get("modus") == "live" and _stop_id(p)}
    kandidaten = []
    for p in positionen:
        if p.get("modus") == "live":
            continue
        sid = _stop_id(p)
        if sid:
            kandidaten.append((str(p.get("boerse") or standard).lower(), sid,
                               p.get("inst")))
    for e in z.get("offene_stops") or []:
        sid = _stop_id(e)
        if sid:
            kandidaten.append((str(e.get("boerse") or standard).lower(), sid,
                               e.get("inst")))
    for sid in weg_ids:
        kandidaten.append((None, sid, None))
    for name, sid, inst in kandidaten:
        if not sid or sid in gefuehrt:
            continue
        # Nur die Boerse DIESER Kennung befragen: ein Rueckfall auf eine andere
        # Boerse wuerde eine fremde Order unter falscher Kennung nachschlagen.
        # Ist die Boerse nicht geladen, bleibt die Kennung unangetastet.
        b = boersen.get(name) if name else None
        if b is None and not name:
            b = next((x for x in boersen.values() if x is not None), None)
        if b is None:
            continue
        try:
            wirksam = b.stop_wirksam(sid)
        except Exception as e:                                 # noqa: BLE001
            _ansage("Waisenstop %s nicht lesbar: %s" % (sid, e))
            bilanz["unklar"] += 1
            continue
        if not wirksam:
            continue                      # an der Boerse erledigt - vergessen
        bilanz["waisen"] += 1
        _befund(bilanz, inst, name or "?", "waisen",
                "Stop %s ohne Live-Position" % sid)
        if anwenden:
            try:
                b.stop_stornieren(inst, sid)
                _ansage("WAISENSTOP %s (%s) storniert" % (sid, inst))
            except Exception as e:                             # noqa: BLE001
                _ansage("WAISENSTOP %s nicht stornierbar: %s" % (sid, e))
        else:
            _ansage("WAISENSTOP %s (%s) - wuerde storniert" % (sid, inst))
    return bilanz


# --- Dateien ----------------------------------------------------------------

def _lade_json(pfad):
    with open(pfad, "r", encoding="utf-8") as f:
        return json.load(f)


def _speichere(pfad, z):
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anwenden", action="store_true",
                    help="fehlende Stops setzen und Weggelaufenes buchen")
    ap.add_argument("--pfad", default=ZUSTAND, help="abweichende zustand.json")
    a = ap.parse_args(argv)

    if not os.path.exists(a.pfad):
        print("keine %s - nichts zu tun" % a.pfad)
        return 0
    if a.anwenden:
        alter = time.time() - os.path.getmtime(a.pfad)
        if alter < MIN_ALTER_S:
            print("zustand.json ist %d s alt (juenger als %d s) - ein Zyklus "
                  "laeuft vermutlich gerade. Spaeter erneut versuchen."
                  % (alter, MIN_ALTER_S))
            return 2

    w = _lade_json(WACHEN) if os.path.exists(WACHEN) else {}
    z = _lade_json(a.pfad)
    standard = "kraken"
    roh = w.get("boersen") or ([w["boerse"]] if w.get("boerse") else [])
    if roh:
        standard = str(roh[0]).strip().lower()
    quote = w.get("kraken_quote")

    import handeln                                          # noqa: PLC0415

    print("Buch gegen Boerse: %d Position(en), davon %d live, Modus %s"
          % (len(z.get("positionen") or []),
             len([p for p in z.get("positionen") or []
                  if p.get("modus") == "live"]),
             "ANWENDEN" if a.anwenden else "Vorschau (ordert nichts)"))
    bilanz = pruefe(z, anwenden=a.anwenden, journal=handeln.journal,
                    standard=standard, quote=quote)
    print("geprueft %(geprueft)d  ok %(ok)d  nachgesetzt %(nachgesetzt)d  "
          "stop fehlt weiter %(fehlt_weiter)d  weg %(weg)d  ausgebucht "
          "%(ausgebucht)d  waisen %(waisen)d  unklar %(unklar)d" % bilanz)

    # Fremde Stops nur anzeigen, wenn jemand davorsitzt (Vorschau): sie
    # gehoeren nicht zur Spur und werden nie angefasst.
    if not a.anwenden:
        namen = sorted({str(p.get("boerse") or standard).lower()
                        for p in z.get("positionen") or []
                        if p.get("modus") == "live"})
        try:
            boersen = lade_boersen(namen, quote=quote)
            bekannt = {_stop_id(p) for p in z.get("positionen") or [] if _stop_id(p)}
            for name, b in boersen.items():
                if b is None or not hasattr(b, "fremde_stops"):
                    continue
                fremd = b.fremde_stops(bekannt)
                if fremd is None:
                    continue
                for txid, o in fremd:
                    print("  fremder Stop an der Boerse (nicht vom Buch "
                          "gefuehrt, wird NICHT angefasst): %s %s %s menge %s "
                          "preis %s" % (name, txid, o.get("paar"), o.get("menge"),
                                        o.get("preis")))
        except Exception as e:                                 # noqa: BLE001
            print("  fremde Stops nicht lesbar (%s)" % e)

    if a.anwenden:
        _speichere(a.pfad, z)
        print("zustand.json geschrieben")
    else:
        print("nichts geschrieben (Vorschau) - mit --anwenden ausfuehren")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())