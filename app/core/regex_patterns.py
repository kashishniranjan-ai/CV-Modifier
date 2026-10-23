"""
High-precision regex patterns and extractors for detecting sensitive contact information:
- Emails (with preceding labels like Email, E-mail, Mail and icons)
- Phone numbers (Indian formats, international, STD codes, with labels like Phone, Mobile, Mob, Ph, Tel, WhatsApp and icons)
- LinkedIn / GitHub / Portfolio URLs (with labels and icons)
- Residential address lines, PIN codes, and contact section headings
"""

import re
from typing import List, Dict, Any, Tuple


# ==========================================
# 0. CONTACT ICONS & LABEL DEFINITIONS
# ==========================================
# Common Unicode icons for phone (☎, 📞, 📱), email (✉, 📧), location (📍, 🏠), web (🔗, 🌐, 💻)
CONTACT_ICONS_PATTERN = (
    r"[\u260e\u260f\u2706\u2709\U0001f4de\U0001f4e7\U0001f4cd\U0001f517\U0001f310\U0001f4f1\U0001f3e0\U0001f4bb\ufe0f]"
)

SEPARATORS_PATTERN = r"[:\—\-\–\.\/|]?"

PHONE_LABELS_PATTERN = (
    r"(?:(?:Alternative|Alt\.?|Secondary|Primary|Work|Home)?\s*"
    r"(?:Phone|Mobile|Mob|Contact\s+No|Contact\s+Number|Cell|Tel(?:ephone)?|Ph|Whatsapp|WhatsApp|Landline)"
    r"(?:\s*(?:No\.?|Number|\#))?)"
)

EMAIL_LABELS_PATTERN = (
    r"(?:(?:Personal|Official|Work|Primary|Secondary)?\s*"
    r"(?:Email|E-mail|Mail)"
    r"(?:\s*(?:ID|Address|\#))?)"
)

URL_LABELS_PATTERN = (
    r"(?:(?:LinkedIn|Linkedin|GitHub|Github|Portfolio|Website|Web|Site|Social|Medium|GitLab|Gitlab|Profile)"
    r"(?:\s*(?:URL|Link|Profile|\#))?)"
)

ADDRESS_LABELS_PATTERN = (
    r"(?:(?:Permanent|Current|Residential|Postal|Correspondence)?\s*"
    r"(?:Address|Location|Residence)"
    r"(?:\s*(?:Details|Line|\#))?)"
)

# Combined prefix patterns: supports icon-first, label-first, icon-only, or label-only
PHONE_PREFIX = (
    rf"(?:(?:{CONTACT_ICONS_PATTERN}\s*)+(?:{PHONE_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*)?"
    rf"|(?:{PHONE_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*(?:{CONTACT_ICONS_PATTERN}\s*)?))"
)

EMAIL_PREFIX = (
    rf"(?:(?:{CONTACT_ICONS_PATTERN}\s*)+(?:{EMAIL_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*)?"
    rf"|(?:{EMAIL_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*(?:{CONTACT_ICONS_PATTERN}\s*)?))"
)

URL_PREFIX = (
    rf"(?:(?:{CONTACT_ICONS_PATTERN}\s*)+(?:{URL_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*)?"
    rf"|(?:{URL_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*(?:{CONTACT_ICONS_PATTERN}\s*)?))"
)

ADDRESS_PREFIX = (
    rf"(?:(?:{CONTACT_ICONS_PATTERN}\s*)+(?:{ADDRESS_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*)?"
    rf"|(?:{ADDRESS_LABELS_PATTERN}\s*{SEPARATORS_PATTERN}\s*(?:{CONTACT_ICONS_PATTERN}\s*)?))"
)

# Heading pattern: matches standalone lines like "Contact Details", "Contact Information", "Contact:", "Get in Touch"
CONTACT_HEADING_REGEX = re.compile(
    r"^\s*(?:[\u260e\u260f\u2706\u2709\U0001f4de\U0001f4e7\U0001f4cd\U0001f517\U0001f310\U0001f4f1\U0001f3e0\U0001f4bb\ufe0f]\s*)?"
    r"(?:Contact\s+Details|Contact\s+Information|Contact\s+Info|Contact\s+Numbers?|Contacts?|Get\s+in\s+Touch|Contact)"
    r"\s*[:\—\-\–\.]?\s*$",
    re.IGNORECASE,
)


