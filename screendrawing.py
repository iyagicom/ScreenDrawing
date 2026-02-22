#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScreenDrawing
Version: 1.4.5
Author: Jeong SeongYong
Email: iyagicom@gmail.com
Description: Lightweight Wayland screen drawing tool
             (pen, shapes, text, highlight, eraser, undo, screenshot)
License: GPL-2.0 or later
"""

# ────────────────────────────────────────────────
#  표준 라이브러리
# ────────────────────────────────────────────────
import sys
import os
import json
import locale
import math
from datetime import datetime

# ────────────────────────────────────────────────
#  PyQt5
# ────────────────────────────────────────────────
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QBrush, QFont, QPolygonF


# ════════════════════════════════════════════════
#  전역 상수
# ════════════════════════════════════════════════

# 툴바 높이 (픽셀) — 이 값 아래부터 캔버스 영역
TOOLBAR_HEIGHT = 58

# 실행취소 최대 단계 수
MAX_UNDO_STEPS = 50

# 설정 파일 저장 경로: ~/.local/share/screendrawing/settings.json
_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "screendrawing")
os.makedirs(_SETTINGS_DIR, exist_ok=True)          # 디렉토리 없으면 자동 생성
SETTINGS_PATH = os.path.join(_SETTINGS_DIR, "settings.json")

# 각 도구의 (아이콘 이모지, 활성화 강조 색상) 매핑
ICONS = {
    "pen":       ("✏",  "#4FC3F7"),   # 하늘색
    "rect":      ("▭",  "#81C784"),   # 초록
    "ellipse":   ("◯",  "#CE93D8"),   # 보라
    "line":      ("/",  "#FFB74D"),   # 주황
    "arrow":     ("➔",  "#FF8A65"),   # 살몬
    "text":      ("T",  "#F48FB1"),   # 핑크
    "eraser":    ("□",  "#FF9800"),   # 주황색 ← 지우개 토글 ON 색상
    "fill":      ("■",  "#AB47BC"),   # 보라색 ← 채우기 토글 ON 색상
    "highlight": ("▌",  "#FFD600"),   # 노란색 ← 형광 토글 ON 색상
    "clear":     ("✕",  "#EF9A9A"),
    "exit":      ("✕",  "#EF5350"),
}


# ════════════════════════════════════════════════
#  유틸리티 함수
# ════════════════════════════════════════════════

def detect_language() -> str:
    """
    시스템 환경변수를 읽어 한국어(ko) 또는 영어(en)를 반환한다.
    LANG, LANGUAGE, LC_ALL, LC_MESSAGES 순서로 확인한다.
    """
    for env in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(env, "")
        if val.lower().startswith("ko"):
            return "ko"
    try:
        code, _ = locale.getdefaultlocale()
        if code and code.lower().startswith("ko"):
            return "ko"
    except Exception:
        pass
    return "en"


# 전역 언어 설정 (모듈 로드 시 1회 결정)
LANG = detect_language()


def tr(ko: str, en: str) -> str:
    """현재 언어(LANG)에 따라 한국어 또는 영어 문자열을 반환한다."""
    return ko if LANG == "ko" else en


# ════════════════════════════════════════════════
#  버튼 스타일 상수 (QSS)
# ════════════════════════════════════════════════

# 기본 버튼 스타일 템플릿 — {pad} 자리에 padding 값을 채워 사용
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

# 용도별 버튼 스타일 (padding만 다름)
_BTN_TOOL  = _BTN_BASE.format(pad="0px 10px")   # 텍스트가 있는 일반 도구 버튼
_BTN_ICON  = _BTN_BASE.format(pad="0px 6px")    # 숫자/아이콘 전용 정방형 버튼
_BTN_SMALL = _BTN_BASE.format(pad="0px 7px")    # 소형 버튼 (예비)


def _active_style(accent: str) -> str:
    """
    현재 선택된 도구 버튼에 적용하는 스타일.
    accent 색상으로 배경 글로우 + 테두리를 강조한다.
    Qt CSS 는 #RRGGBBAA 8자리 hex 미지원 → rgba() 로 변환.
    """
    r, g, b = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
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
    토글 버튼(채우기·형광·지우개)이 ON 상태일 때 적용하는 스타일.
    _active_style 보다 약하게 표시하여 '도구 선택'과 구분한다.
    Qt CSS 는 #RRGGBBAA 8자리 hex 미지원 → rgba() 로 변환.
    """
    r, g, b = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
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
#  FloatingTextInput — 캔버스 위 텍스트 입력 위젯
# ════════════════════════════════════════════════

