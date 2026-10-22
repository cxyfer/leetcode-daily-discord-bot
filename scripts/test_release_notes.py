"""Behavioral release-tool tests using isolated repositories and a local gh stub."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import release_notes as notes


class ReleaseNotesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        old_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, old_cwd)
        self.git("init", "-b", "main")
        self.git("config", "user.email", "release@example.test")
        self.git("config", "user.name", "Release Test")
        self.identity("0.1.0")
        self.first = self.commit("initial repository")
        self.output = self.root / "notes.md"
        self.pulls = {}
        self.calls = []
        original = notes.run

        def run(*args):
            if args[0] != "gh":
                return original(*args)
            self.calls.append(args)
            number = int(args[-1].rsplit("/", 1)[1])
            if number not in self.pulls:
                raise notes.ReleaseError(f"gh failed: pull #{number} is unavailable")
            return json.dumps(self.pulls[number])

        self.patch = patch.object(notes, "run", side_effect=run)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def git(self, *args):
        return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout.strip()

    def cli(self, *args, env=None):
        return subprocess.run(
            [
                sys.executable,
                "-S",
                str(Path(notes.__file__).resolve()),
                *map(str, args),
            ],
            text=True,
            capture_output=True,
            env=env,
        )

    def identity(self, version):
        (self.root / "pyproject.toml").write_text(
            f'[project]\nname = "example"\nversion = "{version}"\n', encoding="utf-8"
        )
        (self.root / "uv.lock").write_text(
            'version = 1\n\n[[package]]\nname = "dependency"\nversion = "9.0.0"\n'
            f'\n[[package]]\nname = "example"\nversion = "{version}"\nsource = {{ virtual = "." }}\n',
            encoding="utf-8",
        )

    def commit(self, subject):
        self.git("add", "pyproject.toml", "uv.lock")
        self.git("commit", "--allow-empty", "-m", subject)
        return self.git("rev-parse", "HEAD")

    def tag(self, tag):
        self.git("tag", tag)

    def pull(self, number, author="alice", title=None):
        self.pulls[number] = {
            "title": title or f"Change {number}",
            "user": {"login": author},
            "html_url": f"https://github.com/owner/example/pull/{number}",
        }

    def generate(self, tag, previous=None):
        notes.generate(tag, "owner/example", self.output, previous)
        return self.output.read_text(encoding="utf-8")

    def test_strict_numeric_semver_order(self):
        tags = ["v1.10.0", "v1.2.0", "v1.10.0-rc.10", "v1.10.0-rc.2", "v1.10.0-rc.0"]
        self.assertEqual(
            sorted(tags, key=notes.version),
            [tags[1], tags[4], tags[3], tags[2], tags[0]],
        )
        for tag in (
            "1.2.0",
            "v01.2.0",
            "v1.02.0",
            "v1.2.00",
            "v1.2.0-rc.01",
            "v1.2.0-beta.1",
            "v1.2.0+build",
            "nightly",
            "v1.2.0\n",
            "v1.2.١",
        ):
            with self.subTest(tag=tag), self.assertRaises(notes.ReleaseError):
                notes.version(tag)

    def test_metadata_validates_and_appends_outputs_without_github(self):
        self.tag("v0.1.0")
        self.identity("0.2.0rc0")
        self.commit("prepare candidate")
        self.tag("v0.2.0-rc.0")
        self.tag("nightly")
        output = self.root / "github-output"
        output.write_text("existing=value\n", encoding="utf-8")
        notes.metadata("v0.2.0-rc.0", output)
        self.assertEqual(
            output.read_text(),
            "existing=value\ntag=v0.2.0-rc.0\nversion=0.2.0-rc.0\nprerelease=true\nprevious_tag=v0.1.0\nis_latest=true\nis_latest_stable=false\n",
        )
        self.assertEqual(self.calls, [])

    def test_metadata_separates_latest_release_and_latest_stable(self):
        self.tag("v0.1.0")
        self.tag("v0.2.0-rc.10")
        self.tag("v0.2.0-rc.2")
        notes.metadata("v0.1.0", self.output)
        text = self.output.read_text()
        self.assertIn("is_latest=false\nis_latest_stable=true", text)
        self.assertIn("previous_tag=\n", text)

    def test_metadata_rejects_missing_tag_head_manifest_and_lock(self):
        with self.assertRaises(notes.ReleaseError):
            notes.metadata("v0.1.0", self.output)
        self.tag("v0.1.0")
        self.commit("later commit")
        with self.assertRaisesRegex(notes.ReleaseError, "HEAD"):
            notes.metadata("v0.1.0", self.output)
        self.git("checkout", "--detach", "v0.1.0")
        self.identity("0.2.0")
        with self.assertRaisesRegex(notes.ReleaseError, "pyproject.toml"):
            notes.metadata("v0.1.0", self.output)
        self.identity("0.1.0")
        (self.root / "uv.lock").write_text('[[package]]\nname = "example"\nversion = "0.2.0"\n', encoding="utf-8")
        with self.assertRaisesRegex(notes.ReleaseError, "uv.lock"):
            notes.metadata("v0.1.0", self.output)
        self.assertFalse(self.output.exists())

    def test_metadata_matches_python_rc_version_and_uv_lock(self):
        self.identity("0.2.0rc10")
        self.commit("prepare Python release candidate")
        self.tag("v0.2.0-rc.10")
        notes.metadata("v0.2.0-rc.10", self.output)
        self.assertIn("tag=v0.2.0-rc.10\nversion=0.2.0-rc.10\nprerelease=true\n", self.output.read_text())
        self.assertIn("is_latest_stable=false\n", self.output.read_text())
        self.output.unlink()
        self.identity("0.2.0-rc.10")
        with self.assertRaisesRegex(notes.ReleaseError, "expected Python version 0.2.0rc10"):
            notes.metadata("v0.2.0-rc.10", self.output)
        self.identity("0.2.0rc10")
        lock = self.root / "uv.lock"
        lock.write_text(lock.read_text().replace('version = "0.2.0rc10"', 'version = "0.2.0rc2"'))
        with self.assertRaisesRegex(notes.ReleaseError, "uv.lock"):
            notes.metadata("v0.2.0-rc.10", self.output)
        self.assertFalse(self.output.exists())

    def test_metadata_rejects_missing_project_and_missing_or_duplicate_locked_package(self):
        self.tag("v0.1.0")
        manifest = self.root / "pyproject.toml"
        manifest.write_text('[tool.example]\nversion = "0.1.0"\n')
        with self.assertRaisesRegex(notes.ReleaseError, "pyproject.toml"):
            notes.metadata("v0.1.0", self.output)
        self.identity("0.1.0")
        lock = self.root / "uv.lock"
        lock.write_text('version = 1\n[[package]]\nname = "another"\nversion = "0.1.0"\n')
        with self.assertRaisesRegex(notes.ReleaseError, "uv.lock"):
            notes.metadata("v0.1.0", self.output)
        self.identity("0.1.0")
        with lock.open("a") as handle:
            handle.write('\n[[package]]\nname = "example"\nversion = "0.1.0"\n')
        with self.assertRaisesRegex(notes.ReleaseError, "uv.lock"):
            notes.metadata("v0.1.0", self.output)
        self.assertFalse(self.output.exists())

    def test_stable_and_rc_baselines_are_lower_reachable_versions(self):
        self.tag("v0.1.0")
        self.commit("candidate two")
        self.tag("v0.2.0-rc.2")
        self.commit("candidate ten")
        self.tag("v0.2.0-rc.10")
        self.tag("nightly")
        self.commit("stable release")
        self.tag("v0.2.0")
        self.tag("v9.0.0")
        self.git("checkout", "-b", "unrelated", self.first)
        self.commit("side release")
        self.tag("v0.1.9")
        self.assertEqual(notes.previous_tag("v0.2.0"), "v0.1.0")
        self.assertEqual(notes.previous_tag("v0.2.0-rc.10"), "v0.2.0-rc.2")
        self.assertEqual(notes.previous_tag("v0.2.0-rc.2"), "v0.1.0")

    def test_explicit_baseline_rejects_self_newer_unrelated_and_missing(self):
        self.tag("v0.1.0")
        self.commit("new release")
        self.tag("v0.2.0")
        self.tag("v0.3.0")
        self.git("checkout", "-b", "side", self.first)
        self.commit("unrelated")
        self.tag("v0.1.9")
        for tag in ("v0.2.0", "v0.3.0", "v0.1.9", "v0.0.1", "nightly"):
            with self.subTest(tag=tag), self.assertRaises(notes.ReleaseError):
                self.generate("v0.2.0", tag)
        self.assertIn("compare/v0.1.0...v0.2.0", self.generate("v0.2.0", "v0.1.0"))

    def test_first_release_direct_commit_and_historical_checkout(self):
        direct = self.commit("fix: handle [input] carefully")
        self.tag("v0.1.0")
        self.commit("must not appear")
        text = self.generate("v0.1.0")
        self.assertTrue(text.startswith("> [!IMPORTANT]\n"))
        self.assertIn("ghcr.io/owner/example:v0.1.0", text)
        self.assertIn(">\n> TODO: Summarize", text)
        self.assertIn(">\n> TODO: Describe upgrade steps", text)
        self.assertIn(f"[{direct[:7]}](https://github.com/owner/example/commit/{direct})", text)
        self.assertIn(r"fix: handle \[input\] carefully", text)
        self.assertNotIn("must not appear", text)
        self.assertIn("/commits/v0.1.0", text)
        self.assertNotIn("## New Contributors", text)
        self.assertEqual(self.calls, [])

    def test_pr_deduplication_merge_subject_and_historical_contributors(self):
        self.pull(1, "alice")
        self.pull(2, "alice", "Fix [input]\nformatting")
        self.pull(3, "bob")
        self.pull(4, "bob")
        self.commit("old change (#1)")
        self.tag("v0.1.0")
        self.git("checkout", "-b", "feature")
        self.commit("branch detail must not appear")
        self.git("checkout", "main")
        self.git(
            "merge",
            "--no-ff",
            "feature",
            "-m",
            "Merge pull request #2 from owner/feature",
        )
        self.commit("rebase detail (#3)")
        self.commit("another rebase detail (#3)")
        self.commit("followup (#4)")
        self.commit("🔖 release: v0.2.0")
        self.tag("v0.2.0")
        text = self.generate("v0.2.0")
        self.assertNotIn("branch detail", text)
        self.assertNotIn("🔖 release", text)
        self.assertIn(r"Fix \[input\] formatting by [@alice]", text)
        changes, contributors = text.split("## New Contributors")
        self.assertEqual(changes.count("in [#3]"), 1)
        self.assertNotIn("[@alice]", contributors)
        self.assertEqual(contributors.count("[@bob]"), 1)
        self.assertIn("in [#3]", contributors)
        self.assertEqual(len(self.calls), 4)

    def test_first_release_contributors_and_rc_warning(self):
        self.pull(2)
        self.commit("improve feature (#2)")
        self.tag("v0.2.0-rc.1")
        text = self.generate("v0.2.0-rc.1")
        self.assertIn("release candidate intended for testing", text)
        self.assertIn("## New Contributors", text)
        self.assertIn("ghcr.io/owner/example:v0.2.0-rc.1", text)

    def test_no_new_contributors_omits_section(self):
        self.pull(1)
        self.pull(2)
        self.commit("earlier (#1)")
        self.tag("v0.1.0")
        self.commit("current (#2)")
        self.tag("v0.2.0")
        self.assertNotIn("## New Contributors", self.generate("v0.2.0"))

    def test_shallow_history_omits_unprovable_new_contributors(self):
        self.pull(2)
        self.commit("current (#2)")
        self.tag("v0.1.0")
        (self.root / ".git" / "shallow").write_text(self.first + "\n", encoding="utf-8")
        self.assertNotIn("## New Contributors", self.generate("v0.1.0"))

    def test_api_failure_or_malformed_metadata_never_creates_partial_file(self):
        self.pull(1)
        self.commit("first (#1)")
        self.commit("second (#2)")
        self.tag("v0.1.0")
        with self.assertRaisesRegex(notes.ReleaseError, "pull #2"):
            self.generate("v0.1.0")
        self.assertFalse(self.output.exists())
        self.pulls[2] = {"title": "broken"}
        with self.assertRaisesRegex(notes.ReleaseError, "Invalid GitHub metadata"):
            self.generate("v0.1.0")
        self.assertFalse(self.output.exists())

    def test_earlier_author_api_failure_is_fatal(self):
        self.commit("earlier (#1)")
        self.tag("v0.1.0")
        self.pull(2)
        self.commit("current (#2)")
        self.tag("v0.2.0")
        with self.assertRaises(notes.ReleaseError):
            self.generate("v0.2.0")
        self.assertFalse(self.output.exists())

    def test_existing_notes_are_preserved_without_api_calls(self):
        self.tag("v0.1.0")
        self.output.write_text("manual notes", encoding="utf-8")
        with self.assertRaisesRegex(notes.ReleaseError, "Refusing to overwrite"):
            self.generate("v0.1.0")
        self.assertEqual(self.output.read_text(), "manual notes")
        self.assertEqual(self.calls, [])

    def edited_notes(self):
        self.tag("v0.1.0")
        draft = self.generate("v0.1.0")
        with self.assertRaisesRegex(notes.ReleaseError, "TODOs"):
            notes.check(self.output)
        return draft.replace("TODO: ", "")

    def test_check_accepts_edited_notes_and_markdown_exceptions(self):
        text = (
            self.edited_notes()
            + "\n<!--\na wrapped comment\nis allowed\n-->\n\n````text\n<!--\nwrapped code\nis allowed\n"
            "```\nmore wrapped\ncode is allowed\n````\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
        )
        self.output.write_text(text, encoding="utf-8")
        notes.check(self.output)

    def test_check_rejects_missing_sections_placeholders_and_wrapping(self):
        valid = self.edited_notes()
        variants = [
            valid.replace("> [!IMPORTANT]", "> Note"),
            valid.replace("## Highlights", "## Other"),
            valid.replace("## What's Changed", "## Changes"),
            valid.replace("**Full Changelog**", "Changelog"),
            valid + "\nTBD\n",
            valid + "\n{{summary}}\n",
            valid + "\n<insert summary>\n",
            valid + "\nA wrapped paragraph\ncontinues here.\n",
            valid + "\n- A wrapped bullet\n  continues here.\n",
            valid + "\n> A wrapped quotation\n> continues here.\n",
        ]
        for text in variants:
            with self.subTest(text=text[-100:]), self.assertRaises(notes.ReleaseError):
                self.output.write_text(text, encoding="utf-8")
                notes.check(self.output)

    def test_cli_requires_repo_and_reports_validation_errors(self):
        missing = self.cli("generate", "v0.1.0", "--output", self.output)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--repo", missing.stderr)
        invalid = self.cli("metadata", "nightly", "--github-output", self.output)
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("Invalid release tag", invalid.stderr)

    def test_cli_uses_local_gh_stub_for_generation_and_checks_edited_notes(self):
        self.commit("feature (#7)")
        self.tag("v0.1.0")
        self.pull(7)
        bindir = self.root / "bin"
        bindir.mkdir()
        stub = bindir / "gh"
        stub.write_text(
            f"#!{sys.executable}\nimport sys\n"
            "assert sys.argv[1:] == ['api', 'repos/owner/example/pulls/7']\n"
            f"print({json.dumps(self.pulls[7])!r})\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}")
        metadata = self.cli("metadata", "v0.1.0", "--github-output", self.root / "outputs", env=env)
        self.assertEqual(metadata.returncode, 0, metadata.stderr)
        generated = self.cli(
            "generate",
            "v0.1.0",
            "--repo",
            "owner/example",
            "--output",
            self.output,
            env=env,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        self.output.write_text(self.output.read_text().replace("TODO: ", ""), encoding="utf-8")
        checked = self.cli("check", self.output, env=env)
        self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    unittest.main()
