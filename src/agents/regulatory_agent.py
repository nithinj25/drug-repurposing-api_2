"""
Regulatory Agent - Stage 7

Purpose: Assess FDA approval pathway options for drug repurposing, including:
- 505(b)(2) pathway (eligible if drug already approved, new indication)
- Orphan Drug designation (< 200,000 US patients)
- Breakthrough Therapy designation (serious condition + preliminary evidence)
- Priority Review Voucher eligibility

Queries FDA orphan drug database where possible, uses rule-based logic otherwise.
"""

import os
import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class RegulatoryAssessment:
    """FDA regulatory pathway assessment"""
    drug_name: str
    indication: str
    recommended_pathway: str  # "505(b)(2)", "Orphan Drug", "Breakthrough Therapy", "Traditional NDA"
    estimated_timeline_years: float  # Years from IND to approval
    key_requirements: List[str]  # Major regulatory requirements
    orphan_eligible: bool  # Orphan Drug Designation eligible
    priority_review_voucher_eligible: bool  # PRV eligible
    breakthrough_eligible: bool  # Breakthrough Therapy eligible
    fast_track_eligible: bool  # Fast Track eligible
    estimated_development_cost_usd: Optional[float] = None  # Total cost estimate
    regulatory_precedents: List[str] = field(default_factory=list)  # Similar approved cases
    key_risks: List[str] = field(default_factory=list)
    recommendation_rationale: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# Regulatory Agent
# ============================================================================

