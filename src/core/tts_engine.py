import os
import sys
import ctypes
import hashlib
import urllib.parse
import urllib.request
import subprocess
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from PySide6.QtTextToSpeech import QTextToSpeech

# Windows MCI audio player for mp3 playback
winmm = ctypes.windll.winmm


def get_short_path(path: Path) -> str:
    """Converts a Path to Windows 8.3 short path to avoid MCI issues with spaces/dots/unicode"""
    path_str = str(path.resolve())
    buf = ctypes.create_unicode_buffer(500)
    if ctypes.windll.kernel32.GetShortPathNameW(path_str, buf, 500) > 0:
        return buf.value
    return path_str


class TTSTask(QRunnable):
    def __init__(
        self,
        text: str,
        lang: str,
        cache_dir: Path,
        on_finish_callback: Optional[Callable] = None,
        offline_fallback_callback: Optional[Callable] = None,
    ):
        super().__init__()
        self.text = text
        self.lang = lang.lower()
        self.cache_dir = cache_dir
        self.on_finish = on_finish_callback
        self.offline_fallback = offline_fallback_callback

    def run(self):
        played_successfully = False
        try:
            # Create hash for filename caching
            cache_key = hashlib.md5(f"{self.lang}:{self.text}".encode("utf-8")).hexdigest()
            mp3_path = self.cache_dir / f"{cache_key}.mp3"

            # Download if not in cache
            if not mp3_path.exists():
                encoded_q = urllib.parse.quote(self.text[:250])  # Limit to 250 chars for TTS safety
                url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={self.lang}&client=tw-ob&q={encoded_q}"
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                with urllib.request.urlopen(req, timeout=4.5) as resp:
                    audio_data = resp.read()
                    with open(mp3_path, "wb") as f:
                        f.write(audio_data)

            # Play audio via Windows MCI
            short_path = get_short_path(mp3_path)
            winmm.mciSendStringW("close ft_tts", None, 0, None)
            open_cmd = f'open "{short_path}" type mpegvideo alias ft_tts'
            ret = winmm.mciSendStringW(open_cmd, None, 0, None)
            if ret != 0:
                # Try with resolved path as fallback
                open_cmd = f'open "{mp3_path.resolve()}" type mpegvideo alias ft_tts'
                ret = winmm.mciSendStringW(open_cmd, None, 0, None)

            if ret == 0:
                winmm.mciSendStringW("play ft_tts wait", None, 0, None)
                winmm.mciSendStringW("close ft_tts", None, 0, None)
                played_successfully = True
        except Exception as e:
            print(f"[TTS] High-quality audio playback failed: {e}")

        # If online / MCI failed (e.g. offline with no cached audio), trigger offline fallback
        if not played_successfully and self.offline_fallback:
            try:
                self.offline_fallback(self.text, self.lang)
            except Exception as ex:
                print(f"[TTS] Offline fallback failed: {ex}")

        if self.on_finish:
            try:
                self.on_finish()
            except RuntimeError:
                pass


class TTSEngine(QObject):
    speaking_started = Signal()
    speaking_finished = Signal()

    def __init__(self):
        super().__init__()
        self._qt_tts: Optional[QTextToSpeech] = None
        self._is_speaking = False
        self.cache_dir = Path.home() / ".fast_translate" / "tts_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thread_pool = QThreadPool.globalInstance()

        self._init_qt_tts()

    def _init_qt_tts(self):
        try:
            self._qt_tts = QTextToSpeech()
        except Exception as e:
            print(f"[TTS] QTextToSpeech init failed: {e}")
            self._qt_tts = None

    def has_offline_voice_for(self, lang_code: str) -> bool:
        """Check if local Windows SAPI voice exists for given language code (e.g. 'en')"""
        if not self._qt_tts:
            return False
        lang_prefix = lang_code.split("-")[0].lower()
        for v in self._qt_tts.availableVoices():
            v_lang = v.locale().name().split("_")[0].lower()
            if v_lang == lang_prefix:
                return True
        return False

    def is_speaking(self) -> bool:
        return self._is_speaking

    def stop(self):
        try:
            winmm.mciSendStringW("stop ft_tts", None, 0, None)
            winmm.mciSendStringW("close ft_tts", None, 0, None)
        except Exception:
            pass
        if self._qt_tts and self._qt_tts.state() == QTextToSpeech.State.Speaking:
            try:
                self._qt_tts.stop()
            except Exception:
                pass
        self._is_speaking = False
        self.speaking_finished.emit()

    def speak(self, text: str, lang: str = "en"):
        text = text.strip()
        if not text:
            return

        self.stop()
        lang_code = lang.lower().split("-")[0].strip()

        self._is_speaking = True
        self.speaking_started.emit()

        # Primary engine: Natural voice with caching and MCI audio playback
        task = TTSTask(
            text=text,
            lang=lang_code,
            cache_dir=self.cache_dir,
            on_finish_callback=self._on_tts_finished,
            offline_fallback_callback=self._speak_offline_fallback
        )
        self.thread_pool.start(task)

    def _speak_offline_fallback(self, text: str, lang_code: str):
        """Offline fallback using Windows SAPI / PowerShell"""
        print(f"[TTS] Invoking offline voice fallback for lang={lang_code}...")
        try:
            escaped = text.replace("'", "''")[:200]
            cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{escaped}')"
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                creationflags=flags,
                timeout=8
            )
        except Exception as e:
            print(f"[TTS] Offline fallback failed: {e}")

    def _on_tts_finished(self):
        self._is_speaking = False
        try:
            self.speaking_finished.emit()
        except RuntimeError:
            pass


# Singleton instance
tts_engine = TTSEngine()
