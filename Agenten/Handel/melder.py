"""Telegram-Anbindung der Handelsspuren - melden und entgegennehmen.

Ein Kanal fuer beides: die taegliche Meldung geht hier raus, die Steuerung
vom Handy kommt hier rein. Angelegt am 03.09.2026 auf Max' Anweisung
("taegliche Meldung mit Updates auf mein Handy", "Steuerung muss auch ueber
mein Smartphone moeglich sein").

Nur Standardbibliothek, wie kraken.py - dieser Ordner soll wegen des Melders
kein Paket nachziehen muessen.

WAS DIESER MELDER NICHT TUT
---------------------------
Er loest keine Order aus. Er kennt keinen Boersenschluessel. Was ueber
Telegram hereinkommt, ist hoechstens eine *Freigabe* - ausgefuehrt wird sie
danach vom Skript der jeweiligen Spur, im Rahmen ihrer wachen.json. Damit
bleibt die tragende Regel aus Wissen/Handelsregeln.md unangetastet: Der
Automat entscheidet ueber Positionen, nicht darueber, ob er selbst scharf
ist.

Die Grenze ist bewusst hier gezogen und nicht erst im Bot: Telegram ist ein
fremder Dienst. Wer den Kanal uebernimmt, darf hoechstens ein Zeitfenster
oeffnen, dessen Grenzen schon in einer Datei stehen - nie einen Betrag, nie
einen Hebel, nie ein Instrument.

FREIGABELISTE
-------------
TELEGRAM_CHAT_ID ist keine Bequemlichkeit, sondern die Zugangssperre. Ein
Telegram-Bot antwortet jedem, der seinen Namen kennt. Ohne die Liste
steuerte ein Fremder die Spuren, sobald er den Bot findet - genau der Punkt,
an dem das Hermes-Gateway in Wissen/Hermes.md haengen geblieben ist. Kommt
eine Nachricht von einer anderen Chat-ID, wird sie verworfen und gezaehlt,
nicht beantwortet.

EINRICHTEN (einmalig, von Max)
------------------------------
  1. In Telegram @BotFather anschreiben, /newbot, Namen vergeben.
     BotFather antwortet mit einem Token der Form 123456:ABC-DEF...
  2. Den eigenen Bot anschreiben (irgendetwas, z.B. "hallo").
  3. Token als Benutzervariable setzen, so wie OKX und Kraken es machen
     (HKCU\\Environment, nicht in den Vault, nicht neben den Code):

       setx TELEGRAM_TOKEN "123456:ABC-DEF..."

  4. Chat-ID ermitteln und ebenfalls setzen:

       python melder.py --chat-id-suchen
       setx TELEGRAM_CHAT_ID "123456789"

  5. Probe:

       python melder.py --probe

Neues Terminal noetig, damit setx sichtbar wird.
"""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

BASIS = "https://api.telegram.org/bot%s/%s"
HEADERS = {"User-Agent": "MaxHirn-Handel/1.0",
           "Content-Type": "application/json"}
MAX_FEHLER = 4

# Telegram bricht Nachrichten ueber 4096 Zeichen hart ab. Der Tagesbericht
# kann laenger werden, sobald mehrere Spuren offene Positionen haben.
MAX_ZEICHEN = 4000


class MelderFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen Telegram-Antwort (ok=false).
    Wird NICHT wiederholt - ein falscher Token ist beim zehnten Versuch
    genauso falsch."""


# --- Schluessel -------------------------------------------------------------

def _aus_registry(name):
    """Benutzervariable direkt aus der Registry.

    Denselben Umweg geht okxf.py: Ein per setx gesetzter Wert erscheint in
    laufenden Prozessen nicht, und der MCP-Client reicht Benutzervariablen
    ohnehin nicht durch (Wissen/Verbindungen.md).
    """
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _variable(name):
    return os.environ.get(name) or _aus_registry(name)


def token():
    return _variable("TELEGRAM_TOKEN")


def chat_id():
    return _variable("TELEGRAM_CHAT_ID")


def bereit():
    """Beide Werte gesetzt? Ohne sie laeuft alles weiter, nur stumm."""
    return bool(token() and chat_id())


def fehlt():
    """Was fehlt - als Text fuer eine Protokollzeile."""
    m = [n for n, v in (("TELEGRAM_TOKEN", token()),
                        ("TELEGRAM_CHAT_ID", chat_id())) if not v]
    return ", ".join(m)


# --- Verkehr ----------------------------------------------------------------

def _ruf(methode, daten=None, zeit=30):
    t = token()
    if not t:
        raise MelderFehler("TELEGRAM_TOKEN nicht gesetzt")

    leib = json.dumps(daten or {}).encode("utf-8")
    anfrage = urllib.request.Request(BASIS % (t, methode), data=leib,
                                     headers=HEADERS, method="POST")

    letzter = None
    for versuch in range(MAX_FEHLER):
        try:
            with urllib.request.urlopen(anfrage, timeout=zeit) as a:
                d = json.load(a)
            if not d.get("ok"):
                # 409 = zweiter Abrufer auf demselben Token. Das ist ein
                # Betriebsfehler, kein Netzfehler: zwei Dauerlaeufe teilen
                # sich einen Bot und nehmen sich die Nachrichten weg.
                raise MelderFehler("%s: %s" % (
                    d.get("error_code"), d.get("description")))
            return d["result"]
        except MelderFehler:
            raise
        except urllib.error.HTTPError as e:
            if e.code == 409:
                raise MelderFehler(
                    "409 - ein zweiter Abrufer haengt an diesem Bot. "
                    "Laeuft der Dauerlauf schon?")
            letzter = e
        except Exception as e:                          # noqa: BLE001
            letzter = e
        time.sleep(1.5 * (versuch + 1))
    raise MelderFehler("Telegram nicht erreichbar: %s" % letzter)


def sende(text, stumm=False, ziel=None):
    """Eine Nachricht. Gibt True zurueck, wenn sie draussen ist.

    Wirft nicht, wenn der Melder nicht eingerichtet ist - eine fehlende
    Meldung darf keinen Handelslauf abbrechen. Sie wird nur nicht gesendet.
    """
    if not bereit():
        return False
    for stueck in _stuecke(_entschaerfe(text)):
        _ruf("sendMessage", {
            "chat_id": ziel or chat_id(),
            "text": stueck,
            "parse_mode": "HTML",
            "disable_notification": bool(stumm),
            "disable_web_page_preview": True,
        })
    return True


# Erlaubte Telegram-HTML-Marken. Alles andere, was wie eine Marke aussieht,
# wird entschaerft - siehe _entschaerfe().
_ERLAUBT = re.compile(r"</?(?:b|i|u|s|code|pre|a)(?:\s[^<>]*)?>", re.I)
# Eine schon gueltige Entitaet darf NICHT doppelt entschaerft werden.
_NACKTES_UND = re.compile(r"&(?!(?:amp|lt|gt|quot|#\d+|#x[0-9a-fA-F]+);)")


def _entschaerfe(text):
    """Rohe < > & entschaerfen, Telegram-Marken stehen lassen.

    ANLASS (21.09.2026, gemessen): Der Wochenbericht enthaelt den Satz
    "n=<Zahl> heisst: zu wenige Runden". Telegram liest mit parse_mode=HTML
    ein "<Zahl>" als Marke und weist die ganze Nachricht ab -
    "400 Bad Request: can't parse entities: Unsupported start tag \"zahl\"".
    Der Bericht kam deshalb nie an, und es sah aus, als haette Telegram
    generell etwas gegen den Bericht.

    Derselbe Fehler lauerte in jedem Traceback im Bericht (<module>, <lambda>)
    und in jeder Fehlermeldung eines fremden Programms. Deshalb steht die
    Rettung hier an der Sendestelle und nicht in jedem Bericht einzeln - sie
    wirkt fuer Tagesbericht, Wochenbericht, Handelsmeldungen und Wachen
    gleichermassen.
    """
    teile, letzter = [], 0
    for m in _ERLAUBT.finditer(text):
        teile.append(_roh(text[letzter:m.start()]))
        teile.append(m.group(0))
        letzter = m.end()
    teile.append(_roh(text[letzter:]))
    return "".join(teile)


def _roh(text):
    # Nur nackte & entschaerfen - eine schon gueltige Entitaet (&amp;, &#39;)
    # bleibt stehen, sonst stuende "&amp;amp;" in der Nachricht.
    text = _NACKTES_UND.sub("&amp;", text)
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _harte_schnitte(zeile):
    """Eine Zeile, die allein schon zu lang ist, in Stuecke zerlegen.

    GEMESSEN 21.09.2026: eine einzelne Zeile ueber der Grenze rutschte
    UNGETEILT durch - 4500 Zeichen bei MAX_ZEICHEN 4000, Telegram schnitt sie
    ab. Selten, aber real: ein Traceback ohne Umbruch, eine lange Fehlerzeile
    eines fremden Programms.
    """
    return [zeile[i:i + MAX_ZEICHEN] for i in range(0, len(zeile), MAX_ZEICHEN)]


def _marken_schliessen(stueck):
    """Offene Marken am Stueckende schliessen. Rueckgabe (Stueck, offene).

    GEMESSEN 21.09.2026: ein <b>, das ueber die Stueckgrenze hinweg aufgespannt
    war, hinterliess im ersten Stueck ein offenes und im zweiten ein verwaistes
    </b> - Telegram weist BEIDE Nachrichten ab ("can't parse entities"). Die
    Trennung darf die Marken also nicht zerreissen.
    """
    offen = []
    for m in _ERLAUBT.finditer(stueck):
        marke = m.group(0)
        name = marke.strip("</>").split()[0].lower()
        if marke.startswith("</"):
            if offen and offen[-1] == name:
                offen.pop()
        elif not marke.endswith("/>"):
            offen.append(name)
    return stueck + "".join("</%s>" % n for n in reversed(offen)), offen


def _stuecke(text):
    """Lange Texte an Zeilengrenzen teilen, statt sie abschneiden zu lassen.

    Zwei Sonderfaelle, beide am 21.09.2026 gemessen: eine einzelne ueberlange
    Zeile (harter Schnitt) und eine Marke, die ueber die Stueckgrenze reicht
    (wird am Ende geschlossen und am naechsten Anfang neu geoeffnet).
    """
    if len(text) <= MAX_ZEICHEN:
        return [text]

    roh, jetzt = [], ""
    for zeile in text.split("\n"):
        teile = _harte_schnitte(zeile) if len(zeile) > MAX_ZEICHEN else [zeile]
        for teil in teile:
            if jetzt and len(jetzt) + len(teil) + 1 > MAX_ZEICHEN:
                roh.append(jetzt.rstrip("\n"))
                jetzt = ""
            jetzt += teil + "\n"
    if jetzt.strip():
        roh.append(jetzt.rstrip("\n"))

    stuecke, offen = [], []
    for s in roh:
        s = "".join("<%s>" % n for n in offen) + s
        s, offen = _marken_schliessen(s)
        stuecke.append(s)
    return stuecke


def hole(seit=None, warten=0):
    """Neue Nachrichten. warten>0 nutzt Long-Polling.

    Fremde Absender werden hier verworfen, nicht erst beim Auswerten. Wer
    nicht in der Freigabeliste steht, existiert fuer den Rest des Programms
    nicht.
    """
    if not bereit():
        return [], seit
    d = {"timeout": warten, "allowed_updates": ["message"]}
    if seit is not None:
        d["offset"] = seit
    roh = _ruf("getUpdates", d, zeit=warten + 25)

    erlaubt = str(chat_id())
    nachrichten, letzte = [], seit
    fremd = 0
    for u in roh:
        letzte = u["update_id"] + 1
        n = u.get("message") or {}
        von = str((n.get("chat") or {}).get("id", ""))
        text = (n.get("text") or "").strip()
        if not text:
            continue
        if von != erlaubt:
            fremd += 1
            continue
        nachrichten.append({"text": text, "von": von,
                            "zeit": n.get("date", 0),
                            "name": (n.get("from") or {}).get("first_name", "")})
    if fremd:
        # Sichtbar machen, nicht beantworten. Wiederholte fremde Zugriffe
        # heissen, dass jemand den Bot gefunden hat.
        print("melder: %d Nachricht(en) von fremden Chats verworfen" % fremd)
    return nachrichten, letzte


def leeren():
    """Wartende Nachrichten wegwerfen und den Zeiger ans Ende setzen.

    Beim Start eines Dauerlaufs noetig: Sonst arbeitet er Befehle ab, die
    waehrend seiner Auszeit aufgelaufen sind - eine Freigabe von gestern
    Nacht ist keine Freigabe fuer heute frueh.
    """
    if not bereit():
        return None
    roh = _ruf("getUpdates", {"timeout": 0})
    return roh[-1]["update_id"] + 1 if roh else None


# --- Werkzeuge --------------------------------------------------------------

def chat_id_suchen():
    """Die eigene Chat-ID aus den wartenden Nachrichten lesen."""
    if not token():
        print("TELEGRAM_TOKEN ist nicht gesetzt - siehe Kopf dieser Datei.")
        return 1
    roh = _ruf("getUpdates", {"timeout": 0})
    if not roh:
        print("Keine wartenden Nachrichten. Schreibe deinem Bot in Telegram")
        print("irgendetwas und rufe das hier noch einmal auf.")
        return 1
    gesehen = {}
    for u in roh:
        n = u.get("message") or {}
        c = n.get("chat") or {}
        if c.get("id"):
            gesehen[c["id"]] = "%s %s" % (c.get("first_name", ""),
                                          c.get("last_name", "")).strip()
    print("Gefundene Chats:")
    for cid, name in gesehen.items():
        print("  %-14s %s" % (cid, name or "(ohne Namen)"))
    print()
    print('Setzen mit:  setx TELEGRAM_CHAT_ID "%s"' % next(iter(gesehen)))
    return 0


def probe():
    """Einrichtung pruefen und eine Testnachricht senden."""
    print("TELEGRAM_TOKEN    %s" % ("gesetzt" if token() else "FEHLT"))
    print("TELEGRAM_CHAT_ID  %s" % (chat_id() or "FEHLT"))
    if not bereit():
        print()
        print("Es fehlt: %s" % fehlt())
        print("Einrichtung steht im Kopf von melder.py.")
        return 1
    ich = _ruf("getMe")
    print("Bot               @%s (%s)" % (ich.get("username"),
                                          ich.get("first_name")))
    sende("<b>Probe</b>\nDer Melder ist eingerichtet und erreicht dieses "
          "Geraet.\n\nGesendet %s" % time.strftime("%d.%m.%Y %H:%M"))
    print()
    print("Testnachricht gesendet.")
    return 0


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--probe", action="store_true",
                   help="Einrichtung pruefen, Testnachricht senden")
    g.add_argument("--chat-id-suchen", action="store_true",
                   help="eigene Chat-ID aus wartenden Nachrichten lesen")
    g.add_argument("--sende", metavar="TEXT", help="eine Nachricht senden")
    g.add_argument("--lauschen", action="store_true",
                   help="eingehende Nachrichten anzeigen (Strg+C beendet)")
    a = p.parse_args()

    if a.chat_id_suchen:
        return chat_id_suchen()
    if a.probe:
        return probe()
    if a.sende:
        return 0 if sende(a.sende) else 1

    print("Lausche. Strg+C beendet.")
    zeiger = leeren()
    while True:
        try:
            n, zeiger = hole(zeiger, warten=25)
        except MelderFehler as e:
            print("Fehler: %s" % e)
            time.sleep(5)
            continue
        for m in n:
            print("[%s] %s: %s" % (
                time.strftime("%H:%M", time.localtime(m["zeit"])),
                m["name"], m["text"]))


if __name__ == "__main__":
    raise SystemExit(main())
