"""
Unit tests for PDF true redaction, link removal, metadata stripping,
DOCX redaction, and final safety validation.
"""

import os
from pathlib import Path
import pytest
import pymupdf as fitz
import docx

from app.core.pdf_redactor import redact_and_brand_pdf
from app.core.docx_redactor import redact_docx, convert_docx_to_pdf
from app.core.validator import validate_clean_pdf


SAMPLE_PDF = "sample_data/sample_cv_john_doe.pdf"
SAMPLE_DOCX = "sample_data/sample_cv_priya_sharma.docx"
SAMPLE_LOGO = "data/assets/scalexpro_logo.png"


class TestPDFRedaction:
    def test_pdf_true_redaction_and_metadata_stripping(self, tmp_path):
        output_pdf = str(tmp_path / "redacted_john_doe.pdf")

        # 1. Run redaction
        result = redact_and_brand_pdf(
            input_path=SAMPLE_PDF,
            output_path=output_pdf,
            logo_path=SAMPLE_LOGO,
            redaction_color="white",
            redact_email=True,
            redact_phone=True,
            redact_urls=True,
            redact_address=True,
            redact_metadata=True,
            add_logo=True,
        )

        assert result.success is True
        assert len(result.redactions_applied) > 0
        assert os.path.exists(output_pdf)

        # 2. Inspect redacted PDF text stream
        doc = fitz.open(output_pdf)
        all_text = ""
        for page in doc:
            all_text += page.get_text("text")

        # Verify sensitive info AND labels are permanently GONE from text stream
        assert "john.doe@techpro-solutions.com" not in all_text
        assert "Email:" not in all_text
        assert "Phone:" not in all_text
        assert "Alternative Phone:" not in all_text
        assert "Landline:" not in all_text
        assert "Residential Address:" not in all_text
        assert "98765 43210" not in all_text
        assert "09876543211" not in all_text
        assert "linkedin.com/in/johndoe-tech" not in all_text
        assert "github.com/johndoe-dev" not in all_text
        assert "560103" not in all_text

        # Verify logo is placed adaptively (width within valid adaptive range)
        img_info = doc[0].get_image_info()
        assert len(img_info) > 0, "Logo image must be present on page 1"
        bbox = img_info[0]["bbox"]
        logo_w = bbox[2] - bbox[0]
        logo_h = bbox[3] - bbox[1]
        # Adaptive: logo height must be in [_MIN_LOGO_H, _MAX_LOGO_H]
        from app.core.logo_placer import _MIN_LOGO_H, _MAX_LOGO_H
        assert logo_h >= _MIN_LOGO_H - 1.0, f"Logo height {logo_h:.1f} below minimum"
        assert logo_h <= _MAX_LOGO_H + 1.0, f"Logo height {logo_h:.1f} above maximum"
        # Logo must start near the left of the page (not beyond 200pt from left)
        assert bbox[0] < 200, f"Logo x0 {bbox[0]:.1f} unexpectedly far from left"
        # Logo must be at the top of the page (y0 < 80pt)
        assert bbox[1] < 80, f"Logo y0 {bbox[1]:.1f} unexpectedly far from top"

        # 3. Verify Links are removed
        links = doc[0].get_links()
        for link in links:
            uri = link.get("uri", "")
            assert not uri.lower().startswith("mailto:")
            assert not uri.lower().startswith("tel:")
            assert "techpro-solutions" not in uri

        # 4. Verify Metadata is stripped
        meta = doc.metadata
        assert meta.get("author", "") == ""
        assert meta.get("title", "") == ""
        assert meta.get("keywords", "") == ""

        doc.close()

        # 5. Verify final safety scanner passes
        is_clean, violations = validate_clean_pdf(output_pdf)
        assert is_clean is True
        assert len(violations) == 0


class TestDOCXRedaction:
    def test_docx_redaction_and_pdf_export(self, tmp_path):
        output_docx = str(tmp_path / "redacted_priya.docx")
        output_pdf = str(tmp_path / "redacted_priya.pdf")

        # 1. Redact DOCX
        res = redact_docx(
            input_path=SAMPLE_DOCX,
            output_docx_path=output_docx,
            redact_email=True,
            redact_phone=True,
            redact_urls=True,
            redact_address=True,
            redact_metadata=True,
        )
        assert res["success"] is True

        # Inspect redacted DOCX
        doc = docx.Document(output_docx)
        full_text = " ".join([p.text for p in doc.paragraphs])
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text += " " + cell.text

        assert "priya.sharma@innovate-tech.in" not in full_text
        assert "91234-56789" not in full_text
        assert "priya.personal@gmail.com" not in full_text
        assert "9811223344" not in full_text
        assert doc.core_properties.author == ""

        # 2. Convert to PDF and brand
        conv_ok = convert_docx_to_pdf(output_docx, output_pdf)
        assert conv_ok is True
        assert os.path.exists(output_pdf)

        # 3. Final safety check on exported PDF
        is_clean, violations = validate_clean_pdf(output_pdf)
        assert is_clean is True
        assert len(violations) == 0


class TestValidatorBlocksDirtyPDF:
    def test_validator_blocks_unredacted_pdf(self):
        # Original sample PDF still contains contact details, so validator should return False
        is_clean, violations = validate_clean_pdf(SAMPLE_PDF)
        assert is_clean is False
        assert len(violations) > 0
        violation_types = {v["type"] for v in violations}
        assert "Email Address" in violation_types or "Phone Number" in violation_types
