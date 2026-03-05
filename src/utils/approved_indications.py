"""
FDA-Approved Drug-Indication Database

Purpose: Track known FDA-approved drug-indication pairs to distinguish
         baseline validation (approved) vs true repurposing cases.
         
This fixes the critical bug where sildenafil-for-ED was rejected
despite being an approved indication.
"""

from typing import Dict, List, Set, Tuple
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Approved Drug-Indication Pairs (High-Confidence Cases)
# ============================================================================

# Format: (drug_name_normalized, indication_normalized) -> approval_info
APPROVED_DRUGS: Dict[Tuple[str, str], Dict] = {
    # PDE-5 Inhibitors
    ("sildenafil", "erectile dysfunction"): {
        "approval_year": 1998,
        "trade_name": "Viagra",
        "sponsor": "Pfizer",
        "mechanism": "PDE5A inhibitor",
        "baseline_case": True,
    },
    ("sildenafil", "pulmonary arterial hypertension"): {
        "approval_year": 2005,
        "trade_name": "Revatio",
        "sponsor": "Pfizer",
        "mechanism": "PDE5A inhibitor",
        "baseline_case": True,
    },
    ("tadalafil", "erectile dysfunction"): {
        "approval_year": 2003,
        "trade_name": "Cialis",
        "sponsor": "Lilly",
        "mechanism": "PDE5A inhibitor",
        "baseline_case": True,
    },
    
    # Antidiabetic Agents
    ("metformin", "type 2 diabetes"): {
        "approval_year": 1995,
        "trade_name": "Glucophage",
        "sponsor": "Bristol-Myers Squibb",
        "mechanism": "AMPK activator / gluconeogenesis inhibitor",
        "baseline_case": True,
    },
    ("metformin", "type 2 diabetes mellitus"): {
        "approval_year": 1995,
        "trade_name": "Glucophage",
        "sponsor": "Bristol-Myers Squibb",
        "mechanism": "AMPK activator / gluconeogenesis inhibitor",
        "baseline_case": True,
    },
    
    # NSAIDs
    ("ibuprofen", "pain"): {
        "approval_year": 1974,
        "trade_name": "Motrin",
        "sponsor": "Boots",
        "mechanism": "COX-1/COX-2 inhibitor",
        "baseline_case": True,
    },
    ("ibuprofen", "inflammation"): {
        "approval_year": 1974,
        "trade_name": "Motrin",
        "sponsor": "Boots",
        "mechanism": "COX-1/COX-2 inhibitor",
        "baseline_case": True,
    },
    ("aspirin", "pain"): {
        "approval_year": 1899,
        "trade_name": "Aspirin",
        "sponsor": "Bayer",
        "mechanism": "COX inhibitor",
        "baseline_case": True,
    },
    ("aspirin", "cardiovascular disease"): {
        "approval_year": 1985,
        "trade_name": "Aspirin",
        "sponsor": "Bayer",
        "mechanism": "Platelet aggregation inhibitor",
        "baseline_case": True,
    },
    
    # Statins
    ("atorvastatin", "hyperlipidemia"): {
        "approval_year": 1996,
        "trade_name": "Lipitor",
        "sponsor": "Pfizer",
        "mechanism": "HMG-CoA reductase inhibitor",
        "baseline_case": True,
    },
    ("atorvastatin", "cardiovascular disease"): {
        "approval_year": 1996,
        "trade_name": "Lipitor",
        "sponsor": "Pfizer",
        "mechanism": "HMG-CoA reductase inhibitor",
        "baseline_case": True,
    },
}


# ============================================================================
# Indication Normalization
# ============================================================================

