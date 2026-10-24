# AGENTS.md - knowledgebase

Agent Skills that let anyone build a local Markdown/Obsidian knowledge base which AI agents
search before answering and keep up to date. This repo is two things at once:

1. An [Agent Skills](https://agentskills.io/specification) collection installable into any agent
   with `npx skills add kastruppro/knowledgebase` (Vercel's `skills` CLI).
2. A Claude Code plugin + marketplace (`/plugin marketplace add kastruppro/knowledgebase`,
   then `/plugin install knowledgebase@knowledgebase`).

No server, no MCP: the vaults are plain folders on the user's machine, listed in
`~/.config/knowledgebase/vaults.json` (or the file in `KB_CONFIG`).

## Layout

```
skills/<name>/SKILL.md                     one folder per skill; `name` in frontmatter == folder name
skills/knowledgebase-search/scripts/kb.py  the only code: search, read, check; never writes (stdlib, Python 3.9+)
skills/knowledgebase-search/scripts/tests/ unittest suite with throwaway vaults
skills/knowledgebase-setup/assets/vault/   scaffold copied into a new vault (AGENTS.md, templates)
.claude-plugin/plugin.json                 Claude Code plugin "knowledgebase" (skills only)
.claude-plugin/marketplace.json            marketplace "knowledgebase", one plugin, source "./"
.codex-plugin/plugin.json                  Codex plugin manifest, skills -> ./skills/
```

## Rules for editing skills

- Follow the Agent Skills spec: frontmatter `name` (lowercase kebab, equal to the folder name,
  max 64 chars) and `description` (max 1024 chars). The description decides whether an agent
  uses the skill: say what it does AND when, with the words a user would actually say.
- Keep `SKILL.md` short (well under 500 lines). Long material goes in `references/` or
  `assets/`, referenced by a relative path one level from `SKILL.md`.
- Write tool-neutral instructions. Each skill must work on its own: users install a subset.
  Mention a sibling skill by name, never by a `../` path.
- The vault config format (`vaults` -> `path`, `about`; optional `aliases`) appears in all three
  skills and in `kb.py`'s `load_config`. Change them together.
- Skills are written in English. Trigger phrases may be Danish or English.
- No absolute paths to anyone's machine, no real notes. Examples use invented names.
- Use plain hyphens, not em/en dashes.

## Checks before committing

```bash
# skills discovered by the skills CLI (needs Node.js)
npx skills add ./ --list

# plugin + marketplace manifests
claude plugin validate .

# search script tests
python3 -m unittest discover -s skills/knowledgebase-search/scripts/tests -v

# no personal paths
git grep -nE "/Users/|/home/[a-z]" -- skills && echo "FOUND - fix before commit"
```

## Git

Conventional Commits, one line. Do not push without an explicit instruction.
