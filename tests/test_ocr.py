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

    def test_dark_mode_ocr_recognition(self):
        """Kiểm tra tiền xử lý ảnh nhận diện thành công chữ trên nền tối Dark mode"""
        img = Image.new("RGB", (320, 80), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((15, 25), "Dark Mode OCR Test", fill=(220, 220, 220))

        result = self.ocr.recognize(img)
        print(f"[Test Dark Mode OCR Result]: '{result}'")
        self.assertTrue(len(result) > 0, "Dark mode text should be recognized successfully")


if __name__ == "__main__":
    unittest.main()
