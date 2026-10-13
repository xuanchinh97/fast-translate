import os
import sys
import ctypes
import hashlib
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread, QRunnable, QThreadPool
from PySide6.QtTextToSpeech import QTextToSpeech

# Windows MCI audio player for mp3 playback
winmm = ctypes.windll.winmm


class TTSTask(QRunnable):
    def __init__(self, text: str, lang: str, cache_dir: Path, on_finish_callback=None):
        super().__init__()
        self.text = text
        self.lang = lang.lower()
        self.cache_dir = cache_dir
        self.on_finish = on_finish_callback

    def run(self):
        try:
            # Create hash for filename caching
            cache_key = hashlib.md5(f"{self.lang}:{self.text}".encode("utf-8")).hexdigest()
            mp3_path = self.cache_dir / f"{cache_key}.mp3"

            # Download if not in cache
            if not mp3_path.exists():
                encoded_q = urllib.parse.quote(self.text[:200])  # Limit to 200 chars for TTS safety
                url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={self.lang}&client=tw-ob&q={encoded_q}"
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    audio_data = resp.read()
                    with open(mp3_path, "wb") as f:
                        f.write(audio_data)

            # Play audio via Windows MCI
            winmm.mciSendStringW("close ft_tts", None, 0, None)
            open_cmd = f'open "{mp3_path.resolve()}" type mpegvideo alias ft_tts'
            if winmm.mciSendStringW(open_cmd, None, 0, None) == 0:
                winmm.mciSendStringW("play ft_tts wait", None, 0, None)
                winmm.mciSendStringW("close ft_tts", None, 0, None)
        except Exception as e:
            print(f"[TTS] Online audio playback failed: {e}")
        finally:
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
            self._qt_tts.stateChanged.connect(self._on_qt_state_changed)
        except Exception as e:
            print(f"[TTS] QTextToSpeech init failed: {e}")
            self._qt_tts = None

    def _on_qt_state_changed(self, state):
        if state == QTextToSpeech.State.Ready:
            self._is_speaking = False
            self.speaking_finished.emit()
        elif state == QTextToSpeech.State.Speaking:
            self._is_speaking = True
            self.speaking_started.emit()

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
        if self._qt_tts and self._qt_tts.state() == QTextToSpeech.State.Speaking:
            self._qt_tts.stop()
        try:
            winmm.mciSendStringW("stop ft_tts", None, 0, None)
            winmm.mciSendStringW("close ft_tts", None, 0, None)
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

        # If offline voice exists (e.g. English), use instant local QTextToSpeech
        if self.has_offline_voice_for(lang_code):
            # Select appropriate voice
            for v in self._qt_tts.availableVoices():
                if v.locale().name().split("_")[0].lower() == lang_code:
                    self._qt_tts.setVoice(v)
                    break
            self._is_speaking = True
            self.speaking_started.emit()
            self._qt_tts.say(text)
        else:
            # Otherwise use Google TTS audio via MCI
            self._is_speaking = True
            self.speaking_started.emit()
            task = TTSTask(
                text=text,
                lang=lang_code,
                cache_dir=self.cache_dir,
                on_finish_callback=self._on_online_tts_finished
            )
            self.thread_pool.start(task)

    def _on_online_tts_finished(self):
        self._is_speaking = False
        try:
            self.speaking_finished.emit()
        except RuntimeError:
            pass


# Singleton instance
tts_engine = TTSEngine()
