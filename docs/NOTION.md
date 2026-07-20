# Notion integration contract

JobScrapper keeps SQLite as the operational source of truth and mirrors jobs to
one Notion master database. `backend/app/notion.py` contains the schema payload
and the five filtered regional views: CDMX, Guadalajara, Mexico (rest of the
country), USA, and Other. Views filter the `Region` select property, so a job
is represented by one page and is never duplicated per region.

## Local credentials

Copy `.env.example` to `.env` and set `NOTION_API_TOKEN` and
`NOTION_DATABASE_ID` locally. The token is read immediately before a future
sync request; only environment-variable names and a boolean configured flag
may appear in diagnostics. `.env` is ignored by Git. No credentials are
required for schema inspection, unit tests, or an offline development run.

The Notion API version is pinned to `2025-09-03`. Database creation and page
updates require explicit operator authorization in the sync workflow; this
task performs no network or destructive operation.

## Master properties

The schema maps normalized title/company, location, region, modality, salary and
currency, source provenance, description/application links, publication and
check dates, score and explanation, matches/gaps/recommendations, status, and
stable local job ID/fingerprint. Full descriptions stay in SQLite because
Notion rich-text blocks have size limits; the Notion page links to the original
description.
