#!/usr/bin/env python
"""Test Full Pipeline via API - Run complete drug repurposing analysis"""

import requests
import json
import time
from datetime import datetime

print('='*80)
print('FULL PIPELINE TEST - Drug Repurposing API')
print('='*80)

# API endpoint
API_URL = "http://127.0.0.1:8010/discover"

# Test drug
drug_name = "sildenafil"
print(f'\nTesting Drug: {drug_name.upper()}')
print('-'*80)

# Request payload
payload = {
    "drug_name": drug_name,
    "population": "general_adult",
    "include_patent": True
}

print(f'\n[REQUEST] Sending to {API_URL}')
print(f'Payload: {json.dumps(payload, indent=2)}')

# Start timer
start_time = time.time()
print('\n[TIMER] Starting full pipeline...\n')

try:
    # Make API request
    response = requests.post(
        API_URL,
        json=payload,
        timeout=300  # 5 minute timeout
    )
    
    # End timer
    elapsed = time.time() - start_time
    
    print(f'\n[TIME] Pipeline completed in {elapsed:.2f} seconds')
    print(f'[STATUS] HTTP {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        
        print('\n' + '='*80)
        print('RESULTS')
        print('='*80)
        
        # Extract key information
        data = result.get('data', {})
        candidates = data.get('candidates', [])
        
        print(f'\n[CANDIDATES] Found {len(candidates)} repurposing opportunities')
        
        # Show top 5 candidates
        if candidates:
            print('\n' + '-'*80)
            print('TOP 5 REPURPOSING CANDIDATES')
            print('-'*80)
            
            for i, candidate in enumerate(candidates[:5], 1):
                print(f'\n{i}. {candidate.get("indication", "Unknown")}')
                print(f'   Tier: {candidate.get("tier", "Unknown")}')
                print(f'   Composite Score: {candidate.get("composite_score", 0):.3f}')
                print(f'   Clinical Evidence: {candidate.get("clinical_evidence_score", 0):.2f}')
                print(f'   Mechanism Score: {candidate.get("mechanism_score", 0):.2f}')
                print(f'   Market Opportunity: {candidate.get("market_opportunity", 0):.2f}')
                
                # Show key insights
                insights = candidate.get("key_insights", [])
                if insights:
                    print(f'   Key Insights:')
                    for insight in insights[:2]:
                        print(f'     - {insight}')
        
        # Save full results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"api_test_results/full_pipeline_{drug_name}_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print('\n' + '='*80)
        print('SUMMARY')
        print('='*80)
        print(f'Drug: {drug_name}')
        print(f'Total Candidates: {len(candidates)}')
        print(f'Execution Time: {elapsed:.2f} seconds')
        print(f'Results Saved: {output_file}')
        
        # Show tier distribution
        tier_counts = {}
        for candidate in candidates:
            tier = candidate.get('tier', 'Unknown')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        if tier_counts:
            print(f'\nTier Distribution:')
            for tier, count in sorted(tier_counts.items()):
                print(f'  {tier}: {count} candidates')
        
        print('\n' + '='*80)
        print('[SUCCESS] Full pipeline test completed')
        print('='*80)
        
    else:
        print(f'\n[ERROR] API returned status code {response.status_code}')
        print(f'Response: {response.text}')
        
except requests.exceptions.Timeout:
    print('\n[ERROR] Request timed out after 5 minutes')
except requests.exceptions.ConnectionError:
    print('\n[ERROR] Could not connect to API server')
    print('Make sure the server is running on http://127.0.0.1:8010')
except Exception as e:
    print(f'\n[ERROR] {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

print('\n')
