# -*- coding: utf-8 -*-
"""Wer claimt welches Plattform-Credential? (rein lesend, NIE Werte ausgeben)

Gegenprobe fuer den „duplicate credential"-Hinweis in `hermes gateway status` /
`hermes doctor`: die Statusbox kann ein veraltetes Election-Artefakt sein (z.B. nach
grosser Source-Update, wenn ein Profil-Standalone den Host-Lock haelt). Dieses Skript
laedt die ECHTE Claim-Logik (hermes_cli.gateway_migrate._credential_claims) ueber alle
Profile und druckt je Profil + Plattform den Fingerabdruck — als Kuerzel, nie als Wert.

Lesart:
- JEDES Profil mit Claim einen EIGENEN Fingerabdruck = kein Duplikat, der Hinweis ist
  falsch; der Befund liegt woanders (Host-Lock / Topologie).
- ZWEI Profile mit GLEICHEM Fingerabdruck = echter Duplikat-Token; den aus dem Profil
  loeschen, das ihn nicht besitzen soll (oder profile_routes nutzen), dann
  `hermes gateway migrate --multiplex`.
- Ein Profil OHNE Claim, das die Box beschuldigt = die Box liest eine Fallback-Kennung
  (scoped Read mit Default-Fallback), kein eigener Token im .env.

Aufruf:
    python gateway-claim-probe.py [--home <HERMES_HOME>] [--platform telegram|all]

--home: HERMES_HOME (Env-Vorgabe HERMES_HOME, sonst Fehlersmeldung). Das Skript laeuft
mit dem Python, das die hermes-agent-Deps tragen kann; fehlt ein Modul (z.B. ruamel im
Checkout-venv), wird der site-packages-Pfad der gestagten install-Umgebung automatisch
gesucht und ergaenzt.
"""
import argparse
import glob
import os
import sys


def hermes_home():
    return os.environ.get("HERMES_HOME")


def bootstrap(checkout):
    sys.path.insert(0, checkout)
    for attempt in range(2):
        try:
            from hermes_cli import gateway_migrate  # noqa: F401
            return gateway_migrate
        except ModuleNotFoundError as exc:
            if attempt == 0:
                # gestagte install-Umgebung finden, die das fehlende Modul traegt
                base = os.path.dirname(os.path.abspath(checkout))
                pattern = os.path.join(base, "installs", "*", "environments", "*", "venv", "Lib", "site-packages")
                need = exc.name.split(".")[0].lower()
                for sp in glob.glob(pattern):
                    if os.path.isdir(os.path.join(sp, need)) or need == "ruamel":
                        sys.path.append(sp)
                        break
            else:
                raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", default=hermes_home(), help="HERMES_HOME")
    p.add_argument("--platform", default="telegram", help="telegram (Vorgabe) oder all")
    a = p.parse_args()
    if not a.home or not os.path.isdir(a.home):
        sys.exit("HERMES_HOME fehlt oder ungueltig: %r (Env HERMES_HOME oder --home)" % a.home)
    checkout = os.path.join(a.home, "hermes-agent")
    gm = bootstrap(checkout)
    want = None if a.platform == "all" else a.platform.lower()
    with gm._multiplex_read_mode():
        for name, home in gm._profile_homes():
            try:
                cfg = gm._profile_gateway_config(home)
            except Exception as exc:
                print("%-28s CONFIG-FEHLER %s" % (name, type(exc).__name__))
                continue
            claims = gm._credential_claims(cfg)
            rows = []
            for (plat, fp), _val in sorted(claims.items(), key=lambda kv: str(kv[0][0])):
                plat_s = str(plat).lower()
                if want and plat_s != want:
                    continue
                shown = str(fp)[:10] + "..." if isinstance(fp, str) and len(str(fp)) > 12 else str(fp)
                rows.append("%s:%s" % (plat_s, shown))
            if rows:
                print("%-28s %s" % (name, "  ".join(rows)))
            else:
                print("%-28s (kein %s-claim)" % (name, want or ""))


if __name__ == "__main__":
    main()