class FloatingTextInput(QtWidgets.QTextEdit):
    """
    캔버스 위에 떠있는 투명 텍스트 입력창.

    동작:
      - Enter         : 줄바꿈
      - Ctrl + Enter  : 입력 확정 → 캔버스에 그리기
      - Escape        : 입력 취소

    특징:
      - 배경·테두리 없이 현재 펜 색상으로 텍스트 표시
      - 각 줄 아래에 얇은 밑줄을 직접 그려서 입력 범위를 표시
      - 내용이 늘어나면 자동으로 크기 조절
    """

    # 입력 완료 신호 (QLineEdit 호환)
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent, pos: QPoint, font: QFont, color: QColor):
        super().__init__(parent)

        # 위치·폰트·색상 저장 (캔버스에 그릴 때 재사용)
        self._pos   = pos
        self._font  = font
        self._color = color

        self.setFont(font)

        # 투명 배경, 테두리 없음 — 밑줄은 paintEvent에서 직접 그림
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

        # 초기 너비: 화면 오른쪽 끝까지 확보 (자동 줄바꿈 방지)
        screen_w    = parent.width() if parent else 1920
        self._max_w = max(screen_w - pos.x() - 20, 400)
        self.setFixedSize(self._max_w, line_h + 10)

        # 스크롤바 숨김
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 자동 줄바꿈 비활성화 (Enter 키로만 줄바꿈)
        self.setWordWrapMode(QtGui.QTextOption.NoWrap)

        self.setFocus()
        self.textChanged.connect(self._adjust_size)
        self.show()

    def paintEvent(self, event):
        """기본 렌더링 후, 각 줄 텍스트 아래에 얇은 색상 밑줄을 추가로 그린다."""
        super().paintEvent(event)

        fm     = self.fontMetrics()
        lines  = self.toPlainText().split('\n')
        line_h = fm.height()

        p = QPainter(self.viewport())
        p.setPen(QPen(self._color, 2))
        for i, line in enumerate(lines):
            # 텍스트 너비만큼만 밑줄 표시 (최소 10px)
            w = max(fm.horizontalAdvance(line) + 4, 10)
            y = (i + 1) * line_h + 2
            p.drawLine(0, y, w, y)
        p.end()

    def _adjust_size(self):
        """텍스트 내용에 따라 입력창 크기를 자동으로 조절한다."""
        lines  = self.toPlainText().split('\n')
        fm     = self.fontMetrics()
        line_h = fm.height()

        # 너비: 가장 긴 줄 기준으로 오른쪽 확장
        max_w = max((fm.horizontalAdvance(l) for l in lines), default=0) + 40
        # 높이: 실제 줄 수 기준
        h = line_h * len(lines) + 10

        # document 내부 줄바꿈 너비를 -1로 설정해 강제 래핑 방지
        self.document().setTextWidth(-1)

        parent_w      = self.parent().width() if self.parent() else 1920
        max_allowed_w = max(parent_w - self._pos.x() - 20, 400)

        self.setFixedSize(
            min(max(max_w, 200), max_allowed_w),
            max(h, line_h + 10)
        )

    def text(self) -> str:
        """QLineEdit.text() 와 동일한 인터페이스를 제공한다."""
        return self.toPlainText()

    def keyPressEvent(self, event):
        """
        Ctrl+Enter : 입력 확정 신호 발생
        Escape     : 텍스트 지우고 취소 신호 발생
        그 외       : 기본 처리 (Enter = 줄바꿈 포함)
        """
        is_enter = event.key() in (Qt.Key_Return, Qt.Key_Enter)
        is_ctrl  = bool(event.modifiers() & Qt.ControlModifier)

        if is_enter and is_ctrl:
            self.editingFinished.emit()
        elif event.key() == Qt.Key_Escape:
            self.setPlainText("")
            self.editingFinished.emit()
        else:
            super().keyPressEvent(event)


# ════════════════════════════════════════════════
#  ToolBar — 상단 도구 모음
# ════════════════════════════════════════════════

