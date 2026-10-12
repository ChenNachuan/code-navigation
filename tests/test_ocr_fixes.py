#!/usr/bin/env python3
"""Tests for the OCR second-review fixes.

Each test encodes one reported defect. Run with:
    python3 -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / 'code-navigate.sh'
sys.path.insert(0, str(SKILL_DIR / 'lib'))


def run_cli(*args, cwd=None, env=None):
    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd, env=env, timeout=30,
    )


def make_tree(root: Path, files: dict) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def make_tree_sitter_stubs(td: Path) -> Path:
    """Minimal stubs so the inline python in `ast` reaches open()."""
    stubs = td / 'stubs'
    stubs.mkdir(exist_ok=True)
    (stubs / 'tree_sitter.py').write_text(
        'class Language:\n'
        '    def __init__(self, *a, **k):\n'
        '        pass\n'
        'class Parser:\n'
        '    def __init__(self, *a, **k):\n'
        '        pass\n'
        '    def parse(self, data):\n'
        '        class Node:\n'
        '            type = "module"\n'
        '            start_point = (0, 0)\n'
        '            children = []\n'
        '        class Tree:\n'
        '            root_node = Node()\n'
        '        return Tree()\n'
    )
    (stubs / 'tree_sitter_python.py').write_text(
        'def language():\n'
        '    return None\n'
    )
    return stubs


class TestShellInjection(unittest.TestCase):
    """code-navigate.sh: $FILE interpolated into inline Python source."""

    def test_ast_filename_cannot_execute_python(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            marker = tmp / 'injected_marker'
            stubs = make_tree_sitter_stubs(tmp)

            # Filename closes open('...'), runs code, re-opens a valid path.
            # Must end in .py (or the script never enters the python branch),
            # must not contain '/' (path separator).
            payload = (
                "x', 'rb') as f: pass\n"
                "__import__('os').system('touch injected_marker')\n"
                "with open('x.py"
            )
            (tmp / 'x').write_text('x = 1\n')
            (tmp / payload).write_text('x = 1\n')

            env = os.environ.copy()
            env['PYTHONPATH'] = str(stubs)
            result = run_cli('ast', payload, cwd=str(tmp), env=env)

            self.assertFalse(
                marker.exists(),
                f"filename executed code. stdout={result.stdout!r} stderr={result.stderr!r}",
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestPipefailAborts(unittest.TestCase):
    """code-navigate.sh: set -euo pipefail makes grep|head abort the script."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        make_tree(self.td, {
            'a.py': 'def alpha():\n    return 1\n',
            'b.py': 'def beta():\n    return 2\n',
        })

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_search_no_match_exits_zero(self):
        result = run_cli('search', 'zzz_no_match_zzz', str(self.td))
        self.assertEqual(result.returncode, 0,
                         f"search aborted on no-match: {result.stderr!r}")
        self.assertIn('Full-text search', result.stdout)

    def test_search_over_50_matches_exits_zero(self):
        # 50k lines exceeds the 64KB pipe buffer so grep actually hits SIGPIPE
        # once `head -50` closes its end.
        make_tree(self.td, {
            'big.py': 'common_token = 1\n' * 50000,
        })
        result = run_cli('search', 'common_token', str(self.td))
        self.assertEqual(result.returncode, 0,
                         f"search aborted on SIGPIPE: {result.stderr!r}")

    def test_refs_no_match_exits_zero(self):
        result = run_cli('refs', 'zzz_no_match_zzz', str(self.td))
        self.assertEqual(result.returncode, 0,
                         f"refs aborted on no-match: {result.stderr!r}")


class TestCodeExts(unittest.TestCase):
    """project_data.py: .tsx/.jsx handled later but missing from CODE_EXTS."""

    def test_tsx_and_jsx_are_collected(self):
        from project_data import build_project_data

        td = Path(tempfile.mkdtemp())
        try:
            make_tree(td, {
                'Widget.tsx': 'export function Widget() { return null; }\n',
                'Badge.jsx': 'export const Badge = () => null;\n',
            })
            data = build_project_data(str(td))
            names = {Path(m['path']).name for m in data['modules']}
            self.assertIn('Widget.tsx', names, f"collected={names}")
            self.assertIn('Badge.jsx', names, f"collected={names}")
        finally:
            shutil.rmtree(td, ignore_errors=True)


