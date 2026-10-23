"""
ScaleXPro Settings & Branding Tab:
Matches Screen 9 on the design board:
- Company Branding Card (Logo upload + preview, Agency Name, Redaction Visual Style)
- Recruiter Profile Card (Name, Role/Designation)
- Email Server Configuration Card (SMTP Host, Port, TLS, Username, Password, Send Test Email)
- Security & Authentication Card (PBKDF2-HMAC-SHA256, 60s lockout)
- User Management Card (Admin Only: User table, Add User modal, Admin Reset Password)
- Sticky bottom "Save Changes" bar with primary orange button
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
    QFormLayout,
)
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtCore import Qt, Signal
import qtawesome as qta

from app.database import (
    get_all_settings,
    set_setting,
    get_all_users,
    create_user,
    admin_reset_password,
    delete_user,
)
from app.security import store_password, get_password, hash_password
from app.email_service import test_smtp_connection
from app.config import ASSETS_DIR
from app.ui.widgets import CardWidget
from app.ui.animations import set_animations_enabled, is_animations_enabled
from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_TINT,
    COLOR_PRIMARY_BORDER,
    COLOR_CTA,
    COLOR_CTA_HOVER,
    COLOR_CTA_PRESSED,
    COLOR_LAVENDER,
    COLOR_PURPLE_DARK,
    COLOR_PURPLE_DEEP,
    COLOR_SUCCESS,
    COLOR_SUCCESS_TINT,
    COLOR_SUCCESS_BORDER,
    COLOR_DANGER,
    COLOR_DANGER_TINT,
    COLOR_DANGER_BORDER,
    COLOR_NAVY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
)
from app.logger import logger


def _create_helper_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: 400;")
    lbl.setWordWrap(True)
    return lbl


def _create_field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 600; font-size: 12px;")
    return lbl


class AddUserDialog(QDialog):
    """Modal dialog for creating a new local team member."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Team Member")
        self.setFixedWidth(440)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 14px;
            }}
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-weight: 600;
                font-size: 12px;
            }}
            QLineEdit, QComboBox {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                color: {COLOR_NAVY};
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl_h = QLabel("Add Local User")
        lbl_h.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 18px; font-weight: 700;")
        title_box.addWidget(lbl_h)

        lbl_s = QLabel("Create credentials for offline team member login.")
        lbl_s.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        title_box.addWidget(lbl_s)
        layout.addLayout(title_box)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. recruiter1")

        self.txt_fullname = QLineEdit()
        self.txt_fullname.setPlaceholderText("e.g. Sarah Jenkins")

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("e.g. sarah@scalexpro.com")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Minimum 4 characters")

        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["Recruiter", "Admin"])

        form.addRow("Username *:", self.txt_username)
        form.addRow("Full Name *:", self.txt_fullname)
        form.addRow("Email Address:", self.txt_email)
        form.addRow("Password *:", self.txt_password)
        form.addRow("Role:", self.cmb_role)

        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_add = QPushButton("Create User")
        btn_add.setFixedHeight(36)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        btn_add.clicked.connect(self._on_submit)
        btns.addWidget(btn_add)

        layout.addLayout(btns)

    def _on_submit(self):
        u = self.txt_username.text().strip()
        fn = self.txt_fullname.text().strip()
        pwd = self.txt_password.text().strip()
        if not u:
            QMessageBox.warning(self, "Validation", "Username cannot be empty.")
            return
        if not fn:
            QMessageBox.warning(self, "Validation", "Full name cannot be empty.")
            return
        if len(pwd) < 4:
            QMessageBox.warning(self, "Validation", "Password must be at least 4 characters.")
            return

        ok, msg = create_user(
            username=u,
            password=pwd,
            full_name=fn,
            email=self.txt_email.text().strip(),
            role=self.cmb_role.currentText(),
        )
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", msg)