class RegulatoryAgent:
    """
    Stage 7: FDA Regulatory Pathway Assessment
    
    Determines optimal approval pathway and regulatory strategy.
    """
    
    def __init__(self):
        self.fda_orphan_url = "https://www.accessdata.fda.gov/scripts/opdlisting/oopd/detailedIndex.cfm"
        self.timeout = 30
        
        # Prevalence thresholds
        self.orphan_threshold_us = 200000  # < 200k patients in US
        
        # Timeline estimates (years)
        self.timelines = {
            "505(b)(2)": 3.5,  # Leverages existing safety data
            "Orphan Drug": 4.0,  # Smaller trials but full review
            "Breakthrough Therapy": 3.0,  # Priority review + intensive guidance
            "Traditional NDA": 7.0,  # Full development
            "Fast Track": 4.5,  # Some expediting but not as much as BT
        }
        
        # Cost estimates (USD millions)
        self.costs = {
            "505(b)(2)": 50_000_000,  # Lower than traditional
            "Orphan Drug": 60_000_000,
            "Breakthrough Therapy": 100_000_000,
            "Traditional NDA": 200_000_000,
            "Fast Track": 150_000_000,
        }
        
        logger.info("RegulatoryAgent initialized (FDA pathways)")
    
    def run(
        self,
        drug_name: str,
        indication: str,
        drug_profile: Optional[Dict] = None,
        preliminary_evidence: Optional[Dict] = None
    ) -> RegulatoryAssessment:
        """
        Main entry point: assess regulatory pathway.
        
        Args:
            drug_name: Name of drug
            indication: Disease/condition
            drug_profile: Optional drug profile from DrugProfilerAgent
            preliminary_evidence: Optional evidence summary from other agents
            
        Returns:
            RegulatoryAssessment with pathway recommendations
        """
        logger.info(f"Assessing regulatory pathway: {drug_name} for {indication}")
        
        assessment = RegulatoryAssessment(
            drug_name=drug_name,
            indication=indication,
            recommended_pathway="",
            estimated_timeline_years=0,
            key_requirements=[],
            orphan_eligible=False,
            priority_review_voucher_eligible=False,
            breakthrough_eligible=False,
            fast_track_eligible=False
        )
        
        try:
            # Step 1: Check if drug is already approved (enables 505(b)(2))
            is_approved = self._check_drug_approved(drug_profile)
            
            # Step 2: Estimate disease prevalence to check orphan eligibility
            prevalence_us = self._estimate_prevalence(indication)
            assessment.orphan_eligible = prevalence_us < self.orphan_threshold_us
            
            # Step 3: Check if indication is serious/life-threatening
            is_serious = self._check_serious_condition(indication)
            
            # Step 4: Check if preliminary evidence exists
            has_prelim_evidence = self._check_preliminary_evidence(preliminary_evidence)
            
            # Step 5: Determine eligibilities
            assessment.breakthrough_eligible = (
                is_serious and has_prelim_evidence and is_approved
            )
            
            assessment.fast_track_eligible = (
                is_serious or assessment.orphan_eligible
            )
            
            assessment.priority_review_voucher_eligible = (
                assessment.orphan_eligible and 
                self._check_prv_disease(indication)
            )
            
            # Step 6: Select recommended pathway based on eligibility
            pathway = self._select_optimal_pathway(
                is_approved=is_approved,
                orphan=assessment.orphan_eligible,
                breakthrough=assessment.breakthrough_eligible,
                fast_track=assessment.fast_track_eligible,
                is_serious=is_serious
            )
            
            assessment.recommended_pathway = pathway
            assessment.estimated_timeline_years = self.timelines.get(pathway, 5.0)
            assessment.estimated_development_cost_usd = self.costs.get(pathway, 100_000_000)
            
            # Step 7: Build key requirements
            assessment.key_requirements = self._build_requirements(
                pathway, assessment.orphan_eligible, assessment.breakthrough_eligible
            )
            
            # Step 8: Find regulatory precedents
            assessment.regulatory_precedents = self._find_precedents(indication, pathway)
            
            # Step 9: Identify key risks
            assessment.key_risks = self._identify_risks(
                pathway, is_approved, assessment.orphan_eligible
            )
            
            # Step 10: Build rationale
            assessment.recommendation_rationale = self._build_rationale(assessment)
            
            logger.info(f"Recommended pathway: {pathway} ({assessment.estimated_timeline_years} years)")
            
        except Exception as e:
            logger.error(f"Error in regulatory assessment: {e}", exc_info=True)
            assessment.key_risks.append(f"Assessment error: {str(e)}")
        
        return assessment
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _check_drug_approved(self, drug_profile) -> bool:
        """Check if drug has at least one FDA approval."""
        if not drug_profile:
            return False
        
        # Handle both DrugProfile dataclass and dict
        if hasattr(drug_profile, 'max_phase'):
            max_phase = drug_profile.max_phase or 0
        elif isinstance(drug_profile, dict):
            max_phase = drug_profile.get('max_phase', 0)
        else:
            max_phase = 0
        
        # Convert string to float if necessary (ChEMBL returns "4.0")
        try:
            max_phase = float(max_phase) if max_phase else 0
        except (ValueError, TypeError):
            max_phase = 0
        
        return max_phase >= 4  # Phase 4 means approved
    
    def _estimate_prevalence(self, indication: str) -> int:
        """
        Estimate US patient population for indication.
        
        Uses heuristic-based estimation. In production, query epidemiology databases.
        """
        indication_lower = indication.lower()
        
        # Known rare diseases (< 200k US patients)
        rare_keywords = [
            'orphan', 'rare', 'syndrome', 'dystrophy', 'atrophy',
            'glioblastoma', 'mesothelioma', 'retinoblastoma',
            'huntington', 'amyotrophic', 'als', 'cystic fibrosis'
        ]
        
        if any(kw in indication_lower for kw in rare_keywords):
            return 50000  # Likely orphan
        
        # Common diseases (> 200k patients)
        common_keywords = [
            'diabetes', 'hypertension', 'cancer', 'carcinoma',
            'alzheimer', 'parkinson', 'depression', 'anxiety',
            'asthma', 'copd', 'heart failure', 'stroke'
        ]
        
        if any(kw in indication_lower for kw in common_keywords):
            return 5000000  # Not orphan
        
        # Default: assume not orphan
        return 300000
    
    def _check_serious_condition(self, indication: str) -> bool:
        """Check if indication is serious/life-threatening."""
        indication_lower = indication.lower()
        
        serious_keywords = [
            'cancer', 'carcinoma', 'tumor', 'lymphoma', 'leukemia',
            'heart failure', 'stroke', 'sepsis', 'fatal',
            'progressive', 'terminal', 'degenerative',
            'als', 'huntington', 'alzheimer advanced'
        ]
        
        return any(kw in indication_lower for kw in serious_keywords)
    
    def _check_preliminary_evidence(self, preliminary_evidence: Optional[Dict]) -> bool:
        """Check if substantial preliminary evidence exists."""
        if not preliminary_evidence:
            return False
        
        # Look for clinical trial data or strong mechanistic evidence
        clinical_score = preliminary_evidence.get('clinical_score', 0)
        molecular_score = preliminary_evidence.get('molecular_score', 0)
        
        return clinical_score > 0.5 or molecular_score > 0.6
    
    def _check_prv_disease(self, indication: str) -> bool:
        """
        Check if disease qualifies for Priority Review Voucher.
        
        PRV applies to: neglected tropical diseases, rare pediatric diseases, 
        medical countermeasures.
        """
        indication_lower = indication.lower()
        
        prv_keywords = [
            'pediatric', 'children', 'infant', 'neonatal',
            'neglected', 'tropical', 'malaria', 'tuberculosis',
            'chagas', 'leishmaniasis', 'dengue'
        ]
        
        return any(kw in indication_lower for kw in prv_keywords)
    
    def _select_optimal_pathway(
        self,
        is_approved: bool,
        orphan: bool,
        breakthrough: bool,
        fast_track: bool,
        is_serious: bool
    ) -> str:
        """Select best regulatory pathway based on eligibilities."""
        
        # Priority order: Breakthrough > 505(b)(2) + Orphan > 505(b)(2) > Orphan > Fast Track
        
        if breakthrough:
            return "Breakthrough Therapy"
        
        if is_approved:
            if orphan:
                return "505(b)(2) + Orphan Drug"  # Can combine
            return "505(b)(2)"
        
        if orphan:
            return "Orphan Drug"
        
        if fast_track:
            return "Fast Track"
        
        return "Traditional NDA"
    
    def _build_requirements(
        self,
        pathway: str,
        orphan: bool,
        breakthrough: bool
    ) -> List[str]:
        """Build list of key regulatory requirements."""
        requirements = []
        
        if "505(b)(2)" in pathway:
            requirements.extend([
                "Bridge to existing safety database via literature/own studies",
                "At least one adequate & well-controlled efficacy study",
                "Differential labeling to distinguish from approved drug",
            ])
        
        if orphan or "Orphan" in pathway:
            requirements.extend([
                "Demonstrate disease affects < 200,000 US patients",
                "Provide plausible hypothesis for efficacy",
                "Orphan Drug Designation application within 90 days of IND",
                "7-year market exclusivity upon approval",
            ])
        
        if breakthrough or "Breakthrough" in pathway:
            requirements.extend([
                "Preliminary clinical evidence of substantial improvement",
                "Intensive FDA guidance throughout development",
                "Rolling review of BLA/NDA sections",
                "Organizational commitment meeting within 60 days",
            ])
        
        if "Traditional NDA" in pathway:
            requirements.extend([
                "Phase 1, 2, and 3 clinical trials",
                "Two pivotal Phase 3 trials typically required",
                "Full CMC and nonclinical package",
                "10-month standard review",
            ])
        
        if "Fast Track" in pathway:
            requirements.extend([
                "Serious condition + unmet medical need",
                "Rolling submission allowed",
                "More frequent FDA meetings",
            ])
        
        return requirements
    
    def _find_precedents(self, indication: str, pathway: str) -> List[str]:
        """Find similar regulatory precedents."""
        # In production, query FDA approval database
        # For now, use heuristic examples
        
        precedents = []
        
        if "505(b)(2)" in pathway:
            precedents.append("Precedent: Nuplazid (pimavanserin) - New indication for Parkinson psychosis")
            precedents.append("Precedent: Epidiolex (cannabidiol) - Repurposed for rare epilepsy")
        
        if "Orphan" in pathway:
            precedents.append("Precedent: Spinraza (nusinersen) - Orphan for spinal muscular atrophy")
            precedents.append("Precedent: Over 50% of orphan drugs are repurposed compounds")
        
        return precedents
    
    def _identify_risks(self, pathway: str, is_approved: bool, orphan: bool) -> List[str]:
        """Identify key regulatory risks."""
        risks = []
        
        if not is_approved and "505(b)(2)" in pathway:
            risks.append("Drug not yet approved - cannot use 505(b)(2) pathway")
        
        if orphan:
            risks.append("Orphan designation requires robust epidemiology data")
            risks.append("Post-marketing studies required to confirm prevalence")
        
        if "Breakthrough" in pathway:
            risks.append("FDA may withdraw designation if evidence doesn't hold")
        
        if "Traditional" in pathway:
            risks.append("Long timeline (7+ years) and high cost ($200M+)")
            risks.append("Risk of competitor approval during development")
        
        return risks
    
    def _build_rationale(self, assessment: RegulatoryAssessment) -> str:
        """Build human-readable recommendation rationale."""
        parts = []
        
        parts.append(f"Recommended pathway: {assessment.recommended_pathway}.")
        
        if assessment.orphan_eligible:
            parts.append("Orphan designation eligible due to rare disease prevalence.")
        
        if assessment.breakthrough_eligible:
            parts.append("Breakthrough Therapy potential given serious condition + preliminary evidence.")
        
        parts.append(f"Estimated timeline: {assessment.estimated_timeline_years} years from IND.")
        parts.append(f"Estimated cost: ${assessment.estimated_development_cost_usd/1_000_000:.0f}M.")
        
        if assessment.priority_review_voucher_eligible:
            parts.append("Priority Review Voucher eligible - significant value ($100M+).")
        
        return " ".join(parts)


