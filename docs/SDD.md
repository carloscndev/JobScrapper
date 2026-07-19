# JobScrapper software design description

## User story

As a professional seeking work in Mexico and the United States, I want a local application to discover jobs daily, compare them with my CV and preferences using local models and explainable rules, and synchronize results to Notion, so I can prioritize strong opportunities without sending my profile to external AI services.

## Product behavior

- Import PDF/DOCX CV data into an editable profile containing skills, experience, seniority, languages, education, desired roles, compensation, work modes, locations, work authorization, and relocation preferences.
- Discover jobs daily from allowed APIs, feeds, and career pages without bypassing authentication, CAPTCHA, robots directives, or access controls.
- Normalize company, role, description, requirements, location, work mode, salary, source, dates, description URL, and application URL.
- Classify locations into CDMX, Guadalajara, rest of Mexico, USA, or other; classify mode as remote, hybrid, on-site, or unknown.
- Deduplicate jobs across sources, retain provenance and description history, and mark unavailable jobs inactive rather than deleting them.
- Calculate a 0-100 compatibility score from auditable weighted rules. Local models produce summaries, matches, gaps, and recommendations; deterministic scoring remains available if the model fails.
- Present searchable, sortable, filterable job lists and detailed score explanations in a local single-user dashboard.
- Upsert a master Notion database idempotently and expose regional filtered views.
- Record each scheduled run, isolate source failures, prevent overlapping executions, retry safely, and redact secrets from logs.
- Never auto-apply in the first release.

## Acceptance criteria

1. A valid CV produces an editable structured profile.
2. Failure of one source does not stop other sources.
3. Every record contains available normalized fields, provenance, and last-check time.
4. URLs, uploaded files, and scraped HTML are validated or sanitized.
5. Rediscovery updates a stable record instead of duplicating it.
6. Every job has region, mode, and deterministic score, permitting unknown classifications.
7. Score detail separates matches, gaps, and hard constraints.
8. A local-model outage leaves deterministic results intact and narrative analysis pending.
9. Notion regional views reflect the master database without duplicate records.
10. Removed jobs remain as inactive history.
11. Daily scheduling operates for seven days without overlapping runs.
12. Sources and profile preferences can be changed without code edits.

## Delivery backlog

After the harness gates are complete: persistence and migrations; profile/CV parsing; source adapter contract and compliant connectors; normalization and deduplication; deterministic scoring; FastAPI API; React dashboard; local-model analysis; Notion synchronization; scheduler/observability; security, backup, and end-to-end verification.

Initial technical defaults are Python/FastAPI/SQLAlchemy/SQLite, React/TypeScript/Vite, Ollama with a small quantized model and deterministic fallback, Docker Compose, and a system cron invoking one guarded pipeline command.
