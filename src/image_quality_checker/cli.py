"""이미지 품질 검사기의 명령행 인터페이스."""

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
        usage="%(prog)s [선택 사항] 입력_폴더",
        description="폴더 안의 이미지에 규칙 기반 사전 QC 검사를 실행합니다.",
        add_help=False,
    )
    parser._positionals.title = "위치 인수"
    parser._optionals.title = "선택 인수"
    parser.add_argument("input_dir", type=Path, help="검사할 이미지가 있는 폴더")
    parser.add_argument("-h", "--help", action="help", help="도움말을 표시하고 종료")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output/image_quality_results.csv"),
        help="결과 CSV 저장 경로",
    )
    parser.add_argument("--config", type=Path, help="선택 사항: JSON 설정 파일")
    parser.add_argument("--recursive", action="store_true", help="하위 폴더까지 탐색")
    parser.add_argument("--verbose", action="store_true", help="상세 로그 표시")
    return parser


def load_config(path: Path | None, recursive: bool) -> CheckConfig:
    values: dict[str, object] = {}
    if path:
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"JSON 설정 형식이 올바르지 않습니다: {path}: {error}") from error
        if not isinstance(values, dict):
            raise ValueError("설정 파일의 최상위 값은 JSON 객체여야 합니다.")
        allowed = {"min_width", "min_height", "dark_threshold", "bright_threshold", "extensions", "recursive"}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"알 수 없는 설정 항목: {', '.join(sorted(unknown))}")
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
    logging.info("검사 완료: 전체=%d, %s", len(results), summary)
    logging.info("CSV 저장 위치: %s", args.output.resolve())
    return 0
