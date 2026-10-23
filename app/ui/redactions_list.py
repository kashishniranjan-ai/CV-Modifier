"""
Interactive list and summary table of all redacted items.
Provides immediate audit trail and confirmation for the recruiter.
"""

from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_SUCCESS_TINT,
    COLOR_SUCCESS_BORDER,
    COLOR_DANGER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
)


class RedactionsListWidget(QWidget):
    """Displays an audited table of all detected and removed contact details."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_items: List[Dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header bar with summary & filter
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 4px 8px;
            }}
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(10)

        self.summary_label = QLabel("Redactions: 0 items removed")
        self.summary_label.setStyleSheet(f"font-weight: 700; color: {COLOR_SUCCESS}; font-size: 12px;")
        top_layout.addWidget(self.summary_label)

        top_layout.addStretch()

        # Category Filter
        lbl_c = QLabel("Category:")
        lbl_c.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        top_layout.addWidget(lbl_c)
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentTextChanged.connect(self._apply_filter)
        top_layout.addWidget(self.category_filter)

        # Search box
        lbl_s = QLabel("Search:")
        lbl_s.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        top_layout.addWidget(lbl_s)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter removed items...")
        self.search_box.textChanged.connect(self._apply_filter)
        self.search_box.setFixedWidth(160)
        top_layout.addWidget(self.search_box)

        layout.addWidget(top_bar)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "#",
            "Page",
            "Category",
            "Redacted Content / Detail",
            "Action Taken",
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(f"""
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
                text-transform: uppercase;
                border: none;
                border-bottom: 1px solid {COLOR_BORDER};
                padding: 6px 10px;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {COLOR_BORDER_LIGHT};
            }}
        """)

        layout.addWidget(self.table)

    def set_redactions(self, items: List[Dict[str, Any]]):
        """Populates the table with redaction items."""
        self.all_items = items

        # Update categories
        cats = sorted(list(set(item["category"] for item in items)))
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        for cat in cats:
            self.category_filter.addItem(cat)
        self.category_filter.blockSignals(False)

        contact_items = [i for i in items if i.get("category") != "Logo Placement"]
        self.summary_label.setText(f"Redactions: {len(contact_items)} sensitive contact items permanently removed")
        self._apply_filter()

    def _apply_filter(self):
        cat = self.category_filter.currentText()
        search = self.search_box.text().strip().lower()

        filtered = []
        for item in self.all_items:
            if cat != "All Categories" and item["category"] != cat:
                continue
            if search:
                content = str(item.get("content", "")).lower()
                category = str(item.get("category", "")).lower()
                action = str(item.get("action", "")).lower()
                if search not in content and search not in category and search not in action:
                    continue
            filtered.append(item)

        self._render_table(filtered)

    def _render_table(self, items: List[Dict[str, Any]]):
        self.table.setRowCount(len(items))

        for row_idx, item in enumerate(items):
            # Index
            idx_item = QTableWidgetItem(str(row_idx + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor(COLOR_TEXT_MUTED))
            self.table.setItem(row_idx, 0, idx_item)

            # Page
            page_val = item.get("page", 1)
            page_item = QTableWidgetItem(f"p. {page_val}")
            page_item.setTextAlignment(Qt.AlignCenter)
            page_item.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.table.setItem(row_idx, 1, page_item)

            # Category
            cat_item = QTableWidgetItem(item.get("category", "Contact"))
            cat_item.setForeground(QColor(COLOR_PRIMARY))
            self.table.setItem(row_idx, 2, cat_item)

            # Content
            content_val = item.get("content", "")
            content_item = QTableWidgetItem(content_val)
            content_item.setForeground(QColor(COLOR_TEXT_PRIMARY))
            self.table.setItem(row_idx, 3, content_item)

            # Action
            action_val = item.get("action", "Redacted")
            action_item = QTableWidgetItem(action_val)
            action_item.setForeground(QColor(COLOR_SUCCESS))
            self.table.setItem(row_idx, 4, action_item)
