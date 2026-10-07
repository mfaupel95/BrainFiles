"""Signal-Ausfuehrer: fuehrt aus, was der Dauerlauf nicht mehr tut.

WARUM DAS HIER STEHT
--------------------
Seit 03.10.2026 laufen markierte Spuren im Signal-Modus: der Dauerlauf
schreibt bei jeder Aenderung der Signalrichtung einen Eintrag in die
signal_queue.json der Spur, FAhrt aber SELBST keine Order. Die Entscheidung
"einstieg" wird also alle 15 Minuten getroffen und in die Queue gelegt -
ausgefuehrt wird sie von diesem Cron, unabhaengig vom Takt.

Das ist kein Workaround, sondern die gewollte Trennung: der Dauerlauf
bleibt der Monitor fuer offene Positionen (Stop/Ziel), die Signalschleife
ist asynchron und reagiert auf Signal-Wechsel, nicht auf die Uhr.

DIESER LAUF IST IMMER PAPIER, solange die Spur selbst
`freigabe.erfuellt=false` traegt. Der Weg prueft das VOR der Order - falls
eine Spur ihre Freigabe NOCH nicht hat, bleibt der Eintrag in der Queue
stehen, bis der naechste Lauf des Ausfuehrers ihn antrifft. Fuer Kraken
und mosaic, die abgeschaltet sind, steht nie wieder ein Signal in der
Queue (der Dauerlauf schreibt weiter vor_signal, aber ohne Aenderung).

WAS GEMACHT WIRD
----------------
1. signal_queue.json lesen (wenn vorhanden und nicht aelter als 30 min)
2. Auftrag nur ausfuehren, wenn die Spur handel_erlaubt=true + freigabe hat
3. Den Auftrag loeschen (damit er nicht zweimal feuert)
"""
import json
import os
import shutil
import sys
import time
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")
CACHE = os.path.join(WURZEL, "Agenten", "Hermes", "cache")
MERK = os.path.join(CACHE, "signal-executor.json")
MAX_ALTER = 1800  # 30 min

# WIEDERHOLUNG_S: ein Wartezustand wird auch dann nur alle sechs Stunden
# wiederholt. Die Meldung selbst ist nuetzlich ("diese Spur wartet auf
# Freigabe"), taeglich - nicht minuetlich.
WIEDERHOLUNG_S = 6 * 3600


