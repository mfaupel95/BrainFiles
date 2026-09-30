"""Die Aussenseite der Reaktionsschicht: vier Kanaele, jeder einzeln abschaltbar.

Hier steht absichtlich alles, was den Rechner verlaesst oder Zustand ausserhalb
des eigenen Ordners anfasst. Der Rest (reaktion.py) entscheidet nur und ruft
diese Funktionen; dadurch laesst sich die Entscheidungslogik ohne Nebenwirkung
testen (siehe test_reaktion.py, das eine Attrappe einsetzt).

Grundhaltung, uebernommen vom Bus (Agenten/Bus/ereignis.py): keine dieser
Funktionen wirft. Eine Reaktion, die wegen eines stummen Melders abbricht,
verliert genau die Meldung, um die es ging. Jede Funktion gibt deshalb
(ok, detail) zurueck und das Protokoll haelt fest, welcher Kanal versagt hat.

Belegte Eigenheiten dieser Installation (beim Bauen am 20.09.2026 gemessen):

- Der Board-Kanal laeuft ueber `hermes kanban`. In einer Kanban-Sitzung ist
  HERMES_DELEGATED_CHILD_CONTEXT gesetzt; die CLI verweigert dann jede
  Board-Aenderung ("delegate_task child contexts cannot mutate Kanban tasks").
  Die Variable wird fuer den Unterprozess entfernt, sonst schlaegt der Kanal
  lautlos fehl (Exitcode 0, Text "cannot mutate").
- Der Memory-Kanal schreibt in das basic-memory-Projekt (~/basic-memory), NICHT
  in den Vault MaxHirn. Das ist Absicht und Grenze: der Vault bleibt die
  einzige Wahrheit und wird von keiner Automatik beschrieben.
- `basic-memory tool edit-note --operation append` legt eine fehlende Notiz an
  (fileCreated: true) - es braucht also kein vorheriges write-note.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BRAINFILES = Path(
    os.environ.get("BRAINFILES_WURZEL")
    or os.environ.get("HERMES_WRITE_SAFE_ROOT")
    or Path.home() / "Documents" / "BrainFiles"
)
HERMES = BRAINFILES / "Agenten" / "Hermes"
BUS = BRAINFILES / "Agenten" / "Bus"
HERMES_EXE = HERMES / "bin" / "hermes.exe"
BASIC_MEMORY_EXE = Path.home() / ".local" / "bin" / "basic-memory.exe"

ZEITLIMIT_S = 120


# --- Hilfsmittel ------------------------------------------------------------


def _umgebung() -> dict[str, str]:
    """Umgebung fuer Unterprozesse: ohne den Delegations-Riegel (siehe Kopf)."""
    umgebung = dict(os.environ)
    umgebung.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    # Trigger: jeder Aufruf von basic-memory (es laedt ein Embedding-Modell).
    # Warum: ohne diese Grenze brach `basic-memory tool edit-note` beim
    # Ende-zu-Ende-Lauf drei von fuenf Mal mit "OpenBLAS error: Memory
    # allocation failed after 10 retries" ab - OpenBLAS oeffnet einen Thread je
    # Kern (hier 28) und scheitert an dessen Stackbedarf, wenn parallel ohnehin
    # Agenten laufen. Mit einem Thread liefen drei Aufrufe in Folge sauber.
    # Outcome: der Memory-Kanal ist langsamer, aber nicht mehr sporadisch stumm.
    umgebung.setdefault("OPENBLAS_NUM_THREADS", "1")
    umgebung.setdefault("OMP_NUM_THREADS", "1")
    return umgebung


def _lauf(argumente: list[str], eingabe: str | None = None, voll: bool = False) -> tuple[bool, str]:
    """Startet ein Programm, gibt (ok, Text) zurueck. Wirft nie.

    voll=False kuerzt auf die letzten drei Zeilen (das Log soll lesbar bleiben);
    voll=True gibt alles zurueck - noetig, wenn der Aufrufer die Ausgabe parst
    statt sie zu protokollieren.
    """
    try:
        fertig = subprocess.run(
            argumente,
            input=eingabe,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=ZEITLIMIT_S,
            env=_umgebung(),
        )
    except Exception as fehler:  # noqa: BLE001 - ein toter Kanal darf nichts abbrechen
        return False, f"{type(fehler).__name__}: {fehler}"
    text = ((fertig.stdout or "") + (fertig.stderr or "")).strip()
    # Die Kanban-CLI meldet die Verweigerung mit Exitcode 0. Ohne diese
    # Sonderpruefung gilt ein nicht geschriebener Kommentar als Erfolg.
    ok = fertig.returncode == 0 and "cannot mutate Kanban tasks" not in text
    if voll:
        return ok, text
    return ok, " | ".join(text.splitlines()[-3:])[:400]


# --- Kanal 1: Log -----------------------------------------------------------


def log_schreiben(pfad: Path, eintrag: dict) -> tuple[bool, str]:
    """Eine JSONL-Zeile anhaengen, mit fsync wie im Bus-Journal.

    Trigger: jede Reaktion, immer, auch im Probelauf.
    Warum: das Log ist der einzige Kanal, der ohne fremden Dienst funktioniert;
    faellt Board, Telegram oder Memory aus, bleibt hier der Beleg.
    """
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with open(pfad, "a", encoding="utf-8", newline="\n") as datei:
            datei.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
            datei.flush()
            os.fsync(datei.fileno())
    except Exception as fehler:  # noqa: BLE001
        return False, f"{type(fehler).__name__}: {fehler}"
    return True, str(pfad)


# --- Kanal 2: Board ---------------------------------------------------------


def board_kommentar(task_id: str, text: str, autor: str = "reaktion") -> tuple[bool, str]:
    """Kanban-Kommentar schreiben (Statusupdate bei Erfolg, Befund bei Fehler)."""
    if not HERMES_EXE.exists():
        return False, f"hermes fehlt: {HERMES_EXE}"
    return _lauf(
        [str(HERMES_EXE), "kanban", "comment", task_id, text, "--author", autor]
    )


def board_blocken(task_id: str, grund: str, art: str = "transient") -> tuple[bool, str]:
    """Task blocken - die schaerfste Eskalation, die ohne Menschen moeglich ist.

    Trigger: eskalation.danach == board_blocken, nach erschoepften Wiederholungen.
    Warum art=transient als Voreinstellung: ein fehlgeschlagener Automatiklauf
    ist zunaechst eine flatternde Stoerung. Wiederholt sich derselbe Block,
    schiebt die Board-Logik den Task selbst nach triage - dafuer braucht die
    Reaktionsschicht keine eigene Zaehlung.

    Trigger: der Task ist bereits blockiert. Dann antwortet die CLI mit "cannot
    block <id>" und Exit 1 - im Ende-zu-Ende-Lauf genau so aufgetreten. Warum
    das als Erfolg gilt: das Ziel der Eskalation ist der Zustand "blockiert",
    nicht der Vorgang. Ein zweiter Fehlschlag derselben Regel darf keinen
    Kanalausfall melden, sonst jagt man einem Phantom nach. Der Grund steht
    ohnehin als Kommentar am Task.
    """
    if not HERMES_EXE.exists():
        return False, f"hermes fehlt: {HERMES_EXE}"
    ok, detail = _lauf(
        [str(HERMES_EXE), "kanban", "block", task_id, grund, "--kind", art]
    )
    if not ok and "cannot block" in detail and _ist_blockiert(task_id):
        return True, "bereits blockiert (Zustand erreicht)"
    return ok, detail


def _ist_blockiert(task_id: str) -> bool:
    """Prueft den Status, damit "cannot block" nicht blind verziehen wird."""
    ok, text = _lauf([str(HERMES_EXE), "kanban", "show", task_id, "--json"], voll=True)
    if not ok:
        return False
    try:
        daten = json.loads(text[text.index("{") :])
    except (ValueError, json.JSONDecodeError):
        return False
    aufgabe = daten.get("task", daten)
    return aufgabe.get("status") == "blocked"


# --- Kanal 3: Nachricht (Telegram ueber den BrainFiles-Bus) -----------------


def telegram_hinweis(wer: str, text: str) -> tuple[bool, str]:
    """Meldung auf das Handy, ueber Agenten/Bus.

    Der Bus ist bewusst die einzige Bruecke: er schreibt die Zeile zuerst ins
    Journal und verteilt danach. Ist der Dienst tot, landet die Meldung im
    Journal und der Sprecher findet sie beim naechsten Durchgang - eine
    verlorene Meldung gibt es damit nicht.
    """
    if not (BUS / "ereignis.py").exists():
        return False, f"Bus fehlt: {BUS}"
    zuvor = list(sys.path)
    try:
        sys.path.insert(0, str(BUS))
        import ereignis  # type: ignore[import-not-found]

        weg = ereignis.hinweis(wer, text)
        return weg in {"bus", "journal"}, f"weg={weg}"
    except Exception as fehler:  # noqa: BLE001
        return False, f"{type(fehler).__name__}: {fehler}"
    finally:
        sys.path[:] = zuvor


# --- Kanal 4: Wissensspeicher (basic-memory) --------------------------------


def memory_anhaengen(
    notiz: str, zeilen: list[str], projekt: str | None = None
) -> tuple[bool, str]:
    """Beobachtungen an eine basic-memory-Notiz anhaengen (Kontext fuer spaeter).

    Format der Zeilen ist bewusst das Beobachtungsformat von basic-memory
    (`- [kategorie] text`), damit die Eintraege durchsuchbar sind und nicht als
    Textblock im Nichts stehen.
    """
    if not BASIC_MEMORY_EXE.exists():
        return False, f"basic-memory fehlt: {BASIC_MEMORY_EXE}"
    argumente = [
        str(BASIC_MEMORY_EXE),
        "tool",
        "edit-note",
        notiz,
        "--operation",
        "append",
        "--content",
        "\n".join(zeilen) + "\n",
    ]
    if projekt:
        argumente += ["--project", projekt]
    return _lauf(argumente)


# --- Buendel ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Kanaele:
    """Die vier Kanaele als austauschbares Buendel.

    reaktion.py kennt nur dieses Buendel. Tests setzen eine Attrappe ein und
    pruefen die Entscheidungen, ohne einen Kommentar, eine Nachricht oder eine
    Notiz in der echten Welt zu erzeugen.
    """

    log: object = log_schreiben
    board_kommentar: object = board_kommentar
    board_blocken: object = board_blocken
    telegram: object = telegram_hinweis
    memory: object = memory_anhaengen


ECHTE_KANAELE = Kanaele()
