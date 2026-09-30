"""Steuerung: vom Ausloeser zum protokollierten Lauf.

Hier wird entschieden, nicht gerechnet. Die Reihenfolge der Pruefungen ist
Absicht - billig und hart zuerst, teuer und weich zuletzt, damit ein gesperrter
oder abgeschalteter Lauf gar nicht erst in die Naehe eines Prozessstarts kommt:

  1. Modus gesperrt              -> uebersprungen
  2. Dauersperre (Fehlerstreak)  -> uebersprungen
  3. abbruch.nur_wenn_pfad_existiert / nicht_wenn_regel_laeuft / max_gleichzeitig
  4. Rate-Limit (max_laeufe im Fenster) und cooldown_s
  5. Modus bestaetigung          -> Frage anlegen, Lauf nur bei vorliegendem 'ja'
  6. Modus dry_run               -> Trockenlauf
  7. Modus auto                  -> echter Lauf unter der Wache

Jeder Ausgang schreibt genau eine Zeile ins JSONL-Log und (ausser bei
uebersprungen) eine Zeile in die Lauftabelle. Ein uebersprungener Lauf gehoert
nicht in die Rate-Limit-Statistik, sonst sperrt sich eine Regel durch ihre
eigenen Ablehnungen selbst aus (siehe zustand.laeufe_im_fenster).
"""
from __future__ import annotations

import os
import time

from . import lauf, pfade, protokoll, zustand

# Ergebnisse, die als Fehlschlag in die Streak-Zaehlung gehen.
FEHLSCHLAG = ("fehler", "timeout", "verstoss")


def _log(regel, ausloeser, ergebnis, registry_version, dauer_ms=0, exit_code=None,
         aktionen=None, grund=None, ausgabe="", extra=None):
    eintrag = protokoll.eintrag_bauen(
        regel_id=regel.id,
        trigger_typ=ausloeser.typ,
        ausgeloest_durch=ausloeser.ausgeloest_durch,
        skill=regel.skill,
        modus=regel.modus,
        ergebnis=ergebnis,
        dauer_ms=dauer_ms,
        exit_code=exit_code,
        aktionen_genutzt=aktionen,
        abbruchgrund=grund,
        ausgabe=ausgabe,
        registry_version=registry_version,
        extra=extra,
    )
    return protokoll.schreiben(eintrag)


def _uebersprungen(regel, ausloeser, grund, version, extra=None):
    """Nicht gelaufen: nur Log, kein Eintrag in der Lauftabelle."""
    return _log(regel, ausloeser, "uebersprungen", version, grund=grund, extra=extra)


def _rate_limit_frei(regel, con) -> str | None:
    grenze = regel.rate_limit or {}
    max_laeufe = int(grenze.get("max_laeufe", 0) or 0)
    fenster_s = int(grenze.get("fenster_s", 0) or 0)
    if max_laeufe and fenster_s:
        bisher = zustand.laeufe_im_fenster(con, regel.id, fenster_s)
        if bisher >= max_laeufe:
            return "Rate-Limit: %d/%d Laeufe in %ds" % (bisher, max_laeufe, fenster_s)

    cooldown = int(grenze.get("cooldown_s", 0) or 0)
    if cooldown:
        letzter = zustand.letzter_lauf(con, regel.id)
        if letzter:
            alter = int(time.time()) - int(letzter["zeit_unix"])
            if alter < cooldown:
                return "Cooldown: noch %ds" % (cooldown - alter)
    return None


def _abbruch_frei(regel, con) -> str | None:
    a = regel.abbruch or {}

    for p in a.get("nur_wenn_pfad_existiert") or []:
        if not pfade.absolut(p).exists():
            return "Pfad fehlt: %s" % p

    laufende = zustand.laufende_regeln(con)
    for andere in a.get("nicht_wenn_regel_laeuft") or []:
        if andere in laufende:
            return "Regel '%s' laeuft gerade" % andere

    max_gleich = int(a.get("max_gleichzeitig", 0) or 0)
    if max_gleich and zustand.belegt_zahl(con, regel.id) >= max_gleich:
        return "schon %d gleichzeitige Laeufe" % max_gleich

    return None


