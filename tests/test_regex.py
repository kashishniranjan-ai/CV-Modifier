"""
Unit tests for regex detection of emails, phone numbers, URLs, addresses,
contact labels (Mobile No.:, E-mail -, Ph:, etc.), contact icons, and headings.
"""

import pytest
from app.core.regex_patterns import (
    EMAIL_REGEX,
    INDIAN_PHONE_REGEX,
    LINKEDIN_REGEX,
    GITHUB_REGEX,
    PORTFOLIO_REGEX,
    CONTACT_HEADING_REGEX,
    is_valid_phone,
    find_all_sensitive_info,
)


class TestEmailRegex:
    def test_standard_emails(self):
        emails = [
            "john.doe@example.com",
            "recruiter_test@domain.co.in",
            "dev+skills@techcorp.org",
            "candidate123@sub.domain.net",
        ]
        for email in emails:
            match = EMAIL_REGEX.search(email)
            assert match is not None, f"Failed to match: {email}"
            assert email in match.group(0)

    def test_email_with_labels_and_icons(self):
        labeled_emails = [
            ("Email: john.doe@example.com", "Email: john.doe@example.com"),
            ("E-mail - name@x.com", "E-mail - name@x.com"),
            ("Mail: user@test.org", "Mail: user@test.org"),
            ("✉ Email: contact@company.in", "✉ Email: contact@company.in"),
            ("✉ contact@company.in", "✉ contact@company.in"),
            ("📧 recruiter@domain.com", "📧 recruiter@domain.com"),
        ]
        for text, expected in labeled_emails:
            match = EMAIL_REGEX.search(text)
            assert match is not None, f"Failed to match: {text}"
            assert match.group(0).strip() == expected

    def test_email_in_sentence(self):
        text = "Please reach out to me at contact@myportfolio.in for any inquiries."
        match = EMAIL_REGEX.search(text)
        assert match is not None
        assert "contact@myportfolio.in" in match.group(0)


class TestPhoneRegex:
    @pytest.mark.parametrize(
        "phone",
        [
            "+91 98765 43210",
            "+91-98765-43210",
            "+919876543210",
            "09876543210",
            "98765 43210",
            "98765-43210",
            "9876543210",
            "080-23456789",
            "+1-415-555-2671",
        ],
    )
    def test_valid_phone_formats(self, phone):
        match = INDIAN_PHONE_REGEX.search(phone)
        assert match is not None, f"Failed to match phone: {phone}"
        assert is_valid_phone(match.group(0))

    def test_phone_with_labels_and_icons(self):
        labeled_phones = [
            ("Mobile No.: 98765-43210", "Mobile No.: 98765-43210"),
            ("Ph: 080-23456789", "Ph: 080-23456789"),
            ("Phone: +91 98765 43210", "Phone: +91 98765 43210"),
            ("Mob: +91 98765 43210", "Mob: +91 98765 43210"),
            ("Contact No: 9876543210", "Contact No: 9876543210"),
            ("Contact Number: +91 98765 43210", "Contact Number: +91 98765 43210"),
            ("Cell: 98765-43210", "Cell: 98765-43210"),
            ("Tel: 080-23456789", "Tel: 080-23456789"),
            ("WhatsApp: +91 98765 43210", "WhatsApp: +91 98765 43210"),
            ("📞 +91 98765 43210", "📞 +91 98765 43210"),
            ("☎ Phone: +91 98765 43210", "☎ Phone: +91 98765 43210"),
        ]
        for text, expected in labeled_phones:
            match = INDIAN_PHONE_REGEX.search(text)
            assert match is not None, f"Failed to match: {text}"
            assert match.group(0).strip() == expected
            assert is_valid_phone(match.group(0))

    def test_reject_false_positives(self):
        false_positives = [
            "2019-2023",
            "2020 - 2024",
            "100%",
            "v1.2.3",
            "Page 1 of 10",
        ]
        for fp in false_positives:
            match = INDIAN_PHONE_REGEX.search(fp)
            if match:
                assert not is_valid_phone(match.group(0)), f"Incorrectly marked as valid phone: {fp}"


class TestURLRegex:
    def test_linkedin_urls(self):
        urls = [
            "https://www.linkedin.com/in/johndoe",
            "http://linkedin.com/in/john-doe-1234",
            "linkedin.com/in/priya_sharma",
            "www.linkedin.com/in/devlead",
            "LinkedIn: https://linkedin.com/in/johndoe",
            "🔗 LinkedIn: https://linkedin.com/in/johndoe",
        ]
        for url in urls:
            match = LINKEDIN_REGEX.search(url)
            assert match is not None, f"Failed to match LinkedIn: {url}"

    def test_github_urls(self):
        urls = [
            "https://github.com/torvalds",
            "http://www.github.com/johndoe-dev",
            "github.com/developer-team",
            "GitHub: https://github.com/torvalds",
        ]
        for url in urls:
            match = GITHUB_REGEX.search(url)
            assert match is not None, f"Failed to match GitHub: {url}"

    def test_portfolio_urls(self):
        urls = [
            "https://johndoe.github.io",
            "https://priyasharma.vercel.app",
            "https://medium.com/@johndoe_ai",
            "behance.net/designer1",
            "dribbble.com/artdirector",
            "leetcode.com/u/coder_master",
            "Portfolio: https://johndoe.dev",
        ]
        for url in urls:
            match = PORTFOLIO_REGEX.search(url)
            assert match is not None, f"Failed to match portfolio: {url}"


class TestContactHeadingRegex:
    def test_headings_matched(self):
        valid_headings = [
            "Contact",
            "Contact Details",
            "Contact Details:",
            "CONTACT DETAILS",
            "Contact Information",
            "Contact Info:",
            "Get in Touch",
            "Contacts:",
        ]
        for h in valid_headings:
            assert CONTACT_HEADING_REGEX.match(h) is not None, f"Failed to match heading: {h}"

    def test_non_contact_headings_rejected(self):
        invalid_headings = [
            "Work Experience",
            "Contract Details",
            "Technical Skills",
            "Contact Person: Jane Doe",
        ]
        for h in invalid_headings:
            assert CONTACT_HEADING_REGEX.match(h) is None, f"Incorrectly matched: {h}"


class TestFindAllSensitiveInfo:
    def test_label_and_contact_removal(self):
        snippet = (
            "John Doe | Lead Engineer\n"
            "Contact Details:\n"
            "E-mail - name@x.com | Mobile No.: 98765-43210\n"
            "Ph: 080-23456789 | WhatsApp: +91 98765 43210\n"
            "LinkedIn: https://linkedin.com/in/johndoe | GitHub: https://github.com/johndoe\n"
            "Residential Address: Flat 301, Palm Grove Layout, Whitefield, Bangalore - 560066\n"
        )
        detected = find_all_sensitive_info(snippet)
        values = [d["value"] for d in detected]
        categories = {d["category"] for d in detected}

        # Check full text with labels was captured
        assert any("E-mail - name@x.com" in v for v in values)
        assert any("Mobile No.: 98765-43210" in v for v in values)
        assert any("Ph: 080-23456789" in v for v in values)
        assert any("LinkedIn:" in v for v in values)
        assert any("Residential Address:" in v for v in values)

        # Check contact heading is detected when contact details are present
        assert "Contact Heading" in categories
        assert any("Contact Details" in v for v in values)
