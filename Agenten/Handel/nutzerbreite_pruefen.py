"""Haelt eine von Hand gezogene Spaltenbreite jetzt?

Befund des UI-Audits vom 04.10.2026: die Nachrechnung in
`_breiten_nachrechnen` hoerte nie auf - `BREITEN_MAX_DURCHGAENGE` stand als
Konstante im Baum und wurde nirgends gelesen. Nachgemessen: eine auf 600 px
gezogene Spalte stand nach EINEM `refresh()` wieder auf 200 px.

Dieses Skript zieht die Spalte, laesst die Nachrechnung mehrfach laufen und
misst danach. Es ist der Gegenbeweis: mit der Grenze (5 Durchgaenge) muss
die Breite stehen bleiben, ohne sie nicht.
"""

import importlib.util
import os
import sys
import tkinter as tk

HANDEL = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
d = os.path.join(HANDEL, "..", "Werkzeuge", "fenster_design.py")
spec = importlib.util.spec_from_file_location("fd", d)
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)

import handelszentrale as hz

GEZOGEN = 600

root = tk.Tk()
try:
    root.tk.call("tk", "scaling", 1.1)
except Exception:
    pass
hz.SCHRIFT_GROESSE = 13
design.stil_anwenden(__import__("tkinter").ttk.Style(), 13)
z = hz.Handelszentrale(root)
root.geometry("1280x860-3200-0")
root.update()
root.update_idletasks()
for _ in range(3):
    z.refresh()
    root.update()
    root.update_idletasks()

print("Breite VOR der Nachrechnung (Bau): %d px"
      % z.t_spuren.column("spur", "width"))
vorher = z.t_spuren.column("spur", "width")
print("nach dem Nachrechnen: spur = %d px, Durchgaenge = %d, gesetzt = %s"
      % (vorher, z._breiten_durchgang, z._breiten_gesetzt))

# Nutzer zieht die Spalte breit. Ein 15-s-Takt laeuft, BEVOR er
# zieht - das ist der Normalfall, und danach gehoert die Breite ihm.
z.t_spuren.column("spur", width=GEZOGEN)
z._breiten_gesetzt = True   # ein Takt hat die Nachrechnung beendet
print("Nutzer zieht auf %d px, danach ist die Nachrechnung fertig" % GEZOGEN)

# EIN Takt: der Nutzer zieht, danach genau eine Aktualisierung.
# Genau damit ist der Befund aus dem Audit reproduziert.
for i in range(1):
    z.refresh()
    root.update()
    root.update_idletasks()
    print("   Takt %d: %4d px  (Durchgang %d, gesetzt %s)"
          % (i + 1, z.t_spuren.column("spur", "width"),
             z._breiten_durchgang, z._breiten_gesetzt))

nachher = z.t_spuren.column("spur", "width")
print()
if nachher == GEZOGEN:
    print("HALTT: die Nutzerbreite %d px steht nach 6 Takten." % GEZOGEN)
    rc = 0
else:
    print("VERLOREN: %d px wurde auf %d px zurueckgesetzt."
          % (GEZOGEN, nachher))
    rc = 1
root.destroy()
sys.exit(rc)