"""
Safety Agent - Comprehensive Safety Signal Detection & Risk Assessment

Ingests clinical, regulatory, post-market, literature and internal safety evidence;
extracts and normalizes adverse events (AEs), PK/PD parameters and toxicity signals;
computes safety feasibility and red-flag lists.

Data Sources:
- ClinicalTrials.gov API
- DailyMed / FDA SPL XML (drug labels)
- FAERS CSVs (post-marketing surveillance)
- PubMed toxicology papers
- Internal documents (PDFs/XLSX)

Key Functions:
- AE extraction and MedDRA mapping
- PK/PD parameter extraction (Cmax, t1/2, AUC)
- Signal detection (PRR/ROR disproportionality)
- Safety feasibility scoring (0-1)
- Red/amber/green flag generation
"""

import os
import re
import json
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, UTC
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
import math

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# LangChain imports with fallback
try:
    from langchain_groq import ChatGroq
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AdverseEvent:
    """Normalized adverse event record"""
    event_id: str
    drug_name: str
    ae_term: str  # Original term
    meddra_term: str  # MedDRA-normalized term
    meddra_code: Optional[str] = None
    severity: Optional[str] = None  # mild, moderate, severe, life-threatening
    frequency: Optional[str] = None  # percentage or count
    source: str = "unknown"  # clinicaltrials, faers, label, pubmed
    dose: Optional[str] = None
    population: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PKPDParameter:
    """Pharmacokinetic/Pharmacodynamic parameters"""
    drug_name: str
    parameter: str  # Cmax, Tmax, t1/2, AUC, CL, Vd
    value: float
    unit: str
    dose: Optional[str] = None
    population: Optional[str] = None
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetySignal:
    """Detected safety signal"""
    signal_id: str
    drug_name: str
    ae_term: str
    signal_type: str  # disproportionality, dose_limiting, boxed_warning, contraindication
    metric: str  # PRR, ROR, frequency
    value: float
    threshold: float
    confidence: float  # 0-1
    evidence_count: int
    source: str
    details: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class SafetyAssessment:
    """Final safety assessment output"""
    drug_name: str
    indication: Optional[str]
    safety_score: float  # 0-1, higher is safer
    safety_transfer_score: Optional[float] = None  # Population-specific transfer score
    hard_stop: bool = False  # Requires human review
    hard_stop_reason: Optional[str] = None
    gate_passed: bool = True  # Stage 3 gate (soft gate - always passes but flags hard_stop)
    risk_level: str = "green"  # green, amber, red
    critical_safety_risk: bool = False
    red_flags: List[str] = field(default_factory=list)
    amber_flags: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)
    adverse_events: List[AdverseEvent] = field(default_factory=list)
    pk_pd_params: List[PKPDParameter] = field(default_factory=list)
    signals: List[SafetySignal] = field(default_factory=list)
    boxed_warnings: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    dose_limiting_toxicities: List[str] = field(default_factory=list)
    summary: str = ""
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class PopulationRiskProfile:
    """
    Population-specific safety thresholds and risk multipliers.
    Master Plan Priority #3: Safety is not a property of a drug in isolation.
    """
    population_type: str  # "general_adult", "terminal_illness", "elderly", "pediatric", etc.
    ae_tolerance: str  # "high", "moderate", "low"
    critical_concerns: List[str]  # What to flag heavily
    acceptable_aes: List[str]  # What's expected/acceptable
    risk_multipliers: Dict[str, float]  # AE category -> multiplier
    
    @staticmethod
    def get_profile(population: str) -> "PopulationRiskProfile":
        """Get population-specific risk profile"""
        profiles = {
            "terminal_illness": PopulationRiskProfile(
                population_type="terminal_illness",
                ae_tolerance="high",
                critical_concerns=["infection_without_immunosuppression"],
                acceptable_aes=["nausea", "fatigue", "hair_loss", "severe_neutropenia"],
                risk_multipliers={
                    "severe": 0.3,  # Severe AEs are acceptable
                    "boxed_warning": 0.5,
                    "contraindication": 0.7
                }
            ),
            "elderly": PopulationRiskProfile(
                population_type="elderly",
                ae_tolerance="low",
                critical_concerns=["qt_prolongation", "fall_risk", "renal_clearance", "cognitive_impairment"],
                acceptable_aes=[],
                risk_multipliers={
                    "qt_prolongation": 3.0,
                    "fall_risk": 2.5,
                    "renal": 2.0,
                    "severe": 1.5
                }
            ),
            "pediatric": PopulationRiskProfile(
                population_type="pediatric",
                ae_tolerance="low",
                critical_concerns=["developmental_toxicity", "growth_impairment", "weight_based_dosing"],
                acceptable_aes=[],
                risk_multipliers={
                    "teratogenicity": 3.0,
                    "developmental": 3.0,
                    "severe": 2.0
                }
            ),
            "women_childbearing": PopulationRiskProfile(
                population_type="women_childbearing",
                ae_tolerance="low",
                critical_concerns=["teratogenicity", "pregnancy_category"],
                acceptable_aes=[],
                risk_multipliers={
                    "teratogenicity": 5.0,  # Absolute veto
                    "pregnancy_risk": 4.0,
                    "severe": 1.5
                }
            ),
            "hepatic_impairment": PopulationRiskProfile(
                population_type="hepatic_impairment",
                ae_tolerance="low",
                critical_concerns=["hepatotoxicity", "liver_enzyme_elevation"],
                acceptable_aes=[],
                risk_multipliers={
                    "hepatotoxicity": 5.0,  # Absolute veto
                    "alt_elevation": 3.0,
                    "severe": 1.5
                }
            ),
            "cardiac_comorbidities": PopulationRiskProfile(
                population_type="cardiac_comorbidities",
                ae_tolerance="low",
                critical_concerns=["qt_prolongation", "qtc_prolongation", "arrhythmia"],
                acceptable_aes=[],
                risk_multipliers={
                    "qt_prolongation": 5.0,  # Hard stop
                    "arrhythmia": 4.0,
                    "severe": 1.5
                }
            ),
            "immunocompromised": PopulationRiskProfile(
                population_type="immunocompromised",
                ae_tolerance="moderate",
                critical_concerns=["opportunistic_infection"],
                acceptable_aes=["immunosuppression", "infection_risk"],  # Expected
                risk_multipliers={
                    "immunosuppression": 0.5,  # Expected, acceptable
                    "infection": 0.7,
                    "severe": 1.2
                }
            ),
            "general_adult": PopulationRiskProfile(
                population_type="general_adult",
                ae_tolerance="moderate",
                critical_concerns=[],
                acceptable_aes=[],
                risk_multipliers={
                    "severe": 1.0,
                    "boxed_warning": 1.0,
                    "contraindication": 1.0
                }
            )
        }
        
        return profiles.get(population, profiles["general_adult"])


