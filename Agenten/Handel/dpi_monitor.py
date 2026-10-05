"""Die physische Monitor-DPI, gemessen MIT dpi-awareness.

Ohne `SetProcessDpiAwareness` meldet `GetDeviceCaps(LOGPIXELSX)` immer 96 -
Windows skaliert die Abfrage auf den logischen Wert. Deshalb meldete der
erste Lauf 96 und damit Faktor 1.0, obwohl dieselbe Maschine im dpi-bewussten
Zustand `winfo_fpixels('1i') = 119` liefert (120 px, Faktor 1.25).

Aufruf:  scanner/.venv/Scripts/python.exe dpi_monitor.py
"""

import ctypes
import sys

ctypes.windll.shcore.SetProcessDpiAwareness(1)
dc = ctypes.windll.user32.GetDC(0)
dpi_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)   # LOGPIXELSX
dpi_y = ctypes.windll.gdi32.GetDeviceCaps(dc, 90)   # LOGPIXELSY
sys.stdout.write("physische Monitor-DPI : %d x %d\n" % (dpi_x, dpi_y))
sys.stdout.write("Faktor gegen 96 dpi   : %.3f\n" % (dpi_x / 96.0))
sys.stdout.write("System physisch       : %d x %d\n"
                 % (ctypes.windll.user32.GetSystemMetrics(0),
                    ctypes.windll.user32.GetSystemMetrics(1)))
sys.stdout.write("\nEin dpi-unawarer Prozess sieht %d x %d - das ist %.1f %% weniger\n"
                 % (3072, 1728, 100 * (1 - 3072 * 1728 / (3840 * 2160))))