# ==========================================
# 1. EMAIL PATTERNS (with optional label & icon)
# ==========================================
EMAIL_CORE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

EMAIL_REGEX = re.compile(
    rf"(?:{EMAIL_PREFIX}\s*)?{EMAIL_CORE}\b",
    re.IGNORECASE,
)

MAILTO_REGEX = re.compile(
    r"mailto:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
    re.IGNORECASE,
)


# ==========================================
# 2. PHONE PATTERNS (with optional label & icon)
# ==========================================
# Indian mobile numbers, STD landlines, and international formats:
PHONE_CORE = r"""
(?:
    # Format 1: With explicit +91, 91, or 0 country/trunk prefix
    (?:\+91[\-\s]?|91[\-\s]|0)
    (?:\([0-9]{2,4}\)[\-\s]?)?        # Optional STD bracket like (022)
    [6-9][0-9]{2,4}[\-\s]?[0-9]{4,5}  # 10-digit mobile split
)
|
(?:
    # Format 2: Direct 10-digit Indian mobile starting with 6, 7, 8, 9
    # with optional space or dash like 98765 43210 or 98765-43210
    \b[6-9][0-9]{4}[\-\s][0-9]{5}\b
)
|
(?:
    # Format 3: 10 contiguous digits starting with 6, 7, 8, 9
    \b[6-9][0-9]{9}\b
)
|
(?:
    # Format 4: International format with country code (+1, +44, +971, etc.)
    \+[1-9][0-9]{0,2}[\-\s]?(?:\([0-9]{1,4}\)[\-\s]?)?[0-9]{3,4}[\-\s]?[0-9]{3,4}(?:[\-\s]?[0-9]{1,4})?
)
|
(?:
    # Format 5: Landline with STD code like 011-23456789 or 080-23456789 or (022) 23456789
    \b0[1-9][0-9]{1,3}[\-\s][1-9][0-9]{6,7}\b
)
"""

INDIAN_PHONE_REGEX = re.compile(
    rf"(?:{PHONE_PREFIX}\s*)?(?:{PHONE_CORE})",
    re.VERBOSE | re.IGNORECASE,
)

TEL_URL_REGEX = re.compile(r"tel:\s*([+0-9\-\s]+)", re.IGNORECASE)


# ==========================================
# 3. URL, LINKEDIN, GITHUB & PORTFOLIO PATTERNS
# ==========================================
LINKEDIN_CORE = r"""
(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|pub|profile)\/[a-zA-Z0-9_\-\%]+(?:\/[a-zA-Z0-9_\-\%]*)?
"""

LINKEDIN_REGEX = re.compile(
    rf"(?:{URL_PREFIX}\s*)?(?:{LINKEDIN_CORE})",
    re.VERBOSE | re.IGNORECASE,
)

GITHUB_CORE = r"""
(?:https?:\/\/)?(?:www\.)?github\.com\/[a-zA-Z0-9_\-\%]+(?:\/[a-zA-Z0-9_\-\%]+)?
"""

GITHUB_REGEX = re.compile(
    rf"(?:{URL_PREFIX}\s*)?(?:{GITHUB_CORE})",
    re.VERBOSE | re.IGNORECASE,
)

PORTFOLIO_CORE = r"""
(?:https?:\/\/)?(?:www\.)?
(?:
    gitlab\.com\/[a-zA-Z0-9_\-]+|
    bitbucket\.org\/[a-zA-Z0-9_\-]+|
    behance\.net\/[a-zA-Z0-9_\-]+|
    dribbble\.com\/[a-zA-Z0-9_\-]+|
    medium\.com\/@[a-zA-Z0-9_\-]+|
    kaggle\.com\/[a-zA-Z0-9_\-]+|
    leetcode\.com\/(?:u\/)?[a-zA-Z0-9_\-]+|
    hackerrank\.com\/[a-zA-Z0-9_\-]+|
    [a-zA-Z0-9_\-]+\.github\.io(?:\/[a-zA-Z0-9_\-\%]*)?|
    [a-zA-Z0-9_\-]+\.vercel\.app(?:\/[^\s<>"'\)]*)?|
    [a-zA-Z0-9_\-]+\.netlify\.app(?:\/[^\s<>"'\)]*)?|
    (?<![BMbm]\.)[a-zA-Z0-9\-]{3,}\.(?:dev|tech|me|site|online)(?:\/[^\s<>"'\)]*)?
)
"""

