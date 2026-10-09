import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "hotkey_text": "alt+d",
    "hotkey_ocr": "alt+shift+d",
    "source_lang": "auto",
    "target_lang": "vi",
    "restore_clipboard": True,
    "auto_close_on_focus_loss": True,
    "theme": "dark",
    "font_size": 13,
    "window_width": 380,
    "window_height": 260,
    "autostart_with_windows": True
}

CONFIG_DIR = Path.home() / ".fast_translate"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
        except Exception as e:
            print(f"[Config] Error loading config: {e}")

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


# Global config instance
config = Config()
