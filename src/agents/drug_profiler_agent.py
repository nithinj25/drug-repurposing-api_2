"""
Drug Profiler Agent - Phase 1, Agent 1

Purpose: Query ChEMBL API to obtain comprehensive drug profile including
ChEMBL ID, synonyms, known targets, approved indications, mechanism of action,
and drug class.

This is the first agent in the 2-phase discovery pipeline.
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
class DrugProfile:
    """Complete drug profile from ChEMBL"""
    drug_name: str
    chembl_id: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    known_targets: List[Dict[str, Any]] = field(default_factory=list)
    approved_indications: List[str] = field(default_factory=list)
    mechanism_of_action: Optional[str] = None
    drug_class: Optional[str] = None
    molecular_weight: Optional[float] = None
    max_phase: Optional[int] = None  # Highest clinical phase reached
    smiles: Optional[str] = None
    inchi_key: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# Drug Profiler Agent
# ============================================================================

class DrugProfilerAgent:
    """
    Phase 1, Agent 1: Drug Profile Discovery
    
    Queries ChEMBL API to retrieve comprehensive drug information.
    """
    
    # Knowledge base: Local fallback targets for common drugs when ChEMBL API fails
    # Format: normalized_drug_name → list of target gene symbols
    _drug_targets_kb = {
        'sildenafil': [
            {'target_name': 'PDE5A', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
            {'target_name': 'PDE6', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
            {'target_name': 'PDE11A', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
        ],
        'aspirin': [
            {'target_name': 'PTGS1', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
            {'target_name': 'PTGS2', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
        ],
        'metformin': [
            {'target_name': 'PRKAA1', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'ACTIVATOR'},
            {'target_name': 'PRKAA2', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'ACTIVATOR'},
        ],
        'ibuprofen': [
            {'target_name': 'PTGS1', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
            {'target_name': 'PTGS2', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
        ],
        'atorvastatin': [
            {'target_name': 'HMGCR', 'target_type': 'PROTEIN', 'organism': 'Homo sapiens', 'action_type': 'INHIBITOR'},
        ],
    }
    
    # Knowledge base: Approved indications
    _approved_indications_kb = {
        'sildenafil': ['erectile dysfunction', 'pulmonary hypertension'],
        'aspirin': ['pain', 'fever', 'cardiovascular disease', 'stroke prevention'],
        'metformin': ['type 2 diabetes', 'prediabetes'],
        'ibuprofen': ['pain', 'fever', 'inflammation'],
        'atorvastatin': ['cardiovascular disease', 'hyperlipidemia', 'dyslipidemia'],
    }
    
    def __init__(self):
        self.chembl_base_url = "https://www.ebi.ac.uk/chembl/api/data"
        self.timeout = 30
        logger.info("DrugProfilerAgent initialized (ChEMBL API + fallback KB)")
    
    def run(self, drug_name: str) -> DrugProfile:
        """
        Main entry point: get complete drug profile.
        
        Args:
            drug_name: Name of drug to profile
            
        Returns:
            DrugProfile with all available information
        """
        logger.info(f"Profiling drug: {drug_name}")
        
        # Store drug name for use in fallback knowledge base methods
        self.current_drug_name = drug_name
        
        profile = DrugProfile(drug_name=drug_name)
        
        try:
            # Step 1: Search for drug in ChEMBL
            chembl_id, synonyms = self._search_drug(drug_name)
            
            if not chembl_id:
                profile.error = f"Drug '{drug_name}' not found in ChEMBL"
                logger.warning(profile.error)
                return profile
            
            profile.chembl_id = chembl_id
            profile.synonyms = synonyms
            
            # Step 2: Get molecule details
            molecule_data = self._get_molecule_details(chembl_id)
            if molecule_data:
                profile.molecular_weight = molecule_data.get('molecule_properties', {}).get('mw_freebase')
                profile.max_phase = molecule_data.get('max_phase')
                profile.smiles = molecule_data.get('molecule_structures', {}).get('canonical_smiles')
                profile.inchi_key = molecule_data.get('molecule_structures', {}).get('standard_inchi_key')
            
            # Step 3: Get drug targets
            profile.known_targets = self._get_drug_targets(chembl_id)
            
            # Step 4: Get approved indications
            profile.approved_indications = self._get_approved_indications(chembl_id)
            
            # Step 5: Get mechanism of action
            profile.mechanism_of_action = self._get_mechanism(chembl_id)
            
            # Step 6: Get drug class/hierarchy
            profile.drug_class = self._get_drug_class(chembl_id)
            
            logger.info(f"Drug profile complete: {len(profile.known_targets)} targets, "
                       f"{len(profile.approved_indications)} indications")
            
        except Exception as e:
            profile.error = f"Error profiling drug: {str(e)}"
            logger.error(profile.error, exc_info=True)
        
        return profile
    
    # ========================================================================
    # ChEMBL API Methods
    # ========================================================================
    
    def _search_drug(self, drug_name: str) -> tuple[Optional[str], List[str]]:
        """
        Search ChEMBL for drug by name.
        
        Returns:
            (chembl_id, list_of_synonyms)
        """
        try:
            url = f"{self.chembl_base_url}/molecule/search"
            params = {
                'q': drug_name,
                'format': 'json'
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            molecules = data.get('molecules', [])
            
            if not molecules:
                return None, []
            
            # Pick the best match (first result is usually most relevant)
            best_match = molecules[0]
            chembl_id = best_match.get('molecule_chembl_id')
            
            # Get synonyms from pref_name and synonyms fields
            synonyms = []
            if best_match.get('pref_name'):
                synonyms.append(best_match['pref_name'])
            if best_match.get('molecule_synonyms'):
                for syn in best_match['molecule_synonyms']:
                    if syn.get('molecule_synonym'):
                        synonyms.append(syn['molecule_synonym'])
            
            # Remove duplicates and original name
            synonyms = list(set(synonyms))
            if drug_name.lower() in [s.lower() for s in synonyms]:
                synonyms = [s for s in synonyms if s.lower() != drug_name.lower()]
            
            logger.info(f"Found ChEMBL ID: {chembl_id}, {len(synonyms)} synonyms")
            return chembl_id, synonyms
            
        except Exception as e:
            logger.error(f"ChEMBL search failed: {e}")
            return None, []
    
    def _get_molecule_details(self, chembl_id: str) -> Optional[Dict]:
        """Get detailed molecule information."""
        try:
            url = f"{self.chembl_base_url}/molecule/{chembl_id}"
            params = {'format': 'json'}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get molecule details: {e}")
            return None
    
    def _get_drug_targets(self, chembl_id: str) -> List[Dict[str, Any]]:
        """
        Get all known targets for this drug from ChEMBL.
        Falls back to knowledge base if API returns empty.
        
        Returns list of dicts with:
        - target_chembl_id
        - target_name
        - target_type (PROTEIN, ENZYME, etc.)
        - organism
        - action_type (INHIBITOR, AGONIST, etc.)
        - confidence_score
        """
        try:
            url = f"{self.chembl_base_url}/mechanism"
            params = {
                'molecule_chembl_id': chembl_id,
                'format': 'json',
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            mechanisms = data.get('mechanisms', [])
            
            targets = []
            seen_target_ids = set()
            
            for mech in mechanisms:
                target_id = mech.get('target_chembl_id')
                
                if not target_id or target_id in seen_target_ids:
                    continue
                
                seen_target_ids.add(target_id)
                
                # Get target details
                target_data = self._get_target_details(target_id)
                
                gene_symbol = self._extract_gene_symbol(target_data)

                target_info = {
                    'target_chembl_id': target_id,
                    'target_name': gene_symbol or mech.get('target_name') or target_data.get('pref_name'),
                    'target_name_raw': mech.get('target_name') or target_data.get('pref_name'),
                    'target_gene_symbol': gene_symbol,
                    'target_type': target_data.get('target_type'),
                    'organism': target_data.get('organism'),
                    'action_type': mech.get('action_type'),
                    'mechanism_of_action': mech.get('mechanism_of_action'),
                }
                
                targets.append(target_info)
            
            # If API returned results, use them
            if targets:
                logger.info(f"Found {len(targets)} targets from ChEMBL API for {chembl_id}")
                return targets
            
            # API returned empty - try fallback knowledge base
            logger.warning(f"ChEMBL API returned 0 targets for {chembl_id}, checking knowledge base...")
            
        except Exception as e:
            logger.warning(f"Failed to get drug targets from API: {e}")
        
        # Fallback: Check knowledge base
        targets_kb = self._get_targets_from_knowledge_base()
        if targets_kb:
            logger.info(f"✅ Using {len(targets_kb)} targets from knowledge base")
            return targets_kb
        
        logger.error(f"No targets found for {chembl_id} in both API and knowledge base")
        return []

    def _extract_gene_symbol(self, target_data: Dict[str, Any]) -> Optional[str]:
        """Extract preferred gene symbol from ChEMBL target payload."""
        try:
            components = target_data.get('target_components', [])
            for component in components:
                synonyms = component.get('target_component_synonyms', [])
                for syn in synonyms:
                    if syn.get('syn_type') == 'GENE_SYMBOL' and syn.get('component_synonym'):
                        return syn['component_synonym']

            for component in components:
                synonyms = component.get('target_component_synonyms', [])
                for syn in synonyms:
                    if syn.get('syn_type') == 'GENE_SYMBOL_OTHER' and syn.get('component_synonym'):
                        return syn['component_synonym']
        except Exception:
            return None

        return None
    
    def _get_targets_from_knowledge_base(self) -> List[Dict[str, Any]]:
        """
        Get targets from local knowledge base using stored drug name.
        
        This is called when ChEMBL API returns empty results.
        Assumes self.current_drug_name is set from the input.
        """
        if not hasattr(self, 'current_drug_name'):
            return []
        
        drug_normalized = self.current_drug_name.lower().strip()
        
        if drug_normalized in self._drug_targets_kb:
            kb_targets = self._drug_targets_kb[drug_normalized]
            logger.info(f"✅ Retrieved {len(kb_targets)} targets from KB for {self.current_drug_name}")
            return kb_targets
        
        return []
    
    def _get_target_details(self, target_chembl_id: str) -> Dict:
        """Get detailed target information."""
        try:
            url = f"{self.chembl_base_url}/target/{target_chembl_id}"
            params = {'format': 'json'}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.debug(f"Failed to get target details for {target_chembl_id}: {e}")
            return {}
    
    def _get_approved_indications(self, chembl_id: str) -> List[str]:
        """
        Get all approved indications for this drug.
        Falls back to knowledge base if API returns empty.
        """
        try:
            url = f"{self.chembl_base_url}/drug_indication"
            params = {
                'molecule_chembl_id': chembl_id,
                'format': 'json',
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            indications_data = data.get('drug_indications', [])
            
            # Extract unique APPROVED indication names only.
            # ChEMBL drug_indication includes non-approved development phases as well,
            # so we restrict to max_phase_for_ind >= 4.0 to avoid over-filtering.
            indications = []
            seen = set()
            
            for ind in indications_data:
                phase_raw = ind.get('max_phase_for_ind')
                try:
                    phase_val = float(phase_raw) if phase_raw is not None else 0.0
                except (TypeError, ValueError):
                    phase_val = 0.0

                if phase_val < 4.0:
                    continue

                indication = ind.get('mesh_heading') or ind.get('efo_term')
                if indication and indication not in seen:
                    indications.append(indication)
                    seen.add(indication)
            
            # If API returned results, use them
            if indications:
                logger.info(
                    f"Found {len(indications)} approved indications from API "
                    f"(from {len(indications_data)} total indication records)"
                )
                return indications
            
            # API returned empty - try knowledge base
            logger.warning(f"ChEMBL API returned 0 indications for {chembl_id}, checking knowledge base...")
            
        except Exception as e:
            logger.warning(f"Failed to get indications from API: {e}")
        
        # Fallback: Check knowledge base
        indications_kb = self._get_indications_from_knowledge_base()
        if indications_kb:
            logger.info(f"✅ Using {len(indications_kb)} approved indications from knowledge base")
            return indications_kb
        
        logger.warning(f"No indications found for {chembl_id} in both API and knowledge base")
        return []
    
    def _get_indications_from_knowledge_base(self) -> List[str]:
        """
        Get approved indications from local knowledge base.
        
        This is called when ChEMBL API returns empty results.
        Assumes self.current_drug_name is set from the input.
        """
        if not hasattr(self, 'current_drug_name'):
            return []
        
        drug_normalized = self.current_drug_name.lower().strip()
        
        if drug_normalized in self._approved_indications_kb:
            kb_indications = self._approved_indications_kb[drug_normalized]
            logger.info(f"✅ Retrieved {len(kb_indications)} indications from KB for {self.current_drug_name}")
            return kb_indications
        
        return []
    
    def _get_mechanism(self, chembl_id: str) -> Optional[str]:
        """
        Get primary mechanism of action description.
        """
        try:
            url = f"{self.chembl_base_url}/mechanism"
            params = {
                'molecule_chembl_id': chembl_id,
                'format': 'json',
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            mechanisms = data.get('mechanisms', [])
            
            if mechanisms:
                return mechanisms[0].get('mechanism_of_action')
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get mechanism: {e}")
            return None
    
    def _get_drug_class(self, chembl_id: str) -> Optional[str]:
        """
        Get drug class/hierarchy information.
        """
        try:
            # Get molecule hierarchy
            molecule_data = self._get_molecule_details(chembl_id)
            
            if not molecule_data:
                return None
            
            # Try to get from molecule hierarchy
            hierarchy = molecule_data.get('molecule_hierarchy')
            if hierarchy:
                parent_chembl = hierarchy.get('parent_chembl_id')
                if parent_chembl and parent_chembl != chembl_id:
                    parent_data = self._get_molecule_details(parent_chembl)
                    if parent_data:
                        return parent_data.get('pref_name')
            
            # Fallback: use therapeutic flag or first phase to classify
            therapeutic_flag = molecule_data.get('therapeutic_flag')
            if therapeutic_flag:
                max_phase = molecule_data.get('max_phase', 0)
                if max_phase >= 4:
                    return "Approved Drug"
                elif max_phase >= 2:
                    return "Clinical Candidate"
                else:
                    return "Investigational Drug"
            
            return "Small Molecule"
            
        except Exception as e:
            logger.error(f"Failed to get drug class: {e}")
            return None


# ============================================================================
# Standalone Test
# ============================================================================

if __name__ == "__main__":
    # Test the agent
    agent = DrugProfilerAgent()
    
    test_drugs = ["aspirin", "metformin", "sildenafil"]
    
    for drug in test_drugs:
        print(f"\n{'='*60}")
        print(f"Testing: {drug}")
        print('='*60)
        
        profile = agent.run(drug)
        
        if profile.error:
            print(f"❌ Error: {profile.error}")
        else:
            print(f"✅ ChEMBL ID: {profile.chembl_id}")
            print(f"   Synonyms: {', '.join(profile.synonyms[:3])}")
            print(f"   Targets: {len(profile.known_targets)}")
            print(f"   Approved Indications: {len(profile.approved_indications)}")
            print(f"   Mechanism: {profile.mechanism_of_action}")
            print(f"   Drug Class: {profile.drug_class}")
            print(f"   Max Phase: {profile.max_phase}")
