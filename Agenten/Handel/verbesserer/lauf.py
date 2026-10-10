"""Orchestrator: eine Woche Selbstverbesserung fuer eine Spur.

Kette fuer eine Spur:

  Kerzen auffrischen (best effort, Cache genuegt)
  -> auswerter.befund   Journal-Segmente + Befund-JSON in den Vorschlagsordner
  -> suche.suche         Basis auswerten, Nachbarschaft absteigen, Kandidat oder
                         None mit Grund
  -> vorschlag.baue / vorschlag.kein_vorschlag   Artefakte in den Ordner
  -> digest.erzeuge      woechentliche LLM-Annotation (bei modus "aus" leer)
  -> digest.annotiere_bericht / digest.haenge_lehren_an

Harter Abbruch (Rueckgabe None) nur, wenn nicht einmal ein Kerzen-Cache fuer
drei Instrumente vorliegt. Alles andere endet mit einem Ordner unter
``berichte/<datum>-<spur>/`` - zur Not nur mit einem kein-Vorschlag-Bericht.

Nur Standardbibliothek.
"""

import argparse
import importlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))

import auswerter, digest, kerzen, ruecktest, suche, vorschlag  # noqa: E402,F401
import bewertung  # noqa: E402

KERZEN_DIR = WURZEL / "kerzen"
BERICHTE = WURZEL / "berichte"
LEHREN = WURZEL.parents[2] / "Werkstatt" / "handelslehren-eingang.md"

_KERZEN_MODULE = {"kerzen": kerzen}


def _kerzen_modul(spur):
    """Das Kerzen-Modul dieser Spur - Default 'kerzen' (OKX, Spur 1), sonst
    der in spuren.json genannte Name (z. B. 'kraken_kerzen'). Import einmal,
    danach aus dem Cache - damit ein Test, der lauf.kerzen patcht, weiter
    dieselbe Objektidentitaet trifft wie vorher."""
    name = spur.get("kerzen_modul", "kerzen")
    if name not in _KERZEN_MODULE:
        _KERZEN_MODULE[name] = importlib.import_module(name)
    return _KERZEN_MODULE[name]


def _universum(wachen, spur, kerzen_holen, km_dir):
    """(Instrumente, Hinweis): was der Rueckblick testet.

    Mit ``spur["universum_testen"]`` und ``universum.modus == "alle"`` in der
    wachen.json ist es das LIVE-Universum des Scanners - alle Spot-Paare der
    konfigurierten Quote-Waehrungen ueber dem Mindestumsatz, gleiche Abfrage
    wie ``scanner/scan.py``. Sonst die Watchlist wie bisher. Ohne Abruf
    (``kerzen_holen=False``) oder bei Fehler: die Paare im Kerzen-Cache mit
    passender Quote, sonst die Watchlist.

    GRENZE, die im Bericht steht: das Universum ist das von HEUTE. Wer
    zwischenzeitlich verschwunden ist, fehlt (Ueberlebenden-Verzerrung), und
    junge Listings fallen in ``ruecktest.ausrichten`` heraus.
    """
    uni = wachen.get("universum") or {}
    if not (spur.get("universum_testen") and uni.get("modus") == "alle"):
        return list(wachen["watchlist"]), None
    quotes = uni.get("quotes", ["USDT", "USDC"])
    paare, quelle = [], "Markt (alle_paare)"
    if kerzen_holen:
        try:
            import okx
            paare = [i for i, _ in okx.alle_paare(
                quote=quotes,
                min_volumen_usd=uni.get("min_volumen_24h_usd", 3000000))]
        except Exception as e:  # noqa: BLE001
            print("  Universum-Abruf: %s - nehme Cache" % e, file=sys.stderr)
    if not paare:
        quelle = "Kerzen-Cache"
        paare = sorted(p.stem for p in Path(km_dir).glob("*.json")
                       if p.stem.rsplit("-", 1)[-1] in quotes)
    if len(paare) < 3:
        return list(wachen["watchlist"]), (
            "Universum nicht ermittelbar (%d Paare) - Watchlist getestet"
            % len(paare))
    return paare, ("Universum: %d Paare aus %s (Quote %s, Umsatz >= %s)"
                   % (len(paare), quelle, "/".join(quotes),
                      uni.get("min_volumen_24h_usd", 3000000)))


def _konf():
    return (json.loads((WURZEL / "konfig.json").read_text("utf-8")),
            json.loads((WURZEL / "spuren.json").read_text("utf-8")))


