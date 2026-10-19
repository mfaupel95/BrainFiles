# Moon-Dev-Funding-Spur (Papier)

Ein Haus-Buch auf den Funding-Extremen von Hyperliquid. Die **Zahlen liefert
der geklonte Bot**, nicht ein Nachbau: `Werkstatt/moon-dev-ai-agents`,
`src/nice_funcs_hl.get_funding_rates()`. Die Regel kommt aus
`src/agents/fundingarb_agent.py` (dort `YEARLY_FUNDING_THRESHOLD = 100`).

## Warum es diese Spur gibt

Max hat die Moon-Dev-Repos installiert und wollte die Bots in den Handelsspuren
sehen. Die Fremd-Agenten sind aber Sprachmodell-Agenten mit echtem
Order-Pfad (Hyperliquid/Solana, echte Schlüssel). Beides wäre im Hausbetrieb
falsch:

- **Kein Sprachmodell.** Urteile eines LLM sind nicht nachrechenbar; ein Buch,
  das man nicht nachrechnen kann, taugt nicht als Messreihe. Die Regel des Bots
  ist hier deterministisch: ab ±100 % Funding im Jahr wird gehandelt.
- **Kein Orderpfad.** Ein `--live` verweigert mit Begründung. Wer die
  Fremd-Agenten scharf schalten will, trifft eine andere Entscheidung als diese
  Spur - sie ist Papier, und zwar ausschließlich.

## Wie die Anbindung läuft

```
moondev_funding/handeln.py                      (Haus-Spur, scanner-venv)
        │  subprocess
        ▼
Werkstatt/moon-dev-ai-agents/.venv/Scripts/python.exe
        │  import nice_funcs_hl; get_funding_rates("BTC")
        ▼
https://api.hyperliquid.xyz/info  (öffentlich, kein Schlüssel)
```

Der Bot läuft in **seinem** venv (pandas, requests), die Haus-Spur bleibt im
gemeinsamen venv - dieselbe Bauform wie bei der nautilus-Spur im Dauerlauf
(`SPUREN[...]["python"]`). Fehlt das Repo oder sein venv, sagt die Spur das im
Zyklus und bucht nichts; sie erfindet keine Zahlen.

Warum `get_funding_rates` auf ein Symbol je Aufruf statt eines Sammelabrufs:
das ist die Funktion, die der Bot anbietet. Ein Sammelabruf wäre ein zweiter
Codeweg neben dem Bot - und würde bei jeder Änderung dort auseinanderlaufen.

## Regel

1. Jahres-Rate = `funding_rate * 24 * 365 * 100` (Hyperliquid rechnet
   stündlich).
2. ≥ +100 %/Jahr → **short** (Longs zahlen, wer short steht kassiert).
   ≤ −100 %/Jahr → **long**. Dazwischen: kein Geschäft.
3. Stop fest in Prozent (`stop_prozent`, im Pflichtrahmen 5–12 %), Ziel =
   `ziel_r_vielfaches` × Stop-Abstand. Kein ATR: das Bot-Repo hätte für Kerzen
   einen zweiten Abruf je Symbol und Zyklus.
4. Größe risiko-normiert (`risiko_je_position_usd / stop_pct`), gedeckelt,
   halbiert bei erreichtem Buchrücklauf (Ratsche aus `Handel/ratschen.py`).

## Aufruf

```powershell
cd Agenten/Handel/moondev_funding
..\scanner\.venv\Scripts\python.exe handeln.py --vorschau   # was wäre dran
..\scanner\.venv\Scripts\python.exe handeln.py --papier     # Papierlauf
..\scanner\.venv\Scripts\python.exe handeln.py --wachen     # Grenzen
```

Im Dauerlauf steht sie als `moondev_funding` in `dauerlauf.SPUREN` und läuft
alle 15 Minuten mit; ihr Journal spiegelt nach
`Q:\Handel_Journal\moondev_funding` (Bedingung 4). Tests ohne Netz:
`python -m unittest test_moondev_funding` **aus dem Ordner `tests/`**.

## Was sie NICHT ist

- keine Anbindung der anderen 45 Moon-Dev-Agenten. Die meisten brauchen
  `MOONDEV_API_KEY` (Daten) oder einen LLM-Schlüssel (Urteil). Diese Spur ist
  die Vorlage: **Bot-Funktion rufen, Regel im Haus, Papierbuch im Hausformat.**
- kein Ersatz für `swap`: dort rechnet eine Haus-Strategie mit
  Funding-Pflichtprüfung je Einstieg, hier kommt das Signal selbst aus dem
  Funding.
