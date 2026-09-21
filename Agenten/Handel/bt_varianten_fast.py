"""Schneller Varianten-Backtest: Indikatoren einmal je Instrument vorrechnen.

Der langsame Pfad (backtest_prognose.lauf) ruft signal() je Schritt neu und
rechnet damit MACD-MTF/Squeeze O(n^2). Die Signale haengen aber nur an Werten
am aktuellen Index (hist[idx], hist[idx-1], ausrichtung = Vorzeichen des
letzten hist-Werts, momentum[idx]/[idx-1], squeeze_an[idx]/[idx-1]). Werden die
Indikator-Arrays einmal auf der VOLLEN Serie gerechnet, sind die Abfragen
identisch zur schrittweisen Rechnung (Fenster und Aggregation starten beide bei
Index 0). Das hier nutzt exakt dieselben ti_indikatoren-Funktionen und dieselbe
Einstiegs-/Ausstiegslogik aus <spur>/handeln.py (ueber den PFAD geladen).

Nur long-Seite, 7000 h, netto 0,10 %/Seite. Schreibt nichts in die Spuren.
"""
import argparse, contextlib, importlib.util, io, json, os, statistics

spec = importlib.util.spec_from_file_location('bt', 'backtest_prognose.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

HIER = os.path.dirname(os.path.abspath(__file__))


def spur_modul(spur):
    return m.lade('bt_%s' % spur, os.path.join(HIER, spur, 'handeln.py'))


def vorwaerts_runden(spur, signal_fn, wachen_patch=None):
    """Fahre long-Seite mit vorgegebenem signal_fn(inst, k, idx), schnell."""
    h = spur_modul(spur)
    w = h.lade_wachen()
    if wachen_patch:
        w = dict(w)
        w.update(wachen_patch)
    kerzen = {}
    for inst in w['instrumente']:
        k = m.kerzen_holen(inst, w.get('kerzen_takt', '1H'), 7000)
        if len(k) > w.get('mindest_kerzen', 300) + 20:
            kerzen[inst] = k
    if not kerzen:
        return None, None

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
                    vz = 1 if e['seite'] == 'long' else -1
                    roh = (kurs - e['einstieg']) / e['einstieg'] * 100.0 * vz
                    runden.append({
                        'inst': inst, 'seite': e['seite'],
                        'einstieg': e['einstieg'], 'ausstieg': kurs,
                        'nominal': e['nominal'], 'stop_pct': e['stop_pct'],
                        'brutto_pct': roh, 'netto_pct': roh - 2 * gebuehr,
                        'gv_netto': e['nominal'] * (roh - 2 * gebuehr) / 100.0,
                        'ein_ts': e['ts'], 'aus_ts': k[-1][0],
                        'stunden': (k[-1][0] - e['ts']) / 3600000.0,
                    })
            vorher_ids = {id(p) for p in z['positionen']}
            if signal_fn(inst, k, len(k) - 1) == 'long':
                _einstieg(inst, k, z, w, 1.0, h)
            for p in z['positionen']:
                if id(p) not in vorher_ids:
                    offen[id(p)] = {'seite': p['seite'], 'einstieg': p['einstieg'],
                                    'nominal': p['nominal'],
                                    'stop_pct': p['stop_pct'], 'ts': k[-1][0]}
    return runden, len(z['positionen'])


def _einstieg(inst, k, z, w, faktor, h):
    """pruefe_einstieg aus <spur>/handeln.py, aber ohne erneuten signal()-Aufruf.

    Kopie der Logik (Position, Stop/Ziel, Groesse), damit das schnelle
    Signal nicht von der langsamen Neuberechnung im Original ueberschrieben
    wird. Identisch zum Original bis auf den fehlenden signal()-Aufruf.
    """
    if not z.get('positionen'):
        z['positionen'] = []
    if len(z['positionen']) >= w.get('max_offene_positionen', 4):
        return
    if not k or len(k) < w.get('mindest_kerzen', 300):
        return
    idx = len(k) - 1
    einstieg = k[idx][4]
    atr = h.atr_abs(k, idx, 14)
    if not atr or atr <= 0:
        return
    stop_pct = atr / einstieg * 100.0
    stop_pct = max(stop_pct, w.get('pflicht_stop_prozent_min', 5.0))
    stop_pct_eff = min(stop_pct, w.get('pflicht_stop_prozent_max', 12.0))
    vz = 1  # nur long
    abstand = einstieg * stop_pct_eff / 100.0
    r = w.get('ziel_r_vielfaches', 2.0)
    stop = einstieg - vz * abstand
    ziel = einstieg + vz * r * abstand
    nominel = w['risiko_je_position_usd'] / (stop_pct_eff / 100.0)
    nominel = min(nominel, w['max_pro_trade_usd'])
    nominel *= faktor
    if nominel <= 0:
        return
    z['positionen'].append({
        'inst': inst, 'seite': 'long', 'einstieg': einstieg,
        'stop': stop, 'ziel': ziel, 'stop_pct': stop_pct_eff,
        'nominal': nominel, 'eroeffnet_zeit': h._jetzt(),
    })


def kennzahlen(runden, offen=0):
    if not runden:
        return {'n': 0, 'offen': offen}
    netto = [r['netto_pct'] for r in runden]
    gv = [r['gv_netto'] for r in runden]
    treffer = sum(1 for x in netto if x > 0)
    kum, hoch, dd = 0.0, 0.0, 0.0
    for x in gv:
        kum += x
        hoch = max(hoch, kum)
        dd = min(dd, kum - hoch)
    return {
        'n': len(runden), 'offen': offen,
        'quote': round(100.0 * treffer / len(runden), 1),
        'netto_pct_mittel': round(statistics.fmean(netto), 3),
        'netto_pct_summe': round(sum(netto), 2),
        'gv_netto_usd': round(sum(gv), 2),
        'max_ruecklauf_usd': round(dd, 2),
        'stunden_median': round(statistics.median(r['stunden'] for r in runden), 1),
    }


# --- MACD-MTF Varianten ------------------------------------------------------

def macd_prep(kerzen, faktoren=(1, 4, 16), schnell=12, langsam=26, signal=9):
    import ti_indikatoren as ti
    prep = {}
    for inst, k in kerzen.items():
        N = len(k)
        e = ti.macd_mtf(k, faktoren=faktoren, schnell=schnell,
                        langsam=langsam, signal=signal)
        # Fuer jeden Faktor: hist auf der aggregierten Serie. Die Aggregation
        # startet bei Index 0; fuer einen Ausschnitt k[:i+1] sind die ersten
        # floor((i+1)/f) TF-Balken identisch mit denen der vollen Serie.
        # val_by_base[i] = hist-Wert des aktuellen TF-Balkens bei i+1 Kerzen,
        # aus_by_base[i] = Vorzeichen des letzten nicht-None hist bis dahin.
        fdata = {}
        for f in faktoren:
            hist = e[f]['hist']
            L = len(hist)
            run = [None] * L
            last = None
            for j, x in enumerate(hist):
                if x is not None:
                    last = 1 if x > 0 else (-1 if x < 0 else 0)
                run[j] = last
            val_by_base = [None] * N
            aus_by_base = [None] * N
            for i in range(N):
                j = (i + 1) // f - 1  # aktueller TF-Balken bei i+1 Kerzen
                if 0 <= j < L:
                    val_by_base[i] = hist[j]
                    aus_by_base[i] = run[j]
            fdata[f] = {'val': val_by_base, 'aus': aus_by_base}
        prep[inst] = {'fdata': fdata, 'faktoren': faktoren}
    return prep


def macd_signal(prep, faktoren=(1, 4, 16), hist_mehrere=False):
    def fn(inst, k, idx):
        d = prep[inst]
        fdata = d['fdata']
        vals = [fdata[f]['aus'][idx] for f in faktoren]
        if any(v is None for v in vals) or len(set(vals)) != 1:
            return None
        if vals[0] != 1:
            return None
        v1 = fdata[1]['val']
        if (v1[idx] is not None and v1[idx - 1] is not None
                and v1[idx] > v1[idx - 1]):
            if not hist_mehrere:
                return 'long'
            v4 = fdata[4]['val']
            if (v4[idx] is not None and v4[idx - 1] is not None
                    and v4[idx] > v4[idx - 1]):
                return 'long'
        return None
    return fn


# --- Squeeze Varianten -------------------------------------------------------

def squeeze_prep(kerzen, laenge=20, bb_mult=2.0, kc_mult=1.5):
    import ti_indikatoren as ti
    prep = {}
    for inst, k in kerzen.items():
        mom, sq, _r = ti.squeeze_momentum(k, laenge=laenge, bb_mult=bb_mult,
                                          kc_mult=kc_mult)
        prep[inst] = {'mom': mom, 'sq': sq}
    return prep


def squeeze_signal(prep, schwelle=0.0):
    def fn(inst, k, idx):
        d = prep[inst]
        mom, sq = d['mom'], d['sq']
        if (sq[idx - 1] is True and sq[idx] is False
                and mom[idx] is not None and mom[idx - 1] is not None):
            if mom[idx] > mom[idx - 1] > schwelle:
                return 'long'
        return None
    return fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', help='Ergebnis als JSON schreiben')
    a = ap.parse_args()

    ergebnis = {}

    # --- macd_mtf ---
    print('=== macd_mtf (long, 7000h, 0.10%%/Seite) ===')
    h = spur_modul('macd_mtf')
    w = h.lade_wachen()
    kerzen = {}
    for inst in w['instrumente']:
        k = m.kerzen_holen(inst, w.get('kerzen_takt', '1H'), 7000)
        if len(k) > w.get('mindest_kerzen', 300) + 20:
            kerzen[inst] = k

    varianten = [
        ('BASE', macd_prep(kerzen), dict(faktoren=(1, 4, 16))),
        ('fakt(1,4,8)', macd_prep(kerzen, faktoren=(1, 4, 8)), dict(faktoren=(1, 4, 8))),
        ('fakt(1,2,4)', macd_prep(kerzen, faktoren=(1, 2, 4)), dict(faktoren=(1, 2, 4))),
        ('macd(5,35,5)', macd_prep(kerzen, schnell=5, langsam=35, signal=5), dict(faktoren=(1, 4, 16))),
        ('macd(8,21,5)', macd_prep(kerzen, schnell=8, langsam=21, signal=5), dict(faktoren=(1, 4, 16))),
        ('hist1+4', macd_prep(kerzen), dict(faktoren=(1, 4, 16), hist_mehrere=True)),
    ]
    for name, prep, kw in varianten:
        fn = macd_signal(prep, **kw)
        r, offen = vorwaerts_runden('macd_mtf', fn)
        k = kennzahlen(r, offen)
        ergebnis['macd_mtf/' + name] = k
        print('  %-12s n=%-4d quote %5.1f%% netto %+7.3f%%/R summe %+8.2f%% dd %8.2f med %5.0fh' % (
            name, k['n'], k['quote'], k['netto_pct_mittel'],
            k['netto_pct_summe'], k['max_ruecklauf_usd'], k['stunden_median']))

    # Parameter-Varianten auf BASE-Signal
    base_prep = macd_prep(kerzen)
    base_fn = macd_signal(base_prep)
    print('  --- Parameter (Stop/Ziel) auf BASE ---')
    for pname, patch in [
        ('ziel R=3', {'ziel_r_vielfaches': 3.0}),
        ('ziel R=1.5', {'ziel_r_vielfaches': 1.5}),
        ('stop min4', {'pflicht_stop_prozent_min': 4.0}),
        ('stop max15', {'pflicht_stop_prozent_max': 15.0}),
        ('stop 3-15', {'pflicht_stop_prozent_min': 3.0, 'pflicht_stop_prozent_max': 15.0}),
    ]:
        r, offen = vorwaerts_runden('macd_mtf', base_fn, wachen_patch=patch)
        k = kennzahlen(r, offen)
        ergebnis['macd_mtf/' + pname] = k
        print('  %-12s n=%-4d quote %5.1f%% netto %+7.3f%%/R summe %+8.2f%% dd %8.2f' % (
            pname, k['n'], k['quote'], k['netto_pct_mittel'],
            k['netto_pct_summe'], k['max_ruecklauf_usd']))

    # --- squeeze ---
    print('\n=== squeeze (long, 7000h, 0.10%%/Seite) ===')
    h = spur_modul('squeeze')
    w = h.lade_wachen()
    kerzen = {}
    for inst in w['instrumente']:
        k = m.kerzen_holen(inst, w.get('kerzen_takt', '1H'), 7000)
        if len(k) > w.get('mindest_kerzen', 300) + 20:
            kerzen[inst] = k

    sv = [
        ('BASE', squeeze_prep(kerzen), dict()),
        ('laenge30', squeeze_prep(kerzen, laenge=30), dict()),
        ('laenge15', squeeze_prep(kerzen, laenge=15), dict()),
        ('kc1.8', squeeze_prep(kerzen, kc_mult=1.8), dict()),
        ('kc1.2', squeeze_prep(kerzen, kc_mult=1.2), dict()),
        ('mom>0.05', squeeze_prep(kerzen), dict(schwelle=0.05)),
    ]
    for name, prep, kw in sv:
        fn = squeeze_signal(prep, **kw)
        r, offen = vorwaerts_runden('squeeze', fn)
        k = kennzahlen(r, offen)
        ergebnis['squeeze/' + name] = k
        print('  %-12s n=%-4d quote %5.1f%% netto %+7.3f%%/R summe %+8.2f%% dd %8.2f med %5.0fh' % (
            name, k['n'], k['quote'], k['netto_pct_mittel'],
            k['netto_pct_summe'], k['max_ruecklauf_usd'], k['stunden_median']))

    base_prep = squeeze_prep(kerzen)
    base_fn = squeeze_signal(base_prep)
    print('  --- Parameter (Stop/Ziel) auf BASE ---')
    for pname, patch in [
        ('ziel R=3', {'ziel_r_vielfaches': 3.0}),
        ('ziel R=1.5', {'ziel_r_vielfaches': 1.5}),
        ('stop min4', {'pflicht_stop_prozent_min': 4.0}),
        ('stop max15', {'pflicht_stop_prozent_max': 15.0}),
        ('stop 3-15', {'pflicht_stop_prozent_min': 3.0, 'pflicht_stop_prozent_max': 15.0}),
    ]:
        r, offen = vorwaerts_runden('squeeze', base_fn, wachen_patch=patch)
        k = kennzahlen(r, offen)
        ergebnis['squeeze/' + pname] = k
        print('  %-12s n=%-4d quote %5.1f%% netto %+7.3f%%/R summe %+8.2f%% dd %8.2f' % (
            pname, k['n'], k['quote'], k['netto_pct_mittel'],
            k['netto_pct_summe'], k['max_ruecklauf_usd']))

    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(ergebnis, f, indent=1)
        print('\ngeschrieben:', a.json)


if __name__ == '__main__':
    main()