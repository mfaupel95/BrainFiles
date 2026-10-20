# omnitrade2-Demo-Befund (Stand 20.10.2026)

Hierarchie + Reparatur-Status des OKX-SWAP-Klons in EINER Datei, damit die
nächste Sitzung nicht wieder die ganze Landschaft nachmessen muss.

## Repos

| Repo | Rolle | fetch |
|---|---|---|
| `mfaupel95/omnitrade2` | **origin** (Basis cc946be, Demo-Kette, Stand 20.10.) | oeffentlich |
| `jackby03/omnitrade` | **upstream** (Rust-Stand cc946be) | oeffentlich |
| `LLMQuant/awesome-trading-agents` | Sammel-Repo der parallelen Sitzung (fremd) | nur lesen |
| `mfaupel95/omnitrade` | wurde von paralleler Sitzung ueberschrieben | NICHT mehr Rust-Stand |

## Reparatur (erledigt 20.10.2026)

- `Werkstatt/omnitrade2` → Arbeitsbaum auf `origin/main` (cc946be) gesetzt,
  Junction neu, HEAD==origin/main verifiziert. Kein lokal verlorener Stand:
  Datensaetze liegen in `Werkstatt/daten/` (+ Bundle-Sicherung 12.10.2026).

## Demo-Kette (T-419)

1. Draft-PR #1 auf `omnitrade2` (branch `claude/nice-pasteur-940iq0`),
   Stand 20.10. Demo-Verifikation AUSSTEHT (Demo-Keys fehlen im Container).
2. Cron-Wachen existieren bereits: omnitrade-lauf-wache, -order-wache,
   omnitrade-demo-wache (alle 15 min, no_agent, Telegram).
3. Nächste Aktion: Demo-Keys im Container setzen
   (OKX_REGION=eea, OKX_LEVERAGE=1, OKX_API_KEY/-SECRET/-PASSPHRASE fuer Demo),
   PR #1 von Draft auf ready setzen, Positions-/Stop-Verifikation gegen echte
   Demo, danach Entscheidung C.1-C.5 (im Memory: omnitrade2-Eintrag).

## Falle

- `Vorschau`-Laeufe mit Junction: `git status` im Ordner meldet ggf. die
  Junction als geaendert, wenn die Junction auf ein anderes Ziel zeigt
  (Memory: Werkstatt-Junction-Verlust 13.10.). Erst `(Get-Item
  'Werkstatt').LinkType` pruefen, dann git.
- Ein Klon OHNE origin (nur upstream) ist kein Repo, das man reparieren kann:
  erst `git remote add origin ...` + fetch, dann vergleichen.
