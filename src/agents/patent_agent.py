"""
Patent Intelligence Agent

Purpose: Automatically discover, parse, classify, and analyze patent claims to assess
Freedom-to-Operate (FTO) for drug repurposing, producing structured patent records
with claim-level provenance and risk triage.

Architecture:
    Patent Source Connectors → Document Parser → Claim Extractor → 
    NLP Classification (LangChain) → FTO Analysis → Patent Family Resolver →
    Indexing (FAISS) → API/Worker Interface
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import uuid
import logging
import requests
import json
from abc import ABC, abstractmethod
import os
import re

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LangChain imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_groq import ChatGroq
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from sentence_transformers import SentenceTransformer
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class ClaimType(str, Enum):
    """Patent claim classification types"""
    COMPOSITION = "composition"  # Chemical composition claims
    METHOD_OF_USE = "method_of_use"  # Therapeutic use claims
    FORMULATION = "formulation"  # Dosage form, excipients
    MANUFACTURING = "manufacturing"  # Process/synthesis claims
    POLYMORPH = "polymorph"  # Crystal forms, salts
    COMBINATION = "combination"  # Drug combinations
    DOSAGE_REGIMEN = "dosage_regimen"  # Dosing schedules
    OTHER = "other"


class FTOStatus(str, Enum):
    """Freedom-to-Operate triage status"""
    GREEN = "green"  # Clear - no blocking claims
    AMBER = "amber"  # Caution - potential conflict
    RED = "red"  # Blocked - high risk claims


class LegalStatus(str, Enum):
    """Patent legal status"""
    PENDING = "pending"
    GRANTED = "granted"
    EXPIRED = "expired"
    ABANDONED = "abandoned"
    REVOKED = "revoked"
    LAPSED = "lapsed"


@dataclass
class PatentClaim:
    """Individual patent claim with classification"""
    claim_id: str
    claim_number: int  # Claim 1, 2, 3...
    claim_text: str
    claim_type: ClaimType
    is_independent: bool  # Independent vs dependent claim
    depends_on: Optional[List[int]] = None  # Dependency chain
    fto_relevance_score: float = 0.0  # 0.0-1.0, how relevant to target drug
    blocking_risk: FTOStatus = FTOStatus.GREEN
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['claim_type'] = self.claim_type.value
        data['blocking_risk'] = self.blocking_risk.value
        return data


@dataclass
class PatentFamily:
    """Patent family metadata (INPADOC family)"""
    family_id: str
    family_members: List[str]  # List of patent numbers
    priority_date: Optional[str] = None
    earliest_filing_date: Optional[str] = None
    jurisdictions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PatentRecord:
    """Complete patent record with claims and metadata"""
    patent_id: str  # USPTO patent number or EPO/WO number
    record_id: str  # Internal UUID
    title: str
    abstract: str
    filing_date: Optional[str] = None
    publication_date: Optional[str] = None
    grant_date: Optional[str] = None
    expiry_date: Optional[str] = None
    legal_status: LegalStatus = LegalStatus.PENDING
    applicants: List[str] = field(default_factory=list)
    inventors: List[str] = field(default_factory=list)
    assignee: Optional[str] = None
    classification_codes: List[str] = field(default_factory=list)  # IPC/CPC codes
    claims: List[PatentClaim] = field(default_factory=list)
    description: str = ""
    patent_family: Optional[PatentFamily] = None
    source_registry: str = "USPTO"  # USPTO, EPO, WIPO, etc.
    pdf_url: Optional[str] = None
    fto_summary: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['legal_status'] = self.legal_status.value
        data['claims'] = [c.to_dict() for c in self.claims]
        if self.patent_family:
            data['patent_family'] = self.patent_family.to_dict()
        data['created_at'] = self.created_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        data['embedding_present'] = self.embedding is not None and len(self.embedding) > 0
        del data['embedding']  # Don't serialize full embedding
        return data


@dataclass
class FTOReport:
    """Freedom-to-Operate analysis report"""
    report_id: str
    drug_name: str
    indication: str
    overall_fto_status: FTOStatus
    blocking_patents: List[str]  # Patent IDs with RED status
    caution_patents: List[str]  # Patent IDs with AMBER status
    clear_patents: List[str]  # Patent IDs with GREEN status
    total_patents_analyzed: int
    risk_summary: str
    recommendations: List[str] = field(default_factory=list)
    # NEW: Stage 2 gate fields
    hard_veto: bool = False  # True if blocking patent exists with expiry > 2 years
    hard_veto_reason: Optional[str] = None
    blocking_patent_expiry_date: Optional[str] = None  # Earliest expiry of blocking patents
    gate_passed: bool = True  # False if hard_veto=True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['overall_fto_status'] = self.overall_fto_status.value
        data['created_at'] = self.created_at.isoformat()
        return data


# ============================================================================
# Patent Source Connectors
# ============================================================================

class PatentSourceConnector(ABC):
    """Base class for patent database connectors"""
    
    def __init__(self, name: str):
        self.name = name
        self.base_url = ""
    
    @abstractmethod
    def search(self, drug_name: str, chemical_class: str = "", limit: int = 10) -> List[Dict]:
        """Search patent database for drug/chemical"""
        pass
    
    @abstractmethod
    def fetch_patent_details(self, patent_id: str) -> Dict:
        """Fetch full patent document with claims"""
        pass


class USPTOConnector(PatentSourceConnector):
    """Connector to USPTO PatentsView API"""
    
    def __init__(self):
        super().__init__("USPTO")
        self.base_url = "https://api.patentsview.org/patents/query"
    
    def search(self, drug_name: str, chemical_class: str = "", limit: int = 10) -> List[Dict]:
        """Search USPTO for drug-related patents"""
        logger.info(f"Searching USPTO for {drug_name}")

        try:
            fields = [
                "patent_number",
                "patent_title",
                "patent_abstract",
                "patent_date",
                "patent_type",
                "patent_kind",
                "patent_num_claims",
                "assignee_organization",
                "inventor_first_name",
                "inventor_last_name",
                "ipc_section",
                "ipc_class",
                "ipc_subclass",
            ]

            query = {
                "_or": [
                    {"_text_phrase": {"patent_title": drug_name}},
                    {"_text_phrase": {"patent_abstract": drug_name}},
                ]
            }

            params = {
                "q": json.dumps(query),
                "f": json.dumps(fields),
                "o": json.dumps({"per_page": max(1, min(limit, 100))}),
            }

            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            patents = payload.get("patents", [])

            normalized = []
            for p in patents:
                inventors = []
                if p.get("inventor_first_name") and p.get("inventor_last_name"):
                    inventors.append(f"{p.get('inventor_last_name')}, {p.get('inventor_first_name')}")

                ipc_classes = []
                ipc_section = p.get("ipc_section")
                ipc_class = p.get("ipc_class")
                ipc_subclass = p.get("ipc_subclass")
                if ipc_section and ipc_class and ipc_subclass:
                    ipc_classes.append(f"{ipc_section}{ipc_class}{ipc_subclass}")

                normalized.append({
                    "patent_number": p.get("patent_number"),
                    "patent_title": p.get("patent_title", ""),
                    "patent_abstract": p.get("patent_abstract", ""),
                    "patent_date": p.get("patent_date"),
                    "assignee_organization": p.get("assignee_organization"),
                    "inventors": inventors,
                    "ipc_classes": ipc_classes,
                    "legal_status": "granted",
                })

            return normalized
        except Exception as e:
            logger.warning(f"USPTO PatentsView search failed: {e}")
            return []
    
    def fetch_patent_details(self, patent_id: str) -> Dict:
        """Fetch full patent with claims"""
        logger.info(f"Fetching USPTO patent {patent_id}")

        return {
            "patent_number": patent_id,
            "claims": [],
            "description": "",
            "pdf_url": f"https://patents.google.com/patent/{patent_id}/en",
        }


class EPOConnector(PatentSourceConnector):
    """Connector to European Patent Office (EPO) Open Patent Services"""
    
    def __init__(self):
        super().__init__("EPO")
        self.base_url = "https://ops.epo.org/3.2/rest-services"
    
    def search(self, drug_name: str, chemical_class: str = "", limit: int = 10) -> List[Dict]:
        """Search EPO for patents"""
        logger.info(f"Searching EPO for {drug_name}")
        # Mock implementation
        return []
    
    def fetch_patent_details(self, patent_id: str) -> Dict:
        """Fetch EPO patent details"""
        return {}


class WIPOConnector(PatentSourceConnector):
    """Connector to WIPO PATENTSCOPE"""
    
    def __init__(self):
        super().__init__("WIPO")
        self.base_url = "https://patentscope.wipo.int/search/en/search.jsf"
    
    def search(self, drug_name: str, chemical_class: str = "", limit: int = 10) -> List[Dict]:
        """Search WIPO PATENTSCOPE"""
        logger.info(f"Searching WIPO for {drug_name}")
        return []
    
    def fetch_patent_details(self, patent_id: str) -> Dict:
        """Fetch WIPO patent details"""
        return {}


# ============================================================================
# Claim Extraction and Parsing
# ============================================================================

class ClaimParser:
    """Parse patent claims from text, identify dependencies"""
    
    def __init__(self):
        self.claim_pattern = re.compile(r'(\d+)\.\s+(.*?)(?=\n\d+\.|$)', re.DOTALL)
        self.dependency_pattern = re.compile(r'\bclaim[s]?\s+(\d+(?:\s*(?:,|and|or)\s*\d+)*)', re.IGNORECASE)
    
    def parse_claims(self, claims_text: str) -> List[Dict]:
        """Extract individual claims with numbering"""
        claims = []
        
        matches = self.claim_pattern.findall(claims_text)
        for claim_num, claim_text in matches:
            claim_text = claim_text.strip()
            
            # Detect dependencies
            is_independent = not any(word in claim_text.lower()[:50] for word in ['claim', 'according to'])
            depends_on = self._extract_dependencies(claim_text) if not is_independent else []
            
            claims.append({
                'claim_number': int(claim_num),
                'claim_text': claim_text,
                'is_independent': is_independent,
                'depends_on': depends_on,
            })
        
        return claims
    
    def _extract_dependencies(self, claim_text: str) -> List[int]:
        """Extract claim numbers this claim depends on"""
        deps = []
        match = self.dependency_pattern.search(claim_text)
        if match:
            dep_str = match.group(1)
            deps = [int(n) for n in re.findall(r'\d+', dep_str)]
        return deps


# ============================================================================
# NLP Classification with LangChain
# ============================================================================

class ClaimClassifier:
    """Classify patent claims using LangChain ChatOpenAI + fallback rules"""
    
    def __init__(self):
        # Initialize LangChain LLM for claim classification
        self.use_llm = False
        self.llm = None
        
        # Try Groq first if enabled
        if LANGCHAIN_AVAILABLE and os.getenv("USE_GROQ") and os.getenv("GROQ_API_KEY"):
            try:
                self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
                self.use_llm = True
                logger.info("ClaimClassifier: Using Groq (llama-3.1-8b-instant) for classification")
            except Exception as e:
                logger.warning(f"ClaimClassifier: Failed to initialize Groq: {e}")
        
        # Fallback to OpenAI if Groq not available
        if not self.use_llm and LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
                self.use_llm = True
                logger.info("ClaimClassifier: Using ChatOpenAI for classification")
            except Exception as e:
                logger.warning(f"ClaimClassifier: Failed to initialize ChatOpenAI: {e}")
        
        if not self.use_llm:
            logger.warning("ClaimClassifier: No LLM API key, using rule-based fallback")
        
        # Rule-based keyword patterns for fallback
        self.claim_patterns = {
            ClaimType.COMPOSITION: ['composition', 'comprising', 'compound', 'formula', 'chemical structure'],
            ClaimType.METHOD_OF_USE: ['method of treating', 'method of use', 'therapeutic', 'treatment', 'administering'],
            ClaimType.FORMULATION: ['formulation', 'dosage form', 'tablet', 'capsule', 'excipient', 'carrier'],
            ClaimType.MANUFACTURING: ['process', 'method of making', 'synthesis', 'manufacturing', 'preparation'],
            ClaimType.POLYMORPH: ['polymorph', 'crystal form', 'salt form', 'isomer', 'crystalline'],
            ClaimType.COMBINATION: ['combination', 'co-administration', 'together with', 'further comprising'],
            ClaimType.DOSAGE_REGIMEN: ['dosage', 'regimen', 'dose', 'frequency', 'administration schedule'],
        }
    
    def classify_claim(self, claim_text: str, drug_name: str) -> Tuple[ClaimType, float]:
        """Classify claim type with confidence score"""
        if self.use_llm:
            return self._llm_classify(claim_text, drug_name)
        else:
            return self._rule_classify(claim_text)
    
    def _llm_classify(self, claim_text: str, drug_name: str) -> Tuple[ClaimType, float]:
        """Use LLM to classify claim type"""
        prompt = f"""Classify the following patent claim into one of these categories:
