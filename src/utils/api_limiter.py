"""
Rate Limiting and Retry Logic for External APIs

Prevents 429 rate limit errors and implements exponential backoff for:
- PubMed E-utilities
- Open Targets GraphQL
- ChEMBL REST API
- ClinicalTrials.gov
- DailyMed
- PharmGKB

Usage:
    @rate_limited_request('pubmed', max_retries=3)
    def fetch_papers(self, query):
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
"""

import time
import requests
from typing import Callable, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Ensures minimum interval between API calls"""
    
    def __init__(self, calls_per_second: float):
        """
        Initialize rate limiter
        
        Args:
            calls_per_second: Maximum allowed requests per second
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
        self.calls_per_second = calls_per_second
    
    def wait(self):
        """Block until minimum interval has elapsed"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_call = time.time()


# Global rate limiters for each API
# Set slightly below official limits to provide buffer
RATE_LIMITERS = {
    'pubmed': RateLimiter(2.5),  # Official: 3 req/sec (no key) or 10 req/sec (with key)
    'pubmed_with_key': RateLimiter(8.0),  # Buffer below 10 req/sec
    'open_targets': RateLimiter(8.0),  # Official: 10 req/sec
    'clinicaltrials': RateLimiter(2.0),  # Conservative limit (no official limit)
    'chembl': RateLimiter(15.0),  # Official: 20 req/sec
    'dailymed': RateLimiter(4.0),  # Official: 5 req/sec
    'pharmgkb': RateLimiter(3.0),  # Conservative (unknown limit)
    'groq': RateLimiter(0.45),  # 30 req/min = 0.5 req/sec (with buffer)
}


def rate_limited_request(api_name: str, max_retries: int = 3):
    """
    Decorator for rate-limited API calls with exponential backoff
    
    Args:
        api_name: Name of API (must exist in RATE_LIMITERS)
        max_retries: Maximum number of retry attempts
    
    Usage:
        @rate_limited_request('pubmed', max_retries=3)
        def fetch_data(self):
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            limiter = RATE_LIMITERS.get(api_name)
            
            if not limiter:
                logger.warning(f"No rate limiter configured for: {api_name}")
            
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # Apply rate limiting
                    if limiter:
                        limiter.wait()
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Success - log if retried
                    if attempt > 0:
                        logger.info(f"✓ {api_name} succeeded on retry {attempt + 1}")
                    
                    return result
                
                except requests.exceptions.HTTPError as e:
                    last_exception = e
                    
                    # Handle rate limiting (429 Too Many Requests)
                    if e.response.status_code == 429:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        retry_after = e.response.headers.get('Retry-After')
                        
                        if retry_after:
                            try:
                                wait_time = int(retry_after)
                            except ValueError:
                                pass
                        
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"⚠ Rate limit hit for {api_name}. "
                                f"Retry {attempt + 1}/{max_retries} after {wait_time}s"
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(f"✗ {api_name} rate limit exceeded after {max_retries} retries")
                            raise
                    
                    # Handle server errors (5xx)
                    elif 500 <= e.response.status_code < 600:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.warning(
                                f"⚠ Server error {e.response.status_code} for {api_name}. "
                                f"Retry {attempt + 1}/{max_retries} after {wait_time}s"
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(f"✗ {api_name} server error after {max_retries} retries")
                            raise
                    
                    # Other HTTP errors (4xx except 429) - don't retry
                    else:
                        logger.error(f"✗ HTTP {e.response.status_code} error for {api_name}: {str(e)}")
                        raise
                
                except requests.exceptions.Timeout as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        wait_time = 1 + attempt  # Linear backoff: 1s, 2s, 3s
                        logger.warning(
                            f"⚠ Timeout for {api_name}. "
                            f"Retry {attempt + 1}/{max_retries} after {wait_time}s"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"✗ {api_name} timeout after {max_retries} retries")
                        raise
                
                except requests.exceptions.ConnectionError as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"⚠ Connection error for {api_name}. "
                            f"Retry {attempt + 1}/{max_retries} after {wait_time}s"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"✗ {api_name} connection error after {max_retries} retries")
                        raise
            
            # If we exhausted retries, raise last exception
            if last_exception:
                raise last_exception
            else:
                raise Exception(f"{api_name} failed after {max_retries} retries")
        
        return wrapper
    return decorator


def get_rate_limiter_stats() -> dict:
    """Get statistics for all rate limiters"""
    stats = {}
    for api_name, limiter in RATE_LIMITERS.items():
        stats[api_name] = {
            'calls_per_second': limiter.calls_per_second,
            'min_interval_ms': int(limiter.min_interval * 1000),
            'last_call_ago_sec': round(time.time() - limiter.last_call, 2) if limiter.last_call > 0 else None
        }
    return stats


# Convenience function for manual rate limiting
def wait_for_rate_limit(api_name: str):
    """Manually wait for rate limit (use when not using decorator)"""
    limiter = RATE_LIMITERS.get(api_name)
    if limiter:
        limiter.wait()
    else:
        logger.warning(f"No rate limiter configured for: {api_name}")
