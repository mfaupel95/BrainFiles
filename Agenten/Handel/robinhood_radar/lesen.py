"""Nur lesender Zugang zur Datenbank des FOMO-Robinhood-Radars.

Der Radar (`Werkstatt/fomo-robinhood-radar`, Fremd-Repo) SAMMELT; diese
Spur LIEST. Es gibt genau einen Zugang, und der kann nicht schreiben:

  * Die Datenbank wird mit `mode=ro` geoeffnet (SQLite verweigert dann jedes
    Schreiben, auch wenn jemand es versucht).
  * Vor jedem Aufruf wird geprueft, dass die Anweisung mit SELECT/WITH/PRAGMA
    beginnt. Ein Wachhund in Python, weil `mode=ro` allein nicht verhindert,
    dass ein spaeterer Bearbeiter hier ein INSERT einbaut.

Kein `subprocess`, kein Netz, kein Radar-CLI: das Sammeln macht der Radar
(Agenten/Routinen/radar-sammeln.ps1 bzw. der Hermes-Cron `radar-sammler`),
diese Spur rechnet nur. Damit ist die Spur offline testbar und die Datenquelle
als Naht austauschbar (`FOMO_RADAR_DB` in der Umgebung).

Datenherkunft (gemessen 22.09.2026 am echten Bestand):
  traders  147 Zeilen, Spalten u. a. address, chain, score (0-100),
           status (active/tracking/dropped), win_rate, median_buy_usd
  trades    65 Zeilen, Spalten address, mint, side (buy/sell), token_amount,
           usd_value, ts (unix), chain
"""

from __future__ import annotations

import os
import sqlite3

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(HIER)))   # BrainFiles
RADAR_DB = os.path.join(WURZEL, "Werkstatt", "fomo-robinhood-radar",
                        "fomo_agent.db")

ERLAUBTE_ANFAENGE = ("select", "with", "pragma")


class DatenbankFehlt(RuntimeError):
    """Die Radar-Datenbank ist nicht da - dann sammelt der Radar noch nicht."""


def datenbank_pfad() -> str:
    """Pfad aus der Umgebung (Tests/andere Ablage), sonst der Hauspfad."""
    return os.environ.get("FOMO_RADAR_DB") or RADAR_DB


def verbinde(pfad: str | None = None) -> sqlite3.Connection:
    p = pfad or datenbank_pfad()
    if not os.path.exists(p):
        raise DatenbankFehlt(
            "Radar-Datenbank fehlt: %s (der Radar muss erst sammeln: "
            "fomo-radar discover --trenches && fomo-radar track)" % p)
    con = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
    con.row_factory = sqlite3.Row
    return con


def anweisung(con: sqlite3.Connection, sql: str, args: tuple = ()):
    """Fuehrt NUR lesende Anweisungen aus - alles andere ist ein Programmierfehler."""
    anfang = sql.strip().split()[0].lower() if sql.strip() else ""
    if anfang not in ERLAUBTE_ANFAENGE:
        raise RuntimeError("lesen.py ist nur lesend, abgelehnt: %.40s..." % sql.strip())
    return con.execute(sql, args)


def kaeufe(con, seit_ts: float, chain: str = "robinhood") -> list[dict]:
    """Alle Kaeufe im Fenster, mit dem Score des Traders (falls vorhanden).

    Rueckgabe je Zeile: wallet, mint, usd, menge, ts, sig, score, status.
    Der Score kann None sein - ein unbewerteter Trader ist kein guter Trader,
    er ist ein unbekannter (siehe wachen.json: score fehlt = zaehlt nicht mit).
    """
    rows = anweisung(
        con,
        """
        SELECT t.address AS wallet, t.mint AS mint, t.usd_value AS usd,
               t.token_amount AS menge, t.ts AS ts, t.sig AS sig,
               tr.score AS score, tr.status AS status
          FROM trades t
          LEFT JOIN traders tr ON tr.address = t.address
         WHERE t.side = 'buy' AND t.chain = ? AND t.ts >= ?
               AND t.token_amount > 0 AND t.usd_value > 0
         ORDER BY t.ts ASC
        """,
        (chain, seit_ts),
    )
    return [dict(r) for r in rows]


