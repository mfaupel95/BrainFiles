# Anbindungs-Audit im Handel-Ordner

Wann: „was ist nicht abgeschlossen / nicht angebunden?“, „was laeuft hier
ueberhaupt?“ - oder als Abschluss nach dem Bau einer neuen Spur. Ziel ist eine
ergebnis-first-Liste in vier Toepfen:

1. **laeuft** und ist gemeldet
2. **laeuft**, aber unsichtbar (nicht im Bus, nicht im Tagesbericht)
3. **bewusst gesperrt** (Sperre in `wachen.json`, negatives Backtest-Urteil)
4. **Altlast** - Handwerkzeug oder verwaist

am Ende **eine** Empfehlung, nicht eine Optionsliste.

## Die Verdrahtungsstellen gegeneinander halten

Nicht jede einzeln lesen, sondern die Schnittmengen bilden - der Befund ist die
Differenz:

- `dauerlauf.SPUREN` — was im 15-min-Takt laeuft
- `Bus/handel_befehle.SPUREN` — was `/status` per Telegram zeigt
- `tagesbericht.py` — `Select-String -Pattern 'def spur_'` **und** der Eintrag im
  Tupel in `baue()` (zwei Stellen, beide noetig)
- Aufgabenplanung — `Get-ScheduledTask | Where-Object { $_.TaskName -match
  'Handel|Kraken|DCA|Verbesserer' }`, dann je Aufgabe
  `(Get-ScheduledTask -TaskName $n).Actions` fuer das Skript und
  `Routinen/<skript>.ps1` fuer das, was es aufruft
- Versionierung — `git check-ignore -v <pfad>` und `git status --porcelain <ordner>`

Eine Spur kann in `dauerlauf.SPUREN` stehen und trotzdem unsichtbar sein: sie
laeuft, aber `/status` und Tagesbericht kennen sie nicht. Das ist der
haeufigste Fund bei einer frisch gebauten Spur (Ordner da, Tests gruen, Lauf
sauber - und keine der vier Melde- und Versionsstellen nachgezogen).

## Aufrufer suchen

```powershell
Select-String -Path "$r\*.ps1","$b\*.py","$h\*.py" -Pattern 'modulname'
```

- **Kein `-Recurse` ueber `Agenten`**: laeuft durch `.venv`, `OpenAlice`,
  `nautilus` und reisst die ~300-s-Grenze des Host-Werkzeugs. Explizite
  Pfadliste uebergeben.
- Wer einen Modulnamen sucht, findet Definitionsstellen mit: `def <name>`, ein
  Docstring-Beispiel und der eigene Aufruf im `__main__`-Block zaehlen **nicht**
  als Aufrufer. Nur Treffer in fremden Dateien sind Beweise.

## Befunde richtig deuten (die drei Fehlalarme)

- **„kein Aufrufer“ ist kein Defekt.** Analysemodule (`dca.py`, `grid.py`,
  `reinvest.py`, `vergleich.py`, `beobachte_live.py`, `dca_auswertung.py`) sind
  Handwerkzeuge fuer Max - im `README.md` des Handelsordners beschrieben, per
  Definition nicht getaktet. Als Topp 4 melden, nicht als Luecke.
- **Stilllegung nie aus einem Textfeld lesen.** `stillgelegt`, `handel_erlaubt`,
  `freigabe.erfuellt` sind die Wahrheit; der `_`-Kommentar daneben ist Historie
  und kann das Gegenteil erzaehlen. Vor dem Urteil `git log --oneline -5` - an
  diesem Baum arbeiten mehrere Sitzungen, und eine Spur kann zwischen zwei
  Commits wieder angeschaltet worden sein.
- **Eine Spur, die ihren Lauf verweigert und trotzdem per Aufgabe startet, ist
  kein Fehler.** Die Kraken-Spur rechnet im Papierlauf die Rangliste weiter, obwohl
  `handeln.py --papier` den Handel verweigert - so bleibt der Nachweis erhalten.
  Das ist gewollt; nicht „aufraeumen“.

## Was in den Bericht gehoert

Je Luecke die **konkrete Stelle** (Datei, Funktion/Dict) und die kleinste
Reparatur - nicht „orbk ist nicht richtig angebunden“, sondern „`spur_orbk()`
fehlt in `tagesbericht.py` plus der Eintrag im Tupel in `baue()`“. Dazu die
Trennung, die Max immer mitliest: was absichtlich **nicht** angefasst wurde
(laufender Zustand, Fremdarbeit, generierte Dateien) und was eine Entscheidung
von ihm braucht.