def _ergebnis_schreiben(ergebnis, eingang, nach_ausrichten, jetzt=None):
    """T-372: maschinenlesbares Ergebnis-Log nach jedem Lauf.

    Ablage ``verbesserer/lauf_ergebnis.json`` (eine Zeile, ueberschreibend).
    Ohne das sind A/B-Experimente (Holdout-Gate, F7-Wirkung) und
    Re-Engagement-Trigger nicht auswertbar. Abwaertskompatibel: neue Datei,
    kein Umbau bestehender Logik.
    """
    kandidat = ergebnis.get("kandidat")
    fast = ergebnis.get("fast_kandidat")
    if kandidat is not None and ergebnis.get("holdout_kandidat") is not None:
        holdout = True
    elif fast is not None:
        holdout = False
    else:
        holdout = None
    eintrag = {
        "lauf_ts": (jetzt or datetime.now(timezone.utc)).isoformat(),
        "instrumente_eingang": eingang,
        "instrumente_nach_ausrichten": nach_ausrichten,
        "kandidat_gefunden": kandidat is not None,
        "holdout_bestanden": holdout,
        "fast_kandidat": "ja" if fast is not None else None,
        "vorschlag_erzeugt": kandidat is not None,
        "grund": ergebnis.get("grund"),
    }
    (WURZEL / "lauf_ergebnis.json").write_text(
        json.dumps(eintrag, ensure_ascii=False, indent=2), "utf-8")
    return eintrag


