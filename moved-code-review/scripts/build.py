#!/usr/bin/env python3
"""Render a commit, range, or PR as a GitHub-style review page that folds moved code.

Usage:
  build.py <target> <out.html> [--title NAME] [--ws MODE] [--repo-dir DIR]

<target> is a commit (abc123), a range (A..B or A...B), or a PR (#123 / pr:123).
--ws passes through to --color-moved-ws (e.g. allow-indentation-change).
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ANSI = re.compile(r'\x1b\[([0-9;]*)m')

# Pin git's colors so user/repo color config can't change what the parser sees.
GIT_COLOR_CONFIG = {
    'color.diff.old': 'red', 'color.diff.new': 'green',
    'color.diff.frag': 'cyan', 'color.diff.meta': 'bold', 'color.diff.context': 'normal',
    'color.diff.whitespace': 'normal red',
    'color.diff.oldMoved': 'bold magenta', 'color.diff.newMoved': 'bold cyan',
    'color.diff.oldMovedAlternative': 'bold blue', 'color.diff.newMovedAlternative': 'bold yellow',
    'color.diff.oldMovedDimmed': 'dim', 'color.diff.newMovedDimmed': 'dim',
    'color.diff.oldMovedAlternativeDimmed': 'dim italic', 'color.diff.newMovedAlternativeDimmed': 'dim italic',
    'diff.noprefix': 'false', 'diff.mnemonicPrefix': 'false', 'diff.external': '',
}
ALTERNATE_CODES = {'2;3', '1;34', '1;33'}
BOUNDARY_PREFIX = '1;'


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def git(args, cwd):
    cfg = [x for k, v in GIT_COLOR_CONFIG.items() for x in ('-c', f'{k}={v}')]
    return run(['git', *cfg, *args], cwd)


def diff_flags(ws):
    flags = ['--color=always', '--color-moved=dimmed-zebra', '--no-ext-diff', '-M']
    if ws:
        flags.append(f'--color-moved-ws={ws}')
    return flags


def resolve_target(target, ws, cwd):
    """Return (meta, colored diff text)."""
    pr = re.fullmatch(r'(?:#|pr:)(\d+)', target)
    if pr:
        num = pr.group(1)
        info = json.loads(run(['gh', 'pr', 'view', num, '--json',
                               'title,body,url,author,baseRefName,headRefOid,createdAt'], cwd))
        run(['git', 'fetch', '--quiet', 'origin', f'refs/pull/{num}/head', info['baseRefName']], cwd)
        base = run(['git', 'merge-base', f'origin/{info["baseRefName"]}', info['headRefOid']], cwd).strip()
        meta = {'subject': info['title'], 'ref': f'#{num}', 'url': info['url'],
                'author': info['author'].get('name') or info['author']['login'],
                'date': info['createdAt'][:10], 'body': info['body'].strip()}
        return meta, git(['diff', *diff_flags(ws), base, info['headRefOid']], cwd)

    if '..' in target:
        log_range = target.replace('...', '..')
        commits = run(['git', 'log', '--reverse', '--format=%h %s', log_range], cwd).strip()
        meta = {'subject': f'Changes in {target}', 'ref': target, 'url': None,
                'author': run(['git', 'log', '-1', '--format=%an', log_range], cwd).strip(),
                'date': run(['git', 'log', '-1', '--format=%ad', '--date=short', log_range], cwd).strip(),
                'body': commits}
        return meta, git(['diff', *diff_flags(ws), target], cwd)

    fields = run(['git', 'log', '-1', '--format=%H%x00%an%x00%ad%x00%s%x00%b', '--date=format:%b %-d, %Y %-I:%M %p', target], cwd)
    sha, author, date, subject, body = fields.split('\x00')
    meta = {'subject': subject, 'ref': sha[:11], 'url': None, 'author': author, 'date': date, 'body': body.strip()}
    return meta, git(['show', '--format=', *diff_flags(ws), target], cwd)


def parse(colored):
    files, cur, hunk = [], None, None
    for raw in colored.split('\n'):
        codes = ANSI.findall(raw)
        text = ANSI.sub('', raw)
        first = codes[0] if codes else ''
        if text.startswith('diff --git'):
            m = re.match(r'diff --git a/(.*) b/(.*)', text)
            cur = {'old': m.group(1), 'new': m.group(2), 'status': 'modified', 'similarity': None, 'hunks': []}
            files.append(cur)
            hunk = None
            continue
        if cur is None:
            continue
        if hunk is None or text.startswith('@@'):
            if text.startswith('deleted file'):
                cur['status'] = 'deleted'
            elif text.startswith('new file'):
                cur['status'] = 'added'
            elif text.startswith('similarity index'):
                cur['status'], cur['similarity'] = 'renamed', text.split()[-1]
            elif text.startswith('@@'):
                m = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@ ?(.*)', text)
                hunk = {'o': int(m.group(1)), 'n': int(m.group(2)), 'ctx': m.group(3), 'lines': [],
                        '_o': int(m.group(1)), '_n': int(m.group(2))}
                cur['hunks'].append(hunk)
            continue
        if raw == '' or text.startswith('\\'):
            continue
        sign, body = text[:1], text[1:]
        if sign == ' ':
            hunk['lines'].append(['ctx', 0, body, [hunk['_o'], hunk['_n']]])
            hunk['_o'] += 1
            hunk['_n'] += 1
            continue
        side = 'del' if sign == '-' else 'add'
        nums = [hunk['_o'], None] if side == 'del' else [None, hunk['_n']]
        hunk['_o' if side == 'del' else '_n'] += 1
        if first in ('31', '32'):
            hunk['lines'].append([side, 0, body, nums])
        else:
            kind = 'm' + side + ('b' if first.startswith(BOUNDARY_PREFIX) else '')
            hunk['lines'].append([kind, 1 if first in ALTERNATE_CODES else 0, body, nums])
    for f in files:
        for h in f['hunks']:
            del h['_o'], h['_n']
    return files


def pair_moves(files, ws):
    """Link each moved-out line to the moved-in line it became, preferring the longest contiguous block."""
    key = (lambda s: s.strip()) if ws else (lambda s: s)
    seq = {'del': [], 'add': []}
    for fi, f in enumerate(files):
        for h in f['hunks']:
            for ln in h['lines']:
                if ln[0].startswith('m'):
                    side = 'del' if 'del' in ln[0] else 'add'
                    seq[side].append({'f': fi, 'num': ln[3][0] if side == 'del' else ln[3][1],
                                      'key': key(ln[2]), 'ref': ln})
    dels, adds = seq['del'], seq['add']
    by_key = {}
    for idx, a in enumerate(adds):
        by_key.setdefault(a['key'], []).append(idx)

    def contiguous(items, start, offset):
        a, b = items[start], items[start + offset]
        return a['f'] == b['f'] and b['num'] == a['num'] + offset

    used, i = set(), 0
    while i < len(dels):
        best_len, best_c = 0, None
        for c in by_key.get(dels[i]['key'], []):
            n = 0
            while (i + n < len(dels) and c + n < len(adds) and c + n not in used
                   and dels[i + n]['key'] == adds[c + n]['key']
                   and (n == 0 or (contiguous(dels, i, n) and contiguous(adds, c, n)))):
                n += 1
            if n > best_len:
                best_len, best_c = n, c
        if not best_len:
            i += 1
            continue
        for k in range(best_len):
            d, a = dels[i + k], adds[best_c + k]
            used.add(best_c + k)
            d['ref'].append([a['f'], 'n', a['num']])
            a['ref'].append([d['f'], 'o', d['num']])
        i += best_len
    return sum(1 for x in dels + adds if len(x['ref']) < 5)


def stats(files):
    c = {'add': 0, 'del': 0, 'moved': 0}
    for f in files:
        for h in f['hunks']:
            for k, *_ in h['lines']:
                if k in ('add', 'del'):
                    c[k] += 1
                elif k.startswith('m'):
                    c['moved'] += 1
    total = c['add'] + c['del'] + c['moved']
    c['moved_pct'] = round(100 * c['moved'] / total) if total else 0
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('out')
    ap.add_argument('--title')
    ap.add_argument('--ws')
    ap.add_argument('--repo-dir', default='.')
    args = ap.parse_args()

    meta, colored = resolve_target(args.target, args.ws, args.repo_dir)
    files = parse(colored)
    unpaired = pair_moves(files, args.ws)
    s = stats(files)

    title = args.title or f'Moves in {meta["ref"]}'
    data = json.dumps({'meta': meta, 'files': files}).replace('</', '<\\/')
    template = (Path(__file__).parent / 'template.html').read_text()
    page = template.replace('__TITLE__', html.escape(title), 1).replace('__DATA__', data, 1)
    Path(args.out).write_text(page)

    print(json.dumps({'out': str(Path(args.out).resolve()), 'title': title, 'files': len(files),
                      'real_added': s['add'], 'real_removed': s['del'], 'moved': s['moved'],
                      'moved_pct': s['moved_pct'], 'unpaired_moved': unpaired}))


if __name__ == '__main__':
    sys.exit(main())
