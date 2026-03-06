# Dashboard Data Mapping - Agent Output Analysis

## System Overview

The 10-agent system produces **hierarchical, nested JSON data** where:
- **Top Level**: Overall drug analysis result
- **Tier 1**: Drug profile + discovery results
- **Tier 2**: Per-candidate agent results (molecular, clinical, literature, safety, market, patent, population)
- **Tier 3**: Detailed agent-specific data structures

---

## Overall Pipeline Output Structure

```json
{
  "success": true,
  "data": {
    "drug_name": "string",
    "chembl_id": "string",
    "execution_time": "float (seconds)",
    "cache_hit": "boolean",
    "drug_profile": { ... },          ← Master Agent Output
    "discovery_result": { ... },      ← Discovery Agent Output
    "candidates": [                   ← Per-Candidate Analysis
      {
        "indication": "string",
        "tier": "string",             ← Final Tier from Reasoning Agent
        "agent_results": {            ← Individual Agent Outputs
          "molecular": { ... },
          "clinical": { ... },
          "literature": { ... },
          "safety": { ... },
          "market": { ... },
          "patent": { ... },
          "population": { ... }
        }
      }
    ]
  }
}
```

---

## Agent-by-Agent Output Breakdown

### 1. MASTER AGENT Output

**File:** `src/agents/master_agent.py`

**Key Output Section:** `drug_profile`

```json
{
  "drug_profile": {
    "chembl_id": "CHEMBL521",
    "drug_name": "ibuprofen",
    "max_phase": "4.0",                           // Clinical trial phase
    "mechanism_of_action": "Cyclooxygenase inhibitor",
    
    "synonyms": [                                  // All known drug names
      "Advil", "Motrin", "Nurofen", ...
    ],
    
    "known_targets": [                             // Drug-target interactions
      {
        "target_chembl_id": "CHEMBL2094253",
        "target_name": "PTGS2",
        "target_gene_symbol": "PTGS2",
        "action_type": "INHIBITOR",                // INHIBITOR/ACTIVATOR/MODULATOR
        "mechanism_of_action": "Cyclooxygenase inhibitor"
      },
      {
        "target_name": "PTGS1",
        "action_type": "INHIBITOR"
      }
    ],
    
    "approved_indications": [                     // FDA-approved uses
      "Fever", "Pain", "Arthritis", "Dysmenorrhea", 
      "Patent Ductus Arteriosus", ...
    ],
    
    "drug_class": "NSAID"                         // Pharmacological class
  }
}
```

**Dashboard Use:**
- Display drug name, synonyms, targets
- Show approved indications (baseline comparisons)
- Icon/badge for clinical phase

---

### 2. DISCOVERY AGENT Output

**File:** `src/agents/discovery_agent.py`

**Key Output Section:** `discovery_result`

```json
{
  "discovery_result": {
    "candidates_found": 10,                       // Total candidates identified
    
    "top_candidates": [                           // Top 10 ranked by score
      {
        "disease_name": "Patent ductus arteriosus",
        "mechanistic_score": 0.803,               // 0-1 scale
        "linking_targets": ["PTGS2"],             // Shared targets
        "therapeutic_area": "phenotype"
      },
      {
        "disease_name": "ankylosing spondylitis",
        "mechanistic_score": 0.789,
        "linking_targets": ["PTGS2"],
        "therapeutic_area": "Musculoskeletal"
      },
      // ... more candidates
    ]
  }
}
```

**Dashboard Use:**
- **Candidate List View**: Show disease name + mechanistic_score (ranked)
- **Filtering**: Filter by therapeutic_area or mechanistic_score threshold
- **Search**: Jump to specific candidate from discovery

---

### 3. MOLECULAR AGENT Output

**File:** `src/agents/molecular_agent.py`

**Key Output Section:** `candidates[*].agent_results.molecular`

