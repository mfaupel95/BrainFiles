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

Die SWAP-Spur laeuft daneben mit, seit 12.09.2026 mit demselben Live-Pfad
wie xperp: handeln.py hat die sieben Sperren und wird nur bei offenem
Freigabefenster scharf. Ihr Zustand und ihr Journal sind das, was der
Tagesbericht und /status von ihr zeigen.

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
  /lage        JETZT: offene Positionen je Spur, Live-Tore, Freigaben
  /bericht     der volle Tagesbericht (mit Rangliste)
  /spuren      alle Spur-Namen
  /spur NAME   eine Spur in der Tiefe (Positionen, Wachen, Journal)
  /strategien  Bilanz aller Strategien nebeneinander
  /indikatoren die vier Indikator-Spuren: Signale und Treffer
  /markt       Kurs, 24 h, Trend, Volatilitaet (Beobachtung)
  /scan        Rangliste neu rechnen
  /ja [h]      wartende Freigabe erteilen (Vorgabe: die angefragte Dauer)
  /nein        wartende Freigabe ablehnen
  /stop        alle Fenster zu, zurueck auf Papier
  /pause       Zyklus aussetzen, Meldungen laufen weiter
  /weiter      Zyklus fortsetzen
  /hilfe       diese Liste

Der Text der Befehle steht in befehle.py - dort, wo ihn auch der SkillsBot
liest (eine Quelle, zwei Bots). /lage und /bericht sind seit 15.09.2026
verschiedene Auskuenfte: /lage zeigt den Zustand, /bericht die Geschichte.

Aufruf:
    python dauerlauf.py                 # laeuft, bis Strg+C
    python dauerlauf.py --takt 15       # anderer Zyklus-Takt
    python dauerlauf.py --trocken       # nichts senden, nur Konsole
    python dauerlauf.py --risiko mittel # zweiter Lauf, doppelte Betraege

RISIKOSTUFEN (--risiko, seit 15.09.2026)
---------------------------------------
Derselbe Lauf, derselbe Code, nur ein Faktor auf die Betraege: `niedrig`
(1.0, die Vorgabe), `mittel` (2.0), `hoch` (4.0). Der Zweck ist nicht mehr
Gewinn, sondern mehr Beobachtungen je Zeiteinheit - bei 20-EUR-Einsaetzen
dauert jede Statistik Monate. Siehe Handel/risikostufe.py.

Der Schalter wird als `HANDEL_RISIKO` gesetzt, BEVOR der erste Zyklus laeuft:
daraus leitet jede Spur ihren Faktor und den Dateinamen-Zusatz ab
(zustand.mittel.json, handelsjournal.mittel.csv). Der Basislauf bleibt
unberuehrt - ohne die Stufe aendert sich nichts.

Eine Stufe laeuft ausdruecklich als DATENSAMMLER:

  * immer `--papier`, nie `--live`, auch bei offenem Freigabefenster. Der
    Faktor wuerde sonst echtes Geld vervielfachen, und das Buch dieser Stufe
    ist getrennt - niemand saehe die Positionen in der Auswertung.
  * kein Telegram: kein Senden, kein Abholen von Befehlen, keine
    Freigabe-Anfrage. Zwei Laeufe an einem Bot wuerden sich die Nachrichten
    gegenseitig wegschnappen, und ein `/ja` waere nicht mehr zuzuordnen.
  * kein Schliessen der Freigabefenster beim Beenden: die Fenster gehoeren
    dem Basislauf.
  * der Spiegel laeuft nur in der Basis (Vorgabe Max): er hat in jeder Stufe
    denselben Einsatz, ein zweites Buch waere dieselbe Beobachtung noch
    einmal - und beide Laeufe schrieben in dieselben Dateien.
