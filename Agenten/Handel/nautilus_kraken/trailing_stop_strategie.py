"""Trailing-Stop-Strategie der Kraken-Spur (Papier, Spot BTC/EUR oder Futures PF_XBTUSD).

Die Ausstiegsform, die Max fuer spiegel/kopier bestellt hat, als echte
NautilusTrader-Strategy im Kraken-Paper-Node. Zwei Produkttypen, ein Kern:
Spot (BTC/EUR, kein Hebel, EUR) und Futures (PF_XBTUSD Perpetual, Hebel, USD).
Symbol, Waehrung, Gebuehr und die Ausstiegsparameter kommen aus wachen.json.

KEIN ORDERPFAD
--------------
Die Strategie stellt keine Broker-Order: Sie fuehrt ein PAPIER-Buch - jede
Position traegt Einstieg, Stop, Trailing und Frist in sich selbst (Muster:
spiegel/kopier, nautilus/OKX). `handel_erlaubt` steht false in wachen.json,
bis alle Freigabewerte erfuellt sind.

EINSTIEGE
---------
Signale kommen aus der KOPIER-Spur (Pump.fun-Copy-Trade): Jeder frische
Kauf, den kopier in ihr Journal bucht (aktion=eroeffnen), wird hier zu
einer Papier-Position im Kraken-Instrument zum aktuellen Mid - ein Proxy,
dokumentiert als Messung der AUSSTIEGSFORM auf dem liquiden Instrument,
nicht als Markt-Urteil ueber Pump.fun-Tokens.

AUSSTIEGE (die bestellte Form)
------------------------------
- Harter Stop: stop_pct sitzt so, dass der realisierte Verlust am Stop
  inklusive Slippage und Gebuehr maximal 20 % des Einsatzes betraegt.
- Trailing: lag der Kurs trail_aktiv_ab_pct ueber dem Einstieg, haengt der
  Ausstieg trail_abstand_pct unter dem hoechsten beobachteten Kurs.
- Frist: 168 h Sicherheitsnetz gegen tote Positionen.
"""

from datetime import datetime, timezone

from nautilus_trader.trading.strategy import Strategy


# --- Reine Mathematik (testbar ohne Engine) -------------------------------

def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bis_zeit(iso):
    try:
        return datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def _plus_stunden(iso, stunden):
    z = _bis_zeit(iso)
    if z is None:
        return iso
    from datetime import timedelta
    return (z + timedelta(hours=stunden)).isoformat(timespec="seconds")


def betrag_feld(w, basis):
    """Feldname fuer Betraege: einsatz_eur / einsatz_usd je Waehrung."""
    return "%s_%s" % (basis, w.get("waehrung", "usd").lower())


def kaufpreis(mid, w):
    """Einstiegspreis: Mid plus Slippage - wie bei spiegel/kopier."""
    return mid * (1 + w["slippage_pct"] / 100.0)


def verkaeuflich(menge, kurs, w):
    """Erloes nach Slippage und Gebuehr - die Kosten wirken zweimal."""
    return menge * kurs * (1 - w["slippage_pct"] / 100.0) * (
        1 - w["gebuehr_pct"] / 100.0)


def ausstiegsgrund(p, kurs, jetzt, w):
    """Der Ausstiegsgrund einer Papier-Position - EINE Stelle.

    Reihenfolge: zuerst der harte Stop (Schaden begrenzen), dann Trailing,
    dann Frist. Ein gerissener Stop schliesst zum BEOBACHTETEN Kurs, nicht
    zum Stop-Preis.
    """
    if kurs <= p["stop_preis"]:
        return "stop"
    if p.get("trail_abstand_pct"):
        p["hoechster_kurs"] = max(p.get("hoechster_kurs") or kurs, kurs)
        peak = p["hoechster_kurs"] / p["preis_einstieg"] - 1
        if peak >= p["trail_aktiv_ab_pct"] / 100.0:
            trail_stop = p["hoechster_kurs"] * (
                1 - p["trail_abstand_pct"] / 100.0)
            if kurs <= trail_stop:
                return "trail"
    if jetzt >= (_bis_zeit(p["frist"]) or jetzt):
        return "frist"
    return None


def stop_preis_fuer(einstieg, w):
    return einstieg * (1 - w["stop_pct"] / 100.0)


# --- Die NautilusTrader-Strategie -----------------------------------------

