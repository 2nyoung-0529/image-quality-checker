"""규칙 기반 이미지 품질 사전 검사기."""

from .checker import CheckConfig, ImageResult, inspect_directory

__all__ = ["CheckConfig", "ImageResult", "inspect_directory"]
__version__ = "1.0.0"
