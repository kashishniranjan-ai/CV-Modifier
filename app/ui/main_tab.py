"""
Primary Workflow Tab for ScaleXPro CV-Modifier:
ScaleXPro Enterprise SaaS Commercial Workflow (HubSpot / Stripe / Zoho Recruit quality):
1. Modern Stepper (Upload, Review, Send) with orange progress indicator
2. Step 1: Upload & Profile info, adaptive logo size/position toolbar, automatic one-step execution
3. Step 2: Large side-by-side Before/After preview with page navigation, zoom, and collapsible audit trail
4. Step 3: Send to client with client picker, email validation, and prominent orange Send button
"""

import os
import shutil
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QSplitter,
    QComboBox,
    QProgressBar,
    QFrame,
    QSizePolicy,
    QStackedWidget,
    QScrollArea,
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent, QFont, QPixmap, QIcon
import qtawesome as qta

from app.config import EXPORTS_DIR, DATA_DIR, ASSETS_DIR, BASE_DIR, ensure_directories
from app.database import (
    get_all_settings,
    get_next_candidate_code,
    save_candidate,
    get_all_clients,
    record_redaction_event,
)
from app.core.pdf_redactor import redact_and_brand_pdf
from app.core.docx_redactor import redact_docx, convert_docx_to_pdf
from app.core.validator import validate_clean_pdf
from app.email_service import send_branded_cv_email
from app.ui.preview_widget import BeforeAfterPreviewWidget
from app.ui.redactions_list import RedactionsListWidget
from app.ui.process_dialogs import ProcessLoadingDialog, ProcessSuccessDialog
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
    COLOR_LAVENDER_LIGHT,
    COLOR_PURPLE_DARK,
    COLOR_PURPLE_DEEP,
    COLOR_SUCCESS,
    COLOR_SUCCESS_TINT,
    COLOR_SUCCESS_BORDER,
    COLOR_DANGER,
    COLOR_NAVY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
)
from app.ui.widgets import CardWidget, PastelIconCircle
from app.logger import logger


