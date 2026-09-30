"""Testlauf der Reaktionsschicht - ohne echte Nachricht, ohne echtes Board.

Die Kanaele werden durch eine Attrappe ersetzt; geprueft wird, was die Schicht
ENTSCHEIDET. Die echten Kanaele werden separat belegt (siehe ende_zu_ende.py),
denn ein Test, der bei jedem Lauf eine Telegram-Nachricht schickt, wird nicht
mehr ausgefuehrt.

Aufruf:  python test_reaktion.py
Erwartet: 'alle Tests gruen', Exitcode 0.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import reaktion  # noqa: E402
from kanaele import Kanaele  # noqa: E402

BASIS_LAUF = {
    "zeit": "2026-09-20T05:00:00+02:00",
    "regel_id": "inventar-nach-skill-aenderung",
    "trigger_typ": "datei",
    "ausgeloest_durch": "skills/brainfiles/mcp-sync/SKILL.md",
    "skill": "scripts/inventar.py",
    "modus": "auto",
    "dauer_ms": 1234,
    "exit": 0,
    "aktionen_genutzt": ["lesen", "bericht_schreiben"],
    "erlaubte_aktionen": ["lesen", "bericht_schreiben"],
    "abbruchgrund": None,
    "ausgabe": "52 Skills; none=20, local=6",
    "task_id": None,
}


class Aufzeichnung:
    """Attrappe: merkt sich jeden Kanalaufruf, tut nichts."""

    def __init__(self) -> None:
        self.rufe: list[tuple[str, tuple]] = []

    def _melder(self, name: str):
        def melden(*argumente):
            self.rufe.append((name, argumente))
            return True, f"attrappe/{name}"

        return melden

    def buendel(self) -> Kanaele:
        return Kanaele(
            log=self._melder("log"),
            board_kommentar=self._melder("board"),
            board_blocken=self._melder("board_block"),
            telegram=self._melder("telegram"),
            memory=self._melder("memory"),
        )

    def namen(self) -> list[str]:
        return [name for name, _ in self.rufe]


def _lauf(**aenderungen):
    daten = dict(BASIS_LAUF)
    daten.update(aenderungen)
    return reaktion.Ergebnis.aus_dict(daten)


def _reagieren(ergebnis, konfig, ordner: Path, probe: bool = False):
    aufzeichnung = Aufzeichnung()
    plan, belege = reaktion.reagieren(
        ergebnis,
        konfig,
        kanaele=aufzeichnung.buendel(),
        ablage=reaktion.Ablage(ordner),
        probe=probe,
    )
    return plan, belege, aufzeichnung


def pruefe(bedingung: bool, was: str) -> None:
    if not bedingung:
        raise AssertionError(was)


# --- Test 1: Erfolg erzeugt Memory-Eintrag, wiederholter Erfolg wird still ---


def test_erfolg(ordner: Path, konfig) -> str:
    plan, _, auf1 = _reagieren(_lauf(), konfig, ordner)
    pruefe(plan.befund == "erfolg", f"Befund erwartet erfolg, war {plan.befund}")
    pruefe("memory" in auf1.namen(), "Erfolg muss in den Wissensspeicher")
    pruefe("telegram" in auf1.namen(), "erste Ausgabe ist neu -> Meldung erwartet")

    # Zweiter Lauf, gleiche Ausgabe: melde_erfolg=bei_aenderung haelt still.
    _, _, auf2 = _reagieren(_lauf(zeit="2026-09-20T06:00:00+02:00"), konfig, ordner)
    pruefe("telegram" not in auf2.namen(), "gleiche Ausgabe darf nicht erneut melden")
    pruefe("memory" in auf2.namen(), "gemerkt wird trotzdem")

    # Dritter Lauf, andere Ausgabe: meldet wieder.
    _, _, auf3 = _reagieren(
        _lauf(zeit="2026-09-20T07:00:00+02:00", ausgabe="53 Skills; none=21"), konfig, ordner
    )
    pruefe("telegram" in auf3.namen(), "geaenderte Ausgabe muss melden")
    return "Erfolg: Memory-Eintrag immer, Meldung nur bei Aenderung"


# --- Test 2: Fehler -> Wiederholung -> Eskalation ---------------------------


def test_fehler_eskalation(ordner: Path, konfig) -> str:
    fehlerlauf = _lauf(
        exit=3, ausgabe="Traceback: PermissionError", abbruchgrund="exit!=0"
    )
    plan1, belege1, auf1 = _reagieren(fehlerlauf, konfig, ordner)
    pruefe(plan1.befund == "fehler", f"Befund erwartet fehler, war {plan1.befund}")
    pruefe(plan1.nachlauf_in_s == 300, f"Wiederholung nach 300s erwartet, war {plan1.nachlauf_in_s}")
    pruefe(plan1.versuch == 1, "erster Wiederholungsversuch")
    pruefe("nachlauf" in belege1, "Nachlauf-Auftrag muss geschrieben werden")

    # Zweiter Fehler: Wiederholungen erschoepft (wiederholungen: 1) -> melden.
    plan2, _, auf2 = _reagieren(fehlerlauf, konfig, ordner)
    pruefe(plan2.nachlauf_in_s is None, "keine zweite Wiederholung bei wiederholungen=1")
    pruefe("telegram" in auf2.namen(), "erschoepfte Wiederholung muss melden")
    pruefe("Fehler in Folge: 2" in plan2.zusammenfassung, plan2.zusammenfassung)
    return "Fehler: 1x vorgemerkt, dann Eskalation mit Fehlerzaehler"


# --- Test 3: danach=board_blocken blockt den Task ---------------------------


def test_board_blocken(ordner: Path, konfig) -> str:
    lauf = _lauf(
        regel_id="blocked-task-aufbereiten",
        trigger_typ="board_event",
        skill="brainfiles/mcp-sync",
        exit=1,
        task_id="t_probe123",
        ausgabe="Skill brach ab",
        abbruchgrund="exit!=0",
    )
    letzter_plan = None
    for _ in range(3):  # wiederholungen: 2, danach board_blocken
        letzter_plan, _, aufzeichnung = _reagieren(lauf, konfig, ordner)
    pruefe(letzter_plan is not None, "kein Plan")
    pruefe(letzter_plan.board_block is not None, "nach 2 Versuchen muss geblockt werden")
    pruefe("board_block" in aufzeichnung.namen(), "board_blocken-Kanal muss gerufen werden")
    pruefe("board" in aufzeichnung.namen(), "Board-Kommentar erwartet")

    # Ohne task_id darf nicht geblockt werden, sondern nur gemeldet.
    ohne = _lauf(
        regel_id="blocked-task-aufbereiten", exit=1, task_id=None, abbruchgrund="exit!=0"
    )
    plan_ohne = None
    for _ in range(3):
        plan_ohne, _, _ = _reagieren(ohne, konfig, ordner)
    pruefe(plan_ohne.board_block is None, "ohne task_id kein Block")
    pruefe(
        any("keine task_id" in g for g in plan_ohne.begruendung),
        f"Begruendung fehlt: {plan_ohne.begruendung}",
    )
    return "Eskalation board_blocken: blockt mit task_id, meldet ohne"


# --- Test 4: Grenzverletzung sperrt sofort, ohne Wiederholung ---------------


def test_grenzverletzung(ordner: Path, konfig) -> str:
    lauf = _lauf(
        regel_id="inventar-nach-skill-aenderung",
        exit=0,
        aktionen_genutzt=["lesen", "bericht_schreiben", "git_push"],
        erlaubte_aktionen=["lesen", "bericht_schreiben"],
        task_id="t_probe123",
    )
    plan, belege, aufzeichnung = _reagieren(lauf, konfig, ordner)
    pruefe(plan.befund == "grenzverletzung", f"Befund war {plan.befund}")
    pruefe(plan.nachlauf_in_s is None, "Grenzverletzung darf nie wiederholt werden")
    pruefe(plan.regel_sperren is not None, "Grenzverletzung muss die Regel sperren")
    pruefe("git_push" in plan.zusammenfassung, plan.zusammenfassung)
    pruefe("telegram" in aufzeichnung.namen(), "Grenzverletzung muss immer melden")
    sperren = json.loads((ordner / "sperren.json").read_text(encoding="utf-8"))
    pruefe("inventar-nach-skill-aenderung" in sperren, "Sperrliste nicht geschrieben")
    return "Grenzverletzung: sofort gesperrt, gemeldet, nie wiederholt"


# --- Test 5: dry_run und --probe wirken nicht -------------------------------


def test_stille_faelle(ordner: Path, konfig) -> str:
    plan, _, auf1 = _reagieren(_lauf(modus="dry_run"), konfig, ordner)
    pruefe(plan.befund == "probelauf", f"Befund war {plan.befund}")
    pruefe(auf1.namen() == ["log"], f"dry_run darf nur loggen, war {auf1.namen()}")

    plan2, _, auf2 = _reagieren(
        _lauf(exit=9, abbruchgrund="exit!=0"), konfig, ordner, probe=True
    )
    pruefe(plan2.befund == "fehler", "Probe muss den Fehler trotzdem erkennen")
    pruefe(auf2.namen() == ["log"], f"--probe darf nur loggen, war {auf2.namen()}")
    pruefe(not (ordner / "nachlauf.jsonl").exists(), "--probe darf keinen Nachlauf schreiben")
    return "dry_run und --probe: entschieden, nichts bewirkt"


# --- Test 6: unvollstaendige Lauf-Zeile faellt auf ------------------------


def test_unvollstaendig(ordner: Path, konfig) -> str:
    kaputt = dict(BASIS_LAUF)
    del kaputt["exit"]
    try:
        reaktion.Ergebnis.aus_dict(kaputt)
    except ValueError as fehler:
        pruefe("exit" in str(fehler), f"Meldung nennt das Feld nicht: {fehler}")
        return "Unvollstaendige Lauf-Zeile: abgelehnt mit Feldnamen"
    raise AssertionError("fehlendes Pflichtfeld wurde nicht abgelehnt")


# --- Test 7: Konfigurationspruefung findet Unsinn ---------------------------


def test_konfig_pruefung(ordner: Path, konfig) -> str:
    pruefe(reaktion.konfig_pruefen(konfig) == [], "gute Konfiguration wurde beanstandet")
    schlecht = {
        "konfig_version": "1.0.0",
        "defaults": {"kanal": "rauchzeichen", "melde_erfolg": "vielleicht"},
        "regeln": {"x": {"eskalation": {"danach": "abschalten", "wiederholungen": 9}}},
    }
    meldungen = reaktion.konfig_pruefen(schlecht)
    pruefe(len(meldungen) == 4, f"4 Meldungen erwartet, waren {len(meldungen)}: {meldungen}")
    return f"Konfigpruefung: 4 Verstoesse gefunden ({len(meldungen)} Meldungen)"


# --- Test 8: echte Engine-Zeile (uebersprungen, exit=null) ------------------


def test_engine_uebersprungen(ordner: Path, konfig) -> str:
    """Regression: die Engine schreibt bei uebersprungenen Laeufen exit=null.

    Vor diesem Test brach reaktion.py hier mit TypeError ab (int(None)) - die
    Schicht haette beim ersten Rate-Limit-Treffer im Betrieb die Arbeit
    eingestellt. Die Lauf-Zeile unten stammt wortgleich aus
    engine/protokoll.py::eintrag_bauen (t_9f7db046).
    """
    engine_zeile = {
        "zeit": "2026-09-20T07:14:58+0200",
        "zeit_unix": 1789881298,
        "lauf_id": "inventar-nach-skill-aenderung-1789881298147-69328",
        "regel_id": "inventar-nach-skill-aenderung",
        "trigger_typ": "datei",
        "ausgeloest_durch": "skills/brainfiles/mcp-sync/SKILL.md",
        "skill": "scripts/inventar.py",
        "modus": "auto",
        "ergebnis": "uebersprungen",
        "dauer_ms": 0,
        "exit": None,
        "aktionen_genutzt": [],
        "abbruchgrund": "rate_limit",
        "ausgabe": "",
        "ausgabe_gekuerzt": False,
        "registry_version": "1.0.0",
        "versuch": 1,
    }
    ergebnis = reaktion.Ergebnis.aus_dict(engine_zeile)
    pruefe(ergebnis.exit is None, "exit=null muss None bleiben, nicht 0 werden")
    pruefe(
        ergebnis.unbekannte_felder == (),
        f"Engine-Felder gelten als Drift: {ergebnis.unbekannte_felder}",
    )
    plan, _, auf = _reagieren(ergebnis, konfig, ordner)
    pruefe(plan.befund == "uebersprungen", f"Befund war {plan.befund}")
    pruefe(auf.namen() == ["log"], f"uebersprungen darf nur loggen, war {auf.namen()}")
    pruefe(plan.nachlauf_in_s is None, "uebersprungen darf keine Wiederholung vormerken")
    zustand = json.loads((ordner / "zustand.json").read_text(encoding="utf-8"))
    eintrag = zustand["inventar-nach-skill-aenderung"]
    pruefe(eintrag.get("fehlerstreak", 0) == 0, f"Fehlerzaehler angefasst: {eintrag}")
    return "Engine-Zeile uebersprungen: exit=null akzeptiert, still, kein Zaehler"


# --- Test 9: bestaetigung_offen meldet, ohne zu eskalieren ------------------


def test_engine_bestaetigung(ordner: Path, konfig) -> str:
    ergebnis = _lauf(
        regel_id="blocked-task-aufbereiten",
        modus="bestaetigung",
        exit=None,
        ergebnis="bestaetigung_offen",
        abbruchgrund="wartet auf Freigabe",
        task_id="t_probe",
    )
    plan, _, auf = _reagieren(ergebnis, konfig, ordner)
    pruefe(plan.befund == "wartet", f"Befund war {plan.befund}")
    pruefe(plan.nachlauf_in_s is None, "Warten darf keine Wiederholung ausloesen")
    pruefe(not plan.board_block, "Warten darf keinen Task blocken")
    pruefe("board" in auf.namen(), f"Wartemeldung muss sichtbar sein: {auf.namen()}")
    zustand = json.loads((ordner / "zustand.json").read_text(encoding="utf-8"))
    pruefe(
        zustand["blocked-task-aufbereiten"].get("fehlerstreak", 0) == 0,
        "Warten darf den Fehlerzaehler nicht erhoehen",
    )
    return "bestaetigung_offen: gemeldet, nicht eskaliert, Zaehler unberuehrt"


# --- Test 10: unbekanntes Engine-Vokabular gilt als Fehler ------------------


def test_engine_drift(ordner: Path, konfig) -> str:
    """Ein neues ergebnis-Wort darf nicht stillschweigend als Erfolg durchgehen."""
    ergebnis = _lauf(exit=0, ergebnis="halb_fertig")
    plan, _, _ = _reagieren(ergebnis, konfig, ordner)
    pruefe(plan.befund == "fehler", f"unbekanntes Vokabular wurde {plan.befund}")
    return "Unbekanntes ergebnis-Wort: als Fehler behandelt, nicht als Erfolg"


# --- Test 11: Engine-Worte verstoss/timeout/abgelehnt -----------------------


def test_engine_verstoss(ordner: Path, konfig) -> str:
    """Befund des Integrationslaufs (t_f7937187): drei Engine-Worte fehlten.

    Der gefaehrliche Fall ist "verstoss": die Wache hat den Lauf wegen einer
    unerlaubten Aktion abgebrochen, darum ist aktionen_genutzt LEER - der
    Vergleich genutzte/erlaubte Aktionen greift nicht. Ohne Eintrag in
    ENGINE_BEFUND war das ein gewoehnlicher Fehler und wurde WIEDERHOLT,
    statt die Regel zu sperren.
    """
    verstoss = _lauf(
        exit=97, ergebnis="verstoss", aktionen_genutzt=[],
        abbruchgrund="Wache: datei_schreiben C:/woanders.txt",
    )
    plan, _, auf = _reagieren(verstoss, konfig, ordner)
    pruefe(plan.befund == "grenzverletzung", f"verstoss wurde {plan.befund}")
    pruefe(bool(plan.regel_sperren), "Grenzverletzung muss die Regel sperren")
    pruefe(plan.nachlauf_in_s is None, "Grenzverletzung darf nie wiederholt werden")

    # timeout: echter Lauf, nicht fertig geworden -> Fehler (Wiederholung ok).
    plan2, _, _ = _reagieren(_lauf(exit=124, ergebnis="timeout"), konfig, ordner)
    pruefe(plan2.befund == "fehler", f"timeout wurde {plan2.befund}")

    # abgelehnt: ein Mensch hat "nein" gesagt - keine Eskalation dafuer.
    plan3, _, auf3 = _reagieren(
        _lauf(exit=None, ergebnis="abgelehnt", modus="bestaetigung",
              abbruchgrund="Bestaetigung verweigert oder verfallen"),
        konfig, ordner,
    )
    pruefe(plan3.befund == "uebersprungen", f"abgelehnt wurde {plan3.befund}")
    pruefe(plan3.nachlauf_in_s is None, "ein Nein darf keine Wiederholung ausloesen")
    return "verstoss sperrt, timeout wiederholt, abgelehnt bleibt still"


TESTS = (
    test_erfolg,
    test_fehler_eskalation,
    test_board_blocken,
    test_grenzverletzung,
    test_stille_faelle,
    test_unvollstaendig,
    test_konfig_pruefung,
    test_engine_uebersprungen,
    test_engine_bestaetigung,
    test_engine_drift,
    test_engine_verstoss,
)


def main() -> int:
    konfig = reaktion.konfig_laden(HIER / "reaktionen.yaml")
    fehler = 0
    for nummer, test in enumerate(TESTS, start=1):
        ordner = Path(tempfile.mkdtemp(prefix="reaktion-test-"))
        try:
            ergebnis = test(ordner, konfig)
            print(f"  {nummer}. gruen  {ergebnis}")
        except AssertionError as fehlschlag:
            print(f"  {nummer}. ROT    {test.__name__}: {fehlschlag}")
            fehler += 1
        finally:
            shutil.rmtree(ordner, ignore_errors=True)
    print()
    if fehler:
        print(f"{fehler} von {len(TESTS)} Tests ROT")
        return 1
    print(f"alle Tests gruen ({len(TESTS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
