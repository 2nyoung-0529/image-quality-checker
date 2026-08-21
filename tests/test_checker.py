import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_quality_checker.checker import CheckConfig, Status, inspect_directory


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_image(self, name: str, size=(400, 400), color=(128, 128, 128)) -> Path:
        path = self.root / name
        Image.new("RGB", size, color).save(path)
        return path

    def test_flags_low_resolution(self):
        self.make_image("small.png", size=(100, 400))
        result = inspect_directory(self.root, CheckConfig())[0]
        self.assertEqual(result.status, Status.DROP)
        self.assertIn("low_resolution", result.reasons)

    def test_flags_dark_image_for_review(self):
        self.make_image("dark.png", color=(10, 10, 10))
        result = inspect_directory(self.root, CheckConfig())[0]
        self.assertEqual(result.status, Status.REVIEW)
        self.assertEqual(result.reasons, "dark_candidate")

    def test_marks_exact_duplicate(self):
        first = self.make_image("a.png")
        (self.root / "b.png").write_bytes(first.read_bytes())
        results = inspect_directory(self.root, CheckConfig())
        self.assertEqual(results[0].status, Status.PASS)
        self.assertEqual(results[1].status, Status.DROP)
        self.assertEqual(results[1].duplicate_of, "a.png")

    def test_reports_invalid_image(self):
        (self.root / "broken.png").write_text("not an image", encoding="utf-8")
        result = inspect_directory(self.root, CheckConfig())[0]
        self.assertEqual(result.status, Status.ERROR)
        self.assertIn("unreadable_image", result.reasons)


if __name__ == "__main__":
    unittest.main()
