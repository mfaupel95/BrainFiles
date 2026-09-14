# Kopier1zu1 — echte 1:1-Copy-Trade-Spur (Papierbuch)

Zweite Kopier-Spur, angelegt 15.09.2026. Anders als `kopier/` arbeitet
diese hier auf **Trade-Ereignissen** statt auf Portfolio-Diff:

- Jeder **Kauf** des Vorbilds (`typ=buy` aus `trades/batch`, frisch)
  öffnet eine Papier-Position zum Vorbild-Kurs.
- Jeder **Verkauf** derselben (Wallet, Token), der nach dem Einstieg
  liegt, schließt die Kopie sofort zum letzten beobachteten Kurs.

Damit trifft der Ausstieg die Entscheidung des Modells auf die Sekunde,
nicht erst beim nächsten Portfolio-Snapshot.

## Was geteilt wird

- **`lesen.py`**: dieselbe Datei wie in `kopier/` (Import-Verweis auf
  `Handel/kopier/lesen.py`). Nur Lese-Pfade, Waechter aktiv.
- **`verfolgte.json`**: kein zweiter Rangliste-Abruf; die Wallets kommen
  aus `Handel/kopier/verfolgte.json` (pflegt kopier alle 4 h).

## Was eigen ist

- **Signal-Ebene**: Trade-Events statt Portfolio-Diff.
- **Ausstieg**: `verkauft` (Vorbild verkauft) hat Vorrang vor Stop/Trail.
- **Kosten je Kauf** kleiner (30 USD statt 50), Buch tiefer (100 statt 60
  Papier-Plätze), weil ein aktiver Trader viele Käufe pro Tag hat.
- **Stop in USD** (10 USD, kein Prozent).
- **Frist** 168 h nur als Sicherheitsnetz.

## Aufruf

    python handeln.py --wachen      # Grenzen als Momentaufnahme
    python handeln.py --vorschau    # ohne zu schreiben
    python handeln.py --papier      # Papierzyklus mit Journal
    python handeln.py --bilanz      # was hat getragen
    python handeln.py --live        # verweigert (Papier)

Verdrahtung: `dauerlauf.SPUREN['kopier1zu1']` → `handeln.py`. Journal +
Zustand + Ablehnungen werden nach jedem Zyklus nach
`Q:\Handel_Journal\kopier1zu1` gespiegelt (Bedingung 4).
