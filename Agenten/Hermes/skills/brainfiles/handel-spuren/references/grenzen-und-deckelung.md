# Grenzen einer Spur: welche Zahl bindet, und der Deckel vor dem Fenster

Fuer Auftraege der Form „Limit pro Trade X, insgesamt Y“, „Deckel hochschrauben“,
„handel erlaubt“ — also Aenderungen an den GRENZEN einer bestehenden Spur. Gilt
fuer Papier- und Live-Grenzen gleichermassen; die Live-Grenzen heissen eigen
(`live_*`).

## 1. Wer liest die Zahl, die ich aendere?

Vor jeder Aenderung greppen, wer den Schluessel liest — nicht nur, wo er steht:

```
grep -rn "live_max_pro_trade_usd\|live_max_gesamt_usd\|max_pro_trade_usd" <spur>/
```

- Ein Grenzwert wird fast immer ueber einen **einen Leser** geholt
  (`_live_grenze(w, "max_pro_trade_usd", <ersatz>)` liest `live_max_pro_trade_usd`,
  sonst den Papierwert), damit Papier und Live getrennte Zahlen haben. Wer den
  Papierwert aendert und den Live-Treffer meint, hat nichts geaendert.
- **Ein Kommentar-/Vermerkfeld ist keine Messung.** Gemessen: der datierte Vermerk
  an der Grenze nannte „10“, der tatsaechliche Wert war 50 — ein alter Text, der wie
  eine Tatsache aussieht, kostet eine ganze Runde. Nach jeder Aenderung den VERMERK
  mitziehen und die alten Zahlen darin richtigstellen; sonst fuehrt die naechste
  Sitzung mit einer falschen Zahl.

## 2. Welche der vier Grenzen bindet?

Es gibt vier Kandidaten, und nur einer ist der Engpass. Rechne sie aus und NENNE
den bindenden, statt die Aenderung zu feiern:

| Grenze | Wirkung |
|---|---|
| Betrag **je Trade** (`live_max_pro_trade_usd`) | deckelt den einzelnen Einsatz |
| **Gesamt**deckel (`live_max_gesamt_usd`) | deckelt die Summe aller offenen Positionen |
| **Plaetze** (`live_max_offene_positionen`) | deckelt die Zahl der Positionen |
| **Guthaben** in der Kontowaehrung | deckelt alles zusammen, unabhaengig von der Konfiguration |

Merksatz: **Plaetze x Betrag gegen den Gesamtdeckel halten.** 5 Plaetze a 100 =
500 bei Deckel 400 heisst: ab der vierten Position ist nicht mehr der Betrag der
Engpass, sondern der Deckel. Der Guthaben-Deckel schlaegt beide, sobald das freie
Guthaben kleiner ist als Betrag x Plaetze — das ist der Normalfall und kein Fehler.

## 3. Den Einsatz auf das freie Guthaben deckeln — VOR dem Freigabefenster

Ein Betrag, den die Boerse gar nicht deckt, ist kein Grenzproblem, sondern eine
abgelehnte Order: sie schreibt eine Fehlerzeile ins Journal und sieht wie ein
Defekt aus, obwohl die Spur richtig gerechnet hat. Deshalb steht die Deckelung
**vor** der Anzeige des Freigabefensters und vor der Mengenrechnung:

```python
def betrag_gedeckelt(betrag, w):
    """Einsatz auf das FREIE Guthaben deckeln (Gebuehr + etwas Luft)."""
    frei = op_guthaben(GUTHABEN_WAEHRUNG)
    if not frei:
        return betrag, "kein freies %s-Guthaben gemeldet" % GUTHABEN_WAEHRUNG
    geb = float(w.get("gebuehr_taker", 0.006) or 0.0)
    deckel = frei * (1 - geb - 0.002)
    if betrag <= deckel:
        return betrag, None
    return deckel, "Einsatz %.2f -> %.2f EUR gedeckelt (%.2f frei)" % (betrag, deckel, frei)
```

- **Keinen neuen Mindestbetrag erfinden:** reicht der gedeckelte Betrag nicht fuer
die Mindestmenge des Paares, lehnt die vorhandene Mengenrechnung ab (`menge_fuer`).
- **Die Gebuehr des VENUE nehmen, nicht die der Heimatboerse** (Kraken taker 0,6 %,
  Deribit anders, OKX anders) — sonst ist der Deckel zu hoch und die Order platzt
  genau an der Grenze.
- Die Deckelung **sichtbar machen** (`print` in der Vorschau): bei der Frage
  „warum ist die Position kleiner als eingestellt?“ ist diese Zeile die Antwort.
- Gilt auch beim Guthabentor (`mindest_guthaben_*`): erst pruefen, ob das Tor noch
der Verwendung entspricht (ein Tor „3 x Einsatz 30 = 100“ ist veraltet, wenn der
Mindesteinsatz laengst 60 ist), dann erst die Zahl senken.

## 4. Nachweis fuer eine Grenzaenderung

1. **Vorher/nachher am echten Objekt zeigen:**
   `<spur>/handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1` (so ruft der Dauerlauf sie
   auf) muss `Live waere gesperrt durch: nichts` sagen — genau EIN Grund, sonst
   greift die Auto-Freigabe nicht.
2. **Die Rechnung der Grenze direkt pruefen** (Funktion mit gepatchtem Guthaben und
   Waehrung, nicht das ganze Buch) — und mit einem Kontostand, der die Grenze reisst.
3. **Die Reihenfolge im Code festnageln** (Quelltext-Test): der Deckel-Aufruf muss
   VOR dem Orderaufruf stehen. Ein Test, der nur den Rueckgabewert prueft, merkt
   nicht, wenn die Deckelung hinter der Order landet.
4. **Spiegelung und Buch unberuehrt nachweisen** (`spiegelstand.py`), und im Bericht
   sagen, was NICHT angefasst wurde (offene Positionen, Stops, Fremdguthaben).
5. Wirkt **ohne Neustart** des Dauerlaufs, solange die Spur je Zyklus als eigenes
   Kind startet; nur die Wachen-Datei wird bei jedem Zyklus neu gelesen.
