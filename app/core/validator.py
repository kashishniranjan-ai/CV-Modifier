"""
Final verification engine:
Scans the output PDF text, links, and annotations again.
Blocks sending/exporting if any email or phone number pattern is still found!
"""

from typing import Tuple, List, Dict, Any
import pymupdf as fitz
from app.core.regex_patterns import EMAIL_REGEX, INDIAN_PHONE_REGEX, is_valid_phone
from app.logger import logger


def validate_clean_pdf(pdf_path: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Exhaustively scans the final rendered PDF.
    Returns:
        (is_clean: bool, violations: List[Dict])
    If any email or phone number is found, is_clean will be False.
    """
    violations: List[Dict[str, Any]] = []

    try:
        doc = fitz.open(pdf_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1

            # 1. Check extracted text stream
            text = page.get_text("text")

            # Check for emails
            for match in EMAIL_REGEX.finditer(text):
                val = match.group(0).strip(".,;:()")
                violations.append({
                    "page": page_num,
                    "type": "Email Address",
                    "value": val,
                    "description": f"Found residual email '{val}' on page {page_num}",
                })

            # Check for phone numbers
            for match in INDIAN_PHONE_REGEX.finditer(text):
                val = match.group(0).strip(".,;:()")
                if is_valid_phone(val):
                    violations.append({
                        "page": page_num,
                        "type": "Phone Number",
                        "value": val,
                        "description": f"Found residual phone number '{val}' on page {page_num}",
                    })

            # 2. Check remaining link annotations
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri.lower().startswith("mailto:"):
                    violations.append({
                        "page": page_num,
                        "type": "Mailto Link",
                        "value": uri,
                        "description": f"Found clickable mailto link '{uri}' on page {page_num}",
                    })
                elif uri.lower().startswith("tel:"):
                    violations.append({
                        "page": page_num,
                        "type": "Tel Link",
                        "value": uri,
                        "description": f"Found clickable tel link '{uri}' on page {page_num}",
                    })

        doc.close()

    except Exception as e:
        logger.error(f"Error validating output PDF: {e}", exc_info=True)
        violations.append({
            "page": 0,
            "type": "Validation Error",
            "value": str(e),
            "description": f"Could not verify PDF file: {e}",
        })

    is_clean = len(violations) == 0
    if not is_clean:
        logger.warning(f"Validation FAILED for {pdf_path}: {len(violations)} violations detected!")
    else:
        logger.info(f"Validation PASSED for {pdf_path}: 0 sensitive items detected.")

    return is_clean, violations
