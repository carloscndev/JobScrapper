#!/usr/bin/env python3
"""Daily scheduler entry point delegating to the canonical pipeline command."""

from __future__ import annotations

import sys

from run_pipeline import main as run_pipeline


if __name__ == "__main__":
    raise SystemExit(run_pipeline(sys.argv[1:]))
