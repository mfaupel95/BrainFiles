"""Wache: die Aktionsgrenze als Zwang im Kindprozess, nicht als Bitte.

Die Spezifikation (Abschnitt 3) sagt es deutlich: erlaubte_aktionen ist der
einzige Punkt, an dem die Registry einen Skill zuverlaessig begrenzt, weil eine
SKILL.md Prosa ist und sich nur freiwillig an ihre eigenen Regeln haelt. Eine
Engine, die "bitte nur lesen" in einen Prompt schreibt, hat keine Grenze.

Darum laeuft jeder Skript-Lauf mit einem Audit-Hook (sys.addaudithook, ab
Python 3.8, nicht entfernbar sobald gesetzt). Der Hook sieht:

  open                  -> Schreibzugriff? Pfad gegen schreibpfade pruefen
  os.remove/unlink/rmdir/shutil.rmtree -> loeschen
  os.rename/os.replace  -> datei_schreiben (Quelle und Ziel)
  subprocess.Popen      -> Kommando einordnen (muster.py)
  socket.connect        -> nur beobachten, nicht sperren (siehe unten)

Bei einem Verstoss schreibt die Wache eine JSON-Zeile in die Verstossdatei und
beendet den Prozess hart mit Exit 97. Kein Aufraeumen, kein except: der Lauf
darf ab diesem Punkt nichts mehr tun.

Warum socket.connect nur beobachtet wird: das Aktionsvokabular der Registry
kennt keine Aktion "Netzzugriff". nachricht_senden meint Telegram/Mail/A2A, und
ein Skill, der eine Webseite liest, sendet keine Nachricht. Ein Hook, der jede
Verbindung sperrt, wuerde DNS und lokale Sockets treffen und die Engine
unbrauchbar machen. Beobachtete Ziele landen im Log (netz_ziele), damit ein
Nachhinein pruefbar bleibt - das ist die ehrliche Grenze dieser Wache und steht
auch in BETRIEB.md.

Grenzen, die man kennen muss:
- Ein Kindprozess des Kindprozesses laeuft ohne diesen Hook (PYTHONPATH wird von
  manchen Skripten absichtlich entfernt). Der Start selbst wird aber gesehen und
  eingeordnet - eine Regel ohne prozess_starten kommt gar nicht dazu.
- Nicht-Python-Skills (skill_art=skill ueber hermes.exe) werden nicht von innen
  bewacht; fuer sie gilt die Einordnung des Startkommandos und der Modus.
"""
from __future__ import annotations

import json
import os
import sys

_INSTALLIERT = False
_IN_HOOK = False

SCHREIB_FLAGS = 0
for _name in ("O_WRONLY", "O_RDWR", "O_APPEND", "O_CREAT", "O_TRUNC", "O_EXCL"):
    SCHREIB_FLAGS |= getattr(os, _name, 0)

VERSTOSS_EXIT = 97


def _konfig():
    roh = os.environ.get("HERMES_AUTOMATIK_WACHE", "")
    if not roh:
        return None
    try:
        return json.loads(roh)
    except json.JSONDecodeError:
        return None


def _norm(pfad) -> str:
    try:
        return os.path.abspath(str(pfad)).replace("\\", "/").lower()
    except (TypeError, ValueError):
        return str(pfad).replace("\\", "/").lower()


