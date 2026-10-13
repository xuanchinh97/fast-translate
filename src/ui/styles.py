# Modern stylesheet for FastTranslate Popup and Widgets

DARK_THEME = """
QWidget#MainCard {
    background-color: #1e1e24;
    border: 1px solid #33333d;
    border-radius: 12px;
}

QLabel {
    color: #f0f0f5;
    font-family: "Segoe UI", "Roboto", sans-serif;
}

QLabel#HeaderTitle {
    font-size: 11px;
    font-weight: 600;
    color: #9292a0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#LangBadge {
    background-color: #2b2b36;
    color: #60a5fa;
    border: 1px solid #3b3b4a;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QTextEdit#SourceText {
    background-color: #24242e;
    border: 1px solid #3d3d4e;
    border-radius: 8px;
    color: #f1f5f9;
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 12px;
    padding: 6px 8px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QTextEdit#SourceText:focus {
    border: 1px solid #3b82f6;
    background-color: #292936;
}

QTextEdit#TranslatedText {
    background-color: transparent;
    border: none;
    color: #ffffff;
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 14px;
    font-weight: 500;
    padding: 4px;
}

QPushButton {
    background-color: #2b2b36;
    border: 1px solid #3b3b4a;
    border-radius: 6px;
    color: #d1d1dc;
    font-family: "Segoe UI", sans-serif;
    font-size: 11px;
    font-weight: 500;
    padding: 4px 10px;
}

QPushButton:hover {
    background-color: #383848;
    color: #ffffff;
    border-color: #4f4f63;
}

QPushButton:pressed {
    background-color: #1f1f28;
}

QPushButton#IconButton {
    background-color: transparent;
    border: none;
    color: #8a8a9a;
    padding: 2px;
    font-size: 13px;
    border-radius: 4px;
}

QPushButton#IconButton:hover {
    background-color: #2f2f3d;
    color: #ffffff;
}

QPushButton#SmallActionButton {
    background-color: #2b2b38;
    border: 1px solid #3d3d4e;
    border-radius: 5px;
    color: #a1a1aa;
    font-size: 10px;
    padding: 2px 7px;
    font-weight: 500;
}

QPushButton#SmallActionButton:hover {
    background-color: #38384a;
    color: #ffffff;
    border-color: #60a5fa;
}

QPushButton#SmallActionButton:pressed {
    background-color: #20202a;
}

QPushButton#SwapButton {
    background-color: #262632;
    border: 1px solid #3d3d4e;
    border-radius: 5px;
    color: #60a5fa;
    font-size: 13px;
    font-weight: bold;
    padding: 1px 7px;
}

QPushButton#SwapButton:hover {
    background-color: #3b82f6;
    color: #ffffff;
    border-color: #60a5fa;
}

QPushButton#LangBadgeBtn {
    background-color: #262632;
    color: #60a5fa;
    border: 1px solid #3d3d4e;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}

QPushButton#LangBadgeBtn:hover {
    background-color: #323242;
    border-color: #60a5fa;
    color: #93c5fd;
}

QMenu {
    background-color: #1e1e24;
    border: 1px solid #3b3b4a;
    border-radius: 8px;
    padding: 4px;
    color: #f0f0f5;
}

QMenu::item {
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 11px;
    color: #e2e8f0;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QPushButton#PinButton[pinned="true"] {
    background-color: #2563eb;
    color: #ffffff;
}

QPushButton#CopyButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-weight: 600;
}

QPushButton#CopyButton:hover {
    background-color: #3b82f6;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3e3e4f;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #5a5a70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
