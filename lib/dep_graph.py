#!/usr/bin/env python3
"""Dependency graph analysis for code navigation."""

import sys
from pathlib import Path
from project_data import build_project_data
from collections import defaultdict


def analyze_deps(root: str):
    data = build_project_data(root)
    modules = data['modules']

    # Build dependency map
    dep_map = defaultdict(list)
    reverse_dep = defaultdict(list)

    for m in modules:
        for imp in m['imports']:
            imp_path = imp.replace('.', '/')
            last_seg = imp_path.split('/')[-1]
            for other in modules:
                mod_path = str(Path(other['path']).with_suffix(''))
                # Exact match or path-boundary match (avoid partial name collisions)
                if (mod_path == imp_path or
                    mod_path.startswith(imp_path + '/') or
                    mod_path.endswith('/' + imp_path) or
                    Path(other['path']).stem == last_seg):
                    dep_map[m['path']].append(other['path'])
                    reverse_dep[other['path']].append(m['path'])
                    break

    print(f"=== Dependency Graph: {data['project']['name']} ===\n")

    # Most depended upon (hub modules)
    hubs = sorted(reverse_dep.items(), key=lambda x: -len(x[1]))[:15]
    print("🔗 Most depended upon (hub modules):")
    for path, dependents in hubs:
        print(f"  {path} ← {len(dependents)} dependents")
        for d in dependents[:5]:
            print(f"    ← {d}")
        if len(dependents) > 5:
            print(f"    ... and {len(dependents)-5} more")

    print("\n📡 Most dependencies (imports many):")
    importers = sorted(dep_map.items(), key=lambda x: -len(x[1]))[:15]
    for path, deps in importers:
        print(f"  {path} → {len(deps)} dependencies")
        for d in deps[:5]:
            print(f"    → {d}")
        if len(deps) > 5:
            print(f"    ... and {len(deps)-5} more")

    # Circular dependencies
    print("\n⚠️  Circular dependencies:")
    circular = []
    for m1, deps1 in dep_map.items():
        for d1 in deps1:
            if d1 in dep_map and m1 in dep_map[d1]:
                pair = tuple(sorted([m1, d1]))
                if pair not in circular:
                    circular.append(pair)
    if circular:
        for m1, m2 in circular[:10]:
            print(f"  {m1} ↔ {m2}")
    else:
        print("  None found ✓")


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    analyze_deps(root)
