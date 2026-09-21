"""OOS-Stabilitaetscheck der Gewinner-Varianten: erste vs. zweite Haelfte.

Faehrt die 7000 h in zwei Haelften (0-3500, 3500-7000) und vergleicht BASE
gegen die Gewinner-Variante je Spur auf beiden Haelften. Nur long, netto
0,10 %/Seite. Schreibt nichts in die Spuren.
"""
import importlib.util, io, contextlib, statistics, json

spec = importlib.util.spec_from_file_location('bt', 'backtest_prognose.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

import bt_varianten_fast as F

HIER = F.HIER


def rune_half(spur, signal_fn, wachen_patch=None, start=0, ende=7000):
    h = F.spur_modul(spur)
    w = h.lade_wachen()
    if wachen_patch:
        w = dict(w)
        w.update(wachen_patch)
    kerzen = {}
    for inst in w['instrumente']:
        k = m.kerzen_holen(inst, w.get('kerzen_takt', '1H'), 7000)
        if len(k) > w.get('mindest_kerzen', 300) + 20:
            kerzen[inst] = k[start:ende]
    if not kerzen:
        return None
    h.SCHREIBEN = False
    h.journal = lambda **f: None
    z = {'positionen': [], 'modus': 'papier', 'letzter_lauf': None,
         'verluste_usd': 0.0}
    offen = {}
    runden = []
    gebuehr = 0.1
    mindest = w.get('mindest_kerzen', 300)
    laenge = min(len(k) for k in kerzen.values())
    for i in range(mindest, laenge):
        for inst, alle in kerzen.items():
            k = alle[:i + 1]
            vorher = {id(p): p for p in z['positionen']}
            h.pruefe_ausstiege(z, k, w, nur=inst)
            nachher = {id(p) for p in z['positionen']}
            for pid, p in vorher.items():
                if pid not in nachher and pid in offen:
                    e = offen.pop(pid)
                    kurs = k[-1][4]
                    roh = (kurs - e['einstieg']) / e['einstieg'] * 100.0
                    runden.append({'netto_pct': roh - 2 * gebuehr,
                                   'gv_netto': e['nominal'] * (roh - 2 * gebuehr) / 100.0,
                                   'stunden': (k[-1][0] - e['ts']) / 3600000.0})
            vorher_ids = {id(p) for p in z['positionen']}
            if signal_fn(inst, k, len(k) - 1) == 'long':
                F._einstieg(inst, k, z, w, 1.0, h)
            for p in z['positionen']:
                if id(p) not in vorher_ids:
                    offen[id(p)] = {'seite': p['seite'], 'einstieg': p['einstieg'],
                                    'nominal': p['nominal'],
                                    'stop_pct': p['stop_pct'], 'ts': k[-1][0]}
    return F.kennzahlen(runden, len(z['positionen']))


def zeile(name, k):
    if k is None:
        return '  %-14s keine Kerzen' % name
    return '  %-14s n=%-4d quote %5.1f%% netto %+7.3f%%/R summe %+8.2f%% dd %8.2f' % (
        name, k['n'], k['quote'], k['netto_pct_mittel'],
        k['netto_pct_summe'], k['max_ruecklauf_usd'])


# macd_mtf: BASE vs hist1+4
print('=== macd_mtf long OOS (Haelfte 1 = 0-3500, Haelfte 2 = 3500-7000) ===')
h = F.spur_modul('macd_mtf')
w = h.lade_wachen()
kerzen = {}
for inst in w['instrumente']:
    k = m.kerzen_holen(inst, w.get('kerzen_takt', '1H'), 7000)
    if len(k) > w.get('mindest_kerzen', 300) + 20:
        kerzen[inst] = k
base_prep = F.macd_prep(kerzen)
hist_prep = F.macd_prep(kerzen)
base_fn = F.macd_signal(base_prep)
hist_fn = F.macd_signal(hist_prep, hist_mehrere=True)
for haelfte, s, e in (('H1', 0, 3500), ('H2', 3500, 7000)):
    print('  -- %s --' % haelfte)
    print(zeile('BASE', rune_half('macd_mtf', base_fn, start=s, ende=e)))
    print(zeile('hist1+4', rune_half('macd_mtf', hist_fn, start=s, ende=e)))

# squeeze: BASE vs laenge30
print('\n=== squeeze long OOS ===')
h = F.spur_modul('squeeze')
w = h.lade_wachen()
kerzen = {}
for inst in w['instrumente']:
    k = m.kerzen_holen(inst, w.get('kerzen_takt', '1H'), 7000)
    if len(k) > w.get('mindest_kerzen', 300) + 20:
        kerzen[inst] = k
base_prep = F.squeeze_prep(kerzen)
l30_prep = F.squeeze_prep(kerzen, laenge=30)
base_fn = F.squeeze_signal(base_prep)
l30_fn = F.squeeze_signal(l30_prep)
for haelfte, s, e in (('H1', 0, 3500), ('H2', 3500, 7000)):
    print('  -- %s --' % haelfte)
    print(zeile('BASE', rune_half('squeeze', base_fn, start=s, ende=e)))
    print(zeile('laenge30', rune_half('squeeze', l30_fn, start=s, ende=e)))