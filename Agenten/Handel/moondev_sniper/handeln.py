"""Moon-Dev-Bot-Spur: neue Solana-Token-Launches als Papierbuch

WOHER DIE IDEE KOMMT
--------------------
Der Agent `sniper_agent` aus `Werkstatt/moon-dev-ai-agents` scannt neue
Solana-Token-Launches und zeigt sie an (mit Animation und Sound). Er faellt
KEIN eigenes Kauf- oder Verkaufsurteil - er ist ein Anzeige-Scanner. Seine
Datenquelle (`http://api.moondev.com:8000/files/new_token_addresses.csv`) ist
der tote Eigen-Server des Autors, nicht erreichbar. Deshalb hier:

  * **Daten** ueber die oeffentliche Pump.fun-API (`Handel/moondev_daten.py`):
    `/coins?sort=created_timestamp` liefert die neuesten Launches mit Alter,
    Marktwert und Liquiditaet - ohne Schluessel, ohne Wallet.
  * **Regel** deterministisch im Haus (siehe `signal()`): Ein NEUER Launch
    (jung, nicht gebannt/nsfw, Marktwert im Band) wird long gekauft. Das ist
    das gedankliche Vorbild des Bots: die frischesten Launches beobachten.
  * **Buch** ein Haus-Buch (`Handel/spur_buch.py`): Zustand, Journal, Kopie
    nach `Q:\\Handel_Journal\\moondev_sniper` (Bedingung 4), Ratsche, Stop/Ziel.

Kein Live-Zweig: die Fremd-Agenten handeln mit echten Schluesseln und einer
Wallet; diese Spur bucht Papier. Ein `--live` verweigert.

Instrumente sind DYNAMISCH: welche Mints gehandelt werden, entscheidet jeder
Zyklus neu (die neuesten Launches). Die Positionsliste im Zustand kennt die
offenen Mints - fuer sie holt `quelle()` weiterhin einen Kurs, damit Stop und
Ziel auch nach dem Ausscheiden aus der Neuesten-Liste geprueft werden.

Aufruf:
  python handeln.py --vorschau | --papier | --wachen
"""

import argparse
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, os.path.join(HANDEL, "scanner"), HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import spur_buch as buch  # noqa: E402
import moondev_daten as daten  # noqa: E402

# Test-Seam: None -> echter Abruf. Tests setzen ein Lambda.
quelle_override = None


def _alter_minuten(c):
    """Alter eines Tokens in Minuten oder None (Erstwerte fehlen zu oft)."""
    erstellt = daten.zahl(c.get("created_timestamp"))
    if not erstellt:
        return None
    return (time.time() * 1000.0 - erstellt) / 60000.0


def signal(d, w):
    """long bei einem NEUEN Launch - jung genug, nicht gesperrt, Wert im Band.

    Die Regel des Bots ist kein Urteil (er zeigt nur an), deshalb liegt sie
    hier: ein Launch ist einen Blick wert, wenn er frisch ist (unter
    `max_alter_minuten`), nicht gebannt oder nsfw ist und seine
    Marktkapitalisierung im Band `marktkap_band_usd` liegt. Genau die ruft
    `quelle()` als Kandidaten auf.
    """
    # Das Gate liegt in quelle() (nur Kandidaten kommen hier an); signal() kennt
    # die Metadaten als vorberechnete Felder, ein vorhandener Eintrag heisst:
    # Kandidat. Der Einstieg trifft nur, wenn das Alter noch frisch genug ist.
    if not d.get("mint"):
        return None
    alter = daten.zahl(d.get("alter_minuten"))
    if alter is None or alter > float(w.get("max_alter_minuten", 60.0)):
        return None
    mk = daten.zahl(d.get("market_cap_usd"))
    lo, hi = (w.get("marktkap_band_usd") or [0.0, 1e18])
    lo = float(lo or 0.0)
    hi = float(hi or 1e18)
    if mk is None or not (lo <= mk <= hi):
        return None
    if not daten.zahl(d.get("kurs")):
        return None
    return "long"


