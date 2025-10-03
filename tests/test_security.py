"""Tests for security scanning and content filtering."""

from security import (ContentFilter, MedicalComplianceChecker,
                      scan_and_filter_content)


class TestContentFilter:
    """Test content filtering functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filter = ContentFilter()

    def test_detect_pii_email(self):
        """Test detection of email addresses."""
        text = "Contact us at john.doe@example.com for more information."
        entities = self.filter.detect_pii(text)

        assert len(entities) == 1
        assert entities[0]["type"] == "email"
        assert entities[0]["text"] == "john.doe@example.com"

    def test_detect_pii_phone(self):
        """Test detection of phone numbers."""
        text = "Call (555) 123-4567 for support."
        entities = self.filter.detect_pii(text)

        assert len(entities) == 1
        assert entities[0]["type"] == "phone"

    def test_detect_pii_ssn(self):
        """Test detection of SSN."""
        text = "Patient SSN: 123-45-6789"
        entities = self.filter.detect_pii(text)

        # Should detect SSN, but not "Patient SSN" as patient_id
        ssn_entities = [e for e in entities if e["type"] == "ssn"]
        assert len(ssn_entities) == 1
        assert ssn_entities[0]["text"] == "123-45-6789"

    def test_redact_sensitive_content(self):
        """Test redaction of sensitive content."""
        text = "Contact john.doe@example.com or call (555) 123-4567."
        entities = self.filter.detect_pii(text)

        redacted = self.filter.redact_sensitive_content(text, entities)
        assert "[REDACTED-email]" in redacted
        assert "[REDACTED-phone]" in redacted

    def test_detect_compliance_issues_hipaa(self):
        """Test detection of HIPAA violations."""
        text = "Patient's social security number is 123-45-6789."
        warnings = self.filter.detect_compliance_issues(text)

        assert len(warnings) > 0
        assert "HIPAA" in warnings[0]

    def test_detect_compliance_issues_controlled_substance(self):
        """Test detection of controlled substance mentions."""
        text = "This study involves Schedule II controlled substances."
        warnings = self.filter.detect_compliance_issues(text)

        assert len(warnings) > 0
        assert "verify compliance" in warnings[0]

    def test_scan_content_no_sensitive(self):
        """Test scanning content with no sensitive information."""
        text = "This is a normal medical study about treatment efficacy."
        result = self.filter.scan_content(text, "test-request")

        assert not result.has_sensitive_content
        assert result.risk_level == "low"
        assert result.redacted_text == text

    def test_scan_content_with_sensitive(self):
        """Test scanning content with sensitive information."""
        text = "Patient john.doe@example.com has SSN 123-45-6789."
        result = self.filter.scan_content(text, "test-request")

        assert result.has_sensitive_content
        assert result.risk_level in ["medium", "high"]
        assert "[REDACTED-email]" in result.redacted_text
        assert "[REDACTED-ssn]" in result.redacted_text


class TestMedicalComplianceChecker:
    """Test medical compliance checking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = MedicalComplianceChecker()

    def test_check_compliance_valid(self):
        """Test compliance check for valid content."""
        text = "The study showed improved patient outcomes with standard care."
        result = self.checker.check_compliance(text)

        assert result["compliant"]
        assert result["severity"] == "low"

    def test_check_compliance_prohibited_claims(self):
        """Test detection of prohibited claims."""
        text = "This treatment guarantees a cure for all patients."
        result = self.checker.check_compliance(text)

        assert not result["compliant"]
        assert len(result["issues"]) > 0
        assert "prohibited claim" in result["issues"][0].lower()

    def test_check_compliance_missing_disclaimers(self):
        """Test detection of missing disclaimers."""
        text = "This is an investigational treatment."
        result = self.checker.check_compliance(text)

        # Should detect missing disclaimers
        assert len(result["issues"]) > 0 or "disclaimers" in str(
            result["recommendations"]
        )


class TestSecurityIntegration:
    """Test integrated security scanning."""

    def test_scan_and_filter_content_clean(self):
        """Test scanning clean content."""
        text = "Normal medical research content."
        processed_text, security_result, compliance_result = scan_and_filter_content(
            text, "test-id"
        )

        assert processed_text == text
        assert not security_result.has_sensitive_content
        assert compliance_result["compliant"]

    def test_scan_and_filter_content_sensitive(self):
        """Test scanning content with sensitive information."""
        text = "Contact patient at john.doe@example.com regarding their treatment."
        processed_text, security_result, compliance_result = scan_and_filter_content(
            text, "test-id"
        )

        assert processed_text != text
        assert "[REDACTED-email]" in processed_text
        assert security_result.has_sensitive_content
        assert len(security_result.detected_entities) > 0