```json
{
  "molecular": {
    "drug": "ibuprofen",
    "indication": "Patent ductus arteriosus",
    
    "overlap_score": 1.0,                         // Target overlap 0-1
    "overlapping_targets": ["PTGS1", "PTGS2"],   // Shared targets
    "drug_targets": ["PTGS1", "PTGS2"],          // All drug targets
    "disease_genes": [                            // All disease-associated genes
      "PTGS2", "PTGS1", "FLNA", "PTGER2", ...
    ],
    
    "mechanistic_plausibility": "high",           // low/moderate/high
    "gate_passed": true,                          // Critical gate decision
    "safety_flags": [],                           // Early safety concerns
    
    "pathways": [                                 // KEGG/Reactome pathways
      "Requires Reactome/KEGG enrichment"
    ],
    
    "directionality_check": {                     // Effect direction match
      "PTGS1": "unknown",
      "PTGS2": "unknown"
    },
    
    "timestamp": "2026-03-04T13:25:22.941530",
    "summary": "Ibuprofen shows high mechanistic plausibility...",
    "gate_threshold_used": 0.08                   // Minimum overlap threshold
  }
}
```

**Dashboard Use:**
- **Card/Widget** displaying:
  - Overlap Score (visual bar: 0-1)
  - Gate Status (✓ PASS or ✗ REJECT)
  - Overlapping targets (list)
  - Mechanistic plausibility (color-coded)
  - Summary text
- **Highlight** if gate_passed = false (early exit)
- **Tooltip** showing safety_flags if any

---

### 4. CLINICAL AGENT Output

**File:** `src/agents/clinical_agent.py`

**Key Output Section:** `candidates[*].agent_results.clinical`

```json
{
  "clinical": {
    "agent": "clinical_agent",
    "drug": "ibuprofen",
    "indication": "Patent ductus arteriosus",
    
    "clinical_evidence_score": 0.65,              // 0-1 evidence strength
    "trial_phase": 2,                             // 0-4 (preclinical to post-market)
    "num_trials": 3,                              // Number of relevant clinical trials
    "num_subjects": 156,                          // Total patients studied
    
    "primary_outcome_met": true,                  // Trial success
    "serious_adverse_events": [
      {
        "adverse_event": "Hypotension",
        "incidence_rate": 0.05,
        "severity": "moderate"
      },
      {
        "adverse_event": "Renal dysfunction",
        "incidence_rate": 0.02,
        "severity": "moderate"
      }
    ],
    
    "adverse_event_severity": "moderate",         // mild/moderate/severe
    "contraindications": [                        // Absolute/relative CIs
      "Severe renal impairment",
      "Active peptic ulcer"
    ],
    
    "patient_population_fit": "General adult, with caution in elderly",
    "dosage_established": true,
    "dosage_range": "200-400 mg every 4-6 hours",
    
    "mechanism_clinical_relevance": 0.75,         // Link strength 0-1
    "confidence": 0.72,                           // Confidence in assessment
    
    "timestamp": "2026-03-04T13:25:38",
    "summary": "Patent ductus arteriosus shows moderate clinical evidence..."
  }
}
```

**Dashboard Use:**
- **Evidence Card**:
  - Clinical evidence score (large number)
  - Trial phase indicator (0-4 badge)
  - Publication count
  - Primary outcome status (✓/✗)
- **Safety Section**:
  - AE severity indicator (color)
  - List of serious adverse events
  - Contraindications warning
- **Population Info**:
  - Compatible populations (text/badge)
  - Dosage range if available

---

### 5. LITERATURE AGENT Output

**File:** `src/agents/literature_agent.py`

**Key Output Section:** `candidates[*].agent_results.literature`

```json
{
  "literature": {
    "agent": "literature_agent",
    "drug": "ibuprofen",
    "indication": "Patent ductus arteriosus",
    
    "literature_score": 0.68,                     // 0-1 evidence support
    "publication_count": 9,                       // Total papers found
    
    "evidence_trend": "increasing",               // increasing/stable/decreasing
    "high_quality_studies": 5,                    // RCT/meta-analysis count
    "author_authority": 0.62,                     // Citation-weighted expertise
    
    "papers": [                                   // Top papers with full metadata
      {
        "record_id": "unique-id",
        "metadata": {
          "pmid": "37169914",
          "doi": "10.1038/s41372-023-01697-2",
          "title": "Acetaminophen for the patent ductus arteriosus...",
          "authors": ["Wright CJ", "McCulley DJ", ...],
          "journal": "Journal of perinatology",
          "publication_date": "2023",
          "url": "https://..."
        },
        "abstract": "Patent ductus arteriosus (PDA) is the most common...",
        "sentences_count": 11,
        
        "claims": [                               // Extracted findings
          {
            "claim_id": "unique-id",
            "text": "ibuprofen exhibits therapeutic potential...",
            "evidence_type": "mechanism",
            "confidence_score": 0.85
          }
        ],
        
        "entities": [                             // NER: drugs, diseases, genes
          {
            "text": "ibuprofen",
            "entity_type": "drug",
            "confidence": 0.95
          },
          {
            "text": "PDA",
            "entity_type": "disease",
            "confidence": 0.90
          }
        ]
      },
      // ... more papers
    ],
    
    "consensus_sentiment": "supportive",          // supportive/neutral/skeptical
    "contradictory_evidence": [],                 // Papers disagreeing
    
    "timestamp": "2026-03-04T13:25:51",
    "summary": "Found 9 publications supporting ibuprofen for PDA..."
  }
}
```

