# Docker-Sandbox: Umgebungsvariablen hineinreichen

Trigger: Tools laufen im Docker-Terminal-Backend (Desktop/GUI) und sehen
Variablen nicht — `${env:NAME}` bleibt leer, Ollama findet keine Modelle,
Werkzeuge laufen ohne Key. Der Sandbox-Container erbt die Host- oder
Profil-Umgebung **nicht von selbst**.

Zwei Schluessel unter `terminal:` legen fest, was hineinkommt:

- `terminal.docker_forward_env` — Liste von Variablen**Namen**. Hermes loest
deren Werte beim Ausfuehren aus der Shell-Umgebung, dann aus der Profil-`.env`
auf und injectet sie in den Container. Die echten Geheimnisse stehen **nie** in
der Config, nur die Namen — fuer Tokens/Keys ist das immer die richtige Wahl.
- `terminal.docker_env` — Literale `KEY: value`-Paare direkt in der Config.
Fuer statische Schalter (DEBUG, PYTHONUNBUFFERED), nicht fuer Geheimnisse.

Setzen und belegen:

    hermes config set terminal.docker_forward_env '["A","B"]'
    hermes config get terminal.docker_forward_env   # Block-Liste, kein String

`hermes config set` speichert den JSON/YAML-Wert als echte Liste (dieselbe
strukturierte Parsung wie bei `fallback_providers`) — kein Handedit, keine
eigenen Listenzeilen in der Datei.

Fallen:

- **Der Container erbt nur, was im Prozess steht, der Hermes startet.**
  Windows-Benutzervariablen (HKCU, z. B. `OLLAMA_MODELS`, `HANDEL_RISIKO`)
  findet `docker_forward_env` nur, wenn der Desktop/Gateway sie in seiner
  Umgebung hat (HKCU erben sie beim Start). Stehen sie nur in einer
  bash-Session, fehlen sie dem Container. Namen in die Forward-Liste
  aufnehmen; die Werte kommen aus HKCU.
- **Backend-Konfig gilt fuer alle Oberflaechen gleichzeitig.** Die CLI kann
  `terminal.backend: local` laufen, waehrend Desktop/GUI den Docker-Backend
  nutzt — `docker_forward_env` wirkt nur auf den Docker-Zweig, unabhaengig
  vom gerade aktiven Backend. „Im Docker verfuegbar" heisst: den Docker-Zweig
  der `terminal:`-Sektion konfigurieren, den aktiven Backend nicht umstellen.
- **Nachweis nur aus einer Docker-Sitzung.** Aus einer Host-`local`-Sitzung
  (git-bash) ist kein docker-exec-Nachweis moeglich; den Live-Check
  (`env | grep -E 'NAME'`) als Schritt dem Container-User ueberlassen.
  Config-seitig belegt: `hermes config get` + die Datei lesen.
