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


def _konf():
    return (json.loads((WURZEL / "konfig.json").read_text("utf-8")),
            json.loads((WURZEL / "spuren.json").read_text("utf-8")))


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
    watchlist = wachen["watchlist"]
    tage = (konfig["oos_training_tage"]
            + konfig.get("oos_fenster_ziel", 12) * konfig["oos_test_tage"]
            + konfig.get("holdout_tage", 0))

    kerzen_je_inst = {}
    for inst in watchlist:
        if kerzen_holen:
            try:
                kerzen.hole(inst, tage, KERZEN_DIR)
            except Exception as e:  # noqa: BLE001
                print("  Kerzen %s: %s - nehme Cache" % (inst, e),
                      file=sys.stderr)
        k, _alter = kerzen.laden(inst, KERZEN_DIR)
        if k:
            kerzen_je_inst[inst] = k
    if len(kerzen_je_inst) < 3:
        print("Kein ausreichender Kerzen-Cache - Abbruch.", file=sys.stderr)
        return None

    kerzen_je_inst, ausricht_hinweise = ruecktest.ausrichten(kerzen_je_inst)
    for h in ausricht_hinweise:
        print("  Ausrichtung: %s" % h, file=sys.stderr)
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
    basis = suche.basis_kandidat(wachen, bewertung.CHANCE_GEWICHTE,
                                 bewertung.RISIKO_GEWICHTE)
    grenzen = spur["aenderbar"]["wachen.json"]
    grenzen = {**grenzen,
               "stop_min": grenzen.get("pflicht_stop_prozent_min", [4, 8]),
               "stop_max": grenzen.get("pflicht_stop_prozent_max", [8, 15])}
    ergebnis = suche.suche(basis, kerzen_je_inst, konfig, grenzen)

    if ergebnis["kandidat"] is not None:
        vorschlag.baue(ordner, ergebnis, spur, konfig)
    else:
        vorschlag.kein_vorschlag(ordner, ergebnis, spur_name)

    d = digest.erzeuge(befund, ergebnis["basis_wf"], ergebnis["kandidat_wf"],
                       ergebnis.get("aenderungen", {}), konfig["llm"],
                       fast_kandidat=ergebnis.get("fast_kandidat"))
    digest.annotiere_bericht(ordner / "bericht.md", d)
    if d["lehren"]:
        digest.haenge_lehren_an(LEHREN, d["lehren"], datum)
    return ordner


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--spur", default="spur1")
    p.add_argument("--ohne-kerzen-abruf", action="store_true")
    a = p.parse_args()
    o = einmal(a.spur, kerzen_holen=not a.ohne_kerzen_abruf)
    print("Abbruch." if o is None else "Ordner: %s" % o)
    sys.exit(0 if o else 1)
