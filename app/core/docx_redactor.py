"""
python-docx redactor:
1. Detects and removes sensitive contact details in paragraphs and tables.
2. Removes <w:hyperlink> XML elements and link targets.
3. Clears document core properties (author, title, comments, dates).
4. Cleans headers and footers.
5. Converts DOCX to PDF (using MS Word COM if available, or high-fidelity ReportLab renderer fallback).
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.core.regex_patterns import (
    find_all_sensitive_info,
    EMAIL_REGEX,
    INDIAN_PHONE_REGEX,
    LINKEDIN_REGEX,
    GITHUB_REGEX,
    PORTFOLIO_REGEX,
    GENERAL_URL_REGEX,
    is_valid_phone,
)
from app.logger import logger


def _remove_hyperlinks_from_paragraph(paragraph):
    """Removes all w:hyperlink XML elements from a python-docx paragraph."""
    p_element = paragraph._p
    hyperlinks = p_element.xpath(".//w:hyperlink")
    for hl in hyperlinks:
        # Remove hyperlink element from parent
        parent = hl.getparent()
        if parent is not None:
            parent.remove(hl)


def _redact_text_in_runs(paragraph, sensitive_items: List[Dict[str, Any]]) -> int:
    """
    Scans paragraph text, matches sensitive items, and cleanses the runs.
    Returns the count of redactions performed.
    """
    p_text = paragraph.text
    if not p_text.strip():
        return 0

    detected = find_all_sensitive_info(p_text)
    if not detected:
        return 0

    redactions_count = 0
    # Collect values to redact, longest first to avoid partial replacements
    values_to_remove = sorted([item["value"] for item in detected], key=len, reverse=True)

    for val in values_to_remove:
        if val in paragraph.text:
            # First attempt: if val is contained inside a single run, replace it
            replaced = False
            for run in paragraph.runs:
                if val in run.text:
                    run.text = run.text.replace(val, "")
                    replaced = True
                    redactions_count += 1
            # If split across multiple runs:
            if not replaced and val in paragraph.text:
                new_text = paragraph.text.replace(val, "")
                # Clear all runs and assign to first run
                for i, run in enumerate(paragraph.runs):
                    if i == 0:
                        run.text = new_text
                    else:
                        run.text = ""
                redactions_count += 1

    return redactions_count


def redact_docx(
    input_path: str,
    output_docx_path: str,
    redact_email: bool = True,
    redact_phone: bool = True,
    redact_urls: bool = True,
    redact_address: bool = True,
    redact_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Cleanses a DOCX document by deleting sensitive text, removing hyperlinks,
    clearing core properties, and cleaning headers/footers.
    """
    result = {
        "success": True,
        "redactions_applied": [],
        "output_path": output_docx_path,
        "error_message": None,
    }

    try:
        doc = docx.Document(input_path)

        # 1. Process paragraphs
        for idx, p in enumerate(doc.paragraphs):
            _remove_hyperlinks_from_paragraph(p)
            detected = find_all_sensitive_info(p.text)
            if detected:
                for d in detected:
                    result["redactions_applied"].append({
                        "page": 1,  # DOCX doesn't have fixed pages until layout
                        "category": d["category"],
                        "value": d["value"],
                        "count": 1,
                        "status": "Removed from DOCX",
                    })
                _redact_text_in_runs(p, detected)
                if p.text and re.fullmatch(r"[\s\|\•\·\-\,\:\;]+", p.text):
                    for run in p.runs:
                        run.text = ""

        # 2. Process tables
        for t_idx, table in enumerate(doc.tables):
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        _remove_hyperlinks_from_paragraph(p)
                        detected = find_all_sensitive_info(p.text)
                        if detected:
                            for d in detected:
                                result["redactions_applied"].append({
                                    "page": 1,
                                    "category": d["category"],
                                    "value": d["value"],
                                    "count": 1,
                                    "status": "Removed from Table",
                                })
                            _redact_text_in_runs(p, detected)
                            if p.text and re.fullmatch(r"[\s\|\•\·\-\,\:\;]+", p.text):
                                for run in p.runs:
                                    run.text = ""

        # 3. Process headers and footers
        for s_idx, section in enumerate(doc.sections):
            for p in section.header.paragraphs:
                _remove_hyperlinks_from_paragraph(p)
                detected = find_all_sensitive_info(p.text)
                if detected:
                    _redact_text_in_runs(p, detected)

            for p in section.footer.paragraphs:
                _remove_hyperlinks_from_paragraph(p)
                detected = find_all_sensitive_info(p.text)
                if detected:
                    _redact_text_in_runs(p, detected)

        # 4. Strip document core properties
        if redact_metadata:
            core = doc.core_properties
            core.author = ""
            core.last_modified_by = ""
            core.title = ""
            core.subject = ""
            core.keywords = ""
            core.comments = ""
            core.category = ""

        os.makedirs(os.path.dirname(os.path.abspath(output_docx_path)), exist_ok=True)
        doc.save(output_docx_path)
        logger.info(f"Redacted DOCX saved to {output_docx_path}")

    except Exception as e:
        logger.error(f"Error redacting DOCX: {e}", exc_info=True)
        result["success"] = False
        result["error_message"] = str(e)

    return result


def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """
    Converts a DOCX file to PDF format offline on Windows.
    Tries Microsoft Word COM automation first (100% native layout fidelity).
    Falls back to ReportLab document synthesizer if Word is not installed.
    """
    docx_path_abs = str(Path(docx_path).resolve())
    pdf_path_abs = str(Path(pdf_path).resolve())
    os.makedirs(os.path.dirname(pdf_path_abs), exist_ok=True)

    # Strategy 1: Try MS Word COM via comtypes or win32com
    try:
        import comtypes.client
        import pythoncom
        import gc

        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = comtypes.client.CreateObject("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(docx_path_abs)
            doc.ExportAsFixedFormat(pdf_path_abs, 17)
            doc.Close(SaveChanges=False)
            logger.info("Successfully converted DOCX to PDF using MS Word COM.")
            return True
        finally:
            if doc is not None:
                del doc
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
                del word
            gc.collect()
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
    except Exception as e:
        logger.info(f"MS Word COM not available or failed ({e}). Using pure Python ReportLab fallback.")

    # Strategy 2: Pure Python ReportLab fallback
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        doc = docx.Document(docx_path)
        pdf_doc = SimpleDocTemplate(
            pdf_path_abs,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]
        h1_style = styles["Heading1"]
        h2_style = styles["Heading2"]

        story = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                story.append(Spacer(1, 6))
                continue

            # Determine heading level from style
            style_name = p.style.name.lower()
            if "heading 1" in style_name or "title" in style_name:
                story.append(Paragraph(text, h1_style))
                story.append(Spacer(1, 4))
            elif "heading 2" in style_name or "heading 3" in style_name:
                story.append(Paragraph(text, h2_style))
                story.append(Spacer(1, 4))
            else:
                story.append(Paragraph(text, normal_style))
                story.append(Spacer(1, 4))

        # Add tables
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [Paragraph(cell.text.strip(), normal_style) for cell in row.cells]
                table_data.append(row_data)
            if table_data:
                t = Table(table_data)
                t.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))

        if not story:
            story.append(Paragraph("Empty Document", normal_style))

        pdf_doc.build(story)
        logger.info(f"Successfully converted DOCX to PDF using ReportLab fallback: {pdf_path_abs}")
        return True

    except Exception as e:
        logger.error(f"Failed to convert DOCX to PDF using ReportLab: {e}", exc_info=True)
        return False