- composition: Chemical composition or compound structure claims
- method_of_use: Therapeutic use or treatment method claims
- formulation: Dosage form, excipient, or formulation claims
- manufacturing: Process or synthesis method claims
- polymorph: Crystal form, salt, or polymorph claims
- combination: Drug combination or co-administration claims
- dosage_regimen: Dosing schedule or regimen claims
- other: Other types

Claim: {claim_text[:500]}

Return ONLY the category name (e.g., "method_of_use"), no additional text."""
        
        try:
            response = self.llm.invoke(prompt)
            category = response.content.strip().lower()
            
            # Map to ClaimType enum
            for claim_type in ClaimType:
                if claim_type.value in category:
                    return claim_type, 0.9  # High confidence for LLM
            
            return ClaimType.OTHER, 0.5
        
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}, using rule-based fallback")
            return self._rule_classify(claim_text)
    
    def _rule_classify(self, claim_text: str) -> Tuple[ClaimType, float]:
        """Rule-based classification using keywords"""
        claim_lower = claim_text.lower()
        
        # Count keyword matches for each type
        scores = {}
        for claim_type, keywords in self.claim_patterns.items():
            score = sum(1 for kw in keywords if kw in claim_lower)
            if score > 0:
                scores[claim_type] = score
        
        if scores:
            best_type = max(scores, key=scores.get)
            confidence = min(scores[best_type] * 0.2, 0.8)  # Cap at 0.8 for rules
            return best_type, confidence
        
        return ClaimType.OTHER, 0.3


# ============================================================================
# FTO Analysis Engine
# ============================================================================

class FTOAnalyzer:
    """Analyze claims for Freedom-to-Operate risk using LangChain"""
    
    def __init__(self):
        # Initialize LangChain LLM for FTO analysis
        self.use_llm = False
        self.llm = None
        
        # Try Groq first if enabled
        if LANGCHAIN_AVAILABLE and os.getenv("USE_GROQ") and os.getenv("GROQ_API_KEY"):
            try:
                self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)
                self.use_llm = True
                logger.info("FTOAnalyzer: Using Groq (llama-3.1-8b-instant) for FTO analysis")
            except Exception as e:
                logger.warning(f"FTOAnalyzer: Failed to initialize Groq: {e}")
        
        # Fallback to OpenAI if Groq not available
        if not self.use_llm and LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
                self.use_llm = True
                logger.info("FTOAnalyzer: Using ChatOpenAI for FTO analysis")
            except Exception as e:
                logger.warning(f"FTOAnalyzer: Failed to initialize ChatOpenAI: {e}")
        
        if not self.use_llm:
            logger.warning("FTOAnalyzer: No LLM API key, using heuristic fallback")
    
    def analyze_claim(self, claim: PatentClaim, drug_name: str, indication: str,
                     patent_status: LegalStatus, expiry_date: Optional[str]) -> Tuple[FTOStatus, float, str]:
        """
        Analyze single claim for FTO blocking risk.
        Returns: (FTOStatus, relevance_score, risk_explanation)
        """
        
        # Quick filters
        if patent_status in [LegalStatus.EXPIRED, LegalStatus.ABANDONED, LegalStatus.REVOKED]:
            return FTOStatus.GREEN, 0.0, "Patent expired or abandoned"
        
        if expiry_date:
            try:
                expiry = datetime.fromisoformat(expiry_date)
                if expiry < datetime.utcnow():
                    return FTOStatus.GREEN, 0.0, "Patent expired"
            except:
                pass
        
        # LLM-based analysis if available
        if self.use_llm:
            return self._llm_analyze_claim(claim, drug_name, indication)
        else:
            return self._heuristic_analyze_claim(claim, drug_name, indication)
    
    def _llm_analyze_claim(self, claim: PatentClaim, drug_name: str, 
                          indication: str) -> Tuple[FTOStatus, float, str]:
        """Use LLM to assess FTO risk"""
        prompt = f"""Analyze if this patent claim blocks the use of {drug_name} for treating {indication}.

