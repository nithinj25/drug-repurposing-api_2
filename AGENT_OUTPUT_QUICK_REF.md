# Quick Agent Output Reference - For Dashboard Devs

## TL;DR - What Each Agent Outputs

### 🤖 Agent 1: MASTER AGENT
**Purpose:** Drug identification & baseline data

**Input:** `drug_name: "ibuprofen"`

**Output:**
```
drug_profile {
  chembl_id: "CHEMBL521"
  targets: ["PTGS1", "PTGS2"]
  approved_indications: ["Fever", "Pain", "Arthritis", ...]
  mechanism: "Cyclooxygenase inhibitor"
  synonyms: ["Advil", "Motrin", "Nurofen", ...]
}
```

**For Dashboard:** Show as info header with drug name, targets, approved indications

---

### 🔬 Agent 2: DISCOVERY AGENT  
**Purpose:** Find disease candidates mechanistically similar to approved uses

**Input:** Drug profile from Master Agent

**Output:**
```
top_candidates: [
  { disease: "Patent ductus arteriosus", score: 0.803, targets: ["PTGS2"] },
  { disease: "Ankylosing spondylitis", score: 0.789, targets: ["PTGS2"] },
  { disease: "Inflammation", score: 0.779, targets: ["PTGS2"] },
  ...
]
```

**For Dashboard:** 
- **Candidate list** sorted by mechanistic_score
- **Click any one** to drill into full analysis

---

### 🧬 Agent 3: MOLECULAR AGENT
**Purpose:** Validate mechanistic overlap at molecular level + GATE CHECK

**Input:** Drug + Candidate disease

**Output:**
```
{
  overlap_score: 0.33 (0-1, higher=more shared targets)
  overlapping_targets: ["PTGS1", "PTGS2"]
  gate_passed: true ✓ (or false ✗ = early exit)
  mechanistic_plausibility: "high" / "moderate" / "low"
  safety_flags: [] (early warnings)
}
```

**For Dashboard:**
- **Score bar** 0-1 (green if high, red if low)
- **Gate badge** ✓/✗ (red if failed = stop here)
- **Shared targets** as list/tags

---

### 🏥 Agent 4: CLINICAL AGENT
**Purpose:** Find clinical trial evidence for drug-disease combo

**Input:** Drug + Disease

**Output:**
```
{
  clinical_evidence_score: 0.65 (0-1)
  trial_phase: 2 (0=preclinical, 4=FDA approved)
  num_trials: 3 (number of clinical trials found)
  num_subjects: 156 (total patients studied)
  primary_outcome_met: true ✓
  serious_adverse_events: [
    { event: "Hypotension", rate: 5%, severity: "moderate" },
    { event: "Renal dysfunction", rate: 2%, severity: "moderate" }
  ]
  contraindications: ["Severe renal impairment", "Active ulcer"]
}
```

**For Dashboard:**
- **Evidence score** as large number (0-1)
- **Trial phase badge** (0, 1, 2, 3, 4)
- **AE table** with frequency & severity
- **CI warning** banner if absolute contraindications

---

### 📚 Agent 5: LITERATURE AGENT
**Purpose:** Mine PubMed for supporting papers

**Input:** Drug + Disease

**Output:**
```
{
  literature_score: 0.68 (0-1)
  publication_count: 9 (papers found)
  evidence_trend: "increasing" / "stable" / "decreasing"
  high_quality_studies: 5 (RCTs & meta-analyses)
  papers: [
    {
      title: "Acetaminophen for the patent ductus arteriosus...",
      pmid: "37169914",
      authors: ["Wright CJ", "McCulley DJ", ...],
      year: 2023,
      journal: "Journal of perinatology",
      entities: [
        { text: "ibuprofen", type: "drug", confidence: 0.95 },
        { text: "PDA", type: "disease", confidence: 0.90 }
      ]
    },
    ...
  ],
  consensus_sentiment: "supportive" / "neutral" / "skeptical"
}
```