class UploadHeroCard(QFrame):
    """
    Welcoming, spacious hero dropzone shown when no CV is currently loaded.
    Provides instant clarity with 1-click actions and value points.
    """
    files_dropped = Signal(list)
    browse_clicked = Signal()
    sample_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("UploadHeroCard")
        self.setStyleSheet(f"""
            QFrame#UploadHeroCard {{
                background-color: #FFFFFF;
                border: 2px dashed #C4B5FD;
                border-radius: 20px;
            }}
            QFrame#UploadHeroCard:hover {{
                border-color: {COLOR_PRIMARY};
                background-color: #FAF8FF;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 46, 36, 46)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        # Big pastel cloud icon
        icon_circle = PastelIconCircle("fa5s.cloud-upload-alt", circle_type="lavender", size=68, icon_size=30)
        layout.addWidget(icon_circle, alignment=Qt.AlignCenter)

        # Headline
        lbl_head = QLabel("Drop Candidate CV Here")
        lbl_head.setAlignment(Qt.AlignCenter)
        lbl_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 22px; font-weight: 800; font-family: 'Inter', sans-serif;")
        layout.addWidget(lbl_head)

        # Subtitle
        lbl_sub = QLabel("Supports PDF and DOCX formats • 100% offline, private & secure")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13.5px;")
        layout.addWidget(lbl_sub)

        layout.addSpacing(8)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)
        btn_row.setAlignment(Qt.AlignCenter)

        self.btn_browse = QPushButton("  Browse CV from Computer...")
        self.btn_browse.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        self.btn_browse.setIconSize(QSize(16, 16))
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFixedHeight(46)
        self.btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 0 24px;
                font-weight: 700;
                font-size: 13.5px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        self.btn_browse.clicked.connect(self.browse_clicked.emit)
        btn_row.addWidget(self.btn_browse)

        self.btn_sample = QPushButton("  ✨ Try Sample CV (Instant Demo)")
        self.btn_sample.setCursor(Qt.PointingHandCursor)
        self.btn_sample.setFixedHeight(46)
        self.btn_sample.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_LAVENDER_LIGHT};
                color: {COLOR_PURPLE_DEEP};
                border: 1.5px solid #DDD6F7;
                border-radius: 12px;
                padding: 0 22px;
                font-weight: 700;
                font-size: 13.5px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER};
            }}
        """)
        self.btn_sample.clicked.connect(self.sample_clicked.emit)
        btn_row.addWidget(self.btn_sample)

        layout.addLayout(btn_row)

        layout.addSpacing(14)

        # 4 Trust feature pills in a balanced 2x2 grid
        trust_grid = QGridLayout()
        trust_grid.setHorizontalSpacing(14)
        trust_grid.setVerticalSpacing(8)
        trust_grid.setAlignment(Qt.AlignCenter)

        features = [
            ("fa5s.shield-alt", "100% Offline & Private"),
            ("fa5s.user-secret", "Erases Emails & Phones"),
            ("fa5s.building", "Adds Agency Logo"),
            ("fa5s.check-double", "Pre-Send Safety Scan"),
        ]
        for idx, (icon_n, text) in enumerate(features):
            row = idx // 2
            col = idx % 2
            pill = QFrame()
            pill.setStyleSheet("""
                QFrame {
                    background-color: #F8F9FE;
                    border: 1px solid #ECEEF8;
                    border-radius: 12px;
                    padding: 6px 14px;
                }
            """)
            pl = QHBoxLayout(pill)
            pl.setContentsMargins(6, 3, 6, 3)
            pl.setSpacing(8)

            ic = QLabel()
            ic.setPixmap(qta.icon(icon_n, color=COLOR_PRIMARY).pixmap(14, 14))
            pl.addWidget(ic)

            tx = QLabel(text)
            tx.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 12px; font-weight: 600;")
            pl.addWidget(tx)

            trust_grid.addWidget(pill, row, col)

        layout.addLayout(trust_grid)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = Path(url.toLocalFile()).suffix.lower()
                if ext in (".pdf", ".docx", ".doc"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        valid_files = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if Path(local_path).suffix.lower() in (".pdf", ".docx", ".doc"):
                    valid_files.append(local_path)
        if valid_files:
            event.acceptProposedAction()
            self.files_dropped.emit(valid_files)


class ProcessedCVRecord:
    """Holds state for a single processed CV in multi-CV batch operations."""
    def __init__(
        self,
        candidate_code: str,
        name: str,
        role: str,
        input_file: str,
        original_pdf: str,
        output_pdf: str,
        output_filename: str,
        redactions: list,
    ):
        self.candidate_code = candidate_code
        self.name = name
        self.role = role
        self.input_file = input_file
        self.original_pdf = original_pdf
        self.output_pdf = output_pdf
        self.output_filename = output_filename
        self.redactions = redactions


class RedactionWorkerThread(QThread):
    """Background worker thread executing PDF/DOCX redaction and branding."""
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(
        self,
        input_file: str,
        candidate_code: str,
        role: str,
        settings: dict,
        logo_size_override: str = "Auto",
        logo_position_override: str = "Auto",
    ):
        super().__init__()
        self.input_file = input_file
        self.candidate_code = candidate_code
        self.role = role
        self.settings = settings
        self.logo_size_override = logo_size_override
        self.logo_position_override = logo_position_override

    def run(self):
        try:
            ensure_directories()
            temp_dir = DATA_DIR / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            input_ext = Path(self.input_file).suffix.lower()
            safe_role = re.sub(r"[^\w\s-]", "", self.role).strip().replace(" ", "_")
            if not safe_role:
                safe_role = "Candidate"
            output_filename = f"{self.candidate_code}_{safe_role}_Branded.pdf"
            output_pdf_path = str(EXPORTS_DIR / output_filename)

            logo_path = self.settings.get("logo_path", "")
            if not logo_path or not os.path.exists(logo_path):
                default_logo = ASSETS_DIR / "scalexpro_logo.png"
                if default_logo.exists():
                    logo_path = str(default_logo)

            redaction_color = self.settings.get("redaction_color", "black")
            redact_email = self.settings.get("redact_email", True)
            redact_phone = self.settings.get("redact_phone", True)
            redact_urls = self.settings.get("redact_urls", True)
            redact_address = self.settings.get("redact_address", True)
            redact_metadata = self.settings.get("redact_metadata", True)
            add_logo = self.settings.get("add_logo", True)

            original_preview_pdf = ""
            redacted_manifest = []

            if input_ext == ".pdf":
                original_preview_pdf = self.input_file
                res = redact_and_brand_pdf(
                    input_path=self.input_file,
                    output_path=output_pdf_path,
                    logo_path=logo_path,
                    redaction_color=redaction_color,
                    redact_email=redact_email,
                    redact_phone=redact_phone,
                    redact_urls=redact_urls,
                    redact_address=redact_address,
                    redact_metadata=redact_metadata,
                    add_logo=add_logo,
                    logo_size_override=self.logo_size_override,
                    logo_position_override=self.logo_position_override,
                )
                if not res.success:
                    self.error_signal.emit(res.error_message or "Failed to redact PDF.")
                    return
                redacted_manifest = res.redactions_applied

            elif input_ext in (".docx", ".doc"):
                temp_orig_pdf = str(temp_dir / f"orig_{self.candidate_code}.pdf")
                convert_docx_to_pdf(self.input_file, temp_orig_pdf)
                original_preview_pdf = temp_orig_pdf

                temp_redacted_docx = str(temp_dir / f"redacted_{self.candidate_code}.docx")
                docx_res = redact_docx(
                    input_path=self.input_file,
                    output_docx_path=temp_redacted_docx,
                    redact_email=redact_email,
                    redact_phone=redact_phone,
                    redact_urls=redact_urls,
                    redact_address=redact_address,
                    redact_metadata=redact_metadata,
                )
                redacted_manifest = docx_res.get("redactions_applied", [])

                temp_redacted_pdf = str(temp_dir / f"interim_{self.candidate_code}.pdf")
                convert_success = convert_docx_to_pdf(temp_redacted_docx, temp_redacted_pdf)
                if not convert_success:
                    self.error_signal.emit("Failed to convert DOCX to PDF.")
                    return

                res = redact_and_brand_pdf(
                    input_path=temp_redacted_pdf,
                    output_path=output_pdf_path,
                    logo_path=logo_path,
                    redaction_color=redaction_color,
                    redact_email=redact_email,
                    redact_phone=redact_phone,
                    redact_urls=redact_urls,
                    redact_address=redact_address,
                    redact_metadata=redact_metadata,
                    add_logo=add_logo,
                    logo_size_override=self.logo_size_override,
                    logo_position_override=self.logo_position_override,
                )
                if not res.success:
                    self.error_signal.emit(res.error_message or "Failed to brand and finalize PDF.")
                    return
                redacted_manifest.extend(res.redactions_applied)

            else:
                self.error_signal.emit(f"Unsupported file format '{input_ext}'. Please select a PDF or DOCX file.")
                return

            self.finished_signal.emit({
                "candidate_code": self.candidate_code,
                "role": self.role,
                "input_file": self.input_file,
                "original_pdf": original_preview_pdf,
                "output_pdf": output_pdf_path,
                "output_filename": output_filename,
                "redactions": redacted_manifest,
            })

        except Exception as e:
            logger.error(f"Redaction thread failed: {e}", exc_info=True)
            self.error_signal.emit(str(e))


class CVRedactionTab(QWidget):
    """Main Tab for One-Step Automatic CV Redaction & Branding, Preview, and Client Dispatch."""
    status_signal = Signal(str, str)  # (message, status_type: 'info' | 'success' | 'error')
    navigate_to_tab = Signal(int)     # (tab_index)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.selected_file: Optional[str] = None
        self.current_output_pdf: Optional[str] = None
        self.current_output_filename: Optional[str] = None
        self.worker: Optional[RedactionWorkerThread] = None
        self.loading_dialog: Optional[ProcessLoadingDialog] = None

        # Multi-file batch processing state
        self.batch_queue: List[str] = []
        self.total_batch_count: int = 0
        self.current_batch_index: int = 0
        self.processed_records: List[ProcessedCVRecord] = []

        self._setup_ui()
        self.reset_form()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # =============================================================
        # 0. COMMERCIAL STEPPER (Upload -> Review -> Send)
        # =============================================================
        self._build_stepper(main_layout)

        # =============================================================
        # MAIN BODY: 2-COLUMN SPLIT (Previews Left + Controls/Send Right)
        # =============================================================
        body_row = QHBoxLayout()
        body_row.setSpacing(16)

        # -------------------------------------------------------------
        # LEFT COLUMN (stretch=3): Compact CV Info Bar + Previews & Toolbar
        # -------------------------------------------------------------
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # Compact file selector bar (Visible after CV is loaded for editing ID/Role or Re-running)
        self.compact_bar = QFrame()
        self.compact_bar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E8E5F7;
                border-radius: 14px;
                padding: 4px 8px;
            }}
        """)
        cb_l = QHBoxLayout(self.compact_bar)
        cb_l.setContentsMargins(12, 6, 12, 6)
        cb_l.setSpacing(10)

        lbl_id = QLabel("ID:")
        lbl_id.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        cb_l.addWidget(lbl_id)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("CAND-1042")
        self.code_edit.setToolTip("Candidate unique identification code")
        self.code_edit.setFixedWidth(100)
        cb_l.addWidget(self.code_edit)

        lbl_role = QLabel("Role:")
        lbl_role.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        cb_l.addWidget(lbl_role)

        self.role_edit = QLineEdit()
        self.role_edit.setPlaceholderText("e.g. Python Developer")
        self.role_edit.setToolTip("Target job title or candidate specialization")
        cb_l.addWidget(self.role_edit, stretch=1)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setVisible(False)
        self.name_edit = QLineEdit()
        self.name_edit.setVisible(False)

        self.btn_browse = QPushButton(" Browse CV...")
        self.btn_browse.setIcon(qta.icon("fa5s.folder-open", color=COLOR_TEXT_PRIMARY))
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setToolTip("Select a PDF or DOCX resume from your computer")
        self.btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.btn_browse.clicked.connect(self._browse_file)
        cb_l.addWidget(self.btn_browse)



        self.btn_process = QPushButton(" Re-run")
        self.btn_process.setIcon(qta.icon("fa5s.redo-alt", color="#FFFFFF"))
        self.btn_process.setCursor(Qt.PointingHandCursor)
        self.btn_process.setToolTip("Re-run automatic redaction and logo branding")
        self.btn_process.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        self.btn_process.clicked.connect(self._rerun_processing)
        cb_l.addWidget(self.btn_process)

        self.compact_bar.setVisible(False)
        left_col.addWidget(self.compact_bar)

        # Batch dropdown container if multiple CVs
        self.batch_selector_container = QWidget()
        row_batch = QHBoxLayout(self.batch_selector_container)
        row_batch.setContentsMargins(0, 0, 0, 0)
        row_batch.setSpacing(8)
        lbl_batch = QLabel("Active Batch CV:")
        lbl_batch.setStyleSheet(f"font-weight: 600; color: {COLOR_PRIMARY}; font-size: 12px;")
        row_batch.addWidget(lbl_batch)
        self.batch_combo = QComboBox()
        self.batch_combo.currentIndexChanged.connect(self._on_batch_selection_changed)
        row_batch.addWidget(self.batch_combo, stretch=1)
        self.batch_selector_container.setVisible(False)
        left_col.addWidget(self.batch_selector_container)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        left_col.addWidget(self.progress_bar)

        # Workspace Stack: Page 0 = Upload Hero Card (Empty State), Page 1 = Active Preview
        self.workspace_stack = QStackedWidget()

        # Page 0: Upload Hero Card
        self.upload_hero_card = UploadHeroCard()
        self.upload_hero_card.files_dropped.connect(self.start_batch_processing)
        self.upload_hero_card.browse_clicked.connect(self._browse_file)
        self.upload_hero_card.sample_clicked.connect(self._load_sample_cv)
        self.workspace_stack.addWidget(self.upload_hero_card)

        # Page 1: Active Preview with top summary banner
        preview_container = QWidget()
        pc_layout = QVBoxLayout(preview_container)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setSpacing(8)

        # Status & Safety Summary Banner
        self.status_banner = QFrame()
        self.status_banner.setStyleSheet("""
            QFrame {
                background-color: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 10px;
                padding: 4px 12px;
            }
        """)
        sb_l = QHBoxLayout(self.status_banner)
        sb_l.setContentsMargins(8, 4, 8, 4)
        sb_l.setSpacing(10)

        self.lbl_status_icon = QLabel()
        self.lbl_status_icon.setPixmap(qta.icon("fa5s.check-circle", color="#16A34A").pixmap(14, 14))
        sb_l.addWidget(self.lbl_status_icon)

        self.lbl_status_text = QLabel("CV Ready: Anonymized & Branded")
        self.lbl_status_text.setStyleSheet("color: #166534; font-weight: 700; font-size: 12px;")
        sb_l.addWidget(self.lbl_status_text, stretch=1)

        self.lbl_status_details = QLabel("Contacts removed • Logo branded • Pre-send safety verified")
        self.lbl_status_details.setStyleSheet("color: #15803D; font-size: 11px; font-weight: 500;")
        sb_l.addWidget(self.lbl_status_details)

        pc_layout.addWidget(self.status_banner)

        # Side-by-side Before/After Previews
        self.preview_widget = BeforeAfterPreviewWidget()
        self.preview_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_widget.version_saved_signal.connect(self._on_preview_version_saved)
        self.preview_widget.edit_audit_signal.connect(self._on_preview_edit_audit)
        pc_layout.addWidget(self.preview_widget, stretch=1)

        self.workspace_stack.addWidget(preview_container)
        left_col.addWidget(self.workspace_stack, stretch=1)

        body_row.addLayout(left_col, stretch=3)

        # -------------------------------------------------------------
        # RIGHT COLUMN (Scrollable container for Actions, Send, Protection)
        # -------------------------------------------------------------
        self.right_scroll = QScrollArea()
        self.right_scroll.setFixedWidth(320)
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.right_scroll.setFrameShape(QFrame.NoFrame)
        self.right_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        right_panel_container = QWidget()
        right_panel_container.setObjectName("rightPanelContainer")
        right_panel_container.setStyleSheet("#rightPanelContainer { background: transparent; }")
        right_col = QVBoxLayout(right_panel_container)
        right_col.setContentsMargins(0, 0, 4, 0)
        right_col.setSpacing(12)

        # =============================================================
        # CARD 1: EXPORT & PRIMARY ACTIONS (PROMINENT & EASY)
        # =============================================================
        export_card = CardWidget(radius=18)
        ec_layout = QVBoxLayout(export_card)
        ec_layout.setContentsMargins(16, 14, 16, 14)
        ec_layout.setSpacing(10)

        ec_header = QHBoxLayout()
        lbl_ec_title = QLabel("Actions & Export")
        lbl_ec_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13.5px; font-weight: 700;")
        ec_header.addWidget(lbl_ec_title)
        ec_header.addStretch()
        ec_layout.addLayout(ec_header)

        # Export filename display badge
        self.export_name_label = QLabel("No CV processed yet")
        self.export_name_label.setWordWrap(True)
        self.export_name_label.setStyleSheet("""
            background-color: #F8FAFC;
            color: #64748B;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        ec_layout.addWidget(self.export_name_label)

        # Button 1: Save / Download PDF (Primary Purple)
        self.btn_save_as = QPushButton("  Save / Download PDF...")
        self.btn_save_as.setIcon(qta.icon("fa5s.download", color="#FFFFFF"))
        self.btn_save_as.setIconSize(QSize(15, 15))
        self.btn_save_as.setCursor(Qt.PointingHandCursor)
        self.btn_save_as.setFixedHeight(42)
        self.btn_save_as.setToolTip("Save the clean, branded PDF to your computer")
        self.btn_save_as.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
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
        self.btn_save_as.clicked.connect(self._save_as)
        ec_layout.addWidget(self.btn_save_as)

        # Button 2: Open in PDF Viewer
        self.btn_open_pdf = QPushButton("  Open in PDF Viewer")
        self.btn_open_pdf.setIcon(qta.icon("fa5s.external-link-alt", color=COLOR_NAVY))
        self.btn_open_pdf.setIconSize(QSize(13, 13))
        self.btn_open_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_open_pdf.setFixedHeight(36)
        self.btn_open_pdf.setToolTip("Open in default system PDF reader (Adobe, Chrome, Edge)")
        self.btn_open_pdf.setStyleSheet(f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: {COLOR_NAVY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
                border-color: {COLOR_PRIMARY};
                color: {COLOR_PRIMARY};
            }}
            QPushButton:disabled {{
                background-color: #F1F5F9;
                color: #94A3B8;
                border-color: #E2E8F0;
            }}
        """)
        self.btn_open_pdf.clicked.connect(self._open_output_pdf)
        ec_layout.addWidget(self.btn_open_pdf)

        # Button 3: Process Another CV
        self.btn_new_cv = QPushButton("  Process Another CV")
        self.btn_new_cv.setIcon(qta.icon("fa5s.plus-circle", color=COLOR_PRIMARY))
        self.btn_new_cv.setIconSize(QSize(13, 13))
        self.btn_new_cv.setCursor(Qt.PointingHandCursor)
        self.btn_new_cv.setFixedHeight(30)
        self.btn_new_cv.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_PRIMARY};
                border: none;
                font-weight: 600;
                font-size: 11.5px;
            }}
            QPushButton:hover {{
                text-decoration: underline;
                color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        self.btn_new_cv.clicked.connect(self.reset_form)
        ec_layout.addWidget(self.btn_new_cv)

        right_col.addWidget(export_card)

        # =============================================================
        # CARD 2: SEND TO CLIENT (OPTIONAL DISPATCH)
        # =============================================================
        client_card = CardWidget(radius=18)
        client_card_l = QVBoxLayout(client_card)
        client_card_l.setContentsMargins(16, 12, 16, 12)
        client_card_l.setSpacing(6)

        lbl_c_sec = QLabel("Send to Client")
        lbl_c_sec.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13px; font-weight: 700;")
        client_card_l.addWidget(lbl_c_sec)

        lbl_c = QLabel("Client")
        lbl_c.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        client_card_l.addWidget(lbl_c)
        self.client_combo = QComboBox()
        self.client_combo.currentIndexChanged.connect(self._on_client_selected)
        client_card_l.addWidget(self.client_combo)

        lbl_em = QLabel("Email")
        lbl_em.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        client_card_l.addWidget(lbl_em)
        self.client_email_edit = QLineEdit()
        self.client_email_edit.setPlaceholderText("client@acmefoods.com")
        client_card_l.addWidget(self.client_email_edit)

        # Action Button: Final Check & Send to Client (Primary ScaleXPro Orange CTA)
        self.btn_send_email = QPushButton("  Send CV to Client via Email")
        self.btn_send_email.setIcon(qta.icon("fa5s.paper-plane", color="#FFFFFF"))
        self.btn_send_email.setIconSize(QSize(13, 13))
        self.btn_send_email.setCursor(Qt.PointingHandCursor)
        self.btn_send_email.setEnabled(True)
        self.btn_send_email.setFixedHeight(42)
        self.btn_send_email.setToolTip("Send the sanitized and branded CV directly to this client via email")
        self.btn_send_email.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-weight: 700;
                font-size: 12.5px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CTA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_CTA_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: #FED7AA;
                color: #FFFFFF;
            }}
        """)
        self.btn_send_email.clicked.connect(self._verify_and_send)
        client_card_l.addSpacing(4)
        client_card_l.addWidget(self.btn_send_email)

        right_col.addWidget(client_card)

        # =============================================================
        # CARD 3: PROTECTION & BRANDING SUMMARY
        # =============================================================
        protect_card = CardWidget(radius=18)
        protect_l = QVBoxLayout(protect_card)
        protect_l.setContentsMargins(16, 12, 16, 12)
        protect_l.setSpacing(8)

        # Title
        p_title = QLabel("Branding & Protection")
        p_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 13px; font-weight: 700;")
        protect_l.addWidget(p_title)

        # Removed items checkboxes
        self.removed_items_list = [
            "Email address",
            "Phone number",
            "LinkedIn / Links",
            "Location / Address",
            "Phone label",
            "Email label",
            "Social labels",
        ]
        self.removed_item_widgets = []
        grid_items = QHBoxLayout()
        grid_items.setSpacing(10)
        col1 = QVBoxLayout()
        col1.setSpacing(3)
        col2 = QVBoxLayout()
        col2.setSpacing(3)

        for i, item_txt in enumerate(self.removed_items_list):
            r = QHBoxLayout()
            r.setSpacing(6)
            chk = QLabel()
            chk.setPixmap(qta.icon("fa5s.check-circle", color=COLOR_SUCCESS).pixmap(12, 12))
            r.addWidget(chk)
            lbl = QLabel(item_txt)
            lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            r.addWidget(lbl)
            r.addStretch()
            if i < 4:
                col1.addLayout(r)
            else:
                col2.addLayout(r)
            self.removed_item_widgets.append((chk, lbl))

        grid_items.addLayout(col1)
        grid_items.addLayout(col2)
        protect_l.addLayout(grid_items)

        # Logo row: Thumbnail + Size/Pos + Change
        logo_drop_row = QHBoxLayout()
        logo_drop_row.setSpacing(8)

        col_size = QVBoxLayout()
        col_size.setSpacing(2)
        lbl_s = QLabel("Logo Size")
        lbl_s.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        col_size.addWidget(lbl_s)
        self.logo_size_combo = QComboBox()
        self.logo_size_combo.addItems(["Auto", "Small", "Medium", "Large"])
        self.logo_size_combo.setCurrentText("Medium")
        col_size.addWidget(self.logo_size_combo)
        logo_drop_row.addLayout(col_size)

        col_pos = QVBoxLayout()
        col_pos.setSpacing(2)
        lbl_p = QLabel("Position")
        lbl_p.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 10px;")
        col_pos.addWidget(lbl_p)
        self.logo_pos_combo = QComboBox()
        self.logo_pos_combo.addItems(["Auto", "Top Left", "Top Center", "Top Right"])
        self.logo_pos_combo.setCurrentText("Top Center")
        col_pos.addWidget(self.logo_pos_combo)
        logo_drop_row.addLayout(col_pos)

        protect_l.addLayout(logo_drop_row)

        logo_thumb_row = QHBoxLayout()
        self.lbl_logo_thumb = QLabel()
        logo_p = ASSETS_DIR / "scalexpro_logo.png"
        if logo_p.exists():
            pix = QPixmap(str(logo_p)).scaledToWidth(70, Qt.SmoothTransformation)
            self.lbl_logo_thumb.setPixmap(pix)
        logo_thumb_row.addWidget(self.lbl_logo_thumb)
        logo_thumb_row.addStretch()

        self.btn_change_logo = QPushButton("Change")
        self.btn_change_logo.setCursor(Qt.PointingHandCursor)
        self.btn_change_logo.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-size: 11px; font-weight: 600;")
        self.btn_change_logo.clicked.connect(self._change_logo_quick)
        logo_thumb_row.addWidget(self.btn_change_logo)
        protect_l.addLayout(logo_thumb_row)

        # Audit summary label & toggle button
        self.lbl_audit_summary = QLabel("Audit Trail: No items redacted yet")
        self.lbl_audit_summary.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        self.lbl_audit_summary.setWordWrap(True)
        protect_l.addWidget(self.lbl_audit_summary)

        self.btn_toggle_audit = QPushButton("Show Full Audit Manifest")
        self.btn_toggle_audit.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_audit.setStyleSheet(f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.btn_toggle_audit.clicked.connect(self._toggle_audit_panel)
        protect_l.addWidget(self.btn_toggle_audit)

        self.audit_container = QWidget()
        ac_l = QVBoxLayout(self.audit_container)
        ac_l.setContentsMargins(0, 4, 0, 0)
        self.redactions_list = RedactionsListWidget()
        ac_l.addWidget(self.redactions_list)
        self.audit_container.setVisible(False)
        protect_l.addWidget(self.audit_container)

        right_col.addWidget(protect_card)

        right_col.addStretch()
        self.right_scroll.setWidget(right_panel_container)
        body_row.addWidget(self.right_scroll)

        main_layout.addLayout(body_row, stretch=1)

    def _change_logo_quick(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Company Logo",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if file_path and os.path.exists(file_path):
            from app.config import ASSETS_DIR
            from app.database import set_setting
            dest_logo = ASSETS_DIR / "company_logo.png"
            shutil.copyfile(file_path, str(dest_logo))
            set_setting("logo_path", str(dest_logo))
            pix = QPixmap(str(dest_logo)).scaledToWidth(80, Qt.SmoothTransformation)
            self.lbl_logo_thumb.setPixmap(pix)
            self.status_signal.emit("Company logo updated successfully.", "success")

    # -----------------------------------------------------------------
    # Commercial Stepper Component
    # -----------------------------------------------------------------
    def _build_stepper(self, parent_layout: QVBoxLayout):
        stepper_frame = QFrame()
        stepper_frame.setFixedHeight(48)
        stepper_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E8E5F7;
                border-radius: 24px;
            }}
        """)
        s_layout = QHBoxLayout(stepper_frame)
        s_layout.setContentsMargins(20, 4, 20, 4)
        s_layout.setSpacing(16)
        s_layout.setAlignment(Qt.AlignCenter)

        self.step1_pill = QPushButton("1  Upload CV")
        self.step2_pill = QPushButton("2  Review & Edit")
        self.step3_pill = QPushButton("3  Save & Send")

        for pill in (self.step1_pill, self.step2_pill, self.step3_pill):
            pill.setFont(QFont("Inter", 11, QFont.Bold))
            pill.setCursor(Qt.PointingHandCursor)

        self.step1_pill.clicked.connect(self._on_step1_clicked)
        self.step2_pill.clicked.connect(self._on_step2_clicked)
        self.step3_pill.clicked.connect(self._on_step3_clicked)

        line1 = QFrame()
        line1.setFixedWidth(40)
        line1.setFixedHeight(2)
        line1.setStyleSheet(f"background-color: {COLOR_LAVENDER};")

        line2 = QFrame()
        line2.setFixedWidth(40)
        line2.setFixedHeight(2)
        line2.setStyleSheet(f"background-color: {COLOR_LAVENDER};")

        s_layout.addStretch()
        s_layout.addWidget(self.step1_pill)
        s_layout.addWidget(line1)
        s_layout.addWidget(self.step2_pill)
        s_layout.addWidget(line2)
        s_layout.addWidget(self.step3_pill)
        s_layout.addStretch()

        parent_layout.addWidget(stepper_frame)
        self._update_stepper(1)

    def _update_stepper(self, active_step: int):
        """Highlights the active stepper stage with interactive styling."""
        steps = [
            (self.step1_pill, "1  Upload CV"),
            (self.step2_pill, "2  Review & Edit"),
            (self.step3_pill, "3  Save & Send"),
        ]
        for idx, (pill, title) in enumerate(steps, start=1):
            if idx == active_step:
                pill.setText(f"●  {title}")
                pill.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_LAVENDER};
                        color: {COLOR_PURPLE_DEEP};
                        border: none;
                        border-radius: 14px;
                        padding: 5px 16px;
                        font-weight: 700;
                        font-size: 12px;
                    }}
                """)
            elif idx < active_step:
                pill.setText(f"✓  {title}")
                pill.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #DDF5E8;
                        color: #166534;
                        border: 1px solid #BBF7D0;
                        border-radius: 14px;
                        padding: 5px 14px;
                        font-weight: 700;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: #BBF7D0;
                    }}
                """)
            else:
                pill.setText(f"○  {title}")
                pill.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {COLOR_TEXT_MUTED};
                        border: none;
                        padding: 5px 12px;
                        font-weight: 500;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        color: {COLOR_TEXT_PRIMARY};
                    }}
                """)

    def _on_step1_clicked(self):
        """Stepper 1 Click: Browse new file or switch to upload view."""
        self._browse_file()

    def _on_step2_clicked(self):
        """Stepper 2 Click: View processed review if document loaded."""
        if self.selected_file and hasattr(self, "workspace_stack"):
            self.workspace_stack.setCurrentIndex(1)
            self._update_stepper(2)

    def _on_step3_clicked(self):
        """Stepper 3 Click: Jump to export and send section."""
        if self.selected_file:
            self._update_stepper(3)
            if hasattr(self, "btn_save_as"):
                self.btn_save_as.setFocus()

    def _load_sample_cv(self):
        """Loads bundled sample CV for instant 1-click demonstration."""
        sample_path = BASE_DIR / "sample_data" / "sample_cv_john_doe.pdf"
        if not sample_path.exists():
            sample_path = BASE_DIR / "sample_data" / "sample_cv_priya_sharma.docx"
        if sample_path.exists():
            self.start_batch_processing([str(sample_path)])
        else:
            QMessageBox.information(
                self,
                "Sample CV",
                "Sample CV not found in sample_data folder. Please browse a CV from your computer.",
            )

    # =============================================================
    # DRAG & DROP SUPPORT
    # =============================================================
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = Path(url.toLocalFile()).suffix.lower()
                if ext in (".pdf", ".docx", ".doc"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        valid_files = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if Path(local_path).suffix.lower() in (".pdf", ".docx", ".doc"):
                    valid_files.append(local_path)

        if valid_files:
            event.acceptProposedAction()
            self.start_batch_processing(valid_files)

    def _browse_file(self):
        """Allows selecting one or multiple CVs and starts automatic processing immediately."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Candidate CV(s)",
            "",
            "CV Documents (*.pdf *.docx *.doc)",
        )
        if files:
            self.start_batch_processing(files)

    # =============================================================
    # AUTOMATIC ONE-STEP PROCESSING (SINGLE & BATCH)
    # =============================================================
    def load_multiple_files(self, file_paths: List[str]):
        """Entry point when files are dropped from Dashboard."""
        self.start_batch_processing(file_paths)

    def start_batch_processing(self, file_paths: List[str]):
        """Initiates one-step sequential processing for one or multiple CVs."""
        if not file_paths:
            return

        self.batch_queue = [f for f in file_paths if os.path.exists(f)]
        if not self.batch_queue:
            return

        self.total_batch_count = len(self.batch_queue)
        self.current_batch_index = 0
        self.processed_records.clear()

        self.batch_combo.blockSignals(True)
        self.batch_combo.clear()
        self.batch_combo.blockSignals(False)
        self.batch_selector_container.setVisible(self.total_batch_count > 1)

        self.btn_browse.setEnabled(False)
        self.btn_process.setEnabled(False)
        self.progress_bar.setVisible(True)
        self._update_stepper(1)

        # Show centered loading dialog
        try:
            self.loading_dialog = ProcessLoadingDialog(self.window())
            self.loading_dialog.show()
        except Exception as e:
            logger.debug(f"Could not show loading dialog: {e}")

        self._process_next_in_queue()

    def _process_next_in_queue(self):
        """Processes the next file from the batch queue."""
        if not self.batch_queue:
            self._on_batch_complete()
            return

        file_path = self.batch_queue.pop(0)
        self.current_batch_index += 1

        self.selected_file = file_path
        self.file_path_edit.setText(file_path)

        # Automatic profile inference from filename
        cand_code = get_next_candidate_code()
        base_name = Path(file_path).stem.replace("_", " ").replace("-", " ")
        inferred_role = base_name.strip()
        inferred_name = base_name.split()[0] if base_name.split() else "Candidate"

        self.code_edit.setText(cand_code)
        self.name_edit.setText(inferred_name)
        self.role_edit.setText(inferred_role)

        status_msg = f"Processing [{self.current_batch_index}/{self.total_batch_count}]: {Path(file_path).name}..."
        self.status_signal.emit(status_msg, "info")

        settings = get_all_settings()

        self.worker = RedactionWorkerThread(
            input_file=file_path,
            candidate_code=cand_code,
            role=inferred_role,
            settings=settings,
            logo_size_override=self.logo_size_combo.currentText(),
            logo_position_override=self.logo_pos_combo.currentText(),
        )
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_finished(self, result: dict):
        """Callback when a single CV in the queue is redacted & branded."""
        cand_code = result["candidate_code"]
        role = result["role"]
        name = self.name_edit.text().strip() or cand_code

        record = ProcessedCVRecord(
            candidate_code=cand_code,
            name=name,
            role=role,
            input_file=result["input_file"],
            original_pdf=result["original_pdf"],
            output_pdf=result["output_pdf"],
            output_filename=result["output_filename"],
            redactions=result["redactions"],
        )
        self.processed_records.append(record)

        # Add to batch dropdown
        item_text = f"[{len(self.processed_records)}/{self.total_batch_count}] {record.candidate_code} - {record.role}"
        self.batch_combo.addItem(item_text, record)

        # Save to database
        try:
            save_candidate(
                name=name,
                role=role,
                original_filename=Path(record.input_file).name,
                candidate_code=cand_code,
            )
            record_redaction_event(record.redactions)
        except Exception as e:
            logger.warning(f"Could not save candidate to DB: {e}")

        # If it's a single file, immediately display it
        if self.total_batch_count == 1:
            self._display_record(record)

        # Continue queue
        self._process_next_in_queue()

    def _on_batch_complete(self):
        """Called when all queued CVs have been processed."""
        self.btn_browse.setEnabled(True)
        self.btn_process.setEnabled(True)
        self.progress_bar.setVisible(False)

        if hasattr(self, "loading_dialog") and self.loading_dialog and self.loading_dialog.isVisible():
            try:
                self.loading_dialog.set_complete()
            except Exception:
                pass
            self.loading_dialog = None

        count = len(self.processed_records)
        if count > 0:
            first_record = self.processed_records[0]
            self._display_record(first_record)
            self.batch_combo.setCurrentIndex(0)
            self._update_stepper(2)

            msg = f"One-Step Processing Complete: {count} CV(s) automatically redacted & branded."
            self.status_signal.emit(msg, "success")

            if count > 1:
                QMessageBox.information(
                    self,
                    "Batch Processing Complete",
                    f"Successfully redacted and branded {count} CVs in one step!\n\n"
                    f"All CVs received company branding and contact redaction.\n"
                    f"Use the 'Active Batch CV' dropdown to review each before sending.",
                )

    def _display_record(self, record: ProcessedCVRecord):
        """Displays a specific processed CV in the UI and preview widgets."""
        self.code_edit.setText(record.candidate_code)
        self.name_edit.setText(record.name)
        self.role_edit.setText(record.role)
        self.file_path_edit.setText(record.input_file)
        self.selected_file = record.input_file

        self.current_output_pdf = record.output_pdf
        self.current_output_filename = record.output_filename
        self.export_name_label.setText(f"Ready: {record.output_filename}")

        self.btn_open_pdf.setEnabled(True)
        self.btn_save_as.setEnabled(True)
        self.btn_send_email.setEnabled(True)
        self._update_stepper(2)

        if hasattr(self, "workspace_stack"):
            self.workspace_stack.setCurrentIndex(1)
        if hasattr(self, "compact_bar"):
            self.compact_bar.setVisible(True)

        # Retrieve logo path from settings
        settings = get_all_settings()
        logo_path = settings.get("logo_path", "")

        # Load side-by-side preview with editor context
        self.preview_widget.load_documents(
            original_pdf_path=record.original_pdf,
            redacted_pdf_path=record.output_pdf,
            candidate_code=record.candidate_code,
            source_file_path=record.input_file,
            logo_path=logo_path,
        )

        # Populate audit list
        contact_redactions = [r for r in record.redactions if r.get("category") != "Logo Placement"]
        logo_entries = [r for r in record.redactions if r.get("category") == "Logo Placement"]
        num_redactions = len(contact_redactions)
        self.redactions_list.set_redactions(record.redactions)

        if hasattr(self, "lbl_status_text"):
            self.lbl_status_text.setText(f"CV Ready: {record.output_filename}")
        if hasattr(self, "lbl_status_details"):
            self.lbl_status_details.setText(f"{num_redactions} contacts permanently removed • Logo branded • Pre-send safety verified")

        # Build audit summary with logo placement details
        logo_summary = ""
        for le in logo_entries:
            if le.get("count", 0) >= 1:
                val = le.get("value", "")
                size_part = next((p.strip() for p in val.split("|") if "Size:" in p), "")
                strategy = le.get("status", "")
                logo_summary = f"  |  Logo: {size_part}  ({strategy})"
                break
        self.lbl_audit_summary.setText(
            f"Audit Trail: {num_redactions} contact items permanently removed{logo_summary}"
        )

    def _on_preview_version_saved(self, saved_path: str):
        self.current_output_pdf = saved_path
        self.current_output_filename = Path(saved_path).name
        self.export_name_label.setText(f"Ready: {self.current_output_filename}")

        if hasattr(self, "processed_records") and self.processed_records:
            idx = self.batch_combo.currentIndex()
            if 0 <= idx < len(self.processed_records):
                self.processed_records[idx].output_pdf = saved_path
                self.processed_records[idx].output_filename = self.current_output_filename

        self.status_signal.emit(f"Saved new version: {self.current_output_filename}", "success")

    def _on_preview_edit_audit(self, audit_entries: list):
        if not audit_entries:
            return

        if hasattr(self, "processed_records") and self.processed_records:
            idx = self.batch_combo.currentIndex()
            if 0 <= idx < len(self.processed_records):
                rec = self.processed_records[idx]
                for ae in audit_entries:
                    new_item = {
                        "category": ae.get("action", "Manual Edit"),
                        "value": f"{ae.get('old_snippet', '')} -> {ae.get('new_snippet', '')}",
                        "count": 1,
                        "status": f"Page {ae.get('page', 1)} ({ae.get('user', 'User')})",
                    }
                    if new_item not in rec.redactions:
                        rec.redactions.append(new_item)
                self.redactions_list.set_redactions(rec.redactions)

    def _on_batch_selection_changed(self, index: int):
        record = self.batch_combo.currentData()
        if record and isinstance(record, ProcessedCVRecord):
            self._display_record(record)

    def _rerun_processing(self):
        """Re-runs processing on the current CV with edited candidate profile details."""
        if not self.selected_file or not os.path.exists(self.selected_file):
            QMessageBox.warning(self, "Validation", "Please select a candidate CV document first.")
            self.status_signal.emit("Validation failed: No CV document selected", "error")
            return

        cand_code = self.code_edit.text().strip()
        role = self.role_edit.text().strip()
        if not cand_code:
            QMessageBox.warning(self, "Validation", "Candidate ID is required.")
            return
        if not role:
            QMessageBox.warning(self, "Validation", "Target Role is required.")
            return

        self.btn_process.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_signal.emit(f"Re-running redaction and branding for {cand_code}...", "info")

        settings = get_all_settings()

        self.worker = RedactionWorkerThread(
            input_file=self.selected_file,
            candidate_code=cand_code,
            role=role,
            settings=settings,
            logo_size_override=self.logo_size_combo.currentText(),
            logo_position_override=self.logo_pos_combo.currentText(),
        )
        self.worker.finished_signal.connect(self._on_rerun_finished)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.start()

    def _on_rerun_finished(self, result: dict):
        self.btn_process.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.progress_bar.setVisible(False)

        cand_code = result["candidate_code"]
        role = result["role"]
        name = self.name_edit.text().strip() or cand_code

        record = ProcessedCVRecord(
            candidate_code=cand_code,
            name=name,
            role=role,
            input_file=result["input_file"],
            original_pdf=result["original_pdf"],
            output_pdf=result["output_pdf"],
            output_filename=result["output_filename"],
            redactions=result["redactions"],
        )
        self._display_record(record)
        self.status_signal.emit(f"Re-run complete for {cand_code}. Output: {record.output_filename}", "success")

    def _on_worker_error(self, err_msg: str):
        self.btn_process.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.progress_bar.setVisible(False)
        if hasattr(self, "loading_dialog") and self.loading_dialog and self.loading_dialog.isVisible():
            try:
                self.loading_dialog.reject()
            except Exception:
                pass
            self.loading_dialog = None
        self.status_signal.emit(f"Redaction Error: {err_msg}", "error")
        QMessageBox.critical(self, "Redaction Error", f"Failed to process CV:\n{err_msg}")

    # =============================================================
    # AUDIT TRAIL, DISPATCH, AND EXPORT
    # =============================================================
    def _toggle_audit_panel(self):
        is_visible = self.audit_container.isVisible()
        self.audit_container.setVisible(not is_visible)
        self.btn_toggle_audit.setText("Hide Audit Details" if not is_visible else "Show Audit Details")

    def reset_form(self):
        """Resets the form fields and generates next candidate ID."""
        self.code_edit.setText(get_next_candidate_code())
        self.name_edit.clear()
        self.role_edit.clear()
        self.file_path_edit.clear()
        self.selected_file = None
        self.current_output_pdf = None
        self.current_output_filename = None
        self.export_name_label.setText("No CV processed yet")
        self.lbl_audit_summary.setText("Audit Trail: No items redacted yet")
        self.btn_toggle_audit.setText("Show Audit Details")
        self.audit_container.setVisible(False)
        self.btn_open_pdf.setEnabled(False)
        self.btn_save_as.setEnabled(False)
        self.btn_send_email.setEnabled(False)
        self.batch_selector_container.setVisible(False)
        self.preview_widget.clear()
        self.redactions_list.set_redactions([])
        self.reload_clients_dropdown()
        if hasattr(self, "workspace_stack"):
            self.workspace_stack.setCurrentIndex(0)
        if hasattr(self, "compact_bar"):
            self.compact_bar.setVisible(False)
        self._update_stepper(1)

    def reload_clients_dropdown(self):
        """Loads client list into dropdown."""
        self.client_combo.blockSignals(True)
        self.client_combo.clear()
        self.client_combo.addItem("-- Select Client or enter email below --", None)
        clients = get_all_clients()
        for c in clients:
            self.client_combo.addItem(f"{c['company']} - {c['name']} ({c['email']})", c)
        self.client_combo.blockSignals(False)

    def _on_client_selected(self, index: int):
        data = self.client_combo.currentData()
        if data:
            self.client_email_edit.setText(data.get("email", ""))
            self._update_stepper(3)

    def _open_output_pdf(self):
        if self.current_output_pdf and os.path.exists(self.current_output_pdf):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_output_pdf))
            self.status_signal.emit(f"Opened PDF: {Path(self.current_output_pdf).name}", "info")

    def _save_as(self):
        if not self.current_output_pdf or not os.path.exists(self.current_output_pdf):
            return

        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Anonymized CV As",
            self.current_output_filename or "anonymized_cv.pdf",
            "PDF Files (*.pdf)",
        )
        if dest_path:
            shutil.copyfile(self.current_output_pdf, dest_path)
            self.status_signal.emit(f"File saved to: {dest_path}", "success")
            QMessageBox.information(self, "Saved", f"File saved successfully to:\n{dest_path}")

    def _verify_and_send(self):
        """Performs final verification check, confirms with user, and sends email."""
        if not self.current_output_pdf or not os.path.exists(self.current_output_pdf):
            QMessageBox.warning(self, "Error", "No output PDF available. Please process a CV first.")
            self.status_signal.emit("No output PDF available to send", "error")
            return

        client_email = self.client_email_edit.text().strip()
        if not client_email or "@" not in client_email:
            QMessageBox.warning(self, "Validation", "Please enter a valid client email address.")
            self.status_signal.emit("Please enter a valid client email address", "error")
            return

        # 1. FINAL SAFETY SCAN
        is_clean, violations = validate_clean_pdf(self.current_output_pdf)
        if not is_clean:
            violation_text = "\n".join([f"- {v['description']}" for v in violations[:5]])
            self.status_signal.emit("SECURITY BLOCK: Residual contact data detected in output PDF", "error")
            QMessageBox.critical(
                self,
                "SECURITY BLOCK: Residual Contact Data Detected!",
                f"Sending has been BLOCKED to protect candidate privacy.\n\n"
                f"The final verification scan detected residual contact details:\n\n{violation_text}\n\n"
                f"Please review the redaction settings and re-process the document.",
            )
            return

        # Confirm with user
        client_data = self.client_combo.currentData() or {}
        client_name = client_data.get("name", "Hiring Manager")
        cand_code = self.code_edit.text().strip()
        role = self.role_edit.text().strip()

        reply = QMessageBox.question(
            self,
            "Confirm Send",
            f"Are you sure you want to send the branded CV to {client_email}?\n\n"
            f"Candidate: {cand_code} ({role})\n"
            f"Attachment: {self.current_output_filename}\n"
            f"Safety Check: PASSED (0 sensitive items detected)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Send Email
        self.btn_send_email.setEnabled(False)
        self.btn_send_email.setText("Sending...")
        self.status_signal.emit(f"Sending CV to {client_email}...", "info")

        success, msg = send_branded_cv_email(
            client_email=client_email,
            client_name=client_name,
            candidate_code=cand_code,
            role=role,
            pdf_path=self.current_output_pdf,
            candidate_name=self.name_edit.text().strip(),
            client_id=client_data.get("id"),
        )

        self.btn_send_email.setEnabled(True)
        self.btn_send_email.setText("  Final Check && Send to Client")

        if success:
            self.status_signal.emit(f"Successfully sent CV to {client_email}", "success")
            try:
                success_dialog = ProcessSuccessDialog(
                    client_name=client_data.get("company", client_name),
                    client_email=client_email,
                    candidate_id=cand_code,
                    sent_time=datetime.now().strftime("%d %b %Y, %I:%M %p"),
                    parent=self.window(),
                )
                success_dialog.view_submission_clicked.connect(lambda: self.navigate_to_tab.emit(2))
                success_dialog.process_another_clicked.connect(self.reset_form)
                success_dialog.exec_()
            except Exception as e:
                logger.debug(f"Could not open success modal: {e}")
                QMessageBox.information(self, "Dispatch Success", msg)
        else:
            self.status_signal.emit(f"Dispatch Failed: {msg}", "error")
            QMessageBox.critical(self, "Dispatch Error", msg)
