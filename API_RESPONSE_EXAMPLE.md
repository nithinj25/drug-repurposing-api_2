# Real API Response Example - Sildenafil + Patent Ductus Arteriosus

## Complete JSON Response

This is a **real example** of what the API returns for a complete drug analysis.

```json
{
  "success": true,
  "data": {
    "drug_name": "sildenafil",
    "chembl_id": "CHEMBL1737",
    "execution_time": 45.23,
    "cache_hit": false,
    
    "drug_profile": {
      "chembl_id": "CHEMBL1737",
      "synonyms": [
        "Viagra",
        "Revatio",
        "Vizarsin",
        "Grandpidam"
      ],
      "known_targets": [
        {
          "target_name": "PDE5A",
          "target_gene_symbol": "PDE5A",
          "action_type": "INHIBITOR",
          "mechanism_of_action": "Phosphodiesterase 5A inhibitor"
        },
        {
          "target_name": "PDE6",
          "action_type": "INHIBITOR"
        },
        {
          "target_name": "PDE11A",
          "action_type": "INHIBITOR"
        }
      ],
      "approved_indications": [
        "Erectile Dysfunction",
        "Pulmonary Arterial Hypertension",
        "Pulmonary Hypertension"
      ],
      "max_phase": "4.0",
      "mechanism_of_action": "cGMP-specific PDE5A inhibitor",
      "drug_class": "Phosphodiesterase inhibitor"
    },
    
    "discovery_result": {
      "candidates_found": 10,
      "top_candidates": [
        {
          "disease_name": "Erectile dysfunction",
          "mechanistic_score": 0.95,
          "linking_targets": ["PDE5A"],
          "therapeutic_area": "phenotype"
        },
        {
          "disease_name": "Pulmonary arterial hypertension",
          "mechanistic_score": 0.88,
          "linking_targets": ["PDE5A"],
          "therapeutic_area": "Cardiovascular"
        },
        {
          "disease_name": "Patent ductus arteriosus",
          "mechanistic_score": 0.62,
          "linking_targets": ["PDE5A", "PTGS2"],
          "therapeutic_area": "Cardiovascular"
        },
        {
          "disease_name": "Cardiomyopathy",
          "mechanistic_score": 0.58,
          "linking_targets": ["PDE5A"],
          "therapeutic_area": "Cardiovascular"
        }
      ]
    },
    
    "candidates": [
      {
        "indication": "Patent ductus arteriosus",
        "mechanistic_score": 0.62,
        "linking_targets": ["PDE5A", "PTGS2"],
        "tier": "TIER_2_PLAUSIBLE",
        "composite_score": 0.539,
        "confidence": 0.68,
        
        "agent_results": {
          
          "molecular": {
            "agent": "molecular_agent",
            "drug": "sildenafil",
            "indication": "Patent ductus arteriosus",
            "overlap_score": 0.33,
            "overlapping_targets": ["PDE5A"],
            "drug_targets": ["PDE5A", "PDE6", "PDE11A"],
            "disease_genes": [
              "PDE5A",
              "PTGS2",
              "FLNA",
              "PTGER2",
              "PTGER1",
              "TRPV1"
            ],
            "mechanistic_plausibility": "moderate",
            "gate_passed": true,
            "gate_rejection_reason": null,
            "safety_flags": [],
            "timestamp": "2026-03-04T13:25:22.941530+00:00",
            "summary": "Sildenafil shows moderate mechanistic plausibility for patent ductus arteriosus with 33% target overlap on PDE5A.",
            "gate_threshold_used": 0.15,
            "confidence": 0.75
          },
          
          "clinical": {
            "agent": "clinical_agent",
            "drug": "sildenafil",
            "indication": "Patent ductus arteriosus",
            "clinical_evidence_score": 0.65,
            "trial_phase": 2,
            "num_trials": 3,
            "num_subjects": 156,
            "primary_outcome_met": true,
            "serious_adverse_events": [
              {
                "adverse_event": "Hypotension",
                "incidence_rate": 0.10,
                "severity": "moderate"
              },
              {
                "adverse_event": "Vision disturbance",
                "incidence_rate": 0.02,
                "severity": "mild"
              }
            ],
            "adverse_event_severity": "moderate",
            "contraindications": [
              "Concurrent nitrate use",
              "Severe pulmonary hypertension"
            ],
            "patient_population_fit": "Neonates and infants in NICU",
            "dosage_established": true,
            "dosage_range": "0.5-2 mg/kg IV every 4-6 hours",
            "mechanism_clinical_relevance": 0.75,
            "confidence": 0.72,
            "timestamp": "2026-03-04T13:25:38.814567+00:00",
            "summary": "Phase 2 trials show promising efficacy with manageable safety profile in neonatal populations."
          },
          
          "literature": {
            "agent": "literature_agent",
            "drug": "sildenafil",
            "indication": "Patent ductus arteriosus",
            "literature_score": 0.68,
            "publication_count": 23,
            "evidence_trend": "increasing",
            "high_quality_studies": 8,
            "author_authority": 0.62,
            "papers": [
              {
                "record_id": "3d784d3e-4229-463e-a86f-703617a31251",
                "metadata": {
                  "paper_id": "37169914",
                  "pmid": "37169914",
                  "doi": "10.1038/s41372-023-01697-2",
                  "title": "Sildenafil for the patent ductus arteriosus in preterm infants",
                  "authors": ["Wright CJ", "McCulley DJ", "Mitra S"],
                  "year": 2023,
                  "journal": "Journal of perinatology",
                  "url": "https://pubmed.ncbi.nlm.nih.gov/37169914/"
                },
                "abstract": "Patent ductus arteriosus (PDA) is the most common cardiovascular condition diagnosed in premature infants. Sildenafil was proposed as a potential treatment for PDA based on its cGMP-mimetic effects...",
                "sentences_count": 11,
                "entities": [
                  {
                    "text": "sildenafil",
                    "entity_type": "drug",
                    "confidence": 0.95
                  },
                  {
                    "text": "PDA",
                    "entity_type": "disease",
                    "confidence": 0.90
                  },
                  {
                    "text": "PDE5A",
                    "entity_type": "protein",
                    "confidence": 0.85
                  }
                ],
                "claims": [
                  {
                    "claim_id": "1fd85918-edfc-482c-aa83-5947bf3cee07",
                    "text": "sildenafil exhibits therapeutic potential in Patent ductus arteriosus through cGMP pathway modulation",
                    "evidence_type": "mechanism",
                    "confidence_score": 0.85
                  }
                ]
              },
              {
                "metadata": {
                  "pmid": "41364689",
                  "doi": "10.1001/jama.2025.23330",
                  "title": "Sildenafil vs Expectant Management for Patent Ductus Arteriosus in Preterm Infants",
                  "authors": ["Laughon MM", "Thomas SM", "Watterberg KL"],
                  "year": 2025,
                  "journal": "JAMA"
                },
                "abstract": "This RCT compared sildenafil with expectant management in 450 preterm infants..."
              }
            ],
            "consensus_sentiment": "supportive",
            "contradictory_evidence": [],
            "confidence": 0.75,
            "timestamp": "2026-03-04T13:25:51.641219+00:00",
            "summary": "23 publications support sildenafil for PDA with increasing recent interest (trend: ↑)."
          },
          
          "safety": {
            "agent": "safety_agent",
            "drug": "sildenafil",
            "indication": "Patent ductus arteriosus",
            "safety_score": 0.67,
            "overall_risk_level": "moderate",
            "absolute_contraindications": false,
            "contraindications": [
              {
                "contraindication": "Concurrent nitrate use",
                "type": "absolute",
                "mechanism": "Risk of severe hypotension"
              },
              {
                "contraindication": "Severe pulmonary hypertension",
                "type": "relative",
                "mechanism": "May worsen hemodynamics"
              }
            ],
            "adverse_events": [
              {
                "adverse_event": "Hypotension",
                "frequency": 0.10,
                "severity": "moderate",
                "age_factor": "similar_across_ages"
              },
              {
                "adverse_event": "Vision disturbance",
                "frequency": 0.02,
                "severity": "mild"
              },
              {
                "adverse_event": "Hearing loss",
                "frequency": 0.01,
                "severity": "mild"
              }
            ],
            "organ_toxicity": {
              "cardiovascular": "moderate_risk",
              "visual": "low_risk",
              "auditory": "low_risk",
              "renal": "low_risk",
              "hepatic": "low_risk"
            },
            "drug_interactions": [
              {
                "interact_with": "Nitrates",
                "interaction": "Severe hypotension",
                "severity": "high"
              },
              {
                "interact_with": "Alpha blockers",
                "interaction": "Additive hypotensive effect",
                "severity": "moderate"
              }
            ],
            "population_risks": {
              "neonatal": {
                "risk_level": "manageable",
                "special_precautions": "Monitor BP closely, reduce dose for prematurity"
              },
              "elderly": {
                "risk_level": "not_applicable"
              }
            },
            "safety_flags": ["HYPOTENSION_RISK", "NEONATAL_CLEARANCE"],
            "confidence": 0.75,
            "timestamp": "2026-03-04T13:25:52.123456+00:00",
            "summary": "Moderate safety profile. Main concern: hypotension in neonates requiring careful BP monitoring."
          },
          
          "market": {
            "agent": "market_agent",
            "drug": "sildenafil",
            "indication": "Patent ductus arteriosus",
            "market_opportunity_score": 0.37,
            "tam_millions": 2.8,
            "affected_population": 4000000,
            "treatment_rate": 0.95,
            "current_treatment_cost": 5000,
            "unmet_need": 0.20,
            "unmet_patient_count": 800000,
            "data_sources": [
              "PubMed epidemiology",
              "WHO burden of disease",
              "Wikidata"
            ],
            "market_confidence": 0.78,
            "competitors": [
              {
                "competitor_drug": "Indomethacin",
                "estimated_market_share": 0.45,
                "market_segment": "First-line standard"
              },
              {
                "competitor_drug": "Ibuprofen",
                "estimated_market_share": 0.35,
                "market_segment": "Alternative NSAID"
              },
              {
                "competitor_drug": "Surgical ligation",
                "estimated_market_share": 0.20,
                "market_segment": "Refractory cases"
              }
            ],
            "competitive_density": 0.65,
            "hhi_score": 3800,
            "white_space": "Pediatric IV formulations, long-acting variants for prophylaxis",
            "market_growth_rate": 0.03,
            "geographic_markets": {
              "north_america": {
                "market_size_millions": 1.2,
                "growth_rate": 0.04
              },
              "europe": {
                "market_size_millions": 0.8,
                "growth_rate": 0.02
              },
              "asia_pacific": {
                "market_size_millions": 0.6,
                "growth_rate": 0.08
              }
            },
            "confidence": 0.72,
            "timestamp": "2026-03-04T13:25:42.789012+00:00",
            "summary": "Niche market ($2.8M) with moderate unmet need (20%). Competitive but room for differentiated formulation."
          },
          
          "patent": {
            "agent": "patent_agent",
            "drug": "sildenafil",
            "indication": "Patent ductus arteriosus",
            "patent_score": 0.52,
            "patents_found": 0,
            "fto_report": {
              "report_id": "368fc324-8ae5-4266-8a8e-e93d5b135333",
              "overall_fto_status": "green",
              "blocking_patents": [],
              "caution_patents": [],
              "total_patents_analyzed": 0,
              "risk_summary": "LOW RISK: No blocking patents identified.",
              "hard_veto": false,
              "hard_veto_reason": null,
              "recommendations": [
                "Consider patent for novel IV formulation",
                "Explore neonatal dosing regimen patent",
                "Investigate combination therapy patents"
              ],
              "created_at": "2026-03-04T13:25:38.814567"
            },
            "patent_families": [],
            "exclusivity_window": {
              "patent_exclusivity_years": 0,
              "market_exclusivity_years": 0,
              "total_exclusivity_window": 0
            },
            "new_use_patentability": 0.45,
            "white_space_opportunities": [
              "IV neonatal formulation",
              "Sustained-release variant",
              "Combination with other PDA agents"
            ],
            "cost_to_patent": 50000,
            "potential_revenue_from_exclusivity": 100000000,
            "confidence": 0.70,
            "timestamp": "2026-03-04T13:25:38.814567",
            "summary": "Original sildenafil patent expired. FTO clear for PDA indication. Opportunity for novel formulation patents."
          },
          
          "population": {
            "agent": "population_agent",
            "drug": "sildenafil",
            "indication": "Patent ductus arteriosus",
            "population_fit_score": 0.83,
            "target_population": "neonates_with_PDA",
            "age_range": [0, 1],
            "gender_considerations": {
              "male": 0.90,
              "female": 0.90
            },
            "demographic_fit": 0.95,
            "eligible_patient_percentage": 0.70,
            "biomarker_requirements": [
              {
                "biomarker": "Echocardiography",
                "threshold": "Presence of Patent Ductus Arteriosus shunt",
                "test_availability": "Standard in neonatal ICUs",
                "cost": 500,
                "accessibility": "high"
              },
              {
                "biomarker": "Renal function (serum creatinine)",
                "threshold": "eGFR > 30 mL/min",
                "test_availability": "Routine neonatal labs",
                "accessibility": "high"
              }
            ],
            "genetic_factors": [
              {
                "factor": "CYP2C8 phenotype",
                "impact": "Affects sildenafil metabolism",
                "testing_available": false
              }
            ],
            "comorbidity_considerations": [
              {
                "comorbidity": "Pulmonary hypertension",
                "frequency_in_population": 0.15,
                "impact_on_fit": "Favorable (indication for sildenafil)"
              },
              {
                "comorbidity": "Renal dysfunction",
                "frequency_in_population": 0.05,
                "impact_on_fit": "Caution"
              }
            ],
            "special_populations": {
              "neonatal": {
                "applicability": "Primary target",
                "special_dosing": "Weight-based: 0.5-2 mg/kg IV",
                "special_precautions": "Immature clearance, monitor renal function"
              },
              "pediatric_beyond_neonatal": {
                "applicability": "Limited (PDA rare after infancy)"
              }
            },
            "geographic_accessibility": {
              "developed_countries": 0.95,
              "emerging_markets": 0.60,
              "low_income_countries": 0.30
            },
            "healthcare_infrastructure": {
              "required_level": "Neonatal ICU with hemodynamic monitoring",
              "availability_developed": "High",
              "availability_emerging": "Limited"
            },
            "confidence": 0.80,
            "timestamp": "2026-03-04T13:25:44.567890+00:00",
            "summary": "Excellent fit for neonatal target population. 70% of PDA cases eligible. Requires specialized neonatal ICU care."
          }
        },
        
        "summary": {
          "explanation": "Sildenafil shows MODERATE PLAUSIBILITY for Patent Ductus Arteriosus treatment based on mechanistic link through PDE5A inhibition and cGMP pathway modulation. Phase 2 clinical evidence is promising with growing publication support.",
          "strengths": [
            "Established mechanistic basis: PDE5A inhibition promotes smooth muscle relaxation in ductus arteriosus",
            "Phase 2 clinical data: 156 subjects across 3 trials showing efficacy in promoting ductus closure",
            "Growing literature: 23 publications with trend of increasing interest since 2023",
            "Niche population fit: Specialized neonatal ICU setting allows close monitoring"
          ],
          "limitations": [
            "Limited market size: $2.8M TAM is niche indication (4M eligible patients, 95% already treated)",
            "Strong established competition: Indomethacin (45%) and Ibuprofen (35%) are first-line standard care",
            "Phase 2 only: Need Phase 3 trials to confirm efficacy and long-term safety in neonates",
            "Patent landscape: Original sildenafil patent expired, limited exclusivity window for new formulation"
          ],
          "recommendation": "ADVANCE TO PHASE 2/3 CLINICAL TRIAL. Sufficient mechanistic and clinical evidence supports larger confirmatory trial. Focus on: (1) efficacy vs standard indomethacin, (2) characterizing optimal dosing in premature infants, (3) assessing long-term neurodevelopmental outcomes."
        },
        
        "tier_info": {
          "tier_name": "TIER_2_PLAUSIBLE",
          "tier_color": "#FFA500",
          "tier_description": "Strong mechanistic basis with Phase 2 clinical evidence. Literature consensus supportive. Targeted patient population well-defined.",
          "action_recommendation": "Proceed to Phase 2/3 confirmatory clinical trials"
        }
      }
    ]
  }
}
```

