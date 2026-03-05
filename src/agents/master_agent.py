from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, UTC
import uuid
import logging
import sys
from pathlib import Path
import importlib
import csv

# Ensure project root is on path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Local orchestrated reasoning
from src.agents.reasoning_agent import ReasoningAgent
from src.utils.approved_indications import get_detector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Models & Enums
# ============================================================================

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class EvidenceDimension(str, Enum):
    CLINICAL = "clinical"
    LITERATURE = "literature"
    SAFETY = "safety"
    PATENT = "patent"
    MOLECULAR = "molecular"
    MARKET = "market"
    INTERNAL = "internal"


class ConfidenceTier(str, Enum):
    """Confidence tiers for sequential gating pipeline"""
    TIER_1_CONFIRMED = "tier_1_confirmed_plausible"  # High overlap + Tier A/B lit + clean safety + trial data
    TIER_2_MECHANISTIC = "tier_2_mechanistically_supported"  # Good overlap + any lit + acceptable safety
    TIER_3_SPECULATIVE = "tier_3_speculative"  # Literature only, low mechanistic score
    ESCALATE_HUMAN = "escalate_human_review"  # Black-box warning, contradictions, pediatric concerns


class GateStage(str, Enum):
    """Sequential pipeline stages"""
    STAGE_1_MECHANISTIC = "stage_1_mechanistic"
    STAGE_2_LITERATURE = "stage_2_literature"
    STAGE_3_SAFETY = "stage_3_safety"
    STAGE_4_CLINICAL = "stage_4_clinical"
    STAGE_5_CONFIDENCE = "stage_5_confidence"


@dataclass
class GatingResult:
    """Result from sequential gating pipeline"""
    success: bool
    stage: GateStage
    confidence_tier: Optional[ConfidenceTier] = None
    rejection_reason: Optional[str] = None
    escalation_reason: Optional[str] = None
    mechanistic_score: Optional[float] = None
    overlapping_targets: List[str] = field(default_factory=list)
    literature_tier: Optional[str] = None
    safety_transfer_score: Optional[float] = None
    clinical_data_available: bool = False
    flags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DrugIndicationQuery:
    """User input: drug + indication + options"""
    drug_name: str
    indication: str
    drug_synonyms: List[str] = field(default_factory=list)
    indication_synonyms: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Task:
    """Atomic task dispatched to an agent"""
    task_id: str
    agent_name: str
    dimension: EvidenceDimension
    query: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        data['status'] = self.status.value
        data['dimension'] = self.dimension.value
        return data


@dataclass
class JobMetadata:
    """Overall job tracking"""
    job_id: str
    created_at: datetime
    user_id: str
    query: DrugIndicationQuery
    tasks: Dict[str, Task] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    human_review_required: bool = False
    human_review_paused_at: Optional[datetime] = None
    reasoning_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        data = {
            'job_id': self.job_id,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id,
            'query': self.query.to_dict(),
            'status': self.status.value,
            'human_review_required': self.human_review_required,
            'human_review_paused_at': self.human_review_paused_at.isoformat() if self.human_review_paused_at else None,
            'reasoning_result': self.reasoning_result,
            'tasks': {k: v.to_dict() for k, v in self.tasks.items()},
        }
        return data


# ============================================================================
# Query Normalizer
# ============================================================================

