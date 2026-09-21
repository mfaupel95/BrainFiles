import importlib.util, json, sys, os

# Load backtest_prognose as module
spec = importlib.util.spec_from_file_location('bt', 'backtest_prognose.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

out = {}
for spur in ('macd_mtf', 'squeeze'):
    for seite in (None, 'long', 'short'):
        r, k = m.fahre(spur, 7000, 0.1, nur_seite=seite)
        nm = seite or 'beide'
        out['%s/%s' % (spur, nm)] = {'k': k, 'r': r}
        print('%-11s %-6s n=%-4d quote %5.1f netto %+7.3f summe %+8.2f dd %8.2f med %5.0fh' % (
            spur, nm, k['n'], k.get('quote', 0), k.get('netto_pct_mittel', 0),
            k.get('netto_pct_summe', 0), k.get('max_ruecklauf_usd', 0),
            k.get('stunden_median', 0)), flush=True)
json.dump(out, open('bt_lang_verif.json', 'w'), indent=1)