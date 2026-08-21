"""Core image inspection logic.

The checks in this module are deterministic heuristics intended to reduce manual
screening work. They are not a substitute for visual review.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

LOGGER = logging.getLogger(__name__)


class Status(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    DROP = "DROP"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CheckConfig:
    min_width: int = 300
    min_height: int = 300
    dark_threshold: float = 40.0
    bright_threshold: float = 220.0
    extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
    recursive: bool = False

    def __post_init__(self) -> None:
        if self.min_width < 1 or self.min_height < 1:
            raise ValueError("Minimum dimensions must be positive integers.")
        if not 0 <= self.dark_threshold < self.bright_threshold <= 255:
            raise ValueError("Brightness thresholds must satisfy 0 <= dark < bright <= 255.")


@dataclass
class ImageResult:
    file_path: str
    file_name: str
    extension: str
    width: int | None = None
    height: int | None = None
    mode: str | None = None
    file_size_bytes: int | None = None
    average_brightness: float | None = None
    sha256: str | None = None
    duplicate_of: str = ""
    status: Status = Status.PASS
    reasons: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


def discover_images(input_dir: Path, config: CheckConfig) -> list[Path]:
    iterator: Iterable[Path] = input_dir.rglob("*") if config.recursive else input_dir.iterdir()
    allowed = {extension.lower() for extension in config.extensions}
    return sorted(
        (path for path in iterator if path.is_file() and path.suffix.lower() in allowed),
        key=lambda path: path.as_posix().lower(),
    )


def sha256_file(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _brightness(image: Image.Image) -> float:
    normalized = ImageOps.exif_transpose(image).convert("RGB")
    grayscale = ImageOps.grayscale(normalized)
    return round(float(ImageStat.Stat(grayscale).mean[0]), 2)


def inspect_image(file_path: Path, input_dir: Path, config: CheckConfig) -> ImageResult:
    relative_path = file_path.relative_to(input_dir).as_posix()
    result = ImageResult(
        file_path=relative_path,
        file_name=file_path.name,
        extension=file_path.suffix.lower(),
        file_size_bytes=file_path.stat().st_size,
    )
    drop_reasons: list[str] = []
    review_reasons: list[str] = []

    try:
        with Image.open(file_path) as image:
            image.load()  # Force full decoding so truncated data is detected here.
            oriented = ImageOps.exif_transpose(image)
            result.width, result.height = oriented.size
            result.mode = oriented.mode
            result.average_brightness = _brightness(oriented)

        result.sha256 = sha256_file(file_path)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        result.status = Status.ERROR
        result.reasons = f"unreadable_image: {type(error).__name__}"
        LOGGER.warning("Could not inspect %s: %s", relative_path, error)
        return result

    if result.width is not None and result.height is not None:
        if result.width < config.min_width or result.height < config.min_height:
            drop_reasons.append("low_resolution")

    if result.average_brightness is not None:
        if result.average_brightness < config.dark_threshold:
            review_reasons.append("dark_candidate")
        elif result.average_brightness > config.bright_threshold:
            review_reasons.append("bright_candidate")

    if drop_reasons:
        result.status = Status.DROP
        result.reasons = "; ".join(drop_reasons)
    elif review_reasons:
        result.status = Status.REVIEW
        result.reasons = "; ".join(review_reasons)
    return result


def mark_exact_duplicates(results: list[ImageResult]) -> None:
    originals: dict[str, ImageResult] = {}
    for result in results:
        if not result.sha256:
            continue
        original = originals.get(result.sha256)
        if original is None:
            originals[result.sha256] = result
            continue
        result.duplicate_of = original.file_path
        reasons = [reason for reason in result.reasons.split("; ") if reason]
        if "exact_duplicate" not in reasons:
            reasons.append("exact_duplicate")
        result.reasons = "; ".join(reasons)
        result.status = Status.DROP


def inspect_directory(input_dir: Path, config: CheckConfig) -> list[ImageResult]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    paths = discover_images(input_dir, config)
    LOGGER.info("Found %d supported image(s) in %s", len(paths), input_dir)
    results = [inspect_image(path, input_dir, config) for path in paths]
    mark_exact_duplicates(results)
    return results
