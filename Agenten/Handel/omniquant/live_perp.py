"""Omniquants Live-Zweig auf Kraken Futures - abgetrennt, damit der Papierkern
und die neun `spur_buch`-Spuren unberuehrt bleiben.

Auftrag Max 01.10.2026: "Omniquant Handel Freigabe auf kraken live", nachgemeldet
"aber mit perp und hebel x6".

Aufbau (nach dem kraken/handeln.py-Muster)
------------------------------------------
* `SPUR = "omniquant"` - eigener Fensterschluessel. Ein fremder Name wuerde das
  Fenster mit der Nachbarspur teilen: ein `/ja_kraken` schaltete beide scharf.
* Die Sperrenkette nennt JEDEN Grund einzeln. `dauerlauf.nur_fenster_fehlt()`
  liest die Vorschau-Zeile und fragt nur dann eine Freigabe an, wenn GENAU EIN
  Grund das Wort "Freigabefenster" traegt - deshalb ist der Text eine
  Schnittstelle, kein Kommentar.
* Beide Wege zu Punkt 3: Bildschirmfenster ODER Zeitfenster. Der Dauerlauf setzt
  `MAXHIRN_ROUTINE=1`, damit ist `sitzung_da()` immer False - wer nur den
  Bildschirm prueft, baut eine Spur, die im Dauerlauf NIE live geht.
* Der Schutz-Stop kommt DIREKT nach dem Kauf. Eine nackte Live-Position ist kein
  Handel, sondern ein offenes Risiko.
* Jede Fehlerstelle schreibt eine Journalzeile (`aktion="fehler"`), damit ein
  ausbleibender Einstieg eine beantwortbare Frage ist statt stumm.
* Jeder Ausgang schreibt Zustand und spiegelt - auch der abbrechende. Sonst
  kann das Herzschlag-Tor seinen Wert nie erneuern und bleibt fuer immer zu.

Was hier NICHT steht
--------------------
Keine Signatur, keine Kontraktgroesse, keine Margenstufe - das liegt alles in
`nautilus_kraken/kraken_futures.py`. `kraken_perp.py` uebersetzt Omniquants
Namen in PF_-Symbole und rechnet das Sizing (Nennwert = Einsatz x Hebel).
"""

import json
import os
import sys
from datetime import datetime, timezone
from importlib.util import spec_from_file_location, module_from_spec

import kraken_perp

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

SPUR = "omniquant"

# Freigabefenster ueber den PFAD laden: die Spur hat ihren eigenen Ordner als
# sys.path[0], ein blankes `import freigabefenster` faellt mit
# ModuleNotFoundError um - und der best-effort-except meldete dann "kein
# Zeitfenster", obwohl das Fenster offen war.
_fw_datei = os.path.join(HANDEL, "freigabefenster.py")
_fg_datei = os.path.join(HANDEL, "freigabe.py")


def _lade(pfad, name):
    spec = spec_from_file_location(name, pfad)
    modul = module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def zeitfenster_offen():
    """Liest das Zeitfenster. Best effort - im Zweifel False, aber LAUT.

    Eine stumme False-Rueckgabe behauptet "kein Zeitfenster", obwohl nur der
    Import scheiterte. Der Fehler geht deshalb nach stderr.
    """
    try:
        fw = _lade(_fw_datei, "omniquant_freigabefenster")
        return bool(fw.lade(SPUR).offen())
    except Exception as e:                               # noqa: BLE001
        sys.stderr.write("Zeitfenster nicht lesbar: %s: %s\n"
                         % (type(e).__name__, e))
        return False


def sitzung_da():
    """Sitzt jemand am Bildschirm? Im Dauerlauf (MAXHIRN_ROUTINE) nie."""
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:                                    # noqa: BLE001
        return False


def freigabe_erfuellt(w):
    """Bedingung 1: der von Hand gesetzte Haken - kein nachgerechneter Wert."""
    return (w.get("freigabe") or {}).get("erfuellt") is True


def freigabe_protokoll(z, was, grund=None):
    """Schreibt den Vorgang ins Freigabe-Audit, wenn das Modul es anbietet."""
    try:
        fg = _lade(_fg_datei, "omniquant_freigabe")
        if hasattr(fg, "audit"):
            fg.audit(SPUR, was, grund)
    except Exception as e:                               # noqa: BLE001
        sys.stderr.write("Freigabe-Audit nicht schreibbar: %s\n" % e)


