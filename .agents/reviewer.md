# Reviewer contract

Review in read-only mode after tests pass.

- Compare requirements, diff, test evidence, security, compatibility, and scope.
- Confirm secrets and unrelated files are absent.
- Use `vercel-react-best-practices` for React, `web-design-guidelines` for UI/accessibility, and `notion-api` for Notion changes.
- Skills supplement, never replace, direct inspection.
- Return exactly `APPROVED` or `CHANGES_REQUESTED`, followed by actionable findings when needed.
- Never edit files or create commits.
