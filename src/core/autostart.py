import sys
import winreg
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FastTranslate"


def get_startup_command() -> str:
    """Returns the command line to launch FastTranslate silently on Windows startup"""
    project_root = Path(__file__).resolve().parent.parent.parent
    pythonw_exe = project_root / ".venv" / "Scripts" / "pythonw.exe"
    main_py = project_root / "src" / "main.py"
    return f'"{pythonw_exe}" "{main_py}"'


def is_autostart_enabled() -> bool:
    """Checks whether FastTranslate is registered to start with Windows"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        return False


def enable_autostart() -> bool:
    """Enables FastTranslate to start automatically when user logs in"""
    try:
        cmd = get_startup_command()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        return False


def disable_autostart() -> bool:
    """Removes FastTranslate from Windows startup"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
            return True
        except FileNotFoundError:
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        return False


def set_autostart(enable: bool) -> bool:
    if enable:
        return enable_autostart()
    else:
        return disable_autostart()