# --- Sperren ----------------------------------------------------------------

def einsatz_und_grenzen(w):
    """Die Zahlen, mit denen der LIVE-Lauf rechnet (nicht die Papierwerte)."""
    return {
        "einsatz": kraken_perp.einsatz_usd(w, True),
        "hebel": kraken_perp.hebel(w),
        "max_offen": int(w.get("live_max_offene_positionen",
                               w.get("max_offen", 10))),
        "max_gesamt": float(w.get("live_max_gesamt_usd",
                                  w.get("max_gesamt_risiko_usd", 500))),
        "mindest_guthaben": float(w.get("mindest_guthaben_usd", 0) or 0),
    }


def live_sperren(w, z):
    """Gruende, warum --live nicht scharf schalten kann. Jeder einzeln.

    Die Reihenfolge ist Absicht: kommt nur EIN Grund heraus und traegt er das
    Wort "Freigabefenster", oeffnet der Dauerlauf die Anfrage von selbst.
    """
    g = []
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false")
    if not freigabe_erfuellt(w):
        g.append("freigabe.erfuellt=false (Bedingung 1)")
    if not sitzung_da() and not zeitfenster_offen():
        g.append("Freigabefenster nicht offen - keine Sitzung am Bildschirm "
                 "und kein Zeitfenster (Handelsregeln Punkt 3)")
    try:
        if not kraken_perp.schluessel_vorhanden():
            g.append("Kraken-Futures-Schluessel fehlen")
    except Exception as e:                               # noqa: BLE001
        g.append("Schluessel nicht pruefbar (%s)" % type(e).__name__)
    if kraken_perp.demo_modus():
        g.append("Demo-Konto gesetzt")

    # Guthaben-Tor: hier steht die UNTERGRENZE aus der wachen.json. Was die
    # Boerse fuer den naechsten Satz WIRKLICH verlangt, haengt am Markt und an
    # der Kontraktzahl - das rechnet `kaufe()` unmittelbar vor der Order nach
    # (`kraken_perp.einschuss_usd`). Die Vorpruefung soll frueh warnen, nicht
    # das Sizing nachbauen; ein fest eingetragenes "noetig" waere sonst eine
    # zweite Wahrheit neben der Boerse. (Die tote Schleife, die einen
    # Kandidatenkurs aus dem Zustand lesen wollte, ist am 01.10.2026 entfallen -
    # der Zustand fuehrt keine Kandidatenkurse, T-282.)
    grenzen = einsatz_und_grenzen(w)
    try:
        frei = kraken_perp.guthaben_usd()
    except Exception as e:                               # noqa: BLE001
        g.append("Guthaben nicht abrufbar (%s)" % type(e).__name__)
        frei = None
    if frei is not None:
        noetig = grenzen["mindest_guthaben"]
        if noetig and frei < noetig:
            g.append("nur %.2f USD freie Margin, noetig %.2f"
                     % (frei, noetig))
    if z.get("verluste_usd", 0.0) >= w.get("max_gesamt_risiko_usd", 500):
        g.append("Kill-Switch: Verluste %.2f USD >= %g"
                 % (z.get("verluste_usd", 0.0),
                    w.get("max_gesamt_risiko_usd", 500)))
    return g


def sperren_zeile(w, z):
    """Druckt die Zeile, die der Dauerlauf parst. Immer - auch bei leerer Liste.

    Eine Sperrzeile, die nur im Fehlerfall gedruckt wird, ist von "nicht
    geprueft" nicht zu unterscheiden.
    """
    try:
        g = live_sperren(w, z)
    except Exception as e:                               # noqa: BLE001
        print("Live waere gesperrt durch: nicht bestimmbar (%s: %s)"
              % (type(e).__name__, e))
        return
    print("Live waere gesperrt durch: " + ("; ".join(g) if g else "nichts"))


# --- Order ------------------------------------------------------------------

