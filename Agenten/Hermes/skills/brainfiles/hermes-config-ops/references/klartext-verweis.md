# Klartext-Geheimnis auf einen Verweis umstellen

1. **Fundstelle und Umfang** bestimmen: alle Zeilen mit `api_key|token|secret|password`
   in `config.yaml` auflisten, Werte redigieren (nur Länge ausgeben).
2. **Kandidat in der `.env` suchen**: SHA-256-Anfang jedes `NAME=WERT` gegen den Fund
   hashen. Treffer = Variablenname, fertig. Kein Treffer → sprechenden Namen in der
   `.env` anlegen. Hermes' eigene Namen (`HERMES_CUSTOM_<host>_<port>_API_KEY`) sind
   stabil, solange der Provider-Eintrag bleibt — der Verweis darf sie mitbenutzen.
3. **Sichern, dann die eine Zeile ersetzen:** `token: ${NAME}`. Regex mit
   `MatchEvaluator`, **nicht** mit Ersatzstring — `$` und `${…}` im Ersatz würden sonst
   als Gruppenreferenz gedeutet.
4. **Auflösung belegen:**
   `scripts/config-wert-pruefen.py --pfad <punktpfad>` — Länge und `sha8` müssen dem
   Vorher-Wert entsprechen (identischer Wert = der Dienst läuft unverändert weiter).
5. **Speicher-Rundlauf belegen** (derselbe Aufruf mit `--speicherprobe`): kopiert die
   `config.yaml` in ein Temp-`HERMES_HOME`, belegt die Variable mit einem Dummy, speichert
   und zeigt, dass danach weiter `${NAME}` in der Datei steht. Erst damit ist belegt, dass
   die laufende App den Klartext nicht beim nächsten Speichern zurückholt.
6. Erst dann Notiz und Commit.
