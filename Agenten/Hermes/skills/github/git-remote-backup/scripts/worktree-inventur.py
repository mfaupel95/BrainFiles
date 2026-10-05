#!/usr/bin/env python3
"""Inventur aller registrierten git worktrees eines Baumes.

Je Worktree: Zweig, Commits die NICHT in master liegen, uncommittete Dateien.
Aufruf:  python worktree-inventur.py [<wurzel>] [<zweigsbasis>]
Beispiel: python worktree-inventur.py "C:/pfad/baum" master

Nur lesend. Beendet sich mit 0; findet es nichts, meldet es das explizit.
"""
import os
import subprocess
import sys


def git(root, *args, cwd=None):
    r = subprocess.run(
        ['git', '-C', cwd or root] + list(args),
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    basis = sys.argv[2] if len(sys.argv) > 2 else 'master'
    if not os.path.isdir(os.path.join(root, '.git')) and not os.path.isfile(
            os.path.join(root, '.git')):
        print('kein Repo unter', root)
        return 1

    rc, out, err = git(root, 'worktree', 'list', '--porcelain')
    if rc != 0:
        print('git worktree list fehlgeschlagen:', err)
        return 1
    pfade = [l[len('worktree '):] for l in out.splitlines() if l.startswith('worktree ')]

    print('registrierte Worktrees:', len(pfade))
    for w in pfade:
        ist_wurzel = os.path.normcase(w) == os.path.normcase(root)
        _, zweig, _ = git(root, 'rev-parse', '--abbrev-ref', 'HEAD', cwd=w)
        _, eigene, _ = git(root, 'log', '--oneline', '%s..HEAD' % basis, cwd=w)
        _, schmutz, _ = git(root, 'status', '--porcelain', cwd=w)
        eigene_l = [l for l in eigene.splitlines() if l]
        schmutz_l = [l for l in schmutz.splitlines() if l]
        print('==', w, '(WURZEL)' if ist_wurzel else '')
        print('   zweig        :', zweig)
        print('   eigene commits: %d  -> %s' % (
            len(eigene_l), 'ARBEIT, erst auf origin sichern' if eigene_l else 'toter zweig'))
        for l in eigene_l[:8]:
            print('      +', l)
        print('   uncommitted   : %d' % len(schmutz_l))
        for l in schmutz_l[:10]:
            print('      ?', l)
    return 0


if __name__ == '__main__':
    sys.exit(main())