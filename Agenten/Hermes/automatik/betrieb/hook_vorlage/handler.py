"""Hook-Vorlage: Gateway-Nachrichten in den Engine-Eingang legen.

NICHT INSTALLIERT. Diese Datei ist eine Vorlage. Wer den Nachricht-Trigger
scharf stellen will, kopiert sie nach

    Agenten/Hermes/hooks/automatik-nachricht/handler.py

und legt daneben eine HOOK.yaml an (Beispiel in derselben Vorlage, siehe
BETRIEB.md Abschnitt "Nachricht-Trigger anbinden").

Warum der Hook nur eine Datei schreibt und die Engine nicht aufruft:
Hook-Fehler blockieren die Hermes-Pipeline nicht - ein Fehler hier bliebe
unsichtbar. Eine Datei dagegen liegt im Eingang und wird beim naechsten
Cron-Tick gesehen, auch wenn der Hook zwischendurch kaputt war. Ausserdem
haelt das den Hook billig: er darf nie so lange brauchen, dass eine
Chat-Antwort daran haengt.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

# Muss zu HERMES_AUTOMATIK_BASIS der Engine passen.
BASIS = Path(os.environ.get(
    "HERMES_AUTOMATIK_BASIS",
    "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/kanban/workspaces/"
    "t_9f7db046/betrieb/arbeit"))

INTERESSANT = ("agent:start", "command:telegram", "gateway:message")


def handle(event_type, context):
    if event_type not in INTERESSANT:
        return

    text = ""
    absender = ""
    kanal = "telegram"
    if isinstance(context, dict):
        text = str(context.get("text") or context.get("prompt") or "")
        absender = str(context.get("sender") or context.get("user") or "")
        kanal = str(context.get("channel") or kanal)
    if not text:
        return

    eingang = BASIS / "nachrichten"
    try:
        eingang.mkdir(parents=True, exist_ok=True)
        ziel = eingang / ("%d_%s.json" % (int(time.time()), uuid.uuid4().hex[:8]))
        ziel.write_text(json.dumps({
            "kanal": kanal,
            "text": text[:2000],
            "von": absender,
            "zeit_unix": int(time.time()),
        }, ensure_ascii=False), encoding="utf-8")
    except OSError:
        # Ein kaputter Eingang darf niemals die Chat-Antwort aufhalten.
        return
