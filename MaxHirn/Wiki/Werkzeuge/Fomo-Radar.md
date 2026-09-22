# FOMO Robinhood Radar (On-Chain-Beobachtung)

`cvxv666/fomo-robinhood-radar` — beobachtet die On-Chain-Aktivitaet von
Tradern auf **Robinhood Chain (Chain-ID 4663)** ueber die Handelsplattform
`fomo.family`, bewertet Wallets mit einem Sprachmodell und baut daraus ein
20-Sekunden-Tape, eine HTML-Seite, einen Telegram-Bot und eine API.

Fork `mfaupel95/fomo-robinhood-radar`, Klon `Werkstatt/Repos/fomo-robinhood-radar`
(`origin`=Fork, `upstream`=Original), eigenes `.venv`, installiert
(`pip install -e ".[dev]"`).

## Was ohne einen einzigen Schluessel laeuft (gemessen 22.09.2026)

| Befehl | Ergebnis |
|---|---|
| `fomo-radar init` | Datenbank angelegt; meldet selbst fehlende Schluessel |
| `fomo-radar discover --trenches` | **147 Wallets** aus der kostenlosen rhtrenches-Liste (`window 7d`) |
| `fomo-radar track --show` | **65 echte Fills** von 25 Wallets, direkt ueber `eth_getLogs` gelesen, **8 freie RPC-Aufrufe**, 0 Fehler (62 Trades, 2 Staub) |
| `fomo-radar report --hours 24` | Roster + Tape als Bericht |

Der Kern (`rpc`, `trenches`, `dexscreener`, `geckoterminal`) ist **kostenlos und
schluessellos**. Alles Optionale schaltet sich bei fehlendem Schluessel
**still ab**, statt zu scheitern.

Tests: **306 gruen, 1 rot** —
`tests/test_wave2.py::test_an_invite_rewards_both_once_and_only_a_new_chat`
erwartet „7 days of PRO" in einer Einladungsnachricht, die der Code so nicht
mehr baut (Text-/Ablauf-Drift im PRO-Werbeweg, kein Absturz). Unangetastet
gelassen: Fremd-Repo, nicht unsere Baustelle.

## Fallen

- **Windows braucht `PYTHONIOENCODING=utf-8`** (sonst cp1251-Mojibake). Das
  Repo dokumentiert das selbst in seiner `CLAUDE.md` — es ist auf Windows
  entwickelt worden.
- **Bewertung nicht ueber die API.** `init` meldete „anthropic key: set" — das
  ist Max' Console-Schluessel, und der hat **kein Guthaben**. Der dafuer
  vorgesehene Weg `--export` / `--import` ist anbieterunabhaengig und passt auf
  das lokale Ollama (Hausregel: Sprachmodell lokal).
- **fomo.family blockt Serveraufrufe** (Cloudflare) — Nutzerlisten kommen nur
  per Browser-Export (`scripts/fomo_export.js` → `fomo-radar fomo-import`).
- Das Repo bringt eine eigene `SKILL.md` mit. **Nicht** in die
  Hermes-Skill-Bibliothek importieren (Hausregel `skill-library-sync`).

## Was daran fuer den Handel interessant ist

Bauartgleich mit der Haus-Spur `kopier`: einer Menge von Tradern nachkaufen.
Der Unterschied ist die **Bewertung** — hier werden Wallets mit einem Score
versehen und nur Kohorten ab 60 Punkten als Signal genommen, statt einer
PnL-Rangliste zu folgen. Ein Anschluss als **papierene** Signalspur ist damit
naheliegend; echtes Geld beruehrt das nicht.

Verwandt: die Skizze `mfaupel95/robinhood-fomo-kronos-arena` nennt einen
`fomo-client` als Dienst — der Ordner dort ist **leer** (nur `.gitkeep`), das
Repo ist ein Bauplan ohne Code. Dieser Radar ist die erste echte Umsetzung
dieses Bausteins.