class TestDepSubstring(unittest.TestCase):
    """dep_graph.py: `imp_path in other['path']` is a substring test."""

    def test_import_os_does_not_link_to_cost_py(self):
        from dep_graph import analyze_deps

        td = Path(tempfile.mkdtemp())
        try:
            make_tree(td, {
                'app.py': 'import os\n',
                'cost.py': 'def total():\n    return 0\n',
            })
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                analyze_deps(str(td))
            out = buf.getvalue()
            self.assertNotIn('cost.py', out,
                             f"false dependency edge from substring match:\n{out}")
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_real_import_still_matches(self):
        """main.py -> lib/helper.py must still be linked after the fix."""
        from dep_graph import analyze_deps

        td = Path(tempfile.mkdtemp())
        try:
            make_tree(td, {
                'lib/helper.py': 'def f():\n    return 1\n',
                'main.py': 'from lib.helper import f\n',
            })
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                analyze_deps(str(td))
            out = buf.getvalue()
            self.assertIn('helper.py', out,
                          f"real import lost after fix:\n{out}")
        finally:
            shutil.rmtree(td, ignore_errors=True)


class TestMechanicalConnections(unittest.TestCase):
    """to_archify.py: edges added to every directory regardless of import."""

    def test_stdlib_import_does_not_link_all_dirs(self):
        from to_archify import to_archify_mechanical
        from project_data import build_project_data

        td = Path(tempfile.mkdtemp())
        try:
            make_tree(td, {
                'a/main.py': 'import json\n',
                'b/other.py': 'def f():\n    return 1\n',
                'c/third.py': 'def g():\n    return 2\n',
            })
            data = build_project_data(str(td))
            arch = to_archify_mechanical(data, 'out.html')
            ids = {c['id'] for c in arch['components']}
            dangling = [
                e for e in arch['connections']
                if e['from'] not in ids or e['to'] not in ids
            ]
            self.assertEqual(
                [], dangling,
                f"connections reference dropped components: {arch['connections']}",
            )
            self.assertEqual(
                0, len(arch['connections']),
                f"fully-connected graph (json does not resolve to b/c): "
                f"{arch['connections']}",
            )
        finally:
            shutil.rmtree(td, ignore_errors=True)


class TestDriftState(unittest.TestCase):
    """drift_detect.py: state keyed by basename only; json.loads unguarded."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self._old_home = os.environ.get('HOME')
        os.environ['HOME'] = str(self.home)

    def tearDown(self):
        if self._old_home is None:
            os.environ.pop('HOME', None)
        else:
            os.environ['HOME'] = self._old_home
        shutil.rmtree(self.home, ignore_errors=True)

    def test_same_basename_projects_do_not_share_state(self):
        from drift_detect import detect_drift

        proj_a = self.home / 'one' / 'src'
        proj_b = self.home / 'two' / 'src'
        make_tree(proj_a, {'alpha.py': 'A = 1\n'})
        make_tree(proj_b, {'beta.py': 'B = 2\n'})

        with contextlib.redirect_stdout(io.StringIO()):
            detect_drift(str(proj_a))

        buf_b = io.StringIO()
        with contextlib.redirect_stdout(buf_b):
            detect_drift(str(proj_b))
        out_b = buf_b.getvalue()

        self.assertIn('Initial snapshot', out_b,
                      f"project B read project A's state:\n{out_b}")
        self.assertNotIn('Removed', out_b,
                         f"project B saw phantom removals:\n{out_b}")

    def test_corrupt_state_file_does_not_crash(self):
        from drift_detect import detect_drift

        proj = self.home / 'proj' / 'src'
        make_tree(proj, {'a.py': 'A = 1\n'})

        with contextlib.redirect_stdout(io.StringIO()):
            detect_drift(str(proj))

        cache = self.home / '.cache' / 'code-navigate'
        state_files = list(cache.glob('*.json'))
        self.assertTrue(state_files, "expected a state file to be created")
        for f in state_files:
            f.write_text('{not json')

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                detect_drift(str(proj))
        except json.JSONDecodeError as e:
            self.fail(f"corrupt state crashed the run: {e}")


if __name__ == '__main__':
    unittest.main()
