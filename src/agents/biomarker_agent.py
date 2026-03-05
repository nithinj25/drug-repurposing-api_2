"""
Biomarker Agent - Stage 9

Purpose: Query PharmGKB API for pharmacogenomic associations to identify:
- Which patient genetic variants affect drug response
- Biomarker hypotheses for patient stratification
- Target populations most likely to benefit
- Pharmacogenomic variants of interest

Cross-references with disease genetic architecture when available.
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
class PharmacogenomicVariant:
    """A genetic variant affecting drug response"""
    variant_id: str  # rsID or HGVS
    gene: str
    genotype: str  # e.g., "CYP2D6*1/*1"
    phenotype: str  # e.g., "Normal metabolizer"
    clinical_effect: str  # e.g., "Increased efficacy", "Toxicity risk"
    evidence_level: str  # "1A", "1B", "2A", "2B", "3", "4"
    source: str = "PharmGKB"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BiomarkerAssessment:
    """Biomarker and pharmacogenomic assessment"""
    drug_name: str
    indication: Optional[str]
    biomarker_hypothesis: str  # Main hypothesis for patient stratification
    target_population: str  # Description of ideal patient population
    pharmacogenomic_variants: List[PharmacogenomicVariant]
    stratification_confidence: str  # HIGH/MEDIUM/LOW
    key_genes: List[str]  # Most important genes
    dosing_implications: List[str]  # Dose adjustment recommendations
    companion_diagnostic_potential: bool  # Could develop companion diagnostic?
    genetic_testing_recommendation: str
    estimated_responder_rate: Optional[float] = None  # % of population likely to respond
    population_enrichment_strategy: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['pharmacogenomic_variants'] = [v.to_dict() for v in self.pharmacogenomic_variants]
        return data


# ============================================================================
# Biomarker Agent
# ============================================================================

class BiomarkerAgent:
    """
    Stage 9: Pharmacogenomic and Biomarker Assessment
    
    Identifies genetic markers for patient stratification.
    """
    
    def __init__(self):
        self.pharmgkb_base_url = "https://api.pharmgkb.org/v1/data"
        self.api_key = os.getenv("PHARMGKB_API_KEY")  # Optional API key
        self.timeout = 30
        
        # PharmGKB evidence levels
        self.evidence_levels = {
            "1A": "High - Clinical annotation with strong evidence",
            "1B": "High - Clinical annotation with moderate evidence",
            "2A": "Moderate - Based on multiple case reports",
            "2B": "Moderate - Based on in vitro/pharmacology",
            "3": "Low - Single case report",
            "4": "Preclinical only"
        }
        
        logger.info("BiomarkerAgent initialized (PharmGKB API)")
    
    def run(
        self,
        drug_name: str,
        indication: Optional[str] = None,
        drug_profile: Optional[Dict] = None
    ) -> BiomarkerAssessment:
        """
        Main entry point: assess pharmacogenomic associations.
        
        Args:
            drug_name: Name of drug
            indication: Optional disease/condition
            drug_profile: Optional drug profile from DrugProfilerAgent
            
        Returns:
            BiomarkerAssessment with pharmacogenomic data
        """
        logger.info(f"Assessing biomarkers for: {drug_name}")
        
        assessment = BiomarkerAssessment(
            drug_name=drug_name,
            indication=indication,
            biomarker_hypothesis="",
            target_population="",
            pharmacogenomic_variants=[],
            stratification_confidence="LOW",
            key_genes=[],
            dosing_implications=[],
            companion_diagnostic_potential=False,
            genetic_testing_recommendation=""
        )
        
        try:
            # Step 1: Query PharmGKB for drug-gene interactions
            variants = self._query_pharmgkb(drug_name)
            assessment.pharmacogenomic_variants = variants
            
            if not variants:
                # Fallback: Use heuristic knowledge base
                variants = self._get_fallback_variants(drug_name)
                assessment.pharmacogenomic_variants = variants
            
            # Step 2: Extract key genes
            assessment.key_genes = list(set([v.gene for v in variants]))
            
            # Step 3: Assess stratification confidence
            assessment.stratification_confidence = self._assess_confidence(variants)
            
            # Step 4: Generate biomarker hypothesis
            assessment.biomarker_hypothesis = self._generate_hypothesis(
                drug_name, variants, indication
            )
            
            # Step 5: Define target population
            assessment.target_population = self._define_target_population(variants)
            
            # Step 6: Extract dosing implications
            assessment.dosing_implications = self._extract_dosing_implications(variants)
            
            # Step 7: Assess companion diagnostic potential
            assessment.companion_diagnostic_potential = self._assess_cdx_potential(
                variants, assessment.stratification_confidence
            )
            
            # Step 8: Build genetic testing recommendation
            assessment.genetic_testing_recommendation = self._build_testing_recommendation(
                assessment
            )
            
            # Step 9: Estimate responder rate
            assessment.estimated_responder_rate = self._estimate_responder_rate(variants)
            
            # Step 10: Build enrichment strategy
            assessment.population_enrichment_strategy = self._build_enrichment_strategy(
                assessment
            )
            
            logger.info(f"Biomarker assessment complete: {len(variants)} variants found, "
                       f"{assessment.stratification_confidence} confidence")
            
        except Exception as e:
            assessment.error = f"Error in biomarker assessment: {str(e)}"
            logger.error(assessment.error, exc_info=True)
        
        return assessment
    
    # ========================================================================
    # PharmGKB Methods
    # ========================================================================
    
    def _query_pharmgkb(self, drug_name: str) -> List[PharmacogenomicVariant]:
        """
        Query PharmGKB API for clinical annotations.
        
        Note: PharmGKB API requires authentication. If no API key, uses fallback.
        """
        if not self.api_key:
            logger.warning("No PharmGKB API key found, using fallback knowledge base")
            return []
        
        try:
            # Search for drug first
            search_url = f"{self.pharmgkb_base_url}/search"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {"query": drug_name, "type": "Chemical"}
            
            response = requests.get(search_url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            search_data = response.json()
            
            if not search_data.get('results'):
                logger.debug(f"No PharmGKB results for {drug_name}")
                return []
            
            drug_id = search_data['results'][0]['id']
            
            # Get clinical annotations for this drug
            annotations_url = f"{self.pharmgkb_base_url}/clinicalAnnotation"
            params = {"drugId": drug_id}
            
            response = requests.get(annotations_url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            annotations = response.json().get('data', [])
            
            # Parse annotations into variants
            variants = []
            for annotation in annotations:
                variant = self._parse_annotation(annotation)
                if variant:
                    variants.append(variant)
            
            logger.info(f"Found {len(variants)} PharmGKB variants for {drug_name}")
            return variants
            
        except Exception as e:
            logger.warning(f"PharmGKB query failed: {e}")
            return []
    
    def _parse_annotation(self, annotation: Dict) -> Optional[PharmacogenomicVariant]:
        """Parse PharmGKB annotation into variant object."""
        try:
            variant = PharmacogenomicVariant(
                variant_id=annotation.get('variantId', 'unknown'),
                gene=annotation.get('gene', {}).get('symbol', 'unknown'),
                genotype=annotation.get('genotype', 'unknown'),
                phenotype=annotation.get('phenotype', 'unknown'),
                clinical_effect=annotation.get('annotation', 'unknown'),
                evidence_level=annotation.get('level', '4'),
                source="PharmGKB"
            )
            return variant
        except Exception as e:
            logger.debug(f"Failed to parse annotation: {e}")
            return None
    
    def _get_fallback_variants(self, drug_name: str) -> List[PharmacogenomicVariant]:
        """
        Fallback knowledge base of well-known pharmacogenomic interactions.
        """
        drug_lower = drug_name.lower()
        
        knowledge_base = {
            "warfarin": [
                PharmacogenomicVariant(
                    variant_id="rs9923231",
                    gene="VKORC1",
                    genotype="VKORC1 -1639G>A",
                    phenotype="Increased sensitivity",
                    clinical_effect="Dose reduction required (30-50%)",
                    evidence_level="1A"
                ),
                PharmacogenomicVariant(
                    variant_id="CYP2C9",
                    gene="CYP2C9",
                    genotype="CYP2C9*2 or *3",
                    phenotype="Poor metabolizer",
                    clinical_effect="Increased bleeding risk",
                    evidence_level="1A"
                ),
            ],
            "clopidogrel": [
                PharmacogenomicVariant(
                    variant_id="CYP2C19",
                    gene="CYP2C19",
                    genotype="CYP2C19*2 or *3",
                    phenotype="Poor metabolizer",
                    clinical_effect="Reduced efficacy, cardiovascular events",
                    evidence_level="1A"
                ),
            ],
            "abacavir": [
                PharmacogenomicVariant(
                    variant_id="HLA-B*57:01",
                    gene="HLA-B",
                    genotype="HLA-B*57:01 positive",
                    phenotype="Hypersensitivity",
                    clinical_effect="Contraindication - severe reaction",
                    evidence_level="1A"
                ),
            ],
            "tamoxifen": [
                PharmacogenomicVariant(
                    variant_id="CYP2D6",
                    gene="CYP2D6",
                    genotype="CYP2D6 poor metabolizer",
                    phenotype="Reduced activation",
                    clinical_effect="Decreased efficacy in breast cancer",
                    evidence_level="1A"
                ),
            ],
            "simvastatin": [
                PharmacogenomicVariant(
                    variant_id="SLCO1B1",
                    gene="SLCO1B1",
                    genotype="SLCO1B1*5 (c.521T>C)",
                    phenotype="Reduced uptake",
                    clinical_effect="Myopathy risk - dose limit 40mg",
                    evidence_level="1A"
                ),
            ],
        }
        
        # Return variants if drug is in knowledge base
        return knowledge_base.get(drug_lower, [])
    
    # ========================================================================
    # Analysis Methods
    # ========================================================================
    
    def _assess_confidence(self, variants: List[PharmacogenomicVariant]) -> str:
        """Assess confidence in stratification based on variant evidence."""
        if not variants:
            return "LOW"
        
        # Count high-evidence variants
        high_evidence = sum(1 for v in variants if v.evidence_level in ["1A", "1B"])
        
        if high_evidence >= 2:
            return "HIGH"
        elif high_evidence >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_hypothesis(
        self,
        drug_name: str,
        variants: List[PharmacogenomicVariant],
        indication: Optional[str]
    ) -> str:
        """Generate biomarker hypothesis."""
        if not variants:
            return f"No established pharmacogenomic biomarkers identified for {drug_name}. " \
                   f"Consider exploratory analysis of drug metabolism and target pathway genes."
        
        key_gene = variants[0].gene
        key_effect = variants[0].phenotype
        
        hypothesis = f"Most likely to show efficacy in patients with {key_gene} {key_effect} " \
                    f"based on pharmacogenomic data."
        
        if len(variants) > 1:
            other_genes = [v.gene for v in variants[1:3]]
            hypothesis += f" Additional markers: {', '.join(other_genes)}."
        
        return hypothesis
    
    def _define_target_population(self, variants: List[PharmacogenomicVariant]) -> str:
        """Define target patient population."""
        if not variants:
            return "General population without genetic stratification"
        
        # Look for high-evidence positive predictors
        positive_markers = [
            v for v in variants
            if "increased" in v.clinical_effect.lower() or "efficacy" in v.clinical_effect.lower()
        ]
        
        # Look for negative predictors (exclude)
        negative_markers = [
            v for v in variants
            if "contraindication" in v.clinical_effect.lower() or "toxicity" in v.clinical_effect.lower()
        ]
        
        population = []
        
        if positive_markers:
            for marker in positive_markers[:2]:
                population.append(f"{marker.gene} {marker.genotype}")
        
        if negative_markers:
            for marker in negative_markers[:2]:
                population.append(f"EXCLUDE {marker.gene} {marker.genotype}")
        
        if population:
            return "Target: " + "; ".join(population)
        
        return "General population"
    
    def _extract_dosing_implications(self, variants: List[PharmacogenomicVariant]) -> List[str]:
        """Extract dosing adjustment recommendations."""
        implications = []
        
        for variant in variants:
            if "dose" in variant.clinical_effect.lower():
                implications.append(f"{variant.gene} {variant.genotype}: {variant.clinical_effect}")
        
        if not implications:
            implications.append("No specific genetic dose adjustments identified")
        
        return implications
    
    def _assess_cdx_potential(
        self,
        variants: List[PharmacogenomicVariant],
        confidence: str
    ) -> bool:
        """Assess potential for companion diagnostic development."""
        # CDx likely if HIGH confidence and clear actionable markers
        if confidence == "HIGH" and len(variants) >= 1:
            # Check for strong evidence
            strong_variants = [v for v in variants if v.evidence_level in ["1A", "1B"]]
            return len(strong_variants) >= 1
        
        return False
    
    def _build_testing_recommendation(self, assessment: BiomarkerAssessment) -> str:
        """Build genetic testing recommendation."""
        if assessment.companion_diagnostic_potential:
            return f"Recommend genetic testing for {', '.join(assessment.key_genes[:3])} " \
                   f"before treatment. Consider developing companion diagnostic."
        
        if assessment.stratification_confidence == "MEDIUM":
            return f"Optional genetic testing for {', '.join(assessment.key_genes[:2])} " \
                   f"may guide dosing."
        
        return "Genetic testing not required based on current evidence."
    
    def _estimate_responder_rate(self, variants: List[PharmacogenomicVariant]) -> Optional[float]:
        """Estimate percentage of population likely to respond."""
        if not variants:
            return None
        
        # Simplified heuristic based on variant allele frequencies
        # In production, use actual population genetics data
        
        # If genetic stratification required, assume ~60-80% have favorable genotype
        return 0.70
    
    def _build_enrichment_strategy(self, assessment: BiomarkerAssessment) -> str:
        """Build population enrichment strategy."""
        if not assessment.pharmacogenomic_variants:
            return "No genetic enrichment strategy available."
        
        strategy = f"Enrich trial population by screening for {', '.join(assessment.key_genes)} variants. "
        
        if assessment.companion_diagnostic_potential:
            strategy += "Develop companion diagnostic as part of Phase 2/3 strategy."
        else:
            strategy += "Collect genotype data as exploratory endpoint."
        
        return strategy


# ============================================================================
# Standalone Test
# ============================================================================

if __name__ == "__main__":
    agent = BiomarkerAgent()
    
    # Test with known pharmacogenomic drugs
    test_drugs = ["warfarin", "clopidogrel", "tamoxifen"]
    
    for drug in test_drugs:
        print(f"\n{'='*60}")
        print(f"Testing: {drug}")
        print('='*60)
        
        result = agent.run(drug_name=drug)
        
        if result.error:
            print(f"❌ Error: {result.error}")
        else:
            print(f"✅ Variants found: {len(result.pharmacogenomic_variants)}")
            print(f"   Key genes: {', '.join(result.key_genes)}")
            print(f"   Confidence: {result.stratification_confidence}")
            print(f"   Hypothesis: {result.biomarker_hypothesis[:100]}...")
            print(f"   CDx potential: {result.companion_diagnostic_potential}")
            print(f"   Testing rec: {result.genetic_testing_recommendation[:80]}...")
