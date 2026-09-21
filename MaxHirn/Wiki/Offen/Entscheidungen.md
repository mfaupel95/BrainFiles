---
id: 20260921-offene-entscheidungen
title: 'Offen — was auf eine Entscheidung wartet'
tags: [offen]
created: 2026-09-21
updated: 2026-09-22
related: ['[[INDEX]]', '[[Betrieb/Sicherung-und-Laufwerke]]', '[[Handel/Spuren-Uebersicht]]']
summary: 'Die offenen Punkte mit dem Stand vom 21.09.2026 — je Punkt: was gemessen ist, was fehlt, was der naechste Schritt ist.'
---

# Offen — was auf eine Entscheidung wartet

**Diese Seite ist eine Wiedervorlage, kein Auftrag.** Jeder Punkt nennt nur Messung und
naechsten Schritt. Erledigtes wird geloescht, nicht durchgestrichen (Historie liegt in Git).

## 1. xperp: Schluessel liefert 50101

Der OKX-EEA-Satz von `xperp` antwortete mit `APIKey does not match current environment`,
obwohl `handel_erlaubt` und `freigabe.erfuellt` true sind und das Fenster offen war.
**Offen:** Konto-seitig klaeren (Host EEA vs. global, IP-Whitelist, read-only-Recht).
Kein Dateischalter loest das. Kandidaten zum Gegenpruefen: signierter Leseaufruf gegen den
Registry-Host, Rechte des Schluessels im OKX-Portal.

## 2. `kraken` bleibt im Papier

Freies Guthaben reichte zuletzt nicht fuer `mindest_guthaben_eur 60`, und die eigene
Rueckrechnung ist **-0,57 % je Runde**. Der Schalter steht auf `false`, `stillgelegt` ist
gesetzt.
**Offen:** Entscheidung, ob Kraken-Guthaben aufgestockt wird. Ohne das ist kraken bewusst
nicht live — die Auto-Freigabe wuerde nur das Fenster oeffnen, nicht das Guthaben.

## 3. Ausser-Haus-Kopie

`Q:\MaxHirn-AusserHaus` ist vollstaendig und geprueft (150.732 Dateien / 63,74 GB), aber
**nicht verschluesselt** und enthaelt Klartext-Zugangsdaten (`Wissen/Zugaenge.md`,
`Wissen/OKX_API.env`). Ohne angesteckte `Q:`-Platte stecken alle Kopien im selben Rechner.
**Offen:** Verschluesselung oder ein zweiter Ort ausser Haus.

## 4. Abschaltungen des Rechners (T-004)

Kernel-Power 41 mit BugcheckCode 0, kein Minidump, kein WHEA; Netzteiltausch erfolglos.
**Offen:** naechste Verdaechtige sind Kaltgeraetekabel/Steckdose und Lastspitzen. Bis dahin
keine langen Schreiblaeufe ohne Sicherung, keine Windows-Reparaturinstallation.

## 5. Skill-Baum: ~914 MB Fremd-Klone

`Agenten/Hermes/skills/` traegt noch **fuenf** unversionierte Fremd-Repo-Klone ohne
SKILL.md: OmniRoute 828M, claude-code 45M, onchainos-skills 31M, one-skill-to-rule-them-all
6,9M und -main 3,4M (gemessen 22.09.2026). Die uebrigen ~892 MB (unsloth, nautilus_trader,
EasyCLIProxyAPI, chromaprint, public-apis, acoustid-index, mfaupel95) sind am 21.09.2026 nach
`Werkstatt/repos-verschoben-aus-skills` verschoben. Alle neu klonbar; per `.gitignore`
gesperrt (sonst bricht `git add -A` mit Exitcode 128 ab).
**Offen:** die fuenf loeschen oder bewusst behalten — Kosten sind nur Plattenplatz.

## 6. Profile in `.deleted/`

17 am 19.09.2026 weggelegte Profile (`projectatlas`, `skills`, `superpowers`, `tradingview-mcp`,
`agent-reach`, `nous`, `codex`, `scrapling`, `santiment`, …) sind per `/bot` nicht erreichbar.
**Offen:** zurueckholen, was wieder gebraucht wird — oder liegen lassen.

## 7. Uv-Cache und App-Daten auf C:

`C:` ist bei **61,1 GB frei von 475 GB** (gemessen 22.09.2026) — nicht mehr kritisch.
`uv/cache` ist auf 0,8 GB geschrumpft. Der Plattendruck ist damit entschaerft; `uv cache clean`
bleibt ein reproduzierbarer Knopf, falls es wieder knapp wird. Kein Umzug von `MaxHirn` noetig.