**Dashboard Use:**
- **Literature Score Card**:
  - Score 0-1 with visual bar
  - Publication count
  - Evidence trend (↑ increasing, → stable, ↓ decreasing)
- **Paper List** (expandable):
  - Title, authors, year, journal
  - Click to expand: abstract, entities, claims
  - Confidence badges for entities
- **Consensus Sentiment** badge (supportive/neutral/skeptical)
- **Key Claims** extraction (single-line summaries)

---

### 6. SAFETY AGENT Output

**File:** `src/agents/safety_agent.py`

**Key Output Section:** `candidates[*].agent_results.safety`

```json
{
  "safety": {
    "agent": "safety_agent",
    "drug": "ibuprofen",
    "indication": "Patent ductus arteriosus",
    
    "safety_score": 0.65,                         // 0-1 confidence
    "overall_risk_level": "moderate",             // low/moderate/high
    
    "absolute_contraindications": false,          // Hard veto?
    "contraindications": [                        // Known absolute/relative CIs
      {
        "contraindication": "Severe renal impairment",
        "type": "absolute",
        "mechanism": "Altered drug clearance"
      },
      {
        "contraindication": "Active peptic ulcer",
        "type": "absolute",
        "mechanism": "NSAID-induced ulcer exacerbation"
      },
      {
        "contraindication": "Asthma",
        "type": "relative",
        "mechanism": "NSAID-induced bronchospasm"
      }
    ],
    
    "adverse_events": [                           // Known AEs from FAERS
      {
        "adverse_event": "Gastrointestinal bleeding",
        "frequency": 0.08,                        // 8% of patients
        "severity": "severe",
        "age_factor": "higher_in_elderly"
      },
      {
        "adverse_event": "Renal dysfunction",
        "frequency": 0.03,
        "severity": "moderate"
      },
      {
        "adverse_event": "Hypersensitivity reaction",
        "frequency": 0.01,
        "severity": "moderate"
      }
    ],
    
    "organ_toxicity": {
      "gastrointestinal": "high_risk",            // high/moderate/low_risk
      "renal": "moderate_risk",
      "hepatic": "low_risk",
      "cardiac": "low_risk",
      "neurological": "low_risk"
    },
    
    "drug_interactions": [                        // Known interactions
      {
        "interact_with": "Warfarin",
        "interaction": "Increased bleeding risk",
        "severity": "high"
      },
      {
        "interact_with": "ACE inhibitors",
        "interaction": "Reduced antihypertensive effect",
        "severity": "moderate"
      }
    ],
    
    "population_risks": {
      "elderly": {
        "risk_multiplier": 1.8,                   // 80% higher risk
        "primary_concern": "GI bleeding"
      },
      "pregnant": {
        "risk_level": "contraindicated",
        "pregnancy_category": "D"
      },
      "pediatric": {
        "risk_level": "manageable",
        "special_precautions": "Dose-based on weight"
      }
    },
    
    "safety_flags": [                             // Red flags
      "HIGH_GI_BLEEDING_RISK",
      "RENAL_IMPAIRMENT_CONCERN"
    ],
    
    "confidence": 0.75,
    "timestamp": "2026-03-04T13:25:52",
    "summary": "Moderate safety profile. Main concerns: GI bleeding..."
  }
}
```

**Dashboard Use:**
- **Safety Alert** (top-level):
  - Risk level badge (LOW/MODERATE/HIGH)
  - Absolute CI warning (red banner if true)
