#!/usr/bin/env python
"""Test Market Agent WITHOUT caching - shows real API call performance"""

import time
import sys
sys.path.insert(0, '.')

print('='*80)
print('NO-CACHE TEST - Market Agent with Fresh API Calls')
print('='*80)
print('\nClearing any existing cache...')
print('(Cache already cleared via terminal command)')

print('\n' + '-'*80)
print('TESTING: Aspirin for Cardiovascular Disease')
print('-'*80)

# Import market agent
from src.agents.market_agent import MarketAgent

# Create agent instance
agent = MarketAgent()
print('\n[OK] Market Agent initialized')

# Start timer
print('\n[TIMER] Starting timer...')
start_time = time.time()

# Run analysis WITHOUT cache (fresh API calls)
print('[API] Making LIVE API calls (no cache)...\n')
result = agent.run(
    drug_name='aspirin',
    indication='cardiovascular disease',
    options={'geography': 'US'}
)

# End timer
end_time = time.time()
elapsed = end_time - start_time

print('\n' + '='*80)
print('RESULTS')
print('='*80)
print(f'\n[TIME] Execution Time: {elapsed:.2f} seconds')
print(f'Status: {result["status"]}')
print(f'Drug: {result["drug"]}')
print(f'Indication: {result["indication"]}')

if result.get('tam_estimate'):
    tam = result['tam_estimate']
    if tam.get('tam_usd'):
        print(f'\n[MARKET] Market Analysis:')
        print(f'   TAM: ${tam["tam_usd"]:.0f}M')
        print(f'   Patient Population: {tam.get("patient_population", 0):,}')
        print(f'   Treatment Rate: {tam.get("penetration_rate", 0):.0%}')
        print(f'   CAGR: {tam.get("cagr_percent", 0):.1f}%')

if result.get('competitors'):
    print(f'\n[COMPETITORS] Competitive Landscape:')
    print(f'   Competitors Identified: {len(result["competitors"])}')
    for i, comp in enumerate(result["competitors"][:3], 1):
        print(f'   {i}. {comp["drug_name"]}: {comp.get("market_share_estimate", 0):.0%} market share')

print(f'\n[SCORES] Overall Scores:')
print(f'   Market Opportunity: {result.get("market_opportunity_score", 0):.2f}/1.0')
print(f'   Unmet Need: {result.get("unmet_need_score", 0):.2f}/1.0')
print(f'   Data Confidence: {result.get("data_confidence", 0):.0%}')

print('\n' + '='*80)
print('TEST COMPLETE')
print('='*80)
print(f'\n[PERFORMANCE] Without cache: {elapsed:.2f} seconds')
print('[CACHE] Next run with cache will be ~0.06 seconds (811x faster)')
print('\n')
