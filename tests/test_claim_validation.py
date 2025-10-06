"""
Comprehensive tests for pharmaceutical regulatory claim validation.

Tests cover all examples from the specification including:
- Valid complete claims (EFFICACY, SAFETY, INDICATION, etc.)
- Invalid fragments and incomplete sentences
- Background information (should be rejected)
- Study methodology (should be rejected)
- Table headers and structural elements (should be rejected)
- Questions, citations, and boilerplate (should be rejected)
"""

import pytest

from claim_validation import claim_validator, ClaimType, ValidationWarning


class TestValidClaims:
    """Test cases for VALID regulatory claims that should be extracted."""

    def test_efficacy_claim_with_statistics(self):
        """Test extraction of efficacy claim with comparative statistics."""
        claim = "XARELTO reduced the risk of stroke by 21% compared to warfarin"
        
        result = claim_validator.validate_claim(claim, "test_001")
        
        assert result.is_valid is True
        assert result.has_subject is True
        assert result.has_verb is True
        assert result.is_complete is True
        assert result.is_about_drug is True
        assert result.requires_evidence is True
        
        # Check classification
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type in [ClaimType.EFFICACY, ClaimType.COMPARATIVE]
        
        # Check comparative and statistical flags
        assert claim_validator.is_comparative_claim(claim) is True
        assert claim_validator.has_statistical_evidence(claim) is True

    def test_safety_claim_tolerability(self):
        """Test safety claim about tolerability."""
        claim = "Well-tolerated in patients 75 years and older"
        
        result = claim_validator.validate_claim(claim, "test_002")
        
        assert result.is_valid is True
        assert result.requires_evidence is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.SAFETY

    def test_indication_claim(self):
        """Test indication/approval claim."""
        claim = "Indicated for the treatment of atrial fibrillation"
        
        result = claim_validator.validate_claim(claim, "test_003")
        
        assert result.is_valid is True
        assert result.is_about_drug is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.INDICATION

    def test_pharmacokinetic_claim(self):
        """Test PK claim."""
        claim = "Peak plasma concentration occurs within 2-4 hours of oral administration"
        
        result = claim_validator.validate_claim(claim, "test_004")
        
        assert result.is_valid is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.PHARMACOKINETIC

    def test_dosing_claim(self):
        """Test dosing recommendation claim."""
        claim = "The recommended dose is 20 mg once daily with the evening meal"
        
        result = claim_validator.validate_claim(claim, "test_005")
        
        assert result.is_valid is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.DOSING

    def test_contraindication_claim(self):
        """Test contraindication claim."""
        claim = "Contraindicated in patients with active pathological bleeding"
        
        result = claim_validator.validate_claim(claim, "test_006")
        
        assert result.is_valid is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.CONTRAINDICATION

    def test_safety_claim_adverse_events(self):
        """Test safety claim with adverse event data."""
        claim = "The most common adverse reaction was bleeding"
        
        result = claim_validator.validate_claim(claim, "test_007")
        
        assert result.is_valid is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.SAFETY