class ResetPasswordDialog(QDialog):
    """Admin modal dialog to reset another user's password locally."""
    def __init__(self, username: str, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle(f"Reset Password - {username}")
        self.setFixedWidth(400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 14px;
            }}
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-weight: 600;
                font-size: 12px;
            }}
            QLineEdit {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                color: {COLOR_NAVY};
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        lbl_head = QLabel(f"Reset Password: {username}")
        lbl_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 17px; font-weight: 700;")
        layout.addWidget(lbl_head)

        lbl_sub = QLabel("Set a new offline password for this user account.")
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(lbl_sub)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_new_pwd = QLineEdit()
        self.txt_new_pwd.setEchoMode(QLineEdit.Password)
        self.txt_new_pwd.setPlaceholderText("Enter new password")

        self.txt_confirm_pwd = QLineEdit()
        self.txt_confirm_pwd.setEchoMode(QLineEdit.Password)
        self.txt_confirm_pwd.setPlaceholderText("Confirm new password")

        form.addRow("New Password *:", self.txt_new_pwd)
        form.addRow("Confirm *:", self.txt_confirm_pwd)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch()

        btn_c = QPushButton("Cancel")
        btn_c.setFixedHeight(36)
        btn_c.setCursor(Qt.PointingHandCursor)
        btn_c.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
            }}
        """)
        btn_c.clicked.connect(self.reject)
        btns.addWidget(btn_c)

        btn_res = QPushButton("Reset Password")
        btn_res.setFixedHeight(36)
        btn_res.setCursor(Qt.PointingHandCursor)
        btn_res.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        btn_res.clicked.connect(self._on_reset)
        btns.addWidget(btn_res)

        layout.addLayout(btns)

    def _on_reset(self):
        p1 = self.txt_new_pwd.text()
        p2 = self.txt_confirm_pwd.text()
        if len(p1) < 4:
            QMessageBox.warning(self, "Validation", "Password must be at least 4 characters.")
            return
        if p1 != p2:
            QMessageBox.warning(self, "Validation", "Passwords do not match.")
            return

        ok, msg = admin_reset_password(self.user_id, p1)
        if ok:
            QMessageBox.information(self, "Success", "Password updated successfully.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", msg)


class SettingsTab(QWidget):
    """Configuration interface for Branding, SMTP, Recruiter Profile, Security, and User Management."""
    settings_saved_signal = Signal()
    show_toast_signal = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user: Optional[Dict[str, Any]] = None
        self._setup_ui()
        self.load_settings()
        self.refresh_users()

    def set_current_user(self, user_dict: Optional[Dict[str, Any]]):
        self.current_user = user_dict
        if user_dict:
            is_admin = user_dict.get("role") == "Admin"
            self.user_mgmt_card.setVisible(is_admin)
            self.recruiter_name_edit.setText(user_dict.get("full_name", ""))

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background-color: #F1F5F9; border: none; }")

        container = QWidget()
        container.setObjectName("settingsContainer")
        container.setStyleSheet("#settingsContainer { background-color: #F1F5F9; }")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        # -----------------------------------------------------------------
        # Header Title
        # -----------------------------------------------------------------
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_title = QLabel("System Settings & Branding")
        lbl_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 22px; font-weight: 700; letter-spacing: -0.3px;")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Configure your ScaleXPro agency branding, recruiter details, offline access, and SMTP delivery.")
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px; line-height: 18px;")
        title_col.addWidget(lbl_sub)
        layout.addLayout(title_col)

        # -----------------------------------------------------------------
        # 1. Company Branding & Logo Card
        # -----------------------------------------------------------------
        brand_card = CardWidget(radius=20)
        brand_layout = QVBoxLayout(brand_card)
        brand_layout.setContentsMargins(24, 22, 24, 22)
        brand_layout.setSpacing(16)

        brand_head_row = QHBoxLayout()
        brand_icon = QLabel()
        brand_icon.setPixmap(qta.icon("fa5s.paint-brush", color=COLOR_PRIMARY).pixmap(20, 20))
        brand_head_row.addWidget(brand_icon)

        brand_title_box = QVBoxLayout()
        brand_title_box.setSpacing(2)
        lbl_b_head = QLabel("Company Branding & Logo")
        lbl_b_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        brand_title_box.addWidget(lbl_b_head)
        brand_title_sub = QLabel("This logo is automatically placed on every redacted candidate CV across all pages.")
        brand_title_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        brand_title_box.addWidget(brand_title_sub)
        brand_head_row.addLayout(brand_title_box)
        brand_head_row.addStretch()
        brand_layout.addLayout(brand_head_row)

        b_grid = QGridLayout()
        b_grid.setHorizontalSpacing(16)
        b_grid.setVerticalSpacing(14)

        # Agency Name
        b_grid.addWidget(_create_field_label("Agency Name"), 0, 0)
        cname_box = QVBoxLayout()
        cname_box.setSpacing(4)
        self.company_name_edit = QLineEdit()
        self.company_name_edit.setPlaceholderText("e.g. ScaleXPro")
        cname_box.addWidget(self.company_name_edit)
        cname_box.addWidget(_create_helper_label("Displayed in email dispatches, reports, and generated headers."))
        b_grid.addLayout(cname_box, 0, 1, 1, 2)

        # Logo Path & Upload
        b_grid.addWidget(_create_field_label("Company Logo"), 1, 0)
        logo_box = QVBoxLayout()
        logo_box.setSpacing(4)
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        self.logo_path_edit = QLineEdit()
        self.logo_path_edit.setReadOnly(True)
        self.logo_path_edit.setPlaceholderText("Logo file path...")
        logo_row.addWidget(self.logo_path_edit, 1)

        self.btn_upload_logo = QPushButton(" Change Logo")
        self.btn_upload_logo.setIcon(qta.icon("fa5s.image", color=COLOR_PRIMARY))
        self.btn_upload_logo.setCursor(Qt.PointingHandCursor)
        self.btn_upload_logo.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_TINT};
                color: {COLOR_PRIMARY};
                border: 1px solid {COLOR_PRIMARY_BORDER};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #FED7AA;
            }}
        """)
        self.btn_upload_logo.clicked.connect(self._upload_logo)
        logo_row.addWidget(self.btn_upload_logo)
        logo_box.addLayout(logo_row)
        logo_box.addWidget(_create_helper_label("Recommended: Transparent PNG (approx. 400-800px width). Saved offline in data/assets/."))
        b_grid.addLayout(logo_box, 1, 1, 1, 2)

        # Logo Preview Box
        b_grid.addWidget(_create_field_label("Logo Preview"), 2, 0)
        preview_box = QVBoxLayout()
        preview_box.setSpacing(4)
        self.logo_preview = QLabel("No Logo Selected")
        self.logo_preview.setFixedSize(260, 68)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setStyleSheet(f"""
            QLabel {{
                background-color: #F8FAFC;
                border: 1.5px dashed {COLOR_BORDER};
                border-radius: 10px;
                color: {COLOR_TEXT_MUTED};
                font-size: 11px;
                font-weight: 500;
                padding: 6px;
            }}
        """)
        preview_box.addWidget(self.logo_preview)
        preview_box.addWidget(_create_helper_label("Adaptive placement fits this logo gracefully without obscuring candidate content."))
        b_grid.addLayout(preview_box, 2, 1, 1, 2)

        # Redaction visual style
        b_grid.addWidget(_create_field_label("Redaction Visual Style"), 3, 0)
        style_box = QVBoxLayout()
        style_box.setSpacing(4)
        self.color_combo = QComboBox()
        self.color_combo.addItem("Clean Whiteout (Invisible / Seamless)", "white")
        self.color_combo.addItem("Blackout Bar (Visible Solid Blocks)", "black")
        style_box.addWidget(self.color_combo)
        style_box.addWidget(_create_helper_label("Whiteout produces clean, agency-ready CVs. Blackout clearly signals redactions were made."))
        b_grid.addLayout(style_box, 3, 1, 1, 2)

        brand_layout.addLayout(b_grid)
        layout.addWidget(brand_card)

        # -------------------------------------------------------------
        # 2. Recruiter Profile Card
        # -------------------------------------------------------------
        prof_card = CardWidget(radius=20)
        prof_layout = QVBoxLayout(prof_card)
        prof_layout.setContentsMargins(24, 22, 24, 22)
        prof_layout.setSpacing(16)

        prof_head_row = QHBoxLayout()
        prof_icon = QLabel()
        prof_icon.setPixmap(qta.icon("fa5s.user-tie", color=COLOR_PRIMARY).pixmap(20, 20))
        prof_head_row.addWidget(prof_icon)

        prof_title_box = QVBoxLayout()
        prof_title_box.setSpacing(2)
        lbl_p_head = QLabel("Recruiter Profile")
        lbl_p_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        prof_title_box.addWidget(lbl_p_head)
        prof_title_sub = QLabel("Used in email templates and client communications.")
        prof_title_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        prof_title_box.addWidget(prof_title_sub)
        prof_head_row.addLayout(prof_title_box)
        prof_head_row.addStretch()
        prof_layout.addLayout(prof_head_row)

        p_grid = QGridLayout()
        p_grid.setHorizontalSpacing(16)
        p_grid.setVerticalSpacing(14)

        p_grid.addWidget(_create_field_label("Full Name"), 0, 0)
        rname_box = QVBoxLayout()
        rname_box.setSpacing(4)
        self.recruiter_name_edit = QLineEdit()
        self.recruiter_name_edit.setPlaceholderText("e.g. Kashish Niranjan")
        rname_box.addWidget(self.recruiter_name_edit)
        rname_box.addWidget(_create_helper_label("Your personal recruiter sign-off name."))
        p_grid.addLayout(rname_box, 0, 1)

        p_grid.addWidget(_create_field_label("Role / Title"), 0, 2)
        rrole_box = QVBoxLayout()
        rrole_box.setSpacing(4)
        self.recruiter_role_edit = QLineEdit()
        self.recruiter_role_edit.setPlaceholderText("e.g. Talent Operations Lead")
        rrole_box.addWidget(self.recruiter_role_edit)
        rrole_box.addWidget(_create_helper_label("Your professional job title at ScaleXPro."))
        p_grid.addLayout(rrole_box, 0, 3)

        prof_layout.addLayout(p_grid)
        layout.addWidget(prof_card)

        # -------------------------------------------------------------
        # 3. SMTP Email Configuration Card
        # -------------------------------------------------------------
        smtp_card = CardWidget(radius=20)
        smtp_layout = QVBoxLayout(smtp_card)
        smtp_layout.setContentsMargins(24, 22, 24, 22)
        smtp_layout.setSpacing(16)

        smtp_head_row = QHBoxLayout()
        smtp_icon = QLabel()
        smtp_icon.setPixmap(qta.icon("fa5s.envelope", color=COLOR_PRIMARY).pixmap(20, 20))
        smtp_head_row.addWidget(smtp_icon)

        smtp_title_box = QVBoxLayout()
        smtp_title_box.setSpacing(2)
        lbl_s_head = QLabel("Email Server Configuration (SMTP)")
        lbl_s_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        smtp_title_box.addWidget(lbl_s_head)
        smtp_title_sub = QLabel("ScaleXPro connects directly to your corporate mail server. Passwords saved with Windows DPAPI.")
        smtp_title_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        smtp_title_box.addWidget(smtp_title_sub)
        smtp_head_row.addLayout(smtp_title_box)
        smtp_head_row.addStretch()
        smtp_layout.addLayout(smtp_head_row)

        s_grid = QGridLayout()
        s_grid.setHorizontalSpacing(16)
        s_grid.setVerticalSpacing(14)

        s_grid.addWidget(_create_field_label("SMTP Host"), 0, 0)
        host_box = QVBoxLayout()
        host_box.setSpacing(4)
        self.smtp_host_edit = QLineEdit()
        self.smtp_host_edit.setPlaceholderText("smtp.gmail.com")
        host_box.addWidget(self.smtp_host_edit)
        host_box.addWidget(_create_helper_label("e.g. smtp.gmail.com, smtp.office365.com, or mail.company.com"))
        s_grid.addLayout(host_box, 0, 1)

        s_grid.addWidget(_create_field_label("Port"), 0, 2)
        port_box = QVBoxLayout()
        port_box.setSpacing(4)
        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        self.smtp_port_spin.setValue(587)
        port_box.addWidget(self.smtp_port_spin)
        port_box.addWidget(_create_helper_label("Usually 587 for STARTTLS or 465 for SSL."))
        s_grid.addLayout(port_box, 0, 3)

        self.smtp_tls_check = QCheckBox("Use STARTTLS (Encrypted transmission)")
        self.smtp_tls_check.setChecked(True)
        self.smtp_tls_check.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 500; font-size: 13px;")
        s_grid.addWidget(self.smtp_tls_check, 1, 1, 1, 3)

        s_grid.addWidget(_create_field_label("SMTP Username"), 2, 0)
        user_box = QVBoxLayout()
        user_box.setSpacing(4)
        self.smtp_user_edit = QLineEdit()
        self.smtp_user_edit.setPlaceholderText("your-agency-email@gmail.com")
        user_box.addWidget(self.smtp_user_edit)
        user_box.addWidget(_create_helper_label("The full email address of your dispatch mailbox."))
        s_grid.addLayout(user_box, 2, 1, 1, 3)

        s_grid.addWidget(_create_field_label("App Password"), 3, 0)
        pwd_box = QVBoxLayout()
        pwd_box.setSpacing(4)
        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(8)
        self.smtp_pwd_edit = QLineEdit()
        self.smtp_pwd_edit.setEchoMode(QLineEdit.Password)
        self.smtp_pwd_edit.setPlaceholderText("16-character App Password (saved securely)")
        pwd_row.addWidget(self.smtp_pwd_edit, 1)

        self.btn_toggle_pwd = QPushButton("Show")
        self.btn_toggle_pwd.setFixedWidth(64)
        self.btn_toggle_pwd.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_pwd.setStyleSheet(f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 7px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #EEF2F6;
                color: {COLOR_NAVY};
            }}
        """)
        self.btn_toggle_pwd.clicked.connect(self._toggle_password_visibility)
        pwd_row.addWidget(self.btn_toggle_pwd)
        pwd_box.addLayout(pwd_row)
        pwd_box.addWidget(_create_helper_label("For Gmail / Outlook, generate a dedicated 16-character App Password."))
        s_grid.addLayout(pwd_box, 3, 1, 1, 3)

        smtp_layout.addLayout(s_grid)

        test_row = QHBoxLayout()
        test_row.setSpacing(14)

        self.btn_test_smtp = QPushButton(" Send Test Email")
        self.btn_test_smtp.setIcon(qta.icon("fa5s.paper-plane", color=COLOR_PRIMARY))
        self.btn_test_smtp.setCursor(Qt.PointingHandCursor)
        self.btn_test_smtp.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_TINT};
                color: {COLOR_PRIMARY};
                border: 1px solid {COLOR_PRIMARY_BORDER};
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #FED7AA;
            }}
        """)
        self.btn_test_smtp.clicked.connect(self._test_connection)
        test_row.addWidget(self.btn_test_smtp)

        self.smtp_status_label = QLabel("")
        self.smtp_status_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        test_row.addWidget(self.smtp_status_label)
        test_row.addStretch()

        smtp_layout.addLayout(test_row)
        layout.addWidget(smtp_card)

        # -------------------------------------------------------------
        # 4. User Management Card (Admin Only)
        # -------------------------------------------------------------
        self.user_mgmt_card = CardWidget(radius=20)
        um_layout = QVBoxLayout(self.user_mgmt_card)
        um_layout.setContentsMargins(24, 22, 24, 22)
        um_layout.setSpacing(16)

        um_head_row = QHBoxLayout()
        um_icon = QLabel()
        um_icon.setPixmap(qta.icon("fa5s.users-cog", color=COLOR_PRIMARY).pixmap(20, 20))
        um_head_row.addWidget(um_icon)

        um_title_box = QVBoxLayout()
        um_title_box.setSpacing(2)
        lbl_u_head = QLabel("User Management (Admin Only)")
        lbl_u_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        um_title_box.addWidget(lbl_u_head)
        lbl_u_sub = QLabel("Manage offline local recruiter accounts and role privileges. Hashed with PBKDF2-HMAC-SHA256.")
        lbl_u_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        um_title_box.addWidget(lbl_u_sub)
        um_head_row.addLayout(um_title_box)
        um_head_row.addStretch()

        btn_add_user = QPushButton(" + Add User")
        btn_add_user.setCursor(Qt.PointingHandCursor)
        btn_add_user.setFixedHeight(34)
        btn_add_user.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        btn_add_user.clicked.connect(self._on_add_user)
        um_head_row.addWidget(btn_add_user)

        um_layout.addLayout(um_head_row)

        # User Table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels([
            "Username",
            "Full Name",
            "Email",
            "Role",
            "Actions",
        ])
        u_hdr = self.user_table.horizontalHeader()
        u_hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        u_hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        u_hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        u_hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        self.user_table.setColumnWidth(3, 110)
        u_hdr.setSectionResizeMode(4, QHeaderView.Fixed)
        self.user_table.setColumnWidth(4, 190)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.setShowGrid(False)
        self.user_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: #F8FAFC;
                color: {COLOR_TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
                border: none;
                border-bottom: 1px solid {COLOR_BORDER};
                padding: 8px 12px;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
        """)
        um_layout.addWidget(self.user_table)
        layout.addWidget(self.user_mgmt_card)

        # -------------------------------------------------------------
        # 5. Active Privacy & Redaction Rules Card
        # -------------------------------------------------------------
        rules_card = CardWidget(radius=20)
        rules_layout = QVBoxLayout(rules_card)
        rules_layout.setContentsMargins(24, 22, 24, 22)
        rules_layout.setSpacing(16)

        rules_head_row = QHBoxLayout()
        rules_icon = QLabel()
        rules_icon.setPixmap(qta.icon("fa5s.shield-alt", color=COLOR_SUCCESS).pixmap(20, 20))
        rules_head_row.addWidget(rules_icon)

        rules_title_box = QVBoxLayout()
        rules_title_box.setSpacing(2)
        lbl_r_head = QLabel("Active Privacy & Redaction Rules")
        lbl_r_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        rules_title_box.addWidget(lbl_r_head)
        rules_title_sub = QLabel("Processed 100% offline with PyMuPDF. Redacted characters are permanently destroyed.")
        rules_title_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        rules_title_box.addWidget(rules_title_sub)
        rules_head_row.addLayout(rules_title_box)
        rules_head_row.addStretch()
        rules_layout.addLayout(rules_head_row)

        rg = QGridLayout()
        rg.setHorizontalSpacing(24)
        rg.setVerticalSpacing(14)

        self.check_email = QCheckBox("Permanently remove Email addresses")
        self.check_phone = QCheckBox("Permanently remove Phone numbers (Indian +91, 10-digit, STD, Intl)")
        self.check_urls = QCheckBox("Permanently remove LinkedIn, GitHub, and Portfolio URLs")
        self.check_address = QCheckBox("Permanently remove Street Addresses and PIN codes")
        self.check_metadata = QCheckBox("Strip PDF metadata (Author, Title, Producer, Timestamps)")

        for cb in (self.check_email, self.check_phone, self.check_urls, self.check_address, self.check_metadata):
            cb.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13px; font-weight: 500;")

        rg.addWidget(self.check_email, 0, 0)
        rg.addWidget(self.check_phone, 0, 1)
        rg.addWidget(self.check_urls, 1, 0)
        rg.addWidget(self.check_address, 1, 1)
        rg.addWidget(self.check_metadata, 2, 0, 1, 2)

        rules_layout.addLayout(rg)
        layout.addWidget(rules_card)

        # -------------------------------------------------------------
        # 6. Appearance & Performance Card (Reduce Animations)
        # -------------------------------------------------------------
        perf_card = CardWidget(radius=20)
        perf_layout = QVBoxLayout(perf_card)
        perf_layout.setContentsMargins(24, 22, 24, 22)
        perf_layout.setSpacing(14)

        perf_head_row = QHBoxLayout()
        perf_icon = QLabel()
        perf_icon.setPixmap(qta.icon("fa5s.magic", color=COLOR_PRIMARY).pixmap(20, 20))
        perf_head_row.addWidget(perf_icon)

        perf_title_box = QVBoxLayout()
        perf_title_box.setSpacing(2)
        lbl_perf_head = QLabel("Appearance & Performance")
        lbl_perf_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 16px; font-weight: 700;")
        perf_title_box.addWidget(lbl_perf_head)
        lbl_perf_sub = QLabel("Configure dashboard motion, visual transitions, and hardware optimization.")
        lbl_perf_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        perf_title_box.addWidget(lbl_perf_sub)
        perf_head_row.addLayout(perf_title_box)
        perf_head_row.addStretch()
        perf_layout.addLayout(perf_head_row)

        self.check_reduce_animations = QCheckBox("Reduce animations (disables sliding transitions, confetti, and counter effects for low-power PCs)")
        self.check_reduce_animations.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13px; font-weight: 500;")
        self.check_reduce_animations.toggled.connect(lambda checked: set_animations_enabled(not checked))
        perf_layout.addWidget(self.check_reduce_animations)
        layout.addWidget(perf_card)

        self.scroll.setWidget(container)
        main_layout.addWidget(self.scroll)

        # -------------------------------------------------------------
        # 7. Sticky Bottom "Save Changes" Bar
        # -------------------------------------------------------------
        bottom_bar = QFrame()
        bottom_bar.setObjectName("settingsBottomBar")
        bottom_bar.setStyleSheet(f"""
            #settingsBottomBar {{
                background-color: #FFFFFF;
                border-top: 1px solid #E8E5F7;
            }}
        """)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(28, 14, 28, 14)

        self.save_feedback_label = QLabel("")
        self.save_feedback_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-weight: 600; font-size: 13px;")
        bottom_layout.addWidget(self.save_feedback_label)
        bottom_layout.addStretch()

        self.btn_save = QPushButton(" Save Changes")
        self.btn_save.setIcon(qta.icon("fa5s.check", color="#FFFFFF"))
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setToolTip("Save company branding, SMTP connection, and performance preferences")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 11px 32px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CTA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_CTA_PRESSED};
            }}
        """)
        self.btn_save.clicked.connect(self.save_settings)
        bottom_layout.addWidget(self.btn_save)

        main_layout.addWidget(bottom_bar)

    def refresh_users(self):
        users = get_all_users()
        self.user_table.setRowCount(len(users))
        for row_idx, u in enumerate(users):
            self.user_table.setRowHeight(row_idx, 42)

            # 0: Username
            u_item = QTableWidgetItem(u.get("username", ""))
            u_item.setForeground(QColor(COLOR_NAVY))
            self.user_table.setItem(row_idx, 0, u_item)

            # 1: Full name
            f_item = QTableWidgetItem(u.get("full_name", ""))
            f_item.setForeground(QColor(COLOR_TEXT_PRIMARY))
            self.user_table.setItem(row_idx, 1, f_item)

            # 2: Email
            e_item = QTableWidgetItem(u.get("email", ""))
            e_item.setForeground(QColor(COLOR_TEXT_MUTED))
            self.user_table.setItem(row_idx, 2, e_item)

            # 3: Role pill
            role_str = u.get("role", "Recruiter")
            role_w = QWidget()
            rw_l = QHBoxLayout(role_w)
            rw_l.setContentsMargins(4, 4, 4, 4)
            rw_l.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            r_pill = QLabel(f" {role_str} ")
            if role_str == "Admin":
                r_pill.setStyleSheet(f"""
                    background-color: {COLOR_PRIMARY_TINT};
                    color: {COLOR_PRIMARY};
                    border: 1px solid {COLOR_PRIMARY_BORDER};
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 2px 6px;
                """)
            else:
                r_pill.setStyleSheet("""
                    background-color: #EFF6FF;
                    color: #2563EB;
                    border: 1px solid #BFDBFE;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 6px;
                """)
            rw_l.addWidget(r_pill)
            self.user_table.setCellWidget(row_idx, 3, role_w)

            # 4: Action buttons
            act_w = QWidget()
            aw_l = QHBoxLayout(act_w)
            aw_l.setContentsMargins(4, 2, 4, 2)
            aw_l.setSpacing(6)

            btn_reset = QPushButton("Reset Pwd")
            btn_reset.setCursor(Qt.PointingHandCursor)
            btn_reset.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #F8FAFC;
                    border-color: {COLOR_PRIMARY};
                }}
            """)
            btn_reset.clicked.connect(lambda ch=False, uid=u["id"], un=u["username"]: self._on_reset_user_pwd(uid, un))
            aw_l.addWidget(btn_reset)

            btn_del = QPushButton("Delete")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_DANGER_TINT};
                    color: {COLOR_DANGER};
                    border: 1px solid {COLOR_DANGER_BORDER};
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #FEE2E2;
                }}
            """)
            btn_del.clicked.connect(lambda ch=False, uid=u["id"], un=u["username"]: self._on_delete_user(uid, un))
            aw_l.addWidget(btn_del)

            self.user_table.setCellWidget(row_idx, 4, act_w)

    def _on_add_user(self):
        dlg = AddUserDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_users()
            self.show_toast_signal.emit("New user account created.", "success", "User Added")

    def _on_reset_user_pwd(self, user_id: int, username: str):
        dlg = ResetPasswordDialog(username, user_id, self)
        if dlg.exec() == QDialog.Accepted:
            self.show_toast_signal.emit(f"Password reset for {username}.", "success", "Password Reset")

    def _on_delete_user(self, user_id: int, username: str):
        if self.current_user and self.current_user.get("id") == user_id:
            QMessageBox.warning(self, "Action Prohibited", "You cannot delete your own logged-in account.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete user '{username}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok, msg = delete_user(user_id)
            if ok:
                self.refresh_users()
                self.show_toast_signal.emit(f"User '{username}' deleted.", "info", "User Removed")
            else:
                QMessageBox.critical(self, "Error", msg)

    def _upload_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Upload Company Logo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_path:
            ASSETS_DIR.mkdir(parents=True, exist_ok=True)
            dest_filename = Path(file_path).name
            dest_path = str(ASSETS_DIR / dest_filename)
            try:
                shutil.copy2(file_path, dest_path)
                self.logo_path_edit.setText(dest_path)
                self._update_logo_preview(dest_path)
                set_setting("logo_path", dest_path)
                self.show_toast_signal.emit("Logo uploaded and saved successfully.", "success", "Branding Updated")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save logo: {e}")

    def _update_logo_preview(self, path: str):
        if path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                scaled = pix.scaled(240, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_preview.setPixmap(scaled)
                return
        self.logo_preview.clear()
        self.logo_preview.setText("No Logo Selected")

    def _toggle_password_visibility(self):
        if self.smtp_pwd_edit.echoMode() == QLineEdit.Password:
            self.smtp_pwd_edit.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_pwd.setText("Hide")
        else:
            self.smtp_pwd_edit.setEchoMode(QLineEdit.Password)
            self.btn_toggle_pwd.setText("Show")

    def _test_connection(self):
        host = self.smtp_host_edit.text().strip()
        port = self.smtp_port_spin.value()
        tls = self.smtp_tls_check.isChecked()
        user = self.smtp_user_edit.text().strip()
        pwd = self.smtp_pwd_edit.text().strip()

        if not host or not user or not pwd:
            self.smtp_status_label.setText("Please fill Host, Username, and Password first.")
            self.smtp_status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: 600; font-size: 12px;")
            return

        self.btn_test_smtp.setEnabled(False)
        self.smtp_status_label.setText("Testing SMTP connection...")
        self.smtp_status_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: 600; font-size: 12px;")

        success, msg = test_smtp_connection(host, port, user, pwd, tls)
        self.btn_test_smtp.setEnabled(True)

        if success:
            self.smtp_status_label.setText(f"✓ {msg}")
            self.smtp_status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-weight: 700; font-size: 12px;")
            self.show_toast_signal.emit(msg, "success", "SMTP Verified")
        else:
            self.smtp_status_label.setText(f"✗ {msg}")
            self.smtp_status_label.setStyleSheet(f"color: {COLOR_DANGER}; font-weight: 600; font-size: 12px;")
            self.show_toast_signal.emit(msg, "error", "SMTP Failed")

    def load_settings(self):
        s = get_all_settings()

        self.recruiter_name_edit.setText(s.get("recruiter_name", "Kashish Niranjan"))
        self.recruiter_role_edit.setText(s.get("recruiter_role", "Talent Operations"))
        self.company_name_edit.setText(s.get("company_name", "ScaleXPro"))

        logo_path = s.get("logo_path", "")
        if not logo_path or not os.path.exists(logo_path):
            default_logo = str(ASSETS_DIR / "scalexpro_logo.png")
            if os.path.exists(default_logo):
                logo_path = default_logo

        self.logo_path_edit.setText(logo_path)
        self._update_logo_preview(logo_path)

        color = s.get("redaction_color", "white")
        idx = self.color_combo.findData(color)
        if idx >= 0:
            self.color_combo.setCurrentIndex(idx)

        self.smtp_host_edit.setText(s.get("smtp_host", "smtp.gmail.com"))
        self.smtp_port_spin.setValue(s.get("smtp_port", 587))
        self.smtp_tls_check.setChecked(s.get("smtp_use_tls", True))
        self.smtp_user_edit.setText(s.get("smtp_username", ""))

        user = s.get("smtp_username", "") or "smtp_credentials"
        saved_pwd = get_password(user)
        if saved_pwd:
            self.smtp_pwd_edit.setText(saved_pwd)

        self.check_email.setChecked(s.get("redact_email", True))
        self.check_phone.setChecked(s.get("redact_phone", True))
        self.check_urls.setChecked(s.get("redact_urls", True))
        self.check_address.setChecked(s.get("redact_address", True))
        self.check_metadata.setChecked(s.get("redact_metadata", True))

        reduce_anim = bool(s.get("reduce_animations", False))
        self.check_reduce_animations.setChecked(reduce_anim)
        set_animations_enabled(not reduce_anim)

    def save_settings(self):
        set_setting("recruiter_name", self.recruiter_name_edit.text().strip())
        set_setting("recruiter_role", self.recruiter_role_edit.text().strip())
        set_setting("company_name", self.company_name_edit.text().strip())
        set_setting("logo_path", self.logo_path_edit.text().strip())
        set_setting("redaction_color", self.color_combo.currentData())

        set_setting("smtp_host", self.smtp_host_edit.text().strip())
        set_setting("smtp_port", self.smtp_port_spin.value())
        set_setting("smtp_use_tls", self.smtp_tls_check.isChecked())
        set_setting("smtp_username", self.smtp_user_edit.text().strip())

        pwd = self.smtp_pwd_edit.text().strip()
        if pwd:
            user = self.smtp_user_edit.text().strip() or "smtp_credentials"
            store_password(user, pwd)

        set_setting("redact_email", self.check_email.isChecked())
        set_setting("redact_phone", self.check_phone.isChecked())
        set_setting("redact_urls", self.check_urls.isChecked())
        set_setting("redact_address", self.check_address.isChecked())
        set_setting("redact_metadata", self.check_metadata.isChecked())

        reduce_anim = self.check_reduce_animations.isChecked()
        set_setting("reduce_animations", reduce_anim)
        set_animations_enabled(not reduce_anim)

        self.save_feedback_label.setText("✓ Settings saved successfully.")
        self.show_toast_signal.emit("Settings and branding saved successfully.", "success", "Saved")
        self.settings_saved_signal.emit()
