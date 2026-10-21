# -*- coding: utf-8 -*-
"""Wache fuer den omnitrade2-SOL-XPERP-Live-Lauf (Auftrag Max 21.10.2026).

Prueft den Loop unter Agenten/Hermes/cache/omnitrade2/:
  1. Status frisch? (updated_ms < 10 min) - sonst Loop tot/hangend.
  2. Neue Orders seit letzter Pruefung? -> melden (die erste Order ist der
     Beweis, dass die Strategie handelt).
  3. Abgelehnte Orders (orders_rejected) -> melden (RiskGuard oder Boerse).
  4. Offene Position tief im Minus? (Entry aus recent_orders, -2,5 % gegen
     last_close - der Boersen-Stop liegt bei 2 %, -25 % war nach dem
     Stop-Einbau toter Code) -> melden.
  5. Letzter Fehler im Status -> einmal melden.
  6. BOERSENABGLEICH (Entscheidung Max 21.10.2026), drei Pruefungen:
     a) Position da, aber kein (vollstaendiger) Schutz-Stop an der Boerse,
     b) Loop fuehrt eine Position, die Boerse kennt keine (oder umgekehrt),
     c) Loop-Stand weicht von der Boersenmenge ab (> 0,5 Kontrakte).
  7. Loop lebt, hat aber 0 Orders platziert, obwohl Signale kamen und Orders
     abgelehnt wurden -> der Orderweg ist kaputt (genau der Zustand vom
     21.10.: 12 Rejects, 0 Fills, und niemandem fiel es als Wegfehler auf).

Muster: leere Ausgabe = nichts zu melden (nichts senden). Ein Fehler der
PRUEFUNG selbst darf nie in diesen stillen Zweig fallen - er wird gemeldet.

Merkdatei: Agenten/Hermes/cache/omnitrade2/wache-zustand.json
"""
import importlib.util
import json
import os
import subprocess
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
# Agenten/Hermes/scripts -> Agenten/Hermes/cache/omnitrade2
CACHE = os.path.join(HIER, "..", "cache", "omnitrade2")
CACHE = os.path.normpath(CACHE)
STATUS_FILE = os.path.join(CACHE, "sol-xperp-status.json")
MERK_FILE = os.path.join(CACHE, "wache-zustand.json")

FRESH_MS = 10 * 60 * 1000  # Status muss juester sein (eine 1m-Kerze + Puffer)
LOSS_PCT_WARN = 2.5  # Boersen-Stop liegt bei 2 % - -25 % waere nie erreicht worden
MAX_MELDUNGEN_PRO_TAG = 6
# Abbruchkriterium des Versuchs (Entscheidung Max 21.10.2026): der Lauf bekommt
# 48 h; vorher wird er nur bei kumuliert -2,50 USD oder nach drei
# Verlustrunden in Folge zur Entscheidung gemeldet.
ABBRUCH_USD = -2.5
VERLUSTE_IN_FOLGE = 3
# Nachzieher = EINE Quelle fuer Boersenposition, Deckung und Stop-Regeln.
NACHZIEHER = os.path.normpath(
    os.path.join(HIER, "..", "..", "Handel", "omnitrade2", "nachziehen.py")
)
OHNE_ORDER_KERZEN = 120  # zwei Stunden 1m-Kerzen ohne eine einzige Order = Wegfehler


def basis_je_kontrakt(okxf, inst):
    """ctVal des Kontrakts in Basis-Einheiten (0.0 = unbekannt).

    Der Loop fuehrt net_quantity in BASIS-Einheiten (0.19 SOL), die Boerse in
    KONTRAKTEN (19) - ohne ctVal ist der Vergleich zweier Zahlen aus
    verschiedenen Einheiten und meldet bei jeder Position eine Abweichung.
    """
    try:
        d = okxf.instrument(inst) or {}
        return float(d.get("ctVal") or 0.0)
    except Exception:  # noqa: BLE001 - unbekannt heisst: nicht vergleichen
        return 0.0


