#!/usr/bin/env python3
"""Dependency-free lifecycle CLI for the JobScrapper agent harness."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / ".harness"
CONFIG_PATH = HARNESS / "config.json"
BACKLOG_PATH = HARNESS / "backlog.json"
CURRENT_PATH = HARNESS / "current-task.json"
ACTIVE_STATES = {"coding", "testing", "review", "rework", "approved"}
REQUIRED_STATES = {"pending", "coding", "testing", "review", "rework", "approved", "committed", "blocked"}
HASH_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
COMMIT_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([a-z0-9._/-]+\))?!?: .+[^.]$")


class HarnessError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HarnessError(f"Missing required file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise HarnessError(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessError(f"Expected an object in {path.relative_to(ROOT)}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=ROOT, text=True, capture_output=capture, check=False)
    except OSError as exc:
        raise HarnessError(f"Could not run {command[0]}: {exc}") from exc


def checked(command: list[str], label: str) -> None:
    result = run(command)
    if result.returncode:
        details = (result.stdout + result.stderr).strip()
        raise HarnessError(f"Gate failed ({label}): {details or f'exit {result.returncode}'}")
    print(f"gate passed: {label}")


def load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return read_json(CONFIG_PATH), read_json(BACKLOG_PATH), read_json(CURRENT_PATH)


def tasks_by_id(backlog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tasks = backlog.get("tasks")
    if not isinstance(tasks, list):
        raise HarnessError("backlog.tasks must be a list")
    result: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str):
            raise HarnessError("Every backlog task needs a string id")
        if task["id"] in result:
            raise HarnessError(f"Duplicate task id: {task['id']}")
        result[task["id"]] = task
    return result


def validate_data(config: dict[str, Any], backlog: dict[str, Any], current: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = set(config.get("allowed_states", []))
    missing_states = REQUIRED_STATES - allowed
    if missing_states:
        errors.append("config.allowed_states is missing: " + ", ".join(sorted(missing_states)))
    roles = set(config.get("roles", []))
    if not {"coder", "tester", "reviewer"}.issubset(roles):
        errors.append("config.roles must include coder, tester, and reviewer")
    try:
        indexed = tasks_by_id(backlog)
    except HarnessError as exc:
        return [str(exc)]
    active = []
    for task in indexed.values():
        state = task.get("status")
        if state not in allowed:
            errors.append(f"{task['id']}: invalid status {state!r}")
        if state in ACTIVE_STATES:
            active.append(task["id"])
        commit = task.get("commit", "")
        match = COMMIT_RE.fullmatch(commit) if isinstance(commit, str) else None
        if not match or match.group("type") not in config.get("commit_types", []):
            errors.append(f"{task['id']}: invalid Conventional Commit template")
        allowed_paths = task.get("allowed_paths")
        if not isinstance(allowed_paths, list) or not allowed_paths or not all(isinstance(path, str) and path for path in allowed_paths):
            errors.append(f"{task['id']}: allowed_paths must be a non-empty string list")
        dependencies = task.get("depends_on", [])
        if not isinstance(dependencies, list):
            errors.append(f"{task['id']}: depends_on must be a list")
        else:
            for dependency in dependencies:
                if dependency not in indexed:
                    errors.append(f"{task['id']}: unknown dependency {dependency}")
                elif dependency == task["id"]:
                    errors.append(f"{task['id']}: task cannot depend on itself")
    # Dependencies must form a DAG; otherwise no valid sequence can ever
    # unblock the cyclic tasks.
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(task_id: str) -> None:
        if task_id in visiting:
            errors.append(f"Dependency cycle detected at {task_id}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in indexed[task_id].get("depends_on", []):
            if dependency in indexed:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)
    for task_id in indexed:
        visit(task_id)
    if len(active) > 1:
        errors.append(f"Multiple active backlog tasks: {', '.join(active)}")
    is_active = current.get("active") is True
    if is_active:
        task_id = current.get("task_id")
        if task_id not in indexed:
            errors.append("Current task is not in backlog")
        elif indexed[task_id].get("status") != current.get("state"):
            errors.append("Current task state differs from backlog")
        if current.get("state") not in ACTIVE_STATES:
            errors.append("Active current task has a non-active state")
        if active != [task_id]:
            errors.append("Backlog active task does not match current task")
        if not isinstance(current.get("attempt"), int) or current["attempt"] < 1:
            errors.append("Active task attempt must be a positive integer")
    elif active:
        errors.append("Backlog has an active task but current-task is inactive")
    else:
        if current.get("task_id") is not None or current.get("state") is not None:
            errors.append("Inactive current-task must not identify a task or state")
        if current.get("attempt") != 0:
            errors.append("Inactive current-task attempt must be zero")
    return errors


def require_valid(config: dict[str, Any], backlog: dict[str, Any], current: dict[str, Any]) -> None:
    errors = validate_data(config, backlog, current)
    if errors:
        raise HarnessError("Invalid harness state:\n" + "\n".join(f"- {item}" for item in errors))


def active_task(backlog: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if not current.get("active"):
        raise HarnessError("No active task")
    return tasks_by_id(backlog)[current["task_id"]]


def set_state(task: dict[str, Any], current: dict[str, Any], state: str) -> None:
    task["status"] = state
    current["state"] = state


def persist(backlog: dict[str, Any], current: dict[str, Any]) -> None:
    write_json(BACKLOG_PATH, backlog)
    write_json(CURRENT_PATH, current)


def command_init(args: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    if current.get("active") and not args.force:
        raise HarnessError("Cannot initialize while a task is active; use --force to reset intentionally")
    if args.force:
        for task in backlog["tasks"]:
            task["status"] = "pending" if not task.get("depends_on") else "blocked"
        current = {"schema_version": 1, "active": False, "task_id": None, "state": None, "attempt": 0, "evidence": {}, "rejections": [], "commit": None}
        persist(backlog, current)
    print("Harness initialized and valid")


def command_start(args: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    if current.get("active"):
        raise HarnessError(f"Task {current['task_id']} is already active")
    indexed = tasks_by_id(backlog)
    if args.task_id not in indexed:
        raise HarnessError(f"Unknown task: {args.task_id}")
    task = indexed[args.task_id]
    if task.get("status") != "pending":
        raise HarnessError(f"Task {args.task_id} is not pending")
    incomplete = [item for item in task.get("depends_on", []) if indexed[item].get("status") != "committed"]
    if incomplete:
        raise HarnessError("Uncommitted dependencies: " + ", ".join(incomplete))
    set_state(task, current, "coding")
    current.update({"active": True, "task_id": args.task_id, "attempt": 1, "evidence": {}, "rejections": [], "commit": None})
    persist(backlog, current)
    print(f"Started {args.task_id}; next: coder")


def evidence_for(current: dict[str, Any], role: str) -> dict[str, Any] | None:
    value = current.get("evidence", {}).get(role)
    return value if isinstance(value, dict) else None


def require_pass(current: dict[str, Any], role: str) -> None:
    evidence = evidence_for(current, role)
    if not evidence or evidence.get("result") != "pass" or not evidence.get("evidence"):
        raise HarnessError(f"Passing {role} evidence is required")


def command_handoff(args: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    task = active_task(backlog, current)
    state = current["state"]
    if args.role == "tester":
        if state not in {"coding", "rework"}:
            raise HarnessError("Tester handoff requires coding or rework state")
        require_pass(current, "coder")
        set_state(task, current, "testing")
    elif args.role == "reviewer":
        if state != "testing":
            raise HarnessError("Reviewer handoff requires testing state")
        require_pass(current, "tester")
        set_state(task, current, "review")
    else:
        raise HarnessError("Coder receives work through start or reject, not handoff")
    persist(backlog, current)
    print(f"Handed {task['id']} to {args.role}")


def command_record(args: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    task = active_task(backlog, current)
    expected = {"coding": "coder", "rework": "coder", "testing": "tester", "review": "reviewer"}.get(current["state"])
    if args.role != expected:
        raise HarnessError(f"State {current['state']} expects evidence from {expected}")
    evidence = args.evidence.strip()
    if not evidence:
        raise HarnessError("Evidence must not be empty")
    current.setdefault("evidence", {})[args.role] = {"result": args.result, "evidence": evidence, "attempt": current["attempt"]}
    if args.result == "fail":
        current.setdefault("rejections", []).append({"by": args.role, "reason": evidence, "attempt": current["attempt"]})
        current["attempt"] += 1
        current["evidence"] = {}
        set_state(task, current, "rework")
    persist(backlog, current)
    print(f"Recorded {args.result} from {args.role}")


def command_reject(args: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    task = active_task(backlog, current)
    reason = args.reason.strip()
    if not reason:
        raise HarnessError("Rejection reason must not be empty")
    if current["state"] not in {"testing", "review"}:
        raise HarnessError("Only tester or reviewer stages can reject")
    role = "tester" if current["state"] == "testing" else "reviewer"
    current.setdefault("rejections", []).append({"by": role, "reason": reason, "attempt": current["attempt"]})
    current["attempt"] += 1
    current["evidence"] = {}
    set_state(task, current, "rework")
    persist(backlog, current)
    print(f"Rejected by {role}; returned to coder for attempt {current['attempt']}")


def command_approve(_: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    task = active_task(backlog, current)
    if current["state"] != "review":
        raise HarnessError("Approval requires review state")
    require_pass(current, "coder")
    require_pass(current, "tester")
    require_pass(current, "reviewer")
    set_state(task, current, "approved")
    persist(backlog, current)
    print(f"Approved {task['id']}; coordinator may prepare commit")


def command_validate(_: argparse.Namespace) -> None:
    config, backlog, current = load()
    errors = validate_data(config, backlog, current)
    if errors:
        raise HarnessError("Validation failed:\n" + "\n".join(f"- {item}" for item in errors))
    print("Harness state is valid")


def command_commit_ready(_: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    task = active_task(backlog, current)
    if current["state"] != "approved":
        raise HarnessError("Task is not approved")
    for role in ("coder", "tester", "reviewer"):
        require_pass(current, role)
    for command in config.get("gate_commands", []):
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise HarnessError("Every gate_commands entry must be a non-empty string array")
        checked(command, " ".join(command))
    # JSON integrity is a gate independent of the state-machine validation above.
    for relative in config.get("json_gate_files", []):
        if not isinstance(relative, str):
            raise HarnessError("Every json_gate_files entry must be a string")
        read_json(ROOT / relative)
    print("gate passed: JSON integrity")
    staged_result = run(["git", "diff", "--cached", "--name-status", "-z"])
    if staged_result.returncode:
        raise HarnessError("Could not inspect staged files")
    fields = staged_result.stdout.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    staged_entries: list[tuple[str, list[str]]] = []
    position = 0
    while position < len(fields):
        status = fields[position]
        position += 1
        path_count = 2 if status.startswith(("R", "C")) else 1
        if position + path_count > len(fields):
            raise HarnessError("Could not parse staged Git name-status output")
        paths = fields[position:position + path_count]
        position += path_count
        staged_entries.append((status, paths))
    if not staged_entries:
        raise HarnessError("Staging area is empty")
    # Check both old and new rename/copy paths; otherwise a rename could smuggle a
    # file into or out of the active task scope. Deletions are included as well.
    staged_paths = [name for _, paths in staged_entries for name in paths]
    indexed_paths = [paths[-1] for status, paths in staged_entries if not status.startswith("D")]
    forbidden = [name for name in staged_paths if Path(name).name == ".env" or name.endswith(".env") or name.startswith(".env.") and name != ".env.example"]
    if forbidden:
        raise HarnessError("Forbidden environment file staged: " + ", ".join(forbidden))
    allowed_paths = task.get("allowed_paths", [])
    outside_scope = [name for name in staged_paths if not any(name == pattern or fnmatch.fnmatchcase(name, pattern) for pattern in allowed_paths)]
    if outside_scope:
        raise HarnessError("Staged files outside task scope: " + ", ".join(outside_scope))
    staged_diff = run(["git", "diff", "--cached", "--no-ext-diff", "--unified=0"])
    if staged_diff.returncode:
        raise HarnessError("Could not inspect staged diff")
    secret_patterns = [
        re.compile(r"(?i)^\+.*(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{8,}"),
        re.compile(r"^\+.*(?:[:=]\s*|[\"'])(?:ghp_|github_pat_|sk-[A-Za-z0-9])"),
        re.compile(r"^\+-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    def is_scanner_pattern_definition(line: str) -> bool:
        """Ignore only this scanner's own added Python regex declarations."""
        return bool(re.match(r"^\+\s*re\.compile\(r(?:f)?[\"']", line)) and r"^\+" in line

    leaked = [
        line
        for line in staged_diff.stdout.splitlines()
        if not line.startswith("+++")
        and not is_scanner_pattern_definition(line)
        and any(pattern.search(line) for pattern in secret_patterns)
    ]
    if leaked:
        raise HarnessError("Potential secret detected in staged content")
    print(f"gate passed: staged scope ({len(staged_entries)} changes) and secret scan")
    task_id = task["id"]
    required_documents: list[Path] = []
    for key in ("development_log", "changelog"):
        path_value = config.get(key)
        if not isinstance(path_value, str):
            raise HarnessError(f"Missing configured {key}")
        document = ROOT / path_value
        required_documents.append(document)
        relative = document.relative_to(ROOT).as_posix()
        if relative not in indexed_paths:
            raise HarnessError(f"Required traceability document is not staged: {relative}")
        staged_content = run(["git", "show", f":{relative}"])
        if staged_content.returncode:
            raise HarnessError(f"Could not read staged traceability document: {relative}")
        content = staged_content.stdout
        heading = re.compile(rf"^### {re.escape(task_id)} — Attempt {current['attempt']}$", re.MULTILINE)
        match = heading.search(content)
        if not match:
            raise HarnessError(f"Missing structured section for {task_id} attempt {current['attempt']} in {path_value}")
        next_heading = re.search(r"^### ", content[match.end():], re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(content)
        section = content[match.end():end]
        required_lines = {
            "Skills": r"(?m)^- Skills: .+",
            "Files": r"(?m)^- Files: .+",
            "Commands": r"(?m)^- Commands: .+",
            "Tester PASS": r"(?m)^- Tester: PASS(?:\s|$)",
            "Reviewer APPROVED": r"(?m)^- Reviewer: APPROVED(?:\s|$)",
            "Risks": r"(?m)^- Risks: .+",
            "Commit subject": rf"(?m)^- Commit subject: {re.escape(task['commit'])}$",
            "Commit hash": r"(?m)^- Commit hash: (?:pending|[0-9a-fA-F]{7,40})$",
        }
        missing = [label for label, pattern in required_lines.items() if not re.search(pattern, section)]
        if missing:
            raise HarnessError(f"Incomplete {task_id} attempt {current['attempt']} section in {path_value}: {', '.join(missing)}")
    print("gate passed: current-attempt traceability in staged development log and changelog")
    print(task["commit"])


def command_complete(args: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    task = active_task(backlog, current)
    if current["state"] != "approved":
        raise HarnessError("Only an approved task can be completed")
    if not HASH_RE.fullmatch(args.commit):
        raise HarnessError("Commit must be a 7-40 character hexadecimal Git hash")
    resolved = run(["git", "rev-parse", "--verify", f"{args.commit}^{{commit}}"])
    head = run(["git", "rev-parse", "--verify", "HEAD^{commit}"])
    if resolved.returncode or head.returncode:
        raise HarnessError("Commit must exist in this Git repository and HEAD must resolve")
    if resolved.stdout.strip().lower() != head.stdout.strip().lower():
        raise HarnessError("Commit must be the current HEAD")
    subject = run(["git", "show", "-s", "--format=%s", "HEAD"])
    if subject.returncode or subject.stdout.strip() != task.get("commit"):
        raise HarnessError("Commit subject does not match the task Conventional Commit")
    task["status"] = "committed"
    task["commit_hash"] = args.commit.lower()
    indexed = tasks_by_id(backlog)
    for candidate in backlog["tasks"]:
        if candidate.get("status") == "blocked" and all(indexed[item].get("status") == "committed" for item in candidate.get("depends_on", [])):
            candidate["status"] = "pending"
    current.update({"active": False, "task_id": None, "state": None, "attempt": 0, "evidence": {}, "rejections": [], "commit": resolved.stdout.strip().lower()})
    persist(backlog, current)
    print(f"Completed {task['id']} at {resolved.stdout.strip().lower()}")


def command_status(_: argparse.Namespace) -> None:
    config, backlog, current = load()
    require_valid(config, backlog, current)
    if current.get("active"):
        evidence = ", ".join(sorted(current.get("evidence", {}))) or "none"
        print(f"{current['task_id']}: state={current['state']} attempt={current['attempt']} evidence={evidence}")
        return
    pending = [task["id"] for task in backlog["tasks"] if task.get("status") == "pending"]
    print("No active task" + (f"; next={pending[0]}" if pending else "; backlog complete or blocked"))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--force", action="store_true")
    init.set_defaults(handler=command_init)
    start = commands.add_parser("start")
    start.add_argument("task_id")
    start.set_defaults(handler=command_start)
    handoff = commands.add_parser("handoff")
    handoff.add_argument("role", choices=["coder", "tester", "reviewer"])
    handoff.set_defaults(handler=command_handoff)
    record = commands.add_parser("record")
    record.add_argument("role", choices=["coder", "tester", "reviewer"])
    record.add_argument("--result", choices=["pass", "fail"], required=True)
    record.add_argument("--evidence", required=True)
    record.set_defaults(handler=command_record)
    reject = commands.add_parser("reject")
    reject.add_argument("--reason", required=True)
    reject.set_defaults(handler=command_reject)
    approve = commands.add_parser("approve")
    approve.set_defaults(handler=command_approve)
    validate = commands.add_parser("validate")
    validate.set_defaults(handler=command_validate)
    ready = commands.add_parser("commit-ready")
    ready.set_defaults(handler=command_commit_ready)
    complete = commands.add_parser("complete")
    complete.add_argument("--commit", required=True)
    complete.set_defaults(handler=command_complete)
    status = commands.add_parser("status")
    status.set_defaults(handler=command_status)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        args.handler(args)
        return 0
    except HarnessError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
