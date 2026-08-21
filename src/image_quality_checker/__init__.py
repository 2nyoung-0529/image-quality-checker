"""Rule-based image quality pre-checker."""

from .checker import CheckConfig, ImageResult, inspect_directory

__all__ = ["CheckConfig", "ImageResult", "inspect_directory"]
__version__ = "1.0.0"
