# Job identity and history

Ingestion canonicalizes absolute HTTP(S) URLs by removing fragments, default
ports, trailing slashes, and common tracking parameters. A SHA-256 fingerprint
of normalized title, company, and location provides a second deduplication key.

`JobRepository.upsert` is idempotent: rediscovery updates the existing row,
merges metadata/provenance, and preserves non-empty fields. A description or
link change stores the prior values in `job_snapshots` using a content hash.
After a successful source run, `mark_missing` marks absent active postings as
`inactive`; rows are retained for history and are never deleted.
