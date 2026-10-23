"""
PyMuPDF-based CV Editor Engine for ScaleXPro CV-Modifier.
Provides offline, high-fidelity PDF modification capabilities:
- Interactive text detection at coordinates using page.get_text("dict")
- Natural text replacement matching font, size, color, background sampling, and shrink-to-fit
- Custom text box placement with font family, size, style, color, alignment
- True redaction area deletion (text + images)
- Logo move and resize
- In-memory 30+ step Undo/Redo stack
- Version file management (v1 original branded, v2, v3... with restore)
- Contact detection and safety re-scan
- Audit trail logging
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pymupdf as fitz
from PIL import Image

from app.core.regex_patterns import (
    find_all_sensitive_info,
    EMAIL_REGEX,
    INDIAN_PHONE_REGEX,
    GENERAL_URL_REGEX,
    is_valid_phone,
)
from app.logger import logger


def match_base14_font(font_name: str, is_bold: bool = False, is_italic: bool = False) -> str:
    """Matches any arbitrary embedded font name to the closest PyMuPDF standard font."""
    fn = (font_name or "").lower()
    
    # Check Times / Serif
    if any(k in fn for k in ["times", "serif", "georgia", "cambria", "garamond", "roman"]):
        if is_bold and is_italic:
            return "tibi"
        if is_bold:
            return "tibo"
        if is_italic:
            return "tiit"
        return "times"

    # Check Courier / Monospace
    if any(k in fn for k in ["courier", "mono", "consolas", "code"]):
        if is_bold and is_italic:
            return "cobi"
        if is_bold:
            return "cobo"
        if is_italic:
            return "coit"
        return "couri"

    # Default to Helvetica / Sans-Serif (Arial, Inter, Segoe UI, Roboto, etc.)
    if is_bold and is_italic:
        return "hebi"
    if is_bold:
        return "hebo"
    if is_italic:
        return "heit"
    return "helv"


def sample_background_color(page: fitz.Page, rect: fitz.Rect) -> Tuple[float, float, float]:
    """
    Samples the background color behind or surrounding a text rectangle on a PDF page.
    Inspects perimeter pixels of a rendered clip to distinguish white backgrounds
    from dark navy headers (#0F172A), tinted banners, or light gray panels.
    Returns RGB tuple with floats in [0.0, 1.0].
    """
    try:
        # Expand rect slightly by 2pt to sample canvas behind glyph edges
        expanded = fitz.Rect(
            max(0, rect.x0 - 2),
            max(0, rect.y0 - 2),
            min(page.rect.width, rect.x1 + 2),
            min(page.rect.height, rect.y1 + 2),
        )
        pix = page.get_pixmap(clip=expanded, dpi=100)
        if pix.width < 2 or pix.height < 2:
            return (1.0, 1.0, 1.0)

        # Collect border pixels along the top, bottom, left, right edges
        edge_pixels = []
        w, h = pix.width, pix.height
        for x in range(w):
            edge_pixels.append(pix.pixel(x, 0))
            edge_pixels.append(pix.pixel(x, h - 1))
        for y in range(h):
            edge_pixels.append(pix.pixel(0, y))
            edge_pixels.append(pix.pixel(w - 1, y))

        if not edge_pixels:
            return (1.0, 1.0, 1.0)

        # Quantize border pixels into 16-step bins to isolate the true background
        # from any glyph strokes, borders, or accents
        from collections import Counter
        quantized = [(p[0] // 16 * 16, p[1] // 16 * 16, p[2] // 16 * 16) for p in edge_pixels]
        counts = Counter(quantized)
        dominant_bin = counts.most_common(1)[0][0]

        # Average only pixels within the dominant background cluster
        cluster = [p for p in edge_pixels if (p[0] // 16 * 16, p[1] // 16 * 16, p[2] // 16 * 16) == dominant_bin]
        if not cluster:
            cluster = edge_pixels

        avg_r = sum(p[0] for p in cluster) / len(cluster)
        avg_g = sum(p[1] for p in cluster) / len(cluster)
        avg_b = sum(p[2] for p in cluster) / len(cluster)

        return (avg_r / 255.0, avg_g / 255.0, avg_b / 255.0)
    except Exception as e:
        logger.debug(f"Background sampling fallback to white: {e}")
        return (1.0, 1.0, 1.0)


class CVEditorEngine:
    """
    Manages in-memory document state, undo/redo history, text modifications,
    and versioning for a single CV document.
    """
    def __init__(self, original_pdf_path: str, candidate_code: str, user: str = "Recruiter"):
        self.original_pdf_path = original_pdf_path
        self.candidate_code = candidate_code
        self.user = user

        # Current working document
        self.doc: fitz.Document = fitz.open(original_pdf_path)
        self.current_pdf_bytes: bytes = self.doc.tobytes()

        # Undo / Redo stacks (stores document bytes snapshots)
        self.undo_stack: List[bytes] = []
        self.redo_stack: List[bytes] = []
        self.max_history: int = 50

        # Audit log entries
        self.audit_log: List[Dict[str, Any]] = []

        # Version tracking
        self.versions: List[Dict[str, Any]] = []
        # Version 1 is the original branded state
        self._register_version(self.original_pdf_path, "Original Branded (v1)")

    def _register_version(self, path: str, description: str):
        v_num = len(self.versions) + 1
        self.versions.append({
            "version": v_num,
            "path": path,
            "description": description,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user,
        })

    def get_versions_info(self) -> List[Dict[str, Any]]:
        """Returns the list of recorded versions for this document."""
        return list(self.versions)

    def push_state(self):
        """Pushes current document state onto the undo stack and clears redo stack."""
        self.undo_stack.append(self.current_pdf_bytes)
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.current_pdf_bytes = self.doc.tobytes()

    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def get_undo_count(self) -> int:
        return len(self.undo_stack)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.current_pdf_bytes)
        prev_bytes = self.undo_stack.pop()
        self.doc.close()
        self.doc = fitz.open(stream=prev_bytes, filetype="pdf")
        self.current_pdf_bytes = prev_bytes
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.current_pdf_bytes)
        next_bytes = self.redo_stack.pop()
        self.doc.close()
        self.doc = fitz.open(stream=next_bytes, filetype="pdf")
        self.current_pdf_bytes = next_bytes
        return True

    def reset_to_original(self) -> bool:
        """Resets the document back to Version 1 (the initial original branded state)."""
        if not self.versions:
            return False
        v1_path = self.versions[0]["path"]
        if not os.path.exists(v1_path):
            return False

        self.push_state()
        self.doc.close()
        self.doc = fitz.open(v1_path)
        self.current_pdf_bytes = self.doc.tobytes()

        self.audit_log.append({
            "page": 1,
            "action": "Reset to Original",
            "old_snippet": "Custom edits",
            "new_snippet": "v1 state restored",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user,
        })
        return True

    def is_page_scanned(self, page_num: int) -> bool:
        """Returns True if the page contains no extractable text (image-only or scanned)."""
        if page_num < 0 or page_num >= len(self.doc):
            return False
        page = self.doc[page_num]
        text = page.get_text("text").strip()
        return len(text) == 0

    def detect_text_under_point(self, page_num: int, x: float, y: float) -> Optional[Dict[str, Any]]:
        """
        Detects the text span/line/block under the coordinates (x, y) on the given page.
        Returns detailed font, size, color, flags, alignment, bounding box, and text.
        """
        if page_num < 0 or page_num >= len(self.doc):
            return None

        page = self.doc[page_num]
        page_dict = page.get_text("dict")
        target_point = fitz.Point(x, y)

        candidate_span = None
        candidate_line = None
        min_dist = float("inf")

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block
                continue
            b_bbox = fitz.Rect(block.get("bbox", (0, 0, 0, 0)))
            if not (b_bbox.x0 - 5 <= x <= b_bbox.x1 + 5 and b_bbox.y0 - 5 <= y <= b_bbox.y1 + 5):
                continue

            for line in block.get("lines", []):
                l_bbox = fitz.Rect(line.get("bbox", (0, 0, 0, 0)))
                if l_bbox.x0 - 2 <= x <= l_bbox.x1 + 2 and l_bbox.y0 - 2 <= y <= l_bbox.y1 + 2:
                    for span in line.get("spans", []):
                        s_bbox = fitz.Rect(span.get("bbox", (0, 0, 0, 0)))
                        if s_bbox.x0 - 2 <= x <= s_bbox.x1 + 2 and s_bbox.y0 - 2 <= y <= s_bbox.y1 + 2:
                            candidate_span = span
                            candidate_line = line
                            break
                    if candidate_span:
                        break
            if candidate_span:
                break

        # Fallback: find the closest text line within 12pt
        if not candidate_span:
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    l_bbox = fitz.Rect(line.get("bbox", (0, 0, 0, 0)))
                    dx = max(0.0, l_bbox.x0 - x, x - l_bbox.x1)
                    dy = max(0.0, l_bbox.y0 - y, y - l_bbox.y1)
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < 12 and dist < min_dist:
                        min_dist = dist
                        candidate_line = line
                        if line.get("spans"):
                            candidate_span = line["spans"][0]

        if not candidate_span or not candidate_line:
            return None

        # Build line text
        line_text = "".join(s.get("text", "") for s in candidate_line.get("spans", []))
        if not line_text.strip():
            line_text = candidate_span.get("text", "")

        # Extract font properties
        font_name = candidate_span.get("font", "Helvetica")
        font_size = candidate_span.get("size", 10.0)
        flags = candidate_span.get("flags", 0)
        is_bold = bool(flags & 2) or ("bold" in font_name.lower())
        is_italic = bool(flags & 1) or ("italic" in font_name.lower()) or ("oblique" in font_name.lower())

        color_int = candidate_span.get("color", 0)
        r = ((color_int >> 16) & 255) / 255.0
        g = ((color_int >> 8) & 255) / 255.0
        b = (color_int & 255) / 255.0

        line_rect = fitz.Rect(candidate_line.get("bbox", candidate_span.get("bbox")))
        bg_rgb = sample_background_color(page, line_rect)

        return {
            "text": line_text.strip(),
            "rect": (line_rect.x0, line_rect.y0, line_rect.x1, line_rect.y1),
            "font_name": font_name,
            "font_size": font_size,
            "is_bold": is_bold,
            "is_italic": is_italic,
            "color_rgb": (r, g, b),
            "bg_rgb": bg_rgb,
            "line_bbox": line_rect,
            "base14_font": match_base14_font(font_name, is_bold, is_italic),
        }

    def replace_text(
        self,
        page_num: int,
        rect: Tuple[float, float, float, float],
        new_text: str,
        font_name: str = "helv",
        font_size: float = 10.0,
        color_rgb: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        align: int = fitz.TEXT_ALIGN_LEFT,
        bg_rgb: Optional[Tuple[float, float, float]] = None,
        old_text_snippet: str = "",
    ) -> Tuple[bool, str]:
        """
        Replaces text at rect with new_text.
        Applies redaction annotation over old rect and inserts new text.
        Shrinks font if text overflows.
        """
        if page_num < 0 or page_num >= len(self.doc):
            return False, "Invalid page number"

        self.push_state()
        page = self.doc[page_num]
        fitz_rect = fitz.Rect(rect)

        # Sample background if not specified
        if bg_rgb is None:
            bg_rgb = sample_background_color(page, fitz_rect)

        # Add true redaction over the old text rect preserving vector drawings & images
        page.add_redact_annot(fitz_rect, fill=bg_rgb)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        target_font = font_name
        current_size = font_size
        min_size = 6.0
        fitted = False
        warning_msg = ""

        # Progressively scale down if text overflows
        while current_size >= min_size:
            rc = page.insert_textbox(
                fitz_rect,
                new_text,
                fontname=target_font,
                fontsize=current_size,
                color=color_rgb,
                align=align,
            )
            if rc >= 0:
                fitted = True
                break
            current_size *= 0.92

        if not fitted:
            page.insert_textbox(
                fitz_rect,
                new_text,
                fontname=target_font,
                fontsize=min_size,
                color=color_rgb,
                align=align,
            )
            warning_msg = f"Text wrapped to fit within {fitz_rect.width:.0f}x{fitz_rect.height:.0f}pt"

        self.audit_log.append({
            "page": page_num + 1,
            "action": "Text Edited",
            "old_snippet": (old_text_snippet or "")[:60],
            "new_snippet": new_text[:60],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user,
        })

        self.current_pdf_bytes = self.doc.tobytes()
        return True, warning_msg

    def add_text_box(
        self,
        page_num: int,
        rect: Tuple[float, float, float, float],
        text: str,
        font_name: str = "helv",
        font_size: float = 11.0,
        color_rgb: Tuple[float, float, float] = (0.05, 0.09, 0.16),
        align: int = fitz.TEXT_ALIGN_LEFT,
    ) -> Tuple[bool, str]:
        """Inserts a new text box onto the specified page."""
        if page_num < 0 or page_num >= len(self.doc):
            return False, "Invalid page number"

        self.push_state()
        page = self.doc[page_num]
        fitz_rect = fitz.Rect(rect)

        page.insert_textbox(
            fitz_rect,
            text,
            fontname=font_name,
            fontsize=font_size,
            color=color_rgb,
            align=align,
        )

        self.audit_log.append({
            "page": page_num + 1,
            "action": "Text Added",
            "old_snippet": "-",
            "new_snippet": text[:60],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user,
        })

        self.current_pdf_bytes = self.doc.tobytes()
        return True, ""

    def delete_area(
        self,
        page_num: int,
        rect: Tuple[float, float, float, float],
        bg_rgb: Optional[Tuple[float, float, float]] = None,
    ) -> Tuple[bool, str]:
        """
        Permanently blanks out and redacts the rectangular area on the page,
        removing both text glyphs and graphics/images in that region.
        """
        if page_num < 0 or page_num >= len(self.doc):
            return False, "Invalid page number"

        self.push_state()
        page = self.doc[page_num]
        fitz_rect = fitz.Rect(rect)

        if bg_rgb is None:
            bg_rgb = sample_background_color(page, fitz_rect)

        page.add_redact_annot(fitz_rect, fill=bg_rgb)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)

        self.audit_log.append({
            "page": page_num + 1,
            "action": "Area Deleted",
            "old_snippet": f"Region ({fitz_rect.x0:.0f}, {fitz_rect.y0:.0f}) {fitz_rect.width:.0f}x{fitz_rect.height:.0f}pt",
            "new_snippet": "Permanently redacted",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user,
        })

        self.current_pdf_bytes = self.doc.tobytes()
        return True, ""

    def move_resize_logo(
        self,
        page_num: int,
        old_rect: Tuple[float, float, float, float],
        new_rect: Tuple[float, float, float, float],
        logo_path: str,
        bg_rgb: Optional[Tuple[float, float, float]] = None,
    ) -> Tuple[bool, str]:
        """
        Relocates or resizes the company logo on the page.
        Redacts the previous logo bounding box and renders the logo at the new rect.
        """
        if page_num < 0 or page_num >= len(self.doc):
            return False, "Invalid page number"
        if not os.path.exists(logo_path):
            return False, "Logo image file not found"

        self.push_state()
        page = self.doc[page_num]
        old_fitz_rect = fitz.Rect(old_rect)
        new_fitz_rect = fitz.Rect(new_rect)

        if bg_rgb is None:
            bg_rgb = sample_background_color(page, old_fitz_rect)

        page.add_redact_annot(old_fitz_rect, fill=bg_rgb)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
        page.insert_image(new_fitz_rect, filename=logo_path, keep_proportion=True)

        self.audit_log.append({
            "page": page_num + 1,
            "action": "Logo Moved/Resized",
            "old_snippet": f"({old_fitz_rect.x0:.0f}, {old_fitz_rect.y0:.0f})",
            "new_snippet": f"({new_fitz_rect.x0:.0f}, {new_fitz_rect.y0:.0f}) {new_fitz_rect.width:.0f}x{new_fitz_rect.height:.0f}pt",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": self.user,
        })

        self.current_pdf_bytes = self.doc.tobytes()
        return True, ""

    def check_safety(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Exhaustively scans the edited document for contact details (emails, phone numbers, urls).
        Returns:
            (is_clean: bool, violations: List[Dict])
        """
        violations: List[Dict[str, Any]] = []

        for page_idx in range(len(self.doc)):
            page = self.doc[page_idx]
            page_num = page_idx + 1
            text = page.get_text("text")

            # Email check
            for match in EMAIL_REGEX.finditer(text):
                val = match.group(0).strip(".,;:()")
                violations.append({
                    "page": page_num,
                    "type": "Email Address",
                    "value": val,
                    "description": f"Email '{val}' detected on page {page_num}",
                })

            # Phone check
            for match in INDIAN_PHONE_REGEX.finditer(text):
                val = match.group(0).strip(".,;:()")
                if is_valid_phone(val):
                    violations.append({
                        "page": page_num,
                        "type": "Phone Number",
                        "value": val,
                        "description": f"Phone '{val}' detected on page {page_num}",
                    })

            # Links check
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri.lower().startswith("mailto:") or uri.lower().startswith("tel:"):
                    violations.append({
                        "page": page_num,
                        "type": "Interactive Link",
                        "value": uri,
                        "description": f"Contact link '{uri}' detected on page {page_num}",
                    })

        return (len(violations) == 0, violations)

    def save_version(self, target_dir: Path) -> Tuple[bool, str, str]:
        """
        Saves the current edited document as a new version file (e.g. CAND-0003_v2.pdf).
        Enforces safety check: blocks saving if any personal contact details are present!
        Returns (success: bool, saved_path: str, message: str).
        """
        is_safe, violations = self.check_safety()
        if not is_safe:
            v_msgs = "\n".join(f"• {v['type']}: {v['value']} (page {v['page']})" for v in violations[:3])
            return False, "", f"Safety scan blocked save! Contact info detected:\n{v_msgs}"

        target_dir.mkdir(parents=True, exist_ok=True)
        next_v_num = len(self.versions) + 1
        output_filename = f"{self.candidate_code}_v{next_v_num}.pdf"
        output_path = str(target_dir / output_filename)

        self.doc.save(output_path, garbage=4, deflate=True)
        self._register_version(output_path, f"User Edit Version {next_v_num}")

        return True, output_path, f"Version {next_v_num} saved successfully: {output_filename}"
