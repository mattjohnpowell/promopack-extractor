# Pharmaceutical Claim Extraction - Quick Reference Guide

## The 3-Question Test

For content to be extracted as a claim, it must pass ALL three tests:

| Question | What It Means | Example ✅ | Example ❌ |
|----------|---------------|-----------|-----------|
| **1. Complete statement?** | Has subject + verb + object, stands alone | "XARELTO reduces stroke risk by 21%" | "increase in AUCinf and a 56%" |
| **2. Assertion about drug?** | States what drug does/is, not background | "Well-tolerated in elderly patients" | "Atrial fibrillation affects millions" |
| **3. Needs proof?** | Requires clinical evidence | "Contraindicated in active bleeding" | "XARELTO is a tablet" |

## Valid Claim Types

### ✅ EFFICACY
**What:** Treatment effectiveness, clinical outcomes  
**Examples:**
- "XARELTO reduced stroke risk by 21% vs warfarin"
- "Patients achieved 85% symptom control"
- "Drug X demonstrated 40% reduction in disease progression"

### ✅ SAFETY
**What:** Adverse events, tolerability, side effects  
**Examples:**
- "Well-tolerated in patients ≥75 years old"
- "The most common adverse reaction was bleeding"
- "Serious adverse events occurred in 3.2% of patients"

### ✅ INDICATION
**What:** Approved uses, treatment indications  
**Examples:**
- "Indicated for treatment of DVT and pulmonary embolism"
- "Approved for prophylaxis of VTE following hip replacement"
- "XARELTO is indicated to reduce risk of stroke in AF patients"

### ✅ CONTRAINDICATION
**What:** Restrictions, warnings about use  
**Examples:**
- "Contraindicated in patients with active pathological bleeding"
- "Should not be used in patients with severe hepatic impairment"
- "Avoid use in pregnancy"

### ✅ DOSING
**What:** Dosage recommendations, administration  
**Examples:**
- "The recommended dose is 20 mg once daily"
- "Administer 15 mg twice daily for 21 days"
- "No dose adjustment required in elderly patients"

### ✅ PHARMACOKINETIC
**What:** PK/PD, absorption, metabolism  
**Examples:**
- "Peak plasma concentration occurs within 2-4 hours"
- "Terminal half-life is 5-9 hours in young adults"
- "Bioavailability is 80-100% for the 10 mg tablet"

### ✅ COMPARATIVE
**What:** Head-to-head comparisons with other treatments  
**Examples:**
- "XARELTO was superior to enoxaparin in preventing VTE"
- "Non-inferior to warfarin for stroke prevention"
- "Lower bleeding rates compared to standard therapy (p=0.008)"

### ✅ MECHANISM
**What:** How the drug works, pharmacology  
**Examples:**
- "Rivaroxaban is a direct Factor Xa inhibitor"
- "Selectively blocks thrombin generation"
- "Inhibits both free and bound Factor Xa"

## Invalid Content (Rejected)

### ❌ FRAGMENTS
**What:** Incomplete sentences, missing subject/verb  
**Examples:**
- "increase in AUCinf and a 56%"
- "and showed improvement in patients"
- "reduction observed in the treatment arm"

**Why Rejected:** Cannot stand alone, torn from context

### ❌ BACKGROUND INFORMATION
**What:** Facts about the disease, not the drug  
**Examples:**
- "Atrial fibrillation affects 2.7 million Americans"
- "DVT is a serious medical condition"
- "Stroke is a leading cause of disability"

**Why Rejected:** Not about drug performance

### ❌ STUDY METHODOLOGY
**What:** How the study was conducted  
**Examples:**
- "Patients were randomized 1:1 to treatment groups"
- "The trial enrolled 14,264 participants"
- "Primary endpoint was assessed at 12 months"

**Why Rejected:** Study design, not results

### ❌ TABLE HEADERS / STRUCTURAL
**What:** Document structure elements  
**Examples:**
- "Table 3: Adverse Events by Treatment Group"
- "Figure 2: Kaplan-Meier Curves"
- "CLINICAL PHARMACOLOGY"

**Why Rejected:** Not content, just organization

### ❌ QUESTIONS
**What:** Interrogative statements  
**Examples:**
- "What is XARELTO?"
- "How should I store XARELTO?"
- "When should treatment be discontinued?"

**Why Rejected:** Questions don't make assertions

### ❌ CITATIONS / REFERENCES
**What:** Source citations  
**Examples:**
- "(Smith et al., NEJM 2011)"
- "[1,2,3]"
- "(PMID: 12345678)"

**Why Rejected:** These are proof, not claims

