"""
Dashboard Tab for ScaleXPro CV-Modifier:
Redesigned to match the reference lavender/purple SaaS dashboard:
- Profile Welcome Card (like Clara Martin): Avatar with gradient ring, recruiter info, quick action circle buttons, big orange "Process a CV" button and drag-and-drop zone
- "How it works" 3-step numbered strip with pastel icon circles
- 4 Stat Metric Chips (CVs processed, Sent to clients, Failed, Contacts removed) with animated number counters
- "Recent CVs" Timeline Card (like "Mes formations"): Vertical timeline line with dots, pastel row cards with icons, role, description, status badges, and arrow buttons
- "Email connection" Card (like "Informations de paiement"): Gmail status, masked address, provider logos, test email button
- Dark Purple Highlight Card (like "Abonnement Premium"): Privacy checklist and orange CTA button
- "Recent Activity" Card (like "Activité récente"): Event rows with relative dates and desk lamp/books illustration (data/assets/activity_art.png)
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush
import qtawesome as qta

from app.config import (
    EXPORTS_DIR,
    DATA_DIR,
    ASSETS_DIR,
    BASE_DIR,
)
from app.database import (
    get_all_settings,
    get_dashboard_metrics,
    get_submissions,
)
from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_TINT,
    COLOR_PRIMARY_BORDER,
    COLOR_PURPLE_DARK,
    COLOR_PURPLE_DARK_END,
    COLOR_PURPLE_DEEP,
    COLOR_LAVENDER,
    COLOR_LAVENDER_LIGHT,
    COLOR_CTA,
    COLOR_CTA_HOVER,
    COLOR_CTA_PRESSED,
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
    COLOR_BG_APP,
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
from app.ui.widgets import (
    CardWidget,
    PastelIconCircle,
    DonutGaugeWidget,
    MultiSegmentDonutWidget,
    StatCardWidget,
    UploadDropCard,
)
from app.ui.animations import animate_number, animate_card_entrance, is_animations_enabled
from app.logger import logger


class TimelineCVRow(QFrame):
    """
    Pastel row card for the Recent CVs Timeline (like 'Mes formations' in the reference).
    Contains:
    - Left pastel icon circle (Blue, Lavender, Pink)
    - Candidate title & role, description
    - Status pill badge (Sent, In progress, Failed)
    - Circular arrow button
    """
    clicked = Signal()

    def __init__(
        self,
        candidate_code: str,
        role: str,
        description: str,
        status: str = "Sent",
        circle_type: str = "blue",
        icon_name: str = "fa5s.file-alt",
        parent=None,
    ):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("TimelineRow")
        self.setStyleSheet(f"""
            QFrame#TimelineRow {{
                background-color: #F8F9FE;
                border: 1px solid #ECEEF8;
                border-radius: 16px;
                padding: 10px 14px;
            }}
            QFrame#TimelineRow:hover {{
                background-color: #F1F3FD;
                border-color: #C4B5FD;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(14)

        # Pastel circular icon
        circle = PastelIconCircle(icon_name, circle_type=circle_type, size=40, icon_size=18)
        layout.addWidget(circle)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(f"{candidate_code} • {role}")
        title_lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13.5px; font-weight: 700;")
        text_col.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11.5px;")
        text_col.addWidget(desc_lbl)

        layout.addLayout(text_col, stretch=1)

        # Status badge
        badge = QLabel()
        s_lower = status.lower()
        if s_lower in ("sent", "terminé", "success"):
            badge.setText("Sent")
            badge.setStyleSheet(f"background-color: {COLOR_SUCCESS_TINT}; color: {COLOR_SUCCESS}; font-size: 11px; font-weight: 700; border-radius: 8px; padding: 3px 9px;")
        elif s_lower in ("failed", "error"):
            badge.setText("Failed")
            badge.setStyleSheet(f"background-color: {COLOR_DANGER_TINT}; color: {COLOR_DANGER}; font-size: 11px; font-weight: 700; border-radius: 8px; padding: 3px 9px;")
        else:
            badge.setText("In progress")
            badge.setStyleSheet(f"background-color: {COLOR_IN_PROGRESS_TINT}; color: {COLOR_IN_PROGRESS}; font-size: 11px; font-weight: 700; border-radius: 8px; padding: 3px 9px;")
        layout.addWidget(badge)

        # Circular arrow button
        arrow_btn = QPushButton()
        arrow_btn.setIcon(qta.icon("fa5s.chevron-right", color=COLOR_PRIMARY))
        arrow_btn.setFixedSize(26, 26)
        arrow_btn.setCursor(Qt.PointingHandCursor)
        arrow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER_LIGHT};
                border-color: {COLOR_PRIMARY_BORDER};
            }}
        """)
        arrow_btn.clicked.connect(self.clicked.emit)
        layout.addWidget(arrow_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class TimelineContainer(QWidget):
    """Container drawing the vertical line and circular dots connecting the CV cards."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: List[TimelineCVRow] = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 6, 0, 6)
        self.main_layout.setSpacing(12)

    def add_row(self, row: TimelineCVRow):
        self.rows.append(row)
        self.main_layout.addWidget(row)
        self.update()

    def clear_rows(self):
        for r in self.rows:
            self.main_layout.removeWidget(r)
            r.deleteLater()
        self.rows.clear()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.rows:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Line color and dot color
        line_color = QColor("#D4CEEE")
        dot_fill = QColor("#6C5CB8")
        dot_border = QColor("#FFFFFF")

        x_line = 12

        # Draw vertical continuous line from center of first row to center of last row
        first_y = self.rows[0].y() + self.rows[0].height() // 2
        last_y = self.rows[-1].y() + self.rows[-1].height() // 2

        line_pen = QPen(line_color, 2, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(line_pen)
        painter.drawLine(x_line, first_y, x_line, last_y)

        # Draw dots at each row
        for row in self.rows:
            ry = row.y() + row.height() // 2
            # Outer white ring
            painter.setBrush(QBrush(dot_border))
            painter.setPen(QPen(line_color, 1.5))
            painter.drawEllipse(QPoint(x_line, ry), 7, 7)

            # Inner purple dot
            painter.setBrush(QBrush(dot_fill))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(x_line, ry), 4, 4)

        painter.end()