- **Safety Score Card**:
  - Score 0-1 with color (green/yellow/red)
  - Overall risk assessment
- **Contraindications** (expandable section):
  - List with type (absolute/relative) and mechanism
  - Red color for absolute, orange for relative
- **Organ Toxicity** (icon grid):
  - Organ name with risk indicator (🟢/🟡/🔴)
  - Hover tooltip with details
- **Adverse Events** (table/list):
  - AE name, frequency (%), severity
  - Age/population factors
- **Drug Interactions** (expandable):
  - Drug name, interaction type, severity
- **Population-Specific Risks**:
  - Tabs: Elderly, Pregnant, Pediatric
  - Custom warnings per population

---

### 7. MARKET AGENT Output

**File:** `src/agents/market_agent.py`

**Key Output Section:** `candidates[*].agent_results.market`

```json
{
  "market": {
    "agent": "market_agent",
    "drug": "ibuprofen",
    "indication": "Patent ductus arteriosus",
    
    "market_opportunity_score": 0.37,             // 0-1 commercial viability
    
    "tam_millions": 2.8,                          // Total addressable market $M
    "affected_population": 4000000,               // Global eligible patients
    "treatment_rate": 0.95,                       // % currently treated
    "current_treatment_cost": 5000,               // Annual cost per patient ($)
    
    "market_confidence": 0.78,                    // Confidence in estimate (0-1)
    "data_sources": [                             // Where data came from
      "PubMed epidemiology",
      "WHO burden of disease",
      "Wikidata"
    ],
    
    "unmet_need": 0.20,                           // % without adequate treatment
    "unmet_patient_count": 800000,                // Absolute number
    
    "competitors": [                              // Market competitors
      {
        "competitor_drug": "Indomethacin",
        "estimated_market_share": 0.45,
        "market_segment": "First-line"
      },
      {
        "competitor_drug": "Acetaminophen",
        "estimated_market_share": 0.35,
        "market_segment": "Alternative"
      },
      {
        "competitor_drug": "Surgical intervention",
        "estimated_market_share": 0.20,
        "market_segment": "Refractory cases"
      }
    ],
    
    "competitive_density": 0.65,                  // 0-1 crowded-ness
    "hhi_score": 4200,                            // Concentration (low=<1500, high=>2500)
    "white_space": "Pediatric formulations, long-acting variants",
    
    "market_growth_rate": 0.03,                   // CAGR (3% annual)
    "pricing_opportunity": "Limited premium potential",
    
    "geographic_markets": {                       // Region breakdown
      "north_america": {
        "market_size_millions": 1.2,
        "growth_rate": 0.04,
        "key_insight": "Mature market, price-sensitive"
      },
      "europe": {
        "market_size_millions": 0.8,
        "growth_rate": 0.02
      },
      "asia_pacific": {
        "market_size_millions": 0.6,
        "growth_rate": 0.08,
        "key_insight": "Emerging market, growth opportunity"
      },
      "rest_of_world": {
        "market_size_millions": 0.2,
        "growth_rate": 0.01
      }
    },
    
    "timestamp": "2026-03-04T13:25:42",
    "summary": "Patent ductus arteriosus market: $2.8M TAM..."
  }
}
```

**Dashboard Use:**
- **Market Opportunity Card**:
  - Score 0-1 (large number)
  - TAM in $M (format: "$2.8M")
  - Treatment rate percentage
- **Market Size Visualization**:
  - Pie chart: Current market by competitor
  - Bar chart: TAM by geography
  - Line chart: Market growth rate
- **Unmet Need** section:
  - % unmet (large number)
  - Absolute patient count if available
- **Competitive Landscape**:
  - Competitor list with market share
  - HHI score interpretation ("Concentrated" vs "Competitive")
- **Growth Projection**:
  - CAGR percentage
  - Regional growth highlights
- **White Space Opportunities**:
  - Text description of gaps

---

### 8. PATENT AGENT Output

**File:** `src/agents/patent_agent.py`

**Key Output Section:** `candidates[*].agent_results.patent`

