"""Standalone test for claim validation without full environment setup."""

import re
from typing import Tuple

# Simplified version of the validation logic for testing
def check_completeness_old(text: str) -> Tuple[bool, bool, bool]:
    """OLD version - overly strict."""
    has_verb = bool(
        re.search(
            r"\b(is|are|was|were|reduce[ds]?|improve[ds]?|prevent[ds]?|cause[ds]?|show[ns]?|demonstrate[ds]?|achieve[ds]?|indicate[ds]?|recommend[s]?|may|should|will|can)\b",
            text,
            re.IGNORECASE,
        )
    )

    has_subject = bool(
        re.search(
            r"^[A-Z][a-zA-Z]+\s+(is|are|was|were|reduce|improve|prevent|demonstrate|show)|^\w+\s+(patients?|subjects?|treatment|therapy|drug)",
            text
        )
    ) or len(text.split()) >= 5

    # OLD: Required specific ending punctuation
    is_complete = text.strip().endswith((".", ")", "%")) and len(text.split()) >= 5

    return has_subject, has_verb, is_complete


def check_completeness_new(text: str) -> Tuple[bool, bool, bool]:
    """NEW version - more lenient."""
    has_verb = bool(
        re.search(
            r"\b(is|are|was|were|reduce[ds]?|improve[ds]?|prevent[ds]?|cause[ds]?|show[ns]?|demonstrate[ds]?|achieve[ds]?|indicate[ds]?|recommend[s]?|contraindicate[ds]?|tolerate[ds]?|occur[rs]?|report[s]?ed|observe[ds]?|may|should|will|can|had|have|has)\b",
            text,
            re.IGNORECASE,
        )
    )

    first_portion = text[:max(50, len(text) // 3)]
    has_subject = bool(
        re.search(
            r"\b([A-Z][a-zA-Z]{2,}|patients?|subjects?|treatment|therapy|drug|dose|study|trial|adverse|events?|bleeding|efficacy|safety|indication|contraindication|risk)\b",
            first_portion,
            re.IGNORECASE
        )
    ) or len(text.split()) >= 6

    word_count = len(text.split())
    ends_reasonably = not text.strip().endswith((',', 'and', 'or', 'but', 'with', 'in', 'of', 'to'))
    is_complete = word_count >= 5 and ends_reasonably

    return has_subject, has_verb, is_complete


# Test claims from Xarelto PI
valid_claims = [
    'XARELTO reduced the risk of stroke by 21% compared to warfarin',
    'The most common adverse reaction was bleeding',
    'Well-tolerated in patients 75 years and older',
    'Indicated for treatment of deep vein thrombosis',
    'Peak plasma concentration occurs within 2-4 hours',
    'Contraindicated in patients with active bleeding',
    'The recommended dose is 20 mg once daily',
    'rivaroxaban is a direct Factor Xa inhibitor',
    'XARELTO reduced the risk of stroke and systemic embolism by 21% compared to warfarin (HR 0.79, 95% CI 0.70-0.89, p<0.001)',
]

invalid_claims = [
    'increase in AUCinf and a 56%',
    'Atrial fibrillation affects millions',
    'Patients were randomized 1:1',
    'Table 3: Adverse Events',
]

print("=" * 80)
print("TESTING VALIDATION CHANGES")
print("=" * 80)

print("\n📊 VALID CLAIMS (should pass new validation):")
print("-" * 80)
for claim in valid_claims:
    old_subj, old_verb, old_complete = check_completeness_old(claim)
    new_subj, new_verb, new_complete = check_completeness_new(claim)

    old_valid = old_subj and old_verb and old_complete and len(claim.split()) >= 5
    new_valid = new_subj and new_verb and new_complete and len(claim.split()) >= 4

    status = "✅" if new_valid else "❌"
    improvement = "🔧 FIXED" if (not old_valid and new_valid) else ("✓ OK" if new_valid else "⚠️ STILL FAILS")

    print(f"\n{status} {improvement}")
    print(f"   Claim: {claim[:70]}...")
    print(f"   OLD: subj={old_subj}, verb={old_verb}, complete={old_complete}, valid={old_valid}")
    print(f"   NEW: subj={new_subj}, verb={new_verb}, complete={new_complete}, valid={new_valid}")

print("\n\n📊 INVALID CLAIMS (should still be rejected):")
print("-" * 80)
for claim in invalid_claims:
    old_subj, old_verb, old_complete = check_completeness_old(claim)
    new_subj, new_verb, new_complete = check_completeness_new(claim)

    old_valid = old_subj and old_verb and old_complete and len(claim.split()) >= 5
    new_valid = new_subj and new_verb and new_complete and len(claim.split()) >= 4

    status = "✅" if not new_valid else "❌"
    note = "✓ Correctly rejected" if not new_valid else "⚠️ FALSE POSITIVE"

    print(f"\n{status} {note}")
    print(f"   Claim: {claim[:70]}")
    print(f"   NEW: subj={new_subj}, verb={new_verb}, complete={new_complete}, valid={new_valid}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

valid_fixed = sum(1 for c in valid_claims if
    not all(check_completeness_old(c)) and all(check_completeness_new(c)))
valid_passing = sum(1 for c in valid_claims if all(check_completeness_new(c)[:3]) and len(c.split()) >= 4)
invalid_rejected = sum(1 for c in invalid_claims if
    not (all(check_completeness_new(c)[:3]) and len(c.split()) >= 4))

print(f"✅ Valid claims now passing: {valid_passing}/{len(valid_claims)}")
print(f"🔧 Valid claims fixed by changes: {valid_fixed}/{len(valid_claims)}")
print(f"❌ Invalid claims correctly rejected: {invalid_rejected}/{len(invalid_claims)}")