Claim Type: {claim.claim_type.value}
Claim Text: {claim.claim_text[:500]}

Assess:
1. Does this claim cover {drug_name} specifically?
2. Does this claim cover therapeutic use for {indication}?
3. What is the blocking risk? (green=no block, amber=potential conflict, red=high risk)

Return in format:
RISK: <green|amber|red>
RELEVANCE: <0.0-1.0>
REASON: <one sentence explanation>"""
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Parse response
            risk_match = re.search(r'RISK:\s*(green|amber|red)', content, re.IGNORECASE)
            relevance_match = re.search(r'RELEVANCE:\s*([\d.]+)', content)
            reason_match = re.search(r'REASON:\s*(.+)', content, re.IGNORECASE)
            
            risk_str = risk_match.group(1).lower() if risk_match else 'green'
            relevance = float(relevance_match.group(1)) if relevance_match else 0.5
            reason = reason_match.group(1).strip() if reason_match else "Analyzed by LLM"
            
            # Map to enum
            risk_status = FTOStatus.GREEN
            if risk_str == 'amber':
                risk_status = FTOStatus.AMBER
            elif risk_str == 'red':
                risk_status = FTOStatus.RED
            
            return risk_status, relevance, reason
        
        except Exception as e:
            logger.warning(f"LLM FTO analysis failed: {e}")
            return self._heuristic_analyze_claim(claim, drug_name, indication)
    
    def _heuristic_analyze_claim(self, claim: PatentClaim, drug_name: str,
                                indication: str) -> Tuple[FTOStatus, float, str]:
        """Heuristic-based FTO analysis"""
        claim_lower = claim.claim_text.lower()
        drug_lower = drug_name.lower()
        indication_lower = indication.lower()
        
        # Check if drug mentioned
        drug_mentioned = drug_lower in claim_lower
        indication_mentioned = indication_lower in claim_lower
        
        # Scoring based on claim type and content
        if claim.claim_type == ClaimType.METHOD_OF_USE and drug_mentioned and indication_mentioned:
            return FTOStatus.RED, 0.9, f"Method-of-use claim covers {drug_name} for {indication}"
        
        if claim.claim_type == ClaimType.COMPOSITION and drug_mentioned:
            if claim.is_independent:
                return FTOStatus.RED, 0.8, f"Composition claim covers {drug_name}"
            else:
                return FTOStatus.AMBER, 0.6, f"Dependent composition claim may cover {drug_name}"
        
        if claim.claim_type == ClaimType.COMBINATION and drug_mentioned:
            return FTOStatus.AMBER, 0.7, f"Combination claim includes {drug_name}"
        
        if drug_mentioned or indication_mentioned:
            return FTOStatus.AMBER, 0.5, "Claim may have partial relevance"
        
        return FTOStatus.GREEN, 0.2, "No direct blocking risk identified"
    
    def generate_fto_report(self, patents: List[PatentRecord], drug_name: str,
                           indication: str) -> FTOReport:
        """Generate overall FTO report from analyzed patents"""
        blocking = []
        caution = []
        clear = []
        
        for patent in patents:
            has_red = any(c.blocking_risk == FTOStatus.RED for c in patent.claims)
            has_amber = any(c.blocking_risk == FTOStatus.AMBER for c in patent.claims)
            
            if has_red:
                blocking.append(patent.patent_id)
            elif has_amber:
                caution.append(patent.patent_id)
            else:
                clear.append(patent.patent_id)
        
        # Determine overall status
        if blocking:
            overall_status = FTOStatus.RED
            risk_summary = f"HIGH RISK: {len(blocking)} blocking patent(s) identified with RED claims."
        elif caution:
            overall_status = FTOStatus.AMBER
            risk_summary = f"MODERATE RISK: {len(caution)} patent(s) with potential conflicts (AMBER claims)."
        else:
            overall_status = FTOStatus.GREEN
            risk_summary = f"LOW RISK: All {len(patents)} patent(s) analyzed show no blocking claims."
        
        recommendations = []
        if blocking:
            recommendations.append("Conduct detailed infringement analysis with patent attorney")
            recommendations.append("Consider design-around strategies or licensing negotiations")
        if caution:
            recommendations.append("Review AMBER claims for potential conflicts")
            recommendations.append("Monitor patent status and expiry dates")
        
        return FTOReport(
            report_id=str(uuid.uuid4()),
            drug_name=drug_name,
            indication=indication,
            overall_fto_status=overall_status,
            blocking_patents=blocking,
            caution_patents=caution,
            clear_patents=clear,
            total_patents_analyzed=len(patents),
            risk_summary=risk_summary,
            recommendations=recommendations,
        )


# ============================================================================
# Patent Family Resolver
# ============================================================================

class PatentFamilyResolver:
    """Resolve patent families and compute expiry dates"""
    
    def __init__(self):
        pass
    
    def resolve_family(self, patent_id: str) -> Optional[PatentFamily]:
        """Resolve patent family (INPADOC) for given patent"""
        logger.info(f"Resolving patent family for {patent_id}")
        
        # Mock family resolution (in production: use INPADOC API)
        base_number = patent_id.replace("US", "").replace("B2", "").replace("A1", "")
        
        return PatentFamily(
            family_id=f"FAMILY-{base_number[:6]}",
            family_members=[patent_id, f"EP{base_number}A1", f"WO{base_number}A1"],
            priority_date="2019-06-15",
            earliest_filing_date="2020-06-15",
            jurisdictions=["US", "EP", "WO"],
        )
    
    def compute_expiry_date(self, filing_date: str, grant_date: Optional[str] = None) -> str:
        """Compute patent expiry (typically filing + 20 years)"""
        try:
            filing = datetime.fromisoformat(filing_date)
            expiry = filing + timedelta(days=20*365)  # 20 years
            return expiry.isoformat()
        except:
            return ""


# ============================================================================
# Embedding Generator with LangChain
# ============================================================================

class PatentEmbeddingGenerator:
    """Generate embeddings for patent claims using SentenceTransformer"""
    
    def __init__(self):
        self.use_model = False
        self.model = None
        
        if LANGCHAIN_AVAILABLE:
            try:
                self.model = SentenceTransformer('allenai-specter')
                self.use_model = True
                logger.info("PatentEmbeddingGenerator: Loaded allenai-specter model")
            except Exception as e:
                logger.warning(f"PatentEmbeddingGenerator: Failed to load model: {e}")
        
        if not self.use_model:
            logger.warning("PatentEmbeddingGenerator: Using mock embeddings")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for patent claim or abstract"""
        if not text:
            return []
        
        if self.use_model and self.model:
            try:
                embedding = self.model.encode(text, convert_to_tensor=False)
                return embedding.tolist()
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}, using mock")
        
        # Fallback: Mock embedding
        import hashlib
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random
        random.seed(seed)
        return [random.uniform(-1, 1) for _ in range(384)]


