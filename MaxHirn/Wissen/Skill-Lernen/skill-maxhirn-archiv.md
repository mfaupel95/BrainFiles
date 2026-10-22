---
name: skill-maxhirn-archiv
description: Trockenlauf des Skills MaxHirn:archiv - sucht im Archiv-Index nach den Lernnotizen; Ergebnis: keine Treffer, weil Wissen/ nicht im Index liegt.
metadata:
  type: reference
---

**Zweck:** Durchsucht Max' Dateiarchiv per Volltext. Immer vor einer Internetsuche, wenn es um eigene Unterlagen geht.

**Wann nutzen:** Bei Fragen, deren Antwort in Rechnungen, Verträgen, Belegen, Fotos, Anleitungen oder Notizen liegen könnte.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: prüfen, ob eine Lernnotiz im Archiv-Index auffindbar ist. Suche mit `search_cli.py` über den Begriff `skill-lernen`. Nichts abgelegt.

**Ergebnis:**
- Die Suche liefert `Keine Treffer fuer: skill-lernen`.
- Der Befund ist erwartbar: Der Index deckt die Ordner des Archivs ab (Bilder, Videos, Musik, Dokumente). Die Lernnotizen liegen in `MaxHirn/Wissen/`, und `Wissen/` ist nicht Teil dieses Index.
- Die Lernnotizen sind also über das Archiv nicht auffindbar. Gefunden werden sie über `MaxHirn/Wissen/INDEX.md` oder über eine Textsuche im Ordner `Wissen/Skill-Lernen/`.

**Gelernt:** Der Archiv-Skill ist für eigene Unterlagen gebaut. Vault-Notizen gehören in den Wissen-Index. Eine Suche dort kann man nicht mit dem Archiv-Befehl ersetzen.

**Vorgehen beim Trockenlauf:** Der Server `archiv` war in dieser Sitzung nicht geprüft. Der Befehl über die Kommandozeile lief, der Python-Pfad muss vom Vault-Wurzelordner `MaxHirn` aus gestartet werden, nicht von `BrainFiles`.

**Grenzen:** Eine Stichwortsuche, keine Prüfung des Inhalts der Notizen. Ein Treffer hätte nur die Dateiliste gezeigt, nicht die Qualität der Einträge.
