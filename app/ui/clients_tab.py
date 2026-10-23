"""
Clients Directory Tab for ScaleXPro CV-Modifier:
Matches Screen 7 and Screen 7b (Add New Client modal) on the design board:
- Search and "+ Add New Client" button (ScaleXPro Primary Orange #F28A1E)
- Clean table with Company, Contact Person, Email, Status badge (Active/Inactive), and Actions
- ClientDialog modal with Client Name, Email, Contact Person, Status, Notes
"""

from typing import Optional, Dict, Any
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
    QMessageBox,
    QDialog,
    QFormLayout,
    QTextEdit,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
import qtawesome as qta

from app.database import get_all_clients, add_client, update_client, delete_client
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


class ClientDialog(QDialog):
    """Screen 7b: Modal dialog to add or edit client records."""
    def __init__(self, client_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.client_data = client_data
        is_edit = client_data is not None
        self.setWindowTitle("Edit Client Account" if is_edit else "Add New Client")
        self.setFixedWidth(460)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                border: 1px solid #E8E5F7;
                border-radius: 20px;
            }}
            QLabel {{
                color: {COLOR_TEXT_SECONDARY};
                font-weight: 600;
                font-size: 12px;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: #FFFFFF;
                border: 1px solid #E8E5F7;
                border-radius: 10px;
                color: {COLOR_NAVY};
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Title + Subtitle
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        lbl_head = QLabel("Edit Client" if is_edit else "Add New Client")
        lbl_head.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 18px; font-weight: 700;")
        header_box.addWidget(lbl_head)

        lbl_sub = QLabel("Add a client to send branded CVs directly.")
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        header_box.addWidget(lbl_sub)
        layout.addLayout(header_box)

        form = QFormLayout()
        form.setSpacing(14)

        self.company_edit = QLineEdit()
        self.company_edit.setPlaceholderText("e.g. Acme Foods Pvt Ltd")

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("e.g. client@acmefoods.com")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Sarah Jenkins")

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Hiring manager details, department, or preferences...")
        self.notes_edit.setMaximumHeight(70)

        form.addRow("Client Name *:", self.company_edit)
        form.addRow("Client Email *:", self.email_edit)
        form.addRow("Contact Person:", self.name_edit)
        form.addRow("Status:", self.status_combo)
        form.addRow("Notes / Role:", self.notes_edit)

        layout.addLayout(form)

        # Pre-fill if editing
        if client_data:
            self.company_edit.setText(client_data.get("company", ""))
            self.name_edit.setText(client_data.get("name", ""))
            self.email_edit.setText(client_data.get("email", ""))
            self.notes_edit.setText(client_data.get("notes", ""))
            st = client_data.get("status", "Active")
            idx = self.status_combo.findText(st)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

        layout.addSpacing(6)

        # Buttons Row
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(12)
        btns_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid #E8E5F7;
                border-radius: 10px;
                padding: 0 18px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
                border-color: {COLOR_PRIMARY};
            }}
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btns_layout.addWidget(self.btn_cancel)

        btn_text = "Save Changes" if is_edit else "Add Client"
        self.btn_save = QPushButton(btn_text)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(38)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_CTA};
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 0 22px;
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
        self.btn_save.clicked.connect(self._on_save)
        btns_layout.addWidget(self.btn_save)

        layout.addLayout(btns_layout)

    def _on_save(self):
        company = self.company_edit.text().strip()
        email = self.email_edit.text().strip()
        if not company:
            QMessageBox.warning(self, "Validation", "Client Name (Company) is required.")
            return
        if not email or "@" not in email:
            QMessageBox.warning(self, "Validation", "A valid Client Email is required.")
            return
        self.accept()

    def get_data(self) -> Dict[str, str]:
        return {
            "company": self.company_edit.text().strip(),
            "name": self.name_edit.text().strip() or self.company_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "status": self.status_combo.currentText(),
        }