class TestInvalidClaims:
    """Test cases for INVALID claims that should be rejected."""

    def test_fragment_incomplete_sentence(self):
        """Test rejection of sentence fragment."""
        fragment = "increase in AUCinf and a 56%"
        
        result = claim_validator.validate_claim(fragment, "test_100")
        
        assert result.is_valid is False
        assert ValidationWarning.INCOMPLETE_SENTENCE in result.warnings or \
               ValidationWarning.FRAGMENT in result.warnings
        assert result.confidence_adjustment < 0
        assert "fragment" in result.reasoning.lower() or "incomplete" in result.reasoning.lower()

    def test_background_disease_info(self):
        """Test rejection of background information about disease."""
        background = "Atrial fibrillation affects 2.7 million Americans"
        
        result = claim_validator.validate_claim(background, "test_101")
        
        assert result.is_valid is False
        assert ValidationWarning.BACKGROUND_INFO in result.warnings
        assert result.is_about_drug is False
        assert "background" in result.reasoning.lower()

    def test_study_methodology(self):
        """Test rejection of study design description."""
        methodology = "Patients were randomized 1:1 to receive either XARELTO or placebo"
        
        result = claim_validator.validate_claim(methodology, "test_102")
        
        assert result.is_valid is False
        assert ValidationWarning.STUDY_METHODOLOGY in result.warnings
        assert result.is_about_drug is False
        assert "methodology" in result.reasoning.lower()

    def test_table_header(self):
        """Test rejection of table header."""
        header = "Table 3: Adverse Events by Treatment Group"
        
        result = claim_validator.validate_claim(header, "test_103")
        
        assert result.is_valid is False
        assert ValidationWarning.TABLE_HEADER in result.warnings

    def test_column_headers(self):
        """Test rejection of table column structure."""
        columns = "Adverse Event | XARELTO (n=67) | Warfarin (n=65)"
        
        result = claim_validator.validate_claim(columns, "test_104")
        
        assert result.is_valid is False
        assert ValidationWarning.TABLE_HEADER in result.warnings

    def test_boilerplate_text(self):
        """Test rejection of boilerplate language."""
        boilerplate = "See full prescribing information for complete details"
        
        result = claim_validator.validate_claim(boilerplate, "test_105")
        
        assert result.is_valid is False
        assert ValidationWarning.BOILERPLATE in result.warnings

    def test_question_form(self):
        """Test rejection of questions."""
        question = "What is XARELTO?"
        
        result = claim_validator.validate_claim(question, "test_106")
        
        assert result.is_valid is False
        assert ValidationWarning.QUESTION_FORM in result.warnings

    def test_citation_reference(self):
        """Test rejection of citation."""
        citation = "(Smith et al., NEJM 2011)"
        
        result = claim_validator.validate_claim(citation, "test_107")
        
        assert result.is_valid is False
        assert ValidationWarning.CITATION_ONLY in result.warnings

    def test_fragment_starting_lowercase(self):
        """Test rejection of fragment starting with lowercase."""
        fragment = "subjects maintained with chronic and stable hemodialysis; reported"
        
        result = claim_validator.validate_claim(fragment, "test_108")
        
        assert result.is_valid is False
        assert ValidationWarning.FRAGMENT in result.warnings or \
               ValidationWarning.INCOMPLETE_SENTENCE in result.warnings


class TestEdgeCases:
    """Test borderline and edge cases."""

    def test_mechanism_of_action_valid(self):
        """Test that mechanism of action is considered a valid claim."""
        claim = "Rivaroxaban is a direct Factor Xa inhibitor"
        
        result = claim_validator.validate_claim(claim, "test_200")
        
        # This should be VALID - it's an assertion about the drug requiring evidence
        assert result.is_valid is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.MECHANISM

    def test_safety_claim_descriptive(self):
        """Test safety claim that sounds descriptive but is actionable."""
        claim = "The most common adverse reaction was bleeding"
        
        result = claim_validator.validate_claim(claim, "test_201")
        
        # Should be VALID - it's a safety claim requiring data
        assert result.is_valid is True
        assert result.requires_evidence is True

    def test_drug_interaction_claim(self):
        """Test drug interaction safety claim."""
        claim = "Bleeding risk increases with concomitant use of antiplatelet agents"
        
        result = claim_validator.validate_claim(claim, "test_202")
        
        # Should be VALID - safety claim about interactions
        assert result.is_valid is True
        
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type == ClaimType.SAFETY

    def test_short_but_valid_claim(self):
        """Test that short but complete claims pass."""
        claim = "XARELTO is contraindicated in active bleeding"
        
        result = claim_validator.validate_claim(claim, "test_203")
        
        assert result.is_valid is True
        assert len(claim.split()) >= 5  # Meets minimum word count

    def test_trivial_claim_rejected(self):
        """Test that trivial statements are rejected."""
        trivial = "XARELTO is a tablet"
        
        result = claim_validator.validate_claim(trivial, "test_204")
        
        # Should be invalid - too trivial, doesn't need evidence
        assert result.is_valid is False
        assert result.requires_evidence is False


