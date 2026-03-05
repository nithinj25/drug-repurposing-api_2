"""
Pre-cache Script for Hackathon Demo

This script pre-fetches and caches data for common drugs BEFORE the demo,
ensuring the hackathon presentation runs smoothly with minimal API calls.

Run 30 minutes before hackathon:
    python scripts/precache_for_hackathon.py

Expected time: 10-15 minutes
Expected cache size: ~50-100 MB
"""

import sys
import os
import time
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.drug_profiler_agent import DrugProfilerAgent
from src.agents.literature_agent import LiteratureAgent
from src.agents.clinical_agent import ClinicalAgent
from src.agents.safety_agent import SafetyAgent
from src.utils import set_cached, get_cache_stats
from dataclasses import asdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Drugs to pre-cache for demo
DEMO_DRUGS = [
    "sildenafil",  # Primary demo drug
    "metformin",   # Backup option
    "aspirin",     # Backup option
]

# Top indications to pre-cache for sildenafil
SILDENAFIL_INDICATIONS = [
    "coronary artery disease",
    "benign prostatic hyperplasia",
    "stroke",
    "heart failure",
    "raynaud disease",
]


def precache_drug_profile(drug_name: str):
    """Pre-cache ChEMBL drug profile"""
    logger.info(f"==> Caching drug profile: {drug_name}")
    
    try:
        profiler = DrugProfilerAgent()
        cache_key = drug_name.lower()
        
        # Check if already cached
        from src.utils import get_cached
        if get_cached("chembl", cache_key):
            logger.info(f"    ✓ Already cached: {drug_name}")
            return
        
        # Fetch and cache
        profile = profiler.run(drug_name)
        if profile:
            set_cached("chembl", cache_key, asdict(profile))
            logger.info(f"    ✓ Cached: {drug_name} ({len(profile.targets)} targets)")
            return profile
        else:
            logger.warning(f"    ✗ No profile found: {drug_name}")
            return None
    
    except Exception as e:
        logger.error(f"    ✗ Error caching {drug_name}: {e}")
        return None


def precache_literature(drug: str, indication: str):
    """Pre-cache PubMed literature"""
    logger.info(f"    → Caching literature: {drug} + {indication}")
    
    try:
        lit_agent = LiteratureAgent()
        cache_key = f"{drug}:{indication}:top5"
        
        from src.utils import get_cached
        if get_cached("pubmed", cache_key):
            logger.info(f"      ✓ Already cached")
            return
        
        # Fetch and cache (limit to 5 papers for speed)
        papers = lit_agent.search_pubmed(drug, indication, max_results=5)
        if papers:
            set_cached("pubmed", cache_key, papers)
            logger.info(f"      ✓ Cached {len(papers)} papers")
        
        time.sleep(1)  # Rate limit
    
    except Exception as e:
        logger.error(f"      ✗ Error: {e}")


def precache_clinical_trials(drug: str, indication: str):
    """Pre-cache ClinicalTrials.gov data"""
    logger.info(f"    → Caching clinical trials: {drug} + {indication}")
    
    try:
        clinical_agent = ClinicalAgent()
        cache_key = f"{drug}:{indication}"
        
        from src.utils import get_cached
        if get_cached("clinicaltrials", cache_key):
            logger.info(f"      ✓ Already cached")
            return
        
        # Fetch and cache
        trials = clinical_agent.fetch_trials(drug, indication)
        if trials:
            set_cached("clinicaltrials", cache_key, trials)
            logger.info(f"      ✓ Cached {len(trials)} trials")
        
        time.sleep(1)  # Rate limit
    
    except Exception as e:
        logger.error(f"      ✗ Error: {e}")


def precache_safety(drug: str):
    """Pre-cache DailyMed safety data"""
    logger.info(f"    → Caching safety data: {drug}")
    
    try:
        safety_agent = SafetyAgent()
        cache_key = drug.lower()
        
        from src.utils import get_cached
        if get_cached("dailymed", cache_key):
            logger.info(f"      ✓ Already cached")
            return
        
        # Fetch and cache
        adverse_events = safety_agent.fetch_adverse_events(drug)
        if adverse_events:
            set_cached("dailymed", cache_key, adverse_events)
            logger.info(f"      ✓ Cached adverse events")
        
        time.sleep(1)  # Rate limit
    
    except Exception as e:
        logger.error(f"      ✗ Error: {e}")


def main():
    """Main pre-caching workflow"""
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("PRE-CACHE SCRIPT FOR HACKATHON DEMO")
    logger.info("=" * 80)
    logger.info("")
    
    # Check initial cache state
    initial_stats = get_cache_stats()
    logger.info(f"Initial cache: {initial_stats}")
    logger.info("")
    
    # 1. Cache drug profiles
    logger.info("STEP 1: Caching drug profiles...")
    logger.info("-" * 80)
    for drug in DEMO_DRUGS:
        precache_drug_profile(drug)
        time.sleep(2)  # Rate limit between drugs
    
    logger.info("")
    
    # 2. Cache sildenafil indication data (primary demo)
    logger.info("STEP 2: Caching sildenafil indication data...")
    logger.info("-" * 80)
    for indication in SILDENAFIL_INDICATIONS:
        logger.info(f"  Processing: {indication}")
        
        # Cache literature
        precache_literature("sildenafil", indication)
        
        # Cache clinical trials
        precache_clinical_trials("sildenafil", indication)
        
        time.sleep(3)  # Rate limit between indications
    
    logger.info("")
    
    # 3. Cache safety data
    logger.info("STEP 3: Caching safety data...")
    logger.info("-" * 80)
    for drug in DEMO_DRUGS:
        precache_safety(drug)
        time.sleep(2)
    
    logger.info("")
    
    # Final statistics
    final_stats = get_cache_stats()
    elapsed_time = time.time() - start_time
    
    logger.info("=" * 80)
    logger.info("PRE-CACHING COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Total time: {elapsed_time/60:.1f} minutes")
    logger.info(f"Initial cache: {initial_stats}")
    logger.info(f"Final cache: {final_stats}")
    logger.info(f"New entries: {final_stats.get('total', 0) - initial_stats.get('total', 0)}")
    logger.info("")
    logger.info("✓ Hackathon demo is ready!")
    logger.info("✓ Expected demo performance:")
    logger.info("  - API calls: <30 (down from 150+)")
    logger.info("  - Runtime: 2-3 minutes (down from 6+ minutes)")
    logger.info("  - Cache hit rate: 80-90%")
    logger.info("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n✗ Pre-caching interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n✗ Pre-caching failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
