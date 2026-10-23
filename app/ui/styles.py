"""
ScaleXPro Friendly & Premium Lavender/Purple Design System:
Inspired by the clean modern French SaaS dashboard reference:
- Soft purple vertical gradient sidebar (#6B5FB5 to #7B6CC4) with rounded lavender active pill (#DDD6F7)
- Soft lavender page background (#EEF1FB)
- Pure white cards with 20px radius and soft purple-tinted drop shadow (rgba(107, 95, 181, 0.08))
- Primary Purple #6C5CB8, Dark highlight card #5B4FA3, Pastel icon circles (Lavender, Pink, Blue, Mint)
- ScaleXPro Brand Orange #F28A1E for primary Call-To-Action buttons
- Deep Navy text #1E1B4B, Secondary #6B7280
- Inter typography with generous spacing and friendly tooltips
"""

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

# -----------------------------------------------------------------------------
# Color Tokens
# -----------------------------------------------------------------------------
# Primary Purple & Lavender Palette (from Reference)
COLOR_PRIMARY = "#6C5CB8"
COLOR_PRIMARY_HOVER = "#5B4FA3"
COLOR_PRIMARY_PRESSED = "#4E3F96"
COLOR_PRIMARY_TINT = "#DDD6F7"          # Lavender pill background
COLOR_PRIMARY_BORDER = "#C4B5FD"

COLOR_PURPLE_DARK = "#5B4FA3"           # Dark highlight card (like Premium)
COLOR_PURPLE_DARK_END = "#4A3E8C"
COLOR_PURPLE_DEEP = "#3B2D7C"           # Text inside active lavender pill
COLOR_LAVENDER = "#DDD6F7"
COLOR_LAVENDER_LIGHT = "#ECE8F9"

# ScaleXPro Brand Orange for Main Call-to-Action Buttons
COLOR_CTA = "#F28A1E"
COLOR_CTA_HOVER = "#DB7710"
COLOR_CTA_PRESSED = "#C46A0C"
COLOR_CTA_TINT = "#FFF3E4"
COLOR_CTA_BORDER = "#FED7AA"

# Semantic Status Colors
COLOR_SUCCESS = "#3DBE7A"               # Fresh Green
COLOR_SUCCESS_TINT = "#EDFAF2"
COLOR_SUCCESS_BORDER = "#C6F0D8"

COLOR_DANGER = "#EF4444"                # Warm Coral Red
COLOR_DANGER_TINT = "#FEECEC"
COLOR_DANGER_BORDER = "#FECACA"

COLOR_WARNING = "#F59E0B"               # Amber
COLOR_WARNING_TINT = "#FEF3C7"
COLOR_WARNING_BORDER = "#FDE68A"

COLOR_IN_PROGRESS = "#8B5CF6"           # In-progress purple badge
COLOR_IN_PROGRESS_TINT = "#F3E8FF"
COLOR_IN_PROGRESS_BORDER = "#DDD6FE"

COLOR_INFO = "#3B82F6"
COLOR_INFO_TINT = "#EFF6FF"
COLOR_INFO_BORDER = "#BFDBFE"

# Pastel Icon Circles (from Reference)
PASTEL_LAVENDER = "#E4E0FA"
PASTEL_LAVENDER_ICON = "#6C5CB8"

PASTEL_PINK = "#FBE4F3"
PASTEL_PINK_ICON = "#D946EF"

PASTEL_BLUE = "#DCE8FB"
PASTEL_BLUE_ICON = "#3B82F6"

PASTEL_MINT = "#DDF5E8"
PASTEL_MINT_ICON = "#10B981"

# Typography Colors
COLOR_NAVY = "#1E1B4B"                  # Deep Navy Headings
COLOR_TEXT_PRIMARY = "#1E1B4B"          # Primary text
COLOR_TEXT_SECONDARY = "#6B7280"        # Gray 500 secondary
COLOR_TEXT_MUTED = "#9CA3AF"            # Gray 400 muted

