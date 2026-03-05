# API Rate Limit Reduction Strategies

## Current State Analysis

### API Usage Per Pipeline Run (TOP 3 candidates):

| API Source | Calls/Run | Rate Limits | Current Protection |
|------------|-----------|-------------|-------------------|
| **Open Targets GraphQL** | ~30-50 | 10 req/sec | ✅ EFO cache (molecular) |
| **ChEMBL REST** | ~15-20 | 20 req/sec | ❌ No caching |
| **PubMed E-utilities** | ~10-15 | 3 req/sec (no key), 10 req/sec (with key) | ❌ No caching |
| **ClinicalTrials.gov** | ~10-15 | 1000 req/day | ❌ No caching |
| **DailyMed** | ~3-5 | 5 req/sec | ❌ No caching |
| **Groq LLM API** | ~50-70 | 30 req/min (free tier) | ❌ No caching |
| **PharmGKB** | ~3-5 | Unknown | ❌ No caching |

**Total API calls per run: ~150-200 calls**

---

## 🚀 **STRATEGY 1: Persistent Caching (HIGHEST IMPACT)**

### Implementation: Redis/File-based Cache Layer

**Impact:** Reduce repeated calls by **60-80%** for common drugs/diseases

#### A. Drug Profile Caching
```python
# src/utils/cache_manager.py
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class DrugRepurposingCache:
    def __init__(self, cache_dir: str = "cache_data"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_days = 30  # Cache validity period
    
    def _get_cache_key(self, source: str, identifier: str) -> str:
        """Generate cache key"""
        key_str = f"{source}:{identifier}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, source: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached data"""
        cache_key = self._get_cache_key(source, identifier)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)
        
        # Check TTL
        cached_time = datetime.fromisoformat(cached_data['timestamp'])
        if datetime.now() - cached_time > timedelta(days=self.ttl_days):
            cache_file.unlink()  # Delete expired cache
            return None
        
        return cached_data['data']
    
    def set(self, source: str, identifier: str, data: Dict[str, Any]):
        """Store data in cache"""
        cache_key = self._get_cache_key(source, identifier)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cached_data = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'identifier': identifier,
            'data': data
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cached_data, f, indent=2)

# Global cache instance
_cache = DrugRepurposingCache()

def get_cached(source: str, identifier: str) -> Optional[Dict]:
    return _cache.get(source, identifier)

def set_cached(source: str, identifier: str, data: Dict):
    _cache.set(source, identifier, data)
```

#### B. Integration Points

**1. ChEMBL Drug Profile (drug_profiler_agent.py)**
```python
# BEFORE API CALL (line ~170):
cache_key = f"chembl_drug:{drug_name.lower()}"
cached_profile = get_cached("chembl", cache_key)
if cached_profile:
    logger.info(f"✓ Cache HIT: ChEMBL drug profile for {drug_name}")
    return DrugProfile(**cached_profile)

# AFTER API SUCCESS (line ~350):
set_cached("chembl", cache_key, asdict(drug_profile))
logger.info(f"✓ Cached ChEMBL profile: {drug_name}")
```

**2. PubMed Literature (literature_agent.py)**
```python
# BEFORE PUBMED SEARCH (line ~235):
search_hash = hashlib.md5(f"{drug}:{indication}".encode()).hexdigest()
cached_papers = get_cached("pubmed", search_hash)
if cached_papers:
    logger.info(f"✓ Cache HIT: PubMed literature ({len(cached_papers)} papers)")
    return cached_papers

# AFTER RETRIEVAL (line ~280):
set_cached("pubmed", search_hash, results)
```

**3. Clinical Trials (clinical_agent.py)**
```python
# BEFORE TRIAL SEARCH (line ~208):
trial_key = f"{drug_name}:{indication}"
cached_trials = get_cached("clinicaltrials", trial_key)
if cached_trials:
    logger.info(f"✓ Cache HIT: Clinical trials ({len(cached_trials)} trials)")
    return cached_trials

# AFTER FETCHING (line ~240):
set_cached("clinicaltrials", trial_key, trials)
```

**Expected Savings:** 
- ChEMBL: 15 calls → **3 calls** (80% reduction)
- PubMed: 10 calls → **2 calls** (80% reduction)  
- ClinicalTrials: 10 calls → **2 calls** (80% reduction)

---

## 🔄 **STRATEGY 2: Request Deduplication**

### Problem: Same drug evaluated 3 times = 3x duplicate DrugProfiler calls

**Solution:** Share drug profiles across candidates

```python
# src/agents/master_agent.py (line ~650)

async def run_discovery(self, drug_name: str, ...):
    # ...
    
    # ✓ OPTIMIZATION: Profile drug once, reuse for all candidates
    logger.info(f"Profiling drug: {drug_name}")
    drug_profile = await self.drug_profiler.run(drug_name)
    
    evaluated_candidates = []
    for candidate in candidates_to_evaluate:
        # Pass pre-fetched drug_profile instead of re-profiling
        result = await self.evaluate_candidate(
            drug_profile,  # ✓ Reuse
            candidate,
            options
        )
        evaluated_candidates.append(result)
```

