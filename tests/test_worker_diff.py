"""Tests for scripts/worker_diff.py.

Each test builds a throwaway git repository in a temporary directory, commits a
base state, makes changes, and runs the script as a subprocess against it.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "worker_diff.py"


def section(output, title):
    """Return the lines of one output section, from its title line to the next blank line."""
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(title):
            out = [line]
            for rest in lines[i + 1:]:
                if not rest.strip():
                    break
                out.append(rest)
            return out
    raise AssertionError(f"section {title!r} not found in output:\n{output}")


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        self.env = dict(os.environ)
        # Isolate from any global/system git config.
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["GIT_CONFIG_NOSYSTEM"] = "1"
        self.git("init", "-q")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        done = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              text=True, env=self.env)
        if done.returncode != 0:
            raise RuntimeError(f"git {args} failed: {done.stderr}")
        return done.stdout.strip()

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message="commit"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def base(self, files):
        """Commit the given {path: text} as the base state and return its sha."""
        for rel, text in files.items():
            self.write(rel, text)
        return self.commit("base")

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
                              capture_output=True, text=True, env=self.env)

    def inventory(self, base, report=None):
        args = ["--base", base]
        if report is not None:
            report_path = Path(self._tmp.name) / "report.md"
            report_path.write_text(report, encoding="utf-8")
            args += ["--report", str(report_path)]
        done = self.run_script(*args)
        self.assertEqual(done.returncode, 0, f"stdout:\n{done.stdout}\nstderr:\n{done.stderr}")
        return done.stdout

    def added_hits(self, output):
        """Return [(path, lineno, label, text)] parsed from the ADDED LINES section."""
        hits = []
        for line in section(output, "ADDED LINES to read first:")[1:]:
            loc, _, rest = line.strip().partition("  ")
            path, _, lineno = loc.rpartition(":")
            label, _, text = rest.partition(": ")
            hits.append((path, int(lineno), label, text))
        return hits


class ChangedSectionTests(RepoTestCase):
    def test_modified_added_deleted_untracked_statuses(self):
        base = self.base({"keep.py": "a = 1\n", "gone.py": "b = 2\n"})
        self.write("new_committed.py", "c = 3\nd = 4\n")
        (self.repo / "gone.py").unlink()
        self.commit("worker commit")
        self.write("keep.py", "a = 10\n")  # uncommitted modification
        self.write("loose.py", "e = 5\nf = 6\ng = 7\n")  # untracked

        out = self.inventory(base)
        changed = section(out, "CHANGED against")
        self.assertEqual(changed[0], f"CHANGED against {base}: 4 file(s)")
        body = "\n".join(changed[1:])
        self.assertIn("  modified       keep.py  (+1 -1)  [code]", body)
        self.assertIn("  added          new_committed.py  (+2 -0)  [code]", body)
        self.assertIn("  deleted        gone.py  (+0 -1)  [code]", body)
        self.assertIn("  new, untracked loose.py  (+3 -0)  [code]", body)
        self.assertEqual(len(changed), 5)

    def test_no_changes(self):
        base = self.base({"a.py": "x = 1\n"})
        out = self.inventory(base)
        self.assertIn(f"CHANGED against {base}: 0 file(s)", out)
        self.assertIn("ADDED LINES to read first: 0", out)


class ReportTests(RepoTestCase):
    def test_unmentioned_files_listed_and_mentioned_not(self):
        base = self.base({"src/alpha.py": "x = 1\n", "src/beta.py": "y = 1\n"})
        self.write("src/alpha.py", "x = 2\n")
        self.write("src/beta.py", "y = 2\n")
        self.write("src/gamma.py", "z = 1\n")
        report = "I changed src/alpha.py to fix the bug, and also tweaked gamma.py.\n"

        out = self.inventory(base, report=report)
        unmentioned = section(out, "UNMENTIONED in the report:")
        self.assertEqual(unmentioned[0], "UNMENTIONED in the report: 1")
        self.assertEqual([line.strip() for line in unmentioned[1:]], ["src/beta.py"])

    def test_without_report_check_is_not_run(self):
        base = self.base({"a.py": "x = 1\n"})
        self.write("a.py", "x = 2\n")
        out = self.inventory(base)
        self.assertIn("UNMENTIONED in the report: not checked (no --report given)", out)


class AssertionCountTests(RepoTestCase):
    def test_fewer_assertions_flagged(self):
        base = self.base({"tests/test_calc.py": (
            "def test_add():\n"
            "    assert add(1, 2) == 3\n"
            "    assert add(0, 0) == 0\n"
            "    assert add(-1, 1) == 0\n")})
        self.write("tests/test_calc.py", (
            "def test_add():\n"
            "    assert add(1, 2) == 3\n"))

        out = self.inventory(base)
        guarded = section(out, "TESTS AND CHECK CONFIG touched:")
        self.assertEqual(guarded[0], "TESTS AND CHECK CONFIG touched: 1")
        self.assertEqual(guarded[1].strip(), "tests/test_calc.py: assertion lines removed 2, added 0"
                                             "  <- fewer assertions than before")

    def test_same_assertion_count_not_flagged(self):
        base = self.base({"tests/test_calc.py": "def test_add():\n    assert add(1, 2) == 3\n"})
        self.write("tests/test_calc.py", "def test_add():\n    assert add(2, 2) == 4\n")
        out = self.inventory(base)
        guarded = section(out, "TESTS AND CHECK CONFIG touched:")
        self.assertEqual(guarded[1].strip(), "tests/test_calc.py: assertion lines removed 1, added 1")
        self.assertNotIn("fewer assertions", out)


class AddedLineLabelTests(RepoTestCase):
    CODE = [
        ("test skipped or narrowed", "@pytest.mark.skip(reason='flaky')"),
        ("check silenced", "import os  # noqa"),
        ("unfinished marker", "# TODO: handle the empty case"),
        ("failure swallowed", "except:"),
        ("stand-in outside tests", "PRICE = 42  # hardcoded for now"),
    ]

    def test_each_label_fires_on_added_code_line(self):
        base = self.base({"app/module.py": "VALUE = 1\n"})
        added = [text for _, text in self.CODE]
        self.write("app/module.py", "VALUE = 1\n" + "\n".join(added) + "\n")

        out = self.inventory(base)
        hits = self.added_hits(out)
        for offset, (label, text) in enumerate(self.CODE):
            with self.subTest(label=label):
                self.assertIn(("app/module.py", 2 + offset, label, text), hits)

    def test_failure_swallowed_except_exception_pass(self):
        base = self.base({"app/io.py": "def f():\n    pass\n"})
        self.write("app/io.py", "def f():\n    try:\n        g()\n    except Exception: pass\n")
        hits = self.added_hits(self.inventory(base))
        self.assertIn(("app/io.py", 4, "failure swallowed", "except Exception: pass"), hits)

    def test_failure_swallowed_empty_js_catch(self):
        base = self.base({"web/app.js": "run();\n"})
        self.write("web/app.js", "try { run(); } catch (e) {}\n")
        labels = [h[2] for h in self.added_hits(self.inventory(base))]
        self.assertIn("failure swallowed", labels)

    def test_labels_fire_on_untracked_file(self):
        base = self.base({"a.py": "x = 1\n"})
        self.write("b.py", "y = 1\n# FIXME later\n")
        hits = self.added_hits(self.inventory(base))
        self.assertIn(("b.py", 2, "unfinished marker", "# FIXME later"), hits)

    def test_plain_line_raises_no_hits(self):
        base = self.base({"app/module.py": "VALUE = 1\n"})
        self.write("app/module.py", "VALUE = 2\n")
        out = self.inventory(base)
        self.assertIn("ADDED LINES to read first: 0", out)


class TestFileScopeTests(RepoTestCase):
    def test_code_only_labels_do_not_fire_in_test_file(self):
        base = self.base({"tests/test_thing.py": "def test_a():\n    assert True\n"})
        self.write("tests/test_thing.py", (
            "def test_a():\n"
            "    assert True\n"
            "def test_b():\n"
            "    fake = make_mock_client()\n"
            "    mock = object()\n"
            "    try:\n"
            "        boom()\n"
            "    except:\n"
            "        pass\n"
            "    try:\n"
            "        boom()\n"
            "    except Exception: pass\n"))
        hits = self.added_hits(self.inventory(base))
        labels = {h[2] for h in hits}
        self.assertNotIn("failure swallowed", labels)
        self.assertNotIn("stand-in outside tests", labels)

    def test_any_scope_labels_still_fire_in_test_file(self):
        base = self.base({"tests/test_thing.py": "def test_a():\n    assert True\n"})
        self.write("tests/test_thing.py", (
            "import pytest\n"
            "@pytest.mark.skip\n"
            "def test_a():\n"
            "    assert True\n"))
        hits = self.added_hits(self.inventory(base))
        self.assertIn(("tests/test_thing.py", 2, "test skipped or narrowed", "@pytest.mark.skip"), hits)


class ErrorTests(RepoTestCase):
    def test_unknown_base_exits_2(self):
        self.base({"a.py": "x = 1\n"})
        done = self.run_script("--base", "no-such-ref-xyz")
        self.assertEqual(done.returncode, 2, f"stdout:\n{done.stdout}\nstderr:\n{done.stderr}")
        self.assertIn("worker_diff: git", done.stderr)


if __name__ == "__main__":
    unittest.main()
