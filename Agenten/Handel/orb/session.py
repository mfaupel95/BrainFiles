"""Zeitrechnung der vierten Spur: Eroeffnung, DST, Opening-Range-Fenster,
Zwangsschluss, letzter Einstieg. Reine Funktionen, kein Netz.

Alle Rueckgaben sind tz-aware in UTC. Die Eroeffnung wird JE HANDELSTAG in der
Boersen-Lokalzeit gerechnet (SPEC.md: DST-fest ueber zoneinfo), dann nach UTC
gewandelt - eine feste UTC-Zeit waere im Winter eine Stunde daneben.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

RANGE_MINUTEN = 30  # die ersten zwei M15-Kerzen


def _lokal(inst_konf, tag, hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    zone = ZoneInfo(inst_konf["zone"])
    return datetime.combine(tag, time(h, m), tzinfo=zone)


def eroeffnung(inst_konf, tag):
    return _lokal(inst_konf, tag, inst_konf["eroeffnung"]).astimezone(timezone.utc)


def zwangsschluss(inst_konf, tag):
    return _lokal(inst_konf, tag, inst_konf["cash_close"]).astimezone(timezone.utc)


def opening_range_fenster(inst_konf, tag):
    start = eroeffnung(inst_konf, tag)
    return start, start + timedelta(minutes=RANGE_MINUTEN)


def letzter_einstieg(inst_konf, tag, min_vor_schluss):
    return zwangsschluss(inst_konf, tag) - timedelta(minutes=min_vor_schluss)


def handelstag(moment, zone):
    return moment.astimezone(ZoneInfo(zone)).date()


def in_session(inst_konf, moment):
    """True, wenn moment nach dem Opening-Range-Fenster und vor dem
    Zwangsschluss des zugehoerigen Boersen-Handelstags liegt."""
    tag = handelstag(moment, inst_konf["zone"])
    _, range_ende = opening_range_fenster(inst_konf, tag)
    return range_ende <= moment < zwangsschluss(inst_konf, tag)
