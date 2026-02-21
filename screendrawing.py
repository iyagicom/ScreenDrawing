#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScreenDrawing
Version: 1.2.0
Author: Jeong SeongYong
Email: iyagicom@gmail.com
Description: Lightweight Wayland screen drawing tool
             (pen, shapes, text, highlight, eraser, undo, screenshot)
License: GPL-2.0 or later
"""

import sys
import os
import locale
import math
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, QPointF
from PyQt5.QtGui import (QPainter, QPen, QColor, QPixmap, QBrush, QFont, QPolygonF)

# ── 설정 상수 ──────────────────────────────────
TOOLBAR_HEIGHT = 56
MAX_UNDO_STEPS = 50

# ── 아이콘 정보 (이모지, 강조 색상) ───────────────
ICONS = {
    "pen":       ("✏",  "#4FC3F7"),
    "rect":      ("▭",  "#81C784"),
    "ellipse":   ("◯",  "#CE93D8"),
    "line":      ("/",  "#FFB74D"),
    "arrow":     ("➔",  "#FF8A65"),
    "text":      ("T",  "#F48FB1"),
    "eraser":    ("□",  "#90A4AE"),
    "fill":      ("■",  "#78909C"),
    "highlight": ("▌",  "#FFD600"),
    "clear":     ("✕",  "#EF9A9A"),
    "exit":      ("✕",  "#EF5350"),
}

# ── 유틸리티 함수 ───────────────────────────────
def detect_language() -> str:
    """시스템 언어를 감지하여 한국어(ko) 또는 영어(en) 반환"""
    for env in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(env, "")
        if val.lower().startswith("ko"): return "ko"
    try:
        code, _ = locale.getdefaultlocale()
        if code and code.lower().startswith("ko"): return "ko"
    except: pass
    return "en"

LANG = detect_language()

def tr(ko: str, en: str) -> str:
    """언어 설정에 따라 텍스트 선택"""
    return ko if LANG == "ko" else en

# ── 텍스트 입력 위젯 ─────────────────────────────
class FloatingTextInput(QtWidgets.QTextEdit):
    """화면 위에서 직접 글씨를 입력받는 플로팅 입력창 (엔터로 줄바꿈, Ctrl+Enter로 확정)"""
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, parent, pos, font, color):
        super().__init__(parent)
        self._pos, self._font, self._color = pos, font, color
        self.setFont(font)
        self.setStyleSheet(
            f"QTextEdit {{ background: transparent; border: none; "
            f"border-bottom: 2px solid {color.name()}; color: {color.name()}; padding: 0px; }}"
        )
        self.move(pos.x(), pos.y() - self.fontMetrics().height())
        self.setFixedSize(200, self.fontMetrics().height() + 10)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setFocus()
        self.textChanged.connect(self._adjust_size)
        self.show()

    def _adjust_size(self):
        """내용에 따라 입력창 크기 자동 조절"""
        doc = self.document()
        doc.setTextWidth(max(self.width(), 200))
        h = int(doc.size().height()) + 10
        # 너비: 가장 긴 줄 기준
        lines = self.toPlainText().split('\n')
        max_w = max((self.fontMetrics().width(l) for l in lines), default=0) + 20
        self.setFixedSize(max(max_w, 200), max(h, self.fontMetrics().height() + 10))

    def text(self):
        """QLineEdit 호환용 text() 메서드"""
        return self.toPlainText()

    def keyPressEvent(self, event):
        # Ctrl+Enter 또는 Ctrl+Return → 확정
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() & Qt.ControlModifier:
            self.editingFinished.emit()
        # Escape → 취소
        elif event.key() == Qt.Key_Escape:
            self.setPlainText("")
            self.editingFinished.emit()
        # 일반 Enter → 줄바꿈
        else:
            super().keyPressEvent(event)

# ── 툴바 컴포넌트 ───────────────────────────────
class ToolBar(QtWidgets.QWidget):
    """상단 도구 모음 클래스"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_HEIGHT)
        self.init_ui()

    def init_ui(self):
        # 전체 툴바 스타일 설정
        self.setStyleSheet("""
            QWidget { background-color: #1A1D26; color: #E0E0E0; font-size: 13px; }
            QLabel { background: transparent; color: #707080; font-size: 12px; }
            QSpinBox { background-color: #2E3243; border: 1px solid #3E4460; border-radius: 6px; color: #E0E0E0; padding: 2px 4px; font-size: 13px; }
            QSpinBox::up-button, QSpinBox::down-button { width: 16px; }
        """)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(5)

        # 1. 도구 버튼 생성 (펜, 사각형, 원, 직선, 화살표, 글씨)
        self.btns = {}
        tool_list = [
            ("pen", "펜", "Pen"), ("rect", "사각형", "Rect"), ("ellipse", "원", "Ellipse"),
            ("line", "직선", "Line"), ("arrow", "화살표", "Arrow"), ("text", "글씨", "Text")
        ]
        for key, ko, en in tool_list:
            emoji, _ = ICONS[key]
            btn = QtWidgets.QPushButton(f"{emoji}  {tr(ko, en)}")
            btn.setFixedHeight(38)
            btn.setProperty("tool_key", key)
            layout.addWidget(btn)
            self.btns[key] = btn

        layout.addWidget(self.create_separator())

        # 2. 색상 및 두께 설정
        self.color_preview = QtWidgets.QPushButton(tr("● 색상", "● Color"))
        self.color_preview.setFixedHeight(38)
        layout.addWidget(self.color_preview)

        self.width_label = QtWidgets.QLabel(tr("두께", "Width"))
        self.width_label.setStyleSheet("background-color: #3E4460; color: #FFFFFF; border-radius: 4px; padding: 2px 6px;")
        layout.addWidget(self.width_label)

        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(1, 120); self.width_spin.setValue(4); self.width_spin.setFixedWidth(64)
        layout.addWidget(self.width_spin)

        layout.addWidget(self.create_separator())

        # 3. 폰트 설정 및 퀵 사이즈 버튼
        self.font_btn = QtWidgets.QPushButton(tr("A 폰트", "A Font"))
        self.font_btn.setFixedHeight(38)
        layout.addWidget(self.font_btn)

        for sz in ["10", "16", "24", "36"]:
            btn = QtWidgets.QPushButton(sz)
            btn.setFixedWidth(38); btn.setFixedHeight(38)
            btn.setProperty("size_val", int(sz))
            layout.addWidget(btn)
            self.btns[f"fs{sz}"] = btn

        layout.addWidget(self.create_separator())

        # 4. 기능 버튼 (채우기, 형광, 지우개, 실행취소, 저장, 전체지우기)
        self.fill_btn = self.create_func_btn("fill", "채우기", "Fill")
        self.hl_btn = QtWidgets.QPushButton(tr("▌ 형광", "▌ Highlight"))
        self.hl_btn.setFixedHeight(38)
        self.eraser_btn = self.create_func_btn("eraser", "지우개", "Eraser")
        
        layout.addWidget(self.fill_btn)
        layout.addWidget(self.create_separator())
        layout.addWidget(self.hl_btn)
        layout.addWidget(self.create_separator())
        layout.addWidget(self.eraser_btn)
        layout.addWidget(self.create_separator())

        self.undo_btn = QtWidgets.QPushButton(tr("← 실행취소", "← Undo"))
        self.snapshot_btn = QtWidgets.QPushButton(tr("[ ] 저장", "[ ] Save"))
        self.clear_btn = self.create_func_btn("clear", "전체지우기", "Clear All")
        
        for b in [self.undo_btn, self.snapshot_btn, self.clear_btn]:
            b.setFixedHeight(38); layout.addWidget(b)

        layout.addStretch()

        # 5. 종료 버튼
        self.exit_btn = QtWidgets.QPushButton(tr("✕ 종료", "✕ Exit"))
        self.exit_btn.setFixedHeight(38)
        self.exit_btn.setStyleSheet("""
            QPushButton { background-color: #4A1E1E; border: 1px solid #7A3030; border-radius: 8px; color: #FF6B6B; padding: 5px 12px; }
            QPushButton:hover { background-color: #6A2525; border-color: #EF5350; color: #FF9090; }
        """)
        layout.addWidget(self.exit_btn)
        self.setLayout(layout)

    def create_func_btn(self, key, ko, en):
        emoji, _ = ICONS[key]
        btn = QtWidgets.QPushButton(f"{emoji}  {tr(ko, en)}")
        btn.setFixedHeight(38)
        return btn

    def create_separator(self):
        f = QtWidgets.QFrame()
        f.setFrameShape(QtWidgets.QFrame.VLine)
        f.setStyleSheet("QFrame { color: #3E4460; min-width:1px; max-width:1px; margin: 6px 2px; }")
        return f

    def update_button_styles(self, current_tool, fill, hl, eraser):
        """도구 활성화 상태에 따른 버튼 스타일 업데이트 (외곽선 강조)"""
        for key in ["pen", "rect", "ellipse", "line", "arrow", "text"]:
            _, accent = ICONS[key]
            is_active = (key == current_tool)
            # 활성화 시에만 해당 도구의 색상으로 외곽선 강조
            border = f"1.5px solid {accent}" if is_active else "1px solid #3E4460"
            self.btns[key].setStyleSheet(f"QPushButton {{ background-color: #2E3243; border: {border}; border-radius: 8px; color: #E0E0E0; padding: 5px 11px; }} QPushButton:hover {{ background-color: #3A4060; }}")

        # 기능 버튼 스타일 업데이트
        self.fill_btn.setStyleSheet(self.get_toggle_style("fill", fill))
        self.hl_btn.setStyleSheet(self.get_toggle_style("highlight", hl))
        self.eraser_btn.setStyleSheet(self.get_toggle_style("eraser", eraser))

    def get_toggle_style(self, key, is_on):
        _, accent = ICONS[key]
        border = f"1.5px solid {accent}" if is_on else "1px solid #3E4460"
        return f"QPushButton {{ background-color: #2E3243; border: {border}; border-radius: 8px; color: #E0E0E0; padding: 5px 11px; }} QPushButton:hover {{ background-color: #3A4060; }}"

    def update_color_preview(self, color: QColor):
        """[요청사항] 색상 버튼은 외곽선 강조 없이 아이콘과 글자만 현재 색상 반영"""
        c_hex = color.name()
        self.color_preview.setStyleSheet(f"""
            QPushButton {{ background-color: #2E3243; border: 1px solid #3E4460; border-radius: 8px; color: {c_hex}; font-weight: bold; padding: 5px 11px; }}
            QPushButton:hover {{ background-color: #3A4060; }}
        """)