**For Dashboard:**
- **Score card** 0-1
- **Publication count** display
- **Trend badge** ↑/→/↓
- **Expandable paper list** with authors, year, journal
- **Sentiment badge** 😊/😐/😔

---

### ⚠️ Agent 6: SAFETY AGENT
**Purpose:** Check for contraindications, adverse events, toxicology

**Input:** Drug + Disease

**Output:**
```
{
  safety_score: 0.65 (0-1, higher=safer)
  overall_risk_level: "low" / "moderate" / "high"
  absolute_contraindications: false (true = HARD NO)
  contraindications: [
    {
      ci: "Severe renal impairment",
      type: "absolute",
      mechanism: "Altered drug clearance"
    },
    {
      ci: "Active peptic ulcer",
      type: "absolute",
      mechanism: "NSAID ulcer exacerbation"
    }
  ],
  adverse_events: [
    { event: "GI bleeding", frequency: 0.08, severity: "severe", age_note: "higher_in_elderly" },
    { event: "Renal dysfunction", frequency: 0.03, severity: "moderate" }
  ],
  organ_toxicity: {
    gastrointestinal: "high_risk" 🔴,
    renal: "moderate_risk" 🟡,
    hepatic: "low_risk" 🟢,
    ...
  },
  drug_interactions: [
    { drug: "Warfarin", interaction: "Increased bleeding", severity: "high" },
    { drug: "ACE inhibitors", interaction: "Reduced BP control", severity: "moderate" }
  ],
  population_risks: {
    elderly: { risk_multiplier: 1.8, concern: "GI bleeding" },
    pregnant: { risk_level: "contraindicated", category: "D" },
    pediatric: { risk_level: "manageable", dose: "weight-based" }
  },
  safety_flags: ["HIGH_GI_BLEEDING_RISK", "RENAL_IMPAIRMENT_CONCERN"]
}
```

**For Dashboard:**
- **Risk level badge** 🟢/🟡/🔴
- **Absolute CI alert** (red banner if true)
- **Organ toxicity icons** (heart: 🔴, kidney: 🟡, etc.)
- **AE table** with frequency & severity
- **CI list** with type & mechanism
- **Drug interaction list** (expandable)
- **Population tabs** (Elderly, Pregnant, Pediatric)

---

### 💰 Agent 7: MARKET AGENT
**Purpose:** Assess commercial opportunity (TAM, competitors, unmet need)

**Input:** Drug + Disease

**Output:**
```
{
  market_opportunity_score: 0.37 (0-1)
  tam_millions: 2.8 ($M total addressable market)
  affected_population: 4000000 (eligible patients globally)
  treatment_rate: 0.95 (95% currently treated)
  unmet_need: 0.20 (20% without adequate treatment)
  unmet_patient_count: 800000
  
  competitors: [
    { drug: "Indomethacin", market_share: 0.45, segment: "First-line" },
    { drug: "Acetaminophen", market_share: 0.35, segment: "Alternative" },
    { drug: "Surgical", market_share: 0.20, segment: "Refractory" }
  ],
  
  competitive_density: 0.65 (0-1, crowded-ness)
  hhi_score: 4200 (concentration: >2500 = monopolistic)
  white_space: "Pediatric formulations, long-acting variants"
  
  market_growth_rate: 0.03 (CAGR 3% annual)
  
  geographic_markets: {
    north_america: { size_millions: 1.2, growth: 0.04 },
    europe: { size_millions: 0.8, growth: 0.02 },
    asia_pacific: { size_millions: 0.6, growth: 0.08 },
    ...
  }
}
```

**For Dashboard:**
- **TAM card** "$2.8M"
- **Pie chart** by competitor market share
- **Unmet need %** large display
- **Growth rate** percentage
- **Competitive density** gauge (crowded?)
- **Geographic breakdown** bar/pie chart

---

