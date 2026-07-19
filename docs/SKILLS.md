# Managed skills

Project skills are allow-listed in `.harness/skills.json`. The manifest records the canonical GitHub source, exact 40-character upstream commit, SHA-256 of `SKILL.md`, purpose, authorized roles, risk, and risk rationale. `roles` and `allowlist` are intentionally duplicated and must remain identical so tooling can enforce role access without inference. It is the source of truth; skills are never updated automatically.

## Approved capabilities

| Skill | Roles | Purpose | Risk |
| --- | --- | --- | --- |
| `vercel-react-best-practices` | coder, reviewer | React performance and implementation review | Normal |
| `web-design-guidelines` | reviewer | UI, UX, and accessibility review | Normal |
| `webapp-testing` | tester | Playwright end-to-end testing | Normal |
| `notion-api` | coder, reviewer | Notion REST integration guidance | **High: Snyk assessment** |

`notion-api` may only be used after the coordinator acknowledges the high-risk entry and the assigned agent rereads its `SKILL.md`. Never copy commands, tokens, or outbound behavior blindly from a skill.

## Installation and verification

Run `scripts/install-skills.sh` only with approval because it uses the network and writes to the global agent skill directory. It reads every source and commit from the manifest, installs the commit-specific URL, and then invokes `scripts/check-skills.sh`; it never tracks a moving branch or tag. Re-running it is safe and produces the same requested revisions.

Run `scripts/check-skills.sh` at any time for a read-only checksum and manifest check. It validates GitHub sources, immutable revisions, SHA-256 format, risk values, and role allowlists before checking installed files. Use `scripts/check-skills.sh --skill NAME --role ROLE` to enforce per-task authorization; unmanaged skills and unauthorized roles fail closed. Extra global/system skills are ignored. Set `AGENT_SKILLS_HOME` to verify an isolated installation root.

### Verification record (SKILLS-002)

Verified on 2026-07-18 (America/Mexico_City) from the repository root with the
read-only command:

```text
scripts/check-skills.sh
Verified 4 approved skills: notion-api, vercel-react-best-practices, web-design-guidelines, webapp-testing
```

The command checks the four allow-listed files under
`$HOME/.agents/skills/<skill>/SKILL.md` against the manifest's SHA-256 values.
The observed values matched exactly:

| Skill | Installed path | Manifest SHA-256 | Result |
| --- | --- | --- | --- |
| `vercel-react-best-practices` | `$HOME/.agents/skills/vercel-react-best-practices/SKILL.md` | `71ed7794962fa6e803ee83030517b5b93a9f70fbfeb431ec4535c5480a8d8355` | PASS |
| `web-design-guidelines` | `$HOME/.agents/skills/web-design-guidelines/SKILL.md` | `f4647ca866a3accf763777f83e7682954f0187cd6bea7eea0399796652414e8f` | PASS |
| `webapp-testing` | `$HOME/.agents/skills/webapp-testing/SKILL.md` | `51b7349e77ec63b7744a6f63647e7566a0b4d2e301121cc10e8c2113af6556a2` | PASS |
| `notion-api` | `$HOME/.agents/skills/notion-api/SKILL.md` | `cad2c5f98f0665059abcfe29cbb9609da49f836cb5f22fd85939056e2b2a4d8f` | PASS |

No installation or update was required. Verification is reproducible on another
machine by setting `AGENT_SKILLS_HOME` to an isolated skills directory and
running the same script; an absent file or checksum mismatch fails closed.

To upgrade a skill, create a dedicated backlog task, inspect the upstream diff and full `SKILL.md`, update its pinned checksum/revision, run verification, and use a Conventional Commit. Unlisted skills are not authorized by this project.

The task backlog also defines `allowed_paths`. Skill-related work must stay within that allowlist; `commit-ready` rejects unrelated staged files even when all skill checks pass.
