"""Burst-Gegenbeweis: dieselbe Last ohne und mit Haus-Bremse.

Beantwortet zwei Fragen getrennt, weil sie oft verwechselt werden:

  1. Ist die Fremd-API ueberhaupt drosselungsempfindlich?  -> Lauf A
  2. Wirkt die Bremse im BETRIEB, nicht nur im Labor?      -> Lauf B

Lauf B setzt bewusst KEIN eigenes Taktverzeichnis: die Bremse teilt sich das
Fenster mit den laufenden Prozessen. Ein Gegenbeweis in einem selbst
gewaehlten Temp-Verzeichnis prueft die Bremse, nicht ihre Stellung im Haus
(das war der Fehler der ersten Fassung dieses Nachweises).

Aufruf ueber das terminal-Werkzeug, Ergebnis nach <ziel>/BURST-ERGEBNIS.txt:

    python burst-gegenbeweis.py --zugang Agenten/Handel/scanner/okx.py \\
        --takt-modul Agenten/Handel/okx_takt.py --paare BTC-USDC \\
        --threads 8 --je-thread 40

Nur Standardbibliothek. Ohne --takt-modul laeuft nur Lauf A.
"""
import argparse
import importlib.util as _ilu
import os
import sys
import threading
import time


def lade(pfad, name):
    """Modul frisch laden und den alten Eintrag wirklich ersetzen.

    sys.modules.pop(name, None) ist Pflicht: ohne das zieht ein
    zweites Laden die ALTE Instanz (mit neutralisierter Bremse aus
    Lauf A) und Lauf B prueft dieselbe Sache zweimal. Das war der
    zweite Fehler dieses Skripts - 12,0/s trotz gesetzter Bremse.
    """
    sys.modules.pop(name, None)
    s = _ilu.spec_from_file_location(name, pfad)
    m = _ilu.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


def burst(okx, paare, threads, je_thread, fenster_name="ohne Bremse"):
    fehler = []
    sperre = threading.Lock()

    def arbeite(k):
        for i in range(je_thread):
            try:
                okx.letzter_kurs(paare[(i + k) % len(paare)])
            except Exception as e:                        # noqa: BLE001
                with sperre:
                    fehler.append(str(e)[:90])

    ts = [threading.Thread(target=arbeite, args=(k,)) for k in range(threads)]
    t0 = time.time()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    dauer = time.time() - t0
    n = threads * je_thread
    print("  %s: %d Abrufe in %.1f s (%.1f/s), %d Fehler"
          % (fenster_name, n, dauer, n / dauer, len(fehler)))
    for f in fehler[:4]:
        print("      - %s" % f)
    return len(fehler), dauer


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zugang", required=True,
                    help="Pfad zum Zugangsmodul (z. B. scanner/okx.py)")
    ap.add_argument("--takt-modul", default="",
                    help="Pfad zum Taktmodul; leer = Lauf A ohne Bremse")
    ap.add_argument("--paare", nargs="+", default=["BTC-USDC"],
                    help="InstIds fuer den Kursabruf")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--je-thread", type=int, default=40)
    ap.add_argument("--ablage", default="", help="Ergebnisdatei (leer = stdout)")
    a = ap.parse_args()

    zeilen = []
    def log(text):
        print(text)
        zeilen.append(text)

    okx = lade(os.path.abspath(a.zugang), "zugang_unter_test")

    log("Burst-Gegenbeweis")
    log("  Last: %d Threads x %d = %d parallele Kursabrufe"
        % (a.threads, a.je_thread, a.threads * a.je_thread))
    log("  Paare: %s" % ", ".join(a.paare))

    # Lauf A heisst "Bremse aus", nicht "Aufrufer ohne Bremse": das
    # Zugangsmodul holt sie selbst. Ein Lauf A, der die Bremse still
    # laufen laesst, vergleicht nichts und sieht harmlos aus - die erste
    # Fassung dieses Skripts tat genau das und meldete 0 Fehler OHNE zu
    # fragen. Lauf B laedt das Taktmodul ohnehin neu, die Neutralisierung
    # wirkt also nur hier.
    takt_modul = getattr(okx, "okx_takt", None) if a.takt_modul else None
    log("")
    if takt_modul is not None and hasattr(takt_modul, "reserviere"):
        log("Lauf A - Bremse NEUTRALISIERT (reserviere() auf Luft gesetzt):")
        takt_modul.reserviere = lambda *x, **y: None
        fehler_a, dauer_a = burst(okx, a.paare, a.threads,
                                 a.je_thread, "ohne Bremse")
    else:
        log("HINWEIS: Das Zugangsmodul holt keine Bremse - Lauf A ist dann")
        log("         der echte Betrieb, nicht die Vergleichsprobe.")
        fehler_a, dauer_a = burst(okx, a.paare, a.threads,
                                 a.je_thread, "Betrieb")

    if a.takt_modul:
        log("")
        log("Lauf B - MIT Bremse, gegen das ECHTE Fenster (laufender Betrieb):")
        # FRISCH laden: Lauf A hat die Taktinstanz des Zugangsmoduls
        # auf Luft gesetzt, und beide teilen sich sonst denselben
        # Zustand - Lauf B waere dann ebenfalls ungebremst.
        takt = lade(os.path.abspath(a.takt_modul), "okx_takt_unter_test")
        okx_b = lade(os.path.abspath(a.zugang), "zugang_mit_bremse")
        log("  Fenster: %s" % takt.DATEI)
        log("  Grenze  : %d Abrufe je %.0f s (Mindestabstand %.3f s)"
            % (takt.TAKT_ABRUFE, takt.TAKT_FENSTER_S,
               takt.TAKT_ABSTAND_S))
        fehler_b, dauer_b = burst(okx_b, a.paare, a.threads, a.je_thread, "mit Bremse")
        log("")
        n = a.threads * a.je_thread
        soll = takt.TAKT_ABRUFE / takt.TAKT_FENSTER_S
        ist_a = n / max(dauer_a, 0.001)
        ist_b = n / max(dauer_b, 0.001)
        log("  RATE   : ohne Bremse %.1f/s, mit Bremse %.1f/s (Soll %.1f/s)"
            % (ist_a, ist_b, soll))
        log("  TAKT   : %s"
            % ("greift - die Rate liegt an der Bremse"
               if ist_b <= soll * 1.25 else
               "GREIFT NICHT - 0 Fehler, weil sie nicht angesetzt"))
        log("  URTEIL: %s"
            % ("BREMSE WIRKT" if fehler_b == 0
               else "NOCH %d FEHLER" % fehler_b))
        log("  Unbelegt bleibt, ob der Anbieter selbst drosselt (geteiltes Netz,")
        log("  Fremdnutzung) - dafuer fehlt ein Zaehler.")

    if a.ablage:
        with open(os.path.abspath(a.ablage), "w", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")


if __name__ == "__main__":
    main()