#!/usr/bin/env python3
"""Project data extraction — outputs structured JSON for code navigation."""

import json
import re
import hashlib
import sys
from pathlib import Path
from collections import Counter

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next', 'target'}
CODE_EXTS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.hpp', '.rb', '.php', '.swift', '.kt'}


def get_files(root: Path) -> list:
    """Get all code files in project."""
    files = []
    for path in sorted(root.rglob('*')):
        if any(d in path.parts for d in SKIP_DIRS):
            continue
        if path.is_file() and path.suffix in CODE_EXTS:
            files.append(path)
    return files


def extract_symbols_ctags(root: Path) -> list:
    """Extract symbols using ctags (if available)."""
    import subprocess
    try:
        result = subprocess.run(
            ['ctags', '-R', '--output-format=json', '--fields=+n+S',
             '--exclude=.git', '--exclude=node_modules', '--exclude=__pycache__',
             str(root)],
            capture_output=True, text=True, timeout=30
        )
        symbols = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get('_type') == 'tag':
                    symbols.append({
                        'name': entry.get('name', ''),
                        'file': entry.get('path', ''),
                        'line': entry.get('line', 0),
                        'kind': entry.get('kind', ''),
                        'signature': entry.get('signature', ''),
                    })
            except json.JSONDecodeError:
                continue
        return symbols
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def extract_imports_python(content: str, file_path: str) -> list:
    """Extract Python imports."""
    imports = []
    for m in re.finditer(r'^(?:from\s+(\S+)\s+)?import\s+(.+)$', content, re.MULTILINE):
        if m.group(1):
            imports.append(m.group(1))
        for name in m.group(2).split(','):
            imports.append(name.strip().split('.')[0])
    return imports


def extract_imports_go(content: str) -> list:
    """Extract Go imports."""
    imports = []
    # Single import
    for m in re.finditer(r'import\s+"([^"]+)"', content):
        imports.append(m.group(1))
    # Import block
    for block in re.finditer(r'import\s*\(([^)]+)\)', content, re.DOTALL):
        for m in re.finditer(r'"([^"]+)"', block.group(1)):
            imports.append(m.group(1))
    return imports


def extract_imports_js(content: str) -> list:
    """Extract JS/TS imports."""
    imports = []
    for m in re.finditer(r'(?:require\([\'"]([^\'"]+)[\'"]\)|import\s+.*?from\s+[\'"]([^\'"]+)[\'"])', content):
        imports.append(m.group(1) or m.group(2))
    return imports


def extract_functions_simple(content: str, ext: str) -> list:
    """Extract function/class definitions via regex."""
    funcs = []
    if ext == '.py':
        for m in re.finditer(r'^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)', content, re.MULTILINE):
            funcs.append({'name': m.group(1), 'type': 'function', 'line': content[:m.start()].count('\n') + 1})
        for m in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            funcs.append({'name': m.group(1), 'type': 'class', 'line': content[:m.start()].count('\n') + 1})
    elif ext == '.go':
        for m in re.finditer(r'^func\s+(?:\([^)]+\)\s+)?(\w+)', content, re.MULTILINE):
            funcs.append({'name': m.group(1), 'type': 'function', 'line': content[:m.start()].count('\n') + 1})
        for m in re.finditer(r'^type\s+(\w+)\s+struct', content, re.MULTILINE):
            funcs.append({'name': m.group(1), 'type': 'struct', 'line': content[:m.start()].count('\n') + 1})
    elif ext in ('.js', '.ts', '.tsx', '.jsx'):
        for m in re.finditer(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\()', content):
            name = m.group(1) or m.group(2) or m.group(3)
            if name:
                funcs.append({'name': name, 'type': 'function', 'line': content[:m.start()].count('\n') + 1})
    return funcs


def build_project_data(root: str) -> dict:
    """Build complete project data structure."""
    root_path = Path(root).resolve()
    files = get_files(root_path)

    modules = []
    for f in files:
        rel = f.relative_to(root_path)
        content = f.read_text(errors='ignore')
        ext = f.suffix

        imports = []
        if ext == '.py':
            imports = extract_imports_python(content, str(rel))
        elif ext == '.go':
            imports = extract_imports_go(content)
        elif ext in ('.js', '.ts', '.tsx', '.jsx'):
            imports = extract_imports_js(content)

        symbols = extract_functions_simple(content, ext)

        # Fingerprint for drift detection
        fp = hashlib.sha256(content.encode()).hexdigest()[:16]

        modules.append({
            'path': str(rel),
            'ext': ext,
            'size': len(content),
            'lines': content.count('\n') + 1,
            'fingerprint': fp,
            'imports': imports[:20],
            'symbols': symbols[:50],
        })

    # Ctags symbols (richer, if available)
    ctags_symbols = extract_symbols_ctags(root_path)

    return {
        'project': {
            'name': root_path.name,
            'root': str(root_path),
            'total_files': len(modules),
            'total_lines': sum(m['lines'] for m in modules),
            'languages': dict(Counter(m['ext'] for m in modules).most_common()),
        },
        'modules': modules,
        'symbols': ctags_symbols,
    }


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    data = build_project_data(root)
    print(json.dumps(data, indent=2))
