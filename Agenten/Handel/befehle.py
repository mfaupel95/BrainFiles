"""Textbefehle fuer den Handelsstand - EINE Quelle fuer beide Telegram-Bots.

Warum dieses Modul
------------------
`/lage` und `/bericht` waren bis zum 15.09.2026 derselbe Bericht: beide riefen
`tagesbericht.baue(...)`, der einzige Unterschied war die XPERP-Rangliste
(`mit_xperp`). Wer die beiden Befehle nebeneinander las, sah zweimal dasselbe.
Und fuer die Frage "wie steht Spur X?" gab es gar keinen Befehl - man musste
den ganzen Bericht durchsuchen.

Hier stehen deshalb die vier Sichten getrennt:
  /lage        JETZT: offene Positionen je Spur, Live-Tore, offene Freigaben
  /bericht     der volle Tagesbericht (tagesbericht.baue) - unveraendert
  /spur NAME   eine Spur in der Tiefe (Positionen, Wachen, Journal, Ablehnungen)
  /strategien  die BILANZ aller Spuren nebeneinander (Runden, Treffer, Ergebnis)
  /indikatoren die vier Indikator-Spuren: Signale und offene Positionen

Regeln, die fuer alle Funktionen hier gelten
--------------------------------------------
1. **Rein lesend.** Keine Datei wird geschrieben, kein Prozess gestartet, keine
   Order. Der SkillsBot laeuft neben dem Dauerlauf; ein schreibender Befehl aus
   zwei Prozessen waere ein zweiter Schreiber im Buch.
2. **Die Spurliste kommt aus `dauerlauf.SPUREN`**, aus der Datei gelesen (AST),
   nicht als zweite Liste kopiert. Eine Abschrift altert beim naechsten neuen
   Spurordner still - genau der Fehler, den dieser Baum schon mehrfach hatte.
3. **Keine zweite Zahlenformel.** Runden, Trefferquote und Ergebnis kommen aus
   der Auswertung, die die Spur schon hat: `auswertung_alle.py` fuer die
   Kontrakt-/Spot-/Buchspuren, `kernzeile()` der Spur fuer die fuenf Buecher mit
   eigener Auswertung. Was keine geschlossenen Runden hat, sagt das - statt eine
   Null-Bilanz zu erfinden.
4. **Gruppierung ist eine eigene Liste - und der Test haelt sie fest.** `FAMILIE`
   ordnet jede Spur ihrer Strategie zu (Kontrakt, Spot, Grid, Feed, Indikator).
   Fehlt eine Spur darin, meldet das der Test, nicht der Nutzer.
5. **Der Text ist HTML** (wie `tagesbericht`) - der Handelsbot sendet mit
   `parse_mode=HTML`. Der SkillsBot sendet Klartext und ruft `klartext()`.
"""

import csv
import datetime as dt
import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
# ANS ENDE, nicht nach vorn: dieses Modul wird auch aus dem Bus-Prozess geladen
# (SkillsBot). Stuende der Handel-Ordner ganz vorn, koennte ein gleichnamiges
# Modul des Aufrufers verdeckt werden - tagesbericht/scanner/... gibt es im Bus
# nicht, aber die Regel gilt fuer jedes kuenftige Modul.
if HIER not in sys.path:
    sys.path.append(HIER)

import freigabefenster                                        # noqa: E402
import tagesbericht as tb                                    # noqa: E402
import lage as lg   # "lage" ist hier der Befehlsname            # noqa: E402

DAUERLAUF = os.path.join(HIER, "dauerlauf.py")
DAUERLAUF_LOG = os.path.join(HIER, "dauerlauf.log")