def _streak_pruefen(regel, con) -> None:
    """Nach einem Fehlschlag: Dauersperre setzen, wenn die Streak reicht."""
    grenze = int((regel.abbruch or {}).get("bei_fehlerstreak", 0) or 0)
    if not grenze:
        return
    if zustand.fehlerstreak(con, regel.id) >= grenze:
        zustand.sperren(con, regel.id,
                        "bei_fehlerstreak=%d erreicht" % grenze)


def _bestaetigung(regel, ausloeser, con, version):
    """S8: Rueckfrage ueber den Kanal, Start erst nach Ja, Verfall = Nein."""
    antwort = zustand.bestaetigung_antwort(con, regel.id)
    if antwort == "ja":
        return True, None
    if antwort == "nein":
        zustand.lauf_merken(con, regel.id, "abgelehnt", trigger_typ=ausloeser.typ,
                            ausgeloest_durch=ausloeser.ausgeloest_durch,
                            abbruchgrund="Bestaetigung verweigert oder verfallen")
        return False, _log(regel, ausloeser, "abgelehnt", version,
                           grund="Bestaetigung verweigert oder verfallen")

    frage = "Regel '%s' (%s) starten? Ausgeloest durch: %s" % (
        regel.id, regel.skill, ausloeser.ausgeloest_durch)
    zustand.bestaetigung_anlegen(con, regel.id, frage, regel.kanal, regel.timeout_s)
    return False, _log(regel, ausloeser, "bestaetigung_offen", version, grund=frage)


def ausfuehren(regel, ausloeser, con, registry_version="") -> dict:
    """Einen Ausloeser abarbeiten. Rueckgabe: der geschriebene Logeintrag."""
    if regel.modus == "gesperrt":
        return _uebersprungen(regel, ausloeser,
                              "Regel ist in der Registry gesperrt", registry_version)

    sperre = zustand.ist_gesperrt(con, regel.id)
    if sperre:
        return _uebersprungen(regel, ausloeser,
                              "Dauersperre: %s" % sperre, registry_version)

    grund = _abbruch_frei(regel, con)
    if grund:
        return _uebersprungen(regel, ausloeser, grund, registry_version)

    grund = _rate_limit_frei(regel, con)
    if grund:
        return _uebersprungen(regel, ausloeser, grund, registry_version)

    if regel.modus == "bestaetigung":
        weiter, eintrag = _bestaetigung(regel, ausloeser, con, registry_version)
        if not weiter:
            return eintrag

    if regel.modus == "dry_run":
        e = lauf.trockenlauf(regel, ausloeser.werte)
        zustand.lauf_merken(con, regel.id, "dry_run", trigger_typ=ausloeser.typ,
                            ausgeloest_durch=ausloeser.ausgeloest_durch)
        return _log(regel, ausloeser, "dry_run", registry_version,
                    grund=e.grund, extra={"kommando": e.kommando})

    belegung = zustand.belegen(con, regel.id, os.getpid())
    try:
        e = lauf.starten(regel, ausloeser.werte)
    finally:
        zustand.freigeben(con, belegung)

    if e.ergebnis == "uebersprungen":
        return _uebersprungen(regel, ausloeser, e.grund, registry_version)

    zustand.lauf_merken(
        con, regel.id, e.ergebnis, exit_code=e.exit_code, dauer_ms=e.dauer_ms,
        trigger_typ=ausloeser.typ, ausgeloest_durch=ausloeser.ausgeloest_durch,
        abbruchgrund=e.grund or None,
    )
    if e.ergebnis in FEHLSCHLAG:
        _streak_pruefen(regel, con)

    extra = {"kommando": e.kommando}
    if e.verstoesse:
        extra["verstoesse"] = e.verstoesse
    if e.netz_ziele:
        extra["netz_ziele"] = e.netz_ziele

    return _log(regel, ausloeser, e.ergebnis, registry_version,
                dauer_ms=e.dauer_ms, exit_code=e.exit_code,
                aktionen=e.aktionen_genutzt, grund=e.grund or None,
                ausgabe=e.ausgabe, extra=extra)
