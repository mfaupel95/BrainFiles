---
name: okx-live-anbinden
description: "OKX-Spur live anbinden: Freigabe, Keys, Guthaben, Transfer."
version: 0.1.0
author: Hermes
platforms: [windows]
metadata:
  hermes:
    tags: [Handel, OKX, Live, Freigabe, Guthaben]
---

# OKX-Spur live anbinden

Bringt eine OKX-Handelsspur (z. B. xperp) von Papier auf Live: Freigabe-Bedingungen
pruefen und ggf. lockern, `handel_erlaubt` + Herzschlag setzen, OKX-Keys und
Guthaben verifizieren, USDC vom Funding- ins Trading-Konto transferieren. Es
schaltet NIE selbst scharf — die Freigabe kommt nur ueber die Kette. Kann die
Freigabe auf Max' Anweisung automatisieren (Auto-Freigabe fuer feste Spuren,
zeitlich begrenzt).

## When to Use

- „Spur X live schalten" / „Handelsfreigabe fuer X" / „X auf OKX anbinden"
- „nimm automatisch an" / Freigabe ohne /ja erteilen (Auto-Freigabe)
- Eine OKX-Spur soll echtes Geld bewegen (XPERP-Futures, Spot)
- OKX-Keys funktionieren nicht (50101) oder Guthaben fehlt im Trading-Konto

## Prerequisites

- Spur-Ordner unter `Agenten/Handel/<spur>/` mit `wachen.json`, `handeln.py`,
  `okxf.py` (OKX-Anbindung). Interpreter: `Agenten/Handel/scanner/.venv/Scripts/python.exe`.
- OKX-Keys als Benutzervariablen/Registry: `OKX_API_KEY`, `OKX_API_SECRET`,
  `OKX_API_PASSPHRASE`, optional `OKX_BASE` (EEA-Portal: `https://eea.okx.com`).
- Keys muessen `Trade`-Recht haben und die IP-Whitelist fuer Orders muss stehen.

## How to Run

Invoke through the `terminal` tool, aus dem Spur-Ordner:
`../scanner/.venv/Scripts/python.exe handeln.py --wachen`

## Quick Reference

- Freigabe-Status: `handeln.py --wachen` (runden_echt, freigabe_erfuellt, herzschlag, EV)
- Bedingung 1: `MaxHirn/Wissen/Handelsregeln.md` Zeile ~401
- wachen.json freigabe-Block: `erfuellt`, `papierlauf_min_runden`, `netto_positiv_nach_gebuehren_und_funding`, `groesster_ruecklauf`
- Lockerung: `_netto_positiv_entfaellt`, `_papierlauf_min_wochen_entfaellt`, `_papierlauf_min_runden_entfaellt`
- OKX-Basis: `OKX_BASE` (www vs eea); 50101 = falsche Basis
- Demo-Modus: `OKX_DEMO`/`OKX_SIMULATED` (Registry HKCU\Environment)
- Guthaben Trading: `GET /api/v5/account/balance`
- Guthaben Funding: `GET /api/v5/asset/balances`
- Transfer Funding→Trading: `POST /api/v5/asset/transfer` from=6 to=18

## Procedure

1. **Freigabe-Status messen** (nicht raten): aus dem Spur-Ordner
   `../scanner/.venv/Scripts/python.exe handeln.py --wachen`. Zeile `Freigabe erfuellt`
   nennt `runden_echt` (echte Papierrunden) und `freigabe_erfuellt`. Herzschlag-Grenze
   und EV daneben.
2. **Fehlende Bedingungen namentlich nennen** (Hausregel: Live nie aus dem Chat).
   Bedingung 1 = 6 Wochen Papierlauf, ≥ 50 Runden, netto positiv, Ruecklauf < kill_switch.