# Strategie-Familie je Spur. Die vier Indikator-Spuren teilen sich einen
# Eintrag: sie sind EIN Verfahren (je ein Signal auf einem Indikator) und
# werden in /indikatoren einzeln gezeigt.
FAMILIE = {
    "xperp": "Kontrakt",
    "swap": "Kontrakt",
    "scanner": "Spot-Rangliste",
    "kraken": "Spot Kraken (EUR)",
    "orbk": "Breakout (ORB)",
    "orb": "Breakout (ORB)",
    "gitter": "Grid",
    "nautilus": "Quote-Sammler",
    "nautilus_kraken": "Kraken-Spot (EUR)",
    "nautilus_kraken_futures": "Kraken-Futures (USD)",
    "nautilus_emacross": "EMA-Cross 10/20 (Original)",
    "spiegel": "Feed-Spiegel",
    # SPIEGEL-SCHATTENBUECHER (18.09.2026, V1 Ausstiegsgeometrie): dieselbe
    # Signalquelle wie spiegel, andere Stop/Trailing-Parameter. Gleiche
    # Familie, damit sie im Bericht neben dem Hauptbuch stehen.
    "spiegel_knapp": "Feed-Spiegel",
    "spiegel_weit": "Feed-Spiegel",
    "kopier": "Feed-Kopie",
    # Robinhood-Radar (22.09.2026): Buch auf einem fremden Feed -
    # dieselbe Familie wie die Kopier-Spuren.
    "robinhood_radar": "Feed-Kopie",
    # omnitrade (30.09.2026): spiegelt die Position eines fremden LAUFS
    # (Rust, Werkstatt/omnitrade) - dieselbe Familie, aber der Fremdlauf
    # entscheidet, nicht ein Wallet-Feed.
    "omnitrade": "Feed-Kopie",
    # Hebel-Bein (30.09.2026): dasselbe Signal, Ausfuehrung auf Kraken Futures.
    "omnitrade_futures": "Feed-Kopie (Hebel)",
    "omniquant": "Prognose-Buch",
    "omniquant_weit": "Prognose-Buch (weit)",
    "macd_mtf": "Indikator",
    "squeeze": "Indikator",
    # Schattenarm squeeze_eth (03.10.2026, Auftrag Max "Schattenarm").
    # Die Familie heisst genau "Indikator" wie sein Hauptbuch - der Zusatz
    # waere hier eine zweite Familie (test_befehle prueft die Eigenschaft).
    "squeeze_eth": "Indikator",
    "supertrend": "Indikator",
    "trendwende_btc": "Indikator",
    # Prophet-Signal (02.10.2026): EMA30-Trend + Saisonalitaet, ein Signal
    # je Instrument - gehoert zu den Indikator-Spuren.
    "prophet_signal": "Indikator",
    "klassik_sma": "Indikator",
    "klassik_ema": "Indikator",
    "klassik_macd": "Indikator",
    "klassik_bollinger": "Indikator",
    "klassik_donchian": "Indikator",
    "klassik_rsi": "Indikator",
    "klassik_rsi2": "Indikator",
    "klassik_donchian_trend": "Indikator",
    "klassik_sr_breaks": "Indikator",
    "klassik_pmax": "Indikator",
    "klassik_supertrend": "Indikator",
    "liq_wand": "Options-Zone",
    "wavetrend": "Indikator",
    # Mosaic ist keine Indikator-Spur: sie handelt Preisaktion (4H-Bias,
    # 30M-Pullback, 5M-Structure-Shift). Eigene Familie statt "?" - die
    # Gruppierung im Bericht und der Test haengen daran.
    "mosaic": "Preisaktion",
    # Bot-Signale: die Papierbuecher auf geklonten Fremd-Bots
    # (moondev_funding). Eigene Familie, weil hier keine Haus-Strategie
    # rechnet, sondern ein fremder Bot die Quelle ist.
    "moondev_funding": "Bot-Signal",
    "moondev_listingarb": "Bot-Signal",
    "moondev_topmovers": "Bot-Signal",
    "moondev_signalwelle": "Bot-Signal",
    "moondev_marktlage": "Bot-Signal",
    # Die IV-Wand ist keine Bot-Spur: sie rechnet eine Zone aus dem
    # Optionsmarkt. Eigene Familie, damit der Bericht sie nicht unter
    # "Bot-Signal" mischt.
    "iv_wand": "Options-Zone",
    # IV-WAELLE (18.09.2026): dieselbe Optionszone wie iv_wand, nur auf
    # Deribit-IV-Waenden statt auf OKX-OI-Strikes. Gleiche Familie, damit
    # beide Optionszonen im Bericht zusammenstehen.
    "iv_waelle": "Options-Zone",
    # Die drei Sprachmodell-Spuren (17.09.2026): Quelle und Gate sind Haus-Bau,
    # die RICHTUNG kommt aus dem lokalen Modell. Eigene Familie, damit im
    # Bericht sichtbar bleibt, wo ein Sprachmodell geurteilt hat.
    "moondev_whale": "Bot-Signal (LLM)",
    "moondev_liquidation": "Bot-Signal (LLM)",
    "moondev_sentiment": "Bot-Signal (LLM)",
    # MOONDEV_SNIPER (19.09.2026): neue Solana-Launches, deterministische
    # Haus-Regel - dieselbe Familie wie die anderen deterministischen
    # Moon-Dev-Bot-Spuren.
    "moondev_sniper": "Bot-Signal",
}

INDIKATOREN = ("macd_mtf", "squeeze", "supertrend", "wavetrend",
               "trendwende_btc",
               # Schattenarm squeeze_eth (03.10.2026) - eigener Befehl, sonst
               # bediente /bericht squeeze_eth das Buch des Hauptbuchs.
               "squeeze_eth",
               # Prophet-Signal (02.10.2026).
               "prophet_signal",
               "klassik_sma", "klassik_ema", "klassik_macd", "klassik_bollinger",
               "klassik_donchian", "klassik_rsi", "klassik_rsi2",
               "klassik_donchian_trend", "klassik_sr_breaks", "klassik_pmax",
               "klassik_supertrend")


def spuren():
    """Die Spurliste aus `dauerlauf.SPUREN` - gelesen, nicht abgeschrieben.

    Gelesen wird per AST, nicht per Textsuche: eine Textsuche findet die
    Schluessel auch in Kommentaren und Beispielen. Faellt das Lesen aus (Datei
    umgebaut), gibt es eine LEERE Liste und einen Hinweis - eine geratene Liste
    waere schlimmer als keine.
    """
    try:
        import ast                                            # noqa: PLC0415
        with open(DAUERLAUF, "r", encoding="utf-8") as f:
            baum = ast.parse(f.read())
        for knoten in baum.body:
            if isinstance(knoten, ast.Assign) and any(
                    getattr(z, "id", None) == "SPUREN" for z in knoten.targets):
                if isinstance(knoten.value, ast.Dict):
                    return [k.value for k in knoten.value.keys
                            if isinstance(k, ast.Constant)]
        return []
    except Exception:                                         # noqa: BLE001
        return []


def familie(spur):
    return FAMILIE.get(spur, "?")


def klartext(text):
    """HTML-Marken fuer den SkillsBot entfernen (der sendet ohne parse_mode)."""
    return re.sub(r"</?b>", "", text)


def bericht():
    """Der volle Tagesbericht (mit Rangliste) - derselbe Aufruf wie im Handelsbot."""
    return tb.baue(mit_xperp=True)


# --- Lage (jetzt) -----------------------------------------------------------

