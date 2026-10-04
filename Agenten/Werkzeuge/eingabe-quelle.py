"""Wer verhindert den Bildschirm-Standby? Eingaben mit Geraetenamen protokollieren.

Zweck: Wenn der Monitor nicht ausgeht, liegt es an einer von zwei Ursachen:
  (a) etwas erzeugt laufend "Eingaben" und setzt den Leerlauf-Timer zurueck
  (b) ein Programm haelt einen Anzeige-Request (dafuer braucht es Admin)

Dieses Werkzeug beantwortet (a) hart belegbar: Es lauscht auf die Rohdaten
(Raw Input) und schreibt zu JEDER Eingabe den Geraetenamen (VID/PID).
  - Kommt eine Eingabe MIT Geraetenamen -> Hardware (Maus, Tastatur, Adapter).
  - Rueckfall des Leerlauf-Timers OHNE Rohdaten-Ereignis -> SOFTWARE hat die
    Eingabe erzeugt (SendInput), z. B. ein Agenten-Overlay oder ein Makro.

Am Ende steht ein Urteil: hochster erreichter Leerlaufwert gegen die
eingestellte Bildschirm-Auszeit. Erreicht der Wert die Auszeit nie, geht der
Bildschirm nie aus - und die Auswertung nennt die beteiligten Geraete.

Aufruf (PowerShell, aus der BrainFiles-Wurzel):
    python Agenten\\Werkzeuge\\eingabe-quelle.py
    python Agenten\\Werkzeuge\\eingabe-quelle.py --dauer 120
    python Agenten\\Werkzeuge\\eingabe-quelle.py --log C:\\...\\mein.log

Waehrend der Messung nichts anfassen - jede eigene Bewegung ist ein Messfehler.
Fuer Ursache (b) braucht es Admin:  powercfg -requests
"""
from __future__ import annotations

import argparse
import ctypes
import subprocess
import time
from collections import Counter
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_INPUT = 0x00FF
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIDI_DEVICENAME = 0x20000007
RIM_NAMEN = {0: "MAUS", 1: "TASTATUR", 2: "HID"}

HIER = Path(__file__).resolve().parent
STANDARD_LOG = HIER.parent / "Hermes" / "cache" / "eingabe-quelle.log"


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT),
                ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD),
                ("hwndTarget", wintypes.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD),
                ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE),
                ("wParam", wintypes.WPARAM)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT),
                ("lpfnWndProc", ctypes.c_void_p),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR)]


# --- Signaturen festnageln (ohne das wirft ctypes bei langen Werten OverflowError) ---
user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
user32.GetLastInputInfo.restype = wintypes.BOOL
user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p,
                                   ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputData.restype = wintypes.UINT
user32.GetRawInputDeviceInfoW.argtypes = [wintypes.HANDLE, wintypes.UINT,
                                          ctypes.c_void_p, ctypes.POINTER(wintypes.UINT)]
user32.GetRawInputDeviceInfoW.restype = wintypes.UINT
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
user32.RegisterRawInputDevices.restype = wintypes.BOOL
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_longlong

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)

ereignisse: list[tuple[str, str, str, float]] = []


def leerlauf() -> float:
    l = LASTINPUTINFO()
    l.cbSize = ctypes.sizeof(LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(l))
    return (kernel32.GetTickCount() - l.dwTime) / 1000.0


def geraetename(h) -> str:
    if not h:
        return "SIMULIERT (kein Geraet)"
    groesse = wintypes.UINT(0)
    user32.GetRawInputDeviceInfoW(h, RIDI_DEVICENAME, None, ctypes.byref(groesse))
    if not groesse.value:
        return "unbekannt"
    puffer = ctypes.create_unicode_buffer(groesse.value)
    user32.GetRawInputDeviceInfoW(h, RIDI_DEVICENAME, puffer, ctypes.byref(groesse))
    teile = puffer.value.split("#")
    if len(teile) > 2:
        return teile[1] + " / " + teile[2].split("&")[0]
    return puffer.value[:80] or "unbekannt"


