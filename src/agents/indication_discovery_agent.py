"""
Indication Discovery Agent - Phase 1, Agent 2

Purpose: Given a drug profile with known targets, query Open Targets GraphQL API
to find diseases associated with those targets. Rank diseases by mechanistic score
(average Open Targets association score + bonus for multiple linking targets).
Filter out diseases the drug is already approved for.

Returns top 5 ranked disease candidates for repurposing evaluation.
"""

import os
import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from collections import defaultdict

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
class DiseaseCandidate:
    """A ranked disease candidate for repurposing"""
    disease_name: str
    disease_id: str  # EFO or similar ID
    mechanistic_score: float  # 0.0-1.0, higher is better
    linking_targets: List[str]  # Target names that link drug to disease
    target_scores: Dict[str, float]  # target_name -> Open Targets score
    therapeutic_area: Optional[str] = None
    confidence: str = "MEDIUM"  # HIGH/MEDIUM/LOW
    evidence_count: int = 0
    rank: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DiscoveryResult:
    """Complete indication discovery output"""
    drug_name: str
    drug_chembl_id: Optional[str]
    targets_queried: List[str]
    candidates: List[DiseaseCandidate]
    approved_indications_filtered: List[str]
    total_diseases_found: int
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['candidates'] = [c.to_dict() for c in self.candidates]
        return data


# ============================================================================
# Indication Discovery Agent
# ============================================================================

