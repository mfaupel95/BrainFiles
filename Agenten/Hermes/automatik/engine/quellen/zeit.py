"""Trigger-Quelle zeit: Intervall oder Cron-Ausdruck.

Aufgerufen wird die Engine selbst von aussen (Hermes-Cron, Feld script mit
no_agent, siehe Spezifikation Abschnitt 5). Diese Quelle entscheidet nur, ob
eine Regel bei DIESEM Aufruf faellig ist - sie schlaeft nie und wartet nie.

nur_wenn_wach ist der wichtigste Teil und kein Komfort: ein verpasster Lauf
entfaellt ersatzlos. Der Rechner geht schlagartig aus (Kernel-Power 41), und ein
Stapel nachgeholter Automatik nach dem Hochfahren ist der gefaehrlichste Fall,
den diese Registry kennt. Praktisch heisst das: liegt die faellige Zeit weiter
als NACHHOL_FENSTER_S zurueck, wird sie uebersprungen und die Marke einfach
vorgestellt.
"""
from __future__ import annotations

import time

from .. import zustand
from . import _schluessel

NACHHOL_FENSTER_S = 3600  # eine Stunde; aelteres gilt als verpasst


def _feld_passt(teil: str, wert: int) -> bool:
    """Ein Cron-Feld gegen einen Wert. Unterstuetzt *, */n, a-b, Listen."""
    for stueck in teil.split(","):
        stueck = stueck.strip()
        if not stueck:
            return False
        schritt = 1
        if "/" in stueck:
            stueck, _, s = stueck.partition("/")
            if not s.isdigit() or int(s) == 0:
                return False
            schritt = int(s)
        if stueck in ("*", ""):
            von, bis = None, None
        elif "-" in stueck:
            a, _, b = stueck.partition("-")
            if not (a.isdigit() and b.isdigit()):
                return False
            von, bis = int(a), int(b)
        elif stueck.isdigit():
            von = bis = int(stueck)
        else:
            return False
        if von is None:
            if wert % schritt == 0:
                return True
        elif von <= wert <= bis and (wert - von) % schritt == 0:
            return True
    return False


def cron_passt(ausdruck: str, t: time.struct_time) -> bool:
    """Fuenf Felder: Minute Stunde Tag Monat Wochentag (0/7 = Sonntag)."""
    felder = ausdruck.split()
    if len(felder) != 5:
        return False
    wochentag = (t.tm_wday + 1) % 7  # Python Mo=0 -> Cron So=0
    # Sonntag darf 0 oder 7 heissen; auf 0 normieren statt Sonderfall im Feld.
    felder[4] = ",".join(
        "0" if teil.strip() == "7" else teil for teil in felder[4].split(","))
    werte = (t.tm_min, t.tm_hour, t.tm_mday, t.tm_mon, wochentag)
    for feld, wert in zip(felder, werte):
        if feld in ("*", "?"):
            continue
        if not _feld_passt(feld, wert):
            return False
    return True


def _letzte_cron_minute(ausdruck: str, jetzt: float, rueckblick_s: int):
    """Letzte Minute <= jetzt, in der der Cron-Ausdruck zutraf. None = keine."""
    start = int(jetzt // 60) * 60
    for i in range(0, int(rueckblick_s // 60) + 1):
        kandidat = start - i * 60
        if cron_passt(ausdruck, time.localtime(kandidat)):
            return kandidat
    return None


def pruefen(regeln, con, jetzt=None):
    from . import Ausloeser

    jetzt = float(jetzt if jetzt is not None else time.time())
    treffer = []

    for regel in regeln:
        b = regel.bedingungen
        marke = _schluessel("zeit", regel.id)
        vorher = zustand.marke_lesen(con, marke)
        vorher = float(vorher) if vorher else 0.0
        nur_wach = bool(b.get("nur_wenn_wach", True))

        if b.get("cron"):
            rueckblick = NACHHOL_FENSTER_S if nur_wach else 7 * 86400
            faellig = _letzte_cron_minute(b["cron"], jetzt, rueckblick)
            if faellig is None:
                # Nichts im Fenster. Marke vorstellen, damit ein spaeterer Lauf
                # nicht doch noch eine uralte Faelligkeit findet.
                if nur_wach and vorher and jetzt - vorher > NACHHOL_FENSTER_S:
                    zustand.marke_setzen(con, marke, int(jetzt))
                continue
            if vorher >= faellig:
                continue
            zustand.marke_setzen(con, marke, int(faellig))
            treffer.append(Ausloeser(
                regel_id=regel.id, typ="zeit",
                ausgeloest_durch="cron '%s' faellig %s" % (
                    b["cron"], time.strftime("%Y-%m-%d %H:%M", time.localtime(faellig))),
                werte={"faellig_unix": int(faellig)},
                prioritaet=regel.prioritaet,
            ))
            continue

        intervall_s = int(b.get("intervall_min", 0)) * 60
        if intervall_s <= 0:
            continue
        if vorher == 0.0:
            # Erster Lauf: Takt beginnen, aber nicht sofort ausloesen. Sonst
            # startet jede neue Intervall-Regel beim Einbau gleichzeitig.
            zustand.marke_setzen(con, marke, int(jetzt))
            continue
        if jetzt - vorher < intervall_s:
            continue
        zustand.marke_setzen(con, marke, int(jetzt))
        treffer.append(Ausloeser(
            regel_id=regel.id, typ="zeit",
            ausgeloest_durch="intervall %d min (letzter %s)" % (
                intervall_s // 60,
                time.strftime("%Y-%m-%d %H:%M", time.localtime(vorher))),
            werte={"faellig_unix": int(jetzt)},
            prioritaet=regel.prioritaet,
        ))

    return treffer