# ============================================================================
# MedDRA MAPPER (NER + NORMALIZATION)
# ============================================================================

class MedDRAMapper:
    """Extract and normalize adverse events to MedDRA terms using Groq/OpenAI"""
    
    def __init__(self):
        self.llm = None
        self.use_llm = False
        
        # Try Groq first
        if LANGCHAIN_AVAILABLE and os.getenv("USE_GROQ") == "true" and os.getenv("GROQ_API_KEY"):
            try:
                self.llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    temperature=0.0,
                    api_key=os.getenv("GROQ_API_KEY")
                )
                self.use_llm = True
                logger.info("Using Groq (llama-3.1-8b-instant) for AE extraction and MedDRA mapping")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")
        
        # Fallback to OpenAI
        if not self.use_llm and LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.0,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                self.use_llm = True
                logger.info("Using ChatOpenAI for AE extraction and MedDRA mapping")
            except Exception as e:
                logger.warning(f"Failed to initialize ChatOpenAI: {e}")
        
        if not self.use_llm:
            logger.warning("No LLM API key found, using rule-based AE extraction")
        
        # Lexicon for rule-based fallback
        self.ae_lexicon = {
            "nausea": "Nausea",
            "vomiting": "Vomiting",
            "diarrhea": "Diarrhoea",
            "headache": "Headache",
            "dizziness": "Dizziness",
            "fatigue": "Fatigue",
            "rash": "Rash",
            "hypotension": "Hypotension",
            "hypertension": "Hypertension",
            "tachycardia": "Tachycardia",
            "bradycardia": "Bradycardia",
            "neutropenia": "Neutropenia",
            "thrombocytopenia": "Thrombocytopenia",
            "anemia": "Anaemia",
            "hepatotoxicity": "Hepatotoxicity",
            "nephrotoxicity": "Nephrotoxicity",
            "qT prolongation": "QT prolongation",
            "seizure": "Seizure",
            "confusion": "Confusional state",
            "depression": "Depression",
            "anxiety": "Anxiety",
            "insomnia": "Insomnia",
            "dyspnea": "Dyspnoea",
            "chest pain": "Chest pain",
            "myocardial infarction": "Myocardial infarction",
            "stroke": "Cerebrovascular accident",
            "bleeding": "Haemorrhage",
            "infection": "Infection",
        }
    
    def extract_aes_from_text(self, text: str, drug_name: str, source: str) -> List[AdverseEvent]:
        """Extract adverse events from free text"""
        if self.use_llm:
            return self._llm_extract_aes(text, drug_name, source)
        else:
            return self._lexicon_extract_aes(text, drug_name, source)
    
    def _llm_extract_aes(self, text: str, drug_name: str, source: str) -> List[AdverseEvent]:
        """LLM-based AE extraction"""
        prompt = f"""Extract all adverse events (AEs) from the following text about {drug_name}.

For each AE, provide:
1. ae_term: The adverse event name
2. meddra_term: MedDRA preferred term (if you can map it)
3. severity: mild, moderate, severe, or life-threatening (if mentioned)
4. frequency: percentage or count (if mentioned)

Text:
{text[:2000]}

Return JSON array of objects with keys: ae_term, meddra_term, severity, frequency.
If a field is unknown, use null.
Example: [{{"ae_term": "nausea", "meddra_term": "Nausea", "severity": "mild", "frequency": "15%"}}]
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                ae_list = json.loads(json_match.group(0))
                
                events = []
                for idx, ae_data in enumerate(ae_list):
                    events.append(AdverseEvent(
                        event_id=f"{source}_{drug_name}_{idx}_{datetime.now(UTC).timestamp()}",
                        drug_name=drug_name,
                        ae_term=ae_data.get("ae_term", ""),
                        meddra_term=ae_data.get("meddra_term") or ae_data.get("ae_term", ""),
                        severity=ae_data.get("severity"),
                        frequency=ae_data.get("frequency"),
                        source=source,
                        metadata={"raw_text": text[:500]}
                    ))
                return events
            else:
                logger.warning("No JSON found in LLM response")
                return []
        
        except Exception as e:
            logger.error(f"LLM AE extraction failed: {e}")
            return self._lexicon_extract_aes(text, drug_name, source)
    
    def _lexicon_extract_aes(self, text: str, drug_name: str, source: str) -> List[AdverseEvent]:
        """Rule-based AE extraction using lexicon"""
        text_lower = text.lower()
        events = []
        
        for term, meddra_term in self.ae_lexicon.items():
            if term.lower() in text_lower:
                # Try to extract frequency if present
                freq_pattern = rf"{re.escape(term)}[^\n.]*?(\d+\.?\d*%|\d+/\d+)"
                freq_match = re.search(freq_pattern, text, re.IGNORECASE)
                frequency = freq_match.group(1) if freq_match else None
                
                events.append(AdverseEvent(
                    event_id=f"{source}_{drug_name}_{term}_{datetime.now(UTC).timestamp()}",
                    drug_name=drug_name,
                    ae_term=term,
                    meddra_term=meddra_term,
                    frequency=frequency,
                    source=source,
                    metadata={"extraction_method": "lexicon"}
                ))
        
        return events


# ============================================================================
# PK/PD PARAMETER EXTRACTOR
# ============================================================================

class PKPDExtractor:
    """Extract pharmacokinetic/pharmacodynamic parameters using Groq/OpenAI"""
    
    def __init__(self):
        self.llm = None
        self.use_llm = False
        
        # Try Groq first
        if LANGCHAIN_AVAILABLE and os.getenv("USE_GROQ") == "true" and os.getenv("GROQ_API_KEY"):
            try:
                self.llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    temperature=0.0,
                    api_key=os.getenv("GROQ_API_KEY")
                )
                self.use_llm = True
                logger.info("Using Groq for PK/PD parameter extraction")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")
        
        # Fallback to OpenAI
        if not self.use_llm and LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.0,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                self.use_llm = True
                logger.info("Using ChatOpenAI for PK/PD extraction")
            except Exception as e:
                logger.warning(f"Failed to initialize ChatOpenAI: {e}")
        
        if not self.use_llm:
            logger.warning("No LLM API key found, using rule-based PK/PD extraction")
    
    def extract_parameters(self, text: str, drug_name: str, source: str) -> List[PKPDParameter]:
        """Extract PK/PD parameters from text"""
        if self.use_llm:
            return self._llm_extract_pkpd(text, drug_name, source)
        else:
            return self._regex_extract_pkpd(text, drug_name, source)
    
    def _llm_extract_pkpd(self, text: str, drug_name: str, source: str) -> List[PKPDParameter]:
        """LLM-based PK/PD extraction"""
        prompt = f"""Extract all pharmacokinetic (PK) and pharmacodynamic (PD) parameters from the text about {drug_name}.

