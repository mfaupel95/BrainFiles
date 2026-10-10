"""Kill-Phase einer Spur: Frist, Reset des Ruecklaufs, Opt-out. Eine Stelle fuer alle.

HINTERGRUND (09.10.2026, PR #21): Der Kill leerte die Positionen ohne Buchung und
sperrte dauerhaft. `spur_buch.zyklus` bekam Zwangsschluss zum Marktkurs, eine Frist
(`kill_frist_stunden`, Standard 168 h) mit Reset des Ruecklaufs (`kill_ab_runde`, gelesen
von wachen_pruefung.lage) und den Opt-out `kill_wiederaufnahme: false`. Fuenf Spuren mit
eigenem Lauf (supertrend, squeeze, wavetrend, macd_mtf, moondev_funding) und iv_waelle
hatten denselben Defekt, dort ohne jede Frist. Damit die Regel nicht sechsmal
auseinanderlaeuft, steht sie hier und `spur_buch` ruft dieselbe Funktion.

Reine Zustandslogik: schreibt weder Zustand noch Journal; das tut der Aufrufer.
"""

from __future__ import annotations

from datetime import datetime, timezone

KILL_GRUND = "kill_zwangsschluss"


def _stunden_seit(zeitstempel):
    """Stunden seit `zeitstempel` (ISO) oder None, wenn fehlend/unlesbar."""
    if not zeitstempel:
        return None
    try:
        seit = datetime.fromisoformat(zeitstempel)
        if seit.tzinfo is None:
            seit = seit.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - seit).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return None


def phase(z, w, ruecklauf, runden_gesamt, jetzt):
    """Eine Kill-Runde. Nur aufrufen, wenn `lage()["kill"]` wahr ist.

    Rueckgabe (status, ruecklauf):
      "frei"   - Frist um und Wiederaufnahme erlaubt: `kill_seit` entfernt,
                 `kill_ab_runde` gesetzt, Ruecklauf 0. Der Zyklus laeuft normal weiter.
      "sperre" - der Zyklus handelt nicht; der Aufrufer schliesst offene Positionen
                 (Grund KILL_GRUND), schreibt den Zustand und endet.
    Mutiert `z` (kill_seit, kill_ruecklauf_usd, kill_ab_runde, kill_aufgehoben).
    `jetzt()` liefert den ISO-Zeitstempel fuer neue Eintraege.
    """
    frist_h = float(w.get("kill_frist_stunden", 168))
    verstrichen = _stunden_seit(z.get("kill_seit"))        # None: neuer Kill (auch unlesbar)
    automatisch = bool(w.get("kill_wiederaufnahme", True))

    if verstrichen is not None and verstrichen >= frist_h:
        if automatisch:
            print("- Kill-Frist abgelaufen (%.0f h) - Kill aufgehoben, der "
                  "Ruecklauf beginnt bei 0 (war %.2f USD)." % (verstrichen, ruecklauf))
            z.pop("kill_seit", None)
            z["kill_ab_runde"] = runden_gesamt
            z["kill_aufgehoben"] = jetzt()
            return "frei", 0.0
        # Opt-out: die Frist hebt nichts auf, nur ein Mensch (kill_seit aus dem Zustand).
        print("- Kill-Frist abgelaufen (%.0f h), aber kill_wiederaufnahme=false: "
              "Spur bleibt gesperrt, Freigabe nur von Hand." % verstrichen)
        return "sperre", ruecklauf

    if verstrichen is None:
        print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf). Offene Positionen "
              "werden zum Marktkurs geschlossen und gebucht. Frist: %.0f h."
              % (ruecklauf, frist_h))
        z["kill_seit"] = jetzt()
        z["kill_ruecklauf_usd"] = round(ruecklauf, 2)
    else:
        print("- Kill aktiv (%.2f USD Ruecklauf). Frist noch %.0f von %.0f h."
              % (ruecklauf, frist_h - verstrichen, frist_h))
    return "sperre", ruecklauf


def schliesse_alle(z, lade, pruefe):
    """Zwangsschluss fuer Spuren mit eigener Ausstiegsfunktion je Instrument.

    `lade(inst)` liefert die Kerzen (oder wirft), `pruefe(kerzen, inst)` ruft die
    Ausstiegsfunktion der Spur mit `erzwinge=KILL_GRUND`. Ohne Kurs bleibt die
    Position im Buch und der naechste Zyklus der Sperre versucht es erneut.
    Rueckgabe: Zahl der noch offenen Positionen.
    """
    import sys
    for inst in sorted({p.get("inst") for p in z.get("positionen", []) if p.get("inst")}):
        try:
            k = lade(inst)
        except Exception as e:                                       # noqa: BLE001
            print("  Kill: %s ohne Kurs (%s) - Position bleibt, naechster Zyklus "
                  "versucht es erneut" % (inst, str(e)[:80]), file=sys.stderr)
            continue
        if not k:
            print("  Kill: %s ohne Kerzen - Position bleibt" % inst, file=sys.stderr)
            continue
        pruefe(k, inst)
    offen = len(z.get("positionen", []))
    if offen:
        print("  %d Position(en) noch offen (kein Kurs) - naechster Zyklus "
              "versucht es erneut." % offen)
    return offen