def _log_alter():
    """Alter des letzten Eintrags in `dauerlauf.log` in Minuten, sonst None.

    Datum und Uhrzeit stehen dort LOKAL und ohne Jahr ("15.09. 20:02:47").
    Verglichen wird in derselben Zone; das Jahr kommt aus dem Bezug. Ein
    Eintrag mehr als einen Tag in der Zukunft gehoert zum Vorjahr - sonst
    meldet die Zeile im Januar ein Alter von einem Jahr.
    """
    try:
        with open(DAUERLAUF_LOG, "r", encoding="utf-8", errors="replace") as f:
            zeilen = f.readlines()[-40:]
    except OSError:
        return None
    import datetime as dt                                     # noqa: PLC0415
    jetzt = dt.datetime.now()
    for zeile in reversed(zeilen):
        treffer = re.match(r"\s*(\d{2})\.(\d{2})\.\s+(\d{2}):(\d{2}):(\d{2})\s",
                           zeile)
        if not treffer:
            continue
        tag, monat, std, minu, sek = (int(x) for x in treffer.groups())
        for jahr in (jetzt.year, jetzt.year - 1):
            try:
                zeit = dt.datetime(jahr, monat, tag, std, minu, sek)
            except ValueError:
                continue
            if zeit - jetzt <= dt.timedelta(hours=12):
                return max(0.0, (jetzt - zeit).total_seconds() / 60.0)
    return None