class QueryNormalizer:
    """Resolves drug synonyms and canonicalizes indication text"""
    
    def __init__(self):
        self.drugbank_alias_to_common: Dict[str, str] = {}

        # Lightweight defaults (used if DrugBank row not found)
        self.drug_synonyms_map = {
            "aspirin": ["acetylsalicylic acid", "asa", "bayer"],
            "metformin": ["glucophage", "fortamet"],
            "ibuprofen": ["advil", "motrin", "nurofen"],
        }
        self.indication_map = {
            "diabetes": ["type 2 diabetes", "diabetes mellitus", "t2dm"],
            "hypertension": ["high blood pressure", "htn", "hypertensive disease"],
            "inflammation": ["inflammatory condition", "inflamm"],
        }

        self._load_drugbank_vocabulary()

    def _load_drugbank_vocabulary(self):
        """Load DrugBank vocabulary CSV and build alias/canonical maps."""
        csv_path = PROJECT_ROOT / "data" / "drugbank_vocabulary.csv"

        if not csv_path.exists():
            logger.warning(f"DrugBank vocabulary file not found at {csv_path}")
            return

        loaded_rows = 0

        try:
            with open(csv_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:
                    common_name = (row.get("Common name") or "").strip().lower()
                    synonyms_raw = (row.get("Synonyms") or "").strip()

                    if not common_name:
                        continue

                    aliases = {common_name}

                    if synonyms_raw:
                        for synonym in synonyms_raw.split("|"):
                            synonym_clean = synonym.strip().lower()
                            if synonym_clean:
                                aliases.add(synonym_clean)

                    # Build alias -> canonical lookup
                    for alias in aliases:
                        self.drugbank_alias_to_common[alias] = common_name

                    # Merge into canonical -> synonyms map
                    existing = set(self.drug_synonyms_map.get(common_name, []))
                    existing_lower = {syn.lower() for syn in existing}
                    for alias in aliases:
                        if alias != common_name and alias not in existing_lower:
                            existing.add(alias)

                    self.drug_synonyms_map[common_name] = sorted(existing)
                    loaded_rows += 1

            logger.info(
                f"Loaded DrugBank vocabulary: {loaded_rows} rows, "
                f"{len(self.drugbank_alias_to_common)} aliases"
            )
        except Exception as e:
            logger.warning(f"Failed to load DrugBank vocabulary: {e}")
    
    def normalize_drug(self, drug_name: str) -> str:
        """Return canonical drug name"""
        normalized = drug_name.lower().strip()
        return self.drugbank_alias_to_common.get(normalized, normalized)
    
    def normalize_indication(self, indication: str) -> str:
        """Return canonical indication text"""
        return indication.lower().strip()
    
    def expand_synonyms(self, drug_name: str) -> List[str]:
        """Return list of known synonyms"""
        canonical = self.normalize_drug(drug_name)
        synonyms = self.drug_synonyms_map.get(canonical)
        if synonyms:
            return synonyms
        return [canonical]


# ============================================================================
# Task Planner
# ============================================================================

class TaskPlanner:
    """Decomposes query into deterministic task templates"""
    
    AGENT_TO_DIMENSION = {
        "literature_agent": EvidenceDimension.LITERATURE,
        "clinical_agent": EvidenceDimension.CLINICAL,
        "safety_agent": EvidenceDimension.SAFETY,
        "patent_agent": EvidenceDimension.PATENT,
        "molecular_agent": EvidenceDimension.MOLECULAR,
        "market_agent": EvidenceDimension.MARKET,
        "internal_agent": EvidenceDimension.INTERNAL,
    }
    
    def plan_tasks(self, query: DrugIndicationQuery) -> List[Task]:
        """Create task list based on query options"""
        tasks = []
        
        # Always run core agents
        core_agents = [
            "literature_agent",
            "clinical_agent",
            "safety_agent",
            "molecular_agent",
        ]
        
        # Optionally add patent, market, internal
        if query.options.get("include_patent", True):
            core_agents.append("patent_agent")
        if query.options.get("include_market", True):
            core_agents.append("market_agent")
        if query.options.get("use_internal_data", False):
            core_agents.append("internal_agent")
        
        for agent_name in core_agents:
            dimension = self.AGENT_TO_DIMENSION[agent_name]
            task = Task(
                task_id=str(uuid.uuid4()),
                agent_name=agent_name,
                dimension=dimension,
                query=f"Analyze {query.drug_name} for {query.indication}"
            )
            tasks.append(task)
        
        return tasks


# ============================================================================
# Result Aggregator
# ============================================================================

class ResultAggregator:
    """Collects and validates agent outputs"""
    
    def aggregate(self, tasks: Dict[str, Task]) -> Dict[str, Any]:
        """Merge all task results into structured evidence"""
        aggregated = {
            'by_dimension': {},
            'raw_evidence': [],
            'validation_issues': [],
        }
        
        for task_id, task in tasks.items():
            if task.status == TaskStatus.COMPLETED and task.result:
                dimension_name = task.dimension.value
                if dimension_name not in aggregated['by_dimension']:
                    aggregated['by_dimension'][dimension_name] = []
                
                aggregated['by_dimension'][dimension_name].append({
                    'task_id': task.task_id,
                    'agent': task.agent_name,
                    'result': task.result,
                })
                aggregated['raw_evidence'].append(task.result)
            
            elif task.status == TaskStatus.FAILED:
                aggregated['validation_issues'].append({
                    'task_id': task.task_id,
                    'agent': task.agent_name,
                    'error': task.error,
                })
        
        return aggregated


# ============================================================================
# Master Agent (Coordinator)
# ============================================================================

class MasterAgent:
    """
    Orchestrator that:
    1. Accepts user query (drug + indication + options)
    2. Normalizes the query
    3. Plans tasks for specialized agents
    4. Dispatches tasks (via message broker)
    5. Collects results
    6. Validates outputs
    7. Coordinates human-in-loop checkpoints
    8. Triggers final synthesis (Reasoning Agent → ReportGenerator)
    """
    
    def __init__(self, user_id: str = "demo_user"):
        self.user_id = user_id
        self.normalizer = QueryNormalizer()
        self.planner = TaskPlanner()
        self.aggregator = ResultAggregator()
        self.job_store: Dict[str, JobMetadata] = {}
        self.task_results: Dict[str, Any] = {}
        self.reasoning_agent = ReasoningAgent()
        self.approved_detector = get_detector()  # Detect FDA-approved drug-indication pairs
        # Agent registry: module path -> class name
        self.agent_registry: Dict[str, Dict[str, str]] = {
            "clinical_agent": {"module": "src.agents.clinical_agent", "class": "ClinicalTrialsAgent"},
            "literature_agent": {"module": "src.agents.literature_agent", "class": "LiteratureAgent"},
            "safety_agent": {"module": "src.agents.safety_agent", "class": "SafetyAgent"},
            "patent_agent": {"module": "src.agents.patent_agent", "class": "PatentAgent"},
            "market_agent": {"module": "src.agents.market_agent", "class": "MarketAgent"},
            "molecular_agent": {"module": "src.agents.molecular_agent", "class": "MolecularAgent"},
        }
        logger.info("MasterAgent initialized")
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def start_job(self, drug_name: str, indication: str, options: Optional[Dict] = None) -> str:
        """
        Entry point: user submits a query.
        Returns: job_id for polling/status checks
        """
        if options is None:
            options = {}
        
        # 1. Normalize query
        normalized_drug = self.normalizer.normalize_drug(drug_name)
        normalized_indication = self.normalizer.normalize_indication(indication)
        drug_synonyms = self.normalizer.expand_synonyms(drug_name)
        
        # ===== CRITICAL FIX (Priority 2): Check if this is an FDA-approved baseline case =====
        # If sildenafil-for-ED, metformin-for-diabetes, etc. → skip pipeline, return baseline validation
        if self.approved_detector.is_approved(drug_name, indication):
            approval_info = self.approved_detector.get_approval_info(drug_name, indication)
            logger.info(f"\n✅ ✅ ✅ BASELINE VALIDATION CASE DETECTED ✅ ✅ ✅")
            logger.info(f"   Drug: {drug_name}")
            logger.info(f"   Indication: {indication}")
            logger.info(f"   FDA Approval: {approval_info.get('approval_year', 'N/A')}")
            logger.info(f"   Mechanism: {approval_info.get('mechanism', 'N/A')}")
            logger.info(f"   → Skipping full repurposing pipeline (this is not a repurposing candidate)")
            logger.info(f"   → Returning BASELINE_APPROVED response with high confidence\n")
            
            # Create a pseudo-job that represents baseline approval
            job_id = str(uuid.uuid4())
            baseline_hypothesis = {
                'hypothesis_id': f"baseline_{drug_name}_{indication}_{datetime.now(UTC).timestamp()}",
                'drug_name': drug_name,
                'indication': indication,
                'composite_score': 0.95,
                'decision': 'baseline_approved',
                'confidence': 0.99,
                'explanation': (
                    f"✅ BASELINE VALIDATION: {drug_name} is FDA-approved for {indication} "
                    f"(approved {approval_info.get('approval_year', 'N/A')}). "
                    f"This is NOT a drug repurposing candidate - it's the approved indication. "
                    f"Mechanism: {approval_info.get('mechanism', 'N/A')}. "
                    f"Repurposing pipeline skipped as this serves as a positive control baseline."
                ),
                'dimension_scores': [],
                'constraints': [],
                'contradictions': [],
                'baseline_validation': True,
                'approval_info': approval_info
            }
            
            # Store minimal job info for status endpoint compatibility
            job = JobMetadata(
                job_id=job_id,
                created_at=datetime.now(UTC),
                user_id=self.user_id,
                query=DrugIndicationQuery(
                    drug_name=normalized_drug,
                    indication=normalized_indication,
                    drug_synonyms=drug_synonyms,
                    options=options
                ),
            )
            job.status = TaskStatus.COMPLETED
            job.reasoning_result = {'hypotheses': [baseline_hypothesis]}
            job.tasks = {}
            self.job_store[job_id] = job
            
            logger.info(f"Baseline job {job_id} created for {drug_name} → {indication}")
            return job_id
        # ===== End baseline case check =====
        
        query = DrugIndicationQuery(
            drug_name=normalized_drug,
            indication=normalized_indication,
            drug_synonyms=drug_synonyms,
            options=options
        )
        
        # 2. Create job metadata
        job_id = str(uuid.uuid4())
        job = JobMetadata(
            job_id=job_id,
            created_at=datetime.now(UTC),
            user_id=self.user_id,
            query=query,
        )
        
        # 3. Plan tasks
        tasks = self.planner.plan_tasks(query)
        for task in tasks:
            job.tasks[task.task_id] = task
        
        # 4. Store job
        self.job_store[job_id] = job
        logger.info(f"Job {job_id} created with {len(tasks)} tasks")
        
        # 5. Dispatch tasks
        self._dispatch_tasks(job_id)
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Retrieve current job status - returns COMPLETE information including all agent results"""
        if job_id not in self.job_store:
            return {"error": "Job not found"}
        
        job = self.job_store[job_id]
        
        # Build tasks dictionary with all results
        tasks_dict = {}
        for task_id, task in job.tasks.items():
            tasks_dict[task_id] = {
                'task_id': task.task_id,
                'agent_name': task.agent_name,
                'dimension': task.dimension.value,
                'status': task.status.value,
                'result': task.result,
                'error': task.error,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            }
        
        return {
            'job_id': job_id,
            'drug_name': job.query.drug_name,
            'indication': job.query.indication,
            'status': job.status.value,
            'created_at': job.created_at.isoformat(),
            'query': job.query.to_dict(),
            'task_summary': {
                'total': len(job.tasks),
                'completed': sum(1 for t in job.tasks.values() if t.status == TaskStatus.COMPLETED),
                'failed': sum(1 for t in job.tasks.values() if t.status == TaskStatus.FAILED),
                'pending': sum(1 for t in job.tasks.values() if t.status == TaskStatus.PENDING),
            },
            'tasks': tasks_dict,  # Include ALL task results
            'reasoning_result': job.reasoning_result,  # Include reasoning/synthesis result
            'human_review_required': job.human_review_required,
        }
    
    def submit_task_result(self, job_id: str, task_id: str, result: Dict[str, Any], success: bool = True):
        """Agent callback: submit task result"""
        if job_id not in self.job_store:
            logger.error(f"Job {job_id} not found")
            return
        
        job = self.job_store[job_id]
        if task_id not in job.tasks:
            logger.error(f"Task {task_id} not found in job {job_id}")
            return
        
        task = job.tasks[task_id]
        
        if success:
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now(UTC)
            logger.info(f"Task {task_id} completed successfully")
        else:
            task.status = TaskStatus.FAILED
            task.error = result.get('error', 'Unknown error')
            task.completed_at = datetime.now(UTC)
            logger.warning(f"Task {task_id} failed: {task.error}")
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                logger.info(f"Task {task_id} queued for retry ({task.retry_count}/{task.max_retries})")
        
        self._check_job_completion(job_id)
    
    def approve_human_review(self, job_id: str) -> Dict[str, Any]:
        """User approves job to proceed to synthesis"""
        if job_id not in self.job_store:
            return {"error": "Job not found"}
        
        job = self.job_store[job_id]
        job.human_review_required = False
        logger.info(f"Job {job_id} approved by human reviewer")
        
        return self._trigger_synthesis(job_id)
    
    # ========================================================================
    # NEW: 2-Phase Pipeline for Drug-Only API (Master Plan Phase A)
    # ========================================================================

    def discover_and_evaluate(self, drug_name: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        NEW ENTRY POINT for drug-only API with 2-phase pipeline:
        
        Phase 1 - DISCOVERY:
          1. DrugProfilerAgent: Get drug profile from ChEMBL (targets, indications, mechanism)
          2. IndicationDiscoveryAgent: Query Open Targets for disease candidates via target overlap
          3. Return top 5 disease candidates ranked by mechanistic_score
        
        Phase 2 - EVALUATION (for each candidate):
          1. MolecularAgent (Stage 1 gate: overlap < 0.15 → REJECT)
          2. PatentAgent (Stage 2 gate: blocking patent → BLOCK)
          3. LiteratureAgent
          4. SafetyAgent (Stage 3 gate: hard_stop → ESCALATE but continue)
          5. ClinicalAgent
          6. MarketAgent
          7. RegulatoryAgent
          8. EXIMAgent
          9. BiomarkerAgent
         10. ReasoningAgent → Assign tier (Tier 1/2/3/Escalate/Insufficient)
        
        Returns:
            {
                'drug_name': str,
                'chembl_id': str,
                'discovery_result': {...},  # Phase 1 output
                'candidates': [  # Phase 2 output for each indication
                    {
                        'indication': str,
                        'mechanistic_score': float,
                        'tier': str,
                        'gate_results': {...},
                        'agent_results': {...}
                    }
                ]
            }
        """
        if options is None:
            options = {}

        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 2-PHASE PIPELINE START: {drug_name}")
        logger.info(f"{'='*80}\n")

        # ========== PHASE 1: DISCOVERY ==========
        logger.info(f"📍 PHASE 1: DISEASE DISCOVERY\n")

        # Step 1: DrugProfiler - Get drug profile from ChEMBL
        logger.info("Step 1/2: DrugProfilerAgent querying ChEMBL...")
        try:
            drug_profiler_module = importlib.import_module("src.agents.drug_profiler_agent")
            DrugProfilerAgent = getattr(drug_profiler_module, "DrugProfilerAgent")
            drug_profiler = DrugProfilerAgent()
            drug_profile = drug_profiler.run(drug_name)
            logger.info(f"✅ DrugProfiler complete: {drug_profile.chembl_id}, {len(drug_profile.known_targets)} targets")
        except Exception as e:
            logger.error(f"❌ DrugProfiler failed: {e}")
            return {'error': f'DrugProfiler failed: {e}', 'drug_name': drug_name}

        # Step 2: IndicationDiscovery - Find disease candidates via Open Targets
        logger.info("Step 2/2: IndicationDiscoveryAgent querying Open Targets...")
        try:
            indication_discovery_module = importlib.import_module("src.agents.indication_discovery_agent")
            IndicationDiscoveryAgent = getattr(indication_discovery_module, "IndicationDiscoveryAgent")
            discovery_agent = IndicationDiscoveryAgent()
            if hasattr(drug_profile, "to_dict"):
                drug_profile_payload = drug_profile.to_dict()
            elif hasattr(drug_profile, "__dict__"):
                drug_profile_payload = dict(drug_profile.__dict__)
            else:
                drug_profile_payload = drug_profile

            discovery_result = discovery_agent.run(drug_profile_payload)
            candidates = discovery_result.candidates
            logger.info(f"✅ IndicationDiscovery complete: {len(candidates)} candidates found")
        except Exception as e:
            logger.error(f"❌ IndicationDiscovery failed: {e}")
            return {'error': f'IndicationDiscovery failed: {e}', 'drug_name': drug_name, 'chembl_id': drug_profile.chembl_id}

        if len(candidates) == 0:
            logger.warning("⚠️  No disease candidates found for drug")
            return {
                'drug_name': drug_name,
                'chembl_id': drug_profile.chembl_id,
                'discovery_result': {'candidates': [], 'message': 'No disease candidates found'},
                'candidates': []
            }

        logger.info(f"\n📊 Phase 1 Complete: Top {len(candidates)} candidates:")
        for i, candidate in enumerate(candidates[:5], 1):
            logger.info(f"  {i}. {candidate.disease_name} (score: {candidate.mechanistic_score:.3f})")

        # ========== HACKATHON OPTIMIZATION: Only evaluate TOP 3 candidates ==========
        MAX_CANDIDATES_TO_EVALUATE = 3
        candidates_to_evaluate = candidates[:MAX_CANDIDATES_TO_EVALUATE]
        logger.info(f"\n⚡ PERFORMANCE OPTIMIZATION: Evaluating only TOP {len(candidates_to_evaluate)} candidates (out of {len(candidates)} discovered)")
        logger.info(f"   This reduces processing time from ~{len(candidates)*2}min to ~{len(candidates_to_evaluate)*1.4}min\n")

        # ========== PHASE 2: SEQUENTIAL EVALUATION ==========
        logger.info(f"\n📍 PHASE 2: 10-STAGE EVALUATION (with gates at stages 1, 2, 3)\n")

        evaluated_candidates = []

        for idx, candidate in enumerate(candidates_to_evaluate, 1):
            indication = candidate.disease_name
            logger.info(f"\n{'─'*80}")
            logger.info(f"🔬 Candidate {idx}/{len(candidates)}: {drug_name} → {indication}")
            logger.info(f"   Mechanistic Score: {candidate.mechanistic_score:.3f}")
            logger.info(f"{'─'*80}\n")

            candidate_result = {
                'indication': indication,
                'mechanistic_score': candidate.mechanistic_score,
                'linking_targets': candidate.linking_targets,
                'tier': None,
                'gate_results': {},
                'agent_results': {},
                'early_exit': False,
                'exit_reason': None
            }

            # ========== CRITICAL FIX (Priority 2): Check if this is an FDA-approved baseline case ==========
            # If sildenafil-for-ED, metformin-for-diabetes, etc. → skip repurposing pipeline, return baseline validation
            if self.approved_detector.is_approved(drug_name, indication):
                approval_info = self.approved_detector.get_approval_info(drug_name, indication)
                logger.info(f"✅ ✅ ✅ BASELINE VALIDATION CASE DETECTED ✅ ✅ ✅")
                logger.info(f"   Drug: {drug_name}")
                logger.info(f"   Indication: {indication}")
                logger.info(f"   FDA Approval: {approval_info.get('approval_year', 'N/A')}")
                logger.info(f"   Mechanism: {approval_info.get('mechanism', 'N/A')}")
                logger.info(f"   → Skipping repurposing pipeline (this is not a repurposing candidate)")
                logger.info(f"   → Assigning BASELINE_APPROVED tier with high confidence\n")
                
                candidate_result['tier'] = 'BASELINE_APPROVED'
                candidate_result['composite_score'] = 0.95  # High score for approved baseline
                candidate_result['confidence'] = 0.99
                candidate_result['early_exit'] = True
                candidate_result['exit_reason'] = f"FDA-approved for this indication (approved {approval_info.get('approval_year', 'N/A')})"
                candidate_result['baseline_validation'] = True
                candidate_result['approval_info'] = approval_info
                candidate_result['explanation'] = (
                    f"✅ BASELINE VALIDATION: {drug_name} is FDA-approved for {indication} "
                    f"(approved {approval_info.get('approval_year', 'N/A')}). "
                    f"This is NOT a drug repurposing candidate - it's the approved indication. "
                    f"Mechanism: {approval_info.get('mechanism', 'N/A')}. "
                    f"Repurposing pipeline skipped as this serves as a positive control baseline."
                )
                
                evaluated_candidates.append(candidate_result)
                logger.info(f"✅ Baseline validation recorded for {indication}\n")
                continue
            # ========== End baseline case check ==========

            try:
                # === Stage 1: Molecular (GATE 1) ===
                logger.info("Stage 1/10: MolecularAgent (GATE 1: overlap < 0.15 → REJECT)...")
                molecular_module = importlib.import_module("src.agents.molecular_agent")
                MolecularAgent = getattr(molecular_module, "MolecularAgent")
                molecular_agent = MolecularAgent()
                molecular_result = molecular_agent.run(drug_name, indication)
                candidate_result['agent_results']['molecular'] = molecular_result

                if not molecular_result.get('gate_passed', True):
                    logger.warning(f"❌ STAGE 1 GATE FAILED: {molecular_result.get('gate_rejection_reason')}")
                    candidate_result['early_exit'] = True
                    candidate_result['exit_reason'] = molecular_result.get('gate_rejection_reason')
                    candidate_result['tier'] = 'REJECT'
                    evaluated_candidates.append(candidate_result)
                    logger.info(f"⏭️  Skipping remaining stages for {indication}\n")
                    continue

                logger.info(f"✅ Stage 1 passed: overlap={molecular_result.get('overlap_score', 0):.3f}")

                # === Stage 2: Patent (GATE 2) ===
                logger.info("Stage 2/10: PatentAgent (GATE 2: blocking patent → BLOCK)...")
                patent_module = importlib.import_module("src.agents.patent_agent")
                PatentAgent = getattr(patent_module, "PatentAgent")
                patent_agent = PatentAgent()
                patent_result = patent_agent.run(drug_name, indication)
                candidate_result['agent_results']['patent'] = patent_result

                if patent_result.get('hard_veto', False):
                    logger.warning(f"❌ STAGE 2 GATE FAILED: {patent_result.get('hard_veto_reason')}")
                    candidate_result['early_exit'] = True
                    candidate_result['exit_reason'] = patent_result.get('hard_veto_reason')
                    candidate_result['tier'] = 'BLOCKED_BY_PATENT'
                    evaluated_candidates.append(candidate_result)
                    logger.info(f"⏭️  Skipping remaining stages for {indication}\n")
                    continue

                logger.info("✅ Stage 2 passed: no blocking patents")

                # === Stage 3: Literature ===
                logger.info("Stage 3/10: LiteratureAgent...")
                literature_module = importlib.import_module("src.agents.literature_agent")
                LiteratureAgent = getattr(literature_module, "LiteratureAgent")
                literature_agent = LiteratureAgent()
                literature_result = literature_agent.run(drug_name, indication)
                candidate_result['agent_results']['literature'] = literature_result
                logger.info(f"✅ Stage 3 complete: {literature_result.get('paper_count', 0)} papers, grade {literature_result.get('grade', 'E')}")

                # === Stage 4: Safety (GATE 3 - soft gate) ===
                logger.info("Stage 4/10: SafetyAgent (GATE 3: hard_stop → ESCALATE but continue)...")
                safety_module = importlib.import_module("src.agents.safety_agent")
                SafetyAgent = getattr(safety_module, "SafetyAgent")
                safety_agent = SafetyAgent()
                population = options.get('population', 'general_adult')
                safety_result = safety_agent.run(drug_name, indication, population=population)
                candidate_result['agent_results']['safety'] = safety_result.__dict__ if hasattr(safety_result, '__dict__') else safety_result

                if candidate_result['agent_results']['safety'].get('hard_stop', False):
                    logger.warning(f"⚠️  STAGE 3 SOFT GATE: {candidate_result['agent_results']['safety'].get('hard_stop_reason')}")
                    logger.warning("   Continuing evaluation but will ESCALATE final decision")
                else:
                    logger.info(f"✅ Stage 4 passed: safety_score={candidate_result['agent_results']['safety'].get('safety_score', 0):.3f}")

                # === Stage 5: Clinical ===
                logger.info("Stage 5/10: ClinicalAgent...")
                clinical_module = importlib.import_module("src.agents.clinical_agent")
                ClinicalTrialsAgent = getattr(clinical_module, "ClinicalTrialsAgent")
                clinical_agent = ClinicalTrialsAgent()
                clinical_result = clinical_agent.run(drug_name, indication)
                candidate_result['agent_results']['clinical'] = clinical_result
                logger.info(f"✅ Stage 5 complete: {clinical_result.get('trial_count', 0)} trials")

                # === Stage 6: Market ===
                logger.info("Stage 6/10: MarketAgent...")
                market_module = importlib.import_module("src.agents.market_agent")
                MarketAgent = getattr(market_module, "MarketAgent")
                market_agent = MarketAgent()
                market_result = market_agent.run(drug_name, indication, options={'failed_trials': clinical_result.get('failed_trials', [])})
                candidate_result['agent_results']['market'] = market_result
                
                # CRITICAL FIX: Check tam_estimate exists before logging
                tam_value = 0
                if market_result.get('tam_estimate') and isinstance(market_result['tam_estimate'], dict):
                    tam_value = market_result['tam_estimate'].get('tam_usd', 0)
                logger.info(f"✅ Stage 6 complete: TAM=${tam_value:.0f}M, label={market_result.get('opportunity_label', 'None')}")

                # === Stage 7: Regulatory ===
                logger.info("Stage 7/10: RegulatoryAgent...")
                regulatory_module = importlib.import_module("src.agents.regulatory_agent")
                RegulatoryAgent = getattr(regulatory_module, "RegulatoryAgent")
                regulatory_agent = RegulatoryAgent()
                regulatory_result = regulatory_agent.run(drug_name, indication, drug_profile)
                candidate_result['agent_results']['regulatory'] = regulatory_result.__dict__ if hasattr(regulatory_result, '__dict__') else regulatory_result
                logger.info(f"✅ Stage 7 complete: pathway={candidate_result['agent_results']['regulatory'].get('recommended_pathway', 'Unknown')}")

                # === Stage 8: EXIM ===
                logger.info("Stage 8/10: EXIMAgent...")
                exim_module = importlib.import_module("src.agents.exim_agent")
                EXIMAgent = getattr(exim_module, "EXIMAgent")
                exim_agent = EXIMAgent()
                exim_result = exim_agent.run(drug_name, indication, drug_profile)
                candidate_result['agent_results']['exim'] = exim_result.__dict__ if hasattr(exim_result, '__dict__') else exim_result
                logger.info(f"✅ Stage 8 complete: COGS=${candidate_result['agent_results']['exim'].get('estimated_cogs_per_unit', 0):.2f}")

                # === Stage 9: Biomarker ===
                logger.info("Stage 9/10: BiomarkerAgent...")
                biomarker_module = importlib.import_module("src.agents.biomarker_agent")
                BiomarkerAgent = getattr(biomarker_module, "BiomarkerAgent")
                biomarker_agent = BiomarkerAgent()
                biomarker_result = biomarker_agent.run(drug_name, indication, drug_profile.known_targets)
                candidate_result['agent_results']['biomarker'] = biomarker_result.__dict__ if hasattr(biomarker_result, '__dict__') else biomarker_result
                logger.info(f"✅ Stage 9 complete: {len(candidate_result['agent_results']['biomarker'].get('pharmacogenomic_variants', []))} variants")

                # === Stage 10: Reasoning (Tier Assignment) ===
                logger.info("Stage 10/10: ReasoningAgent (tiered decision logic)...")
                reasoning_input = [{
                    'drug': drug_name,
                    'indication': indication,
                    'agent_results': candidate_result['agent_results']
                }]
                reasoning_result = self.reasoning_agent.run(reasoning_input)

                if len(reasoning_result.hypotheses) > 0:
                    hypothesis = reasoning_result.hypotheses[0]
                    candidate_result['tier'] = hypothesis.decision.value
                    candidate_result['composite_score'] = hypothesis.composite_score
                    candidate_result['confidence'] = hypothesis.confidence
                    candidate_result['explanation'] = hypothesis.explanation
                    logger.info(f"✅ Stage 10 complete: TIER={candidate_result['tier']}, score={hypothesis.composite_score:.3f}")
                else:
                    candidate_result['tier'] = 'INSUFFICIENT_EVIDENCE'
                    logger.warning("⚠️  Stage 10: No hypothesis generated")

                evaluated_candidates.append(candidate_result)
                logger.info(f"\n✅ Evaluation complete for {indication}\n")

            except Exception as e:
                logger.error(f"❌ Evaluation failed for {indication}: {e}")
                candidate_result['tier'] = 'ERROR'
                candidate_result['error'] = str(e)
                evaluated_candidates.append(candidate_result)

        # ========== FINAL RESULT ==========
        logger.info(f"\n{'='*80}")
        logger.info(f"🏁 2-PHASE PIPELINE COMPLETE: {drug_name}")
        logger.info(f"   Candidates discovered: {len(candidates)}")
        logger.info(f"   Candidates evaluated: {len(evaluated_candidates)} (Top 3 for demo speed)")
        logger.info(f"   Baseline Approved (FDA): {sum(1 for c in evaluated_candidates if c['tier'] == 'BASELINE_APPROVED')}")
        logger.info(f"   Tier 1 (Confirmed): {sum(1 for c in evaluated_candidates if c['tier'] == 'tier_1_confirmed')}")
        logger.info(f"   Tier 2 (Plausible): {sum(1 for c in evaluated_candidates if c['tier'] == 'tier_2_plausible')}")
        logger.info(f"   Tier 3 (Speculative): {sum(1 for c in evaluated_candidates if c['tier'] == 'tier_3_speculative')}")
        logger.info(f"   Escalate (Human Review): {sum(1 for c in evaluated_candidates if c['tier'] == 'escalate_human_review')}")
        logger.info(f"   Blocked (Patent): {sum(1 for c in evaluated_candidates if c['tier'] == 'BLOCKED_BY_PATENT')}")
        logger.info(f"   Rejected (Gate 1): {sum(1 for c in evaluated_candidates if c['tier'] == 'REJECT')}")
        logger.info(f"{'='*80}\n")

        return {
            'drug_name': drug_name,
            'chembl_id': drug_profile.chembl_id,
            'drug_profile': {
                'chembl_id': drug_profile.chembl_id,
                'synonyms': drug_profile.synonyms,
                'known_targets': drug_profile.known_targets,
                'approved_indications': drug_profile.approved_indications,
                'max_phase': drug_profile.max_phase,
                'mechanism_of_action': drug_profile.mechanism_of_action,
                'drug_class': drug_profile.drug_class
            },
            'discovery_result': {
                'candidates_found': len(candidates),
                'top_candidates': [
                    {
                        'disease_name': c.disease_name,
                        'mechanistic_score': c.mechanistic_score,
                        'linking_targets': c.linking_targets,
                        'therapeutic_area': c.therapeutic_area
                    } for c in candidates
                ]
            },
            'candidates': evaluated_candidates
        }
    
    # ========================================================================
    # End of 2-Phase Pipeline
    # ========================================================================
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    def _dispatch_tasks(self, job_id: str):
        """Send tasks to agents"""
        job = self.job_store[job_id]
        
        for task in job.tasks.values():
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now(UTC)
            logger.info(f"Dispatching task {task.task_id} to {task.agent_name}")
            try:
                result = self._execute_task(task, job.query)
                self.submit_task_result(job_id, task.task_id, result, success=True)
            except Exception as e:
                logger.exception(f"Task {task.task_id} failed: {e}")
                self.submit_task_result(job_id, task.task_id, {"error": str(e)}, success=False)
    
    def _check_job_completion(self, job_id: str):
        """Check if all tasks done; trigger synthesis if so"""
        job = self.job_store[job_id]
        
        total = len(job.tasks)
        completed = sum(1 for t in job.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in job.tasks.values() if t.status == TaskStatus.FAILED)
        
        if completed + failed == total:
            job.status = TaskStatus.COMPLETED
            logger.info(f"Job {job_id}: All tasks completed ({completed} success, {failed} failed)")
            
            if failed > 0:
                job.human_review_required = True
                job.human_review_paused_at = datetime.now(UTC)
                logger.warning(f"Job {job_id} requires human review due to {failed} failed tasks")
            else:
                self._trigger_synthesis(job_id)
    
    def _trigger_synthesis(self, job_id: str) -> Dict[str, Any]:
        """Aggregate evidence and call Reasoning Agent"""
        job = self.job_store[job_id]
        
        aggregated = self.aggregator.aggregate(job.tasks)
        logger.info(f"Job {job_id}: Evidence aggregated, {len(aggregated['raw_evidence'])} items")
        
        # Build reasoning input (single hypothesis for this job)
        reasoning_input = [self._build_reasoning_payload(job, aggregated)]
        reasoning_result = self.reasoning_agent.run(reasoning_input)
        job.reasoning_result = asdict(reasoning_result)
        
        return {
            'job_id': job_id,
            'status': 'synthesis_complete',
            'evidence_summary': {
                'total_items': len(aggregated['raw_evidence']),
                'by_dimension': {k: len(v) for k, v in aggregated['by_dimension'].items()},
                'validation_issues': len(aggregated['validation_issues']),
            },
            'reasoning_result': job.reasoning_result,
        }

    # ========================================================================
    # Sequential Gating Pipeline (Master Plan Priority #1)
    # ========================================================================
    
    async def repurpose_with_gating(
        self,
        drug_name: str,
        indication: str,
        patient_population: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> GatingResult:
        """
        Sequential gating pipeline that replaces parallel dispatch.
        Each stage acts as a gate - if criteria not met, pipeline stops.
        
        STAGE 1: Mechanistic gate (overlap_score > 0.15)
        STAGE 2: Literature gate (mechanism-guided search)  
        STAGE 3: Safety gate (population-specific thresholds)
        STAGE 4: Clinical gate (dosing + failed trials)
        STAGE 5: Confidence tier assignment
        """
        if options is None:
            options = {}
        if patient_population is None:
            patient_population = "general_adult"
            
        logger.info(f"Starting sequential gating: {drug_name} → {indication} (population: {patient_population})")
        
        # Normalize inputs
        normalized_drug = self.normalizer.normalize_drug(drug_name)
        normalized_indication = self.normalizer.normalize_indication(indication)
        
        # ====================================================================
        # STAGE 1: Mechanistic Gate (runs first, always)
        # ====================================================================
        logger.info("STAGE 1: Mechanistic analysis (target-disease overlap)")
        
        try:
            mol_agent = self._load_agent("molecular_agent")
            mol_result = mol_agent.run(
                drug_name=normalized_drug,
                indication=normalized_indication
            )
            
            overlap_score = mol_result.get("overlap_score", 0.0)
            overlapping_targets = mol_result.get("overlapping_targets", [])
            gate_passed = mol_result.get("gate_passed", overlap_score >= 0.15)
            gate_threshold_used = mol_result.get("gate_threshold_used", 0.15)
            gate_rejection_reason = mol_result.get("gate_rejection_reason", "No mechanistic basis")
            
            logger.info(f"Mechanistic overlap score: {overlap_score:.3f} ({len(overlapping_targets)} targets)")
            
            if not gate_passed:
                logger.warning(
                    f"REJECTED at Stage 1: overlap_score {overlap_score:.3f} < threshold {gate_threshold_used:.3f}"
                )
                return GatingResult(
                    success=False,
                    stage=GateStage.STAGE_1_MECHANISTIC,
                    rejection_reason=gate_rejection_reason,
                    mechanistic_score=overlap_score,
                    overlapping_targets=overlapping_targets
                )
        except Exception as e:
            logger.exception(f"Stage 1 failed: {e}")
            return GatingResult(
                success=False,
                stage=GateStage.STAGE_1_MECHANISTIC,
                rejection_reason=f"Molecular agent error: {str(e)}"
            )
        
        # ====================================================================
        # STAGE 2: Literature Gate (mechanism-guided)
        # ====================================================================
        logger.info("STAGE 2: Literature search (mechanism-first queries)")
        
        lit_result = {}
        try:
            lit_agent = self._load_agent("literature_agent")
            lit_result = lit_agent.run(
                drug_name=normalized_drug,
                indication=normalized_indication,
                targets=overlapping_targets  # Pass targets from Stage 1
            )
            
            max_tier = lit_result.get("max_evidence_tier", "D")
            paper_count = lit_result.get("paper_count", 0)
            
            logger.info(f"Literature: {paper_count} papers (max tier: {max_tier})")
            
            # Flag computational-only hypotheses
            if max_tier == "D" and paper_count < 3:
                lit_result["flag"] = "computational_hypothesis_only"
                logger.warning("Literature flag: computational hypothesis only (< 3 papers, all Tier D)")
                
        except Exception as e:
            logger.exception(f"Stage 2 failed: {e}")
            lit_result = {"error": str(e), "paper_count": 0, "max_evidence_tier": "D"}
        
        # ====================================================================
        # STAGE 3: Safety Gate (population-specific)
        # ====================================================================
        logger.info(f"STAGE 3: Safety analysis (population: {patient_population})")
        
        safety_result = {}
        try:
            safety_agent = self._load_agent("safety_agent")
            safety_result = safety_agent.run(
                drug_name=normalized_drug,
                indication=normalized_indication,
                population=patient_population  # Population-specific thresholds
            )
            
            hard_stop = safety_result.get("hard_stop", False)
            safety_transfer_score = safety_result.get("safety_transfer_score", 0.0)
            
            logger.info(f"Safety transfer score: {safety_transfer_score:.3f} (hard_stop: {hard_stop})")
            
            # Hard stop conditions require human review
            if hard_stop:
                escalation_msg = safety_result.get("hard_stop_reason", "Safety hard stop detected")
                logger.warning(f"ESCALATE at Stage 3: {escalation_msg}")
                return GatingResult(
                    success=False,
                    stage=GateStage.STAGE_3_SAFETY,
                    confidence_tier=ConfidenceTier.ESCALATE_HUMAN,
                    escalation_reason=escalation_msg,
                    mechanistic_score=overlap_score,
                    overlapping_targets=overlapping_targets,
                    literature_tier=lit_result.get("max_evidence_tier"),
                    safety_transfer_score=safety_transfer_score,
                    flags=["safety_hard_stop"]
                )
                
        except Exception as e:
            logger.exception(f"Stage 3 failed: {e}")
            safety_result = {"error": str(e), "safety_transfer_score": 0.0}
        
        # ====================================================================
        # STAGE 4: Clinical Gate (dosing + failed trials)
        # ====================================================================
        logger.info("STAGE 4: Clinical trial evidence extraction")
        
        clin_result = {}
        try:
            clin_agent = self._load_agent("clinical_agent")
            clin_result = clin_agent.run(
                drug_name=normalized_drug,
                indication=normalized_indication
            )
            
            has_trial_data = clin_result.get("trial_count", 0) > 0
            failed_trials = clin_result.get("failed_trials", [])
            
            logger.info(f"Clinical: {clin_result.get('trial_count', 0)} trials ({len(failed_trials)} failures)")
            
        except Exception as e:
            logger.exception(f"Stage 4 failed: {e}")
            clin_result = {"error": str(e), "trial_count": 0, "has_trial_data": False}
        
        # ====================================================================
        # STAGE 5: Confidence Tier Assignment
        # ====================================================================
        logger.info("STAGE 5: Assigning confidence tier")
        
        tier, flags = self._assign_confidence_tier(
            overlap_score=overlap_score,
            lit_tier=lit_result.get("max_evidence_tier", "D"),
            paper_count=lit_result.get("paper_count", 0),
            safety_score=safety_result.get("safety_transfer_score", 0.0),
            has_trials=clin_result.get("trial_count", 0) > 0,
            contradictions=lit_result.get("contradictory_papers", 0)
        )
        
        logger.info(f"Final confidence tier: {tier.value}")
        
        return GatingResult(
            success=True,
            stage=GateStage.STAGE_5_CONFIDENCE,
            confidence_tier=tier,
            mechanistic_score=overlap_score,
            overlapping_targets=overlapping_targets,
            literature_tier=lit_result.get("max_evidence_tier"),
            safety_transfer_score=safety_result.get("safety_transfer_score"),
            clinical_data_available=clin_result.get("trial_count", 0) > 0,
            flags=flags
        )
    
    def _assign_confidence_tier(
        self,
        overlap_score: float,
        lit_tier: str,
        paper_count: int,
        safety_score: float,
        has_trials: bool,
        contradictions: int
    ) -> tuple[ConfidenceTier, List[str]]:
        """
        Assign confidence tier based on multi-stage evidence.
        
        Tier 1: overlap > 0.4 + Tier A/B lit + clean safety + trial data
        Tier 2: overlap > 0.2 + any lit + acceptable safety
        Tier 3: Literature only, overlap < 0.2
        Escalate: Contradictions or other concerns
        """
        flags = []
        
        # Check for escalation conditions first
        if contradictions >= 3:
            flags.append("high_contradictions")
            return (ConfidenceTier.ESCALATE_HUMAN, flags)
        
        # Tier 1: Confirmed Plausible
        if (overlap_score > 0.4 and
            lit_tier in ["A", "B"] and
            safety_score > 0.7 and
            has_trials):
            flags.append("high_confidence")
            return (ConfidenceTier.TIER_1_CONFIRMED, flags)
        
        # Tier 2: Mechanistically Supported
        if overlap_score > 0.2 and paper_count > 0 and safety_score > 0.5:
            if not has_trials:
                flags.append("first_mover_opportunity")
            return (ConfidenceTier.TIER_2_MECHANISTIC, flags)
        
        # Tier 3: Speculative
        if overlap_score < 0.2:
            flags.append("low_mechanistic_score")
        if lit_tier == "D":
            flags.append("computational_only")
        
        return (ConfidenceTier.TIER_3_SPECULATIVE, flags)
    
    def _load_agent(self, agent_name: str):
        """Dynamically load an agent by name"""
        if agent_name not in self.agent_registry:
            raise ValueError(f"Unknown agent: {agent_name}")
        meta = self.agent_registry[agent_name]
        module = importlib.import_module(meta["module"])
        agent_cls = getattr(module, meta["class"])
        return agent_cls()

    def _execute_task(self, task: Task, query: DrugIndicationQuery) -> Dict[str, Any]:
        """Run the appropriate agent synchronously and return its result"""
        if task.agent_name not in self.agent_registry:
            raise ValueError(f"Unknown agent: {task.agent_name}")
        meta = self.agent_registry[task.agent_name]
        module = importlib.import_module(meta["module"])
        agent_cls = getattr(module, meta["class"])
        agent = agent_cls()
        if not hasattr(agent, "run"):
            raise AttributeError(f"Agent {task.agent_name} missing run() method")
        result = agent.run(drug_name=query.drug_name, indication=query.indication)
        return self._serialize_result(result)

    def _serialize_result(self, result: Any) -> Dict[str, Any]:
        """Best-effort conversion of agent output to dict"""
        if result is None:
            return {}
        if isinstance(result, dict):
            return result
        if hasattr(result, "dict"):
            return result.dict()  # pydantic-style
        if hasattr(result, "to_dict"):
            return result.to_dict()
        if hasattr(result, "__dataclass_fields__"):
            return asdict(result)
        if hasattr(result, "__dict__"):
            return dict(result.__dict__)
        raise TypeError(f"Unsupported result type: {type(result)}")

    def _build_reasoning_payload(self, job: JobMetadata, aggregated: Dict[str, Any]) -> Dict[str, Any]:
        """Convert aggregated task results into ReasoningAgent input structure"""
        agent_results: Dict[str, Any] = {}
        
        # Pick the first completed result per dimension (simple heuristic)
        for dimension, results in aggregated['by_dimension'].items():
            if not results:
                continue
            # If multiple, prefer the one with highest evidence_count if present
            selected = max(results, key=lambda r: r['result'].get('evidence_count', 0))
            agent_results[dimension] = selected['result']
        
        return {
            'drug': job.query.drug_name,
            'indication': job.query.indication,
            'agent_results': agent_results,
        }


if __name__ == "__main__":
    master = MasterAgent(user_id="demo_user")
    
    # Start a job
    job_id = master.start_job(
        drug_name="ibuprofen",
        indication="inflammatory bowel disease",
        options={"include_patent": True, "use_internal_data": False}
    )
    print(f"\n✓ Job started: {job_id}")
    
    # All agents run synchronously during start_job; show final status
    final_status = master.get_job_status(job_id)
    print(f"\n✓ Final job status:\n{final_status}")
    
    if master.job_store[job_id].reasoning_result:
        print("\n✓ Reasoning result (composite ranking):")
        print(master.job_store[job_id].reasoning_result)