Look for:
- Cmax (maximum concentration)
- Tmax (time to maximum concentration)
- t1/2 or half-life
- AUC (area under curve)
- CL (clearance)
- Vd (volume of distribution)
- Bioavailability
- Protein binding

For each parameter, provide:
1. parameter: name (e.g., "Cmax", "t1/2")
2. value: numeric value
3. unit: unit of measurement

Text:
{text[:2000]}

Return JSON array: [{{"parameter": "Cmax", "value": 125, "unit": "ng/mL"}}]
If none found, return empty array [].
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                params_list = json.loads(json_match.group(0))
                
                parameters = []
                for param_data in params_list:
                    parameters.append(PKPDParameter(
                        drug_name=drug_name,
                        parameter=param_data.get("parameter", ""),
                        value=float(param_data.get("value", 0)),
                        unit=param_data.get("unit", ""),
                        source=source,
                        metadata={"extraction_method": "llm"}
                    ))
                return parameters
            else:
                return []
        
        except Exception as e:
            logger.error(f"LLM PK/PD extraction failed: {e}")
            return self._regex_extract_pkpd(text, drug_name, source)
    
    def _regex_extract_pkpd(self, text: str, drug_name: str, source: str) -> List[PKPDParameter]:
        """Regex-based PK/PD extraction"""
        parameters = []
        
        # Pattern: Cmax = 125 ng/mL
        patterns = {
            "Cmax": r"Cmax[:\s=]+(\d+\.?\d*)\s*([a-zA-Z/]+)",
            "Tmax": r"Tmax[:\s=]+(\d+\.?\d*)\s*([a-zA-Z/]+)",
            "t1/2": r"(?:t1/2|half[- ]?life)[:\s=]+(\d+\.?\d*)\s*([a-zA-Z/]+)",
            "AUC": r"AUC[:\s=]+(\d+\.?\d*)\s*([a-zA-Z/*·]+)",
            "CL": r"(?:clearance|CL)[:\s=]+(\d+\.?\d*)\s*([a-zA-Z/]+)",
            "Vd": r"Vd[:\s=]+(\d+\.?\d*)\s*([a-zA-Z/]+)",
        }
        
        for param_name, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.group(1))
                    unit = match.group(2)
                    parameters.append(PKPDParameter(
                        drug_name=drug_name,
                        parameter=param_name,
                        value=value,
                        unit=unit,
                        source=source,
                        metadata={"extraction_method": "regex"}
                    ))
                except (ValueError, IndexError):
                    continue
        
        return parameters