PORTFOLIO_REGEX = re.compile(
    rf"(?:{URL_PREFIX}\s*)?(?:{PORTFOLIO_CORE})",
    re.VERBOSE | re.IGNORECASE,
)

GENERAL_URL_CORE = r"""
\b(?:https?:\/\/|www\.)[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:\/[^\s<>"'\)]*)?
"""

GENERAL_URL_REGEX = re.compile(
    rf"(?:{URL_PREFIX}\s*)?(?:{GENERAL_URL_CORE})",
    re.VERBOSE | re.IGNORECASE,
)


# ==========================================
# 4. ADDRESS & PINCODE PATTERNS
# ==========================================
PINCODE_REGEX = re.compile(
    r"\b(?:Pin(?:\s*code)?|Postal(?:\s*code)?|Zip(?:\s*code)?|\#)?\s*:?\s*([1-9][0-9]{2}\s?[0-9]{3})\b",
    re.IGNORECASE,
)

# Address prefixes and street lines
ADDRESS_HEADER_REGEX = re.compile(
    rf"""
    (?:{ADDRESS_PREFIX}\s*)
    [^\n\r]+
    """,
    re.VERBOSE | re.IGNORECASE,
)

STREET_ADDRESS_REGEX = re.compile(
    r"""
    \b(?:
        (?:Flat|House|Door|Plot|Bldg|Building|Apartment|Apt|Tower|Block|Villa)\s*(?:No\.?|\#)?\s*[A-Za-z0-9\/\-]+[,\s]+
        |
        (?:[0-9]{1,4}[A-Za-z]?[\/,\-]\s*[0-9A-Za-z\s]+,\s*)
    )?
    (?:[A-Za-z0-9\s,\-\/]+)?
    \b(?:
        Street|St\.|Road|Rd\.|Cross|Main|Lane|Avenue|Ave\.|Nagar|Colony|Layout|Sector|Phase|
        Vihar|Puram|Bazaar|Enclave|Society|Marg|Mohalla|Chowk|Gali|Extension|Extn\.
    )\b
    (?:[,\s]+[A-Za-z0-9\s,\-\/]+)?
    """,
    re.VERBOSE | re.IGNORECASE,
)


def is_valid_phone(candidate_text: str) -> bool:
    """
    Sanity check for phone candidates to avoid false positives (like year ranges '2019-2023').
    Robustly handles strings with contact labels (e.g. 'Mobile No.: 98765-43210', 'Ph: 080-23456789').
    """
    text = candidate_text.strip()
    digits = re.sub(r"\D", "", text)

    # Years like 2020-2024 or 2019-2023
    if re.fullmatch(r"(?:19|20)\d{2}[\-\s](?:19|20)?\d{2}", text):
        return False

    # Mobile: exactly 10 digits starting with 6, 7, 8, 9
    if len(digits) == 10:
        return digits[0] in "6789"
    # Mobile with 0 prefix or Landline with STD code (10 or 11 digits starting with 0)
    elif len(digits) in (10, 11) and digits.startswith("0"):
        return True
    # Mobile with 91 prefix
    elif len(digits) == 12 and digits.startswith("91"):
        return digits[2] in "6789"
    elif len(digits) in (7, 8):  # Landline local part
        return True
    elif 10 <= len(digits) <= 15 and ("+" in text or len(digits) >= 10):
        return True

    return False


