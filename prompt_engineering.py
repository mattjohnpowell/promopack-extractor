"""Advanced prompt engineering and model selection for LLM integration."""

import re
import textwrap
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import langextract as lx

from logging_config import logger


class ModelType(Enum):
    """Available LLM models with their characteristics."""

    GEMINI_FLASH = "gemini-1.5-flash"  # Fast, cost-effective
    GEMINI_PRO = "gemini-1.5-pro"  # More accurate, slower, expensive


class PromptVersion(Enum):
    """Available prompt versions for A/B testing."""

    V1_BASIC = "v1_basic"
    V2_ENHANCED = "v2_enhanced"
    V3_CONTEXT_AWARE = "v3_context_aware"
    V4_REGULATORY = "v4_regulatory"  # Strict pharmaceutical regulatory claim extraction


class PromptTemplate:
    """Template for claim extraction prompts with versioning."""

    def __init__(self, version: PromptVersion, model: ModelType):
        self.version = version
        self.model = model
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[PromptVersion, Dict[str, Any]]:
        """Load prompt templates for different versions."""
        return {
            PromptVersion.V1_BASIC: {
                "prompt": textwrap.dedent(
                    """\
                    Extract key claims from the document. A claim is a significant statement that asserts facts about results, efficacy, or findings.
                    Extract the exact text of the claim without paraphrasing."""
                ),
                "examples": [
                    lx.data.ExampleData(
                        text="The study showed that Drug X reduced symptoms by 50% compared to placebo.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="The study showed that Drug X reduced symptoms by 50% compared to placebo",
                                attributes={"confidence": 0.95},
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="Patients treated with the new therapy had a 30% improvement in quality of life.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Patients treated with the new therapy had a 30% improvement in quality of life",
                                attributes={"confidence": 0.92},
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="The medication was well-tolerated with only mild side effects reported in 5% of participants.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="The medication was well-tolerated with only mild side effects reported in 5% of participants",
                                attributes={"confidence": 0.88},
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="Clinical trials demonstrated a 40% reduction in disease progression over 12 months.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Clinical trials demonstrated a 40% reduction in disease progression over 12 months",
                                attributes={"confidence": 0.94},
                            )
                        ],
                    ),
                ],
            },
            PromptVersion.V2_ENHANCED: {
                "prompt": textwrap.dedent(
                    """\
                    Extract key claims from pharmaceutical or medical documents. A claim is a significant statement that asserts facts about:

                    - Clinical trial results and efficacy data
                    - Safety and side effect information
                    - Dosage and administration outcomes
                    - Comparative effectiveness against other treatments
                    - Patient response rates and demographics

                    Guidelines:
                    - Extract the exact text of the claim without paraphrasing
                    - Focus on quantitative results, statistical significance, and clinical outcomes
                    - Include context about study design when relevant
                    - Prioritize claims with specific numbers, percentages, or statistical measures"""
                ),
                "examples": [
                    lx.data.ExampleData(
                        text="In the randomized controlled trial, patients receiving Drug X showed a 45% reduction in symptom severity compared to placebo (p<0.001).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="patients receiving Drug X showed a 45% reduction in symptom severity compared to placebo (p<0.001)",
                                attributes={
                                    "confidence": 0.98,
                                    "claim_type": "efficacy",
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="The meta-analysis of 12 studies demonstrated that Treatment Y reduced hospitalization rates by 32% (95% CI: 0.58-0.81).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Treatment Y reduced hospitalization rates by 32% (95% CI: 0.58-0.81)",
                                attributes={
                                    "confidence": 0.96,
                                    "claim_type": "outcome",
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="Adverse events were reported in 8.3% of patients in the treatment group versus 12.1% in controls.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Adverse events were reported in 8.3% of patients in the treatment group versus 12.1% in controls",
                                attributes={"confidence": 0.94, "claim_type": "safety"},
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="The pharmacokinetic study showed that Drug Z achieves peak plasma concentration within 2 hours of administration.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Drug Z achieves peak plasma concentration within 2 hours of administration",
                                attributes={
                                    "confidence": 0.91,
                                    "claim_type": "pharmacokinetics",
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="In pediatric patients aged 6-12, the treatment resulted in a 55% improvement in symptom control (p=0.002).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="In pediatric patients aged 6-12, the treatment resulted in a 55% improvement in symptom control (p=0.002)",
                                attributes={
                                    "confidence": 0.97,
                                    "claim_type": "efficacy",
                                    "population": "pediatric",
                                },
                            )
                        ],
                    ),
                ],
            },
            PromptVersion.V3_CONTEXT_AWARE: {
                "prompt": textwrap.dedent(
                    """\
                    Extract key claims from pharmaceutical documents with clinical context. Focus on statements that could be used in promotional materials or regulatory submissions.

                    Claim Categories to Extract:
                    1. EFFICACY: Treatment effectiveness, response rates, clinical outcomes
                    2. SAFETY: Adverse events, tolerability, side effect profiles
                    3. DOSAGE: Optimal dosing, administration schedules, pharmacokinetics
                    4. COMPARATIVE: Superiority/inferiority to other treatments
                    5. POPULATION: Specific patient subgroups, demographics, indications

                    Quality Criteria:
                    - Include statistical significance when available (p-values, confidence intervals)
                    - Note study design (RCT, meta-analysis, observational)
                    - Preserve exact wording for regulatory compliance
                    - Flag claims requiring additional context or caveats"""
                ),
                "examples": [
                    lx.data.ExampleData(
                        text="PRIMARY ENDPOINT: In the Phase 3 RCT (NCT-12345), Drug X achieved a 52% clinical response rate vs 28% for placebo (p<0.0001, N=450).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Drug X achieved a 52% clinical response rate vs 28% for placebo (p<0.0001, N=450)",
                                attributes={
                                    "confidence": 0.99,
                                    "claim_type": "efficacy",
                                    "study_design": "RCT",
                                    "endpoint": "primary",
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="SAFETY PROFILE: Treatment-emergent adverse events led to discontinuation in 4.2% of Drug X patients vs 6.8% placebo (p=0.03).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Treatment-emergent adverse events led to discontinuation in 4.2% of Drug X patients vs 6.8% placebo (p=0.03)",
                                attributes={
                                    "confidence": 0.97,
                                    "claim_type": "safety",
                                    "adverse_event": True,
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="SUBGROUP ANALYSIS: In patients aged 65+, Drug X reduced cardiovascular events by 38% (HR=0.62, 95% CI: 0.45-0.85).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="In patients aged 65+, Drug X reduced cardiovascular events by 38% (HR=0.62, 95% CI: 0.45-0.85)",
                                attributes={
                                    "confidence": 0.95,
                                    "claim_type": "efficacy",
                                    "subgroup": "elderly",
                                    "outcome": "cardiovascular",
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="DOSAGE OPTIMIZATION: Once-daily dosing of 10mg Drug Y provided equivalent efficacy to twice-daily 5mg with improved tolerability.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Once-daily dosing of 10mg Drug Y provided equivalent efficacy to twice-daily 5mg with improved tolerability",
                                attributes={
                                    "confidence": 0.93,
                                    "claim_type": "dosage",
                                    "regimen": "once-daily",
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="COMPARATIVE EFFECTIVENESS: Drug Z was superior to standard therapy in reducing relapse rates (23% vs 35%, p=0.008) in the intent-to-treat population.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Drug Z was superior to standard therapy in reducing relapse rates (23% vs 35%, p=0.008) in the intent-to-treat population",
                                attributes={
                                    "confidence": 0.98,
                                    "claim_type": "comparative",
                                    "analysis": "ITT",
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="LONG-TERM SAFETY: Over 5 years of follow-up, no new safety signals emerged with an adverse event rate of 0.8 per patient-year.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Over 5 years of follow-up, no new safety signals emerged with an adverse event rate of 0.8 per patient-year",
                                attributes={
                                    "confidence": 0.96,
                                    "claim_type": "safety",
                                    "duration": "5 years",
                                },
                            )
                        ],
                    ),
                ],
            },
            PromptVersion.V4_REGULATORY: {
                "prompt": textwrap.dedent(
                    """\
                    Extract ONLY pharmaceutical regulatory claims from this document.

                    CRITICAL: A regulatory claim must pass ALL three tests:
                    
                    1. Is it a COMPLETE statement?
                       - Has subject + verb + object
                       - Can stand alone and be understood without surrounding context
                       - NOT a fragment, NOT a partial sentence
                    
                    2. Does it make an ASSERTION about the DRUG?
                       - States what the drug DOES, IS, or CAUSES
                       - NOT about the disease background
                       - NOT about study methodology
                    
                    3. Would a regulator ask "WHERE'S THE PROOF?"
                       - Requires clinical evidence to substantiate
                       - Is actionable medical information
                       - NOT trivial facts (e.g., "is a tablet")

                    EXTRACT THESE (Valid Claims):
                    ✅ "[DRUG] reduced [outcome] by X% compared to [comparator]"
                    ✅ "Well-tolerated in [population]"
                    ✅ "Indicated for treatment of [condition]"
                    ✅ "Peak plasma concentration occurs within X hours"
                    ✅ "The most common adverse reaction was [event]"
                    ✅ "Contraindicated in patients with [condition]"
                    ✅ "The recommended dose is X mg [frequency]"

                    DO NOT EXTRACT (Invalid - Skip These):
                    ❌ Sentence fragments: "increase in AUCinf and a 56%"
                    ❌ Background info: "Atrial fibrillation affects 2.7 million Americans"
                    ❌ Study methodology: "Patients were randomized 1:1 to treatment groups"
                    ❌ Table headers: "Adverse Event | Drug | Placebo"
                    ❌ Section titles: "Clinical Pharmacology"
                    ❌ Questions: "What is [DRUG]?"
                    ❌ Citations: "(Smith et al. NEJM 2011)"
                    ❌ Boilerplate: "See full prescribing information"

                    Extract the EXACT text of the claim. Do NOT paraphrase. Include statistical data when present."""
                ),
                "examples": [
                    # POSITIVE EXAMPLES - Valid Claims
                    lx.data.ExampleData(
                        text="XARELTO reduced the risk of stroke and systemic embolism by 21% compared to warfarin (HR 0.79, 95% CI 0.70-0.89, p<0.001).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="XARELTO reduced the risk of stroke and systemic embolism by 21% compared to warfarin (HR 0.79, 95% CI 0.70-0.89, p<0.001)",
                                attributes={
                                    "confidence": 0.99,
                                    "claim_type": "EFFICACY",
                                    "is_comparative": True,
                                    "has_statistics": True,
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="The most common adverse reaction was bleeding, occurring in 14.9% of XARELTO-treated patients.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="The most common adverse reaction was bleeding, occurring in 14.9% of XARELTO-treated patients",
                                attributes={
                                    "confidence": 0.96,
                                    "claim_type": "SAFETY",
                                    "is_comparative": False,
                                    "has_statistics": True,
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="XARELTO is indicated for the treatment of deep vein thrombosis (DVT) and pulmonary embolism (PE).",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="XARELTO is indicated for the treatment of deep vein thrombosis (DVT) and pulmonary embolism (PE)",
                                attributes={
                                    "confidence": 0.98,
                                    "claim_type": "INDICATION",
                                    "is_comparative": False,
                                    "has_statistics": False,
                                },
                            )
                        ],
                    ),
                    lx.data.ExampleData(
                        text="Well-tolerated in patients 75 years and older with no dose adjustment required.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="Well-tolerated in patients 75 years and older with no dose adjustment required",
                                attributes={
                                    "confidence": 0.94,
                                    "claim_type": "SAFETY",
                                    "is_comparative": False,
                                    "has_statistics": False,
                                },
                            )
                        ],
                    ),
                    # NEGATIVE EXAMPLES - Should NOT Extract
                    lx.data.ExampleData(
                        text="increase in AUCinf and a 56%",
                        extractions=[],  # No extraction - incomplete fragment
                    ),
                    lx.data.ExampleData(
                        text="Atrial fibrillation is a common cardiac arrhythmia affecting millions worldwide.",
                        extractions=[],  # No extraction - background info about disease
                    ),
                    lx.data.ExampleData(
                        text="In the ROCKET AF trial, 14,264 patients with atrial fibrillation were randomized to receive either XARELTO or warfarin.",
                        extractions=[],  # No extraction - study methodology
                    ),
                    lx.data.ExampleData(
                        text="Table 3: Adverse Events by Treatment Group",
                        extractions=[],  # No extraction - table header
                    ),
                    lx.data.ExampleData(
                        text="What is XARELTO?",
                        extractions=[],  # No extraction - question
                    ),
                    lx.data.ExampleData(
                        text="See full prescribing information for complete safety information.",
                        extractions=[],  # No extraction - boilerplate
                    ),
                    # MIXED EXAMPLES - Extract only valid claims
                    lx.data.ExampleData(
                        text="In the ROCKET AF trial, patients receiving XARELTO showed a 45% reduction in major bleeding events compared to warfarin. Atrial fibrillation affects millions of people.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="claim",
                                extraction_text="patients receiving XARELTO showed a 45% reduction in major bleeding events compared to warfarin",
                                attributes={
                                    "confidence": 0.97,
                                    "claim_type": "SAFETY",
                                    "is_comparative": True,
                                    "has_statistics": True,
                                },
                            )
                        ],  # Extract only the claim about drug performance, not the background info
                    ),
                ],
            },
        }

    def get_template(self) -> Dict[str, Any]:
        """Get the prompt template for this version."""
        return self.templates[self.version]