# ============================================================================
# SIGNAL DETECTION ENGINE
# ============================================================================

class SignalDetector:
    """Detect safety signals using disproportionality analysis and thresholds"""
    
    def __init__(self):
        self.prr_threshold = 2.0  # Proportional Reporting Ratio
        self.ror_threshold = 2.0  # Reporting Odds Ratio
        self.min_reports = 3
    
    def compute_disproportionality(
        self,
        drug_ae_count: int,
        drug_total: int,
        ae_total: int,
        grand_total: int
    ) -> Tuple[float, float]:
        """
        Compute PRR and ROR for disproportionality analysis
        
        2x2 contingency table:
                    AE of interest    Other AEs       Total
        Drug of interest    a               b           a+b
        Other drugs         c               d           c+d
        Total              a+c             b+d          N
        
        PRR = (a/(a+b)) / (c/(c+d))
        ROR = (a/c) / (b/d)
        """
        a = drug_ae_count
        b = drug_total - drug_ae_count
        c = ae_total - drug_ae_count
        d = grand_total - drug_total - ae_total + drug_ae_count
        
        # Avoid division by zero
        if b == 0 or d == 0 or c == 0:
            return 0.0, 0.0
        
        prr = (a / (a + b)) / (c / (c + d)) if (c + d) > 0 else 0.0
        ror = (a / c) / (b / d) if c > 0 and d > 0 else 0.0
        
        return prr, ror
    
    def detect_signals(
        self,
        adverse_events: List[AdverseEvent],
        drug_name: str
    ) -> List[SafetySignal]:
        """Detect signals from adverse event data"""
        signals = []
        
        # Group by AE term
        ae_counts = defaultdict(int)
        for ae in adverse_events:
            if ae.drug_name.lower() == drug_name.lower():
                ae_counts[ae.meddra_term] += 1
        
        # Simple frequency-based signal detection
        total_aes = len(adverse_events)
        drug_aes = sum(ae_counts.values())
        
        for ae_term, count in ae_counts.items():
            if count >= self.min_reports:
                # Simplified disproportionality (would need full FAERS data for real PRR/ROR)
                frequency = count / total_aes if total_aes > 0 else 0
                
                # Flag if frequency > 5%
                if frequency > 0.05:
                    signals.append(SafetySignal(
                        signal_id=f"SIG_{drug_name}_{ae_term}_{datetime.now(UTC).timestamp()}",
                        drug_name=drug_name,
                        ae_term=ae_term,
                        signal_type="high_frequency",
                        metric="frequency",
                        value=frequency,
                        threshold=0.05,
                        confidence=min(frequency / 0.1, 1.0),
                        evidence_count=count,
                        source="aggregated",
                        details=f"{ae_term} reported in {count} cases ({frequency*100:.1f}%)"
                    ))
        
        return signals


# ============================================================================
# DATA SOURCE CONNECTORS
# ============================================================================

