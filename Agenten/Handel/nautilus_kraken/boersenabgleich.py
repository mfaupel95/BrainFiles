"""Buch gegen Boerse fuer die Nautilus-Arme (T-227).

Warum es das gibt (Befund 09.10.2026)
------------------------------------
Die Nautilus-Arme (`nautilus_kraken` Spot, `nautilus_kraken_futures` Futures)
haben einen Live-Orderpfad ueber Kraken-REST (bzw. Kraken-Futures-REST),
aber KEINEN Boersenabgleich. Sobald einer scharf geht, fehlt der Abgleich:

  1. Ist der Bestand noch da? Wenn nein: Stop gefeuert oder Handverkauf ->
     Position mit dem ECHTEN Ausstiegspreis ausbuchen.
  2. Ist der Notausstieg noch wirksam? Wenn nein und Bestand da -> neu setzen.
  3. Kennt das Buch eine Stop-Kennung, die zu keiner Live-Position mehr
     gehoert, und steht sie an der Boerse noch offen -> Waisenstop, stornieren.
  4. Steht an der Boerse ein Stop, den das Buch NICHT kennt -> nur MELDEN,
     nie anfassen.

Die REGELN sind von `mosaic/boersenabgleich.py` uebernommen, nicht der Code -
aber die Positionsstruktur ist anders (Nautilus statt mosaic):

  - `token` statt `inst` (die Boerse kennt das Paar, nicht das Symbol)
  - `preis_einstieg` statt `einstieg`
  - `stop_preis` statt `stop`
  - `einsatz_eur` / `einsatz_usd` statt `nominal`
  - `stop_id` (ein Feld, nicht `stop_algo_id` / `stop_txid`)
  - `boerse` fehlt noch in wachen.json - wird ergaenzt

Die Boerse ist bei beiden Armen Kraken (Spot oder Futures), abhaengig von
`produkt` in wachen.json. Der Abgleich laeuft ueber `kraken_rest`, das
intern `kraken.py` (Spot) oder `kraken_futures.py` (Futures) laedt.

Aufruf (aus nautilus_kraken):
    python boerenabgleich.py               # Vorschau, schreibt und ordert nichts
    python boersenabgleich.py --anwenden  # fehlende Stops setzen, Weggelaufenes buchen

Im Betrieb ruft `handeln.py` `pruefe(z, anwenden=True)` am Anfang jedes
Live-Zyklus (nach dem Buchabgleich, vor den Ausstiegen).
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

# Lade kraken_rest (diese laedt intern kraken.py oder kraken_futures.py)
_kraken_rest_path = os.path.join(HIER, "kraken_rest.py")
_spec = importlib.util.spec_from_file_location("kraken_rest_abgleich", _kraken_rest_path)
kraken_rest = importlib.util.module_from_spec(_spec)
sys.modules["kraken_rest_abgleich"] = kraken_rest
_spec.loader.exec_module(kraken_rest)

# Kraken-Spot-Client (fuer Spot-Abfragen: kontostaende, offene_orders, etc.)
_kraken_path = os.path.join(HANDEL, "kraken", "kraken.py")
_spec2 = importlib.util.spec_from_file_location("kraken_spot_abgleich", _kraken_path)
kraken_spot = importlib.util.module_from_spec(_spec2)
sys.modules["kraken_spot_abgleich"] = kraken_spot
_spec2.loader.exec_module(kraken_spot)

# Kraken-Futures-Client (fuer Futures-Abfragen)
_kraken_futures_path = os.path.join(HIER, "kraken_futures.py")
_spec3 = importlib.util.spec_from_file_location("kraken_futures_abgleich", _kraken_futures_path)
kraken_futures = importlib.util.module_from_spec(_spec3)
sys.modules["kraken_futures_abgleich"] = kraken_futures
_spec3.loader.exec_module(kraken_futures)


def _jetzt():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ansage(text):
    print("  " + text)


def _befund(bilanz, inst, boerse, lage, text=""):
    bilanz.setdefault("befunde", []).append(
        {"inst": inst, "boerse": boerse, "lage": lage, "text": text})


def _stop_id(p):
    """Die gemerkte Stop-Kennung einer Position."""
    return (p.get("stop_id") or p.get("stop_algo_id")
            or p.get("stop_txid") or p.get("stop_ord_id") or None)


def _buch_menge(p):
    """Menge der Position im Buch."""
    m = float(p.get("menge") or 0)
    if m > 0:
        return m
    try:
        return float(p.get("einsatz_eur") or 0) / float(p.get("preis_einstieg") or 0)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _einsatz(p, w):
    """Einsatz der Position in der Waehrung der Wachen."""
    waehrung = (w.get("waehrung") or "usd").lower()
    feld = "einsatz_%s" % waehrung
    return float(p.get(feld) or 0.0)


# --- Kraken Boerse (Spot oder Futures) --------------------------------------

class KrakenBoerse:
    """Der Kraken-Zugang fuer den Abgleich (Spot oder Futures)."""

    def __init__(self, produkt="spot", wachen=None):
        self.produkt = (produkt or "spot").lower()
        self.wachen = wachen or {}
        self._spot = kraken_spot
        self._futures = kraken_futures
        self._details = {}

    def _client(self):
        if self.produkt == "futures":
            return self._futures
        return self._spot

    def name(self):
        return "kraken"

    def _paar(self):
        """Das Kraken-Paar aus wachen.json."""
        if self.produkt == "futures":
            return self.wachen.get("paar", "PF_SOLUSD")
        return self.wachen.get("paar", "XXBTZEUR")

    def basis(self, token):
        """Kraken-Code der Basiswaehrung (nur Spot)."""
        if self.produkt == "futures":
            # Futures: symbol ist PF_SOLUSD -> Basis SOL
            symbol = self._paar()
            return symbol.split("_")[0].replace("PF_", "")
        # Spot: Paar ist XXBTZEUR -> Basis XXBT
        paar = self._paar()
        # Extrahiere Basis aus dem Paar (ohne Quote)
        info = self._spot.paar_info(self._paar())
        # Wir brauchen den Basis-Code aus AssetPairs
        roh = self._spot._roh_oeffentlich("AssetPairs", pair=self._paar())
        for name, wert in (roh or {}).items():
            if name != "last":
                return wert.get("base")
        return paar[:-4]  # Fallback: letzte 4 Zeichen abschneiden

    def bestand(self, token):
        """Freier Bestand der Basiswaehrung; fehlt der Posten, ist er 0."""
        try:
            if self.produkt == "futures":
                # Futures: offene Positionen abfragen
                symbol = self._paar()
                positionen = self._futures.offene_positionen(symbol)
                # Summe der Groessen aller offenen Long-Positionen
                total = 0.0
                for p in positionen:
                    if p.get("side") == "long":
                        total += float(p.get("size") or 0)
                return total
            else:
                # Spot: Kontostaende abfragen
                konten = self._spot.kontostaende() or {}
                basis = self.basis(token)
                # Finde den passenden Kontostand
                for k, v in konten.items():
                    norm = k.lstrip("X")  # XXBT -> XBT
                    if norm == basis or k == basis:
                        return float(v or 0)
                return 0.0
        except Exception:
            return 0.0

    def stop_details(self, txid):
        if not txid:
            return {}
        if txid not in self._details:
            try:
                if self.produkt == "futures":
                    # Futures: offene Orders abfragen und Details finden
                    orders = self._futures.offene_orders()
                    for oid, o in (orders or {}).items():
                        if oid == txid:
                            self._details[txid] = o
                            break
                else:
                    self._details[txid] = self._spot.order_details(txid) or {}
            except Exception:
                self._details[txid] = {}
        return self._details[txid]

    def stop_wirksam(self, txid):
        """True/False, None = nicht lesbar."""
        if not txid:
            return False
        d = self.stop_details(txid)
        if not d:
            return None
        if self.produkt == "futures":
            # Futures: offene Order mit status
            if float(d.get("size") or 0) > 0:
                return False  # ausgefuehlt
            return True  # offen
        else:
            # Spot: Order-Details mit status
            if not d.get("status"):
                return None
            if float(d.get("vol_exec") or 0) > 0:
                return False
            return str(d.get("status")).lower() == "open"

    def stop_gefuellt(self, txid):
        if not txid:
            return False
        d = self.stop_details(txid)
        if self.produkt == "futures":
            return float(d.get("size") or 0) > 0
        return float(d.get("vol_exec") or 0) > 0

    def ausstieg(self, token, txid):
        """Der ECHTE Ausstieg des Boersen-Stops."""
        if not txid:
            return None
        d = self.stop_details(txid)
        if self.produkt == "futures":
            # Futures: Fuellung ueber /fills
            try:
                fills = self._futures._roh("/fills?lastFillTime=1970-01-01T00:00:00Z")
                menge = 0.0
                erloes = 0.0
                for f in fills.get("fills") or []:
                    if f.get("order_id") == txid:
                        menge += float(f.get("size") or 0)
                        erloes += float(f.get("fillPrice") or 0) * float(f.get("size") or 0)
                if menge <= 0:
                    return None
                return {"menge": menge, "preis": erloes / menge,
                        "erloes": erloes, "art": "stop-loss", "misc": "stopped"}
            except Exception:
                return None
        else:
            # Spot: order_details mit cost/fee/vol_exec
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
        try:
            if self.produkt == "futures":
                orders = self._futures.offene_orders()
                aus = []
                for oid, o in (orders or {}).items():
                    if oid in bekannt:
                        continue
                    aus.append((oid, o))
                return aus
            else:
                orders = self._spot.offene_orders()
                aus = []
                for txid, o in (orders or {}).items():
                    if txid in bekannt:
                        continue
                    if "stop" not in (o.get("art") or "").lower():
                        continue
                    aus.append((txid, o))
                return aus
        except Exception:
            return []

    def menge_gerundet(self, token, menge):
        """Menge auf lot_decimals abrunden."""
        try:
            if self.produkt == "futures":
                # Futures: mindestens 1 Kontrakt
                return max(1, int(round(float(menge))))
            else:
                # Spot: lot_decimals aus AssetPairs
                info = self._spot.paar_info(self._paar())
                stellen = int(info.get("mengen_stellen", 8))
                m = float(int(float(menge) * 10 ** stellen)) / 10 ** stellen
                if m <= 0 or m < float(info.get("mindestmenge") or 0):
                    return None
                return m
        except Exception:
            return None

    def stop_setzen(self, token, menge, preis):
        """Notausstieg als Stop-Loss setzen."""
        paar = self._paar()
        if self.produkt == "futures":
            return self._futures.stop_setzen(paar, menge, preis, echt=True)
        else:
            return self._spot.stop_setzen(paar, menge, preis, echt=True)

    def stop_stornieren(self, token, txid):
        if self.produkt == "futures":
            return self._futures.order_stornieren(txid)
        else:
            return self._spot.order_stornieren(txid)


# --- Abgleich ---------------------------------------------------------------

def pruefe(z, wachen=None, anwenden=False, journal=None, standard="kraken",
           laden=None):
    """Eine Runde Buch <-> Boerse. Rueckgabe: Zahlen fuer den Bericht.

    ``anwenden=False`` (Vorschau) liest nur und sagt, was es taete.
    ``laden`` ist die Naht fuer Tests (kein Netz): eine Funktion
    ``namen -> {name: Zugang}``.
    """
    bilanz = {"geprueft": 0, "ok": 0, "nachgesetzt": 0, "fehlt_weiter": 0,
              "weg": 0, "ausgebucht": 0, "waisen": 0, "unklar": 0,
              "befunde": []}

    if wachen is None:
        wachen = {}
    if laden is None:
        def _laden_default(namen):
            produkt = wachen.get("produkt", "spot").lower()
            try:
                return {n: KrakenBoerse(produkt=produkt, wachen=wachen)
                        for n in namen}
            except Exception as e:
                _ansage("Boersen nicht erreichbar (%s) - Buch unveraendert" % e)
                return {n: None for n in namen}
        laden = _laden_default

    positionen = z.get("positionen") or []
    live = [p for p in positionen if p.get("modus") == "live"]
    if not live:
        return bilanz

    namen = []
    for p in live:
        n = str(p.get("boerse") or standard).strip().lower()
        if n not in namen:
            namen.append(n)
    try:
        boersen = laden(namen)
    except Exception as e:
        _ansage("Boersen nicht erreichbar (%s) - Buch unveraendert" % e)
        bilanz["geprueft"] = len(live)
        bilanz["unklar"] = len(live)
        return bilanz

    behalten = []
    weg_ids = []
    for p in positionen:
        if p.get("modus") != "live":
            behalten.append(p)
            continue
        bilanz["geprueft"] += 1
        inst = p.get("token") or p.get("inst") or "?"
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
        waehrung = (wachen.get("waehrung") or "usd").lower()
        einsatz_feld = "einsatz_%s" % waehrung
        if not wachen.get("waehrung") and not p.get(einsatz_feld):
            for w in ("eur", "usd"):
                if p.get("einsatz_%s" % w):
                    waehrung = w
                    einsatz_feld = "einsatz_%s" % w
                    break

        try:
            bestand = b.bestand(inst)
        except Exception as e:
            _ansage("Bestand %s nicht lesbar: %s - unangetastet" % (inst, e))
            _befund(bilanz, inst, name, "unklar_bestand", str(e))
            bilanz["unklar"] += 1
            behalten.append(p)
            continue

        sid = _stop_id(p)
        try:
            wirksam = b.stop_wirksam(sid)
            gefuellt = b.stop_gefuellt(sid)
        except Exception as e:
            _ansage("Stop %s nicht lesbar: %s - unangetastet" % (sid, e))
            _befund(bilanz, inst, name, "unklar_stop", str(e))
            bilanz["unklar"] += 1
            behalten.append(p)
            continue

        buch_menge = _buch_menge(p)
        schwelle = max(0.0, buch_menge * 0.02)  # WEG_QUOTE

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
                except Exception as e:
                    _ansage("Waisenstop %s nicht stornierbar: %s" % (sid, e))
            a = None
            try:
                a = b.ausstieg(inst, sid)
            except Exception as e:
                _ansage("Ausstiegspreis %s nicht lesbar: %s" % (inst, e))
            if not a:
                _ansage("WEG, aber kein Ausstiegspreis belegbar: %s - Buch "
                        "bleibt unveraendert (bitte von Hand pruefen)" % inst)
                _befund(bilanz, inst, name, "weg_ohne_beleg",
                        "kein Ausstiegspreis an der Boerse")
                bilanz["unklar"] += 1
                behalten.append(p)
                continue
            einsatz = float(p.get(einsatz_feld) or 0.0)
            gv = a["erloes"] - einsatz
            _ansage("AUSSTIEG (%s): %s %.8f Stueck @ %.6f  Erloes %.2f  "
                    "G/V %+.2f" % (grund, inst, a["menge"], a["preis"],
                                   a["erloes"], gv))
            if journal:
                wert_feld = "wert_%s" % waehrung
                journal(zeit=_jetzt(), modus="live", aktion="verkauf",
                        inst=inst, seite=p.get("seite", "long"),
                        preis="%.6f" % a["preis"],
                        **{einsatz_feld: "%.2f" % a["erloes"]},
                        **{wert_feld: ""},
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
            behalten.append(p)
            continue

        if wirksam:
            bilanz["ok"] += 1
            if p.get("boersen_stop_fehlt"):
                p["boersen_stop_fehlt"] = False
            behalten.append(p)
            continue

        # Bestand da, Stop nicht (mehr) wirksam -> neu setzen
        menge = b.menge_gerundet(inst, min(bestand, buch_menge) if buch_menge
                                 else bestand)
        if not menge:
            _ansage("%s: Bestand %.8f kleiner als die kleinste Ordergroesse - "
                    "kein Stop moeglich" % (inst, bestand))
            p["boersen_stop_fehlt"] = True
            _befund(bilanz, inst, name, "fehlt_weiter",
                    "Bestand %.8f unter der kleinesten Ordergroesse" % bestand)
            bilanz["fehlt_weiter"] += 1
            behalten.append(p)
            continue
        stop_preis = float(p.get("stop_preis") or 0.0)
        if not anwenden:
            _ansage("STOP FEHLT: %s - wuerde %.8f Stueck bei %.6f sichern"
                    % (inst, menge, stop_preis))
            p["boersen_stop_fehlt"] = True
            _befund(bilanz, inst, name, "stop_fehlt",
                    "wuerde %.8f Stueck ueber %.6f sichern"
                    % (menge, stop_preis))
            bilanz["fehlt_weiter"] += 1
            behalten.append(p)
            continue
        try:
            txid = b.stop_setzen(inst, menge, stop_preis)
        except Exception as e:
            _ansage("Stop fuer %s liess sich NICHT setzen: %s" % (inst, e))
            txid = None
        if txid:
            p["stop_id"] = txid
            p["boersen_stop_fehlt"] = False
            bilanz["nachgesetzt"] += 1
            _befund(bilanz, inst, name, "nachgesetzt",
                    "%.8f Stueck ueber %s" % (menge, stop_preis))
            _ansage("Stop nachgesetzt: %s %.8f ueber %s (Kennung %s)"
                    % (inst, menge, stop_preis, txid))
        else:
            p["boersen_stop_fehlt"] = True
            _befund(bilanz, inst, name, "fehlt_weiter",
                    "Stop liess sich nicht setzen")
            bilanz["fehlt_weiter"] += 1
        behalten.append(p)

    if anwenden:
        z["positionen"] = behalten

    # Waisenstops
    gefuehrt = {_stop_id(p) for p in behalten
                if p.get("modus") == "live" and _stop_id(p)}
    kandidaten = []
    for p in positionen:
        if p.get("modus") == "live":
            continue
        sid = _stop_id(p)
        if sid:
            kandidaten.append((str(p.get("boerse") or standard).lower(), sid, p.get("token") or p.get("inst")))
    for sid in weg_ids:
        kandidaten.append((None, sid, None))
    for name, sid, inst in kandidaten:
        if not sid or sid in gefuehrt:
            continue
        b = boersen.get(name) if name else None
        if b is None and not name:
            b = next((x for x in boersen.values() if x is not None), None)
        if b is None:
            continue
        try:
            wirksam = b.stop_wirksam(sid)
        except Exception as e:
            _ansage("Waisenstop %s nicht lesbar: %s" % (sid, e))
            bilanz["unklar"] += 1
            continue
        if not wirksam:
            continue
        bilanz["waisen"] += 1
        _befund(bilanz, inst, name or "?", "waisen",
                "Stop %s ohne Live-Position" % sid)
        if anwenden:
            try:
                b.stop_stornieren(inst, sid)
                _ansage("WAISENSTOP %s (%s) storniert" % (sid, inst))
            except Exception as e:
                _ansage("WAISENSTOP %s nicht stornierbar: %s" % (sid, e))
        else:
            _ansage("WAISENSTOP %s (%s) - wuerde storniert" % (sid, inst))
    return bilanz


# --- Dateien ----------------------------------------------------------------

def _lade_json(pfad):
    with open(pfad, "r", encoding="utf-8") as f:
        return json.load(f)


def _speichern(pfad, z):
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


ZUSTAND = os.path.join(HIER, "zustand.json")
WACHEN = os.path.join(HIER, "wachen.json")


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
        if alter < 300:
            print("zustand.json ist %d s alt (juenger als 300 s) - ein Zyklus "
                  "laeuft vermutlich gerade. Spaeter erneut versuchen." % alter)
            return 2

    w = _lade_json(WACHEN) if os.path.exists(WACHEN) else {}
    z = _lade_json(a.pfad)
    standard = w.get("boerse") or "kraken"

    import handeln
    print("Buch gegen Boerse: %d Position(en), davon %d live, Modus %s"
          % (len(z.get("positionen") or []),
             len([p for p in z.get("positionen") or []
                  if p.get("modus") == "live"]),
             "ANWENDEN" if a.anwenden else "Vorschau (ordert nichts)"))
    bilanz = pruefe(z, wachen=w, anwenden=a.anwenden, journal=handeln.journal,
                    standard=standard)
    print("geprueft %(geprueft)d  ok %(ok)d  nachgesetzt %(nachgesetzt)d  "
          "stop fehlt weiter %(fehlt_weiter)d  weg %(weg)d  ausgebucht "
          "%(ausgebucht)d  waisen %(waisen)d  unklar %(unklar)d" % bilanz)

    if not a.anwenden:
        # Fremde Stops nur anzeigen
        try:
            produkt = w.get("produkt", "spot").lower()
            boerse = KrakenBoerse(produkt=produkt, wachen=w)
            bekannt = {_stop_id(p) for p in z.get("positionen") or [] if _stop_id(p)}
            fremd = boerse.fremde_stops(bekannt)
            if fremd:
                for txid, o in fremd:
                    print("  fremder Stop an der Boerse (nicht vom Buch "
                          "gefuehrt, wird NICHT angefasst): %s %s" % (txid, o))
        except Exception as e:
            print("  fremde Stops nicht lesbar (%s)" % e)

    if a.anwenden:
        _speichern(a.pfad, z)
        print("zustand.json geschrieben")
    else:
        print("nichts geschrieben (Vorschau) - mit --anwenden ausfuehren")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())