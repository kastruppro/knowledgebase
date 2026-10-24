---
name: knowledgebase-search
description: >-
  Search and read the user's own local Markdown knowledge bases (Obsidian vaults) before
  answering a question they are likely to cover, and return concise evidence with its
  verification status. Use when the user asks a technical or domain question their notes may
  answer, or says "check my knowledge base", "search my notes", "what does my KB say about",
  "søg i min vidensbase", "slå op i mine noter", or quotes an error code. Ranked search with
  status and date, bounded section reads that keep prerequisites and pitfalls, drafts and
  archive excluded or flagged. Needs Python 3.9+; vaults are listed in
  ~/.config/knowledgebase/vaults.json.
license: MIT
---

# Search your knowledge base

Set `SKILL_DIR` to the absolute directory of this loaded skill. All commands run
`python3 "$SKILL_DIR/scripts/kb.py"`. The script never changes a file.

## Step 1 - Pick the vault

```bash
python3 "$SKILL_DIR/scripts/kb.py" vaults
```

Lists each configured vault with what it covers. Search the vault whose description fits the
question, or all of them (the default) for cross-cutting questions. If it says "No vaults
configured", use the **knowledgebase-setup** skill (or create the config it describes).

## Step 2 - Search, then read

```bash
python3 "$SKILL_DIR/scripts/kb.py" search --vault <name> "<keywords or error code>"
python3 "$SKILL_DIR/scripts/kb.py" read --vault <name> "<returned relative path>" --query "<keywords>"
```

- Search returns five ranked hits with status, date and a line-numbered excerpt. Words may
  occur separately; punctuation is normalized; error codes match even with extra words.
  `--path "<folder>"` narrows to a folder of one vault, `--literal` matches an exact phrase,
  `--regex` a pattern, `--offset 5` pages on, `--json` for programmatic use.
- Exit **0** = matches, **1** = no matches, **2** = error. Exit 1 is never proof that the
  knowledge base has no answer: widen the folder or vault or simplify the query first.
- The reader returns a small document whole, or a bounded preview of the relevant section
  plus every prerequisite, warning and pitfall section. For more: `--outline`, then
  `--section "Exact heading"`, then `--offset` if truncated. `--full` is explicit and
  unbounded. Never apply partial code or procedures without reading their prerequisites and
  warnings.

## Step 3 - Judge the evidence

- `status: verified` with a recent `last-verified` and a matching `verified-against`
  (product/version) is strong evidence, not a guarantee. `draft` and `unknown` are leads to
  verify against official documentation before relying on them.
- Say which document an answer came from (vault and path) and its status.
- Reading a document does not reverify it. Do not change status or dates while searching.

## Excluded by default

- `_drafts/` is always excluded (session scratch), also through symlinks.
- `Archive` / `NN - Archive` folders and `status: archived` need `--include-archived` (or
  `--status archived` to search only those). Notes in an archive folder count as archived.
- `AGENTS.md`, `CLAUDE.md`, `_templates/` and `_prompts/` need `--include-admin`.

## Vault health

```bash
python3 "$SKILL_DIR/scripts/kb.py" check --vault <name>
```

Reports articles without frontmatter or a valid status, `verified` without a valid
`last-verified` date, broken `[[wiki-links]]`, section folders without `Index.md` and drafts
older than 30 days. Exit 0 = clean, 1 = problems, 2 = error. It changes nothing.

## Config

`~/.config/knowledgebase/vaults.json` (override with the `KB_CONFIG` environment variable):

```json
{
  "vaults": {
    "notes": {"path": "~/Documents/Obsidian/Notes", "about": "What this vault covers"}
  },
  "aliases": [["k8s", "kubernetes"]]
}
```

`aliases` is optional: each pair makes a search for one term also find the other.

To add or correct knowledge, use the **knowledgebase-write** skill.
