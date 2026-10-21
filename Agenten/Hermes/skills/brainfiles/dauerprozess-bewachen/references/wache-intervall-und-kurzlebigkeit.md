# Wache-Intervall vs. kurzlebige Vorfälle

## Regel

Das Polling-Intervall einer Wache muss KLEINER sein als der kürzeste Vorfall,
den sie fangen soll. Eine Wache, die alle 4 h läuft, verpasst einen Verlust,
der zwischen zwei Läufen entsteht und repariert wird.

Gemessener Fall (11.10.2026): die konfig-doktor-wache prüfte die
Wurzel-Junctions (Werkstatt, Modelle) alle 4 h. Ein Junction-Verlust entstand
02:00, wurde 02:20 repariert, der nächste 4-h-Lauf kam 05:18 — unerkannt,
obwohl die Reparatur-Sitzung ihn dokumentiert hatte. Der Verlust fiel durch
das Fenster.

## Vorgehen

- **Für einen kurzlebig möglichen Zustand eine eigene schnelle Wache fahren**
  (10 min), neben der langsamen Breitensicht — nicht das Intervall der
  Breitensicht senken. Die schnelle Wache prüft nur das eine Merkmal
  (z. B. LinkType+Target+Inhalt der Junctions), die langsame bleibt der breite
  Blick (Regelpaare, Plattenplatz, Ballast).
- **Die schnelle Wache prüft mehr als „ist der Verweis da“:**
  1. Pfad existiert und ist ein Reparse-Punkt (Junction/Symlink) — ein
     Schatten-Ordner ist der Verlust in seiner häufigsten Form und wird von
     `os.path.islink()` übersehen (liefert für Windows-Junctions False).
     Verlässlich ist FILE_ATTRIBUTE_REPARSE_POINT (0x400).
  2. Ziel stimmt (zeigt der Verweis auf das erwartete Laufwerk?).
  3. Ziel erreichbar und nicht (fast) leer — ein Schatten mit 2 Einträgen
     wäre sonst still.
- **Watchdog-Muster:** leere Ausgabe = nichts senden; ein Fehler der Prüfung
  selbst ist NIE ein leeres Ergebnis, sondern ein gemeldeter Befund.
- **Merkdatei mit Wiederholungs-Sperre** (derselbe Befund höchstens alle
  12 h), damit ein wachsender Wert nicht jede Stunde neu meldet.

## Testmuster

Echte Junctions in %TEMP% anlegen (`cmd /c mklink /J <link> <target>`,
braucht keine Admin-Rechte), die echte Wurzel unberührt lassen. Fälle:
gesunde Junction schweigt, echter Ordner statt Verweis wird gemeldet,
Junction auf falsches Ziel wird gemeldet, Junction auf leeres Ziel wird
gemeldet, `_ist_verweis` erkennt die Junction trotz `islink()==False`.
