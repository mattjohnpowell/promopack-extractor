/**
 * TypeScript interfaces for Promopack Extractor API
 * Updated: October 2025
 * 
 * Enhanced claim extraction with pharmaceutical regulatory validation
 */

// ============================================================================
// REQUEST TYPES
// ============================================================================

export interface ExtractClaimsRequest {
  /** URL of the PDF document to extract claims from */
  document_url: string;
  
  /** 
   * Prompt version to use for extraction
   * @default "v4_regulatory" (recommended)
   * @options "v1_basic", "v2_enhanced", "v3_context_aware", "v4_regulatory"
   */
  prompt_version?: 'v1_basic' | 'v2_enhanced' | 'v3_context_aware' | 'v4_regulatory';
  
  /** 
   * Force specific LLM model
   * @options "gemini-1.5-flash", "gemini-1.5-pro"
   */
  force_model?: 'gemini-1.5-flash' | 'gemini-1.5-pro';
}

// ============================================================================
// RESPONSE TYPES
// ============================================================================

/**
 * Pharmaceutical regulatory claim type classification
 */
export type ClaimType = 
  | 'EFFICACY'           // Treatment effectiveness, clinical outcomes
  | 'SAFETY'             // Adverse events, tolerability, side effects
  | 'INDICATION'         // Approved uses, treatment indications
  | 'CONTRAINDICATION'   // Restrictions, warnings on use
  | 'DOSING'            // Dosage recommendations, administration
  | 'PHARMACOKINETIC'    // PK/PD, absorption, metabolism
  | 'COMPARATIVE'        // Head-to-head comparisons
  | 'MECHANISM'         // Mechanism of action, pharmacology
  | 'POPULATION';        // Specific patient subgroups

/**
 * Quality warnings for extracted claims
 */
export type ClaimWarning =
  | 'INCOMPLETE_SENTENCE'  // Missing subject or verb
  | 'MISSING_SUBJECT'      // No clear subject
  | 'MISSING_VERB'         // No action word
  | 'LOW_WORD_COUNT'       // Very short (< 5 words)
  | 'FRAGMENT'             // Sentence fragment, torn from context
  | 'QUESTION_FORM'        // Question, not assertion
  | 'TABLE_HEADER'         // Structural element
  | 'CITATION_ONLY'        // Just a citation reference
  | 'BOILERPLATE'          // Standard regulatory language
  | 'BACKGROUND_INFO'      // Disease background, not drug claim
  | 'STUDY_METHODOLOGY'    // Study design description
  | 'TOO_TRIVIAL'          // Too basic to need substantiation
  | 'NO_DRUG_MENTION'      // No drug-related assertion
  | 'CONTEXT_DEPENDENT';   // Cannot stand alone

/**
 * Context surrounding a claim (future enhancement)
 */
export interface ClaimContext {
  /** Text appearing before the claim */
  preceding?: string | null;
  /** Text appearing after the claim */
  following?: string | null;
}

/**
 * Enhanced claim object with regulatory validation metadata
 */
export interface Claim {
  /** The extracted claim text */
  text: string;
  
  /** Page number where claim appears (1-indexed) */
  page: number;
  
  /** 
   * Confidence score from LLM, adjusted by validation
   * @range 0.0 to 1.0
   */
  confidence: number;
  
  // ========== NEW FIELDS (Optional) ==========
  
  /** 
   * Classification of claim type
   * @nullable Unable to classify
   */
  suggested_type?: ClaimType | null;
  
  /** 
   * Human-readable explanation of classification/validation
   * @example "Valid regulatory claim; makes assertion about drug; requires clinical evidence"
   */
  reasoning?: string | null;
  
  /** 
   * Surrounding text context (future enhancement)
   * @nullable Not yet implemented
   */
  context?: ClaimContext | null;
  
  /** 
   * Document section name (future enhancement)
   * @nullable Not yet implemented
   * @example "CLINICAL STUDIES"
   */
  section?: string | null;
  
  /** 
   * Whether claim contains comparative language
   * @example "vs", "compared to", "superior to"
   */
  is_comparative: boolean;
  
  /** 
   * Whether claim contains statistical evidence
   * @example p-values, confidence intervals, percentages, HR, OR
   */
  contains_statistics: boolean;
  
  /** 
   * Whether citation references are present (future enhancement)
   * @default false
   */
  citation_present: boolean;
  
  /** 
   * Quality warnings if any issues detected
   * @nullable No warnings (high quality claim)
   */
  warnings?: ClaimWarning[] | null;
}

/**
 * Metadata about the extraction process
 */
export interface ExtractionMetadata {
  /** Total number of claims extracted by LLM (before validation) */
  total_claims_extracted: number;
  
  /** Number of claims with confidence >= 0.8 */
  high_confidence_claims: number;
  
  /** Number of claims with 0.5 <= confidence < 0.8 */
  medium_confidence_claims: number;
  
  /** Number of claims with confidence < 0.5 */
  low_confidence_claims: number;
  
  /** Processing time in milliseconds */
  processing_time_ms: number;
  
  /** LLM model used for extraction */
  model_version: string;
  
  /** Prompt version used for extraction */
  prompt_version: string;
  
  /** 
   * Document sections analyzed (future enhancement)
   * @nullable Not yet implemented
   */
  sections_analyzed?: string[] | null;
}

/**
 * Security scan information
 */