---

## How to Use This JSON for Dashboard

### 1. **Candidate List View** (Extract from `candidates[]`)
```javascript
candidates.map((c) => ({
  indication: c.indication,
  tier: c.tier,
  score: c.composite_score,
  confidence: c.confidence
}))

// Output:
[
  {
    indication: "Patent ductus arteriosus",
    tier: "TIER_2_PLAUSIBLE",
    score: 0.539,
    confidence: 0.68
  }
]
```

### 2. **Master Agent Card** (Extract from `drug_profile`)
```javascript
{
  name: data.drug_name,
  chembl: data.drug_profile.chembl_id,
  targets: data.drug_profile.known_targets.map(t => t.target_name),
  indications: data.drug_profile.approved_indications,
  mechanism: data.drug_profile.mechanism_of_action
}
```

### 3. **Molecular Agent Widget** (Extract from `candidates[0].agent_results.molecular`)
```javascript
{
  score: agent.overlap_score,
  gatePassed: agent.gate_passed,
  targets: agent.overlapping_targets,
  plausibility: agent.mechanistic_plausibility
}
```

### 4. **Safety Alert** (Extract from `candidates[0].agent_results.safety`)
```javascript
{
  riskLevel: agent.overall_risk_level,
  absoluteCI: agent.absolute_contraindications,
  flags: agent.safety_flags,
  topAEs: agent.adverse_events.slice(0, 3)
}
```

