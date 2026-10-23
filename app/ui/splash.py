"""
ScaleXPro CV-Modifier Splash Screen:
Matches Screen 10 on the design board:
- Rounded branded card
- ScaleXPro Logo
- 'CV Modifier' title
- Tagline: 'Send clean, branded CVs to clients in seconds'
- Smooth animated progress bar
- 'v2.5.0 • Offline Mode' status footer
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPixmap, QPainter, QLinearGradient, QBrush

from app.config import ASSETS_DIR
from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_NAVY,
    COLOR_TEXT_SECONDARY,
    COLOR_BORDER,
)


class ScaleXProSplashScreen(QWidget):
    """Screen 10: Splash Screen with Logo, Title, Tagline, and Progress Bar."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(520, 330)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        # Centered Card Frame
        self.card = QFrame()
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 16px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(self.card)
        c_layout.setContentsMargins(36, 32, 36, 28)
        c_layout.setSpacing(12)
        c_layout.setAlignment(Qt.AlignCenter)

        # 1. ScaleXPro Logo
        logo_path = ASSETS_DIR / "scalexpro_logo.png"
        self.lbl_logo = QLabel()
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        self.lbl_logo.setStyleSheet("background: transparent; border: none;")
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaledToWidth(220, Qt.SmoothTransformation)
            self.lbl_logo.setPixmap(pix)
        else:
            self.lbl_logo.setText("ScaleXPro")
            self.lbl_logo.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {COLOR_PRIMARY};")
        c_layout.addWidget(self.lbl_logo, alignment=Qt.AlignCenter)

        # 2. Title: "CV Modifier"
        self.lbl_title = QLabel("CV Modifier")
        self.lbl_title.setStyleSheet(f"background: transparent; border: none; color: {COLOR_NAVY}; font-size: 22px; font-weight: 800; letter-spacing: -0.3px;")
        c_layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)

        # 3. Tagline
        self.lbl_tagline = QLabel("Send clean, branded CVs to clients in seconds")
        self.lbl_tagline.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_SECONDARY}; font-size: 13px; font-weight: 500;")
        c_layout.addWidget(self.lbl_tagline, alignment=Qt.AlignCenter)

        c_layout.addSpacing(8)

        # 4. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(35)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E2E8F0;
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_PRIMARY};
                border-radius: 3px;
            }}
        """)
        c_layout.addWidget(self.progress_bar)

        # 5. Status message & version
        status_row = QHBoxLayout()
        self.lbl_status = QLabel("Loading offline redaction engine...")
        self.lbl_status.setStyleSheet("background: transparent; border: none; color: #94A3B8; font-size: 11px;")
        status_row.addWidget(self.lbl_status)

        status_row.addStretch()

        self.lbl_ver = QLabel("v2.5.0 • Offline Mode")
        self.lbl_ver.setStyleSheet("background: transparent; border: none; color: #94A3B8; font-size: 11px; font-weight: 600;")
        status_row.addWidget(self.lbl_ver)

        c_layout.addLayout(status_row)
        root_layout.addWidget(self.card)

        # Center on primary screen
        self._center()

        self._val = 35
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._pulse)
        self.timer.start(40)

    def _center(self):
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def _pulse(self):
        self._val = min(100, self._val + 4)
        self.progress_bar.setValue(self._val)
        if self._val > 70:
            self.lbl_status.setText("Initializing interface & local database...")
        if self._val >= 100:
            self.timer.stop()

    def finish(self, window):
        self.timer.stop()
        self.close()
