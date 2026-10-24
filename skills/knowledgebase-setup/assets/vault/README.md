# {{Vault name}}

{{One-line scope.}}

## Sections

- [[01 - {{Section}}/Index|{{Section}}]]

## How this vault works

- Every article has frontmatter with `status` (`verified`, `draft` or `archived`),
  `last-verified` and `verified-against`, so you and your AI agent know how much to trust it.
- New notes start from `_templates/`. The rules are in
  [_templates/Writing Guide.md](_templates/Writing%20Guide.md); agents start at
  [AGENTS.md](AGENTS.md).
- `00 - Inbox/` is for unsorted notes, `_drafts/` for unverified agent notes, `90 - Archive/`
  for superseded articles. Search skips drafts and the archive by default.