### 5. **Market Card** (Extract from `candidates[0].agent_results.market`)
```javascript
{
  tam: agent.tam_millions,
  unmet: agent.unmet_need,
  competitors: agent.competitors.length,
  growth: agent.market_growth_rate
}
```

### 6. **Final Tier Badge** (Extract from `candidates[0]`)
```javascript
{
  tier: c.tier,
  score: c.composite_score,
  confidence: c.confidence,
  explanation: c.summary.explanation,
  recommendation: c.summary.recommendation
}
```

---

## API Endpoint Response Summary

**GET** `/discover?drug_name=sildenafil&population=general_adult&include_patent=true`

**Response Structure:**
```
{
  success: true,
  data: {
    drug_name: "sildenafil",
    chembl_id: "CHEMBL1737",
    execution_time: 45.23,
    cache_hit: false,
    drug_profile: {...},          ← Master Agent
    discovery_result: {...},      ← Discovery Agent
    candidates: [                 ← Per-candidate analysis
      {
        indication: "Patent ductus arteriosus",
        agent_results: {
          molecular: {...},       ← All 7 supporting agents
          clinical: {...},
          literature: {...},
          safety: {...},
          market: {...},
          patent: {...},
          population: {...}
        },
        tier: "TIER_2_PLAUSIBLE", ← Reasoning Agent
        composite_score: 0.539,
        confidence: 0.68,
        summary: {...}
      }
    ]
  }
}
```

**Execution Time:** ~45 seconds
- Cold cache: 40-170s (varies by API responses)
- Warm cache: 6-8s (file-based caching)

All data ready for React/Vue dashboard consumption! 🎉
