"""Proben der Auto-Ausfuehrungs-Engine.

Jeder Test laeuft in einem eigenen tmp_path: eigene Basis (Log, Zustand,
Nachrichteneingang), eigene Wurzel, eigene Kanban-DB. Die Engine im Betrieb
wird dabei nicht angefasst - das ist Pflicht, weil dieselben Module sonst gegen
die echte Zustands-DB und das echte Board laufen wuerden.

Was hier NICHT passiert: kein Test startet einen Agentenlauf (skill_art=skill).
Die Engine sperrt den Weg ohne ausdrueckliche Freigabe, und genau das wird
geprueft - ein Test, der ihn oeffnet, wuerde die Grenze wegtesten, die er
beweisen soll.

Lauf:  python -m pytest tests/test_engine.py -q     (aus dem Workspace)
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest
import yaml

WORKSPACE = Path(__file__).resolve().parent.parent
PROBEN = WORKSPACE / "tests" / "proben"
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from engine import lauf, protokoll, registry, steuerung, zustand  # noqa: E402
from engine.quellen import Ausloeser, board, sammeln  # noqa: E402


# --- Gerüst ---------------------------------------------------------------

@pytest.fixture()
def umgebung(tmp_path, monkeypatch):
    """Eigene Welt je Test: Basis, Wurzel, Skriptpfade, leere Kanban-DB."""
    basis = tmp_path / "arbeit"
    wurzel = tmp_path / "wurzel"
    wurzel.mkdir()
    monkeypatch.setenv("HERMES_AUTOMATIK_BASIS", str(basis))
    monkeypatch.setenv("HERMES_AUTOMATIK_WURZEL", str(wurzel))
    monkeypatch.setenv("HERMES_AUTOMATIK_SKRIPTPFADE", str(PROBEN))
    monkeypatch.setenv("HERMES_AUTOMATIK_KANBAN_DB", str(tmp_path / "kanban.db"))
    monkeypatch.delenv("HERMES_AUTOMATIK_SKILL_START", raising=False)
    return {"tmp": tmp_path, "basis": basis, "wurzel": wurzel}


def regel_dict(**abweichung) -> dict:
    """Vollstaendige, gueltige Regel; einzelne Felder ueberschreibbar."""
    regel = {
        "id": "probe-regel",
        "skill": "probe_schreiber.py",
        "skill_art": "skript",
        "trigger": {"typ": "zeit", "prioritaet": 50,
                    "bedingungen": {"intervall_min": 5}},
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


def registry_schreiben(tmp_path, regeln) -> Path:
    daten = {"registry_version": "1.0.0", "defaults": {"modus": "dry_run"},
             "regeln": regeln}
    p = tmp_path / "probe_registry.yaml"
    p.write_text(yaml.safe_dump(daten, allow_unicode=True), encoding="utf-8")
    return p


def laden(pfad):
    """Ohne Validator laden: die Proben-Skripte liegen bewusst ausserhalb der
    Pfade, die der Spez-Validator kennt. Der Validator selbst wird in
    test_unbekannter_skill_wird_abgelehnt geprueft."""
    return registry.laden(pfad, pruefen=False)


def tick(reg):
    """Ein Engine-Durchlauf wie 'python -m engine tick'."""
    eintraege = []
    with zustand.offen() as con:
        for a in sammeln(reg, con):
            r = reg.nach_id(a.regel_id)
            eintraege.append(steuerung.ausfuehren(r, a, con, reg.version))
    return eintraege


def von_hand(reg, regel_id, typ="zeit"):
    r = reg.nach_id(regel_id)
    a = Ausloeser(regel_id=r.id, typ=typ, ausgeloest_durch="Probe")
    with zustand.offen() as con:
        return steuerung.ausfuehren(r, a, con, reg.version)


# --- Trigger: zeit --------------------------------------------------------

def test_zeit_trigger_loest_skript_aus(umgebung, tmp_path):
    ziel = tmp_path / "zeit_ergebnis.json"
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="zeit-probe",
        parameter={"ziel": str(ziel), "text": "zeit"},
        schreibpfade=[str(tmp_path)],
    )])
    reg = laden(reg_pfad)

    # Erster Tick nimmt nur den Takt auf - das ist Absicht, sonst feuert jede
    # neue Intervall-Regel sofort beim Einbau.
    assert tick(reg) == []
    assert not ziel.exists()

    # Marke zurueckdatieren = 5 Minuten sind vergangen.
    with zustand.offen() as con:
        zustand.marke_setzen(con, "quelle:zeit:zeit-probe", int(time.time()) - 400)

    eintraege = tick(reg)
    assert [e["ergebnis"] for e in eintraege] == ["erfolg"]
    assert eintraege[0]["trigger_typ"] == "zeit"
    assert json.loads(ziel.read_text(encoding="utf-8"))["text"] == "zeit"


def test_cron_ausdruck_trifft_minute():
    from engine.quellen import zeit as zeitquelle

    t = time.localtime(time.mktime((2026, 9, 21, 9, 30, 0, 0, 0, -1)))  # Montag
    assert zeitquelle.cron_passt("30 9 * * 1", t)
    assert not zeitquelle.cron_passt("31 9 * * 1", t)
    assert zeitquelle.cron_passt("*/15 * * * *", t)


# --- Trigger: datei -------------------------------------------------------

def test_datei_trigger_loest_bei_neuer_datei_aus(umgebung, tmp_path):
    wurzel = umgebung["wurzel"]
    (wurzel / "skills").mkdir()
    ziel = tmp_path / "datei_ergebnis.json"

    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="datei-probe",
        trigger={"typ": "datei", "prioritaet": 20,
                 "bedingungen": {"pfad_muster": ["skills/**/SKILL.md"],
                                 "aktion": "created"}},
        parameter={"ziel": str(ziel), "text": "datei"},
        schreibpfade=[str(tmp_path)],
    )])
    reg = laden(reg_pfad)

    assert tick(reg) == []  # Bestand aufnehmen

    neu = wurzel / "skills" / "frisch"
    neu.mkdir()
    (neu / "SKILL.md").write_text("probe", encoding="utf-8")

    eintraege = tick(reg)
    assert [e["ergebnis"] for e in eintraege] == ["erfolg"]
    assert eintraege[0]["trigger_typ"] == "datei"
    assert "1 Datei(en) created" in eintraege[0]["ausgeloest_durch"]
    assert ziel.exists()

    # Ohne weitere Aenderung passiert nichts mehr.
    assert tick(reg) == []


def test_datei_trigger_entprellt(umgebung, tmp_path):
    wurzel = umgebung["wurzel"]
    (wurzel / "skills").mkdir()
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="datei-entprellt",
        trigger={"typ": "datei", "prioritaet": 20,
                 "bedingungen": {"pfad_muster": ["skills/*.md"],
                                 "mindestabstand_s": 600}},
        parameter={"ziel": str(tmp_path / "e.json")},
        schreibpfade=[str(tmp_path)],
    )])
    reg = laden(reg_pfad)
    tick(reg)

    (wurzel / "skills" / "a.md").write_text("1", encoding="utf-8")
    assert len(tick(reg)) == 1
    (wurzel / "skills" / "b.md").write_text("2", encoding="utf-8")
    assert tick(reg) == []  # innerhalb mindestabstand_s: gesehen, nicht gemeldet


# --- Trigger: board_event -------------------------------------------------

def _board_db(pfad: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(pfad))
    con.executescript(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, assignee TEXT,"
        " status TEXT);"
        "CREATE TABLE task_events (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " task_id TEXT, run_id INTEGER, kind TEXT, payload TEXT,"
        " created_at INTEGER);")
    con.commit()
    return con


def test_board_trigger_meldet_blockierte_karte(umgebung, tmp_path):
    kdb = tmp_path / "kanban.db"
    con = _board_db(kdb)
    con.execute("INSERT INTO tasks VALUES ('t_1','Testkarte','claude-code','running')")
    con.execute("INSERT INTO task_events (task_id,kind,payload,created_at)"
                " VALUES ('t_1','heartbeat',NULL,?)", (int(time.time()),))
    con.commit()

    ziel = tmp_path / "board_ergebnis.json"
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="board-probe",
        trigger={"typ": "board_event", "prioritaet": 0,
                 "bedingungen": {"ereignis": "blocked", "assignee": "claude-code"}},
        parameter={"ziel": str(ziel), "text": "board"},
        schreibpfade=[str(tmp_path)],
    )])
    reg = laden(reg_pfad)

    assert tick(reg) == []  # erster Blick setzt nur die Marke

    con.execute("INSERT INTO task_events (task_id,kind,payload,created_at)"
                " VALUES ('t_1','blocked',?,?)",
                (json.dumps({"reason": "brauche Zugang"}), int(time.time())))
    con.commit()

    eintraege = tick(reg)
    assert [e["ergebnis"] for e in eintraege] == ["erfolg"]
    assert "blocked t_1" in eintraege[0]["ausgeloest_durch"]

    # Der Trigger-Wert (Blockgrund) erreicht den Lauf.
    trigger = json.loads(json.loads(ziel.read_text(encoding="utf-8"))["trigger"])
    assert trigger["reason"] == "brauche Zugang"
    assert trigger["titel"] == "Testkarte"

    assert tick(reg) == []  # dasselbe Ereignis feuert nicht zweimal
    con.close()


def test_board_trigger_filtert_assignee(umgebung, tmp_path):
    kdb = tmp_path / "kanban.db"
    con = _board_db(kdb)
    con.execute("INSERT INTO tasks VALUES ('t_2','Fremd','jemand-anders','running')")
    con.execute("INSERT INTO task_events (task_id,kind,created_at)"
                " VALUES ('t_2','heartbeat',?)", (int(time.time()),))
    con.commit()

    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="board-filter",
        trigger={"typ": "board_event", "prioritaet": 0,
                 "bedingungen": {"ereignis": "blocked", "assignee": "claude-code"}},
        parameter={"ziel": str(tmp_path / "x.json")},
        schreibpfade=[str(tmp_path)],
    )])
    reg = laden(reg_pfad)
    tick(reg)

    con.execute("INSERT INTO task_events (task_id,kind,created_at)"
                " VALUES ('t_2','blocked',?)", (int(time.time()),))
    con.commit()
    assert tick(reg) == []
    con.close()


def test_board_arten_bilden_spezifikation_ab():
    # Die Spezifikation kennt genau diese sechs Ereignisse.
    assert set(board.ARTEN.values()) == {
        "created", "claimed", "blocked", "review", "done", "failed"}


# --- Trigger: nachricht ---------------------------------------------------

def test_nachricht_trigger_mit_absenderfilter(umgebung, tmp_path):
    from engine import pfade

    ziel = tmp_path / "nachricht_ergebnis.json"
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="nachricht-probe",
        trigger={"typ": "nachricht", "prioritaet": 30,
                 "bedingungen": {"kanal": "telegram",
                                 "muster": ["^stand melden$"],
                                 "nur_von": ["4711"]}},
        parameter={"ziel": str(ziel), "text": "nachricht"},
        schreibpfade=[str(tmp_path)],
    )])
    reg = laden(reg_pfad)
    eingang = pfade.nachrichten_eingang()

    # Falscher Absender: kein Trigger, Datei trotzdem weggeraeumt.
    (eingang / "a.json").write_text(json.dumps(
        {"kanal": "telegram", "text": "stand melden", "von": "9999"}),
        encoding="utf-8")
    assert tick(reg) == []
    assert not (eingang / "a.json").exists()

    (eingang / "b.json").write_text(json.dumps(
        {"kanal": "telegram", "text": "Stand melden", "von": "4711"}),
        encoding="utf-8")
    eintraege = tick(reg)
    assert [e["ergebnis"] for e in eintraege] == ["erfolg"]
    assert ziel.exists()
    assert not (eingang / "b.json").exists()


# --- Trigger: skill_ergebnis (Verkettung) --------------------------------

def test_verkettung_nach_erfolg(umgebung, tmp_path):
    erst = tmp_path / "kette_a.json"
    zweit = tmp_path / "kette_b.json"
    reg_pfad = registry_schreiben(tmp_path, [
        regel_dict(id="kette-a", parameter={"ziel": str(erst), "text": "a"},
                   schreibpfade=[str(tmp_path)]),
        regel_dict(id="kette-b",
                   trigger={"typ": "skill_ergebnis", "prioritaet": 60,
                            "bedingungen": {"regel": "kette-a", "status": "erfolg"}},
                   parameter={"ziel": str(zweit), "text": "b"},
                   schreibpfade=[str(tmp_path)]),
    ])
    reg = laden(reg_pfad)

    assert von_hand(reg, "kette-a")["ergebnis"] == "erfolg"
    assert erst.exists() and not zweit.exists()

    eintraege = tick(reg)
    assert [e["regel_id"] for e in eintraege] == ["kette-b"]
    assert eintraege[0]["ergebnis"] == "erfolg"
    assert zweit.exists()

    assert tick(reg) == []  # ein Vorgaengerlauf kettet genau einmal


def test_verkettung_ignoriert_fehlschlag(umgebung, tmp_path):
    reg_pfad = registry_schreiben(tmp_path, [
        regel_dict(id="kette-x",
                   parameter={"ziel": str(tmp_path / "x.json"), "exit": 3},
                   schreibpfade=[str(tmp_path)]),
        regel_dict(id="kette-y",
                   trigger={"typ": "skill_ergebnis", "prioritaet": 60,
                            "bedingungen": {"regel": "kette-x", "status": "erfolg"}},
                   parameter={"ziel": str(tmp_path / "y.json")},
                   schreibpfade=[str(tmp_path)]),
    ])
    reg = laden(reg_pfad)
    assert von_hand(reg, "kette-x")["ergebnis"] == "fehler"
    assert tick(reg) == []
    assert not (tmp_path / "y.json").exists()


# --- Sicherheit -----------------------------------------------------------

def test_wache_blockt_schreiben_ausserhalb(umgebung, tmp_path):
    verboten = tmp_path / "verboten.txt"
    erlaubt = tmp_path / "erlaubt"
    erlaubt.mkdir()

    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="frech",
        skill="probe_frech.py",
        parameter={"ziel": str(verboten)},
        schreibpfade=[str(erlaubt)],
    )])
    reg = laden(reg_pfad)

    eintrag = von_hand(reg, "frech")
    assert eintrag["ergebnis"] == "verstoss"
    assert eintrag["exit"] == 97
    assert not verboten.exists()
    assert "datei_schreiben" in (eintrag.get("abbruchgrund") or "")


def test_unerlaubte_aktion_blockt_auch_bei_erlaubtem_pfad(umgebung, tmp_path):
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="nur-lesen-regel",
        erlaubte_aktionen=["lesen"],          # kein datei_schreiben
        parameter={"ziel": str(tmp_path / "trotzdem.json")},
        schreibpfade=[str(tmp_path)],
    )])
    reg = laden(reg_pfad)
    eintrag = von_hand(reg, "nur-lesen-regel")
    assert eintrag["ergebnis"] == "verstoss"
    assert not (tmp_path / "trotzdem.json").exists()


def test_unbekannter_skill_wird_abgelehnt(umgebung, tmp_path):
    """S1 ueber den echten Validator der Spezifikation."""
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="gibt-es-nicht",
        skill="brainfiles/existiert-sicher-nicht",
        skill_art="skill",
        modus="dry_run",
    )])
    with pytest.raises(registry.RegistryFehler) as fehler:
        registry.laden(reg_pfad, pruefen=True)
    assert any("S1" in d for d in fehler.value.details)


def test_registry_version_wird_geprueft(umgebung, tmp_path):
    p = tmp_path / "zukunft.yaml"
    p.write_text(yaml.safe_dump(
        {"registry_version": "2.0.0", "regeln": []}), encoding="utf-8")
    with pytest.raises(registry.RegistryFehler):
        registry.laden(p, pruefen=False)


def test_gesperrte_regel_laeuft_nicht(umgebung, tmp_path):
    ziel = tmp_path / "nie.json"
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="gesperrt-probe", modus="gesperrt",
        parameter={"ziel": str(ziel)}, schreibpfade=[str(tmp_path)])])
    reg = laden(reg_pfad)
    eintrag = von_hand(reg, "gesperrt-probe")
    assert eintrag["ergebnis"] == "uebersprungen"
    assert not ziel.exists()


def test_rate_limit_greift(umgebung, tmp_path):
    ziel = tmp_path / "rate.json"
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="rate-probe",
        parameter={"ziel": str(ziel)},
        schreibpfade=[str(tmp_path)],
        rate_limit={"max_laeufe": 1, "fenster_s": 3600})])
    reg = laden(reg_pfad)

    assert von_hand(reg, "rate-probe")["ergebnis"] == "erfolg"
    zweiter = von_hand(reg, "rate-probe")
    assert zweiter["ergebnis"] == "uebersprungen"
    assert "Rate-Limit" in zweiter["abbruchgrund"]


def test_cooldown_greift(umgebung, tmp_path):
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="cooldown-probe",
        parameter={"ziel": str(tmp_path / "c.json")},
        schreibpfade=[str(tmp_path)],
        rate_limit={"max_laeufe": 10, "fenster_s": 3600, "cooldown_s": 900})])
    reg = laden(reg_pfad)
    assert von_hand(reg, "cooldown-probe")["ergebnis"] == "erfolg"
    assert "Cooldown" in von_hand(reg, "cooldown-probe")["abbruchgrund"]


def test_fehlerstreak_sperrt_regel(umgebung, tmp_path):
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="streak-probe",
        parameter={"ziel": str(tmp_path / "s.json"), "exit": 5},
        schreibpfade=[str(tmp_path)],
        abbruch={"bei_fehlerstreak": 2})])
    reg = laden(reg_pfad)

    assert von_hand(reg, "streak-probe")["ergebnis"] == "fehler"
    assert von_hand(reg, "streak-probe")["ergebnis"] == "fehler"
    dritter = von_hand(reg, "streak-probe")
    assert dritter["ergebnis"] == "uebersprungen"
    assert "Dauersperre" in dritter["abbruchgrund"]

    with zustand.offen() as con:
        zustand.entsperren(con, "streak-probe")
    assert von_hand(reg, "streak-probe")["ergebnis"] == "fehler"


def test_bestaetigung_wartet_und_laeuft_nach_ja(umgebung, tmp_path):
    ziel = tmp_path / "bestaetigt.json"
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="bestaetigung-probe", modus="bestaetigung",
        parameter={"ziel": str(ziel)}, schreibpfade=[str(tmp_path)])])
    reg = laden(reg_pfad)

    erster = von_hand(reg, "bestaetigung-probe")
    assert erster["ergebnis"] == "bestaetigung_offen"
    assert not ziel.exists()

    with zustand.offen() as con:
        con.execute("UPDATE bestaetigungen SET antwort='ja' WHERE regel_id=?",
                    ("bestaetigung-probe",))
    assert von_hand(reg, "bestaetigung-probe")["ergebnis"] == "erfolg"
    assert ziel.exists()


def test_bestaetigung_verfallen_gilt_als_nein(umgebung, tmp_path):
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="verfall-probe", modus="bestaetigung", timeout_s=5,
        parameter={"ziel": str(tmp_path / "v.json")}, schreibpfade=[str(tmp_path)])])
    reg = laden(reg_pfad)
    assert von_hand(reg, "verfall-probe")["ergebnis"] == "bestaetigung_offen"

    with zustand.offen() as con:
        con.execute("UPDATE bestaetigungen SET verfall_unix=? WHERE regel_id=?",
                    (int(time.time()) - 10, "verfall-probe"))
    zweiter = von_hand(reg, "verfall-probe")
    assert zweiter["ergebnis"] == "abgelehnt"
    assert not (tmp_path / "v.json").exists()


def test_dry_run_startet_nichts(umgebung, tmp_path):
    ziel = tmp_path / "dry.json"
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="dry-probe", modus="dry_run",
        parameter={"ziel": str(ziel)}, schreibpfade=[str(tmp_path)])])
    reg = laden(reg_pfad)
    eintrag = von_hand(reg, "dry-probe")
    assert eintrag["ergebnis"] == "dry_run"
    assert "wuerde starten" in eintrag["abbruchgrund"]
    assert not ziel.exists()


def test_timeout_wird_erzwungen(umgebung, tmp_path):
    schlaefer = PROBEN / "probe_schlaefer.py"
    schlaefer.write_text(
        "import time, sys\ntime.sleep(30)\nsys.exit(0)\n", encoding="utf-8")
    try:
        reg_pfad = registry_schreiben(tmp_path, [regel_dict(
            id="timeout-probe", skill="probe_schlaefer.py", timeout_s=5,
            erlaubte_aktionen=["lesen"], schreibpfade=[str(tmp_path)])])
        reg = laden(reg_pfad)
        start = time.time()
        eintrag = von_hand(reg, "timeout-probe")
        assert eintrag["ergebnis"] == "timeout"
        assert eintrag["exit"] == 124
        assert time.time() - start < 25
    finally:
        schlaefer.unlink(missing_ok=True)


def test_skill_art_skill_ist_ohne_freigabe_gesperrt(umgebung, tmp_path):
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="agent-probe", skill="chat", skill_art="skill",
        erlaubte_aktionen=["lesen", "nachricht_senden"])])
    reg = laden(reg_pfad)
    eintrag = von_hand(reg, "agent-probe")
    assert eintrag["ergebnis"] == "uebersprungen"
    assert "HERMES_AUTOMATIK_SKILL_START" in eintrag["abbruchgrund"]


def test_skript_ausserhalb_der_skriptpfade_wird_nicht_gefunden(umgebung, tmp_path):
    fremd = tmp_path / "fremd.py"
    fremd.write_text("print('fremd')\n", encoding="utf-8")
    assert lauf.skript_finden(str(fremd)) is None


# --- Log und Reihenfolge --------------------------------------------------

def test_log_enthaelt_pflichtfelder(umgebung, tmp_path):
    reg_pfad = registry_schreiben(tmp_path, [regel_dict(
        id="log-probe",
        parameter={"ziel": str(tmp_path / "l.json")},
        schreibpfade=[str(tmp_path)])])
    reg = laden(reg_pfad)
    von_hand(reg, "log-probe")

    zeilen = protokoll.zeilen_lesen()
    assert len(zeilen) == 1
    z = zeilen[0]
    for feld in ("zeit", "regel_id", "trigger_typ", "ausgeloest_durch", "skill",
                 "modus", "dauer_ms", "exit", "aktionen_genutzt", "ergebnis"):
        assert feld in z, feld
    assert z["aktionen_genutzt"] == ["datei_schreiben"]
    assert z["registry_version"] == "1.0.0"


def test_prioritaet_bestimmt_reihenfolge(umgebung, tmp_path):
    wurzel = umgebung["wurzel"]
    (wurzel / "skills").mkdir()
    gemeinsam = {"typ": "datei", "bedingungen": {"pfad_muster": ["skills/*.md"]}}

    reg_pfad = registry_schreiben(tmp_path, [
        regel_dict(id="spaet", trigger=dict(gemeinsam, prioritaet=80),
                   parameter={"ziel": str(tmp_path / "spaet.json")},
                   schreibpfade=[str(tmp_path)]),
        regel_dict(id="frueh", trigger=dict(gemeinsam, prioritaet=5),
                   parameter={"ziel": str(tmp_path / "frueh.json")},
                   schreibpfade=[str(tmp_path)]),
    ])
    reg = laden(reg_pfad)
    tick(reg)
    (wurzel / "skills" / "neu.md").write_text("x", encoding="utf-8")

    eintraege = tick(reg)
    assert [e["regel_id"] for e in eintraege] == ["frueh", "spaet"]


def test_bool_parameter_werden_zu_flaggen():
    """store_true-Semantik: true wird Flagge, false faellt weg.

    Die echte Regel 'inventar-nach-skill-aenderung' uebergibt print: false an
    ein Skript, das nur --print kennt. Eine erfundene Gegenflagge wuerde dort
    argparse zum Abbruch bringen.
    """
    from engine.lauf import _parameter_argumente

    assert _parameter_argumente({"print": False}) == []
    assert _parameter_argumente({"print": True}) == ["--print"]
    assert _parameter_argumente({"nur_pruefen": True}) == ["--nur-pruefen"]
    assert _parameter_argumente({"ziel": "C:/x"}) == ["--ziel", "C:/x"]


def test_echte_beispiel_registry_laedt_mit_validator():
    """Die mitgelieferte Registry der Spezifikation muss durch den Validator
    gehen - sonst prueft die Engine gegen eine Fiktion."""
    reg = registry.laden(WORKSPACE / "spez" / "registry.example.yaml", pruefen=True)
    assert len(reg.regeln) == 6
    assert {r.trigger_typ for r in reg.regeln} == {
        "datei", "zeit", "board_event", "skill_ergebnis", "nachricht"}