class ToolBar(QtWidgets.QWidget):
    """
    화면 상단에 고정되는 반투명 다크 글래스 스타일 툴바.

    구성 그룹:
      1. 도구    : 펜·사각형·원·직선·화살표·글씨
      2. 색상+두께: 색상 선택, 두께 스핀박스
      3. 폰트    : 폰트 선택, 퀵 사이즈(10/16/24/36)
      4. 토글    : 채우기·형광·지우개
      5. 액션    : 되돌리기·저장·전체삭제
      6. 종료    : 종료 버튼 (빨간 포인트, 오른쪽 끝)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_HEIGHT)
        # 배경을 paintEvent에서 직접 그리기 위해 Qt 기본 배경 비활성화
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_ui()

    def paintEvent(self, event):
        """반투명 다크 글래스 배경과 하단 구분선을 직접 그린다."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 배경: 거의 불투명한 딥 네이비
        p.setBrush(QBrush(QColor(14, 16, 26, 215)))
        p.setPen(Qt.NoPen)
        p.drawRect(self.rect())

        # 하단 구분선: 아주 미묘한 흰색 빛
        p.setPen(QPen(QColor(255, 255, 255, 22), 1))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        p.end()

    def init_ui(self):
        """모든 버튼과 위젯을 생성하고 레이아웃에 배치한다."""

        # 전체 툴바 QSS (자식 위젯에 상속됨)
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
                width: 20px;
                height: 14px;
                background: rgba(255,255,255,20);
                border-left: 1px solid rgba(255,255,255,25);
                border-bottom: 1px solid rgba(255,255,255,15);
                border-top-right-radius: 6px;
            }
            QSpinBox::up-button:hover   { background: rgba(255,255,255,50); }
            QSpinBox::up-button:pressed { background: rgba(255,255,255,15); }
            QSpinBox::up-arrow {
                image: none;
                width: 0px;  height: 0px;
                border-left:   5px solid transparent;
                border-right:  5px solid transparent;
                border-bottom: 6px solid rgba(210,220,255,230);
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                height: 14px;
                background: rgba(255,255,255,20);
                border-left: 1px solid rgba(255,255,255,25);
                border-top: 1px solid rgba(255,255,255,15);
                border-bottom-right-radius: 6px;
            }
            QSpinBox::down-button:hover   { background: rgba(255,255,255,50); }
            QSpinBox::down-button:pressed { background: rgba(255,255,255,15); }
            QSpinBox::down-arrow {
                image: none;
                width: 0px;  height: 0px;
                border-left:  5px solid transparent;
                border-right: 5px solid transparent;
                border-top:   6px solid rgba(210,220,255,230);
            }
            QSpinBox:hover {
                border: 1px solid rgba(255,255,255,35);
                background: rgba(255,255,255,18);
            }
        """)

        # 최상위 수평 레이아웃
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(3)

        # ── 내부 헬퍼: 위젯 그룹을 pill 컨테이너로 묶기 ──────
        def make_group(*widgets, spacing=3) -> QtWidgets.QWidget:
            """
            여러 위젯을 하나의 둥근 반투명 컨테이너(pill)로 묶어 반환한다.
            시각적으로 관련 버튼들을 그룹화하는 데 사용한다.
            """
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

        # ── 그룹 1: 그리기 도구 ──────────────────────────────
        # (도구 키, 아이콘, 한국어명, 영어명) 순서로 정의
        tool_list = [
            ("pen",     "✏", "펜",     "Pen"),
            ("rect",    "▭", "사각형", "Rect"),
            ("ellipse", "◯", "원",     "Ellipse"),
            ("line",    "╱", "직선",   "Line"),
            ("arrow",   "➔", "화살표", "Arrow"),
            ("text",    "T", "글씨",   "Text"),
        ]

        self.btns = {}          # 버튼 참조 딕셔너리 (외부에서 스타일 변경 시 사용)
        tool_widgets = []

        for key, icon, ko, en in tool_list:
            btn = QtWidgets.QPushButton(f"{icon}  {tr(ko, en)}")
            btn.setFixedHeight(38)
            btn.setStyleSheet(_BTN_TOOL)
            btn.setProperty("tool_key", key)    # 클릭 핸들러에서 도구 식별용
            self.btns[key] = btn
            tool_widgets.append(btn)

        layout.addWidget(make_group(*tool_widgets, spacing=2))
        layout.addSpacing(6)

        # ── 그룹 2: 색상 + 두께 ──────────────────────────────
        self.color_preview = QtWidgets.QPushButton("● 색상" if LANG == "ko" else "● Color")
        self.color_preview.setFixedHeight(38)
        self.color_preview.setStyleSheet(_BTN_TOOL)
        # 색상 버튼은 update_color_preview()에서 글자색이 동적으로 변경됨

        # 두께 스핀박스 (1~120, 기본 4)
        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(1, 120)
        self.width_spin.setValue(4)
        self.width_spin.setFixedWidth(56)
        self.width_spin.setFixedHeight(28)

        # "W" 레이블 — 두께 스핀박스 앞에 표시
        lbl_w = QtWidgets.QLabel("W")
        lbl_w.setStyleSheet(
            "background: transparent; border: none;"
            " color: rgba(180,185,210,160); font-size: 11px;"
        )

        layout.addWidget(make_group(self.color_preview, lbl_w, self.width_spin, spacing=4))
        layout.addSpacing(6)

        # ── 그룹 3: 폰트 + 퀵 사이즈 ────────────────────────
        self.font_btn = QtWidgets.QPushButton("A  폰트" if LANG == "ko" else "A  Font")
        self.font_btn.setFixedHeight(38)
        self.font_btn.setStyleSheet(_BTN_TOOL)

        size_widgets = [self.font_btn]
        for sz in ["10", "16", "24", "36"]:
            btn = QtWidgets.QPushButton(sz)
            btn.setFixedWidth(34)
            btn.setFixedHeight(38)
            btn.setProperty("size_val", int(sz))    # quick_size() 에서 이 값을 읽음
            btn.setStyleSheet(_BTN_ICON)
            self.btns[f"fs{sz}"] = btn              # "fs10", "fs16" … 형태로 저장
            size_widgets.append(btn)

        layout.addWidget(make_group(*size_widgets, spacing=2))
        layout.addSpacing(6)

        # ── 그룹 4: 토글 (채우기·형광·지우개) ───────────────
        self.fill_btn   = QtWidgets.QPushButton("■  " + tr("채우기", "Fill"))
        self.hl_btn     = QtWidgets.QPushButton("▌  " + tr("형광",   "Highlight"))
        self.eraser_btn = QtWidgets.QPushButton("◻  " + tr("지우개", "Eraser"))

        for btn in (self.fill_btn, self.hl_btn, self.eraser_btn):
            btn.setFixedHeight(38)
            btn.setStyleSheet(_BTN_TOOL)

        layout.addWidget(make_group(self.fill_btn, self.hl_btn, self.eraser_btn, spacing=2))
        layout.addSpacing(6)

        # ── 그룹 5: 액션 버튼 ────────────────────────────────
        self.undo_btn     = QtWidgets.QPushButton("↩  " + tr("되돌리기", "Undo"))
        self.snapshot_btn = QtWidgets.QPushButton("⬡  " + tr("저장",     "Save"))
        self.clear_btn    = QtWidgets.QPushButton("✕  " + tr("전체삭제", "Clear"))

        for btn in (self.undo_btn, self.snapshot_btn, self.clear_btn):
            btn.setFixedHeight(38)
            btn.setStyleSheet(_BTN_TOOL)

        layout.addWidget(make_group(self.undo_btn, self.snapshot_btn, self.clear_btn, spacing=2))
        layout.addStretch()     # 남은 공간을 채워 종료 버튼을 오른쪽 끝으로 밀기

        # ── 종료 버튼 (단독, 빨간 포인트) ───────────────────
        self.exit_btn = QtWidgets.QPushButton("⏻  " + tr("종료", "Exit"))
        self.exit_btn.setFixedHeight(38)
        self.exit_btn.setStyleSheet("""
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
            QPushButton:pressed {
                background: rgba(150,20,20,100);
            }
        """)
        layout.addWidget(self.exit_btn)
        self.setLayout(layout)

    def update_button_styles(self, current_tool: str, fill: bool, hl: bool, eraser: bool):
        """
        현재 선택된 도구와 토글 상태에 따라 버튼 스타일을 갱신한다.
        ScreenDrawing.update_ui_styles() 에서 호출된다.
        """
        # 도구 버튼: 선택된 도구만 accent 글로우, 나머지는 기본
        for key in ("pen", "rect", "ellipse", "line", "arrow", "text"):
            _, accent = ICONS[key]
            style = _active_style(accent) if key == current_tool else _BTN_TOOL
            self.btns[key].setStyleSheet(style)

        # 토글 버튼: ON이면 해당 도구의 accent 색으로 하이라이트
        _, fill_accent   = ICONS["fill"]
        _, hl_accent     = ICONS["highlight"]
        _, eraser_accent = ICONS["eraser"]

        self.fill_btn.setStyleSheet(
            _toggle_on_style(fill_accent) if fill else _BTN_TOOL
        )
        self.hl_btn.setStyleSheet(
            _toggle_on_style(hl_accent) if hl else _BTN_TOOL
        )
        self.eraser_btn.setStyleSheet(
            _toggle_on_style(eraser_accent) if eraser else _BTN_TOOL
        )

    def update_color_preview(self, color: QColor):
        """
        색상 버튼의 글자색을 현재 선택된 펜 색상으로 변경한다.
        테두리는 기본 스타일과 동일하게 유지 (외곽선 없이 색상만 반영).
        """
        c = color.name()
        self.color_preview.setStyleSheet(f"""
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
#  ScreenDrawing — 메인 그리기 클래스
# ════════════════════════════════════════════════