class IndicationDiscoveryAgent:
    """
    Phase 1, Agent 2: Disease Candidate Discovery
    
    Uses Open Targets API to find diseases associated with drug targets.
    """
    
    def __init__(self):
        self.opentargets_url = os.getenv(
            "OPENTARGETS_API_URL",
            "https://api.platform.opentargets.org/api/v4/graphql"
        )
        self.timeout = 30
        self.discovery_fetch_size = 20  # Fetch this many diseases per target
        self.post_filter_target = 10  # Evaluate this many after approved-filtering
        self.min_mechanistic_score = 0.3
        self.min_score_threshold = 0.1  # Minimum Open Targets association score
        logger.info("IndicationDiscoveryAgent initialized (Open Targets GraphQL)")
    
    def run(self, drug_profile: Dict[str, Any]) -> DiscoveryResult:
        """
        Main entry point: discover disease candidates.
        
        Args:
            drug_profile: Output from DrugProfilerAgent
            
        Returns:
            DiscoveryResult with top 5 ranked disease candidates
        """
        drug_name = drug_profile.get('drug_name', 'unknown')
        logger.info(f"Discovering indications for: {drug_name}")
        
        result = DiscoveryResult(
            drug_name=drug_name,
            drug_chembl_id=drug_profile.get('chembl_id'),
            targets_queried=[],
            candidates=[],
            approved_indications_filtered=drug_profile.get('approved_indications', []),
            total_diseases_found=0
        )
        
        try:
            # Extract target names from drug profile
            known_targets = drug_profile.get('known_targets', [])
            
            if not known_targets:
                result.error = "No known targets found in drug profile"
                logger.warning(result.error)
                return result
            
            # Step 1: For each target, query Open Targets for associated diseases
            drug_target_symbols = {
                (target_info.get('target_gene_symbol') or target_info.get('target_name') or target_info.get('target_name_raw') or '').upper()
                for target_info in known_targets
                if (target_info.get('target_gene_symbol') or target_info.get('target_name') or target_info.get('target_name_raw'))
            }

            disease_scores = defaultdict(lambda: {
                'scores': [],
                'linking_targets': [],
                'target_scores': {},
                'disease_name': None,
                'therapeutic_area': None,
                'therapeutic_areas': [],
                'all_disease_rows': [],
                'evidence_count': 0
            })
            disease_rows_cache: Dict[str, List[Dict[str, Any]]] = {}
            
            for target_info in known_targets:
                target_name = (
                    target_info.get('target_gene_symbol')
                    or target_info.get('target_name')
                    or target_info.get('target_name_raw')
                )
                
                if not target_name:
                    continue
                
                result.targets_queried.append(target_name)
                
                # Query Open Targets for this target's disease associations
                diseases = self._get_target_disease_associations(target_name)
                
                for disease in diseases:
                    disease_id = disease['disease_id']
                    disease_name = disease['disease_name']
                    score = disease['score']
                    therapeutic_area = disease.get('therapeutic_area')
                    therapeutic_areas = disease.get('therapeutic_areas', [])
                    
                    disease_scores[disease_id]['scores'].append(score)
                    disease_scores[disease_id]['linking_targets'].append(target_name)
                    disease_scores[disease_id]['target_scores'][target_name] = score
                    disease_scores[disease_id]['disease_name'] = disease_name
                    disease_scores[disease_id]['therapeutic_area'] = therapeutic_area
                    disease_scores[disease_id]['therapeutic_areas'] = therapeutic_areas
                    disease_scores[disease_id]['evidence_count'] += 1

                    if disease_id not in disease_rows_cache:
                        disease_rows_cache[disease_id] = self._get_disease_target_rows(disease_id)
                    disease_scores[disease_id]['all_disease_rows'] = disease_rows_cache[disease_id]
            
            result.total_diseases_found = len(disease_scores)
            
            # Step 2: Compute mechanistic score for each disease
            candidates = []
            
            for disease_id, data in disease_scores.items():
                base_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0.0
                mechanistic_score = self.compute_candidate_score(
                    disease_data={"open_targets_score": base_score},
                    drug_targets=drug_target_symbols,
                    all_disease_rows=data.get('all_disease_rows', [])
                )
                
                # Assign confidence based on score and evidence count
                if mechanistic_score >= 0.6 and len(data['linking_targets']) >= 2:
                    confidence = "HIGH"
                elif mechanistic_score >= 0.3:
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"
                
                candidate = DiseaseCandidate(
                    disease_name=data['disease_name'],
                    disease_id=disease_id,
                    mechanistic_score=mechanistic_score,
                    linking_targets=list(dict.fromkeys(data['linking_targets'])),
                    target_scores=data['target_scores'],
                    therapeutic_area=self.extract_therapeutic_area(data.get('therapeutic_areas', [])),
                    confidence=confidence,
                    evidence_count=data['evidence_count']
                )
                
                candidates.append(candidate)
            
            # Step 3: Filter out approved indications (with synonym expansion)
            candidates = self.filter_approved_indications(candidates, result.approved_indications_filtered)

            # Step 4: Keep only mechanistically relevant candidates
            candidates = [c for c in candidates if c.mechanistic_score >= self.min_mechanistic_score]
            
            # Step 5: Sort by mechanistic_score descending
            candidates.sort(key=lambda c: c.mechanistic_score, reverse=True)
            
            # Step 6: Take post-filter top N and assign ranks
            top_candidates = candidates[:self.post_filter_target]
            for rank, candidate in enumerate(top_candidates, start=1):
                candidate.rank = rank
            
            result.candidates = top_candidates
            
            logger.info(
                f"Found {len(top_candidates)} top candidates "
                f"(filtered approved indications; min mechanistic score: {self.min_mechanistic_score})"
            )
            
        except Exception as e:
            result.error = f"Error discovering indications: {str(e)}"
            logger.error(result.error, exc_info=True)
        
        return result
    
    # ========================================================================
    # Open Targets GraphQL Methods
    # ========================================================================
    
    def _get_target_disease_associations(self, target_name: str) -> List[Dict]:
        """
        Query Open Targets for diseases associated with a target.
        
        Args:
            target_name: Human-readable target name (e.g., "COX1", "PTGS1")
            
        Returns:
            List of dicts with disease_id, disease_name, score, therapeutic_area
        """
        try:
            # Step 1: Search for target by name to get Ensembl ID
            target_id = self._search_target_id(target_name)
            
            if not target_id:
                logger.debug(f"Target '{target_name}' not found in Open Targets")
                return []
            
            # Step 2: Query target-disease associations
            query = """
            query targetDiseaseAssociations($targetId: String!, $size: Int!) {
              target(ensemblId: $targetId) {
                associatedDiseases(page: {index: 0, size: $size}) {
                  rows {
                    disease {
                      id
                      name
                      therapeuticAreas {
                        id
                        name
                      }
                    }
                    score
                    datatypeScores {
                      id
                      score
                    }
                  }
                }
              }
            }
            """
            
            variables = {
                "targetId": target_id,
                "size": self.discovery_fetch_size
            }
            
            response = requests.post(
                self.opentargets_url,
                json={'query': query, 'variables': variables},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"Open Targets GraphQL errors: {data['errors']}")
                return []
            
            target_data = data.get('data', {}).get('target')
            if not target_data:
                return []
            
            associations = target_data.get('associatedDiseases', {}).get('rows', [])
            
            diseases = []
            for assoc in associations:
                score = assoc.get('score', 0.0)
                
                if score < self.min_score_threshold:
                    continue
                
                disease = assoc.get('disease', {})
                disease_id = disease.get('id')
                disease_name = disease.get('name')
                
                if not disease_id or not disease_name:
                    continue
                
                therapeutic_areas = disease.get('therapeuticAreas', [])
                therapeutic_area = self.extract_therapeutic_area(therapeutic_areas)
                
                diseases.append({
                    'disease_id': disease_id,
                    'disease_name': disease_name,
                    'score': score,
                    'therapeutic_area': therapeutic_area,
                    'therapeutic_areas': therapeutic_areas
                })
            
            logger.debug(f"Found {len(diseases)} diseases for target {target_name}")
            return diseases
            
        except Exception as e:
            logger.error(f"Failed to get disease associations for {target_name}: {e}")
            return []
    
    def _search_target_id(self, target_name: str) -> Optional[str]:
        """
        Search Open Targets for target by name, return Ensembl gene ID.
        
        Args:
            target_name: Gene symbol or protein name
            
        Returns:
            Ensembl gene ID (e.g., "ENSG00000095303")
        """
        try:
            query = """
            query searchTarget($queryString: String!) {
                            search(queryString: $queryString, entityNames: ["target"], page: {index: 0, size: 1}) {
                hits {
                  id
                  name
                  entity
                }
              }
            }
            """
            
            variables = {"queryString": target_name}
            
            response = requests.post(
                self.opentargets_url,
                json={'query': query, 'variables': variables},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data:
                logger.debug(f"Search errors for {target_name}: {data['errors']}")
                return None
            
            hits = data.get('data', {}).get('search', {}).get('hits', [])
            
            if not hits:
                return None
            
            # Return first match (most relevant)
            target_id = hits[0].get('id')
            logger.debug(f"Mapped {target_name} -> {target_id}")
            
            return target_id
            
        except Exception as e:
            logger.debug(f"Failed to search for target {target_name}: {e}")
            return None
    
    def _get_disease_target_rows(self, disease_id: str) -> List[Dict[str, Any]]:
        """Get top associated targets for a disease to compute rank bonus and multi-target bonus."""
        query = """
        query($efoId: String!) {
          disease(efoId: $efoId) {
            associatedTargets(page: {index: 0, size: 50}) {
              rows {
                target {
                  approvedSymbol
                  id
                }
                score
              }
            }
          }
        }
        """
        try:
            response = requests.post(
                self.opentargets_url,
                json={"query": query, "variables": {"efoId": disease_id}},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                return []
            return payload.get("data", {}).get("disease", {}).get("associatedTargets", {}).get("rows", []) or []
        except Exception:
            return []

    def compute_candidate_score(
        self,
        disease_data: Dict[str, Any],
        drug_targets: set,
        all_disease_rows: List[Dict[str, Any]],
    ) -> float:
        """Compute candidate score with base + rank bonus + multi-target bonus."""
        base_score = float(disease_data.get("open_targets_score", 0.0))

        target_rank = 999
        for i, row in enumerate(all_disease_rows):
            symbol = (row.get("target", {}).get("approvedSymbol") or "").upper()
            if symbol and symbol in drug_targets:
                target_rank = i
                break

        rank_bonus = max(0.0, (10 - target_rank) * 0.02) if target_rank != 999 else 0.0

        row_symbols = {
            (row.get("target", {}).get("approvedSymbol") or "").upper()
            for row in all_disease_rows
            if row.get("target", {}).get("approvedSymbol")
        }
        multi_target_count = sum(1 for t in drug_targets if t in row_symbols)
        multi_bonus = min(max(0, multi_target_count - 1) * 0.05, 0.15)

        final_score = min(base_score + rank_bonus + multi_bonus, 1.0)
        return round(final_score, 3)

    def filter_approved_indications(
        self,
        candidates: List[DiseaseCandidate],
        approved_indications: List[str],
    ) -> List[DiseaseCandidate]:
        """Filter approved indications (and synonyms) before evaluation pipeline."""
        approved_lower = {ind.lower() for ind in approved_indications}
        synonym_map = {
            "erectile dysfunction": {"impotence", "ed", "male impotence"},
            "pulmonary arterial hypertension": {"pulmonary hypertension", "pah", "ph"},
            "hypertension, pulmonary": {"pulmonary hypertension", "pah"},
            "connective tissue diseases": {"connective tissue disease", "ctd"},
        }

        expanded_exclusions = set(approved_lower)
        for approved in approved_lower:
            for canonical, synonyms in synonym_map.items():
                if approved == canonical or approved in synonyms:
                    expanded_exclusions.update(synonyms)
                    expanded_exclusions.add(canonical)

        return [
            c for c in candidates
            if c.disease_name.lower() not in expanded_exclusions
        ]

    def extract_therapeutic_area(self, therapeutic_areas: list) -> str:
        """Extract therapeutic area with priority ordering."""
        priority = [
            "oncology", "neurology", "cardiovascular", "respiratory",
            "immunology", "endocrinology", "gastroenterology",
            "dermatology", "hematology", "infectious disease",
            "musculoskeletal", "ophthalmology", "psychiatry", "urology"
        ]

        if not therapeutic_areas:
            return "Other"

        area_names = [a.get("name", "").lower() for a in therapeutic_areas if a.get("name")]

        for p in priority:
            for name in area_names:
                if p in name:
                    return p.title()

        return therapeutic_areas[0].get("name", "Other")


# ============================================================================
# Standalone Test
# ============================================================================

if __name__ == "__main__":
    # Test the agent
    import sys
    import json
    from pathlib import Path
    
    # Import DrugProfilerAgent
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.agents.drug_profiler_agent import DrugProfilerAgent
    
    # Step 1: Get drug profile
    profiler = DrugProfilerAgent()
    drug_profile = profiler.run("aspirin")
    
    if drug_profile.error:
        print(f"❌ Failed to profile drug: {drug_profile.error}")
        sys.exit(1)
    
    # Step 2: Discover indications
    discovery_agent = IndicationDiscoveryAgent()
    result = discovery_agent.run(drug_profile.to_dict())
    
    print(f"\n{'='*60}")
    print(f"INDICATION DISCOVERY: {result.drug_name}")
    print('='*60)
    
    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Targets queried: {len(result.targets_queried)}")
        print(f"   Total diseases found: {result.total_diseases_found}")
        print(f"   Approved indications filtered: {len(result.approved_indications_filtered)}")
        print(f"\n📋 Top {len(result.candidates)} Disease Candidates:")
        
        for candidate in result.candidates:
            print(f"\n   {candidate.rank}. {candidate.disease_name} ({candidate.confidence})")
            print(f"      Score: {candidate.mechanistic_score:.3f}")
            print(f"      Linking targets: {', '.join(candidate.linking_targets[:3])}")
            print(f"      Therapeutic area: {candidate.therapeutic_area}")
