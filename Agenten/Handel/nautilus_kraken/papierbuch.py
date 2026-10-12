"""Papierbuch fuer den Kraken-Paper-Node: simulierte Fills, keine Broker-Order.

Signal: SMA-Kreuzung auf 15-Minuten-Mids (schnell/langsam) mit Abstandsband
(Hysterese gegen Hin-und-Her, das sonst nur Gebuehren kostet), nur Long.
Backtest 7,5 Tage BTC/EUR: ohne Band 35 Trades/-209 EUR, Band 0,4 % 1 Trade.
Kauf voll investiert zum Ask, Verkauf zum Bid, Taker-Gebuehr je Seite.
Stand -> papierbuch.<produkt>.json (liest der Leitstand),
Fills -> papierjournal.<produkt>.csv.
Sperre papierbuch.<produkt>.lock verhindert zwei Nodes auf einem Buch.
"""

import csv
import datetime as dt
import json
import os
import sys
from collections import deque
from pathlib import Path


def _stand_pfad(produkt, ordner):
    return Path(ordner) / ("papierbuch.%s.json" % produkt)


def sperren(produkt, ordner):
    """Exklusive Sperre fuer die Lebensdauer des Prozesses; None wenn belegt."""
    f = open(Path(ordner) / ("papierbuch.%s.lock" % produkt), "a+")
    try:
        if sys.platform == "win32":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def lese_stand(produkt, ordner):
    try:
        return json.loads(_stand_pfad(produkt, ordner).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class Papierbuch:
    def __init__(self, produkt, ordner, startkapital=1000.0, gebuehr=0.0026,
                 schnell=4, langsam=16, takt_s=900, band=0.004):
        self.produkt = produkt
        self.ordner = Path(ordner)
        self.startkapital = startkapital
        self.gebuehr = gebuehr
        self.schnell, self.langsam, self.takt_s = schnell, langsam, takt_s
        self.band = band
        self._mids = deque(maxlen=langsam)
        self._letzter_takt = None
        self.kasse = startkapital
        self.position = None
        self.realisiert = 0.0
        self.trades = 0
        self.letzter_bid = None
        alt = lese_stand(produkt, ordner)
        if alt:
            self.kasse = alt["kasse"]
            self.position = alt["position"]
            self.realisiert = alt["realisiert"]
            self.trades = alt["trades"]
            self._mids.extend(alt.get("mids", []))
            self._letzter_takt = alt.get("letzter_takt")

    # --- Takt -------------------------------------------------------------
    def tick(self, bid, ask, ts):
        """ts in Sekunden. Nur ein Mid je Takt geht ins Signal."""
        self.letzter_bid = bid
        takt = int(ts // self.takt_s)
        if takt == self._letzter_takt:
            return
        self._letzter_takt = takt
        self._mids.append((bid + ask) / 2)
        if len(self._mids) >= self.langsam:
            werte = list(self._mids)
            schnell = sum(werte[-self.schnell:]) / self.schnell
            langsam = sum(werte) / len(werte)
            if self.position is None and schnell > langsam * (1 + self.band):
                self._kaufen(ask, ts)
            elif self.position is not None and schnell < langsam * (1 - self.band):
                self._verkaufen(bid, ts)
        self._schreiben(ts)

    def _kaufen(self, ask, ts):
        menge = self.kasse * (1 - self.gebuehr) / ask
        self.position = {"menge": menge, "einstieg": ask, "kosten": self.kasse}
        self._journal(ts, "kauf", ask, menge, 0.0)
        self.kasse = 0.0

    def _verkaufen(self, bid, ts):
        erloes = self.position["menge"] * bid * (1 - self.gebuehr)
        pnl = erloes - self.position["kosten"]
        self.realisiert += pnl
        self.trades += 1
        self._journal(ts, "verkauf", bid, self.position["menge"], pnl)
        self.kasse = erloes
        self.position = None

    # --- Auswertung ---------------------------------------------------------
    def unrealisiert(self):
        if self.position is None or self.letzter_bid is None:
            return 0.0
        return (self.position["menge"] * self.letzter_bid * (1 - self.gebuehr)
                - self.position["kosten"])

    def stand(self):
        return {"produkt": self.produkt, "startkapital": self.startkapital,
                "kasse": self.kasse, "position": self.position,
                "realisiert": self.realisiert, "unrealisiert": self.unrealisiert(),
                "trades": self.trades}

    def _schreiben(self, ts):
        daten = self.stand()
        daten["mids"] = list(self._mids)
        daten["letzter_takt"] = self._letzter_takt
        daten["stand"] = dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()
        ziel = _stand_pfad(self.produkt, self.ordner)
        tmp = ziel.with_suffix(".tmp")
        tmp.write_text(json.dumps(daten, indent=1), encoding="utf-8")
        os.replace(tmp, ziel)

    def _journal(self, ts, seite, preis, menge, pnl):
        pfad = self.ordner / ("papierjournal.%s.csv" % self.produkt)
        neu = not pfad.exists()
        with pfad.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if neu:
                w.writerow(["zeit", "seite", "preis", "menge", "pnl"])
            w.writerow([dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(),
                        seite, preis, menge, round(pnl, 6)])