```json
{
  "patent": {
    "agent": "patent_agent",
    "drug": "ibuprofen",
    "indication": "Patent ductus arteriosus",
    
    "patent_score": 0.52,                         // 0-1 IP opportunity
    "patents_found": 0,                           // Total patents for drug
    
    "fto_report": {                               // Freedom-to-operate analysis
      "report_id": "unique-id",
      "overall_fto_status": "green",              // green/yellow/red
      "risk_summary": "LOW RISK: All 0 patents analyzed show no blocking claims.",
      
      "blocking_patents": [],                     // Patents preventing operation
      "caution_patents": [],                      // Potentially problematic
      "clear_patents": [],                        // Approved for operation
      
      "total_patents_analyzed": 0,
      "hard_veto": false,                         // Absolute blocker?
      "hard_veto_reason": null,
      
      "recommendations": [
        "Consider novel formulation patents",
        "Explore pediatric indication patents"
      ],
      
      "created_at": "2026-03-04T13:25:38"
    },
    
    "patent_families": [                          // Patent families (if any found)
      {
        "family_id": "WO2023123456",
        "invention": "Novel sustained-release ibuprofen formulation",
        "patent_countries": ["US", "EP", "JP"],
        "expiry_date": "2043-01-15",
        "years_remaining": 17,
        "status": "active"
      }
    ],
    
    "exclusivity_window": {
      "patent_exclusivity_years": 0,              // Years exclusive
      "market_exclusivity_years": 0,
      "total_exclusivity_window": 0,
      "key_dates": {}
    },
    
    "new_use_patentability": 0.45,                // Likelihood of patent grant 0-1
    "white_space_opportunities": [
      "Combination with other agents",
      "Specific dosing regimen",
      "New formulation (pediatric)"
    ],
    
    "cost_to_patent": 50000,                      // Estimated cost ($)
    "potential_revenue_from_exclusivity": 100000000,  // Revenue estimate ($)
    
    "timestamp": "2026-03-04T13:25:38",
    "summary": "Patent ductus arteriosus indication has limited patent..."
  }
}
```

**Dashboard Use:**
- **Patent Score Card**:
  - Score 0-1 with interpretation
  - FTO Status badge (GREEN/YELLOW/RED)
- **Freedom-to-Operate**:
  - Risk summary text
  - Blocking patents count (red if > 0)
  - Caution patents count (orange if > 0)
- **Patent Families** (if found):
  - Expiry date with countdown timer
  - Years remaining indicator
- **White Space Opportunities**:
  - Bullet list of unpatented uses
- **IP Strategy**:
  - Patentability % for new use
  - Estimated cost to patent
  - Revenue potential estimate

---

### 9. POPULATION AGENT Output

**File:** `src/agents/population_agent.py`

**Key Output Section:** `candidates[*].agent_results.population`

