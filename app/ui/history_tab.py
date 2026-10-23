"""
Submissions History Tab for ScaleXPro CV-Modifier:
Matches Screen 6 on the design board:
- Filter chips (All / Sent / Failed)
- Live search bar
- Primary orange Export CSV button
- Data table with colored status badges (dot + text)
- Showing X of Y submissions footer
"""

import os
import csv
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLineEdit,
    QLabel,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QColor
import qtawesome as qta

from app.database import get_submissions
from app.config import EXPORTS_DIR
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


class HistoryTab(QWidget):
    """Submissions audit trail with search, status filter chips, and CSV export."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = "ALL"
        self.submissions = []
        self._setup_ui()
        self.refresh_history()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        # Header Title
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_title = QLabel("Candidate Submissions History")
        lbl_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 700;")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Complete immutable audit log of all candidate profile dispatches and client interactions.")
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")
        title_col.addWidget(lbl_sub)
        layout.addLayout(title_col)

        # Filter & Action Bar Card
        top_bar = CardWidget(radius=20, enable_shadow=True)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(18, 14, 18, 14)
        top_layout.setSpacing(14)

        # Filter Chips (All, Sent, Failed)
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)

        self.btn_filter_all = QPushButton("All")
        self.btn_filter_all.setCursor(Qt.PointingHandCursor)
        self.btn_filter_all.setFixedHeight(34)
        self.btn_filter_all.clicked.connect(lambda: self._set_filter("ALL"))
        chips_layout.addWidget(self.btn_filter_all)

        self.btn_filter_sent = QPushButton("Sent")
        self.btn_filter_sent.setCursor(Qt.PointingHandCursor)
        self.btn_filter_sent.setFixedHeight(34)
        self.btn_filter_sent.clicked.connect(lambda: self._set_filter("SENT"))
        chips_layout.addWidget(self.btn_filter_sent)

        self.btn_filter_failed = QPushButton("Failed")
        self.btn_filter_failed.setCursor(Qt.PointingHandCursor)
        self.btn_filter_failed.setFixedHeight(34)
        self.btn_filter_failed.clicked.connect(lambda: self._set_filter("FAILED"))
        chips_layout.addWidget(self.btn_filter_failed)

        top_layout.addLayout(chips_layout)

        # Search Bar with magnifying glass
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E8E5F7;
                border-radius: 12px;
            }}
            QFrame:focus-within {{
                border-color: {COLOR_PRIMARY};
            }}
        """)
        search_l = QHBoxLayout(search_frame)
        search_l.setContentsMargins(12, 0, 12, 0)
        search_l.setSpacing(8)

        lbl_s_icon = QLabel()
        lbl_s_icon.setPixmap(qta.icon("fa5s.search", color=COLOR_TEXT_MUTED).pixmap(13, 13))
        lbl_s_icon.setStyleSheet("background: transparent; border: none;")
        search_l.addWidget(lbl_s_icon)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search candidate, role, client, or email...")
        self.search_box.setToolTip("Filter submissions by candidate ID, role, or client")
        self.search_box.setMinimumWidth(260)
        self.search_box.setFixedHeight(36)
        self.search_box.setStyleSheet(f"border: none; background: transparent; font-size: 13px; color: {COLOR_NAVY};")
        self.search_box.textChanged.connect(self.refresh_history)
        search_l.addWidget(self.search_box)
        top_layout.addWidget(search_frame)

        top_layout.addStretch()

        # Refresh Button
        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color=COLOR_TEXT_SECONDARY))
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(38)
        self.btn_refresh.setToolTip("Reload candidate submissions from database")
        self.btn_refresh.setStyleSheet(f"""
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
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.btn_refresh.clicked.connect(self.refresh_history)
        top_layout.addWidget(self.btn_refresh)

        # Export CSV Button (ScaleXPro Orange CTA)
        self.btn_export_csv = QPushButton(" Export CSV")
        self.btn_export_csv.setIcon(qta.icon("fa5s.file-csv", color="#FFFFFF"))
        self.btn_export_csv.setCursor(Qt.PointingHandCursor)
        self.btn_export_csv.setFixedHeight(38)
        self.btn_export_csv.setToolTip("Export the current submissions list to a CSV spreadsheet")
        self.btn_export_csv.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 0 18px;
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
        self.btn_export_csv.clicked.connect(self._export_to_csv)
        top_layout.addWidget(self.btn_export_csv)

        layout.addWidget(top_bar)

        # Table Container Card
        table_card = CardWidget(radius=20)
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(18, 18, 18, 16)
        tc_layout.setSpacing(12)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Candidate ID",
            "Role",
            "Client Name",
            "Client Email",
            "Status",
            "Date & Time",
            "Actions",
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 110)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 140)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
                color: {COLOR_TEXT_PRIMARY};
                gridline-color: transparent;
            }}
            QHeaderView::section {{
                background-color: #F8FAFC;
                color: {COLOR_TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                border: none;
                border-bottom: 1px solid {COLOR_BORDER};
                padding: 10px 14px;
            }}
            QTableWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
            QTableWidget::item:hover {{
                background-color: #F8FAFC;
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_PRIMARY_TINT};
            }}
        """)
        tc_layout.addWidget(self.table)

        # Footer Row: "Showing X of Y" + Pagination
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(4, 2, 4, 2)

        self.lbl_showing_count = QLabel("Showing 0 of 0 submissions")
        self.lbl_showing_count.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")
        footer_row.addWidget(self.lbl_showing_count)

        footer_row.addStretch()

        lbl_page = QLabel("Page 1 of 1")
        lbl_page.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        footer_row.addWidget(lbl_page)

        btn_prev = QPushButton("<")
        btn_prev.setFixedSize(26, 26)
        btn_prev.setEnabled(False)
        btn_prev.setStyleSheet(f"border: 1px solid {COLOR_BORDER}; border-radius: 4px; color: {COLOR_TEXT_MUTED}; background: #FFFFFF;")
        footer_row.addWidget(btn_prev)

        btn_next = QPushButton(">")
        btn_next.setFixedSize(26, 26)
        btn_next.setEnabled(False)
        btn_next.setStyleSheet(f"border: 1px solid {COLOR_BORDER}; border-radius: 4px; color: {COLOR_TEXT_MUTED}; background: #FFFFFF;")
        footer_row.addWidget(btn_next)

        tc_layout.addLayout(footer_row)
        layout.addWidget(table_card, stretch=1)

    def _set_filter(self, filter_status: str):
        self.current_filter = filter_status
        self._update_chip_styles()
        self.refresh_history()

    def _update_chip_styles(self):
        active_style = f"""
            QPushButton {{
                background-color: {COLOR_LAVENDER};
                color: {COLOR_PURPLE_DEEP};
                border: 1px solid #C4B5FD;
                border-radius: 17px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 12px;
            }}
        """
        inactive_style = f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid #E8E5F7;
                border-radius: 17px;
                padding: 0 16px;
                font-weight: 500;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
                border-color: {COLOR_PRIMARY};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """
        self.btn_filter_all.setStyleSheet(active_style if self.current_filter == "ALL" else inactive_style)
        self.btn_filter_sent.setStyleSheet(active_style if self.current_filter == "SENT" else inactive_style)
        self.btn_filter_failed.setStyleSheet(active_style if self.current_filter == "FAILED" else inactive_style)

    def refresh_history(self):
        """Reloads submissions from SQLite database."""
        self._update_chip_styles()
        search = self.search_box.text().strip()
        self.submissions = get_submissions(search_query=search, status_filter=self.current_filter)

        total_all = len(get_submissions(search_query="", status_filter="ALL"))
        shown = len(self.submissions)
        self.lbl_showing_count.setText(f"Showing {shown} of {total_all} submissions")

        self.table.setRowCount(len(self.submissions))

        for row_idx, sub in enumerate(self.submissions):
            self.table.setRowHeight(row_idx, 48)

            # 0: Candidate ID
            c_item = QTableWidgetItem(sub.get("candidate_code", ""))
            c_item.setForeground(QColor(COLOR_PRIMARY))
            self.table.setItem(row_idx, 0, c_item)

            # 1: Role
            r_item = QTableWidgetItem(sub.get("candidate_role", ""))
            r_item.setForeground(QColor(COLOR_NAVY))
            self.table.setItem(row_idx, 1, r_item)

            # 2: Client Name
            cl_item = QTableWidgetItem(sub.get("client_name", ""))
            cl_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.table.setItem(row_idx, 2, cl_item)

            # 3: Email
            em_item = QTableWidgetItem(sub.get("client_email", ""))
            em_item.setForeground(QColor(COLOR_TEXT_MUTED))
            self.table.setItem(row_idx, 3, em_item)

            # 4: Status Badge (Dot + Pill)
            status = str(sub.get("status", "")).upper()
            status_widget = QWidget()
            sw_layout = QHBoxLayout(status_widget)
            sw_layout.setContentsMargins(4, 4, 4, 4)
            sw_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            badge_frame = QFrame()
            bf_l = QHBoxLayout(badge_frame)
            bf_l.setContentsMargins(8, 3, 10, 3)
            bf_l.setSpacing(5)

            dot = QLabel()
            dot.setFixedSize(7, 7)
            dot.setStyleSheet("border-radius: 3px;")

            lbl_st = QLabel(status.capitalize())
            lbl_st.setStyleSheet("border: none; background: transparent; font-size: 11px; font-weight: 600;")

            if status == "SENT":
                badge_frame.setStyleSheet("""
                    background-color: #DDF5E8;
                    border: 1px solid #BBF7D0;
                    border-radius: 10px;
                """)
                dot.setStyleSheet("background-color: #3DBE7A; border-radius: 3px;")
                lbl_st.setStyleSheet("border: none; background: transparent; color: #166534; font-size: 11px; font-weight: 600;")
            elif status == "FAILED":
                badge_frame.setStyleSheet("""
                    background-color: #FEE2E2;
                    border: 1px solid #FECACA;
                    border-radius: 10px;
                """)
                dot.setStyleSheet("background-color: #EF4444; border-radius: 3px;")
                lbl_st.setStyleSheet("border: none; background: transparent; color: #B91C1C; font-size: 11px; font-weight: 600;")
            else:
                badge_frame.setStyleSheet("""
                    background-color: #E4E0FA;
                    border: 1px solid #DDD6F7;
                    border-radius: 10px;
                """)
                dot.setStyleSheet(f"background-color: {COLOR_PRIMARY}; border-radius: 3px;")
                lbl_st.setStyleSheet(f"border: none; background: transparent; color: {COLOR_PURPLE_DARK}; font-size: 11px; font-weight: 600;")

            bf_l.addWidget(dot)
            bf_l.addWidget(lbl_st)
            sw_layout.addWidget(badge_frame)
            self.table.setCellWidget(row_idx, 4, status_widget)

            # 5: Date
            d_item = QTableWidgetItem(sub.get("sent_at", ""))
            d_item.setForeground(QColor(COLOR_TEXT_MUTED))
            self.table.setItem(row_idx, 5, d_item)

            # 6: Action cell (Open PDF or Show Error)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            cv_path = sub.get("cv_path", "")
            btn_open = QPushButton(" Open PDF")
            btn_open.setIcon(qta.icon("fa5s.file-pdf", color=COLOR_PRIMARY))
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setEnabled(bool(cv_path and os.path.exists(cv_path)))
            btn_open.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_PRIMARY_TINT};
                    border-color: {COLOR_PRIMARY_BORDER};
                }}
                QPushButton:disabled {{
                    background-color: #F8FAFC;
                    color: {COLOR_TEXT_MUTED};
                    border-color: {COLOR_BORDER};
                }}
            """)
            btn_open.clicked.connect(lambda ch=False, p=cv_path: self._open_pdf(p))
            actions_layout.addWidget(btn_open)

            if sub.get("error_message"):
                btn_err = QPushButton("Error")
                btn_err.setStyleSheet(f"""
                    QPushButton {{
                        padding: 3px 8px;
                        font-size: 11px;
                        background-color: {COLOR_DANGER_TINT};
                        color: {COLOR_DANGER};
                        border: 1px solid {COLOR_DANGER_BORDER};
                        border-radius: 6px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: #FEE2E2;
                    }}
                """)
                err_text = sub.get("error_message")
                btn_err.clicked.connect(lambda ch=False, m=err_text: self._show_error(m))
                actions_layout.addWidget(btn_err)

            self.table.setCellWidget(row_idx, 6, actions_widget)

    def _open_pdf(self, path: str):
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "File Not Found", "The exported PDF file no longer exists on disk.")

    def _show_error(self, err_text: str):
        QMessageBox.critical(self, "Dispatch Error Details", f"Failed dispatch details:\n\n{err_text}")

    def _export_to_csv(self):
        if not self.submissions:
            QMessageBox.information(self, "Export", "No submissions to export.")
            return

        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Export Submissions to CSV",
            f"submissions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)",
        )
        if dest:
            try:
                with open(dest, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Timestamp",
                        "Candidate ID",
                        "Candidate Role",
                        "Client Name",
                        "Client Email",
                        "Status",
                        "CV Filename",
                        "CV Path",
                        "Error Details",
                    ])
                    for sub in self.submissions:
                        writer.writerow([
                            sub.get("sent_at", ""),
                            sub.get("candidate_code", ""),
                            sub.get("candidate_role", ""),
                            sub.get("client_name", ""),
                            sub.get("client_email", ""),
                            sub.get("status", ""),
                            sub.get("cv_filename", ""),
                            sub.get("cv_path", ""),
                            sub.get("error_message", ""),
                        ])
                QMessageBox.information(self, "Export Successful", f"Submissions history exported to:\n{dest}")
            except Exception as e:
                logger.error(f"Failed to export CSV: {e}")
                QMessageBox.critical(self, "Export Failed", f"Could not export CSV file:\n{e}")