### 🛡️ Agent 8: PATENT AGENT
**Purpose:** IP landscape (freedom-to-operate, exclusivity, patentability)

**Input:** Drug + Disease

**Output:**
```
{
  patent_score: 0.52 (0-1)
  patents_found: 0 (total patents for drug)
  
  fto_report: {
    overall_fto_status: "green" / "yellow" / "red"
    blocking_patents: [] (patents preventing operation)
    caution_patents: [] (potentially problematic)
    risk_summary: "LOW RISK: All patents analyzed show no blocking claims"
    hard_veto: false (absolute blocker?)
    recommendations: [
      "Consider novel formulation patents",
      "Explore pediatric indication patents"
    ]
  },
  
  patent_families: [
    {
      patent_id: "WO2023123456",
      invention: "Novel sustained-release ibuprofen",
      countries: ["US", "EP", "JP"],
      expiry: "2043-01-15",
      years_remaining: 17
    }
  ],
  
  exclusivity_window: {
    patent_years: 0,
    market_years: 0,
    total: 0
  },
  
  new_use_patentability: 0.45 (likelihood of patent grant)
  white_space_opportunities: [
    "Combination with other agents",
    "Specific dosing regimen",
    "New formulation (pediatric)"
  ],
  
  cost_to_patent: 50000 ($)
  potential_revenue: 100000000 ($)
}
```

**For Dashboard:**
- **FTO badge** 🟢/🟡/🔴
- **Patent count** badges for blocking/caution/clear
- **Exclusivity timeline** countdown
- **White space opportunities** list
- **Cost/revenue** estimate

---

### 👥 Agent 9: POPULATION AGENT
**Purpose:** Patient stratification (demographics, biomarkers, accessibility)

**Input:** Drug + Disease

**Output:**
```
{
  population_fit_score: 0.83 (0-1)
  
  target_population: "neonates_with_PDA"
  age_range: [0, 1] (years)
  gender_consideratons: { male: 0.9, female: 0.9 }
  demographic_fit: 0.95 (fraction of indication in population)
  eligible_patient_percentage: 0.70 (% of indication eligible)
  
  biomarker_requirements: [
    {
      marker: "Echocardiography",
      threshold: "Presence of PDA shunt",
      availability: "high",
      cost: 500
    },
    {
      marker: "Renal function (creatinine)",
      threshold: "eGFR > 30",
      availability: "standard"
    }
  ],
  
  genetic_factors: [
    {
      factor: "CYP2C8 phenotype",
      impact: "Affects ibuprofen metabolism",
      testing: true
    }
  ],
  
  comorbidity_considerations: [
    {
      comorbidity: "Renal impairment",
      frequency: 0.05,
      impact: "Contraindicated"
    }
  ],
  
  concomitant_medications: [
    { drug: "Antibiotics", interaction: "None", severity: "low" },
    { drug: "ACE inhibitors", interaction: "Reduced BP", severity: "moderate" }
  ],
  
  special_populations: {
    pregnant: { applicable: false, reason: "Post-birth indication" },
    pediatric: { applicable: true, dosing: "Weight-based 4-10 mg/kg" },
    geriatric: { applicable: false },
    renal_impairment: { applicable: false },
    hepatic_impairment: { applicable: true, note: "Use with caution" }
  },
  
  geographic_accessibility: {
    developed_countries: 0.95,
    emerging_markets: 0.60,
    low_income: 0.30
  },
  
  healthcare_infrastructure: {
    required: "Neonatal ICU",
    availability_developed: "High",
    availability_emerging: "Limited"
  }
}
```

**For Dashboard:**
- **Population fit score** 0-1
- **Age/gender** display
- **Eligible %** large number with interpretation
- **Biomarkers** checklist with availability ✓/✗
- **Special populations** tabs (Pregnant, Pediatric, Elderly, etc.)
- **Geography** map or region list with accessibility %
- **Infrastructure** requirement note

---

### 🏆 Agent 10: REASONING AGENT
**Purpose:** Final aggregation, scoring, and tier assignment

