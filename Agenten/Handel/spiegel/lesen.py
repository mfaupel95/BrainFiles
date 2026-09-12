"""Lesezugriff auf den OKX-Onchain-Feed - die Signalquelle der Spiegel-Spur.

Diese Datei ruft **nur lesende** Unterbefehle des OnchainOS-CLI. Es gibt hier
keinen Kauf, keinen Tausch, keine Signatur, keinen Brueckentausch. Wer das
aendern will, braucht einen anderen Plan: Der Schreibpfad liegt in
`onchainos swap` / `strategy` und gehoert nach `okx-dapp-discovery`, nicht in
eine Papierspur.

Was geliefert wird
------------------
  leaderboard(kette)          gemessene Wallets (PnL, Trefferquote, Trades)
  tracker(kette, art)         echte Trades dieser Wallets, Transaktionsebene
  signale(kette, art)         dieselben Trades, auf eine Form gebracht
  preise(punkte)              Kurse fuer offene Kopien (Stapelabfrage)
  risiko(token, kette)        Betrugsmerkmale vor dem Kauf

Befehle und Felder sind am 12.09.2026 gegen das echte CLI geprueft
(onchainos 4.5.2), nicht aus der Erinnerung geschrieben.
"""

import json
import os
import subprocess
import sys
import time

CLI = os.environ.get("ONCHAINOS_CLI", "onchainos")

# Unterbefehle, die Geld bewegen oder etwas unterschreiben. Sie werden hier
# verweigert, nicht nur "nicht benutzt": Die Spiegel-Spur ist papierfest, und
# dieser Schutz ist die Stelle, an der das durchgesetzt wird. Wer ihn entfernt,
# bricht spiegel.py beim Start (dort steht die Gegenprobe).
SCHREIBBEFEHLE = ("swap", "cross-chain", "strategy", "payment", "wallet",
                  "defi", "agent", "gateway")

# Kette -> chainIndex. Dieselbe Schreibweise nimmt das CLI auch als Namen an;
# die Zahl steht hier, weil die Stapelabfrage sie verlangt.
KETTEN = {"solana": "501", "base": "8453", "ethereum": "1", "bnb": "56",
          "xlayer": "196"}

# So viele Eintraege liefert das CLI je Abfrage zurueck (gemessen).
GRENZE_LEADERBOARD = 50
GRENZE_TRACKER = 100


class Lesefehler(RuntimeError):
    """Das CLI hat nicht geantwortet, was erwartet wurde."""


class Schreibversuch(RuntimeError):
    """Ein Schreib-Unterbefehl wurde angefordert. Diese Spur ist papierfest."""