def find_all_sensitive_info(text: str) -> List[Dict[str, Any]]:
    """
    Scans a given text string and returns a sorted list of all detected sensitive items:
    emails, phone numbers, URLs, addresses, and section headings with category and position.
    Includes preceding label words and unicode contact symbols.
    """
    matches: List[Dict[str, Any]] = []

    # 1. Emails
    for match in EMAIL_REGEX.finditer(text):
        val = match.group(0).rstrip(".,;:()")
        matches.append({
            "category": "Email",
            "value": val,
            "start": match.start(),
            "end": match.end(),
        })

    # 2. LinkedIn
    for match in LINKEDIN_REGEX.finditer(text):
        val = match.group(0).rstrip(".,;:()")
        matches.append({
            "category": "LinkedIn URL",
            "value": val,
            "start": match.start(),
            "end": match.end(),
        })

    # 3. GitHub
    for match in GITHUB_REGEX.finditer(text):
        val = match.group(0).rstrip(".,;:()")
        matches.append({
            "category": "GitHub URL",
            "value": val,
            "start": match.start(),
            "end": match.end(),
        })

    # 4. Portfolios & specific platforms
    for match in PORTFOLIO_REGEX.finditer(text):
        val = match.group(0).rstrip(".,;:()")
        matches.append({
            "category": "Portfolio/Social URL",
            "value": val,
            "start": match.start(),
            "end": match.end(),
        })

    # 5. Other General URLs (excluding already matched)
    for match in GENERAL_URL_REGEX.finditer(text):
        val = match.group(0).rstrip(".,;:()")
        overlaps = False
        for m in matches:
            if m["category"] in ("LinkedIn URL", "GitHub URL", "Portfolio/Social URL", "Email"):
                if not (match.end() <= m["start"] or match.start() >= m["end"]):
                    overlaps = True
                    break
        if not overlaps:
            matches.append({
                "category": "Website URL",
                "value": val,
                "start": match.start(),
                "end": match.end(),
            })

    # 6. Phone Numbers
    for match in INDIAN_PHONE_REGEX.finditer(text):
        val = match.group(0).rstrip(".,;:()")
        if is_valid_phone(val):
            overlaps = False
            for m in matches:
                if not (match.end() <= m["start"] or match.start() >= m["end"]):
                    overlaps = True
                    break
            if not overlaps:
                matches.append({
                    "category": "Phone Number",
                    "value": val,
                    "start": match.start(),
                    "end": match.end(),
                })

    # 7. Address Headers & Lines
    for match in ADDRESS_HEADER_REGEX.finditer(text):
        val = match.group(0).strip()
        overlaps = False
        for m in matches:
            if not (match.end() <= m["start"] or match.start() >= m["end"]):
                overlaps = True
                break
        if not overlaps and len(val) > 8:
            matches.append({
                "category": "Address",
                "value": val,
                "start": match.start(),
                "end": match.end(),
            })

    # 8. Street Address Patterns
    for match in STREET_ADDRESS_REGEX.finditer(text):
        val = match.group(0).strip(" ,;:")
        overlaps = False
        for m in matches:
            if not (match.end() <= m["start"] or match.start() >= m["end"]):
                overlaps = True
                break
        if not overlaps and len(val) >= 12:
            matches.append({
                "category": "Address",
                "value": val,
                "start": match.start(),
                "end": match.end(),
            })

    # 9. Pincodes
    for match in PINCODE_REGEX.finditer(text):
        val = match.group(0).strip()
        overlaps = False
        for m in matches:
            if not (match.end() <= m["start"] or match.start() >= m["end"]):
                overlaps = True
                break
        if not overlaps:
            matches.append({
                "category": "Postal/PIN Code",
                "value": val,
                "start": match.start(),
                "end": match.end(),
            })

    # 10. Contact Headings (e.g. "Contact Details:", "Contact Information")
    # If any contact item was found, also redact the heading so it is not left empty
    has_contact_info = any(
        m["category"] in ("Email", "Phone Number", "LinkedIn URL", "GitHub URL", "Address", "Website URL", "Portfolio/Social URL")
        for m in matches
    )
    if has_contact_info:
        for line in text.splitlines():
            stripped_line = line.strip()
            if stripped_line and CONTACT_HEADING_REGEX.match(stripped_line):
                # Locate line in text
                start_pos = 0
                while True:
                    idx = text.find(stripped_line, start_pos)
                    if idx == -1:
                        break
                    is_line_start = (idx == 0 or text[idx - 1] in "\r\n")
                    end_idx = idx + len(stripped_line)
                    is_line_end = (end_idx >= len(text) or text[end_idx] in "\r\n")
                    if is_line_start and is_line_end:
                        # Ensure no overlap
                        overlaps = any(not (end_idx <= m["start"] or idx >= m["end"]) for m in matches)
                        if not overlaps:
                            matches.append({
                                "category": "Contact Heading",
                                "value": stripped_line,
                                "start": idx,
                                "end": end_idx,
                            })
                        break
                    start_pos = idx + 1

    # Sort matches by start position
    matches.sort(key=lambda x: x["start"])
    return matches
