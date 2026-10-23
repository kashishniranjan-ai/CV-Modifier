"""
Generates 5 realistic candidate CV test documents for verifying CV-Modifier:
1. Simple single-column PDF (John Doe)
2. Two-column modern layout PDF (Alex Rivera)
3. Dark colored header CV (Marcus Vance)
4. DOCX source CV (Priya Sharma)
5. Scanned / image-only CV (Elena Rostova)
"""

from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT_DIR / "sample_data"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


def create_two_column_pdf():
    pdf_path = SAMPLE_DIR / "sample_two_column.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Left sidebar (column 1): 180pt wide
    sidebar_rect = fitz.Rect(0, 0, 180, 842)
    page.draw_rect(sidebar_rect, color=None, fill=(0.95, 0.96, 0.98))

    # Sidebar content
    page.insert_text((24, 60), "ALEX RIVERA", fontname="hebo", fontsize=16, color=(0.06, 0.09, 0.16))
    page.insert_text((24, 82), "DevOps Engineer", fontname="helv", fontsize=11, color=(0.4, 0.45, 0.54))

    page.insert_text((24, 130), "CONTACT", fontname="hebo", fontsize=11, color=(0.95, 0.54, 0.12))
    page.insert_text((24, 150), "alex.rivera@gmail.com", fontname="helv", fontsize=9, color=(0.2, 0.2, 0.2))
    page.insert_text((24, 168), "+91 98765 43210", fontname="helv", fontsize=9, color=(0.2, 0.2, 0.2))
    page.insert_text((24, 186), "linkedin.com/in/alexrivera", fontname="helv", fontsize=9, color=(0.2, 0.2, 0.2))

    page.insert_text((24, 230), "TECH SKILLS", fontname="hebo", fontsize=11, color=(0.95, 0.54, 0.12))
    page.insert_text((24, 250), "• Kubernetes, Docker\n• AWS, Terraform\n• Python, Go, Bash\n• CI/CD, GitHub Actions", fontname="helv", fontsize=9, color=(0.2, 0.2, 0.2))

    # Right main body (column 2): x=200 to 560
    page.insert_text((205, 60), "PROFILE SUMMARY", fontname="hebo", fontsize=13, color=(0.06, 0.09, 0.16))
    page.insert_textbox(
        fitz.Rect(205, 75, 560, 140),
        "Senior infrastructure engineer with 7+ years of experience designing scalable container orchestration pipelines and secure hybrid-cloud environments.",
        fontname="helv",
        fontsize=10,
        color=(0.2, 0.25, 0.33),
    )

    page.insert_text((205, 160), "PROFESSIONAL EXPERIENCE", fontname="hebo", fontsize=13, color=(0.06, 0.09, 0.16))
    page.insert_text((205, 185), "Lead Infrastructure Engineer | CloudScale Tech", fontname="hebo", fontsize=11, color=(0.06, 0.09, 0.16))
    page.insert_text((205, 202), "2021 – Present • Bengaluru, India", fontname="helv", fontsize=9, color=(0.4, 0.45, 0.54))
    page.insert_textbox(
        fitz.Rect(205, 215, 560, 280),
        "Architected multi-region Kubernetes clusters handling 50M+ requests daily. Reduced cloud expenditure by 34% through automated spot instance scheduling.",
        fontname="helv",
        fontsize=9.5,
        color=(0.2, 0.25, 0.33),
    )

    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


def create_colored_header_pdf():
    pdf_path = SAMPLE_DIR / "sample_colored_header.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Top dark navy header banner: 130pt high
    header_rect = fitz.Rect(0, 0, 595, 130)
    page.draw_rect(header_rect, color=None, fill=(0.06, 0.09, 0.16))  # Navy #0F172A

    # Text in navy header (white text)
    page.insert_text((40, 68), "MARCUS VANCE", fontname="hebo", fontsize=24, color=(1.0, 1.0, 1.0))
    page.insert_text((40, 92), "HEAD OF PRODUCT DESIGN & UI/UX", fontname="helv", fontsize=11, color=(0.95, 0.54, 0.12))
    page.insert_text((40, 114), "marcus.vance@designops.co  |  +91 91234 56789  |  Mumbai, India", fontname="helv", fontsize=9.5, color=(0.85, 0.88, 0.92))

    # Page body
    page.insert_text((40, 160), "EXECUTIVE BIO", fontname="hebo", fontsize=13, color=(0.06, 0.09, 0.16))
    page.insert_textbox(
        fitz.Rect(40, 175, 555, 245),
        "Award-winning Design Director specializing in enterprise design systems, high-converting digital products, and user-centric SaaS platforms.",
        fontname="helv",
        fontsize=10,
        color=(0.2, 0.25, 0.33),
    )

    page.insert_text((40, 260), "PORTFOLIO & CASE STUDIES", fontname="hebo", fontsize=13, color=(0.06, 0.09, 0.16))
    page.insert_textbox(
        fitz.Rect(40, 275, 555, 345),
        "Designed comprehensive design token libraries for FinTech platforms across 12 countries. Published author on design tokens and accessibility guidelines.",
        fontname="helv",
        fontsize=10,
        color=(0.2, 0.25, 0.33),
    )

    doc.save(str(pdf_path))
    doc.close()
    print(f"Created: {pdf_path}")


def create_scanned_image_cv():
    pdf_path = SAMPLE_DIR / "sample_scanned_cv.pdf"

    # Create an image simulating a scanned paper document
    img_w, img_h = 1200, 1700
    img = Image.new("RGB", (img_w, img_h), color=(248, 248, 246))  # slightly off-white paper
    draw = ImageDraw.Draw(img)

    # Draw faux scanned resume lines and boxes
    draw.rectangle([60, 60, img_w - 60, img_h - 60], outline=(220, 220, 220), width=2)
    # Header block
    draw.text((100, 100), "ELENA ROSTOVA", fill=(20, 25, 35))
    draw.text((100, 150), "Senior Data Analyst (Scanned Record)", fill=(70, 75, 85))
    draw.text((100, 200), "Confidential Paper Assessment - Delhi Regional Office", fill=(100, 105, 115))

    # Faux horizontal rule
    draw.line([100, 240, img_w - 100, 240], fill=(200, 200, 200), width=2)

    # Some faux scanned document content blocks
    draw.text((100, 270), "ACADEMIC QUALIFICATIONS & CERTIFICATIONS", fill=(30, 35, 45))
    for i in range(12):
        y = 330 + i * 80
        draw.text((100, y), f"Section {i+1}: Paper evaluation score: {85 + i}% - Verified by Testing Authority.", fill=(60, 65, 75))

    # Save to PDF directly from image without text stream (scanned image PDF)
    temp_img_path = SAMPLE_DIR / "scanned_temp.png"
    img.save(str(temp_img_path), "PNG")

    doc = fitz.open()
    rect = fitz.Rect(0, 0, 595, 842)
    page = doc.new_page(width=595, height=842)
    page.insert_image(rect, filename=str(temp_img_path))
    doc.save(str(pdf_path))
    doc.close()

    if temp_img_path.exists():
        temp_img_path.unlink()
    print(f"Created: {pdf_path}")


if __name__ == "__main__":
    create_two_column_pdf()
    create_colored_header_pdf()
    create_scanned_image_cv()