def ruf(args, timeout=120):
    """Ein Leseaufruf. Rueckgabe: der Inhalt von data - oder Lesefehler.

    Jeder Schreib-Unterbefehl wird hier abgewiesen, bevor ein Prozess startet.
    """
    args = [str(a) for a in args]
    if not args:
        raise Lesefehler("leerer Aufruf")
    if args[0] in SCHREIBBEFEHLE:
        raise Schreibversuch("'%s' ist ein Schreibbefehl - diese Spur liest "
                            "nur." % args[0])
    try:
        p = subprocess.run([CLI] + list(args), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
    except FileNotFoundError as e:
        raise Lesefehler("onchainos nicht gefunden (%s)" % e) from e
    except subprocess.TimeoutExpired as e:
        raise Lesefehler("onchainos antwortet nicht innerhalb %d s" % timeout) from e
    roh = (p.stdout or "").strip()
    try:
        d = json.loads(roh)
    except ValueError as e:
        raise Lesefehler("keine JSON-Antwort (%s): %s" % (e, roh[:120])) from e
    if not d.get("ok"):
        raise Lesefehler("CLI-Fehler: %s" % str(d.get("error"))[:200])
    return d.get("data")


def leaderboard(kette, zeitfenster=4, sortierung=1):
    """Gemessene Wallets einer Kette.

    zeitfenster: 1 heute, 2 drei Tage, 3 sieben Tage, 4 ein Monat, 5 drei Monate
    sortierung:  1 PnL, 2 Trefferquote, 3 Trades, 4 Volumen, 5 ROI
    """
    d = ruf(["leaderboard", "list", "--chain", kette,
             "--time-frame", str(zeitfenster), "--sort-by", str(sortierung)])
    return _liste(d)


def tracker(kette, art="smart_money", trade_typ=1):
    """Echte Trades der vom CLI als smart_money/kol gefuehrten Wallets.

    Transaktionsebene: trade_typ 1 = Kaeufe, 2 = Verkaeufe, 0 = beides.
    Verkaeufe werden gebraucht, um zu sehen, wann ein Vorbild aussteigt -
    kopiert wird trotzdem nach eigener Mathematik (siehe wachen.json).
    """
    d = ruf(["tracker", "activities", "--tracker-type", art,
             "--chain", kette, "--trade-type", str(trade_typ)])
    if isinstance(d, dict):
        return d.get("trades") or []
    return _liste(d)


def signale(kette, art="smart_money"):
    """Tracker-Trades in einer Form, mit der das Buch arbeitet.

    Ein Signal ist ein Kauf. Preise sind Zeichenketten mit absurd vielen
    Stellen - deshalb hier einmal in float, damit das Buch damit rechnen kann.
    """
    aus = []
    for t in tracker(kette, art):
        try:
            preis = float(t["tokenPrice"])
        except (KeyError, TypeError, ValueError):
            continue
        if preis <= 0:
            continue
        marktkap = _zahl(t.get("marketCap"))
        zeit_ms = int(t.get("tradeTime") or 0)
        aus.append({
            "quelle": "tracker/%s" % art,
            "kette": kette,
            "wallet": t.get("walletAddress"),
            "token": t.get("tokenContractAddress"),
            "symbol": t.get("tokenSymbol") or "?",
            "preis": preis,
            "zeit_ms": zeit_ms,
            "alter_s": max(0.0, time.time() - zeit_ms / 1000) if zeit_ms else None,
            "marktkap_usd": marktkap,
            "quote": t.get("quoteTokenSymbol"),
            "tx": t.get("txHash"),
        })
    return aus


def preise(punkte, kette_vorgabe=None):
    """Kurse zu (kette, token)-Paaren. Rueckgabe: {(kette, token): float}.

    Stapelabfrage: das CLI nimmt 'chainIndex:adresse' durch Komma getrennt.
    """
    punkte = list(punkte)
    if not punkte:
        return {}
    marken = ",".join("%s:%s" % (_index(k, kette_vorgabe), a)
                      for k, a in punkte)
    args = ["market", "prices", "--tokens", marken]
    if kette_vorgabe:
        args += ["--chain", kette_vorgabe]
    d = ruf(args)
    aus = {}
    for e in _liste(d):
        kette = _kette_aus_index(e.get("chainIndex"))
        kurs = _zahl(e.get("price"))
        if kette and kurs:
            aus[(kette, e.get("tokenContractAddress"))] = kurs
    return aus


def preise_info(token, kette):
    """Tiefe und Kennzahlen eines Tokens - Liquiditaet, Marktkapitalisierung,
    Halter, Volumen. Grundlage der Kostenmessung."""
    d = ruf(["token", "price-info", "--address", token, "--chain", kette])
    if isinstance(d, list):
        return d[0] if d else {}
    return d or {}


def risiko(token, kette):
    """Betrugsmerkmale eines Tokens vor dem Kauf.

    Rueckgabe: die Stufe (z. B. 'safe', 'LOW') und die Merkmalsliste. Das CLI
    klassifiziert selbst ('action'); die Spur entscheidet nur, ob die Stufe
    unter der Grenze aus wachen.json liegt.
    """
    d = ruf(["security", "token-scan", "--tokens", "%s:%s" % (KETTEN[kette],
                                                              token),
             "--trade-direction", "buy"])
    if isinstance(d, dict):
        eintraege = d.get("tokens") or []
        stufe = d.get("combinedAction") or (eintraege[0].get("action")
                                            if eintraege else None)
    else:
        eintraege, stufe = _liste(d), None
    merkmale = sorted(k for k, v in (eintraege[0] if eintraege else {}).items()
                      if v is True and k.startswith("is"))
    return {"stufe": stufe, "merkmale": merkmale,
            "roh": eintraege[0] if eintraege else {}}


# --- Kleinkram --------------------------------------------------------------

def _liste(d):
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for schluessel in ("list", "rows", "data"):
            if isinstance(d.get(schluessel), list):
                return d[schluessel]
    return []


def _zahl(wert):
    try:
        return float(str(wert).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _kette_aus_index(index):
    for name, i in KETTEN.items():
        if str(index) == i:
            return name
    return None


def _index(kette, vorgabe=None):
    """Kettenname, Index oder Vorgabe -> chainIndex als Zeichenkette."""
    if kette in KETTEN:
        return KETTEN[kette]
    if kette is not None and str(kette).isdigit():
        return str(kette)
    if vorgabe in KETTEN:
        return KETTEN[vorgabe]
    return str(vorgabe)


def main():
    """Der Lagebericht: was der Feed gerade liefert. Nur lesend."""
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kette", default="solana")
    p.add_argument("--art", default="smart_money")
    a = p.parse_args()
    try:
        sig = signale(a.kette, a.art)
        rang = leaderboard(a.kette)
    except Lesefehler as e:
        print("Lese fehlgeschlagen: %s" % e)
        return 1
    print("%s: %d Signale, %d gemessene Wallets" % (a.kette, len(sig), len(rang)))
    for s in sig[:10]:
        print("  %-10s %-28s %s  MC %s USD  %s  vor %.0f s"
              % (s["symbol"][:10], (s["token"] or "")[:28], s["preis"],
                 "?" if s["marktkap_usd"] is None else "%.0f" % s["marktkap_usd"],
                 s["quelle"], s["alter_s"] or 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
