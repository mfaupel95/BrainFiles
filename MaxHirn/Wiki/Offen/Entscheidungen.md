---
id: 20260921-offene-entscheidungen
title: 'Offen — was auf eine Entscheidung wartet'
tags: [offen]
created: 2026-09-21
updated: 2026-09-21
related: ['[[INDEX]]', '[[Betrieb/Sicherung-und-Laufwerke]]', '[[Handel/Spuren-Uebersicht]]']
summary: 'Die offenen Punkte mit dem Stand vom 21.09.2026 — je Punkt: was gemessen ist, was fehlt, was der naechste Schritt ist.'
---

# Offen — was auf eine Entscheidung wartet

**Diese Seite ist eine Wiedervorlage, kein Auftrag.** Jeder Punkt nennt nur Messung und
naechsten Schritt. Erledigtes wird geloescht, nicht durchgestrichen (Historie liegt in Git).

## 1. Bedingung 4: eine Spur spiegelt manchmal spaeter

Stand 21.09.2026: nach dem Dauerlauf-Neustart 18:59 lief `Q:\Handel_Journal\ablehnungen.csv`
24 min hinterher, `spiegelstand.py` meldete ueber zwei Pruefungen „scanner ABWEICHUNG".
`spiegele_journal` kopiert unbedingt, `_spiegeln()` steht in `handeln.py` an vier Stellen
(846/933/947/994) — es gibt also einen Zykluspfad, der zwischen Schreiben und Spiegeln frueher
aussteigt. Nach manuellem Nachzug wieder 28/28 byte-gleich.
**Offen:** den Pfad finden und die Spiegelung an jeden Ausgang haengen — oder eine Wache auf
das Alter der `Q:`-Dateien setzen.

## 2. xperp: Schluessel liefert 50101

Der OKX-EEA-Satz von `xperp` antwortete mit `APIKey does not match current environment`,
obwohl `handel_erlaubt` und `freigabe.erfuellt` true sind und das Fenster offen war.
**Offen:** Konto-seitig klaeren (Host EEA vs. global, IP-Whitelist, read-only-Recht).
Kein Dateischalter loest das. Kandidaten zum Gegenpruefen: signierter Leseaufruf gegen den
Registry-Host, Rechte des Schluessels im OKX-Portal.

## 3. `kraken` bleibt im Papier

Freies Guthaben reichte zuletzt nicht fuer `mindest_guthaben_eur 60`, und die eigene
Rueckrechnung ist **-0,57 % je Runde**. Der Schalter steht auf `false`, `stillgelegt` ist
gesetzt.
**Offen:** Entscheidung, ob Kraken-Guthaben aufgestockt wird. Ohne das ist kraken bewusst
nicht live — die Auto-Freigabe wuerde nur das Fenster oeffnen, nicht das Guthaben.

## 4. Ausser-Haus-Kopie

`Q:\MaxHirn-AusserHaus` ist vollstaendig und geprueft (150.732 Dateien / 63,74 GB), aber
**nicht verschluesselt** und enthaelt Klartext-Zugangsdaten (`Wissen/Zugaenge.md`,
`Wissen/OKX_API.env`). Ohne angesteckte `Q:`-Platte stecken alle Kopien im selben Rechner.
**Offen:** Verschluesselung oder ein zweiter Ort ausser Haus.

## 5. Abschaltungen des Rechners (T-004)

Kernel-Power 41 mit BugcheckCode 0, kein Minidump, kein WHEA; Netzteiltausch erfolglos.
**Offen:** naechste Verdaechtige sind Kaltgeraetekabel/Steckdose und Lastspitzen. Bis dahin
keine langen Schreiblaeufe ohne Sicherung, keine Windows-Reparaturinstallation.

## 6. Skill-Baum: 1,8 GB Fremd-Klone

`Agenten/Hermes/skills/` traegt 12 unversionierte Fremd-Repo-Klone ohne SKILL.md (~1,8 GB,
jeder neu klonbar). Sie sind per `.gitignore` gesperrt (sonst bricht `git add -A` mit
Exitcode 128 ab und der Nachtsicherungszweig steht still).
**Offen:** loeschen oder bewusst behalten — Kosten sind nur Plattenplatz.

## 7. Profile in `.deleted/`

17 am 19.09.2026 weggelegte Profile (`projectatlas`, `skills`, `superpowers`, `tradingview-mcp`,
`agent-reach`, `nous`, `codex`, `scrapling`, `santiment`, …) sind per `/bot` nicht erreichbar.
**Offen:** zurueckholen, was wieder gebraucht wird — oder liegen lassen.

## 8. Uv-Cache und App-Daten auf C:

`C:` ist zu ~97 % voll. Echte Fresser sind App-Daten (AppData\Local\Packages 23,9 GB,
uv\cache 11,8 GB — reproduzierbar per `uv cache clean`), **nicht** Dokumente.
**Offen:** Aufraeumen ist jederzeit moeglich; kein Umzug von `MaxHirn` noetig (das entlastet
C: kaum und riskiert Pfadbrueche).