def verkaufsdruck(con, seit_ts: float, chain: str = "robinhood") -> dict:
    """Zu jedem Token: wie viel USD die bewertete Kohorte in diesem Fenster verkauft hat.

    Eine Kopie kauft, was die Guten kaufen - verkaufen dieselben Guten im selben
    Fenster mehr, als sie kauften, ist das kein Kaufsignal mehr, sondern ein
    Ausstieg. Ohne diese Zahl wuerde die Spur in einen Abverkauf hineinkaufen.
    """
    rows = anweisung(
        con,
        """
        SELECT t.mint AS mint, SUM(t.usd_value) AS usd, COUNT(*) AS n
          FROM trades t
         WHERE t.side = 'sell' AND t.chain = ? AND t.ts >= ? AND t.usd_value > 0
         GROUP BY t.mint
        """,
        (chain, seit_ts),
    )
    return {r["mint"]: float(r["usd"] or 0.0) for r in rows}


def letzte_beobachtung(con, mint: str, chain: str = "robinhood") -> tuple:
    """Der JUENGSTE beobachtete Handel dieses Tokens: (preis, ts), sonst (0, 0).

    Wofuer: eine OFFENE Position braucht einen Kurs, sonst prueft das Buch
    gar nichts (T-299). Der Radar sammelt jeden Handel dieser Kette - auch
    von fremden Wallets -, also ist das der beste Kurs, den das Haus hat.
    Das Alter entscheidet: `handeln.raeume_ohne_kurs` schliesst eine Position,
    deren letzte Beobachtung zu alt ist. Ohne diese Funktion blieb die
    Position monatelang stehen und blockierte einen der drei Plaetze.
    """
    row = anweisung(
        con,
        """
        SELECT usd_value, token_amount, ts FROM trades
         WHERE mint = ? AND chain = ? AND token_amount > 0 AND usd_value > 0
         ORDER BY ts DESC LIMIT 1
        """,
        (mint, chain),
    ).fetchone()
    if not row or not row["ts"] or not row["token_amount"]:
        return 0.0, 0.0
    return float(row["usd_value"]) / float(row["token_amount"]), float(row["ts"])


def juengster_kauf(con, chain: str = "robinhood") -> float:
    """Der neueste Kauf-Zeitstempel ueberhaupt - das Alter der Sammlung."""
    row = anweisung(
        con,
        "SELECT MAX(ts) AS ts FROM trades WHERE side = 'buy' AND chain = ?",
        (chain,),
    ).fetchone()
    return float(row["ts"]) if row and row["ts"] is not None else 0.0


def alle_fills(con, seit_ts: float = 0.0, chain: str = "robinhood") -> list[dict]:
    """ALLE beobachteten Fuellungen (Kauf UND Verkauf) im Fenster, nach Zeit.

    Fuer die Nachlauf-Messung (T-268): die Spur bucht hinter dem Vorbild, und
    wie weit der Kurs in der Zwischenzeit weg ist, laesst sich nur aus der
    eigenen Sammlung ablesen - naemlich am NAECHSTEN beobachteten Handel
    desselben Tokens. Rueckgabe je Zeile: mint, wallet, seite, preis, ts.
    """
    rows = anweisung(
        con,
        """
        SELECT t.mint AS mint, t.address AS wallet, t.side AS seite,
               t.usd_value AS usd, t.token_amount AS menge, t.ts AS ts
          FROM trades t
         WHERE t.chain = ? AND t.ts >= ?
               AND t.token_amount > 0 AND t.usd_value > 0
         ORDER BY t.mint ASC, t.ts ASC
        """,
        (chain, seit_ts),
    )
    aus = []
    for r in rows:
        d = dict(r)
        d["preis"] = float(d["usd"]) / float(d["menge"])
        aus.append(d)
    return aus