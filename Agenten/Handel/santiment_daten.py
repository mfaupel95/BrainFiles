"""Santiment SanAPI (GraphQL) - On-Chain-, Social- und Dev-Metriken, lesend.

WOZU
----
Santiment liefert ueber EINEN GraphQL-Endpunkt mehr als 1.000 Metriken fuer
2.800+ Coins (aktive Adressen, MVRV, Exchange-Zu-/Abfluesse, Social Volume,
Dev-Aktivitaet). Fuer die Handelsspuren ist das die Datenquelle, die unser
eigener Stack nicht hat und die auch nicht aus OKX-Kerzen nachbaubar ist.

HERKUNFT DES WISSENS
--------------------
`Werkstatt/Repos/santiment` (Fork von `api-evangelist/santiment`, reine
Dokumentation + vollstaendiges GraphQL-Schema, 83 KB). Das Schema ist die
Wahrheit ueber Feldnamen - vor jeder neuen Abfrage dort nachsehen statt raten.

AM 16.09.2026 LIVE GEMESSEN
---------------------------
- Der Endpunkt antwortet **ohne Schluessel** (Stufe `SANAPI FREE`): Schema,
  `allProjects`, `getTrendingWords` und `getMetric` mit
  `daily_active_addresses` kamen mit HTTP 200 und echten Werten.
- Die Schranke ist **pro Metrik** und wird von der API selbst genannt, z. B.
  `social_volume_total`: erlaubt ist anonym nur `from` 2025-09-16 bis `to`
  2026-08-17 - also rund einen Monat Rueckstand. `erlaubtes_fenster()` holt
  diese Grenze genau so ab, statt sie zu raten.
- Ein Schluessel (kostenloses Konto) hebt die Grenzen; er wird **nicht** hier
  abgelegt, sondern als Benutzervariable `SANTIMENT_API_KEY` gesetzt und aus
  der Registry gelesen (Muster `melder.py`). Fehlt er, laeuft alles anonym
  weiter - nur mit den kleineren Fenstern.

Nichts hier schreibt: nur POST an den Endpunkt, keine Mutation, kein Handel.

Aufruf (aus dem Handel-Ordner):
    python santiment_daten.py --probe                       # was geht gerade?
    python santiment_daten.py --fenster social_volume_total
    python santiment_daten.py --metrik daily_active_addresses --slug bitcoin \\
        --von 2026-09-01 --bis 2026-09-08
    python santiment_daten.py --woerter --von 2026-09-13 --bis 2026-09-15
    python santiment_daten.py --projekte 5
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

ENDPUNKT = "https://api.santiment.net/graphql"
ZEITLIMIT = 30


class SantimentFehler(RuntimeError):
    """Antwort mit `errors` - die Meldung der API ist der Inhalt, nicht Rauschen."""


def schluessel():
    """`SANTIMENT_API_KEY` aus HKCU\\Environment (wie melder.py), sonst aus der
    Prozessumgebung. Der Wert wird nie ausgegeben."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            wert, _ = winreg.QueryValueEx(k, "SANTIMENT_API_KEY")
            if wert:
                return wert.strip()
    except OSError:
        pass
    import os
    return (os.environ.get("SANTIMENT_API_KEY") or "").strip()


