"""Ende-zu-Ende: Trigger -> Engine -> Skill laeuft -> Reaktion -> Log/Memory.

Das ist der Nachweis fuer t_f7937187: die beiden getrennt gebauten Haelften
(Engine t_9f7db046, Reaktionsschicht t_f682e5c1) arbeiten ueber automatik/
wirklich zusammen - nicht nur laut Beschreibung.

Was dieser Lauf NICHT tut, und warum:

  - Er fasst den Betrieb nicht an. Jede Probe bekommt ein eigenes tmp_path mit
    eigener Basis (Log, Zustands-DB), eigener Wurzel, eigener Registry, eigener
    Reaktionskonfig und eigenem Ablageordner. Dieselben Module wuerden sonst
    gegen die echte Zustands-DB und das echte Board laufen.
  - Er schickt keine Nachricht und kommentiert kein Board. Die vier Kanaele
    werden durch eine Attrappe ersetzt (wie test_reaktion.py); belegt werden
    die Entscheidungen und die Spuren im Dateisystem. Die echten Kanaele hat
    t_f682e5c1 separat belegt (ende_zu_ende.py dort).
  - Er startet keinen Agentenlauf (skill_art=skill). Die Engine sperrt den Weg
    ohne HERMES_AUTOMATIK_SKILL_START=1; ein Test, der ihn oeffnet, wuerde die
    Grenze wegtesten, die er beweisen soll.

Lauf:  python -m pytest tests/ende_zu_ende.py -q     (aus dem Workspace)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest
import yaml

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from automatik import pfade  # noqa: E402

pfade.module_einhaengen()

from automatik import kopplung  # noqa: E402
from engine import protokoll, registry, steuerung, zustand  # noqa: E402
from engine.quellen import Ausloeser, sammeln  # noqa: E402
import reaktion as reaktionsschicht  # noqa: E402

PROBEN = Path(pfade.engine()) / "tests" / "proben"


# --- Gerüst -----------------------------------------------------------------


class Attrappe:
    """Ersetzt die vier Kanaele: merkt sich jeden Aufruf, tut nichts.

    Dieselbe Bauart wie in test_reaktion.py. Nur so ist ein E2E-Lauf
    wiederholbar - ein Test, der bei jedem Aufruf eine Telegram-Nachricht
    schickt, wird nach zwei Tagen nicht mehr ausgefuehrt.
    """

    def __init__(self) -> None:
        self.rufe: list[tuple[str, tuple]] = []

    def _melder(self, name: str):
        def melden(*argumente):
            self.rufe.append((name, argumente))
            return True, "attrappe/" + name
        return melden

    def kanaele(self):
        """Echter Log-Kanal, attrappierte Aussenkanaele.

        Das Log schreibt in die Test-Ablage (tmp_path) und verlaesst den
        Rechner nicht - es bleibt darum echt, sonst pruefte der Test die
        Protokollspur nie wirklich. Board, Telegram und Memory werden ersetzt.
        """
        from kanaele import Kanaele, log_schreiben

        def log(pfad, eintrag):
            self.rufe.append(("log", (pfad, eintrag)))
            return log_schreiben(pfad, eintrag)

        return Kanaele(
            log=log,
            board_kommentar=self._melder("board_kommentar"),
            board_blocken=self._melder("board_blocken"),
            telegram=self._melder("telegram"),
            memory=self._melder("memory"),
        )

    def namen(self) -> list[str]:
        return [n for n, _ in self.rufe]


@pytest.fixture()
def welt(tmp_path, monkeypatch):
    """Eine vollstaendige, eigene Automatik-Welt je Test."""
    basis = tmp_path / "arbeit"
    wurzel = tmp_path / "wurzel"
    ablage = tmp_path / "reaktion"
    kopplungsordner = tmp_path / "kopplung"
    for p in (wurzel, ablage, kopplungsordner):
        p.mkdir(parents=True, exist_ok=True)

    # Engine-Seite
    monkeypatch.setenv("HERMES_AUTOMATIK_BASIS", str(basis))
    monkeypatch.setenv("HERMES_AUTOMATIK_WURZEL", str(wurzel))
    monkeypatch.setenv("HERMES_AUTOMATIK_SKRIPTPFADE", str(PROBEN))
    monkeypatch.setenv("HERMES_AUTOMATIK_KANBAN_DB", str(tmp_path / "kanban.db"))
    monkeypatch.delenv("HERMES_AUTOMATIK_SKILL_START", raising=False)
    # Kopplungs-Seite
    monkeypatch.setenv("HERMES_AUTOMATIK_ABLAGE", str(ablage))
    monkeypatch.setenv("HERMES_AUTOMATIK_KOPPLUNG", str(kopplungsordner))

    return {"tmp": tmp_path, "basis": basis, "wurzel": wurzel, "ablage": ablage}


def registry_schreiben(tmp_path, regeln) -> Path:
    daten = {"registry_version": "1.0.0", "defaults": {"modus": "dry_run"}, "regeln": regeln}
    p = tmp_path / "registry.yaml"
    p.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    return p


def reaktionskonfig_schreiben(tmp_path, regeln, monkeypatch, **defaults) -> Path:
    grund = {
        "kanal": "log+telegram",
        "memory_notiz": "automatik/laeufe/{regel_id}",
        "melde_erfolg": "immer",
        "eskalation": {"wiederholungen": 0, "wiederhol_abstand_s": 600, "danach": "melden"},
    }
    grund.update(defaults)
    daten = {"konfig_version": "1.1.0", "defaults": grund, "regeln": regeln}
    p = tmp_path / "reaktionen.yaml"
    p.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv("HERMES_AUTOMATIK_REAKTIONSKONFIG", str(p))
    return p


def regel_dict(**abweichung) -> dict:
    regel = {
        "id": "e2e-regel",
        "skill": "probe_schreiber.py",
        "skill_art": "skript",
        "trigger": {"typ": "datei", "prioritaet": 20,
                    "bedingungen": {"pfad_muster": ["quelle/*.md"], "aktion": "modified"}},
        "parameter": {},
        "erlaubte_aktionen": ["lesen", "datei_schreiben"],
        "schreibpfade": [],
        "modus": "auto",
        "timeout_s": 60,
        "kanal": "log",
        "rate_limit": {"max_laeufe": 10, "fenster_s": 3600},
        "abbruch": {"bei_fehlerstreak": 3},
    }
    regel.update(abweichung)
    return regel


def tick(reg) -> list[dict]:
    """Ein Engine-Durchlauf wie 'python -m engine tick'."""
    eintraege = []
    with zustand.offen() as con:
        for a in sammeln(reg, con):
            r = reg.nach_id(a.regel_id)
            eintraege.append(steuerung.ausfuehren(r, a, con, reg.version))
    return eintraege


def durchgang(attrappe, probe=False, registry_pfad=None, jetzt=None):
    """Ein Kopplungs-Durchlauf wie 'python -m automatik durchgang'."""
    return kopplung.durchgang(
        probe=probe, registry_pfad=registry_pfad, pruefen=False,
        jetzt=jetzt, kanaele=attrappe.kanaele(),
    )


def log_zeilen() -> list[dict]:
    return protokoll.zeilen_lesen()


def reaktionslog() -> list[dict]:
    p = Path(pfade.ablage()) / "reaktion-log.jsonl"
    if not p.exists():
        return []
    return [json.loads(z) for z in p.read_text(encoding="utf-8").splitlines() if z.strip()]


# --- 1. Der vollstaendige Weg ------------------------------------------------


def test_trigger_bis_reaktion(welt, monkeypatch):
    """Datei geaendert -> Skript laeuft -> Erfolg gemeldet -> Memory geschrieben.

    Das ist das Akzeptanzkriterium der Task in einem Test: ein Trigger, ein
    echter Prozess, eine Reaktion, ein nachweisbarer Eintrag.
    """
    quelle = welt["wurzel"] / "quelle"
    quelle.mkdir()
    (quelle / "a.md").write_text("erste Fassung\n", encoding="utf-8")
    ziel = welt["tmp"] / "ergebnis.json"

    reg_pfad = registry_schreiben(welt["tmp"], [regel_dict(
        parameter={"ziel": str(ziel), "text": "e2e"},
        schreibpfade=[str(welt["tmp"])],
    )])
    reaktionskonfig_schreiben(welt["tmp"], {}, monkeypatch)
    monkeypatch.setenv("HERMES_AUTOMATIK_REGISTRY", str(reg_pfad))
    reg = registry.laden(reg_pfad, pruefen=False)

    # Erster Tick nimmt nur den Stand auf - eine neue Datei-Regel feuert nicht
    # sofort beim Einbau (Engine-Verhalten, hier bewusst mitgeprueft).
    assert tick(reg) == []
    assert not ziel.exists()

    # Jetzt die echte Aenderung.
    time.sleep(0.01)
    (quelle / "a.md").write_text("zweite Fassung\n", encoding="utf-8")

    eintraege = tick(reg)
    assert [e["ergebnis"] for e in eintraege] == ["erfolg"], eintraege
    # Der Prozess lief wirklich - nicht nur die Engine meldet Erfolg.
    assert json.loads(ziel.read_text(encoding="utf-8"))["text"] == "e2e"

    attrappe = Attrappe()
    ergebnis = durchgang(attrappe, registry_pfad=reg_pfad)

    assert ergebnis.gelesen == 1, ergebnis
    assert ergebnis.fehler == []
    assert [r["befund"] for r in ergebnis.reaktionen] == ["erfolg"]
    # Gemeldet UND gemerkt: beides gehoert zum Akzeptanzkriterium.
    assert "telegram" in attrappe.namen()
    assert "memory" in attrappe.namen()
    assert reaktionslog()[-1]["befund"] == "erfolg"

    # Ein zweiter Durchgang ohne neuen Lauf meldet nichts - die Marke haelt.
    zweiter = Attrappe()
    nochmal = durchgang(zweiter, registry_pfad=reg_pfad)
    assert nochmal.gelesen == 0
    assert zweiter.namen() == []


# --- 2. Der Rueckweg: Fehler -> Nachlauf -> Neustart durch die Engine --------


def test_fehler_wird_nachgeholt(welt, monkeypatch):
    """Ein Fehlschlag wird vorgemerkt und beim naechsten Durchgang nachgestartet.

    Wichtig ist die Rollenteilung: die Reaktionsschicht merkt nur vor, die
    Engine startet. Ein Nachlauf, den niemand einspeist, ist eine Datei, die
    niemand liest.
    """
    ziel = welt["tmp"] / "nie.json"
    reg_pfad = registry_schreiben(welt["tmp"], [regel_dict(
        id="fehler-regel",
        trigger={"typ": "zeit", "prioritaet": 50, "bedingungen": {"intervall_min": 5}},
        parameter={"ziel": str(ziel), "exit": 7},
        schreibpfade=[str(welt["tmp"])],
    )])
    reaktionskonfig_schreiben(welt["tmp"], {}, monkeypatch, eskalation={
        "wiederholungen": 1, "wiederhol_abstand_s": 10, "danach": "melden"})
    monkeypatch.setenv("HERMES_AUTOMATIK_REGISTRY", str(reg_pfad))
    reg = registry.laden(reg_pfad, pruefen=False)

    with zustand.offen() as con:
        a = Ausloeser(regel_id="fehler-regel", typ="zeit", ausgeloest_durch="Probe")
        eintrag = steuerung.ausfuehren(reg.nach_id("fehler-regel"), a, con, reg.version)
    assert eintrag["ergebnis"] == "fehler", eintrag
    assert eintrag["exit"] == 7

    attrappe = Attrappe()
    ergebnis = durchgang(attrappe, registry_pfad=reg_pfad)
    assert [r["befund"] for r in ergebnis.reaktionen] == ["fehler"]
    assert ergebnis.reaktionen[0]["nachlauf_in_s"] == 10

    nachlauf = Path(pfade.ablage()) / "nachlauf.jsonl"
    assert nachlauf.exists(), "Reaktionsschicht hat nichts vorgemerkt"

    # Noch nicht faellig: die Engine bekommt nichts vorgelegt.
    zweiter = Attrappe()
    frueh = durchgang(zweiter, registry_pfad=reg_pfad, jetzt=time.time())
    assert frueh.nachlaeufe == []

    # Faellig: jetzt legt die Kopplung ihn der Engine vor, und die startet.
    dritter = Attrappe()
    spaet = durchgang(dritter, registry_pfad=reg_pfad, jetzt=time.time() + 30)
    assert [n["regel_id"] for n in spaet.nachlaeufe] == ["fehler-regel"], spaet.nachlaeufe
    assert spaet.nachlaeufe[0]["ergebnis"] == "fehler"

    # Und der Nachstart steht als eigener Lauf im Engine-Log.
    letzte = log_zeilen()[-1]
    assert letzte["regel_id"] == "fehler-regel"
    assert letzte["ausgeloest_durch"].startswith("nachlauf:")


# --- 3. Der Rueckweg: Grenzverletzung -> Sperre in der Engine ----------------


def test_grenzverletzung_sperrt_regel_in_der_engine(welt, monkeypatch):
    """Die Wache bricht ab, die Reaktion sperrt, die Engine haelt die Regel an.

    Das ist der sicherheitsrelevante Pfad: ohne die Uebertragung der Sperre
    waere eine Regel, die nachweislich ihre Grenze verletzt hat, beim naechsten
    Trigger einfach wieder gelaufen.
    """
    verboten = welt["tmp"] / "verboten.txt"
    reg_pfad = registry_schreiben(welt["tmp"], [regel_dict(
        id="frech-regel",
        skill="probe_frech.py",
        trigger={"typ": "zeit", "prioritaet": 50, "bedingungen": {"intervall_min": 5}},
        parameter={"ziel": str(verboten)},
        erlaubte_aktionen=["lesen"],      # datei_schreiben fehlt bewusst
        schreibpfade=[],
    )])
    reaktionskonfig_schreiben(welt["tmp"], {}, monkeypatch)
    monkeypatch.setenv("HERMES_AUTOMATIK_REGISTRY", str(reg_pfad))
    reg = registry.laden(reg_pfad, pruefen=False)

    with zustand.offen() as con:
        a = Ausloeser(regel_id="frech-regel", typ="zeit", ausgeloest_durch="Probe")
        eintrag = steuerung.ausfuehren(reg.nach_id("frech-regel"), a, con, reg.version)
    assert eintrag["ergebnis"] == "verstoss", eintrag
    assert not verboten.exists(), "die Wache hat den Schreibzugriff durchgelassen"

    attrappe = Attrappe()
    ergebnis = durchgang(attrappe, registry_pfad=reg_pfad)
    assert [r["befund"] for r in ergebnis.reaktionen] == ["grenzverletzung"]
    assert ergebnis.reaktionen[0]["gesperrt"] is True
    assert [s["regel_id"] for s in ergebnis.sperren] == ["frech-regel"]

    with zustand.offen() as con:
        assert zustand.ist_gesperrt(con, "frech-regel")

    # Und die Sperre wirkt: der naechste Lauf kommt nicht mehr zum Prozessstart.
    with zustand.offen() as con:
        a = Ausloeser(regel_id="frech-regel", typ="zeit", ausgeloest_durch="Probe 2")
        zweiter = steuerung.ausfuehren(reg.nach_id("frech-regel"), a, con, reg.version)
    assert zweiter["ergebnis"] == "uebersprungen", zweiter

    # Dieselbe Sperre wird nicht zweimal uebertragen (Marke haelt).
    nochmal = durchgang(Attrappe(), registry_pfad=reg_pfad)
    assert nochmal.sperren == []


# --- 4. Leiser Pfad: uebersprungen bleibt still ------------------------------


def test_uebersprungen_bleibt_still(welt, monkeypatch):
    """Ein uebersprungener Lauf erzeugt Log, aber keine Meldung.

    Sonst waere jede nicht gelaufene Regel eine Nachricht - genau das Rauschen,
    das die echten Meldungen unlesbar macht.
    """
    reg_pfad = registry_schreiben(welt["tmp"], [regel_dict(
        id="gesperrt-regel", modus="gesperrt",
        trigger={"typ": "zeit", "prioritaet": 50, "bedingungen": {"intervall_min": 5}},
    )])
    reaktionskonfig_schreiben(welt["tmp"], {}, monkeypatch)
    monkeypatch.setenv("HERMES_AUTOMATIK_REGISTRY", str(reg_pfad))
    reg = registry.laden(reg_pfad, pruefen=False)

    with zustand.offen() as con:
        a = Ausloeser(regel_id="gesperrt-regel", typ="zeit", ausgeloest_durch="Probe")
        eintrag = steuerung.ausfuehren(reg.nach_id("gesperrt-regel"), a, con, reg.version)
    assert eintrag["ergebnis"] == "uebersprungen"

    attrappe = Attrappe()
    ergebnis = durchgang(attrappe, registry_pfad=reg_pfad)
    assert [r["befund"] for r in ergebnis.reaktionen] == ["uebersprungen"]
    assert attrappe.namen() == ["log"], attrappe.namen()
    assert ergebnis.nachlaeufe == []


# --- 5. Probe: entscheidet alles, bewirkt nichts -----------------------------


def test_probe_bewirkt_nichts(welt, monkeypatch):
    """--probe ist echt: derselbe Weg, nur ohne Meldung, Sperre und Neustart."""
    reg_pfad = registry_schreiben(welt["tmp"], [regel_dict(
        id="frech-regel", skill="probe_frech.py",
        trigger={"typ": "zeit", "prioritaet": 50, "bedingungen": {"intervall_min": 5}},
        parameter={"ziel": str(welt["tmp"] / "verboten.txt")},
        erlaubte_aktionen=["lesen"], schreibpfade=[],
    )])
    reaktionskonfig_schreiben(welt["tmp"], {}, monkeypatch)
    monkeypatch.setenv("HERMES_AUTOMATIK_REGISTRY", str(reg_pfad))
    reg = registry.laden(reg_pfad, pruefen=False)

    with zustand.offen() as con:
        a = Ausloeser(regel_id="frech-regel", typ="zeit", ausgeloest_durch="Probe")
        steuerung.ausfuehren(reg.nach_id("frech-regel"), a, con, reg.version)

    attrappe = Attrappe()
    ergebnis = kopplung.durchgang(
        probe=True, registry_pfad=reg_pfad, pruefen=False, kanaele=attrappe.kanaele())

    assert [r["befund"] for r in ergebnis.reaktionen] == ["grenzverletzung"]
    # Entschieden ja - gemeldet nein, gesperrt nein.
    assert attrappe.namen() == ["log"], attrappe.namen()
    with zustand.offen() as con:
        assert not zustand.ist_gesperrt(con, "frech-regel")

    # Und die Probe verbraucht die Zeile nicht: der echte Durchgang danach
    # meldet sie noch. Befund des ersten Betriebslaufs (20.09.2026) - die
    # Probe schrieb ihre Marken fort, die geprueften Zeilen galten als
    # beantwortet und waeren nie gemeldet worden. Eine Probe, die Meldungen
    # verschluckt, ist schlimmer als keine Probe.
    echt = Attrappe()
    danach = durchgang(echt, registry_pfad=reg_pfad)
    assert danach.gelesen == 1, "die Probe hat die Lauf-Zeile verbraucht"
    assert [r["befund"] for r in danach.reaktionen] == ["grenzverletzung"]
    assert "telegram" in echt.namen()
    with zustand.offen() as con:
        assert zustand.ist_gesperrt(con, "frech-regel")


# --- 6. Robustheit: kaputte Log-Zeile haelt die Kopplung nicht an ------------


def test_kaputte_zeile_blockiert_nicht(welt, monkeypatch):
    """Eine unvollstaendige Lauf-Zeile wird gemeldet und uebersprungen.

    Sonst bliebe die Kopplung fuer immer an derselben Zeile stehen und alle
    spaeteren Laeufe waeren stumm - der schlimmste Ausfall fuer ein
    Meldesystem, weil er wie Ruhe aussieht.
    """
    reg_pfad = registry_schreiben(welt["tmp"], [regel_dict(id="e2e-regel")])
    reaktionskonfig_schreiben(welt["tmp"], {}, monkeypatch)
    monkeypatch.setenv("HERMES_AUTOMATIK_REGISTRY", str(reg_pfad))

    log = pfade.log_datei()
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("{kein json\n")                                   # unlesbar
        fh.write(json.dumps({"regel_id": "e2e-regel"}) + "\n")     # Pflichtfelder fehlen
        fh.write(json.dumps({
            "zeit": "2026-09-20T12:00:00+02:00", "regel_id": "e2e-regel",
            "trigger_typ": "zeit", "skill": "probe_schreiber.py", "modus": "auto",
            "ergebnis": "erfolg", "exit": 0, "aktionen_genutzt": [],
            "erlaubte_aktionen": [], "ausgabe": "ok",
        }) + "\n")

    attrappe = Attrappe()
    ergebnis = durchgang(attrappe, registry_pfad=reg_pfad)

    # Die kaputte JSON-Zeile zaehlt gar nicht erst mit, die unvollstaendige
    # wird als Fehler gemeldet - und die gute danach trotzdem beantwortet.
    assert len(ergebnis.fehler) == 1, ergebnis.fehler
    assert [r["befund"] for r in ergebnis.reaktionen] == ["erfolg"]
