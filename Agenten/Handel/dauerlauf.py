"""Der 24/7-Betrieb: analysieren, rechnen, melden, auf Befehle hoeren.

Angelegt am 03.09.2026 auf Max' Anweisung ("24/7 aktiv und am analysieren,
kalkulieren, anpassen"). Loest die Tagesroutinen nicht ab - es ergaenzt sie:
Die geplanten Laeufe unter ../Routinen/ bleiben, wie sie sind, und dieser
Dauerlauf setzt sich darueber.

DREI TAKTE, ABSICHTLICH VERSCHIEDEN
-----------------------------------
  Befehle       alle paar Sekunden   Long-Polling, kostet nichts
  Zyklus        alle takt_minuten    Positionen pruefen, Stops, Journal
  Tagesbericht  einmal taeglich      der Ueberblick aufs Handy

Der Zyklus-Takt ist an den Herzschlag gekoppelt und nicht frei waehlbar:
xperp/wachen.json setzt herzschlag_max_minuten auf 30. Laeuft der Zyklus
seltener, meldet die eigene Wache den Bot als tot und faellt auf Papier
zurueck - richtig so, aber dann laeuft er eben nicht.

WAS ER SELBST NICHT TUT
-----------------------
Er schaltet sich nicht scharf. Ohne offenes Freigabefenster laeuft jeder
Zyklus als Papierhandel - auch wenn wachen.json handel_erlaubt truege. Das
ist die Umsetzung von Punkt 3 der Handelsregeln unter den Bedingungen des
Dauerbetriebs: Ein Zeitplan legt den Schalter nicht um, und ein Dauerlauf ist
nichts anderes als ein sehr enger Zeitplan.

Er handelt nur Spuren mit Live-Pfad. Seit 03.09.2026 sind das zwei: Spur 2
(xperp, der Hauptweg - der Pfad entstand an diesem Tag) und Spur 1
(scanner). Spur 3 (Kraken) ist stillgelegt.

WER FRAGT, WANN
---------------
Ein Fenster oeffnet sich nur auf Anfrage, und die stellt pruefe_anfragen()
nach jedem Zyklus - aber nur, wenn ALLE anderen Sperren einer Spur offen
sind und wirklich nichts mehr fehlt als die Freigabe. Eine Frage, die auch
nach einem /ja folgenlos bliebe, wird nicht gestellt: Wer solche Fragen
schickt, bekommt sie weggewischt, ohne gelesen zu werden - und dann auch
die eine, auf die es ankam.

BEFEHLE VOM HANDY
-----------------
  /lage        Positionen und Sperren, sofort
  /bericht     der volle Tagesbericht
  /scan        Rangliste neu rechnen
  /ja [h]      wartende Freigabe erteilen (Vorgabe: die angefragte Dauer)
  /nein        wartende Freigabe ablehnen
  /stop        alle Fenster zu, zurueck auf Papier
  /pause       Zyklus aussetzen, Meldungen laufen weiter
  /weiter      Zyklus fortsetzen
  /hilfe       diese Liste

Aufruf:
    python dauerlauf.py                 # laeuft, bis Strg+C
    python dauerlauf.py --takt 15       # anderer Zyklus-Takt
    python dauerlauf.py --trocken       # nichts senden, nur Konsole
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
# Bus-Anbindung (Aufgabe 7): meldet nur Start/Ende, ersetzt melder.sende()
# nirgends - ein toter Bus darf den Dauerlauf nie aufhalten (ereignis.melden
# faengt selbst alles ab).
sys.path.insert(0, os.path.join(HIER, os.pardir, "Bus"))

import ereignis                                           # noqa: E402
import freigabefenster                                   # noqa: E402
import melder                                            # noqa: E402
import tagesbericht                                      # noqa: E402

# Der woechentliche Selbstverbesserungs-Lauf (verbesserer/) haengt hier nur
# lose dran: anfrage.py haelt die reine Ordner-/Textlogik, anwenden.py den
# einzigen schreibenden Pfad. Faellt der Import aus - Modul kaputt, Ordner
# fehlt -, bleibt verbesserer_anfrage None und der Dauerlauf laeuft ohne den
# Anfrage-Typ weiter.
VERB_DIR = os.path.join(HIER, "verbesserer")
VERB_BERICHTE = os.path.join(VERB_DIR, "berichte")
REPO_WURZEL = os.path.dirname(os.path.dirname(HIER))
sys.path.insert(0, VERB_DIR)
try:
    import anfrage as verbesserer_anfrage                # noqa: E402
    import anwenden as verbesserer_anwenden              # noqa: E402
except Exception:                                        # noqa: BLE001
    verbesserer_anfrage = None
    verbesserer_anwenden = None

PYTHON = os.path.join(HIER, "scanner", ".venv", "Scripts", "python.exe")

# Spuren, die dieser Lauf fuehrt.
#
# Spur 2 (xperp) ist seit 03.09.2026 der Hauptweg und hat seit demselben Tag
# einen Live-Pfad - vorher legte bot.py nur vor. Sie steht zuerst.
#
# Spur 3 (Kraken) ist seit 03.09.2026 stillgelegt und steht deshalb nicht
# mehr hier - Grund und Zahlen in kraken/wachen.json, Feld
# _stillgelegt_grund. Der Ordner bleibt, die Spur kann wieder anlaufen.
SPUREN = {
    "xperp": {"ordner": "xperp", "waehrung": "USD"},
    "scanner": {"ordner": "scanner", "waehrung": "USD"},
}

# Der Takt ist bei Spur 2 keine Geschmacksfrage: xperp/wachen.json setzt
# herzschlag_max_minuten auf 30. Laeuft der Zyklus seltener, stellt der
# naechste Lauf alle Positionen flach und faellt auf Papier zurueck - richtig
# so, aber dann handelt die Spur eben nicht. 15 Minuten lassen einen
# ausgefallenen Zyklus zu, bevor es eng wird.
TAKT_MAX_MINUTEN = 15


def jetzt():
    return dt.datetime.now()


def protokoll(text):
    zeile = "%s  %s" % (jetzt().strftime("%d.%m. %H:%M:%S"), text)
    print(zeile, flush=True)
    try:
        with open(os.path.join(HIER, "dauerlauf.log"), "a",
                  encoding="utf-8") as f:
            f.write(zeile + "\n")
    except OSError:
        pass


class Lauf:
    def __init__(self, takt, trocken=False):
        self.takt = takt
        self.trocken = trocken
        self.pausiert = False
        self.zeiger = None
        self.letzter_zyklus = None
        self.letzter_bericht = None
        self.zyklen = 0
        self.fehler = 0

    # --- senden ---------------------------------------------------------

    def sende(self, text, stumm=False):
        if self.trocken:
            print("--- wuerde senden ---\n%s\n---" %
                  text.replace("<b>", "").replace("</b>", ""))
            return True
        return melder.sende(text, stumm=stumm)

    # --- die Spuren -----------------------------------------------------

    def zyklus_spur(self, spur):
        """Ein Zyklus einer Spur. Papier, ausser das Fenster ist offen."""
        f = freigabefenster.lade(spur)
        modus = "--live" if f.offen() else "--papier"

        ordner = os.path.join(HIER, SPUREN[spur]["ordner"])
        umgebung = dict(os.environ)
        if modus == "--papier":
            # Sagt handeln.py, dass niemand am Bildschirm sitzt: kein
            # Freigabefenster aus einem laufenden Dienst heraus. Bei --live
            # ist die Freigabe bereits erteilt und die Variable faellt weg.
            umgebung["MAXHIRN_ROUTINE"] = "1"

        p = subprocess.run([PYTHON, "handeln.py", modus], cwd=ordner,
                           capture_output=True, text=True, timeout=600,
                           env=umgebung)
        return modus, p.returncode, (p.stdout or "") + (p.stderr or "")

    def zyklus(self):
        self.zyklen += 1
        self.letzter_zyklus = jetzt()
        auffaellig = []

        for spur in SPUREN:
            try:
                modus, code, ausgabe = self.zyklus_spur(spur)
            except Exception as e:                       # noqa: BLE001
                self.fehler += 1
                protokoll("%s FEHLER: %s" % (spur, e))
                auffaellig.append("%s: %s" % (spur, e))
                continue

            kurz = modus.lstrip("-")
            if code != 0:
                self.fehler += 1
                protokoll("%s (%s) Rueckgabe %d" % (spur, kurz, code))
                auffaellig.append("%s endete mit %d" % (spur, code))
            else:
                protokoll("%s (%s) ok" % (spur, kurz))

            # Verkauf oder Stop im Lauf: das gehoert sofort gemeldet, nicht
            # erst im Tagesbericht. Gemeldet wird nur die Zeile, die das
            # Wort traegt - deshalb muss jede gemeldete Zeile ihr
            # Instrument selbst nennen. Eine Fortsetzungszeile ohne Subjekt
            # ist im Chat nicht zuzuordnen (Befund 11.09.2026: die
            # Stop-Zeile von xperp kam ohne Wertnamen an).
            for wort in ("verkauf", "stop", "KILL", "gesperrt"):
                if wort.lower() in ausgabe.lower():
                    for zeile in ausgabe.splitlines():
                        if wort.lower() in zeile.lower():
                            auffaellig.append("%s: %s" % (spur, zeile.strip()))
                    break

        if auffaellig:
            self.sende("<b>Zyklus %d</b>\n%s" % (
                self.zyklen, "\n".join(auffaellig[:12])))

        self.pruefe_anfragen()

    def pruefe_anfragen(self):
        """Fragt nach Freigabe, wenn NUR noch das Fenster fehlt.

        Ohne diesen Schritt koennte Max nie /ja sagen: freigabefenster
        oeffnet nur auf Anfrage, und eine Anfrage stellt sonst niemand.

        Gefragt wird bewusst spaet - erst wenn jede andere Sperre offen ist.
        Eine Freigabe einzuholen, waehrend handel_erlaubt noch false steht
        oder die Freigabe aus Bedingung 1 fehlt, waere eine Frage ohne Folge:
        Der Lauf handelte auch nach einem /ja weiter auf Papier. Wer solche
        Fragen stellt, bekommt sie irgendwann weggewischt, ohne gelesen zu
        werden - und dann auch die eine, auf die es ankam.
        """
        for spur, d in SPUREN.items():
            f = freigabefenster.lade(spur)
            if f.offen() or f.anfrage_offen():
                continue
            offen_bis_auf_fenster = self.nur_fenster_fehlt(spur, d)
            if not offen_bis_auf_fenster:
                continue
            w = offen_bis_auf_fenster
            dauer = freigabefenster.anfrage_stellen(spur, 12 * 60)
            protokoll("Freigabe-Anfrage %s (%d min)" % (spur, dauer))
            self.sende(freigabefenster.anfrage_text(
                spur, w, dauer, d.get("waehrung", "USD")))

        self.pruefe_verbesserer()

    def pruefe_verbesserer(self):
        """Schickt einen offenen Verbesserungsvorschlag per Telegram und
        markiert ihn ANGEFRAGT - aber nur, wenn nirgends eine Freigabe-Anfrage
        offen ist. Die Freigabe hat immer Vorrang: eine unbeantwortete
        Freigabe-Anfrage darf nicht neben einer Verbesserer-Anfrage stehen,
        sonst weiss ein /ja nicht, was es meint.

        Faellt der verbesserer/-Import aus oder wirft die Ordner-/Textlogik,
        bleibt es bei einer Protokollzeile - der Zyklus laeuft weiter.
        """
        if verbesserer_anfrage is None:
            return
        if any(freigabefenster.lade(s).anfrage_offen() for s in SPUREN):
            return
        try:
            offen = verbesserer_anfrage.offener_vorschlag(VERB_BERICHTE)
            if not offen:
                return
            self.sende(verbesserer_anfrage.text(offen))
            verbesserer_anfrage.markiere_angefragt(offen)
            protokoll("Verbesserer-Anfrage %s" % offen.name)
        except Exception as e:                            # noqa: BLE001
            protokoll("Verbesserer-Anfrage gescheitert: %s" % e)

    def _spur_konf(self, schluessel):
        """Eintrag aus verbesserer/spuren.json zu ``schluessel`` (z. B.
        ``spur1``), mit ``wachen``/``bewertung_datei`` (und den weiteren
        Pfadfeldern, falls vorhanden) absolut gegen den verbesserer/-Ordner
        aufgeloest - so, wie anwenden.anwenden sie erwartet."""
        with open(os.path.join(VERB_DIR, "spuren.json"), encoding="utf-8") as f:
            eintrag = dict(json.load(f)[schluessel])
        for k in ("wachen", "bewertung_datei", "journal", "zustand",
                  "berichte"):
            if k in eintrag:
                eintrag[k] = str((Path(VERB_DIR) / eintrag[k]).resolve())
        return eintrag

    def nur_fenster_fehlt(self, spur, d):
        """wachen.json der Spur, wenn allein das Freigabefenster noch fehlt.

        Sonst None. Die Spur sagt selbst, was sie sperrt - gefragt wird ihr
        eigenes handeln.py, nicht eine zweite Liste hier, die auseinander
        laufen koennte.
        """
        ordner = os.path.join(HIER, d["ordner"])
        try:
            p = subprocess.run([PYTHON, "handeln.py", "--vorschau"],
                               cwd=ordner, capture_output=True, text=True,
                               timeout=600, env=dict(os.environ,
                                                     MAXHIRN_ROUTINE="1"))
        except Exception:                                # noqa: BLE001
            return None
        zeile = ""
        for z in (p.stdout or "").splitlines():
            if "gesperrt durch" in z or "gesperrt:" in z:
                zeile = z
                break
        if not zeile:
            return None
        # Genau eine Sperre, und zwar das Fenster.
        gruende = [g.strip() for g in zeile.split(":", 1)[-1].split(";")]
        if len(gruende) != 1 or "Freigabefenster" not in gruende[0]:
            return None
        try:
            with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _verbesserer_befehl(self, ja):
        """/ja bzw. /nein fuer einen wartenden Verbesserungsvorschlag.

        Rueckgabe: Antworttext, wenn der Fall behandelt wurde - sonst None,
        dann laeuft die Freigabe-Logik im Aufrufer unveraendert weiter.

        Nur aktiv, wenn der verbesserer/-Import steht UND nirgends eine
        Freigabe-Anfrage offen ist: ein wartendes Freigabefenster scharf zu
        schalten geht immer vor. anwenden.anwenden wirft nie; anfrage.wartet
        und die Ordnerlogik schon - beides faengt der try/except hier ab,
        damit der Befehl den Lauf nicht mitreisst.
        """
        if verbesserer_anfrage is None or verbesserer_anwenden is None:
            return None
        if any(freigabefenster.lade(s).anfrage_offen() for s in SPUREN):
            return None
        try:
            wartet = verbesserer_anfrage.wartet(VERB_BERICHTE)
            if not wartet:
                return None
            if not ja:
                verbesserer_anwenden.ablehnen(wartet, "per /nein abgelehnt")
                protokoll("Verbesserungsvorschlag abgelehnt: %s" % wartet.name)
                return "Vorschlag archiviert (%s)." % wartet.name
            schluessel = wartet.name.split("-", 3)[-1]
            r = verbesserer_anwenden.anwenden(
                wartet, self._spur_konf(schluessel), REPO_WURZEL)
        except Exception as e:                            # noqa: BLE001
            protokoll("Verbesserer-Befehl gescheitert: %s" % e)
            return "Vorschlag NICHT verarbeitet: %s" % e
        if r["ok"]:
            protokoll("Verbesserungsvorschlag angewandt: %s" % r["commit"])
            return "Vorschlag angewandt: %s" % r["commit"]
        return "Vorschlag NICHT angewandt: %s" % r["grund"]

    # --- Befehle --------------------------------------------------------

    def befehl(self, text):
        wort = text.split()[0].lower().lstrip("/")
        rest = text.split()[1:]

        if wort in ("ja_xperp", "nein_xperp", "stop_xperp", "freigabe_xperp"):
            f = freigabefenster.lade("xperp")
            if wort == "freigabe_xperp":
                with open(os.path.join(HIER, "xperp", "wachen.json"), encoding="utf-8") as datei:
                    w = json.load(datei)
                if not f.anfrage_offen():
                    return ("XPERP: %s. Keine wartende Anfrage.\n"
                            "handel_erlaubt=%s, freigabe.erfuellt=%s.\n"
                            "Nur der Dauerlauf stellt nach Sperrenpruefung eine Anfrage. SWAP bleibt gesperrt."
                            % (f.text(), w.get("handel_erlaubt"), w.get("freigabe", {}).get("erfuellt")))
                return freigabefenster.anfrage_text("xperp", w, f.d.get("anfrage_dauer_minuten", 60)).replace("/ja", "/ja_xperp").replace("/nein", "/nein_xperp")
            if wort in ("nein_xperp", "stop_xperp"):
                freigabefenster.schliessen("xperp", "Telegram " + wort)
                return "XPERP-Fenster geschlossen. Keine neuen Live-Einstiege; keine Position glattgestellt. Spot unveraendert."
            import math
            try:
                h = float(rest[0]) if len(rest) == 1 else None
                if h is None or not math.isfinite(h) or not 0 < h <= freigabefenster.MAX_STUNDEN:
                    raise ValueError
            except ValueError:
                return "Syntax: /ja_xperp STUNDEN (groesser 0, hoechstens 24). Erst /freigabe_xperp lesen."
            m = freigabefenster.oeffnen("xperp", h, "telegram/xperp")
            if m is None:
                return "Keine aktuelle XPERP-Anfrage. Nichts freigegeben; Spot unveraendert."
            protokoll("FREIGABE xperp fuer %s min" % m)
            return "XPERP-Fenster fuer %g h offen; alle Wachen gelten weiter. Spot unveraendert. /stop_xperp schliesst das Fenster." % h

        if wort == "prognose":
            return "Bitte im SkillsBot: /prognose [N]. Die Marktanalyse darf hier weder Stop-Befehle noch den Handelszyklus blockieren."
        if wort == "papierstatus":
            import handel_befehle
            return handel_befehle.status(papier=True)

        if wort in ("lage", "status"):
            return tagesbericht.baue(mit_xperp=False)

        if wort == "bericht":
            return tagesbericht.baue(mit_xperp=True)

        if wort == "scan":
            return self.scan_kurz()

        if wort == "ja":
            stunden = None
            if rest:
                try:
                    stunden = float(rest[0])
                except ValueError:
                    return "Verstehe ich nicht: /ja %s\nGemeint war /ja 6" % rest[0]
            # Ein wartender Verbesserungsvorschlag wird hier abgefangen -
            # aber nur, wenn keine Freigabe-Anfrage offen ist (die gewinnt).
            v = self._verbesserer_befehl(ja=True)
            if v is not None:
                return v
            for spur in SPUREN:
                if freigabefenster.lade(spur).anfrage_offen():
                    m = freigabefenster.oeffnen(spur, stunden, "telegram")
                    if m:
                        protokoll("FREIGABE %s fuer %d min" % (spur, m))
                        return ("<b>%s ist scharf</b> fuer %d:%02d h.\n"
                                "Es gelten die Grenzen aus wachen.json.\n"
                                "/stop schliesst sofort." % (spur, m // 60, m % 60))
            return "Keine Anfrage offen. Eine Freigabe geht nur auf Anfrage."

        if wort == "nein":
            v = self._verbesserer_befehl(ja=False)
            if v is not None:
                return v
            for spur in SPUREN:
                if freigabefenster.lade(spur).anfrage_offen():
                    freigabefenster.schliessen(spur, "abgelehnt")
                    return "Abgelehnt. %s bleibt auf Papier." % spur
            return "Keine Anfrage offen."

        if wort in ("stop", "notaus"):
            w = freigabefenster.alles_schliessen("Befehl /stop")
            protokoll("NOTAUS: %s" % (", ".join(w) or "nichts war offen"))
            return ("<b>Alles auf Papier.</b>\n%s" %
                    ("Geschlossen: " + ", ".join(w) if w
                     else "Es war ohnehin nichts scharf."))

        if wort == "pause":
            self.pausiert = True
            return "Zyklus ausgesetzt. /weiter setzt fort."

        if wort == "weiter":
            self.pausiert = False
            return "Zyklus laeuft wieder."

        if wort in ("hilfe", "start", "help"):
            return self.hilfe()

        return "Unbekannt: %s\n\n%s" % (text[:40], self.hilfe())

    def hilfe(self):
        stand = []
        for spur in SPUREN:
            stand.append("  %-9s %s" % (spur, freigabefenster.lade(spur).text()))
        return ("<b>Befehle</b>\n"
                "/lage      Positionen und Sperren\n"
                "/bericht   voller Tagesbericht\n"
                "/scan      Rangliste neu rechnen\n"
                "/freigabe_xperp - XPERP-Anfrage und Grenzen lesen\n"
                "/ja_xperp STUNDEN - nur XPERP freigeben (max. 24 h)\n"
                "/nein_xperp /stop_xperp - nur XPERP-Fenster schliessen\n"
                "/papierstatus - gespeicherter Papierstand\n"
                "Prognose im SkillsBot: /prognose [N]\n"
                "/ja [h]    wartende Freigabe erteilen\n"
                "/nein      ablehnen\n"
                "/stop      alles zu, zurueck auf Papier\n"
                "/pause /weiter\n\n"
                "<b>Jetzt</b>\n%s\n"
                "  Zyklen %d, Fehler %d, Takt %d min"
                % ("\n".join(stand), self.zyklen, self.fehler, self.takt))

    def scan_kurz(self):
        try:
            x = tagesbericht.spur_xperp(anzahl=4)
        except Exception as e:                           # noqa: BLE001
            return "Scan gescheitert: %s" % e
        if "fehler" in x["spitzen"]:
            return "Scan gescheitert: %s" % x["spitzen"]["fehler"][:200]
        z = ["<b>Rangliste</b>  %s" % jetzt().strftime("%H:%M")]
        for zweck, titel in (("long", "Long"), ("short", "Short"),
                             ("grid", "Grid")):
            teile = []
            for b in x["spitzen"].get(zweck, []):
                kz = {"krypto": "K", "aktie": "A", "rohstoff": "R"}[b["kategorie"]]
                warn = "!" if (b["vola"] > b["tor"] or b["deckel"] < 5) else ""
                teile.append("%s·%s %.0f%s" % (b["basis"], kz, b["punkte"], warn))
            z.append("%-6s %s" % (titel, "  ".join(teile)))
        z.append("\n! = ein Tor ist zu (Vola oder Hebel-Deckel)")
        return "\n".join(z)

    # --- Schleife -------------------------------------------------------

    def start(self):
        protokoll("Dauerlauf startet, Takt %d min%s" % (
            self.takt, ", trocken" if self.trocken else ""))

        if not self.trocken and not melder.bereit():
            protokoll("Melder nicht eingerichtet (%s) - laeuft stumm weiter"
                      % melder.fehlt())
        elif not self.trocken:
            # Wartende Nachrichten wegwerfen: Ein /ja von gestern Nacht ist
            # keine Freigabe fuer heute frueh.
            try:
                self.zeiger = melder.leeren()
            except Exception as e:                       # noqa: BLE001
                protokoll("Telegram beim Start nicht erreichbar: %s" % e)
            self.sende("<b>Dauerlauf gestartet</b>\n%s" % self.hilfe(),
                       stumm=True)

        while True:
            try:
                self.runde()
            except KeyboardInterrupt:
                protokoll("Beendet (Strg+C)")
                self.sende("<b>Dauerlauf beendet.</b> Alle Spuren auf Papier.",
                           stumm=True)
                # Kein Fenster ueberlebt den Lauf, der es bewacht. Eine
                # Freigabe, die noch offen stuende, waere unbewacht scharf -
                # genau der Fall, den Bedingung 3 (Herzschlag) faengt, nur
                # eben erst beim naechsten Start.
                freigabefenster.alles_schliessen("Dauerlauf beendet")
                try:
                    os.remove(os.path.join(HIER, "dauerlauf.pid"))
                except OSError:
                    pass
                return 0
            except Exception:                            # noqa: BLE001
                self.fehler += 1
                protokoll("Runde gescheitert:\n%s" % traceback.format_exc())
                time.sleep(30)

    def runde(self):
        # 1. Befehle
        if not self.trocken and melder.bereit():
            try:
                nachrichten, self.zeiger = melder.hole(self.zeiger, warten=20)
            except Exception as e:                       # noqa: BLE001
                protokoll("Telegram: %s" % e)
                nachrichten = []
                time.sleep(10)
            for n in nachrichten:
                protokoll("Befehl: %s" % n["text"][:60])
                try:
                    antwort = self.befehl(n["text"])
                except Exception as e:                   # noqa: BLE001
                    antwort = "Der Befehl ist gescheitert: %s" % e
                    protokoll("Befehl gescheitert:\n%s" % traceback.format_exc())
                self.sende(antwort)
        else:
            time.sleep(min(20, self.takt * 60))

        # 2. Zyklus faellig?
        if not self.pausiert:
            faellig = (self.letzter_zyklus is None or
                       (jetzt() - self.letzter_zyklus).total_seconds()
                       >= self.takt * 60)
            if faellig:
                self.zyklus()

        # 3. Tagesbericht faellig? Einmal am Tag, ab 8 Uhr.
        heute = jetzt().date()
        if (self.letzter_bericht != heute and jetzt().hour >= 8):
            self.letzter_bericht = heute
            protokoll("Tagesbericht")
            try:
                self.sende(tagesbericht.baue(mit_xperp=True))
            except Exception as e:                       # noqa: BLE001
                self.sende("<b>Tagesbericht gescheitert</b>\n%s" % e)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--takt", type=int, default=TAKT_MAX_MINUTEN,
                   help="Minuten zwischen zwei Zyklen (Vorgabe %d; der "
                        "Herzschlag von Spur 2 liegt bei 30 und begrenzt "
                        "das nach oben)" % TAKT_MAX_MINUTEN)
    p.add_argument("--trocken", action="store_true",
                   help="nichts senden, alles auf die Konsole")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.takt > TAKT_MAX_MINUTEN:
        # Nicht stillschweigend korrigieren: Wer einen groesseren Takt
        # setzt, soll erfahren, warum er ihn nicht bekommt.
        print("Takt %d min liegt ueber dem Herzschlag von Spur 2 (30 min) - "
              "jeder Zyklus wuerde flach stellen. Es gilt %d min."
              % (a.takt, TAKT_MAX_MINUTEN))
        a.takt = TAKT_MAX_MINUTEN

    with ereignis.lauf("handel/dauerlauf"):
        return Lauf(a.takt, a.trocken).start()


if __name__ == "__main__":
    raise SystemExit(main())
