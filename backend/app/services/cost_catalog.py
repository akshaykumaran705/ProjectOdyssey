"""
Curated cost catalog — deterministic pricing for diagnostic tests.

Rules:
  - All prices are US cash-pay estimates (no insurance)
  - If a test is NOT in the catalog, it gets low=0, high=0 with a note
  - Synonym normalization handles LLM output variations
  - NO hallucinated costs — only catalog data is used
"""
import re
from typing import Optional, Tuple

# ── Master Catalog ───────────────────────────────────────────────
# key: normalized test name → {low, high, code}

COST_CATALOG: dict[str, dict] = {
    # ── Cardiac ──
    "ecg": {"low": 30, "high": 150, "code": "CPT 93000"},
    "echocardiogram": {"low": 400, "high": 1200, "code": "CPT 93306"},
    "cardiac mri": {"low": 1200, "high": 5000, "code": "CPT 75561"},
    "cardiac catheterization": {"low": 3000, "high": 15000, "code": "CPT 93458"},
    "stress test": {"low": 200, "high": 1200, "code": "CPT 93015"},
    "holter monitor": {"low": 200, "high": 600, "code": "CPT 93224"},
    "troponin": {"low": 20, "high": 100, "code": "CPT 84484"},
    "bnp": {"low": 30, "high": 120, "code": "CPT 83880"},

    # ── Imaging ──
    "chest x-ray": {"low": 80, "high": 350, "code": "CPT 71046"},
    "ct chest": {"low": 300, "high": 1500, "code": "CPT 71260"},
    "ct abdomen": {"low": 400, "high": 2000, "code": "CPT 74177"},
    "ct head": {"low": 300, "high": 1500, "code": "CPT 70450"},
    "ct angiography": {"low": 500, "high": 2500, "code": "CPT 71275"},
    "mri brain": {"low": 1000, "high": 4000, "code": "CPT 70553"},
    "mri spine": {"low": 1000, "high": 4000, "code": "CPT 72148"},
    "ultrasound abdomen": {"low": 200, "high": 800, "code": "CPT 76700"},
    "ultrasound pelvis": {"low": 200, "high": 800, "code": "CPT 76856"},
    "venous doppler": {"low": 200, "high": 700, "code": "CPT 93970"},
    "x-ray": {"low": 60, "high": 300, "code": "CPT 73502"},

    # ── Basic Labs ──
    "cbc": {"low": 15, "high": 60, "code": "CPT 85025"},
    "cmp": {"low": 20, "high": 80, "code": "CPT 80053"},
    "bmp": {"low": 15, "high": 60, "code": "CPT 80048"},
    "lipid panel": {"low": 15, "high": 60, "code": "CPT 80061"},
    "thyroid panel": {"low": 30, "high": 120, "code": "CPT 84443"},
    "tsh": {"low": 25, "high": 80, "code": "CPT 84443"},
    "hemoglobin a1c": {"low": 20, "high": 80, "code": "CPT 83036"},
    "urinalysis": {"low": 10, "high": 40, "code": "CPT 81001"},
    "urine culture": {"low": 20, "high": 80, "code": "CPT 87086"},
    "blood culture": {"low": 30, "high": 120, "code": "CPT 87040"},
    "procalcitonin": {"low": 30, "high": 150, "code": "CPT 84145"},
    "crp": {"low": 15, "high": 60, "code": "CPT 86140"},
    "esr": {"low": 10, "high": 40, "code": "CPT 85652"},
    "d-dimer": {"low": 30, "high": 120, "code": "CPT 85379"},
    "pt inr": {"low": 15, "high": 50, "code": "CPT 85610"},
    "ptt": {"low": 15, "high": 50, "code": "CPT 85730"},
    "ferritin": {"low": 20, "high": 80, "code": "CPT 82728"},
    "iron studies": {"low": 30, "high": 120, "code": "CPT 83540"},
    "lactate": {"low": 20, "high": 80, "code": "CPT 83605"},
    "ammonia": {"low": 25, "high": 100, "code": "CPT 82140"},
    "magnesium": {"low": 15, "high": 50, "code": "CPT 83735"},

    # ── Autoimmune / Rheum ──
    "ana panel": {"low": 40, "high": 200, "code": "CPT 86235"},
    "ana": {"low": 30, "high": 120, "code": "CPT 86235"},
    "anti-dsdna": {"low": 40, "high": 180, "code": "CPT 86225"},
    "complement c3 c4": {"low": 30, "high": 140, "code": "CPT 86160"},
    "rheumatoid factor": {"low": 20, "high": 80, "code": "CPT 86431"},
    "anti-ccp": {"low": 40, "high": 180, "code": "CPT 86200"},
    "anca": {"low": 50, "high": 200, "code": "CPT 86235"},
    "hla-b27": {"low": 50, "high": 200, "code": "CPT 86812"},

    # ── Metabolic / Genetic ──
    "genetic testing panel": {"low": 300, "high": 5000, "code": None},
    "whole exome sequencing": {"low": 1500, "high": 8000, "code": None},
    "karyotype": {"low": 200, "high": 800, "code": "CPT 88262"},
    "amino acid panel": {"low": 100, "high": 400, "code": None},
    "organic acid panel": {"low": 100, "high": 400, "code": None},
    "newborn screening panel": {"low": 50, "high": 200, "code": None},

    # ── Infectious ──
    "hiv test": {"low": 20, "high": 80, "code": "CPT 87389"},
    "hepatitis panel": {"low": 50, "high": 200, "code": "CPT 80074"},
    "lyme disease panel": {"low": 50, "high": 200, "code": "CPT 86618"},
    "covid-19 pcr": {"low": 50, "high": 200, "code": "CPT 87635"},
    "tb skin test": {"low": 15, "high": 50, "code": "CPT 86580"},
    "quantiferon gold": {"low": 80, "high": 250, "code": "CPT 86480"},

    # ── Pulmonary ──
    "pulmonary function test": {"low": 150, "high": 600, "code": "CPT 94010"},
    "abg": {"low": 50, "high": 200, "code": "CPT 82803"},
    "sputum culture": {"low": 30, "high": 100, "code": "CPT 87070"},

    # ── Renal ──
    "renal biopsy": {"low": 2500, "high": 8000, "code": "CPT 50200"},
    "urine protein/creatinine ratio": {"low": 20, "high": 80, "code": "CPT 84156"},
    "24h urine protein": {"low": 30, "high": 120, "code": "CPT 84156"},
    "cystatin c": {"low": 40, "high": 150, "code": "CPT 82610"},

    # ── GI ──
    "liver function tests": {"low": 15, "high": 60, "code": "CPT 80076"},
    "amylase": {"low": 15, "high": 50, "code": "CPT 82150"},
    "lipase": {"low": 15, "high": 50, "code": "CPT 83690"},
    "endoscopy": {"low": 800, "high": 3000, "code": "CPT 43239"},
    "colonoscopy": {"low": 1000, "high": 4000, "code": "CPT 45378"},

    # ── Neuro ──
    "lumbar puncture": {"low": 500, "high": 2000, "code": "CPT 62270"},
    "eeg": {"low": 200, "high": 800, "code": "CPT 95816"},
    "emg": {"low": 300, "high": 1200, "code": "CPT 95907"},

    # ── Procedures ──
    "skin biopsy": {"low": 200, "high": 600, "code": "CPT 11102"},
    "bone marrow biopsy": {"low": 1000, "high": 4000, "code": "CPT 38222"},
}


