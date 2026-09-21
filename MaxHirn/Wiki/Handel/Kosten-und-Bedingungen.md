---
id: 20260921-kosten-und-bedingungen
title: 'Handel — Kosten und Bedingungen'
tags: [handel, kosten]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Handel/Spuren-Uebersicht]]', '[[Wissen/Handelsregeln]]', '[[Wissen/Handelsbots]]']
summary: 'Gebuehren und ihr Wendepunkt je Spur (f_max), die Bedingungen 1-5, und der Merksatz zur Aussagekraft kleiner Stichproben.'
---

# Kosten und Bedingungen

## Wo die Bedingungen stehen

Die vollstaendigen Bedingungen stehen in `Wissen/Handelsregeln.md` (Bedingung 1: Freigabe
durch Papierlauf — Datum, Runden, netto positiv; 2: Ruecklauf positiv; 3: Herzschlag;
4: Spiegelung; 5: EV nicht negativ). Diese Wiki-Seite sagt nur, **wie sie gerechnet werden**.

**Max lockert einzelne Kriterien** und dokumentiert das als datierten Vermerk
`_<kriterium>_entfaellt` im `freigabe`-Block der `wachen.json` plus Zeile in
`Handelsregeln.md`. Der Haken `freigabe.erfuellt` bleibt die Endabnahme.

## Bedingung 4 — Spiegelung

Jede Spur spiegelt Journal und Zustand **nach jedem Zyklus** nach `Q:\Handel_Journal\<spur>`
(auch im Notausstieg). Eine Rechnung: `scanner/wachen_pruefung.vermerke_spiegelung` schreibt
`journal_zweitziel/_ok/_info` nur beim **Wechsel**; die Kopie liegt NACH dem Herzschlag;
fehlendes `Q:` ist kein Zyklusfehler. `--vorschau` schreibt in keiner Spur Zustand.

**Nachweis.** `Agenten/Handel/spiegelstand.py` vergleicht jede Spur **byte-genau** (zuletzt
27/27; `spiegel` und `orb` werden als „ausserhalb des Dauerlaufs" mitgeprueft). Dieselbe
Rechnung liefert die Zeile „Journal ausser Haus" im Tagesbericht.

**Bekannter Ausreisser (21.09.2026, offen):** Nach dem Dauerlauf-Neustart um 18:59 lief
`Q:\Handel_Journal\ablehnungen.csv` 24 min hinterher, obwohl `spiegele_journal` unbedingt
kopiert und `_spiegeln()` an vier Stellen im `handeln.py` steht (846/933/947/994) — es gibt
also einen Zykluspfad, der zwischen Schreiben und Spiegeln frueher aussteigt. Nach manuellem
Nachzug wieder byte-gleich.

## Gebuehren

| Boerse | Gebuehr | Besonderheit |
|---|---|---|
| Kraken (Spot) | `gebuehr_taker: 0` | Kraken-Pro-Abo: Kauf+Verkauf bis 10.000 EUR Monatsvolumen gebuehrenfrei |
| OKX | wie in `wachen.json` | Margin ist **USDC**, nicht USDT (siehe [[Handel/Boersen-und-Schluessel]]) |
| Deribit (`iv_waelle`) | 0,05 % | hier NICHT 0 — bewusst eigener Wert |

**Risiko des Kraken-Nullsatzes:** Das ist ein **Abo-Vorteil, kein Marktpreis**. Faellt das Abo
weg, kostet die Runde wieder 0,4–0,8 %; die Rueckrechnung von `kraken` ist dann **-0,57 % je
Runde** und die Freigabe bleibt zu. Vor jedem Zaehlen von Runden fuer Bedingung 1 pruefen, ob
`gebuehr_taker` noch 0 sein DARF. Altzeilen im Journal tragen 50.20 (vor der Umstellung),
neue 50.00 — der Uebergang ist sichtbar.

**Freivolumen zaehlt auf das HANDELSVOLUMEN** (Kauf + Verkauf), also doppelt je Runde:
~250 Runden/Monat bei 20 EUR Nominal, ~50 bei 100 EUR. Gilt fuer alle Paare und ist an das
Abo gebunden. `orbk` ist die einzige Spur, deren Kalkulation auf 0 % Gebuehr gebaut ist.

## `kosten_wendepunkt.py` — f_max je Buch

Rechnet aus dem **eigenen Journal**: `f_max = p*C - (1-p)*R` (R = mittlerer Stop-Abstand in
Prozent, C = mittlerer Ziel-Abstand, p = Trefferquote) — die Gebuehr JE RUNDE, ab der nur noch
die Nullinie getroffen wird. Je JOURNAL eine Zeile (ein Ordner fuehrt Basis/Mittel/knapp/weit/
futures); umskalierte Altbestaende (`.falsch-skaliert`) und Sammel-globs ausgeschlossen.

Stand 21.09.2026: `orbk` **+0,07 %** (Runden nur 0,48 % breit — haengt vollstaendig an der
Kraken-Gebuehrenfreiheit; ohne Abo kostet die Runde 0,4 %, also fuenfmal der Vorteil),
`moondev_topmovers` +6,29 % (71 % Treffer), `scanner` +8,98 %, `xperp` +3,16 %, `swap`
+1,52 %, `omniquant` **-1,70 %** (8 Runden, 25 %) — auch bei 0 % Gebuehr nicht tragfaehig.

**Merksatz.** `f_max` benutzt die eigene Stichprobe. Unter **8 Runden** ist es ein Befund,
keine Messung. `auswertung_alle.py` unterscheidet deshalb „WARTET AUF DAS ERSTE SIGNAL"
(Zustand frisch, Journal entsteht erst beim ersten Handel: `supertrend`, `iv_wand`, `iv_waelle`)
von „KEIN BUCH UND LAEUFT NICHT" (echter Betriebsfehler). Mehrere Spuren schreiben **nur**
Handelszeilen — bei ihnen ist ein fehlendes Journal kein Fehler.

## Ratsch(en) — `ratschen.py`

Die EINE Umsetzung der Drawdown-Ratsche, von allen Spuren ueber den **Pfad** geladen
(`importlib.spec_from_file_location`, NICHT ueber `sys.path` — ein Eintrag auf `Handel/`
koennte gleichnamige Spurenmodule verdecken). Regel:

1. Schwelle ist ein **BETRAG** `drawdown_halbierung_usd`, ausdruecklich in der `wachen.json`.
2. Fehlt er: hergeleitet aus **Buchrisiko** = Risiko je Position x Hoechstzahl Positionen,
   x `drawdown_halbierung_im_buchrisiko` (Standard 1.0).
3. Sonst **keine** Ratsche (`halbierungsschwelle()` → None, Faktor 1.0, `lage()` meldet es).

`drawdown_halbierung_prozent` wird **nirgends** mehr gelesen — er war der Fehler. Werte heute
alle = 1.0 x Buchrisiko: scanner 36.00, xperp 30.00, swap 30.00, orbk 10.00, kraken 24.00,
mosaic 20.00, iv_waelle 24.00. `pruefe_ratschen.py` fragt jede Spur ueber ihr **eigenes**
`lage()` — eine nachgebaute Formel prueft die Formel, nicht die Spur.

**KAPITALKURVE BLEIBT UNGEFILTERT:** `drawdown`/Halbierung/Kill rechnen auf **allen** Buchungen.
Eine Stoerung ist gebucht — auch wenn sie keine Handelsentscheidung war.