class ClinicalTrialsConnector:
    """Fetch safety data from ClinicalTrials.gov"""
    
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    
    def fetch_safety_data(self, drug_name: str) -> List[Dict[str, Any]]:
        """Fetch adverse event data from clinical trials"""
        try:
            params = {
                "query.term": drug_name,
                "fields": "NCTId,BriefTitle,Condition,InterventionName,AdverseEventsModule",
                "pageSize": 10
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            studies = data.get("studies", [])
            
            logger.info(f"Fetched {len(studies)} trials for {drug_name}")
            return studies
        
        except Exception as e:
            logger.error(f"Failed to fetch clinical trials data: {e}")
            return []


class DailyMedConnector:
    """Fetch drug labels from DailyMed"""
    
    BASE_URL = "https://dailymed.nlm.nih.gov/dailymed"
    
    def fetch_label(self, drug_name: str) -> Optional[str]:
        """Fetch drug label SPL XML"""
        try:
            # Search for drug
            search_url = f"{self.BASE_URL}/services/v2/spls.json"
            params = {"drug_name": drug_name}
            
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                setid = data["data"][0].get("setid")
                
                # Fetch SPL XML
                spl_url = f"{self.BASE_URL}/services/v2/spls/{setid}.xml"
                spl_response = requests.get(spl_url, timeout=30)
                spl_response.raise_for_status()
                
                logger.info(f"Fetched label for {drug_name}")
                return spl_response.text
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to fetch DailyMed label: {e}")
            return None
    
    def parse_label_warnings(self, xml_content: str) -> Dict[str, List[str]]:
        """Parse boxed warnings and contraindications from SPL XML"""
        warnings = {
            "boxed_warnings": [],
            "contraindications": [],
            "warnings_precautions": []
        }
        
        try:
            # Remove namespace for easier parsing
            xml_content = re.sub(r'xmlns="[^"]+"', '', xml_content)
            root = ET.fromstring(xml_content)
            
            # Find boxed warnings
            for section in root.findall(".//section"):
                code = section.find(".//code")
                if code is not None and code.get("code") == "34066-1":  # BOXED WARNING
                    text = section.find(".//text")
                    if text is not None:
                        warnings["boxed_warnings"].append(ET.tostring(text, method="text", encoding="unicode"))
                
                elif code is not None and code.get("code") == "34070-3":  # CONTRAINDICATIONS
                    text = section.find(".//text")
                    if text is not None:
                        warnings["contraindications"].append(ET.tostring(text, method="text", encoding="unicode"))
            
            return warnings
        
        except Exception as e:
            logger.error(f"Failed to parse label warnings: {e}")
            return warnings


# ============================================================================
# SAFETY SCORING ENGINE
# ============================================================================

class SafetyScorer:
    """Compute safety feasibility score and risk flags"""
    
    def __init__(self):
        self.llm = None
        self.use_llm = False
        
        # Try Groq first
        if LANGCHAIN_AVAILABLE and os.getenv("USE_GROQ") == "true" and os.getenv("GROQ_API_KEY"):
            try:
                self.llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    temperature=0.3,
                    api_key=os.getenv("GROQ_API_KEY")
                )
                self.use_llm = True
                logger.info("Using Groq for safety assessment summarization")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")
        
        # Fallback to OpenAI
        if not self.use_llm and LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.3,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                self.use_llm = True
                logger.info("Using ChatOpenAI for safety assessment")
            except Exception as e:
                logger.warning(f"Failed to initialize ChatOpenAI: {e}")
        
        if not self.use_llm:
            logger.warning("No LLM API key found, using rule-based safety scoring")
    
    def compute_safety_score(
        self,
        adverse_events: List[AdverseEvent],
        signals: List[SafetySignal],
        boxed_warnings: List[str],
        contraindications: List[str],
        population: str = "general_adult"
    ) -> Tuple[float, bool, Optional[str]]:
        """
        Compute population-specific safety transfer score (0-1, higher is safer).
        Master Plan Priority #3: Population-specific thresholds.
        
        Returns:
            (safety_transfer_score, hard_stop, hard_stop_reason)
        """
        profile = PopulationRiskProfile.get_profile(population)
        base_score = 1.0
        hard_stop = False
        hard_stop_reason = None
        
        # Check for absolute veto conditions
        ae_terms_lower = [ae.ae_term.lower() for ae in adverse_events]
        warning_terms_lower = [w.lower() for w in boxed_warnings]
        
        # Cardiac population: QT prolongation = hard stop
        if population == "cardiac_comorbidities":
            if any("qt" in term or "qtc" in term for term in ae_terms_lower + warning_terms_lower):
                hard_stop = True
                hard_stop_reason = "QT/QTc prolongation detected in cardiac population"
                return (0.0, hard_stop, hard_stop_reason)
        
        # Hepatic impairment: Hepatotoxicity = hard stop
        if population == "hepatic_impairment":
            if any("hepat" in term or "liver" in term for term in ae_terms_lower + warning_terms_lower):
                hard_stop = True
                hard_stop_reason = "Hepatotoxicity signal in hepatic impairment population"
                return (0.0, hard_stop, hard_stop_reason)
        
        # Women of childbearing age: Teratogenicity = hard stop
        if population == "women_childbearing":
            if any("terato" in term or "pregnancy" in term for term in ae_terms_lower + warning_terms_lower):
                hard_stop = True
                hard_stop_reason = "Teratogenicity risk in women of childbearing age"
                return (0.0, hard_stop, hard_stop_reason)
        
        # Apply population-specific penalties
        severe_ae_count = sum(1 for ae in adverse_events if ae.severity in ["severe", "life-threatening"])
        severe_multiplier = profile.risk_multipliers.get("severe", 1.0)
        base_score -= min(severe_ae_count * 0.05 * severe_multiplier, 0.4)
        
        # High-confidence signals
        high_conf_signals = sum(1 for s in signals if s.confidence > 0.7)
        base_score -= min(high_conf_signals * 0.1, 0.3)
        
        # Boxed warnings (population-adjusted)
        boxed_multiplier = profile.risk_multipliers.get("boxed_warning", 1.0)
        base_score -= min(len(boxed_warnings) * 0.15 * boxed_multiplier, 0.4)
        
        # Contraindications (population-adjusted)
        contra_multiplier = profile.risk_multipliers.get("contraindication", 1.0)
        base_score -= min(len(contraindications) * 0.1 * contra_multiplier, 0.3)
        
        # Apply critical concern penalties
        for concern in profile.critical_concerns:
            concern_detected = any(concern.replace("_", " ") in ae.ae_term.lower() for ae in adverse_events)
            if concern_detected:
                base_score -= 0.2
                logger.warning(f"Critical concern detected: {concern} in population {population}")
        
        # Boost for terminal illness population (high tolerance)
        if profile.ae_tolerance == "high":
            base_score = min(1.0, base_score + 0.2)
        
        return (max(0.0, min(1.0, base_score)), hard_stop, hard_stop_reason)
    
    def generate_flags(
        self,
        adverse_events: List[AdverseEvent],
        signals: List[SafetySignal],
        boxed_warnings: List[str],
        contraindications: List[str],
        dose_limiting_toxicities: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate red, amber, green flags"""
        red_flags = []
        amber_flags = []
        green_flags = []
        
        # Red flags (critical issues)
        if boxed_warnings:
            red_flags.append(f"Boxed warning present: {len(boxed_warnings)} warning(s)")
        
        if dose_limiting_toxicities:
            red_flags.append(f"Dose-limiting toxicities identified: {len(dose_limiting_toxicities)}")
        
        severe_aes = [ae for ae in adverse_events if ae.severity in ["severe", "life-threatening"]]
        if len(severe_aes) > 10:
            red_flags.append(f"High number of severe AEs: {len(severe_aes)}")
        
        # Amber flags (caution required)
        if contraindications:
            amber_flags.append(f"Contraindications noted: {len(contraindications)}")
        
        high_signals = [s for s in signals if s.confidence > 0.7]
        if high_signals:
            amber_flags.append(f"High-confidence safety signals detected: {len(high_signals)}")
        
        moderate_aes = [ae for ae in adverse_events if ae.severity == "moderate"]
        if len(moderate_aes) > 20:
            amber_flags.append(f"Elevated moderate AE count: {len(moderate_aes)}")
        
        # Green flags (positive safety indicators)
        mild_aes = [ae for ae in adverse_events if ae.severity == "mild"]
        if len(mild_aes) > len(severe_aes) * 3:
            green_flags.append("Predominantly mild adverse events")
        
        if not boxed_warnings and not contraindications:
            green_flags.append("No boxed warnings or contraindications")
        
        if len(signals) == 0:
            green_flags.append("No significant safety signals detected")
        
        return red_flags, amber_flags, green_flags
    
    def generate_summary(
        self,
        drug_name: str,
        indication: Optional[str],
        safety_score: float,
        risk_level: str,
        red_flags: List[str],
        amber_flags: List[str],
        adverse_events: List[AdverseEvent],
        signals: List[SafetySignal]
    ) -> str:
        """Generate natural language safety summary"""
        if self.use_llm:
            return self._llm_generate_summary(
                drug_name, indication, safety_score, risk_level,
                red_flags, amber_flags, adverse_events, signals
            )
        else:
            return self._template_summary(
                drug_name, indication, safety_score, risk_level,
                red_flags, amber_flags, adverse_events, signals
            )
    
    def _llm_generate_summary(
        self,
        drug_name: str,
        indication: Optional[str],
        safety_score: float,
        risk_level: str,
        red_flags: List[str],
        amber_flags: List[str],
        adverse_events: List[AdverseEvent],
        signals: List[SafetySignal]
    ) -> str:
        """LLM-generated summary"""
        prompt = f"""Generate a concise safety assessment summary for {drug_name}{"" if not indication else f" for {indication}"}.

Safety Score: {safety_score:.2f}/1.0 (Risk Level: {risk_level.upper()})

Red Flags:
{chr(10).join(f"- {flag}" for flag in red_flags) if red_flags else "None"}

Amber Flags:
{chr(10).join(f"- {flag}" for flag in amber_flags) if amber_flags else "None"}

Total Adverse Events: {len(adverse_events)}
Safety Signals: {len(signals)}

Provide a 3-4 sentence summary assessing repurposing safety feasibility.
Focus on: major safety concerns, signal strength, and overall risk-benefit outlook.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        
        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
            return self._template_summary(
                drug_name, indication, safety_score, risk_level,
                red_flags, amber_flags, adverse_events, signals
            )
    
    def _template_summary(
        self,
        drug_name: str,
        indication: Optional[str],
        safety_score: float,
        risk_level: str,
        red_flags: List[str],
        amber_flags: List[str],
        adverse_events: List[AdverseEvent],
        signals: List[SafetySignal]
    ) -> str:
        """Template-based summary"""
        summary = f"Safety assessment for {drug_name}"
        if indication:
            summary += f" (repurposing for {indication})"
        summary += f": Safety score {safety_score:.2f}/1.0 (Risk: {risk_level.upper()}). "
        
        if red_flags:
            summary += f"Critical concerns: {len(red_flags)} red flag(s) including {red_flags[0]}. "
        
        if amber_flags:
            summary += f"Caution advised: {len(amber_flags)} amber flag(s). "
        
        summary += f"Analysis based on {len(adverse_events)} adverse events and {len(signals)} safety signals."
        
        return summary


# ============================================================================
# MAIN SAFETY AGENT
# ============================================================================

class SafetyAgent:
    """
    Comprehensive safety signal detection and risk assessment agent
    
    Workflow:
    1. Fetch data from multiple sources (ClinicalTrials, DailyMed, FAERS, PubMed)
    2. Extract and normalize adverse events (MedDRA mapping)
    3. Extract PK/PD parameters
    4. Detect safety signals (disproportionality, dose-limiting toxicities)
    5. Parse boxed warnings and contraindications
    6. Compute safety feasibility score (0-1)
    7. Generate red/amber/green flags
    8. Produce comprehensive assessment with evidence
    """
    
    def __init__(self):
        self.meddra_mapper = MedDRAMapper()
        self.pkpd_extractor = PKPDExtractor()
        self.signal_detector = SignalDetector()
        self.safety_scorer = SafetyScorer()
        self.ct_connector = ClinicalTrialsConnector()
        self.dailymed_connector = DailyMedConnector()
        
        logger.info("SafetyAgent initialized with Groq/OpenAI support")
    
    def run(
        self,
        drug_name: str,
        indication: Optional[str] = None,
        population: str = "general_adult",
        include_sources: List[str] = None
    ) -> SafetyAssessment:
        """
        Run comprehensive safety assessment
        
        Args:
            drug_name: Name of drug to assess
            indication: Target indication (for context)
            include_sources: List of sources to query ["clinicaltrials", "dailymed", "faers", "pubmed"]
        
        Returns:
            SafetyAssessment object with all findings
        """
        if include_sources is None:
            include_sources = ["clinicaltrials", "dailymed"]
        
        logger.info(f"Starting safety assessment for {drug_name}")
        
        # Initialize collections
        all_adverse_events = []
        all_pkpd_params = []
        boxed_warnings = []
        contraindications = []
        dose_limiting_toxicities = []
        evidence_items = []
        
        # 1. Fetch from ClinicalTrials.gov
        if "clinicaltrials" in include_sources:
            logger.info("Fetching clinical trials data...")
            trials = self.ct_connector.fetch_safety_data(drug_name)
            
            for trial in trials:
                nct_id = trial.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "")
                
                # Extract AEs from adverse events module
                ae_module = trial.get("resultsSection", {}).get("adverseEventsModule", {})
                if ae_module:
                    ae_text = json.dumps(ae_module)
                    aes = self.meddra_mapper.extract_aes_from_text(ae_text, drug_name, f"clinicaltrials_{nct_id}")
                    all_adverse_events.extend(aes)
                
                # Store evidence
                evidence_items.append({
                    "source": "clinicaltrials",
                    "id": nct_id,
                    "title": trial.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle", ""),
                    "url": f"https://clinicaltrials.gov/study/{nct_id}"
                })
        
        # 2. Fetch from DailyMed
        if "dailymed" in include_sources:
            logger.info("Fetching drug label from DailyMed...")
            label_xml = self.dailymed_connector.fetch_label(drug_name)
            
            if label_xml:
                # Parse warnings
                warnings = self.dailymed_connector.parse_label_warnings(label_xml)
                boxed_warnings = warnings.get("boxed_warnings", [])
                contraindications = warnings.get("contraindications", [])
                
                # Extract AEs from label
                label_text = label_xml[:10000]  # Limit to first 10k chars
                aes = self.meddra_mapper.extract_aes_from_text(label_text, drug_name, "dailymed_label")
                all_adverse_events.extend(aes)
                
                # Extract PK/PD parameters
                pkpd_params = self.pkpd_extractor.extract_parameters(label_text, drug_name, "dailymed_label")
                all_pkpd_params.extend(pkpd_params)
                
                evidence_items.append({
                    "source": "dailymed",
                    "title": f"{drug_name} Label",
                    "boxed_warnings": len(boxed_warnings),
                    "contraindications": len(contraindications)
                })
        
        # 3. Detect safety signals
        logger.info("Detecting safety signals...")
        signals = self.signal_detector.detect_signals(all_adverse_events, drug_name)
        
        # Identify dose-limiting toxicities (simplified - would need more data)
        severe_aes = [ae for ae in all_adverse_events if ae.severity in ["severe", "life-threatening"]]
        if len(severe_aes) > 5:
            dlt_terms = list(set(ae.meddra_term for ae in severe_aes[:5]))
            dose_limiting_toxicities = dlt_terms
        
        # 4. Compute safety score (population-specific)
        logger.info(f"Computing population-specific safety score (population: {population})...")
        safety_transfer_score, hard_stop, hard_stop_reason = self.safety_scorer.compute_safety_score(
            all_adverse_events,
            signals,
            boxed_warnings,
            contraindications,
            population=population
        )

        # Grade 3+ adverse event veto (unless terminal illness population)
        critical_safety_risk, critical_terms = self._detect_grade3_risk(
            all_adverse_events,
            boxed_warnings
        )
        if critical_safety_risk and population not in ["terminal_illness", "immunocompromised"]:
            safety_transfer_score = min(safety_transfer_score, 0.3)
            logger.warning(f"Critical safety risk detected: {critical_terms}")
        
        # ========== STAGE 3 GATE: SAFETY VETO (SOFT GATE) ==========
        # Unlike Stages 1 & 2 which REJECT/BLOCK, Stage 3 is a "soft gate":
        # - If hard_stop=True: Log warning, flag as ESCALATE_HUMAN_REVIEW, but CONTINUE pipeline
        # - Gate always passes (gate_passed=True) since we don't stop evaluation
        # - Hard stop reasons: black box warnings relevant to patient population
        gate_passed = True  # Soft gate - always continues
        if hard_stop:
            logger.warning(f"⚠️  STAGE 3 SOFT GATE: hard_stop=True for {drug_name} + {indication}")
            logger.warning(f"    Reason: {hard_stop_reason}")
            logger.warning(f"    Decision: ESCALATE to human review but CONTINUE pipeline")
            logger.warning(f"    Population: {population}")
        else:
            logger.info(f"✅ Stage 3 GATE PASSED: No population-critical safety concerns for {drug_name} + {indication}")
        
        # Use safety_transfer_score as the primary score
        safety_score = safety_transfer_score
        
        # Determine risk level
        if safety_score >= 0.7:
            risk_level = "green"
        elif safety_score >= 0.4:
            risk_level = "amber"
        else:
            risk_level = "red"
        
        # 5. Generate flags
        logger.info("Generating risk flags...")
        red_flags, amber_flags, green_flags = self.safety_scorer.generate_flags(
            all_adverse_events,
            signals,
            boxed_warnings,
            contraindications,
            dose_limiting_toxicities
        )

        if critical_safety_risk:
            red_flags.insert(0, f"CRITICAL SAFETY VETO: Grade 3+ AE keywords found ({', '.join(sorted(critical_terms))})")
        
        # 6. Generate summary
        logger.info("Generating safety summary...")
        summary = self.safety_scorer.generate_summary(
            drug_name,
            indication,
            safety_score,
            risk_level,
            red_flags,
            amber_flags,
            all_adverse_events,
            signals
        )
        
        # 7. Construct final assessment
        assessment = SafetyAssessment(
            drug_name=drug_name,
            indication=indication,
            safety_score=safety_score,
            safety_transfer_score=safety_transfer_score,
            hard_stop=hard_stop,
            hard_stop_reason=hard_stop_reason,
            gate_passed=gate_passed,
            risk_level=risk_level,
            critical_safety_risk=critical_safety_risk,
            red_flags=red_flags,
            amber_flags=amber_flags,
            green_flags=green_flags,
            adverse_events=all_adverse_events,
            pk_pd_params=all_pkpd_params,
            signals=signals,
            boxed_warnings=boxed_warnings,
            contraindications=contraindications,
            dose_limiting_toxicities=dose_limiting_toxicities,
            summary=summary,
            evidence_items=evidence_items
        )
        
        logger.info(f"Safety assessment complete: Score={safety_score:.2f}, Risk={risk_level}")
        return assessment

    def _parse_frequency_ratio(self, frequency_text: Optional[str]) -> Optional[float]:
        if not frequency_text:
            return None
        text = frequency_text.strip().lower()
        if text.endswith("%"):
            try:
                return float(text.replace("%", "")) / 100.0
            except ValueError:
                return None
        if "/" in text:
            parts = text.split("/")
            if len(parts) == 2:
                try:
                    numerator = float(parts[0])
                    denominator = float(parts[1])
                    if denominator > 0:
                        return numerator / denominator
                except ValueError:
                    return None
        return None

    def _detect_grade3_risk(
        self,
        adverse_events: List[AdverseEvent],
        boxed_warnings: List[str]
    ) -> Tuple[bool, List[str]]:
        keywords = [
            "hospitalization",
            "disabling",
            "life-threatening",
            "fatal",
            "death",
            "permanent damage",
            "severe liver injury",
            "anaphylaxis",
        ]

        matched_terms = set()

        for warning in boxed_warnings:
            warning_lower = warning.lower()
            for keyword in keywords:
                if keyword in warning_lower:
                    matched_terms.add(keyword)

        for ae in adverse_events:
            ae_text = f"{ae.ae_term} {ae.meddra_term}".lower()
            freq_ratio = self._parse_frequency_ratio(ae.frequency)
            if freq_ratio is None or freq_ratio <= 0.01:
                continue
            for keyword in keywords:
                if keyword in ae_text:
                    matched_terms.add(keyword)

        return (len(matched_terms) > 0), list(matched_terms)
    
    def export_assessment(self, assessment: SafetyAssessment, output_path: str):
        """Export assessment to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(asdict(assessment), f, indent=2, default=str)
        logger.info(f"Assessment exported to {output_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Example usage
    agent = SafetyAgent()
    
    # Test with aspirin
    print("\n" + "="*80)
    print("SAFETY ASSESSMENT: Aspirin for Cardiovascular Disease Prevention")
    print("="*80 + "\n")
    
    assessment = agent.run(
        drug_name="aspirin",
        indication="cardiovascular disease prevention",
        include_sources=["clinicaltrials", "dailymed"]
    )
    
    # Print results
    print(f"\n{'='*80}")
    print(f"Drug: {assessment.drug_name}")
    if assessment.indication:
        print(f"Indication: {assessment.indication}")
    print(f"{'='*80}\n")
    
    print(f"Safety Score: {assessment.safety_score:.2f}/1.0")
    print(f"Risk Level: {assessment.risk_level.upper()}\n")
    
    print(f"RED FLAGS ({len(assessment.red_flags)}):")
    for flag in assessment.red_flags:
        print(f"  ❌ {flag}")
    
    print(f"\nAMBER FLAGS ({len(assessment.amber_flags)}):")
    for flag in assessment.amber_flags:
        print(f"  ⚠️  {flag}")
    
    print(f"\nGREEN FLAGS ({len(assessment.green_flags)}):")
    for flag in assessment.green_flags:
        print(f"  ✅ {flag}")
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(assessment.summary)
    
    print(f"\n{'='*80}")
    print("STATISTICS")
    print(f"{'='*80}")
    print(f"Total Adverse Events: {len(assessment.adverse_events)}")
    print(f"Safety Signals Detected: {len(assessment.signals)}")
    print(f"PK/PD Parameters: {len(assessment.pk_pd_params)}")
    print(f"Boxed Warnings: {len(assessment.boxed_warnings)}")
    print(f"Contraindications: {len(assessment.contraindications)}")
    print(f"Dose-Limiting Toxicities: {len(assessment.dose_limiting_toxicities)}")
    print(f"Evidence Sources: {len(assessment.evidence_items)}")
    
    # Show top 5 AEs
    if assessment.adverse_events:
        print(f"\nTop Adverse Events:")
        ae_counter = Counter(ae.meddra_term for ae in assessment.adverse_events)
        for term, count in ae_counter.most_common(5):
            print(f"  • {term}: {count} reports")
    
    # Show signals
    if assessment.signals:
        print(f"\nSafety Signals:")
        for signal in assessment.signals[:5]:
            print(f"  • {signal.ae_term}: {signal.metric}={signal.value:.3f} (confidence: {signal.confidence:.2f})")
    
    # Export to JSON
    output_file = "safety_assessment_aspirin.json"
    agent.export_assessment(assessment, output_file)
    print(f"\n✅ Full assessment exported to: {output_file}")
    print("\n" + "="*80 + "\n")