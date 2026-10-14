"""Moon-Dev-Spur: Funding-Extreme auf Hyperliquid als Papierbuch.

QUELLE IST DER BOT, NICHT EIN NACHBAU
------------------------------------
Die Zahlen kommen aus dem geklonten Fremd-Repo
`Werkstatt/moon-dev-ai-agents` - konkret aus
`src.agents.fundingarb_agent`, das ueber `src.nice_funcs_hl.get_funding_rates()`
alle Perpetuals von Hyperliquid abfragt und bei einer Jahres-Funding-Rate ueber
seiner Schwelle (`YEARLY_FUNDING_THRESHOLD = 100`) einsteigt. Dieses Modul ruft
DIESELBE Funktion auf (per Pfad geladen) und bucht daraus Papierpositionen -
der Bot wird also benutzt, nicht nachgebaut.

WAS HIER ANDERS IST ALS BEIM BOT
--------------------------------
Der Bot laesst ein Sprachmodell (Claude/DeepSeek) ueber jede Gelegenheit
urteilen und handelt danach auf Hyperliquid mit einem echten Wallet. Beides
ist hier ausgeschaltet:

  * kein Sprachmodell - die Regel ist die des Bots, aber deterministisch
    (Schwelle, Richtung, Stop, Ziel stehen in `wachen.json`),
  * kein Orderpfad - es gibt keinen Live-Zweig. Ein `--live` verweigert.
    Die Fremd-Agenten handeln auf Solana/Hyperliquid mit echten Schluesseln;
    sie dafuer anzuschliessen waere eine andere Entscheidung als diese Spur.

Das Buch ist ein Haus-Buch: `zustand.json`, `handelsjournal.csv`,
`ablehnungen.csv` im Spuren-Ordner, Kopie nach `Q:\\Handel_Journal\\moondev_funding`
(`journal_zweitziel`, Bedingung 4), Groesse ueber die Ratsche aus `ratschen.py`.

Aufruf:
  python handeln.py --vorschau   was waere dran, ohne schreiben
  python handeln.py --papier     Papierlauf mit Journal
  python handeln.py --wachen     Grenzen als Momentaufnahme
  python handeln.py --live       verweigert, nennt den Grund
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
# Reihenfolge zaehlt: sys.path.insert(0, ...) dreht die Liste um, deshalb
# rueckwaerts einfuegen. HIER muss ganz vorne stehen, sonst gewinnt
# scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, os.pardir, "Bus"),
          os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import wachen_pruefung as wp  # noqa: E402
import ereignis  # noqa: E402
import kill_gemeinsam as kg  # noqa: E402  # Kill-Frist/Reset/Opt-out

# ratschen.py ueber den PFAD laden, nicht ueber sys.path: die Datei liegt eine
# Ebene hoeher und heisst wie kein Paket.
from importlib.util import module_from_spec as _rs_mod  # noqa: E402
from importlib.util import spec_from_file_location as _rs_spec  # noqa: E402

_rs_datei = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "ratschen.py")
_rs_spec_obj = _rs_spec("ratschen", _rs_datei)
ratschen = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(ratschen)

# Risikostufe (HANDEL_RISIKO): Faktor auf die Betraege, Suffix auf Zustand
# und Journal. OHNE die Variable aendert sich nichts (Faktor 1.0, kein
# Suffix) - das ist die Bedingung, unter der diese Umstellung in laufenden
# Handelscode darf. Ueber den PFAD geladen wie ratschen.py: die Spur hat ihren
# eigenen Ordner als sys.path[0], ein 'import risikostufe' haenge an der
# Reihenfolge der Eintraege.
from importlib.util import module_from_spec as _ris_mod  # noqa: E402
from importlib.util import spec_from_file_location as _ris_spec  # noqa: E402

_ris_datei = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "risikostufe.py")
_ris_spec_obj = _ris_spec("risikostufe", _ris_datei)
risikostufe = _ris_mod(_ris_spec_obj)
_ris_spec_obj.loader.exec_module(risikostufe)

# Risiko-Vorfilter (Regeln des Moon-Dev risk_agent): dasselbe Modul wie in
# spur_buch.py, ueber den PFAD geladen - eine Umsetzung fuer alle Feed-Spuren.
_vf_datei = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "risikovorfilter.py")
_vf_spec_obj = _ris_spec("risikovorfilter", _vf_datei)
risikovorfilter = _ris_mod(_vf_spec_obj)
_vf_spec_obj.loader.exec_module(risikovorfilter)

WACHEN = os.path.join(HIER, "wachen.json")
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.csv"))

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund"]

SCHREIBEN = True

# Wo der Bot liegt. Das Repo ist Fremdware (Durchgangsware) und darf fehlen -
# dann sagt diese Spur das und tut nichts, statt Zahlen zu erfinden.
BOT = os.path.join(HANDEL, os.pardir, os.pardir, "Werkstatt",
                   "moon-dev-ai-agents")
BOT_MODUL = os.path.join(BOT, "src", "nice_funcs_hl.py")
# Die Funktion des Bots braucht ihre eigenen Pakete (pandas, requests). Sie
# laeuft deshalb in IHREM venv als kurzer Unterprozess - dieselbe Bauform wie
# bei der nautilus-Spur im Dauerlauf ("python" je Spur). Das Haus-venv bleibt
# unangetastet: pandas gehoert nicht in die Handelsspur, nur in den Bot.
BOT_PYTHON = os.path.join(BOT, ".venv", "Scripts", "python.exe")
BOT_AUFRUF = (
    "import json, contextlib, io, sys\n"
    "sys.path.insert(0, r'{src}')\n"
    "import nice_funcs_hl as n\n"
    "_puffer = io.StringIO()\n"
    "with contextlib.redirect_stdout(_puffer):\n"
    "    d = n.get_funding_rates(sys.argv[1])\n"
    "print(json.dumps(d))\n"
)

# --- Test-Seams -----------------------------------------------------------
# Kurse/Funding: None -> echte Bot-Funktion. Tests setzen ein Lambda.
funding_quelle = None
zeit_quelle = None

# --- Zeit und Dateien ------------------------------------------------------

def _jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def lade_wachen():
    with open(WACHEN, encoding="utf-8") as f:
        return risikostufe.skaliere(json.load(f))


# Zustand atomar schreiben und laut lesen (atomar.py, 30.09.2026). Ueber den
# PFAD geladen wie risikostufe.py: die Spur hat ihren eigenen Ordner als
# sys.path[0]. Defekte Datei -> Sicherung .bak, sonst laute Ausnahme statt
# leerem Bestand.
from importlib.util import module_from_spec as _at_mod, \
    spec_from_file_location as _at_spec
_at_obj = _at_spec("atomar", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "atomar.py"))
atomar = _at_mod(_at_obj)
_at_obj.loader.exec_module(atomar)


def lade_zustand():
    return atomar.lade_json(ZUSTAND, lambda: {"positionen": [], "modus": "papier", "letzter_lauf": None,
                "verlust_usd": 0.0})


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(**felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        if neu:
            w.writeheader()
        w.writerow(felder)


def spiegeln(z, w):
    """Bedingung 4: Journal und Zustand ausser Haus (Muster swap/handeln.py)."""
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        wp.spiegele_journal([ZUSTAND], ziel)


# --- Die Quelle: der Bot ---------------------------------------------------

def funding_holen(symbol):
    """Funding-Daten EINES Symbols: dict oder None.

    Gerufen wird die Funktion DES BOTS in dessen eigenem venv. Ihre
    Statuszeilen ("Fetching funding rate ...") unterdrueckt das Skript selbst -
    der Dauerlauf liest die Ausgabe seiner Spuren, und fremde Zeilen darin
    waeren nicht zuzuordnen.
    """
    if funding_quelle:
        return funding_quelle(symbol)
    if not os.path.isfile(BOT_MODUL):
        raise RuntimeError("Bot-Repo fehlt: %s (nicht geklont?)" % BOT_MODUL)
    if not os.path.isfile(BOT_PYTHON):
        raise RuntimeError("Bot-venv fehlt: %s (Requirements nicht installiert?)"
                           % BOT_PYTHON)
    skript = BOT_AUFRUF.format(src=os.path.dirname(BOT_MODUL))
    p = subprocess.run([BOT_PYTHON, "-c", skript, symbol], cwd=BOT,
                       capture_output=True, text=True, timeout=90,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("Bot-Aufruf scheiterte: %s"
                           % ((p.stderr or "").strip().splitlines()[-1:] or
                              ["Rueckgabe %d" % p.returncode])[0])
    zeilen = [z for z in (p.stdout or "").strip().splitlines() if z.strip()]
    if not zeilen:
        return None
    try:
        return json.loads(zeilen[-1])
    except ValueError:
        return None


def jahres_funding_pct(daten):
    """Jahres-Rate in Prozent aus der stuendlichen Rate von Hyperliquid.

    Hyperliquid rechnet stuendlich (`funding` in metaAndAssetCtxs). Der Bot
    vergleicht denselben Wert mit seiner Schwelle (100 = 100 % im Jahr),
    deshalb dieselbe Rechnung: Rate * 24 * 365 * 100.
    """
    if not daten:
        return None
    rate = daten.get("funding_rate")
    if rate is None:
        return None
    return float(rate) * 24.0 * 365.0 * 100.0


def richtung(jahres_pct, w):
    """Die Regel des Bots: hohes positives Funding -> short, negatives -> long.

    Positives Funding zahlen die Longs an die Shorts - wer short steht,
    kassiert es. Deshalb short bei +, long bei -. Unter der Schwelle: kein
    Geschaeft (der Bot handelt erst ab `YEARLY_FUNDING_THRESHOLD`).
    """
    if jahres_pct is None:
        return None
    schwelle = abs(float(w.get("funding_schwelle_jahr_pct", 100.0)))
    if jahres_pct >= schwelle:
        return "short"
    if jahres_pct <= -schwelle:
        return "long"
    return None


# --- Positionen ------------------------------------------------------------

def groessenfaktor(ruecklauf, w):
    """Drawdown-Ratsche aus ratschen.py - eine Umsetzung fuer alle Spuren."""
    return ratschen.groessenfaktor(ruecklauf, w)


def pruefe_einstieg(inst, daten, z, w, faktor):
    """Einstieg nach dem Funding der Quelle. Stop und Ziel in Prozent."""
    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 3):
        return
    if any(p.get("inst") == inst for p in z["positionen"]):
        return

    jahres = jahres_funding_pct(daten)
    seite = richtung(jahres, w)
    if not seite:
        return

    einstieg = float(daten.get("mark_price") or 0.0)
    if einstieg <= 0:
        return
    stop_pct = float(w.get("stop_prozent", 6.0))
    stop_pct = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
    stop_pct = min(stop_pct, w.get("pflicht_stop_prozent_max", 12.0))
    vz = 1 if seite == "long" else -1
    abstand = einstieg * stop_pct / 100.0
    r = float(w.get("ziel_r_vielfaches", 1.5))
    stop = einstieg - vz * abstand
    ziel = einstieg + vz * r * abstand

    nominel = w["risiko_je_position_usd"] / (stop_pct / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"])
    nominel *= faktor
    if nominel <= 0:
        return

    # Vorfilter VOR dem Buchen (nur wenn die Wache ihn einschaltet).
    if w.get("risikovorfilter"):
        ok, warum = risikovorfilter.pruefe(w, JOURNAL, z,
                                           nominel * stop_pct / 100.0)
        if not ok:
            print("VORFILTER: %s" % warum)
            return

    z["positionen"].append({
        "inst": inst, "seite": seite, "einstieg": einstieg,
        "stop": stop, "ziel": ziel, "stop_pct": stop_pct,
        "nominal": nominel, "eroeffnet_zeit": _jetzt(),
        "funding_jahr_pct": round(jahres, 2),
    })
    print("EINSTIEG %s %s @ %.6f  Funding %+.1f %%/Jahr  Stop %.2f%%  "
          "Ziel %.6f  Nominal %.2f USD"
          % (seite.upper(), inst, einstieg, jahres, stop_pct, ziel, nominel))
    journal(zeit=_jetzt(), modus="papier", aktion="kauf", inst=inst,
            seite=seite, preis="%.6f" % einstieg,
            einsatz_usd="%.2f" % nominel, stop="%.6f" % stop,
            ziel="%.6f" % ziel, stop_pct="%.2f" % stop_pct,
            grund="moondev_funding")


def pruefe_ausstiege(z, kurse, w, nur=None, erzwinge=None):
    """Bestehende Positionen gegen Stop und Ziel pruefen.

    `kurse` ist {Symbol: mark_price}. Der G/V laeuft auf den NOMINALWERT -
    die rohe Kursdifferenz waere bei BTC ein Faktor von Zehntausenden.
    """
    behalten = []
    for p in z.get("positionen", []):
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue
        kurs = kurse.get(p["inst"])
        if not kurs:
            # Kein Kurs heisst nicht "nichts passiert": die Position wird
            # uebersprungen und kann so beliebig lange stehen bleiben. Bis zum
            # 29.09.2026 schwieg dieser Zweig (spur_buch meldet es seit dem
            # 28.09.2026 - dieselbe Zeile, dieselbe Bedeutung).
            print("  %s: kein Kurs - Position wird NICHT geprueft (seit %s)"
                  % (p.get("inst"), p.get("eroeffnet_zeit") or "?"),
                  file=sys.stderr)
            behalten.append(p)
            continue
        grund = None
        if p["seite"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
                grund = "ziel"
        if erzwinge and not grund:
            grund = erzwinge       # Kill: Zwangsschluss zum Kurs, Stop/Ziel haben Vorrang
        if not grund:
            behalten.append(p)
            continue

        vz = 1 if p["seite"] == "long" else -1
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        erloes = p["nominal"] + gv
        print("AUSSTIEG (%s) %s %.6f G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        journal(zeit=_jetzt(), modus="papier", aktion="verkauf", inst=p["inst"],
                seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % erloes, stop="%.6f" % p["stop"],
                ziel="%.6f" % p["ziel"], stop_pct="%.2f" % p["stop_pct"],
                grund=grund)

    z["positionen"] = behalten


# --- Lauf ------------------------------------------------------------------

def hole_kurse(w, z):
    """Ein Durchgang durch die Instrumente: (daten, kurse, fehler).

    Ein Abruf je Symbol, weil die Funktion des Bots genau das anbietet.
    Fehler EINES Symbols brechen den Zyklus nicht ab - sie stehen im
    Rueckgabewert und werden vom Aufrufer gemeldet.

    GEFRAGT WIRD DER PLAN **UND** DAS BUCH (`wp.pruef_instrumente`): ein Symbol
    kann aus `instrumente` verschwinden (Hyperliquid listet und delistet
    laufend), waehrend eine Position darauf noch offen ist. Ueber die blosse
    Plan-Liste bekaeme diese Position keinen Kurs mehr - `pruefe_ausstiege`
    haette sie stillschweigend behalten, sie waere nie geschlossen worden und
    haette einen der drei Plaetze dauerhaft belegt (dieselbe Falle wie in den
    vier Indikatorspuren am 29.09.2026, nur eine Ebene tiefer).
    """
    daten, fehler = {}, []
    verwaist = wp.verwaiste_instrumente(w, z)
    if verwaist:
        print("  Verwaiste Instrumente (nicht mehr im Plan, Position bleibt "
              "im Buch): %s" % ", ".join(verwaist), file=sys.stderr)
    for inst in wp.pruef_instrumente(w, z):
        try:
            d = funding_holen(inst)
        except Exception as e:                                # noqa: BLE001
            fehler.append("%s: %s" % (inst, e))
            continue
        if not d:
            fehler.append("%s: keine Funding-Daten" % inst)
            continue
        daten[inst] = d
    kurse = {i: float(d.get("mark_price") or 0.0) for i, d in daten.items()}
    return daten, kurse, fehler


def lauf(modus):
    """Ein Zyklus der Moon-Dev-Funding-Spur."""
    w = lade_wachen()
    z = lade_zustand()
    z.setdefault("positionen", [])

    if modus == "wachen":
        print(json.dumps(wp.lage(w, JOURNAL, z), indent=2, ensure_ascii=False))
        return

    s = wp.lage(w, JOURNAL, z)
    ruecklauf = s.get("ruecklauf_usd", 0.0)
    faktor = groessenfaktor(ruecklauf, w)

    if s.get("kill") and modus != "vorschau":
        status, ruecklauf = kg.phase(z, w, ruecklauf, s.get("runden_gesamt", 0), _jetzt)
        if status == "frei":
            faktor = groessenfaktor(ruecklauf, w)
        else:
            # Zwangsschluss zum Marktkurs MIT Buchung (bis 09.10.2026 ungebucht
            # geleert, Spur danach fuer immer gesperrt).
            _d, kurse_kill, fehler_kill = hole_kurse(w, z)
            for f in fehler_kill:
                print("Uebersprungen (%s)" % f, file=sys.stderr)
            pruefe_ausstiege(z, kurse_kill, w, erzwinge=kg.KILL_GRUND)
            if z.get("positionen"):
                print("  %d Position(en) noch offen (kein Kurs) - naechster Zyklus "
                      "versucht es erneut." % len(z["positionen"]))
            schreibe_zustand(z)
            spiegeln(z, w)
            return

    daten, kurse, fehler = hole_kurse(w, z)
    for f in fehler:
        print("Uebersprungen (%s)" % f, file=sys.stderr)
    if not daten:
        print("Keine Funding-Daten - Zyklus ohne Buchung beendet (%s)"
              % ("; ".join(fehler)[:200] if fehler else "keine Instrumente"))
        if modus == "vorschau":
            print("Vorschau: keine Dateien geschrieben.")
            print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
                  "(Papier)")
        return

    # Ausstiege zuerst: sie brauchen nur den Kurs.
    pruefe_ausstiege(z, kurse, w)
    if modus == "vorschau":
        print("Vorschau: keine Dateien geschrieben.")
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier)")
        return

    for inst in w.get("instrumente", []):
        if inst in daten:
            pruefe_einstieg(inst, daten[inst], z, w, faktor)

    schreibe_zustand(z)
    spiegeln(z, w)


# --- Main -------------------------------------------------------------------

def main():
    with ereignis.lauf("handel/moondev_funding"):
        return _main()


def _main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau",
                    dest="modus", help="was waere dran, ohne schreiben")
    ap.add_argument("--papier", action="store_const", const="papier",
                    dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen",
                    dest="modus")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier). Die Fremd-Agenten handeln auf Hyperliquid/Solana mit "
              "echten Schluesseln - dieser Haus-Lauf bucht nur Papier.")
        return 0
    return lauf(a.modus) or 0


if __name__ == "__main__":
    raise SystemExit(main())
