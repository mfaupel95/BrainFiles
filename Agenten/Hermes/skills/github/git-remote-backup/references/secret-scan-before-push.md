# Secret scan before pushing a repo to a remote

A credential committed once stays in the repo history forever; removing it
means rewriting history. Scan before the FIRST push of any repo that ever
touched keys, tokens, env-file setups or trading credentials — the check
covers the history, not just the working tree.

## 1. Full history + worktree

```bash
git log -p --all | grep -iE "api[_-]?key|secret|passw|BEGIN (RSA|OPENSSH|PRIVATE)|bearer|token[[:space:]]*[=:]" \
  | grep -vE "^(\+\+\+|---)" | sort | uniq -c | sort -rn
```

Clean result: only env-var NAMES (`${env:OKX_API_KEY}`), `"..."`
placeholders, comments and code that reads from the environment. Dirty
result: printable key material — do NOT push; exclude or rewrite first.

Mask long tokens in the output so real values never land in the
conversation: `... | sed -E 's/([A-Za-z0-9_\-]{16,})/\1<MASKED>/g'`.

## 2. Credential-shaped fields in tracked configs

Walk every tracked config (JSON/YAML/INI) and print only the SHAPE of
fields whose name contains key/secret/pass/token/cred/pwd — never the value:

```python
import json

def walk(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if any(s in k.lower() for s in ('key','secret','pass','token','cred','pwd')):
                s = str(v)
                print(p+k, '=', '<leer>' if not s else
                      ('<PLATZHALTER>' if any(t in s.lower() for t in ('xxx','<','your','placeholder','aaaa'))
                       else '<WERT len=%d>' % len(s)))
            else:
                walk(v, p+k+'.')
    elif isinstance(o, list):
        for i, x in enumerate(o):
            walk(x, p+'[%d].' % i)

for f in ['config/a.json', 'config/b.json']:
    print('--', f)
    walk(json.load(open(f)))
```

## 3. Also check

- `git status --porcelain --ignored=matching | grep -iE '\.env|key|secret|cred'`
  — sensitive files present but merely ignored are fine for a push only if
  the .gitignore rule really covers them (confirm the pattern list).
- The ideal shape is configs with NO credential fields at all, secrets
  injected from the environment at runtime.
- After a clean result, commit nothing extra: push the existing history as
  it is.