3. **Bedingungen lockern** (nur auf Max' Anweisung): in `Handelsregeln.md` Bedingung 1
   den Entfall dokumentieren UND in `wachen.json` das Feld durch
   `_<name>_entfaellt` ersetzen (z. B. `netto_positiv_nach_gebuehren_und_funding` →
   `_netto_positiv_entfaellt` mit Datum + Anweisung). `freigabe.erfuellt` bleibt der
   von Hand gesetzte Haken.
4. **`handel_erlaubt=true` + `herzschlag_max_minuten=45`** setzen (Hausregel: 45 BEVOR
   handel_erlaubt auf true). JSON-Gueltigkeit pruefen (`json.load`).
5. **OKX-Keys verifizieren**: `okxf.schluessel_vorhanden()` und `okxf.demo_modus()`.
   `50101 APIKey does not match current environment` = Keys passen nicht zur Basis
   (www vs eea) — `OKX_BASE=https://eea.okx.com` setzen, wenn die Keys vom EEA-Portal
   sind. Demo-Modus (`OKX_DEMO`/`OKX_SIMULATED`) setzt den `x-simulated-trading`-Header
   und lehnt Live-Keys mit 50101 ab — in der Registry pruefen
   (`[Environment]::GetEnvironmentVariable('OKX_DEMO','User')`).
6. **Guthaben pruefen**: Trading (`/api/v5/account/balance`) UND Funding
   (`/api/v5/asset/balances`). USDC landen oft im Funding (Cash), aber Futures brauchen
   sie im Trading (Krypto).
7. **Transfer Funding→Trading** (OKX-intern, kein Blockchain-Transfer):
   `POST /api/v5/asset/transfer` mit `{ccy, amt, from: "6", to: "18"}`. Danach
   Trading-Balance erneut pruefen.
8. **Freigabekette ausloesen** (Max): `/ja_<spur>` im Dauerlauf oder `freigabe.py`-Fenster.
   `freigabe.erfuellt=true` kommt NUR ueber die Kette, nie aus dem Chat.
9. **Auto-Freigabe einbauen** (nur auf Max' Anweisung, namentlich Spuren): erlaubt
   den Spuren, die Freigabe automatisch zu bekommen, ohne /ja je Signal.
   - **Nur Spuren mit echtem Live-Pfad**: `grep -c -- "--live" <spur>/handeln.py`;
     enthaelt die Datei `verweigert` (moondev-*), hat sie keinen Live-Pfad und die
     Auto-Freigabe waere wirkungslos — weglassen und benennen.
   - In `dauerlauf.py` die Konstanten `AUTO_FREIGABE = ("<spur>", ...)` und
     `AUTO_FREIGABE_STUNDEN = 12` einfuegen (zeitlich begrenzt, kein Dauerzustand).
   - In `pruefe_anfragen()`: nach `anfrage_stellen(spur, 12*60)` fuer Spuren in
     `AUTO_FREIGABE` sofort `freigabefenster.oeffnen(spur, AUTO_FREIGABE_STUNDEN,
     "auto")` statt zu senden — genau der Weg, den `/ja` geht.
   - **`freigabe.erfuellt=true` in wachen.json setzen** — der Live-Pfad prueft
     BEIDES (freigabe.erfuellt UND das Freigabefenster); ohne den Haken oeffnet
     die Auto-Freigabe das Fenster, aber die Spur handelt trotzdem nicht.
   - Tests laufen lassen (`test_dauerlauf_*`, Bus-Suite), committen, pushen,
     **Dauerlauf neu starten** (PID-Dateien + `Start-ScheduledTask` fuer
     `MaxHirn-Handel-Dauerlauf` und `-Mittel-Waechter`), damit die neue
     dauerlauf.py aktiv wird.

## Pitfalls

- **Live nie aus dem Chat scharf schalten** — auch nicht, wenn Max bittet. Fehlende
  Bedingungen namentlich nennen, den Weg zeigen.
- **`freigabe.erfuellt` ist der von Hand gesetzte Haken** — `handel_erlaubt=true` allein
  schaltet nichts scharf; der Live-Pfad verweigert bis `freigabe.erfuellt=true`.
- **50101 = falsche Basis**, nicht kaputte Keys. www.okx.com vs eea.okx.com pruefen.
- **Demo-Modus in bash-Session ist ein Artefakt**: `OKX_SIMULATED` kann in der
  Session-Umgebung geerbt sein, ohne in der Registry zu stehen. Mit
  `env -u OKX_SIMULATED -u OKX_DEMO` testen; im echten Betrieb (Dauerlauf) zaehlt die
  Registry.
- **USDC im Funding ≠ Trading**: Futures brauchen die Margin im Trading-Konto. Erst
  transferieren, dann pruefen.
- **Guthaben 0 USDT/USDC** = kein Kapital; xperp rechnet in USD (USDT/USDC), nicht in
  WAXP/CHIP o. a. Token.
- **Fremdaenderung im Arbeitsbaum**: `git status --porcelain <pfad>` vor dem Schreiben;
  eine parallele Sitzung kann an derselben Datei arbeiten. Nicht doppelt schreiben.
- **Auto-Freigabe hebt die letzte menschliche Huerde auf**: jedes Einstiegssignal wird
  ohne Bestaetigung ausgefuehrt — Konsequenz klar benennen, zeitlich begrenzen
  (12h), nicht dauerhaft. Nur Spuren mit echtem Live-Pfad aufnehmen.
- **`freigabe.erfuellt` und Freigabefenster sind ZWEI Sperren**: die Auto-Freigabe
  oeffnet nur das Fenster; ohne `freigabe.erfuellt=true` in wachen.json handelt die
  Spur trotzdem nicht. Beides setzen.
- **Der Kill-Switch steht NICHT im `--vorschau`-Text — und `handel_erlaubt=true`
  allein loest ihn aus.** Gemessen am 01.10.2026 an xperp: `lage` meldete
  `kill=true` (Ruecklauf 279.85 >= `kill_switch_gesamt_usd` 250), die Vorschau
  nannte aber nur `handel_erlaubt=false; kein offenes Freigabefenster`. Wer nur den
  Schalter umlegt, laesst genau EINEN Sperrgrund uebrig, der das Wort
  'Freigabefenster' traegt — `dauerlauf.nur_fenster_fehlt` greift, die
  AUTO_FREIGABE oeffnet das Fenster selbst, und der naechste Live-Lauf stellt
  FLACH (verkauft die echten Positionen). **Reihenfolge: erst Kill-Switch bzw.
  Deckel klaeren, dann `handel_erlaubt` setzen.** Vorher immer `handeln.py
  --wachen` lesen, nicht nur `--vorschau`.
- **Eine Papier-Spur schuetzt ihre echten Positionen nicht.** `xperp/handeln.py`
  ruft `bueche_fremde_positionen_uebernehmen` nur im LIVE-Zyklus — solange die
  Spur Papier laeuft, bleiben an der Boerse eroeffnete Positionen ohne Buch und
  ohne Stop. Handgriff fuer den Bestand:
  `xperp/fremde_positionen_uebernehmen.py` (Vorschau ist Standard, `--anwenden`
  bucht und stellt den Stop). Vor jedem Live-Schalten pruefen:
  `/api/v5/account/positions` gegen `<spur>/zustand.json` und auf einen
  Schutzauftrag — **ALLE ordTypes lesen** (`conditional`, `oco`, `trigger`,
  `move_order_stop`), nicht nur `attachAlgoOrds`. Genau daran ist
  `fremde_positionen_uebernehmen.py` am 01.10.2026 gescheitert: es sah bei ZEC,
  VVV und ADA kein `attachAlgoOrds`, uebersah die vorhandenen OCO- und
  move_order_stop-Auftraege und stellte drei Stops doppelt — der neuere, engere
  feuert zuerst, der Stop wurde damit unbemerkt von -8.6 % auf -2.7 % gezogen.

## Verification

`../scanner/.venv/Scripts/python.exe handeln.py --wachen` zeigt `Freigabe erfuellt True`
und `handel_erlaubt true`; `GET /api/v5/account/balance?ccy=USDC` zeigt USDC im
Trading-Konto.
