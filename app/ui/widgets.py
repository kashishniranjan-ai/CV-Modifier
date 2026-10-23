"""
Custom reusable UI components for ScaleXPro Lavender/Purple Desktop:
- CardWidget: Clean white card with 20px radius, soft purple shadow (rgba(107, 95, 181, 0.08)), and optional hover elevation
- PastelIconCircle: 40x40 pastel circular icon container (Lavender, Pink, Blue, Mint)
- DonutGaugeWidget: QPainter-based circular gauge with smooth track and animated sweep
- MultiSegmentDonutWidget: Category breakdown donut chart
- StatCardWidget: Metric card with pastel icon circle, animated count-up numbers, and trend chip
- UploadDropCard: Dashed drag-and-drop zone with pulse effect and orange CTA button
- ToastNotification: Soft white notification toast with slide-in animation
"""

import os
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QRectF, Signal, QTimer, QPoint
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QFont,
    QPalette,
    QDragEnterEvent,
    QDropEvent,
)
import qtawesome as qta

from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_TINT,
    COLOR_PURPLE_DARK,
    COLOR_PURPLE_DEEP,
    COLOR_LAVENDER,
    COLOR_LAVENDER_LIGHT,
    COLOR_CTA,
    COLOR_CTA_HOVER,
    COLOR_SUCCESS,
    COLOR_SUCCESS_TINT,
    COLOR_DANGER,
    COLOR_DANGER_TINT,
    COLOR_IN_PROGRESS,
    COLOR_IN_PROGRESS_TINT,
    COLOR_NAVY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    PASTEL_LAVENDER,
    PASTEL_LAVENDER_ICON,
    PASTEL_PINK,
    PASTEL_PINK_ICON,
    PASTEL_BLUE,
    PASTEL_BLUE_ICON,
    PASTEL_MINT,
    PASTEL_MINT_ICON,
)
from app.ui.animations import animate_number, is_animations_enabled


class CardWidget(QFrame):
    """
    Clean pure white card frame with 20px radius, very soft purple-tinted drop shadow,
    and smooth 2px hover elevation.
    """
    def __init__(self, parent=None, radius: int = 20, enable_shadow: bool = True, enable_hover_lift: bool = True):
        super().__init__(parent)
        self.radius = radius
        self.enable_hover_lift = enable_hover_lift
        self.setObjectName("SaaSCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        card_pal = self.palette()
        card_pal.setColor(QPalette.Window, QColor("#FFFFFF"))
        card_pal.setColor(QPalette.Base, QColor("#FFFFFF"))
        card_pal.setColor(QPalette.Button, QColor("#FFFFFF"))
        self.setPalette(card_pal)

        self.setStyleSheet(f"""
            QFrame#SaaSCard {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: {radius}px;
            }}
        """)
        self._shadow: Optional[QGraphicsDropShadowEffect] = None
        if enable_shadow:
            self._shadow = QGraphicsDropShadowEffect(self)
            self._shadow.setBlurRadius(22)
            self._shadow.setXOffset(0)
            self._shadow.setYOffset(4)
            self._shadow.setColor(QColor(107, 95, 181, 18))  # rgba(107, 95, 181, 0.07)
            self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event):
        if self.enable_hover_lift and is_animations_enabled() and self._shadow:
            self._shadow.setBlurRadius(28)
            self._shadow.setYOffset(6)
            self._shadow.setColor(QColor(107, 95, 181, 28))
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.enable_hover_lift and is_animations_enabled() and self._shadow:
            self._shadow.setBlurRadius(22)
            self._shadow.setYOffset(4)
            self._shadow.setColor(QColor(107, 95, 181, 18))
        super().leaveEvent(event)