# ───────────────────────────────────────────────
#  메인 그리기 클래스
# ───────────────────────────────────────────────
class ScreenDrawing(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_window()
        self.init_variables()
        self.init_ui()

    def init_window(self):
        """윈도우 설정: 투명, 전체화면, 항상 위"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        geo = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(geo)
        # 그림 저장용 Pixmap
        self.canvas = QPixmap(geo.size())
        self.canvas.fill(Qt.transparent)

    def init_variables(self):
        """내부 상태 변수 초기화"""
        self.current_tool = "pen"
        self.pen_color = QColor(255, 50, 50)
        self.pen_width = 4
        self.fill_enabled = False
        self.highlighter = False
        self.eraser = False
        
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.path = QtGui.QPainterPath()
        self._cursor_pos = QPoint(-100, -100)
        self._hl_layer = None
        self._text_input = None
        self.text_font = QFont("Sans", 24)
        
        self.undo_stack = []
        self._temp_eraser = False
        self._temp_line = False
        self._saved_tool = "pen"

    def init_ui(self):
        """UI 구성 및 이벤트 연결"""
        self.toolbar = ToolBar(self)
        self.toolbar.setGeometry(0, 0, self.width(), TOOLBAR_HEIGHT)
        
        # 버튼 이벤트 연결
        for key, btn in self.toolbar.btns.items():
            if key.startswith("fs"):
                btn.clicked.connect(lambda checked, b=btn: self.quick_size(b.property("size_val")))
            else:
                btn.clicked.connect(lambda checked, k=key: self.set_tool(k))

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

        self.update_ui_styles()

    # ── 도구 및 상태 관리 ───────────────────────────
    def set_tool(self, tool):
        self.current_tool = tool
        if self.eraser and not self._temp_eraser: self.eraser = False
        self.update_ui_styles()

    def set_width(self, val): self.pen_width = val
    def toggle_fill(self): self.fill_enabled = not self.fill_enabled; self.update_ui_styles()
    def toggle_highlighter(self): self.highlighter = not self.highlighter; self.update_ui_styles()
    def toggle_eraser(self): self.eraser = not self.eraser; self.update_ui_styles()
    
    def update_ui_styles(self):
        self.toolbar.update_button_styles(self.current_tool, self.fill_enabled, self.highlighter, self.eraser)
        self.toolbar.update_color_preview(self.pen_color)

    def quick_size(self, size):
        self.pen_width = size
        self.toolbar.width_spin.setValue(size)
        self.text_font.setPointSize(size)
        self.update()

    def select_color(self):
        color = QtWidgets.QColorDialog.getColor(self.pen_color, self, tr("색상 선택", "Select Color"))
        if color.isValid():
            self.pen_color = color
            self.update_ui_styles()

    def select_font(self):
        font, ok = QtWidgets.QFontDialog.getFont(self.text_font, self, tr("폰트 선택", "Select Font"))
        if ok: self.text_font = font

    # ── 핵심 그리기 로직 (버그 수정 포인트) ──────────────
    def get_pen(self, for_line=False):
        """
        [버그수정] 직선(line)이나 화살표(arrow)를 그릴 때는 FlatCap을 강제하여 라운딩(원형 잔상) 제거.
        """
        color = QColor(self.pen_color)
        if self.highlighter: color.setAlpha(128)

        # 직선이나 화살표 도구일 때는 FlatCap을 사용하여 끝부분 라운딩을 금지함
        cap = Qt.FlatCap if for_line else Qt.RoundCap
        return QPen(color, self.pen_width, Qt.SolidLine, cap, Qt.RoundJoin)

    def get_brush(self):
        if self.fill_enabled and self.current_tool in ("rect", "ellipse", "arrow") and not self.eraser:
            color = QColor(self.pen_color)
            if self.highlighter: color.setAlpha(128)
            return QBrush(color)
        return Qt.NoBrush

    def draw_arrow(self, painter, start, end):
        """사다리꼴 몸통과 화살촉을 가진 화살표 그리기"""
        if start == end: return
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1: return
        
        angle = math.atan2(dy, dx)
        head_len = max(self.pen_width * 3, 15)
        head_width = max(self.pen_width * 2.5, 12)
        body_end_len = max(0, length - head_len)
        body_end = QPointF(start.x() + math.cos(angle) * body_end_len, start.y() + math.sin(angle) * body_end_len)
        
        # 사다리꼴 몸통 (시작은 얇고 끝으로 갈수록 두꺼워짐)
        w_start, w_end = self.pen_width / 2.0, self.pen_width
        p1 = QPointF(start.x() + w_start * math.cos(angle + math.pi/2), start.y() + w_start * math.sin(angle + math.pi/2))
        p2 = QPointF(start.x() + w_start * math.cos(angle - math.pi/2), start.y() + w_start * math.sin(angle - math.pi/2))
        p3 = QPointF(body_end.x() + w_end * math.cos(angle - math.pi/2), body_end.y() + w_end * math.sin(angle - math.pi/2))
        p4 = QPointF(body_end.x() + w_end * math.cos(angle + math.pi/2), body_end.y() + w_end * math.sin(angle + math.pi/2))
        
        h1 = QPointF(end.x(), end.y())
        h2 = QPointF(body_end.x() + head_width * math.cos(angle + math.pi/2), body_end.y() + head_width * math.sin(angle + math.pi/2))
        h3 = QPointF(body_end.x() + head_width * math.cos(angle - math.pi/2), body_end.y() + head_width * math.sin(angle - math.pi/2))
        
        painter.setPen(Qt.NoPen)
        color = QColor(self.pen_color)
        if self.highlighter: color.setAlpha(128)
        painter.setBrush(QBrush(color))
        
        painter.drawPolygon(QPolygonF([p1, p2, p3, p4]))
        painter.drawPolygon(QPolygonF([h1, h2, h3]))

    # ── 텍스트 입력 처리 ────────────────────────────
    def _destroy_input(self):
        if self._text_input:
            self._text_input.hide()
            self._text_input.deleteLater()
            self._text_input = None

    def _commit_text(self):
        """입력된 텍스트를 캔버스에 그리기"""
        if not self._text_input: return
        text = self._text_input.text().strip('\n').rstrip()
        pos, font, color = self._text_input._pos, self._text_input._font, self._text_input._color
        self._destroy_input()
        
        if text:
            self._push_undo()
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            p.setFont(font)
            p.setPen(QPen(color))
            line_height = QtGui.QFontMetrics(font).height()
            for i, line in enumerate(text.split('\n')):
                p.drawText(pos.x(), pos.y() + i * line_height, line)
            p.end()
            self.update()

    def _open_text_input(self, pos: QPoint):
        self._destroy_input()
        self._text_input = FloatingTextInput(self, pos, self.text_font, self.pen_color)
        self._text_input.editingFinished.connect(self._commit_text)

    # ── 마우스 이벤트 ──────────────────────────────
    def mousePressEvent(self, event):
        if event.pos().y() <= TOOLBAR_HEIGHT: return
        if self._text_input: self._commit_text(); return
        if event.button() != Qt.LeftButton: return
        
        self.setFocus()
        self.start_point = event.pos()
        self.end_point = event.pos()
        
        # 글씨 입력 도구인 경우
        if self.current_tool == "text" and not self.eraser:
            self._open_text_input(event.pos())
            return
            
        self.drawing = True
        self._push_undo()
        self.path = QtGui.QPainterPath()
        self.path.moveTo(event.pos())

        if self.highlighter and self.current_tool == "pen" and not self.eraser:
            self._hl_layer = QPixmap(self.canvas.size())
            self._hl_layer.fill(Qt.transparent)

    def mouseMoveEvent(self, event):
        self._cursor_pos = event.pos()
        if self.eraser or (self.highlighter and self.current_tool == "pen"): self.update()
            
        if not self.drawing: return
        self.end_point = event.pos()

        # 지우개
        if self.eraser and self.current_tool not in ("rect", "ellipse"):
            p = QPainter(self.canvas)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.setBrush(QBrush(Qt.black))
            p.setPen(Qt.NoPen)
            p.drawEllipse(event.pos(), self.pen_width//2, self.pen_width//2)
            p.end()
            self.update()
            return

        # 형광펜 자유곡선
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

        # 일반 펜
        if self.current_tool == "pen":
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(self.get_pen(for_line=False))
            self.path.lineTo(event.pos())
            p.drawPath(self.path)
            p.end()
            self.update()
            return

        if self.current_tool in ("rect", "ellipse", "line", "arrow"): self.update()

    def mouseReleaseEvent(self, event):
        if not self.drawing: return
        self.drawing = False
        self.end_point = event.pos()

        if self.highlighter and self.current_tool == "pen" and self._hl_layer:
            p = QPainter(self.canvas); p.drawPixmap(0, 0, self._hl_layer); p.end()
            self._hl_layer = None; self.update(); return

        if not self.eraser or self.current_tool in ("rect", "ellipse"):
            p = QPainter(self.canvas); p.setRenderHint(QPainter.Antialiasing)
            if self.eraser:
                p.setCompositionMode(QPainter.CompositionMode_Clear)
                p.setBrush(QBrush(Qt.black)); p.setPen(Qt.NoPen)
            else:
                # [버그수정] 직선/화살표 확정 시 FlatCap 적용하여 라운딩 제거
                is_line_tool = (self.current_tool in ("line", "arrow"))
                p.setPen(self.get_pen(for_line=is_line_tool))
                p.setBrush(self.get_brush())

            rect = QRect(self.start_point, self.end_point).normalized()
            if self.current_tool == "rect": p.drawRect(rect)
            elif self.current_tool == "ellipse": p.drawEllipse(rect)
            elif self.current_tool == "line": p.drawLine(self.start_point, self.end_point)
            elif self.current_tool == "arrow": self.draw_arrow(p, self.start_point, self.end_point)
            p.end()
        self.update()

    # ── 화면 출력 ──────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.canvas)
        if self._hl_layer: painter.drawPixmap(0, 0, self._hl_layer)

        # 커서 미리보기 (펜 도구가 아닐 때는 형광펜 원이 나타나지 않음)
        if self._cursor_pos.y() > TOOLBAR_HEIGHT:
            if self.eraser:
                r = max(self.pen_width // 2, 2)
                painter.setPen(QPen(QColor(200, 200, 200, 180), 1, Qt.DashLine))
                painter.drawEllipse(self._cursor_pos, r, r)
            elif self.highlighter and self.current_tool == "pen":
                r = max(self.pen_width // 2, 2)
                painter.setPen(Qt.NoPen)
                c = QColor(self.pen_color); c.setAlpha(100)
                painter.setBrush(QBrush(c))
                painter.drawEllipse(self._cursor_pos, r, r)

        # 도형 미리보기
        if self.drawing and self.current_tool in ("rect", "ellipse", "line", "arrow"):
            pv = QPainter(self); pv.setRenderHint(QPainter.Antialiasing)
            if self.eraser:
                pv.setPen(QPen(QColor(255, 80, 80, 200), 1.5, Qt.DashLine))
                pv.setBrush(QBrush(QColor(255, 80, 80, 40)))
            else:
                # [버그수정] 미리보기에서도 직선/화살표는 FlatCap 적용
                is_line_tool = (self.current_tool in ("line", "arrow"))
                pv.setPen(self.get_pen(for_line=is_line_tool))
                pv.setBrush(self.get_brush())

            rect = QRect(self.start_point, self.end_point).normalized()
            if self.current_tool == "rect": pv.drawRect(rect)
            elif self.current_tool == "ellipse": pv.drawEllipse(rect)
            elif self.current_tool == "line": pv.drawLine(self.start_point, self.end_point)
            elif self.current_tool == "arrow": self.draw_arrow(pv, self.start_point, self.end_point)

    # ── 유틸리티 기능 ──────────────────────────────
    def _push_undo(self):
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > MAX_UNDO_STEPS: self.undo_stack.pop(0)

    def undo(self):
        if self.undo_stack: self.canvas = self.undo_stack.pop(); self.update()

    def clear_canvas(self):
        self._push_undo(); self.canvas.fill(Qt.transparent); self.update()

    def save_snapshot(self):
        home = os.path.expanduser("~")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(home, f"drawing_{ts}.png")
        self.canvas.save(path, "PNG")
        msg = QtWidgets.QLabel(tr(f"저장됨: {path}", f"Saved: {path}"), self)
        msg.setStyleSheet("background-color: #1A2540; color: #81C784; padding: 8px; border-radius: 5px;")
        msg.adjustSize(); msg.move((self.width()-msg.width())//2, TOOLBAR_HEIGHT + 10)
        msg.show(); QTimer.singleShot(2000, msg.deleteLater)

    def force_exit(self): QtWidgets.QApplication.quit()

    # ── 키보드 단축키 ──────────────────────────────
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Control and not self.drawing:
            self._temp_eraser = True; self._saved_tool = self.current_tool
            self.eraser = True; self.update_ui_styles()
        elif key == Qt.Key_Shift and not self.drawing:
            self._temp_line = True; self._saved_tool = self.current_tool
            self.current_tool = "line"; self.update_ui_styles()
        elif key == Qt.Key_Escape: (self._text_input and self._destroy_input()) or self.force_exit()
        elif key == Qt.Key_Z and event.modifiers() & Qt.ControlModifier: self.undo()
        elif key == Qt.Key_S and event.modifiers() & Qt.ControlModifier: self.save_snapshot()
        elif key == Qt.Key_C and not self._text_input: self.clear_canvas()

    def keyReleaseEvent(self, event):
        key = event.key()
        if key == Qt.Key_Control and self._temp_eraser:
            self._temp_eraser = False; self.eraser = False
            self.current_tool = self._saved_tool; self.update_ui_styles()
        elif key == Qt.Key_Shift and self._temp_line:
            self._temp_line = False; self.current_tool = self._saved_tool
            self.update_ui_styles()

# ── 실행 ──────────────────────────────────────
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ScreenDrawing()
    window.showFullScreen()
    sys.exit(app.exec_())
