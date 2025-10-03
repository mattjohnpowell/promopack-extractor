"""Security scanning and content filtering for sensitive information."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from logging_config import logger


@dataclass
class SecurityScanResult:
    """Result of security scanning operation."""

    has_sensitive_content: bool
    redacted_text: str
    detected_entities: List[Dict[str, Any]]
    compliance_warnings: List[str]
    risk_level: str  # 'low', 'medium', 'high'


class ContentFilter:
    """Content filtering for sensitive information in medical documents."""

    def __init__(self):
        # PII patterns
        self.pii_patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "phone": re.compile(
                r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
            ),
            "ssn": re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),
            "date_of_birth": re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
            "address": re.compile(r"\b\d+\s+[A-Za-z0-9\s,.-]+\b.{10,}", re.IGNORECASE),
            "patient_id": re.compile(
                r"\b(?:patient\s*(?:id|number|#|record)\s*[:\-]?\s*[A-Za-z0-9\-]+|subject\s*(?:id|number|#)\s*[:\-]?\s*[A-Za-z0-9\-]+)\b",
                re.IGNORECASE,
            ),
            "medical_record": re.compile(
                r"\b(?:mrn|medical\s*record|chart)\s*(?:number|#)?\s*[:\-]?\s*[A-Za-z0-9\-]+\b",
                re.IGNORECASE,
            ),
        }

        # Medical compliance patterns
        self.compliance_patterns = {
            "hipaa_violation": re.compile(
                r"\b(?:social\s*security|ssn|medicare|medicaid)\b", re.IGNORECASE
            ),
            "controlled_substance": re.compile(
                r"\b(?:schedule\s*[iv]+|controlled\s*substance|dea\s*number)\b",
                re.IGNORECASE,
            ),
            "experimental_treatment": re.compile(
                r"\b(?:experimental|investigational|off-label)\b", re.IGNORECASE
            ),
            "adverse_event": re.compile(
                r"\b(?:adverse\s*event|serious\s*adverse\s*event|sae)\b", re.IGNORECASE
            ),
        }

        # Risk level thresholds
        self.risk_thresholds = {"low": 0, "medium": 3, "high": 6}

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """Detect personally identifiable information in text."""
        detected_entities = []

        for entity_type, pattern in self.pii_patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                detected_entities.append(
                    {
                        "type": entity_type,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.8,  # Could be improved with ML models
                    }
                )

        return detected_entities

    def detect_compliance_issues(self, text: str) -> List[str]:
        """Detect potential compliance issues in medical documents."""
        warnings = []

        for issue_type, pattern in self.compliance_patterns.items():
            if pattern.search(text):
                if issue_type == "hipaa_violation":
                    warnings.append(
                        "Potential HIPAA violation: sensitive patient identifiers detected"
                    )
                elif issue_type == "controlled_substance":
                    warnings.append(
                        "Controlled substance information detected - verify compliance"
                    )
                elif issue_type == "experimental_treatment":
                    warnings.append(
                        "Experimental treatment claims detected - ensure proper disclaimers"
                    )
                elif issue_type == "adverse_event":
                    warnings.append(
                        "Adverse event reporting detected - verify regulatory compliance"
                    )

        return warnings

    def redact_sensitive_content(
        self, text: str, detected_entities: List[Dict[str, Any]]
    ) -> str:
        """Redact sensitive content from text."""
        redacted_text = text

        # Sort entities by start position (reverse order to avoid offset issues)
        sorted_entities = sorted(
            detected_entities, key=lambda x: x["start"], reverse=True
        )

        for entity in sorted_entities:
            start, end = entity["start"], entity["end"]
            entity_type = entity["type"]

            # Create redaction marker
            redaction_marker = f"[REDACTED-{entity_type.lower()}]"

            # Replace the sensitive content
            redacted_text = (
                redacted_text[:start] + redaction_marker + redacted_text[end:]
            )

        return redacted_text

    def assess_risk_level(
        self, detected_entities: List[Dict[str, Any]], compliance_warnings: List[str]
    ) -> str:
        """Assess overall risk level of the content."""
        risk_score = len(detected_entities) + len(compliance_warnings)

        if risk_score >= self.risk_thresholds["high"]:
            return "high"
        elif risk_score >= self.risk_thresholds["medium"]:
            return "medium"
        else:
            return "low"

    def scan_content(self, text: str, request_id: str) -> SecurityScanResult:
        """Perform comprehensive security scanning on content."""
        logger.info(
            "Starting security content scan",
            extra={"request_id": request_id, "text_length": len(text)},
        )

        # Detect PII
        detected_entities = self.detect_pii(text)

        # Detect compliance issues
        compliance_warnings = self.detect_compliance_issues(text)

        # Redact sensitive content
        redacted_text = self.redact_sensitive_content(text, detected_entities)

        # Assess risk level
        risk_level = self.assess_risk_level(detected_entities, compliance_warnings)

        # Determine if content has sensitive information
        has_sensitive_content = (
            len(detected_entities) > 0 or len(compliance_warnings) > 0
        )

        result = SecurityScanResult(
            has_sensitive_content=has_sensitive_content,
            redacted_text=redacted_text,
            detected_entities=detected_entities,
            compliance_warnings=compliance_warnings,
            risk_level=risk_level,
        )

        logger.info(
            "Security scan completed",
            extra={
                "request_id": request_id,
                "has_sensitive_content": has_sensitive_content,
                "detected_entities_count": len(detected_entities),
                "compliance_warnings_count": len(compliance_warnings),
                "risk_level": risk_level,
            },
        )

        return result


class MedicalComplianceChecker:
    """Compliance checker for medical document content."""

    def __init__(self):
        self.required_disclaimers = [
            "investigational use",
            "not for diagnostic use",
            "consult healthcare provider",
            "individual results may vary",
        ]

        self.prohibited_claims = [
            "cure",
            "guaranteed results",
            "miracle treatment",
            "breakthrough cure",
        ]

    def check_compliance(self, text: str) -> Dict[str, Any]:
        """Check medical content for compliance issues."""
        issues = []
        recommendations = []

        # Check for prohibited claims
        for claim in self.prohibited_claims:
            if claim.lower() in text.lower():
                issues.append(f"Potentially prohibited claim detected: '{claim}'")
                recommendations.append("Consider rephrasing to avoid absolute claims")

        # Check for required disclaimers (only if content seems promotional)
        promotional_indicators = [
            "treatment",
            "therapy",
            "drug",
            "medication",
            "cure",
            "effective",
        ]
        has_promotional_content = any(
            indicator in text.lower() for indicator in promotional_indicators
        )

        if has_promotional_content:
            missing_disclaimers = []
            for disclaimer in self.required_disclaimers:
                if disclaimer.lower() not in text.lower():
                    missing_disclaimers.append(disclaimer)

            if missing_disclaimers:
                issues.append(
                    f"Missing recommended disclaimers: {', '.join(missing_disclaimers)}"
                )
                recommendations.append(
                    "Consider adding appropriate disclaimers for medical content"
                )

        # Check for statistical claims without proper context (only if stats are present)
        stat_pattern = re.compile(r"\b\d+(?:\.\d+)?%\b")
        if stat_pattern.search(text):
            stats_without_context = []
            for match in stat_pattern.finditer(text):
                # Check if there's context within 100 characters
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].lower()

                if not any(
                    word in context
                    for word in [
                        "study",
                        "trial",
                        "patients",
                        "subjects",
                        "data",
                        "results",
                        "clinical",
                    ]
                ):
                    stats_without_context.append(match.group())

            if stats_without_context:
                issues.append("Statistical claims detected without clear study context")
                recommendations.append(
                    "Ensure statistical claims reference specific studies or data sources"
                )

        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "recommendations": recommendations,
            "severity": "high" if len(issues) > 2 else "medium" if issues else "low",
        }


# Global instances
content_filter = ContentFilter()
compliance_checker = MedicalComplianceChecker()


def scan_and_filter_content(
    text: str, request_id: str
) -> Tuple[str, SecurityScanResult, Dict[str, Any]]:
    """Comprehensive security scanning and filtering of content."""
    # Security scanning
    security_result = content_filter.scan_content(text, request_id)

    # Medical compliance checking
    compliance_result = compliance_checker.check_compliance(text)

    # Use redacted text if sensitive content detected
    processed_text = (
        security_result.redacted_text if security_result.has_sensitive_content else text
    )

    return processed_text, security_result, compliance_result
