#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
manifest="$repo_root/.harness/skills.json"
command -v npx >/dev/null 2>&1 || { echo "npx is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

skills="$(python3 - "$manifest" <<'PY'
import json, pathlib, re, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
roles = data.get("allowed_roles")
if not isinstance(roles, list) or not roles: raise SystemExit("manifest allowed_roles must be a non-empty list")
for item in data.get("skills", []):
    name, source, revision = item.get("name"), item.get("source"), item.get("revision")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name): raise SystemExit(f"invalid skill name: {name!r}")
    if not isinstance(source, str) or not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source): raise SystemExit(f"invalid source for {name}")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision): raise SystemExit(f"invalid immutable revision for {name}")
    if not isinstance(item.get("purpose"), str) or not item["purpose"].strip(): raise SystemExit(f"missing purpose for {name}")
    if item.get("risk") not in {"normal", "high"}: raise SystemExit(f"invalid risk for {name}")
    if not isinstance(item.get("risk_detail"), str) or not item["risk_detail"].strip(): raise SystemExit(f"missing risk_detail for {name}")
    if not isinstance(item.get("roles"), list) or item["roles"] != item.get("allowlist") or set(item["roles"]) - set(roles): raise SystemExit(f"invalid role allowlist for {name}")
    print(f"{name}\t{source}\t{revision}")
PY
 )"
while IFS= read -r entry; do
  [ -n "$entry" ] || continue
  IFS=$'\t' read -r name source revision <<<"$entry"
  npx skills add "$source/tree/$revision" --skill "$name" -g -y
done <<< "$skills"
"$repo_root/scripts/check-skills.sh"