def quelle(w):
    """Die neuesten Launches plus Kurse fuer alle gehaltenen Positionen.

    Liefert (daten, kurse, fehler). Nur Kandidaten (jung, nicht gebannt/nsfw,
    Marktwert im Band, Preis vorhanden) landen in `daten` - das sind die
    moeglichen Einstiege. `kurse` enthaelt zusaetzlich die offenen Positionen
    (damit Stop/Ziel weiter laufen), selbst wenn ihr Mint die Neuesten-Liste
    verlassen hat.

    Rate-Limit: swap-api.pump.fun deckelt hart (HTTP 429). Fuer ALLE 40
    Kandidaten einen Preis zu holen wuerde den Deckel reissen und nichts
    mehr liefern. Einstiege koennen ohnehin nur die `max_offene_positionen`
    juengsten sein (das Buch ist danach voll) - genau fuer die wird der
    Preis geholt, plus fuer die gehaltenen Positionen.
    """
    fehler = []
    try:
        roh = daten.pump_neue_token(int(w.get("abruf_grenze", 40)))
    except Exception as e:                                     # noqa: BLE001
        return {}, {}, ["Pump.fun: %s" % str(e)[:120]]
    if not roh:
        return {}, {}, ["Pump.fun: leere Antwort"]

    grenze = float(w.get("max_alter_minuten", 60.0))
    lo, hi = (w.get("marktkap_band_usd") or [0.0, 1e18])
    lo, hi = float(lo or 0.0), float(hi or 1e18)

    # Kandidaten filtern und nach Alter sortieren (juengste zuerst) - das
    # sind die potenziellen Einstiege dieses Zyklus.
    kandidaten = []
    for c in roh:
        if c.get("is_banned") or c.get("nsfw"):
            continue
        alter = _alter_minuten(c)
        if alter is None or alter > grenze:
            continue
        mk = daten.zahl(c.get("market_cap_usd"))
        if mk is None or not (lo <= mk <= hi):
            continue
        if not c.get("mint"):
            continue
        kandidaten.append((alter, c))
    kandidaten.sort(key=lambda x: x[0])

    # Nur die max_offene juengsten Kandidaten bekommen einen Preis - der
    # restliche Zyklus kann ohnehin nicht mehr oeffnen (Buch voll).
    aus, kurse = {}, {}
    anzahl = int(w.get("max_offene_positionen", 3))
    for _, c in kandidaten[:anzahl]:
        mint = c["mint"]
        try:
            preis = daten.pump_letzter_preis(mint)
        except Exception as e:                                 # noqa: BLE001
            # Ein einzelner Kursabruf darf den Zyklus nicht kippen (22.09.2026:
            # Verbindungsabbruch -> Rueckgabe 1, der ganze Lauf fiel aus).
            fehler.append("Preis %s: %s" % (mint[:8], str(e)[:80]))
            continue
        if not preis:
            continue
        alter = _alter_minuten(c)
        aus[mint] = {"mint": mint, "symbol": c.get("symbol"),
                     "market_cap_usd": daten.zahl(c.get("market_cap_usd")),
                     "alter_minuten": round(alter, 1), "kurs": preis}
        kurse[mint] = preis

    # Offene Positionen brauchen weiter einen Kurs, auch wenn der Mint nicht
    # mehr in der Neuesten-Liste auftaucht.
    try:
        z = buch.lade_zustand(buch.pfade(HIER)[1])
    except Exception:                                          # noqa: BLE001
        z = {"positionen": []}
    for p in z.get("positionen", []):
        inst = p.get("inst")
        if not inst or inst in kurse:
            continue
        try:
            preis = daten.pump_letzter_preis(inst)
        except Exception as e:                                 # noqa: BLE001
            # Wie oben: ein Kursausfall wird gemeldet, nicht geworfen.
            fehler.append("Preis %s: %s" % (str(inst)[:8], str(e)[:80]))
            continue
        if preis:
            kurse[inst] = preis

    return aus, kurse, fehler


def daten_holen(w):
    """quelle() mit Test-Seam: Tests setzen `quelle_override`."""
    if quelle_override:
        return quelle_override(w)
    return quelle(w)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau", dest="modus")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier). Der Fremd-Agent handelt mit echten Schluesseln und "
              "einer Wallet - dieser Haus-Lauf bucht nur Papier.")
        return 0
    return buch.zyklus(HIER, daten_holen, signal, a.modus,
                       "handel/moondev_sniper")


if __name__ == "__main__":
    raise SystemExit(main())