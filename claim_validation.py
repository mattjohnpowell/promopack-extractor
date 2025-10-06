"""
Pharmaceutical regulatory claim validation module.

This module implements strict validation rules to distinguish regulatory claims
from background information, study methodology, and sentence fragments.

A regulatory claim must pass ALL three tests:
1. Is it a complete statement? (subject + verb + object, standalone)
2. Does it make an assertion about the drug? (not disease/study design)
3. Would a regulator ask "Where's the proof?" (requires clinical evidence)
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import spacy
from spacy.language import Language

from logging_config import logger


class ClaimType(Enum):
    """Types of pharmaceutical regulatory claims."""

    EFFICACY = "EFFICACY"  # Treatment effectiveness, clinical outcomes
    SAFETY = "SAFETY"  # Adverse events, tolerability, side effects
    INDICATION = "INDICATION"  # Approved uses, treatment indications
    CONTRAINDICATION = "CONTRAINDICATION"  # Restrictions, warnings
    DOSING = "DOSING"  # Dosage, administration, regimens
    PHARMACOKINETIC = "PHARMACOKINETIC"  # PK/PD, absorption, metabolism
    COMPARATIVE = "COMPARATIVE"  # Head-to-head comparisons
    MECHANISM = "MECHANISM"  # Mechanism of action, pharmacology
    POPULATION = "POPULATION"  # Specific patient subgroups


class ValidationWarning(Enum):
    """Warning flags for low-quality or borderline extractions."""

    INCOMPLETE_SENTENCE = "INCOMPLETE_SENTENCE"
    MISSING_SUBJECT = "MISSING_SUBJECT"
    MISSING_VERB = "MISSING_VERB"
    LOW_WORD_COUNT = "LOW_WORD_COUNT"
    FRAGMENT = "FRAGMENT"
    QUESTION_FORM = "QUESTION_FORM"
    TABLE_HEADER = "TABLE_HEADER"
    CITATION_ONLY = "CITATION_ONLY"
    BOILERPLATE = "BOILERPLATE"
    BACKGROUND_INFO = "BACKGROUND_INFO"
    STUDY_METHODOLOGY = "STUDY_METHODOLOGY"
    TOO_TRIVIAL = "TOO_TRIVIAL"
    NO_DRUG_MENTION = "NO_DRUG_MENTION"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"


@dataclass
class ClaimValidationResult:
    """Result of claim validation."""

    is_valid: bool
    warnings: List[ValidationWarning]
    reasoning: str
    confidence_adjustment: float  # Penalty to apply to LLM confidence (-0.5 to 0.0)
    has_subject: bool
    has_verb: bool
    is_complete: bool
    is_about_drug: bool
    requires_evidence: bool


class ClaimValidator:
    """Validates whether extracted text is a true regulatory claim."""

    def __init__(self):
        """Initialize validator with NLP models and pattern libraries."""
        # Load spaCy for linguistic analysis
        try:
            self.nlp: Language = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning(
                "spaCy model 'en_core_web_sm' not found. "
                "Run: python -m spacy download en_core_web_sm"
            )
            self.nlp = None

        # Non-claim patterns (SKIP these)
        self.background_patterns = [
            r"\b(affects?|afflicts?)\s+\d+(\.\d+)?\s+(million|billion|thousand)",
            r"is\s+a\s+(common|rare|chronic|serious|life-threatening)\s+(condition|disease|disorder)",
            r"\b(epidemiology|prevalence|incidence)\b",
        ]

        self.methodology_patterns = [
            r"\b(were|was)\s+(randomized|enrolled|assigned|stratified)",
            r"\btrial\s+(enrolled|recruited|included)",
            r"\bstudy\s+design\b",
            r"\b(primary|secondary)\s+endpoint\s+(was|were)",
            r"\bpatients?\s+(received|underwent)\b",
            r"\bsubjects?\s+(were|was)\s+(given|administered)",
        ]

        self.structural_patterns = [
            r"^(Table|Figure|Chart|Graph|Appendix)\s+\d+",
            r"^\d+\.\s+[A-Z]",  # Numbered section headers
            r"^[A-Z\s]+:$",  # ALL CAPS HEADERS:
            r"\|\s+\w+\s+\|",  # Table cell separators
        ]

        self.boilerplate_patterns = [
            r"see\s+(full\s+)?prescribing\s+information",
            r"refer\s+to\s+package\s+insert",
            r"consult\s+the\s+full\s+label",
            r"individual\s+results\s+may\s+vary",
            r"ask\s+your\s+(doctor|physician|healthcare\s+provider)",
        ]

        self.question_patterns = [
            r"^(what|when|where|why|how|who|which)\s+",
            r"\?$",
        ]

        self.citation_patterns = [
            r"^\([A-Za-z]+\s+et\s+al[.,]",  # (Smith et al.
            r"\(PMID[:=]\s*\d+\)",
            r"\(doi[:=]",
            r"^\[\d+[,\s\d]*\]",  # [1,2,3]
            r"\(NCT-?\d+\)",
        ]

        # Claim patterns (EXTRACT these)
        self.claim_verb_patterns = [
            r"\b(reduc(es?|ed|ing|tion)|decreas(es?|ed|ing))",
            r"\b(improv(es?|ed|ing|ement))",
            r"\b(prevent(s?|ed|ing|ion))",
            r"\b(achiev(es?|ed|ing))",
            r"\b(demonstrat(es?|ed|ing))",
            r"\b(show(s?|ed|ing|n))",
            r"\b(indicat(es?|ed)\s+for)",
            r"\b(contraindicated\s+in)",
            r"\b(recommended\s+dose)",
            r"\b(should\s+(not\s+)?be\s+(used|administered))",
            r"\b(may\s+cause)",
            r"\b(well-tolerated)",
            r"\b(superior\s+to|inferior\s+to|non-inferior)",
        ]

        # Comparative markers
        self.comparative_patterns = [
            r"\b(vs\.?|versus|compared\s+(to|with))\b",
            r"\b(superior|inferior|non-inferior|equivalent)\s+to\b",
            r"\b(better|worse)\s+than\b",
            r"\b(more|less)\s+\w+\s+than\b",
        ]

        # Statistical markers (indicates clinical evidence)
        self.statistical_patterns = [
            r"\bp\s*[<>=]\s*0?\.\d+",
            r"\b(95|99)%\s*CI\b",
            r"\bHR\s*=?\s*\d+\.\d+",
            r"\bOR\s*=?\s*\d+\.\d+",
            r"\d+(\.\d+)?%\s+(reduction|increase|improvement|decrease)",
        ]

        # Drug-related action words
        self.drug_action_words = {
            "reduces",
            "decreases",
            "improves",
            "prevents",
            "treats",
            "indicated",
            "contraindicated",
            "administered",
            "dosed",
            "tolerated",
            "effective",
            "safe",
        }

    def validate_claim(
        self, text: str, request_id: Optional[str] = None
    ) -> ClaimValidationResult:
        """
        Validate if text is a true regulatory claim using the 3-question test.

        Args:
            text: The extracted text to validate
            request_id: Optional request ID for logging

        Returns:
            ClaimValidationResult with validation details
        """
        warnings: List[ValidationWarning] = []
        confidence_penalty = 0.0

        # Question 1: Is it a complete statement?
        has_subject, has_verb, is_complete = self._check_completeness(text)

        if not is_complete:
            warnings.append(ValidationWarning.INCOMPLETE_SENTENCE)
            confidence_penalty -= 0.3
        if not has_subject:
            warnings.append(ValidationWarning.MISSING_SUBJECT)
            confidence_penalty -= 0.2
        if not has_verb:
            warnings.append(ValidationWarning.MISSING_VERB)
            confidence_penalty -= 0.3

        # Check word count
        word_count = len(text.split())
        if word_count < 5:
            warnings.append(ValidationWarning.LOW_WORD_COUNT)
            confidence_penalty -= 0.2

        # Check for questions
        if self._is_question(text):
            warnings.append(ValidationWarning.QUESTION_FORM)
            confidence_penalty -= 0.4

        # Check for structural elements (tables, headers)
        if self._is_structural_element(text):
            warnings.append(ValidationWarning.TABLE_HEADER)
            confidence_penalty -= 0.5

        # Check for citations only
        if self._is_citation_only(text):
            warnings.append(ValidationWarning.CITATION_ONLY)
            confidence_penalty -= 0.5

        # Check for boilerplate
        if self._is_boilerplate(text):
            warnings.append(ValidationWarning.BOILERPLATE)
            confidence_penalty -= 0.4

        # Question 2: Does it make an assertion about the drug?
        is_about_drug = self._is_about_drug(text)

        if self._is_background_info(text):
            warnings.append(ValidationWarning.BACKGROUND_INFO)
            confidence_penalty -= 0.4
            is_about_drug = False

        if self._is_study_methodology(text):
            warnings.append(ValidationWarning.STUDY_METHODOLOGY)
            confidence_penalty -= 0.4
            is_about_drug = False

        if not is_about_drug and not self._mentions_drug_action(text):
            warnings.append(ValidationWarning.NO_DRUG_MENTION)
            confidence_penalty -= 0.3

        # Question 3: Would a regulator ask "Where's the proof?"
        requires_evidence = self._requires_evidence(text)

        if not requires_evidence:
            warnings.append(ValidationWarning.TOO_TRIVIAL)
            confidence_penalty -= 0.2

        # Check if fragment (context-dependent)
        if self._is_likely_fragment(text):
            warnings.append(ValidationWarning.FRAGMENT)
            warnings.append(ValidationWarning.CONTEXT_DEPENDENT)
            confidence_penalty -= 0.4

        # Determine validity - must pass all three tests
        is_valid = is_complete and is_about_drug and requires_evidence and word_count >= 5

        # Generate reasoning
        reasoning = self._generate_reasoning(
            is_valid, warnings, has_subject, has_verb, is_about_drug, requires_evidence
        )

        logger.debug(
            "Claim validation result",
            extra={
                "request_id": request_id,
                "text_preview": text[:100],
                "is_valid": is_valid,
                "warnings": [w.value for w in warnings],
                "confidence_penalty": confidence_penalty,
            },
        )

        return ClaimValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            reasoning=reasoning,
            confidence_adjustment=confidence_penalty,
            has_subject=has_subject,
            has_verb=has_verb,
            is_complete=is_complete,
            is_about_drug=is_about_drug,
            requires_evidence=requires_evidence,
        )

    def _check_completeness(self, text: str) -> Tuple[bool, bool, bool]:
        """Check if text is a complete sentence with subject and verb."""
        if not self.nlp:
            # Fallback to basic heuristics
            has_verb = bool(
                re.search(
                    r"\b(is|are|was|were|reduce[ds]?|improve[ds]?|prevent[ds]?|cause[ds]?|show[ns]?|demonstrate[ds]?)\b",
                    text,
                    re.IGNORECASE,
                )
            )
            has_subject = len(text.split()) >= 3
            is_complete = text.strip().endswith((".", ")", "%")) or len(text) > 30
            return has_subject, has_verb, is_complete

        # Use spaCy for accurate parsing
        doc = self.nlp(text)

        # Check for verb
        has_verb = any(token.pos_ in ["VERB", "AUX"] for token in doc)

        # Check for subject (NOUN or PROPN as subject)
        has_subject = any(token.dep_ in ["nsubj", "nsubjpass"] for token in doc)

        # Check completeness
        is_complete = (
            has_verb
            and has_subject
            and len(doc) >= 5
            and not text.strip().endswith((",", ";", "and", "or", "but"))
        )

        return has_subject, has_verb, is_complete

    def _is_question(self, text: str) -> bool:
        """Check if text is a question."""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self.question_patterns)

    def _is_structural_element(self, text: str) -> bool:
        """Check if text is a table header, figure caption, or section title."""
        return any(re.search(pattern, text) for pattern in self.structural_patterns)

    def _is_citation_only(self, text: str) -> bool:
        """Check if text is just a citation reference."""
        # Citation patterns or very short with parentheses
        if any(re.search(pattern, text) for pattern in self.citation_patterns):
            return True
        # Short text that's mostly parentheses
        if len(text) < 30 and text.count("(") + text.count("[") > 0:
            return True
        return False

    def _is_boilerplate(self, text: str) -> bool:
        """Check if text is standard boilerplate language."""
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.boilerplate_patterns
        )

    def _is_background_info(self, text: str) -> bool:
        """Check if text is background about disease, not drug."""
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.background_patterns
        )

    def _is_study_methodology(self, text: str) -> bool:
        """Check if text describes study design, not results."""
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.methodology_patterns
        )

    def _is_about_drug(self, text: str) -> bool:
        """Check if text makes assertions about the drug (not disease/methodology)."""
        # Check for claim verb patterns
        has_claim_verb = any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.claim_verb_patterns
        )

        # Not background or methodology
        not_background = not self._is_background_info(text)
        not_methodology = not self._is_study_methodology(text)

        return has_claim_verb and not_background and not_methodology

    def _mentions_drug_action(self, text: str) -> bool:
        """Check if text mentions drug-related actions."""
        text_lower = text.lower()
        return any(word in text_lower for word in self.drug_action_words)

    def _requires_evidence(self, text: str) -> bool:
        """Check if statement requires clinical evidence to substantiate."""
        # Trivial statements that don't need evidence
        trivial_patterns = [
            r"is\s+a\s+(tablet|capsule|pill|liquid|injection)",
            r"comes\s+in\s+\d+\s*mg",
            r"is\s+(available|supplied)",
            r"manufactured\s+by",
        ]

        if any(re.search(pattern, text, re.IGNORECASE) for pattern in trivial_patterns):
            return False

        # Statements with quantitative claims or clinical outcomes need evidence
        has_statistics = any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.statistical_patterns
        )

        has_outcome = bool(
            re.search(
                r"\b(efficacy|safety|adverse|benefit|risk|response|survival|mortality|reduction|improvement)\b",
                text,
                re.IGNORECASE,
            )
        )

        return has_statistics or has_outcome or self._mentions_drug_action(text)

    def _is_likely_fragment(self, text: str) -> bool:
        """Check if text appears to be a sentence fragment."""
        # Starts with lowercase (except "p<" for p-values)
        if text and text[0].islower() and not text.startswith("p"):
            return True

        # Ends with conjunctions or commas
        if re.search(r"(and|or|but|with|,|;)\s*$", text.strip()):
            return True

        # Contains percentage without subject
        if re.search(r"^\d+(\.\d+)?%\s+", text):
            return True

        # Very short without clear subject
        if len(text.split()) < 6 and not re.search(
            r"\b(is|are|was|were|indicated|contraindicated)\b", text, re.IGNORECASE
        ):
            return True

        return False

    def _generate_reasoning(
        self,
        is_valid: bool,
        warnings: List[ValidationWarning],
        has_subject: bool,
        has_verb: bool,
        is_about_drug: bool,
        requires_evidence: bool,
    ) -> str:
        """Generate human-readable reasoning for validation result."""
        if is_valid:
            reasons = ["Valid regulatory claim"]

            if is_about_drug:
                reasons.append("makes assertion about drug")
            if requires_evidence:
                reasons.append("requires clinical evidence")

            return "; ".join(reasons)
        else:
            # Explain why it failed
            reasons = []

            if not has_subject or not has_verb:
                reasons.append("incomplete sentence structure")
            if ValidationWarning.FRAGMENT in warnings:
                reasons.append("appears to be sentence fragment")
            if ValidationWarning.BACKGROUND_INFO in warnings:
                reasons.append("background information about disease, not drug claim")
            if ValidationWarning.STUDY_METHODOLOGY in warnings:
                reasons.append("describes study methodology, not results")
            if ValidationWarning.TABLE_HEADER in warnings:
                reasons.append("structural element (table/header)")
            if ValidationWarning.BOILERPLATE in warnings:
                reasons.append("standard boilerplate language")
            if ValidationWarning.QUESTION_FORM in warnings:
                reasons.append("question, not assertion")
            if ValidationWarning.TOO_TRIVIAL in warnings:
                reasons.append("trivial statement not requiring evidence")
            if ValidationWarning.LOW_WORD_COUNT in warnings:
                reasons.append("too short to be meaningful claim")

            if not reasons:
                reasons.append("does not meet claim criteria")

            return "Rejected: " + "; ".join(reasons)

    def classify_claim_type(self, text: str) -> Optional[ClaimType]:
        """Classify the type of regulatory claim."""
        text_lower = text.lower()

        # Check patterns for each claim type
        if re.search(r"indicat(ed|ion)\s+for|approved\s+for|treatment\s+of", text_lower):
            return ClaimType.INDICATION

        if re.search(
            r"contraindicated|should\s+not\s+be\s+used|avoid\s+(use\s+)?in", text_lower
        ):
            return ClaimType.CONTRAINDICATION

        if re.search(
            r"(recommended\s+)?dos(e|age|ing)|administr(ation|ed)|once\s+daily|twice\s+daily|\d+\s*mg",
            text_lower,
        ):
            return ClaimType.DOSING

        if re.search(
            r"adverse\s+(event|reaction|effect)|side\s+effect|tolera(ted|bility)|bleeding|safety",
            text_lower,
        ):
            return ClaimType.SAFETY

        if any(re.search(pattern, text_lower) for pattern in self.comparative_patterns):
            return ClaimType.COMPARATIVE

        if re.search(
            r"(auc|cmax|tmax|half-life|absorption|metabolism|excretion|plasma\s+concentration|bioavailability)",
            text_lower,
        ):
            return ClaimType.PHARMACOKINETIC

        if re.search(
            r"(mechanism\s+of\s+action|inhibitor|agonist|antagonist|binds\s+to|blocks)", text_lower
        ):
            return ClaimType.MECHANISM

        # Default to efficacy if it mentions outcomes
        if re.search(
            r"reduc(ed|es|tion)|improv(ed|es|ement)|prevent(ed|s|ion)|efficacy|response\s+rate",
            text_lower,
        ):
            return ClaimType.EFFICACY

        return None

    def is_comparative_claim(self, text: str) -> bool:
        """Check if claim includes comparative language."""
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.comparative_patterns
        )

    def has_statistical_evidence(self, text: str) -> bool:
        """Check if claim contains statistical measures."""
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in self.statistical_patterns
        )


# Global validator instance
claim_validator = ClaimValidator()
