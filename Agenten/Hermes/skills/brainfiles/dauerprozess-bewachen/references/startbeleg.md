# Einen Start belegen statt behaupten

Gilt fuer alles, was gestartet und dann fuer "fertig" gehalten wird: Server,
Oberflaechen, Dienste, gebaute Frontends.

## Warum der einfache Weg nicht reicht

| Scheinbeleg | Was er wirklich sagt |
|---|---|
| Prozess laeuft | gestartet, nicht bereit |
| Logdatei hat Zeilen | Startzeilen, nicht Funktion |
| `GET /` -> 200 | irgendeine Seite, nicht das Programm |
| kurz gewartet, HTTP 000 | keine Aussage, nur zu frueh gefragt |
| Befehl "erfolgreich" gestartet | nichts ueber das Ueberleben |

## 1. Bereitschaft messen, nicht Liveness

Nach dem Start in Schritten von 3 s bis ~150 s den ECHTEN Endpunkt abfragen
(`urllib.request`; `HTTPError` mitnehmen, er traegt einen Code). Fristen fuer
Anwendungen sind grosszuegig: ein Server, der nach 8 s "lief", war nach 41-57 s
bereit. Zusaetzlicher Abbruch: Prozess tot UND Log hat Inhalt — dann nennt das
Log den Grund.

**Ein lebender Prozess ist nie das Kriterium.** Er ist die Vorbedingung.

## 2. Statuscode ist keine Identitaet

Hat das Frontend eine Catch-all-Route, liefert JEDER Pfad 200 und dieselbe
Datei. Eine Antwort auf `/` beweist deshalb nichts ueber das, was auf `/` liegt.

- Nach **Inhalt** unterscheiden: `<div id="root">`, Bundle-Name
  (`/assets/main-*.js`), `<title>`, Dateigroesse.
- Alle Kandidaten vergleichen (`/`, die eigentliche Datei, `/app`, `/docs`) und
den abweichenden finden — die Startseite eines Web-Baus ist oft eine
  Marketing-/Landing-Seite, die Anwendung liegt eine Ebene daneben.
- **Die gemessene Adresse weitergeben, mit dem Unterschied.** "Die Oberflaeche
  laeuft auf Port X" ist als Anleitung unbrauchbar: eine falsche Adresse
  schickt den Nutzer auf eine Seite, die antwortet und trotzdem nicht das
  Programm ist.
- Authentifizierte Endpunkte separat nennen: `401` auf einem API-Pfad ist ein
  gueltiger Beleg ("die API verlangt Anmeldung"), kein Fehlschlag.

## 3. Bau- und Pruefbefehle: Ausgabeverzeichnis vorher sichern

Ein Bau-Befehl wird geprueft, indem er einmal laeuft — und ein Fehlversuch kann
`dist/`, `build/` oder `target/` **vorher leeren**. Vorher kopieren (kopieren,
nicht umbenennen: der Bau legt es oft neu an), danach Dateizahl UND Groesse
gegen vorher halten, bei Rueckgang zurueckschieben. Exit 0 allein ist kein
Beleg fuer einen gelungenen Bau — die Dateizahl ist es.

## 4. Das cwd entscheidet ueber relative Pfade

Ein relativer Programmpfad wird gegen das Arbeitsverzeichnis des AUFRUFERS
aufgeloest, und ein Verzeichnis, das ueber eine Junction/einen Symlink erreicht
wird, kann vom Bauwerkzeug auf sein echtes Ziel aufgeloest und dann abgelehnt
werden (`vite`: `fileName darf nicht absolut sein, received O:/...`).
Deshalb: **erst das tatsaechliche cwd ausgeben, dann den Fehlschlag deuten.**
Ein Befehl, der nur aus dem aufgeloesten Pfad laeuft, wird als solcher
aufgeschrieben (`cmd /c cd /d <echter Pfad> && <befehl>`) und mit Hinweis
weitergegeben — nicht anders formuliert, als er gemessen wurde.

## 5. Nachbefunde gehoeren in die Weitergabe

Ein ehrlicher Beleglauf foerdert fast immer mehr zutage, als "laeuft":
fehlende Hilfsdienste, die still auf einen Rueckfall umschalten (Cache,
Warteschlange), deaktivierte Anbindungen ohne Zugangsdaten. Das sind die
Befunde, die sonst niemand sieht, weil die Anwendung trotzdem startet.
