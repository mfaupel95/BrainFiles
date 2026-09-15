#!/usr/bin/env python3
"""OmniRoute-Diagnose (read-only): Fehlerquellen, Nutzung, Verbindungen, Budgets.

Aufruf: python3 router-diagnose.py [pfad/zu/storage.sqlite]
Standard: ~/.omniroute/storage.sqlite
Schreibt nichts, fasst key_value (Secrets!) nicht an.
"""
import sqlite3, sys, os

db = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/.omniroute/storage.sqlite')
c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
c.row_factory = sqlite3.Row

def show(title, sql):
    print(f'\n=== {title} ===')
    try:
        rows = list(c.execute(sql))
        if not rows:
            print('(leer)')
        for r in rows:
            print(dict(r))
    except Exception as e:
        print('ERR', e)

show('7 Tage: Erfolg/Fehler je Provider (chat)', """
 SELECT provider, count(*) n,
        sum(CASE WHEN status BETWEEN 200 AND 299 THEN 1 ELSE 0 END) ok,
        sum(CASE WHEN status NOT BETWEEN 200 AND 299 THEN 1 ELSE 0 END) fail,
        substr(group_concat(DISTINCT substr(error_summary,1,45)),1,400) fehler
 FROM call_logs WHERE timestamp > datetime('now','-7 days') AND method='POST' AND path='/v1/chat/completions'
 GROUP BY provider ORDER BY n DESC""")

show('7 Tage: je Combo+Model (Top 15)', """
 SELECT combo_name, model, count(*) n,
        sum(CASE WHEN status BETWEEN 200 AND 299 THEN 1 ELSE 0 END) ok,
        sum(tokens_in) ti, sum(tokens_out) to_, sum(tokens_cache_read) tcr
 FROM call_logs WHERE timestamp > datetime('now','-7 days') AND method='POST' AND path='/v1/chat/completions'
 GROUP BY combo_name, model ORDER BY n DESC LIMIT 15""")

show('provider_connections', """
 SELECT provider, name, is_active, test_status, default_model, error_code,
        substr(last_error,1,60) last_error
 FROM provider_connections ORDER BY is_active DESC, provider""")

show('domain_budgets (Monatsdeckel je Key)', """
 SELECT api_key_id, monthly_limit_usd, warning_threshold, reset_interval
 FROM domain_budgets ORDER BY monthly_limit_usd DESC""")

c.close()
