#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScreenDrawing
Version: 1.7.3
Author: Jeong SeongYong
Email: iyagicom@gmail.com
Description: Lightweight screen drawing tool for Linux and Windows
             (pen, shapes, text, highlight, eraser, undo, screenshot)
License: GPL-2.0-or-later
"""

# ────────────────────────────────────────────────
#  표준 라이브러리
# ────────────────────────────────────────────────
import sys
import os
import json
import locale
import math
import subprocess
from datetime import datetime

# ────────────────────────────────────────────────
#  PyQt5
# ────────────────────────────────────────────────
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QPixmap, QBrush, QFont, QPolygonF,
)

# ────────────────────────────────────────────────
#  Windows API (Windows 전용)
# ────────────────────────────────────────────────
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    GWL_EXSTYLE        = -20
    WS_EX_LAYERED      = 0x00080000
    WS_EX_TRANSPARENT  = 0x00000020
    SWP_NOMOVE         = 0x0002
    SWP_NOSIZE         = 0x0001
    HWND_TOPMOST       = -1

    SetWindowPos  = ctypes.windll.user32.SetWindowPos
    SetWindowLong = ctypes.windll.user32.SetWindowLongW
    GetWindowLong = ctypes.windll.user32.GetWindowLongW


# ════════════════════════════════════════════════
#  전역 상수
# ════════════════════════════════════════════════

# 툴바 높이(px) — 이 값 아래부터 캔버스 드로잉 영역
TOOLBAR_HEIGHT = 58

# 실행취소 최대 단계 수
MAX_UNDO_STEPS = 50

# 유효한 그리기 도구 목록 (설정 저장/복원 검증에도 사용)
VALID_TOOLS = ("pen", "rect", "ellipse", "line", "arrow", "text")

# 설정 파일 경로 (OS별 표준 위치)
if sys.platform == "win32":
    _CFG_DIR = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")), "screendrawing"
    )
else:
    _CFG_DIR = os.path.join(
        os.path.expanduser("~"), ".local", "share", "screendrawing"
    )
os.makedirs(_CFG_DIR, exist_ok=True)
SETTINGS_PATH = os.path.join(_CFG_DIR, "settings.json")

# 각 도구의 (아이콘, accent 색상) 매핑
#   - 도구 버튼 강조(active/toggle ON) 색에 사용
ICONS = {
    "pen":       ("✏",  "#4FC3F7"),   # 하늘색
    "rect":      ("▭",  "#81C784"),   # 초록
    "ellipse":   ("◯",  "#CE93D8"),   # 보라
    "line":      ("╱",  "#FFB74D"),   # 주황
    "arrow":     ("➔",  "#FF8A65"),   # 살몬
    "text":      ("T",  "#F48FB1"),   # 핑크
    "eraser":    ("◻",  "#FF9800"),   # 주황 (지우개 ON 강조색)
    "fill":      ("■",  "#AB47BC"),   # 보라 (채우기 ON 강조색)
    "highlight": ("▌",  "#FFD600"),   # 노랑 (형광 ON 강조색)
}


# ════════════════════════════════════════════════
#  언어 감지 및 번역
# ════════════════════════════════════════════════

def _detect_language() -> str:
    """
    시스템 환경변수(LANG·LANGUAGE·LC_ALL·LC_MESSAGES)와
    locale 설정을 순서대로 확인해 한국어(ko) 또는 영어(en)를 반환한다.
    """
    for env in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        if os.environ.get(env, "").lower().startswith("ko"):
            return "ko"
    try:
        code = locale.getlocale()[0]
        if code and code.lower().startswith("ko"):
            return "ko"
    except Exception:
        pass
    return "en"


# 모듈 로드 시 1회 결정
LANG: str = _detect_language()


def tr(ko: str, en: str) -> str:
    """LANG 값에 따라 한국어 또는 영어 문자열을 반환한다."""
    return ko if LANG == "ko" else en


# ════════════════════════════════════════════════
#  버튼 QSS 스타일 상수 및 생성 함수
# ════════════════════════════════════════════════

# 기본 버튼 QSS 템플릿 — {pad} 자리에 padding 값을 채워 파생 상수 생성
_BTN_BASE = """
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255,255,255,18), stop:1 rgba(255,255,255,6));
        border: 1px solid rgba(255,255,255,14);
        border-radius: 8px;
        color: rgba(220,225,240,200);
        font-size: 14px;
        font-weight: 500;
        letter-spacing: 0.3px;
        padding: {pad};
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255,255,255,32), stop:1 rgba(255,255,255,14));
        border: 1px solid rgba(255,255,255,28);
        color: rgba(255,255,255,240);
    }}
    QPushButton:pressed {{
        background: rgba(0,0,0,30);
        border: 1px solid rgba(255,255,255,10);
    }}
"""

_BTN_TOOL = _BTN_BASE.format(pad="0px 10px")   # 텍스트 있는 일반 도구 버튼
_BTN_ICON = _BTN_BASE.format(pad="0px 6px")    # 숫자/아이콘 전용 정방형 버튼

# 그리기 버튼: ON(초록) / OFF(주황) 두 가지 상태
_BTN_DRAWING_ON = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(80,180,120,80), stop:1 rgba(50,140,80,40));
        border: 1px solid rgba(100,220,140,120);
        border-radius: 8px;
        color: rgba(140,240,170,230);
        font-size: 14px;
        padding: 0px 12px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(100,210,140,130), stop:1 rgba(60,160,100,70));
        border: 1px solid rgba(120,255,160,200);
        color: #FFFFFF;
    }
    QPushButton:pressed { background: rgba(30,100,60,100); }
"""

_BTN_DRAWING_OFF = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(220,140,40,100), stop:1 rgba(180,100,20,60));
        border: 1px solid rgba(255,180,60,160);
        border-radius: 8px;
        color: rgba(255,210,120,240);
        font-size: 14px;
        padding: 0px 12px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255,170,60,150), stop:1 rgba(200,120,30,90));
        border: 1px solid rgba(255,210,80,220);
        color: #FFFFFF;
    }
    QPushButton:pressed { background: rgba(120,60,10,100); }
"""

# 종료 버튼 (빨간 포인트)
_BTN_EXIT = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(220,50,50,80), stop:1 rgba(180,30,30,40));
        border: 1px solid rgba(240,80,80,120);
        border-radius: 8px;
        color: rgba(255,140,140,230);
        font-size: 14px;
        padding: 0px 12px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(240,70,70,130), stop:1 rgba(200,40,40,70));
        border: 1px solid rgba(255,100,100,200);
        color: #FFFFFF;
    }
    QPushButton:pressed { background: rgba(150,20,20,100); }
"""


def _accent_rgb(hex_color: str) -> tuple[int, int, int]:
    """
    '#RRGGBB' 문자열을 (R, G, B) 정수 튜플로 변환한다.
    Qt CSS는 8자리 #RRGGBBAA를 미지원하므로 rgba()로 변환할 때 사용.
    """
    return (
        int(hex_color[1:3], 16),
        int(hex_color[3:5], 16),
        int(hex_color[5:7], 16),
    )


def _active_style(accent: str) -> str:
    """
    선택된 도구 버튼에 적용하는 accent 글로우 스타일을 생성한다.
    (도구 선택 강조 — 토글 ON보다 더 진하게 표시)
    """
    r, g, b = _accent_rgb(accent)
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba({r},{g},{b},0.33), stop:1 rgba({r},{g},{b},0.13));
            border: 1px solid rgba({r},{g},{b},0.73);
            border-radius: 8px;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.3px;
            padding: 0px 10px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba({r},{g},{b},0.47), stop:1 rgba({r},{g},{b},0.2));
            border: 1px solid rgba({r},{g},{b},0.93);
        }}
    """


def _toggle_on_style(accent: str) -> str:
    """
    토글 버튼(채우기·형광·지우개) ON 상태에 적용하는 스타일을 생성한다.
    _active_style 보다 약하게 표시해 '도구 선택'과 시각적으로 구분한다.
    """
    r, g, b = _accent_rgb(accent)
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba({r},{g},{b},0.27), stop:1 rgba({r},{g},{b},0.09));
            border: 1px solid rgba({r},{g},{b},0.6);
            border-radius: 8px;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.3px;
            padding: 0px 10px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba({r},{g},{b},0.4), stop:1 rgba({r},{g},{b},0.16));
        }}
    """


