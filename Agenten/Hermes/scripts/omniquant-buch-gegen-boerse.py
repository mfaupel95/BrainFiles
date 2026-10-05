"""Buch gegen Boerse: welche der 9 Positionen existieren wirklich?

Auftrag Max 05.10.2026: "NEAR freigeben". Die Freigabe ist seit 01.10.
erteilt - das ergab die Gegenprobe. Der Grund fuer "kein Einstieg" liegt
woanders, und der ist wichtiger als die Freigabe:

Das Buch fuehrt 9 Positionen im Modus `live`, davon 8 OHNE `modus`-Feld
und OHNE `einsatz_usd`. Das ist dieselbe Klasse wie T-319 (ZRO, 02.10.) und
T-354 (GENIUS/BTC, 05.10.): eine Position ohne Modus ist nicht als Papier
erkennbar, also kann `bueche_papier_altlasten_aus()` sie nicht ausbuchen.

Gesucht wird deshalb die Antwort auf zwei Fragen, und beide stehen in
`live_max_offene_positionen: 1`:
  1. Wie viele dieser 9 stehen WIRKLICH an der Boerse?
  2. Ist das Buch voll - und ist es voll, weil die Spur gehandelt hat oder
     weil sie Geister zaehlt?

Rein lesend. Keine Order, kein Storno, keine Freigabe-Aenderung.
"""
import importlib.util
import json
import os
import sys

HANDEL = r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel"
SPUR = os.path.join(HANDEL, "omniquant")


def lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


kp = lade(os.path.join(SPUR, "kraken_perp.py"), "kp")
kp.lade_maerkte()
kp.setze_ableitung(True)

z = json.load(open(os.path.join(SPUR, "zustand.json"), encoding="utf-8"))
buch = z.get("positionen") or []

print("Buch: %d Positionen, modus=%s" % (len(buch), z.get("modus")))
print("\n%-14s %-9s %-9s  %s" % ("im Buch", "modus?", "einsatz?", "an der Boerse?"))
print("-" * 74)

echt = geister = 0
for p in buch:
    inst = p.get("inst")
    hat_modus = p.get("modus")
    einsatz = p.get("einsatz_usd")
    try:
        pos = kp.offene_positionen(inst)
        n = len(pos) if isinstance(pos, (list, dict)) else 0
        if n:
            echt += 1
            print("%-14s %-9s %-9s  JA (%d Position/en)" % (
                inst, hat_modus or "FEHLT",
                einsatz if einsatz else "FEHLT", n))
        else:
            geister += 1
            print("%-14s %-9s %-9s  NEIN - 0 offene" % (
                inst, hat_modus or "FEHLT",
                einsatz if einsatz else "FEHLT"))
    except Exception as e:                                     # noqa: BLE001
        geister += 1
        print("%-14s %-9s %-9s  ABFRAGE FEHLGESCHLAGEN: %s"
              % (inst, hat_modus or "FEHLT", einsatz if einsatz else "FEHLT",
                 str(e)[:44]))

print("\n  echt an der Boerse: %d" % echt)
print("  nur im Buch:        %d" % geister)

print("\n=== Die Sperre, die daraus folgt ===")
w = json.load(open(os.path.join(SPUR, "wachen.json"), encoding="utf-8"))
maxi = w.get("live_max_offene_positionen")
print("  live_max_offene_positionen = %s" % maxi)
if len(buch) >= maxi:
    print("  -> DAS BUCH IST VOLL. Kein neuer Einstieg, unabhaengig von")
    print("     jedem Signal: %d Positionen >= %s Plaetze." % (len(buch), maxi))
    print("  -> Die Freigabe von NEAR aendert daran NICHTS. Der Einstieg")
    print("     scheitert am Platz, nicht am Tor.")
else:
    print("  -> %d von %s Plaetzen belegt, es ist Platz." % (len(buch), maxi))

print("\n=== Und die Freigabe selbst, zur Klarstellung ===")
print("  live_pf_ableitung = %s (seit 01.10.2026, Auftrag Max)"
      % w.get("live_pf_ableitung"))
print("  NEAR-USDC/USDT loesen beide auf PF_NEARUSD auf - geprueft gegen")
print("  /instruments, 204 tradeable PF_-Maerkte, 05.10.2026.")

frei = kp.guthaben_usd()
print("\n  freie Margin: %.2f USD" % frei)
print("  -> NEAR bei 50 USD Einsatz, Hebel 6: 61 Kontrakte, 29.97 USD")
print("     Einschuss. Das Guthaben-Tor (>= %.2f) waere offen."
      % float(w.get("mindest_guthaben_usd", 0)))