def graphql(query, variablen=None, zeitlimit=ZEITLIMIT):
    """Ein POST an SanAPI. Gibt `data` zurueck, wirft bei `errors`."""
    rumpf = {"query": query}
    if variablen:
        rumpf["variables"] = variablen
    kopf = {"Content-Type": "application/json",
            "User-Agent": "BrainFiles-Santiment/1.0"}
    k = schluessel()
    if k:
        kopf["Authorization"] = "Apikey " + k
    anfrage = urllib.request.Request(ENDPUNKT, data=json.dumps(rumpf).encode("utf-8"),
                                     headers=kopf, method="POST")
    try:
        with urllib.request.urlopen(anfrage, timeout=zeitlimit) as r:
            antwort = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SantimentFehler("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))
    except urllib.error.URLError as e:
        raise SantimentFehler("Endpunkt nicht erreichbar: %s" % e.reason)

    if antwort.get("errors"):
        raise SantimentFehler(antwort["errors"][0].get("message", "unbekannter Fehler"))
    if "data" not in antwort:
        raise SantimentFehler("Antwort ohne data-Feld: %s" % str(antwort)[:200])
    return antwort["data"]


# --- Abfragen ---------------------------------------------------------------

def projekte(seite=1, menge=50):
    """(slug, name, ticker, marketcapUsd) - Discovery, laeuft anonym."""
    d = graphql("query($p: Int!, $m: Int!) { allProjects(page: $p, pageSize: $m) "
                "{ slug name ticker marketcapUsd } }", {"p": seite, "m": menge})
    return [(x["slug"], x["name"], x.get("ticker"), x.get("marketcapUsd"))
            for x in d["allProjects"]]


def projekt(slug):
    d = graphql("query($s: String!) { projectBySlug(slug: $s) "
                "{ slug name ticker marketcapUsd priceUsd } }", {"s": slug})
    return d["projectBySlug"]


def metrik(metric, slug, von, bis, interval="1d"):
    """Zeitreihe einer Metrik -> Liste (datetime, value). Leere Reihe = []."""
    d = graphql("query($m: String!, $s: String!, $v: DateTime!, $b: DateTime!, $i: interval!)"
                " { getMetric(metric: $m) { timeseriesData(slug: $s, from: $v, to: $b,"
                " interval: $i) { datetime value } } }",
                {"m": metric, "s": slug, "v": von, "b": bis, "i": interval})
    reihe = (d.get("getMetric") or {}).get("timeseriesData") or []
    return [(p["datetime"], p.get("value")) for p in reihe]


def erlaubtes_fenster(metric, slug="bitcoin"):
    """Was erlaubt die aktuelle Stufe fuer diese Metrik?

    Die API nennt die Grenze selbst, wenn ein Fenster zu weit reicht:
        Both `from` and `to` parameters are outside the allowed interval …
          - `from` - 2025-09-16 15:03:11.225510Z
          - `to`   - 2026-08-17 15:03:11.225510Z
    Genau diese Zeilen werden gelesen - geraten wird nichts.
    """
    # Zwei VERSCHIEDENE zukuenftige Zeitpunkte: mit from == to antwortet die API
    # zuerst "must be after the from datetime" und sagt nichts ueber die Grenze.
    weit_von, weit_bis = "2099-01-01T00:00:00Z", "2099-01-02T00:00:00Z"
    try:
        metrik(metric, slug, weit_von, weit_bis)
    except SantimentFehler as e:
        text = str(e)
        if "allowed time restrictions" not in text.lower():
            return None, text
        grenzen = {}
        for zeile in text.splitlines():
            z = zeile.strip().lstrip("-").strip()
            for name in ("from", "to"):
                marke = "`%s` -" % name
                if z.startswith(marke):
                    grenzen[name] = z[len(marke):].strip()
        if "from" in grenzen and "to" in grenzen:
            return (grenzen["from"], grenzen["to"]), None
        return None, text
    return (None, None), "Kein Fehler - das Fenster ist offen (laengerer Schluessel aktiv?)"


def trendende_woerter(von, bis, size=10):
    d = graphql("query($v: DateTime!, $b: DateTime!, $n: Int!) { getTrendingWords("
                "size: $n, from: $v, to: $b, interval: \"1d\") "
                "{ topWords { word score } } }", {"v": von, "b": bis, "n": size})
    # Die API liefert je Zeit-Eimer eine eigene Liste: bei zwei Tagen und size=10
    # kommen also bis zu 20 Woerter zurueck, nicht 10.
    reihen = d.get("getTrendingWords") or []
    return [(w["word"], round(w["score"], 1)) for r in reihen for w in r.get("topWords", [])]


# --- Selbstpruefung ---------------------------------------------------------

def probe():
    """Live pruefen, was ohne Schluessel geht. Gibt 0 zurueck, wenn der Zugang steht."""
    k = schluessel()
    print("Santiment SanAPI - Probe %s" % ("mit Schluessel" if k else "anonym (kein Schluessel gesetzt)"))
    ok = 0

    try:
        d = graphql("{ __schema { queryType { name } } }")
        print("  [1] Endpunkt erreichbar, Wurzeltyp %s" % d["__schema"]["queryType"]["name"])
        ok += 1
    except SantimentFehler as e:
        print("  [1] NICHT erreichbar: %s" % e)

    try:
        p = projekte(1, 3)
        print("  [2] Projekt-Discovery: %d Treffer, z. B. %s"
              % (len(p), ", ".join(x[0] for x in p)))
        ok += 1
    except SantimentFehler as e:
        print("  [2] Discovery fehlgeschlagen: %s" % e)

    try:
        reihe = metrik("daily_active_addresses", "bitcoin",
                       "2026-09-01T00:00:00Z", "2026-09-08T00:00:00Z")
        print("  [3] daily_active_addresses/bitcoin: %d Punkte, letzter %s"
              % (len(reihe), reihe[-1] if reihe else "-"))
        ok += 1 if reihe else 0
        if not reihe:
            print("      leere Reihe - die Metrik liegt ausserhalb des erlaubten Fensters")
    except SantimentFehler as e:
        print("  [3] Metrik fehlgeschlagen: %s" % str(e)[:200])

    fenster, fehler = erlaubtes_fenster("social_volume_total")
    if fenster and fenster[0]:
        print("  [4] social_volume_total erlaubt: %s bis %s" % fenster)
        ok += 1
    elif fenster == (None, None):
        print("  [4] social_volume_total: kein Fenster-Fehler - offenbar volle Tiefe")
        ok += 1
    else:
        print("  [4] Fenster nicht ablesbar: %s" % str(fehler)[:160])

    try:
        w = trendende_woerter("2026-09-13T00:00:00Z", "2026-09-15T00:00:00Z", 5)
        print("  [5] Trendwoerter: %s" % ", ".join(x[0] for x in w))
        ok += 1 if w else 0
    except SantimentFehler as e:
        print("  [5] Trendwoerter fehlgeschlagen: %s" % str(e)[:160])

    print("  Ergebnis: %d von 5 Abfragen beantwortet." % ok)
    return 0 if ok >= 3 else 1


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--probe", action="store_true", help="lebende Selbstpruefung")
    p.add_argument("--metrik", metavar="NAME", help="z. B. daily_active_addresses")
    p.add_argument("--slug", default="bitcoin")
    p.add_argument("--von", default=None, help="ISO, z. B. 2026-09-01T00:00:00Z")
    p.add_argument("--bis", default=None)
    p.add_argument("--interval", default="1d", choices=("1m", "5m", "15m", "1h", "4h", "1d", "7d"))
    p.add_argument("--woerter", action="store_true", help="Trendwoerter statt Metrik")
    p.add_argument("--fenster", metavar="METRIK", help="erlaubtes Zeitfenster abfragen")
    p.add_argument("--projekte", type=int, metavar="N", help="erste N Projekte")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.probe:
        return probe()
    if a.fenster:
        fenster, fehler = erlaubtes_fenster(a.fenster, a.slug)
        if fenster and fenster[0]:
            print("%s erlaubt: %s bis %s" % (a.fenster, fenster[0], fenster[1]))
        else:
            print("%s: %s" % (a.fenster, fehler))
        return 0
    if a.projekte:
        for slug, name, ticker, mc in projekte(1, a.projekte):
            print("%-22s %-28s %-8s %s" % (slug, name[:28], ticker or "-",
                                           ("%.0f Mio" % (mc / 1e6)) if mc else "-"))
        return 0
    if a.woerter:
        if not (a.von and a.bis):
            p.error("--woerter braucht --von und --bis")
        for wort, score in trendende_woerter(a.von, a.bis):
            print("%-24s %8.1f" % (wort, score))
        return 0
    if a.metrik:
        if not (a.von and a.bis):
            p.error("--metrik braucht --von und --bis")
        for ts, wert in metrik(a.metrik, a.slug, a.von, a.bis, a.interval):
            print("%s  %s" % (ts, wert))
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