"""

import argparse
import datetime as dt
import json
import math
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

import befehle                                             # noqa: E402
import ereignis                                           # noqa: E402
import freigabefenster                                   # noqa: E402
import lage                                              # noqa: E402
import melder                                            # noqa: E402
import risikostufe                                       # noqa: E402
import schnappschuss                                      # noqa: E402
import sperre                                            # noqa: E402
import tagesbericht                                      # noqa: E402
import wochenbericht                                      # noqa: E402

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
except Exception as _e:                                  # noqa: BLE001
    verbesserer_anfrage = None
    verbesserer_anwenden = None
    # Nicht lautlos: ein kaputter Import schaltete den Anfrage-Typ bisher ab,
    # ohne dass es jemand erfuhr (Review 09.10.2026). Der Grund bleibt hier
    # stehen und wird beim Start gemeldet (verbesserer_import_melden).
    VERB_IMPORT_FEHLER = "%s: %s" % (type(_e).__name__, _e)
else:
    VERB_IMPORT_FEHLER = None


def verbesserer_import_melden():
    """Meldet einmal beim Start, wenn verbesserer/ nicht geladen werden konnte.

    Der Dauerlauf laeuft ohne den Selbstverbesserungs-Typ weiter - das bleibt
    so -, aber der Ausfall steht jetzt im Log und im Bus. Wirft nie.
    """
    if not VERB_IMPORT_FEHLER:
        return False
    text = ("verbesserer/ nicht geladen (%s) - der Dauerlauf laeuft ohne "
            "Selbstverbesserungs-Anfragen weiter" % VERB_IMPORT_FEHLER)
    print(text, file=sys.stderr)
    try:
        ereignis.hinweis("handel/dauerlauf", text)
    except Exception:                                    # noqa: BLE001
        pass
    return True

PYTHON = os.path.join(HIER, "scanner", ".venv", "Scripts", "python.exe")

# Sekunden, die EIN Zyklus EINER Spur dauern darf, bevor der Dauerlauf ihn
# abbricht. Der Wert ist keine Schaetzung, sondern eine Obergrenze mit Grund:
# er MUSS ueber dem Zeitlimit des Freigabefensters liegen (scanner, kraken,
# mosaic und moondev_marktlage fuehren FREIGABE_ZEITLIMIT_S = 600). Sonst
# toetet der Timeout einen Lauf, der korrekt auf eine Freigabe wartet, statt
# sie abzulehnen - und mit ihm die Spiegelung nach Q: (Bedingung 4).
# Genau das passierte am 21.09.2026, als das Zeitlimit von 120 auf 600 s ging
# und der Timeout bei 300 s stehen blieb: scanner lief ab 19:22 in jedem
# Zyklus in den Abbruch, das Journal wuchs lokal weiter, Q: stand still.
# Festgehalten von tests/test_zyklus_zeitgrenze.py.
TIMEOUT_S = 700

# Spuren, die dieser Lauf fuehrt.
#
# Spur 2 (xperp) ist seit 03.09.2026 der Hauptweg und hat seit demselben Tag
# einen Live-Pfad - vorher legte bot.py nur vor. Sie steht zuerst.
#
# Spur 3 (Kraken) wurde am 03.09.2026 stillgelegt und laeuft seit dem
# 14.09.2026 wieder als Papier - deshalb steht sie wieder hier, im selben Takt
# wie die uebrigen. Ihre Rangliste bleibt ein Tagesstand: scan.py laeuft weiter
# einmal taeglich (Aufgabe MaxHirn-Kraken-Spur3), gehandelt wird nur hier -
# zwei Schreiber auf denselben Zustand waren der Fehler bei xperp (Aufgabe
# MaxHirn-XPERP-Spur2, am 14.09.2026 abgeschaltet). Den Einstand nimmt ihre
# Einstiegsrechnung vom lebenden Kurs; der Bericht waehlt aus.
# Grund und Zahlen der Stilllegung: kraken/wachen.json, _stillgelegt_grund.
# SWAP laeuft mit demselben Live-Pfad wie xperp: handeln.py hat die sieben
# Sperren, der letzte Grund traegt das Wort Freigabefenster (geprueft in
# swap/tests/test_handeln_papier.py). pruefe_anfragen() fragt nur, wenn
# ausschliesslich das Fenster fehlt. Ein Zyklus kostet trotzdem Zeit: die
# Rangliste bewertet bis zu 60 SWAP-Reihen und ist zwei Stunden gueltig
# (SCAN_ALTER_MINUTEN).
# SPIEGEL (Papierbuch fuer Copy-Trading, angelegt 12.09.2026): liest den
# OnchainOS-Feed und bucht nach, was Nachahmen gekostet haette. Kein Live-Zweig,
# keine Orderfunktion - ihr --live verweigert mit einem Grund, den
# nur_fenster_fehlt() nicht als Fenster-Bitte liest (anders als bei swap: die
# Spur hat seit 12.09.2026 einen Live-Pfad, ihre Sperrgruende nennen deshalb das
# Freigabefenster und der Lauf darf fragen). Sie braucht kein eigenes venv (nur
# Standardbibliothek plus das onchainos-CLI auf dem PATH).
# OMNIQUANT (Papierbuch auf dem Prognose-Bericht, angelegt 13.09.2026): handelt
# die Treffer aus prognose_berichte/neuester.json als Papierpositionen (gleiche
# Idee wie omniquant.trade, aber eigene Daten und eigene Kontrolle). Kein
# Live-Zweig wie spiegel: --live verweigert, das Wort Freigabefenster kommt in
# keinem Sperrgrund vor, der Lauf fragt nie. Liest nur den Bericht und OKX-Kurse.
# NAUTILUS (OKX-DEMO-Node, angelegt 13.09.2026): startet je Zyklus eine
# begrenzte Node-Session (~30 s), sammelt BTC-USDT-SWAP-Quotes vom oeffentlichen
# Websocket und schreibt damit Herzschlag und Journal. Papierfest wie spiegel/
# omniquant - der Node hat keinen Live-Zweig (Schluessel read_only, keine
# IP-Whitelist fuer Orders). Braucht sein EIGENES venv (nautilus/.venv), dort
# liegt nautilus_trader; das Feld "python" traegt den Interpreter.
SPUREN = {
    "xperp":   {"ordner": "xperp",   "waehrung": "USD"},
    "scanner": {"ordner": "scanner", "waehrung": "USD"},
    # SWAP AUS seit 10.10.2026 (Hermes, Auftrag Max "alles sinnvolle"): 12
    # Runden, 17 % Treffer, netto -3.90 %, verfehlt eigenes Freigabe-Bar
    # ">=8 Runden, netto positiv". handel_erlaubt war seit 27.09. false; jetzt
    # ganz aus dem Dauerlauf. Journal bleibt als Vergleichsbuch stehen.
    # WIEDER ANSCHALTEN: die Zeile hier re-einkommentieren, swap aus
    # AUTO_FREIGABE wieder aufnehmen, und in swap/zustand.json "letzter_lauf"
    # auf jetzt setzen.
    # "swap":    {"ordner": "swap",    "waehrung": "USD"},
    # SPIEGEL AUS seit 21.09.2026 (Max: "spiegel Spuren erstmal deaktivieren").
    # Die drei Arme laufen nicht mehr; ihre Buecher bleiben als
    # Vergleichsgrundlage stehen, wachsen aber nicht weiter.
    # WIEDER ANSCHALTEN: die Zeilen hier und in NUR_BASIS wieder einkommentieren
    # UND vorher in spiegel/zustand.json, zustand.knapp.json und
    # zustand.weit.json "letzter_lauf" auf jetzt setzen - sonst gilt der
    # Herzschlag nach mehr als 180 Minuten als alt und der erste Zyklus stellt
    # alle offenen Papierpositionen flach (spiegel.py, flach_stellen
    # "herzschlag_alt"). Ohne diesen Schritt waeren die Vergleichsbuecher weg.
    # SPIEGEL KOMPLETT AUS (Max, 01.10.2026: "spiegel spuren komplett raus
    # nehmen. eh absolut nicht profitabel"). Die drei Buecher bleiben als
    # Vergleichsgrundlage auf der Platte (60 Positionen je Arm), wachsen aber
    # nicht weiter. WIEDER ANSCHALTEN: die Zeilen hier und in NUR_BASIS
    # einkommentieren UND vorher in spiegel/zustand.json, zustand.knapp.json
    # und zustand.weit.json "letzter_lauf" auf jetzt setzen - sonst haelt der
    # erste Zyklus den Herzschlag fuer alt und stellt alle offenen
    # Papierpositionen flach (spiegel.py, flach_stellen "herzschlag_alt").
    # "spiegel": {"ordner": "spiegel", "waehrung": "USD",
    #             "skript": "spiegel.py"},
    # KOPIER (Papierbuch auf der Pump.fun-Rangliste, angelegt 14.09.2026):
    # kopiert die Top-Trader der taeglichen PnL-Rangliste (user-portfolio als
    # Positions-Spiegel, trades/batch als Signal-Bestätigung). Kein Live-Zweig
    # wie spiegel - lesen.py kennt keine Schreibpfade. Reine
    # Standardbibliothek (urllib), laeuft unter dem scanner-venv.
    # KOPIER AKTIV (seit 30.09.2026, Parallelsitzung hat die Eintraege aktiviert).
    # Beide laufen als Papierspuren; der Kommentar ist auf den aktuellen Stand
    # gezogen. AUSSCHALTEN: die Zeilen hier auskommentieren UND vorher
    # in kopier/zustand.json ("letzter_lauf") auf jetzt setzen, sonst
    # stellt der erste Zyklus offene Papierpositionen flach.
    "kopier":  {"ordner": "kopier", "waehrung": "USD",
                "skript": "kopier.py"},
    # KOPIER1ZU1 (Papierbuch, angelegt 15.09.2026): zweite Copy-Trade-Spur,
    # die auf TRADE-Ereignissen arbeitet (trades/batch) statt auf einem
    # Portfolio-Diff. Jeder Kauf des Vorbilds oeffnet eine Papier-Position,
    # jeder Verkauf schliesst sie sofort. Kein Live-Zweig - teilt lesen.py
    # mit kopier/ und liest verfolgte.json aus kopier/ (kein zweiter
    # Rangliste-Abruf).
    "orbk":    {"ordner": "orbk",    "waehrung": "USD",
                "skript": "handeln.py"},
    # ORB AUF OKX-PERPETUALS (angeschlossen 21.09.2026, Auftrag Max: "orb
    # aktivieren"). Dieselbe Strategie wie orbk, andere Boerse: BTC-/ETH-USDT-
    # SWAP, 00:00-UTC-Tagesgrenze, USDT. Papier ohne Live-Pfad; der eigene
    # Backtest ist fuer BEIDE Instrumente negativ (EV -45.1 bzw. -3.7 Pkt je
    # Runde, nachrechenbar mit orb/backtest.py), deshalb laeuft die Spur nur,
    # um den gemessenen Erwartungswert an laufenden Kursen zu beobachten -
    # handel_erlaubt bleibt false und freigabe.backtest_bestanden auch.
    "orb":     {"ordner": "orb",     "waehrung": "USDT",
                "skript": "handeln.py"},
    "omniquant": {"ordner": "omniquant", "waehrung": "USD",
                  "skript": "handeln.py"},
    # Schattenarm 'weit' (24.09.2026): dasselbe Buch, aber die weiche
    # Prognose-Fassung (prognose.weit.json -> neuester.weit.json).
    # AUS DEM DAUERLAUF GENOMMEN am 24.09.2026, Auftrag Max "Omniquant auf
    # Papier auf weit stellen": der HAUPTARM liest die weite Fassung jetzt
    # selbst (wachen.json prognose_fassung=weit), damit die Spur nicht zweimal
    # dieselben Signale in zwei Buecher bucht. Die Arm-Dateien
    # (wachen.weit.json, zustand.weit.json, handelsjournal.weit.csv) und die
    # Spiegelung Q:\Handel_Journal\omniquant_weit bleiben als Aufzeichnung
    # stehen, sie wachsen nicht weiter. Wieder einschalten: Zeilen
    # einkommentieren UND vorher in zustand.weit.json 'letzter_lauf' auf jetzt
    # setzen - sonst stellt der erste Zyklus alles als 'herzschlag_alt' flach.
    # "omniquant_weit": {"ordner": "omniquant", "waehrung": "USD",
    #                    "skript": "omniquant_weit.py"},
    "nautilus": {"ordner": "nautilus", "waehrung": "USD",
                 "skript": "handeln.py",
                 "python": os.path.join(HIER, "nautilus", ".venv",
                                        "Scripts", "python.exe")},
    # KRAKEN-SPUREN (19.09.2026): zwei Varianten der Nautilus-Trailing-
    # Strategie auf Kraken. Spot (BTC/EUR, EUR, kein Hebel, gebuehrfrei bis
    # 10k via Pro-Abo) und Futures (PF_XBTUSD Perpetual, USD, Hebel). Beide
    # Papier, kein Live-Orderpfad. Nutzen das nautilus-venv (nautilus_trader).
    "nautilus_kraken": {"ordner": "nautilus_kraken", "waehrung": "EUR",
                        "skript": "handeln.py",
                        "python": os.path.join(HIER, "nautilus", ".venv",
                                               "Scripts", "python.exe")},
    "nautilus_kraken_futures": {"ordner": "nautilus_kraken", "waehrung": "USD",
                        "skript": "handeln_futures.py",
                        "python": os.path.join(HIER, "nautilus", ".venv",
                                               "Scripts", "python.exe")},
    # EMACROSS (angelegt 03.10.2026, Auftrag Max "EMA-Spur bauen"): die
        # Originalstrategie aus nautilus_trader (develop, docs/tutorials/
    # ema_cross.py, EMA 10/20, long und short mit Umkehr beim Kreuz). Sie
    # steht als EIGENE Spur neben den drei Armen, die Kopier-Signale als
    # BTC-Proxy buchen - sie ist der Vergleich, nicht deren Umbau.
    # Rechnet auf abgeschlossenen 1H-Kerzen ueber scanner/okx, braucht
    # darum KEIN nautilus-venv: nur die Regel stammt von dort.
    "nautilus_emacross": {"ordner": "nautilus_emacross", "waehrung": "USDT",
                          "skript": "handeln.py"},
    # Die Gitter-Spur braucht kein eigenes venv: sie liest OKX-Kerzen ueber
    # scanner/okx und rechnet die Stufen mit Handel/grid.py - beides liegt im
    # gemeinsamen venv.
    "gitter":  {"ordner": "gitter",  "waehrung": "USDT",
                "skript": "handeln.py"},
    # VIER INDIKATOR-SPUREN (angelegt 15.09.2026, selben Tag angeschlossen):
    # ein Signal auf einem Indikator, ATR-Stop, Ziel x Stop, Papier ohne
    # Live-Zweig wie spiegel. Kein eigenes venv.
    "macd_mtf": {"ordner": "macd_mtf", "waehrung": "USD",
               "skript": "handeln.py"},
    # SQUEEZE AUS seit 10.10.2026 (Hermes, Auftrag Max "alles sinnvolle"):
    # Parameter-Suche (optimieren.py, 9 Kandidaten) fand keinen Kandidaten - die
    # Spur ist von keinem Stop/Ziel-Wert behebbar, Live netto -0.72 % (15 Runden).
    # Haupt- und Schattenarm (squeeze_eth) gehen zusammen raus.
    # WIEDER ANSCHALTEN: beide Zeilen re-einkommentieren und in
    # squeeze/zustand.json "letzter_lauf" auf jetzt setzen.
    # "squeeze": {"ordner": "squeeze", "waehrung": "USD",
    #             "skript": "handeln.py"},
    # "squeeze_eth": {"ordner": "squeeze", "waehrung": "USD",
    #                 "skript": "squeeze_eth.py"},
    # Schattenarm squeeze_eth (03.10.2026, Auftrag Max "Schattenarm"):
    # dieselbe Regel fest auf ETH, Hauptarm unveraendert als Vergleich.
    # SUPERTREND AUS seit 18.10.2026 (Hermes, Auftrag Max "beide stilllegen"):
    # Parameter-Suche (optimieren.py, 9 Kandidaten) fand keinen Kandidaten -
    # die Spur ist von keinem Stop/Ziel-Wert behebbar, Live netto -0.11 %
    # (10 Runden), Backtest +0.116 %/Runde grenzwertig. Journal bleibt als
    # Vergleichsbuch stehen.
    # WIEDER ANSCHALTEN: die Zeile hier re-einkommentieren und in
    # supertrend/zustand.json "letzter_lauf" auf jetzt setzen.
    # "supertrend": {"ordner": "supertrend", "waehrung": "USD",
    #               "skript": "handeln.py"},
    "wavetrend": {"ordner": "wavetrend", "waehrung": "USD",
                 "skript": "handeln.py"},
    # MOSAIC (Mehr-Zeitrahmen-Preisaktion, angelegt 15.09.2026):
    # Top-Down: 4H-Bias (gruene Kerze), 30M-Pullback zur Nachfragezone
    # (Swing-Tiefs), 5M-Structure-Shift (BOS). Nur LONG verdrahtet,
    # Papier ohne Live-Zweig. Kein eigenes venv.
    "mosaic": {"ordner": "mosaic", "waehrung": "USD",
               "skript": "handeln.py"},
    # Kraken (EUR, Spot, kein Hebel) braucht kein eigenes venv: scan.py und
    # handeln.py laufen unter dem scanner-venv. Ihr Herzschlag steht auf 180
    # Minuten statt auf 30 wie bei xperp: ein Rechnerneustart soll die
    # Papierpositionen nicht flachstellen (kraken/wachen.json, _herzschlag).
    "kraken": {"ordner": "kraken", "waehrung": "EUR"},
    # SPIEGEL-SCHATTENBUECHER (18.09.2026, V1 Ausstiegsgeometrie): fahren
    # dieselbe Signalquelle wie spiegel mit anderen Stop/Trailing-Parametern
    # (wachen.knapp.json / wachen.weit.json). Die Launcher setzen HANDEL_BUCH
    # und rufen spiegel.py - alle Buchdateien tragen dann das Suffix .knapp
    # bzw. .weit, das Hauptbuch bleibt unveraendert (Vergleichsgrundlage).
    # SPIEGEL-SCHATTENBUECHER AUS seit 21.09.2026, siehe oben bei "spiegel".
    # SPIEGEL-SCHATTENBUECHER AUS, siehe oben bei "spiegel" (01.10.2026).
    # "spiegel_knapp": {"ordner": "spiegel", "waehrung": "USD",
    #                   "skript": "spiegel_knapp.py"},
    # "spiegel_weit": {"ordner": "spiegel", "waehrung": "USD",
    #                  "skript": "spiegel_weit.py"},
    # MOONDEV_FUNDING (16.09.2026): Papierbuch auf den Funding-Extremen von
    # Hyperliquid. Die Zahlen liefert der geklonte Bot
    # (Werkstatt/moon-dev-ai-agents, src/nice_funcs_hl.get_funding_rates),
    # gerufen in DESSEN venv - kein Sprachmodell, kein Orderpfad, kein Live.
    # Die Spur laeuft unter dem gemeinsamen venv, weil sie selbst nur stdlib
    # braucht; fremde Pakete bleiben im Bot. Siehe moondev_funding/README.md.
    "moondev_funding": {"ordner": "moondev_funding", "waehrung": "USD",
                        "skript": "handeln.py"},
    # WEITERE BOT-SPUREN (16.09.2026): dieselbe Bauform, andere Quelle. Die
    # Daten kommen ueber die oeffentliche CoinGecko-/Binance-API
    # (Handel/moondev_daten.py), die Regel steht im Haus, das Buch fuehrt
    # Handel/spur_buch.py. Kein Sprachmodell, kein Live.
    #   listingarb  - grosse Coins, die bei Binance (noch) fehlen
    #   topmovers   - Momentum der letzten 24 h, ohne Ueberhitzung
    #   marktlage   - BTC-Regime aus Kurs und Marktbreite
    "moondev_listingarb": {"ordner": "moondev_listingarb", "waehrung": "USD",
                           "skript": "handeln.py"},
    "moondev_topmovers": {"ordner": "moondev_topmovers", "waehrung": "USD",
                          "skript": "handeln.py"},
    # TRENDWENDE-BTC (21.09.2026, Auftrag Max): SHORT, sobald der SuperTrend auf
    # 1H von aufwaerts auf abwaerts dreht UND der Schluss unter der EMA200
    # liegt. Papier, kein Live-Zweig (--live verweigert), Buch ueber
    # Handel/spur_buch.py wie die Feed-Spuren. Ein Instrument (BTC-USDT-SWAP),
    # ein Platz, Risiko 5 USD, Stop 4 %, Ziel 2R.
    "trendwende_btc": {"ordner": "trendwende_btc", "waehrung": "USD",
                       "skript": "handeln.py"},
    # LIQ_WAND (21.09.2026, Auftrag Max): handelt MIT dem Liquidations-
    # Cluster - zwangsgeschlossene Shorts sind Kaufdruck, geschlossene
    # Longs Verkaufsdruck. Wand = groesstes Preisband der letzten ~78 min
    # Zwangsschluesse (OKX oeffentlich). Papier, kein Live-Zweig.
    "liq_wand": {"ordner": "liq_wand", "waehrung": "USD",
                 "skript": "handeln.py"},
    # ROBINHOOD_RADAR (22.09.2026, Auftrag Max "Radar -papierspur"):
    # kopiert das GESCHEHEN (nicht die Rangliste) auf Robinhood Chain -
    # kaufen mindestens zwei bewertete Wallets (Score >= 60) denselben
    # Token im Fenster, ist das ein Signal. Quelle ist die SQLite des
    # Fremd-Repos fomo-robinhood-radar, NUR LESEND. Papier, kein
    # Orderweg (Robinhood Chain hat in diesem Haus keinen).
    "robinhood_radar": {"ordner": "robinhood_radar", "waehrung": "USD",
                        "skript": "handeln.py"},
    # JEV_TRADER (13.10.2026, parallele Sitzung): Papier-Spur ueber das
    # Block-Event-Log des jev-trader-Bots (Monad/Kuru). Liest die Datei,
    # bucht geschlossene Roundtrips als Journal. PAPIER-FEST, kein Live-Pfad.
    "jev_trader": {"ordner": "jev_trader", "waehrung": "USD",
                   "skript": "handeln.py"},
    # SCANNER_LLM (13.10.2026, parallele Sitzung): leichter Marktscanner +
    # LLM-Qualitaetsfilter (llm_lokal). Papier, handel_erlaubt=false.
    "scanner_llm": {"ordner": "scanner_llm", "waehrung": "USD",
                    "skript": "handeln.py"},
    # OMNITRADE (30.09.2026, Auftrag Max "nur noch omnitrade auf kraken handel
    # erlaubt"): spiegelt die POSITION der Rust-Laeufe in Werkstatt/omnitrade
    # (Statusdatei, gelesen ueber omnitrade_bridge.py) in ein eigenes Buch. Der
    # Rust-Lauf entscheidet (sein .omni-Skript), diese Spur fuehrt aus - im
    # Live-Zweig ueber den bewaehrten Kraken-Spot-Weg (boerse kraken,
    # kraken_quote USDC), weil omnitrade selbst nur binance und okx kennt
    # (live.rs:33 weist jedes andere --exchange ab). Weg B der Entscheidung
    # vom 30.09.2026: kein Kraken-Adapter in Rust (zweiter Schluessel, zweiter
    # Nonce-Zaehler neben dem Haus-Pool). Papier: handel_erlaubt=false.
    # Einstieg nur, wenn die Statusdatei frisch ist UND die PID lebt (eine
    # Leiche mit state=running lag am 30.09. zwei Stunden im Statusordner).
    "omnitrade": {"ordner": "omnitrade", "waehrung": "USD",
                  "skript": "handeln.py"},
    # OMNITRADE_FUTURES (30.09.2026, Auftrag Max "hebel x7 fuer den anfang"):
    # dasselbe Signal wie omnitrade, aber die Ausfuehrung laeuft auf Kraken
    # FUTURES mit Hebel 7 (wachen-Feld hebel) und ganzen Kontrakten
    # (PF_SOLUSD, 1 Kontrakt = 1 SOL). Eigene Spur, weil ein Buch EINE
    # Waehrung fuehrt - Futures rechnet USD, der Spot-Weg USDC. Papier:
    # handel_erlaubt=false, Hebel geht als leverage-Parameter je Order raus.
    "omnitrade_futures": {"ordner": "omnitrade_futures", "waehrung": "USD",
                          "skript": "handeln.py"},
    # SIGNALWELLE (20.09.2026): ehrliches Gegenstueck zu VIP-Signal-Kanaelen
    # (Anlass Screenshot NVDAUSDT Perpetual 10x) - 1h-Momentum, kein Hebel,
    # kein Live-Zweig. Siehe moondev_signalwelle/README.md.
    "moondev_signalwelle": {"ordner": "moondev_signalwelle", "waehrung": "USD",
                            "skript": "handeln.py"},
    # PROPHET-SIGNAL (02.10.2026, CryptoPredictions-Papier):
    # Saisonale Zerlegung + Trend-Prognose nach Facebook Prophet.
    # Das Paper zeigt Prophet als best performer (MAE 83 vs ARIMA 1009).
    # Diese Spur nutzt die Idee ohne externe Prophet-Installation
    # (NumPy-Kompatibilitaet): EMA30 Trend + Saisonalitaets-Erkennung.
    # Papier, kein Live-Zweig.
    "prophet_signal": {"ordner": "prophet_signal", "waehrung": "USD",
                        "skript": "handeln.py"},
    # KLASSIK-SPUREN (30.09.2026, Auftrag Max "neue Strategien und Spuren"): die
    # sechs Pine-Vorlagen (MaxHirn/Wiki/Handel/*.pine) plus zwei neue Regeln
    # und die LuxAlgo-S/R-Vorlage (klassik_sr_breaks, 02.10.2026) als
    # Papierspuren auf BTC/ETH/SOL-Perps, 4H. Eine Rechnung fuer
    # alle: Handel/klassik_regeln.py, Buch spur_buch.py. Kein Live-Zweig.
    "klassik_sma": {"ordner": "klassik_sma", "waehrung": "USD",
                    "skript": "handeln.py"},
    "klassik_ema": {"ordner": "klassik_ema", "waehrung": "USD",
                    "skript": "handeln.py"},
    "klassik_macd": {"ordner": "klassik_macd", "waehrung": "USD",
                     "skript": "handeln.py"},
    "klassik_bollinger": {"ordner": "klassik_bollinger", "waehrung": "USD",
                          "skript": "handeln.py"},
    "klassik_donchian": {"ordner": "klassik_donchian", "waehrung": "USD",
                         "skript": "handeln.py"},
    "klassik_rsi": {"ordner": "klassik_rsi", "waehrung": "USD",
                    "skript": "handeln.py"},
    "klassik_rsi2": {"ordner": "klassik_rsi2", "waehrung": "USD",
                     "skript": "handeln.py"},
    "klassik_donchian_trend": {"ordner": "klassik_donchian_trend",
                               "waehrung": "USD", "skript": "handeln.py"},
    "klassik_sr_breaks": {"ordner": "klassik_sr_breaks", "waehrung": "USD",
                          "skript": "handeln.py"},
    "klassik_pmax": {"ordner": "klassik_pmax", "waehrung": "USD",
                     "skript": "handeln.py"},
    "klassik_supertrend": {"ordner": "klassik_supertrend", "waehrung": "USD",
                           "skript": "handeln.py"},
    # LLM-STUNDE (12.10.2026): drei Indikator-Kandidaten auf 1H, je Regelarm
    # und LLM-Arm (sechs Straenge in laeufe/). Papier, kein Live-Zweig.
    "llm_stunde": {"ordner": "llm_stunde", "waehrung": "USD",
                   "skript": "handeln.py"},
    "moondev_marktlage": {"ordner": "moondev_marktlage", "waehrung": "USD",
                          "skript": "handeln.py"},
    # IV-WAND (17.09.2026): der Strike mit dem groessten Open Interest im
    # Optionsmarkt ist die "Wand" - der Kurs wandert dorthin. Daten von den
    # oeffentlichen OKX-Optionsendpunkten, Ziel ist die Wand selbst, das Buch
    # fuehrt Handel/spur_buch.py. Papier, kein Live.
    "iv_wand": {"ordner": "iv_wand", "waehrung": "USD", "skript": "handeln.py"},
    # IV-WAELLE (18.09.2026): Deribit-IV-Waende. Aus historischer Volatilitaet
    # UND Options-Bepreisung (DVOL) eine erwartete Tagesspanne rechnen, dann an
    # den Waenden (Strikes mit hohem offenem Interesse) gegen die Bewegung
    # handeln - Stop hinter die Wand, Ziel der halbe Rueckweg. Daten von den
    # oeffentlichen Deribit-Endpunkten (daten.py), das Buch fuehrt die Spur
    # selbst nach spur_buch-Muster. Papier, kein Live (handel_erlaubt=false).
    "iv_waelle": {"ordner": "iv_waelle", "waehrung": "USD",
                  "skript": "handeln.py"},
    # DREI SPRACHMODELL-SPUREN (17.09.2026): dieselbe Bauform wie die Bot-Spuren
    # oben, aber die RICHTUNG kommt nicht aus einer Haus-Regel, sondern aus dem
    # LOKALEN Modell (Handel/llm_lokal.py, Ollama auf 127.0.0.1:11434 - kein
    # Schluessel, keine Kosten). Vorbilder sind die Sprachmodell-Agenten des
    # geklonten Bot-Repos: whale_agent, liquidation_agent, sentiment_agent.
    # Das GATE vor dem Urteil ist deterministisch (OI-Anomalie,
    # Liquidationsdruck, Mindestmenge Schlagzeilen) - ohne Gate faellt kein
    # Aufruf. Kein Live-Zweig, kein Orderpfad.
    #   moondev_whale       - Open-Interest-Anomalie, Urteil vom Modell
    #   moondev_liquidation - Zwangsschluesse, Urteil vom Modell
    #   moondev_sentiment   - Schlagzeilen (RSS), Urteil vom Modell
    "moondev_whale": {"ordner": "moondev_whale", "waehrung": "USD",
                      "skript": "handeln.py"},
    "moondev_liquidation": {"ordner": "moondev_liquidation", "waehrung": "USD",
                            "skript": "handeln.py"},
    "moondev_sentiment": {"ordner": "moondev_sentiment", "waehrung": "USD",
                          "skript": "handeln.py"},
    # MOONDEV_SNIPER (19.09.2026): neue Solana-Token-Launches von Pump.fun als
    # Papierbuch. Der Bot-Agent `sniper_agent` ist ein Anzeige-Scanner ohne
    # eigenes Urteil - die Regel liegt im Haus (jung, nicht gesperrt, Marktwert
    # im Band). Quelle ueber die oeffentliche Pump.fun-API
    # (Handel/moondev_daten.py), Buch in Handel/spur_buch.py. Kein
    # Sprachmodell, kein Wallet, kein Live.
    "moondev_sniper": {"ordner": "moondev_sniper", "waehrung": "USD",
                       "skript": "handeln.py"},
    "fib_retrace": {"ordner": "fib_retrace", "waehrung": "USD",
                    "skript": "handeln.py"},
    # OMNI2 (Papierbuch auf den Rust-Laeufen des Forks, angelegt 14.10.2026,
    # Auftrag Interpool): spiegelt die POSITION der omnitrade2-Laeufe in
    # Werkstatt/omnitrade2/status/ in ein eigenes Buch. Muster ist die
    # bestehende omnitrade-Spur (Agenten/Handel/omnitrade/), geteilt sind
    # omnitrade_bridge.py und omnitrade_lauf.py.
    # AUS DEM DAUERLAUF GENOMMEN (14.10.2026): omnitrade2 schreibt aktuell
    # KEINE Statusdatei - sein CLI kennt nur 'backtest' und 'validate', keinen
    # 'live'-Befehl. Der Statuspfad ist definiert
    # (Werkstatt/omnitrade2/status/live.json), die Datei existiert aber nicht.
    # Die Spur wuerde nur "keine Statusdatei" melden und nichts tun - sie
    # erfindet keine Position. Sobald der Rust-Klon einen Live-Modus bekommt,
    # kann die Spur hier re-einkommentiert werden.
    # WIEDER ANSCHALTEN: die Zeile hier re-einkommentieren und in
    # omnitrade2/zustand.json "letzter_lauf" auf jetzt setzen - sonst stellt
    # der erste Zyklus offene Papierpositionen flach (herzschlag_alt).
    # "omnitrade2": {"ordner": "omnitrade2", "waehrung": "USD",
    #                "skript": "handeln.py"},
}

# Spuren, die NUR der Basislauf fuehrt: der Spiegel hat in jeder Risikostufe
# denselben Einsatz (Vorgabe Max). Er liefe dort mit identischem Inhalt und
# schriebe in dieselben Dateien wie der Basislauf - zwei Schreiber auf einem
# Buch. Deshalb ueberspringt ihn jede Stufe.
# LEER seit 21.09.2026: die drei Spiegel-Arme sind deaktiviert (siehe SPUREN).
# Beim Wiedereinschalten gehoeren sie hier wieder hinein - ohne den Eintrag
# faehrt JEDE Risikostufe jede Spur, und Basis und mittel schrieben in
# dieselben Buchdateien (zwei Schreiber auf einem Buch).
NUR_BASIS = ()

# Der Takt ist bei Spur 2 keine Geschmacksfrage: xperp/wachen.json setzt
# herzschlag_max_minuten auf 30. Laeuft der Zyklus seltener, stellt der
# naechste Lauf alle Positionen flach und faellt auf Papier zurueck - richtig
# so, aber dann handelt die Spur eben nicht. 15 Minuten lassen einen
# ausgefallenen Zyklus zu, bevor es eng wird.
TAKT_MAX_MINUTEN = 15

# Spuren mit Auto-Freigabe (20.09.2026, Max): der Dauerlauf erteilt die Freigabe
# ohne /ja, sobald nur noch das Fenster fehlt. NUR Spuren mit echtem Live-Pfad
# (moondev-* verweigern --live). Zeitlich begrenzt auf AUTO_FREIGABE_STUNDEN -
# danach laeuft die Freigabe ab und es muss wieder bestaetigt werden.
# kraken stand vom 21.09.2026 bis 30.09.2026 hier (Auftrag Max: kraken wieder
# live und Handel erlaubt). Bindende Grenze war das freie EUR-Guthaben
# (mindest_guthaben_eur 60).
# KRAKEN AM 30.09.2026 ENTZOGEN (Auftrag Max: "nur noch omnitrade auf kraken
# handel erlaubt"). Entfernt wurden die vier Spuren mit Kraken-Orderweg:
# kraken, moondev_marktlage (live_kraken.py), nautilus_kraken und
# nautilus_kraken_futures. mosaic bleibt drin, handelt aber nur noch auf OKX
# (boersen in mosaic/wachen.json auf ["okx"] gekuerzt).
# KRAKEN AM 01.10.2026 WIEDER AUFGENOMMEN (Auftrag Max: "kraken scharf").
# Der Auftrag vom 30.09.2026 ("nur noch omnitrade auf kraken") ist damit
# aufgehoben. OFFEN: Bedingung 5 sperrt die Spur weiter (rollierender EV
# -0,028 EUR auf 6 Handelsrunden) - solange nennt ihre --vorschau ZWEI
# Gruende und nur_fenster_fehlt() verlangt genau einen, es geht also kein
# Fenster auf. Die Aufnahme hier wirkt, sobald Bedingung 5 faellt.
# OMNQUANT AM 01.10.2026 AUFGENOMMEN (Auftrag Max: "auto freigabe erlaubt").
# Der Orderweg auf Kraken Futures ist gebaut (omniquant/kraken_perp.py +
# live_perp.py, Hebel 6 als Sizing-Regel). Bindende Grenze ist die freie
# Margin im flex-Konto (mindest_guthaben_usd 31).
# SCANNER AM 13.10.2026 ENTZOGEN (Auftrag Max: "Scanner zurueckbauen", T-322):
# keine neuen Einstiege/Freigaben mehr. Die Spur laeuft weiter und laesst ihre
# offenen Live-Positionen mit Boersen-Stop auslaufen; nur die Auto-Freigabe
# entfaellt. handel_erlaubt und freigabe.erfuellt stehen in scanner/wachen.json
# auf false.
# ORBK AM 14.10.2026 ENTZOGEN (Auftrag Max 'letzte Aufgabe der
# Handelsauswertung fertig machen', Befund 13.10.): Punktebuch ohne Einsatz,
# Kosten 1,2 %/Runde gegen f_max +0,06 % - die Live-Freigabe vom 12.10. ist
# zurueckgenommen (handel_erlaubt=false, freigabe.erfuellt=false in
# orbk/wachen.json). orb bleibt live (OKX, 0,1 %/Runde).
# ORBK AM 14.10.2026 WIEDER LIVE (Auftrag Max 'Orbk live schalten'):
# ueberstimmt die Ruecknahme vom selben Tag. handel_erlaubt=true,
# freigabe.erfuellt=true in orbk/wachen.json.
#
# STAND 15.10.2026 (Auftrag Max 'Ja autofreigabe fuer live handel komplett'):
# Die Liste ist die Abwicklung der Live-Spuren, KEIN Schalter. Ein Eintrag
# oeffnet ein Fenster nur, wenn NUR noch das Fenster fehlt (nur_fenster_fehlt,
# genau ein Grund) - handel_erlaubt, Freigabe, Bedingung 1/5 muessen offen
# sein. Gemessen heute mit spuren_stand + Wachten: 11 der 14 Eintraege haben
# handel_erlaubt=true UND einen Live-Pfad im Code (xperp, orb, kraken, mosaic,
# omniquant, nautilus_kraken, moondev_listingarb, moondev_marktlage,
# moondev_signalwelle, omnitrade_futures, moondev_topmovers). Keine Spur mit
# Live-Pfad fehlt. Drei Eintraege sind derzeit WIRKUNGSLOS, weil ihre Wachen
# sperren: orbk (handel_erlaubt=false seit 14.10., f_max +0,06 % gegen
# 1,2 % Kosten), trendwende_btc (handel_erlaubt=false), liq_wand
# (handel_erlaubt=false, und orderweg() findet keinen Orderpfad). Sie
# bleiben stehen: sobald Max die Schalter umlegt, braucht es keinen zweiten
# Eingriff an dieser Stelle. moondev_topmovers steht ebenfalls drin, hat aber
# laut Wachen handel_erlaubt=true und keinen Orderpfad - der Eintrag wartet
# auf den Live-Pfad. SCANNER fehlt hier seit 13.10. absichtlich (T-322).
AUTO_FREIGABE = ("xperp", "mosaic", "kraken",
                 "moondev_listingarb", "moondev_topmovers",
                 "trendwende_btc", "liq_wand", "omniquant",
                 "moondev_marktlage", "nautilus_kraken",
                 "omnitrade_futures", "moondev_signalwelle",
                 "orb", "orbk")
AUTO_FREIGABE_STUNDEN = 12


# Module-level state fuer Log-Rotation-Optimierung
_LOG_ROTATION_CHECK_INTERVAL = 100  # noqa: E305
_LOG_ROTATION_COUNTER = 0

# KEINE Whitelist fuer die Subprozess-Umgebung: die Spuren sind eigener,
# vertrauenswuerdiger Code und brauchen die API-Schluessel (OKX_*, KRAKEN_*,
# OLLAMA_MODELS, HANDEL_RISIKO ...) in ihrer Umgebung. Eine Whitelist wie die
# hier entfernte (PATH/PYTHONPATH/HOME/...) liess sie ohne Schluessel starten -
# der betriebsbrechende Fehler des Refactors vom 19.09.2026. _env_sicher()
# reicht die volle Umgebung durch und setzt nur HANDEL_RISIKO explizit.


def jetzt():
    return dt.datetime.now()


def protokoll(text):
    """Logg mit Rotation bei 1 MB. Rotation-Check nur alle N Aufrufe."""
    global _LOG_ROTATION_COUNTER
    zeile = "%s  %s" % (jetzt().strftime("%d.%m. %H:%M:%S"), text)
    print(zeile, flush=True)
    try:
        # Eigene Logdatei je Stufe (dauerlauf.mittel.log): zwei Laeufe in
        # einer Datei liessen sich nicht mehr auseinanderhalten, und die
        # Systempruefung liest genau diese Datei auf "ENDE FEHLER".
        pfad = risikostufe.datei(os.path.join(HIER, "dauerlauf.log"))
        
        # Rotation-Check nur jeden Nth Aufruf, nicht bei JEDEM write
        _LOG_ROTATION_COUNTER = (_LOG_ROTATION_COUNTER + 1) % _LOG_ROTATION_CHECK_INTERVAL
        if _LOG_ROTATION_COUNTER == 0:
            if os.path.exists(pfad) and os.path.getsize(pfad) > 1_000_000:
                # Entferne alte Rotation, benenne aktiv -> .1
                try:
                    if os.path.exists(pfad + ".1"):
                        os.remove(pfad + ".1")
                    os.replace(pfad, pfad + ".1")
                    print("LOG ROTATION: %s -> %s.1" % (pfad, pfad), file=sys.stderr)
                except OSError as e:
                    print("LOG ROTATION ERROR: %s" % e, file=sys.stderr)
        
        with open(pfad, "a", encoding="utf-8") as f:
            f.write(zeile + "\n")
    except OSError as e:
        # Don't silently ignore -- signal disk problem
        print("LOG WRITE ERROR: %s (Disk full?)" % e, file=sys.stderr)


def _lade_wachen_sicher(pfad):
    """Lade wachen.json mit Fehlerbehandlung und Struktur-Validierung.
    
    Rueckgabe: dict oder None. Fehler werden protokolliert.
    """
    try:
        if not os.path.exists(pfad):
            protokoll("wachen.json fehlt: %s" % pfad)
            return None
        if os.path.getsize(pfad) == 0:
            protokoll("wachen.json leer: %s" % pfad)
            return None
        with open(pfad, encoding="utf-8", errors="replace") as f:
            w = json.load(f)
        # Validierung: muss ein dict sein
        if not isinstance(w, dict):
            protokoll("wachen.json ist kein dict: %s (Typ: %s)" % (pfad, type(w).__name__))
            return None
        return w
    except json.JSONDecodeError as e:
        protokoll("wachen.json ungueltig (JSON): %s -- %s" % (pfad, e))
        return None
    except (OSError, ValueError) as e:
        protokoll("wachen.json Lesefehler: %s -- %s" % (pfad, e))
        return None


def _handel_erlaubt_aus(ordner):
    """`handel_erlaubt` der Spur (None, wenn Datei/Feld fehlt).

    Gebraucht fuer die MELDUNG: das Freigabefenster sagt nur, dass --live
    erlaubt waere - ob die Spur live geht, entscheidet ihr eigener Riegel.
    Am 22.09.2026 stand fuenfmal "(live)" im Log, waehrend kraken Papier
    handelte (handel_erlaubt=false); Max hat genau danach gefragt.
    """
    w = _lade_wachen_sicher(os.path.join(ordner, "wachen.json"))
    if not isinstance(w, dict):
        return None
    return w.get("handel_erlaubt")


def _meldungsmodus(modus, ordner):
    """Der Modus, der GEMELDET wird: die Wirkung, nicht die Anfrage.

    Das Freigabefenster erlaubt --live, die Spur kann es trotzdem verweigern
    (wachen.json handel_erlaubt=false). Am 22.09.2026 stand fuenfmal
    "(kraken (live) ok)" im Log, waehrend kraken Papier handelte - Max hat
    genau danach gefragt. Der AUFRUF bleibt der angeforderte Modus; nur die
    Meldung sagt die Wahrheit.
    """
    if modus == "--live" and _handel_erlaubt_aus(ordner) is False:
        return "--papier"
    return modus


def _env_sicher():
    """Umgebung fuer Subprozesse: die volle Umgebung, plus HANDEL_RISIKO.

    Die Spuren sind eigener, vertrauenswuerdiger Code und lesen ihre
    API-Schluessel (OKX_*, KRAKEN_*, OLLAMA_MODELS ...) aus der Umgebung.
    Eine Whitelist wuerde sie ohne Schluessel starten lassen - das war der
    betriebsbrechende Fehler des Refactors vom 19.09.2026. Kein Leak: die
    Spuren sind die legitimen Empfaenger dieser Werte.
    """
    umgebung = dict(os.environ)
    # HANDEL_RISIKO explizit setzen, nicht erben
    umgebung["HANDEL_RISIKO"] = risikostufe.stufe()
    return umgebung


def zyklus_umgebung(modus, basis=None):
    """Umgebung EINES Spur-Zyklus - in beiden Modi dieselbe Zusicherung.

    MAXHIRN_ROUTINE=1 heisst: hier sitzt niemand am Bildschirm. Das schlaegt
    in jeder Spur die isatty-Erkennung (sitzung_da) und verhindert, dass ein
    Dienstprozess das Freigabefenster aufzieht und auf einen Klick wartet.
    Der Modus ist deshalb absichtlich KEIN Parameter der Entscheidung - er
    steht nur in der Signatur, damit ein Aufrufer nicht in Versuchung kommt,
    die Variable wieder an --papier zu binden (Fehler vom 21.09.2026).
    Geprueft von tests/test_zyklus_zeitgrenze.py.
    """
    umgebung = dict(basis) if basis is not None else _env_sicher()
    umgebung["MAXHIRN_ROUTINE"] = "1"
    return umgebung


# --- Was in den Chat gehoert -------------------------------------------------
#
# Eine reine Wortsuche ("verkauf", "stop", "ausstieg") traf auch Zeilen, die
# kein Ereignis melden. Zyklus 21 der Basis am 25.09.2026 schickte fuenf Zeilen,
# davon NULL Ereignisse: zweimal die Ueberschrift "- Ausstiege -" (die Spuren
# scanner und kraken hatten nichts zu melden), die Fortsetzungszeile einer
# frisch eroeffneten swap-Anlage ("XAU-USDT-SWAP short Stop 4318.2 ...", das
# Wort stop ist dort eine Spaltenueberschrift) und dreimal derselbe mosaic-
# Hinweis "... der Papierzweig verkauft sie nicht".
#
# Deshalb: gemeldet wird, was einen Ausstieg, eine Eroeffnung, einen Notaus
# oder einen FEHLSCHLAG AUSSPRICHT - und zwar an der Zeile, die ihr Instrument
# selbst nennt (Befund 11.09.2026: die Stop-Zeile von xperp kam ohne Wertnamen
# an). Wiederholt sich dieselbe Zeile im naechsten Zyklus, wird sie nicht
# erneut geschickt (eine Sperre, die stehen bleibt, war sonst 96-mal am Tag
# im Chat).
EREIGNIS_ANFANG = ("AUSSTIEG", "NOTAUS", "AUF ")
EREIGNIS_WORTE = ("kill-switch", "kill-schwelle", "notausstieg",
                  "fehlgeschlagen", "hat ausgeloest", "gesperrt")


def ereigniszeilen(ausgabe):
    """Die Zeilen einer Spur-Ausgabe, die ein Ereignis melden."""
    treffer = []
    for zeile in ausgabe.splitlines():
        z = zeile.strip()
        if not z:
            continue
        if z.startswith(EREIGNIS_ANFANG) or any(
                w in z.lower() for w in EREIGNIS_WORTE):
            treffer.append(z)
    return treffer


def neue_ereignisse(ausgabe, vorher=()):
    """(neue Zeilen, alle Zeilen) - `vorher` sind die Zeilen des letzten Zyklus.

    Gemeldet werden nur die neuen; gespeichert wird die volle Liste, damit
    ein Ereignis nach einer Pause wieder gemeldet wird.
    """
    alle = ereigniszeilen(ausgabe)
    alt = set(vorher or ())
    return [z for z in alle if z not in alt], alle


# Fehlerzeilen dauerhaft ablegen (fuer den Waechter-Cron, 28.09.2026): die
# "fehlgeschlagen"-Zeilen schickt der Dauerlauf zwar als Zyklus-Meldung, aber
# er speichert sie nirgends - ein einzelner transienter Fehler (z.B. der
# XAG-Kontraktwechsel am 20.09.) ist nicht von einem wiederholten zu
# unterscheiden. Der Waechter liest diese Datei und meldet nur, wenn derselbe
# Basiswert mehrfach fehlschlaegt. Nur "fehlgeschlagen"-Zeilen (nicht
# "gesperrt"/"kill-switch", die sind normal und haeufig).
FEHLER_DATEI = os.path.join(HIER, "cache", "ereignis-fehler.jsonl")


def protokolliere_fehler(spur, zeile):
    """Hängt eine Fehlschlag-Zeile einer Spur dauerhaft an (watchdog-Quelle)."""
    if "fehlgeschlagen" not in zeile.lower():
        return
    try:
        os.makedirs(os.path.dirname(FEHLER_DATEI), exist_ok=True)
        eintrag = {
            "zeit": jetzt().isoformat(timespec="seconds"),
            "spur": spur,
            "zeile": zeile[:300],
        }
        with open(FEHLER_DATEI, "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    except OSError:
        # Ein Fehlschlag beim Protokollieren darf den Zyklus nicht stoppen.
        pass


class Lauf:
    def __init__(self, takt, trocken=False):
        self.takt = takt
        self.trocken = trocken
        # Die Stufe steht schon in der Umgebung, bevor der erste Zyklus
        # laeuft (main setzt sie) - hier nur die Kurzform.
        self.risiko = risikostufe.stufe()
        # Eine Stufe ueber der Basis ist ein DATENSAMMLER: kein Telegram,
        # keine Befehle, keine Freigabe-Anfrage, immer Papier. Die Begruendung
        # steht im Modulkopf.
        self.stumm = not risikostufe.ist_basis()
        self.pausiert = False
        self.zeiger = None
        self.letzter_zyklus = None
        self.letzter_bericht = None
        self.zyklen = 0
        self.fehler = 0
        # Je Spur die Ereigniszeilen des VORIGEN Zyklus: dieselbe Zeile wird
        # nicht zweimal geschickt (siehe ereigniszeilen()).
        self.gemeldet = {}

    # --- senden ---------------------------------------------------------

    def sende(self, text, stumm=False):
        if self.trocken or self.stumm:
            grund = ("trocken" if self.trocken
                     else "Stufe %s, kein Telegram" % self.risiko)
            print("--- nicht gesendet (%s) ---\n%s\n---" %
                  (grund, text.replace("<b>", "").replace("</b>", "")))
            return True
        return melder.sende(text, stumm=stumm)

    # --- die Spuren -----------------------------------------------------

    def zyklus_spur(self, spur):
        """Ein Zyklus einer Spur. Papier, ausser das Fenster ist offen.
        
        Timeout: TIMEOUT_S (siehe Konstante oben). Subprocess-Fehler sind nicht mehr fatal.
        """
        f = freigabefenster.lade(spur)
        # Eine Risikostufe geht NIE live, auch bei offenem Fenster: ihre
        # groesseren Betraege sind zum MESSEN da, nicht zum Handeln, und ihr
        # Buch ist getrennt - wer sie scharf schaltet, haette echtes Geld im
        # Einsatz, ohne es in der Auswertung zu sehen. Das Fenster gehoert
        # dem Basislauf; hier wird es nur gelesen.
        modus = "--live" if (f.offen() and not self.stumm) else "--papier"

        ordner = os.path.join(HIER, SPUREN[spur]["ordner"])
        # WIRKUNG STATT ANFRAGE (siehe _meldungsmodus): der AUFRUF bleibt der
        # angeforderte Modus - sonst aendert sich das Verhalten der Spur
        # (z.B. laeuft die Buchbereinigung nur im Live-Zweig) -, gemeldet wird
        # aber, was wirklich passiert.
        kennung = _meldungsmodus(modus, ordner)
        # Nicht jede Spur heisst handeln.py: die Spiegel-Spur liest einen
        # fremden Feed und bucht nach (spiegel.py). Der Eintrag in SPUREN
        # entscheidet, welche Datei gestartet wird.
        skript = SPUREN[spur].get("skript", "handeln.py")
        # Nicht jede Spur laeuft unter dem scanner-venv: die Nautilus-Spur
        # braucht ihr eigenes venv (nautilus_trader liegt nur dort). Das
        # Feld "python" in SPUREN traegt den Interpreter, Vorgabe bleibt
        # der gemeinsame.
        python = SPUREN[spur].get("python", PYTHON)
        umgebung = _env_sicher()  # FIXED: sichere Umgebung, nicht alle vars
        # Sagt handeln.py, dass niemand am Bildschirm sitzt - in BEIDEN Modi.
        # Bis zum 21.09.2026 stand die Variable nur bei --papier, mit der
        # Begruendung "bei --live ist die Freigabe ohnehin schon erteilt".
        # Die Annahme war falsch: sitzung_da() prueft isatty() auf stdin, und
        # ein Dienstprozess erbt ein Terminal - der Live-Lauf hielt sich fuer
        # eine Sitzung am Bildschirm, oeffnete das Freigabefenster, wartete
        # auf einen Klick, den niemand geben kann, und lief in den Timeout
        # (scanner ab 21.09. 19:22 in jedem Zyklus).
        umgebung = zyklus_umgebung(modus, umgebung)

        # Popen statt run: bei Timeout muss der GANZE Prozessbaum enden. run()
        # beendet nur den direkten Kindprozess; dessen Enkel bleiben als
        # Waisen stehen und laufen in jedem Zyklus weiter (am 12.10.2026 wuchs
        # so die Zahl der Scanner-Prozesse auf 768).
        p = subprocess.Popen([python, skript, modus], cwd=ordner,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, env=umgebung,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            out, err = p.communicate(timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           capture_output=True)
            p.communicate()
            protokoll("%s TIMEOUT (exceeded %ds limit), Prozessbaum beendet" % (spur, TIMEOUT_S))
            return kennung, 124, "TIMEOUT: Handelslogik antwortet nicht"
        except Exception as e:
            protokoll("%s subprocess ERROR: %s" % (spur, e))
            return kennung, 1, str(e)
        return kennung, p.returncode, (out or "") + (err or "")


    def zyklus(self):
        self.zyklen += 1
        self.letzter_zyklus = jetzt()
        auffaellig = []

        for spur in SPUREN:
            if self.stumm and spur in NUR_BASIS:
                # Der Spiegel laeuft nur in der Basis (siehe NUR_BASIS).
                # Ohne Meldung: eine Zeile je Zyklus waere Rauschen.
                continue
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

            # Ausstieg, Eroeffnung, Notaus oder Fehlschlag im Lauf: das gehoert
            # sofort gemeldet, nicht erst im Tagesbericht. Ausgewaehlt wird
            # ueber ereigniszeilen() - siehe die Anmerkung dort, warum eine
            # Wortsuche dafuer zu grob ist.
            neu, alle = neue_ereignisse(ausgabe, self.gemeldet.get(spur))
            for zeile in neu:
                auffaellig.append("%s: %s" % (spur, zeile))
            # Fehlschlag dauerhaft ablegen (Waechter-Quelle, 28.09.2026): nur
            # die NEUEN Zeilen - dieselbe Zeile wird sonst mit jedem Zyklus
            # erneut angehaengt.
            for zeile in neu:
                protokolliere_fehler(spur, zeile)
            self.gemeldet[spur] = alle

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

        Und gefragt wird nicht oefter als noetig: neue_anfrage_erlaubt() haelt
        die Wiedervorlage-Fristen. Ohne sie stand hier alle 30 Minuten
        dieselbe Frage (die Frist einer unbeantworteten Anfrage), auch direkt
        nach einem /nein - am 12.09.2026 um 19:06 abgelehnt, um 19:20 erneut
        gefragt.
        """
        if self.stumm:
            # Eine Stufe fragt NICHT nach Freigabe - sie darf sie nicht
            # bekommen (siehe Modulkopf). Ohne diesen Schritt haenge hier
            # alle 30 Minuten eine Frage, die nur mit /nein zu beantworten
            # waere.
            return
        for spur, d in SPUREN.items():
            f = freigabefenster.lade(spur)
            if f.offen() or f.anfrage_offen():
                continue
            if not freigabefenster.neue_anfrage_erlaubt(spur):
                # Gerade gefragt oder gerade abgelehnt: nicht wiederholen.
                # Die Fristen stehen in freigabefenster.py samt Begruendung.
                continue
            offen_bis_auf_fenster = self.nur_fenster_fehlt(spur, d)
            if not offen_bis_auf_fenster:
                continue
            w = offen_bis_auf_fenster
            dauer = freigabefenster.anfrage_stellen(spur, 12 * 60)
            if spur in AUTO_FREIGABE:
                # Auto-Freigabe (20.09.2026, Max): sofort bestaetigen statt
                # auf /ja zu warten. anfrage_stellen() legt die Anfrage an,
                # oeffnen() bestaetigt sie - genau der Weg, den /ja geht.
                m = freigabefenster.oeffnen(spur, AUTO_FREIGABE_STUNDEN, "auto")
                if m:
                    protokoll("Auto-Freigabe %s (%d min)" % (spur, m))
                continue
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
        skript = d.get("skript", "handeln.py")
        python = d.get("python", PYTHON)
        try:
            p = subprocess.run([python, skript, "--vorschau"],
                               cwd=ordner, capture_output=True, text=True,
                               timeout=600, env=dict(os.environ,
                                                     MAXHIRN_ROUTINE="1"),
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
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
        # FIXED: sichere JSON-Lade mit Fehlerbehandlung
        return _lade_wachen_sicher(os.path.join(ordner, "wachen.json"))

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

        if wort in ("ja_xperp", "nein_xperp", "stop_xperp", "freigabe_xperp",
                    "ja_swap", "nein_swap", "stop_swap", "freigabe_swap"):
            spur = "swap" if wort.endswith("_swap") else "xperp"
            kurz = spur.upper()
            endung = "_" + spur
            f = freigabefenster.lade(spur)
            if wort == "freigabe" + endung:
                with open(os.path.join(HIER, spur, "wachen.json"), encoding="utf-8") as datei:
                    w = json.load(datei)
                if not f.anfrage_offen():
                    return ("%s: %s. Keine wartende Anfrage.\n"
                            "handel_erlaubt=%s, freigabe.erfuellt=%s.\n"
                            "Nur der Dauerlauf stellt nach Sperrenpruefung eine Anfrage."
                            % (kurz, f.text(), w.get("handel_erlaubt"), w.get("freigabe", {}).get("erfuellt")))
                return freigabefenster.anfrage_text(spur, w, f.d.get("anfrage_dauer_minuten", 60)).replace("/ja", "/ja" + endung).replace("/nein", "/nein" + endung)
            if wort in ("nein" + endung, "stop" + endung):
                freigabefenster.schliessen(spur, "Telegram " + wort)
                return ("%s-Fenster geschlossen. Keine neuen Live-Einstiege; "
                        "keine Position glattgestellt. Spot unveraendert." % kurz)
            import math
            try:
                h = float(rest[0]) if len(rest) == 1 else None
                if h is None or not math.isfinite(h) or not 0 < h <= freigabefenster.MAX_STUNDEN:
                    raise ValueError
            except ValueError:
                return ("Syntax: /ja%s STUNDEN (groesser 0, hoechstens 24). "
                        "Erst /freigabe%s lesen." % (endung, endung))
            m = freigabefenster.oeffnen(spur, h, "telegram/" + spur)
            if m is None:
                return "Keine aktuelle %s-Anfrage. Nichts freigegeben; Spot unveraendert." % kurz
            protokoll("FREIGABE %s fuer %s min" % (spur, m))
            return ("%s-Fenster fuer %g h offen; alle Wachen gelten weiter. "
                    "Spot unveraendert. /stop%s schliesst das Fenster." % (kurz, h, endung))

        if wort == "prognose":
            return ("Bitte im SkillsBot: /prognose [N]. Die Marktanalyse darf hier "
                    "weder Stop-Befehle noch den Handelszyklus blockieren. "
                    "Kurz und ohne Order: /markt")
        if wort == "papierstatus":
            import handel_befehle
            return handel_befehle.status(papier=True)

        # /lage ist die JETZT-Sicht: Positionen, Live-Tore, offene Freigaben.
        # Bis 15.09.2026 war sie derselbe Bericht wie /bericht, nur ohne
        # Rangliste - zwei Befehle, eine Auskunft. Wer alles sehen will, nimmt
        # /bericht; wer eine Spur in der Tiefe will, /spur NAME.
        if wort in ("lage", "status"):
            return befehle.lage()

        # /live ist die reine Live-Sicht: nur die Spuren mit Orderweg im Code,
        # getrennt nach eigenem Haus-Orderweg und Fremd-Laufzeit (DEMO), mit
        # Fenster, Buch und letztem echten Vorgang.
        if wort in ("live", "livestand"):
            return befehle.live()

        if wort == "bericht":
            return tagesbericht.baue(mit_xperp=True)

        if wort == "spuren":
            namen = befehle.spuren()
            return ("Spuren: %s" % ", ".join(namen) if namen
                    else "Spurliste nicht lesbar (SPUREN in dauerlauf.py).")

        if wort == "spur":
            return befehle.spur(" ".join(rest))

        if wort == "strategien":
            return befehle.strategien()

        if wort == "indikatoren":
            return befehle.indikatoren()

        if wort == "markt":
            return befehle.markt()

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
        return (befehle.hilfe()
                + "\n\n<b>Jetzt</b>\n%s\n"
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

        if self.stumm:
            protokoll("Risikostufe %s: ohne Telegram, ohne Befehle, nur Papier"
                      % self.risiko)
        elif not self.trocken and not melder.bereit():
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
                #
                # Nur der Basislauf: die Fenster sind gemeinsame Dateien, und
                # ein Stufenlauf, der sie beim Beenden schliesst, nimmt dem
                # Basislauf mitten im Handel die Freigabe weg.
                if not self.stumm:
                    freigabefenster.alles_schliessen("Dauerlauf beendet")
                sperre.freigib(sperre.pfad())
                return 0
            except Exception:                            # noqa: BLE001
                self.fehler += 1
                protokoll("Runde gescheitert:\n%s" % traceback.format_exc())
                time.sleep(30)

    def runde(self):
        # 1. Befehle
        if not self.trocken and not self.stumm and melder.bereit():
            try:
                nachrichten, self.zeiger = melder.hole(self.zeiger, warten=20)
            except Exception as e:                       # noqa: BLE001
                protokoll("Telegram: %s" % e)
                nachrichten = []
                time.sleep(10)
            # FIXED: Sende-Fehler blockieren nicht mehr das ganze Queue
            for n in nachrichten:
                protokoll("Befehl: %s" % n["text"][:60])
                antwort = None
                try:
                    antwort = self.befehl(n["text"])
                except Exception as e:                   # noqa: BLE001
                    antwort = "Der Befehl ist gescheitert: %s" % e
                    protokoll("Befehl gescheitert:\n%s" % traceback.format_exc())
                
                # Sende immer, auch wenn fehlgeschlagen
                if antwort:
                    try:
                        self.sende(antwort)
                    except Exception as e:
                        # Sende-Fehler: zeiger wird trotzdem vorbeibeweegt
                        protokoll("Sende fehlgeschlagen (aber zeiger wird vorbeigezogen): %s" % e)
                else:
                    protokoll("Warnung: kein Antworttext erzeugt")
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
        #    Nicht in einer Risikostufe: der Bericht liest die Basisdateien
        #    (feste Pfade je Spur) und zeigt damit ein anderes Buch als das,
        #    das dieser Lauf fuehrt - doppelte Rechenzeit fuer eine Auskunft,
        #    die der Basislauf ohnehin schickt.
        heute = jetzt().date()
        if (not self.stumm and self.letzter_bericht != heute
                and jetzt().hour >= 8):
            self.letzter_bericht = heute
            protokoll("Tagesbericht")
            try:
                self.sende(tagesbericht.baue(mit_xperp=True))
            except Exception as e:                       # noqa: BLE001
                self.sende("<b>Tagesbericht gescheitert</b>\n%s" % e)
            # Erst danach den Stand von heute ablegen - siehe oben.
            try:
                schnappschuss.schreibe(
                    schnappschuss.baue(lage.erhebe(mit_xperp=False)))
            except Exception as e:                       # noqa: BLE001
                protokoll("Schnappschuss gescheitert: %s" % e)
            if heute.weekday() == 0:
                protokoll("Wochenbericht")
                try:
                    self.sende(wochenbericht.baue())
                except Exception as e:                   # noqa: BLE001
                    self.sende("<b>Wochenbericht gescheitert</b>\n%s" % e)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--takt", type=int, default=TAKT_MAX_MINUTEN,
                   help="Minuten zwischen zwei Zyklen (Vorgabe %d; der "
                        "Herzschlag von Spur 2 liegt bei 30 und begrenzt "
                        "das nach oben)" % TAKT_MAX_MINUTEN)
    p.add_argument("--trocken", action="store_true",
                   help="nichts senden, alles auf die Konsole")
    p.add_argument("--risiko", choices=sorted(risikostufe.FAKTOREN),
                   default=risikostufe.STANDARD,
                   help="Risikostufe dieses Laufs (Vorgabe %s). Alles ueber "
                        "der Basis ist ein zweiter, reiner Papierlauf mit "
                        "eigenen Dateien - siehe Modulkopf."
                        % risikostufe.STANDARD)
    a = p.parse_args()

    # ZUERST die Stufe in die Umgebung: daraus leitet risikostufe.py jeden
    # weiteren Namen ab (dauerlauf.mittel.log, dauerlauf.mittel.pid) und die
    # Kindprozesse erben sie ueber env=dict(os.environ).
    os.environ["HANDEL_RISIKO"] = a.risiko

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.takt > TAKT_MAX_MINUTEN:
        # Nicht stillschweigend korrigieren: Wer einen groesseren Takt
        # setzt, soll erfahren, warum er ihn nicht bekommt.
        print("Takt %d min liegt ueber dem Herzschlag von Spur 2 (30 min) - "
              "jeder Zyklus wuerde flach stellen. Es gilt %d min."
              % (a.takt, TAKT_MAX_MINUTEN))
        a.takt = TAKT_MAX_MINUTEN

    if not risikostufe.ist_basis():
        print("Risikostufe %s: Faktor %.1f, eigene Dateien (*%s.*), immer "
              "Papier, kein Telegram. Der Basislauf laeuft daneben "
              "unveraendert weiter." % (a.risiko, risikostufe.faktor(),
                                        risikostufe.suffix()))

    # Die Sperre. Bis zum 29.09.2026 pruefte sie nur handel-dauerlauf.ps1 -
    # ein von Hand gestarteter `python dauerlauf.py` ging daran vorbei UND war
    # fuer den Waechter unsichtbar, weil er sie auch nicht schrieb. Genau so
    # entstand der Vorfall vom 15.09.2026 (Modulkopf): zwei Laeufe, dieselben
    # Dateien. Im Zweifel startet der Lauf, statt sich auszusperren - die
    # Begruendung steht im Kopf von sperre.py.
    sperr_datei = sperre.pfad()
    if sperre.belegt(sperr_datei):
        gelesen = sperre.lies(sperr_datei)
        print("Es laeuft bereits ein Dauerlauf der Stufe %s (PID %s). Zwei "
              "Laeufe schreiben in dieselben Dateien - dieser beendet sich."
              % (a.risiko, gelesen[0] if gelesen else "?"))
        return 0
    sperre.schreibe(sperr_datei)
    verbesserer_import_melden()

    try:
        with ereignis.lauf("handel/dauerlauf"):
            return Lauf(a.takt, a.trocken).start()
    finally:
        # Auch nach Abbruch oder Ausnahme: eine liegengebliebene Sperre waere
        # zwar erkennbar tot, aber der Waechter muesste sie erst wegraeumen.
        sperre.freigib(sperr_datei)


if __name__ == "__main__":
    raise SystemExit(main())
