#!/usr/bin/env python
"""Test Market Agent with Market Intelligence API integration"""

import sys
sys.path.insert(0, '.')

print('Testing Market Agent imports...')
try:
    from src.agents.market_agent import MarketAgent
    print('✓ Market Agent imports successfully')
    
    # Test creating an instance
    agent = MarketAgent()
    print('✓ MarketAgent instance created')
    
    # Test running the agent
    print('\nTesting Market Agent run with dysmenorrhea...')
    result = agent.run(
        drug_name='ibuprofen',
        indication='dysmenorrhea',
        options={'geography': 'US'}
    )
    
    print(f'\n✓ Market Agent completed')
    print(f'Status: {result["status"]}')
    print(f'Drug: {result["drug"]}')
    print(f'Indication: {result["indication"]}')
    
    if result['tam_estimate']:
        print(f'TAM: ${result["tam_estimate"]["tam_usd"]:.0f}M')
        print(f'CAGR: {result["tam_estimate"]["cagr_percent"]:.1f}%')
    
    print(f'Competitors: {len(result["competitors"])}')
    print(f'Market Phase: {result["market_phase"]}')
    print(f'Data Confidence: {result["data_confidence"]:.0%}')
    
    print('\n' + '='*80)
    print('✓ MARKET AGENT INTEGRATION SUCCESSFUL')
    print('='*80)
    
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
