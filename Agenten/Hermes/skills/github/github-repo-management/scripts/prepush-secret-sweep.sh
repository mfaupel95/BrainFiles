#!/usr/bin/env bash
# Pre-push secret sweep for a git repo that is about to get a remote.
# Scans the tracked tree, .gitignore coverage, ignored/untracked sensitive
# files, the FULL history (git log -p --all), and credential fields in JSON
# configs. Output is masked: values are never printed, only their shape.
#
# Usage: bash prepush-secret-sweep.sh <repo-dir>
# Exit:  0 = clean (only env-var names / placeholders), 2 = repo missing
set -u

repo="$1"
cd "$repo" 2>/dev/null || { echo "FEHLER: Repo nicht erreichbar: $repo"; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "FEHLER: kein Git-Repo: $repo"; exit 2; }

MASK='s/([A-Za-z0-9_\-]{16,})/\1⟨…⟩/g'

echo "=== 1) Getrackte Dateien mit Credential-Namen ==="
git ls-files | grep -iE '\.(env|key|pem|pfx|p12)$|credential|secret|token' || echo "   (keine)"

echo; echo "=== 2) .gitignore deckt Credentials ab? ==="
grep -inE 'env|\.key|\.pem|cred|secret|token' .gitignore 2>/dev/null || echo "   (keine Treffer)"

echo; echo "=== 3) Sensibel benannte Dateien im Baum (auch ignoriert) ==="
git status --porcelain --ignored=matching | grep -iE '\.env|\.key|\.pem|cred|secret|token' || echo "   (keine)"
find . -maxdepth 3 -name '.env*' -not -path './.venv/*' 2>/dev/null | grep -v '^\./\.git/' || echo "   (keine .env-Dateien)"

echo; echo "=== 4) Verlauf: Wert-artige Treffer (maskiert) ==="
git log -p --all | grep -iE 'api[_-]?key[[:space:]]*[=:]|api[_-]?secret|passphrase|passw(or)?d[[:space:]]*[=:]|BEGIN (RSA|OPENSSH|PRIVATE)|token[[:space:]]*[=:]' \
  | grep -vE '^\+\+\+|^---' \
  | sed -E "$MASK" \
  | grep -vE '\$\{env:|"\.\.\."|setx |<.*>' \
  | sort -u | head -30
echo "   (leer = sauber)"

echo; echo "=== 5) JSON-Configs: Credential-Felder nur als Form (nie Werte) ==="
python3 - <<'PY'
import json, glob, re
seen = False
for pat in ('config/*.json', '*.json'):
    for f in glob.glob(pat):
        try:
            with open(f, encoding='utf-8') as fh: d = json.load(fh)
        except Exception:
            continue
        hits = []
        def walk(o, p=''):
            if isinstance(o, dict):
                for k, v in o.items():
                    if any(s in k.lower() for s in ('key','secret','pass','token','cred','pwd')):
                        vs = str(v)
                        kind = '<leer>' if not vs else ('<PLATZHALTER>' if re.fullmatch(r'\$\{env:[A-Z_]+\}', vs) or any(t in vs.lower() for t in ('xxx','<','your','placeholder','aaaa')) else '<WERT len=%d>' % len(vs))
                        hits.append(f'{p}{k} = {kind}')
                    else:
                        walk(v, p + k + '.')
            elif isinstance(o, list):
                for i, x in enumerate(o): walk(x, p + f'[{i}].')
        walk(d)
        if hits:
            seen = True
            print(f'-- {f}')
            for h in hits:
                print('   ' + h)
if not seen:
    print('   (keine Credential-Felder)')
PY

echo; echo "=== Ergebnis ==="
echo "Sauber, wenn in 4 und 5 nur Env-Var-Namen, Platzhalter oder 'keine' stehen."