def lade_merk():
    try:
        with open(MERK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def schreibe_merk(merk):
    os.makedirs(CACHE, exist_ok=True)
    tmp = MERK_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(merk, f, indent=1)
    os.replace(tmp, MERK_FILE)


def heutig(merk):
    if merk.get("tag") != time.strftime("%Y-%m-%d"):
        merk["tag"] = time.strftime("%Y-%m-%d")
        merk["meldungen"] = 0
        merk["deckel_zaehler"] = 0
    return merk


def ist_deckel(text):
    """Ist das eine Ablehnung durch den POSITIONSDECKEL?

    Solche Ablehnungen sind erwartetes Verhalten: der Plan haelt nur so viele
    Stufen, wie der Deckel zulaesst, und die Strategie wiederholt ihr Signal
    minuetlich. Sie werden gezaehlt, nicht als Fehler gemeldet
    (Entscheidung Max 21.10.2026).
    """
    return "positionsdeckel" in str(text or "").lower()


def meldung(merk, text):
    """Gibt True, wenn gemeldet werden darf (Tageslimit beachten)."""
    if merk.get("meldungen", 0) >= MAX_MELDUNGEN_PRO_TAG:
        return False
    merk["meldungen"] = merk.get("meldungen", 0) + 1
    print(text)
    return True


def _nachzieher():
    """Das Nachzieher-Modul ueber den PFAD laden (kein sys.path-Eintrag)."""
    if not os.path.exists(NACHZIEHER):
        return None, "Nachzieher fehlt: %s" % NACHZIEHER
    try:
        spec = importlib.util.spec_from_file_location("omnitrade2_nachziehen_wache", NACHZIEHER)
        modul = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = modul
        spec.loader.exec_module(modul)
        return modul, None
    except Exception as e:  # noqa: BLE001 - jeder Ladefehler ist ein Befund
        return None, "Nachzieher nicht ladbar: %s" % e


def boersenpruefung(merk, st, net):
    """Drei Pruefungen gegen die BOERSE. Rueckgabe: Zahl der Meldungen."""
    modul, fehler = _nachzieher()
    if modul is None:
        return 1 if meldung(merk, "omnitrade2-Wache: %s" % fehler) else 0
    inst = st.get("symbol") or ""
    try:
        okxf = modul.okxf_laden()
        pos = modul.position(okxf, inst)
        # Richtungsgebunden (Entscheidung Max 21.10.2026): ein Stop der
        # GEGENRICHTUNG deckt die Position nicht.
        gedeckt, anzahl, fremde = (modul.deckung(okxf, inst, pos["seite"]) if pos
                                   else (0.0, 0, []))
    except Exception as e:  # noqa: BLE001 - ein Prueffeheler darf nie still bleiben
        return 1 if meldung(merk, "omnitrade2-Wache: Boersenabfrage scheiterte: %s" % e) else 0

    meldet = 0
    if pos is None:
        if abs(net) > 0 and merk.get("drift_gemeldet") != "boerse-leer":
            merk["drift_gemeldet"] = "boerse-leer"
            meldet += meldung(
                merk,
                "omnitrade2-Wache: Loop fuehrt %+.4f Basiseinheiten, die BOERSE kennt "
                "keine Position (%s)" % (net, inst),
            )
        return meldet
    merk.pop("drift_gemeldet", None)

    luecke = abs(pos["menge"]) - gedeckt
    if luecke >= modul.MIN_LUECKE:
        schluessel = "stop-fehlt-%.2f" % round(luecke, 2)
        if merk.get("stop_gemeldet") != schluessel:
            merk["stop_gemeldet"] = schluessel
            meldet += meldung(
                merk,
                "omnitrade2-Wache: Position %+.2f (%.2f Kontrakte) OHNE vollstaendigen "
                "Schutz-Stop - gedeckt %.2f in %d Auftrag/Auftraegen%s"
                % (
                    pos["menge"],
                    abs(pos["menge"]),
                    gedeckt,
                    anzahl,
                    ("; %d Stop(s) der Gegenrichtung liegen falsch" % len(fremde))
                    if fremde else "",
                ),
            )
    else:
        merk.pop("stop_gemeldet", None)

    if abs(net) > 0:
        ctval = basis_je_kontrakt(okxf, inst)
        soll_kontrakte = net / ctval if ctval > 0 else net
        if abs(abs(pos["menge"]) - abs(soll_kontrakte)) > 0.5:
            schluessel = "menge-%.2f-%.2f" % (round(net, 2), round(pos["menge"], 2))
            if merk.get("menge_gemeldet") != schluessel:
                merk["menge_gemeldet"] = schluessel
                meldet += meldung(
                    merk,
                    "omnitrade2-Wache: Loop-Stand %+.4f Basiseinheiten (=%+.2f Kontrakte) "
                    "weicht von der BOERSE ab (%+.2f Kontrakte)"
                    % (net, soll_kontrakte, pos["menge"]),
                )
    else:
        merk.pop("menge_gemeldet", None)
    return meldet


def orderwegpruefung(merk, st):
    """Loop lebt, aber 0 Orders platziert: der WEG ist kaputt, nicht der Markt."""
    platziert = int(st.get("orders_placed", 0))
    kerzen = int(st.get("candles_seen", 0))
    abgelehnt = int(st.get("orders_rejected", 0))
    if platziert == 0 and kerzen >= OHNE_ORDER_KERZEN and abgelehnt > 0:
        schluessel = "ohne-order-%d" % abgelehnt
        if merk.get("orderweg_gemeldet") != schluessel:
            merk["orderweg_gemeldet"] = schluessel
            return 1 if meldung(
                merk,
                "omnitrade2-Wache: Loop lebt (%d Kerzen), aber 0 Orders platziert bei "
                "%d ABGELEHNTEN - der Orderweg ist kaputt, nicht der Markt (Log: %s)"
                % (kerzen, abgelehnt, os.path.join(CACHE, "sol-xperp.log")),
            ) else 0
    elif platziert > 0:
        merk.pop("orderweg_gemeldet", None)
    return 0


def _arg_wert(zeile, name):
    """Zahl hinter '--name 0.19' aus einer Kommandozeile (None, wenn nicht da)."""
    teile = str(zeile or "").split()
    for i, t in enumerate(teile):
        if t == name and i + 1 < len(teile):
            try:
                return float(teile[i + 1].strip('"'))
            except ValueError:
                return None
    return None


def lauf_argumente(inst):
    """Kommandozeile des LAUFENDEN Prozesses fuer dieses Instrument (Naht)."""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='omnitrade-cli.exe'\" | "
        "Where-Object { $_.CommandLine -like '*%s*' } | "
        "Select-Object -First 1 -ExpandProperty CommandLine" % inst
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=90,
        )
    except Exception as e:  # noqa: BLE001 - Prueffeheler ist ein Befund
        return None, str(e)
    zeile = (r.stdout or "").strip()
    return (zeile or None), None