def markte_laden():
    """Die Marktliste der Boerse EINMAL je Lauf holen - auf EINSTIEG und AUSSTIEG.

    `kraken_perp.maerkte()` liefert absichtlich nur die bereits geladene
    Liste (kein Netzzugriff auf dem heissen Pfad). Wird `lade_maerkte()`
    nicht gerufen, verweigert `pf_markt` JEDEN Einstieg mit "Marktliste nicht
    geladen" - so geschehen am 01.10.2026: 19 Fehlerzeilen im echten Journal,
    alle HBAR-USDT, alle im Live-Modus, obwohl PF_HBARUSD existiert.

    Rueckgabe: Anzahl der Maerkte, oder 0 mit Fehler auf stderr. Ein Fehler
    hier ist kein Absturz - der Lauf geht weiter. Fuer den Ausstieg ist das
    anders: eine offene Position, deren Markt sich nicht auflosen laesst,
    bleibt liegen. Deshalb meldet `pruefe_ausstiege()` das selbst (T-306).
    """
    lader = getattr(kraken_perp, "lade_maerkte", None)
    if lader is None:
        return 0
    try:
        return int(lader())
    except Exception as e:                               # noqa: BLE001
        sys.stderr.write("Marktliste nicht ladbar: %s: %s\n"
                         % (type(e).__name__, e))
        return 0


def _journal_schreiben(handeln, **felder):
    """Eine Journalzeile ueber den Kern der Spur - eine Buchhaltung, kein Zwilling."""
    handeln.journal(**felder)