**Input:** All 9 agent outputs

**Output:**
```
{
  tier: "TIER_2_PLAUSIBLE" (final classification)
  composite_score: 0.539 (0-1 aggregate)
  confidence: 0.68 (confidence in decision 0-1)
  
  agent_scores: {
    molecular: 0.33,
    clinical: 0.65,
    literature: 0.68,
    safety: 0.67,
    market: 0.37,
    patent: 0.52,
    population: 0.83
  },
  
  agent_weights: {
    molecular: 0.25,    // 25% of formula
    clinical: 0.25,     // 25%
    market: 0.20,       // 20%
    literature: 0.15,   // 15%
    safety: 0.10,       // 10%
    patent: 0.05        // 5%
  },
  
  explanation: {
    summary: "Moderate evidence. Phase 2 trials...",
    strengths: [
      "Mechanistic basis strong",
      "Clinical evidence from Phase 2",
      "Growing literature support",
      "Safe profile in neonates"
    ],
    limitations: [
      "Limited TAM ($2.8M)",
      "Competitive pressure from std care",
      "Phase 2 only, need Phase 3",
      "Patent expired, no exclusivity"
    ],
    recommendation: "Advance to Phase 2/3 trials"
  },
  
  tier_info: {
    tier_name: "TIER_2_PLAUSIBLE",
    tier_description: "Mechanistic and clinical evidence...",
    color: "#FFA500",  // Orange
    action: "Conduct Phase 2/3 trials"
  }
}

// TIER LEGEND:
// TIER_1_APPROVED: Already approved or near-certain (green)
// TIER_2_PLAUSIBLE: Strong evidence, advance trials (orange)  
// TIER_3_EXPLORATORY: Moderate evidence, research needed (blue)
// INSUFFICIENT_EVIDENCE: Limited data (gray)
// REJECT: Not viable, failed gates or safety (red)
```

**For Dashboard:**
- **Large tier badge** with color & description
- **Composite score** as big number 0-1
- **Confidence %** with interpretation
- **Radar/spider chart** showing all 7 agent scores
- **Explanation summary** paragraph
- **Strengths / Limitations** bullets
- **Recommendation** action text
- **Weighted formula** visualization

---

## Quick Reference Table

| Agent | Input | Output | Dashboard Widget |
|-------|-------|--------|------------------|
| Master | Drug name | Profile, targets, approved indications | Header card |
| Discovery | Drug profile | 10 candidate diseases with scores | Ranked list |
| Molecular | Drug + Disease | Target overlap, gate pass/fail | Score bar + badge |
| Clinical | Drug + Disease | Trial phase, AEs, evidence score | Evidence card + table |
| Literature | Drug + Disease | Paper count, trend, sentiment | Stat card + list |
| Safety | Drug + Disease | Risk level, AEs, CIs, organ toxicity | Alert + toxicity grid |
| Market | Drug + Disease | TAM, competitors, unmet need | Charts & gauges |
| Patent | Drug + Disease | FTO status, exclusivity, white space | Badge + timeline |
| Population | Drug + Disease | Eligible %, biomarkers, accessibility | Demographics panel |
| Reasoning | All agents | Composite score, tier, explanation | Final badge + radar |

---

