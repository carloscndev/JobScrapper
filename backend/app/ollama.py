"""Strictly-local Ollama analysis for explainable matching narratives.

The deterministic score remains the source of truth.  This worker only adds a
short summary and human-readable explanations.  Requests are restricted to a
loopback Ollama endpoint and the payload is explicitly allowlisted so CV text,
tokens, credentials, and arbitrary metadata never leave the process.
"""
from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class LocalModelError(RuntimeError):
    """Raised when local analysis cannot be completed or validated."""


@dataclass(frozen=True)
class LocalAnalysis:
    summary: str
    matches: list[str]
    gaps: list[str]
    recommendations: list[str]
    model: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "matches": list(self.matches),
            "gaps": list(self.gaps),
            "recommendations": list(self.recommendations),
            "model": self.model,
        }


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{key}: {value[key]}" for key in sorted(value))
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def _safe_payload(profile: object, job: object) -> dict[str, Any]:
    """Build an allowlisted payload; never include CV text or raw metadata."""
    get = lambda obj, key, default=None: obj.get(key, default) if isinstance(obj, Mapping) else getattr(obj, key, default)
    pref = get(profile, "preferences", None)
    if isinstance(pref, (list, tuple)):
        pref = next((item for item in pref if get(item, "is_current", True)), None)
    experience = []
    for item in get(profile, "experience", []) or []:
        if isinstance(item, Mapping):
            experience.append({key: item[key] for key in ("title", "company", "years", "years_experience", "duration_years") if key in item})
        else:
            experience.append(_text(item))
    return {
        "profile": {
            "skills": list(get(profile, "skills", []) or []),
            "experience": experience,
            "languages": list(get(profile, "languages", []) or []),
            "preferences": {
                "target_roles": list(get(pref or {}, "target_roles", []) or []),
                "locations": list(get(pref or {}, "locations", []) or []),
                "modalities": list(get(pref or {}, "modalities", []) or []),
                "seniority": _text(get(pref or {}, "seniority", "")),
            },
        },
        "job": {
            "title": _text(get(job, "title", "")),
            "company": _text(get(job, "company", "")),
            "description": _text(get(job, "description", ""))[:12000],
            "location": _text(get(job, "location", "")),
            "region": _text(get(job, "region", "")),
            "modality": _text(get(job, "modality", "unknown")),
        },
    }


def _loopback(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "http" or not parsed.hostname or parsed.path.rstrip("/") not in {"", "/api"}:
        return False
    host = parsed.hostname.casefold()
    if host in {"localhost", "ip6-localhost"}:
        return True
    try:
        return all(ip in {"127.0.0.1", "::1"} or ip.startswith("127.") for ip in {info[4][0] for info in socket.getaddrinfo(host, parsed.port or 80)})
    except OSError:
        return False


class OllamaAnalyzer:
    """Call Ollama's local ``/api/generate`` endpoint with bounded resources."""

    def __init__(self, *, base_url: str = "http://127.0.0.1:11434", model: str = "llama3.2:3b", timeout_seconds: float = 30.0, num_ctx: int = 2048, num_thread: int = 2, max_retries: int = 2, retry_backoff_seconds: float = 0.1, opener: Callable[..., Any] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        if not _loopback(self.base_url):
            raise ValueError("Ollama must use a local loopback HTTP endpoint")
        if not model.strip() or timeout_seconds <= 0 or num_ctx < 256 or num_thread < 1 or max_retries < 0 or retry_backoff_seconds < 0:
            raise ValueError("invalid Ollama resource configuration")
        self.model, self.timeout_seconds = model.strip(), timeout_seconds
        self.num_ctx, self.num_thread = num_ctx, num_thread
        self.max_retries, self.retry_backoff_seconds = max_retries, retry_backoff_seconds
        self._opener = opener or urlopen

    def analyze(self, profile: object, job: object) -> LocalAnalysis:
        payload = _safe_payload(profile, job)
        prompt = ("Return ONLY a JSON object with string summary and arrays matches, gaps, recommendations. "
                  "Do not invent facts; base every item on the supplied profile and job.\n" + json.dumps(payload, ensure_ascii=False))
        request_body = {"model": self.model, "prompt": prompt, "stream": False, "format": "json", "options": {"num_ctx": self.num_ctx, "num_thread": self.num_thread}}
        request = Request(self.base_url + "/api/generate", data=json.dumps(request_body).encode(), headers={"Content-Type": "application/json", "User-Agent": "JobScrapper-local/1.0"}, method="POST")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with self._opener(request, timeout=self.timeout_seconds) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                break
            except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.max_retries and self.retry_backoff_seconds:
                    time.sleep(self.retry_backoff_seconds * (2 ** attempt))
        else:
            raise LocalModelError("local Ollama request failed") from last_error
        try:
            result = raw.get("response", raw) if isinstance(raw, Mapping) else raw
            if isinstance(result, str):
                result = json.loads(result)
            if not isinstance(result, Mapping):
                raise TypeError
            summary = result.get("summary")
            fields = {key: result.get(key, []) for key in ("matches", "gaps", "recommendations")}
            if not isinstance(summary, str) or not summary.strip() or any(not isinstance(value, list) or any(not isinstance(item, str) for item in value) for value in fields.values()):
                raise TypeError
            return LocalAnalysis(summary.strip(), [item.strip() for item in fields["matches"] if item.strip()], [item.strip() for item in fields["gaps"] if item.strip()], [item.strip() for item in fields["recommendations"] if item.strip()], self.model)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LocalModelError("Ollama returned invalid structured output") from exc
