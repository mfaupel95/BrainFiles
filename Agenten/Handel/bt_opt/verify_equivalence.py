"""Unabhaengige Aequivalenzpruefung: bt_varianten_fast.py vs. echter Spurcode.

Vergleicht fuer die Spuren macd_mtf und squeeze:

  (1) SIGNAL: fuer jeden Index i von mindest_kerzen bis 1200 das schnelle
      Signal (vorberechnet auf der vollen Serie) gegen das echte Signal aus
      <spur>/handeln.py (signal(k[:i+1], i), je Schritt neu gerechnet).

  (2) EINSTIEGSLOGIK: an jeder Stelle, an der BEIDE long sagen, wird die
      Position aus pruefe_einstieg() (echt) gegen die Kopie _einstieg()
      (bt_varianten_fast.py) verglichen - gleicher Faktor, frischer Zustand,
      Toleranz 1e-9. SCHREIBEN=False, journal gepatcht, wachen unveraendert.

Schreibt nichts in die Spuren. Ablage: bt_opt/verify_equivalence.py.
"""
import importlib.util
import os

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)

def lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

# Helfer aus backtest_prognose.py (kerzen_holen, lade) und der schnelle Treiber.
bt = lade('bt', os.path.join(HANDEL, 'backtest_prognose.py'))
btf = lade('btf', os.path.join(HANDEL, 'bt_varianten_fast.py'))

ANZAHL = 1200

def spur_modul(spur):
    return bt.lade('bt_%s' % spur, os.path.join(HANDEL, spur, 'handeln.py'))

def vergleiche_signal(spur, prep_fn, sig_fn_kwargs):
    """Signalvergleich je Index. Liefert (geprueft, abw_long, abw_gesamt,
    erste_long, erste_gesamt)."""
    h = spur_modul(spur)
    w = h.lade_wachen()
    mindest = w.get('mindest_kerzen', 300)
    kerzen = {}
    for inst in w['instrumente']:
        k = bt.kerzen_holen(inst, w.get('kerzen_takt', '1H'), ANZAHL)
        if len(k) > mindest + 20:
            kerzen[inst] = k
    prep = prep_fn(kerzen)
    fast = btf.macd_signal(prep, **sig_fn_kwargs) if spur == 'macd_mtf' \
        else btf.squeeze_signal(prep)

    geprueft = 0
    abw_long = 0          # Entscheidung long: fast vs. echt
    abw_gesamt = 0        # roher Signalwert: fast vs. echt (echt kann 'short')
    erste_long = None
    erste_gesamt = None
    for inst, alle in kerzen.items():
        for i in range(mindest, len(alle)):
            k = alle[:i + 1]
            fs = fast(inst, k, i)
            rs = h.signal(k, i)
            geprueft += 1
            if (fs == 'long') != (rs == 'long'):
                abw_long += 1
                if erste_long is None:
                    erste_long = (inst, i, fs, rs)
            if fs != rs:
                abw_gesamt += 1
                if erste_gesamt is None:
                    erste_gesamt = (inst, i, fs, rs)
    return geprueft, abw_long, abw_gesamt, erste_long, erste_gesamt, list(kerzen)

def vergleiche_einstieg(spur):
    """Einstiegslogik: pruefe_einstieg() (echt) vs. _einstieg() (Kopie)."""
    h = spur_modul(spur)
    w = h.lade_wachen()
    mindest = w.get('mindest_kerzen', 300)
    h.SCHREIBEN = False
    h.journal = lambda **f: None
    kerzen = {}
    for inst in w['instrumente']:
        k = bt.kerzen_holen(inst, w.get('kerzen_takt', '1H'), ANZAHL)
        if len(k) > mindest + 20:
            kerzen[inst] = k
    prep = btf.macd_prep(kerzen) if spur == 'macd_mtf' else btf.squeeze_prep(kerzen)
    fast = btf.macd_signal(prep) if spur == 'macd_mtf' else btf.squeeze_signal(prep)

    geprueft = 0
    abw = 0
    erste = None
    FELDER = ('inst', 'seite', 'einstieg', 'stop', 'ziel', 'stop_pct', 'nominal')
    for inst, alle in kerzen.items():
        for i in range(mindest, len(alle)):
            k = alle[:i + 1]
            fs = fast(inst, k, i)
            rs = h.signal(k, i)
            if fs != 'long' or rs != 'long':
                continue
            # frischer Zustand je Seite, gleicher Faktor wie der Treiber (1.0)
            z_echt = {'positionen': []}
            z_kopie = {'positionen': []}
            h.pruefe_einstieg(inst, k, z_echt, w, 1.0)
            btf._einstieg(inst, k, z_kopie, w, 1.0, h)
            p_echt = z_echt['positionen'][0] if z_echt['positionen'] else None
            p_kopie = z_kopie['positionen'][0] if z_kopie['positionen'] else None
            geprueft += 1
            if p_echt is None or p_kopie is None:
                abw += 1
                if erste is None:
                    erste = (inst, i, 'eine Seite leer', p_echt, p_kopie)
                continue
            for f in FELDER:
                a, b = p_echt[f], p_kopie[f]
                if isinstance(a, float):
                    ok = abs(a - b) <= 1e-9
                else:
                    ok = a == b
                if not ok:
                    abw += 1
                    if erste is None:
                        erste = (inst, i, f, a, b)
                    break
    return geprueft, abw, erste

def run():
    print('=== Signalvergleich: schnelles vorberechnetes Signal vs. echte signal() ===')
    ergebnis = {}
    for spur in ('macd_mtf', 'squeeze'):
        if spur == 'macd_mtf':
            gep, abw_l, abw_g, er_l, er_g, kerzen = vergleiche_signal(
                spur, btf.macd_prep, dict(faktoren=(1, 4, 16)))
        else:
            gep, abw_l, abw_g, er_l, er_g, kerzen = vergleiche_signal(
                spur, btf.squeeze_prep, dict())
        print('\n--- %s ---' % spur)
        print('  Instrumente: %s' % ', '.join(kerzen))
        print('  verglichene Schritte: %d' % gep)
        print('  Abweichungen (Entscheidung long): %d' % abw_l)
        print('  Abweichungen (roher Signalwert):  %d' % abw_g)
        print('  erste long-Abweichung:  %s' % (er_l,))
        print('  erste Signal-Abweichung: %s' % (er_g,))
        ergebnis[spur] = {'geprueft': gep, 'abw_long': abw_l,
                          'abw_signal': abw_g, 'erste_long': er_l,
                          'erste_signal': er_g}

    print('\n=== Einstiegslogik: pruefe_einstieg() (echt) vs. _einstieg() (Kopie) ===')
    for spur in ('macd_mtf', 'squeeze'):
        gep, abw, erste = vergleiche_einstieg(spur)
        print('\n--- %s ---' % spur)
        print('  verglichene Einstiege: %d' % gep)
        print('  Abweichungen: %d' % abw)
        print('  erste Abweichung: %s' % (erste,))
        ergebnis[spur]['einstieg_geprueft'] = gep
        ergebnis[spur]['einstieg_abw'] = abw
        ergebnis[spur]['einstieg_erste'] = erste

    print('\n=== URTEIL ===')
    for spur in ('macd_mtf', 'squeeze'):
        e = ergebnis[spur]
        gleich = (e['abw_long'] == 0 and e['einstieg_abw'] == 0)
        print('  %-10s %s' % (spur, 'gleichwertig' if gleich else 'NICHT gleichwertig'))
    return ergebnis

if __name__ == '__main__':
    run()