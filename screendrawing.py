#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScreenDrawing
Version: 1.1.0
Author: Jeong SeongYong
Email: iyagicom@gmail.com
Description: Lightweight Wayland screen drawing tool
             (pen, shapes, text, highlight, eraser, undo, screenshot)
License: GPL-2.0 or later
"""

# Copyright (C) 2026 Jeong SeongYong
#
# [KOR] 이 프로그램은 자유 소프트웨어입니다. 당신은 자유 소프트웨어 재단이 공표한
# GNU 일반 공중 사용 허가서(GPL) 제2판 또는 (당신의 선택에 따라) 그 이후의
# 버전을 준수하는 조건으로 이 프로그램을 재배포하거나 수정할 수 있습니다.
#
# [ENG] This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# 이 프로그램이 유용하게 사용되기를 바라지만, 어떠한 형태의 보증도 제공하지 않습니다.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

import sys
import os
import locale
from datetime import datetime
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer
from PyQt5.QtGui import (QPainter, QPen, QColor, QPixmap, QBrush, QFont)

TOOLBAR_HEIGHT = 56

# ───────────────────────────────────────────────
#  언어 감지
# ───────────────────────────────────────────────
def _detect_lang() -> str:
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

LANG = _detect_lang()

def tr(ko: str, en: str) -> str:
    return ko if LANG == "ko" else en


# ───────────────────────────────────────────────
#  아이콘 & 스타일
# ───────────────────────────────────────────────
ICONS = {
    "pen":       ("✏",  "#4FC3F7"),   # U+270F
    "rect":      ("▭",  "#81C784"),   # U+25AD
    "ellipse":   ("◯",  "#CE93D8"),   # U+25EF  (⬭ 대신)
    "line":      ("/",  "#FFB74D"),   # 슬래시
    "text":      ("T",  "#F48FB1"),
    "eraser":    ("□",  "#90A4AE"),   # U+25A1
    "fill":      ("■",  "#78909C"),   # U+25A0
    "highlight": ("▌",  "#FFD600"),   # U+258C
    "clear":     ("✕",  "#EF9A9A"),   # clear all
    "exit":      ("✕",  "#EF5350"),   # U+2715
}

ON_STYLE = """
    QPushButton {
        background: rgba(220, 50, 50, 0.85);
        border: 1.5px solid rgba(255, 100, 100, 0.95);
        border-radius: 8px;
        color: #FFFFFF;
        padding: 5px 11px;
        font-size: 13px;
        min-width: 52px;
    }
    QPushButton:hover { background: rgb(220, 50, 50); }
"""

LABEL_STYLE = """
    QLabel {
        background-color: #3E4460;
        color: #FFFFFF;
        font-size: 12px;
        font-weight: bold;
        border-radius: 4px;
        padding: 2px 6px;
    }
