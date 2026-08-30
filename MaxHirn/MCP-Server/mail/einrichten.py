"""
Einmalige Einrichtung: Gmail-Adresse und App-Passwort hinterlegen.

Gespeichert wird im Windows-Anmeldeinformationsspeicher, nicht in einer Datei.
Das Passwort wird waehrend der Eingabe nicht angezeigt und taucht in keinem
Protokoll auf.

Voraussetzung: Zwei-Faktor-Anmeldung im Google-Konto aktiv, danach unter
https://myaccount.google.com/apppasswords ein App-Passwort erzeugen
(16 Zeichen). Das normale Kontopasswort lehnt Gmail fuer SMTP ab.

Aufruf:
    .venv\\Scripts\\python.exe einrichten.py
"""

import getpass
import sys

import keyring

from mailversand import DIENST, SCHLUESSEL_ADRESSE, VersandFehler, zugang_pruefen


def main() -> int:
    print("Gmail-Zugang fuer den Mailversand hinterlegen")
    print("-" * 46)

    vorhanden = keyring.get_password(DIENST, SCHLUESSEL_ADRESSE)
    if vorhanden:
        print(f"Bereits hinterlegt: {vorhanden}")
        if input("Ueberschreiben? [j/N] ").strip().lower() not in ("j", "ja"):
            print("Unveraendert.")
            return 0

    adresse = input("Gmail-Adresse: ").strip()
    if "@" not in adresse:
        print("Das ist keine Adresse.", file=sys.stderr)
        return 1

    passwort = getpass.getpass("App-Passwort (16 Zeichen, Eingabe bleibt unsichtbar): ")
    passwort = passwort.replace(" ", "")  # Google zeigt es in Viererbloecken an
    if len(passwort) != 16:
        print(f"Warnung: {len(passwort)} Zeichen statt der ueblichen 16.", file=sys.stderr)

    keyring.set_password(DIENST, SCHLUESSEL_ADRESSE, adresse)
    keyring.set_password(DIENST, adresse, passwort)
    print("Gespeichert. Pruefe die Anmeldung ...")

    try:
        ergebnis = zugang_pruefen()
    except VersandFehler as fehler:
        print(f"\nFehlgeschlagen:\n{fehler}", file=sys.stderr)
        return 1

    print(f"Anmeldung erfolgreich fuer {ergebnis['adresse']}.")
    print("\nFertig. Ab jetzt verschickt Claude Dateien direkt, ohne Browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
