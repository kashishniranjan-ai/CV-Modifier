"""
Login View for ScaleXPro CV-Modifier:
- Screen 1 of Design Board: Split layout (Left branded sunrise panel, Right sign-in card)
- Real offline PBKDF2 authentication with SQLite users table
- Lockout for 60 seconds after 5 failed attempts
- First-run "Create Admin Account" wizard
- Remember Me support (persists username in settings)
- Show / Hide password toggle
- Responsive, pixel-perfect matching to design board
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QStackedWidget,
    QGraphicsDropShadowEffect,
    QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QLinearGradient,
    QColor,
    QPen,
    QBrush,
    QFont,
    QCursor,
)
import qtawesome as qta

from app.config import ASSETS_DIR
from app.database import (
    get_user_count,
    authenticate_user,
    create_user,
    get_setting,
    set_setting,
)
from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_TINT,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_NAVY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_BORDER_FOCUS,
)
from app.logger import logger


class BrandedLeftPanel(QFrame):
    """Left branded panel matching Screen 1 on the design board."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BrandedLeftPanel")
        self.setMinimumWidth(440)
        self._bg_pixmap: Optional[QPixmap] = None
        
        bg_path = ASSETS_DIR / "login_bg.png"
        if bg_path.exists():
            self._bg_pixmap = QPixmap(str(bg_path))

        self._setup_content()

    def _setup_content(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 48, 40, 48)
        layout.setSpacing(24)

        # ScaleXPro Logo
        logo_label = QLabel()
        logo_path = ASSETS_DIR / "scalexpro_logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                logo_label.setPixmap(pix.scaledToWidth(200, Qt.SmoothTransformation))
        if not logo_label.pixmap() or logo_label.pixmap().isNull():
            logo_label.setText("ScaleXPro")
            logo_label.setStyleSheet("color: #FFFFFF; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;")
        
        layout.addWidget(logo_label)
        layout.addSpacing(20)

        # Headline
        headline = QLabel("Send clean, branded CVs\nto clients in seconds")
        headline.setWordWrap(True)
        headline.setStyleSheet("""
            color: #FFFFFF;
            font-size: 30px;
            font-weight: 800;
            line-height: 1.25;
            letter-spacing: -0.5px;
        """)
        layout.addWidget(headline)

        subhead = QLabel("Automated offline candidate anonymization, enterprise logo branding, and client delivery audit trail.")
        subhead.setWordWrap(True)
        subhead.setStyleSheet("color: rgba(255, 255, 255, 0.88); font-size: 14px; line-height: 1.45;")
        layout.addWidget(subhead)

        layout.addSpacing(16)

        # 3 Trust Points matching the board: Offline, Secure, Tracked
        trust_points = [
            ("fa5s.laptop-code", "#6BA32E", "100% Offline Processing", "Candidate data and resumes never leave your computer."),
            ("fa5s.shield-alt", "#F28A1E", "Permanent Redaction", "True content stripping & label removal with zero recovery risk."),
            ("fa5s.check-circle", "#3B82F6", "Delivery Audit Trail", "Instant SQLite logging, client history, and SMTP email logs."),
        ]

        self.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        for icon_name, icon_color, title, desc in trust_points:
            card = QFrame()
            card.setObjectName("TrustCard")
            card.setStyleSheet("""
                QFrame#TrustCard {
                    background-color: rgba(255, 255, 255, 0.16);
                    border: 1px solid rgba(255, 255, 255, 0.25);
                    border-radius: 12px;
                }
                QLabel {
                    background: transparent;
                    border: none;
                }
            """)
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(14, 12, 14, 12)
            c_layout.setSpacing(14)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon(icon_name, color="#FFFFFF").pixmap(20, 20))
            icon_lbl.setFixedSize(36, 36)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet(f"background-color: rgba(255, 255, 255, 0.2); border-radius: 18px;")
            c_layout.addWidget(icon_lbl)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 13px;")
            d_lbl = QLabel(desc)
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 11px; line-height: 1.3;")
            text_col.addWidget(t_lbl)
            text_col.addWidget(d_lbl)
            c_layout.addLayout(text_col, stretch=1)

            layout.addWidget(card)

        layout.addStretch()

        # Footer badge
        footer_row = QHBoxLayout()
        footer_row.setSpacing(8)
        lock_icon = QLabel()
        lock_icon.setPixmap(qta.icon("fa5s.lock", color="rgba(255, 255, 255, 0.75)").pixmap(12, 12))
        footer_row.addWidget(lock_icon)
        footer_lbl = QLabel("ScaleXPro Enterprise Edition • Better Hiring. Together.")
        footer_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.75); font-size: 11px; font-weight: 500;")
        footer_row.addWidget(footer_lbl)
        footer_row.addStretch()
        layout.addLayout(footer_row)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self._bg_pixmap and not self._bg_pixmap.isNull():
            # Draw the background image scaled to fill
            scaled = self._bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            # Overlay a warm gradient tint for contrast
            overlay_grad = QLinearGradient(0, 0, self.width(), self.height())
            overlay_grad.setColorAt(0.0, QColor(242, 138, 30, 160))  # Orange #F28A1E
            overlay_grad.setColorAt(0.7, QColor(15, 23, 42, 190))   # Navy #0F172A
            overlay_grad.setColorAt(1.0, QColor(15, 23, 42, 220))
            painter.fillRect(self.rect(), QBrush(overlay_grad))
        else:
            # Fallback warm sunrise gradient
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0.0, QColor("#F28A1E"))
            grad.setColorAt(0.5, QColor("#DB7710"))
            grad.setColorAt(1.0, QColor("#0F172A"))
            painter.fillRect(self.rect(), QBrush(grad))


