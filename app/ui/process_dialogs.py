"""
Modal Dialogs for ScaleXPro CV Processing Workflow:
- ProcessLoadingDialog: Soft lavender/purple centered card with progress bar + ticking animated checkmarks
- ProcessSuccessDialog: Celebration card with client summary, confetti particle burst, and orange CTA
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QBrush
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
    COLOR_CTA_PRESSED,
    COLOR_SUCCESS,
    COLOR_SUCCESS_TINT,
    COLOR_NAVY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    PASTEL_LAVENDER,
    PASTEL_MINT,
)
from app.ui.animations import ConfettiBurstWidget, is_animations_enabled


class ProcessLoadingDialog(QDialog):
    """
    Centered soft lavender/purple loading card over a dimmed translucent overlay:
    - Pastel circular file icon
    - 'Processing candidate CV...' heading
    - Subtitle description
    - Smooth purple progress bar
    - 4-step checklist with sequentially animated checkmarks
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(1200, 800)

        self._step_index = 0
        self._progress_val = 20

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Soft purple dimmed backdrop
        backdrop = QFrame()
        backdrop.setStyleSheet("background-color: rgba(30, 27, 75, 0.55);")
        b_layout = QVBoxLayout(backdrop)
        b_layout.setAlignment(Qt.AlignCenter)

        # Centered white 20px card
        card = QFrame()
        card.setFixedSize(450, 410)
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #ECEEF8;
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(107, 95, 181, 70))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(34, 30, 34, 30)
        c_layout.setSpacing(12)
        c_layout.setAlignment(Qt.AlignCenter)

        # Pastel Circular Icon
        icon_box = QFrame()
        icon_box.setFixedSize(54, 54)
        icon_box.setStyleSheet(f"""
            QFrame {{
                background-color: {PASTEL_LAVENDER};
                border-radius: 27px;
                border: none;
            }}
        """)
        ib_l = QVBoxLayout(icon_box)
        ib_l.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setPixmap(qta.icon("fa5s.file-alt", color=COLOR_PRIMARY).pixmap(24, 24))
        ic_lbl.setStyleSheet("background: transparent; border: none;")
        ib_l.addWidget(ic_lbl)
        c_layout.addWidget(icon_box, alignment=Qt.AlignCenter)

        # Title
        lbl_title = QLabel("Processing candidate CV...")
        lbl_title.setStyleSheet(f"background: transparent; border: none; color: {COLOR_NAVY}; font-size: 19px; font-weight: 800;")
        c_layout.addWidget(lbl_title, alignment=Qt.AlignCenter)

        # Subtitle
        lbl_sub = QLabel("Automatically removing personal details,\napplying adaptive branding & running safety checks.")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_SECONDARY}; font-size: 12px; line-height: 1.4;")
        c_layout.addWidget(lbl_sub, alignment=Qt.AlignCenter)

        # Progress bar + Percentage
        prog_row = QHBoxLayout()
        prog_row.setSpacing(10)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(25)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #ECEEF8;
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_PRIMARY};
                border-radius: 4px;
            }}
        """)
        prog_row.addWidget(self.progress_bar, stretch=1)

        self.lbl_pct = QLabel("25%")
        self.lbl_pct.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-size: 12px; font-weight: 700;")
        prog_row.addWidget(self.lbl_pct)
        c_layout.addLayout(prog_row)

        c_layout.addSpacing(6)

        # 4-Step Checklist with Animated Ticking Checkmarks
        self.steps_list = [
            "Parsing document layout & structure",
            "Permanently redacting contact details & labels",
            "Applying adaptive ScaleXPro header logo",
            "Running final offline privacy verification",
        ]
        self.item_widgets = []

        steps_box = QFrame()
        steps_box.setStyleSheet("""
            background-color: #F8F9FE;
            border: 1px solid #ECEEF8;
            border-radius: 14px;
            padding: 8px 12px;
        """)
        s_layout = QVBoxLayout(steps_box)
        s_layout.setSpacing(8)

        for text in self.steps_list:
            r = QHBoxLayout()
            r.setSpacing(10)
            ic = QLabel()
            ic.setPixmap(qta.icon("fa5s.circle", color="#CBD5E1").pixmap(12, 12))
            ic.setStyleSheet("background: transparent; border: none;")
            r.addWidget(ic)

            txt = QLabel(text)
            txt.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_MUTED}; font-size: 12px;")
            r.addWidget(txt, stretch=1)
            s_layout.addLayout(r)
            self.item_widgets.append((ic, txt))

        c_layout.addWidget(steps_box)

        b_layout.addWidget(card)
        root_layout.addWidget(backdrop)

        # Timer to advance simulated steps smoothly
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_step)
        self._timer.start(350)

    def _advance_step(self):
        if self._step_index < len(self.item_widgets):
            ic, txt = self.item_widgets[self._step_index]
            ic.setPixmap(qta.icon("fa5s.check-circle", color=COLOR_SUCCESS).pixmap(15, 15))
            txt.setStyleSheet(f"background: transparent; border: none; color: {COLOR_NAVY}; font-size: 12px; font-weight: 600;")
            self._step_index += 1
            self._progress_val = min(100, int((self._step_index / len(self.item_widgets)) * 100))
            self.progress_bar.setValue(self._progress_val)
            self.lbl_pct.setText(f"{self._progress_val}%")
        else:
            self._timer.stop()

    def complete(self):
        self._timer.stop()
        self.progress_bar.setValue(100)
        self.lbl_pct.setText("100%")
        for ic, txt in self.item_widgets:
            ic.setPixmap(qta.icon("fa5s.check-circle", color=COLOR_SUCCESS).pixmap(15, 15))
            txt.setStyleSheet(f"background: transparent; border: none; color: {COLOR_NAVY}; font-size: 12px; font-weight: 600;")
        self.accept()


class ProcessSuccessDialog(QDialog):
    """
    Celebration card with confetti particle burst:
    - Celebratory green check circle
    - 'CV Processed Successfully!' heading
    - Detail box with Client, Email, Candidate ID, Sent at
    - Primary ScaleXPro Orange button 'View Submission' and lavender 'Process Another CV'
    """
    view_submission_clicked = Signal()
    process_another_clicked = Signal()

    def __init__(
        self,
        client_name: str = "Acme Foods Pvt Ltd",
        client_email: str = "client@acmefoods.com",
        candidate_id: str = "CAND-1042",
        sent_time: str = "22 Oct 2026, 10:24 AM",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.resize(1200, 800)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        backdrop = QFrame()
        backdrop.setStyleSheet("background-color: rgba(30, 27, 75, 0.55);")
        b_layout = QVBoxLayout(backdrop)
        b_layout.setAlignment(Qt.AlignCenter)

        # Centered white card
        card = QFrame()
        card.setFixedSize(460, 450)
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #ECEEF8;
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(107, 95, 181, 70))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(34, 30, 34, 30)
        c_layout.setSpacing(14)
        c_layout.setAlignment(Qt.AlignCenter)

        # Big Celebratory Green Checkmark Circle
        check_circle = QFrame()
        check_circle.setFixedSize(64, 64)
        check_circle.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_SUCCESS};
                border-radius: 32px;
                border: none;
            }}
        """)
        cc_l = QVBoxLayout(check_circle)
        cc_l.setContentsMargins(0, 0, 0, 0)
        cc_ic = QLabel()
        cc_ic.setAlignment(Qt.AlignCenter)
        cc_ic.setPixmap(qta.icon("fa5s.check", color="#FFFFFF").pixmap(28, 28))
        cc_ic.setStyleSheet("background: transparent; border: none;")
        cc_l.addWidget(cc_ic)
        c_layout.addWidget(check_circle, alignment=Qt.AlignCenter)

        # Title
        lbl_t = QLabel("CV Processed Successfully!")
        lbl_t.setStyleSheet(f"background: transparent; border: none; color: {COLOR_NAVY}; font-size: 20px; font-weight: 800;")
        c_layout.addWidget(lbl_t, alignment=Qt.AlignCenter)

        # Subtitle
        lbl_sub = QLabel("Your anonymized CV has been sent to the client.")
        lbl_sub.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")
        c_layout.addWidget(lbl_sub, alignment=Qt.AlignCenter)

        # Detail Box
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #F8F9FE;
                border: 1px solid #ECEEF8;
                border-radius: 12px;
                padding: 6px;
            }
        """)
        b_box_l = QVBoxLayout(box)
        b_box_l.setContentsMargins(14, 10, 14, 10)
        b_box_l.setSpacing(8)

        details = [
            ("fa5s.building", "Client", client_name),
            ("fa5s.envelope", "Email", client_email),
            ("fa5s.id-badge", "Candidate ID", candidate_id),
            ("fa5s.clock", "Sent at", sent_time),
        ]
        for icon_name, label_txt, val_txt in details:
            r = QHBoxLayout()
            r.setSpacing(8)
            ic = QLabel()
            ic.setPixmap(qta.icon(icon_name, color=COLOR_PRIMARY).pixmap(13, 13))
            ic.setStyleSheet("background: transparent; border: none;")
            r.addWidget(ic)

            lbl = QLabel(f"{label_txt}:")
            lbl.setStyleSheet(f"background: transparent; border: none; color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
            r.addWidget(lbl)

            val = QLabel(val_txt)
            val.setStyleSheet(f"background: transparent; border: none; color: {COLOR_NAVY}; font-size: 12px; font-weight: 700;")
            r.addWidget(val)
            r.addStretch()
            b_box_l.addLayout(r)

        c_layout.addWidget(box)
        c_layout.addSpacing(6)

        # Buttons Row: Primary Orange CTA + Secondary Lavender Action
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_view = QPushButton("View Submission")
        self.btn_view.setCursor(Qt.PointingHandCursor)
        self.btn_view.setFixedHeight(42)
        self.btn_view.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                font-weight: 700;
                font-size: 13.5px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_CTA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_CTA_PRESSED};
            }}
        """)
        self.btn_view.clicked.connect(self._on_view_clicked)
        btn_row.addWidget(self.btn_view, stretch=1)

        self.btn_another = QPushButton("Process Another CV")
        self.btn_another.setCursor(Qt.PointingHandCursor)
        self.btn_another.setFixedHeight(42)
        self.btn_another.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_LAVENDER_LIGHT};
                color: {COLOR_PRIMARY};
                border: 1px solid #DDD6F7;
                border-radius: 12px;
                font-weight: 700;
                font-size: 13.5px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LAVENDER};
                color: {COLOR_PURPLE_DEEP};
            }}
        """)
        self.btn_another.clicked.connect(self._on_another_clicked)
        btn_row.addWidget(self.btn_another, stretch=1)

        c_layout.addLayout(btn_row)

        b_layout.addWidget(card)
        root_layout.addWidget(backdrop)

        # Confetti Overlay
        self.confetti = ConfettiBurstWidget(self)

    def showEvent(self, event):
        super().showEvent(event)
        # Trigger confetti burst!
        QTimer.singleShot(150, lambda: self.confetti.burst(count=80))

    def _on_view_clicked(self):
        self.view_submission_clicked.emit()
        self.accept()

    def _on_another_clicked(self):
        self.process_another_clicked.emit()
        self.accept()
