import unittest
from PIL import Image, ImageDraw, ImageFont
from src.core.ocr_engine import OCREngine


class TestOCREngine(unittest.TestCase):
    def setUp(self):
        self.ocr = OCREngine()

    def test_ocr_recognition(self):
        # Create a high-contrast test image with clear text
        img = Image.new("RGB", (320, 80), color="white")
        draw = ImageDraw.Draw(img)
        # Using default bitmap font or basic text
        draw.text((15, 25), "Artificial Intelligence", fill="black")

        result = self.ocr.recognize(img)
        print(f"[Test OCR Result]: '{result}'")
        self.assertTrue(len(result) > 0)
        # At least one word should match
        self.assertTrue(
            "artificial" in result.lower() or "intelligence" in result.lower(),
            f"Expected 'Artificial' or 'Intelligence' in '{result}'"
        )


if __name__ == "__main__":
    unittest.main()