class LoginView(QWidget):
    """
    Main Split-Screen Login View:
    - Left: Branded decorative panel with 3 trust points
    - Right: Centered Sign In card or Create Admin Account card
    """
    login_successful = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginRoot")
        self.setStyleSheet("background-color: #F1F5F9;")

        self._lockout_seconds_remaining = 0
        self._lockout_timer = QTimer(self)
        self._lockout_timer.setInterval(1000)
        self._lockout_timer.timeout.connect(self._on_lockout_tick)

        self._setup_ui()
        self.check_initial_state()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Branded Panel (45% width)
        self.left_panel = BrandedLeftPanel(self)
        main_layout.addWidget(self.left_panel, 45)

        # 2. Right Form Container (55% width)
        right_container = QWidget()
        right_container.setStyleSheet("background-color: #F1F5F9;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(40, 40, 40, 40)
        right_layout.setAlignment(Qt.AlignCenter)

        # Stack hosting Sign In vs Create Admin
        self.form_stack = QStackedWidget()
        self.form_stack.setFixedWidth(460)

        self.signin_page = self._build_signin_card()
        self.admin_setup_page = self._build_admin_setup_card()

        self.form_stack.addWidget(self.signin_page)       # Index 0
        self.form_stack.addWidget(self.admin_setup_page)  # Index 1

        right_layout.addWidget(self.form_stack, 0, Qt.AlignCenter)
        main_layout.addWidget(right_container, 55)

    def _build_signin_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("SignInCard")
        card.setStyleSheet("""
            QFrame#SignInCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(15, 23, 42, 18))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 40, 36, 40)
        layout.setSpacing(18)

        # Header
        h_col = QVBoxLayout()
        h_col.setSpacing(4)
        title = QLabel("Welcome Back")
        title.setStyleSheet("color: #0F172A; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;")
        subtitle = QLabel("Sign in to your ScaleXPro offline account")
        subtitle.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 400;")
        h_col.addWidget(title)
        h_col.addWidget(subtitle)
        layout.addLayout(h_col)

        # Error / Status Banner
        self.lbl_signin_error = QLabel()
        self.lbl_signin_error.setWordWrap(True)
        self.lbl_signin_error.setVisible(False)
        self.lbl_signin_error.setStyleSheet("""
            background-color: #FDEAEA;
            color: #E32B2B;
            border: 1px solid #F8C8C8;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 12px;
            font-weight: 600;
        """)
        layout.addWidget(self.lbl_signin_error)

        # Username / Email Field
        user_box = QVBoxLayout()
        user_box.setSpacing(6)
        lbl_u = QLabel("Username or Email")
        lbl_u.setStyleSheet("color: #0F172A; font-weight: 600; font-size: 12px;")
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. admin or recruiter@scalexpro.com")
        self.txt_username.setFixedHeight(42)
        self.txt_username.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1px solid #F28A1E;
            }
        """)
        self.txt_username.returnPressed.connect(self._handle_signin)
        user_box.addWidget(lbl_u)
        user_box.addWidget(self.txt_username)
        layout.addLayout(user_box)

        # Password Field with Show/Hide Eye Toggle
        pass_box = QVBoxLayout()
        pass_box.setSpacing(6)
        lbl_p = QLabel("Password")
        lbl_p.setStyleSheet("color: #0F172A; font-weight: 600; font-size: 12px;")
        
        pass_row = QHBoxLayout()
        pass_row.setSpacing(0)

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Enter your password")
        self.txt_password.setFixedHeight(42)
        self.txt_password.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 8px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 1px solid #F28A1E;
            }
        """)
        self.txt_password.returnPressed.connect(self._handle_signin)
        pass_row.addWidget(self.txt_password, stretch=1)

        self.btn_toggle_pass = QPushButton()
        self.btn_toggle_pass.setIcon(qta.icon("fa5s.eye", color=COLOR_TEXT_SECONDARY))
        self.btn_toggle_pass.setFixedSize(42, 42)
        self.btn_toggle_pass.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_pass.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
            }
        """)
        self.btn_toggle_pass.clicked.connect(self._toggle_password_visibility)
        pass_row.addWidget(self.btn_toggle_pass)

        pass_box.addWidget(lbl_p)
        pass_box.addLayout(pass_row)
        layout.addLayout(pass_box)

        # Remember Me + Forgot Password Row
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        self.chk_remember = QCheckBox("Remember me")
        self.chk_remember.setStyleSheet("color: #334155; font-size: 12px; font-weight: 500;")
        action_row.addWidget(self.chk_remember)
        action_row.addStretch()

        btn_forgot = QPushButton("Forgot password?")
        btn_forgot.setCursor(Qt.PointingHandCursor)
        btn_forgot.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #F28A1E;
                font-size: 12px;
                font-weight: 600;
                padding: 0;
            }
            QPushButton:hover {
                color: #DB7710;
                text-decoration: underline;
            }
        """)
        btn_forgot.clicked.connect(self._on_forgot_password)
        action_row.addWidget(btn_forgot)
        layout.addLayout(action_row)

        layout.addSpacing(6)

        # Sign In Button (Solid Orange)
        self.btn_signin = QPushButton("  Sign in  →")
        self.btn_signin.setFixedHeight(44)
        self.btn_signin.setCursor(Qt.PointingHandCursor)
        self.btn_signin.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_PRIMARY_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: #CBD5E1;
                color: #FFFFFF;
            }}
        """)
        self.btn_signin.clicked.connect(self._handle_signin)
        layout.addWidget(self.btn_signin)

        # Quick Start (Offline Mode) Button
        self.btn_quick = QPushButton("⚡  Quick Start (Offline Workspace)  →")
        self.btn_quick.setFixedHeight(42)
        self.btn_quick.setCursor(Qt.PointingHandCursor)
        self.btn_quick.setToolTip("Start immediately without entering credentials")
        self.btn_quick.setStyleSheet("""
            QPushButton {
                background-color: #EDE9FE;
                color: #5B21B6;
                border: 1px solid #DDD6FE;
                border-radius: 8px;
                font-size: 13.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #DDD6FE;
                color: #4C1D95;
            }
        """)
        self.btn_quick.clicked.connect(self._handle_quick_start)
        layout.addWidget(self.btn_quick)

        # Version & Offline Mode Footer
        v_row = QHBoxLayout()
        v_row.setSpacing(6)
        v_row.setAlignment(Qt.AlignCenter)
        dot = QLabel("●")
        dot.setStyleSheet("color: #6BA32E; font-size: 10px;")
        v_txt = QLabel("v2.5.0 • Offline Mode (Protected)")
        v_txt.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
        v_row.addWidget(dot)
        v_row.addWidget(v_txt)
        layout.addLayout(v_row)

        return card

    def _build_admin_setup_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("AdminSetupCard")
        card.setStyleSheet("""
            QFrame#AdminSetupCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(15, 23, 42, 18))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(14)

        # Header
        h_col = QVBoxLayout()
        h_col.setSpacing(4)
        title = QLabel("Create Admin Account")
        title.setStyleSheet("color: #0F172A; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;")
        subtitle = QLabel("First-run setup: Configure the local administrator account")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 400;")
        h_col.addWidget(title)
        h_col.addWidget(subtitle)
        layout.addLayout(h_col)

        # Error Banner
        self.lbl_admin_error = QLabel()
        self.lbl_admin_error.setWordWrap(True)
        self.lbl_admin_error.setVisible(False)
        self.lbl_admin_error.setStyleSheet("""
            background-color: #FDEAEA;
            color: #E32B2B;
            border: 1px solid #F8C8C8;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
        """)
        layout.addWidget(self.lbl_admin_error)

        # Form fields
        self.txt_admin_name = QLineEdit()
        self.txt_admin_name.setPlaceholderText("Full Name (e.g. Kashish Niranjan)")
        self.txt_admin_name.setFixedHeight(38)
        layout.addWidget(QLabel("Full Name"))
        layout.addWidget(self.txt_admin_name)

        self.txt_admin_user = QLineEdit()
        self.txt_admin_user.setPlaceholderText("Username (e.g. admin)")
        self.txt_admin_user.setFixedHeight(38)
        layout.addWidget(QLabel("Username"))
        layout.addWidget(self.txt_admin_user)

        self.txt_admin_email = QLineEdit()
        self.txt_admin_email.setPlaceholderText("Work Email (e.g. admin@scalexpro.com)")
        self.txt_admin_email.setFixedHeight(38)
        layout.addWidget(QLabel("Email Address"))
        layout.addWidget(self.txt_admin_email)

        self.txt_admin_pass = QLineEdit()
        self.txt_admin_pass.setEchoMode(QLineEdit.Password)
        self.txt_admin_pass.setPlaceholderText("Password (at least 6 characters)")
        self.txt_admin_pass.setFixedHeight(38)
        layout.addWidget(QLabel("Password"))
        layout.addWidget(self.txt_admin_pass)

        self.txt_admin_confirm = QLineEdit()
        self.txt_admin_confirm.setEchoMode(QLineEdit.Password)
        self.txt_admin_confirm.setPlaceholderText("Confirm password")
        self.txt_admin_confirm.setFixedHeight(38)
        layout.addWidget(QLabel("Confirm Password"))
        layout.addWidget(self.txt_admin_confirm)

        layout.addSpacing(6)

        btn_create = QPushButton("Create Admin && Get Started  →")
        btn_create.setFixedHeight(44)
        btn_create.setCursor(Qt.PointingHandCursor)
        btn_create.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_PRIMARY_PRESSED};
            }}
        """)
        btn_create.clicked.connect(self._handle_create_admin)
        layout.addWidget(btn_create)

        btn_quick_admin = QPushButton("⚡  1-Click Quick Setup (Start Immediately)  →")
        btn_quick_admin.setFixedHeight(42)
        btn_quick_admin.setCursor(Qt.PointingHandCursor)
        btn_quick_admin.setToolTip("Quickly configure default profile and enter workspace")
        btn_quick_admin.setStyleSheet("""
            QPushButton {
                background-color: #EDE9FE;
                color: #5B21B6;
                border: 1px solid #DDD6FE;
                border-radius: 8px;
                font-size: 13.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #DDD6FE;
                color: #4C1D95;
            }
        """)
        btn_quick_admin.clicked.connect(self._handle_quick_admin_setup)
        layout.addWidget(btn_quick_admin)

        return card

    def check_initial_state(self):
        """Switches to Admin Setup if no users exist, else prepares Sign In."""
        user_count = get_user_count()
        if user_count == 0:
            self.form_stack.setCurrentIndex(1)
        else:
            self.form_stack.setCurrentIndex(0)
            # Load remembered username if present
            remembered = get_setting("remembered_username", "")
            if remembered:
                self.txt_username.setText(remembered)
                self.chk_remember.setChecked(True)
                self.txt_password.setFocus()
            else:
                self.txt_username.setFocus()

    def _toggle_password_visibility(self):
        if self.txt_password.echoMode() == QLineEdit.Password:
            self.txt_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_pass.setIcon(qta.icon("fa5s.eye-slash", color=COLOR_PRIMARY))
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_pass.setIcon(qta.icon("fa5s.eye", color=COLOR_TEXT_SECONDARY))

    def _handle_signin(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        self.lbl_signin_error.setVisible(False)

        if not username or not password:
            self.lbl_signin_error.setText("Please enter both username and password.")
            self.lbl_signin_error.setVisible(True)
            return

        success, user, err = authenticate_user(username, password)
        if success and user:
            # Handle remember me
            if self.chk_remember.isChecked():
                set_setting("remembered_username", username)
            else:
                set_setting("remembered_username", "")

            self.txt_password.clear()
            self.lbl_signin_error.setVisible(False)
            logger.info(f"User '{user['username']}' ({user['role']}) authenticated successfully.")
            self.login_successful.emit(user)
        else:
            self.lbl_signin_error.setText(err or "Authentication failed.")
            self.lbl_signin_error.setVisible(True)
            # If account got locked, initiate countdown
            if "locked" in (err or "").lower():
                self._start_lockout_countdown(60)

    def _start_lockout_countdown(self, seconds: int):
        self._lockout_seconds_remaining = seconds
        self.btn_signin.setEnabled(False)
        self.txt_username.setEnabled(False)
        self.txt_password.setEnabled(False)
        self._lockout_timer.start()

    def _on_lockout_tick(self):
        self._lockout_seconds_remaining -= 1
        if self._lockout_seconds_remaining <= 0:
            self._lockout_timer.stop()
            self.btn_signin.setEnabled(True)
            self.txt_username.setEnabled(True)
            self.txt_password.setEnabled(True)
            self.lbl_signin_error.setText("Lockout period expired. You may try signing in again.")
        else:
            self.lbl_signin_error.setText(
                f"Too many failed attempts. Account locked. Try again in {self._lockout_seconds_remaining}s."
            )

    def _handle_create_admin(self):
        full_name = self.txt_admin_name.text().strip()
        username = self.txt_admin_user.text().strip()
        email = self.txt_admin_email.text().strip()
        password = self.txt_admin_pass.text()
        confirm = self.txt_admin_confirm.text()

        self.lbl_admin_error.setVisible(False)

        if not full_name or not username or not email or not password:
            self.lbl_admin_error.setText("All fields are required.")
            self.lbl_admin_error.setVisible(True)
            return

        if len(password) < 6:
            self.lbl_admin_error.setText("Password must be at least 6 characters.")
            self.lbl_admin_error.setVisible(True)
            return

        if password != confirm:
            self.lbl_admin_error.setText("Passwords do not match.")
            self.lbl_admin_error.setVisible(True)
            return

        user_id = create_user(
            username=username,
            email=email,
            full_name=full_name,
            password=password,
            role="Admin",
        )

        if user_id:
            logger.info(f"Initial Administrator account '{username}' created successfully.")
            # Automatically sign in
            success, user, _ = authenticate_user(username, password)
            if success and user:
                self.login_successful.emit(user)
            else:
                self.form_stack.setCurrentIndex(0)
                self.txt_username.setText(username)
                self.txt_password.setFocus()
        else:
            self.lbl_admin_error.setText("Failed to create admin account. Username or email may already exist.")
            self.lbl_admin_error.setVisible(True)

    def _on_forgot_password(self):
        QMessageBox.information(
            self,
            "Offline Password Recovery",
            "ScaleXPro operates 100% offline for enterprise security.\n\n"
            "To reset your password:\n"
            "1. Contact your local System Administrator.\n"
            "2. The Administrator can reset user passwords instantly from the Settings → User Management panel.",
        )

    def _handle_quick_start(self):
        """Bypasses password entry and enters offline workspace directly."""
        from app.database import get_connection, create_user, get_user_by_username
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, full_name, email, role FROM users LIMIT 1")
        row = cur.fetchone()
        conn.close()

        if row:
            user = dict(row)
        else:
            create_user(
                username="recruiter",
                password="OfflinePassword123!",
                full_name="Kashish Niranjan",
                email="kashish@scalexpro.com",
                role="Talent Operations",
            )
            u = get_user_by_username("recruiter")
            user = dict(u) if u else {
                "id": 1,
                "username": "recruiter",
                "full_name": "Kashish Niranjan",
                "email": "kashish@scalexpro.com",
                "role": "Talent Operations",
            }

        self.login_successful.emit(user)

    def _handle_quick_admin_setup(self):
        """Instantly sets up default admin and enters workspace in 1 click."""
        from app.database import create_user, authenticate_user
        username = "admin"
        password = "AdminPassword123!"
        create_user(
            username=username,
            email="admin@scalexpro.com",
            full_name="Kashish Niranjan",
            password=password,
            role="Admin",
        )
        success, user, _ = authenticate_user(username, password)
        if success and user:
            self.login_successful.emit(user)
        else:
            self._handle_quick_start()