def parameterpruefung(merk):
    """Laeuft der Prozess mit den Parametern, die lauf.json nennt?

    Anlass 21.10.2026: der Lauf wurde von aussen mit quantity 0.19 neu
    gestartet, waehrend lauf.json 0.01/mikro trug - der Nachzieher haette
    danach ein zweites Hochziehen ausgeloest. Eine Datei, die den Lauf
    beschreibt, muss gegen den LAUFENDEN Prozess geprueft werden.
    """
    pfad = os.path.join(HIER, "..", "..", "Handel", "omnitrade2", "lauf.json")
    pfad = os.path.normpath(pfad)
    try:
        with open(pfad, encoding="utf-8") as f:
            lauf = json.load(f)
    except Exception as e:  # noqa: BLE001
        return 1 if meldung(merk, "omnitrade2-Wache: lauf.json nicht lesbar (%s): %s" % (pfad, e)) else 0

    inst = lauf.get("inst") or ""
    soll = float(lauf.get("quantity") or 0.0)
    zeile, fehler = lauf_argumente(inst)
    if fehler:
        return 1 if meldung(merk, "omnitrade2-Wache: Prozessabfrage scheiterte: %s" % fehler) else 0
    if zeile is None:
        return 0  # kein Prozess: das meldet schon die Stillstandspruefung

    ist = _arg_wert(zeile, "--quantity")
    if ist is None:
        schluessel = "ohne-quantity"
        if merk.get("parameter_gemeldet") != schluessel:
            merk["parameter_gemeldet"] = schluessel
            return 1 if meldung(merk, "omnitrade2-Wache: laufender Prozess hat KEIN --quantity - lauf.json (%s) beschreibt einen anderen Lauf" % soll) else 0
        return 0
    if abs(ist - soll) > 1e-9:
        schluessel = "qty-%.4f-%.4f" % (soll, ist)
        if merk.get("parameter_gemeldet") != schluessel:
            merk["parameter_gemeldet"] = schluessel
            return 1 if meldung(
                merk,
                "omnitrade2-Wache: lauf.json sagt quantity %s, der LAUFENDE Prozess faehrt %s "
                "- Datei und Lauf sind auseinander (Restart von aussen?)" % (soll, ist),
            ) else 0
        return 0
    merk.pop("parameter_gemeldet", None)
    return 0


