"""Command-line interface for image-quality-checker."""

from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Sequence

from .checker import CheckConfig, ImageResult, inspect_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image-quality-check",
        description="Run deterministic pre-QC checks on a directory of images.",
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing images")
    parser.add_argument("-o", "--output", type=Path, default=Path("output/image_quality_results.csv"))
    parser.add_argument("--config", type=Path, help="Optional JSON configuration file")
    parser.add_argument("--recursive", action="store_true", help="Scan subdirectories")
    parser.add_argument("--verbose", action="store_true", help="Show detailed logs")
    return parser


def load_config(path: Path | None, recursive: bool) -> CheckConfig:
    values: dict[str, object] = {}
    if path:
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON configuration: {path}: {error}") from error
        if not isinstance(values, dict):
            raise ValueError("Configuration must be a JSON object.")
        allowed = {"min_width", "min_height", "dark_threshold", "bright_threshold", "extensions", "recursive"}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Unknown configuration key(s): {', '.join(sorted(unknown))}")
        if "extensions" in values:
            values["extensions"] = tuple(str(item).lower() for item in values["extensions"])
    if recursive:
        values["recursive"] = True
    return CheckConfig(**values)


def write_csv(results: list[ImageResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [result.to_dict() for result in results]
    fieldnames = list(ImageResult("", "", "").to_dict())
    with output_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s | %(message)s",
    )
    try:
        config = load_config(args.config, args.recursive)
        results = inspect_directory(args.input_dir.resolve(), config)
        write_csv(results, args.output)
    except (FileNotFoundError, NotADirectoryError, OSError, TypeError, ValueError) as error:
        logging.error("%s", error)
        return 2

    counts = Counter(result.status.value for result in results)
    summary = ", ".join(f"{status}={counts.get(status, 0)}" for status in ("PASS", "REVIEW", "DROP", "ERROR"))
    logging.info("Completed: total=%d, %s", len(results), summary)
    logging.info("CSV saved to %s", args.output.resolve())
    return 0
