"""
First-Run Guided Tour for ScaleXPro CV-Modifier:
Provides friendly, interactive coach-mark popups highlighting:
1. Drop a CV to automatically redact personal details
2. Review the before/after results and adaptively brand
3. Send verified CVs directly to clients
"""

from typing import Optional, List, Tuple
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QPolygon

from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_CTA,
    COLOR_CTA_HOVER,
    COLOR_NAVY,
    COLOR_TEXT_SECONDARY,
    COLOR_LAVENDER_LIGHT,
)


class GuidedTourDialog(QFrame):
    """Floating coach-mark callout with helpful plain-English guidance."""
    tour_finished = Signal()
    step_changed = Signal(int)

    STEPS = [
        (
            "Welcome to ScaleXPro CV-Modifier!",
            "Effortlessly redact personal contact details (emails, phone numbers, addresses, links) and brand CVs for client submission — 100% offline.",
            "Start Tour",
        ),
        (
            "Step 1: Upload or Drop Your CV",
            "Simply drag and drop any candidate resume (PDF or DOCX) into the upload card, or click 'Process a CV' to select files in bulk.",
            "Next: Review & Clean",
        ),
        (
            "Step 2: Interactive Review & Edit Mode",
            "Compare original vs. cleaned versions side-by-side. Use the 'Edit CV' tool to adjust text, reposition the logo, or blank out sections.",
            "Next: Send to Client",
        ),
        (
            "Step 3: Direct Client Dispatch",
            "Choose a client recipient, select an email template, and send the verified CV with an automated audit trail.",
            "Got it! Let's Go",
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = 0
        self.setFixedWidth(380)
        self.setMinimumHeight(220)
        self.hide()
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1.5px solid #6C5CB8;
                border-radius: 18px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(107, 95, 181, 40))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Header with step pill & close
        top_row = QHBoxLayout()
        self.lbl_step_chip = QLabel("Step 1 of 4")
        self.lbl_step_chip.setStyleSheet("""
            background-color: #DDD6F7;
            color: #3B2D7C;
            font-size: 11px;
            font-weight: 700;
            border-radius: 10px;
            padding: 3px 9px;
            border: none;
        """)
        top_row.addWidget(self.lbl_step_chip)
        top_row.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("background: transparent; border: none; color: #9CA3AF; font-size: 13px; font-weight: 700;")
        btn_close.clicked.connect(self._on_skip)
        top_row.addWidget(btn_close)
        layout.addLayout(top_row)

        # Title
        self.lbl_title = QLabel("")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700; border: none;")
        layout.addWidget(self.lbl_title)

        # Body
        self.lbl_body = QLabel("")
        self.lbl_body.setWordWrap(True)
        self.lbl_body.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px; line-height: 1.45; border: none;")
        layout.addWidget(self.lbl_body)

        layout.addSpacing(6)

        # Button row
        btn_row = QHBoxLayout()
        self.btn_skip = QPushButton("Skip tour")
        self.btn_skip.setCursor(Qt.PointingHandCursor)
        self.btn_skip.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        self.btn_skip.clicked.connect(self._on_skip)
        btn_row.addWidget(self.btn_skip)

        btn_row.addStretch()

        self.btn_next = QPushButton("Next")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CTA_HOVER};
            }}
        """)
        self.btn_next.clicked.connect(self._on_next)
        btn_row.addWidget(self.btn_next)
        layout.addLayout(btn_row)

        self._render_step()

    def _render_step(self):
        title, body, btn_text = self.STEPS[self.current_step]
        self.lbl_step_chip.setText(f"Step {self.current_step + 1} of {len(self.STEPS)}")
        self.lbl_title.setText(title)
        self.lbl_body.setText(body)
        self.btn_next.setText(btn_text)
        self.btn_skip.setVisible(self.current_step < len(self.STEPS) - 1)

    def _on_next(self):
        if self.current_step < len(self.STEPS) - 1:
            self.current_step += 1
            self._render_step()
            self.step_changed.emit(self.current_step)
        else:
            self.hide()
            self.tour_finished.emit()

    def _on_skip(self):
        self.hide()
        self.tour_finished.emit()

    def show_tour(self, center_on_widget: Optional[QWidget] = None):
        self.current_step = 0
        self._render_step()
        self.adjustSize()
        if center_on_widget:
            w = center_on_widget.width()
            h = center_on_widget.height()
            self.move((w - self.width()) // 2, (h - self.height()) // 2)
        self.raise_()
        self.show()
