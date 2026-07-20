"""Deterministic job identity and lifecycle helpers.

The ingestion worker uses these helpers before persistence so URL variants and
provider changes remain one logical posting while content revisions are kept
as snapshots.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .sources import NormalizedJob

_TRACKING_KEYS = {"fbclid", "gclid", "dclid", "mc_cid", "mc_eid", "ref", "referrer", "source", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def canonicalize_url(url: str) -> str:
    """Return a stable HTTP(S) URL with fragments and tracking parameters removed."""
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError("canonical URL must be an absolute HTTP(S) URL")
    host = parts.hostname.lower() if parts.hostname else ""
    port = parts.port
    netloc = host
    if port and not ((parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in _TRACKING_KEYS and not k.lower().startswith("utm_")]
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(sorted(query)), ""))


def fingerprint_job(job: NormalizedJob | Mapping[str, object] | object) -> str:
    """Create a SHA-256 identity from stable posting attributes."""
    if isinstance(job, NormalizedJob):
        values = (job.title, job.company, job.location or "")
    elif isinstance(job, Mapping):
        values = (job.get("title", ""), job.get("company", ""), job.get("location", ""))
    else:
        values = (getattr(job, "title", ""), getattr(job, "company", ""), getattr(job, "location", ""))
    payload = "\x1f".join(re.sub(r"\s+", " ", str(value).strip()).casefold() for value in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def content_hash(*, description: str, description_url: str, application_url: str | None) -> str:
    payload = json.dumps([description, description_url, application_url or ""], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