# LangChain-compatible embedding wrapper
class SentenceTransformerEmbeddings(Embeddings):
    """LangChain Embeddings interface for SentenceTransformer"""
    
    def __init__(self, model):
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode([text], convert_to_tensor=False)
        return embedding[0].tolist()


# ============================================================================
# Patent Ingestion Pipeline
# ============================================================================

class PatentIngestionPipeline:
    """Orchestrate patent fetching, parsing, classification, and FTO analysis"""
    
    def __init__(self):
        self.connectors: Dict[str, PatentSourceConnector] = {
            "uspto": USPTOConnector(),
            "epo": EPOConnector(),
            "wipo": WIPOConnector(),
        }
        self.claim_parser = ClaimParser()
        self.claim_classifier = ClaimClassifier()
        self.fto_analyzer = FTOAnalyzer()
        self.family_resolver = PatentFamilyResolver()
        self.embedder = PatentEmbeddingGenerator()
        self.patent_store: Dict[str, PatentRecord] = {}
        logger.info("PatentIngestionPipeline initialized with 3 connectors")
    
    def ingest_patents(self, drug_name: str, indication: str, 
                      chemical_class: str = "") -> List[PatentRecord]:
        """Main ETL pipeline for patents"""
        all_patents = []
        seen_patent_ids = set()
        
        for source_name, connector in self.connectors.items():
            try:
                raw_results = connector.search(drug_name, chemical_class, limit=5)
                logger.info(f"{source_name}: found {len(raw_results)} patents")
                
                for raw_patent in raw_results:
                    patent_id = raw_patent.get('patent_number')
                    if not patent_id or patent_id in seen_patent_ids:
                        continue
                    seen_patent_ids.add(patent_id)
                    
                    # Parse metadata
                    patent_record = self._parse_patent_metadata(raw_patent, source_name)
                    
                    # Fetch full details with claims
                    details = connector.fetch_patent_details(patent_id)
                    if details.get('claims'):
                        patent_record.claims = self._parse_and_classify_claims(
                            details['claims'], drug_name
                        )
                    
                    # FTO analysis on each claim
                    for claim in patent_record.claims:
                        status, relevance, explanation = self.fto_analyzer.analyze_claim(
                            claim, drug_name, indication,
                            patent_record.legal_status,
                            patent_record.expiry_date
                        )
                        claim.blocking_risk = status
                        claim.fto_relevance_score = relevance
                    
                    # Resolve patent family
                    patent_record.patent_family = self.family_resolver.resolve_family(patent_id)
                    
                    # Generate embedding for abstract
                    patent_record.embedding = self.embedder.embed_text(patent_record.abstract)
                    
                    # Compute FTO summary
                    patent_record.fto_summary = self._compute_fto_summary(patent_record)
                    
                    # Store
                    self.patent_store[patent_record.record_id] = patent_record
                    all_patents.append(patent_record)
                    logger.info(f"Stored patent {patent_id}")
            
            except Exception as e:
                logger.warning(f"Error ingesting from {source_name}: {str(e)}")
        
        logger.info(f"Ingest complete: {len(all_patents)} patents processed")
        return all_patents
    
    def _parse_patent_metadata(self, raw: Dict, source: str) -> PatentRecord:
        """Parse raw patent metadata"""
        patent_id = raw.get('patent_number', f"PATENT{uuid.uuid4().hex[:8]}")
        
        # Parse legal status
        status_str = raw.get('legal_status', 'pending').lower()
        legal_status = LegalStatus.PENDING
        for status in LegalStatus:
            if status.value in status_str:
                legal_status = status
                break
        
        # Compute expiry date
        filing_date = raw.get('patent_date') or raw.get('filing_date')
        expiry_date = ""
        if filing_date:
            expiry_date = self.family_resolver.compute_expiry_date(filing_date)
        
        return PatentRecord(
            patent_id=patent_id,
            record_id=str(uuid.uuid4()),
            title=raw.get('patent_title', ''),
            abstract=raw.get('patent_abstract', ''),
            filing_date=filing_date,
            publication_date=raw.get('patent_date'),
            grant_date=raw.get('grant_date'),
            expiry_date=expiry_date,
            legal_status=legal_status,
            applicants=[],
            inventors=raw.get('inventors', []),
            assignee=raw.get('assignee_organization'),
            classification_codes=raw.get('ipc_classes', []),
            source_registry=source.upper(),
            pdf_url=f"https://patents.google.com/patent/{patent_id}/en",
        )
    
    def _parse_and_classify_claims(self, claims_data: List[Dict], drug_name: str) -> List[PatentClaim]:
        """Parse claims and classify each one"""
        patent_claims = []
        
        for claim_data in claims_data:
            claim_text = claim_data.get('claim_text', '')
            claim_type, confidence = self.claim_classifier.classify_claim(claim_text, drug_name)
            
            patent_claim = PatentClaim(
                claim_id=str(uuid.uuid4()),
                claim_number=claim_data.get('claim_number', 0),
                claim_text=claim_text,
                claim_type=claim_type,
                is_independent=claim_data.get('is_independent', True),
                depends_on=claim_data.get('depends_on', []),
                confidence_score=confidence,
            )
            patent_claims.append(patent_claim)
        
        return patent_claims
    
    def _compute_fto_summary(self, patent: PatentRecord) -> Dict:
        """Compute FTO summary for patent"""
        red_claims = [c for c in patent.claims if c.blocking_risk == FTOStatus.RED]
        amber_claims = [c for c in patent.claims if c.blocking_risk == FTOStatus.AMBER]
        green_claims = [c for c in patent.claims if c.blocking_risk == FTOStatus.GREEN]
        
        return {
            'total_claims': len(patent.claims),
            'blocking_claims_count': len(red_claims),
            'caution_claims_count': len(amber_claims),
            'clear_claims_count': len(green_claims),
            'highest_risk_claim': red_claims[0].claim_number if red_claims else None,
            'overall_risk': FTOStatus.RED.value if red_claims else (
                FTOStatus.AMBER.value if amber_claims else FTOStatus.GREEN.value
            ),
        }