class ModelSelector:
    """Intelligent model selection based on content complexity."""

    def __init__(self):
        self.complexity_thresholds = {
            "short": 1000,  # Use Flash for short documents
            "medium": 5000,  # Consider complexity for medium documents
            "long": 5000,  # Use Pro for long/complex documents
        }

    def analyze_complexity(self, text: str) -> Dict[str, Any]:
        """Analyze text complexity to determine appropriate model."""
        length = len(text)
        word_count = len(text.split())

        # Simple complexity heuristics
        has_stats = bool(
            re.search(
                r"\b\d+(\.\d+)?%\b|\bp\s*[<>]\s*0\.|\b\d+(\.\d+)?\s*(mg|g|ml|mcg)", text
            )
        )
        has_tables = "table" in text.lower() or "figure" in text.lower()
        has_references = bool(
            re.search(r"\bNCT-\d+|\bPMID\b|\bdoi\b", text, re.IGNORECASE)
        )
        medical_terms = len(
            re.findall(
                r"\b(clinical|trial|study|patient|treatment|therapy|drug|dose|adverse|effect)",
                text,
                re.IGNORECASE,
            )
        )

        complexity_score = (
            (has_stats * 2)
            + (has_tables * 1.5)
            + (has_references * 1)
            + (medical_terms * 0.1)
            + (word_count / 1000 * 0.5)  # Length factor
        )

        return {
            "length": length,
            "word_count": word_count,
            "complexity_score": complexity_score,
            "has_stats": has_stats,
            "has_tables": has_tables,
            "has_references": has_references,
            "medical_terms": medical_terms,
        }

    def select_model(
        self, text: str, force_model: Optional[ModelType] = None
    ) -> ModelType:
        """Select the appropriate model based on content analysis."""
        if force_model:
            return force_model

        analysis = self.analyze_complexity(text)

        # Model selection logic
        if analysis["length"] < self.complexity_thresholds["short"]:
            return ModelType.GEMINI_FLASH  # Fast for simple content
        elif analysis["complexity_score"] > 3.0:
            return ModelType.GEMINI_PRO  # Complex content needs better model
        elif analysis["has_stats"] and analysis["has_references"]:
            return ModelType.GEMINI_PRO  # Statistical/regulatory content
        else:
            return ModelType.GEMINI_FLASH  # Default to faster model


