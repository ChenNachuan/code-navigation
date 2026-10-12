#!/usr/bin/env bash
# code-navigate.sh — Lightweight code navigation toolkit
# Usage:
#   ./code-navigate.sh index <dir>        # Build symbol index (ctags)
#   ./code-navigate.sh search <pattern>   # Full-text search
#   ./code-navigate.sh symbol <name>      # Find symbol definition
#   ./code-navigate.sh refs <name>        # Find references
#   ./code-navigate.sh ast <file>         # Show AST
#   ./code-navigate.sh summary <dir>      # Project summary
#   ./code-navigate.sh tree <dir>         # Directory tree
#   ./code-navigate.sh deps <dir>         # Dependency graph analysis
#   ./code-navigate.sh drift <dir>        # Detect code changes (fingerprint)
#   ./code-navigate.sh data <dir>         # Structured JSON (for archify rendering)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "${1:-help}" in
  index)
    DIR="${2:-.}"
    echo "Building symbol index for $DIR..."
    ctags -R --fields=+n+S --exclude=.git --exclude=node_modules --exclude=__pycache__ "$DIR"
    echo "Done: $(wc -l < tags) symbols indexed in ./tags"
    ;;

  search)
    PATTERN="${2:?Pattern required}"
    DIR="${3:-.}"
    echo "=== Full-text search: $PATTERN ==="
    grep -rn --include="*.py" --include="*.js" --include="*.ts" --include="*.go" --include="*.rs" --include="*.java" --include="*.c" --include="*.cpp" --include="*.h" "$PATTERN" "$DIR" 2>/dev/null | head -50
    ;;

  symbol)
    NAME="${2:?Symbol name required}"
    DIR="${3:-.}"
    if [[ ! -f tags ]]; then
      echo "No tags file. Run: ./code-navigate.sh index $DIR first"
      exit 1
    fi
    echo "=== Symbol definition: $NAME ==="
    grep -n "$NAME" tags | head -20
    ;;

  refs)
    NAME="${2:?Symbol name required}"
    DIR="${3:-.}"
    echo "=== References to: $NAME ==="
    grep -rn --include="*.py" --include="*.js" --include="*.ts" --include="*.go" --include="*.rs" --include="*.java" --include="*.c" --include="*.cpp" --include="*.h" "$NAME" "$DIR" 2>/dev/null | head -30
    ;;

  ast)
    FILE="${2:?File required}"
    echo "=== AST for: $FILE ==="
    if [[ "$FILE" == *.py ]]; then
      python3 -c "
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)
with open('$FILE', 'rb') as f:
    tree = parser.parse(f.read())
def walk(node, indent=0):
    print('  ' * indent + f'{node.type} [{node.start_point[0]}:{node.start_point[1]}]')
    for child in node.children:
        walk(child, indent + 1)
walk(tree.root_node)
" 2>/dev/null || echo "Install: pip install tree-sitter-python"
    else
      tree-sitter parse "$FILE" 2>/dev/null | head -50 || echo "tree-sitter not available for this file type"
    fi
    ;;

  summary)
    DIR="${2:-.}"
    echo "=== Project Summary: $DIR ==="
    echo ""
    echo "--- Language breakdown ---"
    find "$DIR" -type f -not -path '*/.*' -not -path '*/node_modules*' -not -path '*/__pycache__*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15
    echo ""
    echo "--- Structure (depth 2) ---"
    find "$DIR" -maxdepth 2 -type d -not -path '*/.*' -not -path '*/node_modules*' | head -30
    echo ""
    echo "--- Code size ---"
    find "$DIR" -type f -not -path '*/.*' -not -path '*/node_modules*' -not -path '*/__pycache__*' | wc -l | xargs echo "Total files:"
    ;;

  tree)
    DIR="${2:-.}"
    find "$DIR" -not -path '*/\.*' -not -path '*/node_modules*' -not -path '*/__pycache__*' | head -100
    ;;

  data)
    DIR="${2:-.}"
    python3 "$SCRIPT_DIR/lib/project_data.py" "$DIR"
    ;;

  viz)
    DIR="${2:-.}"
    MODE="${3:-template}"
    NAV_OUT="$DIR/.navigate/output"
    mkdir -p "$NAV_OUT"
    if [[ "$MODE" == "template" ]]; then
      echo "📝 Generating AI analysis template..."
      python3 "$SCRIPT_DIR/lib/to_archify.py" "$DIR" "$NAV_OUT/template.md" template
      echo ""
      echo "Next: AI reads template.md → creates semantic JSON → render"
    else
      echo "⚡ Mechanical preview (fast, lower quality)..."
      python3 "$SCRIPT_DIR/lib/to_archify.py" "$DIR" "$NAV_OUT/architecture.html" mechanical
      echo ""
      ARCHIFY_BIN="$HOME/.claude/skills/archify/bin/archify.mjs"
      if [[ -f "$ARCHIFY_BIN" ]]; then
        CANDIDATE="$NAV_OUT/candidate.json"
        node "$ARCHIFY_BIN" finalize architecture "$CANDIDATE" "$NAV_OUT/architecture.html" --quality showcase --json --out-dir "$NAV_OUT" 2>&1 | tail -10
        echo "✅ Open $NAV_OUT/architecture.html"
      fi
    fi
    ;;

  deps)
    DIR="${2:-.}"
    python3 "$SCRIPT_DIR/lib/dep_graph.py" "$DIR"
    ;;

  drift)
    DIR="${2:-.}"
    python3 "$SCRIPT_DIR/lib/drift_detect.py" "$DIR"
    ;;

  help|*)
    echo "Code Navigation Toolkit"
    echo ""
    echo "Commands:"
    echo "  index <dir>          Build symbol index (ctags)"
    echo "  search <pattern>     Full-text search"
    echo "  symbol <name>        Find symbol definition"
    echo "  refs <name>          Find all references"
    echo "  ast <file>           Show AST"
    echo "  summary <dir>        Project summary"
    echo "  tree <dir>           Directory tree"
    echo "  data <dir>           Structured JSON"
    echo "  viz <dir> [template|mechanical]"
    echo "                       template: AI analysis prompt (archify quality)"
    echo "                       mechanical: fast preview (lower quality)"
    echo "  deps <dir>           Dependency graph analysis"
    echo "  drift <dir>          Detect code changes"
    ;;
esac