def ablehnungen(merk, st):
    """Regel 3: neue Ablehnungen. Deckel = NORMAL, alles andere = Befund.

    Eine Ablehnung durch den Positionsdeckel ist erwartetes Verhalten
    (Entscheidung Max 21.10.2026): der Plan haelt nur so viele Stufen, wie der
    Deckel zulaesst, und die Strategie wiederholt ihr Signal minuetlich. Sie
    wird gezaehlt und hoechstens einmal am Tag in EINER Zeile genannt - vorher
    erzeugte jede Aenderung des Notional-Werts im Meldungstext eine neue
    Meldung (6 an einem Vormittag).
    """
    rejected = int(st.get("orders_rejected", 0))
    vorher = int(merk.get("rejected_seen", 0))
    if rejected <= vorher:
        return 0
    merk["rejected_seen"] = rejected
    if ist_deckel(st.get("last_error", "")):
        merk["deckel_zaehler"] = int(merk.get("deckel_zaehler", 0)) + (rejected - vorher)
        if merk.get("deckel_gemeldet") != merk.get("tag") and merk["deckel_zaehler"] > 0:
            merk["deckel_gemeldet"] = merk.get("tag")
            return 1 if meldung(
                merk,
                "omnitrade2-Wache: %d Deckel-Ablehnung(en) heute - normal, der Plan "
                "haelt nur begrenzte Stufen (nichts zu tun)." % merk["deckel_zaehler"],
            ) else 0
        return 0
    return 1 if meldung(
        merk,
        "omnitrade2-Wache: %d Order(s) ABGELEHNT (RiskGuard oder Boerse) - Log pruefen."
        % rejected,
    ) else 0


def abbruchpruefung(merk, st):
    """Abbruchkriterium des Versuchs (Entscheidung Max 21.10.2026).

    Der Versuch laeuft 48 h. Vorher wird er nur beendet, wenn
      a) die Summe der realisierten Ergebnisse seit dem Start -2,50 USD
         erreicht oder
      b) drei Verlustrunden in Folge geschlossen wurden.
    Die Wache STOPPT nichts - sie meldet, entschieden wird von Max.

    Quelle ist die BOERSE (`positions-history`, realizedPnl), nicht der Loop:
    der Status des Laufs fuehrt kein Ergebnis.
    """
    modul, _fehler = _nachzieher()
    if modul is None:
        return 0  # der Ladefehler wird in boersenpruefung gemeldet
    inst = st.get("symbol") or ""
    try:
        seit = int(st.get("started_ms") or 0)
    except (TypeError, ValueError):
        seit = 0
    try:
        eintraege = modul.okxf_laden().geschlossene_positionen(inst, 20) or []
    except Exception:  # noqa: BLE001 - ein Prueffehlschlag darf nicht still bleiben
        return 0

    kumuliert = 0.0
    folge = 0
    folge_offen = True
    for e in eintraege:
        try:
            zeit = int(e.get("uTime") or 0)
        except (TypeError, ValueError):
            continue
        if seit and zeit < seit:
            continue
        try:
            pnl = float(e.get("realizedPnl") or 0.0)
        except (TypeError, ValueError):
            continue
        kumuliert += pnl
        if folge_offen:
            if pnl < 0:
                folge += 1
            else:
                folge_offen = False

    grund = None
    if seit and kumuliert <= ABBRUCH_USD:
        grund = "kumuliert %.2f USD seit Start (Grenze %.2f)" % (kumuliert, ABBRUCH_USD)
    elif seit and folge >= VERLUSTE_IN_FOLGE:
        grund = "%d Verlustrunden in Folge" % folge
    if grund is None:
        merk.pop("abbruch_gemeldet", None)
        return 0
    if merk.get("abbruch_gemeldet") == grund:
        return 0
    merk["abbruch_gemeldet"] = grund
    return 1 if meldung(
        merk,
        "omnitrade2-Wache: ABBRUCHKRITERIUM erreicht - %s. Der Loop laeuft weiter, "
        "der Boersen-Stop schuetzt; Entscheidung faellig (stoppen oder weiter)." % grund,
    ) else 0


