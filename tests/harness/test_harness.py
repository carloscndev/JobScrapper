"""Unit tests for the dependency-free multi-agent harness."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_SCRIPT = REPO_ROOT / "scripts" / "harness.py"
CHECK_SKILLS_SCRIPT = REPO_ROOT / "scripts" / "check-skills.sh"
SPEC = importlib.util.spec_from_file_location("job_scrapper_harness", HARNESS_SCRIPT)
assert SPEC and SPEC.loader
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


CONFIG = {
    "schema_version": 1,
    "allowed_states": [
        "pending", "coding", "testing", "review", "rework", "approved",
        "committed", "blocked",
    ],
    "roles": ["coder", "tester", "reviewer"],
    "commit_types": [
        "feat", "fix", "test", "docs", "refactor", "chore", "build", "ci", "perf",
    ],
    "gate_commands": [],
    "json_gate_files": [],
    "development_log": "docs/DEVELOPMENT_LOG.md",
    "changelog": "CHANGELOG.md",
}

BACKLOG = {
    "schema_version": 1,
    "tasks": [
        {
            "id": "ONE",
            "title": "First task",
            "status": "pending",
            "depends_on": [],
            "commit": "feat(harness): implement first task",
            "allowed_paths": ["tracked.txt", "docs/DEVELOPMENT_LOG.md", "CHANGELOG.md"],
        },
        {
            "id": "TWO",
            "title": "Dependent task",
            "status": "blocked",
            "depends_on": ["ONE"],
            "commit": "test(harness): cover dependent task",
            "allowed_paths": ["tracked.txt", "docs/DEVELOPMENT_LOG.md", "CHANGELOG.md"],
        },
    ],
}

CURRENT = {
    "schema_version": 1,
    "active": False,
    "task_id": None,
    "state": None,
    "attempt": 0,
    "evidence": {},
    "rejections": [],
    "commit": None,
}


class HarnessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.harness_dir = self.root / ".harness"
        self.harness_dir.mkdir()
        (self.root / "docs").mkdir()
        (self.root / "docs" / "DEVELOPMENT_LOG.md").write_text("# Log\n\nONE\n", encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\nONE\n", encoding="utf-8")
        self.config_path = self.harness_dir / "config.json"
        self.backlog_path = self.harness_dir / "backlog.json"
        self.current_path = self.harness_dir / "current-task.json"
        self._write(self.config_path, CONFIG)
        self._write(self.backlog_path, BACKLOG)
        self._write(self.current_path, CURRENT)
        self.git("init", "-q")
        self.git("config", "user.email", "tester@example.invalid")
        self.git("config", "user.name", "Harness Tester")
        (self.root / "tracked.txt").write_text("initial\n", encoding="utf-8")
        (self.root / "protected.txt").write_text("outside task scope\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "chore(test): initialize fixture")
        self.paths = patch.multiple(
            harness,
            ROOT=self.root,
            HARNESS=self.harness_dir,
            CONFIG_PATH=self.config_path,
            BACKLOG_PATH=self.backlog_path,
            CURRENT_PATH=self.current_path,
        )
        self.paths.start()
        self.addCleanup(self.paths.stop)

    @staticmethod
    def _write(path: Path, value: dict) -> None:
        path.write_text(json.dumps(deepcopy(value)), encoding="utf-8")

    @staticmethod
    def args(**values: object) -> argparse.Namespace:
        return argparse.Namespace(**values)

    def backlog(self) -> dict:
        return json.loads(self.backlog_path.read_text(encoding="utf-8"))

    def current(self) -> dict:
        return json.loads(self.current_path.read_text(encoding="utf-8"))

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments], cwd=self.root, text=True, capture_output=True, check=True
        )

    def trace_section(self, attempt: int = 1) -> str:
        return (
            f"### ONE — Attempt {attempt}\n"
            "- Skills: none\n"
            "- Files: tracked.txt\n"
            "- Commands: python3 -m unittest\n"
            "- Tester: PASS\n"
            "- Reviewer: APPROVED\n"
            "- Risks: none\n"
            "- Commit subject: feat(harness): implement first task\n"
            "- Commit hash: pending\n"
        )

    def stage_task_change(self, *, attempt: int = 1, stage_documents: bool = True) -> None:
        (self.root / "tracked.txt").write_text("task change\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        section = self.trace_section(attempt)
        (self.root / "docs" / "DEVELOPMENT_LOG.md").write_text(section, encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text(section, encoding="utf-8")
        if stage_documents:
            self.git("add", "docs/DEVELOPMENT_LOG.md", "CHANGELOG.md")

    def start(self, task_id: str = "ONE") -> None:
        harness.command_start(self.args(task_id=task_id))

    def record(self, role: str, result: str = "pass", evidence: str | None = None) -> None:
        harness.command_record(
            self.args(role=role, result=result, evidence=evidence or f"{role} evidence")
        )

    def reach_review(self) -> None:
        self.start()
        self.record("coder")
        harness.command_handoff(self.args(role="tester"))
        self.record("tester")
        harness.command_handoff(self.args(role="reviewer"))

    def approve(self) -> None:
        self.reach_review()
        self.record("reviewer")
        harness.command_approve(self.args())

    def test_happy_path_enforces_ordered_gates_and_becomes_commit_ready(self) -> None:
        self.approve()
        self.stage_task_change()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            harness.command_commit_ready(self.args())
        self.assertTrue(output.getvalue().strip().endswith("feat(harness): implement first task"))
        self.assertIn("gate passed: staged scope", output.getvalue())
        self.assertIn("gate passed: current-attempt traceability", output.getvalue())
        self.assertEqual("approved", self.current()["state"])

    def test_commit_ready_requires_staged_scope(self) -> None:
        self.approve()
        with self.assertRaisesRegex(harness.HarnessError, "Staging area is empty"):
            harness.command_commit_ready(self.args())

    def test_commit_ready_requires_task_traceability(self) -> None:
        self.approve()
        self.stage_task_change()
        (self.root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        self.git("add", "CHANGELOG.md")
        with self.assertRaisesRegex(harness.HarnessError, "Missing structured section.*CHANGELOG.md"):
            harness.command_commit_ready(self.args())

    def test_commit_ready_rejects_traceability_documents_not_staged(self) -> None:
        self.approve()
        self.stage_task_change(stage_documents=False)
        with self.assertRaisesRegex(harness.HarnessError, "Required traceability document is not staged"):
            harness.command_commit_ready(self.args())

    def test_commit_ready_rejects_old_attempt_section(self) -> None:
        self.reach_review()
        harness.command_reject(self.args(reason="retry required"))
        self.record("coder")
        harness.command_handoff(self.args(role="tester"))
        self.record("tester")
        harness.command_handoff(self.args(role="reviewer"))
        self.record("reviewer")
        harness.command_approve(self.args())
        self.stage_task_change(attempt=1)
        with self.assertRaisesRegex(harness.HarnessError, "Missing structured section for ONE attempt 2"):
            harness.command_commit_ready(self.args())

    def test_commit_ready_rejects_staged_file_outside_allowed_paths(self) -> None:
        self.approve()
        self.stage_task_change()
        (self.root / "outside.txt").write_text("scope expansion\n", encoding="utf-8")
        self.git("add", "outside.txt")
        with self.assertRaisesRegex(harness.HarnessError, "Staged files outside task scope: outside.txt"):
            harness.command_commit_ready(self.args())

    def test_commit_ready_reads_traceability_from_index_not_working_tree(self) -> None:
        self.approve()
        self.stage_task_change()
        invalid = "### ONE — Attempt 1\n- Tester: FAIL\n"
        log = self.root / "docs" / "DEVELOPMENT_LOG.md"
        log.write_text(invalid, encoding="utf-8")
        self.git("add", "docs/DEVELOPMENT_LOG.md")
        # Restore a valid working-tree copy without staging it. The index must
        # remain authoritative for a commit-readiness decision.
        log.write_text(self.trace_section(), encoding="utf-8")
        with self.assertRaisesRegex(harness.HarnessError, "Incomplete ONE attempt 1 section"):
            harness.command_commit_ready(self.args())

    def test_commit_ready_rejects_staged_deletion_outside_allowed_paths(self) -> None:
        self.approve()
        self.stage_task_change()
        (self.root / "protected.txt").unlink()
        self.git("add", "-u", "protected.txt")
        with self.assertRaisesRegex(harness.HarnessError, "Staged files outside task scope: protected.txt"):
            harness.command_commit_ready(self.args())

    def test_secret_scanner_ignores_its_regex_definition_and_innocent_text(self) -> None:
        self.approve()
        self.stage_task_change()
        innocent = (
            "task-requested\n"
            "    re.compile(r\"^\\+.*(?:api[_-]?key|secret|token|password)\")\n"
        )
        (self.root / "tracked.txt").write_text(innocent, encoding="utf-8")
        self.git("add", "tracked.txt")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            harness.command_commit_ready(self.args())
        self.assertIn("gate passed: staged scope", output.getvalue())

    def test_secret_scanner_rejects_real_staged_credentials(self) -> None:
        self.approve()
        self.stage_task_change()
        names = ("to" + "ken", "api" + "_key", "sec" + "ret", "pass" + "word")
        value = "abcdefgh" + "12345678"
        credentials = "".join(f'{name} = "{value}"\n' for name in names)
        (self.root / "tracked.txt").write_text(credentials, encoding="utf-8")
        self.git("add", "tracked.txt")
        with self.assertRaisesRegex(harness.HarnessError, "Potential secret detected"):
            harness.command_commit_ready(self.args())

    def test_invalid_handoffs_and_wrong_role_evidence_are_rejected(self) -> None:
        self.start()
        with self.assertRaisesRegex(harness.HarnessError, "Passing coder evidence"):
            harness.command_handoff(self.args(role="tester"))
        with self.assertRaisesRegex(harness.HarnessError, "expects evidence from coder"):
            self.record("tester")
        self.record("coder")
        with self.assertRaisesRegex(harness.HarnessError, "Reviewer handoff requires testing"):
            harness.command_handoff(self.args(role="reviewer"))

    def test_only_one_task_can_be_active(self) -> None:
        self.start()
        with self.assertRaisesRegex(harness.HarnessError, "already active"):
            harness.command_start(self.args(task_id="TWO"))
        backlog = self.backlog()
        backlog["tasks"][1]["status"] = "coding"
        self._write(self.backlog_path, backlog)
        config, backlog, current = harness.load()
        self.assertTrue(any("Multiple active" in error for error in harness.validate_data(config, backlog, current)))

    def test_tester_failure_returns_to_coder_and_increments_attempt(self) -> None:
        self.start()
        self.record("coder")
        harness.command_handoff(self.args(role="tester"))
        self.record("tester", result="fail", evidence="unit test failed")
        current = self.current()
        self.assertEqual("rework", current["state"])
        self.assertEqual(2, current["attempt"])
        self.assertEqual({}, current["evidence"])
        self.assertEqual("tester", current["rejections"][0]["by"])

    def test_reviewer_rejection_requires_full_gate_cycle_again(self) -> None:
        self.reach_review()
        harness.command_reject(self.args(reason="missing edge case"))
        self.assertEqual("rework", self.current()["state"])
        with self.assertRaisesRegex(harness.HarnessError, "Approval requires review"):
            harness.command_approve(self.args())
        self.record("coder", evidence="edge case fixed")
        harness.command_handoff(self.args(role="tester"))
        self.record("tester", evidence="suite passes")
        harness.command_handoff(self.args(role="reviewer"))
        self.record("reviewer", evidence="APPROVED")
        harness.command_approve(self.args())
        self.assertEqual(2, self.current()["attempt"])

    def test_approval_and_commit_ready_require_reviewer_pass(self) -> None:
        self.reach_review()
        with self.assertRaisesRegex(harness.HarnessError, "Passing reviewer evidence"):
            harness.command_approve(self.args())
        with self.assertRaisesRegex(harness.HarnessError, "Task is not approved"):
            harness.command_commit_ready(self.args())

    def test_complete_rejects_bad_hash_then_commits_and_unblocks_dependency(self) -> None:
        self.approve()
        with self.assertRaisesRegex(harness.HarnessError, "7-40 character"):
            harness.command_complete(self.args(commit="not-a-hash"))
        with self.assertRaisesRegex(harness.HarnessError, "must exist"):
            harness.command_complete(self.args(commit="deadbee"))
        self.stage_task_change()
        self.git("commit", "-qm", "feat(harness): implement first task")
        head = self.git("rev-parse", "HEAD").stdout.strip()
        harness.command_complete(self.args(commit=head))
        tasks = {task["id"]: task for task in self.backlog()["tasks"]}
        self.assertEqual("committed", tasks["ONE"]["status"])
        self.assertEqual(head, tasks["ONE"]["commit_hash"])
        self.assertEqual("pending", tasks["TWO"]["status"])
        self.assertFalse(self.current()["active"])

    def test_dependency_must_be_committed_before_start(self) -> None:
        backlog = self.backlog()
        backlog["tasks"][1]["status"] = "pending"
        self._write(self.backlog_path, backlog)
        with self.assertRaisesRegex(harness.HarnessError, "Uncommitted dependencies: ONE"):
            harness.command_start(self.args(task_id="TWO"))

    def test_validate_rejects_unknown_dependencies_and_bad_commits(self) -> None:
        backlog = self.backlog()
        backlog["tasks"][0]["commit"] = "unknown(scope): invalid."
        backlog["tasks"][1]["depends_on"] = ["MISSING"]
        errors = harness.validate_data(CONFIG, backlog, CURRENT)
        self.assertTrue(any("invalid Conventional Commit" in error for error in errors))
        self.assertTrue(any("unknown dependency MISSING" in error for error in errors))

    def test_validate_rejects_self_dependency_and_dependency_cycles(self) -> None:
        backlog = deepcopy(BACKLOG)
        backlog["tasks"][0]["depends_on"] = ["ONE"]
        backlog["tasks"][1]["depends_on"] = ["ONE"]
        errors = harness.validate_data(CONFIG, backlog, CURRENT)
        self.assertTrue(any("cannot depend on itself" in error for error in errors))

        backlog = deepcopy(BACKLOG)
        backlog["tasks"][0]["depends_on"] = ["TWO"]
        backlog["tasks"][1]["depends_on"] = ["ONE"]
        errors = harness.validate_data(CONFIG, backlog, CURRENT)
        self.assertTrue(any("Dependency cycle detected" in error for error in errors))

    def test_validate_rejects_inactive_current_inconsistent_with_backlog(self) -> None:
        backlog = deepcopy(BACKLOG)
        backlog["tasks"][0]["status"] = "coding"
        current = deepcopy(CURRENT)
        errors = harness.validate_data(CONFIG, backlog, current)
        self.assertTrue(any("active task but current-task is inactive" in error for error in errors))

        backlog = deepcopy(BACKLOG)
        current = deepcopy(CURRENT)
        current["task_id"] = "ONE"
        errors = harness.validate_data(CONFIG, backlog, current)
        self.assertTrue(any("Inactive current-task must not identify a task" in error for error in errors))

    def test_record_rejects_blank_evidence(self) -> None:
        self.start()
        with self.assertRaisesRegex(harness.HarnessError, "Evidence must not be empty"):
            harness.command_record(self.args(role="coder", result="pass", evidence="   "))

    def test_reject_rejects_blank_reason(self) -> None:
        self.reach_review()
        with self.assertRaisesRegex(harness.HarnessError, "Rejection reason must not be empty"):
            harness.command_reject(self.args(reason="\t  "))

    def test_complete_requires_exact_head_hash_and_subject(self) -> None:
        self.approve()
        self.stage_task_change()
        self.git("commit", "-qm", "fix(harness): wrong subject")
        head = self.git("rev-parse", "HEAD").stdout.strip()
        with self.assertRaisesRegex(harness.HarnessError, "Commit subject does not match"):
            harness.command_complete(self.args(commit=head))
        previous = self.git("rev-parse", "HEAD^").stdout.strip()
        with self.assertRaisesRegex(harness.HarnessError, "Commit must be the current HEAD"):
            harness.command_complete(self.args(commit=previous))

    def test_conventional_commit_pattern_accepts_configured_examples(self) -> None:
        for message in (
            "feat(api): add health endpoint",
            "fix: handle empty response",
            "refactor(parser)!: remove legacy format",
        ):
            backlog = deepcopy(BACKLOG)
            backlog["tasks"][0]["commit"] = message
            self.assertEqual([], harness.validate_data(CONFIG, backlog, CURRENT), message)

    def test_status_is_read_only(self) -> None:
        before_backlog = self.backlog_path.read_bytes()
        before_current = self.current_path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            harness.command_status(self.args())
        self.assertEqual(before_backlog, self.backlog_path.read_bytes())
        self.assertEqual(before_current, self.current_path.read_bytes())

    def test_status_reports_active_stage_and_evidence_without_mutating_state(self) -> None:
        self.start()
        self.record("coder", evidence="implementation complete")
        before_backlog = self.backlog_path.read_bytes()
        before_current = self.current_path.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            harness.command_status(self.args())
        self.assertIn("ONE: state=coding attempt=1 evidence=coder", output.getvalue())
        self.assertEqual(before_backlog, self.backlog_path.read_bytes())
        self.assertEqual(before_current, self.current_path.read_bytes())

    def test_invalid_transition_cannot_skip_tester_gate(self) -> None:
        self.start()
        self.record("coder")
        with self.assertRaisesRegex(harness.HarnessError, "Reviewer handoff requires testing"):
            harness.command_handoff(self.args(role="reviewer"))
        self.assertEqual("coding", self.current()["state"])


class SkillVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.skills = self.root / "skills"
        (self.repo / "scripts").mkdir(parents=True)
        (self.repo / ".harness").mkdir()
        (self.repo / "scripts" / "check-skills.sh").write_bytes(CHECK_SKILLS_SCRIPT.read_bytes())
        os.chmod(self.repo / "scripts" / "check-skills.sh", 0o755)

    def write_manifest(self, checksum: str) -> None:
        manifest = {
            "schema_version": 1,
            "allowed_roles": ["coder", "tester", "reviewer", "coordinator"],
            "skills": [{
                "name": "local-skill",
                "source": "https://github.com/example/skills",
                "revision": "1" * 40,
                "roles": ["tester"],
                "allowlist": ["tester"],
                "skill_file_sha256": checksum,
                "purpose": "Testing guidance",
                "risk": "normal",
                "risk_detail": "Local-only test guidance.",
            }],
        }
        (self.repo / ".harness" / "skills.json").write_text(json.dumps(manifest), encoding="utf-8")

    def run_check(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["AGENT_SKILLS_HOME"] = str(self.skills)
        return subprocess.run(
            [str(self.repo / "scripts" / "check-skills.sh"), *arguments],
            cwd=self.repo,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_skill_check_succeeds_with_matching_local_checksum(self) -> None:
        skill_file = self.skills / "local-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("# Local skill\n", encoding="utf-8")
        self.write_manifest(hashlib.sha256(skill_file.read_bytes()).hexdigest())
        first = self.run_check()
        second = self.run_check()
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertIn("Verified 1 approved skills", first.stdout)

    def test_skill_check_detects_missing_skill(self) -> None:
        self.write_manifest("0" * 64)
        result = self.run_check()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing: local-skill", result.stderr)

    def test_skill_check_detects_checksum_change(self) -> None:
        skill_file = self.skills / "local-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("tampered", encoding="utf-8")
        self.write_manifest("0" * 64)
        result = self.run_check()
        self.assertEqual(1, result.returncode)
        self.assertIn("checksum mismatch: local-skill", result.stderr)

    def test_skill_check_enforces_allowlist_and_role(self) -> None:
        skill_file = self.skills / "local-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("approved", encoding="utf-8")
        self.write_manifest(hashlib.sha256(skill_file.read_bytes()).hexdigest())
        allowed = self.run_check("--skill", "local-skill", "--role", "tester")
        unmanaged = self.run_check("--skill", "unknown", "--role", "tester")
        unauthorized = self.run_check("--skill", "local-skill", "--role", "coder")
        self.assertEqual(0, allowed.returncode, allowed.stderr)
        self.assertIn("unmanaged skill: unknown", unmanaged.stderr)
        self.assertIn("role coder is not authorized", unauthorized.stderr)

    def test_project_manifest_uses_immutable_revision_pins(self) -> None:
        manifest = json.loads((REPO_ROOT / ".harness" / "skills.json").read_text(encoding="utf-8"))
        self.assertRegex(manifest["reviewed_on"], r"^\d{4}-\d{2}-\d{2}$")
        for skill in manifest["skills"]:
            with self.subTest(skill=skill["name"]):
                self.assertRegex(skill["revision"], r"^[0-9a-f]{40}$")
                self.assertRegex(skill["skill_file_sha256"], r"^[0-9a-f]{64}$")

    def test_install_script_uses_manifest_revisions_and_is_idempotent_with_mock_npx(self) -> None:
        """The installer must be reproducible without contacting the network in tests."""
        install = self.repo / "scripts" / "install-skills.sh"
        install.write_bytes((REPO_ROOT / "scripts" / "install-skills.sh").read_bytes())
        os.chmod(install, 0o755)
        contents = "# approved skill\n"
        checksum = hashlib.sha256(contents.encode()).hexdigest()
        manifest = {
            "schema_version": 1,
            "allowed_roles": ["coder", "tester", "reviewer", "coordinator"],
            "skills": [
                {
                    "name": "local-skill",
                    "source": "https://github.com/example/skills",
                    "revision": "a" * 40,
                    "skill_file_sha256": checksum,
                    "roles": ["tester"],
                    "allowlist": ["tester"],
                    "purpose": "Testing guidance",
                    "risk": "normal",
                    "risk_detail": "Local-only test guidance.",
                }
            ],
        }
        (self.repo / ".harness" / "skills.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        calls = self.root / "npx-calls.log"
        fake_npx = fake_bin / "npx"
        fake_npx.write_text(
            "#!/usr/bin/env bash\n"
            "set -eu\n"
            f"printf '%s\\n' \"$*\" >> {calls}\n"
            "name=\"\"\n"
            "while [ $# -gt 0 ]; do\n"
            "  if [ \"$1\" = \"--skill\" ]; then name=\"$2\"; shift 2; else shift; fi\n"
            "done\n"
            "mkdir -p \"${AGENT_SKILLS_HOME}/$name\"\n"
            f"printf '%b' {contents!r} > \"${{AGENT_SKILLS_HOME}}/$name/SKILL.md\"\n",
            encoding="utf-8",
        )
        os.chmod(fake_npx, 0o755)
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env['PATH']}"
        env["AGENT_SKILLS_HOME"] = str(self.skills)
        result = subprocess.run(
            [str(install)], cwd=self.repo, env=env, text=True, capture_output=True, check=False
        )
        self.assertEqual(0, result.returncode, result.stderr)
        first_calls = calls.read_text(encoding="utf-8")
        self.assertIn("https://github.com/example/skills/tree/" + "a" * 40, first_calls)
        self.assertIn("--skill local-skill", first_calls)
        second = subprocess.run(
            [str(install)], cwd=self.repo, env=env, text=True, capture_output=True, check=False
        )
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(2, len(calls.read_text(encoding="utf-8").splitlines()))

    def test_skill_check_rejects_invalid_manifest_source_and_role_mismatch(self) -> None:
        skill_file = self.skills / "local-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("approved", encoding="utf-8")
        manifest = {
            "schema_version": 1,
            "allowed_roles": ["coder", "tester", "reviewer", "coordinator"],
            "skills": [
                {
                    "name": "local-skill",
                    "source": "http://example.invalid/skills",
                    "revision": "1" * 40,
                    "skill_file_sha256": hashlib.sha256(skill_file.read_bytes()).hexdigest(),
                    "roles": ["tester"],
                    "allowlist": ["coder"],
                    "purpose": "Testing guidance",
                    "risk": "normal",
                    "risk_detail": "Local-only test guidance.",
                }
            ],
        }
        (self.repo / ".harness" / "skills.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        result = self.run_check()
        self.assertEqual(1, result.returncode)
        self.assertIn("invalid source", result.stderr)
        self.assertIn("roles and allowlist differ", result.stderr)

    def test_skill_check_rejects_each_required_manifest_field_when_missing(self) -> None:
        skill_file = self.skills / "local-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text("approved", encoding="utf-8")
        checksum = hashlib.sha256(skill_file.read_bytes()).hexdigest()
        baseline = {
            "schema_version": 1,
            "allowed_roles": ["coder", "tester", "reviewer", "coordinator"],
            "skills": [{
                "name": "local-skill",
                "source": "https://github.com/example/skills",
                "revision": "1" * 40,
                "skill_file_sha256": checksum,
                "roles": ["tester"],
                "allowlist": ["tester"],
                "purpose": "Testing guidance",
                "risk": "normal",
                "risk_detail": "Local-only test guidance.",
            }],
        }
        cases = (
            ("allowed_roles", "manifest allowed_roles"),
            ("purpose", "missing purpose"),
            ("risk", "invalid risk"),
            ("risk_detail", "missing risk_detail"),
            ("allowlist", "roles and allowlist differ"),
        )
        for field, expected in cases:
            with self.subTest(field=field):
                manifest = deepcopy(baseline)
                if field == "allowed_roles":
                    del manifest[field]
                else:
                    del manifest["skills"][0][field]
                (self.repo / ".harness" / "skills.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
                result = self.run_check()
                self.assertEqual(1, result.returncode)
                self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