```json
{
  "population": {
    "agent": "population_agent",
    "drug": "ibuprofen",
    "indication": "Patent ductus arteriosus",
    
    "population_fit_score": 0.83,                 // 0-1 overall fit
    
    "target_population": "neonates_with_PDA",    // Primary population
    "age_range": [0, 1],                          // Years (neonates)
    
    "gender_considerations": {
      "male": 0.9,
      "female": 0.9
    },
    
    "demographic_fit": 0.95,                      // % of indication in population
    "eligible_patient_percentage": 0.70,          // % of indication eligible
    
    "biomarker_requirements": [                   // Required tests/markers
      {
        "biomarker": "Echocardiography",
        "threshold": "Presence of PDA shunt",
        "test_availability": "Standard neonatal care",
        "cost": 500,
        "accessibility": "high"
      },
      {
        "biomarker": "Renal function (creatinine)",
        "threshold": "eGFR > 30 mL/min",
        "accessibility": "standard"
      }
    ],
    
    "genetic_factors": [                          // CYP450, other enzymes
      {
        "factor": "CYP2C8 phenotype",
        "impact": "Affects ibuprofen metabolism",
        "testing_available": true
      }
    ],
    
    "comorbidity_considerations": [               // Common comorbidities
      {
        "comorbidity": "Renal impairment",
        "frequency_in_population": 0.05,
        "impact_on_fit": "Contraindicated",
        "mitigation": "Check renal function"
      },
      {
        "comorbidity": "Hemorrhage risk",
        "frequency_in_population": 0.02,
        "impact_on_fit": "Caution",
        "mitigation": "Monitor PT/INR"
      }
    ],
    
    "concomitant_medications": [                  // Common drugs + interactions
      {
        "medication": "Antibiotics (ampicillin)",
        "interaction": "None known",
        "severity": "low"
      },
      {
        "medication": "ACE inhibitors",
        "interaction": "Reduced BP control",
        "severity": "moderate"
      }
    ],
    
    "special_populations": {
      "pregnant": {
        "applicability": "Not applicable",
        "reason": "Indication occurs post-birth"
      },
      "pediatric": {
        "applicability": "Excellent",
        "special_dosing": "Weight-based (4-10 mg/kg)",
        "safety_profile": "Established"
      },
      "geriatric": {
        "applicability": "Not applicable",
        "reason": "Indication is neonatal"
      },
      "renal_impairment": {
        "applicability": "Contraindicated",
        "clearance": true
      },
      "hepatic_impairment": {
        "applicability": "Use with caution"
      }
    },
    
    "geographic_accessibility": {
      "developed_countries": 0.95,
      "emerging_markets": 0.60,
      "low_income_countries": 0.30
    },
    
    "healthcare_infrastructure": {
      "required_level": "Neonatal ICU",
      "availability_developed": "High",
      "availability_emerging": "Limited",
      "resource_constraints": "Requires specialized care"
    },
    
    "socioeconomic_considerations": "Cost-of-care moderate; neonatal ICU required",
    
    "timestamp": "2026-03-04T13:25:44",
    "summary": "Excellent population fit for neonates in..."
  }
}
```

**Dashboard Use:**
- **Population Fit Score Card**:
  - Score 0-1
  - Target population name
- **Age/Demographics**:
  - Age range display
  - Gender distribution (if applicable)
  - Gender-specific considerations badges
- **Eligible Patient %**:
  - Large percentage display
  - Interpretation: "70% of PDA patients are eligible"
- **Biomarkers Required**:
  - Checklist of tests
  - Availability indicator (high/medium/low)
  - Cost if known
- **Special Populations** (tabbed):
  - Pregnant: Applicability + reason
  - Pediatric: Applicability + special dosing
  - Geriatric: Applicability
  - Renal/Hepatic: Considerations
- **Geographic Accessibility**:
  - World map or region list showing accessibility %
  - Developed vs emerging markets
- **Infrastructure Requirements**:
  - Required care level with availability
  - Resource constraints note

---

### 10. REASONING AGENT Output (Final Decision)

**File:** `src/agents/reasoning_agent.py`

**Key Output Section:** Per-candidate tier + complete aggregation

```json
{
  "tier": "tier_2_plausible",                     // Final tier classification
  "composite_score": 0.539,                       // 0-1 aggregate score
  "confidence": 0.68,                             // Confidence in decision
  
  "agent_scores": {                               // All agent scores aggregated
    "molecular": 0.33,
    "clinical": 0.65,
    "literature": 0.68,
    "safety": 0.67,
    "market": 0.37,
    "patent": 0.52,
    "population": 0.83
  },
  
  "agent_weights": {                              // Weighting formula used
    "molecular": 0.25,
    "clinical": 0.25,
    "literature": 0.15,
    "safety": 0.10,
    "market": 0.20,
    "patent": 0.05,
    "population": 0.00  // Supporting factor only
  },
  
  "explanation": {
    "summary": "Sildenafil shows MODERATE PLAUSIBILITY for Patent Ductus Arteriosus treatment...",
    
    "strengths": [
      "Mechanistic basis: PDE5A inhibition promotes ductus closure via cGMP signaling",
      "Clinical evidence: Phase 2 trials (n~100) showing efficacy",
      "Growing literature: 23 publications with increasing recent interest",
      "Safe profile: Manageable adverse effects in neonatal population"
    ],
    
    "limitations": [
      "Initial market modest: TAM only $2.8M annually",
      "Competitive pressure: Indomethacin/Ibuprofen already standard",
      "Limited long-term data: Phase 2 only, not Phase 3",
      "Patent landscape: Original patent expired, limited exclusivity"
    ],
    
    "recommendation": "ADVANCE TO PHASE 2/3 CLINICAL TRIAL..."
  },
  
  "tier_info": {
    "tier_name": "TIER_2_PLAUSIBLE",
    "tier_description": "Mechanistic and clinical evidence supports further investigation",
    "tier_color": "#FFA500",  // Orange
    "action_recommendation": "Conduct Phase 2/3 trials"
  }
}
```