# ════════════════════════════════════════════════
#  FloatingTextInput — 캔버스 위 투명 텍스트 입력창
# ════════════════════════════════════════════════

class FloatingTextInput(QtWidgets.QTextEdit):
    """
    캔버스 위에 떠 있는 투명 텍스트 입력창.

    키 동작:
      Enter         → 줄바꿈
      Ctrl + Enter  → 입력 확정 (editingFinished 신호 발생)
      Escape        → 내용 삭제 후 취소 (editingFinished 신호 발생)

    시각 특징:
      - 배경·테두리 없이 현재 펜 색상으로 텍스트를 표시한다.
      - 각 줄 아래에 얇은 밑줄을 직접 그려 입력 범위를 표시한다.
      - 내용이 늘어나면 너비·높이를 자동 조절한다.
    """

    # QLineEdit.editingFinished 와 동일한 역할
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget, pos: QPoint,
                 font: QFont, color: QColor) -> None:
        super().__init__(parent)

        # 캔버스에 그릴 때 재사용하는 속성 저장
        self._pos   = pos
        self._font  = font
        self._color = color

        self.setFont(font)
        self.setStyleSheet(
            f"QTextEdit {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  color: {color.name()};"
            f"  padding: 0px;"
            f"}}"
        )

        line_h = self.fontMetrics().height()
        self.move(pos.x(), pos.y() - line_h)

        # 초기 너비: 화면 오른쪽 끝까지 확보해 자동 줄바꿈 방지
        screen_w = parent.width() if parent else 1920
        self.setFixedSize(max(screen_w - pos.x() - 20, 400), line_h + 10)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)  # Enter 키로만 줄바꿈

        self.textChanged.connect(self._adjust_size)
        self.setFocus()
        self.show()

    # ── 렌더링 ──────────────────────────────────

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """기본 렌더링 후, 각 줄 텍스트 아래에 색상 밑줄을 추가로 그린다."""
        super().paintEvent(event)

        fm     = self.fontMetrics()
        lines  = self.toPlainText().split('\n')
        line_h = fm.height()

        p = QPainter(self.viewport())
        p.setPen(QPen(self._color, 2))
        for i, line in enumerate(lines):
            # 텍스트 너비만큼만 밑줄 표시 (최소 10 px)
            w = max(fm.horizontalAdvance(line) + 4, 10)
            p.drawLine(0, (i + 1) * line_h + 2, w, (i + 1) * line_h + 2)
        p.end()

    # ── 크기 자동 조절 ───────────────────────────

    def _adjust_size(self) -> None:
        """텍스트 내용에 따라 입력창 너비·높이를 자동으로 조절한다."""
        lines  = self.toPlainText().split('\n')
        fm     = self.fontMetrics()
        line_h = fm.height()

        # 너비: 가장 긴 줄 기준, 오른쪽 화면 끝을 넘지 않도록 제한
        max_w       = max((fm.horizontalAdvance(l) for l in lines), default=0) + 40
        parent_w    = self.parent().width() if self.parent() else 1920
        max_allowed = max(parent_w - self._pos.x() - 20, 400)

        # document 내부 줄바꿈 너비를 -1로 설정해 강제 래핑 방지
        self.document().setTextWidth(-1)

        self.setFixedSize(
            min(max(max_w, 200), max_allowed),
            max(line_h * len(lines) + 10, line_h + 10),
        )

    # ── 키 처리 ─────────────────────────────────

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Ctrl+Enter=확정, Escape=취소, 그 외=기본 처리(Enter=줄바꿈)."""
        is_enter = event.key() in (Qt.Key_Return, Qt.Key_Enter)
        is_ctrl  = bool(event.modifiers() & Qt.ControlModifier)

        if is_enter and is_ctrl:
            self.editingFinished.emit()
        elif event.key() == Qt.Key_Escape:
            self.setPlainText("")
            self.editingFinished.emit()
        else:
            super().keyPressEvent(event)

    # ── QLineEdit 호환 인터페이스 ────────────────

    def text(self) -> str:
        """QLineEdit.text() 와 동일한 인터페이스를 제공한다."""
        return self.toPlainText()


# ════════════════════════════════════════════════
#  DoubleClickButton — 싱글/더블클릭 구분 버튼
# ════════════════════════════════════════════════

class DoubleClickButton(QtWidgets.QPushButton):
    """
    싱글클릭과 더블클릭을 구분해서 시그널을 보내는 버튼.

    동작 원리:
      클릭 후 250 ms 이내에 두 번째 클릭이 없으면 singleClicked 발생,
      250 ms 이내에 두 번째 클릭이 오면 타이머를 취소하고 doubleClicked 발생.
    """

    singleClicked = QtCore.pyqtSignal()
    doubleClicked = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # 250 ms 이내 두 번째 클릭이 없으면 싱글클릭으로 확정
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(250)
        self._click_timer.timeout.connect(self._emit_single)

        self._pending = False
        super().clicked.connect(self._on_click)

    def _on_click(self) -> None:
        """클릭 시 호출 — 이미 pending이면 더블클릭으로 확정한다."""
        if self._pending:
            self._click_timer.stop()
            self._pending = False
            self.doubleClicked.emit()
        else:
            self._pending = True
            self._click_timer.start()

    def _emit_single(self) -> None:
        """타이머 만료 시 호출 — 싱글클릭으로 확정한다."""
        self._pending = False
        self.singleClicked.emit()


# ════════════════════════════════════════════════
#  ToolBar — 상단 도구 모음 윈도우
# ════════════════════════════════════════════════

class ToolBar(QtWidgets.QWidget):
    """
    화면 상단에 고정되는 반투명 다크 글래스 스타일 독립 툴바 윈도우.

    독립 윈도우(parent=None)로 생성되므로 캔버스가 hide/show 될 때 영향받지 않는다.

    구성 그룹:
      [도구] [색상+두께] [폰트+퀵사이즈] [토글] [액션]  ···  [그리기] [종료]
    """

    # 툴바 배경색 (딥 네이비, 약간 불투명)
    _BG_COLOR = QColor(14, 16, 26, 215)

    def __init__(self, canvas_ref: QtWidgets.QWidget = None) -> None:
        super().__init__(None)   # 독립 Top-level 윈도우

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedHeight(TOOLBAR_HEIGHT)

        # 캔버스 참조 (현재 미사용, 향후 확장용)
        self._canvas_ref = canvas_ref

        self._init_ui()

    # ── 배경 렌더링 ──────────────────────────────

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """반투명 다크 글래스 배경과 하단 구분선을 직접 그린다."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 딥 네이비 배경
        p.setBrush(QBrush(self._BG_COLOR))
        p.setPen(Qt.NoPen)
        p.drawRect(self.rect())

        # 하단 구분선 (미묘한 흰색 빛)
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        p.end()

    # ── UI 생성 ──────────────────────────────────

    def _init_ui(self) -> None:
        """모든 버튼·위젯을 생성하고 수평 레이아웃에 배치한다."""

        # 전체 툴바 QSS — 자식 위젯에 상속됨
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                color: rgba(220,225,240,200);
                font-size: 14px;
                font-family: 'Segoe UI', 'Noto Sans KR', sans-serif;
            }
            QSpinBox {
                background: rgba(255,255,255,12);
                border: 1px solid rgba(255,255,255,18);
                border-radius: 6px;
                color: rgba(220,225,240,220);
                padding: 1px 3px;
                font-size: 14px;
                font-weight: 500;
                min-width: 48px;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px; height: 14px;
                background: rgba(255,255,255,20);
                border-left: 1px solid rgba(255,255,255,25);
                border-bottom: 1px solid rgba(255,255,255,15);
                border-top-right-radius: 6px;
            }
            QSpinBox::up-button:hover   { background: rgba(255,255,255,50); }
            QSpinBox::up-button:pressed { background: rgba(255,255,255,15); }
            QSpinBox::up-arrow {
                image: none; width: 0; height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid rgba(210,220,255,230);
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px; height: 14px;
                background: rgba(255,255,255,20);
                border-left: 1px solid rgba(255,255,255,25);
                border-top: 1px solid rgba(255,255,255,15);
                border-bottom-right-radius: 6px;
            }
            QSpinBox::down-button:hover   { background: rgba(255,255,255,50); }
            QSpinBox::down-button:pressed { background: rgba(255,255,255,15); }
            QSpinBox::down-arrow {
                image: none; width: 0; height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid rgba(210,220,255,230);
            }
            QSpinBox:hover {
                border: 1px solid rgba(255,255,255,35);
                background: rgba(255,255,255,18);
            }
        """)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(3)

        # ── 내부 헬퍼: 위젯들을 pill 컨테이너로 묶기 ──
        def make_group(*widgets: QtWidgets.QWidget,
                       spacing: int = 3) -> QtWidgets.QWidget:
            """여러 위젯을 하나의 둥근 반투명 pill 컨테이너로 묶어 반환한다."""
            container = QtWidgets.QWidget()
            container.setStyleSheet("""
                QWidget {
                    background: rgba(255,255,255,7);
                    border: 1px solid rgba(255,255,255,10);
                    border-radius: 10px;
                }
            """)
            inner = QtWidgets.QHBoxLayout(container)
            inner.setContentsMargins(4, 3, 4, 3)
            inner.setSpacing(spacing)
            for w in widgets:
                inner.addWidget(w)
            return container

        # ── 그룹 1: 그리기 도구 ──────────────────
        # (키, 아이콘, 한국어, 영어) 순서
        tool_defs = [
            ("pen",     "✏", "펜",     "Pen"),
            ("rect",    "▭", "사각형", "Rect"),
            ("ellipse", "◯", "원",     "Ellipse"),
            ("line",    "╱", "직선",   "Line"),
            ("arrow",   "➔", "화살표", "Arrow"),
            ("text",    "T", "글씨",   "Text"),
        ]

        self.btns: dict[str, QtWidgets.QPushButton] = {}
        tool_widgets = []

        for key, icon, ko, en in tool_defs:
            btn = QtWidgets.QPushButton(f"{icon}  {tr(ko, en)}")
            btn.setFixedHeight(38)
            btn.setStyleSheet(_BTN_TOOL)
            self.btns[key] = btn
            tool_widgets.append(btn)

        self._grp_tools = make_group(*tool_widgets, spacing=2)
        layout.addWidget(self._grp_tools)
        layout.addSpacing(6)

        # ── 그룹 2: 색상 + 두께 ──────────────────
        # 색상 버튼 — update_color_preview()에서 글자색을 동적으로 변경
        self.color_btn = QtWidgets.QPushButton(
            tr("● 색상", "● Color")
        )
        self.color_btn.setFixedHeight(38)
        self.color_btn.setStyleSheet(_BTN_TOOL)

        # 두께 스핀박스 (1~120)
        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(1, 120)
        self.width_spin.setValue(4)
        self.width_spin.setFixedWidth(56)
        self.width_spin.setFixedHeight(28)

        # "W" 레이블
        lbl_w = QtWidgets.QLabel("W")
        lbl_w.setStyleSheet(
            "background: transparent; border: none;"
            " color: rgba(180,185,210,160); font-size: 11px;"
        )

        self._grp_color = make_group(
            self.color_btn, lbl_w, self.width_spin, spacing=4
        )
        layout.addWidget(self._grp_color)
        layout.addSpacing(6)

        # ── 그룹 3: 폰트 + 퀵 사이즈 ────────────
        self.font_btn = QtWidgets.QPushButton(tr("A  폰트", "A  Font"))
        self.font_btn.setFixedHeight(38)
        self.font_btn.setStyleSheet(_BTN_TOOL)

        size_widgets = [self.font_btn]
        for sz in (10, 16, 24, 36):
            btn = QtWidgets.QPushButton(str(sz))
            btn.setFixedWidth(34)
            btn.setFixedHeight(38)
            btn.setStyleSheet(_BTN_ICON)
            btn.setProperty("size_val", sz)          # quick_size()에서 읽음
            self.btns[f"fs{sz}"] = btn               # "fs10", "fs16" … 형태
            size_widgets.append(btn)

        self._grp_font = make_group(*size_widgets, spacing=2)
        layout.addWidget(self._grp_font)
        layout.addSpacing(6)

        # ── 그룹 4: 토글 (채우기·형광·지우개) ───
        self.fill_btn   = QtWidgets.QPushButton("■  " + tr("채우기", "Fill"))
        self.hl_btn     = QtWidgets.QPushButton("▌  " + tr("형광",   "Highlight"))
        self.eraser_btn = QtWidgets.QPushButton("◻  " + tr("지우개", "Eraser"))

        for btn in (self.fill_btn, self.hl_btn, self.eraser_btn):
            btn.setFixedHeight(38)
            btn.setStyleSheet(_BTN_TOOL)

        self._grp_toggle = make_group(
            self.fill_btn, self.hl_btn, self.eraser_btn, spacing=2
        )
        layout.addWidget(self._grp_toggle)
        layout.addSpacing(6)

        # ── 그룹 5: 액션 버튼 ────────────────────
        self.undo_btn     = QtWidgets.QPushButton("↩  " + tr("되돌리기", "Undo"))
        self.snapshot_btn = QtWidgets.QPushButton("⬡  " + tr("저장",     "Save"))
        self.clear_btn    = QtWidgets.QPushButton("✕  " + tr("전체삭제", "Clear"))

        for btn in (self.undo_btn, self.snapshot_btn, self.clear_btn):
            btn.setFixedHeight(38)
            btn.setStyleSheet(_BTN_TOOL)

        self._grp_action = make_group(
            self.undo_btn, self.snapshot_btn, self.clear_btn, spacing=2
        )
        layout.addWidget(self._grp_action)
        layout.addStretch()   # 오른쪽 버튼들을 오른쪽 끝으로 밀기

        # ── 그리기 모드 토글 버튼 ────────────────
        # 싱글클릭=캔버스 초기화 후 마우스 모드, 더블클릭=캔버스 유지 모드 전환
        self.drawing_btn = DoubleClickButton("✎  " + tr("그리기", "Drawing"))
        self.drawing_btn.setFixedHeight(38)
        self.drawing_btn.setStyleSheet(_BTN_DRAWING_ON)
        layout.addWidget(self.drawing_btn)
        layout.addSpacing(6)

        # ── 종료 버튼 ────────────────────────────
        self.exit_btn = QtWidgets.QPushButton("⏻  " + tr("종료", "Exit"))
        self.exit_btn.setFixedHeight(38)
        self.exit_btn.setStyleSheet(_BTN_EXIT)
        layout.addWidget(self.exit_btn)

        self.setLayout(layout)

    # ── 스타일 갱신 ──────────────────────────────

    def update_button_styles(
        self,
        current_tool: str,
        fill: bool,
        hl: bool,
        eraser: bool,
    ) -> None:
        """
        현재 도구·토글 상태에 맞게 버튼 스타일을 갱신한다.
        ScreenDrawing.update_ui_styles()에서 호출된다.
        """
        # 도구 버튼: 선택된 도구만 accent 글로우, 나머지는 기본
        for key in VALID_TOOLS:
            _, accent = ICONS[key]
            self.btns[key].setStyleSheet(
                _active_style(accent) if key == current_tool else _BTN_TOOL
            )

        # 토글 버튼: ON이면 accent 색으로 약하게 하이라이트
        self.fill_btn.setStyleSheet(
            _toggle_on_style(ICONS["fill"][1])      if fill   else _BTN_TOOL
        )
        self.hl_btn.setStyleSheet(
            _toggle_on_style(ICONS["highlight"][1]) if hl     else _BTN_TOOL
        )
        self.eraser_btn.setStyleSheet(
            _toggle_on_style(ICONS["eraser"][1])    if eraser else _BTN_TOOL
        )

    def set_drawing_mode(self, drawing: bool) -> None:
        """
        그리기 모드 ON/OFF에 따라 도구 그룹들을 표시/숨김 처리하고
        그리기 버튼 색상을 전환한다.
        drawing=False이면 그리기 버튼만 남기고 나머지는 숨긴다.
        """
        for grp in (
            self._grp_tools, self._grp_color,
            self._grp_font, self._grp_toggle, self._grp_action,
        ):
            grp.setVisible(drawing)

        self.drawing_btn.setStyleSheet(
            _BTN_DRAWING_ON if drawing else _BTN_DRAWING_OFF
        )

        geo = QtWidgets.QApplication.primaryScreen().geometry()

        # Wine/Windows 호환: 크기 변경 전후로 hide/show 처리
        # Wine에서 setFixedSize+move 후 클릭이 안 되는 문제 방지
        was_visible = self.isVisible()
        if was_visible:
            self.hide()

        if drawing:
            # 그리기 모드: 전체 툴바
            self.setFixedSize(geo.width(), TOOLBAR_HEIGHT)
            self.move(geo.x(), geo.y())
        else:
            # 마우스 모드: 버튼 2개만 보이는 작은 툴바 (오른쪽 상단)
            self.setFixedSize(220, TOOLBAR_HEIGHT)
            self.move(geo.right() - 220, geo.y())

        if was_visible:
            self.show()

    def update_color_preview(self, color: QColor) -> None:
        """
        색상 버튼의 글자색을 현재 펜 색상으로 변경한다.
        배경·테두리는 기본 스타일을 유지하고 색상만 반영한다.
        """
        c = color.name()
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,18), stop:1 rgba(255,255,255,6));
                border: 1px solid rgba(255,255,255,14);
                border-radius: 8px;
                color: {c};
                font-size: 14px;
                font-weight: 700;
                padding: 0px 10px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,28);
                border: 1px solid rgba(255,255,255,28);
                color: {c};
            }}
        """)


