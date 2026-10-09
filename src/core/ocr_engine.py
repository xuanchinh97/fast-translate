import io
import re
from typing import Optional, List
from PIL import Image, ImageEnhance
import winocr


def unwrap_lines(lines: List[str]) -> str:
    """
    Unwraps broken lines from OCR into fluent natural paragraphs.
    Avoids sending fragmented lines to translation engine.
    """
    if not lines:
        return ""

    cleaned_blocks = []
    punctuation_ends = ('.', '!', '?', ':', ';', '"', '”', '…')

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if cleaned_blocks and not cleaned_blocks[-1].endswith(punctuation_ends):
            # Previous line didn't end with sentence-ending punctuation -> join with space
            cleaned_blocks[-1] += " " + line
        else:
            cleaned_blocks.append(line)

    return "\n".join(cleaned_blocks)


class OCREngine:
    def __init__(self, default_lang: str = "en"):
        self.default_lang = default_lang
        self.supported_langs = []
        self._init_languages()

    def _init_languages(self):
        """Discover available language recognizers on this Windows machine"""
        candidates = ["en-US", "en", "vi-VN", "vi", "zh-CN", "ja-JP", "ko-KR", "fr-FR", "de-DE"]
        for tag in candidates:
            try:
                if winocr.OcrEngine.is_language_supported(winocr.Language(tag)):
                    self.supported_langs.append(tag)
            except Exception:
                pass

        if not self.supported_langs:
            try:
                engine = winocr.OcrEngine.try_create_from_user_profile_languages()
                if engine and engine.recognizer_language:
                    self.supported_langs.append(engine.recognizer_language.language_tag)
            except Exception:
                pass

    def recognize(self, image_input, lang: Optional[str] = None) -> str:
        """
        Fast direct OCR recognition using Windows Media OCR WinRT operation.
        """
        if isinstance(image_input, (str, bytes)):
            if isinstance(image_input, str):
                img = Image.open(image_input)
            else:
                img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            raise ValueError(f"Unsupported image type: {type(image_input)}")

        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Determine target language
        target_lang = lang or self.default_lang
        if target_lang not in self.supported_langs and self.supported_langs:
            target_lang = self.supported_langs[0]

        try:
            # Direct WinRT call without asyncio loop / reflection overhead
            async_op = winocr.recognize_bytes(img.tobytes(), img.width, img.height, target_lang)
            ocr_result = async_op.get()

            # Extract lines and merge them into natural sentences
            if hasattr(ocr_result, "lines") and ocr_result.lines:
                raw_lines = [l.text for l in ocr_result.lines if l.text]
                result_text = unwrap_lines(raw_lines)
            else:
                result_text = getattr(ocr_result, "text", "")

            return result_text.strip()
        except Exception as e:
            print(f"[OCR] Fast recognize failed: {e}, attempting fallback...")
            try:
                fallback_res = winocr.recognize_pil_sync(img, target_lang)
                return fallback_res.get("text", "").strip()
            except Exception as e2:
                print(f"[OCR] Fallback failed: {e2}")
                return ""


# Singleton instance
ocr_engine = OCREngine()