**Tier Classification Reference:**

```
TIER_1_APPROVED
  ├─ Condition: Indication already in approved_indications OR composite >= 0.85 + safety > 0.8
  └─ Color: 🟢 Green | Action: Monitor / Repurposing already done

TIER_2_PLAUSIBLE  
  ├─ Condition: 0.70 <= composite < 0.85 AND clinical > 0.60 AND literature > 0.50
  └─ Color: 🟡 Orange | Action: Advance to clinical trials

TIER_3_EXPLORATORY
  ├─ Condition: 0.50 <= composite < 0.70 AND molecular > 0.40
  └─ Color: 🔵 Blue | Action: Research needed

INSUFFICIENT_EVIDENCE
  ├─ Condition: 0.30 <= composite < 0.50
  └─ Color: 🟤 Gray | Action: Preliminary data only

REJECT
  ├─ Condition: composite < 0.30 OR safety < 0.4 OR gate_failed OR absolute_contraindication
  └─ Color: 🔴 Red | Action: Not viable
```

**Dashboard Use:**
- **Tier Badge** (large, color-coded):
  - TIER_2_PLAUSIBLE with description
  - Color at top of candidate card
- **Composite Score**:
  - Large number (0.539)
  - Weighted bar showing contribution of each agent
- **Agent Score Breakdown**:
  - Radar chart or horizontal bars
  - Each agent with its score
  - Show weights as annotations
- **Explanation Section**:
  - Summary paragraph
  - Strengths (bullet list)
  - Limitations (bullet list)
  - Recommendation with action
- **Confidence Indicator**:
  - "Moderate Confidence (68%)"
  - Tooltip: "Based on consistency across agents"

---

## Complete Data Example

Here's a **minimal complete example** for a single candidate:

```json
{
  "indication": "Patent ductus arteriosus",
  "mechanistic_score": 0.62,
  "tier": "TIER_2_PLAUSIBLE",
  "composite_score": 0.539,
  "confidence": 0.68,
  
  "agent_scores": {
    "molecular": 0.33,      // Gate: target overlap
    "clinical": 0.65,       // Trial phase + evidence
    "literature": 0.68,     // Publication mining + trend
    "safety": 0.67,         // AE profile + contraindications
    "market": 0.37,         // TAM + unmet need
    "patent": 0.52,         // FTO + exclusivity
    "population": 0.83      // Demographics + biomarkers
  },
  
  "summary": "Moderate evidence. Phase 2 trials show promise. Growing literature support. Manageable safety profile. Limited market but underserved population.",
  
  "key_metrics": {
    "clinical_evidence": "Phase 2, n=100+",
    "publications": 9,
    "adverse_events": "Hypotension (8%), Renal (2%)",
    "market_tam": "$2.8M",
    "patent_fto": "Green (no blocking patents)"
  }
}
```

---

## Dashboard Widget Recommendations

### View 1: **Candidate List View**
```
┌─────────────────────────────────────────────────┐
│  Drug: Ibuprofen  | Candidates: 5/10  Filter ▼  │
├─────────────────────────────────────────────────┤
│                                                   │
│ Patent Ductus Arteriosus          TIER_2 🟡 0.54│
│ ├─ Clinical: 0.65 | Molecular: 0.33              │
│ ├─ Safety: 🟢 (Moderate) | Market: $2.8M        │
│ └─ Action: View Details...                       │
│                                                   │
│ Ankylosing Spondylitis            TIER_3 🔵 0.48│
│ ├─ Clinical: 0.58 | Molecular: 0.45              │
│ └─ Action: View Details...                       │
│                                                   │
│ Juvenile Idiopathic Arthritis     REJECT 🔴 0.22│
│ └─ Reason: Low mechanistic overlap               │
│                                                   │
└─────────────────────────────────────────────────┘
```