def haupt():
    merk = heutig(lade_merk())
    meldet = 0

    if not os.path.exists(STATUS_FILE):
        if not merk.get("status_fehlt_gemeldet"):
            merk["status_fehlt_gemeldet"] = True
            schreibe_merk(merk)
            meldet += meldung(merk, "omnitrade2-Wache: Status-Datei fehlt - Loop gestartet?")
        schreibe_merk(merk)
        return meldet

    try:
        with open(STATUS_FILE, encoding="utf-8") as f:
            st = json.load(f)
    except (OSError, ValueError) as e:
        schreibe_merk(merk)
        return meldet + (1 if meldung(merk, "omnitrade2-Wache: Status nicht lesbar: %s" % e) else 0)

    jetzt = int(time.time() * 1000)
    alter = jetzt - st.get("updated_ms", 0)
    state = st.get("state", "?")
    pid = st.get("pid", "?")

    # 1) Leben: Status frische ist der Lebensbeweis (Loop schreibt je Kerze).
    if alter > FRESH_MS:
        key = "stall-%s" % ("tot" if state != "running" else "hang")
        if merk.get("stall_gemeldet") != key:
            merk["stall_gemeldet"] = key
            if state != "running":
                meldet += meldung(
                    merk,
                    "omnitrade2-Wache: Loop STOPPT (state=%s, PID %s, letzter Fehler: %r)"
                    % (state, pid, st.get("last_error", "")),
                )
            else:
                meldet += meldung(
                    merk,
                    "omnitrade2-Wache: Loop HAENGT (state=running, Status %d min alt, PID %s)"
                    % (alter // 60000, pid),
                )
        schreibe_merk(merk)
        return meldet
    merk.pop("stall_gemeldet", None)
    merk.pop("status_fehlt_gemeldet", None)

    # 2) Neue Orders.
    seen = merk.get("orders_seen", 0)
    placed = int(st.get("orders_placed", 0))
    if placed > seen:
        merk["orders_seen"] = placed
        for order in st.get("recent_orders", [])[-(placed - seen):]:
            meldet += meldung(
                merk,
                "omnitrade2-Wache: NEUE ORDER %s %s Menge %.4f (orders gesamt: %d)"
                % (
                    order.get("side", "?"),
                    st.get("symbol", "?"),
                    float(order.get("quantity", 0) or 0),
                    placed,
                ),
            )
        if placed - seen > 0 and len(st.get("recent_orders", [])) == 0:
            meldet += meldung(merk, "omnitrade2-Wache: %d neue Order(s), Details im Log." % (placed - seen))

    # 3) Abgelehnte Orders (RiskGuard/Boerse).
    meldet += ablehnungen(merk, st)

    # 4) Offene Position im Minus: Entry = letzte Order der Position Richtung.
    #    Long: Kurs fallend gegen Entry. Short: Kurs steigend gegen Entry.
    minus_pct = None
    net = float(st.get("net_quantity", 0.0) or 0.0)
    last_close = float(st.get("last_close", 0.0) or 0.0)
    if abs(net) > 0 and last_close > 0:
        wanted = "buy" if net > 0 else "sell"
        for order in reversed(st.get("recent_orders", [])):
            if order.get("side") == wanted and order.get("price"):
                entry = float(order["price"])
                if net > 0:
                    minus_pct = (entry - last_close) / entry * 100.0
                else:
                    minus_pct = (last_close - entry) / entry * 100.0
                break
    if minus_pct is not None:
        if minus_pct >= LOSS_PCT_WARN:
            if merk.get("minus_gemeldet") is None or minus_pct - merk.get("minus_gemeldet", 0) >= 10:
                merk["minus_gemeldet"] = minus_pct
                meldet += meldung(
                    merk,
                    "omnitrade2-Wache: Position %+.4f (%s) zu -%.1f %% (Entry %s, jetzt %.2f)"
                    % (net, "long" if net > 0 else "short", minus_pct, entry, last_close),
                )
        else:
            merk.pop("minus_gemeldet", None)
    else:
        merk.pop("minus_gemeldet", None)

    # 5) Letzter Fehler (einmal pro Fehlermeldung). Eine Deckel-Ablehnung ist
    #    kein Fehler - sie traegt den Notional-Wert im Text und wuerde sonst bei
    #    jedem Tick als "neu" gelten (heute 6 Meldungen daraus).
    last_error = st.get("last_error", "")
    if last_error and ist_deckel(last_error):
        merk["error_gemeldet"] = last_error
    elif last_error and merk.get("error_gemeldet") != last_error:
        merk["error_gemeldet"] = last_error
        meldet += meldung(merk, "omnitrade2-Wache: letzter Fehler im Loop: %s" % last_error[:200])

    # 6) Boersenabgleich (Position, Stop-Deckung, Mengendrift).
    meldet += boersenpruefung(merk, st, net)
    # 7) Orderweg: lebt der Loop, ohne je zu handeln?
    meldet += orderwegpruefung(merk, st)
    # 8) Faehrt der Prozess die Parameter, die lauf.json beschreibt?
    meldet += parameterpruefung(merk)
    # 9) Abbruchkriterium erreicht? (meldet, stoppt nichts)
    meldet += abbruchpruefung(merk, st)

    schreibe_merk(merk)
    return meldet


if __name__ == "__main__":
    sys.exit(0 if haupt() is not None else 1)
