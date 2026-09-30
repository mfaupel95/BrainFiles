"""Die Sperrdatei des Dauerlaufs - eine PID allein reicht nicht.

WARUM ES DAS GIBT (29.09.2026)
------------------------------
Am 15.09.2026 liefen zwei Dauerlaeufe gleichzeitig "und beide Laeufe schrieben
in dieselben Dateien" (dauerlauf.py, Modulkopf). Dagegen steht seither eine
Datei mit der Prozessnummer, die handel-dauerlauf.ps1 schreibt und prueft. Drei
Luecken blieben:

1. Ein direkt gestarteter `python dauerlauf.py` prueft die Sperre nicht.
2. Er schreibt sie auch nicht - der Waechter haelt sie fuer frei und startet
   einen zweiten Lauf daneben.
3. Windows vergibt PIDs wieder. Traegt nach einem Neustart irgendein anderer
   Python-Prozess die alte Nummer, sieht der Waechter "PID lebt, heisst
   python" und meldet fuer immer "laeuft bereits". Diese Luecke ist die
   gefaehrlichste: sie hebelt die Wiederbelebung aus, die am selben Tag
   ueberhaupt erst in Gang gebracht wurde (MaxHirn/Wissen/Routinen.md).

Gegen (3) hilft die STARTZEIT des Prozesses: eine wiederverwendete Nummer
traegt eine andere. Gegen (1) und (2) hilft, dass der Lauf die Sperre selbst
prueft und selbst schreibt.

DER GRUNDSATZ: IM ZWEIFEL STARTEN
---------------------------------
Das hier ist der Betriebskern von drei laufenden Prozessen. Eine zu strenge
Pruefung haelt einen gesunden Lauf vom Neustart ab - und ein Lauf, der nicht
startet, faellt niemandem auf, weil melder.py nach Zeitplan sendet und nicht
nach Zustand. Deshalb gilt jede Unsicherheit als "nicht belegt": unlesbare
Datei, verweigerter Zugriff, psutil-Fehler. Die eigentliche Doppelstart-Abwehr
bleibt beim Waechter; dieses Modul ergaenzt sie.

DAS FORMAT
----------
Eine Zeile, zwei durch Leerzeichen getrennte Felder:

    12345 1790668314.127303

Das erste Feld ist die nackte PID. Damit liest der PowerShell-Waechter sie mit
($inhalt -split '\s+')[0] - und eine Datei im alten Einfeldformat aus einem
Lauf von vor dem 29.09.2026 bleibt lesbar. Mehrzeilig darf es nicht sein:
Get-Content gaebe dann ein Array, und Get-Process -Id scheitert daran.
"""

from __future__ import annotations

import os

import psutil

import risikostufe

HIER = os.path.dirname(os.path.abspath(__file__))

# Wie weit die gespeicherte Startzeit von der gemessenen abweichen darf.
# Grosszuegig gegen Rundung beim Schreiben, eng gegen Wiederverwendung: eine
# PID kommt Stunden spaeter zurueck, nicht innerhalb einer Sekunde.
ZEIT_TOLERANZ_SEKUNDEN = 1.0


def pfad(basis=None):
    """Der Sperrpfad DIESER Risikostufe: dauerlauf.pid, dauerlauf.mittel.pid ...

    Je Stufe eine eigene Datei - sonst sperrten sich die drei Dauerlaeufe
    gegenseitig aus, obwohl sie getrennte Buecher fuehren.
    """
    return risikostufe.datei(basis or os.path.join(HIER, "dauerlauf.pid"))


def lies(p):
    """(pid, startzeit) aus der Sperrdatei, oder None.

    startzeit ist None, wenn die Datei im alten Einfeldformat vorliegt. Alles,
    was sich nicht als Zahl lesen laesst, gilt als keine Sperre - siehe
    Grundsatz im Modulkopf.
    """
    try:
        with open(p, encoding="ascii") as f:
            roh = f.read()
    except OSError:
        return None
    felder = roh.split()
    if not felder:
        return None
    try:
        nummer = int(felder[0])
    except ValueError:
        return None
    if nummer <= 0:
        return None
    zeit = None
    if len(felder) > 1:
        try:
            zeit = float(felder[1])
        except ValueError:
            zeit = None
    return nummer, zeit


def schreibe(p, prozess=None):
    """Die eigene PID mit Startzeit in die Sperrdatei."""
    ich = prozess or psutil.Process()
    with open(p, "w", encoding="ascii") as f:
        f.write("%d %r\n" % (ich.pid, ich.create_time()))


def belegt(p):
    """True, wenn ein FREMDER Lauf die Sperre haelt und noch lebt.

    Die eigene PID zaehlt nie als fremd - sonst sperrte ein Lauf sich beim
    Neuschreiben selbst aus.
    """
    gelesen = lies(p)
    if gelesen is None:
        return False
    nummer, zeit = gelesen
    if nummer == os.getpid():
        return False
    # Auch mein eigener STARTER zaehlt nicht als fremd. handel-dauerlauf.ps1
    # schreibt die PID des Prozesses, den Start-Process zurueckgibt - bei einem
    # venv-Startprogramm ist das NICHT der Interpreter, sondern sein
    # Elternteil. Ohne diese Zeile sieht der Lauf die Sperre seines eigenen
    # Starters, haelt sie fuer einen zweiten Lauf und beendet sich sofort:
    # am 30.09.2026 standen dadurch alle drei Stufen still (kein Zyklus, kein
    # Traceback, nur "Es laeuft bereits ein Dauerlauf").
    if nummer == os.getppid():
        return False
    try:
        fremd = psutil.Process(nummer)
        if zeit is None:
            # Altes Einfeldformat: mehr als der Waechter bisher konnte, geht
            # nicht - lebt die Nummer und heisst sie python, gilt sie.
            return fremd.name().lower().startswith("python")
        return abs(fremd.create_time() - zeit) <= ZEIT_TOLERANZ_SEKUNDEN
    except psutil.NoSuchProcess:
        return False
    except (psutil.AccessDenied, psutil.Error, OSError):
        # Ein Prozess, den wir nicht befragen duerfen, ist nicht unser eigener
        # Dauerlauf - er laeuft unter demselben Konto. Im Zweifel starten.
        return False


def freigib(p):
    """Die eigene Sperre loeschen. Eine fremde bleibt liegen."""
    gelesen = lies(p)
    if gelesen is not None and gelesen[0] != os.getpid():
        return
    try:
        os.remove(p)
    except OSError:
        pass
