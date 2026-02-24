/* ── API Types for ProjectOdyssey ──────────────────────────── */

export interface Case {
    id: number;
    title: string;
    chief_complaint: string;
    created_by_user_id: number;
    age?: number;
    sex?: string;
    history_present_illness?: string;
}

export interface CaseCreate {
    title: string;
    chief_complaint: string;
    history_present_illness?: string;
    age?: number;
    sex?: string;
}

export interface StructuredCase {
    chief_complaint?: string;
    symptoms?: string[];
    timeline?: Record<string, string>;
    abnormal_labs?: Array<{ name: string; value: string; flag?: string }>;
    medications?: string[];
    red_flags?: string[];
    exam_findings?: string[];
    history_present_illness?: string;
    [key: string]: unknown;
}

export interface DxItem {
    name: string;
    likelihood?: string;
    rationale?: string;
    key_evidence?: string[] | Record<string, unknown>;
}

export interface AnalysisData {
    top_differentials?: DxItem[];
    triage_recommendation?: string;
    recommended_next_steps?: string[];
    missing_info?: string[];
    evidence_summary?: string[];
    meta?: Record<string, unknown>;
    [key: string]: unknown;
}

export interface EvidenceLink {
    claim: string;
    supported: boolean;
    source_path?: string;
    source_excerpt?: string;
    reason?: string;
}

export interface DiagnosisTrust {
    diagnosis: string;
    evidence_links: EvidenceLink[];
    support_ratio: number;
    confidence_score: number;
    confidence_level: "high" | "medium" | "low";
    uncertainty_reasons: string[];
}

export interface SafetyFlag {
    flag: string;
    severity: "low" | "medium" | "high" | "critical";
    triggered_by: string[];
    recommendation: string;
}

export interface TrustReport {
    status: "ok" | "warn" | "fail";
    overall_support_ratio: number;
    overall_confidence: number;
    safety_flags: SafetyFlag[];
    diagnoses: DiagnosisTrust[];
    global_warnings: string[];
    stats: Record<string, number>;
}

export interface CostLineItem {
    item: string;
    cpt_or_code?: string;
    low: number;
    high: number;
    currency?: string;
    notes?: string;
}

export interface CostEstimate {
    items: CostLineItem[];
    total_low: number;
    total_high: number;
    confidence?: string;
    assumptions?: string[];
    exclusions?: string[];
}

export interface RareCandidate {
    disease?: string;
    name?: string;
    likelihood?: string;
    why_this_fits?: string;
    supporting_evidence?: string[];
    confirmatory_tests?: string[];
    specialist_referral?: string;
    safety_notes?: string;
    diagnostic_delay_risk?: number;
    missing_evidence?: string[];
}

export interface RareSpotlight {
    candidates: RareCandidate[];
    diagnostic_delay_risk?: number;
}

export interface Metrics {
    status: string;
    counts: Record<string, number>;
    jobs: Record<string, number>;
    cache: Record<string, number>;
    latency: Record<string, number>;
}