class TestComparativeAndStatistical:
    """Test detection of comparative language and statistical evidence."""

    def test_comparative_vs_detection(self):
        """Test detection of 'vs' comparative language."""
        claim = "XARELTO 20mg once daily vs warfarin showed superior outcomes"
        
        assert claim_validator.is_comparative_claim(claim) is True

    def test_comparative_compared_to(self):
        """Test detection of 'compared to' language."""
        claim = "Drug X reduced events by 30% compared to placebo"
        
        assert claim_validator.is_comparative_claim(claim) is True

    def test_statistical_percentage(self):
        """Test detection of percentage statistics."""
        claim = "Treatment showed 45% reduction in symptom severity"
        
        assert claim_validator.has_statistical_evidence(claim) is True

    def test_statistical_p_value(self):
        """Test detection of p-values."""
        claim = "The difference was significant (p<0.001)"
        
        assert claim_validator.has_statistical_evidence(claim) is True

    def test_statistical_confidence_interval(self):
        """Test detection of confidence intervals."""
        claim = "Risk reduction of 21% (95% CI: 0.70-0.89)"
        
        assert claim_validator.has_statistical_evidence(claim) is True

    def test_statistical_hazard_ratio(self):
        """Test detection of hazard ratios."""
        claim = "Mortality was reduced (HR=0.75, p=0.02)"
        
        assert claim_validator.has_statistical_evidence(claim) is True


class TestConfidenceAdjustment:
    """Test confidence score adjustments based on validation."""

    def test_penalty_for_warnings(self):
        """Test that warnings reduce confidence."""
        fragment = "and showed improvement in patients"
        
        result = claim_validator.validate_claim(fragment, "test_300")
        
        # Should have negative confidence adjustment
        assert result.confidence_adjustment < 0
        assert len(result.warnings) > 0

    def test_valid_claim_minimal_penalty(self):
        """Test that valid claims have minimal/no penalty."""
        claim = "XARELTO reduced stroke risk by 21% compared to warfarin"
        
        result = claim_validator.validate_claim(claim, "test_301")
        
        # Valid claims should have minimal penalty
        assert result.confidence_adjustment >= -0.1


class TestReasoningGeneration:
    """Test human-readable reasoning generation."""

    def test_valid_claim_reasoning(self):
        """Test reasoning for valid claim."""
        claim = "Drug X improved survival rates by 35%"
        
        result = claim_validator.validate_claim(claim, "test_400")
        
        assert result.reasoning is not None
        assert "valid" in result.reasoning.lower() or "claim" in result.reasoning.lower()

    def test_invalid_fragment_reasoning(self):
        """Test reasoning explains why fragment is invalid."""
        fragment = "increase in 56%"
        
        result = claim_validator.validate_claim(fragment, "test_401")
        
        assert result.reasoning is not None
        assert "reject" in result.reasoning.lower() or "invalid" in result.reasoning.lower()
        assert any(word in result.reasoning.lower() for word in ["fragment", "incomplete", "short"])


class TestIntegration:
    """Integration tests combining multiple validation aspects."""

    def test_complex_valid_claim(self):
        """Test complex claim with multiple positive indicators."""
        claim = (
            "In the ROCKET AF trial, XARELTO reduced the risk of stroke and systemic "
            "embolism by 21% compared to warfarin (HR 0.79, 95% CI 0.70-0.89, p<0.001)"
        )
        
        result = claim_validator.validate_claim(claim, "test_500")
        
        # Should be valid
        assert result.is_valid is True
        
        # Should be classified as efficacy or comparative
        claim_type = claim_validator.classify_claim_type(claim)
        assert claim_type in [ClaimType.EFFICACY, ClaimType.COMPARATIVE]
        
        # Should have comparative and statistical markers
        assert claim_validator.is_comparative_claim(claim) is True
        assert claim_validator.has_statistical_evidence(claim) is True

    def test_mixed_paragraph_extraction(self):
        """Test paragraph with both valid and invalid content."""
        # Valid claim
        claim1 = "XARELTO showed a 45% reduction in major bleeding events compared to warfarin"
        # Background info - invalid
        claim2 = "Atrial fibrillation affects millions of people"
        # Study methodology - invalid
        claim3 = "Patients were randomized to receive either drug or placebo"
        
        result1 = claim_validator.validate_claim(claim1, "test_501")
        result2 = claim_validator.validate_claim(claim2, "test_502")
        result3 = claim_validator.validate_claim(claim3, "test_503")
        
        # Only the first should be valid
        assert result1.is_valid is True
        assert result2.is_valid is False
        assert result3.is_valid is False
        
        # Second should be background
        assert ValidationWarning.BACKGROUND_INFO in result2.warnings
        
        # Third should be methodology
        assert ValidationWarning.STUDY_METHODOLOGY in result3.warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
