---
title: Writing Guide
tags:
  - type/reference
  - topic/knowledge-base
status: verified
---

# Writing Guide

The rules for adding and changing articles in this vault. Agents read this once before writing.

## What goes in

- Reusable knowledge: how-tos, reference, error codes, troubleshooting playbooks, scripts.
- Only what was verified, as a full article. Unverified observations go in
  `_drafts/<YYYY-MM-DD>-<topic>/notes.md` until verified or deleted. Guesses go nowhere.
- {{What stays out and where it goes instead.}} Extract only the reusable pattern.

## Frontmatter (every article)

```yaml
---
title: <Document title>
summary: <one line: scope and when it applies>
triggers:
  - <a real symptom, error code or search phrase>
tags:
  - platform/<product or system>
  - type/<howto|reference|troubleshooting|script|moc>
  - topic/<optional finer topic>
last-verified: YYYY-MM-DD
verified-against: <product / version or source, e.g. "Intune 2026-09">
status: verified | draft | archived
---
```

- Tags are hierarchical (`platform/intune`, not `intune`). Always `platform/` and `type/`.
- `summary` and 3-6 `triggers` make articles findable: use the words a searcher would type,
  in every language you search in, plus exact error codes.
- `last-verified` records when the technical content was checked against a source, not when
  the file changed. Metadata, link and formatting edits keep the existing date and status.
- Put versions in frontmatter, not in filenames.

## Files and folders

- Filenames: `Title Case With Spaces.md`. Top-level folders: `NN - Title`.
- Start from the matching template in `_templates/`. Keep a `Common pitfalls` section: the
  search tool always shows prerequisite and pitfall sections in previews.
- Each section folder has an `Index.md` (tag `type/moc`) listing its articles and
  subfolders. A new folder gets an `Index.md`, linked from its parent.
- Superseded articles move to `90 - Archive/`; do not leave stale guidance active.

## Links

- Link articles by bare name: `[[Doc Name]]`. Link Index pages with their path:
  `[[01 - Section/Index|Section]]`, because every section has an `Index.md`.
- Move single articles through Obsidian (drag, or "Move file") so links are rewritten.

## Correcting an article

1. Fix the claim, cite the source, and record the failure mode under `Common pitfalls`.
2. Update `last-verified` and `verified-against`.

## Do not

- Modify `.obsidian/`.
- Invent or refresh verification dates without checking the content.
- Delete or promote drafts from other sessions.