def _wndproc(hwnd, msg, wparam, lparam):
    if msg == WM_INPUT:
        groesse = wintypes.UINT(0)
        user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(groesse),
                               ctypes.sizeof(RAWINPUTHEADER))
        if groesse.value:
            puffer = ctypes.create_string_buffer(groesse.value)
            if user32.GetRawInputData(lparam, RID_INPUT, puffer, ctypes.byref(groesse),
                                      ctypes.sizeof(RAWINPUTHEADER)) != 0xFFFFFFFF:
                kopf = ctypes.cast(puffer, ctypes.POINTER(RAWINPUTHEADER)).contents
                art = RIM_NAMEN.get(kopf.dwType, str(kopf.dwType))
                ereignisse.append((time.strftime("%H:%M:%S"), art,
                                   geraetename(kopf.hDevice), round(leerlauf(), 1)))
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def bildschirm_auszeit() -> int | None:
    """Bildschirm-Auszeit des aktiven Plans in Sekunden (None = nicht lesbar)."""
    try:
        ausgabe = subprocess.run(["powercfg", "-q", "SCHEME_CURRENT", "SUB_VIDEO", "VIDEOIDLE"],
                                 capture_output=True, timeout=30).stdout
    except Exception:
        return None
    if not ausgabe:
        return None
    # powercfg schreibt in der OEM-Zeichentabelle (hier cp850), nicht in UTF-8
    for zeile in ausgabe.decode("cp850", errors="replace").splitlines():
        if "Wechselstromeinstellung" in zeile:
            try:
                return int(zeile.strip().rsplit(" ", 1)[-1], 16)
            except ValueError:
                return None
    return None


