"""
EXIM Agent - Stage 8

Purpose: Assess manufacturing and international trade viability for drug repurposing.
Evaluates API manufacturing countries, import dependency, cost of goods, supply chain
risks, and formulation complexity.

Uses structured estimates based on drug class and molecular properties.
"""

import os
import logging
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
class EXIMAssessment:
    """Manufacturing and trade viability assessment"""
    drug_name: str
    api_manufacturing_countries: List[str]  # Where API is manufactured
    import_dependency_risk: str  # LOW/MEDIUM/HIGH
    estimated_cogs_per_unit: float  # Cost of goods sold per unit (USD)
    supply_chain_risk: str  # LOW/MEDIUM/HIGH
    formulation_complexity: str  # SIMPLE/MODERATE/COMPLEX
    manufacturing_note: str
    key_suppliers: List[str] = field(default_factory=list)
    trade_barriers: List[str] = field(default_factory=list)
    export_markets: List[str] = field(default_factory=list)
    manufacturing_scalability: str = "MODERATE"  # LOW/MODERATE/HIGH
    cmc_challenges: List[str] = field(default_factory=list)  # Chemistry, Manufacturing, Controls
    estimated_setup_cost_usd: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# EXIM Agent
# ============================================================================

class EXIMAgent:
    """
    Stage 8: Manufacturing and Trade Assessment
    
    Evaluates feasibility of scaling manufacturing and international trade.
    """
    
    def __init__(self):
        # Major API manufacturing hubs
        self.manufacturing_hubs = {
            "small_molecule_generic": ["India", "China", "USA", "European Union"],
            "small_molecule_complex": ["USA", "Switzerland", "Germany", "Japan"],
            "biologic": ["USA", "Ireland", "Switzerland", "Singapore"],
            "peptide": ["USA", "China", "European Union"],
        }
        
        # COGS estimates (USD per unit)
        self.cogs_estimates = {
            "simple_oral": 0.50,  # Generic tablet
            "complex_oral": 5.00,  # Modified release, enteric coated
            "injectable": 15.00,  # Sterile injectable
            "biologic": 100.00,  # Monoclonal antibody, etc.
        }
        
        logger.info("EXIMAgent initialized")
    
    def run(
        self,
        drug_name: str,
        indication: str,
        drug_profile = None
    ) -> EXIMAssessment:
        """
        Main entry point: assess manufacturing and trade viability.
        
        Args:
            drug_name: Name of drug
            indication: Disease/condition (not used but maintains consistency)
            drug_profile: Optional drug profile from DrugProfilerAgent
            
        Returns:
            EXIMAssessment with manufacturing and trade analysis
        """
        logger.info(f"Assessing EXIM for: {drug_name}")
        
        assessment = EXIMAssessment(
            drug_name=drug_name,
            api_manufacturing_countries=[],
            import_dependency_risk="MEDIUM",
            estimated_cogs_per_unit=0.0,
            supply_chain_risk="MEDIUM",
            formulation_complexity="MODERATE",
            manufacturing_note=""
        )
        
        try:
            # Step 1: Classify drug type
            drug_class = self._classify_drug_type(drug_profile)
            
            # Step 2: Determine manufacturing countries
            assessment.api_manufacturing_countries = self.manufacturing_hubs.get(
                drug_class,
                ["USA", "European Union"]
            )
            
            # Step 3: Assess formulation complexity
            assessment.formulation_complexity = self._assess_formulation_complexity(drug_profile)
            
            # Step 4: Estimate COGS
            formulation_type = self._determine_formulation_type(drug_profile, drug_class)
            assessment.estimated_cogs_per_unit = self.cogs_estimates.get(
                formulation_type,
                1.00
            )
            
            # Step 5: Assess import dependency risk
            assessment.import_dependency_risk = self._assess_import_risk(
                assessment.api_manufacturing_countries
            )
            
            # Step 6: Assess supply chain risk
            assessment.supply_chain_risk = self._assess_supply_chain_risk(
                drug_class,
                assessment.formulation_complexity
            )
            
            # Step 7: Identify key suppliers (heuristic)
            assessment.key_suppliers = self._identify_key_suppliers(drug_class)
            
            # Step 8: Identify trade barriers
            assessment.trade_barriers = self._identify_trade_barriers(drug_class)
            
            # Step 9: Suggest export markets
            assessment.export_markets = self._suggest_export_markets()
            
            # Step 10: Assess manufacturing scalability
            assessment.manufacturing_scalability = self._assess_scalability(
                drug_class,
                assessment.formulation_complexity
            )
            
            # Step 11: Identify CMC challenges
            assessment.cmc_challenges = self._identify_cmc_challenges(
                drug_class,
                assessment.formulation_complexity
            )
            
            # Step 12: Estimate setup cost
            assessment.estimated_setup_cost_usd = self._estimate_setup_cost(
                drug_class,
                assessment.formulation_complexity
            )
            
            # Step 13: Build manufacturing note
            assessment.manufacturing_note = self._build_note(assessment, drug_class)
            
            logger.info(f"EXIM assessment complete: {assessment.import_dependency_risk} risk, "
                       f"${assessment.estimated_cogs_per_unit:.2f} COGS")
            
        except Exception as e:
            logger.error(f"Error in EXIM assessment: {e}", exc_info=True)
            assessment.manufacturing_note = f"Assessment error: {str(e)}"
        
        return assessment
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _classify_drug_type(self, drug_profile: Optional[Dict]) -> str:
        """Classify drug into manufacturing category."""
        if not drug_profile:
            return "small_molecule_generic"
        
        # Handle both DrugProfile dataclass and dict
        if hasattr(drug_profile, 'drug_class'):
            drug_class = (drug_profile.drug_class or '').lower()
            max_phase = drug_profile.max_phase or 0
        elif isinstance(drug_profile, dict):
            drug_class = drug_profile.get('drug_class', '').lower()
            max_phase = drug_profile.get('max_phase', 0)
        else:
            drug_class = ''
            max_phase = 0
        
        # CRITICAL FIX #3: Ensure max_phase is an int (not a string like "Phase 4")
        if isinstance(max_phase, str):
            try:
                max_phase = int(''.join(c for c in max_phase if c.isdigit()))
            except (ValueError, AttributeError):
                max_phase = 0
        
        max_phase = int(max_phase or 0)
        
        # Biologics
        if any(term in drug_class for term in ['antibody', 'protein', 'enzyme', 'biologic']):
            return "biologic"
        
        # Peptides
        if 'peptide' in drug_class:
            return "peptide"
        
        # Complex small molecules (max_phase must be int for comparison)
        if max_phase >= 4 and any(term in drug_class for term in ['investigational', 'novel']):
            return "small_molecule_complex"
        
        # Default: generic small molecule
        return "small_molecule_generic"
    
    def _assess_formulation_complexity(self, drug_profile: Optional[Dict]) -> str:
        """Assess formulation complexity."""
        if not drug_profile:
            return "MODERATE"
        
        drug_class = drug_profile.get('drug_class', '').lower()
        
        # Biologics are always complex
        if 'biologic' in drug_class or 'antibody' in drug_class:
            return "COMPLEX"
        
        # Injectables are moderate-complex
        if 'injectable' in drug_class or 'parenteral' in drug_class:
            return "COMPLEX"
        
        # Modified release is moderate
        if any(term in drug_class for term in ['modified', 'extended', 'controlled']):
            return "MODERATE"
        
        # Simple oral tablets
        return "SIMPLE"
    
    def _determine_formulation_type(self, drug_profile: Optional[Dict], drug_class: str) -> str:
        """Determine formulation type for COGS estimation."""
        if drug_class == "biologic":
            return "biologic"
        
        if not drug_profile:
            return "simple_oral"
        
        class_str = drug_profile.get('drug_class', '').lower()
        
        if 'injectable' in class_str or 'parenteral' in class_str:
            return "injectable"
        
        if any(term in class_str for term in ['modified', 'extended', 'controlled']):
            return "complex_oral"
        
        return "simple_oral"
    
    def _assess_import_risk(self, manufacturing_countries: List[str]) -> str:
        """Assess import dependency risk."""
        # If only China/India, higher risk
        if set(manufacturing_countries) <= {"China", "India"}:
            return "HIGH"
        
        # If includes USA/EU, lower risk
        if "USA" in manufacturing_countries or "European Union" in manufacturing_countries:
            return "LOW"
        
        return "MEDIUM"
    
    def _assess_supply_chain_risk(self, drug_class: str, formulation_complexity: str) -> str:
        """Assess overall supply chain risk."""
        risk_score = 0
        
        # Biologics have higher supply chain complexity
        if drug_class == "biologic":
            risk_score += 2
        
        # Complex formulations increase risk
        if formulation_complexity == "COMPLEX":
            risk_score += 1
        elif formulation_complexity == "MODERATE":
            risk_score += 0.5
        
        if risk_score >= 2:
            return "HIGH"
        elif risk_score >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _identify_key_suppliers(self, drug_class: str) -> List[str]:
        """Identify likely key suppliers."""
        if drug_class == "biologic":
            return ["Lonza", "Samsung Biologics", "WuXi Biologics", "Catalent Biologics"]
        elif drug_class == "peptide":
            return ["Bachem", "PolyPeptide", "AmbioPharm"]
        else:
            return ["Teva API", "Aurobindo Pharma", "Dr. Reddy's", "Zhejiang Huahai"]
    
    def _identify_trade_barriers(self, drug_class: str) -> List[str]:
        """Identify potential trade barriers."""
        barriers = []
        
        if drug_class in ["biologic", "small_molecule_complex"]:
            barriers.append("Cold chain logistics required")
            barriers.append("Regulatory approval in each market")
        
        barriers.extend([
            "Import tariffs (varies by country)",
            "Good Manufacturing Practice (GMP) certification required",
            "Pharmacopeial compliance (USP/EP/IP)"
        ])
        
        return barriers
    
    def _suggest_export_markets(self) -> List[str]:
        """Suggest promising export markets."""
        return [
            "USA (largest pharmaceutical market)",
            "European Union (high-value, regulatory aligned)",
            "Japan (aging population)",
            "India (generics hub, large population)",
            "Brazil (emerging market, universal healthcare)",
            "Middle East (growing healthcare spend)"
        ]
    
    def _assess_scalability(self, drug_class: str, formulation_complexity: str) -> str:
        """Assess manufacturing scalability."""
        if drug_class == "biologic":
            return "LOW"  # Biologics hard to scale
        
        if formulation_complexity == "SIMPLE":
            return "HIGH"  # Easy to scale generics
        
        return "MODERATE"
    
    def _identify_cmc_challenges(self, drug_class: str, formulation_complexity: str) -> List[str]:
        """Identify Chemistry, Manufacturing, Controls challenges."""
        challenges = []
        
        if drug_class == "biologic":
            challenges.extend([
                "Cell line development and stability",
                "Protein aggregation control",
                "Immunogenicity testing",
                "Comparability studies for biosimilar"
            ])
        
        if formulation_complexity == "COMPLEX":
            challenges.extend([
                "Stability testing (accelerated + long-term)",
                "Dissolution profile matching",
                "Impurity profiling"
            ])
        
        challenges.extend([
            "GMP compliance for multi-country submission",
            "Analytical method validation",
            "Quality control specifications"
        ])
        
        return challenges
    
    def _estimate_setup_cost(self, drug_class: str, formulation_complexity: str) -> float:
        """Estimate manufacturing setup cost (USD)."""
        if drug_class == "biologic":
            return 50_000_000  # Biomanufacturing is expensive
        
        if formulation_complexity == "COMPLEX":
            return 10_000_000
        elif formulation_complexity == "MODERATE":
            return 5_000_000
        else:
            return 2_000_000  # Simple oral forms
    
    def _build_note(self, assessment: EXIMAssessment, drug_class: str) -> str:
        """Build human-readable manufacturing note."""
        parts = []
        
        parts.append(f"Drug classified as {drug_class.replace('_', ' ')}.")
        parts.append(f"Primary manufacturing in {', '.join(assessment.api_manufacturing_countries[:2])}.")
        parts.append(f"Import dependency: {assessment.import_dependency_risk}.")
        parts.append(f"Estimated COGS: ${assessment.estimated_cogs_per_unit:.2f} per unit.")
        parts.append(f"Formulation complexity: {assessment.formulation_complexity}.")
        parts.append(f"Manufacturing scalability: {assessment.manufacturing_scalability}.")
        
        return " ".join(parts)


