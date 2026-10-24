# Knowledge base skills

Agent skills for building your own knowledge base: a local folder of Markdown notes (an
[Obsidian](https://obsidian.md) vault, or any folder) that your AI agent searches before it
answers, and adds to as you work. Every article says whether it is verified, when, and against
what, so the agent knows how far to trust it. Nothing leaves your machine.

Works with Claude Code, Codex, Cursor, Gemini CLI, Antigravity, GitHub Copilot, OpenCode and
any other agent that reads [Agent Skills](https://agentskills.io).

## Skills

| Skill | What it does |
|-------|--------------|
| `knowledgebase-setup` | Creates a new vault (or adopts an existing one): agent guidance, writing guide, templates, section Index pages, drafts and archive folders, optionally a git repository so every agent edit can be reviewed and undone. Registers it in `~/.config/knowledgebase/vaults.json`. |
| `knowledgebase-search` | Ranked search across your vaults with status and date, then bounded reads that always include prerequisites and pitfalls. Drafts and archive are excluded or flagged. `kb.py check` reports missing metadata, broken links, folders without `Index.md` and old drafts. |
| `knowledgebase-write` | Adds verified findings as full articles, unverified ones as dated drafts, corrects wrong articles and archives stale ones, following the vault's own rules. Checks the vault afterwards and commits its own changes in a git vault. |

## Install

### Any agent: the `skills` CLI

```bash
npx skills add kastruppro/knowledgebase
```

Non-interactive examples:

```bash
npx skills add kastruppro/knowledgebase -a claude-code -a codex -y               # this project
npx skills add kastruppro/knowledgebase --skill knowledgebase-search -g          # one skill, globally
```

Install globally (`-g`) if you want your knowledge base available in every project.

### Claude Code: the plugin

```text
/plugin marketplace add kastruppro/knowledgebase
/plugin install knowledgebase@knowledgebase
```

Use either the plugin or the `skills` CLI for Claude Code, not both, or the skills appear twice.

### Codex

`.codex-plugin/plugin.json` lets Codex load this repo as a plugin.

### Manually

Copy the folders you want from `skills/` into your agent's skills directory, for example
`~/.claude/skills/` (Claude Code) or `~/.agents/skills/` (Codex, Cursor, Gemini CLI,
Antigravity, OpenCode, Copilot).

## Get started

Ask your agent: **"Set up a knowledge base for my notes"**. It asks where, what the vault
covers and which sections you want, then scaffolds and registers it. After that:

- "Check my knowledge base: why does X fail with error 0x8018..."
- "Write down what we figured out today in my KB."

Several vaults are fine (for example one for work, one for development); each gets a short
name and a one-line description the agent uses to pick the right one.

## Config

`~/.config/knowledgebase/vaults.json` (or the path in `KB_CONFIG`):

```json
{
  "vaults": {
    "it": {"path": "~/Documents/Obsidian/IT", "about": "Endpoint management, identity, PowerShell"},
    "dev": {"path": "~/Documents/Obsidian/Dev", "about": "Web and app development"}
  },
  "aliases": [["k8s", "kubernetes"], ["aad", "entra"]]
}
```

## Requirements

- Python 3.9+ (`python3`), nothing else. The `knowledgebase-setup` skill checks for it.
- Optional: git, to version the vault.
- Obsidian is optional.

## Privacy

The skills read and write only the folders you register. Nothing is uploaded. Keep vaults with
private content out of public repositories.

## Repository layout

```
skills/<name>/SKILL.md (+ scripts/, assets/)   the skills
.claude-plugin/plugin.json, marketplace.json   Claude Code plugin "knowledgebase" + marketplace
.codex-plugin/plugin.json                      Codex plugin manifest
AGENTS.md                                      contributor and agent instructions
```

## License

MIT - see [LICENSE](LICENSE).
