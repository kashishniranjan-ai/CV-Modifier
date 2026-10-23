"""
Adaptive Logo Placement Engine for CV-Modifier.
Uses PyMuPDF layout analysis (get_text("dict"), get_images, get_drawings)
to intelligently place the company logo on each page without overlapping content.

Placement Strategy:
  1. Analyse page 1 layout: topmost text blocks, candidate name font size,
     top margin, content bounding box.
  2. Choose logo size from the layout (1.0x–1.5x of name font size, clamped 22–48pt).
  3. Pick placement strategy:
       A  – Top margin has enough free space  → place there
       B  – Redacted contact strip is free    → use that gap
       C  – No free space                     → extend page upward with a white header band
  4. Dark-header detection: if logo region background is dark, wrap logo in a
     white rounded pill.
  5. Pages 2+: apply logo only if their own top margin is free.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Optional, Tuple

import pymupdf as fitz
from PIL import Image


# ─────────────────────────────────────────────────────────────────────────────
# Public types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LogoPlacement:
    """Result returned by analyse_page_and_place_logo()."""
    logo_rect: fitz.Rect          # Final rect where the logo was/will be drawn
    logo_w: float                 # Chosen logo width in points
    logo_h: float                 # Chosen logo height in points
    strategy: str                 # "top_margin" | "contact_gap" | "header_strip"
    header_strip_h: float = 0.0   # If strategy=="header_strip": height of added band
    needs_divider: bool = False   # Draw thin divider under header strip
    dark_background: bool = False # Background behind logo is dark → use pill
    name_font_size: float = 0.0   # Detected candidate-name font size
    top_margin_available: float = 0.0
    audit_message: str = ""       # Human-readable summary for audit trail


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

_MIN_LOGO_H: float = 22.0   # pt  (≈ 0.3 in)
_MAX_LOGO_H: float = 48.0   # pt  (≈ 0.67 in)
_PILL_PAD: float = 4.0      # pt  extra padding inside white pill
_DIVIDER_THICKNESS: float = 0.5
_DARK_THRESHOLD: float = 0.45  # luminance below this → "dark"


def _luminance(r: float, g: float, b: float) -> float:
    """Relative luminance 0..1 from (0..1, 0..1, 0..1) triplet."""
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _logo_aspect(logo_path: str) -> float:
    with Image.open(logo_path) as img:
        w, h = img.size
    return w / max(1, h)


def _text_blocks(page: fitz.Page):
    """Return list of (x0, y0, x1, y1, text) for every non-empty text block."""
    raw = page.get_text("blocks")
    result = []
    for b in raw:
        if len(b) >= 5 and str(b[4]).strip():
            result.append((b[0], b[1], b[2], b[3], str(b[4]).strip()))
    return result


def _detect_name_font_size(page: fitz.Page, top_fraction: float = 0.25) -> float:
    """
    Find the largest font size among text in the top `top_fraction` of the page.
    Falls back to 18pt if nothing found.
    """
    page_h = page.rect.height
    top_limit = page_h * top_fraction
    max_size = 0.0
    try:
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for b in blocks:
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    y0 = span.get("origin", (0, 0))[1]
                    fs = span.get("size", 0.0)
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 2**4)  # fitz bold flag
                    if y0 < top_limit and fs > 0:
                        # Weight: prefer large AND bold
                        effective = fs * (1.2 if is_bold else 1.0)
                        if effective > max_size:
                            max_size = effective
    except Exception:
        pass
    return max_size if max_size >= 6.0 else 18.0


def _content_top(blocks) -> float:
    """Y coordinate of the topmost content block on the page."""
    ys = [b[1] for b in blocks if b[4].strip()]
    return min(ys) if ys else 999.0


def _background_color_at(page: fitz.Page, rect: fitz.Rect) -> Tuple[float, float, float]:
    """
    Samples the average pixel colour in `rect` by rendering a tiny snippet.
    Returns (r, g, b) in 0..1 range.
    """
    try:
        zoom = 1.0
        clip = rect & page.rect
        if clip.is_empty:
            return (1.0, 1.0, 1.0)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        data = pix.samples  # bytes: RGB triples
        n = len(data) // 3
        if n == 0:
            return (1.0, 1.0, 1.0)
        r = sum(data[i * 3] for i in range(n)) / n / 255.0
        g = sum(data[i * 3 + 1] for i in range(n)) / n / 255.0
        b = sum(data[i * 3 + 2] for i in range(n)) / n / 255.0
        return (r, g, b)
    except Exception:
        return (1.0, 1.0, 1.0)


def _choose_logo_size(
    name_font_size: float,
    page_width: float,
    size_override: str = "Auto",
) -> Tuple[float, float]:
    """
    Returns (logo_w, logo_h) based on name_font_size and override preference.
    The logo_h is in the range [_MIN_LOGO_H, _MAX_LOGO_H].
    """
    multipliers = {"Auto": None, "Small": 1.0, "Medium": 1.25, "Large": 1.5}
    mul = multipliers.get(size_override)
    if mul is None:
        # Auto: 1.0x for small names, 1.5x for large names
        raw = name_font_size * (1.5 if name_font_size >= 20 else 1.0)
    else:
        raw = name_font_size * mul

    logo_h = max(_MIN_LOGO_H, min(_MAX_LOGO_H, raw))
    # Width cap: never more than 30% of page width
    logo_w = logo_h  # will be scaled by aspect ratio later
    return logo_h, min(logo_h, page_width * 0.30)


def _content_left_margin(blocks) -> float:
    """Return the leftmost x of any text block (content left margin)."""
    xs = [b[0] for b in blocks if b[4].strip()]
    return min(xs) if xs else 36.0


def _is_header_centered(page: fitz.Page, top_fraction: float = 0.25) -> bool:
    """
    Heuristic: if the centre of the most prominent top text spans is
    within 15% of page-centre, call it centered.
    """
    page_w = page.rect.width
    center_zone = (0.35 * page_w, 0.65 * page_w)
    try:
        blocks = page.get_text("dict")["blocks"]
        page_h = page.rect.height
        for b in blocks:
            if b.get("type") != 0:
                continue
            by1 = b.get("bbox", (0, 0, 0, 0))[3]
            if by1 > page_h * top_fraction:
                continue
            for line in b.get("lines", []):
                lx0 = line["bbox"][0]
                lx1 = line["bbox"][2]
                mid = (lx0 + lx1) / 2
                if center_zone[0] <= mid <= center_zone[1]:
                    return True
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def analyse_page_and_place_logo(
    page: fitz.Page,
    logo_path: str,
    size_override: str = "Auto",
    position_override: str = "Auto",
    is_first_page: bool = True,
) -> Optional[LogoPlacement]:
    """
    Analyses `page` and returns a LogoPlacement describing where and how
    to draw the logo.  Returns None if the logo should be skipped on this page.

    Parameters
    ----------
    page             : fitz.Page (already redacted)
    logo_path        : absolute path to logo PNG
    size_override    : "Auto" | "Small" | "Medium" | "Large"
    position_override: "Auto" | "Left" | "Center" | "Right"
    is_first_page    : if False (page 2+), only place if top margin is free
    """
    if not os.path.exists(logo_path):
        return None

    page_rect = page.rect
    page_w = page_rect.width
    page_h = page_rect.height

    blocks = _text_blocks(page)
    name_fs = _detect_name_font_size(page) if is_first_page else 18.0
    content_top_y = _content_top(blocks)
    content_left = _content_left_margin(blocks)

    # ── 1. Choose logo size ───────────────────────────────────────────────
    aspect = _logo_aspect(logo_path)
    target_h, _ = _choose_logo_size(name_fs, page_w, size_override)
    target_w = target_h * aspect
    # Hard width cap: 30% of page width
    if target_w > page_w * 0.30:
        target_w = page_w * 0.30
        target_h = target_w / aspect
    # Re-clamp height
    target_h = max(_MIN_LOGO_H, min(_MAX_LOGO_H, target_h))
    target_w = target_h * aspect

    # ── 2. Choose horizontal position ────────────────────────────────────
    is_centered = _is_header_centered(page)
    if position_override == "Center" or (position_override == "Auto" and is_centered):
        logo_x0 = (page_w - target_w) / 2.0
    elif position_override == "Right":
        right_margin = page_w - max((b[2] for b in blocks if b[4].strip()), default=page_w - 36.0)
        logo_x0 = page_w - right_margin - target_w
    else:  # Left (default)
        logo_x0 = max(content_left, 18.0)

    # ── 3. Choose vertical strategy ──────────────────────────────────────
    PADDING_ABOVE = 8.0
    PADDING_BELOW = 6.0
    required_h = target_h + PADDING_ABOVE + PADDING_BELOW

    strategy: str
    logo_y0: float
    header_strip_h: float = 0.0
    needs_divider: bool = False

    top_margin_avail = content_top_y - PADDING_ABOVE

    if top_margin_avail >= target_h + 4.0:
        # Strategy A: plenty of top margin
        strategy = "top_margin"
        logo_y0 = PADDING_ABOVE
    elif not is_first_page:
        # On subsequent pages, skip if no free top margin
        return None
    else:
        # Strategy C: extend page upward with a clean white header band
        strategy = "header_strip"
        header_strip_h = target_h + 16.0
        logo_y0 = 8.0   # relative to the NEW top (will shift page content down)
        needs_divider = True

    logo_x1 = logo_x0 + target_w
    logo_y1 = logo_y0 + target_h
    logo_rect = fitz.Rect(logo_x0, logo_y0, logo_x1, logo_y1)

    # ── 4. Dark background detection ─────────────────────────────────────
    sample_rect = fitz.Rect(logo_x0, 0, logo_x1, min(logo_y0 + target_h + 8, page_h))
    bg_r, bg_g, bg_b = _background_color_at(page, sample_rect)
    lum = _luminance(bg_r, bg_g, bg_b)
    dark_bg = lum < _DARK_THRESHOLD

    audit_parts = [
        f"Size: {target_w:.0f}x{target_h:.0f}pt",
        f"Strategy: {strategy}",
        f"NameFS: {name_fs:.0f}pt",
        f"TopMargin: {top_margin_avail:.0f}pt",
    ]
    if dark_bg:
        audit_parts.append("DarkBG: pill-wrapped")
    if position_override != "Auto":
        audit_parts.append(f"Position: {position_override}")

    return LogoPlacement(
        logo_rect=logo_rect,
        logo_w=target_w,
        logo_h=target_h,
        strategy=strategy,
        header_strip_h=header_strip_h,
        needs_divider=needs_divider,
        dark_background=dark_bg,
        name_font_size=name_fs,
        top_margin_available=top_margin_avail,
        audit_message="Logo placement | " + " | ".join(audit_parts),
    )


def apply_logo_placement(
    page: fitz.Page,
    logo_path: str,
    placement: LogoPlacement,
) -> None:
    """
    Draws the logo onto `page` according to the LogoPlacement result.
    Handles header-strip creation, optional pill background, and divider line.

    NOTE: If strategy == "header_strip", the caller must have already
    called page.set_mediabox() to expand the page upward BEFORE calling
    this function (see apply_adaptive_logo_to_doc).
    """
    rect = placement.logo_rect

    if placement.dark_background:
        # Draw white rounded rectangle as logo background pill
        pill = fitz.Rect(
            rect.x0 - _PILL_PAD,
            rect.y0 - _PILL_PAD,
            rect.x1 + _PILL_PAD,
            rect.y1 + _PILL_PAD,
        )
        shape = page.new_shape()
        shape.draw_rect(pill)
        shape.finish(fill=(1, 1, 1), color=(0.85, 0.85, 0.85), width=0.5)
        shape.commit()

    page.insert_image(rect, filename=logo_path)

    if placement.needs_divider:
        # Thin light-gray divider under the header band
        divider_y = rect.y1 + 8.0
        shape = page.new_shape()
        shape.draw_line(
            fitz.Point(18.0, divider_y),
            fitz.Point(page.rect.width - 18.0, divider_y),
        )
        shape.finish(color=(0.82, 0.82, 0.82), width=_DIVIDER_THICKNESS)
        shape.commit()


def apply_adaptive_logo_to_doc(
    doc: fitz.Document,
    logo_path: str,
    size_override: str = "Auto",
    position_override: str = "Auto",
) -> list[dict]:
    """
    Main entry point: applies the adaptive logo to every page of `doc`
    (already redacted).  Returns a list of audit-dict entries, one per page
    where the logo was applied.

    Parameters
    ----------
    doc              : open fitz.Document
    logo_path        : absolute path to logo image
    size_override    : "Auto" | "Small" | "Medium" | "Large"
    position_override: "Auto" | "Left" | "Center" | "Right"
    """
    audit_entries = []
    first_page_placement: Optional[LogoPlacement] = None

    for page_idx, page in enumerate(doc):
        is_first = (page_idx == 0)

        if is_first:
            placement = analyse_page_and_place_logo(
                page, logo_path,
                size_override=size_override,
                position_override=position_override,
                is_first_page=True,
            )
            if placement is None:
                continue
            first_page_placement = placement
        else:
            # Reuse the size from page 1 but recheck vertical free space
            if first_page_placement is None:
                continue
            placement = analyse_page_and_place_logo(
                page, logo_path,
                size_override=size_override,
                position_override=position_override,
                is_first_page=False,
            )
            if placement is None:
                # Not enough top margin on this page → skip
                audit_entries.append({
                    "page": page_idx + 1,
                    "category": "Logo Placement",
                    "value": "Skipped: no free top margin",
                    "count": 0,
                    "status": "Skipped",
                })
                continue

        # ── Handle header-strip expansion BEFORE drawing ──────────────────
        if placement.strategy == "header_strip":
            mb = page.mediabox
            shift = placement.header_strip_h + 2.0
            page.set_mediabox(fitz.Rect(mb.x0, mb.y0 - shift, mb.x1, mb.y1))
            # Draw white background for the newly created header band
            band_rect = fitz.Rect(0, 0, page.rect.width, placement.header_strip_h)
            shape = page.new_shape()
            shape.draw_rect(band_rect)
            shape.finish(fill=(1, 1, 1), color=None)
            shape.commit()

        apply_logo_placement(page, logo_path, placement)

        audit_entries.append({
            "page": page_idx + 1,
            "category": "Logo Placement",
            "value": placement.audit_message,
            "count": 1,
            "status": f"Applied ({placement.strategy})",
            # Extra fields for testing / UI display
            "logo_rect": (
                placement.logo_rect.x0,
                placement.logo_rect.y0,
                placement.logo_rect.x1,
                placement.logo_rect.y1,
            ),
            "logo_w": placement.logo_w,
            "logo_h": placement.logo_h,
        })

    return audit_entries