# ============================================================================
# Standalone Test
# ============================================================================

if __name__ == "__main__":
    agent = EXIMAgent()
    
    # Test case 1: Simple generic oral drug
    print("\n" + "="*60)
    print("Test 1: Aspirin (simple generic)")
    print("="*60)
    
    result1 = agent.run(
        drug_name="aspirin",
        drug_profile={
            'drug_class': 'Small Molecule',
            'max_phase': 4
        }
    )
    
    print(f"✅ Formulation: {result1.formulation_complexity}")
    print(f"   COGS: ${result1.estimated_cogs_per_unit:.2f}")
    print(f"   Manufacturing: {', '.join(result1.api_manufacturing_countries)}")
    print(f"   Import risk: {result1.import_dependency_risk}")
    print(f"   Setup cost: ${result1.estimated_setup_cost_usd:,.0f}")
    
    # Test case 2: Biologic
    print("\n" + "="*60)
    print("Test 2: Adalimumab (biologic)")
    print("="*60)
    
    result2 = agent.run(
        drug_name="adalimumab",
        drug_profile={
            'drug_class': 'Monoclonal Antibody',
            'max_phase': 4
        }
    )
    
    print(f"✅ Formulation: {result2.formulation_complexity}")
    print(f"   COGS: ${result2.estimated_cogs_per_unit:.2f}")
    print(f"   Manufacturing: {', '.join(result2.api_manufacturing_countries)}")
    print(f"   Scalability: {result2.manufacturing_scalability}")
    print(f"   CMC challenges: {len(result2.cmc_challenges)} identified")