class PromptManager:
    """Manages prompt versioning and A/B testing."""

    def __init__(self):
        self.model_selector = ModelSelector()
        self.templates: Dict[Tuple[PromptVersion, ModelType], PromptTemplate] = {}

        # Initialize templates for all combinations
        for version in PromptVersion:
            for model in ModelType:
                self.templates[(version, model)] = PromptTemplate(version, model)

        # A/B testing configuration
        self.ab_test_enabled = True
        self.ab_test_weights = {
            PromptVersion.V1_BASIC: 0.0,  # Deprecated
            PromptVersion.V2_ENHANCED: 0.0,  # Deprecated
            PromptVersion.V3_CONTEXT_AWARE: 0.1,  # 10% traffic for comparison
            PromptVersion.V4_REGULATORY: 0.9,  # 90% traffic (strict regulatory rules)
        }

    def select_prompt_version_for_ab_test(self) -> PromptVersion:
        """Select prompt version for A/B testing using weighted random selection."""
        import random

        if not self.ab_test_enabled:
            return PromptVersion.V4_REGULATORY

        rand = random.random()
        cumulative = 0.0

        for version, weight in self.ab_test_weights.items():
            cumulative += weight
            if rand <= cumulative:
                return version

        # Fallback to best performing
        return PromptVersion.V4_REGULATORY

    def get_prompt_config(
        self,
        text: str,
        request_id: str,
        prompt_version: Optional[PromptVersion] = None,
        force_model: Optional[ModelType] = None,
    ) -> Tuple[str, List[Any], str]:
        """Get the optimal prompt configuration for the given text."""

        # Select model based on content
        selected_model = self.model_selector.select_model(text, force_model)

        # Select prompt version
        if prompt_version:
            selected_version = prompt_version
        elif self.ab_test_enabled:
            selected_version = self.select_prompt_version_for_ab_test()
        else:
            selected_version = PromptVersion.V4_REGULATORY

        template = self.templates[(selected_version, selected_model)]
        config = template.get_template()

        logger.info(
            "Selected prompt configuration",
            extra={
                "request_id": request_id,
                "model": selected_model.value,
                "prompt_version": selected_version.value,
                "ab_test_enabled": self.ab_test_enabled,
                "text_length": len(text),
                "complexity_analysis": self.model_selector.analyze_complexity(text),
            },
        )

        return config["prompt"], config["examples"], selected_model.value


# Global prompt manager instance
prompt_manager = PromptManager()
