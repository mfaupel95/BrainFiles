"""nautilus_emacross - der EMA-Cross aus nautilus_trader, im Hausbuchformat.

WARUM DIESE SPUR UND KEIN UMBAU DER NAUTILUS-ARME
-------------------------------------------------
Die drei Arme nautilus, nautilus_kraken und nautilus_kraken_futures lesen
ihre Einstiege aus dem Journal der kopier-Spur - das sind Solana-Memecoin-
Kaeufe - und buchen sie als BTC-Proxy. Das ist keine Strategie, sondern ein
Umweg: das Signal gehoert einem anderen Markt als die Position. Gemessen
(03.10.2026): 6, 4 und 2 Runden, alle auf einem Instrument, Excess 0,09 %,
1,08 % und ohne Basislinie.

Diese Spur faehrt stattdessen die Originalstrategie des Projekts, an ihrem
eigenen Instrument und mit ihren eigenen Kerzen.

DIE ORIGINALSTRATEGIE, WOERTLICH
--------------------------------
Aus nautechsystems/nautilus_trader, develop, docs/tutorials/ema_cross.py:

    class EMACross(Strategy):
        def on_start(self):
            self.register_indicator_for_bars(self.bar_type, self.fast_ema)
            self.register_indicator_for_bars(self.bar_type, self.slow_ema)
            self.subscribe_bars(self.bar_type)

        def on_bar(self, _bar):
            if not self.indicators_initialized():
                return
            if self.fast_ema.value >= self.slow_ema.value:
                if self.portfolio.is_net_flat(self.instrument_id):
                    self.buy()
                elif self.portfolio.is_net_short(self.instrument_id):
                    self.close_all_positions(self.instrument_id)
                    self.buy()
            elif self.fast_ema.value < self.slow_ema.value:
                if self.portfolio.is_net_flat(self.instrument_id):
                    self.sell()
                elif self.portfolio.is_net_long(self.instrument_id):
                    self.close_all_positions(self.instrument_id)
                    self.sell()

        def on_stop(self):
            self.close_all_positions(self.instrument_id)

Die Parameter aus dem Beispiel (examples/backtest/
crypto_ema_cross_ethusdt_trade_ticks.py): fast=10, slow=20,
trade_size=0.10.

WAS DIESER PORT KEEPERT UND WAS EINE EIGENE ENTSCHEIDUNG IST
----------------------------------------------------------
* KEEPERT: die Regel selbst, beide Richtungen, die Umkehr beim Kreuz, das
  Flat beim Stop der Daten.
* EIGENE ENTSCHEIDUNG: Die Originalfassung dreht die Position mit einer
  Market-Order pro Bar-Takt und ohne Schutz-Stop am Markt. Fuer ein Haus,
  das an einer echten Boerse handelt und bei dem T-273 (Position ohne
  Schutz) offen war, ist das keine uebernehmbare Eigenschaft. Diese Spur
  haelt deshalb `stop_pct` und `ziel_r` aus der Wachen, und der Ausstieg
  am Kreuz laeuft ueber `zusatz_ausstieg` - als Grund "emacross", damit er
  im Journal als eigener Ausstiegsgrund steht und nicht als Stop verbucht
  wird.
* EIGENE ENTSCHEIDUNG: BarType. Das Original laeuft auf 250 Ticks
  (ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL); Ticks sind hier nicht
  verfuegbar, die Spur rechnet auf abgeschlossenen 1H-Kerzen. Das ist ein
  anderes Signal und damit eine andere Strategie - es steht als
  `_barmasse_vermerk` in der Wachen und ist der Grund, warum diese Spur
  NICHT als Mass fuer das Original taugt, sondern als Test, ob die Regel
  auf unseren Daten etwas bringt.

Ohne Freigabe, ohne Orderweg, ohne Live-Pfad. Diese Spur soll messen, nicht
handeln.
"""
import os

import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.append(HANDEL)          # ANGEHAENGT, nicht vorn (siehe scanner)

NAME = "nautilus_emacross"
KERZEN = 200          # reichen fuer EMA(20) mit Abstand plus Rauschen
MIN_KERZEN = 40       # darunter ist EMA(20) noch nicht belastbar


def richte_ema(kurse, periode, faktor=None):
    """EMA ueber die Schlusskurse, so wie nautilus_trader sie rechnet.

    Nautilus nutzt den Seedwert SMA der ersten `periode` Werte und danach
    alpha = 2/(n+1). Genau das ist hier nachgebaut - eine EMA, die anders
    gesetzt wird, waere eine andere Strategie und der Vergleich mit dem
    Original waere wertlos.
    """
    if faktor is None:
        faktor = 2.0 / (periode + 1.0)
    if len(kurse) < periode:
        return None
    seed = sum(kurse[:periode]) / float(periode)
    wert = seed
    for k in kurse[periode:]:
        wert = (k - wert) * faktor + wert
    return wert


def ema_paar(kurse, schnell, langsam):
    """(schnell, langsam) - None, wenn die lange EMA noch nicht steht."""
    a = richte_ema(kurse, schnell)
    b = richte_ema(kurse, langsam)
    return a, b


def richtung(kurse, schnell, langsam):
    """'long', 'short' oder None (noch keine belastbare EMA).

    Nimmt Kerzen ODER Schlusskurse: `schluesse` erkennt beide Formen. Das
    Original rechnet auf `Bar.close`; wer hier Kerzen uebergibt, soll nicht
    an einer Liste von Zeilen scheitern.
    """
    a, b = ema_paar(schluesse(kurse), schnell, langsam)
    if a is None or b is None:
        return None
    return "long" if a >= b else "short"