def installieren(konfig=None):
    """Audit-Hook setzen. Ohne Konfiguration passiert nichts (kein Zwang)."""
    global _INSTALLIERT
    if _INSTALLIERT:
        return False
    k = konfig or _konfig()
    if not k:
        return False

    erlaubt = set(k.get("erlaubte_aktionen") or [])
    erlaubt.add("lesen")
    schreibpfade = [_norm(p) for p in (k.get("schreibpfade") or [])]
    berichtspfade = [_norm(p) for p in (k.get("berichtspfade") or [])]
    freipfade = [_norm(p) for p in (k.get("freipfade") or [])]
    verstossdatei = k.get("verstossdatei") or ""
    beobachtung = k.get("beobachtungsdatei") or ""
    regel_id = k.get("regel_id") or "?"

    # muster.py liegt neben dieser Datei; im Kindprozess ist der Engine-Ordner
    # ueber PYTHONPATH erreichbar.
    from . import muster  # noqa: WPS433 (bewusst spaet)

    def _melden(art, aktion, detail):
        if not verstossdatei:
            return
        zeile = json.dumps({
            "art": art,
            "regel_id": regel_id,
            "aktion": aktion,
            "detail": str(detail)[:500],
            "pid": os.getpid(),
        }, ensure_ascii=False)
        try:
            with open(verstossdatei, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(zeile + "\n")
                fh.flush()
        except OSError:
            pass

    def _beobachten(aktion, detail):
        if not beobachtung:
            return
        zeile = json.dumps({"aktion": aktion, "detail": str(detail)[:300]},
                           ensure_ascii=False)
        try:
            with open(beobachtung, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(zeile + "\n")
                fh.flush()
        except OSError:
            pass

    def _abbrechen(aktion, detail):
        _melden("verstoss", aktion, detail)
        sys.stderr.write(
            "WACHE: Aktion '%s' ist fuer Regel '%s' nicht erlaubt: %s\n"
            % (aktion, regel_id, str(detail)[:300]))
        sys.stderr.flush()
        os._exit(VERSTOSS_EXIT)

    def _pfad_erlaubt(pfad, aktion):
        n = _norm(pfad)
        if muster.schreiben_technisch_frei(n):
            return True
        for p in freipfade:
            if n.startswith(p):
                return True
        if aktion == "bericht_schreiben":
            return any(n.startswith(p) for p in berichtspfade)
        return any(n.startswith(p) for p in schreibpfade) or \
            any(n.startswith(p) for p in berichtspfade)

    def _schreibzugriff(pfad, modus, flags):
        """True, wenn dieses open() schreiben kann."""
        if isinstance(modus, str):
            return any(z in modus for z in ("w", "a", "x", "+"))
        try:
            f = int(flags)
        except (TypeError, ValueError):
            return False
        return bool(f & SCHREIB_FLAGS)

    def hook(ereignis, args):
        global _IN_HOOK
        if _IN_HOOK:
            return
        try:
            _IN_HOOK = True

            if ereignis == "open":
                pfad = args[0] if args else None
                modus = args[1] if len(args) > 1 else None
                flags = args[2] if len(args) > 2 else 0
                if pfad is None or not _schreibzugriff(pfad, modus, flags):
                    return
                if isinstance(pfad, int):
                    return  # Dateideskriptor, kein Pfad
                if "datei_schreiben" in erlaubt and _pfad_erlaubt(pfad, "datei_schreiben"):
                    _beobachten("datei_schreiben", pfad)
                    return
                if "bericht_schreiben" in erlaubt and _pfad_erlaubt(pfad, "bericht_schreiben"):
                    _beobachten("bericht_schreiben", pfad)
                    return
                if muster.schreiben_technisch_frei(pfad):
                    return
                _abbrechen("datei_schreiben", pfad)

            elif ereignis in ("os.remove", "os.unlink", "os.rmdir", "shutil.rmtree"):
                pfad = args[0] if args else "?"
                if "loeschen" not in erlaubt:
                    _abbrechen("loeschen", pfad)
                if not _pfad_erlaubt(pfad, "datei_schreiben"):
                    _abbrechen("loeschen", "ausserhalb schreibpfade: %s" % pfad)
                _beobachten("loeschen", pfad)

            elif ereignis in ("os.rename", "os.replace", "os.link", "os.symlink"):
                if "datei_schreiben" not in erlaubt:
                    _abbrechen("datei_schreiben", args)
                for pfad in args[:2]:
                    if not _pfad_erlaubt(pfad, "datei_schreiben"):
                        _abbrechen("datei_schreiben", "ausserhalb schreibpfade: %s" % pfad)
                _beobachten("datei_schreiben", args[:2])

            elif ereignis == "subprocess.Popen":
                kommando = args[1] if len(args) > 1 else (args[0] if args else "")
                if muster.ist_nur_lesen(kommando):
                    _beobachten("lesen", kommando)
                    return
                gefunden = muster.kommando_aktionen(kommando)
                if not gefunden:
                    gefunden = {"prozess_starten"}
                fehlend = gefunden - erlaubt
                if fehlend:
                    _abbrechen(sorted(fehlend)[0], kommando)
                for a in gefunden:
                    _beobachten(a, kommando)

            elif ereignis == "socket.connect":
                _beobachten("netz", args[1] if len(args) > 1 else args)
        finally:
            _IN_HOOK = False

    sys.addaudithook(hook)
    _INSTALLIERT = True
    return True
