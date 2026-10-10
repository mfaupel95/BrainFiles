"""Orchestrator: eine Woche Selbstverbesserung fuer Spur 2 (XPERP).

Kette: Universum + Kerzen + Funding aus dem Cache (auf Wunsch vorher
aufgefrischt) -> Merkmals-Cache -> Koordinatenabstieg -> Sieb a-e -> Holdout ->
Bericht und Vorschlagsartefakte.

Jeder Lauf endet mit einem Ordner unter ``berichte/<datum>-spur2/``:
  * Vorschlag:      bericht.md, wachen.neu.json, commit.txt
  * Kein Vorschlag: bericht.md (mit Grund)
  * Abbruch:        bericht.md (mit Grund), nie commit.txt - ein Abbruch kann
                    so nie als Vorschlag bei Max landen.
Angewendet wird nichts: das macht anwenden.anwenden() nach Max' /ja.

Nur Standardbibliothek.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
for _p in (WURZEL, WURZEL.parent / "xperp", WURZEL.parent / "scanner"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import vorschlag  # noqa: E402
import xperp_kerzen as xk  # noqa: E402
import xperp_merkmale as xm  # noqa: E402
import xperp_ruecktest as rt  # noqa: E402
import xperp_suche as xs  # noqa: E402

BERICHTE = WURZEL / "berichte"
MERKMALE = WURZEL / "xperp_merkmale.json"
HOLDOUT_ZAEHLER = WURZEL / "xperp_holdout_nutzung.json"
MIN_INSTRUMENTE = 3

NICHT_GEPRUEFT = [
    "- Wenige Testfenster; Auswahl und Siebregeln a-e nutzen dieselben Fenster "
    "(nur der Holdout ist unabhaengig).",
    "- Nur Trend-Modus, ohne LLM-Filter, CVD-4h neutral - der Vorschlag gilt "
    "fuer die Strategie OHNE LLM-Filter.",
    "- Zum Fensterende offene Positionen werden nicht bewertet.",
    "- Bestanden heisst: der Vertrag aus a-e und Holdout ist erfuellt, nicht, "
    "dass die Wache live besser ist.",
]


# --- Hilfen mit Netz/Platte (Tests ersetzen sie) ------------------------------

def _konf():
    konfig = json.loads((WURZEL / "konfig.json").read_text("utf-8"))
    spuren = json.loads((WURZEL / "spuren.json").read_text("utf-8"))
    return konfig["spur2"], spuren["spur2"]


def _daten_laden(universum, tage, kerzen_holen, cache_dir):
    """(k4, k1h, k1d, saetze, fehlt): je Instrument aus dem Cache, auf Wunsch
    vorher aufgefrischt (best effort - ein Abruffehler faellt auf den Cache
    zurueck). ``fehlt`` nennt Instrumente ohne vollstaendigen Cache."""
    seiten_1h = -(-tage * 24 // 100)
    seiten_4h = -(-tage * 6 // 100)
    seiten_fund = -(-tage * 24 // 100) + 1
    k4, k1h, k1d, saetze, fehlt = {}, {}, {}, {}, []
    for x in universum:
        iid = x["instId"]
        if kerzen_holen:
            try:
                xk.hole(iid, "1H", seiten=seiten_1h, cache_dir=cache_dir)
                xk.hole(iid, "4H", seiten=seiten_4h, cache_dir=cache_dir)
                xk.hole(iid, "1D", cache_dir=cache_dir)
                xk.hole_funding(iid, seiten=seiten_fund, cache_dir=cache_dir)
            except Exception as e:  # noqa: BLE001
                print("  Abruf %s: %s - nehme Cache" % (iid, e),
                      file=sys.stderr)
        a, _ = xk.laden(iid, "4H", cache_dir)
        b, _ = xk.laden(iid, "1H", cache_dir)
        c, _ = xk.laden(iid, "1D", cache_dir)
        s, _ = xk.laden_funding(iid, cache_dir)
        if not (a and b and c and s):
            fehlt.append(iid)
            continue
        k4[iid], k1h[iid], k1d[iid], saetze[iid] = a, b, c, s
    return k4, k1h, k1d, saetze, fehlt


def _instrumente():
    """Instrumentenstamm je Basiswert (ein OKX-Abruf)."""
    return {i["instId"].split("-")[0]: i
            for i in rt.okxf.instrumente(kategorie=None)}


def mit_funding_ab(universum, saetze_je_inst, start_ms):
    """(bleibt, fehlt): Instrumente, deren Funding-Historie spaetestens bei
    ``start_ms`` beginnt, und die Namen der uebrigen. OKX liefert Funding nur
    ca. 3 Monate zurueck; simuliert die Engine ein Instrument vor seinem
    ersten Satz, wirft sie eine FundingLuecke (nie mit 0.0 aufgefuellt) - der
    Lauf bricht dann ab. Besser: solche Instrumente gar nicht erst nehmen und
    im Bericht benennen."""
    bleibt, fehlt = [], []
    for x in universum:
        s = saetze_je_inst.get(x["instId"]) or []
        if s and s[0][0] <= start_ms:
            bleibt.append(x)
        else:
            fehlt.append(x["instId"])
    return bleibt, fehlt


# --- Holdout-Zaehler ------------------------------------------------------------

def zaehler_lesen(pfad):
    try:
        return int(json.loads(Path(pfad).read_text("utf-8"))["nutzungen"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def zaehler_erhoehen(pfad, datum):
    n = zaehler_lesen(pfad) + 1
    Path(pfad).write_text(json.dumps({"nutzungen": n, "zuletzt": datum}),
                          "utf-8")
    return n


# --- Berichte -------------------------------------------------------------------

def _tag(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d")


def _tabelle(kopf, zeilen):
    aus = ["| " + " | ".join(kopf) + " |",
           "|" + "|".join("---" for _ in kopf) + "|"]
    aus += ["| " + " | ".join(str(z) for z in zeile) + " |" for zeile in zeilen]
    return aus


def bericht_text(ctx, res):
    z = ["# Verbesserer Spur 2 (XPERP) - %s" % ctx["datum"], "",
         "**Ergebnis:** %s" % res["grund"], ""]
    zeigen = res["kandidat"] or res["fast_kandidat"]
    if zeigen:
        titel = ("Geaenderte Parameter" if res["kandidat"]
                 else "Fast-Kandidat (Parameter, NICHT vorgeschlagen)")
        z += ["## " + titel, ""]
        z += _tabelle(["Schluessel", "Basis", "Kandidat"],
                      [(k, res["basis_werte"][k], zeigen[k])
                       for k in sorted(xs.SCHRITT)
                       if res["basis_werte"][k] != zeigen[k]])
        z += [""]

    z += ["## Fenster", "",
          "%d Testfenster a %d Tage, Schritt %d Tage; Holdout: %s bis %s." % (
              len(ctx["fenster"]), ctx["konf"]["test_tage"],
              ctx["konf"]["schritt_tage"], _tag(ctx["holdout"][0]),
              _tag(ctx["holdout"][1])), ""]
    kand_fenster = res["kandidat_ev"]["fenster"]
    z += _tabelle(
        ["Fenster", "von", "bis", "Basis je Runde", "n", "Kandidat je Runde",
         "n"],
        [(i + 1, _tag(v), _tag(b), "%.4f" % bf["je_runde"], bf["n"],
          "%.4f" % kf["je_runde"], kf["n"])
         for i, ((v, b), bf, kf) in enumerate(
             zip(ctx["fenster"], res["basis_ev"]["fenster"], kand_fenster))])
    z += [""]

    if res["regeln"]:
        z += ["## Siebregeln", ""]
        z += _tabelle(["Regel", "Pruefung", "Kandidat", "Soll", "Ergebnis"],
                      [(r["regel"], r["text"], r["ist"], r["soll"],
                        "bestanden" if r["ok"] else "NICHT bestanden")
                       for r in res["regeln"]])
        z += [""]

    z += ["## Holdout", ""]
    if res["holdout_basis"] is None:
        z += ["Nicht bewertet (kein Kandidat hat das Sieb erreicht).", ""]
    else:
        hb, hk = res["holdout_basis"], res["holdout_kandidat"]
        z += _tabelle(["", "Runden", "je Runde", "Liquidationsanteil",
                       "Ruecklauf"],
                      [("Basis", hb["n"], "%.4f" % hb["je_runde"],
                        "%.1f %%" % (100 * hb["liquidationsanteil"]),
                        "%.2f" % hb["ruecklauf"]),
                       ("Kandidat", hk["n"], "%.4f" % hk["je_runde"],
                        "%.1f %%" % (100 * hk["liquidationsanteil"]),
                        "%.2f" % hk["ruecklauf"])])
        z += ["", "Mindestrunden im Holdout: %d." % ctx["konf"][
            "holdout_min_runden"], ""]

    z += ["Holdout-Nutzung: %d von %d" % (
        ctx["nutzungen"], ctx["konf"]["holdout_max_nutzungen"])]
    if ctx["nutzungen"] >= ctx["konf"]["holdout_max_nutzungen"]:
        z += ["", "**Der Holdout-Block gilt als verbraucht** - jede Auswertung "
              "gibt dem Vorschlagenden Information preis. Zaehler zuruecksetzen "
              "(Datei xperp_holdout_nutzung.json loeschen), wenn Max den Block "
              "freigibt."]
    z += ["", "## Nicht geprueft", ""] + NICHT_GEPRUEFT
    if ctx["hinweise"]:
        z += ["", "## Hinweise", ""] + ["- " + h for h in ctx["hinweise"]]
    z += [""]
    return "\n".join(z)


def commit_text(ctx, res, aenderungen):
    b, k = res["basis_ev"]["gesamt"], res["kandidat_ev"]["gesamt"]
    hb, hk = res["holdout_basis"], res["holdout_kandidat"]
    return "\n".join([
        "verbesserer: spur2 Parameter angepasst",
        "",
        "Walk-Forward (%d Fenster a %d Tage), Siebregeln a-e bestanden:" % (
            len(ctx["fenster"]), ctx["konf"]["test_tage"]),
        "OOS netto_gv_je_runde: %.4f -> %.4f" % (b["je_runde"], k["je_runde"]),
        "Holdout netto_gv_je_runde: %.4f -> %.4f (n=%d)" % (
            hb["je_runde"], hk["je_runde"], hk["n"]),
        "",
        "Geaenderte Schluessel: " + ", ".join(sorted(aenderungen)),
        "",
        "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>",
        ""])


def _kopf(ordner, titel, grund, zusatz=()):
    text = ["# Verbesserer Spur 2 (XPERP) - %s" % titel, "",
            "**Grund:** %s" % grund, ""] + list(zusatz) + [""]
    (ordner / "bericht.md").write_text("\n".join(text), "utf-8", newline="\n")


def _abbruch(ordner, grund, zusatz=()):
    print("ABBRUCH: %s" % grund, file=sys.stderr)
    _kopf(ordner, "ABBRUCH", grund, zusatz)
    return ordner, "abbruch"


def _ordner(berichte, datum):
    """Ordner des Tages; Reste eines frueheren Laufs weg, sonst wendet ein
    spaeteres /ja einen Mischstand an (wie lauf.py in Spur 1)."""
    ordner = Path(berichte) / ("%s-spur2" % datum)
    if ordner.exists():
        shutil.rmtree(ordner, ignore_errors=True)
        for rest in ordner.glob("*") if ordner.exists() else []:
            if rest.is_file():
                rest.unlink(missing_ok=True)
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


# --- Der Lauf -------------------------------------------------------------------

def einmal(*, kerzen_holen=True, jetzt=None, konf=None, spur=None,
           basis_w=None, wachen_pfad=None, berichte=BERICHTE, cache_dir=None,
           merkmale_pfad=MERKMALE, zaehler_pfad=HOLDOUT_ZAEHLER):
    """Eine Woche fuer Spur 2. Rueckgabe ``(ordner, status)`` mit status
    ``vorschlag`` | ``kein_vorschlag`` | ``abbruch``."""
    if konf is None or spur is None:
        konf, spur = _konf()
    wachen_pfad = Path(wachen_pfad or (WURZEL / spur["wachen"]).resolve())
    cache_dir = cache_dir or xk.CACHE
    jetzt = jetzt or datetime.now(timezone.utc)
    datum = jetzt.strftime("%Y-%m-%d")
    ordner = _ordner(berichte, datum)
    hinweise = []

    if kerzen_holen:
        try:
            xk.hole_universum(cache_dir)
        except Exception as e:  # noqa: BLE001
            print("  Universum-Abruf: %s - nehme Cache" % e, file=sys.stderr)
    universum = xk.laden_universum(cache_dir)
    if not universum:
        return _abbruch(ordner, "Kein Universum-Cache und kein Abruf moeglich "
                                "- OKX/Netz pruefen und den Lauf wiederholen.")

    k4, k1h, k1d, saetze, fehlt = _daten_laden(
        universum, konf["such_tage"] + rt.WARMUP_TAGE, kerzen_holen,
        cache_dir)
    if fehlt:
        hinweise.append("%d Instrument(e) ohne vollstaendigen Cache "
                        "ausgelassen: %s" % (len(fehlt), ", ".join(fehlt)))
    universum = [x for x in universum if x["instId"] in k4]
    if len(universum) < MIN_INSTRUMENTE:
        return _abbruch(ordner, "weniger als %d Instrumente mit vollstaendigem "
                                "Cache" % MIN_INSTRUMENTE, hinweise)

    try:
        instr_je_basis = _instrumente()
    except Exception as e:  # noqa: BLE001
        return _abbruch(ordner, "OKX-Instrumentenstamm nicht abrufbar: %s" % e,
                        hinweise)

    if basis_w is None:
        basis_w = rt.bot.wachen()
    with open(wachen_pfad, "r", encoding="utf-8", newline="") as f:
        alt_text = f.read()
    basis = xs.basis_werte(basis_w)
    grenzen = spur["aenderbar"]["wachen.json"]

    ende = max(k[-1][0] for k in k4.values())
    fenster, holdout_fenster = xs.fenster_grenzen(ende, konf)
    ctx = {"datum": datum, "konf": konf, "fenster": fenster,
           "holdout": holdout_fenster, "hinweise": hinweise, "nutzungen":
           zaehler_lesen(zaehler_pfad)}
    if len(fenster) < konf["overfit_min_fenster"]:
        res = {"kandidat": None, "fast_kandidat": None,
               "grund": "zu wenig Historie fuer %d Testfenster (vorhanden: %d)"
                        % (konf["overfit_min_fenster"], len(fenster))}
        _kopf(ordner, datum, res["grund"], hinweise)
        return ordner, "kein_vorschlag"

    universum, ohne_funding = mit_funding_ab(
        universum, saetze, ende - konf["such_tage"] * xs.TAG_MS)
    if ohne_funding:
        hinweise.append(
            "%d Instrument(e) ausgelassen, deren Funding-Historie erst nach "
            "dem Simulationsstart beginnt (OKX liefert nur ca. 3 Monate): %s%s"
            % (len(ohne_funding), ", ".join(ohne_funding[:10]),
               " ..." if len(ohne_funding) > 10 else ""))
    if len(universum) < MIN_INSTRUMENTE:
        return _abbruch(ordner, "weniger als %d Instrumente mit ausreichender "
                                "Funding-Historie" % MIN_INSTRUMENTE, hinweise)

    ctval = xm.ctval_je_inst(universum, instr_je_basis)
    matrix, _aus_cache = xm.hole_oder_baue(
        merkmale_pfad, universum, k4, k1d, ctval,
        xm.staende(fenster[0][0], holdout_fenster[1]))

    def simulieren(w, von, bis):
        return rt.simuliere(universum, k4, k1h, k1d, saetze, {},
                            instr_je_basis, w, von, bis, werte_cache=matrix)

    def bewerte(werte):
        return xs.bewerte_fenster(simulieren, {**basis_w, **werte}, fenster)

    def holdout(werte):
        return xs.kennzahlen(simulieren({**basis_w, **werte},
                                        *holdout_fenster))

    try:
        res = xs.entscheide(basis, bewerte, holdout, grenzen, konf)
    except rt.FundingLuecke as e:
        return _abbruch(ordner, "Funding-Luecke: %s" % e, hinweise)

    if res["holdout_basis"] is not None:
        ctx["nutzungen"] = zaehler_erhoehen(zaehler_pfad, datum)

    (ordner / "bericht.md").write_text(bericht_text(ctx, res), "utf-8",
                                       newline="\n")
    if res["kandidat"] is None:
        return ordner, "kein_vorschlag"

    aenderungen = {k: v for k, v in res["kandidat"].items()
                   if res["basis_werte"][k] != v}
    with open(ordner / "wachen.neu.json", "w", encoding="utf-8",
              newline="") as f:
        f.write(vorschlag.wachen_neu_text(alt_text, aenderungen))
    # Pruefsumme der Basis: anwenden.py verweigert, wenn die Wache sich seit
    # diesem Lauf (egal an welchem Schluessel) geaendert hat.
    (ordner / "basis.sha256").write_text(
        hashlib.sha256(alt_text.encode("utf-8")).hexdigest(), "utf-8",
        newline="\n")
    (ordner / "commit.txt").write_text(commit_text(ctx, res, aenderungen),
                                       "utf-8", newline="\n")
    return ordner, "vorschlag"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ohne-kerzen-abruf", action="store_true")
    a = p.parse_args()
    o, status = einmal(kerzen_holen=not a.ohne_kerzen_abruf)
    print("%s: %s" % (status, o))
    sys.exit(1 if status == "abbruch" else 0)