### View 2: **Candidate Detail Card**
```
┌────────────────────────────────────────────────────┐
│  Patent Ductus Arteriosus        TIER_2_PLAUSIBLE  │
│  Score: 0.539/1.0  Confidence: 68%                │
├────────────────────────────────────────────────────┤
│                                                     │
│  📊 MOLECULAR ANALYSIS          Score: 0.33 🟢    │
│     Target Overlap: 33% (33/100 threshold)         │
│     Shared Targets: PTGS1, PTGS2                   │
│     Mechanistic Plausibility: HIGH                 │
│     Gate Status: ✓ PASSED                          │
│                                                     │
│  🏥 CLINICAL EVIDENCE           Score: 0.65 🟡    │
│     Trial Phase: 2 (Efficacy signal)               │
│     Publications: 9 papers                         │
│     Primary Outcome: MET ✓                         │
│     AE Severity: Moderate                          │
│                                                     │
│  📚 LITERATURE SUPPORT          Score: 0.68 🟡    │
│     Papers Found: 9                                │
│     Trend: ↑ Increasing (5 recent papers)          │
│     Consensus: SUPPORTIVE ✓                        │
│                                                     │
│  ⚠️  SAFETY ASSESSMENT          Score: 0.67 🟡    │
│     Risk Level: MODERATE                           │
│     Absolute CI: NO ✓                              │
│     AEs: Hypotension (8%), Renal (2%)             │
│                                                     │
│  💰 MARKET OPPORTUNITY          Score: 0.37 🔴    │
│     TAM: $2.8M (specialized market)                │
│     Patients: 4M (95% treatment rate)              │
│     Unmet Need: 20%                                │
│                                                     │
│  🛡️  PATENT STATUS             Score: 0.52 🟡    │
│     FTO: GREEN (no blocking patents)               │
│     Exclusivity: 0 years (drug expired)            │
│     White Space: 3 opportunities                   │
│                                                     │
│  👥 POPULATION FIT              Score: 0.83 🟢    │
│     Primary: Neonates (0-1 years)                  │
│     Eligible: 70% of PDA population                │
│     Biomarkers: Standard (echo)                    │
│                                                     │
├────────────────────────────────────────────────────┤
│  RECOMMENDATION:                                    │
│  Advance to Phase 2/3 clinical trial for efficacy  │
│  confirmation and long-term safety monitoring.     │
│                                                     │
│  [View Full Report] [Compare] [Export]            │
└────────────────────────────────────────────────────┘
```

### View 3: **Comparative Radar Chart**
```
Multi-agent scoring visualization:
- Each axis = agent (Molecular, Clinical, Literature, etc.)
- Candidate shown as polygon overlaid on threshold
- Helps visualize "well-rounded" vs "one-sided" candidates
```

---

## API Endpoint Response Structure

For dashboard integration, the API returns:

```json
GET /discover?drug_name=ibuprofen

{
  "success": true,
  "execution_time": 45.23,
  "cache_hit": false,
  "data": {
    "drug_name": "ibuprofen",
    "all_candidates": [...],      // Full detailed results above
    "summary": {
      "total_candidates": 10,
      "tiers": {
        "approved": 1,             // Count per tier
        "plausible": 3,
        "exploratory": 2,
        "insufficient": 2,
        "reject": 2
      },
      "top_candidates": [...],     // Top 3 across all tiers
      "next_steps": [...]          // Recommendations
    }
  }
}
```

---

## Summary for Dashboard Developers

Each agent produces **specific, quantified outputs**:

| Agent | Key Output | Dashboard Role | Widget Type |
|-------|-----------|-----------------|-------------|
| **Master** | Drug profile, targets | Baseline info | Info card |
| **Discovery** | Candidate list, scores | Initial ranking | List/table |
| **Molecular** | Overlap score, gate | Mechanistic basis | Progress bar |
| **Clinical** | Study data, AEs | Evidence strength | Metric card |
| **Literature** | Paper count, trend | Community consensus | Stat card |
| **Safety** | AE profile, CIs | Risk assessment | Alert panel |
| **Market** | TAM, competitors | Commercial viability | Chart/gauge |
| **Patent** | FTO, exclusivity | IP opportunity | Status badge |
| **Population** | Eligible %, biomarkers | Patient pool | Demographic |
| **Reasoning** | Composite score, tier | Final decision | Large badge |

All data is **JSON-serializable** and ready for React/Vue/Angular dashboards!
