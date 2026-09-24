# Was der Dauerlauf in den Chat schickt (und was nicht)

Ausloeser: Eine Zyklusmeldung enthaelt Zeilen, die kein Geschehen melden
("scanner: - Ausstiege -", "swap: XAU-USDT-SWAP short Stop 4318.2 …", "mosaic: 3
Live-Position(en) bleiben stehen …" dreimal) — oder eine echte Meldung fehlt.

## Die Regel

Gemeldet wird eine Zeile nur, wenn sie

1. ein **Geschehen ausspricht** (Ausstieg, Eroeffnung, Notaus, Kill, Fehlschlag) UND
2. ihr **Subjekt selbst nennt** (Instrument, Seite) — sonst ist sie im Chat nicht
   zuzuordnen.

Beides steht in `Agenten/Handel/dauerlauf.py` an EINER Stelle:

- `EREIGNIS_ANFANG = ("AUSSTIEG", "NOTAUS", "AUF ")` — die Zeile BEGINNT damit
  (nach `.strip()`). Spaltenueberschriften wie `- Ausstiege -` beginnen mit `-`
  und fallen damit heraus.
- `EREIGNIS_WORTE = ("kill-switch", "kill-schwelle", "notausstieg",
  "fehlgeschlagen", "hat ausgeloest", "gesperrt")` — irgendwo in der Zeile.
- `ereigniszeilen(ausgabe)` liefert die Treffer, `neue_ereignisse(ausgabe,
  vorher)` zusaetzlich die des VORIGEN Zyklus bereits gemeldeten heraus.

`Lauf.gemeldet` haelt je Spur die Zeilen des letzten Zyklus. Ohne diesen Vergleich
steht eine Dauerzeile (z.B. eine Sperrzeile, die bis zum Fensterablauf in jedem
Zyklus faellt) in jeder Meldung. Verschwindet die Zeile und kehrt spaeter zurueck,
meldet sie sich wieder — Stille ist also kein "abgehakt".

## Die drei Rauschklassen (Zyklus 21 der Basis, 25.09.2026)

| Zeile | Warum kein Ereignis |
|---|---|
| `- Ausstiege -` / `- Einstiege -` | Ueberschrift einer Spalte, kein Geschehen |
| `XAU-USDT-SWAP short Stop 4318.2 …` | Fortsetzungszeile der AUF-Zeile (Instrument steht nur in der ersten Zeile); "Stop" ist hier ein Spaltenname |
| `N Live-Position(en) bleiben stehen …` | Hinweis, der je Instrument einmal gedruckt wurde |

Die dritte Zeile war zusaetzlich dreifach: `pruefe_ausstiege(nur=inst)` laeuft je
Instrument ueber ALLE Positionen. Wer in einer solchen Funktion druckt, druckt N
mal — stattdessen **den Zaehler zurueckgeben und im Aufrufer EINMAL drucken**
(`mosaic/handeln.py`: `return uebersprungen`, Meldung in `lauf()`).

## Pflichten fuer eine Spur, die etwas melden will

- Eine neue Meldung braucht eine Zeile, die mit `AUSSTIEG`, `NOTAUS` oder `AUF `
  beginnt oder eines der Merkworte traegt — sonst bleibt sie im Log.
- Nie eine Zeile ohne Subjekt drucken: das Merkwort allein macht sie nicht
  zuordenbar.
- Den Meldeweg EINMAL je Zyklus betreten (Aufrufer), nicht je Schleifendurchlauf.

## Pruefen

- `Agenten/Handel/tests/test_dauerlauf_ereignisse.py` (11 Tests) enthaelt den
  Zyklus-21-Block **woertlich** als Fixture: er muss 0 Zeilen ergeben, ein echter
  Ausstieg/Einstieg/Notaus/Kill/Fehlschlag je 1.
- Gegenprobe am echten Lauf: eine Spur einmal wie der Dauerlauf starten und die
  Ausgabe durch `ereigniszeilen()` schicken
  (`MAXHIRN_ROUTINE=1 …python.exe handeln.py --papier`).
- **Wirkt erst nach einem Neustart des BASIS-Dauerlaufs** — nur die Basis sendet
  (`stumm = not risikostufe.ist_basis()`); die Stufenlaeufe laufen mit altem Code
  weiter, ohne dass es auffaellt. Neustart: `references/dauerlauf-neustart.md`,
  Filter immer ueber `Name='python.exe'` plus Argument-Prüfung, nie ueber einen
  Namensfilter auf `dauerlauf` (er trifft sonst die eigene Kommandozeile).