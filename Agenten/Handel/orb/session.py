"""Zeitrechnung der vierten Spur (OKX): UTC-Tagesgrenze statt Boersen-Open.

Krypto laeuft 24/7 - es gibt kein "Opening". Die Opening Range sind die ersten
zwei abgeschlossenen M15-Kerzen ab Tagesgrenze 00:00 UTC (deckt den
Funding-Rollover der Perpetuals), Session-Ende 24:00 UTC. Reine Funktionen,
kein Netz, keine zoneinfo-Abhaengigkeit.
"""

from datetime import date, datetime, time, timedelta, timezone

RANGE_MINUTEN = 30  # die ersten zwei M15-Kerzen
UTC = timezone.utc


def eroeffnung(inst_konf, tag):
    return datetime.combine(tag, time(0, 0), tzinfo=UTC)


def zwangsschluss(inst_konf, tag):
    return datetime.combine(tag + timedelta(days=1), time(0, 0), tzinfo=UTC)


def opening_range_fenster(inst_konf, tag):
    start = eroeffnung(inst_konf, tag)
    return start, start + timedelta(minutes=RANGE_MINUTEN)


def letzter_einstieg(inst_konf, tag, min_vor_schluss):
    return zwangsschluss(inst_konf, tag) - timedelta(minutes=min_vor_schluss)


def handelstag(moment, zone=None):
    return moment.astimezone(UTC).date()


def in_session(inst_konf, moment):
    """True, wenn moment nach dem Opening-Range-Fenster und vor dem
    Tagesende des zugehoerigen UTC-Handelstags liegt."""
    tag = handelstag(moment)
    _, range_ende = opening_range_fenster(inst_konf, tag)
    return range_ende <= moment < zwangsschluss(inst_konf, tag)