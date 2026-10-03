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
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")
MAX_ALTER = 1800  # 30 min


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
    # Pruefen, ob die Spur ueberhaupt live freigegeben ist
    if not w.get("handel_erlaubt"):
        return False, "%s: handel_erlaubt=false, Auftrag bleibt in Queue" % spur
    if not (w.get("freigabe") or {}).get("erfuellt"):
        return False, "%s: freigabe nicht erteilt, Auftrag bleibt" % spur
    # Orderweg laden
    from spur_buch import orderweg, venue_inst
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


def main():
    berichte = []
    for spur, pfad in alle_queues():
        eintraege = spurqueue(pfad)
        if not eintraege:
            # Alles verfallen: leeren, damit die Datei nicht weiterwaechst.
            if os.path.getsize(pfad) > 2:
                with open(pfad, "w", encoding="utf-8") as fh:
                    json.dump([], fh)
            continue
        ok, meldung = ausfuehren(spur, eintraege[0])
        if not ok and "bleibt" in meldung:
            berichte.append(meldung)      # Spur wartet auf Freigabe
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
        berichte.append(meldung if ok else "Signal nicht ausgefuehrt: %s" % meldung)
    for b in berichte:
        print(b)
    return 0


if __name__ == "__main__":
    sys.exit(main())