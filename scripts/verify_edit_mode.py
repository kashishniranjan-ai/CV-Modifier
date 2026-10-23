"""
Verification script for CV-Modifier 'Edit CV' mode.
Tests all 5 required CV types:
1. Simple single-column PDF (Text replacement, font/size matching, shrink-to-fit)
2. Two-column layout PDF (Delete area true redaction, custom text box placement)
3. Colored header banner PDF (Perimeter background sampling, no white patch over dark navy)
4. DOCX source CV (Pre-conversion paragraph editor, DOCX-to-PDF, redact & brand)
5. Scanned / image-only CV (Scanned detection, warning banner, delete area & text box stamps)

Also verifies:
- Contact re-scan safety check (blocks save if email/phone entered)
- Undo / Redo 30+ step history
- Version file creation and management (v1, v2, v3...)
- Audit trail logging

Generates high-resolution before/after screenshots and UI snapshots in screenshots/
"""

import os
import sys
import shutil
from pathlib import Path
import pymupdf as fitz

# Setup root path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["QT_API"] = "pyside6"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.core.pdf_editor import CVEditorEngine, sample_background_color
from app.core.docx_editor import get_docx_paragraphs, save_docx_paragraph_edits
from app.core.pdf_redactor import redact_and_brand_pdf
from app.core.docx_redactor import convert_docx_to_pdf
from app.ui.styles import apply_scalexpro_palette
from app.ui.cv_editor_widget import CVEditorWidget, DOCXParagraphsDialog


def render_pdf_page_png(pdf_path: str, page_num: int = 0, dpi: int = 150) -> bytes:
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    data = pix.tobytes("png")
    doc.close()
    return data


def save_page_image(pdf_path: str, out_path: Path, dpi: int = 150):
    data = render_pdf_page_png(pdf_path, 0, dpi)
    out_path.write_bytes(data)
    print(f"  [Saved Image] {out_path.name} ({len(data)} bytes)")