export interface SecurityInfo {
  /** Risk level detected */
  risk_level: string;
  
  /** Whether sensitive content was found */
  has_sensitive_content: boolean;
  
  /** Number of sensitive entities detected */
  detected_entities_count: number;
  
  /** Compliance warnings */
  compliance_warnings: string[];
  
  /** Compliance severity level */
  compliance_severity: string;
}

/**
 * Main API response for claim extraction
 */
export interface ExtractClaimsResponse {
  /** Array of extracted and validated claims */
  claims: Claim[];
  
  /** 
   * Extraction process metadata
   * @new Added in October 2025 update
   */
  metadata?: ExtractionMetadata | null;
  
  /** Request correlation ID for logging */
  request_id?: string | null;
  
  /** Security scan results */
  security_info?: SecurityInfo | null;
}

// ============================================================================
// ERROR RESPONSE
// ============================================================================

export interface ErrorResponse {
  /** Error code */
  error: string;
  
  /** Human-readable error message */
  message: string;
  
  /** Request correlation ID */
  request_id: string;
  
  /** ISO 8601 timestamp */
  timestamp: string;
}

// ============================================================================
// HELPER TYPES
// ============================================================================

/**
 * API response wrapper (success or error)
 */
export type ApiResponse<T> = 
  | { success: true; data: T }
  | { success: false; error: ErrorResponse };

/**
 * Claim filtering options
 */
export interface ClaimFilters {
  /** Minimum confidence threshold */
  minConfidence?: number;
  
  /** Filter by claim types */
  types?: ClaimType[];
  
  /** Exclude claims with warnings */
  excludeWarnings?: boolean;
  
  /** Only comparative claims */
  comparativeOnly?: boolean;
  
  /** Only claims with statistical evidence */
  statisticsOnly?: boolean;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get user-friendly label for claim type
 */
export function getClaimTypeLabel(type: ClaimType): string {
  const labels: Record<ClaimType, string> = {
    EFFICACY: 'Efficacy',
    SAFETY: 'Safety',
    INDICATION: 'Indication',
    CONTRAINDICATION: 'Contraindication',
    DOSING: 'Dosing',
    PHARMACOKINETIC: 'Pharmacokinetic',
    COMPARATIVE: 'Comparative',
    MECHANISM: 'Mechanism',
    POPULATION: 'Population'
  };
  return labels[type];
}

/**
 * Get color for claim type badge
 */
export function getClaimTypeColor(type: ClaimType): string {
  const colors: Record<ClaimType, string> = {
    EFFICACY: 'green',
    SAFETY: 'yellow',
    INDICATION: 'blue',
    CONTRAINDICATION: 'red',
    DOSING: 'purple',
    PHARMACOKINETIC: 'cyan',
    COMPARATIVE: 'orange',
    MECHANISM: 'indigo',
    POPULATION: 'teal'
  };
  return colors[type];
}

/**
 * Check if claim has quality issues
 */
export function hasQualityIssues(claim: Claim): boolean {
  return !!(claim.warnings && claim.warnings.length > 0);
}

/**
 * Get confidence level category
 */
export function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 0.8) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

/**
 * Filter claims by criteria
 */
export function filterClaims(claims: Claim[], filters: ClaimFilters): Claim[] {
  return claims.filter(claim => {
    // Confidence threshold
    if (filters.minConfidence && claim.confidence < filters.minConfidence) {
      return false;
    }
    
    // Claim types
    if (filters.types && filters.types.length > 0) {
      if (!claim.suggested_type || !filters.types.includes(claim.suggested_type)) {
        return false;
      }
    }
    
    // Exclude warnings
    if (filters.excludeWarnings && hasQualityIssues(claim)) {
      return false;
    }
    
    // Comparative only
    if (filters.comparativeOnly && !claim.is_comparative) {
      return false;
    }
    
    // Statistics only
    if (filters.statisticsOnly && !claim.contains_statistics) {
      return false;
    }
    
    return true;
  });
}

/**
 * Group claims by type
 */
export function groupClaimsByType(claims: Claim[]): Record<string, Claim[]> {
  return claims.reduce((acc, claim) => {
    const type = claim.suggested_type || 'UNCLASSIFIED';
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(claim);
    return acc;
  }, {} as Record<string, Claim[]>);
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

/**
 * Example: Fetch and process claims
 */
export async function exampleFetchClaims(apiUrl: string, apiKey: string, documentUrl: string) {
  const response = await fetch(`${apiUrl}/extract-claims`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      document_url: documentUrl,
      prompt_version: 'v4_regulatory'  // Recommended!
    } as ExtractClaimsRequest)
  });
  
  if (!response.ok) {
    const error: ErrorResponse = await response.json();
    throw new Error(error.message);
  }
  
  const data: ExtractClaimsResponse = await response.json();
  
  // Filter high-quality claims
  const highQualityClaims = filterClaims(data.claims, {
    minConfidence: 0.8,
    excludeWarnings: true
  });
  
  // Group by type
  const claimsByType = groupClaimsByType(highQualityClaims);
  
  console.log(`Extracted ${data.claims.length} total claims`);
  console.log(`High quality: ${highQualityClaims.length}`);
  console.log(`Metadata:`, data.metadata);
  
  return {
    allClaims: data.claims,
    highQualityClaims,
    claimsByType,
    metadata: data.metadata
  };
}
