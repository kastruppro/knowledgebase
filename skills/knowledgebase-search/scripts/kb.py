#!/usr/bin/env python3
"""Local, bounded Markdown retrieval. Python 3.9+, standard library only."""
import argparse
from datetime import date
import itertools
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

CONFIG = Path(os.environ.get('KB_CONFIG') or Path.home() / '.config/knowledgebase/vaults.json')
EXCLUDED = {'_drafts', '_templates', '_prompts'}
GUIDANCE = {'AGENTS.md', 'CLAUDE.md'}
ARCHIVE = re.compile(r'(\d+\s*-\s*)?archive', re.I)  # "Archive", "90 - Archive"
ROOTS, ABOUT, ALIASES = {}, {}, []
WIKILINK = re.compile(r'!?\[\[([^\]|#^]*)[^\]]*\]\]')
# shortcut: a fence closes on the same marker only, good enough to skip example links in code.
CODE = re.compile(r'^\s{0,3}(`{3,}|~{3,}).*?^\s{0,3}\1|`[^`\n]*`', re.M | re.S)
INBOX = re.compile(r'(\d+\s*-\s*)?inbox', re.I)
SAFETY = re.compile(r'gotchas|pitfalls|prerequisites?|warnings?|forudsæt|faldgrub|sikkerhed|security|requirements?|important|caution|caveats?|advarsel|vigtigt|forbehold|limitations?|begræns|before you|environment', re.I)