# Background & Border Colors
COLOR_BG_APP = "#EEF1FB"                # Soft lavender background
COLOR_BG_CARD = "#FFFFFF"               # Pure White Cards
COLOR_BG_SIDEBAR_START = "#6B5FB5"      # Gradient top
COLOR_BG_SIDEBAR_END = "#7B6CC4"        # Gradient bottom
COLOR_BG_HOVER = "#F5F3FF"
COLOR_BG_ACTIVE = "#ECE8F9"

COLOR_BORDER = "#E5E7EB"                # Soft neutral border
COLOR_BORDER_LIGHT = "#F3F4F6"
COLOR_BORDER_FOCUS = "#6C5CB8"          # Purple focus ring

# -----------------------------------------------------------------------------
# Typography & Metric Tokens
# -----------------------------------------------------------------------------
FONT_FAMILY = '"Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif'
FONT_SIZE_CAPTION = "11px"
FONT_SIZE_SMALL = "12px"
FONT_SIZE_BODY = "14px"
FONT_SIZE_H3 = "18px"
FONT_SIZE_H2 = "22px"
FONT_SIZE_H1 = "28px"

RADIUS_SM = "8px"
RADIUS_DEFAULT = "12px"
RADIUS_MD = "16px"
RADIUS_LG = "20px"                      # Main 20px card radius from reference
RADIUS_PILL = "9999px"

