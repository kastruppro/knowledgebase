What this repo does: It supplies three agent skills for creating, searching and maintaining local Markdown knowledge bases. Its only executable code is a read-only Python search and reader. I assumed one local user, a few vaults and hundreds to thousands of ordinary notes, without a shared server.

**Must fix**

1. **Quoted archive status lets obsolete notes through** (`skills/knowledgebase-search/scripts/kb.py:L25-L34`)
   - **What this is:** The frontmatter parser reads the status that keeps archived articles out of normal searches and reads.
   - **Problem:** Valid frontmatter `status: "archived" # replaced` becomes `unknown`, because quotes are processed before the trailing comment is removed. A temporary note with that value appeared in default search results and was readable without `--include-archived`.
   - **Fix:** Recognize quoted scalar values with trailing comments, while preserving `#` inside quotes. Add a regression test covering both search and read exclusions.
   - **If we skip it:** Superseded instructions can return as active search results.

2. **Long previews drop nested warnings** (`skills/knowledgebase-search/scripts/kb.py:L273-L286`)
   - **What this is:** The default reader chooses a relevant section and adds prerequisite and warning sections before limiting the output length.
   - **Problem:** A long `## Overview` containing a later `### Common pitfalls` loses that warning when the reader removes contained sections and then truncates the parent. In a temporary note with 10,800 characters before `NEVER DELETE RECOVERY KEYS`, the default preview omitted the warning entirely.
   - **Fix:** Keep safety sections separately when their containing section is shortened, and reserve their space before filling the preview. Add a test with a warning nested beyond the parent's preview limit.
   - **If we skip it:** The advertised warning-preserving preview can show a procedure without its specific safety condition, although the generic partial-document warning still appears.

3. **A list can falsely mark an article as verified** (`skills/knowledgebase-search/scripts/kb.py:L47-L55`)
   - **What this is:** The parser flattens lists for fields such as tags and search triggers, then uses the same parsed values for verification status.
   - **Problem:** Frontmatter containing `status:` followed by `  - verified` becomes the scalar `verified`. A temporary note received the verified ranking bonus, and direct reading would suppress the unverified warning, despite the parser's promise that unsupported compound values never become verified status.
   - **Fix:** Track scalar versus compound values for `status`; accept verification status only from a supported scalar. Test that list and mapping values remain unknown.
   - **If we skip it:** An unsupported metadata value can make an unverified article look trusted.

4. **A malformed config is reported like no matches** (`skills/knowledgebase-search/scripts/kb.py:L300-L307`)
   - **What this is:** Every command loads the user's JSON vault registry before doing its work.
   - **Problem:** A config file containing `[]` raises an uncaught `AttributeError`, prints a traceback and exits 1. The documented contract reserves exit 1 for no matches and exit 2 for errors; invalid path or alias value types can also escape the current error handler.
   - **Fix:** Validate the top-level object and the types of vault paths, descriptions and alias pairs before using them, raising `ValueError` with the offending field. Add malformed-config cases that require exit 2 without a traceback.
   - **If we skip it:** A broken registry can be mistaken for an empty search, and the user gets a Python traceback instead of a useful configuration error.

5. **Two aliases in one query fail together** (`skills/knowledgebase-search/scripts/kb.py:L126-L133`)
   - **What this is:** Configured alias pairs let abbreviations find notes written with the full names.
   - **Problem:** With aliases `k8s/kubernetes` and `aad/entra`, a note containing `Kubernetes Entra` matches `k8s entra` and `kubernetes aad`, but not `k8s aad`. Each variant replaces only one pair in the original query, so the needed combined variant never exists.
   - **Fix:** Also expand distinct aliases together in a single pass over the original query, without re-expanding replacement text. Add the two-alias query as a regression case.
   - **If we skip it:** Normal searches using two configured abbreviations falsely return no matches.

6. **Installing ripgrep changes which notes can be found** (`skills/knowledgebase-search/scripts/kb.py:L96-L110`)
   - **What this is:** File discovery uses optional ripgrep, with a Python fallback when it is absent.
   - **Problem:** Ripgrep skips file links, while the fallback includes them. With `Kubernetes.md` linked to an allowed `Generic.md` containing only `Connect service`, searching the link's filename finds the note only without ripgrep; the existing parity test has no links.
   - **Fix:** Apply one file-link policy in both discovery paths; the smallest fix is to skip file links in the fallback, matching ripgrep. Add this case to the existing parity test.
   - **If we skip it:** Search results depend on whether an optional speed tool is installed, and the fallback can return duplicate copies through links.

**Nice to have**

7. **Delete the cache branch that can never run** (`skills/knowledgebase-search/scripts/kb.py:L207-L216`)
   - **What this is:** Search creates a `normalized` variable and conditionally stores it as a cached document value.
   - **Problem:** The variable is always `None`, so its conditional assignment never runs. A whole-tree search found no other writer of `_normalized`, yet `rank()` still checks that cache.
   - **Fix:** Delete the two dead lines and have `rank()` normalize directly, as it already does on every call.
   - **If we skip it:** Readers must trace a cache that never exists; runtime behavior stays the same.

Verdict: Fix status parsing and warning preservation first. The implementation is small and dependency-free, but its trust and preview guarantees have reproducible gaps.

Lean: -2 lines, -0 dependencies possible.

Validation: All 37 existing tests passed on Python 3.14. Each reported behavioral failure was reproduced using temporary vaults or direct calls against temporary notes; no user vault was accessed. Claude plugin validation passed with warnings about root CLAUDE.md context and a missing listing icon. The three plugin/marketplace manifests, all three skills, every scaffold file, the Python script and its full test suite were read. A text scan found no personal paths under `skills/`.

Not checked: Actual installation or use inside each supported agent, Python 3.9 execution, Obsidian/iCloud behavior and large-vault timing. `npx skills add ./ --list` failed because npm's registry hostname could not resolve. This folder has no `.git` directory, so Git-based checks were unavailable. No implementation files were changed.
