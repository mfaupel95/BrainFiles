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


def spurqueue(spur):
    """Die Queue einer Spur: [(inst, richtung, preis, zeit_iso)]. Leer = keine."""
    qpfad = os.path.join(HANDEL, spur, "signal_queue.json")
    if not os.path.isfile(qpfad):
        return []
    try:
        with open(qpfad, encoding="utf-8") as fh:
            q = json.load(fh)
    except (OSError, ValueError):
        return []
    if not isinstance(q, list):
        return []
    jetzt = datetime.now()
    q = [e for e in q if isinstance(e, (list, tuple)) and len(e) >= 3]
    # Segel: zu alte Einträge verfallen — sonst bleibt ein voller Stop
    # ewig liegen, auch wenn der Markt laengst weiter ist
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


def main():
    spur = "moondev_signalwelle"
    q = spurqueue(spur)
    if not q:
        return 0
    ok, meldung = ausfuehren(spur, q[0])
    if not ok and "bleibt" in meldung:
        # Spur nicht bereit — Eintrag bleibt liegen, kein Fehler
        return 0
    # Eintrag aus Queue loeschen (egal ob Treffer oder nicht)
    qpfad = os.path.join(HANDEL, spur, "signal_queue.json")
    if os.path.isfile(qpfad):
        shutil.copy2(qpfad, qpfad + ".bak-" + datetime.now().strftime("%Y%m%d%H%M%S"))
    rest = q[1:] if ok else q
    with open(qpfad, "w", encoding="utf-8") as fh:
        json.dump(rest, fh, ensure_ascii=False, indent=1)
    if ok:
        print(meldung)
        print("(Signal-Modus: der Dauerlauf monitoriert, dieser Cron fuehrt aus)")
    else:
        print("Signal nicht ausgefuehrt: %s" % meldung)
    return 0


if __name__ == "__main__":
    sys.exit(main())