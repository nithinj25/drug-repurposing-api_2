# Quick Start: Sequential Gating Pipeline

## What Changed?

Your drug repurposing system now uses **sequential gating** instead of parallel dispatch. Each stage acts as a filter - if a drug doesn't pass the mechanistic gate, it never reaches clinical analysis.

---

## Setup (5 minutes)

### 1. Environment Configuration

```bash
cd drug-repurposing-api
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required for gating pipeline
GROQ_API_KEY=your_groq_key_here
USE_GROQ=true

# Optional (improves molecular agent)
OPENTARGETS_API_URL=https://api.platform.opentargets.org/api/v4/graphql
DISGENET_API_KEY=your_key_here
CLUE_API_KEY=your_key_here
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Usage Examples

### Example 1: Basic Gating Pipeline

```python
from src.agents.master_agent import MasterAgent
import asyncio

async def main():
    agent = MasterAgent()
    
    result = await agent.repurpose_with_gating(
        drug_name="metformin",
        indication="alzheimer's disease",
        patient_population="elderly"
    )
    
    print(f"✓ Stage: {result.stage.value}")
    print(f"✓ Confidence: {result.confidence_tier.value if result.confidence_tier else 'N/A'}")
    print(f"✓ Mechanistic Score: {result.mechanistic_score:.3f}")
    print(f"✓ Overlapping Targets: {', '.join(result.overlapping_targets)}")
    
    if result.success:
        print(f"\n✅ RECOMMENDATION: {result.confidence_tier.value}")
    else:
        print(f"\n❌ REJECTED: {result.rejection_reason}")

asyncio.run(main())
```

### Example 2: Terminal Illness Population (High AE Tolerance)

```python
result = await agent.repurpose_with_gating(
    drug_name="doxorubicin",
    indication="glioblastoma",
    patient_population="terminal_illness"  # High AE tolerance
)

# Terminal illness patients accept severe AEs if efficacy present
print(f"Safety Transfer Score: {result.safety_transfer_score:.3f}")
print(f"Hard Stop: {result.hard_stop}")  # False - high tolerance
```

### Example 3: Elderly Population (Strict Safety)

```python
result = await agent.repurpose_with_gating(
    drug_name="haloperidol",
    indication="agitation",
    patient_population="elderly"  # QT prolongation critical
)

# If drug causes QT prolongation → hard stop
if result.escalation_reason:
    print(f"⚠️ ESCALATE: {result.escalation_reason}")
```

---

## Understanding Results

### GatingResult Fields:

```python
{
    "success": True,  # Did drug pass all gates?
    "stage": "stage_5_confidence",  # Which stage completed
    "confidence_tier": "tier_2_mechanistically_supported",
    "mechanistic_score": 0.287,  # Jaccard overlap (0-1)
    "overlapping_targets": ["AMPK", "PRKAB1"],
    "literature_tier": "B",  # A=RCT, B=cohort, C=case, D=computational
    "safety_transfer_score": 0.65,
    "clinical_data_available": True,
    "flags": ["first_mover_opportunity"]
}
```

### Confidence Tiers:

| Tier | Meaning | Next Steps |
|------|---------|------------|
| **Tier 1: Confirmed Plausible** | High overlap + RCT evidence + clean safety + trials exist | Ready for clinical protocol design |
| **Tier 2: Mechanistically Supported** | Good overlap + literature + acceptable safety | First-mover opportunity - design Phase 2 |
| **Tier 3: Speculative** | Low overlap OR computational-only | Requires wet lab validation before investment |
| **Escalate: Human Review** | Contradictions / black-box warnings / pediatric | Expert review required |

---

## Rejection Examples

### Rejection at Stage 1 (No Mechanistic Basis):

```python
result = await agent.repurpose_with_gating(
    drug_name="acetaminophen",  # Painkiller
    indication="schizophrenia"  # Psychiatric disorder
)

