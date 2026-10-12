---
name: code-navigation
description: >-
  Efficient codebase navigation for large projects. Use when the user wants to
  find code definitions, trace call chains, understand project structure,
  search for symbols, analyze dependencies, or create architecture diagrams.
  Does NOT handle writing code, code review, or general programming tasks.
metadata:
  uskill.icon: "🗺️"
  uskill.category: developer
  uskill.display_name: Code Navigation
  uskill.display_desc: Navigate and visualize large codebases
---

# Code Navigation

## Hard rules

1. **Index first**: run `code-navigate index <dir>` before symbol lookups.
2. **Right tool for the job**: definition → `symbol`, call chain → `refs`, structure → `summary`, dependency → `deps`.
3. **Start with `summary`**: understand project shape before details.
4. **Architecture diagrams need semantic analysis**: never use directory names as component labels.
5. **Rendering is archify's job**: create semantic JSON, then call archify.

## When to use / NOT

**Use**: find definition · trace call chain · understand project structure · search large codebase · analyze dependencies · create architecture diagram.

**NOT**: writing code · code review · debugging · general programming.

## Tools

| Tool | Purpose | Location |
|------|---------|----------|
| `code-navigate` | CLI: index, search, symbol, refs, ast, summary, tree, deps, drift, data, viz | `~/.claude/skills/code-navigation/code-navigate.sh` |
| `archify` | HTML architecture diagrams | `~/.claude/skills/archify/bin/archify.mjs` |

## Navigation Workflow

### 1. Understand project structure
```bash
code-navigate summary <dir>    # languages, structure, size
code-navigate tree <dir>       # directory layout
```

### 2. Build index (one-time)
```bash
code-navigate index <dir>      # ctags symbol index
```

### 3. Query code
```bash
code-navigate symbol <name>    # find definition
code-navigate refs <name>      # find all references
code-navigate search "pattern" # full-text search
code-navigate ast <file>       # syntax tree
```

### 4. Analyze dependencies
```bash
code-navigate deps <dir>       # dependency graph
code-navigate drift <dir>      # detect changes
```

## Architecture Diagram Pipeline

**Output convention**: all artifacts go to `<project>/.navigate/output/`

### Step 1: Extract raw data
```bash
code-navigate viz <dir> template
```

### Step 2: Semantic analysis (YOU do this)

Read the template and code. Create archify JSON. See `references/archify-guide.md` for complete schema.

**Key rules**:
- **Semantic components**: name by ROLE, not directory ("API Gateway" not "server/")
- **Meaningful connections**: label what flows ("HTTP/WebSocket", "SQL queries", "dispatch tasks")
- **Boundaries**: group related components (`region` / `security-group`)
- **Layout**: left-to-right flow (entry → processing → output)
- **Types**: `frontend`, `backend`, `database`, `cloud`, `security`, `messagebus`, `external`
- **Quality**: `quality_profile: "showcase"` for presentations

### Step 3: Write archify JSON

Write to `.navigate/output/candidate.json`. Full schema in `references/archify-guide.md`.

### Step 4: Render with archify
```bash
node ~/.claude/skills/archify/bin/archify.mjs finalize architecture \
  <dir>/.navigate/output/candidate.json <dir>/.navigate/output/architecture.html \
  --quality showcase --json --out-dir <dir>/.navigate/output
```

## Query Strategies

| Question | Strategy |
|----------|----------|
| "Where is X defined?" | `symbol X` |
| "Who calls X?" | `refs X` |
| "What calls what?" | `deps` |
| "Find code matching X" | `search "pattern"` |
| "What's in this file?" | `ast <file>` |
| "What changed?" | `drift` |
| "Draw the architecture" | Architecture Pipeline (above) |

## Reference files

| File | Load when |
|------|-----------|
| `references/archify-guide.md` | Creating architecture diagrams — full schema, design rules, render commands |
