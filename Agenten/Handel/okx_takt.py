"""EINE Bremse fuer alle OKX-Abrufe des Hauses - prozessuebergreifend.

Warum es sie braucht (gemessen 05.10.2026):
  120 Kerzenabrufe NACHEINANDER in 30 s  -> 0 Fehler
  6 Threads x 40 Ticker-Abrufe in 23 s   -> 93x "OKX 50011: Too Many
                                           Requests (HTTP 429)"
Der Ausloeser ist damit die PARALLELITAEIT, nicht die Menge. Im Haus laufen
gleichzeitig: drei Dauerlauf-Stufen (Basis/mittel/hoch), die Handelszentrale
(eigener Refresh-Takt), die Wachen (breite-wache, topmover, okx_bot_waechter)
und Werkzeuge - alle gegen dieselbe IP, jeder in seinem eigenen Prozess. Eine
Bremse je Prozess wuerde genau nichts helfen, darum sitzt sie in einer Datei.

Der Takt selbst: OKX begrenzt oeffentliche Markt-Endpunkte auf kurze Fenster
(20 Abrufe / 2 s je IP). Hier werden deshalb ZWEI Regeln gleichzeitig
gehalten, und beide ueber alle Prozesse:
  - hoechstens TAKT_ABRUFE in TAKT_FENSTER_S (Fenster ueber die Datei)
  - und mindestens TAKT_ABRUFE / TAKT_PRO_S between zwei Abrufen

`reserviere()` blockiert, bis beide regeln einen Platz freigeben. Es wird
BEVOR dem Senden aufgerufen - dadurch begrenzt schon die Zahl der *Versuche*,
nicht nur die Zahl der Antworten.

`ist_429()` erkennt beide Formen des Fehlers (HTTPStatusError mit 429 und
OKX-Fehlertext 50011 / "Too Many Requests"), weil sie im Haus aus zwei
verschiedenen Ebenen kommen: urllib.error.HTTPError im _roh() und ein
RuntimeError mit dem JSON-msg in den Werkzeugen mit eigenem hole_json().

Warum bei 429 Warten und nicht Wiederholen im ueblichen Sinn: der einzige
Grund, der sich heilen laesst, ist Warten (gilt auch in xperp/cvd.py). Alle
anderen OKX-Fehler sind fachlich - eine Order-Menge zu klein wird beim
zehnten Versuch nicht kleiner. Deshalb:
  - `ist_429()` + Wartezeit -> der Aufrufer entscheidet, ob ueberhaupt
    wiederholt wird (Lesen: ja, Schreiben: nein, siehe WISSEN/Handelsregeln)
  - alles andere -> sofort werfen
"""

import json
import os
import time

# --- Die Zahlen ------------------------------------------------------------
# OKX erlaubt oeffentlich 20 Abrufe / 2 s je IP. Zwei Regeln muessen GLEICHZEITIG
# halten, und sie duerfen sich nicht genau auf dieselbe Zahl deckeln:
#
#   1) TAKT_ABRUFE je TAKT_FENSTER_S   (das harte Fenster, Kopf-an-Kopf-Spitze)
#   2) TAKT_ABRUFE je TAKT_PRO_S       (die Rate, ueber laengere Zeit)
#
# In der ersten Fassung waren beide deckungsgleich (16/2 s UND 16/0,25 s =
# 8/s). Gemessen 4 Threads x 60 Abrufe: 96 s statt 30 s, Median 1,02 s
# Wartezeit je Aufruf. Grund: wer sein Fenster mit genau 8/s fuellt, sieht ein
# randvolles Fenster und wartet auf die ABLAGE der aeltesten Marke (bis 2 s),
# obwohl die naechste Stelle nach 0,25 s frei waere. Das Fenster muss also
# STRAFFER sein als die Rate - dann ist die Ablage der Weg, und gewartet wird
# nur so lange, wie die aelteste Marke wirklich braucht.
TAKT_FENSTER_S = 2.0
TAKT_ABRUFE = 12          # OKX erlaubt 20; wir liegen 40 % darunter
# Daraus folgt der Mindestabstand zwischen zwei Abrufen: das Fenster von
# TAKT_FENSTER_S soll TAKT_ABRUFE Abrufe fassen, also je TAKT_FENSTER_S /
# TAKT_ABRUFE Sekunden einer, das ist TAKT_FENSTER_S / TAKT_ABRUFE = 0,167 s.
#
# Die erste Fassung rechnete TAKT_PRO_S / TAKT_ABRUFE (= 6 / 12 = 0,5 s) und
# war damit DREIMAL zu langsam - gemessen 2,2 Abrufe/s statt 6, Median 1,0 s
# Wartezeit je Aufruf. Die zweite rechnete TAKT_ABRUFE / TAKT_FENSTER_S und
# kam auf 6 s je Abruf (die Division ist verkehrt herum). Merksatz: 'N Abrufe
# je M Sekunden' heisst M/N Sekunden Abstand, und wer 12/2,0 als 6 liest,
# hat den Bruch verdreht - die Kontrolle ist der Vergleich mit der Rate, die
# man selbst erwartet, nicht das Rechnen.
TAKT_ABSTAND_S = TAKT_FENSTER_S / TAKT_ABRUFE     # 0,167 s -> rund 6/s

