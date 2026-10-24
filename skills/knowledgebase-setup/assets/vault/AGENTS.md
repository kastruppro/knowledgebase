# {{Vault name}} - agent guidance

{{One-line scope, e.g. "Reusable reference for endpoint management, identity and PowerShell."}}
{{What stays out, e.g. "Customer names, hostnames, tenant IDs and personal data never go here."}}

## Reading

- Search before answering a question this vault may cover: the knowledgebase-search skill
  (`kb.py search --vault <name> "keywords"`), narrowing with `--path` and widening if needed.
- Start with ranked excerpts and bounded previews; expand the relevant section and its
  prerequisites/pitfalls. Never apply truncated procedures or code.
- Check `status`, `last-verified` and `verified-against`. Drafts are unverified leads.
  Reading or editing metadata does not reverify a claim. `_drafts/` is session scratch;
  archived content is opt-in.

## Writing

For authorized changes, read [_templates/Writing Guide.md](_templates/Writing%20Guide.md)
once. It holds the frontmatter schema, templates, link and verification rules.

Do not modify `.obsidian/`. Move single articles through Obsidian so links are rewritten. Do
not delete or promote other sessions' drafts.