def messen(dauer: int):
    """Laeuft dauer Sekunden. Rueckgabe: Logzeilen, Rueckfaelle, hochster Wert, Geraetezaehler."""
    wndproc_c = WNDPROC(_wndproc)
    hinst = kernel32.GetModuleHandleW(None)
    klasse = WNDCLASS()
    klasse.lpfnWndProc = ctypes.cast(wndproc_c, ctypes.c_void_p)
    klasse.hInstance = hinst
    klasse.lpszClassName = "HermesEingabeQuelle"
    if not user32.RegisterClassW(ctypes.byref(klasse)):
        fehler = ctypes.get_last_error()
        if fehler != 1410:  # Klasse schon vorhanden (zweiter Aufruf im Prozess)
            raise SystemExit("RegisterClass fehlgeschlagen: %d" % fehler)
    hwnd = user32.CreateWindowExW(0, "HermesEingabeQuelle", "Eingabequelle", 0,
                                  0, 0, 0, 0, None, None, hinst, None)
    if not hwnd:
        raise SystemExit("CreateWindowEx fehlgeschlagen: %d" % ctypes.get_last_error())

    geraete = [(0x01, 0x02, RIDEV_INPUTSINK),   # Maus
               (0x01, 0x06, RIDEV_INPUTSINK),   # Tastatur
               (0x01, 0x80, RIDEV_INPUTSINK),   # Systemsteuerung
               (0x0C, 0x01, RIDEV_INPUTSINK)]   # Consumer (Multimedia)
    feld = (RAWINPUTDEVICE * len(geraete))(*[RAWINPUTDEVICE(p, u, f, hwnd) for p, u, f in geraete])
    if not user32.RegisterRawInputDevices(feld, len(geraete), ctypes.sizeof(RAWINPUTDEVICE)):
        raise SystemExit("RegisterRawInputDevices fehlgeschlagen: %d" % ctypes.get_last_error())

    zeilen = ["start %s   (Leerlauf beim Start %.1f s)" % (time.strftime("%H:%M:%S"), leerlauf())]
    rueckfaelle: list[tuple[str, float]] = []
    zaehler: Counter = Counter()
    hoch = 0.0
    letzte = leerlauf()
    msg = wintypes.MSG()
    ende = time.time() + dauer
    while time.time() < ende:
        while user32.PeekMessageW(ctypes.byref(msg), hwnd, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        akt = leerlauf()
        hoch = max(hoch, akt)
        if akt < letzte - 1.0:
            rueckfaelle.append((time.strftime("%H:%M:%S"), round(akt, 1)))
            zeilen.append("%s  LEERLAUF-RUECKFALL auf %.1f s  (ohne Rohdaten-Ereignis)"
                          % (time.strftime("%H:%M:%S"), akt))
        letzte = akt
        while ereignisse:
            z, art, name, idle = ereignisse.pop(0)
            zaehler[name] += 1
            zeilen.append("%s  %-8s  Leerlauf %6.1f s  %s" % (z, art, idle, name))
        time.sleep(0.05)
    zeilen.append("ENDE %s  (Leerlauf zuletzt %.1f s)" % (time.strftime("%H:%M:%S"), leerlauf()))
    return zeilen, rueckfaelle, hoch, zaehler


def urteil(hoch: float, rueckfaelle, auszeit, dauer: int, zaehler: Counter) -> list[str]:
    zeilen = ["", "=== URTEIL ===", "Messdauer: %d s" % dauer]
    if auszeit:
        zeilen.append("Bildschirm-Auszeit des aktiven Plans: %d s" % auszeit)
    else:
        zeilen.append("Bildschirm-Auszeit: nicht lesbar (powercfg -q SCHEME_CURRENT SUB_VIDEO VIDEOIDLE)")
    zeilen.append("hoechster erreichter Leerlaufwert: %.1f s" % hoch)
    if auszeit and hoch >= auszeit:
        zeilen.append("-> Die Auszeit wurde ERREICHT, der Bildschirm muss ausgegangen sein.")
        zeilen.append("   Kommt er sofort wieder: Aufweck-Geraete pruefen")
        zeilen.append("   (powercfg -devicequery wake_armed) oder einen Anzeige-Request")
        zeilen.append("   (powercfg -requests, braucht Admin).")
    else:
        zeilen.append("-> Die Auszeit wurde NICHT erreicht. Der Bildschirm kann nicht ausgehen.")
    if rueckfaelle:
        zeilen.append("")
        zeilen.append("Rueckfaelle OHNE Rohdaten-Ereignis: %d -> SOFTWARE erzeugt die Eingabe."
                      % len(rueckfaelle))
        zeilen.append("   Kandidaten: Agenten-Overlays (cua-driver), Makro-/Geraetesoftware")
        zeilen.append("   (LogiOptions, ROCCAT SWARM), PowerToys-Module.")
    if zaehler:
        zeilen.append("")
        zeilen.append("Geraete der echten Eingaben:")
        for name, anzahl in zaehler.most_common(10):
            zeilen.append("   %4d x  %s" % (anzahl, name))
    if not rueckfaelle and not zaehler:
        zeilen.append("")
        zeilen.append("-> Keine einzige Eingabe im Messfenster. Der Leerlauf-Timer lief durch.")
        zeilen.append("   Fuer einen Anzeige-Request eines Programms braucht es Admin:")
        zeilen.append("   powercfg -requests   (nennt den Prozess beim Namen)")
    return zeilen


def main() -> int:
    p = argparse.ArgumentParser(description="Wer verhindert den Bildschirm-Standby?")
    p.add_argument("--dauer", type=int, default=300, help="Messdauer in Sekunden (Standard 300)")
    p.add_argument("--log", type=Path, default=STANDARD_LOG, help="Logdatei")
    args = p.parse_args()

    auszeit = bildschirm_auszeit()
    print("Messung laeuft %d s - waehrenddessen nichts anfassen." % args.dauer)
    print("Bildschirm-Auszeit: %s s" % (auszeit if auszeit else "unbekannt"))
    zeilen, rueckfaelle, hoch, zaehler = messen(args.dauer)

    zeilen += urteil(hoch, rueckfaelle, auszeit, args.dauer, zaehler)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print("\n".join(zeilen))
    print("\nLog: %s" % args.log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())