def _zeit_ortszeit(z):
    """Journalzeit fuer die Anzeige: '2026-09-30T08:15:00+00:00' -> '2026-09-30 10:15'.

    Die Journale tragen UTC (+00:00); alle anderen Zeiten dieser Nachricht
    (Kopfzeile, Zyklusalter) sind Ortszeit. Ohne Umrechnung stand hier die
    UTC-Uhrzeit ohne Hinweis, 1 bis 2 Stunden neben der Kopfzeile. Kein
    str.replace/datetime.replace: der ReinLesendTest verbietet jeden Aufruf
    namens replace. Nicht lesbar oder ohne Uhrzeit -> wie bisher geschnitten.
    """
    import datetime as dt                                     # noqa: PLC0415
    if len(z) < 16:                # nur Datum (orbk): keine Uhrzeit erfinden
        return z
    try:
        return dt.datetime.fromisoformat(z).astimezone().strftime(
            "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return ("%s %s" % (z[:10], z[11:16])) if len(z) >= 16 else z


def _spur_stand(hole):
    """Eine Spur lesen, wie tagesbericht sie liest - Fehler als Text."""
    try:
        return hole()
    except Exception as e:                                    # noqa: BLE001
        return {"name": "?", "fehler": "%s: %s" % (type(e).__name__, e)}


def _takt_minuten():
    """Der Takt, mit dem der Dauerlauf laeuft - aus seiner Startzeile im Log.

    Nicht aus `dauerlauf.py` gelesen: dort steht die OBERGRENZE
    (TAKT_MAX_MINUTEN), nicht der gestartete Wert. Die Logzeile
    "Dauerlauf startet, Takt 15 min" ist die einzige Stelle, an der der
    laufende Wert steht.
    """
    try:
        with open(DAUERLAUF_LOG, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    treffer = re.findall(r"Dauerlauf startet, Takt (\d+) min", text)
    return int(treffer[-1]) if treffer else None


def lage():
    """Die JETZT-Sicht: wo stehen Positionen, welche Tore sind zu.

    Bewusst OHNE Bilanzen, Wachen-Rechnung und Rangliste: die stehen im
    /bericht und in /strategien. Wer diese Zeilen liest, will wissen, was
    gerade offen ist - nicht, wie die Spur historisch gelaufen ist.
    """
    jetzt = dt.datetime.now()
    kopf = ["<b>Handel Lage  %s</b>" % jetzt.strftime("%d.%m.%Y %H:%M")]
    alter = _log_alter()
    takt = _takt_minuten()
    if alter is None:
        kopf.append("letzter Zyklus: unbekannt (Log nicht lesbar)")
    elif takt and alter > takt + 5:
        kopf.append("<b>letzter Zyklus vor %.0f min - Takt ist %d min</b>"
                    % (alter, takt))
    else:
        kopf.append("letzter Zyklus vor %.0f min%s"
                    % (alter, " (Takt %d min)" % takt if takt else ""))


    zeilen, offen_gesamt, freigaben = [], 0, []
    # Ueber die SPUR-SCHLUESSEL aus dauerlauf.SPUREN, nicht ueber die
    # Anzeigenamen der Berichts-Funktionen ("Spur 2  XPERP"): /lage soll
    # dieselben Namen nennen wie /spur und /strategien.
    for name in spuren() or [h.__name__[5:] for h in tb.HOLER]:
        hole = _holer_fuer(name)
        s = _spur_stand(hole) if hole else {
            "name": name, "fehler": "keine Lesefunktion im Bericht"}
        if "fehler" in s:
            zeilen.append("%-11s AUSFALL: %s" % (name, s["fehler"][:60]))
            continue
        lage_der_spur = None
        if s.get("pruefmodul", "wachen_pruefung"):
            lage_der_spur = tb.wachenlage(s)
            if "fehler" in lage_der_spur:
                lage_der_spur = None
        tore = tb.sperren(s, lage_der_spur)
        if s.get("papierfest"):
            tore.insert(0, "kein Live-Zweig")
        if not tore:
            tor = "LIVE OFFEN"
        elif tore[0] == "kein Live-Zweig":
            tor = "Papier"
        else:
            tor = "GESPERRT (%s)" % tore[0]
        positionen = s.get("positionen") or []
        offen_gesamt += len(positionen)
        if positionen:
            mit = [p for p in positionen if p.get("vh") is not None]
            schnitt = (sum(p["vh"] for p in mit) / len(mit)) if mit else None
            stand = "%d offen %s" % (
                len(positionen),
                "%+.1f%%" % schnitt if schnitt is not None else "")
        else:
            stand = "keine Position"
        zeilen.append("%-11s %-13s %s" % (name, stand, tor))
        try:
            fenster = freigabefenster.lade(name)
            if fenster.anfrage_offen():
                freigaben.append("%s: %s" % (name, fenster.text()))
        except Exception:                                     # noqa: BLE001
            pass

    text = kopf + ["", "<b>Spuren</b>"] + zeilen
    if freigaben:
        text += ["", "<b>Offene Freigabe-Anfragen</b>"] + \
                ["  " + x for x in freigaben]
    text += ["", "%d offene Position(en) insgesamt." % offen_gesamt]
    try:
        text.append(tb.spiegelzeile())
    except Exception as e:                                    # noqa: BLE001
        text.append("Journal ausser Haus: nicht geprueft (%s)" % str(e)[:60])
    return "\n".join(text)


# --- Nur die live handelnden Spuren -----------------------------------------

def _positionen_je_modus(name):
    """Offene Positionen einer Spur, nach `modus` getrennt (live/papier).

    Gelesen aus den zustand-Dateien des Spurordners. Nicht jede Spur fuehrt ein
    modus-Feld: die Kontrakt-Spuren buchen live und Papier ins SELBE Buch (dort
    ist die Wache je Position der Unterschied, nicht ein Feld), spur_buch-Spuren
    fuehren getrennte Staende (zustand.live.json). Was kein Feld traegt, wird
    als 'ohne modus-feld' gezaehlt - nicht als live geraten.
    """
    zaehl = {}
    ordner = os.path.join(HIER, name)
    if not os.path.isdir(ordner):
        return zaehl
    for datei in sorted(os.listdir(ordner)):
        if not (datei.startswith("zustand") and datei.endswith(".json")) \
                or ".bak-" in datei:
            continue
        try:
            with open(os.path.join(ordner, datei), encoding="utf-8") as f:
                z = json.load(f)
        except Exception:                                     # noqa: BLE001
            continue
        pos = z.get("positionen")
        if isinstance(pos, list):
            liste = pos
        elif isinstance(z.get("position"), dict):
            liste = [z["position"]]
        else:
            liste = []
        for p in liste:
            m = p.get("modus") or "ohne modus-feld"
            zaehl[m] = zaehl.get(m, 0) + 1
    return zaehl


def _letzter_live_vorgang(name):
    """Die juengste Journalzeile mit modus=live - der letzte echte Vorgang.

    Papier- und Live-Zeilen stehen in denselben Journalen, unterschieden nur
    durch die Spalte `modus` (so schreibt jede Spur seit 14.09.2026). Ein
    fehlendes modus=live heisst: diese Spur hat noch nie mit echtem Geld
    gehandelt - das ist eine Aussage, keine Luecke.
    """
    ordner = os.path.join(HIER, name)
    if not os.path.isdir(ordner):
        return None
    juengste = None
    for datei in sorted(os.listdir(ordner)):
        if not datei.startswith("handelsjournal") or not datei.endswith(".csv") \
                or ".bak-" in datei or "falsch" in datei:
            continue
        try:
            with open(os.path.join(ordner, datei), encoding="utf-8") as f:
                zeilen = list(csv.reader(f))
        except Exception:                                     # noqa: BLE001
            continue
        if not zeilen:
            continue
        kopf = zeilen[0]
        if "modus" not in kopf:
            continue
        i_modus, i_zeit = kopf.index("modus"), kopf.index("zeit") \
            if "zeit" in kopf else 0
        for z in zeilen[1:]:
            if len(z) <= i_modus or z[i_modus] != "live":
                continue
            if juengste is None or z[i_zeit] > juengste[0]:
                juengste = (z[i_zeit], _spalte(z, kopf, "aktion"),
                            _spalte(z, kopf, "inst"))
    return juengste


def _spalte(zeile, kopf, name):
    try:
        return zeile[kopf.index(name)]
    except (ValueError, IndexError):
        return ""


def live():
    """Nur die Spuren, die WIRKLICH live handeln koennen - mit ihrem Ist-Stand.

    WARUM ein eigener Befehl: `/lage` listet alle Spuren, und seit dem Auftrag
    vom 21.09.2026 ('alle weiteren Spuren live offen und handel erlaubt') steht
    `handel_erlaubt=true` in JEDER wachen.json - auch in 22 Spuren, die gar
    keinen Orderaufruf im Code haben. Wer /lage liest, sieht dort 29x 'erlaubt:
    true' und kann nicht unterscheiden, welche Spur echtes Geld bewegen kann.
    Genau diese Unterscheidung macht dieser Befehl.

    Drei Gruppen, hart getrennt:
      1. eigener Haus-Orderweg (xperp, scanner, swap, kraken, mosaic,
         moondev_marktlage) - diese Spuren koennen an der Boerse ordern.
      2. Orderweg ueber eine Fremd-Laufzeit (Nautilus-Node, DEMO-Konto) -
         die Spur selbst hat keine eigene Orderanbindung.
      3. `handel_erlaubt=true` OHNE Orderweg - der Schalter ist dort wirkungslos
         (so steht es als _handel_erlaubt_vermerk in der wachen.json).

    Rein lesend, wie alle Befehle hier.
    """
    import spuren_stand as ss                                  # noqa: PLC0415
    daten = {e["spur"]: e for e in ss.sammle()}
    jetzt = dt.datetime.now()
    kopf = ["<b>Live-Stand  %s</b>" % jetzt.strftime("%d.%m.%Y %H:%M")]
    alter, takt = _log_alter(), _takt_minuten()
    if alter is None:
        kopf.append("letzter Zyklus: unbekannt (Log nicht lesbar)")
    elif takt and alter > takt + 5:
        kopf.append("<b>letzter Zyklus vor %.0f min - Takt ist %d min</b>"
                    % (alter, takt))
    else:
        kopf.append("letzter Zyklus vor %.0f min%s"
                    % (alter, " (Takt %d min)" % takt if takt else ""))

    haus, fremd, stumm = [], [], []
    for name in spuren() or list(daten):
        e = daten.get(name)
        if e is None or not e["order"]:
            stumm.append(name)
            continue
        (haus if e.get("art") == "haus" else fremd).append((name, e))

    def _block(titel, eintraege, hinweis=""):
        if not eintraege:
            return []
        zeilen = ["", "<b>%s</b>" % titel]
        if hinweis:
            zeilen.append(hinweis)
        for name, e in eintraege:
            fenster = e["fenster"]
            tore = []
            if e["erlaubt"] is not True:
                tore.append("handel_erlaubt=%s" % e["erlaubt"])
            if e["frei"] is not True:
                tore.append("freigabe.erfuellt=%s" % e["frei"])
            if not str(fenster).startswith("offen"):
                tore.append("kein offenes Freigabefenster")
            tor = "LIVE BEREIT" if not tore else "gesperrt: " + ", ".join(tore)
            zeilen.append("%-16s %s" % (name, tor))
            buch = _positionen_je_modus(name)
            if buch:
                mix = ", ".join("%s=%d" % kv for kv in sorted(buch.items()))
            else:
                mix = "keine offene Position"
            hol = _holer_fuer(name)
            schnitt = ""
            if hol:
                s = _spur_stand(hol)
                mit = [p for p in (s.get("positionen") or [])
                       if p.get("vh") is not None]
                if mit:
                    schnitt = " (%+.1f%% im Schnitt)" % (
                        sum(p["vh"] for p in mit) / len(mit))
            zeilen.append("                 Fenster %s | Buch: %s%s"
                          % (fenster, mix, schnitt))
            zeilen.append("                 Orderweg: %s | Zyklus %s"
                          % (", ".join(e["order"])[:60],
                             "%s min" % e["alter"] if e["alter"] is not None
                             else "keine Zeile im Log"))
            lv = _letzter_live_vorgang(name)
            if lv:
                # Kein str.replace: der ReinLesendTest verbietet jeden Aufruf
                # namens replace (Path.replace benennt Dateien um) - er kann
                # str.replace nicht davon unterscheiden. Deshalb Slicing.
                kurz = _zeit_ortszeit(lv[0])
                zeilen.append("                 letzter Live-Vorgang: %s %s %s"
                              % (kurz, lv[1], lv[2]))
            else:
                zeilen.append("                 letzter Live-Vorgang: keiner - "
                              "diese Spur hat noch nie mit echtem Geld gehandelt")
        return zeilen

    text = kopf
    text += _block("Eigener Orderweg (echtes Konto moeglich)", haus)
    text += _block("Orderweg ueber Fremd-Laufzeit (DEMO-Konto, kein echtes Geld)",
                   fremd,
                   "Diese Spuren ordern nicht selbst - sie lassen einen "
                   "Nautilus-Node im DEMO-Modus handeln.")
    text += ["", "%d Spur(en) mit Orderweg, davon %d eigene. %d Spur(en) tragen "
             "handel_erlaubt=true OHNE Orderweg - der Schalter ist dort "
             "wirkungslos (Vermerk in der jeweiligen wachen.json)."
             % (len(haus) + len(fremd), len(haus), len(stumm))]
    text.append("Wer eine stumme Spur live nehmen will, baut ZUERST den "
                "Orderweg (/spur NAME zeigt ihre Wachen).")
    return "\n".join(text)


# --- Eine Spur in der Tiefe -------------------------------------------------

def _holer_fuer(name):
    """Die Lesefunktion EINER Spur aus `lage.py` - dieselbe wie im Bericht.

    Nicht nachgebaut: eine zweite Lesefunktion wuerde die Zustandsformen
    (position/positionen, richtung/seite, EUR/USD) ein zweites Mal kennen
    muessen - und beim naechsten neuen Feld nur an einer Stelle mitziehen.
    """
    if name == "xperp":
        # Die XPERP-Spur heisst im Bericht anders (sie zeigt die Rangliste,
        # ihre Positionen haengen an derselben Funktion).
        return lg.spur_xperp_positionen
    return getattr(lg, "spur_%s" % name, None)


def _journal(spur):
    """Alle Zeilen des Handelsjournals als Liste von dicts (Kopf + Zeilen)."""
    pfad = os.path.join(HIER, spur, "handelsjournal.csv")
    try:
        with open(pfad, newline="", encoding="utf-8", errors="replace") as f:
            zeilen = list(csv.reader(f))
    except OSError:
        return []
    if len(zeilen) < 2:
        return []
    kopf, rest = zeilen[0], zeilen[1:]
    return [dict(zip(kopf, z)) for z in rest if len(z) == len(kopf)]


def _letzte_ablehnung(spur):
    """Die letzte Zeile des Ablehnungsprotokolls einer Spur, oder None.

    Liegt neben dem Journal, NIE darin: dessen Leser zaehlen Zeilen als
    Buchungen, eine Ablehnung waere dort eine erfundene Runde.
    """
    pfad = os.path.join(HIER, spur, "ablehnungen.csv")
    try:
        with open(pfad, newline="", encoding="utf-8", errors="replace") as f:
            zeilen = [z for z in csv.reader(f) if z]
    except OSError:
        return None
    if len(zeilen) < 2:
        return None
    return dict(zip(zeilen[0], zeilen[-1]))


def _wachenzeilen(name, s):
    """Wachen und Ratsche einer Spur - gelesen, nicht gerechnet.

    Rueckgabe: (Zeilen, lage) - `lage` geht an `tb.sperren` weiter, damit
    dieselbe Rechnung nicht zweimal laeuft.
    """
    aus = []
    w = s.get("w") or {}
    lage_der_spur = None
    if s.get("pruefmodul", "wachen_pruefung"):
        lage_der_spur = tb.wachenlage(s)
        if "fehler" in lage_der_spur:
            aus.append("Wachen nicht lesbar: %s" % lage_der_spur["fehler"][:80])
            lage_der_spur = None
    if lage_der_spur:
        rueck = lage_der_spur.get("ruecklauf_%s" % s["waehrung"].lower())
        aus.append("Handelsrunden %d (Papier %d, %d Betriebsstoerung), "
                   "Ruecklauf %.2f %s, Faktor %.2f"
                   % (lage_der_spur.get("runden_echt", lage_der_spur["runden_gesamt"]),
                      lage_der_spur.get("runden_papier_echt", lage_der_spur["runden_papier"]),
                      lage_der_spur.get("runden_stoerung", 0),
                      0.0 if rueck is None else rueck, s["waehrung"],
                      lage_der_spur["groessenfaktor"]))
    try:
        import ratschen                                        # noqa: PLC0415
        schwelle = ratschen.halbierungsschwelle(w)
        if schwelle is None:
            aus.append("Ratsche: keine Schwelle (weder Betrag noch Buchrisiko)")
        else:
            hoch = (lage_der_spur or {}).get("hoch", 0)
            aus.append("Ratsche: halbiert ab %.2f %s Ruecklauf, im Gewinn %s"
                       % (schwelle, s["waehrung"],
                          "ja" if ratschen.im_gewinn(hoch, w, schwelle) else "nein"))
    except Exception as e:                                    # noqa: BLE001
        aus.append("Ratsche nicht lesbar: %s" % str(e)[:60])
    return aus, lage_der_spur


def spur(name):
    """EINE Spur in der Tiefe: Positionen, Bilanz, Wachen, Ratsche, Journal."""
    name = (name or "").strip().split()[0].lower() if (name or "").strip() else ""
    bekannt = spuren()
    if not bekannt:
        return "Spurliste nicht lesbar: SPUREN in dauerlauf.py nicht gefunden."
    if name not in bekannt:
        return ("Unbekannte Spur: %s\nBekannt: %s"
                % (name or "(leer)", ", ".join(bekannt)))
    hole = _holer_fuer(name)
    if hole is None:
        return "Fuer %s gibt es im Bericht keine Lesefunktion." % name
    s = _spur_stand(hole)
    if "fehler" in s:
        return "<b>%s</b>\n  AUSFALL: %s" % (name, s["fehler"][:200])

    aus = ["<b>%s</b>  %s" % (name, familie(name) if familie(name) != "?" else "")]
    aus.append("  Modus %s, letzter Lauf %s"
               % (s["z"].get("modus") or s["w"].get("modus") or "?",
                  s["z"].get("letzter_lauf", "?")))
    if s["w"].get("stillgelegt"):
        aus.append("  STILLGELEGT - kein Lauf mehr, weder Papier noch Live.")
    positionen = s.get("positionen") or []
    if positionen:
        aus.append("  <b>Positionen</b>")
        for p in positionen:
            aus.append(tb.zeile_position(p, s["waehrung"]))
        summe = sum(p["wert"] for p in positionen)
        mit = [p for p in positionen if p.get("vh") is not None]
        if mit:
            aus.append("  = %d Positionen, %.0f %s gebunden, im Schnitt %+.1f%%"
                       % (len(positionen), summe, s["waehrung"],
                          sum(p["vh"] for p in mit) / len(mit)))
    else:
        aus.append("  keine offene Position")
    if s.get("bilanz"):
        aus.append("  %s" % s["bilanz"])
    wachen_zeilen, wachen_lage = _wachenzeilen(name, s)
    aus += ["  " + z for z in wachen_zeilen]
    tore = tb.sperren(s, wachen_lage)
    if s.get("papierfest"):
        tore.insert(0, "kein Live-Zweig (Papierpfad)")
    aus.append("  Live: %s" % ("GESPERRT - " + "; ".join(tore) if tore else "offen"))

    zeilen = _journal(name)
    if zeilen:
        letzte = zeilen[-1]
        teile = [letzte.get(k) for k in ("zeit", "aktion", "inst", "paar", "symbol",
                                         "grund") if letzte.get(k)]
        aus.append("  Journal: %d Buchungen, letzte: %s"
                   % (len(zeilen), " ".join(str(t) for t in teile)))
    else:
        aus.append("  Journal: keine Buchung")
    ablehnung = _letzte_ablehnung(name)
    if ablehnung:
        teile = [ablehnung.get(k) for k in ("zeit", "grund", "anzahl", "kennung",
                                            "detail") if ablehnung.get(k)]
        aus.append("  Ablehnungen (letzte Zeile): %s" % " ".join(str(t) for t in teile))
    zweit = s["z"].get("journal_zweitziel")
    if zweit:
        ok = s["z"].get("journal_zweitziel_ok")
        aus.append("  Kopie ausser Haus: %s (%s)"
                   % (zweit, "ok" if ok else "ABWEICHUNG oder noch nicht geprueft"))
    return "\n".join(aus)


# --- Strategien (Bilanz) ----------------------------------------------------

# Spuren mit einem eigenen `auswertung.py` im Spurordner. Ihre Auswertung ist
# die zustaendige Quelle - hier wird sie nur zitiert, nicht nachgebaut.
EIGENE_AUSWERTUNG = ("spiegel", "omniquant", "gitter", "kopier")

EINSTIEGE = ("kauf", "eroeffnen", "einstieg")
AUSSTIEGE = ("verkauf", "schliessen", "ausstieg", "notaus")


def _indikator_zaehlung(spur):
    """(Einstiege, Ausstiege) aus dem Journal - nur fuer Spuren ohne Auswertung.

    Kein Ergebnis: ohne die Kosten- und Paarungslogik der Spur waere eine hier
    gerechnete Zahl eine zweite Formel. Fehlt eine eigene Auswertung, wird das
    gesagt - nicht geschaetzt.
    """
    ein = raus = 0
    for r in _journal(spur):
        aktion = (r.get("aktion") or "").strip().lower()
        if aktion in EINSTIEGE:
            ein += 1
        elif aktion in AUSSTIEGE:
            raus += 1
    return ein, raus


def _gruende(spur):
    """Die Ausstiegsgruende einer Spur mit Anzahl, haeufigster zuerst."""
    zaehler = {}
    for r in _journal(spur):
        if (r.get("aktion") or "").strip().lower() in AUSSTIEGE:
            grund = (r.get("grund") or "ohne").strip() or "ohne"
            zaehler[grund] = zaehler.get(grund, 0) + 1
    return sorted(zaehler.items(), key=lambda kv: -kv[1])


def _brutto_zusatz(k):
    """Der kurze Zusatz, der sagt, ob die Zahl brutto ist (T-192, 01.10.2026).

    EINE Stelle: /strategien und /bericht zeigen dieselbe Zeile, und beide
    muessen dieselbe Auskunft geben. Ohne den Zusatz liest sich die Zahl auf
    dem Handy wie ein Nettoergebnis - und zwei Spuren mit Verschiedenem
    werden vergleichbar. Leer, wenn die Spur schon netto rechnet.
    """
    if not k.get("brutto"):
        return ""
    if k.get("gebuehr") and k.get("einsatz"):
        return "  netto %+.2f" % k["netto"]
    if not k.get("einsatz"):
        return "  (Punkte, brutto)"
    return "  (brutto, Gebuehr unbekannt)"


def strategien():
    """Die BILANZ aller Spuren nebeneinander - je Spur aus ihrer Quelle.

    Das ist die Antwort auf "welche Strategie traegt?" - nicht /lage (das
    zeigt, was JETZT offen ist) und nicht /bericht (das zeigt alles
    ausfuehrlich).
    """
    import auswertung_alle as aa                              # noqa: PLC0415
    aus = ["<b>Strategien  %s</b>" % dt.datetime.now().strftime("%d.%m.%Y %H:%M")]
    # Nach FAMILIE gruppiert: eine Ueberschrift je Strategie, nicht je Spur.
    gruppen = {}
    for spur in spuren():
        gruppen.setdefault(familie(spur), []).append(spur)
    for fam, liste in gruppen.items():
        aus.append("<b>%s</b>" % fam)
        for spur in liste:
            k = aa.kennzahlen_fuer(spur)
            if k:
                text = "%d Runden  %3.0f %% Treffer  %+.2f %s" % (
                    k["n"], k["treffer_pct"], k["ergebnis"],
                    k.get("einheit") or "USD")
                if k.get("n_stoerung"):
                    text += "  (+%d Betriebsstoerung)" % k["n_stoerung"]
                text += _brutto_zusatz(k)
                if k["n"] < aa.MIN_RUNDEN:
                    text += "  *"
            elif spur in EIGENE_AUSWERTUNG:
                text = tb.bilanz(spur)
            else:
                ein, raus = _indikator_zaehlung(spur)
                text = ("keine geschlossene Runde (%d Einstiege, %d Ausstiege)"
                        % (ein, raus) if (ein or raus) else "keine Buchung")
            aus.append("  %-11s %s" % (spur, text))
    aus.append("")
    aus.append("* unter %d Runden: das ist ein Befund, keine Messung." % aa.MIN_RUNDEN)
    aus.append("Zahlen aus der Auswertung der jeweiligen Spur. /spur NAME zeigt "
               "eine einzelne Spur.")
    return "\n".join(aus)


# --- Indikator-Spuren -------------------------------------------------------

def indikatoren():
    """Die vier Indikator-Spuren: Signale, offene Positionen, Ausstiegsgruende.

    Sie haben JE EINEN Indikator (kein Ensemble) - so ist bei einem Verlust
    zuzuordnen, welcher Baustein schuld war. Genau deshalb stehen sie hier
    einzeln und nicht als eine Summe.
    """
    aus = ["<b>Indikator-Spuren  %s</b>" % dt.datetime.now().strftime("%d.%m. %H:%M")]
    bekannt = spuren()
    for spur in INDIKATOREN:
        if bekannt and spur not in bekannt:
            aus.append("%s: nicht in dauerlauf.SPUREN" % spur)
            continue
        hole = _holer_fuer(spur)
        s = _spur_stand(hole) if hole else {"name": spur, "fehler": "kein Leser"}
        if "fehler" in s:
            aus.append("<b>%s</b>  AUSFALL: %s" % (spur, s["fehler"][:80]))
            continue
        ein, raus = _indikator_zaehlung(spur)
        tore = tb.sperren(s, None)
        if s.get("papierfest"):
            tore.insert(0, "kein Live-Zweig")
        stand_tor = ("Papier (kein Live-Zweig)" if tore and tore[0] == "kein Live-Zweig"
                     else "GESPERRT (%s)" % tore[0] if tore else "LIVE OFFEN")
        aus.append("")
        aus.append("<b>%s</b>  %s" % (spur, stand_tor))
        positionen = s.get("positionen") or []
        for p in positionen:
            aus.append(tb.zeile_position(p, s["waehrung"]))
        gruende = _gruende(spur)
        stand = "%d Einstiege, %d Ausstiege, %d offen" % (
            ein, raus, len(positionen))
        if gruende:
            stand += " (%s)" % ", ".join("%s %d" % g for g in gruende)
        aus.append("  " + stand)
        aus.append("  letzter Lauf %s" % s["z"].get("letzter_lauf", "?"))
    aus.append("")
    aus.append("Reine Beobachtung: alle vier sind Papier (handel_erlaubt=false), "
               "kein Live-Zweig. Treffer je Ausstiegsgrund stehen oben.")
    return "\n".join(aus)


# --- Markt (Beobachtung) ----------------------------------------------------

MARKT_PAARE = ("BTC-USDT", "ETH-USDT", "SOL-USDT")


def _sma(werte, n):
    if len(werte) < n:
        return None
    return sum(werte[-n:]) / n


def _atr(kerzen, n=14):
    """ATR ueber die letzten n Kerzen (True Range, Wilder-naeherung)."""
    if len(kerzen) < n + 1:
        return None
    tr = []
    for i in range(1, len(kerzen)):
        hoch, tief, vor = kerzen[i][2], kerzen[i][3], kerzen[i - 1][4]
        tr.append(max(hoch - tief, abs(hoch - vor), abs(tief - vor)))
    return sum(tr[-n:]) / n


def _kurs_text(x):
    if x is None:
        return "?"
    if abs(x) >= 1000:
        return "%.0f" % x
    return "%.2f" % x


def markt(paare=MARKT_PAARE):
    """Ein kurzes Marktbild der Hauptpaare - Kurs, 24 h, Trend, Volatilitaet.

    Bewusst NICHT die Prognose: die laeuft ueber den ganzen Markt, dauert
    Minuten und gehoert in den SkillsBot (/prognose). Hier stehen drei
    Abrufe je Paar - das ist die Frage "wie steht der Markt gerade?", nicht
    "gibt es heute einen Einstieg?".
    """
    scanner = os.path.join(HIER, "scanner")
    if scanner not in sys.path:
        sys.path.append(scanner)
    aus = ["<b>Markt  %s</b>" % dt.datetime.now().strftime("%d.%m. %H:%M"),
           "OKX Spot, 1-h-Kerzen."]
    try:
        import okx                                            # noqa: PLC0415
    except Exception as e:                                    # noqa: BLE001
        return "Markt nicht lesbar: %s" % str(e)[:80]
    for paar in paare:
        try:
            kerzen = okx.kerzen(paar, "1H", 200)
            schluss = [k[4] for k in kerzen]
            kurs = schluss[-1]
            aenderung = (kurs / schluss[-25] - 1) * 100 if len(schluss) > 25 else None
            atr = _atr(kerzen)
            atr_pct = (atr / kurs * 100) if atr else None
            sma = _sma(schluss, 50)
            abstand = (kurs / sma - 1) * 100 if sma else None
            aus.append("%-9s %8s   24h %s   ATR(1h) %s   SMA50 %s"
                       % (paar, _kurs_text(kurs),
                          "%+.1f %%" % aenderung if aenderung is not None else "?",
                          "%.2f %%" % atr_pct if atr_pct is not None else "?",
                          "%+.1f %%" % abstand if abstand is not None else "?"))
        except Exception as e:                                # noqa: BLE001
            aus.append("%-9s nicht lesbar: %s" % (paar, str(e)[:60]))
    aus.append("")
    aus.append("SMA50: Abstand des Kurses zum 50-Stunden-Mittel (Trendlage). "
               "ATR: mittlere Bewegung je Stunde. Keine Order, keine Prognose.")
    return "\n".join(aus)


# --- Hilfe ------------------------------------------------------------------

def hilfe():
    """Die Befehlsuebersicht - nach Zweck gruppiert, nicht nach Alter."""
    return "\n".join([
        "<b>Handelsbefehle</b>",
        "<b>Wie steht es gerade</b>",
        "  /lage        offene Positionen je Spur, Live-Tore, Freigaben",
        "  /live        NUR die Spuren mit Orderweg (welche Spur kann echtes "
        "Geld bewegen) - Fenster, Buch, letzter echter Vorgang",
        "  /bericht     voller Tagesbericht (mit Rangliste)",
        "  /spuren      alle Spur-Namen",
        "<b>Eine Spur / eine Strategie</b>",
        "  /spur NAME   eine Spur in der Tiefe (Positionen, Wachen, Journal)",
        "  /strategien  Bilanz aller Strategien nebeneinander",
        "  /indikatoren die vier Indikator-Spuren: Signale und Treffer",
        "<b>Markt</b>",
        "  /markt       Kurs, 24 h, Trend, Volatilitaet (Beobachtung)",
        "  /prognose [N] Marktbeobachtung long/short - im SkillsBot (blockiert "
        "hier den Handelszyklus)",
        "<b>Freigabe</b>",
        "  /freigabe_xperp  Anfrage und Grenzen lesen",
        "  /ja_xperp STUNDEN  nur XPERP freigeben (max. 24 h)",
        "  /nein_xperp /stop_xperp  XPERP-Fenster schliessen",
        "  /ja [h] /nein /stop      wartende Freigabe, Ablehnung, alles zu",
        "<b>Steuerung</b>",
        "  /scan /papierstatus /pause /weiter",
    ])



