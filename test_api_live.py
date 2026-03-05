"""
Live API Testing Script
Calls the running API with sample drug-indication pairs and saves responses to JSON files.
"""

import requests
import json
from pathlib import Path
from datetime import datetime

API_BASE = "http://localhost:8000"
OUTPUT_DIR = Path("api_test_results")
OUTPUT_DIR.mkdir(exist_ok=True)

# Test cases
test_cases = [
    {
        "name": "metformin_alzheimer",
        "drug_name": "metformin",
        "indication": "alzheimer's disease",
        "description": "Diabetes drug → Alzheimer's (classic repurposing candidate)"
    },
    {
        "name": "aspirin_colorectal_cancer",
        "drug_name": "aspirin",
        "indication": "colorectal cancer",
        "description": "Anti-inflammatory → Cancer prevention"
    },
    {
        "name": "sildenafil_pulmonary_hypertension",
        "drug_name": "sildenafil",
        "indication": "pulmonary hypertension",
        "description": "Viagra → Lung disease (actual successful repurposing)"
    },
    {
        "name": "thalidomide_multiple_myeloma",
        "drug_name": "thalidomide",
        "indication": "multiple myeloma",
        "description": "Failed drug → Cancer treatment (comeback story)"
    }
]

def test_health_check():
    """Test /health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{API_BASE}/health")
    
    result = {
        "endpoint": "/health",
        "status_code": response.status_code,
        "response": response.json()
    }
    
    output_file = OUTPUT_DIR / "health_check.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✓ Health check saved to {output_file}")
    return result

def test_analyze(test_case):
    """Test /analyze endpoint with a drug-indication pair"""
    print(f"\nTesting: {test_case['name']}")
    print(f"  Drug: {test_case['drug_name']}")
    print(f"  Indication: {test_case['indication']}")
    print(f"  Description: {test_case['description']}")
    
    request_body = {
        "drug_name": test_case['drug_name'],
        "indication": test_case['indication'],
        "include_patent": True,
        "use_internal_data": False
    }
    
    try:
        print("  Sending request...")
        response = requests.post(
            f"{API_BASE}/analyze",
            json=request_body,
            timeout=120
        )
        
        result = {
            "test_case": test_case['name'],
            "description": test_case['description'],
            "request": request_body,
            "status_code": response.status_code,
            "timestamp": datetime.now().isoformat(),
            "response": response.json() if response.status_code == 200 else {"error": response.text}
        }
        
        # Save full response
        output_file = OUTPUT_DIR / f"{test_case['name']}_full.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"  ✓ Response saved to {output_file}")
        
        # Extract and save summary
        if response.status_code == 200:
            resp_data = response.json()
            job_data = resp_data.get('data', {})
            
            summary = {
                "test_case": test_case['name'],
                "drug": test_case['drug_name'],
                "indication": test_case['indication'],
                "success": resp_data.get('success'),
                "job_id": resp_data.get('job_id'),
                "status": job_data.get('status'),
                "task_summary": job_data.get('task_summary'),
                "human_review_required": job_data.get('human_review_required'),
                "timestamp": datetime.now().isoformat()
            }
            
            # Check if reasoning_result exists
            if 'reasoning_result' in job_data and job_data['reasoning_result']:
                reasoning = job_data['reasoning_result']
                summary['reasoning'] = {
                    "composite_score": reasoning.get('composite_score'),
                    "recommendation": reasoning.get('recommendation'),
                    "confidence_level": reasoning.get('confidence_level')
                }
            
            summary_file = OUTPUT_DIR / f"{test_case['name']}_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"  ✓ Summary saved to {summary_file}")
            print(f"  Job ID: {resp_data.get('job_id')}")
            print(f"  Status: {job_data.get('status')}")
            print(f"  Tasks: {job_data.get('task_summary')}")
            
        return result
        
    except Exception as e:
        error_result = {
            "test_case": test_case['name'],
            "request": request_body,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        output_file = OUTPUT_DIR / f"{test_case['name']}_error.json"
        with open(output_file, 'w') as f:
            json.dump(error_result, f, indent=2)
        
        print(f"  ✗ Error: {str(e)}")
        print(f"  Error saved to {output_file}")
        return error_result

def main():
    print("=" * 80)
    print("Drug Repurposing API - Live Testing")
    print("=" * 80)
    print(f"API Base: {API_BASE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Test Cases: {len(test_cases)}")
    print("=" * 80)
    
    # Test health check
    health = test_health_check()
    
    if health['status_code'] != 200:
        print("\n✗ Health check failed! API may not be running.")
        print("  Start the API with: python src/api.py")
        return
    
    print("\n✓ API is healthy\n")
    
    # Run all test cases
    results = []
    for test_case in test_cases:
        result = test_analyze(test_case)
        results.append(result)
    
    # Save master summary
    master_summary = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(test_cases),
        "successful": sum(1 for r in results if r.get('status_code') == 200),
        "failed": sum(1 for r in results if r.get('status_code') != 200),
        "test_cases": [
            {
                "name": r.get('test_case'),
                "status_code": r.get('status_code'),
                "success": r.get('response', {}).get('success') if r.get('status_code') == 200 else False
            }
            for r in results
        ]
    }
    
    master_file = OUTPUT_DIR / "master_summary.json"
    with open(master_file, 'w') as f:
        json.dump(master_summary, f, indent=2)
    
    print("\n" + "=" * 80)
    print("Testing Complete!")
    print("=" * 80)
    print(f"Results saved to: {OUTPUT_DIR}")
    print(f"Total tests: {master_summary['total_tests']}")
    print(f"Successful: {master_summary['successful']}")
    print(f"Failed: {master_summary['failed']}")
    print("\nFiles created:")
    for file in sorted(OUTPUT_DIR.glob("*.json")):
        print(f"  - {file.name}")

if __name__ == "__main__":
    main()