def kaufe(handeln, w, z, kand):
    """Ein echter Einstieg. Rueckgabe: die gebuchte Position oder None.

    Reihenfolge, und jede Stufe kann ablehnen:
      1. Paar aufloesen (unbekannt/MAGIC = lauter Fehler)
      2. Hebel pruefen (1 Kontrakt ZEC waere Hebel 28,7 statt 6)
      3. Boersengroesse und Tageskurs holen
      4. Freigabe: Zeitfenster ODER Bildschirm
      5. Marktkauf, Fuellung abwarten
      6. Schutz-Stop setzen - ohne ihn wird die Position zurueckgedreht
    """
    inst = kand["inst"]
    grenzen = einsatz_und_grenzen(w)

    # Zielmarkt-Auskunft fuer Instrumente AUSSERHALB der geprueften Tabelle
    # (T-282, 01.10.2026): die Marktliste wird einmal je Lauf geholt, die
    # Ableitung nur nach ausdruecklicher Freigabe in den Wachen benutzt. Faellt
    # die Liste aus, bleiben die eingetragenen Instrumente handelbar - ein
    # abgeleiteter Name wird dann NICHT gehandelt (nicht nachweisbar = kein
    # Markt).
    if not kraken_perp.eingetragen(inst):
        erlaubt = bool(w.get("live_pf_ableitung"))
        kraken_perp.setze_ableitung(erlaubt)
        if not erlaubt:
            print("  gesperrt: %s steht nicht in der geprueften Tabelle und "
                  "live_pf_ableitung ist nicht gesetzt" % inst)
            _journal_schreiben(handeln, zeit=handeln._jetzt(), modus="live",
                               aktion="fehler", inst=inst,
                               grund="live_pf_ableitung=false")
            return None
        try:
            kraken_perp.lade_maerkte()
        except Exception as e:                               # noqa: BLE001
            sys.stderr.write("Marktliste nicht abrufbar: %s: %s\n"
                             % (type(e).__name__, e))

    try:
        kurs = kraken_perp.letzter_kurs(inst)
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, inst, "Kurs nicht abrufbar: %s" % e)
        return None

    grund = kraken_perp.hebel_grund(inst, grenzen["einsatz"], kurs, w)
    if grund:
        print("  gesperrt: %s" % grund)
        _journal_schreiben(handeln, zeit=handeln._jetzt(), modus="live",
                           aktion="fehler", inst=inst,
                           grund="hebel: " + grund)
        return None

    kontrakte = kraken_perp.kontrakte_fuer(inst, grenzen["einsatz"], kurs, w)

    # Guthaben-Tor JE ORDER, nicht nur global: der Einschuss haengt am Markt.
    try:
        frei = kraken_perp.guthaben_usd()
        noetig = kraken_perp.einschuss_usd(inst, kontrakte, kurs)
        if frei < noetig:
            print("  gesperrt: %d Kontrakte %s brauchen %.2f USD Einschuss, "
                  "frei sind %.2f" % (kontrakte, inst, noetig, frei))
            _journal_schreiben(handeln, zeit=handeln._jetzt(), modus="live",
                               aktion="fehler", inst=inst,
                               grund="guthaben: %.2f < %.2f" % (frei, noetig))
            return None
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, inst, "Guthaben/Einschuss nicht pruefbar: %s" % e)
        return None

    if not (sitzung_da() or zeitfenster_offen()):
        _fehler(handeln, inst, "Freigabefenster nicht offen")
        return None

    try:
        antwort = kraken_perp.markt_kauf(inst, kontrakte)
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, inst, "Kauf abgelehnt: %s" % e)
        return None

    bestellung = antwort.get("sendStatus") if isinstance(antwort, dict) else {}
    kennung = (bestellung or {}).get("order_id") or antwort
    kurs_ist = kurs

    # Die Order EXISTIERT ab hier - das Geld ist gebunden. Die Fill wird
    # abgewartet; bestaetigt=False heisst "Bestaetigung offen", NICHT "0".
    # Der alte Weg las sofort, bekam 0 und bestellte Stop UND Rueckdrehung
    # mit Groesse 0: Kraken antwortete invalidArgument: 0, die Rueckdrehung
    # blieb wirkungslos und wurde als Erfolg gemeldet (T-306).
    fuellung_bestaetigt = False
    try:
        gefuellt, fuellung_bestaetigt = kraken_perp.gefuellte_menge(kennung)
        if gefuellt:
            kontrakte = gefuellt
    except Exception as e:                               # noqa: BLE001
        sys.stderr.write("Fuellungsmenge nicht lesbar: %s\n" % e)
    if not fuellung_bestaetigt:
        print("  Fuellung fuer %s unbestaetigt - %d Kontrakte bestellt, "
              "mit dieser Groesse gebucht (Kennung %s)"
              % (inst, kontrakte, kennung), file=sys.stderr)
    if kontrakte < 1:
        _fehler(handeln, inst, "Sizing ergab 0 Kontrakte - keine Order")
        return None

    stop = float(kand["stop"])
    algo_id = None
    try:
        s_antwort = kraken_perp.stop_setzen(inst, kontrakte, stop)
        algo_id = (s_antwort or {}).get("sendStatus", {}).get("order_id") \
            if isinstance(s_antwort, dict) else None
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, inst, "Schutz-Stop fehlgeschlagen: %s" % e)
        # Ohne Stop wird zurueckgedreht - eine nackte Position ist kein Handel.
        # Die Rueckdrehung gilt erst als gelungen, wenn die BOERSE die Position
        # danach nicht mehr fuehrt. Am 01.10.2026 wurde sie mit Groesse 0
        # abgeschickt, blieb wirkungslos und wurde trotzdem als Erfolg
        # protokolliert (T-306): 5706 Kontrakte ohne Schutz.
        zurueck_ok = False
        try:
            kraken_perp.markt_verkauf(inst, kontrakte)
            offen = kraken_perp.offene_positionen(inst, fuer_ausstieg=True)
            zurueck_ok = not any(p.get("size") for p in offen)
        except Exception as e2:                          # noqa: BLE001
            _fehler(handeln, inst, "Rueckdrehung fehlgeschlagen: %s" % e2)
        if zurueck_ok:
            _fehler(handeln, inst, "Position wegen fehlendem Stop zurueckgedreht")
        else:
            _fehler(handeln, inst,
                    "SICHERHEITSLÜCKE: Stop fehlgeschlagen UND Rueckdrehung "
                    "ohne Wirkung - die Boerse fuehrt die Position weiter. "
                    "Kein weiterer Einstieg, bis das von Hand geklaert ist.")
        return None

    p = {
        "inst": inst, "seite": "long",
        "einstieg": kurs_ist, "stop": stop, "ziel": float(kand["ziel"]),
        "nominal": round(kraken_perp.nennwert_usd(inst, kontrakte, kurs_ist), 4),
        "kontrakte": kontrakte,
        "einsatz_usd": grenzen["einsatz"],
        "hebel": kraken_perp.effektiver_hebel(inst, kontrakte, kurs_ist,
                                              grenzen["einsatz"]),
        "modus": "live", "boerse": "kraken_futures",
        "paar": kraken_perp.paar_fuer(inst),
        "ord_id": kennung, "stop_algo_id": algo_id,
        "eroeffnet": handeln._heute(),
        "score": kand.get("score"), "cr": kand.get("cr"),
        "mfe_pct": 0.0, "mae_pct": 0.0,
    }
    z.setdefault("positionen", []).append(p)
    _journal_schreiben(handeln, zeit=handeln._jetzt(), modus="live",
                       aktion="eroeffnen", inst=inst, seite="long",
                       preis=kurs_ist, einsatz_usd=grenzen["einsatz"],
                       stop=stop, ziel=p["ziel"],
                       grund="prognose-treffer-live")
    print("OMNIQUANT LIVE EINSTIEG: %s %d Kontrakte @ %.6g (Nennwert %.2f USD, "
          "Hebel %.2f, Stop %.6g)"
          % (inst, kontrakte, kurs_ist, p["nominal"], p["hebel"], stop))
    return p