def _merk_laden():
    try:
        with open(MERK, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _merk_schreiben(d):
    os.makedirs(CACHE, exist_ok=True)
    with open(MERK, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)


def melde_neu(zeilen, jetzt):
    """Nur melden, was sich GEGEN DEN LETZTEN LAUF aendert.

    `zeilen` ist {spur: meldung}. Zurueck kommt die Liste der Zeilen, die
    Max jetzt sehen soll - leer heisst: der Cron schweigt.

    WARUM (gemessen 03.10.2026 22:38-22:48): der Executor laeuft jede Minute
    und meldete den UNVERAENDERTEN Wartezustand jedes Mal erneut, dazu
    dreifach, weil drei Risikostufen je eine Queue-Datei haben (Basis,
    mittel, hoch). Drei identische Zeilen alle zwei Minuten sind keine
    Information, sie sind Lärm - und sie verdecken den einen Fall, der
    zaehlt: eine Spur, deren Zustand sich AENDERT.

    Zwei Ausnahmen gehen immer raus: eine ausgefuehrte Order und ein echter
    Fehler. Der Aufrufer uebergibt dafuer `immer` die Kennungen.
    """
    alt = _merk_laden()
    raus = []
    neu = {}
    for spur, m in zeilen.items():
        eintrag = alt.get(spur) or {}
        immer = (spur in IMMER_MELDEN or "Order" in m or "scheitert" in m
                 or "Queue abgeraeumt" in m)
        alt_genug = jetzt - float(eintrag.get("zeit") or 0) > WIEDERHOLUNG_S
        if eintrag.get("meldung") != m or immer or alt_genug:
            raus.append(m)
            neu[spur] = {"meldung": m, "zeit": jetzt}
        else:
            neu[spur] = eintrag
    # Spuren, die aus der Warteliste verschwunden sind, loescht die Merkung -
    # sonst waere die naechste Meldung dieser Spur nie wieder "neu".
    _merk_schreiben(neu)
    return raus


# Spuren, deren Meldung IMMER rausgeht, egal ob sie sich aendert.
IMMER_MELDEN = ()


def spurqueue(pfad):
    """Die Queue EINER Spur: [(inst, richtung, preis, zeit_iso)]. Leer = keine.

    Nimmt den PFAD, nicht den Spur-Namen: der Executor laeuft ueber alle
    Warteschlangen des Hauses, und je Risikostufe liegt eine eigene Datei
    mit eigenem Suffix.
    """
    if not os.path.isfile(pfad):
        return []
    try:
        with open(pfad, encoding="utf-8") as fh:
            q = json.load(fh)
    except (OSError, ValueError):
        return []
    if not isinstance(q, list):
        return []
    jetzt = datetime.now()
    q = [e for e in q if isinstance(e, (list, tuple)) and len(e) >= 3]
    # Zu alte Eintraege verfallen: der Markt ist laengst weiter, und ein
    # 30-Minuten-alter Auftrag ist kein Auftrag mehr, sondern Ballast.
    q = [e for e in q if not _verfallen(e, jetzt)]
    return q


def _verfallen(e, jetzt):
    """True, wenn der Eintrag aelter als MAX_ALTER ist (kein Ausstiegsfall)."""
    if len(e) < 4:
        return True
    try:
        t = datetime.fromisoformat(e[3])
        return (jetzt - t).total_seconds() > MAX_ALTER
    except (ValueError, TypeError):
        return True


def ausfuehren(spur, eintrag):
    """Einen Queue-Eintrag ausfuehren. Rueckgabe: (ok, meldung)."""
    import importlib.util
    inst, richtung = eintrag[0], eintrag[1]
    preis = eintrag[2] if len(eintrag) > 2 else 0.0
    # Wachen laden
    wpfad = os.path.join(HANDEL, spur, "wachen.json")
    try:
        with open(wpfad, encoding="utf-8") as fh:
            w = json.load(fh)
    except (OSError, ValueError):
        return False, "wachen.json nicht lesbar (%s)" % spur
    # Pruefen, ob die Spur ueberhaupt live freigegeben ist.
    # T-351 (07.10.2026): eine Spur, die NICHT live ist, leert ihre Queue
    # sofort. Vorher sammelten sich Eintraege bis zum 30-Minuten-Verfall -
    # eine Spur, die von live auf papier zurueckgeschaltet wurde, legte
    # weiter Signale ab, die niemand abholt.
    if not w.get("handel_erlaubt"):
        return False, "%s: handel_erlaubt=false, Queue abgeraeumt" % spur
    if not (w.get("freigabe") or {}).get("erfuellt"):
        return False, "%s: freigabe nicht erteilt, Queue abgeraeumt" % spur
    # Orderweg laden
    #
    # T-346 (04./05.10.2026): dieser Import stand VOR dem sys.path-Eintrag. Der
    # Cron startet aus Agenten/Hermes/scripts/, dort liegt spur_buch.py nicht ->
    # ModuleNotFoundError, failure_streak 12 (Hermes-Cron 50921798e27a, jede
    # Minute); der Executor brach bei JEDER Ausfuehrung ab und keine Spur mit
    # trigger_modus=signal kam je zu einem Einstieg. Der Eintrag muss VOR dem
    # Import stehen. Die Hausregel fuer Spuren-Imports verlangt ausserdem die
    # Pruefung gegen __file__: sonst laedt ein gleichnamiges Modul aus einem
    # anderen Verzeichnis (hier: der echte scanner/handeln.py statt der Spur).
    # Die drei Tore weiter unten machten es richtig; nur dieser erste stand falsch.
    if HANDEL not in sys.path:
        sys.path.insert(0, HANDEL)
    try:
        from spur_buch import orderweg, venue_inst
    except ImportError as e:
        return False, ("%s: spur_buch.py nicht ladbar (%s) - im Zweifel KEINE "
                       "Order, Auftrag bleibt in der Queue" % (spur, e))
    if not os.path.abspath(sys.modules["spur_buch"].__file__).startswith(
            os.path.abspath(HANDEL) + os.sep):
        return False, ("%s: spur_buch kam aus %s statt aus %s - im Zweifel "
                       "KEINE Order" % (spur, sys.modules["spur_buch"].__file__,
                                         HANDEL))

    weg = orderweg(w)
    if weg is None:
        return False, "%s: kein Orderweg fuer boerse=%s" % (spur, w.get("boerse"))
    # Instument an der Boerse
    vi = venue_inst(inst, w)
    # Handelsregeln Punkt 3: KEIN Freigabefenster, KEINE Order.
    # spuerren_live() in spur_buch prueft das beim normalen Weg - dieser
    # Executor laeuft ausserhalb und muss es selbst tun. Ohne diese Zeile
    # wuerde eine Queue aus einem live-faehigen Track eine echte Order OHNE
    # Fenster setzen: genau die Luecke, die Handelsregel Punkt 3 schliesst.
    try:
        if HANDEL not in sys.path:
            sys.path.insert(0, HANDEL)
        import freigabefenster
        if not freigabefenster.lade(spur).offen():
            return False, ("%s: kein offenes Freigabefenster (Handelsregeln "
                           "Punkt 3) - Auftrag bleibt in der Queue" % spur)
    except ImportError:
        return False, ("%s: freigabefenster.py nicht erreichbar - im Zweifel "
                       "KEINE Order" % spur)
    except Exception as e:                                      # noqa: BLE001
        return False, ("%s: Freigabefenster unlesbar (%s) - im Zweifel KEINE "
                       "Order" % (spur, e))
    # Gebuehren-Tor (03.10.2026): die Spur muss die Zahl tragen, nicht nur
    # den Haken. 0,09 % Excess gegen 0,10 % Gebuehr ist ein Verlust, und
    # eine Spur mit einem BEFUND im Audit ist beanstandet, nicht gemessen.
    try:
        if HANDEL not in sys.path:
            sys.path.insert(0, HANDEL)
        import freigabe_tor
        ok_tor, g_tor = freigabe_tor.pruefe(spur, w)
        if not ok_tor:
            return False, ("%s: Gebuehren-Tor zu - %s"
                           % (spur, "; ".join(g_tor)))
    except ImportError:
        # Das Tor fehlt: im Zweifel KEINE Order. Ein Torschutz, der bei
        # seinem eigenen Ausfall durchlaesst, ist kein Torschutz.
        return False, ("%s: freigabe_tor.py nicht erreichbar - im Zweifel "
                       "KEINE Order" % spur)
    except Exception as e:                                      # noqa: BLE001
        return False, ("%s: Gebuehren-Tor unlesbar (%s) - im Zweifel KEINE "
                       "Order" % (spur, e))
    # BASIS-DECKEL (03.10.2026): die Basis darf nicht ueber 20 % des
    # Kapitals liegen. Bestehende Positionen bleiben - nur NEUE Einstiege
    # werden abgelehnt.
    try:
        if HANDEL not in sys.path:
            sys.path.insert(0, HANDEL)
        import basis_deckel_tor
        gesperrt, grund = basis_deckel_tor.ueber_dem_deckel(inst)
        if gesperrt:
            return False, "%s: %s - Auftrag bleibt in der Queue" % (spur, grund)
    except ImportError:
        return False, ("%s: basis_deckel_tor.py nicht erreichbar - im Zweifel "
                       "KEINE Order" % spur)
    except Exception as e:                                      # noqa: BLE001
        return False, ("%s: Basis-Deckel unlesbar (%s) - im Zweifel KEINE "
                       "Order" % (spur, e))
    # Freies Guthaben und Mindestdeckel
    try:
        gu = weg.guthaben_waehrung()
        mindest = float(w.get("mindest_guthaben") or w.get("mindest_guthaben_usd") or 0)
        if gu < mindest:
            return False, ("%s: Guthaben %.2f unter Mindest %.2f - Auftrag bleibt"
                           % (spur, gu, mindest))
    except Exception as e:
        return False, "%s: Guthaben nicht abrufbar (%s)" % (spur, e)
    # Einstieg
    menge = None
    try:
        menge, fehler = weg.menge_fuer(vi, w.get("max_pro_trade_usd", 100.0), preis)
    except Exception as e:
        return False, "%s: menge_fuer fehlgeschlagen (%s)" % (spur, e)
    if menge is None or menge <= 0:
        return False, ("%s: menge_fuer: %s (inst=%s, preis=%.6f, deckel=%s)"
                       % (spur, fehler, vi, preis, w.get("max_pro_trade_usd", 100)))
    try:
        if richtung == "short":
            weg.markt_verkauf(vi, menge)
        else:
            weg.markt_kauf(vi, menge)
    except Exception as e:
        return False, ("%s: Order scheitert (%s) - steckt das Instrument im "
                       "Boersenmarkt?" % (spur, e))
    return True, "%s: %s %s @ %.6f" % (spur, richtung.upper(), inst, preis)


def alle_queues():
    """Jede Spur des Hauses mit einer Warteschlange - nicht eine feste.

    Die erste Fassung hatte `spur = "moondev_signalwelle"` fest im Code.
    Das raeumte genau EINE von dreizehn Queues ab; die uebrigen wuchsen
    unbegrenzt (gemessen 03.10.2026: moondev_topmovers mit 59 Eintraegen
    in 88 Minuten, davon je Instrument dreimal dieselbe Richtung - ein
    Wechsel je Risikostufe). Eine Warteschlange ist ein Briefkasten, kein
    Protokoll: sie gehoert geleert zu werden oder begrenzt zu wachsen.
    """
    gefunden = []
    for name in sorted(os.listdir(HANDEL)):
        ordner = os.path.join(HANDEL, name)
        if not os.path.isdir(ordner):
            continue
        for datei in os.listdir(ordner):
            if datei.startswith("signal_queue") and datei.endswith(".json"):
                gefunden.append((name, os.path.join(ordner, datei)))
    return gefunden


def zeilen_je_spur(je_spur):
    """Je SPUR eine Meldungszeile.

    Drei Risikostufen (Basis, mittel, hoch) haben je eine signal_queue*.json.
    Ohne diese Zusammenfassung stand dieselbe Spur dreifach in jeder
    Meldung (gemessen 03.10.2026, 22:38-22:48).
    """
    zeilen = {}
    for spur, d in je_spur.items():
        m = d["meldung"]
        if d["stufen"] > 1 and not d["ok"]:
            m += "  (%d Risikostufen)" % d["stufen"]
        zeilen[spur] = m
    return zeilen


def main():
    # Je SPUR eine Zeile, nicht je Queue-Datei: drei Risikostufen (Basis,
    # mittel, hoch) haben je eine signal_queue*.json, und dieselbe Spur
    # stand dadurch dreifach in jeder Meldung (gemessen 03.10.2026).
    je_spur = {}
    for spur, pfad in alle_queues():
        eintraege = spurqueue(pfad)
        if not eintraege:
            # Alles verfallen: leeren, damit die Datei nicht weiterwaechst.
            if os.path.getsize(pfad) > 2:
                with open(pfad, "w", encoding="utf-8") as fh:
                    json.dump([], fh)
            continue
        ok, meldung = ausfuehren(spur, eintraege[0])
        if not ok and "Queue abgeraeumt" in meldung:
            # T-351: Spur nicht live -> Queue leeren, nicht warten.
            shutil.copy2(pfad, pfad + ".bak-" +
                         datetime.now().strftime("%Y%m%d%H%M%S"))
            with open(pfad, "w", encoding="utf-8") as fh:
                json.dump([], fh, ensure_ascii=False, indent=1)
            if spur not in je_spur:
                je_spur[spur] = {"stufen": 1, "meldung": meldung, "ok": False}
            continue
        if not ok and "bleibt" in meldung:
            if spur not in je_spur:
                je_spur[spur] = {"stufen": 0, "meldung": meldung, "ok": False}
            je_spur[spur]["stufen"] += 1
            # Die Datei wird TROTZDEM neu geschrieben, sonst bleiben die
            # abgelaufenen Eintraege fuer immer stehen: `spurqueue` filtert
            # sie nur aus der RUECKGABE, nicht aus der Datei. Genau daran
            # blieb moondev_topmovers bei 4441 B stehen, nachdem der
            # Executor schon einmal gelaufen war.
            rest = eintraege[-20:]
            if os.path.getsize(pfad) != len(json.dumps(rest)):
                shutil.copy2(pfad, pfad + ".bak-" +
                             datetime.now().strftime("%Y%m%d%H%M%S"))
                with open(pfad, "w", encoding="utf-8") as fh:
                    json.dump(rest, fh, ensure_ascii=False, indent=1)
            continue
        rest = eintraege[1:] if ok else eintraege
        rest = rest[-20:]                  # Deckel: 20 sind 20 echte Wechsel
        shutil.copy2(pfad, pfad + ".bak-" + datetime.now().strftime("%Y%m%d%H%M%S"))
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(rest, fh, ensure_ascii=False, indent=1)
        zeile = meldung if ok else "Signal nicht ausgefuehrt: %s" % meldung
        if spur not in je_spur:
            je_spur[spur] = {"stufen": 1, "meldung": zeile, "ok": ok}
        elif je_spur[spur]["ok"] and ok:
            # Zwei Orders in EINEM Lauf (zwei Stufen): beide melden, das ist
            # je eine echte Order und damit je eine eigene Nachricht wert.
            je_spur[spur]["meldung"] += " || " + zeile
    if not je_spur:
        return 0
    zeilen = zeilen_je_spur(je_spur)
    # Nur melden, was sich gegen den letzten Lauf aendert - sonst schweigt
    # der Cron, statt minuetlich denselben Wartezustand zu wiederholen.
    for zeile in melde_neu(zeilen, time.time()):
        print(zeile)
    return 0


if __name__ == "__main__":
    sys.exit(main())