# ============================================================================
# Patent Index Manager with FAISS
# ============================================================================

class PatentIndexManager:
    """Manage patent storage and FAISS-based semantic search"""
    
    def __init__(self):
        self.relational_store: Dict[str, PatentRecord] = {}
        self.vector_store = None
        self.embedder = PatentEmbeddingGenerator()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=40,
            length_function=len,
        ) if LANGCHAIN_AVAILABLE else None
        logger.info("PatentIndexManager: Initialized with FAISS support")
    
    def store_patent(self, patent: PatentRecord):
        """Store patent in relational store and FAISS vector store"""
        self.relational_store[patent.record_id] = patent
        
        # Add to vector store
        if LANGCHAIN_AVAILABLE and self.text_splitter and patent.embedding:
            try:
                # Create document for FAISS
                doc_text = f"{patent.title}. {patent.abstract[:500]}"
                doc = Document(
                    page_content=doc_text,
                    metadata={
                        'patent_id': patent.patent_id,
                        'record_id': patent.record_id,
                        'title': patent.title,
                        'legal_status': patent.legal_status.value,
                        'source': patent.source_registry,
                    }
                )
                
                if self.vector_store is None:
                    # Initialize FAISS with first patent
                    if self.embedder.use_model:
                        embedding_wrapper = SentenceTransformerEmbeddings(self.embedder.model)
                        self.vector_store = FAISS.from_documents([doc], embedding=embedding_wrapper)
                    else:
                        logger.warning("Embedder not available, skipping FAISS initialization")
                else:
                    self.vector_store.add_documents([doc])
                
                logger.info(f"Added patent {patent.patent_id} to vector store")
            except Exception as e:
                logger.warning(f"Failed to add patent to vector store: {e}")
        
        logger.info(f"Stored patent {patent.patent_id}")
    
    def search_by_semantic_similarity(self, query: str, k: int = 5) -> List[PatentRecord]:
        """Semantic search using FAISS"""
        if not self.vector_store:
            logger.warning("Vector store not initialized")
            return []
        
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            patent_ids = [doc.metadata.get('record_id') for doc in docs]
            return [self.relational_store[pid] for pid in patent_ids if pid in self.relational_store]
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []


