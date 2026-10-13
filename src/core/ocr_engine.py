import io
import re
from typing import Optional, List
from PIL import Image, ImageEnhance, ImageOps
import winocr


def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Tiền xử lý ảnh giúp tăng độ chính xác của WinOCR:
    1. Tự động phóng to nếu vùng chọn quá nhỏ (Upscale bằng LANCZOS).
    2. Chuyển sang ảnh đa cấp xám (Grayscale).
    3. Cân bằng độ tương phản tự động (Auto-contrast).
    4. Tăng cường độ tương phản nhẹ tách chữ rõ ràng khỏi nền mờ / gradient.
    """
    w, h = img.size
    # 1. Phóng to nếu vùng ảnh nhỏ để đảm bảo chiều cao ký tự đủ cho OCR
    if w < 400 or h < 120:
        scale = max(1.5, min(2.5, 600.0 / max(w, 1)))
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 2. Chuyển sang Grayscale
    gray = img.convert("L")

    # 3. Tự động kéo dãn histogram để tăng tương phản
    try:
        enhanced = ImageOps.autocontrast(gray)
    except Exception:
        enhanced = gray

    # 4. Tăng cường nhẹ độ sắc nét tương phản
    try:
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(1.2)
    except Exception:
        pass

    # 5. Chuyển sang RGBA cho WinOCR
    return enhanced.convert("RGBA")


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
        if not self.supported_langs:
            self.supported_langs.append("en")

    def _recognize_single(self, img_rgba: Image.Image, target_lang: str) -> str:
        """Thực hiện 1 lượt nhận diện trên ảnh RGBA"""
        try:
            async_op = winocr.recognize_bytes(img_rgba.tobytes(), img_rgba.width, img_rgba.height, target_lang)
            ocr_result = async_op.get()

            if hasattr(ocr_result, "lines") and ocr_result.lines:
                raw_lines = [l.text for l in ocr_result.lines if l.text]
                result_text = unwrap_lines(raw_lines)
            else:
                result_text = getattr(ocr_result, "text", "")

            return result_text.strip()
        except Exception:
            try:
                fallback_res = winocr.recognize_pil_sync(img_rgba, target_lang)
                return fallback_res.get("text", "").strip()
            except Exception:
                return ""

    def recognize(self, image_input, lang: Optional[str] = None) -> str:
        """
        Nhận diện văn bản đa tầng với tiền xử lý ảnh tự động:
        1. Lượt 1: Ảnh gốc nguyên bản.
        2. Lượt 2: Ảnh tiền xử lý (tăng tương phản, upscale, grayscale).
        3. Lượt 3: Ảnh đảo màu (Inverted polarity cho trường hợp nền tối chữ sáng).
        Lựa chọn kết quả nhận diện đầy đủ và chính xác nhất.
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

        target_lang = lang or self.default_lang
        if target_lang not in self.supported_langs and self.supported_langs:
            target_lang = self.supported_langs[0]

        candidates: List[str] = []

        # --- Lượt 1: Thử trực tiếp trên ảnh gốc ---
        try:
            if img.mode != "RGBA":
                raw_rgba = img.convert("RGBA")
            else:
                raw_rgba = img
            text_raw = self._recognize_single(raw_rgba, target_lang)
            if text_raw:
                candidates.append(text_raw)
        except Exception as e:
            print(f"[OCR] Raw pass error: {e}")

        # --- Lượt 2: Tiền xử lý tăng cường tương phản + upscale ---
        try:
            enhanced = preprocess_image(img)
            text_enh = self._recognize_single(enhanced, target_lang)
            if text_enh:
                candidates.append(text_enh)
        except Exception as e:
            print(f"[OCR] Enhanced pass error: {e}")

        # --- Lượt 3: Thử đảo màu (cho ảnh chụp Dark Mode nền đen chữ trắng) ---
        try:
            inverted = ImageOps.invert(img.convert("L")).convert("RGBA")
            text_inv = self._recognize_single(inverted, target_lang)
            if text_inv:
                candidates.append(text_inv)
        except Exception:
            pass

        if not candidates:
            return ""

        # Chọn kết quả có độ dài và độ hoàn chỉnh tốt nhất
        return max(candidates, key=lambda s: len(s.strip()))


# Singleton instance
ocr_engine = OCREngine()