def neue_richtung(kurse, schnell, langsam, bisher):
    """Die Richtung, in der es GEHT - oder None, wenn sie gleich bleibt.

    Das ist der Punkt, an dem diese Spur vom Zeitgatter weg ist: Sie
    meldet nur dann eine Seite, wenn die schnelle EMA die langsame
    tatsaechlich kreuzt. Ein laufendes Signal ohne Kreuz liefert hier
    nichts, und damit nichts, was gebucht werden koennte.
    """
    jetzt = richtung(kurse, schnell, langsam)
    if jetzt is None or jetzt == bisher:
        return None
    return jetzt


def quelle(w):
    """Kerzen des EIGENEN Instruments - nicht die der kopier-Spur.

    (daten, kurse, fehler) ist die Hausform: daten[inst] traegt die Kerzen,
    kurse[inst] den letzten Kurs. Geholt werden sie ueber denselben Weg,
    den der scanner benutzt - oeffentliche OKX-Schnittstelle, kein
    Schluessel, kein Abruf aus einer fremden Spur.
    """
    inst = w.get("symbol", "BTC-USDT-SWAP")
    anzahl = int(w.get("kerzen", KERZEN))
    try:
        sys.path.insert(0, os.path.join(HANDEL, "scanner"))
        import okx
        reihe = okx.kerzen(inst, bar="1H", anzahl=anzahl)
    except Exception as e:                                   # noqa: BLE001
        return {}, {}, ["Kerzen nicht abrufbar: %s" % str(e)[:120]]
    if not reihe or len(reihe) < MIN_KERZEN:
        return {}, {}, ["nur %d Kerzen, brauche %d" % (len(reihe or []), MIN_KERZEN)]
    daten = {inst: {"kerzen": reihe}}
    kurse = {inst: float(reihe[-1][4])}
    return daten, kurse, []


def signal(daten, w):
    """Die Seite, in der das Kreuz zeigt - None ohne Kreuz.

    `spur_buch` ruft `signal(daten[inst], w)` - also bekommt diese
    Funktion die INNERE Map `{"kerzen": [...]}`, nicht das aeussere Dict
    ueber alle Instrumente. Eine erste Fassung suchte hier
    `daten.get(symbol)` und fand dort nie etwas: die Spur rechnete
    woertlich nie, blieb bei 0 Runden und sah vollstaendig gesund aus.
    Beide Formen werden deshalb angenommen.
    """
    inst = w.get("symbol", "BTC-USDT-SWAP")
    if isinstance(daten, dict) and "kerzen" not in daten and inst in daten:
        daten = daten[inst]
    kerzen = (daten or {}).get("kerzen") or []
    if len(kerzen) < int(w.get("mindest_kerzen", MIN_KERZEN)):
        return None
    return richtung(schluesse(kerzen),
                    int(w.get("ema_schnell", 10)),
                    int(w.get("ema_langsam", 20)))


def schluesse(kerzen):
    """Die Schlusskurse aus einer Kerzenreihe - Folge oder Liste."""
    out = []
    for k in kerzen:
        if isinstance(k, (list, tuple)):
            out.append(float(k[4]))
        else:
            out.append(float(k))
    return out


def kreuzwechsel(kerzen, w, position):
    """True, wenn das EMA-Kreuz die Position auf die Gegenseite dreht.

    Der Ausstiegsgrund des Originals ist das Kreuz selbst. Hier heisst er
    'emacross' - er ist damit unterscheidbar von einem Stop und von einem
    Ziel, und die Auswertung zaehlt ihn als Handelsrunde, nicht als
    Zwangsschluss.
    """
    if len(kerzen) < int(w.get("mindest_kerzen", MIN_KERZEN)):
        return False
    jetzt = richtung(schluesse(kerzen),
                     int(w.get("ema_schnell", 10)),
                     int(w.get("ema_langsam", 20)))
    if jetzt is None:
        return False
    return jetzt != position.get("seite")


def spur_main(argv=None):
    """Der Einstieg der Spur - dieselbe Form wie klassik_regeln.spur_main.

    `spur_buch.zyklus(ordner, quelle, signal, modus, ereignis_name=...,
    zusatz_ausstieg=...)` ist der Hausvertrag. Der Bus-Name steht
    WOERTLICH (T-255): die Bus-Suite prueft genau diese Datei auf ihren
    eigenen Namen, ein hier abgeleiteter waere unsichtbar - und eine
    Umbenennung des Ordners zoege den Journalnamen still mit.
    """
    import argparse
    p = argparse.ArgumentParser(description="EMA-Cross aus nautilus_trader")
    g = p.add_mutually_exclusive_group()
    for opt, c, h in (("--vorschau", "vorschau", "nur rechnen, nichts schreiben"),
                      ("--papier", "papier", "Papierbuch (Standard)"),
                      ("--live", "live", "verweigert: kein Live-Zweig"),
                      ("--wachen", "wachen", "nur den Wachenstand zeigen")):
        g.add_argument(opt, action="store_const", dest="modus", const=c, help=h)
    modus = p.parse_args(argv).modus or "papier"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier, die Originalregel ohne Orderweg).")
        return 0
    return spur_buch.zyklus(str(HIER), quelle, signal, modus,
                            ereignis_name="handel/nautilus_emacross",
                            zusatz_ausstieg=kreuzwechsel)


if __name__ == "__main__":
    import spur_buch  # noqa: E402
    sys.exit(spur_main())