**Expected Savings:** ChEMBL calls drop from 15 → **5 calls** (66% reduction)

---

## ⏱️ **STRATEGY 3: Rate Limiting & Exponential Backoff**

### Implementation: Smart retry with delays

```python
# src/utils/api_limiter.py
import time
import requests
from typing import Callable, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, calls_per_second: float):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
    
    def wait(self):
        """Ensure minimum interval between calls"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_call = time.time()

# Global rate limiters
RATE_LIMITERS = {
    'pubmed': RateLimiter(2.5),  # 2.5 req/sec (buffer below 3)
    'open_targets': RateLimiter(8.0),  # 8 req/sec (buffer below 10)
    'clinicaltrials': RateLimiter(2.0),  # 2 req/sec
    'chembl': RateLimiter(15.0),  # 15 req/sec
}

def rate_limited_request(api_name: str, max_retries: int = 3):
    """Decorator for rate-limited API calls with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            limiter = RATE_LIMITERS.get(api_name)
            
            for attempt in range(max_retries):
                try:
                    if limiter:
                        limiter.wait()
                    
                    return func(*args, **kwargs)
                
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Rate limit hit
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(f"Rate limit hit for {api_name}. Retry {attempt+1}/{max_retries} after {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        raise
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        logger.warning(f"Timeout for {api_name}. Retry {attempt+1}/{max_retries}")
                        time.sleep(1)
                    else:
                        raise
            
            raise Exception(f"{api_name} failed after {max_retries} retries")
        
        return wrapper
    return decorator

# USAGE EXAMPLE:
@rate_limited_request('pubmed', max_retries=3)
def fetch_pubmed_papers(self, query: str):
    response = requests.get(f"{self.base_url}/esearch.fcgi", params=params, timeout=20)
    response.raise_for_status()
    return response.json()
```

**Expected Benefit:** Eliminate 429 errors, auto-recover from transient failures

---

## 📦 **STRATEGY 4: Batch Requests Where Possible**

### A. ChEMBL Multi-Target Fetch
```python
# Instead of 5 separate calls for 5 targets:
for target in drug_targets:
    target_data = self._fetch_target_by_chembl_id(target)

# Batch into single call:
target_ids = [t['id'] for t in drug_targets]
url = f"{self.base_url}/target.json"
params = {"chembl_id__in": ",".join(target_ids)}
response = requests.get(url, params=params)
```

**Expected Savings:** 5 target calls → **1 call** (80% reduction)

### B. PubMed Bulk Fetch
```python
# Fetch 10 papers in one XML response instead of 10 separate calls
pmids = esearch_data.get("idlist", [])[:10]
fetch_params = {
    "db": "pubmed",
    "id": ",".join(pmids),  # ✓ Batch all PMIDs
    "retmode": "xml"
}
```

**Already implemented ✓**

---

## 🔑 **STRATEGY 5: API Key Management**

### Get API Keys (Free Tiers):
1. **PubMed E-utilities**: https://www.ncbi.nlm.nih.gov/account/settings/  
   - Free tier: 10 req/sec (3x improvement over no key)
   
2. **Groq LLM**: https://console.groq.com/keys  
   - Free tier: 30 req/min, 14,400 req/day
   - Consider adding fallback to OpenAI/Anthropic

3. **PharmGKB**: https://www.pharmgkb.org/page/dataUsagePolicy  
   - Academic license available

### Multiple Key Rotation
```python
# src/utils/api_keys.py
from itertools import cycle

class APIKeyRotator:
    def __init__(self, keys: list):
        self.keys = cycle(keys)  # Round-robin rotation
    
    def get_key(self) -> str:
        return next(self.keys)

# Usage:
PUBMED_KEYS = APIKeyRotator([
    os.getenv('NCBI_API_KEY_1'),
    os.getenv('NCBI_API_KEY_2'),
    os.getenv('NCBI_API_KEY_3')
])

params['api_key'] = PUBMED_KEYS.get_key()
```

---

## 📊 **STRATEGY 6: Reduce Data Fetching Scope**

### Current Settings vs. Optimized:

| Agent | Current | Optimized | Savings |
|-------|---------|-----------|---------|
| **Literature** | Top 10 papers | Top 5 papers | 50% |
| **Clinical Trials** | All phases | Phase 2+ only | 40% |
| **Open Targets** | 50 genes | 30 genes | 40% |
| **Discovery** | 20 fetch → 10 final | 15 fetch → 8 final | 25% |

```python
# src/agents/literature_agent.py (line ~225)
"retmax": "5",  # Reduce from 10 to 5

# src/agents/clinical_agent.py (line ~212)
# Add filter:
params["query.cond"] = f"{indication} AND AREA[MinimumPhase]2"  # Phase 2+

# src/agents/molecular_agent.py (line ~327)
"first": 30,  # Reduce from 50 to 30
```

