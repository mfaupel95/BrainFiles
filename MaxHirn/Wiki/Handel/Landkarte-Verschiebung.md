# Landkarte: Wiki-Verschiebung 2026-10-06

31 Dateien aus `Agenten/Handel/` nach `MaxHirn/Wiki/Handel/` verschoben.

## Zielstruktur

```
MaxHirn/Wiki/Handel/
├── plans/           ← 15 Pläne + Designs (aus docs/design/ + docs/plans/)
├── Befunde/         ← 11 Befunde, Notizen, Übergaben
├── Spuren/          ← 3 Spur-Pläne (mosaic, moondev_marktlage, iv_waelle)
├── verbesserer/     ← 7 Verbesserer-Berichte
├── Spuren-Uebersicht.md  ← bestehend, um Verweise erweitert
├── Backtest-Fundament.md
├── Boersen-und-Schluessel.md
├── Dauerlauf-Tode.md
├── Freqtrade-Bots.md
├── Gates-und-Freigabe.md
├── Guthaben-und-Umschichtung.md
├── Kosten-und-Bedingungen.md
├── Leitstand-Einbetten.md
├── Lektionen.md
├── nautilus-rust-Quant-Ebene.md
├── omnitrade-Spur.md
├── Spur-Optimierung-Setzer-Befund.md
└── Strategie-Kennzahlen.md
```

## Verschobene Dateien

### plans/ (15 Dateien)

| Datei | Größe | Herkunft |
|---|---|---|
| 2026-09-18-spiegel-kopier-filter-design.md | 7 KB | docs/design/ |
| 2026-09-19-quant-migration-design.md | 6 KB | docs/design/ |
| 2026-09-24-backtest-fundament-design.md | 13 KB | docs/design/ |
| 2026-09-26-moondev-backtest-design.md | 14 KB | docs/design/ |
| 2026-09-29-leitstand-design.md | 20 KB | docs/design/ |
| 2026-10-01-prognose-merkmale-design.md | 8 KB | docs/design/ |
| 2026-09-18-filter-studie.md | 13 KB | docs/plans/ |
| 2026-09-18-v1-ausstiegsgeometrie.md | 6 KB | docs/plans/ |
| 2026-09-19-daten-auffrischen.md | 17 KB | docs/plans/ |
| 2026-09-19-python-zu-rust-migration.md | 19 KB | docs/plans/ |
| 2026-09-19-quant-migration-plan.md | 22 KB | docs/plans/ |
| 2026-09-24-backtest-fundament.md | 69 KB | docs/plans/ |
| 2026-09-26-moondev-backtest.md | 62 KB | docs/plans/ |
| 2026-09-29-leitstand-plan.md | 282 KB | docs/plans/ |
| 2026-10-01-omniquant-kraken-live-plan.md | 8 KB | docs/plans/ |
| PLAN-auswertung-datengrundlage-2026-09-17.md | 46 KB | Wurzel |
| PLAN-berichtsschicht-2026-09-18.md | 54 KB | Wurzel |

### Befunde/ (11 Dateien)

| Datei | Größe |
|---|---|
| BEFUND-hygiene-2026-09-17.md | 13 KB |
| CODE_REVIEW_AND_FIXES_INDEX.md | 8 KB |
| CODE_REVIEW_FIXES.md | 14 KB |
| CryptoPredictions_Wissen.md | 10 KB |
| DEVELOPER_QUICK_START.md | 8 KB |
| ENTWURF-auswertung-berichte-2026-09-17.md | 13 KB |
| FIXES_APPLIED_SUMMARY.md | 10 KB |
| HANDOFF_FOR_NEXT_DEVELOPER.md | 8 KB |
| QUICK_REFERENCE.md | 8 KB |
| VALIDATION_REPORT.md | 8 KB |

### Spuren/ (3 Dateien)

| Datei | Spur |
|---|---|
| MOSAIC-LIVE-PLAN-OKX.md | mosaic |
| KRAKEN-LIVE-PLAN.md | moondev_marktlage |
| NOTIZ.md | iv_waelle |

### verbesserer/ (7 Dateien)

| Datei | Datum |
|---|---|
| bericht-2026-09-06-spur1.md | 06.09.2026 |
| bericht-2026-09-13-spur1.md | 13.09.2026 |
| bericht-2026-09-16-spur1.md | 16.09.2026 |
| bericht-2026-09-20-spur1.md | 20.09.2026 |
| bericht-2026-09-27-spur1.md | 27.09.2026 |
| bericht-2026-10-01-spur1.md | 01.10.2026 |
| bericht-2026-10-04-spur1.md | 04.10.2026 |

## Bleibt in Agenten/Handel

- Spur-READMEs (30+ Dateien, betrieblich, kurz)
- SPEC.md (orb, orbk)
- AGENTS.md, README.md, QUICK_REFERENCE.md
- Alle .py, .json, .csv, .ps1 (Code + Konfiguration)

## Pfad-Korrektur

- `leitstand_backtests.json`: `docs/plans/2026-09-29-leitstand-plan.md` → `Werkstatt/Projekte/handel/plans/2026-09-29-leitstand-plan.md` (seit 21.10.2026; vorher `MaxHirn/Wiki/Handel/plans/`)

## TASKS

- T-89: Verschiebung
- T-90: TASKS-Einträge
- T-91: Wissen einbauen

## Commit

`04396a0f` — 6 Dateien, 62 Insertions, 584 Deletions