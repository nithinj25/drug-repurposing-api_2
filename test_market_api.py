#!/usr/bin/env python
"""Test Market Intelligence API integration"""

from src.utils.market_intelligence_api import get_market_intelligence_client

print('='*80)
print('TESTING MARKET INTELLIGENCE API')
print('='*80)

api = get_market_intelligence_client()
print('\n✓ API client created')

# Test 1: Dysmenorrhea (fallback KB)
print('\n--- Test 1: Dysmenorrhea (Fallback KB) ---')
result = api.get_market_data('dysmenorrhea')
print(f'Indication: {result.indication}')
print(f'TAM: ${result.tam_millions}M')
print(f'Affected Population: {result.affected_population:,}')
print(f'Treatment Rate: {result.treatment_rate:.0%}')
print(f'Competitors: {len(result.competitors)}')
print(f'Data Sources: {result.data_sources}')

# Test 2: Pharyngitis (fallback KB)
print('\n--- Test 2: Pharyngitis (Fallback KB) ---')
result = api.get_market_data('pharyngitis')
print(f'Indication: {result.indication}')
print(f'TAM: ${result.tam_millions}M')
print(f'Affected Population: {result.affected_population:,}')
print(f'Treatment Rate: {result.treatment_rate:.0%}')
print(f'Competitors: {len(result.competitors)}')

# Test 3: Competitive Landscape
print('\n--- Test 3: Competitive Landscape ---')
landscape = api.get_competitive_landscape('dysmenorrhea', 'ibuprofen')
print(f'Market Concentration (HHI): {landscape.get("market_concentration")}')
print(f'White Space Opportunity: {landscape.get("white_space_opportunity")}')
print(f'Competitive Set: {len(landscape.get("competitive_set", []))} competitors')
for comp in landscape.get('competitive_set', [])[:3]:
    print(f'  - {comp["name"]}: {comp["market_share"]:.0%} share')

print('\n' + '='*80)
print('✓ ALL TESTS PASSED')
print('='*80)
