#!/usr/bin/env python3
"""Convert code-navigate project data to archify architecture JSON.

Two modes:
  1. Mechanical (default): directory-based grouping — fast, for quick previews
  2. AI-refined: output raw data + template for AI to produce semantic JSON

The AI-refined mode is what produces archify-quality diagrams.
"""

import sys
import json
from pathlib import Path
from project_data import build_project_data


def classify_component(mods: list) -> str:
    """Classify component type from file extensions."""
    exts = {}
    for m in mods:
        exts[m['ext']] = exts.get(m['ext'], 0) + 1
    primary = max(exts, key=exts.get) if exts else '.py'
    type_map = {
        '.py': 'backend', '.go': 'backend', '.rs': 'backend', '.java': 'backend',
        '.js': 'frontend', '.ts': 'frontend', '.tsx': 'frontend',
        '.sql': 'database',
        '.yml': 'cloud', '.yaml': 'cloud', '.dockerfile': 'cloud',
    }
    return type_map.get(primary, 'backend')


def to_archify_mechanical(data: dict, output_html: str) -> dict:
    """Fast directory-based grouping (preview quality)."""
    project = data['project']
    modules = data['modules']

    dir_groups = {}
    for m in modules:
        parts = Path(m['path']).parts
        key = parts[0] if len(parts) > 1 else 'root'
        dir_groups.setdefault(key, []).append(m)

    components = []
    for i, (comp_name, mods) in enumerate(sorted(dir_groups.items())):
        components.append({
            'id': comp_name.lower().replace(' ', '_').replace('.', '_').replace('-', '_'),
            'type': classify_component(mods),
            'label': comp_name,
            'sublabel': f"{len(mods)} files · {sum(m['lines'] for m in mods):,} lines",
            'pos': [80 + (i % 4) * 280, 80 + (i // 4) * 200],
            'size': [200, 80],
        })

    # Mechanical connections
    connections = []
    seen = set()
    for comp_name, mods in dir_groups.items():
        src_id = comp_name.lower().replace(' ', '_').replace('.', '_').replace('-', '_')
        for m in mods:
            for imp in m['imports'][:5]:
                imp_clean = imp.replace('.', '/').replace('github.com/', '').replace('gitlab.com/', '')
                last_seg = imp_clean.split('/')[-1]
                for other_name, other_mods in dir_groups.items():
                    if other_name == comp_name:
                        continue
                    # Only connect if the import actually resolves into that directory.
                    hit = any(
                        (str(Path(om['path']).with_suffix('')) == imp_clean or
                         str(Path(om['path']).with_suffix('')).endswith('/' + imp_clean) or
                         Path(om['path']).stem == last_seg)
                        for om in other_mods
                    )
                    if not hit:
                        continue
                    other_id = other_name.lower().replace(' ', '_').replace('.', '_').replace('-', '_')
                    edge = (src_id, other_id)
                    if edge not in seen:
                        seen.add(edge)
                        connections.append({
                            'id': f"{src_id}-to-{other_id}",
                            'from': src_id,
                            'to': other_id,
                            'label': 'imports',
                        })

    return {
        'schema_version': 1,
        'diagram_type': 'architecture',
        'meta': {
            'title': project['name'],
            'subtitle': f"{project['total_files']} files · {project['total_lines']:,} lines",
            'output': output_html,
            'quality_profile': 'showcase',
        },
        'components': components[:20],
        'connections': connections[:25],
    }


def generate_ai_template(data: dict) -> str:
    """Generate raw data + template for AI to produce semantic archify JSON."""
    project = data['project']
    modules = data['modules']

    # Extract key facts for AI
    dir_summary = {}
    for m in modules:
        parts = Path(m['path']).parts
        key = parts[0] if len(parts) > 1 else 'root'
        entry = dir_summary.setdefault(key, {'files': 0, 'lines': 0, 'symbols': [], 'imports': set()})
        entry['files'] += 1
        entry['lines'] += m['lines']
        entry['symbols'].extend(s['name'] for s in m['symbols'][:10])
        entry['imports'].update(m['imports'][:5])

    template = f"""# Archify Architecture JSON Template
# Use code-navigate data to create SEMANTIC architecture JSON for archify.
# Do NOT use directory names as component labels — understand the architecture.

## Project: {project['name']}
- {project['total_files']} files, {project['total_lines']:,} lines
- Languages: {project['languages']}

## Raw structure (for your analysis):
"""
    for d, info in sorted(dir_summary.items()):
        template += f"""
### {d}/
  Files: {info['files']}, Lines: {info['lines']:,}
  Key symbols: {', '.join(info['symbols'][:8])}
  Imports: {', '.join(list(info['imports'])[:6])}
"""

    template += """
## Your task: Create archify architecture JSON

Rules:
1. **Semantic components**: Name by ROLE, not directory ("API Gateway" not "server/")
2. **Meaningful connections**: Label what flows ("HTTP requests", "events", "SQL queries")
3. **Boundaries**: Group related components with dashed borders
4. **Layout**: Left-to-right flow (entry → processing → output)
5. **Types**: Use frontend/backend/database/cloud/security/messagebus/external
6. **Sublabels**: Brief, informative ("auth · JWT validation")

## Example format:
{
  "schema_version": 1,
  "diagram_type": "architecture",
  "meta": {
    "title": "<project-name>",
    "subtitle": "<N> files · <N> lines",
    "output": "architecture.html",
    "quality_profile": "showcase"
  },
  "components": [
    {
      "id": "api-gateway",
      "type": "backend",
      "label": "API Gateway",
      "sublabel": "REST · rate limiting",
      "pos": [100, 300],
      "size": [180, 70]
    }
  ],
  "boundaries": [
    {
      "id": "processing",
      "label": "Processing Layer",
      "kind": "logical"
    }
  ],
  "connections": [
    {
      "id": "gw-to-auth",
      "from": "api-gateway",
      "to": "auth-service",
      "label": "validate JWT"
    }
  ]
}

Write the JSON now. Use positions that create a clear flow.
"""
    return template


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    output = sys.argv[2] if len(sys.argv) > 2 else 'architecture.html'
    mode = sys.argv[3] if len(sys.argv) > 3 else 'template'

    print(f"Analyzing {root}...")
    data = build_project_data(root)

    # All outputs go to <project>/.navigate/output/
    nav_out = Path(root) / '.navigate' / 'output'
    nav_out.mkdir(parents=True, exist_ok=True)

    if mode == 'template':
        # Output AI template for semantic analysis
        template = generate_ai_template(data)
        out_path = nav_out / 'template.md'
        out_path.write_text(template)
        print(f"✅ AI template: {out_path}")
        print(f"   Next: AI reads this and creates semantic archify JSON")
    else:
        # Mechanical preview (fast, lower quality)
        arch = to_archify_mechanical(data, output)
        out_path = nav_out / 'candidate.json'
        out_path.write_text(json.dumps(arch, indent=2))
        print(f"✅ Mechanical candidate: {out_path} ({len(arch['components'])} components)")
        print(f"   This is preview quality. For archify-quality, use AI analysis.")


if __name__ == '__main__':
    main()
