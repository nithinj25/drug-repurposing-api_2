"""
Quick Integration Guide: Add Caching to Agents

This script shows example code snippets for integrating caching
into each agent to reduce API calls by 60-80%.

Run this after implementing to test caching effectiveness.
"""

# ============================================================================
# INTEGRATION EXAMPLES
# ============================================================================

# -----------------------------------------------------------------------------
# 1. Drug Profiler Agent (ChEMBL caching)
# -----------------------------------------------------------------------------
# File: src/agents/drug_profiler_agent.py
# Location: Inside run() method, before ChEMBL API call (~line 90)

"""
from src.utils import get_cached, set_cached

def run(self, drug_name: str) -> DrugProfile:
    logger.info(f"Profiling drug: {drug_name}")
    
    # ✓ CHECK CACHE FIRST
    cache_key = drug_name.lower()
    cached_profile = get_cached("chembl", cache_key)
    if cached_profile:
        logger.info(f"✓ Using cached ChEMBL profile for: {drug_name}")
        return DrugProfile(**cached_profile)
    
    # Original code: fetch from ChEMBL...
    drug_profile = self._fetch_drug_from_chembl(drug_name)
    
    # ✓ CACHE THE RESULT
    if drug_profile:
        from dataclasses import asdict
        set_cached("chembl", cache_key, asdict(drug_profile))
        logger.info(f"✓ Cached ChEMBL profile for: {drug_name}")
    
    return drug_profile
"""

# -----------------------------------------------------------------------------
# 2. Literature Agent (PubMed caching)
# -----------------------------------------------------------------------------
# File: src/agents/literature_agent.py
# Location: Inside search_pubmed() method (~line 225)

"""
from src.utils import get_cached, set_cached
import hashlib

def search_pubmed(self, drug: str, indication: str, max_results: int = 10):
    # ✓ CHECK CACHE FIRST
    cache_key = f"{drug}:{indication}:top{max_results}"
    cached_papers = get_cached("pubmed", cache_key)
    if cached_papers:
        logger.info(f"✓ Using cached PubMed results ({len(cached_papers)} papers)")
        return cached_papers
    
    # Original code: search PubMed...
    results = self._fetch_from_pubmed(drug, indication, max_results)
    
    # ✓ CACHE THE RESULTS
    if results:
        set_cached("pubmed", cache_key, results)
        logger.info(f"✓ Cached {len(results)} PubMed papers")
    
    return results
"""

# -----------------------------------------------------------------------------
# 3. Clinical Agent (ClinicalTrials.gov caching)
# -----------------------------------------------------------------------------
# File: src/agents/clinical_agent.py
# Location: Inside fetch_trials() method (~line 205)

"""
from src.utils import get_cached, set_cached

def fetch_trials(self, drug_name: str, indication: str):
    # ✓ CHECK CACHE FIRST
    cache_key = f"{drug_name}:{indication}"
    cached_trials = get_cached("clinicaltrials", cache_key)
    if cached_trials:
        logger.info(f"✓ Using cached clinical trials ({len(cached_trials)} trials)")
        return cached_trials
    
    # Original code: fetch from ClinicalTrials.gov...
    trials = self._fetch_from_api(drug_name, indication)
    
    # ✓ CACHE THE RESULTS
    if trials:
        set_cached("clinicaltrials", cache_key, trials)
        logger.info(f"✓ Cached {len(trials)} clinical trials")
    
    return trials
"""

# -----------------------------------------------------------------------------
# 4. Molecular Agent (Open Targets gene caching)
# -----------------------------------------------------------------------------
# File: src/agents/molecular_agent.py
# Location: Inside _get_disease_genes_with_scores() method (~line 305)

"""
from src.utils import get_cached, set_cached

def _get_disease_genes_with_scores(self, indication: str):
    # Already has EFO cache, add gene-disease cache too
    
    efo_id = self.get_disease_efo_id(indication)
    if not efo_id:
        return [], {}, None
    
    # ✓ CHECK CACHE FOR GENE-DISEASE ASSOCIATIONS
    cache_key = f"{efo_id}:genes"
    cached_genes = get_cached("open_targets", cache_key)
    if cached_genes:
        logger.info(f"✓ Using cached genes for {indication} ({len(cached_genes['genes'])} genes)")
        return cached_genes['genes'], cached_genes['scores'], efo_id
    
    # Original code: fetch from Open Targets...
    genes, scores = self._fetch_genes_from_open_targets(efo_id)
    
    # ✓ CACHE THE RESULTS
    if genes:
        set_cached("open_targets", cache_key, {'genes': genes, 'scores': scores})
        logger.info(f"✓ Cached {len(genes)} genes for {indication}")
    
    return genes, scores, efo_id
"""

