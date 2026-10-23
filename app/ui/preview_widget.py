"""
Side-by-side Before/After PDF preview widget for ScaleXPro CV-Modifier.
Commercial enterprise quality: clean white containers, crisp typography,
synchronized scrolling, page navigation, zoom controls, and an integrated
interactive CV Editor mode for manual post-processing adjustments.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QStackedWidget,
    QMessageBox,
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QSize, Signal
import qtawesome as qta
import pymupdf as fitz

from app.ui.styles import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_TINT,
    COLOR_PRIMARY_BORDER,
    COLOR_SUCCESS,
    COLOR_SUCCESS_TINT,
    COLOR_SUCCESS_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
)
from app.ui.cv_editor_widget import CVEditorWidget
from app.logger import logger


class PDFPageViewer(QScrollArea):
    """Scrollable container for displaying a rendered PDF page image."""
    def __init__(self, title: str, is_accent: bool = False, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: #F8FAFC;
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}
        """)

        container = QWidget()
        container.setObjectName("pdfViewerContainer")
        container.setStyleSheet("#pdfViewerContainer { background-color: #F8FAFC; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(14, 12, 14, 14)
        container_layout.setSpacing(10)

        # Header Title Banner
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 4px 10px;
            }}
        """)
        h_layout = QHBoxLayout(self.header_frame)
        h_layout.setContentsMargins(8, 6, 8, 6)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-weight: 700; color: {COLOR_TEXT_PRIMARY}; font-size: 13px;")
        h_layout.addWidget(self.title_label)
        h_layout.addStretch()

        if is_accent:
            self.btn_header_edit = QPushButton(" Edit CV")
            self.btn_header_edit.setIcon(qta.icon("fa5s.pen", color=COLOR_PRIMARY))
            self.btn_header_edit.setCursor(Qt.PointingHandCursor)
            self.btn_header_edit.setFixedHeight(24)
            self.btn_header_edit.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY_TINT};
                    color: {COLOR_PRIMARY};
                    border: 1px solid {COLOR_PRIMARY_BORDER};
                    border-radius: 6px;
                    padding: 0 8px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #FED7AA;
                }}
            """)
            h_layout.addWidget(self.btn_header_edit)

        badge_text = "BRANDED & SAFE" if is_accent else "ORIGINAL"
        badge_style = f"""
            background-color: {COLOR_SUCCESS_TINT};
            color: {COLOR_SUCCESS};
            border: 1px solid {COLOR_SUCCESS_BORDER};
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 10px;
            font-weight: 700;
        """ if is_accent else f"""
            background-color: #F1F5F9;
            color: {COLOR_TEXT_SECONDARY};
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 10px;
            font-weight: 600;
        """
        badge = QLabel(badge_text)
        badge.setStyleSheet(badge_style)
        h_layout.addWidget(badge)

        container_layout.addWidget(self.header_frame)

        # Image Display Label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"""
            background-color: #FFFFFF;
            border: 2px dashed {COLOR_BORDER};
            border-radius: 8px;
            color: {COLOR_TEXT_MUTED};
            font-size: 13px;
        """)
        self.image_label.setText("No document preview loaded")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        container_layout.addWidget(self.image_label)

        self.setWidget(container)

    def set_pixmap(self, pixmap: Optional[QPixmap]):
        if pixmap and not pixmap.isNull():
            self.image_label.setPixmap(pixmap)
            self.image_label.setStyleSheet(f"""
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
            """)
        else:
            self.image_label.clear()
            self.image_label.setText("No document preview loaded")
            self.image_label.setStyleSheet(f"""
                background-color: #FFFFFF;
                border: 2px dashed {COLOR_BORDER};
                border-radius: 8px;
                color: {COLOR_TEXT_MUTED};
                font-size: 13px;
            """)


class BeforeAfterPreviewWidget(QWidget):
    """
    Side-by-side comparison widget for Before (Original) and After (Redacted/Branded).
    Features an interactive Edit CV mode on the Branded preview card.
    """
    version_saved_signal = Signal(str)
    edit_audit_signal = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_doc: Optional[fitz.Document] = None
        self.redacted_doc: Optional[fitz.Document] = None
        self.original_pdf_path: str = ""
        self.redacted_pdf_path: str = ""
        self.candidate_code: str = "CAND"
        self.source_file_path: str = ""
        self.logo_path: str = ""
        self.current_page: int = 0
        self.total_pages: int = 0
        self.zoom_scale: float = 1.0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Main stack: Page 0 = Side-by-Side Review, Page 1 = Full-Width Interactive Editor
        self.main_stack = QStackedWidget()

        # -------------------------------------------------------------
        # Mode 0: Side-by-Side Review Mode (Original vs Branded)
        # -------------------------------------------------------------
        review_container = QWidget()
        review_layout = QVBoxLayout(review_container)
        review_layout.setContentsMargins(0, 0, 0, 0)
        review_layout.setSpacing(8)

        # Side by side preview split with equal 50/50 allocation
        previews_layout = QHBoxLayout()
        previews_layout.setSpacing(12)

        self.viewer_before = PDFPageViewer("Original CV", is_accent=False)
        self.viewer_after = PDFPageViewer("Branded & Anonymized CV", is_accent=True)

        previews_layout.addWidget(self.viewer_before, stretch=1)
        previews_layout.addWidget(self.viewer_after, stretch=1)
        review_layout.addLayout(previews_layout, stretch=1)

        # Wire header Edit button
        if hasattr(self.viewer_after, "btn_header_edit"):
            self.viewer_after.btn_header_edit.clicked.connect(self.enter_edit_mode)

        # Bottom Compact Control Bar (Navigation & Zoom)
        controls_bar = QFrame()
        controls_bar.setFixedHeight(36)
        controls_bar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        controls_layout = QHBoxLayout(controls_bar)
        controls_layout.setContentsMargins(8, 2, 8, 2)
        controls_layout.setSpacing(6)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(qta.icon("fa5s.chevron-left", color=COLOR_TEXT_SECONDARY))
        self.btn_prev.setFixedSize(26, 26)
        self.btn_prev.setEnabled(False)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
            }}
        """)
        self.btn_prev.clicked.connect(self._prev_page)
        controls_layout.addWidget(self.btn_prev)

        self.page_label = QLabel("1 / 1")
        self.page_label.setStyleSheet(f"font-weight: 600; color: {COLOR_TEXT_PRIMARY}; font-size: 12px; padding: 0 4px;")
        controls_layout.addWidget(self.page_label)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(qta.icon("fa5s.chevron-right", color=COLOR_TEXT_SECONDARY))
        self.btn_next.setFixedSize(26, 26)
        self.btn_next.setEnabled(False)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
            }}
        """)
        self.btn_next.clicked.connect(self._next_page)
        controls_layout.addWidget(self.btn_next)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #E2E8F0;")
        controls_layout.addWidget(sep)

        self.btn_zoom_out = QPushButton()
        self.btn_zoom_out.setIcon(qta.icon("fa5s.search-minus", color=COLOR_TEXT_SECONDARY))
        self.btn_zoom_out.setFixedSize(26, 26)
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
            }}
        """)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        controls_layout.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet(f"font-weight: 600; color: {COLOR_TEXT_PRIMARY}; font-size: 12px; padding: 0 4px;")
        controls_layout.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton()
        self.btn_zoom_in.setIcon(qta.icon("fa5s.search-plus", color=COLOR_TEXT_SECONDARY))
        self.btn_zoom_in.setFixedSize(26, 26)
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
            }}
        """)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        controls_layout.addWidget(self.btn_zoom_in)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #E2E8F0;")
        controls_layout.addWidget(sep2)

        self.btn_reset_zoom = QPushButton()
        self.btn_reset_zoom.setIcon(qta.icon("fa5s.expand", color=COLOR_TEXT_SECONDARY))
        self.btn_reset_zoom.setFixedSize(26, 26)
        self.btn_reset_zoom.setCursor(Qt.PointingHandCursor)
        self.btn_reset_zoom.setToolTip("Fit Page")
        self.btn_reset_zoom.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
            }}
        """)
        self.btn_reset_zoom.clicked.connect(self._reset_zoom)
        controls_layout.addWidget(self.btn_reset_zoom)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.VLine)
        sep3.setStyleSheet("color: #E2E8F0;")
        controls_layout.addWidget(sep3)

        self.btn_edit_mode = QPushButton(" Edit CV")
        self.btn_edit_mode.setIcon(qta.icon("fa5s.pen", color=COLOR_PRIMARY))
        self.btn_edit_mode.setToolTip("Open interactive CV editor")
        self.btn_edit_mode.setCursor(Qt.PointingHandCursor)
        self.btn_edit_mode.setFixedHeight(26)
        self.btn_edit_mode.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY_TINT};
                color: {COLOR_PRIMARY};
                border: 1px solid {COLOR_PRIMARY_BORDER};
                border-radius: 6px;
                padding: 0 10px;
                font-weight: 700;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #FED7AA;
            }}
        """)
        self.btn_edit_mode.clicked.connect(self._toggle_edit_mode)
        controls_layout.addWidget(self.btn_edit_mode)

        bar_center_row = QHBoxLayout()
        bar_center_row.setAlignment(Qt.AlignCenter)
        bar_center_row.addWidget(controls_bar)
        review_layout.addLayout(bar_center_row)

        self.main_stack.addWidget(review_container)

        # -------------------------------------------------------------
        # Mode 1: Interactive CV Editor (Takes full width for editing)
        # -------------------------------------------------------------
        self.editor_widget = CVEditorWidget()
        self.editor_widget.closed_signal.connect(self.exit_edit_mode)
        self.editor_widget.version_saved_signal.connect(self._on_editor_version_saved)
        self.main_stack.addWidget(self.editor_widget)

        # Maintain backwards compatibility
        self.right_stack = self.main_stack

        layout.addWidget(self.main_stack, stretch=1)

        # Synchronize vertical scrollbars
        self.viewer_before.verticalScrollBar().valueChanged.connect(
            self.viewer_after.verticalScrollBar().setValue
        )
        self.viewer_after.verticalScrollBar().valueChanged.connect(
            self.viewer_before.verticalScrollBar().setValue
        )

    def _toggle_edit_mode(self):
        if self.right_stack.currentIndex() == 0:
            self.enter_edit_mode()
        else:
            self.exit_edit_mode()

    def enter_edit_mode(self):
        if not self.redacted_pdf_path or not os.path.exists(self.redacted_pdf_path):
            QMessageBox.warning(self, "No Document", "Please load a processed CV before editing.")
            return

        self.editor_widget.load_document(
            pdf_path=self.redacted_pdf_path,
            candidate_code=self.candidate_code,
            source_path=self.source_file_path,
            logo_path=self.logo_path,
        )
        self.editor_widget.current_page = self.current_page
        self.editor_widget._render_current_page()
        self.right_stack.setCurrentIndex(1)
        self.btn_edit_mode.setText(" Close Editor")

    def exit_edit_mode(self):
        self.right_stack.setCurrentIndex(0)
        self.btn_edit_mode.setText(" Edit CV")

        if self.redacted_pdf_path and os.path.exists(self.redacted_pdf_path):
            try:
                if self.redacted_doc:
                    self.redacted_doc.close()
                self.redacted_doc = fitz.open(self.redacted_pdf_path)
                self._update_view()
            except Exception as e:
                logger.error(f"Error refreshing view on exit edit mode: {e}")

    def _on_editor_version_saved(self, saved_path: str):
        self.redacted_pdf_path = saved_path
        try:
            if self.redacted_doc:
                self.redacted_doc.close()
            self.redacted_doc = fitz.open(saved_path)
            self._update_view()
        except Exception as e:
            logger.error(f"Error reloading document after version save: {e}")

        self.version_saved_signal.emit(saved_path)
        if self.editor_widget and self.editor_widget.engine:
            self.edit_audit_signal.emit(self.editor_widget.engine.audit_log)

    def load_documents(
        self,
        original_pdf_path: str,
        redacted_pdf_path: str,
        candidate_code: str = "CAND",
        source_file_path: str = "",
        logo_path: str = "",
    ):
        """Loads both original and redacted PDFs into the viewer."""
        try:
            self._close_docs()
            self.original_pdf_path = original_pdf_path
            self.redacted_pdf_path = redacted_pdf_path
            self.candidate_code = candidate_code
            self.source_file_path = source_file_path
            self.logo_path = logo_path

            self.original_doc = fitz.open(original_pdf_path)
            self.redacted_doc = fitz.open(redacted_pdf_path)
            self.total_pages = max(len(self.original_doc), len(self.redacted_doc))
            self.current_page = 0
            self.zoom_scale = 1.0
            self.right_stack.setCurrentIndex(0)
            self.btn_edit_mode.setText(" Edit CV")
            self._update_view()
        except Exception as e:
            logger.error(f"Error loading preview documents: {e}", exc_info=True)

    def _render_page_pixmap(self, doc: Optional[fitz.Document], page_idx: int) -> Optional[QPixmap]:
        """Renders a PDF page to a scaled QPixmap."""
        if not doc or page_idx >= len(doc):
            return None

        try:
            page = doc[page_idx]
            viewport_w = self.viewer_before.viewport().width()
            page_w = page.rect.width if page.rect.width > 0 else 595.0
            if viewport_w > 100:
                target_w = max(300, viewport_w - 30)
                base_dpi = int((target_w / page_w) * 72.0)
            else:
                base_dpi = 110

            dpi = max(72, int(base_dpi * self.zoom_scale))
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            return QPixmap.fromImage(img)
        except Exception as e:
            logger.warning(f"Failed to render page {page_idx}: {e}")
            return None

    def _update_view(self):
        """Refreshes the rendered page on both viewers."""
        if self.total_pages == 0:
            self.page_label.setText("Page 0 of 0")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.viewer_before.set_pixmap(None)
            self.viewer_after.set_pixmap(None)
            return

        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < (self.total_pages - 1))

        pix_before = self._render_page_pixmap(self.original_doc, self.current_page)
        pix_after = self._render_page_pixmap(self.redacted_doc, self.current_page)

        self.viewer_before.set_pixmap(pix_before)
        self.viewer_after.set_pixmap(pix_after)

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_view()
            if self.right_stack.currentIndex() == 1 and self.editor_widget:
                self.editor_widget.current_page = self.current_page
                self.editor_widget._render_current_page()

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_view()
            if self.right_stack.currentIndex() == 1 and self.editor_widget:
                self.editor_widget.current_page = self.current_page
                self.editor_widget._render_current_page()

    def _zoom_in(self):
        if self.zoom_scale < 2.5:
            self.zoom_scale += 0.2
            self._update_view()
            self.lbl_zoom.setText(f"{int(self.zoom_scale * 100)}%")
            if self.right_stack.currentIndex() == 1 and self.editor_widget:
                self.editor_widget.zoom_scale = self.zoom_scale
                self.editor_widget._render_current_page()

    def _zoom_out(self):
        if self.zoom_scale > 0.6:
            self.zoom_scale -= 0.2
            self._update_view()
            self.lbl_zoom.setText(f"{int(self.zoom_scale * 100)}%")
            if self.right_stack.currentIndex() == 1 and self.editor_widget:
                self.editor_widget.zoom_scale = self.zoom_scale
                self.editor_widget._render_current_page()

    def _reset_zoom(self):
        self.zoom_scale = 1.0
        self._update_view()
        self.lbl_zoom.setText("100%")
        if self.right_stack.currentIndex() == 1 and self.editor_widget:
            self.editor_widget.zoom_scale = 1.0
            self.editor_widget._render_current_page()

    def _close_docs(self):
        if self.original_doc:
            try:
                self.original_doc.close()
            except Exception:
                pass
            self.original_doc = None

        if self.redacted_doc:
            try:
                self.redacted_doc.close()
            except Exception:
                pass
            self.redacted_doc = None

    def clear(self):
        self._close_docs()
        self.total_pages = 0
        self.current_page = 0
        self.right_stack.setCurrentIndex(0)
        self._update_view()

    def closeEvent(self, event):
        self._close_docs()
        super().closeEvent(event)
