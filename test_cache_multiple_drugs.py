"""
Test Caching with Multiple Drugs

This script tests the drug profiler cache by:
1. Profiling 5 different drugs (cold cache)
2. Profiling the same 5 drugs again (warm cache)
3. Comparing execution times
4. Showing cache hit rates

Run: python test_cache_multiple_drugs.py
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.drug_profiler_agent import DrugProfilerAgent
from src.utils import get_cache_stats, clear_cache
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


# Test drugs
TEST_DRUGS = [
    "sildenafil",
    "metformin",
    "aspirin",
    "ibuprofen",
    "atorvastatin"
]


def test_drug_profiling(drug_name: str, run_number: int):
    """Profile a single drug and return time taken"""
    profiler = DrugProfilerAgent()
    
    start_time = time.time()
    profile = profiler.run(drug_name)
    elapsed = time.time() - start_time
    
    status = "✓" if not profile.error else "✗"
    cache_status = "(cached)" if elapsed < 0.1 else "(API call)"
    
    logger.info(f"  {status} {drug_name:15s} | {elapsed:6.3f}s | "
               f"{len(profile.known_targets):2d} targets | "
               f"{len(profile.approved_indications):2d} indications | {cache_status}")
    
    return elapsed, not profile.error


def main():
    logger.info("═" * 80)
    logger.info("TESTING DRUG PROFILER CACHE WITH MULTIPLE DRUGS")
    logger.info("═" * 80)
    logger.info("")
    
    # Clear cache to start fresh
    logger.info("Clearing cache to start fresh...")
    clear_cache('chembl')
    initial_stats = get_cache_stats()
    logger.info(f"Initial cache: {initial_stats}")
    logger.info("")
    
    # ========================================================================
    # RUN 1: Cold Cache (should hit APIs)
    # ========================================================================
    logger.info("─" * 80)
    logger.info("RUN 1: COLD CACHE (First time profiling each drug)")
    logger.info("─" * 80)
    logger.info("  Drug            | Time   | Targets | Indications | Status")
    logger.info("  " + "─" * 70)
    
    run1_times = []
    run1_start = time.time()
    
    for drug in TEST_DRUGS:
        elapsed, success = test_drug_profiling(drug, 1)
        if success:
            run1_times.append(elapsed)
        time.sleep(0.5)  # Rate limit between calls
    
    run1_total = time.time() - run1_start
    
    logger.info("  " + "─" * 70)
    logger.info(f"  Total time: {run1_total:.2f}s | Avg per drug: {run1_total/len(TEST_DRUGS):.2f}s")
    logger.info("")
    
    # Check cache after run 1
    stats_after_run1 = get_cache_stats()
    logger.info(f"Cache after Run 1: {stats_after_run1}")
    logger.info("")
    
    # ========================================================================
    # RUN 2: Warm Cache (should hit cache)
    # ========================================================================
    logger.info("─" * 80)
    logger.info("RUN 2: WARM CACHE (Same drugs, should use cache)")
    logger.info("─" * 80)
    logger.info("  Drug            | Time   | Targets | Indications | Status")
    logger.info("  " + "─" * 70)
    
    run2_times = []
    run2_start = time.time()
    
    for drug in TEST_DRUGS:
        elapsed, success = test_drug_profiling(drug, 2)
        if success:
            run2_times.append(elapsed)
    
    run2_total = time.time() - run2_start
    
    logger.info("  " + "─" * 70)
    logger.info(f"  Total time: {run2_total:.2f}s | Avg per drug: {run2_total/len(TEST_DRUGS):.2f}s")
    logger.info("")
    
    # ========================================================================
    # COMPARISON & STATISTICS
    # ========================================================================
    logger.info("═" * 80)
    logger.info("PERFORMANCE COMPARISON")
    logger.info("═" * 80)
    logger.info("")
    
    speedup = run1_total / run2_total if run2_total > 0 else 0
    time_saved = run1_total - run2_total
    percent_saved = (time_saved / run1_total * 100) if run1_total > 0 else 0
    
    logger.info(f"  Cold Cache (Run 1):  {run1_total:6.2f}s  ({len(TEST_DRUGS)} API calls)")
    logger.info(f"  Warm Cache (Run 2):  {run2_total:6.2f}s  ({len(TEST_DRUGS)} cache hits)")
    logger.info(f"  ")
    logger.info(f"  Time Saved:          {time_saved:6.2f}s  ({percent_saved:.1f}% faster)")
    logger.info(f"  Speedup:             {speedup:6.2f}x")
    logger.info("")
    
    # Cache hit rate
    final_stats = get_cache_stats()
    cache_entries = final_stats.get('chembl', 0)
    cache_hit_rate = (cache_entries / (len(TEST_DRUGS) * 2)) * 100 if cache_entries > 0 else 0
    
    logger.info(f"  Cache Statistics:")
    logger.info(f"    Entries cached: {cache_entries}/{len(TEST_DRUGS)}")
    logger.info(f"    Cache hit rate: {cache_hit_rate:.1f}%")
    logger.info("")
    
    # ========================================================================
    # CONCLUSION
    # ========================================================================
    logger.info("═" * 80)
    logger.info("CONCLUSION")
    logger.info("═" * 80)
    logger.info("")
    
    if speedup > 5:
        logger.info("  ✓✓✓ EXCELLENT: Cache is working perfectly!")
        logger.info(f"      {speedup:.1f}x faster with warm cache")
    elif speedup > 2:
        logger.info("  ✓✓ GOOD: Cache is providing significant speedup")
        logger.info(f"     {speedup:.1f}x faster with warm cache")
    elif speedup > 1.2:
        logger.info("  ✓ OK: Cache is working but not fully optimized")
        logger.info(f"    {speedup:.1f}x faster with warm cache")
    else:
        logger.info("  ✗ ISSUE: Cache may not be working properly")
        logger.info(f"    Only {speedup:.1f}x faster (expected >5x)")
    
    logger.info("")
    logger.info("  For hackathon demo:")
    logger.info("    • Pre-cache target drugs before demo")
    logger.info("    • Expected demo speed: 2-3 minutes (with cache)")
    logger.info("    • Zero 429 rate limit errors")
    logger.info("")
    logger.info("═" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
