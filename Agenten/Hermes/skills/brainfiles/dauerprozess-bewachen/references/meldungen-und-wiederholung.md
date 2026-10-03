# Meldungen: nur Aenderungen, und einmal je Zustand

## Die Regel

Ein Watchdog meldet **neue Befunde**, keinen **Zustand**. Derselbe Text
geht genau einmal raus; danach schweigt der Lauf, bis sich etwas aendert
oder eine Wiederholungsfrist (6 h) abgelaufen ist.

Baustein ist eine Merkdatei in `Agenten/Hermes/cache/<name>.json`:

```python
alt = _merk_laden()          # {schluessel: {"meldung": str, "zeit": float}}
for k, m in zeilen.items():
    eintrag = alt.get(k) or {}
    immer = "Order" in m or "scheitert" in m       # Ereignisse
    alt_genug = jetzt - float(eintrag.get("zeit") or 0) > WIEDERHOLUNG_S
    if eintrag.get("meldung") != m or immer or alt_genug:
        raus.append(m); neu[k] = {"meldung": m, "zeit": jetzt}
    else:
        neu[k] = eintrag                          # unveraendert: nicht melden
_merk_schreiben(neu)          # nur heutige Schluessel: wer verschwindet, ist geloescht
```

Vier Punkte, alle aus Fehlern entstanden:

1. **Zustand vs. Ereignis.** Ein Wartender ("Auftrag bleibt in der Queue")
   ist ein Zustand, eine ausgefuehrte Order und ein Ordnerfehler sind
   Ereignisse. Zustand → nur bei Aenderung; Ereignis → immer.
2. **Weg aus der Liste loescht die Merkung.** Sonst ist die naechste
   Meldung derselben Spur nie wieder "neu" und die Spur verstummt
   endgueltig.
3. **Niemals das Wort "bleibt" als Meldung benutzen.** In
   `signal-executor.py` bedeutete "bleibt" "wartet auf Freigabe" – und
   machte aus einem Zustand eine Meldung.
4. **Mehrere Dateien, eine Sache.** Drei Risikostufen (Basis, mittel, hoch)
   haben je eine `signal_queue*.json`; dieselbe Spur stand dadurch dreifach
   in jeder Meldung. Je Sache eine Zeile, Stufen als Zahl in der Zeile.

## Der Takt ist kein Argument

Ein Cron alle 60 Sekunden vervielfacht einen Fehler, nicht eine Information.
Gemessen: 50 Ausgabedateien in 10 Minuten, jede mit derselben dreifachen
Zeile. Wenn eine Wache im Minutentakt laeuft, MUSS die Wiederholungssperre
drin sein - sonst ist sie ein Spamkanal.

## Gegenprobe pflichtig

Test: denselben Zustand dreimal melden -> genau eine Zeile. **Gegenprobe:**
das alte Verhalten (jede Meldung immer, `return list(zeilen.values())`)
macht 4 von 9 Tests rot. Ohne diese Gegenprobe kann `melde_neu()` auch
`immer []` zurueckgeben und der Test ist gruen, ohne etwas zu pruefen.

## Zwei Fallen beim Testen

- **Pfad-Test auf dem umgebogenen Pfad.** Biegt der Test `MERK` auf einen
  Temp-Pfad, prueft `assertTrue(MERK.startswith(CACHE))` genau die Sache,
  die abgestellt werden sollte: gruen, weil der Temp-Pfad in einem Temp-Pfad
  liegt. Das echte `MERK` **vor** dem Umbiegen merken (`MERK_ECHT`) und
  beide pruefen.
- **`FAILED (errors=1)` auf einen Namen, den es nicht gibt.** Am
  03.10.2026 war das kein Testbefund, sondern der Dateischwund (T-100): die
  Testdatei war zwischen zwei Aufrufen weg. Ein FAILED mit `ModuleNotFoundError`
  ist kein Befund ueber den Code - erst `ls`, dann urteilen.