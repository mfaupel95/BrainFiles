"""Test fuer die Routine fremdarbeit-einziehen.ps1.

Baut ein eigenes Git-Repository in einem Temp-Ordner, kopiert Skript und
Bus-Ereignis dort hinein und laesst die Routine WIRKLICH laufen (PowerShell).
Geprueft wird, was danach im Repo steht - nicht, was das Skript behauptet.

Direkt ausfuehrbar: python tests/test_fremdarbeit_einziehen.py
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTEN = os.path.dirname(BUS)
WURZEL = os.path.dirname(AGENTEN)
SKRIPT = os.path.join(AGENTEN, "Routinen", "fremdarbeit-einziehen.ps1")
EREIGNIS = os.path.join(BUS, "Ereignis.ps1")


def git(*argumente, cwd):
    a = subprocess.run(["git"] + list(argumente), cwd=cwd,
                       capture_output=True, text=True, timeout=120)
    return a.stdout.strip()


def ps(*argumente, cwd=None):
    a = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File"] + list(argumente),
                       capture_output=True, text=True, timeout=180, cwd=cwd)
    return a


def probe_aufbauen():
    """Temp-Repo mit Skript, Bus-Meldung und allem Noetigen."""
    w = tempfile.mkdtemp(prefix="fremdarbeit-")
    os.makedirs(os.path.join(w, "Agenten", "Bus"))
    os.makedirs(os.path.join(w, "Agenten", "Routinen", "logs"))
    shutil.copy2(SKRIPT, os.path.join(w, "Agenten", "Routinen", "fremdarbeit-einziehen.ps1"))
    shutil.copy2(EREIGNIS, os.path.join(w, "Agenten", "Bus", "Ereignis.ps1"))
    with open(os.path.join(w, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("Agenten/\norigin.git/\n")
    for name, inhalt in (("datei_a.txt", "a\n"), ("datei_c.txt", "c\n"),
                         ("datei_d.txt", "d\n")):
        with open(os.path.join(w, name), "w", encoding="utf-8") as f:
            f.write(inhalt)
    os.makedirs(os.path.join(w, "ordner"))
    with open(os.path.join(w, "ordner", "tief.txt"), "w", encoding="utf-8") as f:
        f.write("drin\n")
    git("init", "-q", "-b", "master", ".", cwd=w)
    git("config", "user.name", "Probe", cwd=w)
    git("config", "user.email", "probe@local", cwd=w)
    git("add", "--", ".gitignore", "datei_a.txt", "datei_c.txt", "datei_d.txt",
        "ordner/tief.txt", cwd=w)
    git("commit", "-q", "-m", "Basis", cwd=w)
    git("init", "-q", "--bare", os.path.join(w, "origin.git"), cwd=w)
    git("remote", "add", "origin", os.path.join(w, "origin.git"), cwd=w)
    git("push", "-q", "-u", "origin", "master", cwd=w)
    return w


def alt_machen(w, *pfade):
    """Ruhend setzen: Zeitstempel zwei Stunden zurueck."""
    alt = time.time() - 2 * 3600
    for p in pfade:
        os.utime(os.path.join(w, p), (alt, alt))


def fremdarbeit_anlegen(w):
    """Eine fremde Sitzung: aendern, neu, loeschen, vormerken - und frisch."""
    with open(os.path.join(w, "datei_a.txt"), "w", encoding="utf-8") as f:
        f.write("a geaendert\n")
    with open(os.path.join(w, "neu_fremd.txt"), "w", encoding="utf-8") as f:
        f.write("neu von fremd\n")
    with open(os.path.join(w, "datei_c.txt"), "w", encoding="utf-8") as f:
        f.write("c geaendert\n")
    git("add", "--", "datei_c.txt", cwd=w)
    os.remove(os.path.join(w, "ordner", "tief.txt"))
    alt_machen(w, "datei_a.txt", "neu_fremd.txt", "datei_c.txt", "ordner")
    # laufende Sitzung: gerade geschrieben, darf NIE mit
    with open(os.path.join(w, "frisch_gerade.txt"), "w", encoding="utf-8") as f:
        f.write("frisch\n")
    with open(os.path.join(w, "datei_d.txt"), "w", encoding="utf-8") as f:
        f.write("d geaendert\n")


def lauf(w, *argumente):
    return ps(os.path.join(w, "Agenten", "Routinen", "fremdarbeit-einziehen.ps1"),
              *argumente, cwd=w)


def test_ruhende_fremdarbeit_landet_in_der_hauptarbeit():
    w = probe_aufbauen()
    try:
        fremdarbeit_anlegen(w)
        a = lauf(w)
        assert a.returncode == 0, a.stderr

        kopf = git("log", "--format=%an <%ae>", "-1", cwd=w)
        assert kopf == "Andere Sitzung <fremd@local>", kopf

        geaendert = git("show", "--name-only", "--format=", "HEAD", cwd=w).split()
        for pfad in ("datei_a.txt", "neu_fremd.txt", "datei_c.txt", "ordner/tief.txt"):
            assert pfad in geaendert, (pfad, geaendert)

        assert git("show", "HEAD:neu_fremd.txt", cwd=w) == "neu von fremd"
        assert git("ls-files", "ordner/", cwd=w) == "", "Loeschung nicht uebernommen"
        assert git("show", "HEAD:datei_a.txt", cwd=w) == "a geaendert"

        # Frisches bleibt liegen
        rest = git("status", "--porcelain", cwd=w)
        assert "frisch_gerade.txt" in rest, rest
        assert "datei_d.txt" in rest, rest
        assert "neu_fremd.txt" not in rest, rest

        # Kein Phantomeintrag, nichts halb vorgemerkt
        assert git("diff", "--cached", "--name-only", cwd=w) == ""
        assert not any(z.startswith("D ") for z in rest.splitlines()), rest

        # Angekommen im Gegenueber (Push). Ein frisch erzeugtes Bare-Repo
        # muss keinen HEAD-Symref haben; pruefe deshalb den Master-Ref direkt.
        remote = git("-C", os.path.join(w, "origin.git"), "show-ref",
                      "--verify", "--hash", "refs/heads/master", cwd=w)
        assert remote == git("rev-parse", "HEAD", cwd=w), remote
    finally:
        shutil.rmtree(w, ignore_errors=True)


def test_frische_arbeit_allein_ergibt_keinen_commit():
    w = probe_aufbauen()
    try:
        with open(os.path.join(w, "gerade.txt"), "w", encoding="utf-8") as f:
            f.write("gerade\n")
        vorher = git("rev-parse", "HEAD", cwd=w)
        a = lauf(w)
        assert a.returncode == 0, a.stderr
        assert "nichts zu uebernehmen" in a.stdout, a.stdout
        assert git("rev-parse", "HEAD", cwd=w) == vorher
        assert "gerade.txt" in git("status", "--porcelain", cwd=w)
    finally:
        shutil.rmtree(w, ignore_errors=True)


def test_probelauf_schreibt_nichts():
    w = probe_aufbauen()
    try:
        fremdarbeit_anlegen(w)
        vorher = git("rev-parse", "HEAD", cwd=w)
        zustand = hashlib.sha256(
            open(os.path.join(w, "datei_a.txt"), "rb").read()).hexdigest()
        vorgemerkt = git("diff", "--cached", "--name-only", cwd=w)
        a = lauf(w, "-Testlauf")
        assert a.returncode == 0, a.stderr
        assert "TESTLAUF" in a.stdout, a.stdout
        assert git("rev-parse", "HEAD", cwd=w) == vorher
        # Nur der Index darf sich nicht veraendern - die Vormerkung der fremden
        # Sitzung (datei_c.txt) bleibt unangetastet, und nichts kommt hinzu.
        assert git("diff", "--cached", "--name-only", cwd=w) == vorgemerkt
        assert hashlib.sha256(
            open(os.path.join(w, "datei_a.txt"), "rb").read()).hexdigest() == zustand
    finally:
        shutil.rmtree(w, ignore_errors=True)


def test_git_sperre_haelt_den_lauf_an():
    w = probe_aufbauen()
    try:
        fremdarbeit_anlegen(w)
        sperre = os.path.join(w, ".git", "index.lock")
        open(sperre, "w").close()
        vorher = git("rev-parse", "HEAD", cwd=w)
        try:
            a = lauf(w)
        finally:
            os.remove(sperre)
        assert "uebersprungen" in a.stdout, a.stdout
        assert git("rev-parse", "HEAD", cwd=w) == vorher
    finally:
        shutil.rmtree(w, ignore_errors=True)


def test_phantom_eintrag_wird_nachgezogen():
    # Nach einer Uebernahme fehlt dem normalen Index eine neu aufgenommene
    # Datei: 'git status' zeigt sie geloescht UND ungetrackt, und ein
    # 'git commit' einer anderen Sitzung ohne Pfadangabe wuerde sie aus master
    # loeschen. Der naechste Lauf muss das geradeziehen - ohne neuen Commit.
    w = probe_aufbauen()
    try:
        with open(os.path.join(w, "neu_fremd.txt"), "w", encoding="utf-8") as f:
            f.write("neu von fremd\n")
        alt_machen(w, "neu_fremd.txt")
        assert lauf(w).returncode == 0
        assert git("ls-files", "neu_fremd.txt", cwd=w) != "", "Uebernahme hat nicht stattgefunden"

        git("update-index", "--force-remove", "--", "neu_fremd.txt", cwd=w)
        zustand = git("status", "--porcelain", cwd=w)
        assert "D  neu_fremd.txt" in zustand and "?? neu_fremd.txt" in zustand, zustand

        vorher = git("rev-parse", "HEAD", cwd=w)
        a = lauf(w)
        assert a.returncode == 0, a.stderr
        assert git("status", "--porcelain", cwd=w) == "", git("status", "--porcelain", cwd=w)
        assert git("rev-parse", "HEAD", cwd=w) == vorher, "Nachtrag darf nicht committen"
    finally:
        shutil.rmtree(w, ignore_errors=True)


def test_rueckschritt_gegen_head_wird_nicht_uebernommen():
    # T-218: Eine ruhende Datei, deren Stand gegen HEAD ein RUECKSCHRITT ist
    # (Arbeitsbaum-Inhalt entspricht einem AELTEREN Commit, HEAD ist neuer),
    # darf NICHT eingeholt werden. Sonst hebt der Einzug eine Reparatur
    # stillschweigend wieder auf - gemessen am 30.09.2026 am Gateway-Launcher.
    w = probe_aufbauen()
    try:
        fremdarbeit_anlegen(w)   # HEAD lernt die neue Fassung von datei_a
        assert lauf(w).returncode == 0
        # Blob-ID statt Textvergleich (T-318). 'git show' liefert den INHALT
        # mit Zeilenumbruch, die git()-Hilfe strippt - der Vergleich hing am
        # Zeilenumbruch und nicht am Verhalten und meldete eine korrekte
        # Routine als Fehler. Die Blob-ID ist byte-genau und unempfindlich.
        kopfA = git("rev-parse", "HEAD:datei_a.txt", cwd=w)
        assert len(kopfA) == 40, "datei_a.txt fehlt in HEAD: %r" % kopfA

        # Zweite, RUECKFAELLIGE Sitzung schreibt die ALTE Fassung zurueck
        # und laesst sie ruhen - der klassische Rueckschritt-Fall.
        with open(os.path.join(w, "datei_a.txt"), "w", encoding="utf-8") as f:
            f.write("a\n")
        alt_machen(w, "datei_a.txt")
        vorher = git("rev-parse", "HEAD", cwd=w)

        a = lauf(w)
        assert a.returncode == 0, a.stderr
        assert "Rueckschritt" in a.stdout or "Rueckschritt" in a.stderr, \
            "Routine nennt den Rueckschritt nicht: %r %r" % (a.stdout, a.stderr)
        assert git("rev-parse", "HEAD", cwd=w) == vorher, \
            "Rueckschritt wurde committet - Reparatur aufgehoben!"
        assert git("rev-parse", "HEAD:datei_a.txt", cwd=w) == kopfA, \
            "Inhalt von HEAD:datei_a.txt hat sich trotz Ablehnung geaendert"
        # Abgelehnte Datei liegt weiter als Aenderung im Arbeitsbaum
        assert " datei_a.txt" in git("status", "--porcelain", cwd=w)
    finally:
        shutil.rmtree(w, ignore_errors=True)


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Tests fremdarbeit-einziehen bestanden")
