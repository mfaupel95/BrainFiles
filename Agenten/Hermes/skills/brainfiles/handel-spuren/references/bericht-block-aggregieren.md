# Mehrere Spuren als EINEN Block im Bericht zeigen

Ausloeser: „die X-Spuren im Bericht vereinheitlichen“, „die Ausgabe schlanken“,
„die Familie soll kompakt erscheinen“, oder wenn eine Spurgruppe (z. B. spiegel +
Schattenbuecher + Kopier-Arme) den Tagesbericht mit N gleichartigen Bloecken fuellt.

Die Zusammenfassung gehoert auf die **HOLER-Ebene von `lage.py`**, nicht in den
Renderer: `tagesbericht` rendert jede Holer-Rueckgabe generisch (`_block`), und
eine zweite Spurliste im Renderer altert still.

## Vorgehen

1. **Aggregierenden Holer bauen** (`spur_<familie>_familie()`), der die Einzelholer
   aufruft und EIN Dict zurueckgibt:
   - `positionen`: die ECHTEN Positionen aller Buecher, je Eintrag um ein Feld
     `buch` ergaenzt. Sie tragen die Gesamtsumme (`gesamt_offen`) und den
     Tagesvergleich (Schnappschuss) - deshalb NICHT auf eine Zusammenfassung
     kuerzen.
   - `familie`: eine schlanke Liste je Buch `{name, offen, bilanz}` fuer die Ausgabe.
   - `name`, `waehrung`, `w`, `bilanz` (Familien-Summenzeile).
2. **In `HOLER` die N Einzelholer durch den einen Familien-Holer ersetzen** - die
   Funktionen selbst BLEIBEN: andere Verbraucher und Tests importieren sie namentlich.
3. **Render-Zweig in `tagesbericht._block`**, der bei gesetztem `familie` frueh
   zurueckkehrt und je Buch EINE Zeile druckt (Name, offene, Bilanzzeile) plus die
   Summenzeile - nicht die Positionsliste.
4. **Den Zaehler-Test mitziehen** (`len(lage.HOLER)`) und die neue Zahl im Kommentar
   begruenden; sonst ist der Test rot und die Ursache unklar.
5. **Nach dem Umbau die echte Ausgabe zeigen** (`roh -> lage.zu_lage -> _block`),
   nicht nur die Tests gruen melden.

## Fallen

- **`zu_lage()` normalisiert auf eine FESTE Feldliste und verwirft alles andere.**
  Ein neues Feld (`familie`) muss dort ausdruecklich durchgereicht werden
  (`"familie": roh.get("familie")`), sonst greift der Render-Zweig nie und der
  Bericht zeigt weiter die lange Positionsliste - ohne Fehlermeldung. Im Test das
  Feld in der `zu_lage`-Ausgabe zusichern.
- **Der Test muss durch den ECHTEN Pfad laufen** (`roh -> lage.zu_lage(roh, None)
  -> tagesbericht._block(...)`). Eine handgebaute Dict direkt an `_block` verdeckt
  genau diesen Verlust - der Fehler wurde so zuerst uebersehen.
- **Ein Aggregat darf keinen Spurordner-Namen tragen.** `_schluessel_von()` leitet
  den Schluessel aus dem Basename von `roh["ordner"]` ab und gibt ihn nur zurueck,
  wenn er in `auswertung_alle.SPUREN` steht. Fuer eine Familie also KEIN `ordner`
  setzen (sonst kollidiert der Schluessel mit dem Hauptbuch) und keinen
  `auswertung_alle`-Eintrag erwarten: Schluessel bleibt None, der Bericht nimmt den
  Namen.
- **Keine zweite Rechnung.** Die Bilanzzeile jedes Buchs kommt aus dessen eigener
  `auswertung.py` (ueber `lage._bilanz`), nicht aus einer im Bericht nachgebauten
  Formel.
- **Zielgroesse in der Familienzeile:** Treffer UND Ergebnis zeigen. Die
  Trefferquote allein fuehrt in die Irre - ein weiterer Stop kann die Quote heben
  (mehr Positionen knapp im Plus) und das Ergebnis verschlechtern (die Verlierer
  laufen tiefer).
