"""Die Omniquant-Spur: handelt die Signale, die prognose.py findet - als Papierbuch.

Angelegt am 13.09.2026 auf Max' Anweisung ("Omniquant AI trader in Handel/
implementieren"). "Omniquant" ist hier keine externe API und kein fremder
Feed - es ist die Idee aus der Recherche vom 10.09.2026 (omniquant.trade):
ein Trader, der nur handelt, was eine probabilistische Bewertung mit Toren
als guenstig ausweist, und der sich enthaelt, wenn kein frisches Signal da
ist. Damalige Empfehlung, umgesetzt: dieselbe Kategorie Werkzeug auf eigenen
Daten und unter eigener Kontrolle, nicht der kommerzielle Dienst.

WAS ER IST
----------
Die Signalquelle ist der volle Prognose-Bericht (prognose_berichte/
neuester.json), den der Lauf von prognose.py schreibt: Treffer mit Richtung,
Einstieg, Stop und Ziel, alle Tore offen. Diese Spur bucht sie als
Papierpositionen - mit Kosten (Gebuehr + Slippage) auf beiden Seiten, einem
Zwangsschluss nach max_halte_dauer_tagen und einem Kill-Switch ueber die
kumulierten Verluste. Was am Ende uebrig bleibt, ist die Antwort auf die
Frage, ob die Prognose-Treffer nach Kosten tragen.

WAS ER NICHT IST
----------------
Kein Orderpfad. Kein Broker-Aufruf, keine Position am Markt. `--live`
verweigert mit genau einem Grund, in dem das Wort Freigabefenster NICHT
vorkommt - so fragt der Dauerlauf keine Freigabe an, die nichts oeffnen
kann (Muster: spiegel-Spur, papierfest).

GLEICHE WAHRHEIT
----------------
Die Spur erfindet keine zweite Formel: Stop und Ziel kommen aus dem Bericht
(dort gerechnet gegen 20-/60-Tage-Extrema), nicht neu geschaetzt. Der
Einstieg ist der aktuelle Kurs - aber nur, wenn er noch zwischen Stop und
Ziel liegt (long: stop < kurs < ziel; short: ziel < kurs < stop). Liegt er
dahinter, ist das Signal verfallen und wird uebersprungen.

Aufruf:
    python handeln.py --vorschau    # was waere dran, ohne zu schreiben
    python handeln.py --papier      # ein Papierzyklus mit Journal
    python handeln.py --wachen      # Grenzen als Momentaufnahme
    python handeln.py --live        # verweigert, nennt den Grund
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HIER, HANDEL, os.path.join(HANDEL, "scanner"),
          os.path.join(HANDEL, os.pardir, "Bus")):
    if p not in sys.path:
        sys.path.insert(0, p)

# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(          # Handel/, nicht der Spurenordner
    os.path.dirname(os.path.abspath(__file__)))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import pos_kennung
import ereignis                                            # noqa: E402
import okx                                                 # noqa: E402
import wachen_pruefung as wp                               # noqa: E402
import live_perp                                           # noqa: E402
import telemetrie                                          # noqa: E402

# Risikostufe (HANDEL_RISIKO): Faktor auf die Betraege, Suffix auf Zustand
# und Journal. OHNE die Variable aendert sich nichts (Faktor 1.0, kein
# Suffix) - das ist die Bedingung, unter der diese Umstellung in laufenden
# Handelscode darf. Ueber den PFAD geladen wie ratschen.py: die Spur hat ihren
# eigenen Ordner als sys.path[0], ein 'import risikostufe' haenge an der
# Reihenfolge der Eintraege.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec
_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

# Schattenarm (24.09.2026): HANDEL_BUCH=weit haengt an JEDE Buchdatei das
# Suffix .weit - Wachen (wachen.weit.json), Zustand, Journal und der
# Prognose-Bericht (neuester_weit.json). Ohne die Variable aendert sich
# nichts; das Hauptbuch bleibt Vergleichsgrundlage. Bauart wie spiegel_knapp.
ARM = (os.environ.get("HANDEL_BUCH") or "").strip()


def _arm(pfad):
    """Suffix vor die Endung: handelsjournal.csv -> handelsjournal.weit.csv."""
    if not ARM:
        return pfad
    stamm, endung = os.path.splitext(pfad)
    return "%s.%s%s" % (stamm, ARM, endung)


WACHEN = _arm(os.path.join(HIER, "wachen.json"))
ZUSTAND = risikostufe.datei(_arm(os.path.join(HIER, "zustand.json")))
JOURNAL = risikostufe.datei(_arm(os.path.join(HIER, "handelsjournal.csv")))
DEFAULT_BERICHT = os.path.join(HANDEL, "prognose_berichte", _arm("neuester.json"))


def bericht_pfad(w=None):
    """Der Bericht der gewaehlten FASSUNG (wachen-Feld `prognose_fassung`).

    Fassung und Arm sind unabhaengig: "weit" liest den weiten Bericht
    (neuester.weit.json, geschrieben von prognose.py mit PROGNOSE_FASSUNG=weit),
    waehrend die BUCHDATEIEN unveraendert heissen. Ohne das Feld bleibt es beim
    strengen Bericht - die Voreinstellung aendert sich nicht, und wer nur den
    Bericht tauscht, verliert keine Buchhistorie.

    Anlass (Auftrag Max 24.09.2026, "Omniquant auf Papier auf weit stellen"):
    der strenge Bericht liefert seit Tagen 0 Treffer, der weite 6-7. Statt den
    Schattenarm zu verdoppeln, waehlt das Hauptbuch seine Signalquelle.
    """
    if w is None:                     # {} heisst "nichts gesetzt", nicht "lies selbst"
        w = lade_wachen() or {}
    fassung = str(w.get("prognose_fassung") or "").strip().lower()
    if not fassung or fassung in ("streng", "standard"):
        return DEFAULT_BERICHT
    return os.path.join(os.path.dirname(DEFAULT_BERICHT),
                        "neuester.%s.json" % fassung)

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "wert_usd", "stop", "ziel", "grund",
           "score", "cr", "mfe_pct", "mae_pct", "haltetage", "pos_id"]

# Ob geschrieben wird. Die Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True

# --- Test-Seams -------------------------------------------------------------
# None -> echte Quelle. Tests setzen Lambda/dict und stellen in tearDown
# zurueck (Mechanik wie kerzen_quelle bei den anderen Spuren).
letzter_kurs_quelle = None     # f(inst) -> float
bericht_quelle = None          # None -> DEFAULT_BERICHT lesen, sonst dict


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


def _basiswert(inst):
    """Der Vermoegenswert hinter einem Spot-Paar (SOL-USDC -> SOL).

    Die Quote-Waehrung steht hinten und hat keinen Bindestrich - rsplit
    vom rechten Ende trennt auch Basiswerte mit Bindestrich sauber.
    """
    return inst.rsplit("-", 1)[0] if inst and "-" in inst else inst


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
    """Zustand lesen - und fehlende Felder ergaenzen.

    `verluste_usd` kam spaeter dazu. Eine Zustandsdatei von vorher kennt es
    nicht; ohne die Zeile fehlt der GUI das Feld (gui.fuss_texte liest es) und
    die Ruecklauf-Sperre rechnet mit einem Wert, den das Buch nicht kennt.
    gitter/handeln.py haelt es an derselben Stelle genauso - zwei Spuren mit
    alter Zustandsdatei sollen dasselbe Verhalten zeigen.
    """
    z = atomar.lade_json(ZUSTAND, dict)
    z.setdefault("positionen", [])
    z.setdefault("modus", "papier")
    z.setdefault("letzter_lauf", None)
    z.setdefault("verluste_usd", 0.0)
    return z


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(**felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    # Der Kopf der DATEI entscheidet, was geschrieben wird (T-095): ein
    # Altjournal ohne `pos_id` behaelt seine Spalten (pos_kennung.spalten).
    spalten = SPALTEN if neu else pos_kennung.spalten(JOURNAL, SPALTEN)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in spalten})


# --- Signalquelle -----------------------------------------------------------

def lade_bericht():
    """Der volle Prognose-Bericht. None, wenn er zu alt ist - Abstention."""
    w = lade_wachen()
    pfad = bericht_pfad(w)
    if bericht_quelle is not None:
        b = bericht_quelle
    else:
        try:
            with open(pfad, encoding="utf-8") as f:
                b = json.load(f)
        except (OSError, ValueError):
            return None, ("kein Bericht (%s fehlt)" % os.path.basename(pfad))
    try:
        erzeugt = datetime.fromisoformat(str(b.get("erzeugt", "")))
    except (TypeError, ValueError):
        return None, "Bericht ohne Zeitstempel (erzeugt fehlt)"
    if erzeugt.tzinfo is None:
        # Ein Zeitstempel ohne Zone darf die Spur nicht kippen: die
        # Subtraktion naiv/aware wirft TypeError, kein ValueError - die
        # Ausnahme oben faenge ihn nicht, der Zyklus braeche ab. So
        # geschriebene Berichte werden als UTC gelesen (wie prognose.py).
        erzeugt = erzeugt.replace(tzinfo=timezone.utc)
    alter_h = (datetime.now(timezone.utc) - erzeugt).total_seconds() / 3600
    max_alter = w.get("max_bericht_alter_stunden", 26)
    if alter_h > max_alter:
        return None, "Bericht %.1f h alt, Grenze %g h" % (alter_h, max_alter)
    return b, None


def _atr_stop_ziel(w, inst, richtung, kurs, bericht_stop, bericht_ziel):
    """Stop/Ziel aus dem ATR (4H, n=14) - oder None, wenn untragbar.

    Auftrag Max 11.10.2026 (T-393 a, "wie xperp"): omniquant handelt
    Kraken-FUTURES mit Hebel 6, der Bericht klemmt den Stop auf
    stop_min_pct..stop_max_pct (5..12 %), was bei Hebel 6 rund 68 % des
    Einsatzes kosten kann (Messung am Journal, Median 11,3 %). xperp faehrt
    Stop = stop_atr_faktor x ATR und Ziel = ziel_atr_faktor x ATR auf 4H-
    Kerzen (n=14). Dasselbe rechnet diese Spur, sobald `stop_atr_faktor`
    in wachen.json gesetzt ist. Ohne das Feld bleibt der Bericht-Stop.

    Kerzen-Form wie xperp (okx.kerzen: [zeit, offen, hoch, tief, schluss,
    volumen] - indikatoren.atr() erwartet hoech=2, tief=3, schluss=4? NEIN:
    wahre_spanne nutzt k[i][2]=hoch, k[i][3]=tief, k[i][4]=schluss. okx.kerzen
    liefert genau dieses Format - geprueft an scanner/okx.py:242ff.)
    """
    faktor = w.get("stop_atr_faktor")
    if not faktor:
        # kein ATR-Zweig - Berichtswerte unveraendert
        return bericht_stop, bericht_ziel
    try:
        kerzen = okx.kerzen(inst, "4H", 300)
        if not kerzen:
            return None, None
        # indikatoren aus xperp (dieselbe Formel, keine zweite Implementierung)
        import sys as _sys
        xperp_pfad = os.path.join(HANDEL, "xperp")
        schon_drin = any(os.path.normcase(os.path.normpath(p)) ==
                         os.path.normcase(os.path.normpath(xperp_pfad))
                         for p in _sys.path)
        if not schon_drin:
            _sys.path.insert(0, xperp_pfad)
        import indikatoren
        atr_reihe = indikatoren.atr(kerzen, 14)
        atr = next((a for a in reversed(atr_reihe) if a), None)
        if not atr or atr <= 0:
            return None, None
    except Exception as e:                             # noqa: BLE001
        print("  %-14s ATR nicht berechenbar (%s) - Kandidat uebersprungen"
              % (inst, e))
        return None, None
    vz = 1 if richtung == "long" else -1
    ziel_faktor = w.get("ziel_atr_faktor", 3.0)
    stop = kurs - vz * float(faktor) * atr
    ziel = kurs + vz * float(ziel_faktor) * atr
    # Konsistenz-Grenze: ein ATR-Stop muss zwischen Kurs und Ziel liegen und
    # das Ziel ueber (long) bzw. unter (short) dem Kurs. Ein Stop oder Ziel
    # bei/below 0 ist sinnlos (unter der Liquidationsmarke) - verwerfen.
    if richtung == "long" and not (0 < stop < kurs < ziel):
        return None, None
    if richtung == "short" and not (0 < ziel < kurs < stop):
        return None, None
    return stop, ziel


def kandidaten(z, w, statistik=None):
    """Treffer aus dem Bericht als Kandidaten, frisch und noch gueltig.

    Ein Treffer ohne Richtung ist keine Auskunft (Befund aus prognose.py):
    er wird uebersprungen, nicht geraten. Einstieg ist der aktuelle Kurs,
    aber nur, wenn er noch zwischen Stop und Ziel liegt - sonst ist das
    Signal verfallen. Bereits offene oder schon einmal eroeffnete Paare
    kommen nicht doppelt (Merkliste je inst+Richtung im Zustand).

    Streuungs-Filter (max_je_basiswert aus wachen.json): SOL-USDC und
    SOL-USDT sind zwei Treffer, aber ein Vermoegenswert. Drei Regeln
    verhindern den Klumpen - (a) ein Basiswert, der heute schon geschlossen
    wurde, kommt heute nicht wieder (die Merkliste, erweitert um die
    Quote-Ebene), (b) ein Basiswert, der schon max_je_basiswert-mal offen
    ist, bekommt keine weitere Position, (c) innerhalb EINES Zyklus geht je
    Basiswert nur der Staerkste durch - der Bericht ist nach C/R x Score
    sortiert, also kommt der beste Kandidat zuerst und blockt die
    schwaecheren Duplikate.
    """
    b, fehler = lade_bericht()
    if b is None:
        return [], fehler

    # Warum ein Treffer kein Kandidat wurde - als Zahlen, nicht als Gefuehl.
    # Ohne diese Aufschluesselung sieht "0 Kandidaten" aus wie "kein Signal",
    # obwohl der Bericht vielleicht Treffer hatte, die alle verfallen sind.
    st = statistik if statistik is not None else {}
    st["treffer"] = len(b.get("treffer", []))
    for k in ("ohne_richtung", "verfallen", "kurs_fehler", "gefiltert"):
        st[k] = 0

    max_je = w.get("max_je_basiswert", 1)
    heute = _heute()
    offen_je_basis = {}
    for p in z.get("positionen", []):
        bw = _basiswert(p.get("inst"))
        if bw:
            offen_je_basis[bw] = offen_je_basis.get(bw, 0) + 1
    erledigt_heute_basis = {_basiswert(m.get("inst"))
                            for m in z.get("erledigt", [])
                            if m.get("am") == heute}
    zyklus_je_basis = {}

    aus = []
    for t in b.get("treffer", []):
        richtung = t.get("richtung")
        if richtung not in ("long", "short"):
            st["ohne_richtung"] += 1
            continue                       # altes Format oder kaputt: ueberspringen
        inst = t.get("inst")
        if not inst:
            continue
        stop = t.get("stop")
        ziel = t.get("ziel")
        if not stop or not ziel:
            continue
        try:
            kurs = (letzter_kurs_quelle or okx.letzter_kurs)(inst)
            kurs = float(kurs)
        except Exception as e:             # noqa: BLE001
            st["kurs_fehler"] += 1
            print("  %-14s Kurs nicht abrufbar (%s) - Kandidat uebersprungen"
                  % (inst, e))
            continue
        # Verfallen prueft gegen die SIGNAL-Band (Bericht-Stop/Ziel): ist der
        # Kurs schon ueber das Ziel gelaufen, ist das Signal verfallen - egal
        # wie breit der ATR-Ausfuehrungs-Stop danach waere. (T-395: der
        # ATR-Zweig von T-393 hatte die Band ueberschrieben und erweckte
        # verfallene Signale mit einem unsinnig breiten Stop wieder.)
        if richtung == "long" and not (stop < kurs < ziel):
            st["verfallen"] += 1
            continue
        if richtung == "short" and not (ziel < kurs < stop):
            st["verfallen"] += 1
            continue
        # ATR-Zweig (T-393 a): bei gesetztem stop_atr_faktor rechnet die Spur
        # Stop/Ziel selbst aus dem 4H-ATR statt der Bericht-Klammer (5..12 %).
        # (None, None) heisst "nicht tragbar" - Kandidat uebersprungen.
        if w.get("stop_atr_faktor"):
            st["atr_gerechnet"] = st.get("atr_gerechnet", 0) + 1
            stop, ziel = _atr_stop_ziel(w, inst, richtung, kurs, stop, ziel)
            if not stop or not ziel:
                st["atr_untragbar"] = st.get("atr_untragbar", 0) + 1
                continue
        offen = any(p.get("inst") == inst and p.get("seite") == richtung
                    for p in z.get("positionen", []))
        if offen:
            st["gefiltert"] += 1
            continue
        # Merkliste: nur Eintraege vom HEUTIGEN Tag sperren den
        # Wiedereinstieg. Ein frischer Bericht morgen mit neuen Kerzen und
        # neuen Grenzen ist eine neue Lage - ein Eintrag von gestern darf
        # sie nicht fuer immer blockieren (Tor, das nie aufgeht).
        if any(m.get("inst") == inst and m.get("seite") == richtung
               and m.get("am") == heute
               for m in z.get("erledigt", [])):
            st["gefiltert"] += 1
            continue
        # Streuung: gleicher Basiswert zaehlt nur begrenzt (a-c, s. Docstring).
        bw = _basiswert(inst)
        if bw:
            if bw in erledigt_heute_basis:
                st["gefiltert"] += 1
                continue
            if offen_je_basis.get(bw, 0) >= max_je:
                st["gefiltert"] += 1
                continue
            if zyklus_je_basis.get(bw, 0) >= max_je:
                st["gefiltert"] += 1
                continue
            zyklus_je_basis[bw] = zyklus_je_basis.get(bw, 0) + 1
        aus.append({"inst": inst, "seite": richtung, "kurs": kurs,
                    "stop": stop, "ziel": ziel, "score": t.get("score"),
                    "cr": t.get("cr")})
    return aus, None


# --- Einstieg ---------------------------------------------------------------

def _nominal(w):
    """Positionsgroesse: fester Einsatz je Position (Spot, ohne Hebel)."""
    return w.get("max_einsatz_je_position_usd", 50)


def _kosten(w):
    """Slippage + Gebuehr EINER Seite als Anteil (0.0025 = 0,25 %).

    Der Ausfuehrungspreis je Seite liegt um diesen Anteil unguenstig: wer
    kauft, zahlt kurs * (1 + k), wer verkauft, bekommt kurs * (1 - k).
    Beide Seiten rechnet _ergebnis - eine allein waere eine Wunschrechnung.
    """
    return (w.get("slippage_pct", 0.15) + w.get("gebuehr_pct", 0.1)) / 100.0


def eroeffne(z, w, kand):
    nominal = _nominal(w)
    p = {
        "inst": kand["inst"], "seite": kand["seite"],
        "einstieg": kand["kurs"],
        "stop": kand["stop"], "ziel": kand["ziel"],
        "nominal": nominal,
        "eroeffnet": _heute(),
        "score": kand.get("score"), "cr": kand.get("cr"),
        # Buchgewinn/-verlust ab Eroeffnung fortschreiben: die Auswertung
        # braucht die Extreme, um einen zu engen Stop von einem falschen
        # Signal zu trennen (siehe _merke_extrem).
        "mfe_pct": 0.0, "mae_pct": 0.0,
    }
    z.setdefault("positionen", []).append(p)
    journal(zeit=_jetzt(), modus="papier", aktion="EINSTIEG",
            pos_id=p.setdefault("pos_id", pos_kennung.neu(_jetzt())),
            inst=p["inst"], seite=p["seite"], preis=p["einstieg"],
            einsatz_usd=nominal, stop=p["stop"], ziel=p["ziel"],
            grund="prognose-treffer", score=p["score"], cr=p["cr"])
    print("OMNIQUANT EINSTIEG: %s %s @ %.6g, Stop %.6g, Ziel %.6g, "
          "Einsatz %.2f USD"
          % (p["inst"], p["seite"], p["einstieg"], p["stop"], p["ziel"],
             nominal))


# --- Ausstieg ---------------------------------------------------------------

def _ergebnis(p, kurs, w):
    """Was vom Einsatz zurueckkommt - Kosten auf beiden Seiten.

    Long kauft zum Kurs * (1 + k) und verkauft zum Kurs * (1 - k); short
    verkauft zum Kurs * (1 - k) und kauft zum Kurs * (1 + k) zurueck. Beide
    Seiten zusammen ergeben

        erloes = nominal * (1 + bewegung) * (1 - k) / (1 + k)

    Ohne Kursbewegung bleibt also ein Minus von rund 2k (0,5 % bei
    k = 0,25 %) - der wichtigste Test eines Papierbuchs. Eine Rechnung mit
    nur einer Kostenseite waere um genau diese Haelfte zu optimistisch und
    wuerde die Frage, ob die Prognose nach Kosten traegt, verzerren.
    """
    vz = 1 if p["seite"] == "long" else -1
    bewegung = vz * (kurs - p["einstieg"]) / p["einstieg"]
    k = _kosten(w)
    roh = p["nominal"] * (1.0 + bewegung) * (1.0 - k) / (1.0 + k)
    # Ein Short kann nicht mehr verlieren als den Einsatz (Liquidation):
    # ohne Deckel ergaebe ein Anstieg ueber 100 % einen negativen Erloes -
    # mehr Verlust, als Kapital eingesetzt wurde.
    return max(0.0, roh)


def _haltetage(p):
    """Kalendertage seit dem Einstieg (UTC-Datum, wie _heute())."""
    try:
        eroeffnet = datetime.fromisoformat(p.get("eroeffnet", "")).date()
    except (TypeError, ValueError):
        return ""
    return (datetime.now(timezone.utc).date() - eroeffnet).days


def _merke_extrem(p, kurs):
    """Buchgewinn/-verlust fortschreiben (MFE/MAE in Prozent des Einstiegs).

    Gemessen wird an den Zykluspunkten - die echten Extreme zwischen zwei
    Laeufen liegen weiter aussen, die Zahl ist also eine Untergrenze. Sie
    ist trotzdem das einzige Mittel, um spaeter zu trennen, ob ein Stop zu
    eng war (die Position lief erst ins Plus) oder ob das Signal falsch war
    (sie lief sofort gegen den Einstieg).
    """
    vz = 1 if p["seite"] == "long" else -1
    bewegung = vz * (kurs - p["einstieg"]) / p["einstieg"] * 100.0
    p["mfe_pct"] = max(p.get("mfe_pct", 0.0), bewegung)
    p["mae_pct"] = min(p.get("mae_pct", 0.0), bewegung)


def schliesse(z, p, grund, kurs, w):
    ergebnis = _ergebnis(p, kurs, w)
    verlust = p["nominal"] - ergebnis
    if verlust > 0:
        z["verluste_usd"] = z.get("verluste_usd", 0.0) + verlust
    z["positionen"] = [x for x in z["positionen"] if x is not p]
    z.setdefault("erledigt", []).append(
        {"inst": p["inst"], "seite": p["seite"], "am": _heute(),
         "grund": grund, "wert_usd": round(ergebnis, 2)})
    journal(zeit=_jetzt(), modus="papier", aktion="AUSSTIEG",
            pos_id=p.get("pos_id", ""),
            inst=p["inst"], seite=p["seite"], preis=kurs,
            einsatz_usd=p["nominal"], wert_usd=round(ergebnis, 2),
            stop=p["stop"], ziel=p["ziel"], grund=grund,
            score=p.get("score"), cr=p.get("cr"),
            mfe_pct=round(p.get("mfe_pct", 0.0), 4),
            mae_pct=round(p.get("mae_pct", 0.0), 4),
            haltetage=_haltetage(p))
    if SCHREIBEN:
        telemetrie.geschlossen(JOURNAL, p, "papier", grund,
                               ergebnis - p["nominal"], kurs, _haltetage(p) or 0,
                               risikostufe.stufe())
    print("AUSSTIEG (%s): %s %s @ %.6g, wert %.2f USD"
          % (grund, p["inst"], p["seite"], kurs, ergebnis))


def pruefe_ausstiege(z, w):
    """Papier-Ausstiege. Live-Positionen fasst diese Funktion NIE an.

    Eine echte Position schliesst nur der Live-Zweig (`live_perp`). Eine
    Papierbuchung darauf waere ein Geistereintrag: die Position stuende an der
    Boerse weiter, ohne Stop-Ueberwachung und ohne dass es jemand sieht - der
    Fehler, den scanner und mosaic am 21./23.09.2026 hatten.
    """
    behalten = []
    for p in z.get("positionen", []):
        if p.get("modus") == "live":
            behalten.append(p)
            continue
        try:
            kurs = float((letzter_kurs_quelle or okx.letzter_kurs)(p["inst"]))
        except Exception as e:                           # noqa: BLE001
            print("  Kurs %s nicht abrufbar (%s) - Position bleibt"
                  % (p["inst"], e))
            behalten.append(p)
            continue
        vz = 1 if p["seite"] == "long" else -1
        _merke_extrem(p, kurs)
        grund = None
        if vz * (kurs - p["stop"]) <= 0:
            grund = "stop"
        elif vz * (kurs - p["ziel"]) >= 0:
            grund = "ziel"
        else:
            # Zwangsschluss: ein Signal, das sich in max_halte_dauer_tagen
            # nicht bewegt hat, ist verfallen.
            dauer = _haltetage(p)
            if dauer != "" and dauer >= w.get("max_halte_dauer_tage", 14):
                grund = "zwangsschluss"
        if grund:
            schliesse(z, p, grund, kurs, w)
        else:
            behalten.append(p)
    z["positionen"] = behalten
    # Merkliste aufraeumen: nur Eintraege von heute behalten. Alles aeltere
    # blockiert ohnehin nichts mehr (kandidaten prueft nur am == heute) und
    # waere nur Rauschen im Zustand.
    z["erledigt"] = [m for m in z.get("erledigt", [])
                     if m.get("am") == _heute()]


def _spiegeln(w, z=None):
    """Bedingung 4: Journal und Zustand ausser Haus.

    Eigenes Helferchen, weil die Kopie nicht nur am ZYKLUSENDE stehen darf:
    der Herzschlag-Ausstieg weiter unten kehrt frueh zurueck (Befund
    24.09.2026 - der Schattenarm omniquant_weit stellte seine sechs
    Papierpositionen als 'herzschlag' flach, schrieb den Zustand, spiegelte
    aber nicht; Q: blieb auf dem Stand des VORIGEN Zyklus stehen und
    spiegelstand meldete dauerhaft ABWEICHUNG).
    """
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if z is not None and wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        # Der Vermerk ist juenger als die Kopie: einmal nachziehen.
        wp.spiegele_journal([ZUSTAND], ziel)
    return ok, info


def herzschlag_alt(z, w):
    """Bedingung 3: der letzte Lauf darf nicht zu lange zurueckliegen."""
    letzter = z.get("letzter_lauf")
    if not letzter:
        return False
    try:
        alter_min = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(letzter)).total_seconds() / 60
    except ValueError:
        return False
    return alter_min > w.get("herzschlag_max_minuten", 90)


# --- Sperren ----------------------------------------------------------------

def sperren_live(w, z):
    """Gruende, warum --live nicht scharf schalten kann.

    Seit dem 01.10.2026 hat omniquant einen echten Orderweg (Kraken Futures,
    `live_perp.py`). Die Sperren stehen deshalb dort und werden hier nur
    durchgereicht - EINE Fassung, nicht zwei. Der Text ist eine Schnittstelle:
    `dauerlauf.nur_fenster_fehlt()` liest die --vorschau-Zeile und fragt nur
    dann eine Freigabe an, wenn GENAU EIN Grund das Wort "Freigabefenster"
    traegt. Wer hier einen zweiten Grund stillschweigend hinzufuegt, schaltet
    die Auto-Freigabe fuer diese Spur ab.
    """
    return live_perp.live_sperren(w, z)


def sperren_zeile(w, z):
    """Die Zeile, die der Dauerlauf parst - IMMER, auch bei leerer Liste.

    Eine Sperrzeile, die nur im Fehlerfall gedruckt wird, ist von "nicht
    geprueft" nicht zu unterscheiden (Pitfall 91), und `nur_fenster_fehlt`
    findet dann gar nichts.
    """
    try:
        g = sperren_live(w, z)
    except Exception as e:                               # noqa: BLE001
        print("Live waere gesperrt durch: nicht bestimmbar (%s: %s)"
              % (type(e).__name__, e))
        return
    print("Live waere gesperrt durch: " + ("; ".join(g) if g else "nichts"))


def zeige_wachen(w):
    print("=== OMNIQUANT Wachen ===")
    for k in ("handel_erlaubt", "max_einsatz_je_position_usd", "max_offen",
              "max_neu_je_zyklus", "max_gesamt_risiko_usd", "gebuehr_pct",
              "slippage_pct", "max_halte_dauer_tage", "herzschlag_max_minuten",
              "max_bericht_alter_stunden", "max_je_basiswert"):
        print("  %-28s %s" % (k, w.get(k)))
    for zeile in live_perp.kandidaten_grenzen(w):
        print(zeile)
    print("  Signalquelle: %s (Fassung %s)"
          % (os.path.relpath(bericht_pfad(w), HANDEL),
             w.get("prognose_fassung") or "streng"))
    z = lade_zustand()
    print("  %-28s %s" % ("journal_zweitziel",
                          w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  %-28s %s (%s)" % ("  letzte Kopie", z.get("journal_zweitziel_ok"),
                               z.get("journal_zweitziel_info")))


# --- Lauf -------------------------------------------------------------------

def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = lade_wachen()

    if modus == "wachen":
        zeige_wachen(w)
        return

    z = lade_zustand()

    st = {}
    live = False
    # Die Kraken-Marktliste einmal je Lauf holen - der Instrument-Weg
    # (kraken_perp.pf_markt) prueft gegen sie, und eine leere Liste wuerde
    # jeden Einstieg verweigern. Ein Fehler ist kein Absturz.
    if modus in ("live", "vorschau"):
        print("  Kraken-Marktliste: %d Maerkte geladen"
              % live_perp.markte_laden())
    if modus == "live":
        g = sperren_live(w, z)
        if g:
            print("--live angefordert, aber gesperrt: " + "; ".join(g))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    if herzschlag_alt(z, w):
        print("- Herzschlag alt -> Papierbuch flachgestellt -")
        for p in list(z.get("positionen", [])):
            try:
                kurs = float((letzter_kurs_quelle or okx.letzter_kurs)(p["inst"]))
            except Exception as e:                       # noqa: BLE001
                kurs = p["einstieg"]
                print("  Kurs %s nicht abrufbar (%s) - zum Einstiegskurs "
                      "geschlossen" % (p["inst"], e))
            schliesse(z, p, "herzschlag", kurs, w)
        z["modus"] = "papier"
        schreibe_zustand(z)
        # Bedingung 4 auch auf DIESEM Ausgang: er kehrt vor dem Zyklusende
        # zurueck (Befund 24.09.2026 - omniquant_weit stellte sechs Positionen
        # als 'herzschlag' flach, Q: blieb auf dem alten Stand, spiegelstand
        # meldete dauerhaft ABWEICHUNG). Eine Vorschau kommt hier nie an:
        # sie hat einen frischen Zustand, sonst waere sie ein Schreibzugriff.
        _spiegeln(w, z)
        return

    # Kill-Switch: keine neuen Einstiege, wenn die kumulierten Verluste die
    # Grenze erreicht haben. Offene Positionen laufen weiter aus.
    kill = z.get("verluste_usd", 0.0) >= w.get("max_gesamt_risiko_usd", 500)

    kand, fehler = kandidaten(z, w, st)
    basiswerte = len({_basiswert(k["inst"]) for k in kand})
    print("=== OMNIQUANT handeln (%s) | %d Kandidaten, %d Basiswerte | %s ==="
          % ("LIVE" if live else "Papier", len(kand), basiswerte,
             fehler or "Bericht frisch"))
    if st.get("treffer"):
        # Jede Zeile nennt ihr Subjekt, keine traegt ein Meldewort
        # (verkauf/stop/KILL/gesperrt/ausstieg) - der Dauerlauf soll den
        # regelmaessigen Zyklus nicht in den Chat schicken.
        print("  Bericht: %d Treffer; %d verfallen, %d ohne Richtung, "
              "%d gefiltert, %d ohne Kurs"
              % (st["treffer"], st["verfallen"], st["ohne_richtung"],
                 st["gefiltert"], st["kurs_fehler"]))
    if kill:
        print("- KILL-SWITCH: Verluste %.2f USD >= %g, keine neuen Einstiege -"
              % (z.get("verluste_usd", 0.0), w.get("max_gesamt_risiko_usd", 500)))

    if modus == "vorschau":
        for k in kand[:10]:
            print("  %-14s %-5s @ %.6g  Stop %.6g  Ziel %.6g  Score %s  C/R %s"
                  % (k["inst"], k["seite"], k["kurs"], k["stop"], k["ziel"],
                     k.get("score") if k.get("score") is not None else "?",
                     k.get("cr") if k.get("cr") is not None else "?"))
        gebunden = sum(p.get("nominal", 0) for p in z.get("positionen", []))
        print("\nOffener Bestand: %d Positionen, %.2f von %g USD Einsatz"
              % (len(z.get("positionen", [])), gebunden,
                 w.get("max_gesamt_risiko_usd", 500)))
        sperren_zeile(w, z)
        return  # bewusst kein schreibe_zustand: eine Vorschau schreibt nicht

    z["modus"] = "live" if live else "papier"
    if live:
        live_perp.pruefe_ausstiege(sys.modules[__name__], w, z)
    pruefe_ausstiege(z, w)

    if not kill:
        if live:
            grenzen = live_perp.einsatz_und_grenzen(w)
            offen_live = [p for p in z.get("positionen", [])
                          if p.get("modus") == "live"]
            plaetze = max(0, grenzen["max_offen"] - len(offen_live))
            gebunden = sum(float(p.get("einsatz_usd") or 0)
                           for p in offen_live)
            for k in kand[:max(0, min(plaetze, w.get("max_neu_je_zyklus", 5)))]:
                if gebunden + grenzen["einsatz"] > grenzen["max_gesamt"]:
                    print("  Deckel erreicht: %.2f + %.2f > %.2f USD Einsatz"
                          % (gebunden, grenzen["einsatz"],
                             grenzen["max_gesamt"]))
                    break
                if live_perp.kaufe(sys.modules[__name__], w, z, k):
                    gebunden += grenzen["einsatz"]
            print("  Live-Buch: %d von %d Plaetzen, %.2f von %.2f USD Einsatz"
                  % (len(z.get("positionen", [])), grenzen["max_offen"],
                     gebunden, grenzen["max_gesamt"]))
        else:
            freie = w.get("max_offen", 10) - len(z.get("positionen", []))
            for k in kand[:max(0, min(freie, w.get("max_neu_je_zyklus", 5)))]:
                eroeffne(z, w, k)

    gebunden = sum(p.get("nominal", 0) for p in z.get("positionen", []))
    print("\nBestand: %d Positionen, %.2f von %g USD Einsatz, "
          "kumulierte Verluste %.2f USD"
          % (len(z.get("positionen", [])), gebunden,
             w.get("max_gesamt_risiko_usd", 500),
             z.get("verluste_usd", 0.0)))
    schreibe_zustand(z)

    # Bedingung 4: Journal und Zustand ausser Haus - nach dem Herzschlag.
    # Erst schreiben, dann kopieren: ein haengendes Zweitlaufwerk darf den
    # Zyklus verzoegern, aber nicht den Herzschlag verschlucken. Ein fehlendes
    # Ziel ist kein Fehler des Laufs; der Stand steht im Zustand.
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        # Der Vermerk ist juenger als die Kopie: einmal nachziehen, damit auf
        # Q: derselbe Stand liegt. Sonst waere die Kopie in genau dem Zyklus
        # aelter, in dem sich der Spiegelstand aendert.
        wp.spiegele_journal([ZUSTAND], ziel)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))


def main():
    # omniquant/handeln.py ist der automatische Einstieg (dauerlauf.py ruft
    # dieses Skript per subprocess auf) - es meldet sich damit am Bus.
    with ereignis.lauf("handel/omniquant"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier")
    g.add_argument("--live", action="store_const", dest="modus", const="live")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen")
    a = p.parse_args()
    lauf(a.modus or "papier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
