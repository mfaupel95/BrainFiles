# Vorlagen fuer den Sitzungsabschluss

Alles hier ist **Form**, keine Erzaehlung: die Zahlen kommen aus der Sitzung.
Zugangsdaten kommen nirgends hinein.

## 1. Neuer Punkt in `MaxHirn/Archiv/TASKS.md`

In den Abschnitt `## Offen`, ID = hoechste vergebene + 1 (nie wiederverwenden):

```
- [ ] **T-049 — Kurztitel**
      Kontext: worum es geht, warum es offen ist. Messwerte mit Datum und
      Herkunft (Datei, Befehl, Journal), keine Schaetzung.
      Naechster Schritt: eine konkrete, ausfuehrbare Handlung.
      Betrifft: Agenten/Handel/<spur>, Aufgabe MaxHirn-<name>
      Wartet auf: Max - <was genau>        (Pflicht bei [~]/?/[!])
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-22
```

Status: `[ ]` offen · `[~]` in Arbeit · `[?]` wartet auf Entscheidung ·
`[!]` blockiert · `[x]` erledigt.

## 2. Erledigtes nach `## Erledigt`

Der Block wandert **ganz** nach unten, Kuerzel wird `[x]`, das Datum kommt in
Fettschrift an den Anfang des Kontexts:

```
- [x] **T-049 — Kurztitel**
      **Erledigt 2026-09-22.** Was gemessen wurde, bis es fertig war, und mit
      welchem Befehl es sich nachpruefen laesst.
      Betrifft: <Pfade>
      Angelegt: 2026-09-22 · Zuletzt: 2026-09-22
```

Nie loeschen — die Historie ist der Beleg, dass es schon einmal versucht wurde.

## 3. Punkt in `MaxHirn/Wiki/Offen/Entscheidungen.md`

Nur was **Max** entscheiden muss. Messung + naechster Schritt, kein Auftragstext.
Erledigtes wird geloescht (nicht durchgestrichen), `updated:` im Kopf nachziehen.

```markdown
## N. <Stichwort>

Was gemessen ist (Zahl, Datum, Befehl) und was daran fehlt.
**Offen:** die eine Entscheidung, die Max treffen muss, und wer sie ausfuehrt.
```

## 4. Kontextzeilen im Aufgabeneintrag

Fuer die drei Angaben, die sonst gern im Chat bleiben:

```
      Nicht angefasst: <Pfad/Prozess> — <Grund>.
      Uebernommen aus fremder Sitzung: <Pfade> (Commit <hash>, Autor fremd@local).
      Vorschlag: <vermutete Folgearbeit> — noch nicht beauftragt.
```

## 5. Abschlussmeldung (vier Zeilen)

```
1. Funktioniert jetzt: <was> — nachpruefbar mit `<befehl>`.
2. Nicht angefasst: <was> — <warum>.
3. Entscheidung Max: <was> — Zahlen: <gesetzt/bindend>.
4. Naechster Schritt (<2 min): `<befehl>`.
```