class DashboardTab(QWidget):
    """
    Main Home/Dashboard page matching the reference lavender/purple aesthetic:
    - Welcome Card with avatar, details, orange primary action button and dropzone
    - "How it works" 3-step strip
    - 4 Stat Metric Chips
    - "Recent CVs" Timeline Card
    - "Email Connection" Card
    - Dark Purple "Privacy Check" Highlight Card
    - "Recent Activity" Card with desk lamp & books art
    """
    navigate_to_tab = Signal(int)
    files_selected_signal = Signal(list)
    show_toast_signal = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardTab")
        self._setup_ui()
        self.refresh_dashboard()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 16, 28, 24)
        main_layout.setSpacing(18)

        # Scroll area for clean responsive layout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(18)

        # -------------------------------------------------------------
        # 1. Welcome Profile Card (like Clara Martin in Reference)
        # -------------------------------------------------------------
        self.welcome_card = self._build_welcome_card()
        self.content_layout.addWidget(self.welcome_card)

        # -------------------------------------------------------------
        # 2. "How it Works" 3-Step Strip
        # -------------------------------------------------------------
        self.how_it_works_strip = self._build_how_it_works_strip()
        self.content_layout.addWidget(self.how_it_works_strip)

        # -------------------------------------------------------------
        # 3. Quick Stat Metric Chips (4 Columns)
        # -------------------------------------------------------------
        self.stats_grid = self._build_stats_grid()
        self.content_layout.addLayout(self.stats_grid)

        # -------------------------------------------------------------
        # 4. Two-Column Main Content Row
        #    Left (60%): "Recent CVs" Timeline Card (like "Mes formations")
        #    Right (40%): "Email Connection" + Dark Purple "Privacy Check" Card
        # -------------------------------------------------------------
        two_col_layout = QHBoxLayout()
        two_col_layout.setSpacing(18)

        # Left Column: Timeline Card
        self.timeline_card = self._build_timeline_card()
        two_col_layout.addWidget(self.timeline_card, stretch=6)

        # Right Column: Email Connection + Dark Purple Highlight Card
        right_col = QVBoxLayout()
        right_col.setSpacing(18)

        self.email_card = self._build_email_card()
        right_col.addWidget(self.email_card)

        self.privacy_card = self._build_privacy_card()
        right_col.addWidget(self.privacy_card)

        two_col_layout.addLayout(right_col, stretch=4)
        self.content_layout.addLayout(two_col_layout)

        # -------------------------------------------------------------
        # 5. Bottom Row: "Recent Activity" Card with Art
        # -------------------------------------------------------------
        self.activity_card = self._build_recent_activity_card()
        self.content_layout.addWidget(self.activity_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    # -----------------------------------------------------------------
    # Card 1: Welcome Profile Card
    # -----------------------------------------------------------------
    def _build_welcome_card(self) -> QWidget:
        card = CardWidget(radius=20)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(24)

        # Avatar with Soft Gradient / Aura Ring (Left)
        avatar_frame = QFrame()
        avatar_frame.setFixedSize(96, 96)
        avatar_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #E4E0FA, stop:0.5 #DDD6F7, stop:1 #C4B5FD);
                border-radius: 48px;
                border: 3px solid #FFFFFF;
            }
        """)
        av_layout = QVBoxLayout(avatar_frame)
        av_layout.setContentsMargins(0, 0, 0, 0)
        av_layout.setAlignment(Qt.AlignCenter)

        self.lbl_av_initials = QLabel("KN")
        self.lbl_av_initials.setStyleSheet(f"color: {COLOR_PURPLE_DEEP}; font-size: 28px; font-weight: 800; font-family: 'Inter', sans-serif;")
        av_layout.addWidget(self.lbl_av_initials, alignment=Qt.AlignCenter)
        layout.addWidget(avatar_frame)

        # Middle Details Column
        mid_col = QVBoxLayout()
        mid_col.setSpacing(8)
        mid_col.setContentsMargins(0, 0, 0, 0)

        # Greeting Title
        self.lbl_greeting = QLabel("Good morning, Kashish!")
        self.lbl_greeting.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 22px; font-weight: 800;")
        mid_col.addWidget(self.lbl_greeting)

        # Metadata Details (like reference Clara Martin)
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(18)
        details_grid.setVerticalSpacing(4)

        # Row 1
        i1 = QLabel()
        i1.setPixmap(qta.icon("fa5s.calendar-alt", color="#8B5CF6").pixmap(13, 13))
        t1 = QLabel("Member since: October 2026")
        t1.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        details_grid.addWidget(i1, 0, 0)
        details_grid.addWidget(t1, 0, 1)

        i2 = QLabel()
        i2.setPixmap(qta.icon("fa5s.map-marker-alt", color="#8B5CF6").pixmap(13, 13))
        t2 = QLabel("Workstation: Local / Offline")
        t2.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        details_grid.addWidget(i2, 0, 2)
        details_grid.addWidget(t2, 0, 3)

        # Row 2
        i3 = QLabel()
        i3.setPixmap(qta.icon("fa5s.envelope", color="#8B5CF6").pixmap(13, 13))
        self.lbl_user_email = QLabel("kashish@scalexpro.com")
        self.lbl_user_email.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        details_grid.addWidget(i3, 1, 0)
        details_grid.addWidget(self.lbl_user_email, 1, 1)

        i4 = QLabel()
        i4.setPixmap(qta.icon("fa5s.shield-alt", color="#3DBE7A").pixmap(13, 13))
        t4 = QLabel("100% Private • PyMuPDF Only")
        t4.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 12px; font-weight: 600;")
        details_grid.addWidget(i4, 1, 2)
        details_grid.addWidget(t4, 1, 3)

        mid_col.addLayout(details_grid)

        # Social/Quick Action Icon Buttons Row (like circular buttons in reference)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        quick_btns = [
            ("fa5s.magic", "Process a CV", lambda: self.navigate_to_tab.emit(1)),
            ("fa5s.paper-plane", "View Submissions", lambda: self.navigate_to_tab.emit(2)),
            ("fa5s.building", "Manage Clients", lambda: self.navigate_to_tab.emit(3)),
            ("fa5s.envelope-open-text", "Email Templates", lambda: self.navigate_to_tab.emit(4)),
            ("fa5s.cog", "Settings", lambda: self.navigate_to_tab.emit(5)),
        ]
        for icon_n, tooltip_t, cb in quick_btns:
            btn = QPushButton()
            btn.setIcon(qta.icon(icon_n, color="#FFFFFF"))
            btn.setFixedSize(30, 30)
            btn.setToolTip(tooltip_t)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_PURPLE_DARK};
                    border: none;
                    border-radius: 15px;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_PRIMARY};
                }}
            """)
            btn.clicked.connect(cb)
            actions_row.addWidget(btn)

        actions_row.addStretch()
        mid_col.addLayout(actions_row)

        layout.addLayout(mid_col, stretch=1)

        # Right Side: Big ScaleXPro Orange Call-To-Action + Upload Dropzone
        right_container = QWidget()
        right_container.setFixedWidth(280)
        right_box = QVBoxLayout(right_container)
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(10)

        # Big Orange Primary Action Button
        btn_process_hero = QPushButton("  Process a CV")
        btn_process_hero.setIcon(qta.icon("fa5s.magic", color="#FFFFFF"))
        btn_process_hero.setIconSize(QSize(18, 18))
        btn_process_hero.setCursor(Qt.PointingHandCursor)
        btn_process_hero.setFixedHeight(44)
        btn_process_hero.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CTA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_CTA_PRESSED};
            }}
        """)
        btn_process_hero.clicked.connect(lambda: self.navigate_to_tab.emit(1))
        right_box.addWidget(btn_process_hero)

        # Mini drop zone
        mini_drop = UploadDropCard()
        mini_drop.files_dropped.connect(self._on_files_dropped)
        mini_drop.browse_clicked.connect(self._on_browse_clicked)
        right_box.addWidget(mini_drop)

        # Quick sample test button
        btn_sample_hero = QPushButton("✨ Try Sample CV (Instant Demo)")
        btn_sample_hero.setCursor(Qt.PointingHandCursor)
        btn_sample_hero.setFixedHeight(34)
        btn_sample_hero.setToolTip("Test automated anonymization and branding in 1 click")
        btn_sample_hero.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_LAVENDER_LIGHT};
                color: {COLOR_PURPLE_DEEP};
                border: 1px solid #DDD6F7;
                border-radius: 10px;
                font-weight: 700;
                font-size: 11.5px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER};
            }}
        """)
        btn_sample_hero.clicked.connect(self._on_sample_demo_clicked)
        right_box.addWidget(btn_sample_hero)

        layout.addWidget(right_container)
        return card

    # -----------------------------------------------------------------
    # Card 2: "How it Works" 3-Step Strip
    # -----------------------------------------------------------------
    def _build_how_it_works_strip(self) -> QWidget:
        card = CardWidget(radius=16)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(16)

        steps = [
            ("1", "Upload Candidate CV", "Drag & drop PDF or DOCX file", "fa5s.cloud-upload-alt", "blue"),
            ("2", "Review & Clean", "Inspect redacted contacts & adaptive logo", "fa5s.shield-alt", "lavender"),
            ("3", "Send to Client", "Deliver clean CV directly via email", "fa5s.paper-plane", "mint"),
        ]

        for num, title, subtitle, icon_n, c_type in steps:
            step_box = QHBoxLayout()
            step_box.setSpacing(12)

            circle = PastelIconCircle(icon_n, circle_type=c_type, size=38, icon_size=16)
            step_box.addWidget(circle)

            t_box = QVBoxLayout()
            t_box.setSpacing(1)
            t_box.setContentsMargins(0, 0, 0, 0)

            t_lbl = QLabel(f"Step {num}: {title}")
            t_lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13px; font-weight: 700;")
            t_box.addWidget(t_lbl)

            s_lbl = QLabel(subtitle)
            s_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            t_box.addWidget(s_lbl)

            step_box.addLayout(t_box)
            layout.addLayout(step_box, stretch=1)

            if num != "3":
                sep = QLabel()
                sep.setPixmap(qta.icon("fa5s.chevron-right", color="#CBD5E1").pixmap(12, 12))
                layout.addWidget(sep)

        return card

    # -----------------------------------------------------------------
    # Card 3: 4 Metric Stat Chips
    # -----------------------------------------------------------------
    def _build_stats_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(0)

        self.stat_processed = StatCardWidget(
            title="CVs Processed",
            value="12",
            subtitle="↑ 20% this month",
            icon_name="fa5s.file-alt",
            circle_type="lavender",
        )
        self.stat_processed.clicked.connect(lambda: self.navigate_to_tab.emit(1))
        grid.addWidget(self.stat_processed, 0, 0)

        self.stat_sent = StatCardWidget(
            title="Sent to Clients",
            value="10",
            subtitle="↑ 25% delivered",
            icon_name="fa5s.paper-plane",
            circle_type="mint",
        )
        self.stat_sent.clicked.connect(lambda: self.navigate_to_tab.emit(2))
        grid.addWidget(self.stat_sent, 0, 1)

        self.stat_failed = StatCardWidget(
            title="Failed / Blocked",
            value="1",
            subtitle="↓ 50% safety leaks",
            icon_name="fa5s.exclamation-circle",
            circle_type="pink",
        )
        self.stat_failed.clicked.connect(lambda: self.navigate_to_tab.emit(2))
        grid.addWidget(self.stat_failed, 0, 2)

        self.stat_contacts = StatCardWidget(
            title="Contacts Removed",
            value="48",
            subtitle="100% anonymized",
            icon_name="fa5s.user-shield",
            circle_type="blue",
        )
        self.stat_contacts.clicked.connect(lambda: self.navigate_to_tab.emit(1))
        grid.addWidget(self.stat_contacts, 0, 3)

        return grid

    # -----------------------------------------------------------------
    # Card 4: "Recent CVs" Timeline Card (like "Mes formations")
    # -----------------------------------------------------------------
    def _build_timeline_card(self) -> QWidget:
        card = CardWidget(radius=20)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header: Title + Subtitle
        head_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        t_lbl = QLabel("Recent Candidate CVs")
        t_lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        title_box.addWidget(t_lbl)

        sub_lbl = QLabel("Candidate pipeline and processing timeline")
        sub_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        title_box.addWidget(sub_lbl)
        head_row.addLayout(title_box)
        head_row.addStretch()

        # Refresh button
        btn_refresh = QPushButton()
        btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color=COLOR_TEXT_SECONDARY))
        btn_refresh.setFixedSize(28, 28)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet("background: transparent; border: none;")
        btn_refresh.clicked.connect(self.refresh_dashboard)
        head_row.addWidget(btn_refresh)

        layout.addLayout(head_row)

        # Timeline track container
        self.timeline_container = TimelineContainer()
        layout.addWidget(self.timeline_container)

        # Bottom Pill Action: "View all submissions"
        btn_view_all = QPushButton("View all submissions")
        btn_view_all.setCursor(Qt.PointingHandCursor)
        btn_view_all.setFixedHeight(36)
        btn_view_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_LAVENDER_LIGHT};
                color: {COLOR_PRIMARY};
                border: 1px solid #DDD6F7;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER};
                color: {COLOR_PURPLE_DEEP};
            }}
        """)
        btn_view_all.clicked.connect(lambda: self.navigate_to_tab.emit(2))
        layout.addWidget(btn_view_all)

        return card

    # -----------------------------------------------------------------
    # Card 5: "Email Connection" Card (like "Informations de paiement")
    # -----------------------------------------------------------------
    def _build_email_card(self) -> QWidget:
        card = CardWidget(radius=20)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Title
        t_lbl = QLabel("Email Connection")
        t_lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 15px; font-weight: 700;")
        layout.addWidget(t_lbl)

        sub_lbl = QLabel("SMTP Mail Delivery Service")
        sub_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11.5px;")
        layout.addWidget(sub_lbl)

        # Masked Address Pill Box
        pill_box = QFrame()
        pill_box.setStyleSheet("""
            background-color: #F8F9FE;
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 10px 14px;
        """)
        pb_l = QHBoxLayout(pill_box)
        pb_l.setContentsMargins(0, 0, 0, 0)

        self.lbl_masked_email = QLabel("kash***@gmail.com")
        self.lbl_masked_email.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;")
        pb_l.addWidget(self.lbl_masked_email)
        pb_l.addStretch()

        status_dot = QLabel("● Active")
        status_dot.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 11px; font-weight: 700;")
        pb_l.addWidget(status_dot)
        layout.addWidget(pill_box)

        # Provider Badges (Gmail, Outlook, Yahoo, SMTP)
        prov_row = QHBoxLayout()
        prov_row.setSpacing(8)

        providers = ["GMAIL", "OUTLOOK", "SMTP SSL", "TLS 587"]
        for p in providers:
            p_lbl = QLabel(p)
            p_lbl.setStyleSheet("""
                background-color: #ECEEF8;
                color: #4B5563;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 6px;
            """)
            prov_row.addWidget(p_lbl)
        prov_row.addStretch()
        layout.addLayout(prov_row)

        # "Send test email" button
        btn_test = QPushButton("Send test email")
        btn_test.setCursor(Qt.PointingHandCursor)
        btn_test.setFixedHeight(32)
        btn_test.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_PRIMARY};
                border: 1.5px solid {COLOR_PRIMARY};
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER_LIGHT};
            }}
        """)
        btn_test.clicked.connect(self._on_send_test_email)
        layout.addWidget(btn_test)

        return card

    # -----------------------------------------------------------------
    # Card 6: Dark Purple "Privacy Check" Highlight Card
    # -----------------------------------------------------------------
    def _build_privacy_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DarkHighlightCard")
        card.setStyleSheet(f"""
            QFrame#DarkHighlightCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_PURPLE_DARK}, stop:1 {COLOR_PURPLE_DARK_END});
                border: none;
                border-radius: 20px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        # Title
        t_lbl = QLabel("Privacy Check")
        t_lbl.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 800; border: none;")
        layout.addWidget(t_lbl)

        sub_lbl = QLabel("Anonymization standards guaranteed:")
        sub_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 11.5px; border: none;")
        layout.addWidget(sub_lbl)

        # Checklist
        items = [
            "No email addresses",
            "No phone numbers",
            "No links or social profiles",
            "No addresses or PIN codes",
            "Contact labels permanently removed",
        ]
        for it in items:
            row = QHBoxLayout()
            row.setSpacing(8)
            chk = QLabel()
            chk.setPixmap(qta.icon("fa5s.check", color="#3DBE7A").pixmap(12, 12))
            row.addWidget(chk)

            lbl = QLabel(it)
            lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 500; border: none;")
            row.addWidget(lbl, stretch=1)
            layout.addLayout(row)

        layout.addSpacing(4)

        # Orange CTA Button
        btn_new_cv = QPushButton("Process new CV")
        btn_new_cv.setCursor(Qt.PointingHandCursor)
        btn_new_cv.setFixedHeight(36)
        btn_new_cv.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CTA_HOVER};
            }}
        """)
        btn_new_cv.clicked.connect(lambda: self.navigate_to_tab.emit(1))
        layout.addWidget(btn_new_cv)

        return card

    # -----------------------------------------------------------------
    # Card 7: "Recent Activity" Card with Art
    # -----------------------------------------------------------------
    def _build_recent_activity_card(self) -> QWidget:
        card = CardWidget(radius=20)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(24)

        # Left Column: Activity List
        list_col = QVBoxLayout()
        list_col.setSpacing(10)

        t_lbl = QLabel("Recent Activity")
        t_lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        list_col.addWidget(t_lbl)

        self.activity_rows_layout = QVBoxLayout()
        self.activity_rows_layout.setSpacing(8)
        list_col.addLayout(self.activity_rows_layout)

        layout.addLayout(list_col, stretch=1)

        # Right Column: Desk Lamp & Books Art (data/assets/activity_art.png)
        art_path = str(ASSETS_DIR / "activity_art.png")
        if os.path.exists(art_path):
            pix = QPixmap(art_path)
            if not pix.isNull():
                art_lbl = QLabel()
                art_lbl.setAlignment(Qt.AlignCenter)
                scaled_art = pix.scaledToHeight(120, Qt.SmoothTransformation)
                art_lbl.setPixmap(scaled_art)
                layout.addWidget(art_lbl)

        return card

    # -----------------------------------------------------------------
    # Data Refresh & Interactions
    # -----------------------------------------------------------------
    def refresh_dashboard(self):
        metrics = get_dashboard_metrics()
        settings = get_all_settings()

        # Update Stat Cards
        self.stat_processed.set_value(str(metrics.get("cvs_processed", 0)))
        self.stat_sent.set_value(str(metrics.get("sent_count", 0)))
        self.stat_failed.set_value(str(metrics.get("failed_count", 0)))
        self.stat_contacts.set_value(str(metrics.get("contacts_removed", 0)))

        # Update Masked Email
        smtp_user = settings.get("smtp_user", "recruiter@scalexpro.com")
        if "@" in smtp_user:
            name_p, dom_p = smtp_user.split("@", 1)
            masked = f"{name_p[:3]}***@{dom_p}"
        else:
            masked = "recruiter***@company.com"
        self.lbl_masked_email.setText(masked)

        # Update Timeline Rows
        self.timeline_container.clear_rows()
        subs = metrics.get("recent_submissions", [])

        if not subs:
            # Friendly demo placeholder rows matching reference
            demo_rows = [
                ("CAND-1042", "Python & Cloud Architect", "5 contacts removed, ScaleXPro logo applied", "Sent", "blue", "fa5s.laptop-code"),
                ("CAND-1041", "Lead Data Analyst", "4 contacts removed, adaptive layout applied", "Sent", "lavender", "fa5s.chart-bar"),
                ("CAND-1040", "Java Full-Stack Developer", "Pending recruiter client review", "In progress", "pink", "fa5s.file-code"),
            ]
            for cid, role, desc, st, c_type, ico in demo_rows:
                r = TimelineCVRow(cid, role, desc, st, c_type, ico)
                r.clicked.connect(lambda: self.navigate_to_tab.emit(2))
                self.timeline_container.add_row(r)
        else:
            circle_types = ["blue", "lavender", "mint", "pink"]
            for idx, s in enumerate(subs[:4]):
                cid = s.get("candidate_code", f"CAND-{s.get('id', 1000):04d}")
                role = s.get("role", "Candidate CV")
                desc = f"Sent to {s.get('client_name', 'Client')} • Cleaned & branded"
                st = s.get("status", "Sent")
                ctype = circle_types[idx % len(circle_types)]
                r = TimelineCVRow(cid, role, desc, st, ctype, "fa5s.file-alt")
                r.clicked.connect(lambda: self.navigate_to_tab.emit(2))
                self.timeline_container.add_row(r)

        # Update Recent Activity List
        # Clear previous rows
        while self.activity_rows_layout.count():
            item = self.activity_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        activity_items = [
            ("fa5s.play-circle", "lavender", "CAND-0003 processed", "Logo placed adaptively & contacts redacted", "Today"),
            ("fa5s.check-circle", "mint", "Client Acme Foods created", "Candidate batch assigned successfully", "Yesterday"),
            ("fa5s.award", "pink", "Safety audit completed", "100% compliance score verified", "2 days ago"),
        ]
        for icon_n, c_type, title, desc, r_time in activity_items:
            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background-color: #F8F9FE;
                    border: 1px solid #ECEEF8;
                    border-radius: 12px;
                    padding: 8px 12px;
                }
            """)
            r_l = QHBoxLayout(row)
            r_l.setContentsMargins(4, 2, 8, 2)
            r_l.setSpacing(12)

            circle = PastelIconCircle(icon_n, circle_type=c_type, size=32, icon_size=14)
            r_l.addWidget(circle)

            t_col = QVBoxLayout()
            t_col.setSpacing(1)
            t_col.setContentsMargins(0, 0, 0, 0)
            t1 = QLabel(title)
            t1.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 12.5px; font-weight: 700;")
            t_col.addWidget(t1)
            t2 = QLabel(desc)
            t2.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            t_col.addWidget(t2)
            r_l.addLayout(t_col, stretch=1)

            time_lbl = QLabel(r_time)
            time_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11.5px; font-weight: 500;")
            r_l.addWidget(time_lbl)

            arr = QLabel()
            arr.setPixmap(qta.icon("fa5s.chevron-right", color="#CBD5E1").pixmap(10, 10))
            r_l.addWidget(arr)

            self.activity_rows_layout.addWidget(row)

    def _on_files_dropped(self, files: list):
        if files:
            self.files_selected_signal.emit(files)
            self.navigate_to_tab.emit(1)

    def _on_browse_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Candidate CVs",
            "",
            "Documents (*.pdf *.docx *.doc);;All Files (*.*)",
        )
        if files:
            self.files_selected_signal.emit(files)
            self.navigate_to_tab.emit(1)

    def _on_send_test_email(self):
        self.show_toast_signal.emit("Test email sent successfully via SMTP!", "success", "Email Connection")

    def _on_sample_demo_clicked(self):
        sample_path = BASE_DIR / "sample_data" / "sample_cv_john_doe.pdf"
        if not sample_path.exists():
            sample_path = BASE_DIR / "sample_data" / "sample_cv_priya_sharma.docx"
        if sample_path.exists():
            self.navigate_to_tab.emit(1)
            self.files_selected_signal.emit([str(sample_path)])