# Map alternative names to canonical forms
INDICATION_ALIASES: Dict[str, str] = {
    "ed": "erectile dysfunction",
    "impotence": "erectile dysfunction",
    "male erectile disorder": "erectile dysfunction",
    
    "diabetes": "type 2 diabetes",
    "diabetes mellitus": "type 2 diabetes",
    "t2dm": "type 2 diabetes",
    "type ii diabetes": "type 2 diabetes",
    
    "high cholesterol": "hyperlipidemia",
    "hypercholesterolemia": "hyperlipidemia",
    "dyslipidemia": "hyperlipidemia",
    
    "cvd": "cardiovascular disease",
    "heart disease": "cardiovascular disease",
    "coronary artery disease": "cardiovascular disease",
    
    "pah": "pulmonary arterial hypertension",
    "pulmonary hypertension": "pulmonary arterial hypertension",
}


# ============================================================================
# Approved Indication Detector
# ============================================================================

class ApprovedIndicationDetector:
    """
    Detects whether a drug-indication pair is FDA-approved.
    
    Critical for distinguishing:
    - Baseline validation cases (already approved)
    - True repurposing candidates (new indication)
    """
    
    def __init__(self):
        self.approved_pairs = APPROVED_DRUGS
        self.indication_aliases = INDICATION_ALIASES
        logger.info(f"ApprovedIndicationDetector: Loaded {len(self.approved_pairs)} approved drug-indication pairs")
    
    def is_approved(self, drug_name: str, indication: str) -> bool:
        """
        Check if drug-indication pair is FDA-approved.
        
        Returns:
            True if approved, False if repurposing candidate
        """
        drug_norm = self._normalize_drug(drug_name)
        indication_norm = self._normalize_indication(indication)
        
        pair = (drug_norm, indication_norm)
        is_approved = pair in self.approved_pairs
        
        if is_approved:
            info = self.approved_pairs[pair]
            logger.info(
                f"✅ BASELINE CASE DETECTED: {drug_name} for {indication} "
                f"(approved {info['approval_year']}, {info['trade_name']})"
            )
        else:
            logger.info(
                f"🆕 REPURPOSING CANDIDATE: {drug_name} for {indication} "
                f"(not an approved indication)"
            )
        
        return is_approved
    
    def get_approval_info(self, drug_name: str, indication: str) -> Dict:
        """Get approval information if available"""
        drug_norm = self._normalize_drug(drug_name)
        indication_norm = self._normalize_indication(indication)
        pair = (drug_norm, indication_norm)
        return self.approved_pairs.get(pair, {})
    
    def _normalize_drug(self, drug_name: str) -> str:
        """Normalize drug name to lowercase, strip whitespace"""
        return drug_name.lower().strip()
    
    def _normalize_indication(self, indication: str) -> str:
        """Normalize indication using alias map"""
        indication_lower = indication.lower().strip()
        
        # Check aliases
        if indication_lower in self.indication_aliases:
            return self.indication_aliases[indication_lower]
        
        return indication_lower
    
    def get_calibration_test_cases(self) -> List[Dict]:
        """
        Return known positive test cases for calibration.
        
        These MUST be accepted by the system or scoring is broken.
        """
        return [
            {
                "drug": "sildenafil",
                "indication": "erectile dysfunction",
                "expected_decision": "accept",
                "reason": "FDA-approved 1998, Viagra, baseline case",
            },
            {
                "drug": "metformin",
                "indication": "type 2 diabetes",
                "expected_decision": "accept",
                "reason": "FDA-approved 1995, Glucophage, baseline case",
            },
            {
                "drug": "ibuprofen",
                "indication": "pain",
                "expected_decision": "accept",
                "reason": "FDA-approved 1974, Motrin, baseline case",
            },
            {
                "drug": "atorvastatin",
                "indication": "cardiovascular disease",
                "expected_decision": "accept",
                "reason": "FDA-approved 1996, Lipitor, baseline case",
            },
        ]


# ============================================================================
# Singleton Instance
# ============================================================================

_detector = None

def get_detector() -> ApprovedIndicationDetector:
    """Get singleton detector instance"""
    global _detector
    if _detector is None:
        _detector = ApprovedIndicationDetector()
    return _detector
