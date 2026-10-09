import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache
from src.config import config


@dataclass
class TranslationResult:
    original: str
    translated: str
    source_lang: str
    target_lang: str
    success: bool
    error_message: Optional[str] = None


class Translator:
    def __init__(self):
        self.default_source = config.get("source_lang", "auto")
        self.default_target = config.get("target_lang", "vi")

    def _translate_google_dict_chrome(self, text: str, src: str, tgt: str) -> tuple[str, str]:
        """
        Ultra-fast Google Translate endpoint used by Chrome dictionary extension.
        Returns (translated_text, detected_src_lang).
        """
        encoded_text = urllib.parse.quote(text)
        url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={src}&tl={tgt}&q={encoded_text}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
            }
        )
        with urllib.request.urlopen(req, timeout=3.5) as response:
            content = response.read().decode("utf-8")
            data = json.loads(content)
            # Format can be: [["translated text", "detected_lang"]] or ["translated text"]
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, str):
                    return first, src
                elif isinstance(first, list) and len(first) >= 1:
                    translated = first[0]
                    detected_lang = first[1] if len(first) > 1 else src
                    return translated, detected_lang
            elif isinstance(data, str):
                return data, src
            raise ValueError(f"Unexpected response format: {content[:100]}")

    def _translate_mymemory(self, text: str, src: str, tgt: str) -> tuple[str, str]:
        """Fallback translation via MyMemory API"""
        from_lang = "en" if src == "auto" else src
        encoded_text = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={from_lang}|{tgt}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
            if "responseData" in data and "translatedText" in data["responseData"]:
                return data["responseData"]["translatedText"], from_lang
            raise ValueError("MyMemory returned invalid data")

    @lru_cache(maxsize=1024)
    def translate_cached(self, text: str, src: str, tgt: str) -> tuple[str, str, bool, Optional[str]]:
        """Internal cached translation worker"""
        text = text.strip()
        if not text:
            return "", src, True, None

        # Try Google Dict Chrome endpoint first
        try:
            translated, detected = self._translate_google_dict_chrome(text, src, tgt)
            return translated, detected, True, None
        except Exception as e1:
            print(f"[Translator] Google primary failed: {e1}, attempting fallback...")

        # Fallback to MyMemory
        try:
            translated, detected = self._translate_mymemory(text, src, tgt)
            return translated, detected, True, None
        except Exception as e2:
            print(f"[Translator] Fallback failed: {e2}")
            return "", src, False, f"Lỗi dịch thuật: Không thể kết nối máy chủ dịch ({e1})"

    def translate(self, text: str, src: Optional[str] = None, tgt: Optional[str] = None) -> TranslationResult:
        """
        Public method to translate text.
        """
        src = src or config.get("source_lang", "auto")
        tgt = tgt or config.get("target_lang", "vi")

        translated, detected, success, err = self.translate_cached(text, src, tgt)
        return TranslationResult(
            original=text,
            translated=translated if success else "",
            source_lang=detected.upper() if detected else src.upper(),
            target_lang=tgt.upper(),
            success=success,
            error_message=err
        )


# Singleton instance
translator = Translator()
