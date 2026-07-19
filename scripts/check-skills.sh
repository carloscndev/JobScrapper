#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
manifest="$repo_root/.harness/skills.json"
skill_root="${AGENT_SKILLS_HOME:-$HOME/.agents/skills}"

python3 - "$manifest" "$skill_root" "$@" <<'PY'
import argparse
import hashlib
import json
import pathlib
import sys

manifest_path, root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
parser = argparse.ArgumentParser(description="Verify managed project skills")
parser.add_argument("--skill")
parser.add_argument("--role")
args = parser.parse_args(sys.argv[3:])
data = json.loads(manifest_path.read_text(encoding="utf-8"))
errors = []
managed = {item["name"]: item for item in data["skills"]}
if args.skill and args.skill not in managed:
    errors.append(f"unmanaged skill: {args.skill}")
if args.role and not args.skill:
    errors.append("--role requires --skill")
if args.skill in managed and args.role and args.role not in managed[args.skill].get("roles", []):
    errors.append(f"role {args.role} is not authorized for {args.skill}")
selected = [managed[args.skill]] if args.skill in managed else ([] if args.skill else list(managed.values()))
for item in selected:
    path = root / item["name"] / "SKILL.md"
    if not path.is_file():
        errors.append(f"missing: {item['name']} ({path})")
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item["skill_file_sha256"]:
        errors.append(f"checksum mismatch: {item['name']} expected={item['skill_file_sha256']} actual={digest}")

if errors:
    print("Skill verification failed:", file=sys.stderr)
    print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
    raise SystemExit(1)
print(f"Verified {len(selected)} approved skills: {', '.join(sorted(item['name'] for item in selected))}")
PY