# ── Synonym Map ──────────────────────────────────────────────────

SYNONYMS: dict[str, str] = {
    "echo": "echocardiogram",
    "tte": "echocardiogram",
    "transthoracic echocardiogram": "echocardiogram",
    "ekg": "ecg",
    "electrocardiogram": "ecg",
    "12-lead ecg": "ecg",
    "12 lead ecg": "ecg",
    "cxr": "chest x-ray",
    "chest radiograph": "chest x-ray",
    "ua": "urinalysis",
    "urine analysis": "urinalysis",
    "u/a": "urinalysis",
    "complete blood count": "cbc",
    "complete metabolic panel": "cmp",
    "basic metabolic panel": "bmp",
    "prothrombin time": "pt inr",
    "inr": "pt inr",
    "partial thromboplastin time": "ptt",
    "aptt": "ptt",
    "c-reactive protein": "crp",
    "sed rate": "esr",
    "erythrocyte sedimentation rate": "esr",
    "antinuclear antibody": "ana",
    "ana screen": "ana",
    "anti-double stranded dna": "anti-dsdna",
    "anti ds-dna": "anti-dsdna",
    "complement levels": "complement c3 c4",
    "c3 c4": "complement c3 c4",
    "pfts": "pulmonary function test",
    "pft": "pulmonary function test",
    "spirometry": "pulmonary function test",
    "arterial blood gas": "abg",
    "blood gas": "abg",
    "lfts": "liver function tests",
    "lft": "liver function tests",
    "liver panel": "liver function tests",
    "hepatic panel": "liver function tests",
    "upcr": "urine protein/creatinine ratio",
    "spot urine protein": "urine protein/creatinine ratio",
    "urine protein creatinine ratio": "urine protein/creatinine ratio",
    "lp": "lumbar puncture",
    "spinal tap": "lumbar puncture",
    "brain mri": "mri brain",
    "head ct": "ct head",
    "ct scan head": "ct head",
    "ct scan chest": "ct chest",
    "ct pulmonary angiogram": "ct angiography",
    "ctpa": "ct angiography",
    "v/q scan": "ct angiography",
    "duplex ultrasound": "venous doppler",
    "lower extremity doppler": "venous doppler",
    "serial troponin": "troponin",
    "cardiac enzymes": "troponin",
    "serial cardiac enzymes": "troponin",
    "cardiac enzyme": "troponin",
    "troponin i": "troponin",
    "troponin t": "troponin",
    "ck-mb": "troponin",
    "pro-bnp": "bnp",
    "nt-probnp": "bnp",
    "hba1c": "hemoglobin a1c",
    "a1c": "hemoglobin a1c",
    "ppd": "tb skin test",
    "tuberculin skin test": "tb skin test",
    "wes": "whole exome sequencing",
    "exome sequencing": "whole exome sequencing",
}

# ── Normalization ────────────────────────────────────────────────

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s/\-]")


def normalize_test_name(test: str) -> str:
    """
    Normalize a test name for catalog lookup.
    Steps: lowercase → strip punctuation → collapse whitespace → synonym map.
    """
    s = (test or "").strip().lower()
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()

    # Direct synonym lookup
    if s in SYNONYMS:
        return SYNONYMS[s]

    # Try partial synonym matching (for phrases like "obtain serial troponin")
    for syn_key, syn_val in SYNONYMS.items():
        if syn_key in s:
            return syn_val

    # Try direct catalog match
    if s in COST_CATALOG:
        return s

    # Try partial catalog matching
    for cat_key in COST_CATALOG:
        if cat_key in s or s in cat_key:
            return cat_key

    return s


def lookup(test_name: str) -> Optional[Tuple[dict, str]]:
    """
    Look up a test in the catalog.
    Returns (catalog_entry, normalized_key) or None if not found.
    """
    key = normalize_test_name(test_name)
    entry = COST_CATALOG.get(key)
    if entry:
        return entry, key
    return None