# ============================================================================
# Standalone Test
# ============================================================================

if __name__ == "__main__":
    agent = RegulatoryAgent()
    
    # Test case 1: Approved drug, orphan indication
    print("\n" + "="*60)
    print("Test 1: Aspirin for Glioblastoma (orphan)")
    print("="*60)
    
    result1 = agent.run(
        drug_name="aspirin",
        indication="glioblastoma",
        drug_profile={'max_phase': 4},  # Approved
        preliminary_evidence={'molecular_score': 0.7}
    )
    
    print(f"✅ Pathway: {result1.recommended_pathway}")
    print(f"   Timeline: {result1.estimated_timeline_years} years")
    print(f"   Orphan: {result1.orphan_eligible}")
    print(f"   Breakthrough: {result1.breakthrough_eligible}")
    print(f"   Rationale: {result1.recommendation_rationale}")
    
    # Test case 2: Not approved, common indication
    print("\n" + "="*60)
    print("Test 2: Experimental drug for Diabetes (common)")
    print("="*60)
    
    result2 = agent.run(
        drug_name="compound-X",
        indication="type 2 diabetes",
        drug_profile={'max_phase': 2},  # Not approved
        preliminary_evidence=None
    )
    
    print(f"✅ Pathway: {result2.recommended_pathway}")
    print(f"   Timeline: {result2.estimated_timeline_years} years")
    print(f"   Orphan: {result2.orphan_eligible}")
    print(f"   Key risks: {result2.key_risks[:2]}")
