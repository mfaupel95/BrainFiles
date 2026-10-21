"""Nachrechnung der Pruefpflicht mit Max' Anweisungsparametern."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bot, okxf, indikatoren, json

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "wachen.json"), "r", encoding="utf-8") as _f:
    w = json.load(_f)

# Max' Anweisung
einstieg = 0.570   # Mitte von 0.568-0.572
stop = 0.545
ziel = 0.61        # Mitte von 0.60-0.62
hebel = 5
seite = "long"
stunden = 48       # 1-3 Tage

instr = okxf.instrument("TIA-USD_UM_XPERP-310905")
print(f"instId: {instr['instId']}")

# 1. Liquidationspreis und Hebel-Deckel
liq = bot.liquidationspreis(einstieg, hebel, w["wartungsmarge"], seite)
liq_abstand = abs(einstieg - liq) / einstieg
print(f"\n1. Liquidationspreis: {liq:.6f}")
print(f"   Abstand: {liq_abstand*100:.2f}%")

dl, ds = bot.hebel_deckel(instr["instId"], wartung=w["wartungsmarge"])
deckel = dl if seite == "long" else ds
print(f"   Hebel-Deckel: {deckel:.1f}x (long)")
print(f"   Gewaehlt: {hebel}x")
if hebel > deckel:
    print(f"   *** ZU HOCH - der groesste Ruecklauf haette liquidiert ***")

# 2. Funding
f = okxf.funding(instr["instId"])
perioden = stunden / 8.0
funding_pct = (f * perioden * (1 if seite == "long" else -1)) if f is not None else None
print(f"\n2. Funding: {f*100:.4f}% je 8h")
print(f"   Haltedauer: {stunden}h = {perioden:.1f} Perioden")
print(f"   Funding auf Nominal: {funding_pct*100:.3f}%")
print(f"   Funding auf Margin bei {hebel}x: {funding_pct*hebel*100:.3f}%")
if seite == "long":
    print(f"   Vorzeichen: Long zahlt (Kosten)")

# 3. Gebuehren
gewinn = abs(ziel - einstieg) / einstieg
verlust = abs(einstieg - stop) / einstieg
gebuehren = 2 * w["gebuehr_taker"]
kosten = gebuehren + (funding_pct or 0.0)
print(f"\n3. Gebuehren je Runde: {gebuehren*100:.3f}% (2 x Taker)")
print(f"   Ziel-Abstand: {gewinn*100:.2f}%")
print(f"   Stop-Abstand: {verlust*100:.2f}%")
print(f"   Kosten (Gebuehr + Funding): {kosten*100:.3f}%")
print(f"   Gebuehr als Teil des Gewinns: {gebuehren/gewinn*100:.2f}%")

# 4. Noetige vs. beobachtete Trefferquote
noetig = bot.noetige_quote(gewinn, verlust, kosten)
print(f"\n4. Noetige Trefferquote: {noetig*100:.1f}%")

# Beobachtete Trefferquote mit den neuen Parametern
k = okxf.kerzen(instr["instId"], "4H", 300)
atr14 = indikatoren.atr(k, 14)
atr_now = atr14[-1] if atr14[-1] else 0.028
stop_atr = verlust / atr_now
ziel_atr = gewinn / atr_now
tq = bot.trefferquote(k, stop_atr, ziel_atr, seite, max_kerzen=int(stunden/4))
print(f"   Beobachtete Trefferquote: {tq['quote']*100:.1f}% ({tq['ziel']} Ziel / {tq['stop']} Stop, {tq['offen']} offen, {len(k)} Kerzen)")
print(f"   Abstand: {(tq['quote']-noetig)*100:+.1f} Prozentpunkte")

print(f"\n{'='*60}")
print(f"ZUSAMMENFASSUNG")
print(f"{'='*60}")
print(f"  Hebel: {hebel}x (Deckel {deckel:.1f}x) -> {'ZU HOCH' if hebel > deckel else 'OK'}")
print(f"  Liquidationsabstand: {liq_abstand*100:.1f}%")
print(f"  Funding: {funding_pct*hebel*100:+.3f}% auf Margin")
print(f"  Gebuehren: {gebuehren*100:.3f}% je Runde")
print(f"  Noetige Quote: {noetig*100:.1f}% vs. beobachtet {tq['quote']*100:.1f}% -> {'KNAPP' if abs(tq['quote']-noetig) < 2 else 'OK'}")