## Example Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│                    IBUPROFEN ANALYSIS               │
│                  5 Drug Candidate Results            │
├─────────────────────────────────────────────────────┤
│                                                      │
│  🔍 SEARCH RESULTS                                  │
│  ┌──────────────────────────────────────────────┐  │
│  │ 1. Patent Ductus Arteriosus  TIER_2 🟡 0.54 │  │ ← Reasoning Agent
│  │    Molecular:0.33 Clinical:0.65 Safety:0.67 │  │ ← Agent scores
│  │    [View Details ➜]                         │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │ 2. Ankylosing Spondylitis  TIER_3 🔵 0.48   │  │ ← Discovery Agent
│  │    Molecular:0.45 Clinical:0.58 Safety:0.55 │  │
│  │    [View Details ➜]                         │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │ 3. Juvenile Idiopathic Arthritis REJECT 🔴  │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
├─────────────────────────────────────────────────────┤
│                  DETAILED VIEW: PDA                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  MASTER AGENT    Chembl: CHEMBL521  Targets: PTGS1,│
│  🟢               PTGS2  Phase: 4 (FDA approved)    │
│                                                      │
│  DISCOVERY       Mechanistic Score: 0.803          │
│  🟡              Shared Targets: PTGS2              │
│                                                      │
│  MOLECULAR       Target Overlap: 33% ████▯▯▯▯    │  ← Distribution
│  🟢              Gate: ✓ PASSED                    │  ← Alert
│                  Shared: PTGS1, PTGS2              │
│                                                      │
│  CLINICAL        Evidence: 0.65 ████▯▯▯▯           │
│  🟡              Phase: 2 | Trials: 3 | n: 156    │
│                  Primary Outcome: ✓ MET            │
│                  Serious AEs: [table...]           │
│                                                      │
│  LITERATURE      Support: 0.68 ████▯▯▯▯           │
│  🟡              Papers: 9 | Trend: ↑ Increasing  │
│                  Sentiment: supportive ✓           │
│                  [View 9 Papers ➜]                 │
│                                                      │
│  SAFETY          Risk: MODERATE 🟡                 │
│  🟡              Absolute CIs: NONE ✓              │
│                  Organs: GI (🔴), Renal (🟡)      │
│                  AEs: [Hypotension 8%, Renal 2%]  │
│                  [View Warnings ➜]                 │
│                                                      │
│  MARKET          Opportunity: 0.37 ███▯▯▯▯▯       │
│  🔴              TAM: $2.8M | Unmet: 20%           │
│                  Competitors: Indomethacin,        │
│                  Acetaminophen, Surgical           │
│                  [View Market Analysis ➜]         │
│                                                      │
│  PATENT          FTO: GREEN ✓ | Score: 0.52      │
│  🟢              Blocking Patents: 0               │
│                  Exclusivity: 0 years              │
│                  White Space: Formulations         │
│                                                      │
│  POPULATION      Fit: 0.83 █████▯▯▯              │
│  🟢              Target: Neonates (0-1 years)     │
│                  Eligible: 70% | Biomarkers: Echo │
│                  [View Population Details ➜]      │
│                                                      │
├─────────────────────────────────────────────────────┤
│  FINAL DECISION: TIER_2_PLAUSIBLE (0.539/1.0)      │
│  Confidence: 68%                                    │
│                                                      │
│  ✓ Strengths: Phase 2 evidence, growing literature│
│  ✗ Limitations: Limited market, competitive       │
│  → Recommendation: Advance to Phase 2/3 trial     │
│                                                      │
│  [View Full Report] [Compare Candidates]          │
└─────────────────────────────────────────────────────┘
```

---

## Data Types Summary

```javascript
// Core data type for each candidate:
Candidate {
  indication: string,                    // Disease name
  mechanistic_score: float 0-1,         // From Discovery
  tier: enum (APPROVED/PLAUSIBLE/etc),  // From Reasoning
  composite_score: float 0-1,           // From Reasoning
  confidence: float 0-1,                // From Reasoning
  
  agent_results: {
    molecular: MolecularReport,
    clinical: ClinicalReport,
    literature: LiteratureReport,
    safety: SafetyReport,
    market: MarketReport,
    patent: PatentReport,
    population: PopulationReport
  }
}

// Standard report structure for most agents:
Report {
  agent: string,
  drug: string,
  indication: string,
  [agent-specific-scores]: float 0-1,
  [agent-specific-data]: {...},
  summary: string,
  timestamp: ISO8601,
  confidence: float 0-1
}
```

This gives you everything you need to build dashboard visualizations! 🎉