"""


def make_tool_btn(ko_label: str, en_label: str, key: str):
    emoji, _ = ICONS.get(key, ("?", "#fff"))
    btn = QtWidgets.QPushButton(f"{emoji}  {tr(ko_label, en_label)}")
    btn.setProperty("tool_key", key)
    return btn


# ───────────────────────────────────────────────
#  툴바
# ───────────────────────────────────────────────
class ToolBar(QtWidgets.QWidget):

    BASE_STYLE = """
        QWidget {
            background-color: #1A1D26;
            color: #E0E0E0;
            font-size: 13px;
        }
        QPushButton {
            background-color: #2E3243;
            border: 1px solid #3E4460;
            border-radius: 8px;
            padding: 5px 11px;
            color: #E0E0E0;
            font-size: 13px;
            min-width: 52px;
        }
        QPushButton:hover {
            background-color: #3A4060;
            border-color: #5A6080;
        }
        QPushButton:pressed { background-color: #252840; }
        QLabel {
            background: transparent;
            color: #707080;
            font-size: 12px;
        }
        QSpinBox {
            background-color: #2E3243;
            border: 1px solid #3E4460;
            border-radius: 6px;
            color: #E0E0E0;
            padding: 2px 4px;
            font-size: 13px;
        }
        QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_HEIGHT)
        self.setStyleSheet(self.BASE_STYLE)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(5)

        # ── 도구 버튼 ──
        self.pen_btn     = make_tool_btn("펜",    "Pen",     "pen")
        self.rect_btn    = make_tool_btn("사각형", "Rect",    "rect")
        self.ellipse_btn = make_tool_btn("원",    "Ellipse", "ellipse")
        self.line_btn    = make_tool_btn("직선",  "Line",    "line")
        self.text_btn    = make_tool_btn("글씨",  "Text",    "text")

        self._tool_btns = {
            "pen":     self.pen_btn,
            "rect":    self.rect_btn,
            "ellipse": self.ellipse_btn,
            "line":    self.line_btn,
            "text":    self.text_btn,
        }

        # ── 색상·두께 ──
        self.color_preview = QtWidgets.QPushButton(tr("● 색상", "● Color"))
        self.width_label   = QtWidgets.QLabel(tr("두께", "Width"))
        self.width_label.setStyleSheet(LABEL_STYLE)
        self.width_spin    = QtWidgets.QSpinBox()
        self.width_spin.setRange(1, 120)
        self.width_spin.setValue(4)
        self.width_spin.setFixedWidth(64)

        # ── 폰트 + 퀵 크기 ──
        self.font_btn        = QtWidgets.QPushButton(tr("A  폰트", "A  Font"))
        self.font_size_label = QtWidgets.QLabel(tr("크기", "Size"))
        self.font_size_label.setStyleSheet(LABEL_STYLE)
        self.font_size_spin  = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(8, 120)
        self.font_size_spin.setValue(24)
        self.font_size_spin.setFixedWidth(64)

        self.fs10_btn = QtWidgets.QPushButton("10")
        self.fs16_btn = QtWidgets.QPushButton("16")
        self.fs24_btn = QtWidgets.QPushButton("24")
        self.fs36_btn = QtWidgets.QPushButton("36")
        for b in (self.fs10_btn, self.fs16_btn, self.fs24_btn, self.fs36_btn):
            b.setFixedWidth(38)

        # ── 채우기 / 형광 / 지우개 ──
        self.fill_btn   = make_tool_btn("채우기", "Fill",   "fill")
        self.hl_btn     = QtWidgets.QPushButton(tr("▌  형광", "▌  Highlight"))
        self.eraser_btn = make_tool_btn("지우개", "Eraser", "eraser")

        # ── undo / 스크린샷 ──
        self.undo_btn     = QtWidgets.QPushButton(tr("← 실행취소", "← Undo"))
        self.snapshot_btn = QtWidgets.QPushButton(tr("[ ] 저장",  "[ ] Save"))

        # ── 전체지우기·종료 ──
        self.clear_btn = make_tool_btn("전체지우기", "Clear All", "clear")
        self.exit_btn  = QtWidgets.QPushButton(tr("✕  종료", "✕  Exit"))
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A1E1E;
                border: 1px solid #7A3030;
                border-radius: 8px;
                color: #FF6B6B;
                padding: 5px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #6A2525;
                border-color: #EF5350;
                color: #FF9090;
            }
        """)

        def sep():
            f = QtWidgets.QFrame()
            f.setFrameShape(QtWidgets.QFrame.VLine)
            f.setFrameShadow(QtWidgets.QFrame.Plain)
            f.setStyleSheet(
                "QFrame { color: #3E4460; "
                "min-width:1px; max-width:1px; margin: 6px 2px; }"
            )
            return f

        # ── 배치 ──
        for btn in [self.pen_btn, self.rect_btn, self.ellipse_btn,
                    self.line_btn, self.text_btn]:
            btn.setFixedHeight(38)
            layout.addWidget(btn)

        layout.addWidget(sep())
        self.color_preview.setFixedHeight(38)
        layout.addWidget(self.color_preview)
        layout.addWidget(self.width_label)
        layout.addWidget(self.width_spin)

        layout.addWidget(sep())
        self.font_btn.setFixedHeight(38)
        layout.addWidget(self.font_btn)
        layout.addWidget(self.font_size_label)
        layout.addWidget(self.font_size_spin)
        for b in (self.fs10_btn, self.fs16_btn, self.fs24_btn, self.fs36_btn):
            b.setFixedHeight(38)
            layout.addWidget(b)

        layout.addWidget(sep())
        self.fill_btn.setFixedHeight(38)
        layout.addWidget(self.fill_btn)

        layout.addWidget(sep())
        self.hl_btn.setFixedHeight(38)
        layout.addWidget(self.hl_btn)

        layout.addWidget(sep())
        self.eraser_btn.setFixedHeight(38)
        layout.addWidget(self.eraser_btn)

        layout.addWidget(sep())
        self.undo_btn.setFixedHeight(38)
        layout.addWidget(self.undo_btn)
        self.snapshot_btn.setFixedHeight(38)
        layout.addWidget(self.snapshot_btn)

        layout.addWidget(sep())
        self.clear_btn.setFixedHeight(38)
        layout.addWidget(self.clear_btn)

        layout.addStretch()
        self.exit_btn.setFixedHeight(38)
        layout.addWidget(self.exit_btn)

        self.setLayout(layout)

    def set_active(self, active_key):
        for key, btn in self._tool_btns.items():
            _, accent = ICONS.get(key, ("", "#4FC3F7"))
            if key == active_key:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #1A2540;
                        border: 1.5px solid {accent};
                        border-radius: 8px;
                        color: {accent};
                        padding: 5px 11px;
                        font-size: 13px;
                        min-width: 52px;
                    }}
                    QPushButton:hover {{ background-color: #202d50; }}
                """)
            else:
                btn.setStyleSheet("")

    def set_fill_active(self, on: bool):
        self.fill_btn.setStyleSheet(ON_STYLE if on else "")

    def set_hl_active(self, on: bool):
        self.hl_btn.setStyleSheet(ON_STYLE if on else "")

    def set_eraser_active(self, on: bool):
        self.eraser_btn.setStyleSheet(ON_STYLE if on else "")

    def update_color_preview(self, color: QColor):
        r, g, b = color.red(), color.green(), color.blue()
        tc = "#111" if (r * 0.299 + g * 0.587 + b * 0.114) > 160 else "#EEE"
        self.color_preview.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r},{g},{b});
                border: 1px solid rgba(255,255,255,0.30);
                border-radius: 8px;
                color: {tc};
                padding: 5px 11px;
                font-size: 13px;
                min-width: 52px;
            }}
            QPushButton:hover {{ border: 1.5px solid rgba(255,255,255,0.60); }}
        """)


# ───────────────────────────────────────────────
#  인라인 텍스트 입력
# ───────────────────────────────────────────────
class FloatingTextInput(QtWidgets.QLineEdit):
    def __init__(self, parent, pos: QPoint, font: QFont, color: QColor):
        super().__init__(parent)
        self._pos   = pos
        self._font  = QFont(font)
        self._color = QColor(color)

        fm = QtGui.QFontMetrics(font)
        h  = fm.height() + 12
        self.setGeometry(pos.x(), pos.y() - h // 2, 500, h)
        self.setFont(font)
        self.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                border-bottom: 2px solid {color.name()};
                color: {color.name()};
                selection-background-color: rgba(255,255,255,0.25);
                padding: 0px 2px;
            }}
        """)
        self.setFrame(False)
        self.show()
        self.setFocus()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            self.editingFinished.emit()
        else:
            super().keyPressEvent(event)


