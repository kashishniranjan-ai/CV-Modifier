"""
Interactive CV Editor Widget for ScaleXPro CV-Modifier.
Allows recruiters to review, edit text, place custom text boxes,
delete/blank areas with true redaction, move/resize the company logo,
undo/redo edits (30+ steps), manage version files, and inspect audit logs.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import pymupdf as fitz
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDialog,
    QScrollArea,
    QFrame,
    QMessageBox,
    QSplitter,
    QToolTip,
    QButtonGroup,
)
from PySide6.QtGui import (
    QPixmap,
    QImage,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QCursor,
    QFont,
    QKeySequence,
    QShortcut,
)
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, Signal, QSize
import qtawesome as qta

from app.core.pdf_editor import CVEditorEngine, sample_background_color
from app.core.docx_editor import get_docx_paragraphs, save_docx_paragraph_edits
from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_TINT,
    COLOR_PRIMARY_BORDER,
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


class EditTextDialog(QDialog):
    """Dialog for editing detected text on a CV page."""
    def __init__(self, text_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.text_info = text_info
        self.setWindowTitle("Edit CV Text")
        self.setFixedWidth(460)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLOR_NAVY};
                font-size: 12px;
                font-weight: 600;
            }}
            QLineEdit, QTextEdit {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: {COLOR_NAVY};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header info
        head_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.pen", color=COLOR_PRIMARY).pixmap(18, 18))
        head_row.addWidget(icon_lbl)

        title_lbl = QLabel("Modify Text In-Place")
        title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_NAVY};")
        head_row.addWidget(title_lbl)
        head_row.addStretch()
        layout.addLayout(head_row)

        # Font metadata pill
        font_name = text_info.get("font_name", "Helvetica")
        font_size = text_info.get("font_size", 10.0)
        meta_lbl = QLabel(f"Detected Font: {font_name} • {font_size:.1f}pt")
        meta_lbl.setStyleSheet(f"""
            background-color: #F8FAFC;
            color: {COLOR_TEXT_SECONDARY};
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 500;
        """)
        layout.addWidget(meta_lbl)

        # Input text area
        layout.addWidget(QLabel("Text Content:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text_info.get("text", ""))
        self.text_edit.setFixedHeight(90)
        layout.addWidget(self.text_edit)

        # Warning / hint label
        self.hint_label = QLabel("Replaces text exactly at target position. Font scales automatically if longer.")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-weight: 400;")
        layout.addWidget(self.hint_label)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_apply = QPushButton("Apply Edit")
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.setFixedHeight(34)
        btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        btn_apply.clicked.connect(self.accept)
        btns.addWidget(btn_apply)

        layout.addLayout(btns)

    def get_text(self) -> str:
        return self.text_edit.toPlainText().strip()


class AddTextBoxDialog(QDialog):
    """Dialog for creating a new custom text box on a CV page."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert New Text Box")
        self.setFixedWidth(460)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLOR_NAVY};
                font-size: 12px;
                font-weight: 600;
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
                color: {COLOR_NAVY};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {COLOR_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        # Header
        head_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.font", color=COLOR_PRIMARY).pixmap(18, 18))
        head_row.addWidget(icon_lbl)

        title_lbl = QLabel("Add Text Box")
        title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLOR_NAVY};")
        head_row.addWidget(title_lbl)
        head_row.addStretch()
        layout.addLayout(head_row)

        layout.addWidget(QLabel("Text Content:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Enter candidate text or notes...")
        self.text_edit.setFixedHeight(75)
        layout.addWidget(self.text_edit)

        # Controls grid (font, size, style, color, alignment)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("Font Family:"), 0, 0)
        self.font_combo = QComboBox()
        self.font_combo.addItem("Helvetica (Sans-Serif)", "helv")
        self.font_combo.addItem("Times Roman (Serif)", "times")
        self.font_combo.addItem("Courier (Monospace)", "couri")
        grid.addWidget(self.font_combo, 0, 1)

        grid.addWidget(QLabel("Font Size:"), 1, 0)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 36)
        self.size_spin.setValue(11)
        grid.addWidget(self.size_spin, 1, 1)

        grid.addWidget(QLabel("Color:"), 2, 0)
        self.color_combo = QComboBox()
        self.color_combo.addItem("Dark Navy (#0F172A)", (0.05, 0.09, 0.16))
        self.color_combo.addItem("ScaleXPro Orange (#F28A1E)", (0.95, 0.54, 0.12))
        self.color_combo.addItem("Charcoal Gray (#334155)", (0.2, 0.25, 0.33))
        self.color_combo.addItem("Muted Gray (#64748B)", (0.39, 0.45, 0.54))
        self.color_combo.addItem("White (#FFFFFF)", (1.0, 1.0, 1.0))
        grid.addWidget(self.color_combo, 2, 1)

        grid.addWidget(QLabel("Alignment:"), 3, 0)
        self.align_combo = QComboBox()
        self.align_combo.addItem("Left", fitz.TEXT_ALIGN_LEFT)
        self.align_combo.addItem("Center", fitz.TEXT_ALIGN_CENTER)
        self.align_combo.addItem("Right", fitz.TEXT_ALIGN_RIGHT)
        grid.addWidget(self.align_combo, 3, 1)

        layout.addLayout(grid)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(34)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_insert = QPushButton("Insert Text Box")
        btn_insert.setCursor(Qt.PointingHandCursor)
        btn_insert.setFixedHeight(34)
        btn_insert.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        btn_insert.clicked.connect(self.accept)
        btns.addWidget(btn_insert)

        layout.addLayout(btns)

    def get_data(self) -> Dict[str, Any]:
        return {
            "text": self.text_edit.toPlainText().strip(),
            "font": self.font_combo.currentData(),
            "size": self.size_spin.value(),
            "color": self.color_combo.currentData(),
            "align": self.align_combo.currentData(),
        }


