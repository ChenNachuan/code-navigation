# code-navigation

> **Skill + CLI for navigating and visualizing large codebases.** Symbol lookup, call chains, dependency analysis, architecture diagrams — all in one.

Pairs with [archify](https://github.com/tt-a1i/archify) for interactive HTML architecture diagrams.

## What's inside

```
code-navigation/
├─ SKILL.md                  # Claude Code skill — when/how/why to navigate
├─ references/
│  └─ archify-guide.md       # Complete archify schema & design guide
├─ code-navigate.sh          # CLI entry point
├─ lib/
│  ├─ project_data.py        # Project structure extraction
│  ├─ dep_graph.py           # Dependency analysis
│  ├─ drift_detect.py        # Change detection (SHA-256)
│  └─ to_archify.py          # Archify JSON bridge
└─ README.md
```

**One project, two faces**:
- **As a skill** (`~/.claude/skills/code-navigation/`) — teaches Claude how to navigate codebases
- **As a CLI** (`./code-navigate.sh`) — deterministic tools you can run directly

## What this is (and isn't)

| ✅ does | ❌ doesn't |
|---|---|
| Fast CLI queries (`symbol`, `refs`, `search`) | Render HTML diagrams (use archify) |
| Symbol indexing (ctags) | Interactive visualization |
| Dependency analysis | Architecture drawing |
| Drift detection | UI components |
| Structured JSON output | Diagram theming |

## Install

```bash
# Dependencies
brew install ripgrep universal-ctags tree-sitter-cli

# Clone
git clone https://github.com/ChenNachuan/code-navigation.git
cd code-navigation
chmod +x code-navigate.sh

# Install as Claude Code skill
ln -s "$(pwd)" ~/.claude/skills/code-navigation

# Optional: add CLI to PATH
ln -s "$(pwd)/code-navigate.sh" /usr/local/bin/code-navigate
```

## CLI Commands

| Command | Purpose | Backend |
|---------|---------|---------|
| `index <dir>` | Build symbol index | ctags |
| `symbol <name>` | Find definition | ctags |
| `refs <name>` | Find all references | grep |
| `search <pattern>` | Full-text search | grep |
| `ast <file>` | Syntax tree | tree-sitter |
| `summary <dir>` | Project overview | find |
| `tree <dir>` | Directory layout | find |
| `deps <dir>` | Dependency graph | Python |
| `drift <dir>` | Change detection | Python |
| `viz <dir> [template\|mechanical]` | Architecture diagram pipeline | Python + archify |

## Quick start

```bash
# Understand a project
./code-navigate.sh summary ~/projects/my-api
./code-navigate.sh tree ~/projects/my-api

# Build index, then query
./code-navigate.sh index ~/projects/my-api
./code-navigate.sh symbol validate_user
./code-navigate.sh refs validate_user

# Dependency analysis
./code-navigate.sh deps ~/projects/my-api

# Architecture diagram (3-step pipeline)
./code-navigate.sh viz ~/projects/my-api template
# → AI reads template.md → writes candidate.json → renders architecture.html
```

## Architecture diagram pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Extract     │────▶│  Analyze     │────▶│  Render     │
│  (CLI)       │     │  (AI/you)    │     │  (archify)  │
│  template.md │     │  candidate   │     │  .html      │
└─────────────┘     └──────────────┘     └─────────────┘
```

All outputs go to `<project>/.navigate/output/`:
- `template.md` — raw data for AI analysis
- `candidate.json` — semantic archify JSON
- `architecture.html` — interactive diagram

## Why semantic analysis?

Directory names produce ugly diagrams (`server/`, `apps/`, `internal/`). The AI step names components by **role** ("API Gateway", "Auth Service") and labels connections by **what flows** ("HTTP/WebSocket", "SQL queries"). This is what separates a code map from an architecture diagram.

See `references/archify-guide.md` for the complete design guide.

## Why this over raw grep?

| Task | `grep` | `code-navigate` |
|------|--------|-----------------|
| Find definition | Scans all files | Instant (ctags index) |
| Find references | May miss contexts | Structured search |
| Understand structure | Manual | `summary` + `tree` |
| AST analysis | Not possible | tree-sitter |

## Requirements

- [universal-ctags](https://github.com/universal-ctags/ctags)
- [ripgrep](https://github.com/BurntSushi/ripgrep)
- [tree-sitter](https://github.com/tree-sitter/tree-sitter)
- Python 3.8+
- Node.js (for archify rendering)

## License

MIT
