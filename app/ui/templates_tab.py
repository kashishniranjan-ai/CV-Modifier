"""
Templates Tab for ScaleXPro CV-Modifier:
Matches Screen 8 on the design board (3-column layout):
- Left column (~240px): Template list + "+ New Template"
- Middle column (stretch): Subject & Body editor with clickable token chips
- Right column (~340px): Live simulated email preview card
"""

from typing import Dict, Tuple
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFrame,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
import qtawesome as qta

from app.database import get_setting, set_setting
from app.ui.widgets import CardWidget
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
    COLOR_NAVY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
)


class TemplatesTab(QWidget):
    """Screen 8: 3-column Email Templates Editor matching the design board."""
    show_toast_signal = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_template_idx = 0
        self.templates_data = [
            {
                "name": "Standard Dispatch",
                "desc": "Default candidate profile dispatch for client submissions",
                "subject": "Candidate Profile: {candidate_id} - {role}",
                "body": (
                    "Dear {client_name},\n\n"
                    "Please find attached the anonymized and branded profile for candidate {candidate_id} ({role}) for your review.\n\n"
                    "Key candidate highlights and competencies are detailed in the attached document.\n\n"
                    "Best regards,\n"
                    "Recruitment Team\n"
                    "{company_name}"
                ),
            },
            {
                "name": "Executive Shortlist",
                "desc": "Senior leadership & executive level profile presentation",
                "subject": "Executive Shortlist: {candidate_id} ({role}) - {company_name}",
                "body": (
                    "Dear {client_name},\n\n"
                    "We are pleased to present candidate {candidate_id} for the {role} leadership position.\n\n"
                    "This candidate brings extensive leadership pedigree, track record, and verified credentials.\n\n"
                    "Warm regards,\n"
                    "Executive Search Group\n"
                    "{company_name}"
                ),
            },
            {
                "name": "Urgent Candidate",
                "desc": "High-priority immediate requirement profile dispatch",
                "subject": "Priority Candidate: {candidate_id} - {role} (Available Immediately)",
                "body": (
                    "Hi {client_name},\n\n"
                    "Sharing an immediate candidate profile {candidate_id} matching your urgent requirements for {role}.\n\n"
                    "Candidate is fully vetted and available for immediate interviews.\n\n"
                    "Thanks,\n"
                    "Talent Partner\n"
                    "{company_name}"
                ),
            },
        ]
        self._setup_ui()
        self.load_templates()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl_title = QLabel("Email Templates")
        lbl_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 700;")
        title_box.addWidget(lbl_title)

        lbl_sub = QLabel("Customize candidate dispatch email templates and dynamic personalized merge tokens.")
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")
        title_box.addWidget(lbl_sub)
        root_layout.addLayout(title_box)

        # 3-Column Split Row
        content_row = QHBoxLayout()
        content_row.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Left Column: Template List (~240px)
        # -------------------------------------------------------------
        col_list = CardWidget(radius=20)
        col_list.setFixedWidth(250)
        cl_layout = QVBoxLayout(col_list)
        cl_layout.setContentsMargins(18, 18, 18, 18)
        cl_layout.setSpacing(12)

        cl_head = QHBoxLayout()
        lbl_t_list = QLabel("Templates")
        lbl_t_list.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 14px; font-weight: 700;")
        cl_head.addWidget(lbl_t_list)

        btn_new_t = QPushButton("+ New")
        btn_new_t.setCursor(Qt.PointingHandCursor)
        btn_new_t.setStyleSheet(f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: {COLOR_PRIMARY};
                border: 1px solid #E8E5F7;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER};
            }}
        """)
        btn_new_t.clicked.connect(self._create_new_template)
        cl_head.addWidget(btn_new_t)
        cl_layout.addLayout(cl_head)

        self.list_container = QVBoxLayout()
        self.list_container.setSpacing(8)
        self.template_buttons = []

        for idx, t_data in enumerate(self.templates_data):
            btn = self._build_template_item_btn(idx, t_data["name"], t_data["desc"])
            self.list_container.addWidget(btn)
            self.template_buttons.append(btn)

        cl_layout.addLayout(self.list_container)
        cl_layout.addStretch()
        content_row.addWidget(col_list)

        # -------------------------------------------------------------
        # 2. Middle Column: Subject & Body Editor (Stretch)
        # -------------------------------------------------------------
        col_editor = CardWidget(radius=20)
        ce_layout = QVBoxLayout(col_editor)
        ce_layout.setContentsMargins(22, 20, 22, 20)
        ce_layout.setSpacing(14)

        # Subject input
        lbl_subj = QLabel("Subject Line")
        lbl_subj.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 600; font-size: 12px;")
        ce_layout.addWidget(lbl_subj)

        self.subject_edit = QLineEdit()
        self.subject_edit.setFixedHeight(38)
        self.subject_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: #FFFFFF;
                border: 1px solid #E8E5F7;
                border-radius: 10px;
                padding: 0 12px;
                font-size: 13px;
                color: {COLOR_NAVY};
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.subject_edit.textChanged.connect(self._update_live_preview)
        ce_layout.addWidget(self.subject_edit)

        # Token Insertion Chips
        tokens_box = QFrame()
        tokens_box.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border: 1px solid #E8E5F7;
                border-radius: 12px;
            }}
        """)
        tb_l = QVBoxLayout(tokens_box)
        tb_l.setContentsMargins(12, 10, 12, 10)
        tb_l.setSpacing(6)

        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        lbl_tok_title = QLabel("Insert Variable:")
        lbl_tok_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 11px;")
        hdr_row.addWidget(lbl_tok_title)
        hdr_row.addStretch()
        tb_l.addLayout(hdr_row)

        grid_tokens = QGridLayout()
        grid_tokens.setContentsMargins(0, 0, 0, 0)
        grid_tokens.setSpacing(6)

        token_list = [
            ("{client_name}", "{client_name}"),
            ("{candidate_id}", "{candidate_id}"),
            ("{role}", "{role}"),
            ("{company_name}", "{company_name}"),
            ("{candidate_name}", "{candidate_name}"),
            ("{cv_filename}", "{cv_filename}"),
        ]
        for idx, (label_text, token_str) in enumerate(token_list):
            row = idx // 2
            col = idx % 2
            t_btn = QPushButton(f"+ {label_text}")
            t_btn.setCursor(Qt.PointingHandCursor)
            t_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #E4E0FA;
                    color: {COLOR_PURPLE_DARK};
                    border: 1px solid #DDD6F7;
                    border-radius: 8px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_LAVENDER};
                }}
            """)
            t_btn.clicked.connect(lambda ch=False, tok=token_str: self._insert_token(tok))
            grid_tokens.addWidget(t_btn, row, col)

        tb_l.addLayout(grid_tokens)
        ce_layout.addWidget(tokens_box)

        # Body input
        lbl_body = QLabel("Email Body")
        lbl_body.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 600; font-size: 12px;")
        ce_layout.addWidget(lbl_body)

        self.body_edit = QTextEdit()
        self.body_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #FFFFFF;
                border: 1px solid #E8E5F7;
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
                color: {COLOR_NAVY};
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.body_edit.textChanged.connect(self._update_live_preview)
        ce_layout.addWidget(self.body_edit, stretch=1)

        # Action Buttons
        act_row = QHBoxLayout()
        act_row.setSpacing(10)

        self.btn_reset = QPushButton("Reset to Default")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setFixedHeight(38)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid #E8E5F7;
                border-radius: 10px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
            }}
        """)
        self.btn_reset.clicked.connect(self._reset_current_template)
        act_row.addWidget(self.btn_reset)

        act_row.addStretch()

        self.btn_save = QPushButton(" Save Template")
        self.btn_save.setIcon(qta.icon("fa5s.save", color="#FFFFFF"))
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(38)
        self.btn_save.setToolTip("Save this email template for future CV dispatches")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 0 20px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CTA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_CTA_PRESSED};
            }}
        """)
        self.btn_save.clicked.connect(self.save_template)
        act_row.addWidget(self.btn_save)

        ce_layout.addLayout(act_row)
        content_row.addWidget(col_editor, stretch=2)

        # -------------------------------------------------------------
        # 3. Right Column: Live Simulated Preview (~340px)
        # -------------------------------------------------------------
        col_preview = CardWidget(radius=20)
        col_preview.setFixedWidth(340)
        cp_layout = QVBoxLayout(col_preview)
        cp_layout.setContentsMargins(18, 18, 18, 18)
        cp_layout.setSpacing(12)

        cp_head = QHBoxLayout()
        lbl_pv_title = QLabel("Live Preview")
        lbl_pv_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 14px; font-weight: 700;")
        cp_head.addWidget(lbl_pv_title)

        badge_sim = QLabel("Simulated")
        badge_sim.setStyleSheet(f"""
            background-color: {COLOR_LAVENDER};
            color: {COLOR_PURPLE_DEEP};
            border: 1px solid #C4B5FD;
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 600;
        """)
        cp_head.addWidget(badge_sim)
        cp_head.addStretch()
        cp_layout.addLayout(cp_head)

        # Email Card Container
        email_card = QFrame()
        email_card.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
            }}
        """)
        ec_l = QVBoxLayout(email_card)
        ec_l.setContentsMargins(14, 12, 14, 12)
        ec_l.setSpacing(8)

        # Headers box
        self.lbl_pv_to = QLabel("To: client@acmefoods.com")
        self.lbl_pv_to.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        ec_l.addWidget(self.lbl_pv_to)

        self.lbl_pv_from = QLabel("From: recruiter@scalexpro.com")
        self.lbl_pv_from.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        ec_l.addWidget(self.lbl_pv_from)

        self.lbl_pv_subj = QLabel("Subject: Candidate Profile")
        self.lbl_pv_subj.setWordWrap(True)
        self.lbl_pv_subj.setStyleSheet(f"color: {COLOR_NAVY}; font-weight: 700; font-size: 12px; padding: 4px 0;")
        ec_l.addWidget(self.lbl_pv_subj)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E2E8F0;")
        ec_l.addWidget(sep)

        # Body preview
        self.pv_body = QTextEdit()
        self.pv_body.setReadOnly(True)
        self.pv_body.setStyleSheet("border: none; background: transparent; font-size: 12px; color: #334155; line-height: 1.45;")
        ec_l.addWidget(self.pv_body, stretch=1)

        # Attachment chip at bottom
        att_row = QHBoxLayout()
        att_row.setSpacing(6)
        ic_att = QLabel()
        ic_att.setPixmap(qta.icon("fa5s.paperclip", color=COLOR_TEXT_MUTED).pixmap(11, 11))
        ic_att.setStyleSheet("border: none; background: transparent;")
        att_row.addWidget(ic_att)

        lbl_att = QLabel("CAND-1042_Backend_Lead_Branded.pdf")
        lbl_att.setStyleSheet(f"border: none; background: transparent; color: {COLOR_PRIMARY}; font-size: 11px; font-weight: 600;")
        att_row.addWidget(lbl_att)
        att_row.addStretch()
        ec_l.addLayout(att_row)

        cp_layout.addWidget(email_card, stretch=1)
        content_row.addWidget(col_preview)

        root_layout.addLayout(content_row, stretch=1)

    def _build_template_item_btn(self, idx: int, name: str, desc: str) -> QPushButton:
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(56)

        l = QVBoxLayout(btn)
        l.setContentsMargins(12, 8, 12, 8)
        l.setSpacing(2)

        t_lbl = QLabel(name)
        t_lbl.setObjectName("t_title")
        t_lbl.setStyleSheet(f"background: transparent; border: none; font-size: 12px; font-weight: 700; color: {COLOR_NAVY};")
        l.addWidget(t_lbl)

        d_lbl = QLabel(desc)
        d_lbl.setObjectName("t_desc")
        d_lbl.setStyleSheet(f"background: transparent; border: none; font-size: 10px; color: {COLOR_TEXT_MUTED};")
        l.addWidget(d_lbl)

        btn.clicked.connect(lambda ch=False, i=idx: self._select_template(i))
        self._style_template_btn(btn, idx == self.active_template_idx)
        return btn

    def _style_template_btn(self, btn: QPushButton, is_active: bool):
        if is_active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_LAVENDER};
                    border: 1.5px solid {COLOR_PRIMARY};
                    border-radius: 12px;
                    text-align: left;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    border: 1px solid #E8E5F7;
                    border-radius: 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #F8FAFC;
                    border-color: {COLOR_PRIMARY};
                }}
            """)

    def _select_template(self, idx: int):
        self.active_template_idx = idx
        for i, btn in enumerate(self.template_buttons):
            self._style_template_btn(btn, i == idx)

        t = self.templates_data[idx]
        self.subject_edit.setText(t["subject"])
        self.body_edit.setText(t["body"])
        self._update_live_preview()

    def _create_new_template(self):
        new_idx = len(self.templates_data)
        new_data = {
            "name": f"Template {new_idx + 1}",
            "desc": "Custom candidate dispatch template",
            "subject": "Candidate Profile: {candidate_id} - {role}",
            "body": "Dear {client_name},\n\nPlease review candidate {candidate_id}.\n\nBest,\n{company_name}",
        }
        self.templates_data.append(new_data)
        btn = self._build_template_item_btn(new_idx, new_data["name"], new_data["desc"])
        self.list_container.addWidget(btn)
        self.template_buttons.append(btn)
        self._select_template(new_idx)

    def _reset_current_template(self):
        defaults = [
            "Candidate Profile: {candidate_id} - {role}",
            "Dear {client_name},\n\nPlease find attached the anonymized and branded profile for candidate {candidate_id} ({role}).\n\nBest regards,\n{company_name}",
        ]
        self.subject_edit.setText(defaults[0])
        self.body_edit.setText(defaults[1])

    def _insert_token(self, token_str: str):
        if self.body_edit.hasFocus():
            self.body_edit.insertPlainText(token_str)
        else:
            self.subject_edit.insert(token_str)

    def _update_live_preview(self):
        subj = self.subject_edit.text()
        body = self.body_edit.toPlainText()

        tokens = {
            "{client_name}": "Acme Foods Pvt Ltd",
            "{candidate_id}": "CAND-1042",
            "{role}": "Senior Backend Engineer",
            "{company_name}": "ScaleXPro",
            "{candidate_name}": "John Doe",
            "{cv_filename}": "CAND-1042_Backend_Lead_Branded.pdf",
        }
        for k, v in tokens.items():
            subj = subj.replace(k, v)
            body = body.replace(k, v)

        self.lbl_pv_subj.setText(f"Subject: {subj}")
        self.pv_body.setPlainText(body)

    def load_templates(self):
        saved_subj = get_setting("email_subject_template")
        saved_body = get_setting("email_body_template")
        if saved_subj:
            self.templates_data[0]["subject"] = saved_subj
        if saved_body:
            self.templates_data[0]["body"] = saved_body

        self._select_template(0)

    def save_template(self):
        cur_subj = self.subject_edit.text().strip()
        cur_body = self.body_edit.toPlainText().strip()
        if not cur_subj or not cur_body:
            QMessageBox.warning(self, "Validation", "Template subject and body cannot be empty.")
            return

        self.templates_data[self.active_template_idx]["subject"] = cur_subj
        self.templates_data[self.active_template_idx]["body"] = cur_body

        if self.active_template_idx == 0:
            set_setting("email_subject_template", cur_subj)
            set_setting("email_body_template", cur_body)

        self.show_toast_signal.emit("Template Saved", "Email template saved successfully.", "success")
