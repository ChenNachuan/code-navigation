#!/usr/bin/env python3
"""Drift detection — detect code changes via fingerprinting."""

import sys
import json
from pathlib import Path
from project_data import build_project_data


def detect_drift(root: str):
    root_path = Path(root).resolve()
    cache_dir = Path.home() / '.cache' / 'code-navigate'
    cache_dir.mkdir(parents=True, exist_ok=True)
    state_file = cache_dir / (root_path.name + '.state.json')

    # Load previous state
    old_state = {}
    if state_file.exists():
        old_state = json.loads(state_file.read_text())
        print(f"Loaded previous state: {len(old_state.get('modules', []))} modules tracked")
    else:
        print("No previous state found — will create initial snapshot")

    # Build current state
    print(f"Analyzing {root_path.name}...")
    data = build_project_data(root)
    current_modules = {m['path']: m for m in data['modules']}

    # Compare
    if not old_state.get('modules'):
        print("\n📸 Initial snapshot created")
    else:
        old_modules = {m['path']: m for m in old_state['modules']}

        # Changed
        changed = []
        for path, m in current_modules.items():
            if path in old_modules and m['fingerprint'] != old_modules[path]['fingerprint']:
                changed.append(path)

        # Added
        added = [p for p in current_modules if p not in old_modules]

        # Removed
        removed = [p for p in old_modules if p not in current_modules]

        print(f"\n=== Drift Report ===")
        print(f"  📝 Changed: {len(changed)} files")
        for f in changed[:10]:
            print(f"    ~ {f}")
        if len(changed) > 10:
            print(f"    ... and {len(changed)-10} more")

        print(f"  ✨ Added: {len(added)} files")
        for f in added[:10]:
            print(f"    + {f}")

        print(f"  🗑️  Removed: {len(removed)} files")
        for f in removed[:10]:
            print(f"    - {f}")

        if not changed and not added and not removed:
            print("\n✅ No drift detected — code is unchanged")

    # Save current state
    state = {
        'project': data['project'],
        'modules': data['modules'],
    }
    state_file.write_text(json.dumps(state, indent=2))
    print(f"\n💾 State saved to {state_file.name}")


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    detect_drift(root)