def stopdeckung_pruefen(handeln, p):
    """Hat die offene Live-Position ihren Notausstieg noch - und wenn nicht,
    wird er nachgesetzt.

    Zwei Voraussetzungen, beide am 05.10.2026 gemessen:

    * Der Weg ist `/openorders`, NICHT `/editorder` - das ist der
      SPOT-Endpunkt und antwortet in jeder Variante mit
      `requiredArgumentMissing`. Wer ihn benutzt, meldet "nicht lesbar"
      und haelt eine Position ohne erkannten Schutz fuer ungeschuetzt
      (dieselbe Fehlerklasse wie xperp 21.09. und ZRO 02.10.).
    * "Ein Treffer" ist kein Beweis. T-323 belegte eine Position mit 145
      Kontrakten und einem Stop ueber 126 - 19 Kontrakte liefen ungeschuetzt,
      ohne dass ein Abruf das anzeigt. Deshalb wird die MENGE verglichen.

    Rueckgabe: True, wenn die Position am Ende gedeckt ist. Ein fehlgeschlagener
    Nachsatz ist KEIN stiller Fehler - die Journalzeile benennt die Luecke, weil
    eine Position ohne Notausstieg die groesste offene Luecke im Haus ist.
    """
    inst = p.get("inst")
    try:
        gedeckt = kraken_perp.schutzstop_vorhanden(
            inst, kontrakte=p.get("kontrakte"), fuer_ausstieg=True)
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, inst,
                "Stop-Deckung nicht pruefbar (%s: %s) - Position bleibt, "
                "Einmalkontrolle von Hand noetig" % (type(e).__name__, e))
        return False
    if gedeckt:
        return True
    stop = p.get("stop")
    if not stop:
        _fehler(handeln, inst, "KEIN Stop im Buch - die Position ist an der "
                "Boerse ungeschuetzt")
        return False
    try:
        antwort = kraken_perp.stop_setzen(inst, int(p.get("kontrakte") or 0),
                                          float(stop))
        algo = (antwort or {}).get("sendStatus", {}).get("order_id") \
            if isinstance(antwort, dict) else None
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, inst, "SICHERHEITSLÜCKE: Stop fehlte an der Boerse "
                "und liess sich nicht nachsetzen (%s)" % e)
        return False
    p["stop_algo_id"] = algo
    print("  Schutz-Stop nachgesetzt: %s %.6g / %s Kontrakte (orderId %s)"
          % (inst, float(stop), p.get("kontrakte"), algo))
    try:
        if not kraken_perp.schutzstop_vorhanden(inst, kontrakte=p.get("kontrakte"),
                                                fuer_ausstieg=True):
            _fehler(handeln, inst,
                    "Stop wurde gesetzt, deckt aber die ganze Position nicht")
            return False
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, inst, "Nachkontrolle der Stop-Deckung nicht lesbar "
                "(%s: %s)" % (type(e).__name__, e))
        return False
    return True