class ScreenDrawing(QtWidgets.QWidget):
    """
    전체화면 투명 오버레이 위에서 그림을 그리는 메인 위젯.

    주요 구조:
      - canvas      : 실제 그림이 저장되는 QPixmap (투명 배경)
      - _pen_layer  : 일반 펜 드래그 중 임시 레이어 (가시 방지용)
      - _hl_layer   : 형광펜 드래그 중 임시 레이어
      - undo_stack  : 캔버스 스냅샷 스택 (최대 MAX_UNDO_STEPS)
      - toolbar     : 상단 ToolBar 위젯
    """

    def __init__(self):
        super().__init__()
        self.init_window()
        self.init_variables()
        self.init_ui()

    # ── 윈도우 초기화 ──────────────────────────────
    def init_window(self):
        """
        전체화면 투명 오버레이 윈도우를 설정한다.
        항상 다른 창 위에 표시되며 배경이 완전히 투명하다.
        """
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)     # 버튼 클릭 없이도 mouseMoveEvent 발생

        geo = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(geo)

        # 그림이 저장되는 투명 캔버스 (화면 크기와 동일)
        self.canvas = QPixmap(geo.size())
        self.canvas.fill(Qt.transparent)

    # ── 상태 변수 초기화 ───────────────────────────
    def init_variables(self):
        """
        모든 내부 상태 변수를 기본값으로 설정한다.
        저장된 설정 파일이 있으면 덮어씌운다.
        """
        # ── 사용자 설정 (저장/복원 대상) ──
        self.current_tool = "pen"
        self.pen_color    = QColor(255, 50, 50)     # 기본 색: 빨간색
        self.pen_width    = 4
        self.fill_enabled = False
        self.highlighter  = False
        self.eraser       = False
        self.text_font    = QFont("Sans", 24)

        # 저장된 설정이 있으면 위 값들을 덮어씌움
        self._load_settings()

        # ── 드로잉 상태 (저장 안 함) ──
        self.drawing     = False                    # 현재 드래그 중 여부
        self.start_point = QPoint()                 # 드래그 시작점
        self.end_point   = QPoint()                 # 드래그 현재/끝점
        self.path        = QtGui.QPainterPath()     # 펜 경로 (자유곡선)

        # 마우스 커서 위치 (커서 미리보기용, 초기값은 화면 밖)
        self._cursor_pos = QPoint(-100, -100)

        # 임시 레이어 — 드래그 중에만 사용, 마우스를 떼면 canvas에 합성
        self._hl_layer  = None  # 형광펜 임시 레이어
        self._pen_layer = None  # 일반 펜 임시 레이어 (겹침 가시 방지)

        # 텍스트 입력 위젯 참조 (None = 비활성)
        self._text_input = None

        # 실행취소 스택 (QPixmap 스냅샷 저장)
        self.undo_stack = []

        # 임시 도구 전환 상태 (Ctrl=지우개, Shift=직선, 키를 놓으면 복원)
        self._temp_eraser = False
        self._temp_line   = False
        self._saved_tool  = self.current_tool

    # ── 설정 불러오기 ──────────────────────────────
    def _load_settings(self):
        """
        SETTINGS_PATH 의 JSON 파일에서 사용자 설정을 불러온다.
        파일이 없거나 손상된 경우 예외를 무시하고 기본값을 유지한다.
        """
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 도구 — 유효한 값인지 검증
            tool = data.get("tool", "pen")
            if tool in ("pen", "rect", "ellipse", "line", "arrow", "text"):
                self.current_tool = tool

            # 색상 — QColor로 변환
            color = data.get("color")
            if color:
                self.pen_color = QColor(color)

            # 두께 — 범위 검증 (1~120)
            width = data.get("width")
            if isinstance(width, int) and 1 <= width <= 120:
                self.pen_width = width

            # 토글 상태
            self.fill_enabled = bool(data.get("fill",      False))
            self.highlighter  = bool(data.get("highlight", False))

            # 폰트
            font_family = data.get("font_family")
            font_size   = data.get("font_size")
            if font_family:
                size = font_size if isinstance(font_size, int) else 24
                self.text_font = QFont(font_family, size)

        except Exception:
            pass    # 오류 시 기본값 유지

    # ── 설정 저장 ──────────────────────────────────
    def _save_settings(self):
        """
        현재 사용자 설정을 SETTINGS_PATH 의 JSON 파일에 저장한다.
        종료 시(force_exit) 자동 호출된다.
        """
        try:
            data = {
                "tool":        self.current_tool,
                "color":       self.pen_color.name(),   # "#RRGGBB" 형식
                "width":       self.pen_width,
                "fill":        self.fill_enabled,
                "highlight":   self.highlighter,
                "font_family": self.text_font.family(),
                "font_size":   self.text_font.pointSize(),
            }
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass    # 저장 실패는 무시 (읽기 전용 파일시스템 등 대비)

    # ── UI 구성 ────────────────────────────────────
    def init_ui(self):
        """툴바를 생성하고 각 버튼에 이벤트 핸들러를 연결한다."""
        self.toolbar = ToolBar(self)
        self.toolbar.setGeometry(0, 0, self.width(), TOOLBAR_HEIGHT)

        # 도구·퀵사이즈 버튼 이벤트 연결
        for key, btn in self.toolbar.btns.items():
            if key.startswith("fs"):
                # "fs10" → quick_size(10), "fs16" → quick_size(16) …
                btn.clicked.connect(
                    lambda checked, b=btn: self.quick_size(b.property("size_val"))
                )
            else:
                # "pen" → set_tool("pen"), "rect" → set_tool("rect") …
                btn.clicked.connect(
                    lambda checked, k=key: self.set_tool(k)
                )

        # 나머지 버튼 이벤트 연결
        self.toolbar.color_preview.clicked.connect(self.select_color)
        self.toolbar.width_spin.valueChanged.connect(self.set_width)
        self.toolbar.font_btn.clicked.connect(self.select_font)
        self.toolbar.fill_btn.clicked.connect(self.toggle_fill)
        self.toolbar.hl_btn.clicked.connect(self.toggle_highlighter)
        self.toolbar.eraser_btn.clicked.connect(self.toggle_eraser)
        self.toolbar.undo_btn.clicked.connect(self.undo)
        self.toolbar.snapshot_btn.clicked.connect(self.save_snapshot)
        self.toolbar.clear_btn.clicked.connect(self.clear_canvas)
        self.toolbar.exit_btn.clicked.connect(self.force_exit)

        # UI 스타일 초기 적용 및 저장된 두께 스핀박스에 반영
        self.update_ui_styles()
        self.toolbar.width_spin.setValue(self.pen_width)

    # ════════════════════════════════════════════
    #  도구 및 상태 관리
    # ════════════════════════════════════════════

    def set_tool(self, tool: str):
        """
        그리기 도구를 변경한다.
        지우개가 켜져 있으면 (임시 전환이 아닌 경우) 지우개를 끈다.
        """
        self.current_tool = tool
        if self.eraser and not self._temp_eraser:
            self.eraser = False
        self.update_ui_styles()

    def set_width(self, val: int):
        """펜/지우개 두께 및 텍스트 폰트 크기를 변경한다. (스핀박스 valueChanged 신호에 연결)"""
        self.pen_width = val
        self.text_font.setPointSize(val)    # 두께 스핀박스가 글씨 크기도 동기화

    def toggle_fill(self):
        """채우기 모드를 ON/OFF 전환한다."""
        self.fill_enabled = not self.fill_enabled
        self.update_ui_styles()

    def toggle_highlighter(self):
        """형광펜 모드를 ON/OFF 전환한다."""
        self.highlighter = not self.highlighter
        self.update_ui_styles()

    def toggle_eraser(self):
        """지우개 모드를 ON/OFF 전환한다."""
        self.eraser = not self.eraser
        self.update_ui_styles()

    def update_ui_styles(self):
        """툴바의 버튼 스타일을 현재 상태에 맞게 갱신한다."""
        self.toolbar.update_button_styles(
            self.current_tool,
            self.fill_enabled,
            self.highlighter,
            self.eraser,
        )
        self.toolbar.update_color_preview(self.pen_color)

    def quick_size(self, size: int):
        """
        퀵 사이즈 버튼(10/16/24/36)을 눌렀을 때 호출된다.
        펜 두께와 텍스트 폰트 크기를 동시에 변경한다.
        """
        self.pen_width = size
        self.toolbar.width_spin.setValue(size)
        self.text_font.setPointSize(size)
        self.update()

    def select_color(self):
        """색상 선택 다이얼로그를 열고 선택된 색상을 펜 색으로 적용한다."""
        color = QtWidgets.QColorDialog.getColor(
            self.pen_color, self, tr("색상 선택", "Select Color")
        )
        if color.isValid():
            self.pen_color = color
            self.update_ui_styles()

    def select_font(self):
        """폰트 선택 다이얼로그를 열고 선택된 폰트를 텍스트 폰트로 적용한다."""
        font, ok = QtWidgets.QFontDialog.getFont(
            self.text_font, self, tr("폰트 선택", "Select Font")
        )
        if ok:
            self.text_font = font

    # ════════════════════════════════════════════
    #  핵심 그리기 로직
    # ════════════════════════════════════════════

    def get_pen(self, for_line: bool = False) -> QPen:
        """
        현재 설정에 맞는 QPen 을 반환한다.

        버그 수정 사항:
          1. 직선/화살표: FlatCap 강제 → 끝부분 원형 잔상 제거
          2. 형광+채우기+도형: NoPen 반환 → 외곽선·채우기 이중 겹침 방지
        """
        # 형광 + 채우기 + 도형 조합이면 외곽선을 없애 이중 렌더링 방지
        is_filled_hl_shape = (
            self.highlighter
            and self.fill_enabled
            and self.current_tool in ("rect", "ellipse")
            and not self.eraser
            and not for_line
        )
        if is_filled_hl_shape:
            return Qt.NoPen

        color = QColor(self.pen_color)
        if self.highlighter:
            color.setAlpha(128)     # 형광펜: 50% 투명도

        # 모든 도구 RoundCap (직선도 양끝 라운딩 처리)
        # 화살표는 draw_arrow 에서 폴리곤으로 직접 그리므로 cap 무관
        cap = Qt.RoundCap
        return QPen(color, self.pen_width, Qt.SolidLine, cap, Qt.RoundJoin)

    def get_brush(self) -> QBrush:
        """
        채우기가 활성화된 경우 현재 펜 색상으로 채운 QBrush 를 반환한다.
        형광펜 모드면 50% 투명도 적용.
        """
        if (self.fill_enabled
                and self.current_tool in ("rect", "ellipse", "arrow")
                and not self.eraser):
            color = QColor(self.pen_color)
            if self.highlighter:
                color.setAlpha(128)
            return QBrush(color)
        return Qt.NoBrush

    def draw_hl_line(self, painter: QPainter, start: QPoint, end: QPoint):
        """
        형광펜 직선을 겹침 없이 라운딩 처리하여 그린다.

        문제: QPen RoundCap 은 선 몸통과 양끝 반원을 별도 렌더링한다.
              반투명(형광)이면 겹치는 부분이 더 진해져 -0- 처럼 보인다.

        해결: 오프스크린 버퍼에 불투명(alpha=255)으로 RoundCap 선을 그린 뒤,
              버퍼 전체에 원하는 alpha(128)를 곱해서 painter 에 합성한다.
              렌더링이 버퍼 안에서 완전히 끝나므로 겹침이 없다.
        """
        r     = self.pen_width // 2 + 2
        x_min = min(start.x(), end.x()) - r
        y_min = min(start.y(), end.y()) - r
        x_max = max(start.x(), end.x()) + r
        y_max = max(start.y(), end.y()) + r
        w, h  = x_max - x_min, y_max - y_min

        if w < 1 or h < 1:
            return

        # 오프스크린 버퍼 (투명 배경)
        buf = QPixmap(w, h)
        buf.fill(Qt.transparent)

        # 버퍼 좌표계 오프셋 적용
        s = QPoint(start.x() - x_min, start.y() - y_min)
        e = QPoint(end.x()   - x_min, end.y()   - y_min)

        # 불투명 색상으로 RoundCap 선 그리기 (버퍼 안이므로 겹침 무관)
        bp = QPainter(buf)
        bp.setRenderHint(QPainter.Antialiasing)
        color_opaque = QColor(self.pen_color)
        color_opaque.setAlpha(255)
        pen = QPen(color_opaque, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        bp.setPen(pen)
        bp.drawLine(s, e)
        bp.end()

        # 버퍼 전체에 alpha=128 곱해 반투명 적용
        ap = QPainter(buf)
        ap.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        ap.fillRect(buf.rect(), QColor(0, 0, 0, 128))
        ap.end()

        # 결과를 원래 painter 좌표계에 합성
        painter.drawPixmap(x_min, y_min, buf)

    def draw_arrow(self, painter: QPainter, start: QPoint, end: QPoint):
        """
        사다리꼴 몸통 + 삼각형 화살촉으로 구성된 화살표를 그린다.
        몸통은 시작점에서 얇고 화살촉 쪽으로 갈수록 두꺼워진다.
        """
        if start == end:
            return

        dx     = end.x() - start.x()
        dy     = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return

        angle = math.atan2(dy, dx)

        # 화살촉 크기 계산
        head_len   = max(self.pen_width * 3,   15)
        head_width = max(self.pen_width * 2.5, 12)

        # 몸통 끝점 (화살촉 시작점)
        body_end_len = max(0, length - head_len)
        body_end = QPointF(
            start.x() + math.cos(angle) * body_end_len,
            start.y() + math.sin(angle) * body_end_len,
        )

        # 수직 방향 단위벡터 (몸통 너비 계산용)
        perp_cos = math.cos(angle + math.pi / 2)
        perp_sin = math.sin(angle + math.pi / 2)

        # 몸통 사다리꼴 꼭짓점 (p1~p4)
        # p1, p2: 시작점 양쪽 (좁음), p3, p4: 몸통 끝 양쪽 (넓음)
        w_start = self.pen_width / 2.0
        w_end   = float(self.pen_width)

        p1 = QPointF(start.x() + w_start * perp_cos,  start.y() + w_start * perp_sin)
        p2 = QPointF(start.x() - w_start * perp_cos,  start.y() - w_start * perp_sin)
        p3 = QPointF(body_end.x() - w_end * perp_cos, body_end.y() - w_end * perp_sin)
        p4 = QPointF(body_end.x() + w_end * perp_cos, body_end.y() + w_end * perp_sin)

        # 화살촉 삼각형 꼭짓점 (h1~h3)
        h1 = QPointF(end.x(), end.y())                                             # 화살촉 끝
        h2 = QPointF(body_end.x() + head_width * perp_cos,
                     body_end.y() + head_width * perp_sin)
        h3 = QPointF(body_end.x() - head_width * perp_cos,
                     body_end.y() - head_width * perp_sin)

        # 채우기 색상 설정
        color = QColor(self.pen_color)
        if self.highlighter:
            color.setAlpha(128)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPolygon(QPolygonF([p1, p2, p3, p4]))    # 몸통
        painter.drawPolygon(QPolygonF([h1, h2, h3]))        # 화살촉

    # ════════════════════════════════════════════
    #  텍스트 입력 처리
    # ════════════════════════════════════════════

    def _open_text_input(self, pos: QPoint):
        """클릭한 위치에 FloatingTextInput 을 생성한다."""
        self._destroy_input()
        self._text_input = FloatingTextInput(self, pos, self.text_font, self.pen_color)
        self._text_input.editingFinished.connect(self._commit_text)

    def _destroy_input(self):
        """현재 열려있는 텍스트 입력창을 닫고 메모리에서 제거한다."""
        if self._text_input:
            self._text_input.hide()
            self._text_input.deleteLater()
            self._text_input = None

    def _commit_text(self):
        """
        입력된 텍스트를 캔버스에 그리고 입력창을 닫는다.
        여러 줄이 있으면 줄바꿈마다 아래로 내려 그린다.
        """
        if not self._text_input:
            return

        # 앞뒤 빈 줄 제거 (내용이 없으면 그리지 않음)
        text = self._text_input.text().strip('\n').rstrip()
        pos, font, color = (
            self._text_input._pos,
            self._text_input._font,
            self._text_input._color,
        )
        self._destroy_input()

        if not text:
            return

        self._push_undo()
        line_height = QtGui.QFontMetrics(font).height()

        p = QPainter(self.canvas)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(font)
        p.setPen(QPen(color))
        for i, line in enumerate(text.split('\n')):
            p.drawText(pos.x(), pos.y() + i * line_height, line)
        p.end()

        self.update()

    # ════════════════════════════════════════════
    #  마우스 이벤트
    # ════════════════════════════════════════════

    def mousePressEvent(self, event):
        """
        마우스 버튼을 누를 때 호출된다.

        처리 순서:
          1. 툴바 영역 클릭 → 무시
          2. 텍스트 입력 중 → 확정
          3. 우클릭 등 → 무시
          4. 텍스트 도구 → 입력창 생성
          5. 그 외 → 드로잉 시작 + 임시 레이어 초기화
        """
        if event.pos().y() <= TOOLBAR_HEIGHT:
            return                              # 툴바 영역 무시

        if self._text_input:
            self._commit_text()                 # 텍스트 입력 확정
            return

        if event.button() != Qt.LeftButton:
            return                              # 좌클릭만 처리

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
        self.path = QtGui.QPainterPath()
        self.path.moveTo(event.pos())

        # 형광 펜용 임시 레이어 초기화
        if self.highlighter and self.current_tool == "pen" and not self.eraser:
            self._hl_layer = QPixmap(self.canvas.size())
            self._hl_layer.fill(Qt.transparent)
        # 일반 펜용 임시 레이어 초기화 (가시 방지)
        elif not self.highlighter and self.current_tool == "pen" and not self.eraser:
            self._pen_layer = QPixmap(self.canvas.size())
            self._pen_layer.fill(Qt.transparent)

    def mouseMoveEvent(self, event):
        """
        마우스를 움직일 때 호출된다.

        처리:
          - 커서 위치 갱신 (지우개·형광펜 미리보기)
          - 드로잉 중이면 각 도구에 맞게 임시 레이어에 그리기
        """
        self._cursor_pos = event.pos()

        # 지우개·형광펜은 커서 미리보기를 위해 항상 repaint
        if self.eraser or (self.highlighter and self.current_tool == "pen"):
            self.update()

        if not self.drawing:
            return

        self.end_point = event.pos()

        # ── 지우개 (rect/ellipse/arrow 제외: 드래그로 범위 지정) ──
        if self.eraser and self.current_tool not in ("rect", "ellipse", "line", "arrow"):
            p = QPainter(self.canvas)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.setBrush(QBrush(Qt.black))
            p.setPen(Qt.NoPen)
            r = self.pen_width // 2
            p.drawEllipse(event.pos(), r, r)
            p.end()
            self.update()
            return

        # ── 형광펜 자유곡선 ──
        # _hl_layer 를 매번 초기화 후 전체 경로를 다시 그려 매끄러운 선 유지
        if self.highlighter and self.current_tool == "pen":
            if self._hl_layer:
                self._hl_layer.fill(Qt.transparent)
                p = QPainter(self._hl_layer)
                p.setRenderHint(QPainter.Antialiasing)
                p.setPen(self.get_pen(for_line=False))
                self.path.lineTo(event.pos())
                p.drawPath(self.path)
                p.end()
            self.update()
            return

        # ── 일반 펜 자유곡선 ──
        # _pen_layer 를 매번 초기화 후 전체 경로를 다시 그려 가시(겹침) 방지
        if self.current_tool == "pen":
            if self._pen_layer:
                self._pen_layer.fill(Qt.transparent)
                p = QPainter(self._pen_layer)
                p.setRenderHint(QPainter.Antialiasing)
                p.setPen(self.get_pen(for_line=False))
                self.path.lineTo(event.pos())
                p.drawPath(self.path)
                p.end()
            self.update()
            return

        # ── 도형 (rect·ellipse·line·arrow): 미리보기만 갱신 ──
        if self.current_tool in ("rect", "ellipse", "line", "arrow"):
            self.update()

    def mouseReleaseEvent(self, event):
        """
        마우스 버튼을 뗄 때 호출된다.

        처리:
          - 형광펜/일반 펜: 임시 레이어 → canvas 합성
          - 도형/지우개  : canvas 에 직접 확정
        """
        if not self.drawing:
            return

        self.drawing   = False
        self.end_point = event.pos()

        # 형광펜 확정: _hl_layer → canvas 합성
        if self.highlighter and self.current_tool == "pen" and self._hl_layer:
            p = QPainter(self.canvas)
            p.drawPixmap(0, 0, self._hl_layer)
            p.end()
            self._hl_layer = None
            self.update()
            return

        # 일반 펜 확정: _pen_layer → canvas 합성
        if not self.highlighter and self.current_tool == "pen" and self._pen_layer:
            p = QPainter(self.canvas)
            p.drawPixmap(0, 0, self._pen_layer)
            p.end()
            self._pen_layer = None
            self.update()
            return

        # 도형 / 지우개 범위 확정
        if not self.eraser or self.current_tool in ("rect", "ellipse", "line", "arrow"):
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)

            if self.eraser:
                # 지우개 범위 지정 모드 (rect/ellipse/arrow)
                # line은 아래서 별도 처리 (펜으로 지워야 하므로)
                p.setCompositionMode(QPainter.CompositionMode_Clear)
                p.setBrush(QBrush(Qt.black))
                p.setPen(Qt.NoPen)
            else:
                is_line_tool = self.current_tool in ("line", "arrow")
                p.setPen(self.get_pen(for_line=is_line_tool))
                p.setBrush(self.get_brush())

            rect = QRect(self.start_point, self.end_point).normalized()
            if self.current_tool == "rect":
                p.drawRect(rect)
            elif self.current_tool == "ellipse":
                p.drawEllipse(rect)
            elif self.current_tool == "line":
                if self.eraser:
                    # 지우개+직선: CompositionMode_Clear + 두꺼운 RoundCap 펜으로 선 지우기
                    erase_pen = QPen(Qt.black, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    p.setPen(erase_pen)
                    p.drawLine(self.start_point, self.end_point)
                elif self.highlighter:
                    self.draw_hl_line(p, self.start_point, self.end_point)
                else:
                    p.drawLine(self.start_point, self.end_point)
            elif self.current_tool == "arrow":
                self.draw_arrow(p, self.start_point, self.end_point)
            p.end()

        self.update()

    # ════════════════════════════════════════════
    #  화면 출력 (paintEvent)
    # ════════════════════════════════════════════

    def paintEvent(self, event):
        """
        매 프레임 호출되는 렌더링 메서드.
        canvas → 임시 레이어(펜/형광) → 커서 미리보기 → 도형 미리보기 순으로 그린다.
        """
        painter = QPainter(self)

        # 1. 확정된 그림 (canvas)
        painter.drawPixmap(0, 0, self.canvas)

        # 2. 드래그 중인 임시 레이어
        if self._pen_layer:
            painter.drawPixmap(0, 0, self._pen_layer)
        if self._hl_layer:
            painter.drawPixmap(0, 0, self._hl_layer)

        # 3. 커서 미리보기 (툴바 아래 영역에서만)
        if self._cursor_pos.y() > TOOLBAR_HEIGHT:
            if self.eraser:
                # 지우개: 점선 원으로 크기 표시
                r = max(self.pen_width // 2, 2)
                painter.setPen(QPen(QColor(200, 200, 200, 180), 1, Qt.DashLine))
                painter.drawEllipse(self._cursor_pos, r, r)
            elif self.highlighter and self.current_tool == "pen":
                # 형광펜: 반투명 채워진 원으로 크기 표시
                r = max(self.pen_width // 2, 2)
                c = QColor(self.pen_color)
                c.setAlpha(100)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(c))
                painter.drawEllipse(self._cursor_pos, r, r)

        # 4. 도형 드래그 중 미리보기 (확정 전 점선/실선 표시)
        if self.drawing and self.current_tool in ("rect", "ellipse", "line", "arrow"):
            pv = QPainter(self)
            pv.setRenderHint(QPainter.Antialiasing)

            if self.eraser:
                # 지우개 범위: 빨간 점선 (arrow는 draw_arrow 호출 전에 별도 처리)
                pv.setPen(QPen(QColor(255, 80, 80, 200), 1.5, Qt.DashLine))
                pv.setBrush(QBrush(QColor(255, 80, 80, 40)))
            else:
                is_line_tool = self.current_tool in ("line", "arrow")
                pv.setPen(self.get_pen(for_line=is_line_tool))
                pv.setBrush(self.get_brush())

            rect = QRect(self.start_point, self.end_point).normalized()
            if self.current_tool == "rect":
                pv.drawRect(rect)
            elif self.current_tool == "ellipse":
                pv.drawEllipse(rect)
            elif self.current_tool == "line":
                if self.eraser:
                    # 지우개 모드: 직선 모양을 빨간 반투명으로 미리보기
                    saved_color = self.pen_color
                    self.pen_color = QColor(255, 80, 80, 120)
                    self.draw_hl_line(pv, self.start_point, self.end_point)
                    self.pen_color = saved_color
                elif self.highlighter:
                    self.draw_hl_line(pv, self.start_point, self.end_point)
                else:
                    pv.drawLine(self.start_point, self.end_point)
            elif self.current_tool == "arrow":
                if self.eraser:
                    # 지우개 모드: 화살표 모양을 빨간 반투명으로 미리보기
                    saved_color = self.pen_color
                    self.pen_color = QColor(255, 80, 80, 120)
                    self.draw_arrow(pv, self.start_point, self.end_point)
                    self.pen_color = saved_color
                else:
                    self.draw_arrow(pv, self.start_point, self.end_point)

    # ════════════════════════════════════════════
    #  유틸리티 기능
    # ════════════════════════════════════════════

    def _push_undo(self):
        """현재 canvas 를 undo_stack 에 스냅샷으로 저장한다. (최대 MAX_UNDO_STEPS)"""
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > MAX_UNDO_STEPS:
            self.undo_stack.pop(0)      # 가장 오래된 스냅샷 제거

    def undo(self):
        """가장 최근 스냅샷으로 canvas 를 되돌린다."""
        if self.undo_stack:
            self.canvas = self.undo_stack.pop()
            self.update()

    def clear_canvas(self):
        """canvas 를 완전히 지운다. (되돌리기 가능)"""
        self._push_undo()
        self.canvas.fill(Qt.transparent)
        self.update()

    def save_snapshot(self):
        """
        canvas 를 투명 PNG 파일로 저장한다.
        저장 경로: ~/drawing_YYYYMMDD_HHMMSS.png
        저장 완료 후 2초간 화면 상단에 알림 메시지를 표시한다.
        """
        home = os.path.expanduser("~")
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(home, f"drawing_{ts}.png")
        self.canvas.save(path, "PNG")

        # 저장 완료 알림 레이블 (2초 후 자동 제거)
        msg = QtWidgets.QLabel(tr(f"저장됨: {path}", f"Saved: {path}"), self)
        msg.setStyleSheet(
            "background-color: #1A2540; color: #81C784;"
            " padding: 8px; border-radius: 5px;"
        )
        msg.adjustSize()
        msg.move((self.width() - msg.width()) // 2, TOOLBAR_HEIGHT + 10)
        msg.show()
        QTimer.singleShot(2000, msg.deleteLater)

    def force_exit(self):
        """설정을 저장하고 프로그램을 종료한다."""
        self._save_settings()
        QtWidgets.QApplication.quit()

    # ════════════════════════════════════════════
    #  키보드 단축키
    # ════════════════════════════════════════════

    def keyPressEvent(self, event):
        """
        키보드 단축키 처리.

        단축키 목록:
          Ctrl 누름   : 임시 지우개 모드 (키를 뗄 때 원래 도구로 복원)
          Shift 누름  : 임시 직선 모드 (키를 뗄 때 원래 도구로 복원)
          Escape      : 텍스트 입력 취소 또는 프로그램 종료
          Ctrl + Z    : 되돌리기
          Ctrl + S    : 저장 (PNG)
          Ctrl + Q    : 종료
          C           : 전체 지우기
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
            # 텍스트 입력 중이면 취소, 아니면 종료
            if self._text_input:
                self._destroy_input()
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

    def keyReleaseEvent(self, event):
        """
        임시 도구 전환(Ctrl=지우개, Shift=직선) 키를 뗄 때 원래 도구로 복원한다.
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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ScreenDrawing()
    window.showFullScreen()
    sys.exit(app.exec_())
