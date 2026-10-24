---
name: knowledgebase-setup
description: >-
  Create a new local Markdown knowledge base (an Obsidian vault an AI agent can search and
  maintain), or connect an existing vault or notes folder, and register it so the
  knowledgebase-search and knowledgebase-write skills find it. Use when the user says "set up
  a knowledge base", "create my KB", "make an Obsidian vault for my notes", "add my vault",
  "connect my Obsidian vault", "opret en vidensbase", "tilføj min vault", or when another
  knowledgebase skill reports "No vaults configured". Scaffolds AGENTS.md, CLAUDE.md, a
  README, a writing guide, article templates, section folders with Index pages, _drafts and
  an archive, without overwriting anything that exists.
license: MIT
---

# Set up a knowledge base

A knowledge base here is a plain folder of Markdown files with YAML frontmatter, usually an
Obsidian vault. Obsidian is optional; the agent only needs the files.

## Step 0 - Check Python

Searching needs Python 3.9+ and nothing else:

```bash
python3 -c 'import sys; assert sys.version_info >= (3, 9), sys.version; print(sys.version)'
```

If that fails, offer to install it and run the command only after the user agrees:
macOS `brew install python` (or the installer from python.org), Debian/Ubuntu
`sudo apt install python3`, Windows `winget install Python.Python.3.13`. Writing and the
vault itself need no dependencies.

## Step 1 - Ask

Ask in one message, offering defaults:

1. **New or existing?** A new folder, or a vault/notes folder they already have.
2. **Where?** For a new vault, the parent folder (e.g. `~/Documents/Obsidian/`; on macOS the
   iCloud Obsidian folder `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/` syncs
   to phones). The vault name becomes the folder name.
3. **Short name and scope.** A short name for searches (`it`, `dev`, `notes`) and one line
   on what belongs in it, e.g. "Endpoint management, identity and PowerShell".
4. **Sections** (new vaults): 3-8 top-level topics, e.g. `Identity`, `Endpoint`, `Scripts`.
5. **What must stay out:** for example customer names, hostnames, personal data, secrets.

## Step 2 - Scaffold

Set `SKILL_DIR` to the absolute directory of this loaded skill. Copy the scaffold without
overwriting existing files (for an existing vault this only adds what is missing):

```bash
mkdir -p "<vault>" && cp -Rn "$SKILL_DIR/assets/vault/." "<vault>/"
mkdir -p "<vault>/00 - Inbox" "<vault>/90 - Archive" "<vault>/_drafts"
```

Then in the vault:

- Replace the `{{...}}` placeholders in `AGENTS.md`, `README.md` and
  `_templates/Writing Guide.md` with the vault name, scope and "stays out" rules from
  Step 1. Leave `{{title}}` / `{{date}}` in the other templates alone: Obsidian's
  Templates plugin fills those.
- For each section create `NN - <Section>/Index.md` from `_templates/Index Template.md`
  (numbered `01`, `02`, ... so they sort), and link each one from `README.md`. Fill in the
  title and overview and delete the template's example links (`[[Doc Name]]`, ...).
- An existing vault keeps its own `AGENTS.md`, guide and folder names if it already has them.
  If its conventions differ from the scaffold (other frontmatter fields, other folders), say
  so and let the user choose; do not rewrite their notes.

## Step 3 - Version it with git (recommended)

Offer this; it makes every agent edit reviewable (`git diff`) and undoable. Skip it if the
user declines or git is missing (macOS `xcode-select --install`, Debian/Ubuntu
`sudo apt install git`, Windows `winget install Git.Git`).

```bash
git -C "<vault>" rev-parse --git-dir 2>/dev/null || git -C "<vault>" init
git -C "<vault>" add -A && git -C "<vault>" commit -m "Knowledge base scaffold"
```

The scaffold's `.gitignore` leaves out Obsidian's per-device workspace files. Never add a
remote or push unless the user asks; a vault with private notes must not go to a public repo.
On iCloud this is fine for one Mac with "Keep Downloaded" on; editing the same vault from
two Macs can conflict inside `.git`. The Obsidian Git community plugin can commit
automatically if the user wants that.

## Step 4 - Register

Add the vault to `~/.config/knowledgebase/vaults.json` (or the file named in `KB_CONFIG`),
keeping any vaults already there:

```json
{
  "vaults": {
    "<short-name>": {"path": "<absolute vault path>", "about": "<one-line scope>"}
  },
  "aliases": []
}
```

`aliases` is optional: pairs like `["k8s", "kubernetes"]` let a search for one term find the
other. If the **knowledgebase-search** skill is installed, verify with its
`kb.py vaults` command, then run `kb.py check --vault <short-name>`. A new vault must come
out clean: fix what you scaffolded. For an existing vault, summarize what it reports
(missing frontmatter, broken links, folders without `Index.md`, old drafts) and fix nothing
unless the user asks.

## Step 5 - Tell the user

- In Obsidian: "Open folder as vault", then Settings > Core plugins > Templates > template
  folder location = `_templates`, so new notes can start from the templates.
- The agent finds knowledge with the **knowledgebase-search** skill and adds it with the
  **knowledgebase-write** skill. Good first step: "write down what we figured out today in
  my KB".
- iCloud vault on macOS: right-click the vault folder in Finder > "Keep Downloaded".
  Otherwise "Optimize Mac Storage" evicts notes and searches stall while they download.
- Keep the vault out of public repositories if it holds anything private.