### ❌ BOILERPLATE
**What:** Standard regulatory language  
**Examples:**
- "See full prescribing information for complete details"
- "Individual results may vary"
- "Ask your doctor or pharmacist"

**Why Rejected:** Generic legal text

### ❌ TRIVIAL STATEMENTS
**What:** Obvious facts not requiring evidence  
**Examples:**
- "XARELTO is a tablet"
- "Available in 10 mg, 15 mg, and 20 mg"
- "Manufactured by Bayer"

**Why Rejected:** Too basic to need substantiation

## Real-World Example

### Input Paragraph:
```
In the ROCKET AF trial, 14,264 patients with atrial fibrillation were 
randomized to receive either XARELTO 20 mg once daily or dose-adjusted 
warfarin. XARELTO reduced the risk of stroke and systemic embolism by 
21% compared to warfarin (HR 0.79, 95% CI 0.70-0.89). The most common 
adverse reaction was bleeding, occurring in 14.9% of XARELTO-treated 
patients. Atrial fibrillation is a common cardiac arrhythmia affecting 
millions worldwide.
```

### Extracted Claims:

✅ **Claim 1 (EFFICACY + COMPARATIVE):**
```
"XARELTO reduced the risk of stroke and systemic embolism by 21% 
compared to warfarin (HR 0.79, 95% CI 0.70-0.89)"
```
- Complete statement ✅
- About drug performance ✅
- Needs clinical data ✅
- Has statistics ✅
- Is comparative ✅

✅ **Claim 2 (SAFETY):**
```
"The most common adverse reaction was bleeding, occurring in 14.9% 
of XARELTO-treated patients"
```
- Complete statement ✅
- About drug safety ✅
- Needs adverse event data ✅
- Has statistics ✅

### Rejected Content:

❌ **Rejected 1 (METHODOLOGY):**
```
"14,264 patients with atrial fibrillation were randomized to receive 
either XARELTO 20 mg once daily or dose-adjusted warfarin"
```
- Reason: Study design description, not results

❌ **Rejected 2 (BACKGROUND):**
```
"Atrial fibrillation is a common cardiac arrhythmia affecting millions 
worldwide"
```
- Reason: Disease epidemiology, not drug assertion

### Extraction Result:
- **Input:** 4 sentences
- **Extracted:** 2 claims (50% extraction rate is normal)
- **Rejected:** 2 non-claims

## Quick Validation Checklist

Use this when manually reviewing extracted claims:

- [ ] Is it a complete sentence? (subject + verb + object)
- [ ] Can you understand it without reading sentences before/after?
- [ ] Does it state what the DRUG does, is, or causes?
- [ ] Is it about drug performance (not disease or study design)?
- [ ] Would a regulator ask "show me the data to prove this"?
- [ ] Is it more than a trivial fact?
- [ ] Is it NOT a question, citation, or header?

If ALL checkboxes are YES → ✅ Valid Claim  
If ANY checkbox is NO → ❌ Reject

## API Response Fields Explained

```json
{
  "text": "The actual claim text",
  "page": 3,
  "confidence": 0.95,
  
  "suggested_type": "EFFICACY",
  // EFFICACY, SAFETY, INDICATION, CONTRAINDICATION, 
  // DOSING, PHARMACOKINETIC, COMPARATIVE, MECHANISM
  
  "reasoning": "Valid regulatory claim; makes assertion about drug...",
  // Why it was classified this way
  
  "is_comparative": true,
  // Has "vs", "compared to", "superior to", etc.
  
  "contains_statistics": true,
  // Has p-values, CI, percentages, HR, OR
  
  "warnings": null
  // Quality issues if any:
  // ["LOW_WORD_COUNT", "FRAGMENT", "MISSING_VERB", etc.]
}
```

## Common Pitfalls

### ⚠️ Borderline Cases

**Study results WITH drug name:**
✅ "In the trial, Drug X showed 45% reduction" → VALID (about drug)  
❌ "In the trial, 14,264 patients were enrolled" → INVALID (methodology)

**Disease facts WITH treatment mention:**
❌ "AF patients on anticoagulation have lower stroke risk" → INVALID (general fact)  
✅ "XARELTO reduces stroke risk in AF patients" → VALID (drug-specific)

**Mechanism statements:**
✅ "Rivaroxaban is a Factor Xa inhibitor" → VALID (requires evidence)  
❌ "Factor Xa plays a role in coagulation" → INVALID (background)

## Summary

**Extract = Regulatory claim requiring substantiation**
- Complete statement about the drug
- Makes an assertion (not question/background)
- Needs clinical evidence to prove

**Reject = Everything else**
- Fragments, headers, questions
- Background about disease
- Study design descriptions
- Boilerplate and citations