def normalize(s):
    return ' '.join(re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', s).casefold()))


def scalar(s):
    s = s.strip()
    if s in ('', '~', 'null', 'Null', 'NULL'):
        return ''
    # A quoted value may be followed by a comment; '#' inside the quotes is kept.
    m = re.fullmatch(r'("(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\')\s*(?:#.*)?', s)
    if m:
        q = m.group(1)
        if q[0] == '"':
            try: return json.loads(q)
            except ValueError: pass
        return q[1:-1].replace("''", "'")
    return re.split(r'\s+#', s, maxsplit=1)[0].strip()


def metadata(text):
    """Read the vault's flat scalar/list schema; no YAML execution or dependency.

    Unsupported compound YAML is kept as text, never treated as verified status.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip('\ufeff').strip() != '---': return {}, 0
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == '---'), None)
    if end is None: return {}, 0
    fields = {}; key = None; compound = set()
    for line in lines[1:end]:
        m = re.match(r'^([\w-]+):(?:\s+(.*))?$', line)
        if m:
            key, value = m.group(1), m.group(2) or ''
            fields[key] = scalar(value)
        elif key and re.match(r'^\s+\S', line):
            if re.match(r'^\s*(-\s|-$|[\w-]+:)', line): compound.add(key)
            value = re.sub(r'^\s*-\s*', '', line).strip()
            if fields[key] in ('>', '>-', '|', '|-'): fields[key] = ''
            fields[key] = (fields[key] + ' ' + scalar(value)).strip()
    if 'status' in compound: fields['status'] = ''  # only a plain scalar can mark an article verified
    return fields, end + 1


def headings(lines, start=0):
    out = []; fence = None
    for i in range(start, len(lines)):
        line = lines[i]
        m = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if m:
            mark = m.group(1)
            if fence is None: fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence): fence = None
            continue
        if fence: continue
        m = re.match(r'^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$', line)
        if m: out.append({'start': i, 'level': len(m.group(1)), 'title': m.group(2)})
    for pos, h in enumerate(out):
        h['end'] = next((x['start'] for x in out[pos+1:] if x['level'] <= h['level']), len(lines))
    return out


def allowed(path, root, archive=False, admin=False):
    relative = path.relative_to(root)
    # Check lexical AND resolved paths: a symlink must not expose scratch or another vault.
    resolved = path.resolve()
    try: resolved_relative = resolved.relative_to(root.resolve())
    except ValueError: return False
    for parts in (relative.parts, resolved_relative.parts):
        if '_drafts' in parts or any(p.startswith('.') for p in parts): return False
        if not admin and (any(p in EXCLUDED for p in parts) or parts[-1] in GUIDANCE): return False
        if not archive and any(ARCHIVE.fullmatch(x) for x in parts[:-1]): return False
    return True


def discover(root, scope='', archive=False, admin=False):
    if not root.is_dir(): raise ValueError('Vault unavailable: ' + str(root))
    if Path(scope).is_absolute() or '..' in Path(scope).parts: raise ValueError('--path must stay inside the selected vault')
    target = root / scope
    if not target.is_dir(): raise ValueError('Search folder unavailable: ' + str(target))
    if not allowed(target / '__scope__.md', root, archive, admin): raise ValueError('Search folder is excluded')
    paths = []
    def fail(e): raise e
    for current, dirs, files in os.walk(target, onerror=fail):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d != '_drafts' and
                         (admin or d not in EXCLUDED) and (archive or not ARCHIVE.fullmatch(d)))
        # File symlinks are skipped: they would show the same note twice.
        paths.extend(Path(current) / f for f in files if f.endswith('.md') and not os.path.islink(os.path.join(current, f)))
    return sorted((p for p in paths if allowed(p, root, archive, admin)), key=lambda p: str(p).casefold())


def document(path, root, vault, text=None):
    if text is None: text = path.read_text(encoding='utf-8-sig')
    meta, start = metadata(text); lines = text.splitlines()
    hs = headings(lines, start)
    title = meta.get('title') or next((h['title'] for h in hs if h['level'] == 1), path.stem)
    status = meta.get('status', '').casefold()
    if status not in ('verified', 'draft', 'archived'): status = 'unknown'
    if any(ARCHIVE.fullmatch(x) for x in path.relative_to(root).parts[:-1]): status = 'archived'
    return dict(vault=vault, path=str(path.relative_to(root)), title=title, status=status,
                verified=meta.get('last-verified') or meta.get('verified') or 'unknown',
                against=meta.get('verified-against') or 'unspecified', meta=meta, text=text,
                lines=lines, headings=hs, body_start=start)


def variants(query):
    q = normalize(query); swaps = {}
    for a, b in ALIASES:
        swaps.setdefault(a, []).append(b); swaps.setdefault(b, []).append(a)
    if not swaps: return [q]
    # One split of the original query: every alias hit may stay or swap, and replacements
    # are never re-expanded. shortcut: 2^hits variants, fine for short queries.
    pattern = r'(?<!\w)(' + '|'.join(map(re.escape, sorted(swaps, key=len, reverse=True))) + r')(?!\w)'
    parts = re.split(pattern, q)
    options = [[x] if i % 2 == 0 else [x, *swaps[x]] for i, x in enumerate(parts)]
    return list(dict.fromkeys(''.join(c) for c in itertools.product(*options)))


def rank(doc, query, mode):
    text = doc['text'] + ' ' + doc['path']; norm = normalize(text)
    fields = [(normalize(doc['title'] + ' ' + Path(doc['path']).stem), 8),
              (normalize(doc['meta'].get('triggers','') + ' ' + doc['meta'].get('aliases','')), 7),
              (normalize(' '.join(h['title'] for h in doc['headings'])), 4),
              (normalize(doc['meta'].get('summary','')), 3),
              (normalize(doc['meta'].get('tags','') + ' ' + doc['meta'].get('stack','') + ' ' + doc['path']), 1)]
    if mode == 'regex':
        match = re.search(query, text, re.I)
        if not match: return None
        return 100 + sum(w * 10 for field, w in fields if re.search(query, field, re.I))
    if mode == 'literal':
        if query.casefold() not in text.casefold() and query.casefold() not in doc['path'].casefold(): return None
        return 100 + sum(w * 10 for field, w in fields if normalize(query) in field)
    scores = []
    for q in variants(query):
        terms = list(dict.fromkeys(q.split()))
        if not terms:
            return rank(doc, query, 'literal')
        # Error-code fallback may recover a document without all surrounding words.
        codes = [t for t in terms if re.fullmatch(r'(?:0x)?[a-f0-9]{6,}', t) and re.search(r'\d',t)]
        all_terms = all(t in norm for t in terms)
        code_hit = bool(codes) and all(c.removeprefix('0x') in norm for c in codes)
        if not all_terms and not code_hit: continue
        score = 100 if all_terms else 70
        for field, weight in fields:
            score += weight * sum(8 for term in terms if term in field)
            if q in field: score += weight * 15
        if code_hit: score += 100
        scores.append(score)
    if not scores: return None
    # Status breaks close ties; exact technical matches still beat incidental verified mentions.
    score = max(scores) + (8 if doc['status'] == 'verified' else 0)
    if Path(doc['path']).name in ('Index.md', 'README.md') or 'type/moc' in doc['meta'].get('tags',''): score *= .35
    return round(score, 2)


def excerpt(doc, query, mode, width=220):
    terms = normalize(query).split()
    candidates = []
    for n, line in enumerate(doc['lines'][doc['body_start']:], doc['body_start'] + 1):
        if not line.strip() or line.startswith(('#', '```', '~~~')): continue
        value = normalize(line)
        score = sum((40 if re.fullmatch(r'(?:0x)?[a-f0-9]{6,}', t) and re.search(r'\d',t) else 1) for t in terms if t in value)
        if mode == 'regex': score = bool(re.search(query, line, re.I)) * 10
        elif mode == 'literal': score = (query.casefold() in line.casefold()) * 10
        if score: candidates.append((score, n, line.strip()))
    if not candidates: return dict(line=None, text=doc['meta'].get('summary', '')[:width] or 'Title or metadata match; inspect the document.')
    _, n, line = max(candidates, key=lambda x:(x[0], -x[1]))
    if len(line) > width:
        positions = [line.casefold().find(t) for t in terms if t in line.casefold()]
        pos = max(0, min(positions, default=0) - 50)
        line = ('…' if pos else '') + line[pos:pos+width-2] + '…'
    return dict(line=n, text=line)


def search(args):
    if args.path and args.vault == 'all': raise ValueError('--path requires a single --vault')
    query = ' '.join(args.query).strip()
    if not query: raise ValueError('A non-empty search query is required')
    mode = 'regex' if args.regex else 'literal' if args.literal else 'terms'
    if mode == 'regex': re.compile(query, re.I)
    vaults = list(ROOTS) if args.vault == 'all' else [vault_name(args.vault)]
    archived = args.include_archived or args.status == 'archived'
    results = []
    query_variants = variants(query)
    term_groups = [list(dict.fromkeys(q.split())) for q in query_variants]
    codes = [t.removeprefix('0x') for ts in term_groups for t in ts if re.fullmatch(r'(?:0x)?[a-f0-9]{6,}',t) and re.search(r'\d',t)]
    for vault in vaults:
        root = ROOTS[vault]
        for path in discover(root, args.path, archived, args.include_admin):
            text = path.read_text(encoding='utf-8-sig'); rel = str(path.relative_to(root))
            # Cheap rejection before parsing headings and metadata; folder and file names count.
            if mode == 'terms' and any(term_groups):
                candidate = unicodedata.normalize('NFKC', text + ' ' + rel).casefold()
                if not any(all(t in candidate for t in ts) for ts in term_groups) and not (codes and all(c in candidate for c in codes)):
                    continue
            elif mode == 'literal' and query.casefold() not in (text + ' ' + rel).casefold(): continue
            elif mode == 'regex' and not re.search(query, text + ' ' + rel, re.I): continue
            doc = document(path, root, vault, text)
            if doc['status'] == 'archived' and not archived: continue
            if args.status != 'all' and doc['status'] != args.status: continue
            score = rank(doc, query, mode)
            if score is None: continue
            results.append({k:doc[k] for k in ('vault','path','title','status','verified','against')} |
                           dict(score=score, excerpt=excerpt(doc, query, mode)))
    results.sort(key=lambda d:(-d['score'], d['vault'], d['path'].casefold()))
    page = results[args.offset:args.offset+args.limit]
    payload = dict(query=query, mode=mode, vaults=vaults, total=len(results), offset=args.offset,
                   returned=len(page), more=args.offset+len(page)<len(results), results=page)
    if args.json: print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"{len(page)}/{len(results)} matches | vault={args.vault} | mode={mode} | offset={args.offset}")
        for i, d in enumerate(page, args.offset+1):
            print(f"{i}. [{d['vault']}] {d['path']}\n   {d['title']} | {d['status'].upper()} | verified={d['verified']}")
            print(f"   L{d['excerpt']['line'] or '?'}: {d['excerpt']['text']}")
        if payload['more']: print(f"More results: --offset {args.offset+len(page)}")
        if not page and results: print('Page is empty; earlier matching results exist.')
    return 0 if results else 1


def read_doc(args):
    root = ROOTS[vault_name(args.vault)]; relative = Path(args.file)
    if relative.is_absolute() or '..' in relative.parts: raise ValueError('Document must be a vault-relative path')
    p = root / relative
    if not allowed(p, root, args.include_archived, args.include_admin): raise ValueError('Document is excluded or outside vault')
    if p.suffix != '.md': raise ValueError('Only Markdown documents can be read')
    doc = document(p, root, args.vault)
    if doc['status'] == 'archived' and not args.include_archived: raise ValueError('Archived document requires --include-archived')
    print(f"[{args.vault}] {doc['path']} | {doc['status'].upper()} | verified={doc['verified']}")
    print('Against: ' + doc['against'])
    print('Title: ' + doc['title'])
    if doc['status'] != 'verified': print('UNVERIFIED material: use as a lead; verify claims before relying on them.')
    if args.full:
        print(doc['text']); return 0
    hs = [h for h in doc['headings'] if h['level'] > 1]
    if args.outline:
        output = '\n'.join(f"L{h['start']+1}-{h['end']}: {'  '*(h['level']-2)}{h['title']}" for h in hs)
    elif args.section:
        exact = [h for h in hs if normalize(args.section) == normalize(h['title'])]
        matches = exact or [h for h in hs if normalize(args.section) in normalize(h['title'])]
        if len(matches) != 1: raise ValueError('Section missing or ambiguous; use --outline and the exact heading')
        h = matches[0]
        output = f"L{h['start']+1}-{h['end']}\n" + '\n'.join(doc['lines'][h['start']:h['end']])
        print('Selected section only; check prerequisites and pitfalls with the default preview / --outline.')
    elif len(doc['text']) <= args.max_chars and args.offset == 0:
        print('Complete document:'); print(doc['text']); return 0
    else:
        if args.query:
            terms = normalize(args.query).split()
            def score(h):
                title=normalize(h['title']); body=normalize('\n'.join(doc['lines'][h['start']:h['end']]))
                return (sum(10 for t in terms if t in title) + sum(1 for t in terms if t in body), -(h['end']-h['start']))
            chosen = max(hs, key=score) if hs else None
        else:
            chosen = next((h for h in hs if normalize(h['title']) in ('tl dr','summary','overview','decision summary')), hs[0] if hs else None)
        selected = ([chosen] if chosen else []) + [h for h in hs if SAFETY.search(h['title']) and h != chosen]
        # A section stops where a nested selected one starts: no text twice, and a pitfall
        # deep inside a long parent gets its own space instead of being truncated away.
        selected = [dict(h, end=min([h['end']] + [x['start'] for x in selected if h['start'] < x['start'] < h['end']]))
                    for h in selected]
        if not selected: selected = [dict(start=doc['body_start'],end=len(doc['lines']),title='Body')]
        print('PARTIAL document preview; omitted sections may contain requirements. Use --outline / --section / --full before applying incomplete procedures.')
        # Reserve space for every selected section instead of letting the first large one hide pitfalls.
        per_section = max(160, (args.max_chars - 300) // len(selected))
        blocks = []
        if doc['meta'].get('summary'): blocks.append('Summary: ' + doc['meta']['summary'])
        for h in selected:
            body = '\n'.join(doc['lines'][h['start']:h['end']])
            block = f"L{h['start']+1}-{h['end']}: {h['title']}\n"
            if len(body) > per_section:
                body = body[:per_section] + '\n[SECTION TRUNCATED: use --section with this exact heading; do not execute partial code.]'
            blocks.append(block+body)
        output = '\n\n'.join(blocks)
    page = output[args.offset:args.offset+args.max_chars]
    print(page)
    if args.offset + len(page) < len(output): print(f"[OUTPUT TRUNCATED; continue with the same options and --offset {args.offset+len(page)}. Do not execute partial code.]")
    return 0


def check(args):
    """Report vault problems; changes nothing. Exit 0 clean, 1 problems found."""
    vaults = list(ROOTS) if args.vault == 'all' else [vault_name(args.vault)]
    problems = []
    for vault in vaults:
        root = ROOTS[vault]; found = lambda rel, why: problems.append(f'[{vault}] {rel}: {why}')
        if not root.is_dir(): raise ValueError('Vault unavailable: ' + str(root))
        # Every file (attachments, archive and templates too) can be a link target.
        names, paths = set(), []
        for current, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
            rel_dir = Path(current).relative_to(root)
            if rel_dir.parts and not any(p.startswith('_') or ARCHIVE.fullmatch(p) or INBOX.fullmatch(p) for p in rel_dir.parts) \
                    and 'Index.md' not in files:
                found(rel_dir.as_posix() + '/', 'section folder without Index.md')
            for f in files:
                rel = (rel_dir / f).as_posix().casefold()
                names.update((f.casefold(), f.casefold().removesuffix('.md'))); paths += [rel, rel.removesuffix('.md')]
        for path in discover(root):
            doc = document(path, root, vault); rel = Path(doc['path']).as_posix()
            if path.name not in ('Index.md', 'README.md'):  # navigation pages need no verification metadata
                if not doc['meta']: found(rel, 'no frontmatter')
                elif doc['status'] == 'unknown': found(rel, 'status missing or not verified/draft/archived')
                elif doc['status'] == 'verified' and doc['verified'] == 'unknown': found(rel, 'status verified without a last-verified date')
            day = doc['meta'].get('last-verified') or doc['meta'].get('verified')
            if day:
                try: date.fromisoformat(day)
                except ValueError: found(rel, f'last-verified "{day}" is not a YYYY-MM-DD date')
            # Body only: frontmatter triggers are search text and may contain [[...]] syntax.
            for target in WIKILINK.findall(CODE.sub('', '\n'.join(doc['lines'][doc['body_start']:]))):
                t = target.strip().casefold()
                # Obsidian resolves a bare name anywhere, and a path by its end.
                if t and t not in names and not any(x == t or x.endswith('/' + t) for x in paths):
                    found(rel, f'broken link [[{target.strip()}]]')
        drafts = root / '_drafts'
        for d in sorted(drafts.iterdir()) if drafts.is_dir() else []:
            if d.name.startswith('.'): continue
            try: made = date.fromisoformat(d.name[:10])
            except ValueError: made = date.fromtimestamp(d.stat().st_mtime)
            if (date.today() - made).days > 30:
                found('_drafts/' + d.name, f'draft is {(date.today() - made).days} days old; review it with the user')
    print('\n'.join(problems) or 'No problems found.')
    if problems: print(f'{len(problems)} problems. Nothing was changed.')
    return 1 if problems else 0


def load_config():
    """Fill ROOTS/ABOUT/ALIASES from the user's vaults.json (see knowledgebase-setup)."""
    if not CONFIG.is_file():
        raise ValueError(f'No vaults configured. Create {CONFIG} like '
                         '{"vaults": {"notes": {"path": "/path/to/vault", "about": "what it covers"}}}')
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    vaults = config.get('vaults') if isinstance(config, dict) else None
    if not isinstance(vaults, dict) or not vaults: raise ValueError(f'{CONFIG} has no "vaults" object')
    for name, v in vaults.items():
        if name == 'all' or not isinstance(v, dict) or not isinstance(v.get('path'), str) or not v['path'] \
                or not isinstance(v.get('about', ''), str):
            raise ValueError(f'Vault "{name}" in {CONFIG} needs a text "path" and optional text "about" ("all" is reserved)')
        ROOTS[name] = Path(v['path']).expanduser(); ABOUT[name] = v.get('about', '')
    aliases = config.get('aliases') or []
    if not isinstance(aliases, list): raise ValueError(f'"aliases" in {CONFIG} must be a list of pairs')
    for pair in aliases:
        if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) and normalize(x) for x in pair)):
            raise ValueError(f'Alias {json.dumps(pair)} in {CONFIG} must be a pair of words, e.g. ["k8s", "kubernetes"]')
    ALIASES[:] = [tuple(normalize(x) for x in pair) for pair in aliases]