# Wartepfade. Die Datei muss in EINEM Ordner liegen, den alle Prozesse
# sehen - Agenten/Handel/cache ist das einzige gemeinsame (und es ist
# absichtlich nicht versioniert).
ORDNER = os.environ.get("OKX_TAKT_ORDNER") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "cache", "okx-takt")
DATEI = os.path.join(ORDNER, "fenster.json")
SPERRE = os.path.join(ORDNER, "fenster.lock")

MAX_SPERREN_S = 5.0        # ein fremder Prozess darf uns nicht dauerhaft aussperren
# Wie lange gewartet wird, BIS ein Platz frei ist. Das ist bewusst weit
# ueber der Zeit, die der Takt braucht: bei TAKT_ABRUFE/TAKT_FENSTER_S = 8
# Abrufen je Sekunde brauchen 240 Abrufe genau 30 s. Mit MAX_WARTE_S = 30
# (erste Fassung) meldete die Bremse dann "kein Platz frei" - sie tat genau
# das Richtige und wurde trotzdem zum Fehler. Ein Takt, der wartet, ist die
# HEILUNG; er darf sie nicht in einen Abbruch verwandeln. Deshalb 180 s, und
# TaktBlockiert bleibt als Sicht fuer einen fremden Prozess, der die Sperre
# haelt (MAX_SPERREN_S) - der Fall soll auffallen, nicht der Normalfall.
MAX_WARTE_S = 180.0
# Toleranz fuer die Ablagepruefung. Sie darf NICHT groesser sein als ein
# Bruchteil des Mindestabstands, sonst gibt die Bremse einen Platz zu frueh
# frei: bei TAKT_ABSTAND_S = 0,167 s und MESSER = 0,02 lag der gemessene
# Abstand bei 0,166 s statt 0,167 (der Test 'zehn Abrufe' fand es).
# Sie existiert nur, damit ein Zeitstempel, der praktisch genau auf der Kante
# liegt, nicht ein zweites Mal um 0,167 s wartet.
MESSER = TAKT_ABSTAND_S / 10.0     # 0,0167 s


class TaktBlockiert(RuntimeError):
    """Der Takt gibt nach MAX_WARTE_S keinen Platz frei - ein fremder Prozess
    haelt die Sperre oder der Ordner ist nicht schreibbar. Bewusst KEIN
    'Dann halt ohne Bremse': der Aufrufer soll den Ausfall sehen."""


# --- Datei -----------------------------------------------------------------
def _bereit():
    try:
        os.makedirs(ORDNER, exist_ok=True)
        return True
    except OSError:
        return False


def _lese():
    try:
        with open(DATEI, "r", encoding="utf-8") as f:
            roh = f.read().strip()
        if not roh:
            return []
        werte = json.loads(roh)
        return [float(w) for w in werte if isinstance(w, (int, float))]
    except (OSError, ValueError):
        return []