class TrailingStopStrategie(Strategy):
    """Papier-Buch ueber Kraken-Quotes mit Stop/Trailing/Frist.

    Bekommt beim Start die offenen Positionen und die frischen Signale
    (Kopier-Kaeufe) uebergeben; nach dem Zyklus holt der Aufrufer die
    veraenderten Listen ueber `positionen` und `buchungen` ab. Der Node
    lebt nur ~30 s je Zyklus, deshalb liegt der Zustand ausserhalb der
    Engine (zustand.json), nicht im Cache.
    """

    def __init__(self, config, wachen, positionen, signale, buchungen):
        super().__init__(config)
        self.w = wachen
        self.symbol = wachen.get("symbol", "BTC/EUR")
        self.positionen = positionen
        self.signale = list(signale)
        self.buchungen = buchungen
        self.ziel = None
        self.letzte_quotes = 0

    def on_start(self):
        ziel = None
        for inst in self.cache.instruments():
            if self.symbol in str(inst.id):
                ziel = inst.id
                break
        if ziel is None:
            from nautilus_trader.model.identifiers import InstrumentId
            ziel = InstrumentId.from_str("%s.KRAKEN" % self.symbol)
        self.ziel = ziel
        self.subscribe_quote_ticks(ziel)
        self.log.info("Subscribed quotes: %s" % ziel)

    def on_quote_tick(self, tick):
        kurs = float((tick.bid_price + tick.ask_price) / 2.0)
        self.letzte_quotes += 1
        jetzt = datetime.now(timezone.utc)
        einsatz_feld = betrag_feld(self.w, "einsatz")
        wert_feld = betrag_feld(self.w, "wert")
        # 1. Ausstiege pruefen (Stop/Trailing/Frist) - mit Kurs.
        behalten = []
        for p in self.positionen:
            grund = ausstiegsgrund(p, kurs, jetzt, self.w)
            if grund:
                erloes = verkaeuflich(p["menge"], kurs, self.w)
                self.buchungen.append({
                    "aktion": "schliessen", "grund": grund, "kurs": kurs,
                    "symbol": p.get("symbol", ""), "token": p.get("token", ""),
                    "menge": p["menge"], einsatz_feld: p[einsatz_feld],
                    wert_feld: erloes,
                })
            else:
                p["letzter_kurs"] = kurs
                behalten.append(p)
        self.positionen = behalten
        # 2. Frische Signale (Kopier-Kaeufe) einbuchen, wenn Platz ist.
        max_offen = int(self.w.get("max_offene_positionen", 4))
        while self.signale and len(self.positionen) < max_offen:
            sig = self.signale.pop(0)
            einsatz = float(self.w.get("max_risiko_pro_trade", 50))
            preis = kaufpreis(kurs, self.w)
            gebuehr = einsatz * self.w["gebuehr_pct"] / 100.0
            menge = (einsatz - gebuehr) / preis
            self.positionen.append({
                "kette": "kraken", "token": self.symbol,
                "symbol": "KOP:%s" % (sig.get("symbol") or "?"),
                "quelle": "kopier", "quelle_token": sig.get("token", ""),
                einsatz_feld: einsatz, "menge": menge,
                "preis_einstieg": preis, "letzter_kurs": kurs,
                "stop_preis": stop_preis_fuer(preis, self.w),
                "trail_aktiv_ab_pct": self.w["trail_aktiv_ab_pct"],
                "trail_abstand_pct": self.w["trail_abstand_pct"],
                "hoechster_kurs": preis,
                "frist": _plus_stunden(_jetzt(),
                                       self.w.get("haltedauer_stunden", 168)),
                "eroeffnet": _jetzt(),
            })
            self.buchungen.append({
                "aktion": "eroeffnen", "grund": "kopier", "kurs": preis,
                "symbol": self.positionen[-1]["symbol"], "token": self.symbol,
                "menge": menge, einsatz_feld: einsatz, wert_feld: None,
            })

    def on_stop(self):
        """Muss ueberschrieben sein - sonst warnt die Engine und die
        Warnung enthaelt das Dauerlauf-Filterwort 'stop' (siehe handeln.py)."""
        if self.ziel is not None:
            try:
                self.unsubscribe_quote_ticks(self.ziel)
            except Exception:                                   # noqa: BLE001
                pass
        self.log.info("Zyklus beendet, %d Quotes" % self.letzte_quotes)