# ════════════════════════════════════════════════
#  PassthroughOverlay — 마우스 통과 모드 전용 표시 윈도우
# ════════════════════════════════════════════════

class PassthroughOverlay(QtWidgets.QWidget):
    """
    마우스 통과 모드일 때 기존 그림을 화면에 유지시키는 읽기 전용 오버레이.

    마우스 이벤트를 전혀 받지 않으므로 아래 창을 자유롭게 조작할 수 있다.
    생성 시 canvas의 스냅샷을 복사해 표시하며 이후 변경에는 반응하지 않는다.
    """

    def __init__(self, canvas: QPixmap) -> None:
        super().__init__(None)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.setGeometry(QtWidgets.QApplication.primaryScreen().geometry())
        self._snapshot = canvas.copy()   # 스냅샷 저장 (원본 변경 영향 없음)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """저장된 캔버스 스냅샷을 화면에 그린다."""
        p = QPainter(self)
        p.drawPixmap(0, 0, self._snapshot)
        p.end()


# ════════════════════════════════════════════════
#  ScreenDrawing — 메인 그리기 위젯
# ════════════════════════════════════════════════

class ScreenDrawing(QtWidgets.QWidget):
    """
    전체화면 투명 오버레이 위에서 그림을 그리는 메인 위젯.

    주요 구조:
      canvas         : 확정된 그림을 저장하는 QPixmap (투명 배경)
      _pen_layer     : 일반 펜 드래그 중 임시 레이어 (가시성 겹침 방지)
      _hl_layer      : 형광펜 드래그 중 임시 레이어 (겹침 방지)
      undo_stack     : canvas 스냅샷 스택 (최대 MAX_UNDO_STEPS 단계)
      toolbar        : 상단 ToolBar 독립 윈도우

    모드:
      그리기 모드   : canvas 윈도우 표시, 마우스 이벤트 수신
      마우스 통과 모드: canvas 윈도우 숨김 → PassthroughOverlay로 그림 유지 표시
    """

    def __init__(self) -> None:
        super().__init__()
        self._init_window()
        self._init_variables()
        self._init_ui()

    # ════════════════════════════════════════════
    #  초기화
    # ════════════════════════════════════════════

    def _init_window(self) -> None:
        """
        전체화면 투명 오버레이 윈도우를 설정한다.
        항상 다른 창 위에 표시되며 배경이 완전히 투명하다.
        Windows에서는 태스크바 표시를 숨기기 위해 Qt.Tool을 추가한다.
        """
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if sys.platform == "win32":
            flags |= Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        geo = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(geo)

        # 그림이 저장되는 투명 캔버스 (화면 크기와 동일)
        self.canvas = QPixmap(geo.size())
        self.canvas.fill(Qt.transparent)

    def _init_variables(self) -> None:
        """
        모든 내부 상태 변수를 기본값으로 설정한다.
        저장된 설정 파일이 있으면 사용자 설정 항목을 덮어씌운다.
        """
        # ── 사용자 설정 (저장/복원 대상) ──────
        self.current_tool: str    = "pen"
        self.pen_color:    QColor = QColor(255, 50, 50)  # 기본: 빨간색
        self.pen_width:    int    = 4
        self.fill_enabled: bool   = False
        self.highlighter:  bool   = False
        self.eraser:       bool   = False
        self.text_font:    QFont  = QFont("Sans", 24)

        self._load_settings()   # 저장된 값이 있으면 위 변수들을 덮어씌움

        # ── 드로잉 런타임 상태 (저장 안 함) ──
        self.drawing:     bool  = False         # 현재 마우스 드래그 중 여부
        self.start_point: QPoint = QPoint()     # 드래그 시작점
        self.end_point:   QPoint = QPoint()     # 드래그 현재·끝점
        self.path: QtGui.QPainterPath = QtGui.QPainterPath()  # 자유곡선 경로

        # 커서 미리보기 위치 (초기값은 화면 밖)
        self._cursor_pos: QPoint = QPoint(-100, -100)
        # 지우개 이전 위치 (빠른 이동 시 점선 방지용)
        self._last_eraser_pos: QPoint = QPoint()

        # 드래그 중 임시 레이어 (마우스를 떼면 canvas에 합성)
        self._pen_layer: QPixmap | None = None  # 일반 펜 (겹침 가시성 방지)
        self._hl_layer:  QPixmap | None = None  # 형광펜 (반투명 겹침 방지)

        # 텍스트 입력 위젯 참조 (None = 비활성)
        self._text_input: FloatingTextInput | None = None

        # 실행취소 스냅샷 스택
        self.undo_stack: list[QPixmap] = []

        # 임시 도구 전환 상태 (Ctrl=지우개, Shift=직선, 키를 놓으면 복원)
        self._temp_eraser: bool = False
        self._temp_line:   bool = False
        self._saved_tool:  str  = self.current_tool

        # 그리기/마우스 통과 모드 상태
        self._drawing_mode:        bool                   = True
        self._passthrough_overlay: PassthroughOverlay | None = None

    def _init_ui(self) -> None:
        """툴바를 생성하고 각 버튼에 이벤트 핸들러를 연결한다."""
        geo = QtWidgets.QApplication.primaryScreen().geometry()
        self.toolbar = ToolBar(self)
        self.toolbar.setGeometry(geo.x(), geo.y(), geo.width(), TOOLBAR_HEIGHT)
        self.toolbar.show()

        # 도구·퀵사이즈 버튼 이벤트 연결
        for key, btn in self.toolbar.btns.items():
            if key.startswith("fs"):
                # "fs10" → quick_size(10), "fs16" → quick_size(16) …
                btn.clicked.connect(
                    lambda _checked, b=btn: self.quick_size(b.property("size_val"))
                )
            else:
                # "pen" → set_tool("pen"), "rect" → set_tool("rect") …
                btn.clicked.connect(
                    lambda _checked, k=key: self.set_tool(k)
                )

        # 나머지 버튼 이벤트 연결
        tb = self.toolbar
        tb.color_btn.clicked.connect(self.select_color)
        tb.width_spin.valueChanged.connect(self.set_width)
        tb.font_btn.clicked.connect(self.select_font)
        tb.fill_btn.clicked.connect(self.toggle_fill)
        tb.hl_btn.clicked.connect(self.toggle_highlighter)
        tb.eraser_btn.clicked.connect(self.toggle_eraser)
        tb.undo_btn.clicked.connect(self.undo)
        tb.snapshot_btn.clicked.connect(self.save_snapshot)
        tb.clear_btn.clicked.connect(self.clear_canvas)
        tb.drawing_btn.singleClicked.connect(self.toggle_drawing_mode_clear)
        tb.drawing_btn.doubleClicked.connect(self.toggle_drawing_mode)
        tb.exit_btn.clicked.connect(self.force_exit)

        # 초기 스타일 적용 및 저장된 두께를 스핀박스에 반영
        self.update_ui_styles()
        self.toolbar.width_spin.setValue(self.pen_width)

    # ════════════════════════════════════════════
    #  Qt 이벤트 오버라이드
    # ════════════════════════════════════════════

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """윈도우가 표시될 때 OS별 오버레이 설정을 적용한다."""
        super().showEvent(event)
        self._apply_win32_overlay()
        self._suppress_linux_notification()

    # ════════════════════════════════════════════
    #  OS별 윈도우 설정
    # ════════════════════════════════════════════

    def _apply_win32_overlay(self) -> None:
        """
        Windows API로 투명 오버레이 속성을 설정한다. (Windows 전용)
        WS_EX_LAYERED 추가, WS_EX_TRANSPARENT 제거 — 마우스 이벤트 수신 유지.
        """
        if sys.platform != "win32":
            return
        hwnd      = int(self.winId())
        ex_style  = GetWindowLong(hwnd, GWL_EXSTYLE)
        new_style = (ex_style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT
        SetWindowLong(hwnd, GWL_EXSTYLE, new_style)
        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

    def _suppress_linux_notification(self) -> None:
        """
        Linux(X11/GNOME)에서 show() 호출 시 뜨는 "앱 준비됨" 알림을 억제한다.

        xprop으로 _NET_WM_STATE_SKIP_TASKBAR + SKIP_PAGER 힌트를 설정해
        GNOME Shell이 이 창을 일반 앱 창으로 인식하지 않도록 한다.
        Wayland 또는 xprop이 없는 환경에서는 조용히 무시된다.
        (현재 GNOME 버전에 따라 효과가 없을 수 있음 — 향후 개선 예정)
        """
        if sys.platform == "win32":
            return
        try:
            from PyQt5.QtX11Extras import QX11Info
            if not QX11Info.isPlatformX11():
                return
            subprocess.Popen(
                [
                    "xprop", "-id", str(int(self.winId())),
                    "-f", "_NET_WM_STATE", "32a",
                    "-set", "_NET_WM_STATE",
                    "_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # ════════════════════════════════════════════
    #  설정 저장 / 불러오기
    # ════════════════════════════════════════════

    def _load_settings(self) -> None:
        """
        SETTINGS_PATH의 JSON 파일에서 사용자 설정을 불러온다.
        파일이 없거나 손상된 경우 예외를 무시하고 기본값을 유지한다.
        """
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data: dict = json.load(f)

            # 도구 — VALID_TOOLS 범위 검증
            tool = data.get("tool", "pen")
            if tool in VALID_TOOLS:
                self.current_tool = tool

            # 색상 — QColor 변환
            if color_str := data.get("color"):
                self.pen_color = QColor(color_str)

            # 두께 — 1~120 범위 검증
            width = data.get("width")
            if isinstance(width, int) and 1 <= width <= 120:
                self.pen_width = width

            # 토글 상태
            self.fill_enabled = bool(data.get("fill",      False))
            self.highlighter  = bool(data.get("highlight", False))

            # 폰트
            if font_family := data.get("font_family"):
                font_size = data.get("font_size")
                self.text_font = QFont(
                    font_family,
                    font_size if isinstance(font_size, int) else 24,
                )

        except Exception:
            pass   # 오류 시 기본값 유지

    def _save_settings(self) -> None:
        """
        현재 사용자 설정을 SETTINGS_PATH의 JSON 파일에 저장한다.
        종료 시(force_exit) 자동 호출된다.
        """
        try:
            data = {
                "tool":        self.current_tool,
                "color":       self.pen_color.name(),   # "#RRGGBB"
                "width":       self.pen_width,
                "fill":        self.fill_enabled,
                "highlight":   self.highlighter,
                "font_family": self.text_font.family(),
                "font_size":   self.text_font.pointSize(),
            }
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass   # 저장 실패 무시 (읽기 전용 파일시스템 등 대비)

    # ════════════════════════════════════════════
    #  도구 및 상태 관리
    # ════════════════════════════════════════════

    def set_tool(self, tool: str) -> None:
        """
        그리기 도구를 변경한다.
        임시 전환(Ctrl=지우개)이 아닌 상태에서 지우개가 켜져 있으면 끈다.
        """
        self.current_tool = tool
        if self.eraser and not self._temp_eraser:
            self.eraser = False
        self.update_ui_styles()

    def set_width(self, val: int) -> None:
        """
        펜·지우개 두께와 텍스트 폰트 크기를 동시에 변경한다.
        스핀박스 valueChanged 신호에 연결된다.
        """
        self.pen_width = val
        self.text_font.setPointSize(val)

    def toggle_fill(self) -> None:
        """채우기 모드를 ON/OFF 전환한다."""
        self.fill_enabled = not self.fill_enabled
        self.update_ui_styles()

    def toggle_highlighter(self) -> None:
        """형광펜 모드를 ON/OFF 전환한다."""
        self.highlighter = not self.highlighter
        self.update_ui_styles()

    def toggle_eraser(self) -> None:
        """지우개 모드를 ON/OFF 전환한다."""
        self.eraser = not self.eraser
        self.update_ui_styles()

    def update_ui_styles(self) -> None:
        """현재 도구·토글 상태에 맞게 툴바 버튼 스타일을 갱신한다."""
        self.toolbar.update_button_styles(
            self.current_tool,
            self.fill_enabled,
            self.highlighter,
            self.eraser,
        )
        self.toolbar.update_color_preview(self.pen_color)

    def quick_size(self, size: int) -> None:
        """
        퀵 사이즈 버튼(10/16/24/36) 클릭 시 호출된다.
        펜 두께와 텍스트 폰트 크기를 동시에 변경하고 스핀박스를 동기화한다.
        """
        self.pen_width = size
        self.text_font.setPointSize(size)
        self.toolbar.width_spin.setValue(size)   # setValue → set_width 자동 호출

    def select_color(self) -> None:
        """색상 선택 다이얼로그를 열고 선택된 색상을 펜 색으로 적용한다."""
        color = QtWidgets.QColorDialog.getColor(
            self.pen_color, self, tr("색상 선택", "Select Color")
        )
        if color.isValid():
            self.pen_color = color
            self.update_ui_styles()

    def select_font(self) -> None:
        """폰트 선택 다이얼로그를 열고 선택된 폰트를 텍스트 폰트로 적용한다."""
        font, ok = QtWidgets.QFontDialog.getFont(
            self.text_font, self, tr("폰트 선택", "Select Font")
        )
        if ok:
            self.text_font = font

    # ════════════════════════════════════════════
    #  그리기 도구 로직
    # ════════════════════════════════════════════

    def _make_pen(self, for_line: bool = False) -> QPen:
        """
        현재 설정에 맞는 QPen을 생성해 반환한다.

        특수 처리:
          - 형광+채우기+도형(rect/ellipse): NoPen 반환
            → 외곽선과 채우기가 이중으로 렌더링되어 진해지는 현상 방지
          - 형광펜: alpha=128 (50% 투명도)
          - 모든 경우 RoundCap/RoundJoin 적용
        """
        if (
            self.highlighter
            and self.fill_enabled
            and self.current_tool in ("rect", "ellipse")
            and not self.eraser
            and not for_line
        ):
            return Qt.NoPen   # 외곽선 없이 채우기만

        color = QColor(self.pen_color)
        if self.highlighter:
            color.setAlpha(128)   # 형광펜: 50% 투명도

        return QPen(color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def _make_brush(self) -> QBrush:
        """
        채우기가 활성화된 경우 현재 펜 색상의 QBrush를 반환한다.
        형광펜 모드이면 50% 투명도를 적용한다.
        채우기 대상 도구: rect, ellipse, arrow
        """
        if (
            self.fill_enabled
            and self.current_tool in ("rect", "ellipse", "arrow")
            and not self.eraser
        ):
            color = QColor(self.pen_color)
            if self.highlighter:
                color.setAlpha(128)
            return QBrush(color)
        return Qt.NoBrush

    def _make_erase_pen(self) -> QPen:
        """지우개 자유곡선·직선 지우기에 사용하는 QPen을 반환한다."""
        return QPen(Qt.black, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def _draw_hl_line(self, painter: QPainter,
                      start: QPoint, end: QPoint) -> None:
        """
        형광펜 직선을 겹침 없이 라운딩 처리하여 그린다.

        문제:
          QPen RoundCap은 선 몸통과 양끝 반원을 별도 렌더링한다.
          반투명(형광)이면 겹치는 부분이 더 진해져 -0- 형태로 보인다.

        해결:
          오프스크린 버퍼에 불투명(alpha=255)으로 선을 그린 뒤,
          버퍼 전체에 alpha=128을 곱해 반투명으로 변환하고 painter에 합성한다.
          렌더링이 버퍼 안에서 완전히 끝나므로 겹침 현상이 없다.
        """
        r = self.pen_width // 2 + 2
        x_min = min(start.x(), end.x()) - r
        y_min = min(start.y(), end.y()) - r
        x_max = max(start.x(), end.x()) + r
        y_max = max(start.y(), end.y()) + r
        w, h  = x_max - x_min, y_max - y_min

        if w < 1 or h < 1:
            return

        # 1단계: 불투명으로 오프스크린 버퍼에 선 그리기
        buf = QPixmap(w, h)
        buf.fill(Qt.transparent)

        bp = QPainter(buf)
        bp.setRenderHint(QPainter.Antialiasing)
        color_opaque = QColor(self.pen_color)
        color_opaque.setAlpha(255)
        bp.setPen(QPen(color_opaque, self.pen_width,
                       Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        bp.drawLine(
            QPoint(start.x() - x_min, start.y() - y_min),
            QPoint(end.x()   - x_min, end.y()   - y_min),
        )
        bp.end()

        # 2단계: 버퍼 전체에 alpha=128 곱해 반투명 변환
        ap = QPainter(buf)
        ap.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        ap.fillRect(buf.rect(), QColor(0, 0, 0, 128))
        ap.end()

        # 3단계: 결과를 원래 painter 좌표계에 합성
        painter.drawPixmap(x_min, y_min, buf)

    def _draw_arrow(self, painter: QPainter,
                    start: QPoint, end: QPoint) -> None:
        """
        사다리꼴 몸통 + 삼각형 화살촉으로 구성된 화살표를 그린다.

        구조:
          - 몸통: 시작점(좁음) → 화살촉 직전(넓음) 사다리꼴 (p1~p4)
          - 화살촉: 삼각형 (h1=끝점, h2·h3=양쪽 날개)
          - 몸통+화살촉을 하나의 7각형 폴리곤으로 그려 경계 틈을 제거
        """
        dx     = end.x() - start.x()
        dy     = end.y() - start.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return

        angle = math.atan2(dy, dx)

        # 화살촉 크기
        head_len   = max(self.pen_width * 3,   15)
        head_width = max(self.pen_width * 2.5, 12)

        # 몸통 끝점(= 화살촉 시작점)
        body_len = max(0.0, length - head_len)
        body_end = QPointF(
            start.x() + math.cos(angle) * body_len,
            start.y() + math.sin(angle) * body_len,
        )

        # 수직 방향 단위벡터
        pc = math.cos(angle + math.pi / 2)
        ps = math.sin(angle + math.pi / 2)

        # 몸통 사다리꼴 꼭짓점
        ws = self.pen_width / 2.0   # 시작 쪽 절반 너비 (좁음)
        we = float(self.pen_width)  # 몸통 끝 절반 너비 (넓음)
        p1 = QPointF(start.x()   + ws * pc, start.y()   + ws * ps)
        p2 = QPointF(start.x()   - ws * pc, start.y()   - ws * ps)
        p3 = QPointF(body_end.x() - we * pc, body_end.y() - we * ps)
        p4 = QPointF(body_end.x() + we * pc, body_end.y() + we * ps)

        # 화살촉 삼각형 꼭짓점
        h1 = QPointF(end.x(), end.y())
        h2 = QPointF(body_end.x() + head_width * pc, body_end.y() + head_width * ps)
        h3 = QPointF(body_end.x() - head_width * pc, body_end.y() - head_width * ps)

        # 채우기 색상 (형광이면 50% 투명도)
        color = QColor(self.pen_color)
        if self.highlighter:
            color.setAlpha(128)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPolygon(QPolygonF([p1, p4, h2, h1, h3, p3, p2]))

    # ════════════════════════════════════════════
    #  텍스트 입력 처리
    # ════════════════════════════════════════════

    def _open_text_input(self, pos: QPoint) -> None:
        """클릭한 위치에 FloatingTextInput을 생성한다."""
        self._destroy_text_input()
        color = QColor(self.pen_color)
        if self.highlighter:
            color.setAlpha(128)   # 형광 모드이면 50% 투명도 적용
        self._text_input = FloatingTextInput(self, pos, self.text_font, color)
        self._text_input.editingFinished.connect(self._commit_text)

    def _destroy_text_input(self) -> None:
        """열려 있는 텍스트 입력창을 닫고 메모리에서 제거한다."""
        if self._text_input:
            self._text_input.hide()
            self._text_input.deleteLater()
            self._text_input = None

    def _commit_text(self) -> None:
        """
        입력된 텍스트를 canvas에 그리고 입력창을 닫는다.
        여러 줄이 있으면 줄바꿈마다 아래로 내려 그린다.
        내용이 없으면 그리지 않는다.
        """
        if not self._text_input:
            return

        text = self._text_input.text().strip('\n').rstrip()
        pos, font, color = (
            self._text_input._pos,
            self._text_input._font,
            self._text_input._color,
        )
        self._destroy_text_input()

        if not text:
            return

        self._push_undo()
        line_h = QtGui.QFontMetrics(font).height()

        p = QPainter(self.canvas)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(font)
        p.setPen(QPen(color))
        for i, line in enumerate(text.split('\n')):
            p.drawText(pos.x(), pos.y() + i * line_h, line)
        p.end()

        self.update()

    # ════════════════════════════════════════════
    #  마우스 이벤트
    # ════════════════════════════════════════════

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """마우스 버튼을 눌렀을 때 도구에 따라 드로잉을 시작한다."""
        if not self._drawing_mode:
            return
        # 툴바 영역 클릭은 무시 (툴바는 별도 독립 윈도우이나 좌표 겹칠 수 있음)
        if event.pos().y() <= TOOLBAR_HEIGHT:
            return

        # 텍스트 입력 중에 다른 곳을 클릭하면 확정
        if self._text_input:
            self._commit_text()
            return

        if event.button() != Qt.LeftButton:
            return

        self.setFocus()
        self.start_point = event.pos()
        self.end_point   = event.pos()

        # 텍스트 도구: 입력창 열기
        if self.current_tool == "text" and not self.eraser:
            self._open_text_input(event.pos())
            return

        # 드로잉 시작
        self.drawing = True
        self._push_undo()
        self._last_eraser_pos = QPoint()   # 지우개 이전 위치 초기화
        self.path = QtGui.QPainterPath()
        self.path.moveTo(event.pos())

        # 펜 도구일 때 임시 레이어 초기화
        if self.current_tool == "pen" and not self.eraser:
            layer_size = self.canvas.size()
            if self.highlighter:
                self._hl_layer = QPixmap(layer_size)
                self._hl_layer.fill(Qt.transparent)
            else:
                self._pen_layer = QPixmap(layer_size)
                self._pen_layer.fill(Qt.transparent)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """마우스를 움직일 때 도구에 따라 캔버스를 갱신한다."""
        if not self._drawing_mode:
            return

        self._cursor_pos = event.pos()

        # 지우개·형광펜은 커서 미리보기를 위해 항상 repaint
        if self.eraser or (self.highlighter and self.current_tool == "pen"):
            self.update()

        if not self.drawing:
            return

        self.end_point = event.pos()

        # ── 지우개 자유곡선 (도형 모드는 드래그 범위 지정이므로 제외) ──
        if self.eraser and self.current_tool not in ("rect", "ellipse", "line", "arrow"):
            p = QPainter(self.canvas)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.setPen(self._make_erase_pen())
            if not self._last_eraser_pos.isNull():
                p.drawLine(self._last_eraser_pos, event.pos())
            else:
                p.drawPoint(event.pos())
            p.end()
            self._last_eraser_pos = event.pos()
            self.update()
            return

        # ── 형광펜 자유곡선 ──
        # _hl_layer를 매번 초기화 후 전체 경로를 다시 그려 매끄러운 선 유지
        if self.highlighter and self.current_tool == "pen" and self._hl_layer:
            self._hl_layer.fill(Qt.transparent)
            p = QPainter(self._hl_layer)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(self._make_pen())
            self.path.lineTo(event.pos())
            p.drawPath(self.path)
            p.end()
            self.update()
            return

        # ── 일반 펜 자유곡선 ──
        # _pen_layer를 매번 초기화 후 전체 경로를 다시 그려 가시(겹침) 방지
        if self.current_tool == "pen" and self._pen_layer:
            self._pen_layer.fill(Qt.transparent)
            p = QPainter(self._pen_layer)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(self._make_pen())
            self.path.lineTo(event.pos())
            p.drawPath(self.path)
            p.end()
            self.update()
            return

        # ── 도형 (rect·ellipse·line·arrow): 미리보기 갱신 ──
        if self.current_tool in ("rect", "ellipse", "line", "arrow"):
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """마우스 버튼을 놓을 때 드로잉을 확정하고 canvas에 합성한다."""
        if not self._drawing_mode or not self.drawing:
            return

        self.drawing   = False
        self.end_point = event.pos()

        # ── 형광펜 확정: _hl_layer → canvas 합성 ──
        if self.highlighter and self.current_tool == "pen" and self._hl_layer:
            p = QPainter(self.canvas)
            p.drawPixmap(0, 0, self._hl_layer)
            p.end()
            self._hl_layer = None
            self.update()
            return

        # ── 일반 펜 확정: _pen_layer → canvas 합성 ──
        if not self.highlighter and self.current_tool == "pen" and self._pen_layer:
            p = QPainter(self.canvas)
            p.drawPixmap(0, 0, self._pen_layer)
            p.end()
            self._pen_layer = None
            self.update()
            return

        # ── 도형 / 지우개 범위 확정 ──
        # 펜 자유곡선(eraser=False, tool=pen)은 위에서 이미 처리됨
        # 나머지: eraser=True 또는 도형 도구
        if not self.eraser or self.current_tool in ("rect", "ellipse", "line", "arrow"):
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)

            if self.eraser:
                # 지우개 범위 지정 모드 (rect/ellipse/arrow)
                p.setCompositionMode(QPainter.CompositionMode_Clear)
                p.setBrush(QBrush(Qt.black))
                p.setPen(Qt.NoPen)
            else:
                p.setPen(self._make_pen(for_line=self.current_tool in ("line", "arrow")))
                p.setBrush(self._make_brush())

            rect = QRect(self.start_point, self.end_point).normalized()

            if self.current_tool == "rect":
                p.drawRect(rect)

            elif self.current_tool == "ellipse":
                p.drawEllipse(rect)

            elif self.current_tool == "line":
                if self.eraser:
                    # 지우개+직선: Clear 모드 + 두꺼운 RoundCap 펜으로 선 지우기
                    p.setCompositionMode(QPainter.CompositionMode_Clear)
                    p.setPen(self._make_erase_pen())
                    p.drawLine(self.start_point, self.end_point)
                elif self.highlighter:
                    self._draw_hl_line(p, self.start_point, self.end_point)
                else:
                    p.drawLine(self.start_point, self.end_point)

            elif self.current_tool == "arrow":
                if self.eraser:
                    # 지우개+화살표: Clear 모드로 화살표 영역을 지우기
                    p.setCompositionMode(QPainter.CompositionMode_Clear)
                    p.setPen(Qt.NoPen)
                    p.setBrush(QBrush(Qt.black))
                    self._draw_arrow(p, self.start_point, self.end_point)
                else:
                    self._draw_arrow(p, self.start_point, self.end_point)

            p.end()

        self.update()

    # ════════════════════════════════════════════
    #  화면 렌더링
    # ════════════════════════════════════════════

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """
        매 프레임 호출되는 렌더링 메서드.
        렌더링 순서:
          1. canvas (확정된 그림)
          2. 임시 레이어 (_pen_layer / _hl_layer)
          3. 커서 미리보기 (지우개 원 / 형광펜 원)
          4. 도형 드래그 중 미리보기
        """
        painter = QPainter(self)

        # Windows: 완전히 투명한 픽셀은 마우스 이벤트가 통과되므로
        #          alpha=1로 채워서 이벤트 수신 보장.
        #          단, 툴바 영역(TOOLBAR_HEIGHT 위)은 제외 —
        #          툴바가 독립 윈도우로 그 위에 있지만 alpha=1 레이어가
        #          클릭을 가로채므로 툴바 아래 캔버스 영역에만 적용한다.
        if sys.platform == "win32":
            canvas_rect = self.rect().adjusted(0, TOOLBAR_HEIGHT, 0, 0)
            painter.fillRect(canvas_rect, QColor(0, 0, 0, 1))

        # 1. 확정된 그림
        painter.drawPixmap(0, 0, self.canvas)

        # 2. 드래그 중 임시 레이어
        if self._pen_layer:
            painter.drawPixmap(0, 0, self._pen_layer)
        if self._hl_layer:
            painter.drawPixmap(0, 0, self._hl_layer)

        # 3. 커서 미리보기 (툴바 아래 영역에서만)
        if self._cursor_pos.y() > TOOLBAR_HEIGHT:
            r = max(self.pen_width // 2, 2)
            if self.eraser:
                # 지우개: 점선 원으로 지우개 크기 표시
                painter.setPen(QPen(QColor(200, 200, 200, 180), 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(self._cursor_pos, r, r)
            elif self.highlighter and self.current_tool == "pen":
                # 형광펜: 반투명 채워진 원으로 크기 표시
                c = QColor(self.pen_color)
                c.setAlpha(100)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(c))
                painter.drawEllipse(self._cursor_pos, r, r)

        # 4. 도형 드래그 중 미리보기 (확정 전 실선/점선 표시)
        if self.drawing and self.current_tool in ("rect", "ellipse", "line", "arrow"):
            pv = QPainter(self)
            pv.setRenderHint(QPainter.Antialiasing)

            if self.eraser:
                # 지우개 범위: 빨간 점선
                pv.setPen(QPen(QColor(255, 80, 80, 200), 1.5, Qt.DashLine))
                pv.setBrush(QBrush(QColor(255, 80, 80, 40)))
            else:
                pv.setPen(self._make_pen(
                    for_line=self.current_tool in ("line", "arrow")
                ))
                pv.setBrush(self._make_brush())

            rect = QRect(self.start_point, self.end_point).normalized()

            if self.current_tool == "rect":
                pv.drawRect(rect)

            elif self.current_tool == "ellipse":
                pv.drawEllipse(rect)

            elif self.current_tool == "line":
                if self.eraser:
                    # 지우개 직선: 빨간 반투명으로 미리보기
                    saved = self.pen_color
                    self.pen_color = QColor(255, 80, 80, 120)
                    self._draw_hl_line(pv, self.start_point, self.end_point)
                    self.pen_color = saved
                elif self.highlighter:
                    self._draw_hl_line(pv, self.start_point, self.end_point)
                else:
                    pv.drawLine(self.start_point, self.end_point)

            elif self.current_tool == "arrow":
                if self.eraser:
                    # 지우개 화살표: 빨간 반투명으로 미리보기
                    saved = self.pen_color
                    self.pen_color = QColor(255, 80, 80, 120)
                    self._draw_arrow(pv, self.start_point, self.end_point)
                    self.pen_color = saved
                else:
                    self._draw_arrow(pv, self.start_point, self.end_point)

    # ════════════════════════════════════════════
    #  캔버스 유틸리티
    # ════════════════════════════════════════════

    def _push_undo(self) -> None:
        """현재 canvas를 undo_stack에 스냅샷으로 저장한다. (최대 MAX_UNDO_STEPS)"""
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > MAX_UNDO_STEPS:
            self.undo_stack.pop(0)   # 가장 오래된 스냅샷 제거

    def undo(self) -> None:
        """가장 최근 스냅샷으로 canvas를 되돌린다."""
        if self.undo_stack:
            self.canvas = self.undo_stack.pop()
            self.update()

    def clear_canvas(self) -> None:
        """canvas를 완전히 지운다. 실행취소 가능."""
        self._push_undo()
        self.canvas.fill(Qt.transparent)
        self.update()

    def save_snapshot(self) -> None:
        """
        canvas를 투명 PNG 파일로 저장한다.
        저장 경로: ~/drawing_YYYYMMDD_HHMMSS.png
        저장 완료 후 2초간 화면 상단에 알림 레이블을 표시한다.
        """
        path = os.path.join(
            os.path.expanduser("~"),
            f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )
        self.canvas.save(path, "PNG")

        # 저장 완료 알림 (2초 후 자동 제거)
        msg = QtWidgets.QLabel(tr(f"저장됨: {path}", f"Saved: {path}"), self)
        msg.setStyleSheet(
            "background-color: #1A2540; color: #81C784;"
            " padding: 8px; border-radius: 5px;"
        )
        msg.adjustSize()
        msg.move((self.width() - msg.width()) // 2, TOOLBAR_HEIGHT + 10)
        msg.show()
        QTimer.singleShot(2000, msg.deleteLater)

    # ════════════════════════════════════════════
    #  모드 전환
    # ════════════════════════════════════════════

    def toggle_drawing_mode_clear(self) -> None:
        """
        싱글클릭: 캔버스를 초기화한 뒤 마우스 통과 모드로 전환한다.
        그리기 모드로 돌아올 때는 빈 캔버스 상태에서 시작한다.
        """
        if self._drawing_mode:
            # 그리기 → 마우스 모드: 캔버스와 undo 스택 초기화
            self.canvas.fill(Qt.transparent)
            self.undo_stack.clear()
            self.update()
        self.toggle_drawing_mode()

    def toggle_drawing_mode(self) -> None:
        """
        그리기 모드 ↔ 마우스 통과 모드를 전환한다.

        그리기 모드(ON):
          - canvas 윈도우를 표시하고 마우스 이벤트를 수신한다.
          - PassthroughOverlay를 닫는다.

        마우스 통과 모드(OFF):
          - canvas 윈도우를 숨긴다 → 마우스 이벤트 완전히 통과.
          - PassthroughOverlay로 그림을 화면에 유지 표시한다.
          - 툴바는 독립 윈도우이므로 항상 클릭 가능하다.
        """
        self._drawing_mode = not self._drawing_mode
        self.toolbar.set_drawing_mode(self._drawing_mode)

        if self._drawing_mode:
            # 마우스 → 그리기 모드
            self.toolbar.drawing_btn.setText("✎  " + tr("그리기", "Drawing"))
            if self._passthrough_overlay:
                self._passthrough_overlay.close()
                self._passthrough_overlay = None
            self.show()
            self._suppress_linux_notification()
        else:
            # 그리기 → 마우스 통과 모드
            self.toolbar.drawing_btn.setText("⬡  " + tr("마우스", "Mouse"))
            self._passthrough_overlay = PassthroughOverlay(self.canvas)
            self._passthrough_overlay.show()
            self.hide()

    def force_exit(self) -> None:
        """설정을 저장하고 프로그램을 종료한다."""
        self._save_settings()
        if self._passthrough_overlay:
            self._passthrough_overlay.close()
            self._passthrough_overlay = None
        self.toolbar.close()
        self.close()
        QtWidgets.QApplication.quit()

    # ════════════════════════════════════════════
    #  키보드 단축키
    # ════════════════════════════════════════════

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """
        키보드 단축키 처리.

        단축키:
          Ctrl (홀드)  : 임시 지우개 모드 (키를 뗄 때 복원)
          Shift (홀드) : 임시 직선 모드   (키를 뗄 때 복원)
          Escape       : 텍스트 입력 취소 / 프로그램 종료
          Ctrl + Z     : 되돌리기
          Ctrl + S     : PNG 저장
          Ctrl + Q     : 종료
          C            : 전체 지우기
        """
        key  = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)

        if key == Qt.Key_Control and not self.drawing:
            # 임시 지우개 전환
            self._temp_eraser = True
            self._saved_tool  = self.current_tool
            self.eraser       = True
            self.update_ui_styles()

        elif key == Qt.Key_Shift and not self.drawing:
            # 임시 직선 전환
            self._temp_line   = True
            self._saved_tool  = self.current_tool
            self.current_tool = "line"
            self.update_ui_styles()

        elif key == Qt.Key_Escape:
            if self._text_input:
                self._destroy_text_input()
            else:
                self.force_exit()

        elif key == Qt.Key_Z and ctrl:
            self.undo()

        elif key == Qt.Key_S and ctrl:
            self.save_snapshot()

        elif key == Qt.Key_Q and ctrl:
            self.force_exit()

        elif key == Qt.Key_C and not self._text_input:
            self.clear_canvas()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        """
        임시 도구 전환 키(Ctrl=지우개, Shift=직선)를
        뗄 때 원래 도구로 복원한다.
        """
        key = event.key()

        if key == Qt.Key_Control and self._temp_eraser:
            self._temp_eraser = False
            self.eraser       = False
            self.current_tool = self._saved_tool
            self.update_ui_styles()

        elif key == Qt.Key_Shift and self._temp_line:
            self._temp_line   = False
            self.current_tool = self._saved_tool
            self.update_ui_styles()


# ════════════════════════════════════════════════
#  진입점
# ════════════════════════════════════════════════

def main() -> None:
    """앱을 초기화하고 메인 루프를 시작한다."""
    if sys.platform == "win32":
        # 콘솔 창 숨기기
        import ctypes
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0
        )
        # 고DPI 대응
        QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,    True)

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    # 아이콘 설정 (exe와 같은 폴더의 screendrawing.ico 사용)
    icon_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "screendrawing.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QtGui.QIcon(icon_path))

    window = ScreenDrawing()
    window.showFullScreen()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
