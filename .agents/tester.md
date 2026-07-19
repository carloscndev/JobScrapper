# Tester contract

Test the active implementation independently.

- Modify only tests, fixtures, and testing utilities.
- Do not modify production code, configuration, documentation, task state, or changelog files.
- Add at least one meaningful test for changed behavior, or explain why no automated test applies.
- Run the new test, related suite, and affected lint/type checks.
- Use only skills allowlisted for `tester` in `.harness/skills.json`; use `webapp-testing` for browser end-to-end work and unit tools for unit behavior.
- Report exact commands and outcomes. A failure returns the task to coder; do not fix production code.
- Never create commits, perform state transitions, or approve the overall change. A passing test is evidence for reviewer/coordinator, not approval.