class PastelIconCircle(QFrame):
    """Circular pastel icon badge (40x40) from reference: lavender, pink, blue, mint."""
    def __init__(self, icon_name: str, circle_type: str = "lavender", size: int = 40, icon_size: int = 18, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

        type_map = {
            "lavender": (PASTEL_LAVENDER, PASTEL_LAVENDER_ICON),
            "pink": (PASTEL_PINK, PASTEL_PINK_ICON),
            "blue": (PASTEL_BLUE, PASTEL_BLUE_ICON),
            "mint": (PASTEL_MINT, PASTEL_MINT_ICON),
        }
        bg_col, icon_col = type_map.get(circle_type, type_map["lavender"])

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border-radius: {size // 2}px;
                border: none;
            }}
        """)
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setPixmap(qta.icon(icon_name, color=icon_col).pixmap(icon_size, icon_size))
        l.addWidget(icon_lbl)


class DonutGaugeWidget(QWidget):
    """
    Circular percentage gauge drawn with QPainter:
    - Smooth anti-aliasing
    - Soft lavender background track (#ECEEF8)
    - Solid or gradient arc (#3DBE7A green for safety, #6C5CB8 purple, or #F28A1E orange)
    - Value text in center in deep navy (#1E1B4B)
    """
    def __init__(
        self,
        value: float = 100.0,
        max_value: float = 100.0,
        size: int = 100,
        thickness: int = 10,
        arc_color: str = "#3DBE7A",
        track_color: str = "#ECEEF8",
        center_text: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._value = value
        self._max_value = max_value
        self._thickness = thickness
        self._arc_color = QColor(arc_color)
        self._track_color = QColor(track_color)
        self._center_text = center_text
        self.setFixedSize(size, size)

    def set_value(self, val: float, text: Optional[str] = None):
        self._value = max(0.0, min(self._max_value, val))
        if text is not None:
            self._center_text = text
        self.update()

    def set_arc_color(self, color_hex: str):
        self._arc_color = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        margin = self._thickness / 2.0 + 2.0
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        # 1. Background Track
        track_pen = QPen(self._track_color, self._thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # 2. Active Progress Arc
        if self._max_value > 0 and self._value > 0:
            progress_ratio = self._value / self._max_value
            span_angle = int(-progress_ratio * 360.0 * 16)
            arc_pen = QPen(self._arc_color, self._thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            # Start at 90 degrees (12 o'clock)
            painter.drawArc(rect, 90 * 16, span_angle)

        # 3. Center Text
        display_str = self._center_text if self._center_text is not None else f"{int(self._value)}%"
        painter.setPen(QColor(COLOR_NAVY))
        font = QFont("Inter", 13, QFont.Bold)
        font.setStyleHint(QFont.SansSerif)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, display_str)


class MultiSegmentDonutWidget(QWidget):
    """
    Multi-segment circular donut chart for category breakdowns (e.g. What was removed):
    - Smooth anti-aliased arcs for each category
    - Proportional spans
    - Center text and subtitle
    """
    def __init__(
        self,
        segments: Optional[list] = None,
        size: int = 110,
        thickness: int = 12,
        center_text: str = "100%",
        center_subtitle: str = "Clean",
        parent=None,
    ):
        super().__init__(parent)
        self.segments = segments or [
            {"label": "Emails", "value": 40, "color": "#F28A1E"},
            {"label": "Phones", "value": 30, "color": "#3DBE7A"},
            {"label": "Links", "value": 20, "color": "#3B82F6"},
            {"label": "Addresses", "value": 10, "color": "#8B5CF6"},
        ]
        self._thickness = thickness
        self._center_text = center_text
        self._center_subtitle = center_subtitle
        self.setFixedSize(size, size)

    def set_data(self, segments: list, center_text: str = "100%", center_subtitle: str = "Clean"):
        self.segments = segments
        self._center_text = center_text
        self._center_subtitle = center_subtitle
        self.update()

    def set_value(self, val: float, text: Optional[str] = None):
        self._center_text = text or f"{int(val)}%"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        margin = self._thickness / 2.0 + 2.0
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        total = sum(s.get("value", 0) for s in self.segments)
        if total <= 0:
            pen = QPen(QColor("#ECEEF8"), self._thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, 0, 360 * 16)
        else:
            start_angle = 90 * 16
            for seg in self.segments:
                val = seg.get("value", 0)
                if val <= 0:
                    continue
                ratio = val / total
                span_angle = int(-ratio * 360.0 * 16)
                pen = QPen(QColor(seg.get("color", "#6C5CB8")), self._thickness, Qt.SolidLine, Qt.FlatCap)
                painter.setPen(pen)
                painter.drawArc(rect, start_angle, span_angle)
                start_angle += span_angle

        # Draw Center Text
        painter.setPen(QColor(COLOR_TEXT_SECONDARY))
        f_sub = QFont("Inter", 9, QFont.Normal)
        painter.setFont(f_sub)
        painter.drawText(QRectF(0, side * 0.28, side, side * 0.22), Qt.AlignCenter, self._center_subtitle)

        painter.setPen(QColor(COLOR_NAVY))
        f_main = QFont("Inter", 14, QFont.Bold)
        painter.setFont(f_main)
        painter.drawText(QRectF(0, side * 0.48, side, side * 0.28), Qt.AlignCenter, self._center_text)


class StatCardWidget(CardWidget):
    """
    Modern metric card matching the reference:
    - Pastel circular icon badge (Lavender, Pink, Blue, Mint)
    - Value with count-up animation
    - Clear title and subtle trend tag
    """
    clicked = Signal()

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str,
        icon_name: str,
        circle_type: str = "lavender",
        parent=None,
    ):
        super().__init__(parent, radius=20)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        # Top row: Pastel Icon Circle + Trend Badge
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.circle = PastelIconCircle(icon_name, circle_type=circle_type, size=40, icon_size=18)
        top_row.addWidget(self.circle)
        top_row.addStretch()

        self.lbl_sub = QLabel(subtitle)
        self._update_sub_style(subtitle)
        top_row.addWidget(self.lbl_sub)
        layout.addLayout(top_row)

        layout.addSpacing(4)

        # Middle: Big Value (counts up)
        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 26px; font-weight: 700; font-family: 'Inter', sans-serif;")
        layout.addWidget(self.lbl_val)

        # Bottom: Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.lbl_title)

    def _update_sub_style(self, sub: str):
        if "↑" in sub or ("%" in sub and "↓" not in sub) or "100%" in sub:
            badge_bg = COLOR_SUCCESS_TINT
            badge_fg = COLOR_SUCCESS
        elif "↓" in sub or "fail" in sub.lower():
            badge_bg = COLOR_DANGER_TINT
            badge_fg = COLOR_DANGER
        else:
            badge_bg = COLOR_LAVENDER_LIGHT
            badge_fg = COLOR_PRIMARY
        self.lbl_sub.setStyleSheet(f"background-color: {badge_bg}; color: {badge_fg}; font-size: 11px; font-weight: 700; border-radius: 8px; padding: 2px 8px;")

    def set_value(self, val: str):
        # If integer, animate count up
        clean_num = "".join(c for c in val if c.isdigit())
        if clean_num:
            animate_number(self.lbl_val, int(clean_num))
        else:
            self.lbl_val.setText(val)

    def set_subtitle(self, sub: str):
        self.lbl_sub.setText(sub)
        self._update_sub_style(sub)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class UploadDropCard(QFrame):
    """
    Friendly drag-and-drop card for CV files:
    - Lavender pastel circular cloud icon
    - 'Drag & drop a CV here'
    - 'or click to browse' link
    - Big orange action button 'Process a CV'
    """
    files_dropped = Signal(list)
    browse_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("UploadCard")
        self._set_normal_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        # Cloud Icon in Pastel Circle
        cloud_circle = PastelIconCircle("fa5s.cloud-upload-alt", circle_type="lavender", size=48, icon_size=22)
        layout.addWidget(cloud_circle, alignment=Qt.AlignCenter)

        # Title
        lbl_title = QLabel("Drag & drop a CV here")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 15px; font-weight: 700;")
        layout.addWidget(lbl_title)

        # Sub-link
        lbl_browse = QLabel("or click to browse files")
        lbl_browse.setAlignment(Qt.AlignCenter)
        lbl_browse.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 12.5px; font-weight: 600;")
        layout.addWidget(lbl_browse)

        # Supported formats
        lbl_desc = QLabel("Supports PDF, DOCX (Max 15MB)")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(lbl_desc)

    def _set_normal_style(self):
        self.setStyleSheet(f"""
            QFrame#UploadCard {{
                background-color: #F8F9FE;
                border: 2px dashed #C4B5FD;
                border-radius: 16px;
            }}
            QFrame#UploadCard:hover {{
                border-color: {COLOR_PRIMARY};
                background-color: #F3F1FD;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.browse_clicked.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in (".pdf", ".docx", ".doc"):
                    event.acceptProposedAction()
                    self.setStyleSheet(f"""
                        QFrame#UploadCard {{
                            background-color: {COLOR_PRIMARY_TINT};
                            border: 2px dashed {COLOR_PRIMARY};
                            border-radius: 16px;
                        }}
                    """)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._set_normal_style()

    def dropEvent(self, event: QDropEvent):
        self._set_normal_style()
        files = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = url.toLocalFile()
                if os.path.splitext(p)[1].lower() in (".pdf", ".docx", ".doc"):
                    files.append(p)
        if files:
            event.acceptProposedAction()
            self.files_dropped.emit(files)


class ToastNotification(QFrame):
    """
    Floating friendly notification toast anchored at bottom right with slide-in effect.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastFrame")
        self.setFixedWidth(360)
        self.setMinimumHeight(64)
        self.hide()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(107, 95, 181, 35))
        self.setGraphicsEffect(shadow)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(24, 24)
        layout.addWidget(self.lbl_icon)

        content = QVBoxLayout()
        content.setSpacing(2)
        content.setContentsMargins(0, 0, 0, 0)

        self.lbl_title = QLabel("Notification")
        self.lbl_title.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 700; font-size: 13px;")
        content.addWidget(self.lbl_title)

        self.lbl_msg = QLabel("Message body here")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        content.addWidget(self.lbl_msg)
        layout.addLayout(content, stretch=1)

        btn_close = QPushButton()
        btn_close.setIcon(qta.icon("fa5s.times", color="#9CA3AF"))
        btn_close.setFixedSize(22, 22)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("background: transparent; border: none;")
        btn_close.clicked.connect(self.hide)
        layout.addWidget(btn_close)

    def show_message(self, message: str, status_type: str = "info", title: Optional[str] = None, duration_ms: int = 4000):
        color_map = {
            "success": (COLOR_SUCCESS, "fa5s.check-circle", title or "Success"),
            "error": (COLOR_DANGER, "fa5s.exclamation-circle", title or "Error"),
            "warning": (COLOR_CTA, "fa5s.exclamation-triangle", title or "Warning"),
            "info": (COLOR_PRIMARY, "fa5s.info-circle", title or "Information"),
        }
        color_hex, icon_name, default_title = color_map.get(status_type, color_map["info"])

        self.lbl_icon.setPixmap(qta.icon(icon_name, color=color_hex).pixmap(24, 24))
        self.lbl_title.setText(default_title)
        self.lbl_title.setStyleSheet(f"color: {color_hex}; font-weight: 700; font-size: 13px;")
        self.lbl_msg.setText(message)

        self.setStyleSheet(f"""
            QFrame#ToastFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-left: 5px solid {color_hex};
                border-radius: 14px;
            }}
        """)

        if self.parent():
            parent_rect = self.parent().rect()
            x = parent_rect.width() - self.width() - 24
            y = parent_rect.height() - self.height() - 24
            self.move(x, y)

        self.raise_()
        self.show()
        self.timer.start(duration_ms)