def vault_name(name):
    if name not in ROOTS: raise ValueError(f'Unknown vault "{name}"; configured: {", ".join(ROOTS)}')
    return name


def list_vaults(args):
    for name, root in ROOTS.items():
        state = '' if root.is_dir() else ' [MISSING]'
        print(f'{name}: {root}{state}\n   {ABOUT[name] or "(no description)"}')
    return 0


def positive(value):
    n=int(value)
    if n<1: raise argparse.ArgumentTypeError('Must be positive')
    return n


def nonnegative(value):
    n=int(value)
    if n<0: raise argparse.ArgumentTypeError('Must be nonnegative')
    return n


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('vaults',help='List configured vaults and what each covers')
    c=commands.add_parser('check',help='Report missing metadata, broken links, missing Index.md, old drafts')
    c.add_argument('--vault',default='all',help='Vault name from the config, or all')
    s=commands.add_parser('search',help='Ranked bounded search; separate terms by default')
    s.add_argument('--vault',default='all',help='Vault name from the config, or all')
    s.add_argument('--path',default='',help='Vault-relative folder; combine with one --vault')
    s.add_argument('--limit',type=positive,default=5); s.add_argument('--offset',type=nonnegative,default=0)
    s.add_argument('--status',choices=['all','verified','draft','unknown','archived'],default='all')
    modes=s.add_mutually_exclusive_group();modes.add_argument('--literal',action='store_true');modes.add_argument('--regex',action='store_true')
    s.add_argument('--json',action='store_true');s.add_argument('query',nargs='+')
    r=commands.add_parser('read',help='Metadata, relevant section and prerequisites/pitfalls')
    r.add_argument('--vault',required=True);r.add_argument('file')
    r.add_argument('--query',default='');r.add_argument('--offset',type=nonnegative,default=0);r.add_argument('--max-chars',type=positive,default=6000)
    modes=r.add_mutually_exclusive_group();modes.add_argument('--outline',action='store_true');modes.add_argument('--section');modes.add_argument('--full',action='store_true')
    for p in (s,r):
        p.add_argument('--include-archived',action='store_true');p.add_argument('--include-admin',action='store_true')
    args=parser.parse_args()
    try:
        load_config()
        return {'vaults':list_vaults,'search':search,'read':read_doc,'check':check}[args.command](args)
    except (OSError,ValueError,re.error) as e:
        print('KB error: '+str(e),file=sys.stderr);return 2

if __name__=='__main__': sys.exit(main())
