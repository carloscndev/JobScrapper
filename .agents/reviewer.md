# Reviewer contract

Review in read-only mode after tests pass.

- Compare requirements, diff, test evidence, security, compatibility, and scope.
- Inspect only the active task and its `allowed_paths`; reject unrelated or untracked changes.
- Confirm secrets and unrelated files are absent.
- Use only skills allowlisted for `reviewer` in `.harness/skills.json`: `vercel-react-best-practices` for React, `web-design-guidelines` for UI/accessibility, and `notion-api` for Notion changes. For Notion, acknowledge the manifest's high-risk review requirement.
- Skills supplement, never replace, direct inspection.
- Return exactly `APPROVED` or `CHANGES_REQUESTED`, followed by actionable findings when needed.
- Verify tester evidence is present and passing before approving. Never edit files, change task state, or create commits.
