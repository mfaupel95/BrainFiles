---
id: 20260921-kosten-und-bedingungen
title: 'Handel — Kosten und Bedingungen'
tags: [handel, kosten]
created: 2026-09-21
updated: 2026-09-22
related: ['[[Handel/Spuren-Uebersicht]]', '[[Wissen/Handelsregeln]]', '[[Wissen/Handelsbots]]']
summary: 'Gebuehren (Kraken gemessen 0,6 % je Seite) und ihr Wendepunkt je Spur (f_max), die Bedingungen 1-5, und der Merksatz zur Aussagekraft kleiner Stichproben.'
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
| Kraken (Spot) | `gebuehr_taker: 0.006` | **gemessen** 0,60 % je Seite = **1,2 % je Runde** — das Abo wirkt nicht |
| OKX | wie in `wachen.json` | Margin ist **USDC**, nicht USDT (siehe [[Handel/Boersen-und-Schluessel]]) |
| Deribit (`iv_waelle`) | 0,05 % | hier NICHT 0 — bewusst eigener Wert |

**GEMESSEN 22.09.2026 — der Kraken-Nullsatz war falsch.** Zwei unabhaengige Zeugen:
die Fuellungen (`SOLEUR`: Kauf 50,01954 EUR mit 0,30012 EUR Gebuehr, Verkauf 50,01466 EUR mit
0,30009 EUR) und `/0/private/TradeVolume` (taker 0,6000 % fuer SOLEUR, XXBTZEUR, XETHZEUR,
SUIEUR, HYPEEUR; 30-Tage-Volumen 3.479 EUR, naechste Stufe 0,38 % ab 10.000 EUR). Das
Kraken-Pro-Abo entfaellt also **nicht** — es greift auf diesem Konto nicht. `kraken` traegt
deshalb wieder den gemessenen Satz (`gebuehr_taker: 0.006`, datierter Vermerk
`_gebuehren_abo_widerlegt`); eine Runde kostet damit 1,2 % statt 0 %. **Merksatz: eine
Gebuehrenannahme wird an einer echten Fuellung geprueft, nicht an einer Tarifseite** —
`TradeVolume` ist der zweite Zeuge, `handeln.py --wachen` zeigt nur, was in der Datei steht.

**`mosaic` fuehrt KEIN Gebuehrenfeld.** Sein Journal (einstieg/ausstieg) und die Auswertung
ueber `auswertung_alle.runden_indikator` rechnen **brutto** — wer es netto beurteilt, muss
1,2 % je Runde selbst abziehen. Erster Live-Vorgang am 22.09.2026: 0,605 EUR Kosten in gut
einer Sekunde (Kauf, gescheiterter Stop, Rueckverkauf).

**Freivolumen zaehlt auf das HANDELSVOLUMEN** (Kauf + Verkauf), also doppelt je Runde:
~250 Runden/Monat bei 20 EUR Nominal, ~50 bei 100 EUR. Diese Angabe stammt aus der
Abo-Annahme vom 13.09.2026 und ist seit der Messung vom 22.09.2026 **gegenstandslos**: es gibt
kein Freivolumen auf diesem Konto. `orbk` ist die einzige Spur, deren Kalkulation auf 0 %
Gebuehr gebaut ist — bei ihm ist der Nullsatz Teil der Rechnung, nicht nur eine Annahme.

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