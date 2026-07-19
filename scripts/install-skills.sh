#!/usr/bin/env bash
set -euo pipefail

command -v npx >/dev/null 2>&1 || { echo "npx is required" >&2; exit 1; }

npx skills add https://github.com/vercel-labs/agent-skills/tree/f8a72b9603728bb92a217a879b7e62e43ad76c81 --skill vercel-react-best-practices -g -y
npx skills add https://github.com/vercel-labs/agent-skills/tree/f8a72b9603728bb92a217a879b7e62e43ad76c81 --skill web-design-guidelines -g -y
npx skills add https://github.com/anthropics/skills/tree/fa0fa64bdc967915dc8399e803be67759e1e62b8 --skill webapp-testing -g -y
npx skills add https://github.com/intellectronica/agent-skills/tree/9b0e00ad1b941165e2506545bbfddafa34cf2cb8 --skill notion-api -g -y

"$(dirname "$0")/check-skills.sh"