# -----------------------------------------------------------------------------
# Global Master QSS Stylesheet
# -----------------------------------------------------------------------------
SCALEXPRO_SAAS_STYLE = f"""
/* =========================================================================
   1. Global Window & Base Typography
   ========================================================================= */
QWidget {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: 14px;
    selection-background-color: {COLOR_PRIMARY_TINT};
    selection-color: {COLOR_PURPLE_DEEP};
}}

QLabel {{
    background-color: transparent;
    border: none;
}}

QMainWindow {{
    background-color: {COLOR_BG_APP};
}}

QDialog {{
    background-color: #FFFFFF;
    color: {COLOR_NAVY};
    border-radius: 20px;
}}

/* =========================================================================
   2. Purple Gradient Sidebar (240px wide)
   ========================================================================= */
#SidebarFrame {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_BG_SIDEBAR_START}, stop:1 {COLOR_BG_SIDEBAR_END});
    border: none;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
}}

/* White Rounded Card at top of Sidebar containing ScaleXPro Logo */
#SidebarLogoCard {{
    background-color: #FFFFFF;
    border-radius: 16px;
    padding: 8px 12px;
}}

/* Heading "Dashboard" in Sidebar */
#SidebarSectionHeading {{
    color: rgba(255, 255, 255, 0.7);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding-left: 6px;
    margin-bottom: 4px;
}}

/* Inactive Sidebar Navigation Items */
QPushButton.nav-item {{
    background-color: transparent;
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    font-size: 13.5px;
    font-weight: 500;
    text-align: left;
    padding: 10px 14px;
}}

QPushButton.nav-item:hover {{
    background-color: rgba(255, 255, 255, 0.15);
    color: #FFFFFF;
}}

/* Active Nav Item: Rounded Lavender Pill (#DDD6F7) with Deep Purple Text */
QPushButton.nav-item-active {{
    background-color: {COLOR_LAVENDER};
    color: {COLOR_PURPLE_DEEP};
    border: none;
    border-radius: 12px;
    font-size: 13.5px;
    font-weight: 700;
    text-align: left;
    padding: 10px 14px;
}}

/* Small count badge inside sidebar nav items */
QLabel.nav-badge {{
    background-color: rgba(255, 255, 255, 0.25);
    color: #FFFFFF;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 7px;
}}

QLabel.nav-badge-active {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 7px;
}}

/* Bottom "Offline & secure" Chip in Sidebar */
#SidebarSecureChip {{
    background-color: rgba(255, 255, 255, 0.16);
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 12px;
    padding: 6px 10px;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
}}

/* =========================================================================
   3. Top Navigation Header Bar (White Rounded 20px Card)
   ========================================================================= */
#TopBarFrame {{
    background-color: #FFFFFF;
    border: none;
    border-radius: 20px;
}}

/* Search bar pill in top bar */
#TopSearchBar {{
    background-color: #F4F6FC;
    border: 1px solid #E5E7EB;
    border-radius: 20px;
    padding: 2px 6px 2px 14px;
}}

#TopSearchBar:focus-within {{
    background-color: #FFFFFF;
    border: 1.5px solid {COLOR_PRIMARY};
}}

QLineEdit#SearchBox {{
    background-color: transparent;
    border: none;
    color: {COLOR_NAVY};
    font-size: 13px;
    padding: 6px 4px;
}}

QLineEdit#SearchBox::placeholder {{
    color: {COLOR_TEXT_MUTED};
}}

/* Search Button inside search pill */
#SearchCircleBtn {{
    background-color: {COLOR_PRIMARY};
    border-radius: 14px;
    border: none;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}

#SearchCircleBtn:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}

/* Circular Icon Buttons in Top Bar (Bell, Help, User Avatar) */
QPushButton.topbar-icon-btn {{
    background-color: #F4F6FC;
    border: 1px solid #E5E7EB;
    border-radius: 18px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
}}

QPushButton.topbar-icon-btn:hover {{
    background-color: {COLOR_LAVENDER_LIGHT};
    border-color: {COLOR_PRIMARY_BORDER};
}}

/* User avatar pill in Top Bar */
#UserChipFrame {{
    background-color: #F4F6FC;
    border: 1px solid #E5E7EB;
    border-radius: 20px;
    padding: 3px 12px 3px 5px;
}}

#UserChipFrame:hover {{
    background-color: {COLOR_LAVENDER_LIGHT};
    border-color: {COLOR_PRIMARY_BORDER};
}}

/* =========================================================================
   4. Cards, Panels & Pastel Badges (20px radius)
   ========================================================================= */
QFrame#SaaSCard, QFrame.card-panel {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-radius: 20px;
}}

/* Dark Purple Highlight Card (like "Abonnement Premium" in reference) */
QFrame#DarkHighlightCard {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_PURPLE_DARK}, stop:1 {COLOR_PURPLE_DARK_END});
    border: none;
    border-radius: 20px;
    color: #FFFFFF;
}}

/* Pastel Row Cards (like "Mes formations" in reference) */
QFrame.pastel-row-card {{
    background-color: #F7F8FE;
    border: 1px solid #ECEEF8;
    border-radius: 16px;
    padding: 12px 16px;
}}

QFrame.pastel-row-card:hover {{
    background-color: #F1F3FD;
    border-color: {COLOR_PRIMARY_BORDER};
}}

/* Pastel Circular Icon Containers */
QFrame.icon-circle-lavender {{
    background-color: {PASTEL_LAVENDER};
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}

QFrame.icon-circle-pink {{
    background-color: {PASTEL_PINK};
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}

QFrame.icon-circle-blue {{
    background-color: {PASTEL_BLUE};
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}

QFrame.icon-circle-mint {{
    background-color: {PASTEL_MINT};
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}

/* Pastel Status Badges */
QLabel.badge-success {{
    background-color: {COLOR_SUCCESS_TINT};
    color: {COLOR_SUCCESS};
    border: 1px solid {COLOR_SUCCESS_BORDER};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 700;
}}

QLabel.badge-danger {{
    background-color: {COLOR_DANGER_TINT};
    color: {COLOR_DANGER};
    border: 1px solid {COLOR_DANGER_BORDER};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 700;
}}

QLabel.badge-inprogress {{
    background-color: {COLOR_IN_PROGRESS_TINT};
    color: {COLOR_IN_PROGRESS};
    border: 1px solid {COLOR_IN_PROGRESS_BORDER};
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 700;
}}

/* =========================================================================
   5. Buttons: ScaleXPro Orange Primary CTA & Soft Purple Secondary
   ========================================================================= */
/* Orange Primary Call-To-Action (white text, high visibility) */
QPushButton.btn-primary, QPushButton#PrimaryActionBtn {{
    background-color: {COLOR_CTA};
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 10px 22px;
    font-size: 13.5px;
    font-weight: 700;
}}

QPushButton.btn-primary:hover, QPushButton#PrimaryActionBtn:hover {{
    background-color: {COLOR_CTA_HOVER};
}}

QPushButton.btn-primary:pressed, QPushButton#PrimaryActionBtn:pressed {{
    background-color: {COLOR_CTA_PRESSED};
}}

QPushButton.btn-primary:disabled, QPushButton#PrimaryActionBtn:disabled {{
    background-color: #FDBA74;
    color: rgba(255, 255, 255, 0.7);
}}

/* Purple Primary Button */
QPushButton.btn-purple {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: none;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 13.5px;
    font-weight: 600;
}}

QPushButton.btn-purple:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}

QPushButton.btn-purple:pressed {{
    background-color: {COLOR_PRIMARY_PRESSED};
}}

/* Soft Lavender Secondary Button */
QPushButton.btn-secondary, QPushButton.btn-pill-action {{
    background-color: {COLOR_LAVENDER_LIGHT};
    color: {COLOR_PRIMARY};
    border: 1px solid #DDD6F7;
    border-radius: 12px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton.btn-secondary:hover, QPushButton.btn-pill-action:hover {{
    background-color: {COLOR_LAVENDER};
    color: {COLOR_PURPLE_DEEP};
}}

/* Ghost / Plain Button */
QPushButton.btn-ghost {{
    background-color: transparent;
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton.btn-ghost:hover {{
    background-color: #F3F4F6;
    color: {COLOR_NAVY};
}}

/* Circular Arrow Button (like in reference rows) */
QPushButton.btn-circle-arrow {{
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}

QPushButton.btn-circle-arrow:hover {{
    background-color: {COLOR_LAVENDER};
    border-color: {COLOR_PRIMARY_BORDER};
}}

/* =========================================================================
   6. Form Controls: Inputs, TextEdits, ComboBoxes
   ========================================================================= */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
    background-color: #FFFFFF;
    color: {COLOR_NAVY};
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 9px 13px;
    font-size: 13px;
    selection-background-color: {COLOR_PRIMARY_TINT};
    selection-color: {COLOR_PURPLE_DEEP};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
    border: 1.5px solid {COLOR_PRIMARY};
    background-color: #FFFFFF;
}}

QComboBox {{
    background-color: #FFFFFF;
    color: {COLOR_NAVY};
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 20px;
}}

QComboBox:focus {{
    border: 1.5px solid {COLOR_PRIMARY};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 4px;
    selection-background-color: {COLOR_LAVENDER_LIGHT};
    selection-color: {COLOR_PURPLE_DEEP};
}}

/* =========================================================================
   7. Tables & Scrollbars
   ========================================================================= */
QTableWidget {{
    background-color: #FFFFFF;
    border: none;
    gridline-color: #F1F3F9;
    border-radius: 16px;
    selection-background-color: {COLOR_LAVENDER_LIGHT};
    selection-color: {COLOR_PURPLE_DEEP};
}}

QHeaderView::section {{
    background-color: #F8F9FE;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 1px solid #E5E7EB;
    padding: 10px 14px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px 4px 2px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: #CBD5E1;
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_PRIMARY};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    height: 0px;
}}

/* =========================================================================
   8. Tooltips (Plain English, Friendly)
   ========================================================================= */
QToolTip {{
    background-color: {COLOR_NAVY};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 500;
}}
"""


def apply_scalexpro_palette(app: QApplication):
    """Configures application palette with soft lavender and deep purple tones."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLOR_BG_APP))
    palette.setColor(QPalette.WindowText, QColor(COLOR_NAVY))
    palette.setColor(QPalette.Base, QColor(COLOR_BG_CARD))
    palette.setColor(QPalette.AlternateBase, QColor("#F8F9FE"))
    palette.setColor(QPalette.ToolTipBase, QColor(COLOR_NAVY))
    palette.setColor(QPalette.ToolTipText, QColor("#FFFFFF"))
    palette.setColor(QPalette.Text, QColor(COLOR_NAVY))
    palette.setColor(QPalette.Button, QColor(COLOR_BG_CARD))
    palette.setColor(QPalette.ButtonText, QColor(COLOR_NAVY))
    palette.setColor(QPalette.Highlight, QColor(COLOR_PRIMARY))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.Link, QColor(COLOR_PRIMARY))
    app.setPalette(palette)