# Output:
# success: False
# stage: stage_1_mechanistic
# rejection_reason: "No mechanistic basis: target-disease overlap < 0.15"
# mechanistic_score: 0.03
```

### Escalation at Stage 3 (Safety Hard Stop):

```python
result = await agent.repurpose_with_gating(
    drug_name="warfarin",  # Anticoagulant
    indication="pre-eclampsia",
    patient_population="women_childbearing"  # Teratogenic concerns
)

# Output:
# success: False
# stage: stage_3_safety
# confidence_tier: escalate_human_review
# escalation_reason: "Teratogenicity risk in women of childbearing age"
```

---

## Comparing to Old System

### Old Way (Parallel Dispatch):

```python
# All agents run simultaneously, scores averaged
job_id = agent.start_job("metformin", "alzheimer")
result = agent.get_job_status(job_id)

# Result: blended score with no gating
# Problem: Clinical agent runs even if zero mechanistic basis
```

### New Way (Sequential Gating):

```python
# Stages run sequentially with gates
result = await agent.repurpose_with_gating("metformin", "alzheimer", "elderly")

# Result: rejected at Stage 1 if overlap < 0.15
# Benefit: Saves computational resources, matches pharma workflow
```

---

## Testing Failed Trial Mining

```python
from src.agents.clinical_agent import ClinicalTrialsAgent

agent = ClinicalTrialsAgent()
result = agent.run("rosiglitazone", "alzheimer's disease")

# Check failed_trials field
if result['failed_trials']:
    print(f"Found {len(result['failed_trials'])} repurposing opportunities:")
    
    for trial in result['failed_trials']:
        print(f"  • {trial['trial_id']}: {trial['why_stopped']}")
        print(f"    Opportunity: {trial['repurposing_opportunity']}")
```

---

## Population Options

Use these values for `patient_population`:

- `general_adult` (default - baseline thresholds)
- `terminal_illness` (high AE tolerance - e.g., late-stage cancer)
- `elderly` (strict on QT prolongation, fall risk, renal)
- `pediatric` (strict on developmental toxicity)
- `women_childbearing` (teratogenicity = absolute veto)
- `hepatic_impairment` (hepatotoxicity = hard stop)
- `cardiac_comorbidities` (QT prolongation = hard stop)
- `immunocompromised` (immunosuppression acceptable)

---

## Troubleshooting

### "Module not found" Error:

```bash
# Ensure you're in the project root
cd drug-repurposing-api

# Reinstall dependencies
pip install -r requirements.txt
```

### "Open Targets API failed":

No API key needed - it's a public endpoint. If it fails:
- Check internet connection
- Agent falls back to knowledge base automatically

### "RuntimeError: This event loop is already running":

Use `asyncio.run()` for top-level calls:

```python
# ✅ Correct
asyncio.run(main())

# ❌ Wrong (if already in async context)
await main()
```

---

## API Endpoints (If Using FastAPI)

If you've exposed the gating pipeline via API:

```bash
curl -X POST http://localhost:8000/api/v1/repurpose/gating \
  -H "Content-Type: application/json" \
  -d '{
    "drug_name": "metformin",
    "indication": "alzheimer",
    "population": "elderly"
  }'
```

Response:
```json
{
  "success": true,
  "confidence_tier": "tier_2_mechanistically_supported",
  "mechanistic_score": 0.287,
  "overlapping_targets": ["AMPK", "PRKAB1"],
  "safety_transfer_score": 0.65,
  "flags": ["first_mover_opportunity"]
}
```

---

## Next Steps

1. **Test with your drug-indication pairs**
2. **Compare Tier 1 vs Tier 3 results** to validate gating logic
3. **Experiment with different populations** to see safety transfer scoring
4. **Review failed trials** for repurposing opportunities
5. **Integrate with your frontend** (if applicable)

---

## Key Takeaway

The sequential gating pipeline **stops early** if there's no mechanistic basis. This saves computation and matches real pharma workflows:

```
❌ Before: Run all agents → average scores → include weak candidates
✅ After:  Gate 1 (mechanism) → Gate 2 (literature) → Gate 3 (safety) → Gate 4 (clinical) → Tier
```

**Result:** Only mechanistically plausible candidates reach clinical analysis.