# -----------------------------------------------------------------------------
# 5. Safety Agent (DailyMed caching)
# -----------------------------------------------------------------------------
# File: src/agents/safety_agent.py
# Location: Inside fetch_adverse_events() method (~line 625)

"""
from src.utils import get_cached, set_cached

def fetch_adverse_events(self, drug_name: str):
    # ✓ CHECK CACHE FIRST
    cache_key = drug_name.lower()
    cached_events = get_cached("dailymed", cache_key)
    if cached_events:
        logger.info(f"✓ Using cached adverse events for {drug_name}")
        return cached_events
    
    # Original code: fetch from DailyMed...
    adverse_events = self._fetch_from_dailymed(drug_name)
    
    # ✓ CACHE THE RESULTS
    if adverse_events:
        set_cached("dailymed", cache_key, adverse_events)
        logger.info(f"✓ Cached adverse events for {drug_name}")
    
    return adverse_events
"""

# ============================================================================
# RATE LIMITER INTEGRATION
# ============================================================================

# -----------------------------------------------------------------------------
# Add rate limiting to API calls using decorator
# -----------------------------------------------------------------------------

"""
# Example: PubMed search in literature_agent.py

from src.utils import rate_limited_request

class LiteratureAgent:
    
    @rate_limited_request('pubmed', max_retries=3)
    def _fetch_pubmed_papers(self, query: str):
        '''Rate-limited PubMed search with auto-retry'''
        response = requests.get(
            f"{self.base_url}/esearch.fcgi",
            params=params,
            timeout=20
        )
        response.raise_for_status()
        return response.json()
"""

"""
# Example: ChEMBL search in drug_profiler_agent.py

from src.utils import rate_limited_request

class DrugProfilerAgent:
    
    @rate_limited_request('chembl', max_retries=3)
    def _fetch_drug_from_chembl(self, drug_name: str):
        '''Rate-limited ChEMBL search with auto-retry'''
        response = requests.get(
            f"{self.base_url}/molecule.json",
            params={"pref_name__iexact": drug_name},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
"""

"""
# Example: ClinicalTrials.gov in clinical_agent.py

from src.utils import rate_limited_request

class ClinicalAgent:
    
    @rate_limited_request('clinicaltrials', max_retries=3)
    def _fetch_trials_from_api(self, params: dict):
        '''Rate-limited clinical trials search with auto-retry'''
        response = requests.get(
            f"{self.base_url}/studies",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
"""

# ============================================================================
# HOW TO TEST CACHING
# ============================================================================

"""
# 1. Run discovery twice and compare API calls:

# First run (cold cache):
POST /discover {"drug_name": "sildenafil"}
# Expected: 150-200 API calls, 6+ minutes

# Second run (warm cache):
POST /discover {"drug_name": "sildenafil"}
# Expected: 30-50 API calls, 2-3 minutes

# 2. Check cache statistics:
from src.utils import get_cache_stats
print(get_cache_stats())
# Output: {'chembl': 1, 'pubmed': 3, 'clinicaltrials': 3, 'open_targets': 10, 'total': 17}

# 3. View cache files:
ls cache_data/
# chembl/
# pubmed/
# clinicaltrials/
# open_targets/
# dailymed/

# 4. Clear cache if needed:
from src.utils import clear_cache
clear_cache()  # Clear all
clear_cache('chembl')  # Clear specific source
"""

# ============================================================================
# NEXT STEPS
# ============================================================================
print("""
✅ IMPLEMENTATION CHECKLIST:

1. [ ] Add caching to drug_profiler_agent.py (ChEMBL)
2. [ ] Add caching to literature_agent.py (PubMed)
3. [ ] Add caching to clinical_agent.py (ClinicalTrials)
4. [ ] Add caching to molecular_agent.py (Open Targets genes)
5. [ ] Add caching to safety_agent.py (DailyMed)

6. [ ] Add rate limiting decorator to all API calls
7. [ ] Test with sildenafil (cold cache vs warm cache)
8. [ ] Run pre-cache script for hackathon demo
9. [ ] Monitor cache hit rates during demo

EXPECTED RESULTS:
- First run: ~6 minutes, 150-200 API calls
- Second run: ~2-3 minutes, 30-50 API calls
- Cache hit rate: 70-80%
- Zero 429 rate limit errors

HACKATHON PREP:
Run precache script 30 minutes before demo to warm cache!
""")