# ───────────────────────────────────────────────
#  메인 위젯
# ───────────────────────────────────────────────
class ScreenDrawing(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        screen = QtWidgets.QApplication.primaryScreen()
        self._screen  = screen
        geo = screen.geometry()
        self.setGeometry(geo)

        self.canvas = QPixmap(self.size())
        self.canvas.fill(Qt.transparent)

        # 형광펜 임시 레이어 (자유곡선 겹침 방지)
        self._hl_layer = None

        # undo 스택
        self._undo_stack = []
        self._max_undo   = 30

        # 상태
        self.current_tool = "pen"
        self.pen_color    = QColor(255, 50, 50)
        self.pen_width    = 4
        self.fill_enabled = False
        self.highlighter  = False
        self.eraser       = False

        self.text_font   = QFont("Sans", 24)
        self._text_input = None

        self.drawing     = False
        self.start_point = QPoint()
        self.end_point   = QPoint()
        self.path        = QtGui.QPainterPath()

        # 커서 미리보기
        self._cursor_pos = QPoint()
        self.setMouseTracking(True)

        # 툴바
        self.toolbar = ToolBar(self)
        self.toolbar.setGeometry(0, 0, geo.width(), TOOLBAR_HEIGHT)
        self.toolbar.set_active("pen")
        self.toolbar.update_color_preview(self.pen_color)

        # 연결
        self.toolbar.pen_btn.clicked.connect(lambda: self.set_tool("pen"))
        self.toolbar.rect_btn.clicked.connect(lambda: self.set_tool("rect"))
        self.toolbar.ellipse_btn.clicked.connect(lambda: self.set_tool("ellipse"))
        self.toolbar.line_btn.clicked.connect(lambda: self.set_tool("line"))
        self.toolbar.text_btn.clicked.connect(lambda: self.set_tool("text"))

        self.toolbar.color_preview.clicked.connect(self.select_color)
        self.toolbar.width_spin.valueChanged.connect(self.set_width)

        self.toolbar.font_btn.clicked.connect(self.select_font)
        self.toolbar.font_size_spin.valueChanged.connect(self.set_font_size)

        self.toolbar.fs10_btn.clicked.connect(lambda: self.quick_size(10))
        self.toolbar.fs16_btn.clicked.connect(lambda: self.quick_size(16))
        self.toolbar.fs24_btn.clicked.connect(lambda: self.quick_size(24))
        self.toolbar.fs36_btn.clicked.connect(lambda: self.quick_size(36))

        self.toolbar.fill_btn.clicked.connect(self.toggle_fill)
        self.toolbar.hl_btn.clicked.connect(self.toggle_highlighter)
        self.toolbar.eraser_btn.clicked.connect(self.toggle_eraser)

        self.toolbar.undo_btn.clicked.connect(self.undo)
        self.toolbar.snapshot_btn.clicked.connect(self.save_snapshot)
        self.toolbar.clear_btn.clicked.connect(self.clear_canvas)
        self.toolbar.exit_btn.clicked.connect(self.force_exit)

    # ── 종료 ──────────────────────────────────
    def force_exit(self):
        QtWidgets.QApplication.quit()
        os._exit(0)

    # ── undo ──────────────────────────────────
    def _push_undo(self):
        self._undo_stack.append(self.canvas.copy())
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)

    def undo(self):
        if self._undo_stack:
            self.canvas = self._undo_stack.pop()
            self.update()

    # ── 스크린샷 저장 ─────────────────────────
    def save_snapshot(self):
        """낙서 레이어만 투명 PNG로 저장"""
        home = os.path.expanduser("~")
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(home, f"screendrawing_{ts}.png")
        self.canvas.save(path, "PNG")

        msg = QtWidgets.QLabel(
            tr(f">> 저장됨: {path}", f">> Saved: {path}"), self
        )
        msg.setStyleSheet("""
            QLabel {
                background-color: #1A2540;
                color: #81C784;
                border: 1px solid #3E4460;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
            }
        """)
        msg.adjustSize()
        geo = self.geometry()
        msg.move((geo.width() - msg.width()) // 2, TOOLBAR_HEIGHT + 20)
        msg.show()
        msg.raise_()
        QTimer.singleShot(2500, msg.deleteLater)


    def set_tool(self, tool):
        self.current_tool = tool
        self.toolbar.set_active(tool)

    def set_width(self, value):
        self.pen_width = value

    def quick_size(self, size: int):
        self.pen_width = size
        self.toolbar.width_spin.blockSignals(True)
        self.toolbar.width_spin.setValue(size)
        self.toolbar.width_spin.blockSignals(False)
        self.text_font.setPointSize(size)
        self.toolbar.font_size_spin.blockSignals(True)
        self.toolbar.font_size_spin.setValue(size)
        self.toolbar.font_size_spin.blockSignals(False)

    def toggle_fill(self):
        self.fill_enabled = not self.fill_enabled
        self.toolbar.set_fill_active(self.fill_enabled)

    def toggle_highlighter(self):
        self.highlighter = not self.highlighter
        self.toolbar.set_hl_active(self.highlighter)

    def toggle_eraser(self):
        self.eraser = not self.eraser
        self.toolbar.set_eraser_active(self.eraser)

    def select_color(self):
        color = QtWidgets.QColorDialog.getColor(
            self.pen_color, self, tr("색상 선택", "Select Color"))
        if color.isValid():
            self.pen_color = color
            self.toolbar.update_color_preview(color)

    def select_font(self):
        font, ok = QtWidgets.QFontDialog.getFont(
            self.text_font, self, tr("폰트 선택", "Select Font"))
        if ok:
            self.text_font = font
            self.toolbar.font_size_spin.blockSignals(True)
            self.toolbar.font_size_spin.setValue(font.pointSize())
            self.toolbar.font_size_spin.blockSignals(False)

    def set_font_size(self, size):
        self.text_font.setPointSize(size)

    def clear_canvas(self):
        self._push_undo()
        self.canvas.fill(Qt.transparent)
        self.update()

    # ── 펜·브러시 ─────────────────────────────
    def make_pen(self):
        return QPen(self.pen_color, self.pen_width,
                    Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

    def make_brush(self):
        if self.fill_enabled and self.current_tool in ("rect", "ellipse") and not self.eraser:
            return QBrush(self.pen_color)
        return Qt.NoBrush

    def make_hl_color(self) -> QColor:
        c = QColor(self.pen_color)
        c.setAlpha(128)
        return c

    def _is_shape_eraser(self):
        return self.eraser and self.current_tool in ("rect", "ellipse")

    # ── 텍스트 ────────────────────────────────
    def _destroy_input(self):
        if self._text_input is not None:
            self._text_input.hide()
            self._text_input.deleteLater()
            self._text_input = None

    def _commit_text(self):
        if self._text_input is None:
            return
        text  = self._text_input.text().strip()
        pos   = self._text_input._pos
        font  = self._text_input._font
        color = self._text_input._color
        self._destroy_input()
        if text:
            self._push_undo()
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.TextAntialiasing)
            p.setFont(font)
            p.setPen(QPen(color))
            p.drawText(pos, text)
            p.end()
            self.update()

    def _open_text_input(self, pos: QPoint):
        self._destroy_input()
        inp = FloatingTextInput(self, pos, self.text_font, self.pen_color)
        inp.editingFinished.connect(self._commit_text)
        self._text_input = inp

    # ── 마우스 ────────────────────────────────
    def mousePressEvent(self, event):
        self.setFocus()  # 클릭시 포커스 재확보
        if event.pos().y() <= TOOLBAR_HEIGHT:
            return
        if self._text_input is not None:
            self._commit_text()
            return
        if event.button() != Qt.LeftButton:
            return

        self.start_point = event.pos()
        self.end_point   = event.pos()

        if self.current_tool == "text" and not self.eraser:
            self._open_text_input(event.pos())
            return

        self._push_undo()
        self.drawing = True
        self.path    = QtGui.QPainterPath()
        self.path.moveTo(event.pos())

        # 형광펜 자유곡선: 임시 레이어 초기화
        if self.highlighter and self.current_tool == "pen" and not self.eraser:
            self._hl_layer = QPixmap(self.canvas.size())
            self._hl_layer.fill(Qt.transparent)

        # 브러시 지우개 첫 점
        if self.eraser and self.current_tool not in ("rect", "ellipse"):
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, 255)))
            p.drawEllipse(event.pos(), self.pen_width // 2, self.pen_width // 2)
            p.end()
            self.update()

    def mouseMoveEvent(self, event):
        self._cursor_pos = event.pos()

        if self.eraser or (self.highlighter and self.current_tool == "pen"):
            self.update()

        if not self.drawing:
            return

        self.end_point = event.pos()

        if self._is_shape_eraser():
            self.update()
            return

        # 브러시 지우개
        if self.eraser and self.current_tool not in ("rect", "ellipse"):
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, 255)))
            p.drawEllipse(event.pos(), self.pen_width // 2, self.pen_width // 2)
            p.end()
            self.update()
            return

        # 형광펜 자유곡선: 임시 레이어에 그림
        if self.highlighter and self.current_tool == "pen":
            if self._hl_layer is not None:
                self._hl_layer.fill(Qt.transparent)
                p = QPainter(self._hl_layer)
                p.setRenderHint(QPainter.Antialiasing)
                hl_c = self.make_hl_color()
                p.setPen(QPen(hl_c, self.pen_width,
                              Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                self.path.lineTo(event.pos())
                p.drawPath(self.path)
                p.end()
            self.update()
            return

        # 일반 펜
        if self.current_tool == "pen":
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(self.make_pen())
            self.path.lineTo(event.pos())
            p.drawPath(self.path)
            p.end()
            self.update()

        if self.current_tool in ("rect", "ellipse", "line"):
            self.update()

    def mouseReleaseEvent(self, event):
        if not self.drawing:
            return
        self.drawing = False

        # 형광 자유곡선 확정: 임시 레이어 → 캔버스 합성
        if self.highlighter and self.current_tool == "pen" and self._hl_layer:
            p = QPainter(self.canvas)
            p.drawPixmap(0, 0, self._hl_layer)
            p.end()
            self._hl_layer = None
            self.update()
            return

        # 도형 범위 지우기
        if self._is_shape_eraser():
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, 255)))
            rect = QRect(self.start_point, self.end_point).normalized()
            if self.current_tool == "rect":
                p.drawRect(rect)
            elif self.current_tool == "ellipse":
                p.drawEllipse(rect)
            p.end()
            self.update()
            return

        if self.eraser or self.current_tool == "pen":
            self.update()
            return

        # 도형 확정
        p = QPainter(self.canvas)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRect(self.start_point, self.end_point).normalized()

        if self.highlighter and self.current_tool in ("rect", "ellipse", "line"):
            hl_c = self.make_hl_color()
            if self.current_tool == "line":
                p.setPen(QPen(hl_c, self.pen_width, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawLine(self.start_point, self.end_point)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(hl_c))
                if self.current_tool == "rect":
                    p.drawRect(rect)
                else:
                    p.drawEllipse(rect)
        else:
            p.setPen(self.make_pen())
            p.setBrush(self.make_brush())
            if self.current_tool == "rect":
                p.drawRect(rect)
            elif self.current_tool == "ellipse":
                p.drawEllipse(rect)
            elif self.current_tool == "line":
                p.drawLine(self.start_point, self.end_point)

        p.end()
        self.update()

    # ── 화면 그리기 ───────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.canvas)

        # 형광 자유곡선 임시 레이어 오버레이
        if self._hl_layer is not None:
            painter.drawPixmap(0, 0, self._hl_layer)

        # 커서 미리보기 원
        if self._cursor_pos.y() > TOOLBAR_HEIGHT:
            if self.eraser:
                r = max(self.pen_width // 2, 2)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(QPen(QColor(200, 200, 200, 180), 1.5, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(self._cursor_pos, r, r)
            elif self.highlighter and self.current_tool == "pen":
                r = max(self.pen_width // 2, 2)
                hl_c = self.make_hl_color()
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(hl_c))
                painter.drawEllipse(self._cursor_pos, r, r)

        if not self.drawing:
            return

        # 도형 지우개 미리보기
        if self._is_shape_eraser():
            pv = QPainter(self)
            pv.setRenderHint(QPainter.Antialiasing)
            pv.setPen(QPen(QColor(255, 80, 80, 200), 1.5, Qt.DashLine))
            pv.setBrush(QBrush(QColor(255, 80, 80, 35)))
            rect = QRect(self.start_point, self.end_point).normalized()
            if self.current_tool == "rect":
                pv.drawRect(rect)
            elif self.current_tool == "ellipse":
                pv.drawEllipse(rect)
            pv.end()
            return

        # 도형 미리보기
        if self.current_tool in ("rect", "ellipse", "line") and not self.eraser:
            pv = QPainter(self)
            pv.setRenderHint(QPainter.Antialiasing)
            rect = QRect(self.start_point, self.end_point).normalized()

            if self.highlighter:
                hl_c = self.make_hl_color()
                if self.current_tool == "line":
                    pv.setPen(QPen(hl_c, self.pen_width, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin))
                    pv.setBrush(Qt.NoBrush)
                    pv.drawLine(self.start_point, self.end_point)
                else:
                    pv.setPen(Qt.NoPen)
                    pv.setBrush(QBrush(hl_c))
                    if self.current_tool == "rect":
                        pv.drawRect(rect)
                    else:
                        pv.drawEllipse(rect)
            else:
                pv.setPen(self.make_pen())
                pv.setBrush(self.make_brush())
                if self.current_tool == "rect":
                    pv.drawRect(rect)
                elif self.current_tool == "ellipse":
                    pv.drawEllipse(rect)
                elif self.current_tool == "line":
                    pv.drawLine(self.start_point, self.end_point)
            pv.end()

    # ── 키보드 ────────────────────────────────
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self._text_input:
                self._destroy_input()
            else:
                self.force_exit()
        elif event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.undo()
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.save_snapshot()
        elif event.key() == Qt.Key_Q and event.modifiers() & Qt.ControlModifier:
            self.force_exit()
        elif event.key() == Qt.Key_C and not self._text_input:
            self.clear_canvas()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ScreenDrawing()
    win.showFullScreen()
    win.raise_()
    win.activateWindow()
    win.setFocus()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