class ClientsTab(QWidget):
    """Client directory tab for managing corporate hiring contacts."""
    client_list_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clients = []
        self._setup_ui()
        self.refresh_clients()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(16)

        # Header Title
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_title = QLabel("Client Accounts Directory")
        lbl_title.setStyleSheet(f"color: {COLOR_NAVY}; font-size: 20px; font-weight: 700;")
        title_col.addWidget(lbl_title)

        lbl_sub = QLabel("Manage corporate partners and client email contacts for instant branded CV dispatch.")
        lbl_sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 13px;")
        title_col.addWidget(lbl_sub)
        layout.addLayout(title_col)

        # Search and Action Bar
        action_card = CardWidget(radius=20, enable_shadow=True)
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(18, 14, 18, 14)
        action_layout.setSpacing(14)

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
        self.search_box.setPlaceholderText("Filter by client name, contact, or email...")
        self.search_box.setToolTip("Filter client directory by company or contact person")
        self.search_box.setMinimumWidth(300)
        self.search_box.setFixedHeight(36)
        self.search_box.setStyleSheet(f"border: none; background: transparent; font-size: 13px; color: {COLOR_NAVY};")
        self.search_box.textChanged.connect(self._filter_clients)
        search_l.addWidget(self.search_box)
        action_layout.addWidget(search_frame)

        action_layout.addStretch()

        # Add New Client Button (ScaleXPro Orange CTA)
        self.btn_add = QPushButton(" + Add New Client")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFixedHeight(38)
        self.btn_add.setToolTip("Register a new corporate client account for CV dispatches")
        self.btn_add.setStyleSheet(f"""
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
        self.btn_add.clicked.connect(self._on_add_client)
        action_layout.addWidget(self.btn_add)

        layout.addWidget(action_card)

        # Table Container Card
        table_card = CardWidget(radius=20)
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(18, 18, 18, 16)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Company Name",
            "Contact Person",
            "Client Email",
            "Status",
            "Notes / Role",
            "Actions",
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 110)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 185)
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
        layout.addWidget(table_card, stretch=1)

    def refresh_clients(self):
        """Loads all client records from SQLite."""
        self.clients = get_all_clients()
        self._filter_clients()

    def _filter_clients(self):
        query = self.search_box.text().strip().lower()
        filtered = []
        for c in self.clients:
            if not query or (
                query in c.get("name", "").lower()
                or query in c.get("company", "").lower()
                or query in c.get("email", "").lower()
                or query in c.get("notes", "").lower()
            ):
                filtered.append(c)

        self._render_table(filtered)

    def _render_table(self, client_list):
        self.table.setRowCount(len(client_list))

        for row_idx, client in enumerate(client_list):
            self.table.setRowHeight(row_idx, 48)

            # 0: Company Name
            comp_item = QTableWidgetItem(f"  {client.get('company', '')}")
            comp_item.setIcon(qta.icon("fa5s.building", color=COLOR_PRIMARY))
            comp_item.setForeground(QColor(COLOR_NAVY))
            self.table.setItem(row_idx, 0, comp_item)

            # 1: Contact Person
            name_item = QTableWidgetItem(client.get("name", ""))
            name_item.setForeground(QColor(COLOR_TEXT_PRIMARY))
            self.table.setItem(row_idx, 1, name_item)

            # 2: Email
            email_item = QTableWidgetItem(client.get("email", ""))
            email_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.table.setItem(row_idx, 2, email_item)

            # 3: Status Badge
            status_text = client.get("status") or "Active"
            st_widget = QWidget()
            stw_l = QHBoxLayout(st_widget)
            stw_l.setContentsMargins(4, 4, 4, 4)
            stw_l.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            st_pill = QFrame()
            st_pill_l = QHBoxLayout(st_pill)
            st_pill_l.setContentsMargins(8, 3, 10, 3)
            st_pill_l.setSpacing(5)

            st_dot = QLabel()
            st_dot.setFixedSize(7, 7)

            lbl_st = QLabel(status_text)
            lbl_st.setStyleSheet("border: none; background: transparent; font-size: 11px; font-weight: 600;")

            if status_text.lower() == "active":
                st_pill.setStyleSheet("""
                    background-color: #DDF5E8;
                    border: 1px solid #BBF7D0;
                    border-radius: 10px;
                """)
                st_dot.setStyleSheet("background-color: #3DBE7A; border-radius: 3px;")
                lbl_st.setStyleSheet("border: none; background: transparent; color: #166534; font-size: 11px; font-weight: 600;")
            else:
                st_pill.setStyleSheet("""
                    background-color: #E4E0FA;
                    border: 1px solid #DDD6F7;
                    border-radius: 10px;
                """)
                st_dot.setStyleSheet(f"background-color: {COLOR_PRIMARY}; border-radius: 3px;")
                lbl_st.setStyleSheet(f"border: none; background: transparent; color: {COLOR_PURPLE_DARK}; font-size: 11px; font-weight: 600;")

            st_pill_l.addWidget(st_dot)
            st_pill_l.addWidget(lbl_st)
            stw_l.addWidget(st_pill)
            self.table.setCellWidget(row_idx, 3, st_widget)

            # 4: Notes
            notes_item = QTableWidgetItem(client.get("notes", ""))
            notes_item.setForeground(QColor(COLOR_TEXT_MUTED))
            self.table.setItem(row_idx, 4, notes_item)

            # 5: Action buttons (Edit, Delete)
            actions_widget = QWidget()
            aw_layout = QHBoxLayout(actions_widget)
            aw_layout.setContentsMargins(4, 2, 4, 2)
            aw_layout.setSpacing(6)

            btn_edit = QPushButton(" Edit")
            btn_edit.setIcon(qta.icon("fa5s.edit", color=COLOR_TEXT_SECONDARY))
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #F8FAFC;
                    border-color: {COLOR_PRIMARY};
                }}
            """)
            btn_edit.clicked.connect(lambda ch=False, c=client: self._on_edit_client(c))
            aw_layout.addWidget(btn_edit)

            btn_delete = QPushButton(" Delete")
            btn_delete.setIcon(qta.icon("fa5s.trash-alt", color=COLOR_DANGER))
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_DANGER_TINT};
                    color: {COLOR_DANGER};
                    border: 1px solid {COLOR_DANGER_BORDER};
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #FEE2E2;
                }}
            """)
            btn_delete.clicked.connect(lambda ch=False, c_id=client.get("id"): self._on_delete_client(c_id))
            aw_layout.addWidget(btn_delete)

            self.table.setCellWidget(row_idx, 5, actions_widget)

    def _on_add_client(self):
        dlg = ClientDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                add_client(
                    name=data["name"],
                    company=data["company"],
                    email=data["email"],
                    notes=data["notes"],
                    status=data.get("status", "Active"),
                )
                self.refresh_clients()
                self.client_list_changed.emit()
            except Exception as e:
                logger.error(f"Error adding client: {e}")
                QMessageBox.critical(self, "Error", f"Failed to add client:\n{e}")

    def _on_edit_client(self, client):
        dlg = ClientDialog(client_data=client, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                update_client(
                    client_id=client["id"],
                    name=data["name"],
                    company=data["company"],
                    email=data["email"],
                    notes=data["notes"],
                    status=data.get("status", "Active"),
                )
                self.refresh_clients()
                self.client_list_changed.emit()
            except Exception as e:
                logger.error(f"Error updating client: {e}")
                QMessageBox.critical(self, "Error", f"Failed to update client:\n{e}")

    def _on_delete_client(self, client_id):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this client account?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                delete_client(client_id)
                self.refresh_clients()
                self.client_list_changed.emit()
            except Exception as e:
                logger.error(f"Error deleting client: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete client:\n{e}")