def pruefe_ausstiege(handeln, w, z):
    """Live-Ausstiege: Stop, Ziel, Frist. Nur Positionen mit modus=live."""
    offen = [p for p in z.get("positionen", []) if p.get("modus") == "live"]
    if not offen:
        return
    # Vor jedem Stop-/Exit-Pfad den gebuchten Bestand mit der Boerse abgleichen.
    # Fehlt die Position oder weicht die Menge ab, ist das Buch ein Geister-/
    # Teilbestand: nicht blind eine neue Stop- oder Market-Order senden.
    aktiv = []
    for p in list(offen):
        try:
            boersen_pos = kraken_perp.offene_positionen(
                p["inst"], fuer_ausstieg=True) or []
        except Exception as e:                               # noqa: BLE001
            _fehler(handeln, p["inst"],
                    "Live-Bestand nicht abgleichbar (%s: %s) - keine Order gesendet"
                    % (type(e).__name__, e))
            continue
        seite = "short" if p.get("seite") == "short" else "long"
        passend = [q for q in boersen_pos
                   if str(q.get("side", "")).lower() == seite]
        menge = sum(float(q.get("size") or 0) for q in passend)
        erwartet = float(p.get("kontrakte") or 0)
        if erwartet <= 0 or abs(menge - erwartet) > 1e-9:
            _fehler(handeln, p["inst"],
                    "GEISTERPOSITION/Bestandsabweichung: Buch %s %g, Boerse %s %g; "
                    "keine automatische Ausbuchung oder Order"
                    % (seite, erwartet, seite, menge))
            continue
        aktiv.append(p)
    offen = aktiv
    if not offen:
        return
    # VOR jeder Ausstiegsentscheidung pruefen, ob die volle Menge geschuetzt ist.
    for p in list(offen):
        stopdeckung_pruefen(handeln, p)
    # Die Marktliste wird auf BEIDEN Wegen gebraucht. Sie war nur im
    # Einstiegszweig geladen - dadurch blieb jede offene Position unauflösbar,
    # selbst nachdem das Gate sie nicht mehr blockierte (T-306).
    try:
        markte_laden()
    except Exception as e:                               # noqa: BLE001
        _fehler(handeln, offen[0]["inst"],
                "Marktliste nicht ladbar, Ausstieg moeglich: %s" % e)
    for p in list(offen):
        try:
            # fuer_ausstieg=True: das Einstiegs-Gate (live_pf_ableitung)
            # darf eine OFFENE Position nicht am Schliessen hindern (T-306).
            kurs = kraken_perp.letzter_kurs(p["inst"], fuer_ausstieg=True)
        except Exception as e:                           # noqa: BLE001
            _fehler(handeln, p["inst"], "Ausstiegskurs nicht abrufbar: %s" % e)
            continue
        grund = _ausstiegsgrund(handeln, p, kurs, w)
        if not grund:
            continue
        try:
            kraken_perp.markt_verkauf(p["inst"], int(p["kontrakte"]))
        except Exception as e:                           # noqa: BLE001
            _fehler(handeln, p["inst"], "Verkauf abgelehnt: %s" % e)
            continue
        try:
            kraken_perp.order_stornieren(p.get("stop_algo_id"))
        except Exception as e:                           # noqa: BLE001
            sys.stderr.write("Stop nicht storniert: %s\n" % e)
        z["positionen"].remove(p)
        _journal_schreiben(handeln, zeit=handeln._jetzt(), modus="live",
                           aktion="verkauf", inst=p["inst"], seite="long",
                           preis=kurs, grund=grund)
        print("OMNIQUANT LIVE AUSSTIEG: %s @ %.6g (%s)"
              % (p["inst"], kurs, grund))


def _ausstiegsgrund(handeln, p, kurs, w):
    """Stop vor Ziel - ein gerissener Stop behaelt den Vorrang."""
    if kurs <= float(p["stop"]):
        return "stop"
    if kurs >= float(p["ziel"]):
        return "ziel"
    tage = w.get("max_halte_dauer_tage", 14)
    try:
        seit = (datetime.now(timezone.utc)
                - datetime.fromisoformat(p["eroeffnet"] + "T00:00:00+00:00"))
        if seit.days >= tage:
            return "frist"
    except Exception:                                    # noqa: BLE001
        pass
    return None


def _fehler(handeln, inst, text):
    """Jede Fehlerstelle schreibt eine Zeile - sonst ist Stille nicht deutbar."""
    print("  FEHLER %s: %s" % (inst, text))
    try:
        _journal_schreiben(handeln, zeit=handeln._jetzt(), modus="live",
                           aktion="fehler", inst=inst, grund=text)
    except Exception as e:                               # noqa: BLE001
        sys.stderr.write("Fehlerzeile nicht schreibbar: %s\n" % e)


def kandidaten_grenzen(w):
    """Die Live-Grenzen als Zeilen fuer --wachen (was der Live-Lauf WIRKLICH liest)."""
    g = einsatz_und_grenzen(w)
    return ["  %-28s %s" % ("live_einsatz_usd", g["einsatz"]),
            "  %-28s %s" % ("hebel", g["hebel"]),
            "  %-28s %s" % ("live_max_offene_positionen", g["max_offen"]),
            "  %-28s %s" % ("live_max_gesamt_usd", g["max_gesamt"]),
            "  %-28s %s" % ("mindest_guthaben_usd", g["mindest_guthaben"])]