# ============================================================================
# Patent Intelligence Agent (Main Worker)
# ============================================================================

class PatentAgent:
    """Main agent interface for Master Agent"""
    
    def __init__(self):
        self.ingestion_pipeline = PatentIngestionPipeline()
        self.index_manager = PatentIndexManager()
        logger.info("PatentAgent initialized")
    
    def run(self, drug_name: str, indication: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point called by Master Agent.
        
        Returns:
            {
                'agent': 'patent_agent',
                'drug': drug_name,
                'indication': indication,
                'patents_found': int,
                'fto_report': Dict,
                'patents': List[Dict],
                'status': 'success' | 'partial' | 'failed',
            }
        """
        if options is None:
            options = {}
        
        try:
            logger.info(f"Patent Agent: Analyzing {drug_name} for {indication}")
            
            # 1. Ingest patents from registries
            patents = self.ingestion_pipeline.ingest_patents(
                drug_name, indication, 
                chemical_class=options.get('chemical_class', '')
            )
            logger.info(f"Found {len(patents)} patents")
            
            # 2. Index patents in FAISS
            for patent in patents:
                self.index_manager.store_patent(patent)
            
            # 3. Generate FTO report
            fto_report = self.ingestion_pipeline.fto_analyzer.generate_fto_report(
                patents, drug_name, indication
            )
            
            # 3.5: Apply Stage 2 gate logic (NEW FOR 2-PHASE PIPELINE)
            # Check if hard_veto should be triggered
            from datetime import datetime, timedelta
            
            blocking_patents_with_expiry = []
            for patent in patents:
                # Check if patent has blocking claims (RED)
                has_red_claims = any(c.blocking_risk == FTOStatus.RED for c in patent.claims)
                if has_red_claims and patent.expiry_date:
                    try:
                        # Parse expiry date
                        expiry = datetime.fromisoformat(patent.expiry_date.replace('Z', '+00:00'))
                        years_to_expiry = (expiry - datetime.now()).days / 365.25
                        
                        if years_to_expiry > 2:
                            blocking_patents_with_expiry.append({
                                'patent_id': patent.patent_id,
                                'expiry_date': patent.expiry_date,
                                'years_to_expiry': years_to_expiry
                            })
                    except:
                        pass  # Skip if expiry date parsing fails
            
            if blocking_patents_with_expiry:
                fto_report.hard_veto = True
                fto_report.gate_passed = False
                earliest = min(blocking_patents_with_expiry, key=lambda x: x['years_to_expiry'])
                fto_report.blocking_patent_expiry_date = earliest['expiry_date']
                fto_report.hard_veto_reason = (
                    f"Active blocking patent exists for {drug_name} + {indication}. "
                    f"Patent {earliest['patent_id']} expires in {earliest['years_to_expiry']:.1f} years "
                    f"({earliest['expiry_date']}). "
                    f"GATE DECISION: BLOCKED - Skip remaining agents, mark as BLOCKED_BY_PATENT."
                )
                logger.warning(f"❌ Stage 2 GATE FAILED: {fto_report.hard_veto_reason}")
            else:
                fto_report.gate_passed = True
                logger.info(f"✅ Stage 2 GATE PASSED: No blocking patents or all expire within 2 years")
            
            # 4. Compile result
            result = {
                'agent': 'patent_agent',
                'drug': drug_name,
                'indication': indication,
                'patents_found': len(patents),
                'fto_report': fto_report.to_dict(),
                'patents': [p.to_dict() for p in patents[:5]],  # Top 5 for brevity
                'blocking_patents': [
                    {
                        'patent_id': p.patent_id,
                        'title': p.title,
                        'red_claims': [c.to_dict() for c in p.claims if c.blocking_risk == FTOStatus.RED]
                    }
                    for p in patents if any(c.blocking_risk == FTOStatus.RED for c in p.claims)
                ],
                'status': 'success' if len(patents) > 0 else 'partial',
                'timestamp': datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Patent Agent: Complete. Status={result['status']}")
            return result
        
        except Exception as e:
            logger.error(f"Patent Agent failed: {str(e)}")
            return {
                'agent': 'patent_agent',
                'drug': drug_name,
                'indication': indication,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
            }


# ============================================================================
# Demo / Testing
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("PATENT INTELLIGENCE AGENT - Demo")
    print("="*80 + "\n")
    
    agent = PatentAgent()
    
    # Run on sample drug + indication
    result = agent.run(
        drug_name="aspirin",
        indication="cardiovascular disease",
        options={"chemical_class": "salicylates"}
    )
    
    print(f"Status: {result['status']}")
    print(f"Patents Found: {result['patents_found']}")
    print(f"\nFTO Report:")
    print(f"Overall Status: {result['fto_report']['overall_fto_status']}")
    print(f"Risk Summary: {result['fto_report']['risk_summary']}")
    print(f"\nBlocking Patents: {len(result['fto_report']['blocking_patents'])}")
    print(f"Caution Patents: {len(result['fto_report']['caution_patents'])}")
    print(f"Clear Patents: {len(result['fto_report']['clear_patents'])}")
    
    if result['blocking_patents']:
        print(f"\n{'='*80}")
        print("BLOCKING PATENTS DETAIL")
        print(f"{'='*80}\n")
        for bp in result['blocking_patents']:
            print(f"Patent: {bp['patent_id']}")
            print(f"Title: {bp['title']}")
            print(f"RED Claims: {len(bp['red_claims'])}\n")
            for claim in bp['red_claims'][:2]:
                print(f"  Claim {claim['claim_number']} ({claim['claim_type']})")
                print(f"  {claim['claim_text'][:200]}...\n")
    
    print(f"\n{'='*80}")
    print("FIRST PATENT (Full JSON)")
    print(f"{'='*80}\n")
    if result['patents']:
        print(json.dumps(result['patents'][0], indent=2))
