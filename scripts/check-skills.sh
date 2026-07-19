#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
manifest="$repo_root/.harness/skills.json"
skill_root="${AGENT_SKILLS_HOME:-$HOME/.agents/skills}"

python3 - "$manifest" "$skill_root" "$@" <<'PY'
import argparse, hashlib, json, pathlib, re, sys
from urllib.parse import urlparse
manifest_path, root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
parser = argparse.ArgumentParser(description="Verify managed project skills")
parser.add_argument("--skill"); parser.add_argument("--role"); args = parser.parse_args(sys.argv[3:])
try: data = json.loads(manifest_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc: raise SystemExit(f"invalid skills manifest: {exc}")
errors, managed = [], {}
items = data.get("skills")
if not isinstance(items, list) or not items: errors.append("manifest skills must be a non-empty list")
configured_roles = data.get("allowed_roles")
if not isinstance(configured_roles, list) or not configured_roles or any(not isinstance(role, str) or not role.strip() for role in configured_roles):
    errors.append("manifest allowed_roles must be a non-empty list")
known_roles = set(configured_roles or [])
for item in items or []:
    name = item.get("name")
    if not isinstance(name, str) or name in managed: errors.append(f"invalid or duplicate skill name: {name!r}"); continue
    managed[name] = item
    source = item.get("source")
    parsed = urlparse(source or "")
    if parsed.scheme != "https" or parsed.netloc != "github.com" or len(parsed.path.strip("/").split("/")) != 2: errors.append(f"invalid source: {name}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(item.get("revision", ""))): errors.append(f"invalid immutable revision: {name}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("skill_file_sha256", ""))): errors.append(f"invalid checksum: {name}")
    roles, allowlist = item.get("roles"), item.get("allowlist")
    if not isinstance(roles, list) or not roles or set(roles) - known_roles: errors.append(f"invalid role allowlist: {name}")
    if roles != allowlist: errors.append(f"roles and allowlist differ: {name}")
    if not isinstance(item.get("purpose"), str) or not item["purpose"].strip(): errors.append(f"missing purpose: {name}")
    if item.get("risk") not in {"normal", "high"}: errors.append(f"invalid risk: {name}")
    if not isinstance(item.get("risk_detail"), str) or not item["risk_detail"].strip(): errors.append(f"missing risk_detail: {name}")
if args.skill and args.skill not in managed: errors.append(f"unmanaged skill: {args.skill}")
if args.role and not args.skill: errors.append("--role requires --skill")
if args.skill in managed and args.role and args.role not in managed[args.skill].get("allowlist", []): errors.append(f"role {args.role} is not authorized for {args.skill}")
selected = [managed[args.skill]] if args.skill in managed else ([] if args.skill else list(managed.values()))
for item in selected:
    path = root / item["name"] / "SKILL.md"
    if not path.is_file(): errors.append(f"missing: {item['name']} ({path})"); continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item["skill_file_sha256"]: errors.append(f"checksum mismatch: {item['name']} expected={item['skill_file_sha256']} actual={digest}")
if errors:
    print("Skill verification failed:", file=sys.stderr); print("\n".join(f"- {error}" for error in errors), file=sys.stderr); raise SystemExit(1)
print(f"Verified {len(selected)} approved skills: {', '.join(sorted(item['name'] for item in selected))}")
PY
