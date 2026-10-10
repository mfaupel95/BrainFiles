# PR: Fremd-Signale - Schema, Bus-Typ, Tor (Entwurf, nicht gepusht)

Zweig `claude/fremd-signal` -> `master`, Arbeitsbaum `.worktrees/fremd-signal`. Nach dem Merge Zweig und Arbeitsbaum loeschen (`git worktree remove`, `git branch -d claude/fremd-signal`). Merge macht Max.

## Was
Phase 2 aus `Werkstatt/plan-fremdrepos-ausbau-2026-10-09.md`: Signale aus kraken-cli und OKX Agent Trade Kit laufen durch einen geprueften Weg, der nichts ausfuehrt.
- `Agenten/Handel/signal_schema.py` - Validator: Pflichtfelder, `mode` nur paper|demo (live nie), Stale-Verwurf ohne Retry, Zeit aus der Zukunft, `size_pct` in (0,1].
- `Agenten/Bus/fremd_signal.py` - Nachrichtentyp `signal` / `signal_verworfen` im Journal; wirft nie; fuer das Handy still.
- `Agenten/Handel/fremd_tor.py` + `fremd_signale/wachen.json` - wachen.json-Tor mit Zulassungslisten (Modus, Quelle, Instrument, Deckel). **Tor ist im Auslieferungszustand ZU.**
- `.gitignore`: Whitelist fuer die neue Wache.

## Warum
Vertrag steht im Hermes-Skill `fremdrepos-signal`; Code dazu fehlte (dessen "Naechste Schritte"). Ohne Pruefung und Tor haette ein Bot-Profil Rohmaterial direkt in `Handel/` schieben koennen.

## Was NICHT drin ist
- Keine bestehende Spur und keine bestehende `wachen.json` geaendert; keine Ausfuehrung, kein Orderweg.
- Das Tor ist mit dem Bus verbunden: `melden_signal` schickt jedes Signal durchs Tor; ohne Wache oder bei zu = verworfen und so journalisiert. Es wird weiterhin nichts ausgefuehrt.
- Kein Stop im Signal: die Stop-Pflicht greift in der Ausfuehrungsspur, die es fuer Fremd-Signale noch nicht gibt.

## Tests (alle gruen)
```
python Agenten/Handel/tests/test_signal_schema.py   # 12
python Agenten/Handel/tests/test_fremd_tor.py       # 12
python Agenten/Bus/tests/test_fremd_signal.py       # 5
python Agenten/Bus/tests/test_ereignis.py           # bestehend
```
Mergebar ohne Konflikt gegen `master` (merge-tree). Ende-zu-Ende-Bus-Test nicht gelaufen (keine bestehende Bus-Datei geaendert ausser README).

## Fuer Reviewer
- Bereich `handel` (Handel/) und `bot` (Bus/): Befund laut `bereiche.py` - Besitzer von `handel` bitte gegenlesen.
- Tor oeffnen = `fremd_signale_erlaubt: true` von Hand, erst nach Papier-/Demo-Nachweis.
- Offen: Demo-Key fuer `okx-agentkit`, Ausfuehrungsspur, Anbindung Tor <-> Bus.
