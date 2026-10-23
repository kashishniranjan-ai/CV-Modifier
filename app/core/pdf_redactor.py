"""
PyMuPDF-based PDF redactor with true redaction, link removal,
metadata stripping, and adaptive company logo branding.
Logo size and position are chosen automatically from page layout analysis.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pymupdf as fitz
from PIL import Image

from app.core.logo_placer import apply_adaptive_logo_to_doc

from app.core.regex_patterns import (
    find_all_sensitive_info,
    EMAIL_REGEX,
    INDIAN_PHONE_REGEX,
    LINKEDIN_REGEX,
    GITHUB_REGEX,
    PORTFOLIO_REGEX,
    GENERAL_URL_REGEX,
    CONTACT_HEADING_REGEX,
    is_valid_phone,
)
from app.logger import logger


class PDFRedactionResult:
    """Stores the outcome of a PDF redaction run."""
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.redactions_applied: List[Dict[str, Any]] = []
        self.links_removed: int = 0
        self.metadata_cleared: bool = False
        self.logo_applied: bool = False
        self.logo_audit: List[Dict[str, Any]] = []   # adaptive placement details
        self.total_pages: int = 0
        self.success: bool = True
        self.error_message: Optional[str] = None


def get_pdf_page_pixmap(doc_or_path, page_num: int, dpi: int = 140) -> bytes:
    """
    Renders a given PDF page to PNG bytes for UI preview.
    """
    close_doc = False
    if isinstance(doc_or_path, (str, Path)):
        doc = fitz.open(str(doc_or_path))
        close_doc = True
    else:
        doc = doc_or_path

    try:
        page = doc[page_num]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        return png_bytes
    finally:
        if close_doc:
            doc.close()


def redact_and_brand_pdf(
    input_path: str,
    output_path: str,
    logo_path: Optional[str] = None,
    redaction_color: str = "white",  # "white" or "black"
    redact_email: bool = True,
    redact_phone: bool = True,
    redact_urls: bool = True,
    redact_address: bool = True,
    redact_metadata: bool = True,
    add_logo: bool = True,
    max_logo_w: float = 180.0,   # kept for backwards-compat; ignored (adaptive now)
    max_logo_h: float = 60.0,   # kept for backwards-compat; ignored (adaptive now)
    logo_size_override: str = "Auto",      # "Auto"|"Small"|"Medium"|"Large"
    logo_position_override: str = "Auto",  # "Auto"|"Left"|"Center"|"Right"
) -> PDFRedactionResult:
    """
    Performs complete, true PDF redaction:
    1. Text detection and true redaction (add_redact_annot + apply_redactions)
       including contact labels, icons, addresses, and section headings.
    2. Deletion of mailto:, tel:, and web link annotations
    3. Removal of sensitive text from headers/footers
    4. Stripping of PDF metadata (author, title, producer, dates)
    5. Insertion of company logo at the top-left of every page (~180px wide) without overlapping content
    """
    result = PDFRedactionResult(output_path)

    fill_color = (1, 1, 1) if redaction_color == "white" else (0.0, 0.0, 0.0)

    try:
        doc = fitz.open(input_path)
        result.total_pages = len(doc)
        logger.info(f"Starting redaction on {input_path} ({result.total_pages} pages)")

        # Prepare categories to redact
        active_categories = set()
        if redact_email:
            active_categories.add("Email")
        if redact_phone:
            active_categories.add("Phone Number")
        if redact_urls:
            active_categories.update(["LinkedIn URL", "GitHub URL", "Portfolio/Social URL", "Website URL"])
        if redact_address:
            active_categories.update(["Address", "Postal/PIN Code"])
        if redact_email or redact_phone or redact_urls or redact_address:
            active_categories.add("Contact Heading")

        # ----------------------------------------------------
        # Step 1: Scan and Redact each page
        # ----------------------------------------------------
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text("text")

            # Detect sensitive text
            detected = find_all_sensitive_info(page_text)
            page_redacted_values = set()

            for item in detected:
                category = item["category"]
                value = item["value"].strip()

                if category not in active_categories:
                    continue

                if not value or value in page_redacted_values:
                    continue

                # Search for rectangles matching the detected string
                rects = page.search_for(value)

                # Fallback 1: strip unicode icons from search string if search_for returned empty
                if not rects:
                    clean_val = re.sub(
                        r"[\u260e\u260f\u2706\u2709\U0001f4de\U0001f4e7\U0001f4cd\U0001f517\U0001f310\U0001f4f1\U0001f3e0\U0001f4bb\ufe0f]",
                        "",
                        value,
                    ).strip()
                    if clean_val and clean_val != value:
                        rects = page.search_for(clean_val)

                # Fallback 2: if label and value might be in separate text objects, e.g. "Phone:" and "+91 98765 43210"
                if not rects and ":" in value:
                    prefix_part, sep, rest_part = value.partition(":")
                    p_rects = page.search_for(prefix_part + ":") if len(prefix_part) >= 2 else []
                    r_rects = page.search_for(rest_part.strip()) if len(rest_part.strip()) >= 3 else []
                    if p_rects or r_rects:
                        rects = p_rects + r_rects

                # Fallback 3: split by whitespace and search token by token if still not found
                if not rects:
                    parts = value.split()
                    if len(parts) > 1:
                        part_rects = []
                        for p in parts:
                            if len(p) > 2:
                                part_rects.extend(page.search_for(p))
                        rects = part_rects

                if rects:
                    for r in rects:
                        page.add_redact_annot(r, fill=fill_color)

                    page_redacted_values.add(value)
                    result.redactions_applied.append({
                        "page": page_idx + 1,
                        "category": category,
                        "value": value,
                        "count": len(rects),
                        "status": "Redacted (Permanently Deleted)",
                    })

            # Also check headers and footers specifically for stray phone/email
            words = page.get_text("words")  # (x0, y0, x1, y1, "word", ...)
            for w in words:
                w_text = w[4]
                w_rect = fitz.Rect(w[0], w[1], w[2], w[3])
                # Check top 60 pt (header) or bottom 60 pt (footer)
                if w[1] < 60 or w[3] > (page.rect.height - 60):
                    if EMAIL_REGEX.search(w_text) and redact_email:
                        page.add_redact_annot(w_rect, fill=fill_color)
                        result.redactions_applied.append({
                            "page": page_idx + 1,
                            "category": "Header/Footer Email",
                            "value": w_text,
                            "count": 1,
                            "status": "Redacted (Permanently Deleted)",
                        })
                    elif is_valid_phone(w_text) and redact_phone:
                        page.add_redact_annot(w_rect, fill=fill_color)
                        result.redactions_applied.append({
                            "page": page_idx + 1,
                            "category": "Header/Footer Phone",
                            "value": w_text,
                            "count": 1,
                            "status": "Redacted (Permanently Deleted)",
                        })

            # Apply true redactions for this page - removes underlying text & vectors
            page.apply_redactions()

            # Second pass: remove orphaned separator lines (e.g. isolated " | " or " • " left after redaction)
            page_text_after = page.get_text("text")
            has_orphans = False
            for line in page_text_after.splitlines():
                stripped = line.strip()
                if stripped and re.fullmatch(r"[\s\|\•\·\-\,\:\;]+", stripped):
                    for r in page.search_for(line):
                        page.add_redact_annot(r, fill=fill_color)
                        has_orphans = True
            if has_orphans:
                page.apply_redactions()

            # ----------------------------------------------------
            # Step 2: Remove mailto:, tel:, and sensitive URL links
            # ----------------------------------------------------
            links = page.get_links()
            for link in links:
                uri = link.get("uri", "")
                should_delete = False

                if uri.lower().startswith("mailto:") or uri.lower().startswith("tel:"):
                    should_delete = True
                elif uri:
                    for cat_regex in (LINKEDIN_REGEX, GITHUB_REGEX, PORTFOLIO_REGEX, EMAIL_REGEX):
                        if cat_regex.search(uri):
                            should_delete = True
                            break

                if should_delete:
                    page.delete_link(link)
                    result.links_removed += 1

        # ----------------------------------------------------
        # Step 3: Strip PDF Metadata
        # ----------------------------------------------------
        if redact_metadata:
            doc.set_metadata({
                "format": "",
                "title": "",
                "author": "",
                "subject": "",
                "keywords": "",
                "creator": "",
                "producer": "ScaleXPro",
                "creationDate": "",
                "modDate": "",
                "trapped": "",
            })
            result.metadata_cleared = True

        # ----------------------------------------------------
        # Step 4: Adaptive logo placement
        # ----------------------------------------------------
        if add_logo and logo_path and os.path.exists(logo_path):
            try:
                logo_audit = apply_adaptive_logo_to_doc(
                    doc,
                    logo_path,
                    size_override=logo_size_override,
                    position_override=logo_position_override,
                )
                result.logo_applied = True
                result.logo_audit = logo_audit
                # Merge logo audit into main redaction manifest for audit trail display
                result.redactions_applied.extend(logo_audit)
            except Exception as e:
                logger.error(f"Error applying company logo: {e}", exc_info=True)

        # ----------------------------------------------------
        # Step 5: Save with full garbage collection & compression
        # ----------------------------------------------------
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc.save(
            output_path,
            garbage=4,        # Maximum garbage collection: deletes unreferenced streams
            deflate=True,     # Compress streams
            clean=True,       # Sanitize content streams
        )
        doc.close()
        logger.info(f"Redaction completed successfully: {output_path}")

    except Exception as e:
        logger.error(f"Redaction failed: {e}", exc_info=True)
        result.success = False
        result.error_message = str(e)

    return result


# Old _apply_logo_to_pages removed; logic replaced by app/core/logo_placer.py