class DOCXParagraphsDialog(QDialog):
    """Modal for editing raw DOCX paragraphs prior to PDF compilation."""
    def __init__(self, docx_path: str, parent=None):
        super().__init__(parent)
        self.docx_path = docx_path
        self.setWindowTitle("Edit Source DOCX Paragraphs")
        self.resize(650, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLOR_NAVY};
                font-size: 12px;
                font-weight: 600;
            }}
            QTextEdit {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                color: {COLOR_NAVY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        head_lbl = QLabel("Paragraphs Editor (Pre-conversion)")
        head_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_NAVY};")
        layout.addWidget(head_lbl)

        sub_lbl = QLabel("Modify text in the source Word document before converting to PDF and applying branding.")
        sub_lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(sub_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #E2E8F0; border-radius: 8px; }")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(12, 12, 12, 12)
        c_layout.setSpacing(12)

        self.paragraph_edits: Dict[int, QTextEdit] = {}
        paragraphs = get_docx_paragraphs(docx_path)

        for p_info in paragraphs:
            idx = p_info["index"]
            text = p_info["text"]
            row_box = QVBoxLayout()
            row_box.setSpacing(4)
            lbl = QLabel(f"Paragraph #{idx + 1} ({p_info.get('style', 'Normal')}):")
            lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_PRIMARY}; font-weight: 700;")
            row_box.addWidget(lbl)

            te = QTextEdit()
            te.setPlainText(text)
            te.setFixedHeight(65)
            row_box.addWidget(te)
            self.paragraph_edits[idx] = te
            c_layout.addLayout(row_box)

        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        btns = QHBoxLayout()
        btns.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Re-process")
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet(f"""
            background-color: {COLOR_PRIMARY};
            color: #FFFFFF;
            font-weight: 700;
            border-radius: 8px;
            padding: 0 16px;
        """)
        btn_save.clicked.connect(self.accept)
        btns.addWidget(btn_save)

        layout.addLayout(btns)

    def get_edits(self) -> Dict[int, str]:
        return {idx: te.toPlainText().strip() for idx, te in self.paragraph_edits.items()}


class InteractiveCanvas(QWidget):
    """
    Renders the active PDF page and tracks mouse interactions:
    - Text detection and inline selection
    - Add text box placement
    - Delete/blank area rectangle drag
    - Logo move/resize handles
    """
    text_clicked = Signal(dict)
    text_box_requested = Signal(tuple)
    delete_area_requested = Signal(tuple)
    logo_moved_requested = Signal(tuple, tuple)
    status_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.page_pixmap: Optional[QPixmap] = None
        self.scale_factor: float = 1.0
        self.current_tool: str = "edit_text"  # "edit_text" | "add_text" | "delete_area" | "move_logo"
        self.page_width_pt: float = 595.0
        self.page_height_pt: float = 842.0

        # Hover state
        self.hovered_rect: Optional[QRectF] = None
        self.hovered_text_info: Optional[Dict[str, Any]] = None

        # Drag state (for delete_area or logo)
        self.is_dragging: bool = False
        self.drag_start: Optional[QPointF] = None
        self.drag_current: Optional[QPointF] = None

        # Logo bounds (in PDF points)
        self.logo_rect_pt: Optional[fitz.Rect] = None
        self.logo_drag_mode: Optional[str] = None  # "move" | "resize"

    def set_page_image(self, pixmap: QPixmap, pt_width: float, pt_height: float):
        self.page_pixmap = pixmap
        self.page_width_pt = pt_width
        self.page_height_pt = pt_height
        self.setFixedSize(pixmap.size())
        if pt_width > 0:
            self.scale_factor = pixmap.width() / pt_width
        self.hovered_rect = None
        self.update()

    def set_tool(self, tool_name: str):
        self.current_tool = tool_name
        self.hovered_rect = None
        self.hovered_text_info = None
        if tool_name == "edit_text":
            self.setCursor(Qt.IBeamCursor)
        elif tool_name in ["add_text", "delete_area"]:
            self.setCursor(Qt.CrossCursor)
        elif tool_name == "move_logo":
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.page_pixmap and not self.page_pixmap.isNull():
            painter.drawPixmap(0, 0, self.page_pixmap)

        # 1. Draw Hovered Text Highlight
        if self.current_tool == "edit_text" and self.hovered_rect:
            pen = QPen(QColor(COLOR_PRIMARY), 1.5, Qt.DashLine)
            painter.setPen(pen)
            brush = QBrush(QColor(242, 138, 30, 35))
            painter.setBrush(brush)
            painter.drawRoundedRect(self.hovered_rect, 3, 3)

        # 2. Draw Delete Area Selection Drag
        if self.current_tool == "delete_area" and self.is_dragging and self.drag_start and self.drag_current:
            r = QRectF(self.drag_start, self.drag_current).normalized()
            pen = QPen(QColor(COLOR_DANGER), 1.5, Qt.DashLine)
            painter.setPen(pen)
            brush = QBrush(QColor(227, 43, 43, 45))
            painter.setBrush(brush)
            painter.drawRect(r)

        # 3. Draw Add Text Box Placement Drag
        if self.current_tool == "add_text" and self.is_dragging and self.drag_start and self.drag_current:
            r = QRectF(self.drag_start, self.drag_current).normalized()
            pen = QPen(QColor(COLOR_PRIMARY), 1.5, Qt.SolidLine)
            painter.setPen(pen)
            brush = QBrush(QColor(242, 138, 30, 25))
            painter.setBrush(brush)
            painter.drawRoundedRect(r, 4, 4)

        # 4. Draw Logo Drag/Resize Handles
        if self.current_tool == "move_logo" and self.logo_rect_pt:
            s = self.scale_factor
            r = QRectF(
                self.logo_rect_pt.x0 * s,
                self.logo_rect_pt.y0 * s,
                self.logo_rect_pt.width * s,
                self.logo_rect_pt.height * s,
            )
            pen = QPen(QColor(COLOR_PRIMARY), 2, Qt.SolidLine)
            painter.setPen(pen)
            brush = QBrush(QColor(242, 138, 30, 40))
            painter.setBrush(brush)
            painter.drawRect(r)

            # Draw 4 corner handles
            handle_pen = QPen(QColor(COLOR_NAVY), 1)
            handle_brush = QBrush(QColor("#FFFFFF"))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            corners = [r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight()]
            for pt in corners:
                painter.drawRect(QRectF(pt.x() - 4, pt.y() - 4, 8, 8))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start = event.position()
            self.drag_current = event.position()
            self.is_dragging = True

            if self.current_tool == "edit_text" and self.hovered_text_info:
                self.text_clicked.emit(self.hovered_text_info)

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self.is_dragging:
            self.drag_current = pos
            self.update()
            return

        # Handle hover detection in Edit Text mode
        if self.current_tool == "edit_text":
            engine = getattr(self, "engine", None)
            page_num = getattr(self, "current_page", 0)
            if engine and self.scale_factor > 0:
                pdf_x = pos.x() / self.scale_factor
                pdf_y = pos.y() / self.scale_factor
                info = engine.detect_text_under_point(page_num, pdf_x, pdf_y)
                if info:
                    self.hovered_text_info = info
                    r = info["rect"]
                    s = self.scale_factor
                    self.hovered_rect = QRectF(r[0] * s, r[1] * s, (r[2] - r[0]) * s, (r[3] - r[1]) * s)
                else:
                    self.hovered_rect = None
                    self.hovered_text_info = None
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.drag_current = event.position()

            if self.drag_start and self.scale_factor > 0:
                r = QRectF(self.drag_start, self.drag_current).normalized()
                s = self.scale_factor
                pt_rect = (r.x() / s, r.y() / s, (r.x() + r.width()) / s, (r.y() + r.height()) / s)

                if self.current_tool == "delete_area" and r.width() > 5 and r.height() > 5:
                    self.delete_area_requested.emit(pt_rect)
                elif self.current_tool == "add_text":
                    # If just clicked without dragging, provide default size 180x40
                    w = max(180, pt_rect[2] - pt_rect[0])
                    h = max(36, pt_rect[3] - pt_rect[1])
                    self.text_box_requested.emit((pt_rect[0], pt_rect[1], pt_rect[0] + w, pt_rect[1] + h))

            self.update()


class CVEditorWidget(QWidget):
    """
    Full CV Editor container with dedicated toolbar, page navigation,
    interactive canvas, undo/redo buttons, version management, and safety check integration.
    """
    version_saved_signal = Signal(str)  # emitted when a new version is created
    closed_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine: Optional[CVEditorEngine] = None
        self.current_page: int = 0
        self.total_pages: int = 0
        self.zoom_scale: float = 1.0
        self.source_file_path: str = ""
        self.logo_path: str = ""

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # -------------------------------------------------------------
        # 1. Edit Mode Top Toolbar
        # -------------------------------------------------------------
        toolbar_card = QFrame()
        toolbar_card.setFixedHeight(48)
        toolbar_card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        tb_layout = QHBoxLayout(toolbar_card)
        tb_layout.setContentsMargins(10, 4, 10, 4)
        tb_layout.setSpacing(6)

        # Tool button group
        lbl_tools = QLabel("Tools:")
        lbl_tools.setStyleSheet(f"font-weight: 700; color: {COLOR_NAVY}; font-size: 11px;")
        tb_layout.addWidget(lbl_tools)

        self.btn_tool_edit = self._create_tool_button("Edit Text", "fa5s.i-cursor", "edit_text")
        self.btn_tool_add = self._create_tool_button("Add Text", "fa5s.font", "add_text")
        self.btn_tool_delete = self._create_tool_button("Delete Area", "fa5s.eraser", "delete_area")
        self.btn_tool_logo = self._create_tool_button("Move Logo", "fa5s.arrows-alt", "move_logo")

        tb_layout.addWidget(self.btn_tool_edit)
        tb_layout.addWidget(self.btn_tool_add)
        tb_layout.addWidget(self.btn_tool_delete)
        tb_layout.addWidget(self.btn_tool_logo)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #E2E8F0;")
        tb_layout.addWidget(sep1)

        # Undo / Redo
        self.btn_undo = QPushButton()
        self.btn_undo.setIcon(qta.icon("fa5s.undo", color=COLOR_TEXT_PRIMARY))
        self.btn_undo.setToolTip("Undo (Ctrl+Z)")
        self.btn_undo.setFixedSize(30, 30)
        self.btn_undo.clicked.connect(self._on_undo)
        tb_layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton()
        self.btn_redo.setIcon(qta.icon("fa5s.redo", color=COLOR_TEXT_PRIMARY))
        self.btn_redo.setToolTip("Redo (Ctrl+Y)")
        self.btn_redo.setFixedSize(30, 30)
        self.btn_redo.clicked.connect(self._on_redo)
        tb_layout.addWidget(self.btn_redo)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setIcon(qta.icon("fa5s.history", color=COLOR_TEXT_SECONDARY))
        self.btn_reset.setToolTip("Reset to Original Branded Version")
        self.btn_reset.setFixedHeight(30)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
                color: {COLOR_NAVY};
            }}
        """)
        self.btn_reset.clicked.connect(self._on_reset_to_original)
        tb_layout.addWidget(self.btn_reset)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #E2E8F0;")
        tb_layout.addWidget(sep2)

        # Version History Dropdown & Restore
        lbl_ver = QLabel("Ver:")
        lbl_ver.setStyleSheet(f"font-weight: 600; color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        tb_layout.addWidget(lbl_ver)

        self.version_combo = QComboBox()
        self.version_combo.setFixedHeight(28)
        self.version_combo.setMinimumWidth(110)
        tb_layout.addWidget(self.version_combo)

        self.btn_restore_ver = QPushButton("Restore")
        self.btn_restore_ver.setFixedHeight(28)
        self.btn_restore_ver.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
            }}
        """)
        self.btn_restore_ver.clicked.connect(self._on_restore_version)
        tb_layout.addWidget(self.btn_restore_ver)

        tb_layout.addStretch()

        # DOCX paragraph button (visible only if input is DOCX)
        self.btn_docx_edit = QPushButton(" DOCX Paragraphs")
        self.btn_docx_edit.setIcon(qta.icon("fa5s.file-word", color="#2563EB"))
        self.btn_docx_edit.setFixedHeight(30)
        self.btn_docx_edit.setStyleSheet(f"""
            QPushButton {{
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #DBEAFE;
            }}
        """)
        self.btn_docx_edit.setVisible(False)
        self.btn_docx_edit.clicked.connect(self._on_docx_edit_clicked)
        tb_layout.addWidget(self.btn_docx_edit)

        # Save Version CTA (orange)
        self.btn_save_version = QPushButton(" Save Version")
        self.btn_save_version.setIcon(qta.icon("fa5s.save", color="#FFFFFF"))
        self.btn_save_version.setToolTip("Save Version (Ctrl+S)")
        self.btn_save_version.setFixedHeight(32)
        self.btn_save_version.setCursor(Qt.PointingHandCursor)
        self.btn_save_version.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_HOVER};
            }}
        """)
        self.btn_save_version.clicked.connect(self._on_save_version)
        tb_layout.addWidget(self.btn_save_version)

        # Done / Exit button
        self.btn_done = QPushButton("Done")
        self.btn_done.setToolTip("Exit Edit Mode (Esc)")
        self.btn_done.setFixedHeight(32)
        self.btn_done.setCursor(Qt.PointingHandCursor)
        self.btn_done.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 0 12px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
            }}
        """)
        self.btn_done.clicked.connect(self._on_exit_clicked)
        tb_layout.addWidget(self.btn_done)

        main_layout.addWidget(toolbar_card)

        # -------------------------------------------------------------
        # 2. Informational Banner (for Scanned / Safety Warnings)
        # -------------------------------------------------------------
        self.banner_frame = QFrame()
        self.banner_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 6px;
                padding: 4px 10px;
            }}
        """)
        b_l = QHBoxLayout(self.banner_frame)
        b_l.setContentsMargins(8, 4, 8, 4)
        self.banner_label = QLabel("")
        self.banner_label.setStyleSheet("color: #1D4ED8; font-size: 11px; font-weight: 600;")
        b_l.addWidget(self.banner_label)
        self.banner_frame.setVisible(False)
        main_layout.addWidget(self.banner_frame)

        # -------------------------------------------------------------
        # 3. Scrollable Canvas Area
        # -------------------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: #F1F5F9;
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
            }}
        """)

        self.canvas = InteractiveCanvas(self)
        self.canvas.text_clicked.connect(self._on_canvas_text_clicked)
        self.canvas.text_box_requested.connect(self._on_canvas_text_box_requested)
        self.canvas.delete_area_requested.connect(self._on_canvas_delete_area_requested)
        self.canvas.logo_moved_requested.connect(self._on_canvas_logo_moved_requested)

        self.scroll_area.setWidget(self.canvas)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # -------------------------------------------------------------
        # 4. Keyboard Shortcuts
        # -------------------------------------------------------------
        QShortcut(QKeySequence("Ctrl+Z"), self, self._on_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self._on_redo)
        QShortcut(QKeySequence("Ctrl+S"), self, self._on_save_version)
        QShortcut(QKeySequence("Esc"), self, self._on_exit_clicked)

        # Set initial active tool
        self._select_tool("edit_text")

    def _create_tool_button(self, label: str, icon_name: str, tool_name: str) -> QPushButton:
        btn = QPushButton(f" {label}")
        btn.setIcon(qta.icon(icon_name, color=COLOR_TEXT_PRIMARY))
        btn.setFixedHeight(30)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
                border-color: {COLOR_PRIMARY};
            }}
        """)
        btn.clicked.connect(lambda ch=False, tn=tool_name: self._select_tool(tn))
        return btn

    def _select_tool(self, tool_name: str):
        self.canvas.set_tool(tool_name)
        active_style = f"""
            background-color: {COLOR_PRIMARY_TINT};
            color: {COLOR_PRIMARY};
            border: 1.5px solid {COLOR_PRIMARY};
            border-radius: 6px;
            padding: 0 10px;
            font-size: 11px;
            font-weight: 700;
        """
        inactive_style = f"""
            background-color: #FFFFFF;
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
            padding: 0 10px;
            font-size: 11px;
            font-weight: 600;
        """
        self.btn_tool_edit.setStyleSheet(active_style if tool_name == "edit_text" else inactive_style)
        self.btn_tool_add.setStyleSheet(active_style if tool_name == "add_text" else inactive_style)
        self.btn_tool_delete.setStyleSheet(active_style if tool_name == "delete_area" else inactive_style)
        self.btn_tool_logo.setStyleSheet(active_style if tool_name == "move_logo" else inactive_style)

    def load_document(self, pdf_path: str, candidate_code: str, source_path: str = "", logo_path: str = "", source_file_path: str = ""):
        """Initializes the editing session with a clean branded document."""
        self.source_file_path = source_path or source_file_path
        self.logo_path = logo_path
        self.engine = CVEditorEngine(pdf_path, candidate_code)
        self.canvas.engine = self.engine
        self.total_pages = len(self.engine.doc)
        self.current_page = 0

        # Enable DOCX edit button if applicable
        is_docx = (self.source_file_path or "").lower().endswith(".docx")
        self.btn_docx_edit.setVisible(is_docx)

        self._refresh_version_list()
        self._render_current_page()

    def _refresh_version_list(self):
        if not self.engine:
            return
        self.version_combo.clear()
        for v in self.engine.versions:
            self.version_combo.addItem(f"v{v['version']}: {v['description']}", v["path"])
        self.version_combo.setCurrentIndex(len(self.engine.versions) - 1)

    def _render_current_page(self):
        if not self.engine or len(self.engine.doc) == 0:
            return

        page = self.engine.doc[self.current_page]
        self.canvas.current_page = self.current_page

        # Check if page is scanned/image-only
        if self.engine.is_page_scanned(self.current_page):
            self.banner_frame.setVisible(True)
            self.banner_label.setText(
                "ℹ Scanned / image-only CV detected. OCR/Text editing is disabled, but 'Delete Area' and 'Add Text' are fully available."
            )
            self.btn_tool_edit.setEnabled(False)
            if self.canvas.current_tool == "edit_text":
                self._select_tool("delete_area")
        else:
            self.banner_frame.setVisible(False)
            self.btn_tool_edit.setEnabled(True)

        dpi = int(140 * self.zoom_scale)
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.canvas.set_page_image(pixmap, page.rect.width, page.rect.height)

        # Update Undo / Redo buttons
        self.btn_undo.setEnabled(self.engine.can_undo())
        self.btn_redo.setEnabled(self.engine.can_redo())

    def _on_undo(self):
        if self.engine and self.engine.undo():
            self._render_current_page()

    def _on_redo(self):
        if self.engine and self.engine.redo():
            self._render_current_page()

    def _on_reset_to_original(self):
        reply = QMessageBox.question(
            self,
            "Reset Confirmation",
            "Are you sure you want to revert all manual edits and restore the original branded version?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes and self.engine:
            self.engine.reset_to_original()
            self._render_current_page()

    def _on_restore_version(self):
        path = self.version_combo.currentData()
        if path and Path(path).exists() and self.engine:
            self.engine.push_state()
            self.engine.doc.close()
            self.engine.doc = fitz.open(path)
            self.engine.current_pdf_bytes = self.engine.doc.tobytes()
            self._render_current_page()
            QMessageBox.information(self, "Version Restored", f"Restored {Path(path).name}")

    def _on_save_version(self):
        if not self.engine:
            return

        exports_dir = Path(self.engine.original_pdf_path).parent
        ok, saved_path, msg = self.engine.save_version(exports_dir)
        if ok:
            self._refresh_version_list()
            QMessageBox.information(self, "Version Saved", msg)
            self.version_saved_signal.emit(saved_path)
        else:
            QMessageBox.critical(self, "Safety Check Blocked", msg)

    def _on_exit_clicked(self):
        self.closed_signal.emit()

    def _on_canvas_text_clicked(self, text_info: Dict[str, Any]):
        dlg = EditTextDialog(text_info, self)
        if dlg.exec() == QDialog.Accepted and self.engine:
            new_text = dlg.get_text()
            if not new_text:
                return

            ok, warn = self.engine.replace_text(
                page_num=self.current_page,
                rect=text_info["rect"],
                new_text=new_text,
                font_name=text_info.get("base14_font", "helv"),
                font_size=text_info.get("font_size", 10.0),
                color_rgb=text_info.get("color_rgb", (0, 0, 0)),
                bg_rgb=text_info.get("bg_rgb", (1, 1, 1)),
                old_text_snippet=text_info.get("text", ""),
            )
            if ok:
                self._render_current_page()
                if warn:
                    QToolTip.showText(QCursor.pos(), warn, self)

    def _on_canvas_text_box_requested(self, rect: Tuple[float, float, float, float]):
        dlg = AddTextBoxDialog(self)
        if dlg.exec() == QDialog.Accepted and self.engine:
            d = dlg.get_data()
            if not d["text"]:
                return
            ok, msg = self.engine.add_text_box(
                page_num=self.current_page,
                rect=rect,
                text=d["text"],
                font_name=d["font"],
                font_size=d["size"],
                color_rgb=d["color"],
                align=d["align"],
            )
            if ok:
                self._render_current_page()

    def _on_canvas_delete_area_requested(self, rect: Tuple[float, float, float, float]):
        if self.engine:
            ok, msg = self.engine.delete_area(page_num=self.current_page, rect=rect)
            if ok:
                self._render_current_page()

    def _on_canvas_logo_moved_requested(self, old_rect: Tuple[float, float, float, float], new_rect: Tuple[float, float, float, float]):
        if self.engine and self.logo_path:
            ok, msg = self.engine.move_resize_logo(
                page_num=self.current_page,
                old_rect=old_rect,
                new_rect=new_rect,
                logo_path=self.logo_path,
            )
            if ok:
                self._render_current_page()

    def _on_docx_edit_clicked(self):
        if not self.source_file_path or not Path(self.source_file_path).exists():
            return
        dlg = DOCXParagraphsDialog(self.source_file_path, self)
        if dlg.exec() == QDialog.Accepted:
            edits = dlg.get_edits()
            # Save to temporary modified docx
            temp_docx = Path(self.source_file_path).parent / f"edited_{Path(self.source_file_path).name}"
            ok, msg = save_docx_paragraph_edits(self.source_file_path, str(temp_docx), edits)
            if ok:
                QMessageBox.information(
                    self,
                    "DOCX Updated",
                    "Paragraphs saved. Please click 'Re-run' on the main panel to compile the new version.",
                )
