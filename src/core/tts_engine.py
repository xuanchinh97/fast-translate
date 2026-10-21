import os
import sys
import re
import time
import ctypes
import hashlib
import urllib.parse
import urllib.request
import subprocess
from pathlib import Path
from typing import Optional, Callable, List

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


def split_text_into_chunks(text: str, max_chars: int = 180) -> List[str]:
    """
    Chia đoạn văn bản dài thành các phân đoạn ngắn tự nhiên theo dấu câu hoặc từ,
    đảm bảo URL request đến Google TTS không bị tràn giới hạn và đọc trọn vẹn văn bản.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    # Tách theo ranh giới câu (. ! ? ; \n)
    raw_sentences = re.split(r"(?<=[.!?;\n])\s+", text)
    chunks: List[str] = []
    current_chunk = ""

    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) > max_chars:
            # Nếu trước đó đang có current_chunk gom dở, flush ra trước để bảo toàn thứ tự
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # Câu đơn lẻ quá dài -> tách theo từ
            words = s.split(" ")
            sub_chunk = ""
            for w in words:
                if not w:
                    continue
                if len(sub_chunk) + len(w) + 1 <= max_chars:
                    sub_chunk = (sub_chunk + " " + w).strip()
                else:
                    if sub_chunk:
                        chunks.append(sub_chunk)
                    sub_chunk = w
            if sub_chunk:
                chunks.append(sub_chunk)
        else:
            if len(current_chunk) + len(s) + 1 <= max_chars:
                current_chunk = (current_chunk + " " + s).strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = s

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


class TTSTask(QRunnable):
    def __init__(
        self,
        text: str,
        lang: str,
        cache_dir: Path,
        generation: int,
        is_generation_active_callback: Callable[[int], bool],
        on_finish_callback: Optional[Callable[[int], None]] = None,
        offline_fallback_callback: Optional[Callable[[str, str, int], None]] = None,
    ):
        super().__init__()
        self.text = text
        self.lang = lang.lower()
        self.cache_dir = cache_dir
        self.generation = generation
        self.is_active = is_generation_active_callback
        self.on_finish = on_finish_callback
        self.offline_fallback = offline_fallback_callback

    def _download_chunk(self, chunk_text: str) -> Optional[Path]:
        cache_key = hashlib.md5(f"{self.lang}:{chunk_text}".encode("utf-8")).hexdigest()
        mp3_path = self.cache_dir / f"{cache_key}.mp3"
        if mp3_path.exists() and mp3_path.stat().st_size > 0:
            return mp3_path

        try:
            encoded_q = urllib.parse.quote(chunk_text)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={self.lang}&client=tw-ob&q={encoded_q}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                audio_data = resp.read()
                if audio_data:
                    with open(mp3_path, "wb") as f:
                        f.write(audio_data)
                    return mp3_path
        except Exception as e:
            print(f"[TTS] Download chunk failed: {e}")
        return None

    def run(self):
        if not self.is_active(self.generation):
            return

        chunks = split_text_into_chunks(self.text, max_chars=180)
        if not chunks:
            if self.on_finish:
                self.on_finish(self.generation)
            return

        played_any = False
        all_success = True

        for idx, chunk in enumerate(chunks):
            if not self.is_active(self.generation):
                all_success = False
                break

            mp3_path = self._download_chunk(chunk)
            if not mp3_path or not mp3_path.exists():
                all_success = False
                break

            if not self.is_active(self.generation):
                all_success = False
                break

            # Play audio via Windows MCI with unique alias per task
            alias = f"ft_tts_{self.generation}_{idx}"
            short_path = get_short_path(mp3_path)
            winmm.mciSendStringW(f"close {alias}", None, 0, None)
            open_cmd = f'open "{short_path}" type mpegvideo alias {alias}'
            ret = winmm.mciSendStringW(open_cmd, None, 0, None)
            if ret != 0:
                open_cmd = f'open "{mp3_path.resolve()}" type mpegvideo alias {alias}'
                ret = winmm.mciSendStringW(open_cmd, None, 0, None)

            if ret == 0:
                # Non-blocking play kèm polling loop để ngắt tức thì khi user bấm Dừng (<40ms)
                winmm.mciSendStringW(f"play {alias}", None, 0, None)
                status_buf = ctypes.create_unicode_buffer(128)
                while True:
                    if not self.is_active(self.generation):
                        winmm.mciSendStringW(f"stop {alias}", None, 0, None)
                        winmm.mciSendStringW(f"close {alias}", None, 0, None)
                        all_success = False
                        break
                    winmm.mciSendStringW(f"status {alias} mode", status_buf, 128, None)
                    mode = status_buf.value.lower()
                    if mode in ("stopped", ""):
                        winmm.mciSendStringW(f"close {alias}", None, 0, None)
                        played_any = True
                        break
                    time.sleep(0.04)

                if not self.is_active(self.generation):
                    all_success = False
                    break
            else:
                all_success = False
                break

        # Nếu online / MCI không phát được mẩu nào (e.g. offline không có cache), kích hoạt offline fallback
        if not played_any and self.is_active(self.generation) and self.offline_fallback:
            try:
                self.offline_fallback(self.text, self.lang, self.generation)
            except Exception as ex:
                print(f"[TTS] Offline fallback failed: {ex}")

        if self.on_finish:
            try:
                self.on_finish(self.generation)
            except RuntimeError:
                pass


class TTSEngine(QObject):
    speaking_started = Signal()
    speaking_finished = Signal()

    def __init__(self):
        super().__init__()
        self._qt_tts: Optional[QTextToSpeech] = None
        self._is_speaking = False
        self._current_generation = 0
        self._offline_process: Optional[subprocess.Popen] = None
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

    def _is_generation_active(self, gen: int) -> bool:
        return self._is_speaking and self._current_generation == gen

    def stop(self):
        self._current_generation += 1
        try:
            winmm.mciSendStringW("stop all", None, 0, None)
            winmm.mciSendStringW("close all", None, 0, None)
        except Exception:
            pass
        if self._qt_tts and self._qt_tts.state() == QTextToSpeech.State.Speaking:
            try:
                self._qt_tts.stop()
            except Exception:
                pass
        if self._offline_process and self._offline_process.poll() is None:
            try:
                self._offline_process.terminate()
                self._offline_process.kill()
            except Exception:
                pass
            self._offline_process = None
        if self._is_speaking:
            self._is_speaking = False
            self.speaking_finished.emit()

    def speak(self, text: str, lang: str = "en"):
        text = text.strip()
        if not text:
            return

        self.stop()
        lang_code = lang.lower().split("-")[0].strip()

        self._is_speaking = True
        gen = self._current_generation
        self.speaking_started.emit()

        # Primary engine: Natural voice with chunking, caching and MCI audio playback
        task = TTSTask(
            text=text,
            lang=lang_code,
            cache_dir=self.cache_dir,
            generation=gen,
            is_generation_active_callback=self._is_generation_active,
            on_finish_callback=self._on_tts_finished,
            offline_fallback_callback=self._speak_offline_fallback,
        )
        self.thread_pool.start(task)

    def _speak_offline_fallback(self, text: str, lang_code: str, gen: int):
        """Offline fallback using Windows SAPI / PowerShell with immediate interrupt support"""
        if not self._is_generation_active(gen):
            return
        print(f"[TTS] Invoking offline voice fallback for lang={lang_code}...")
        try:
            escaped = text.replace("'", "''")[:300]
            cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{escaped}')"
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                creationflags=flags,
            )
            self._offline_process = proc
            while proc.poll() is None:
                if not self._is_generation_active(gen):
                    try:
                        proc.terminate()
                        proc.kill()
                    except Exception:
                        pass
                    break
                time.sleep(0.05)
            self._offline_process = None
        except Exception as e:
            print(f"[TTS] Offline fallback failed: {e}")

    def _on_tts_finished(self, gen: int):
        if self._current_generation == gen and self._is_speaking:
            self._is_speaking = False
            try:
                self.speaking_finished.emit()
            except RuntimeError:
                pass


# Singleton instance
tts_engine = TTSEngine()