def einmal(spur_name, *, kerzen_holen=True, jetzt=None):
    """Kette fuer eine Spur ausfuehren und den Vorschlagsordner zurueckgeben.

    ``kerzen_holen=False`` ueberspringt den OKX-Abruf und arbeitet nur mit dem
    lokalen Cache. ``jetzt`` (aware ``datetime``) fixiert das Datum im
    Ordnernamen fuer Tests. Rueckgabe: ``Path`` des Ordners, oder ``None`` bei
    hartem Abbruch ohne ausreichenden Kerzen-Cache.
    """
    konfig, spuren = _konf()
    spur = spuren[spur_name]
    spur.setdefault("name", spur_name)
    # Die Pfade in spuren.json sind relativ zum verbesserer/-Ordner
    # ("../scanner/..."). auswerter.befund loest spur["journal"] und
    # spur["berichte"] gegen das aktuelle Arbeitsverzeichnis auf - aus der
    # Repo-Wurzel gestartet zeigen sie ins Leere, und der Befund kaeme still
    # mit runden_gesamt: 0 zurueck. Einmal hier absolut gegen WURZEL aufloesen,
    # damit die ganze Kette dieselben Pfade sieht.
    _pfad_schluessel = ("journal", "zustand", "berichte", "wachen",
                        "bewertung_datei")
    spur = {**spur, **{k: str((WURZEL / spur[k]).resolve())
                       for k in _pfad_schluessel if k in spur}}
    wachen = json.loads(Path(spur["wachen"]).read_text("utf-8"))
    tage = (konfig["oos_training_tage"]
            + konfig.get("oos_fenster_ziel", 12) * konfig["oos_test_tage"]
            + konfig.get("holdout_tage", 0))

    km = _kerzen_modul(spur)
    km_dir = KERZEN_DIR if km is kerzen else WURZEL / km.__name__
    watchlist, universum_hinweis = _universum(wachen, spur, kerzen_holen, km_dir)
    # Live-Universum getestet: Watchlist-Drops waeren wirkungslose Vorschlaege.
    im_universum = bool(universum_hinweis) and set(watchlist) != set(
        wachen["watchlist"])
    if universum_hinweis:
        print("  " + universum_hinweis, file=sys.stderr)
    kerzen_je_inst = {}
    for inst in watchlist:
        if kerzen_holen:
            try:
                km.hole(inst, tage, km_dir)
            except Exception as e:  # noqa: BLE001
                print("  Kerzen %s: %s - nehme Cache" % (inst, e),
                      file=sys.stderr)
        k, _alter = km.laden(inst, km_dir)
        if k:
            kerzen_je_inst[inst] = k
    if len(kerzen_je_inst) < 3:
        print("Kein ausreichender Kerzen-Cache - Abbruch.", file=sys.stderr)
        return None

    eingang = len(kerzen_je_inst)
    kerzen_je_inst, ausricht_hinweise = ruecktest.ausrichten(kerzen_je_inst)
    if universum_hinweis:
        ausricht_hinweise = [universum_hinweis + "; nach Ausrichtung %d"
                             % len(kerzen_je_inst)] + list(ausricht_hinweise)
        if im_universum:
            ausricht_hinweise.append(
                "Das Universum ist das von HEUTE: Paare, die zwischenzeitlich "
                "verschwanden, fehlen (Ueberlebenden-Verzerrung).")
    for h in ausricht_hinweise:
        print("  Ausrichtung: %s" % h, file=sys.stderr)
    nach_ausrichten = len(kerzen_je_inst)
    if len(kerzen_je_inst) < 3:
        print("Nach Ausrichtung weniger als 3 Instrumente - Abbruch.",
              file=sys.stderr)
        return None

    datum = (jetzt or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    ordner = BERICHTE / ("%s-%s" % (datum, spur_name))
    # Ein zweiter Lauf am selben Tag greift auf denselben Ordner. Liegt er
    # schon da, muessen die Artefakte des ersten Laufs (wachen.neu.json,
    # bewertung.patch, commit.txt, ANGEFRAGT ...) weg - sonst wendet ein
    # spaeteres /ja einen Mischstand unter falscher Commit-Botschaft an.
    # berichte/erledigt/ und berichte/abgelehnt/ liegen daneben, nicht darin.
    if ordner.exists():
        shutil.rmtree(ordner, ignore_errors=True)
        # Falls rmtree unter Windows an einer offenen Datei haengen bleibt:
        # den Rest ueberschreiben statt am FileExistsError den Lauf abbrechen.
        for rest in ordner.glob("*") if ordner.exists() else []:
            if rest.is_file():
                rest.unlink(missing_ok=True)
    ordner.mkdir(parents=True, exist_ok=True)

    befund = auswerter.befund(spur, konfig, ordner)
    basis = suche.basis_kandidat({**wachen, "watchlist": watchlist},
                                 bewertung.CHANCE_GEWICHTE,
                                 bewertung.RISIKO_GEWICHTE,
                                 deckel_felder=spur.get("deckel_felder"))
    grenzen = spur["aenderbar"]["wachen.json"]
    grenzen = {**grenzen,
               "stop_min": grenzen.get("pflicht_stop_prozent_min", [4, 8]),
               "stop_max": grenzen.get("pflicht_stop_prozent_max", [8, 15])}

    modell = None
    if spur_name == "spur3":
        import kraken_modell
        for fx_paar in ("EURUSDC", "EURCEUR"):
            if kerzen_holen:
                try:
                    km.hole(fx_paar, tage, km_dir)
                except Exception as e:  # noqa: BLE001
                    print("  FX-Kerzen %s: %s - nehme Cache" % (fx_paar, e),
                          file=sys.stderr)
        fx_eur_usdc, _ = km.laden("EURUSDC", km_dir)
        fx_eur_eurc, _ = km.laden("EURCEUR", km_dir)
        modell = kraken_modell.erzeuge(wachen, fx_eur_usdc, fx_eur_eurc)
    bewerte = ((lambda k, kand, konf: ruecktest.walk_forward(k, kand, konf, modell))
              if modell else None)
    holdout_fn = ((lambda k, kand, h: ruecktest.holdout(k, kand, h, modell))
                 if modell else None)
    ergebnis = suche.suche(basis, kerzen_je_inst, konfig, grenzen,
                           bewerte=bewerte, holdout_fn=holdout_fn,
                           gewichte_durchsuchbar=spur.get(
                               "gewichte_durchsuchbar",
                               konfig.get("gewichte_durchsuchbar", True)),
                           watchlist_aenderbar=not im_universum)

    if ergebnis["kandidat"] is not None:
        vorschlag.baue(ordner, ergebnis, spur, konfig,
                       hinweise=ausricht_hinweise)
    else:
        vorschlag.kein_vorschlag(ordner, ergebnis, spur_name,
                                 hinweise=ausricht_hinweise)

    d = digest.erzeuge(befund, ergebnis["basis_wf"], ergebnis["kandidat_wf"],
                       ergebnis.get("aenderungen", {}), konfig["llm"],
                       fast_kandidat=ergebnis.get("fast_kandidat"))
    digest.annotiere_bericht(ordner / "bericht.md", d)
    if d["lehren"]:
        digest.haenge_lehren_an(LEHREN, d["lehren"], datum)
    _ergebnis_schreiben(ergebnis, eingang, nach_ausrichten, jetzt=jetzt)
    return ordner


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--spur", default="spur1")
    p.add_argument("--ohne-kerzen-abruf", action="store_true")
    a = p.parse_args()
    o = einmal(a.spur, kerzen_holen=not a.ohne_kerzen_abruf)
    print("Abbruch." if o is None else "Ordner: %s" % o)
    sys.exit(0 if o else 1)