def _schreibe(werte):
    # write+replace: ein halb geschriebener Fensterspiegel wuerde als
    # leerer Takt gelesen und die Bremse aufheben.
    #
    # Die Genauigkeit ist 6 Nachkommastellen (Mikrosekunden), NICHT 3: bei
    # einem Mindestabstand von 0,167 s kostet jede gerundete Marke bis zu
    # 0,5 ms, und ueber 10 aufeinanderfolgende Abrufe ergab das 0,166 statt
    # 0,167 - der Test 'zehn Abrufe' fand genau diese Abweichung. Wer hier
    # spart, verlangsamt still den Takt.
    tmp = DATEI + ".tmp-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump([round(w, 6) for w in werte], f)
    os.replace(tmp, DATEI)


def _sperre():
    """Ein exklusives Erstellen als Schloss. Bewusst kein fcntl/msvcrt: die
    Sperre muss auch dann funktionieren, wenn ein Prozess mitten im Lauf
    stirbt (das ist hier die Regel, nicht die Ausnahme - der Dauerlauf
    bekommt SIGTERM)."""
    ende = time.monotonic() + MAX_SPERREN_S
    while True:
        try:
            fd = os.open(SPERRE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            # Ein fremder Prozess haelt sie. Ist er tot, ist die Datei alt.
            try:
                alter = time.time() - os.path.getmtime(SPERRE)
            except OSError:
                alter = 0.0
            if alter > MAX_SPERREN_S:
                try:
                    os.remove(SPERRE)
                except OSError:
                    pass
                continue
            if time.monotonic() > ende:
                return False
            time.sleep(0.01)
        except OSError:
            return False


def _streuung():
    """Zufallswert 0,0-1,0 - pro Prozess einmal gemischt, damit zwei
    Prozesse nicht im Gleichtakt aufwachen. Ohne random-Modul: der Zufall
    kommt aus der Uhr, das reicht fuer Streuung vollkommen aus."""
    _x = (int(time.time() * 1000) * 1103515245 + os.getpid() * 12345) % 1000
    return _x / 1000.0


def _entsperre():
    try:
        os.remove(SPERRE)
    except OSError:
        pass


# --- Fehlerkennung ---------------------------------------------------------
def ist_429(fehler):
    """True, wenn die Meldung eine Drosselung ist - in BEIDEN Formen.

    Form 1: urllib.error.HTTPError mit code 429 (der HTTP-Status).
    Form 2: OKXFehler/RuntimeError mit '50011' oder 'Too Many Requests'
            im Text (der eigene JSON-Fehler, auch bei HTTP 200/4xx).
    Beide kommen im Haus vor, weil vier Module an vier Stellen HTTP machen.
    """
    code = getattr(fehler, "code", None)
    if code == 429:
        return True
    text = str(fehler)
    return "50011" in text or "Too Many Requests" in text


def warte_s(nach_fehlern=1, basis=1.5):
    """Sekunden, die nach einem 429 gewartet werden. Exponentiell, aber
    gedeckelt: OKX rechnet nach, und ein Erfolg holt den Takt sofort nach."""
    return min(30.0, basis * (2 ** max(0, nach_fehlern - 1)))


# --- Die Bremse ------------------------------------------------------------
def reserviere(fester_zeitpunkt=None):
    """Blockiert, bis ein Platz frei ist, und vermerkt ihn. Gibt die Zahl der
    Sekunden zurueck, die gewartet wurde (fuer Meldungen/Tests).

    Ohne brauchbaren Ordner gibt es KEINEN Takt: dann liefert die Funktion
    sofort, statt den Handel aufzuhalten. Das ist der einzige bewusste
    Durchlass - ein fehlender Cache-Ordner darf keine Live-Position
    blockieren.

    `fester_zeitpunkt` ist ausschliesslich fuer Tests (Fenster mit
    vorgegebener Uhr simulieren). Die erste Fassung hiess dafuer `jetzt` und
    benutzte dieselbe Variable als Schleifenvariable - im zweiten Durchlauf
    war sie nicht mehr None, die Uhr eingefroren, `warte_bis - jetzt`
    negativ und die Schleife lief endlos (gemessen: 10 reserviere() statt
    1,1 s -> Timeout nach 45 s). Der Parameter heisst darum ausdruecklich
    NICHT wie die lokale Uhr.
    """
    if not _bereit():
        return 0.0
    warte = 0.0
    ende = time.monotonic() + MAX_WARTE_S
    while True:
        uhr = time.time() if fester_zeitpunkt is None else fester_zeitpunkt
        gehalten = _sperre()
        if not gehalten:
            # Ein fremder Prozess haelt die Sperre laenger als MAX_SPERREN_S.
            # Wir messen dann OHNE Sperre weiter und geben sie ihm frei - nicht
            # returnen: 'durchlassen' hiesse, den Takt aufzuheben, und genau
            # das erzeugt die Drosselung, die die Bremse beseitigen soll. Wirft
            # ein fremder Prozess gerade die Datei weg, lesen wir eben ohne
            # Sperre; der Fensterspiegel kann dadurch um einen Platz daneben-
            # liegen, das ist verkraftbar - ein 429-Zyklusabbruch nicht.
            # Der kurze Streuschlaf traegt hier viel: er nimmt den Prozessen
            # die Belastung, waehrend sie auf die fremde Sperre warten.
            time.sleep(_streuung() * 0.05)
        try:
            werte = [w for w in _lese() if uhr - w < TAKT_FENSTER_S]
            abstand = TAKT_ABSTAND_S
            naechste_ok = len(werte) < TAKT_ABRUFE and not (
                werte and (uhr - max(werte)) < (abstand - MESSER))
            if naechste_ok:
                werte.append(uhr)
                _schreibe(werte)
                return warte
            warte_bis = max(werte) + abstand if werte else uhr + 0.05
        finally:
            if gehalten:
                _entsperre()
        # Wir haben nichts belegt: schlafen, dann erneut messen.
        #
        # Der Streuwert ist KEIN Zuschlag auf die Wartezeit - das war der
        # Fehler der zweiten Fassung: bei Abstand 0,33 s addierte er bis zu
        # 0,33 s und dehnte den gemessenen Abstand auf 0,53 s (Takt danach
        # 4,4/s statt 6/s). Er verschiebt nur das Aufwachen, nicht die Warte-
        # dauer: gewartet wird bis warte_bis, und wenn das frueher liegt als
        # jetzt, wird ein winziger Schlaf eingelegt, damit die Processes sich
        # nicht im Gleichtakt erneut treffen.
        #
        # Die Wartezeit richtet sich nach der ECHTEN Uhr, nicht nach der
        # eingebgebenen: sonst schlaeft ein Aufrufer mit Testuhr minutenlang,
        # waehrend die reale Uhr weiterlaeuft. Genau das tat die erste Fassung -
        # der Test 'Fenster bricht ab' brauchte 180 s und endete in
        # TaktBlockiert. Die Auswertung oben bleibt bei der Testuhr (sonst
        # waere sie sinnlos), nur der Schlaf ist real.
        zeit = max(0.02, min(warte_bis - time.time(), 1.0))
        if time.monotonic() > ende:
            raise TaktBlockiert("OKX-Takt gab nach %.0f s keinen Platz frei"
                                % MAX_WARTE_S)
        time.sleep(zeit)
        warte += zeit


def stand():
    """(jetzt, anzahl im Fenster, sekunden bis zum naechsten Platz) - lesend,
    fuer die Wache und den Test."""
    jetzt = time.time()
    werte = [w for w in _lese() if jetzt - w < TAKT_FENSTER_S]
    abstand = TAKT_ABSTAND_S
    warte_bis = 0.0 if not werte else max(0.0, max(werte) + abstand - jetzt)
    return jetzt, len(werte), warte_bis


def leeren():
    """Fensterspiegel loeschen - nur fuer Tests und nach einem Absturz, in dem
    ein Zeitstempel liegen blieb. Im Betrieb ist das nie noetig: abgelaufene
    Zeitstempel werden ohnehin verworfen."""
    if _bereit():
        _schreibe([])
