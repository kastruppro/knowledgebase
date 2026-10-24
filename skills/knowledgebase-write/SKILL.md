---
name: knowledgebase-write
description: >-
  Add, correct and maintain articles in the user's own local Markdown knowledge base
  (Obsidian vault) without losing verification evidence. Use when the user says "add this to
  my knowledge base", "write this down in the KB", "document what we just found", "update the
  KB article", "tilføj til vidensbasen", "skriv det ind i KB'en", "promote the draft", or when
  a knowledge base article turned out wrong during the task. Verified findings become full
  articles; unverified observations become dated drafts in _drafts/; superseded articles go to
  the archive. Follows the vault's own AGENTS.md and writing guide.
license: MIT
---

# Write to your knowledge base

Write only when the user asked for it, or when fixing a knowledge base article is clearly part
of the task. Never touch `.obsidian/`.

## Step 1 - Find the vault and its rules

1. Vaults are listed in `~/.config/knowledgebase/vaults.json` (or the file in `KB_CONFIG`):
   `{"vaults": {"<name>": {"path": "...", "about": "..."}}}`. Pick the vault whose `about`
   fits the content. If there is no config, use the **knowledgebase-setup** skill.
2. Read the vault's `AGENTS.md` once (or `CLAUDE.md` if there is no AGENTS.md), then the
   writing guide it links (usually `_templates/Writing Guide.md`). The vault's own rules win
   over this skill: frontmatter, folders, language, link style and what must stay out.
3. If the vault is a git repository (`git -C "<vault>" rev-parse --git-dir` succeeds), note
   `git status --short` before you write, so you commit only your own changes later.
4. Before writing a new article, search for an existing one (the **knowledgebase-search**
   skill, or grep the vault). Extend or correct it rather than creating a duplicate.

## Step 2 - Decide what kind of write it is

| What you have | Where it goes |
|---------------|---------------|
| Verified this session against an official source, and reusable | A full article in the right section folder, from the matching `_templates/` template, `status: verified`, `last-verified: <today>`, `verified-against: <product/version or source>` |
| Observed but not verified, or still in progress | A draft: `_drafts/<YYYY-MM-DD>-<topic-slug>/notes.md` (format below) |
| Speculation | Nothing. Do not record guesses as facts. |
| Specific to one customer, client, person or project | Not in a general knowledge base. Keep only the reusable pattern; the specifics belong wherever the vault's rules say. |

Draft file:

```markdown
# UNVERIFIED draft - observed, not yet verified against an external source

<free-form notes; no frontmatter needed in _drafts/>

## Resolve before the session ends
- [ ] verified + reusable -> promote to a full article (vault template)
- [ ] project-specific -> move to that project's own notes
- [ ] wrong / speculation -> delete
```

## Step 3 - Write

- New article: copy the matching template, fill every section, add a one-line `summary` and
  3-6 `triggers` (real symptoms, error codes, words a searcher would type, in every language
  the user searches in). Link it from its section's `Index.md`; a new section folder gets its
  own `Index.md`, linked from the parent.
- Wrong article: correct the claim, explain the failure mode under "Common pitfalls", cite the
  source, update `last-verified` and `verified-against`.
- Metadata-only edits (summary, triggers, tags, links, formatting) keep the existing
  `status` and `last-verified`. Reading or reformatting is not verification. Never invent a
  verification date.
- Superseded article: move it to the archive folder (`90 - Archive/` or as the vault says)
  rather than leaving stale guidance active. Move single articles through Obsidian (drag in
  the file explorer, or "Move file") so wiki-links are rewritten; tell the user if you cannot.

## Step 4 - Drafts

- Resolve only drafts you created in this task, or that the user put in scope.
- Promotion needs verification and the full article format, not just a move.
- A draft older than 30 days is a cue to review it with the user, never to delete or promote
  it automatically. Leave a blocked draft with a one-line reason.

## Step 5 - Check and commit

1. If the **knowledgebase-search** skill is installed, run its
   `kb.py check --vault <name>` and fix problems in the files you touched (broken links,
   missing frontmatter or `Index.md`). Report other problems; do not fix them unasked.
2. In a git vault, commit only the files you changed, e.g.
   `git -C "<vault>" add -- "<file>" ... && git -C "<vault>" commit -m "kb: <what changed>"`.
   Never commit the user's unrelated changes, and never push unless asked.

Report what you wrote: vault, path, status, the commit if any, and what still needs
verification.
