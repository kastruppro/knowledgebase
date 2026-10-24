"""Behavioral regression tests using isolated vaults; no live document mutations."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import date
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'kb.py'
spec=importlib.util.spec_from_file_location('kb',SCRIPT);kb=importlib.util.module_from_spec(spec);spec.loader.exec_module(kb)

class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kb-retrieval-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.ai=self.root/'ai';self.it=self.root/'it'
        self.ai.mkdir();self.it.mkdir()
        self.config=self.root/'vaults.json';self.write_config(self.ai)
        self.env=dict(os.environ,KB_CONFIG=str(self.config),PYTHONDONTWRITEBYTECODE='1')

    def write_config(self,ai):
        self.config.write_text(json.dumps({'vaults':{'ai':{'path':str(ai),'about':'Dev notes'},'it':{'path':str(self.it)}},
            'aliases':[['whfb','windows hello for business'],['azure ad','entra']]}))

    def doc(self,name,body='Needle',status='verified',root=None,extra=''):
        p=(root or self.it)/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(f'---\ntitle: {p.stem}\nstatus: {status}\nlast-verified: 2026-09-07\n{extra}---\n\n# {p.stem}\n\n{body}\n');return p

    def run_kb(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),*args],env=self.env,text=True,capture_output=True)

    def search(self,*args,rc=0):
        p=self.run_kb('search','--json',*args);self.assertEqual(p.returncode,rc,p.stderr)
        return json.loads(p.stdout)

    def test_precise_title_beats_mentions_and_navigation(self):
        self.doc('Retry After.md','Useful instructions')
        self.doc('Other.md','Retry After')
        self.doc('Index.md','Retry After '*1000)
        self.assertEqual(self.search('retry after')['results'][0]['path'],'Retry After.md')

    def test_terms_normalize_punctuation(self):
        self.doc('Retry-After.md','PowerShell returns null')
        self.assertEqual(self.search('powershell retry after null')['total'],1)

    def test_literal_preserves_exact_phrase(self):
        self.doc('Test.md','retry something after literal [ and a.b')
        self.search('--literal','retry after',rc=1)
        self.search('--literal','[')
        self.search('[')

    def test_regex_invalid_is_error(self):
        p=self.run_kb('search','--regex','[')
        self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'')

    def test_regex_and_literal_are_distinct(self):
        self.doc('Test.md','abc')
        self.search('--regex','a.c');self.search('--literal','a.c',rc=1)

    def test_empty_query_is_error(self):
        self.assertEqual(self.run_kb('search','  ').returncode,2)

    def test_no_match_has_exit_one(self):
        self.doc('Test.md');self.search('ABSENT',rc=1)

    def test_error_code_survives_extra_words(self):
        self.doc('Errors.md','0x80180014: mismatch',status='draft')
        r=self.search('autopilot error 80180014')['results'][0]
        self.assertEqual(r['status'],'draft');self.assertIn('80180014',r['excerpt']['text'])

    def test_alias_whfb(self):
        self.doc('Windows Hello for Business.md','Hybrid join')
        self.assertEqual(self.search('whfb hybrid')['total'],1)

    def test_alias_azure_ad(self):
        self.doc('Entra.md','device identity')
        self.assertEqual(self.search('azure ad identity')['total'],1)

    def test_case_unicode(self):
        self.doc('Faldgruber.md','FÆLLES MILJØ')
        self.assertEqual(self.search('fælles miljø')['total'],1)

    def test_scope_only_checks_selected_vault(self):
        self.doc('Topic/Note.md');self.write_config(self.root/'missing')
        self.search('--vault','it','--path','Topic','needle')
        self.assertEqual(self.run_kb('search','needle').returncode,2)

    def test_invalid_scope_is_error(self):
        for path in ['../outside','/tmp','absent','_drafts']:
            self.assertEqual(self.run_kb('search','--vault','it','--path',path,'needle').returncode,2)

    def test_scratch_excluded_even_with_admin_archive_flags(self):
        self.doc('_drafts/secret.md','ONLY_SECRET')
        self.doc('Topic/_drafts/secret.md','ONLY_SECRET')
        self.search('--include-admin','--include-archived','ONLY_SECRET',rc=1)
        self.assertEqual(self.run_kb('read','--vault','it','--include-admin','_drafts/secret.md').returncode,2)

    def test_admin_requires_opt_in(self):
        for name in ['AGENTS.md','CLAUDE.md','_templates/Article.md','_prompts/Bootstrap.md']:
            self.doc(name,'ADMIN_ONLY')
        self.search('ADMIN_ONLY',rc=1)
        self.assertEqual(self.search('--include-admin','ADMIN_ONLY')['total'],4)

    def test_archived_status_and_folder_require_opt_in(self):
        self.doc('90 - Archive/Old.md','ARCHIVE_ONLY')
        self.doc('Old2.md','ARCHIVE_ONLY',status='archived')
        self.search('ARCHIVE_ONLY',rc=1)
        self.assertEqual(self.search('--include-archived','ARCHIVE_ONLY')['total'],2)
        self.assertEqual(self.run_kb('read','--vault','it','Old2.md').returncode,2)

    def test_drafts_visible_and_status_filter(self):
        self.doc('A draft.md','needle',status='draft');self.doc('B verified.md','needle')
        r=self.search('needle');self.assertEqual(r['results'][0]['status'],'verified')
        self.assertEqual(r['total'],2)
        self.assertEqual(self.search('--status','verified','needle')['total'],1)

    def test_pagination_deterministic_and_no_duplicates(self):
        for i in range(12):self.doc(f'Note{i:02}.md')
        a=self.search('needle');b=self.search('--offset','5','needle');c=self.search('--offset','10','needle')
        self.assertEqual([a['returned'],b['returned'],c['returned']],[5,5,2])
        self.assertEqual(len({d['path'] for page in [a,b,c] for d in page['results']}),12)
        self.assertEqual(self.search('--offset','20','needle')['returned'],0)

    def test_symlink_escape_and_scratch_alias_excluded(self):
        outside=self.doc('secret.md','ESCAPE',root=self.root)
        (self.it/'link.md').symlink_to(outside)
        draft=self.doc('_drafts/hidden.md','ESCAPE');(self.it/'alias.md').symlink_to(draft)
        self.search('--include-admin','ESCAPE',rc=1)
        for p in ['link.md','alias.md']:
            self.assertEqual(self.run_kb('read','--vault','it',p).returncode,2)

    def test_frontmatter_lists_quotes_and_folded_summary(self):
        m,_=kb.metadata('---\ntitle: "Colon: title"\ntriggers:\n  - "WHfB issue"\n  - hybrid\nsummary: >-\n  One sentence\n  continued here.\nstatus: draft # needs verification\n---\n')
        self.assertEqual(m['title'],'Colon: title');self.assertEqual(m['status'],'draft')
        self.assertIn('WHfB issue',m['triggers']);self.assertEqual(m['summary'],'One sentence continued here.')

    def test_missing_date_and_status_are_unknown(self):
        (self.it/'Note.md').write_text('# Note\nneedle')
        r=self.search('needle')['results'][0]
        self.assertEqual(r['verified'],'unknown');self.assertEqual(r['status'],'unknown')

    def test_outline_ignores_code_headings(self):
        self.doc('Test.md','## Real\n```bash\n# Fake\n## Also fake\n```\n## Gotchas\nDanger')
        p=self.run_kb('read','--vault','it','Test.md','--outline')
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('Real',p.stdout);self.assertNotIn('Fake',p.stdout)

    def test_small_doc_is_complete_and_carries_warning(self):
        self.doc('Small.md','## Solution\nDo it\n## Gotchas\nCheck first',status='draft')
        p=self.run_kb('read','--vault','it','Small.md')
        self.assertIn('Complete document',p.stdout);self.assertIn('UNVERIFIED',p.stdout);self.assertIn('Check first',p.stdout)

    def test_large_preview_preserves_pitfalls_and_marks_truncation(self):
        self.doc('Large.md','## Overview\n'+'Long text '*2000+'\n## Prerequisites\nNeed permission\n## Gotchas\nDo not remove keys\n## Other\n'+'Other '*1000)
        p=self.run_kb('read','--vault','it','Large.md','--max-chars','2400')
        self.assertIn('Do not remove keys',p.stdout);self.assertIn('Need permission',p.stdout)
        self.assertIn('TRUNCATED',p.stdout);self.assertLess(len(p.stdout),3500)

    def test_section_retrieval_includes_nested_content(self):
        self.doc('Test.md','## Parent\nfirst\n### Child\nsecond\n## Next\nlast')
        p=self.run_kb('read','--vault','it','Test.md','--section','Parent')
        self.assertIn('second',p.stdout);self.assertNotIn('\nlast',p.stdout)

    def test_missing_or_ambiguous_section_is_error(self):
        self.doc('Test.md','## Step One\nfirst\n## Step Two\nsecond')
        for query in ['Step','missing']:
            self.assertEqual(self.run_kb('read','--vault','it','Test.md','--section',query).returncode,2)

    def test_section_pagination_and_explicit_full(self):
        body='## Steps\n'+'abcdefghij'*300
        self.doc('Test.md',body)
        p=self.run_kb('read','--vault','it','Test.md','--section','Steps','--max-chars','200')
        self.assertIn('--offset 200',p.stdout)
        full=self.run_kb('read','--vault','it','Test.md','--full')
        self.assertIn(body,full.stdout);self.assertNotIn('TRUNCATED',full.stdout)

    def test_read_missing_and_parent_escape_are_errors(self):
        for p in ['missing.md','../outside.md','/tmp/outside.md']:
            self.assertEqual(self.run_kb('read','--vault','it',p).returncode,2)

    def test_error_code_excerpt_beats_generic_error_line(self):
        self.doc('Errors.md', 'PowerShell error diagnostics\n0x80180014: mismatch',status='draft')
        result=self.search('autopilot error 80180014')['results'][0]
        self.assertIn('80180014',result['excerpt']['text'])

    def test_filename_is_searchable_when_title_differs(self):
        p=self.doc('Special Finder.md','body')
        p.write_text(p.read_text().replace('title: Special Finder','title: Different'))
        self.assertEqual(self.search('special finder')['total'],1)

    def test_safety_heading_inside_code_is_not_a_section(self):
        self.doc('Large.md','## Overview\n'+('text '*1800)+'\n```bash\n## Fake Gotchas\n```\n## Warnings\nKeep recovery keys')
        p=self.run_kb('read','--vault','it','Large.md','--max-chars','2400')
        self.assertIn('Keep recovery keys',p.stdout)
        self.assertNotIn(': Fake Gotchas',p.stdout)

    def test_unnumbered_archive_folder_requires_opt_in(self):
        self.doc('Archive/Old.md','ARCHIVE_ONLY');self.search('ARCHIVE_ONLY',rc=1)
        self.search('--include-archived','ARCHIVE_ONLY')

    def test_missing_config_and_unknown_vault_are_errors(self):
        self.assertEqual(self.run_kb('search','--vault','nope','needle').returncode,2)
        self.config.unlink();p=self.run_kb('vaults')
        self.assertEqual(p.returncode,2);self.assertIn('No vaults configured',p.stderr)

    def test_vaults_lists_names_descriptions_and_missing(self):
        self.write_config(self.root/'missing');p=self.run_kb('vaults')
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('Dev notes',p.stdout);self.assertIn('[MISSING]',p.stdout)

    def test_folder_names_count_as_search_terms(self):
        self.doc('Networking/DNS.md','resolver order')
        self.assertEqual(self.search('networking dns')['total'],1)

    def test_regex_matches_path(self):
        self.doc('Networking/DNS.md','body');self.search('--regex','network.*dns')

    def test_status_archived_finds_archived_notes(self):
        self.doc('90 - Archive/Old.md','needle');self.doc('Old2.md','needle',status='archived')
        self.assertEqual(self.search('--status','archived','needle')['total'],2)

    def test_quoted_status_with_comment(self):
        self.doc('Old.md','ONLY_OLD',status='"archived" # replaced')
        self.doc('Good.md','ONLY_GOOD',status="'verified' # checked")
        self.search('ONLY_OLD',rc=1)
        self.assertEqual(self.run_kb('read','--vault','it','Old.md').returncode,2)
        self.assertEqual(self.search('ONLY_GOOD')['results'][0]['status'],'verified')
        self.assertEqual(kb.scalar('"a # b" # c'),'a # b')

    def test_list_or_mapping_status_is_unknown(self):
        for body in ('status:\n  - verified\n','status:\n  value: verified\n'):
            m,_=kb.metadata('---\ntitle: T\n'+body+'---\n')
            self.assertEqual(m['status'],'')

    def test_frontmatter_delimiters_with_trailing_space(self):
        m,start=kb.metadata('--- \nstatus: verified\n---  \n# T\n')
        self.assertEqual(m['status'],'verified');self.assertEqual(start,3)

    def test_heading_ending_in_hash_keeps_it(self):
        self.assertEqual([h['title'] for h in kb.headings(['## C#','## Title ##','## F# notes'])],['C#','Title','F# notes'])

    def test_two_aliases_in_one_query(self):
        self.config.write_text(json.dumps({'vaults':{'it':{'path':str(self.it)}},'aliases':[['k8s','kubernetes'],['aad','entra']]}))
        self.doc('Note.md','Kubernetes Entra')
        for q in ('k8s aad','k8s entra','kubernetes aad'):self.assertEqual(self.search(q)['total'],1,q)

    def test_malformed_config_is_error_without_traceback(self):
        for config in ('[]','{"vaults":{"it":{"path":5}}}','{"vaults":{"it":{"path":"x"}},"aliases":null}',
                       '{"vaults":{"it":{"path":"x"}},"aliases":[["k8s"]]}','{"vaults":{"it":{"path":"x"}},"aliases":{}}'):
            self.config.write_text(config);p=self.run_kb('search','needle')
            if config.endswith('null}'):
                self.assertEqual(p.returncode,2,config);self.assertIn('Vault unavailable',p.stderr)
            else:
                self.assertEqual(p.returncode,2,config);self.assertIn('KB error',p.stderr)
            self.assertNotIn('Traceback',p.stderr)

    def test_file_symlinks_skipped(self):
        self.doc('Generic.md','Connect service');(self.it/'Kubernetes.md').symlink_to(self.it/'Generic.md')
        self.assertEqual([p.name for p in kb.discover(self.it)],['Generic.md'])

    def test_unreadable_folder_is_error_not_no_matches(self):
        locked=self.it/'Locked';locked.mkdir();locked.chmod(0);self.addCleanup(locked.chmod,0o755)
        with self.assertRaises(OSError):kb.discover(self.it)

    def test_read_query_picks_section_and_keeps_pitfalls(self):
        self.doc('Long.md','## Install\n'+'setup text '*400+'\n## Rollback\nrestore the snapshot\n## Common pitfalls\nKeep backups\n## Other\n'+'x '*2000)
        p=self.run_kb('read','--vault','it','Long.md','--query','rollback snapshot','--max-chars','2000')
        self.assertIn('restore the snapshot',p.stdout);self.assertIn('Keep backups',p.stdout);self.assertNotIn('setup text',p.stdout)

    def test_nested_pitfall_in_long_parent_survives_preview(self):
        self.doc('Big.md','## Overview\n'+'text '*2200+'\n### Common pitfalls\nNEVER DELETE RECOVERY KEYS\n## End\nbye')
        p=self.run_kb('read','--vault','it','Big.md','--max-chars','2400')
        self.assertIn('NEVER DELETE RECOVERY KEYS',p.stdout);self.assertEqual(p.stdout.count('NEVER DELETE'),1)

    def check(self,rc):
        p=self.run_kb('check','--vault','it');self.assertEqual(p.returncode,rc,p.stdout+p.stderr);return p.stdout

    def test_check_clean_vault(self):
        self.doc('Index.md','[[Note]] [[Topic/Index|Topic]]');self.doc('Note.md','![[pic.png]] [[#Heading]]')
        self.doc('Topic/Index.md');self.doc('Topic/Deep.md','[[Topic/Deep]] [[Deep#Part|alias]]')
        (self.it/'pic.png').write_bytes(b'');self.doc('_templates/T.md','[[{{title}}]]');self.doc('00 - Inbox/Raw.md','x')
        self.assertIn('No problems found',self.check(0))

    def test_check_reports_metadata_problems(self):
        (self.it/'Bare.md').write_text('# Bare\n')
        self.doc('Odd.md',status='maybe');self.doc('NoDate.md',extra='')
        p=self.it/'NoDate.md';p.write_text(p.read_text().replace('last-verified: 2026-09-07\n',''))
        self.doc('BadDate.md',extra='verified-against: x\n')
        p=self.it/'BadDate.md';p.write_text(p.read_text().replace('2026-09-07','2026-13-45'))
        out=self.check(1)
        for expected in ('Bare.md: no frontmatter','Odd.md: status missing','NoDate.md: status verified without','BadDate.md: last-verified "2026-13-45"'):
            self.assertIn(expected,out)

    def test_check_reports_links_index_and_old_drafts(self):
        self.doc('Note.md','[[Missing Note]] `[[In Code]]`\n```\n[[Fenced]]\n```',extra='triggers:\n  - "[[In Frontmatter]]"\n')
        self.doc('Section/Article.md');(self.it/'_drafts/2000-01-01-old').mkdir(parents=True)
        (self.it/'_drafts'/(date.today().isoformat()+'-new')).mkdir()
        out=self.check(1)
        self.assertIn('broken link [[Missing Note]]',out);self.assertNotIn('In Code',out);self.assertNotIn('Fenced',out);self.assertNotIn('In Frontmatter',out)
        self.assertIn('Section/: section folder without Index.md',out)
        self.assertIn('2000-01-01-old: draft is',out);self.assertNotIn('-new',out)

    def test_edit_reflected_without_index_rebuild(self):
        p=self.doc('Test.md','ORIGINAL');self.search('ORIGINAL')
        p.write_text(p.read_text().replace('ORIGINAL','REVISED'))
        self.search('ORIGINAL',rc=1);self.search('REVISED')

if __name__=='__main__':unittest.main()