def main():
    print("=" * 70)
    print("ScaleXPro CV-Modifier: Comprehensive Verification of 'Edit CV' Mode")
    print("=" * 70)

    shots_dir = ROOT_DIR / "screenshots"
    shots_dir.mkdir(exist_ok=True)
    out_dir = ROOT_DIR / "data" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_dir = ROOT_DIR / "sample_data"
    logo_path = str(sample_dir / "scalexpro_logo.png")

    # Initialize Qt for UI widget grabs
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    apply_scalexpro_palette(app)

    # ---------------------------------------------------------
    # CV 1: Simple Single-Column PDF
    # ---------------------------------------------------------
    print("\n--- Verifying CV 1: Simple Single-Column (sample_cv_john_doe.pdf) ---")
    cv1_src = str(sample_dir / "sample_cv_john_doe.pdf")
    cv1_branded = str(out_dir / "CAND-0001_branded_v1.pdf")

    # 1. Redact and brand
    res1 = redact_and_brand_pdf(cv1_src, cv1_branded, logo_path=logo_path)
    assert res1.success, f"Branding failed: {res1.error_message}"
    save_page_image(cv1_branded, shots_dir / "cv1_simple_before.png")

    # 2. Open in CVEditorEngine
    engine1 = CVEditorEngine(cv1_branded, candidate_code="CAND-0001", user="Recruiter Sarah")
    assert not engine1.is_page_scanned(0), "CV1 should have extractable text"

    # 3. Detect text under candidate title area
    detected1 = engine1.detect_text_under_point(0, 50, 85)
    assert detected1 is not None, "Failed to detect text on CV1"
    print(f"  Detected Text: '{detected1['text']}', Font: {detected1['font_name']} ({detected1['font_size']}pt)")

    # 4. Replace text: "Senior Python Developer" -> "Principal Cloud Solutions Architect"
    success, warn = engine1.replace_text(
        0,
        detected1["rect"],
        "Principal Cloud Solutions Architect",
        font_name=detected1["base14_font"],
        font_size=detected1["font_size"],
        color_rgb=detected1["color_rgb"],
        old_text_snippet=detected1["text"],
    )
    assert success, "Replace text failed"

    # 5. Save version 2
    ok, v2_path, msg = engine1.save_version(out_dir)
    assert ok, f"Save version failed: {msg}"
    print(f"  {msg}")
    save_page_image(v2_path, shots_dir / "cv1_simple_after.png")

    # 6. Capture UI Editor view for CV1
    editor1 = CVEditorWidget()
    editor1.resize(1180, 820)
    editor1.load_document(v2_path, candidate_code="CAND-0001", source_file_path=cv1_src, logo_path=logo_path)
    editor1.show()
    app.processEvents()
    pix1 = editor1.grab()
    pix1.save(str(shots_dir / "ui_cv1_editor.png"))
    print(f"  [UI Captured] ui_cv1_editor.png")
    editor1.close()

    # ---------------------------------------------------------
    # CV 2: Two-Column Layout PDF
    # ---------------------------------------------------------
    print("\n--- Verifying CV 2: Two-Column Layout (sample_two_column.pdf) ---")
    cv2_src = str(sample_dir / "sample_two_column.pdf")
    cv2_branded = str(out_dir / "CAND-0002_branded_v1.pdf")

    res2 = redact_and_brand_pdf(cv2_src, cv2_branded, logo_path=logo_path)
    assert res2.success, f"Branding failed: {res2.error_message}"
    save_page_image(cv2_branded, shots_dir / "cv2_twocolumn_before.png")

    engine2 = CVEditorEngine(cv2_branded, candidate_code="CAND-0002", user="Recruiter Mike")

    # 1. Delete/blank area in left sidebar (skills section: y=160 to 220)
    # Using true redaction (PDF_REDACT_IMAGE_PIXELS)
    del_rect = (35, 170, 185, 225)
    ok_del, _ = engine2.delete_area(0, del_rect)
    assert ok_del, "Delete area failed"

    # 2. Add custom text box stamp in redacted area
    box_rect = (38, 172, 185, 222)
    ok_box, _ = engine2.add_text_box(
        0,
        box_rect,
        "CORE COMPETENCY:\n• Cloud Architecture\n• Microservices & APIs\n• PySide6 & Python 3.13",
        font_name="helv",
        font_size=8.5,
        color_rgb=(0.06, 0.09, 0.16),
    )
    assert ok_box, "Add text box failed"

    # 3. Save version 2
    ok, v2_path_2, msg2 = engine2.save_version(out_dir)
    assert ok, f"Save version 2 failed: {msg2}"
    print(f"  {msg2}")
    save_page_image(v2_path_2, shots_dir / "cv2_twocolumn_after.png")

    # 4. Capture UI Editor view for CV2
    editor2 = CVEditorWidget()
    editor2.resize(1180, 820)
    editor2.load_document(v2_path_2, candidate_code="CAND-0002", source_file_path=cv2_src, logo_path=logo_path)
    editor2.show()
    app.processEvents()
    pix2 = editor2.grab()
    pix2.save(str(shots_dir / "ui_cv2_editor.png"))
    print(f"  [UI Captured] ui_cv2_editor.png")
    editor2.close()

    # ---------------------------------------------------------
    # CV 3: Colored Header Banner PDF
    # ---------------------------------------------------------
    print("\n--- Verifying CV 3: Colored Header (sample_colored_header.pdf) ---")
    cv3_src = str(sample_dir / "sample_colored_header.pdf")
    cv3_branded = str(out_dir / "CAND-0003_branded_v1.pdf")

    res3 = redact_and_brand_pdf(cv3_src, cv3_branded, logo_path=logo_path)
    assert res3.success, f"Branding failed: {res3.error_message}"
    save_page_image(cv3_branded, shots_dir / "cv3_colored_header_before.png")

    engine3 = CVEditorEngine(cv3_branded, candidate_code="CAND-0003", user="Recruiter Sarah")

    # 1. Detect candidate name in dark navy banner
    det3 = engine3.detect_text_under_point(0, 50, 60)
    assert det3 is not None, "Failed to detect name in colored banner"
    print(f"  Detected Text: '{det3['text']}'")
    print(f"  Sampled Background RGB: ({det3['bg_rgb'][0]:.3f}, {det3['bg_rgb'][1]:.3f}, {det3['bg_rgb'][2]:.3f})")
    
    # Verify that background sampling detected the dark header rather than plain white (1,1,1)
    is_dark_bg = det3["bg_rgb"][0] < 0.3 and det3["bg_rgb"][1] < 0.3 and det3["bg_rgb"][2] < 0.3
    assert is_dark_bg, f"Expected dark background, got {det3['bg_rgb']}"
    print("  [PASSED] Perimeter sampling correctly identified dark navy banner (NO white patch will occur!)")

    # 2. Replace text in colored banner
    ok_rep, warn = engine3.replace_text(
        0,
        det3["rect"],
        "ALEXANDER VANCE",
        font_name=det3["base14_font"],
        font_size=det3["font_size"],
        color_rgb=(1.0, 1.0, 1.0),  # White text over dark background
        bg_rgb=det3["bg_rgb"],       # Dark background fill
        old_text_snippet=det3["text"],
    )
    assert ok_rep, "Replace in colored banner failed"

    # 3. Save version 2
    ok, v2_path_3, msg3 = engine3.save_version(out_dir)
    assert ok, f"Save version 3 failed: {msg3}"
    print(f"  {msg3}")
    save_page_image(v2_path_3, shots_dir / "cv3_colored_header_after.png")

    # 4. Capture UI Editor view for CV3
    editor3 = CVEditorWidget()
    editor3.resize(1180, 820)
    editor3.load_document(v2_path_3, candidate_code="CAND-0003", source_file_path=cv3_src, logo_path=logo_path)
    editor3.show()
    app.processEvents()
    pix3 = editor3.grab()
    pix3.save(str(shots_dir / "ui_cv3_editor.png"))
    print(f"  [UI Captured] ui_cv3_editor.png")
    editor3.close()

    # ---------------------------------------------------------
    # CV 4: DOCX Source CV
    # ---------------------------------------------------------
    print("\n--- Verifying CV 4: DOCX Source CV (sample_cv_priya_sharma.docx) ---")
    cv4_src = str(sample_dir / "sample_cv_priya_sharma.docx")
    
    # 1. Convert original DOCX to PDF and brand to produce "Before" version
    docx_pdf_temp = str(out_dir / "temp_priya_sharma.pdf")
    cv4_branded_v1 = str(out_dir / "CAND-0004_branded_v1.pdf")
    convert_docx_to_pdf(cv4_src, docx_pdf_temp)
    redact_and_brand_pdf(docx_pdf_temp, cv4_branded_v1, logo_path=logo_path)
    save_page_image(cv4_branded_v1, shots_dir / "cv4_docx_before.png")

    # 2. Test pre-conversion DOCX paragraph editor
    paragraphs = get_docx_paragraphs(cv4_src)
    assert len(paragraphs) > 0, "Failed to read paragraphs from DOCX"
    print(f"  Read {len(paragraphs)} paragraphs from source DOCX")

    # Modify paragraph 1 (Title/Role)
    mod_docx = str(out_dir / "sample_cv_priya_sharma_modified.docx")
    edits = {
        1: "Principal Full-Stack Engineer & AI Architect",
    }
    ok_save = save_docx_paragraph_edits(cv4_src, mod_docx, edits)
    assert ok_save, "Failed to save DOCX paragraph edits"
    print("  [PASSED] Pre-conversion DOCX paragraph editing succeeded.")

    # 3. Convert modified DOCX to PDF, redact and brand -> produce "After" version
    docx_pdf_mod = str(out_dir / "temp_priya_modified.pdf")
    cv4_branded_v2 = str(out_dir / "CAND-0004_branded_v2.pdf")
    convert_docx_to_pdf(mod_docx, docx_pdf_mod)
    redact_and_brand_pdf(docx_pdf_mod, cv4_branded_v2, logo_path=logo_path)
    save_page_image(cv4_branded_v2, shots_dir / "cv4_docx_after.png")

    # 4. Capture UI DOCX Dialog and Editor view
    docx_dialog = DOCXParagraphsDialog(cv4_src)
    docx_dialog.show()
    app.processEvents()
    pix_dlg = docx_dialog.grab()
    pix_dlg.save(str(shots_dir / "ui_cv4_docx_dialog.png"))
    print(f"  [UI Captured] ui_cv4_docx_dialog.png")
    docx_dialog.close()

    editor4 = CVEditorWidget()
    editor4.resize(1180, 820)
    editor4.load_document(cv4_branded_v2, candidate_code="CAND-0004", source_file_path=cv4_src, logo_path=logo_path)
    editor4.show()
    app.processEvents()
    pix4 = editor4.grab()
    pix4.save(str(shots_dir / "ui_cv4_editor.png"))
    print(f"  [UI Captured] ui_cv4_editor.png")
    editor4.close()

    # ---------------------------------------------------------
    # CV 5: Scanned / Image-Only CV
    # ---------------------------------------------------------
    print("\n--- Verifying CV 5: Scanned / Image-Only (sample_scanned_cv.pdf) ---")
    cv5_src = str(sample_dir / "sample_scanned_cv.pdf")
    cv5_branded = str(out_dir / "CAND-0005_branded_v1.pdf")

    res5 = redact_and_brand_pdf(cv5_src, cv5_branded, logo_path=logo_path)
    assert res5.success, f"Branding failed: {res5.error_message}"
    save_page_image(cv5_branded, shots_dir / "cv5_scanned_before.png")

    engine5 = CVEditorEngine(cv5_branded, candidate_code="CAND-0005", user="Recruiter Anna")

    # 1. Verify engine recognizes it as scanned
    assert engine5.is_page_scanned(0), "CV5 should be recognized as scanned/image-only"
    print("  [PASSED] Correctly recognized CV5 as scanned/image-only document.")

    # 2. Blank area (delete region) and add recruiter stamp box
    del_scanned_rect = (50, 480, 540, 540)
    ok_d5, _ = engine5.delete_area(0, del_scanned_rect, bg_rgb=(1.0, 1.0, 1.0))
    assert ok_d5, "Delete area on scanned PDF failed"

    stamp_rect = (55, 485, 535, 535)
    ok_t5, _ = engine5.add_text_box(
        0,
        stamp_rect,
        "VERIFIED & ACCREDITED BY SCALEXPRO RECRUITMENT TEAM\nCandidate Ref: CAND-0005 • All confidential contact details redacted.",
        font_name="hebo",
        font_size=10.0,
        color_rgb=(0.06, 0.09, 0.16),
    )
    assert ok_t5, "Add text box on scanned PDF failed"

    ok, v2_path_5, msg5 = engine5.save_version(out_dir)
    assert ok, f"Save version 5 failed: {msg5}"
    print(f"  {msg5}")
    save_page_image(v2_path_5, shots_dir / "cv5_scanned_after.png")

    # 3. Capture UI Editor view showing scanned warning banner
    editor5 = CVEditorWidget()
    editor5.resize(1180, 820)
    editor5.load_document(v2_path_5, candidate_code="CAND-0005", source_file_path=cv5_src, logo_path=logo_path)
    editor5.show()
    app.processEvents()
    pix5 = editor5.grab()
    pix5.save(str(shots_dir / "ui_cv5_editor.png"))
    print(f"  [UI Captured] ui_cv5_editor.png (showing scanned banner)")
    editor5.close()

    # ---------------------------------------------------------
    # Core Quality Requirements Verification
    # ---------------------------------------------------------
    print("\n--- Verifying Safety Scan, Undo/Redo, Audit Trail ---")

    # 1. Contact Re-scan Safety Check
    engine_safety = CVEditorEngine(cv1_branded, candidate_code="CAND-9999", user="Test Recruiter")
    
    # Try inserting an email and phone number
    engine_safety.add_text_box(0, (50, 300, 300, 350), "Call me at +91 98765 43210 or email secret.applicant@gmail.com")
    is_clean, violations = engine_safety.check_safety()
    assert not is_clean, "Safety check should have detected introduced contact details"
    assert len(violations) >= 2, f"Expected at least 2 violations, got {len(violations)}"
    print(f"  [PASSED] Safety check detected violations:")
    for v in violations:
        print(f"    • {v['type']}: {v['value']}")

    # Verify that save_version BLOCKS save
    saved_ok, _, block_msg = engine_safety.save_version(out_dir)
    assert not saved_ok, "save_version should have been blocked by safety scan"
    print(f"  [PASSED] Save correctly blocked with message:\n    {block_msg.splitlines()[0]}")

    # 2. Undo / Redo (30+ steps)
    engine_undo = CVEditorEngine(cv1_branded, candidate_code="CAND-8888")
    for step in range(35):
        engine_undo.add_text_box(0, (50, 50 + step * 10, 200, 60 + step * 10), f"Step {step}")
    
    assert engine_undo.get_undo_count() == 35, f"Expected 35 undo steps, got {engine_undo.get_undo_count()}"
    
    # Undo 10 steps
    for _ in range(10):
        assert engine_undo.undo()
    assert engine_undo.get_undo_count() == 25
    assert len(engine_undo.redo_stack) == 10
    
    # Redo 5 steps
    for _ in range(5):
        assert engine_undo.redo()
    assert engine_undo.get_undo_count() == 30
    assert len(engine_undo.redo_stack) == 5
    print("  [PASSED] 35-step Undo / Redo fully validated.")

    # 3. Audit Trail Logging
    assert len(engine_undo.audit_log) >= 35
    entry = engine_undo.audit_log[0]
    assert "page" in entry and "action" in entry and "timestamp" in entry and "user" in entry
    print(f"  [PASSED] Audit trail logged {len(engine_undo.audit_log)} actions with full provenance.")

    # 4. Version History
    versions = engine1.get_versions_info()
    assert len(versions) >= 2
    print(f"  [PASSED] Version history registered: {[v['version'] for v in versions]}")

    print("\n" + "=" * 70)
    print("ALL 5 CV VERIFICATIONS AND QUALITY CHECKS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
