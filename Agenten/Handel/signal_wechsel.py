"""Signal-Wechsel-Gatter fuer Spuren mit EIGENEM Buch (03.10.2026).

WARUM EIN EIGENES MODUL
-----------------------
`spur_buch.trigger_modus` wirkt dort, wo `spur_buch` das Buch fuehrt - 28
Spuren. xperp, scanner, mosaic und kraken fuehren einen eigenen
`handeln.py` und wuerden das Flag schweigend ignorieren. Fuer diese vier
liegt die Regel hier, damit sie EINMAL geschrieben wird und nicht viermal
mit vier Fehlerquellen.

DIE REGEL
---------
Ein Einstieg wird nur zugelassen, wenn sich die Signalrichtung fuer
dieses Instrument SEIT DEM LETZTEN EINSTIEG geaendert hat. Ein Long-Signal,
das im naechsten 15-Minuten-Takt wieder Long sagt, ist derselbe Auftrag -
kein neuer. Vorher hat jede dieser Spuren bei erfuelltem Signal bis zu 96
mal am Tag denselben Einstieg gebucht; die Quelle der Ueberhandelung war
nicht ein falsches Signal, sondern der Takt.

Das Gatter merkt sich die zuletzt gesehene Richtung je Instrument im
Zustand (`vor_signal`) und vergleicht damit. Der Vergleich ist
RICHTUNGSBEWUSST: long nach short ist ein Wechsel, long nach long nicht.

WARUM ES AM ENSTIEG HANGT UND NICHT AM SIGNAL
--------------------------------------------
Das Gatter sitzt unmittelbar vor dem Anlegen der Position, nicht in der
Signalberechnung. Grund: das Signal kann aus mehreren Quellen kommen
(Score-Schwelle, Kerzenschluss, Rueckdreh) und die Entscheidung "darf
dieser Auftrag raus" gehoert an die Stelle, an der er wirklich rausgeht.
Ein Gatter in der Signalberechnung wuerde Kandidaten unterdruecken, die
spaeter im Zyklus sowieso an Guthaben, Platz oder Sperrfrist scheitern -
und es wuerde still das Buch beschreiben, statt den Auftrag zu verweigern.

RUECKVERHALTEN, wenn `trigger_modus` fehlt oder etwas anderes ist: alles
wie bisher. Das Gatter ist eine Aenderung, keine Voraussetzung - eine
Spur ohne das Feld verhaelt sich exakt wie vor diesem Modul.
"""

ERLAEUT = "Zugelassen - Signalrichtung neu oder erster Auftrag"
GESPERRT = "Signal unveraendert - kein erneuter Einstieg"


def zugelassen(z, w, inst, seite, zurueckgeben=False):
    """True, wenn dieser Einstieg das Gatter passiert.

    `z` wird in-place um `vor_signal` ergaenzt (der Aufrufer schreibt den
    Zustand danach). `w` ist die geladene wachen.json.

    Legt `z["vor_signal"][inst] = seite` bei JEDER Pruefung fest, auch bei
    der verweigerten - das ist Absicht: das Feld soll den zuletzt
    GESEHENEN Signalzustand abbilden, nicht den zuletzt ausgefuehrten.
    Sonst wuerde eine durch das Gatter verweigerte Runde denselben
    Auftrag beim naechsten Takt erneut durchlassen, sobald ein anderes
    Instrument den Vergleich verschiebt.
    """
    # BEIDE Wege geben denselben Wert zurueck. Ein frueherer Fassung gab hier
    # `True` (bool) zurueck, im Flag-Fall aber den String ERLAEUT - und der
    # Aufrufer prueft `is not ERLAEUT`. Damit sperrte das Gatter jede Spur,
    # die das Feld NICHT gesetzt hat: genau das Gegenteil der beabsichtigten
    # Regel, und drei xperp-Tests haben es am Tag der Einfuehrung gemeldet.
    if str(w.get("trigger_modus") or "").lower() != "signal":
        return ERLAEUT
    vorher = z.setdefault("vor_signal", {})
    alt = vorher.get(inst)
    vorher[inst] = seite
    ok = (alt is None) or (alt != seite)
    if not ok and zurueckgeben:
        return GESPERRT
    return ERLAEUT if ok else GESPERRT


def erklaerung(w):
    """Der Satz fuer die Vermerkzeile der wachen.json."""
    return ("03.10.2026, Auftrag Max \"Erweitern\": derselbe Signal-Wechsel wie "
            "in spur_buch, aber fuer Spuren mit eigenem Buch. Ein Einstieg wird "
            "nur zugelassen, wenn sich die Signalrichtung fuer das Instrument "
            "geaendert hat - sonst kein erneuter Einstieg im 15-Minuten-Takt. "
            "Regel und Gatter: Handel/signal_wechsel.py. Das Gatter sitzt am "
            "Anlegen der Position, nicht in der Signalberechnung - ein Gatter "
            "dort wuerde Kandidaten unterdruecken, die spaeter ohnehin an "
            "Guthaben, Platz oder Sperrfrist scheitern. Ohne das Feld "
            "verhaelt sich die Spur exakt wie vorher.")