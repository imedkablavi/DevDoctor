#!/usr/bin/env python3
"""Measure DevDoctor startup and bounded scan performance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean


def measure_startup(iterations: int) -> list[float]:
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, "-m", "devdoctor", "--version"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        elapsed = time.perf_counter() - started
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "DevDoctor startup benchmark failed")
        samples.append(elapsed)
    return samples


def measure_scan(iterations: int) -> list[float]:
    from devdoctor.bootstrap import bootstrap_inventory
    from devdoctor.hardening import apply_runtime_hardening

    apply_runtime_hardening()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        bootstrap_inventory(include_ids=("git", "python", "node"))
        samples.append(time.perf_counter() - started)
    return samples


def summarize(samples: list[float]) -> dict[str, object]:
    ordered = sorted(samples)
    p95_index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * 0.95)))
    return {
        "samples_seconds": [round(value, 4) for value in samples],
        "min_seconds": round(min(samples), 4),
        "mean_seconds": round(mean(samples), 4),
        "p95_seconds": round(ordered[p95_index], 4),
        "max_seconds": round(max(samples), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be >= 1")

    result = {
        "schema_version": 1,
        "iterations": args.iterations,
        "startup": summarize(measure_startup(args.iterations)),
        "bounded_scan": summarize(measure_scan(args.iterations)),
        "notes": [
            "Startup executes `python -m devdoctor --version` in a fresh subprocess.",
            "Bounded scan inventories git, python, and node without applying changes.",
            "CI results are baselines, not workstation latency guarantees.",
        ],
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
