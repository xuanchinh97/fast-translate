import unittest
from src.core.translator import Translator


class TestTranslator(unittest.TestCase):
    def setUp(self):
        self.translator = Translator()

    def test_translate_english_to_vietnamese(self):
        result = self.translator.translate("Hello world", src="en", tgt="vi")
        self.assertTrue(result.success)
        self.assertIn("chào", result.translated.lower())

    def test_translate_auto_detection(self):
        result = self.translator.translate("Good morning! Have a nice day.", src="auto", tgt="vi")
        self.assertTrue(result.success)
        self.assertGreater(len(result.translated), 0)

    def test_empty_string(self):
        result = self.translator.translate("", src="en", tgt="vi")
        self.assertTrue(result.success)
        self.assertEqual(result.translated, "")

    def test_caching(self):
        # First call
        res1 = self.translator.translate("Fast and smooth translation", src="en", tgt="vi")
        # Second call should hit LRU cache immediately
        res2 = self.translator.translate("Fast and smooth translation", src="en", tgt="vi")
        self.assertEqual(res1.translated, res2.translated)


if __name__ == "__main__":
    unittest.main()