---

## 🔍 **STRATEGY 7: Pre-populate Cache (Batch Mode)**

### Hackathon Preparation: Pre-cache common drugs

```python
# scripts/precache_common_drugs.py
common_drugs = [
    "sildenafil", "metformin", "aspirin", "ibuprofen", 
    "statins", "paracetamol", "warfarin", "insulin"
]

async def precache_drugs():
    """Pre-fetch and cache common drugs before demo"""
    for drug in common_drugs:
        print(f"Caching {drug}...")
        
        # Profile drug
        profile = await drug_profiler.run(drug)
        cache.set("chembl", f"chembl_drug:{drug}", asdict(profile))
        
        # Fetch top 5 indications
        indications = await indication_discovery.run(profile.targets, ...)
        for indication in indications[:5]:
            # Cache clinical trials
            trials = await clinical_agent.fetch_trials(drug, indication)
            cache.set("clinicaltrials", f"{drug}:{indication}", trials)
            
            # Cache literature
            papers = await literature_agent.search_pubmed(drug, indication)
            cache.set("pubmed", f"{drug}:{indication}", papers)
        
        time.sleep(2)  # Rate limit between drugs

# Run before hackathon:
asyncio.run(precache_drugs())
```

---

## 🎯 **Priority Implementation Plan**

### Phase 1: Immediate (Before Hackathon) - 2 hours
1. ✅ **Add file-based cache** (cache_manager.py) → 60% call reduction
2. ✅ **Add rate limiters** (api_limiter.py) → Prevent 429 errors
3. ✅ **Pre-cache sildenafil** → Demo runs with zero external calls

### Phase 2: Post-Hackathon - 1 day
4. ✅ Deduplicate drug profiler calls → 66% ChEMBL reduction
5. ✅ Reduce literature/trial limits → 40% reduction
6. ✅ Get PubMed API key → 3x rate limit boost

### Phase 3: Production - 1 week
7. ✅ Migrate to Redis cache → Distributed caching
8. ✅ Add API key rotation → Scale to multiple keys
9. ✅ Request queue with priority → Critical calls first
10. ✅ Monitoring dashboard → Track API usage live

---

## 📈 **Expected Impact Summary**

| Metric | Before | After All Strategies | Improvement |
|--------|--------|---------------------|-------------|
| **Total API calls/run** | 150-200 | 30-50 | **70-75% reduction** |
| **ChEMBL calls** | 15 | 3 | **80% reduction** |
| **PubMed calls** | 10 | 2 | **80% reduction** |
| **OpenTargets calls** | 40 | 10 | **75% reduction** |
| **429 errors** | Frequent | Rare | **95% reduction** |
| **Pipeline time** | 6.26 min | 2-3 min (with cache) | **50% faster** |

---

## 🔧 **Quick Win: Add Cache Now (5 minutes)**

```bash
# 1. Create cache directory
cd "c:\Users\Nithin J\OneDrive\Desktop\ey_project_2\drug-repurposing-api"
mkdir cache_data

# 2. Create cache_manager.py
# (Copy code from STRATEGY 1)

# 3. Add to drug_profiler_agent.py (line ~170):
from src.utils.cache_manager import get_cached, set_cached

cache_key = f"chembl_drug:{drug_name.lower()}"
cached = get_cached("chembl", cache_key)
if cached:
    return DrugProfile(**cached)

# ... after line 350 (successful fetch):
set_cached("chembl", cache_key, asdict(drug_profile))
```

---

## 📞 **Additional Optimizations**

### 1. Async/Parallel Requests
```python
# Fetch multiple agents in parallel
import asyncio
results = await asyncio.gather(
    literature_agent.run(drug, indication),
    clinical_agent.run(drug, indication),
    safety_agent.run(drug, indication)
)
```

### 2. Local Database Mirror
- Download ChEMBL SQLite database (3GB) → Zero API calls
- Mirror Open Targets gene-disease data → Local GraphQL

### 3. Request Compression
```python
headers = {"Accept-Encoding": "gzip, deflate"}
```

---

## 🚨 **Monitoring & Alerts**

```python
# Track API usage
class APICallTracker:
    calls = defaultdict(int)
    
    @classmethod
    def log_call(cls, api_name: str):
        cls.calls[api_name] += 1
    
    @classmethod
    def report(cls):
        for api, count in cls.calls.items():
            logger.info(f"{api}: {count} calls")

# Add to each API call:
APICallTracker.log_call('pubmed')
```

---

## ✅ **Next Steps**

1. **Implement cache_manager.py** (STRATEGY 1)
2. **Add caching to ChEMBL, PubMed, ClinicalTrials**
3. **Pre-cache sildenafil for hackathon**
4. **Test: Run discovery and verify <50 API calls**
5. **Monitor cache hit rates**

**Expected Result:** Hackathon demo runs in <3 minutes with minimal API calls ✓
