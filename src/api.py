"""
REST API for Drug Repurposing Assistant
Exposes the MasterAgent through FastAPI endpoints
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
import sys
import os
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.agents.master_agent import MasterAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Pydantic Models for API
# ============================================================================

class DrugRepurposingRequest(BaseModel):
    """Request model for drug repurposing query (legacy - drug + indication input)"""
    drug_name: str = Field(..., description="Name of the drug to analyze")
    indication: str = Field(..., description="Target indication/disease for repurposing")
    drug_synonyms: Optional[List[str]] = Field(
        default_factory=list,
        description="Alternative names for the drug"
    )
    indication_synonyms: Optional[List[str]] = Field(
        default_factory=list,
        description="Alternative names for the indication"
    )
    include_patent: Optional[bool] = Field(
        default=True,
        description="Whether to include patent analysis"
    )
    use_internal_data: Optional[bool] = Field(
        default=False,
        description="Whether to use internal proprietary data"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "drug_name": "metformin",
                "indication": "cardiovascular disease",
                "drug_synonyms": ["metformin hydrochloride"],
                "indication_synonyms": ["heart disease", "CVD"],
                "include_patent": True,
                "use_internal_data": False
            }
        }


class DrugOnlyRequest(BaseModel):
    """NEW: Request model for drug-only API with automatic disease discovery"""
    drug_name: str = Field(..., description="Name of the drug to analyze")
    population: Optional[str] = Field(
        default="general_adult",
        description="Target population for safety assessment (general_adult, terminal_illness, elderly, etc.)"
    )
    include_patent: Optional[bool] = Field(
        default=True,
        description="Whether to include patent analysis"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "drug_name": "aspirin",
                "population": "general_adult",
                "include_patent": True
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    drug_name: str
    indication: str
    status: str
    tasks_total: int
    tasks_completed: int
    tasks_failed: int
    human_review_required: bool
    reasoning_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="Drug Repurposing Assistant API",
    description="Multi-agent system for analyzing drug repurposing opportunities",
    version="1.0.0"
)

# Add CORS middleware BEFORE any other middleware
# This allows requests from Lovable, ngrok, and any other domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins
    ],
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all response headers to client
    max_age=600,  # Cache preflight response for 10 minutes
)

# Global MasterAgent instance
master_agent = MasterAgent(user_id="api_user")

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Drug Repurposing Assistant API is running"
    }


@app.post("/analyze", response_model=Dict[str, Any])
async def analyze_drug_repurposing(request: DrugRepurposingRequest):
    """
    Analyze a drug-indication pair for repurposing potential.
    
    This endpoint:
    1. Creates a new job in the MasterAgent
    2. Runs all 6 specialized agents in parallel (literature, clinical, safety, patent, market, molecular)
    3. Aggregates evidence across dimensions
    4. Performs reasoning synthesis to generate recommendations
    5. Returns the complete analysis result
    
    Args:
        request: DrugRepurposingRequest with drug_name and indication
    
    Returns:
        Job status with reasoning results and agent outputs
    """
    try:
        logger.info(f"Processing request: {request.drug_name} for {request.indication}")
        
        # Start the job (this runs all agents synchronously)
        job_id = master_agent.start_job(
            drug_name=request.drug_name,
            indication=request.indication,
            options={
                "include_patent": request.include_patent,
                "use_internal_data": request.use_internal_data
            }
        )
        
        # Get the final job status and results
        job_data = master_agent.get_job_status(job_id)
        
        logger.info(f"Job {job_id} completed successfully")
        
        return {
            "success": True,
            "job_id": job_id,
            "data": job_data
        }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing drug repurposing request: {str(e)}"
        )


@app.post("/discover", response_model=Dict[str, Any])
async def discover_indications(request: DrugOnlyRequest):
    """
    NEW ENDPOINT: Analyze a drug with automatic disease discovery (drug-only input).
    
    This endpoint implements the 2-phase pipeline:
    
    Phase 1 - DISCOVERY:
      1. DrugProfilerAgent: Get drug profile from ChEMBL
      2. IndicationDiscoveryAgent: Find disease candidates via target overlap
      3. Return top 5 candidates ranked by mechanistic_score
    
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
     10. ReasoningAgent → Assign tier
    
    Args:
        request: DrugOnlyRequest with drug_name (no indication required)
    
    Returns:
        {
            'drug_name': str,
            'chembl_id': str,
            'drug_profile': {...},
            'discovery_result': {...},
            'candidates': [
                {
                    'indication': str,
                    'tier': str,
                    'mechanistic_score': float,
                    'gate_results': {...},
                    'agent_results': {...}
                }
            ]
        }
    """
    try:
        logger.info(f"NEW API: Processing drug-only request for {request.drug_name}")
        
        # Call the new 2-phase pipeline method
        result = master_agent.discover_and_evaluate(
            drug_name=request.drug_name,
            options={
                "population": request.population,
                "include_patent": request.include_patent
            }
        )
        
        logger.info(f"Drug discovery complete for {request.drug_name}: {len(result.get('candidates', []))} candidates evaluated")
        
        return {
            "success": True,
            "data": result
        }
    
    except Exception as e:
        logger.error(f"Error processing drug discovery request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing drug discovery request: {str(e)}"
        )


@app.get("/job/{job_id}", response_model=Dict[str, Any])
async def get_job_status(job_id: str):
    """
    Get the status and results of a specific job.
    
    Args:
        job_id: The job ID returned from /analyze endpoint
    
    Returns:
        Current job status with all agent results and reasoning output
    """
    try:
        if job_id not in master_agent.job_store:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        job_data = master_agent.get_job_status(job_id)
        
        return {
            "success": True,
            "job_id": job_id,
            "data": job_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching job status: {str(e)}"
        )


@app.get("/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job_status_plural(job_id: str):
    """
    Get the status and results of a specific job (plural endpoint for React app).
    
    Args:
        job_id: The job ID returned from /analyze endpoint
    
    Returns:
        Current job status with all agent results and reasoning output
    """
    try:
        if job_id not in master_agent.job_store:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        job_data = master_agent.get_job_status(job_id)
        
        return job_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching job status: {str(e)}"
        )


@app.get("/jobs", response_model=Dict[str, Any])
async def list_jobs():
    """
    List all jobs processed by the API.
    
    Returns:
        List of job summaries with IDs, drugs, indications, and status
    """
    try:
        jobs_summary = []
        
        for job_id, job in master_agent.job_store.items():
            jobs_summary.append({
                "job_id": job_id,
                "drug_name": job.query.drug_name,
                "indication": job.query.indication,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "tasks_count": len(job.tasks),
                "human_review_required": job.human_review_required
            })
        
        return {
            "success": True,
            "total_jobs": len(jobs_summary),
            "jobs": jobs_summary
        }
    
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing jobs: {str(e)}"
        )


@app.post("/batch", response_model=Dict[str, Any])
async def batch_analyze(requests: List[DrugRepurposingRequest]):
    """
    Analyze multiple drug-indication pairs in batch.
    
    Args:
        requests: List of DrugRepurposingRequest objects
    
    Returns:
        List of analysis results, one per request
    """
    try:
        results = []
        
        for request in requests:
            logger.info(f"Processing batch request: {request.drug_name} for {request.indication}")
            
            job_id = master_agent.start_job(
                drug_name=request.drug_name,
                indication=request.indication,
                options={
                    "include_patent": request.include_patent,
                    "use_internal_data": request.use_internal_data
                }
            )
            
            job_data = master_agent.get_job_status(job_id)
            
            results.append({
                "job_id": job_id,
                "drug_name": request.drug_name,
                "indication": request.indication,
                "data": job_data
            })
        
        logger.info(f"Batch processing completed: {len(results)} jobs")
        
        return {
            "success": True,
            "total_processed": len(results),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing batch requests: {str(e)}"
        )


# ============================================================================
# Info Endpoints
# ============================================================================

@app.get("/agents", response_model=Dict[str, Any])
async def get_agents_info():
    """
    Get information about all available agents.
    
    Returns:
        Details about each specialized agent and their capabilities
    """
    agents_info = {
        "literature_agent": {
            "name": "Literature Agent",
            "description": "Searches biomedical literature for drug-indication evidence",
            "sources": ["PubMed", "Europe PMC", "bioRxiv", "medRxiv"],
            "dimension": "literature"
        },
        "clinical_agent": {
            "name": "Clinical Agent",
            "description": "Searches clinical trial databases for ongoing or completed trials",
            "sources": ["ClinicalTrials.gov", "EU CTR", "ISRCTN", "CTRI"],
            "dimension": "clinical"
        },
        "safety_agent": {
            "name": "Safety Agent",
            "description": "Analyzes adverse events and safety signals for the drug",
            "sources": ["Groq LLM for NER"],
            "dimension": "safety"
        },
        "patent_agent": {
            "name": "Patent Agent",
            "description": "Searches patent databases for IP landscape analysis",
            "sources": ["USPTO", "EPO", "WIPO"],
            "dimension": "patent"
        },
        "market_agent": {
            "name": "Market Agent",
            "description": "Analyzes market opportunity and competitive landscape",
            "sources": ["IQVIA", "GlobalData"],
            "dimension": "market"
        },
        "molecular_agent": {
            "name": "Molecular Agent",
            "description": "Analyzes molecular targets and biological pathways",
            "sources": ["Curated Knowledge Base"],
            "dimension": "molecular"
        }
    }
    
    return {
        "total_agents": len(agents_info),
        "agents": agents_info,
        "reasoning_agent": {
            "name": "Reasoning Agent",
            "description": "Synthesizes evidence from all agents and generates recommendations",
            "scoring_dimensions": [
                "clinical",
                "safety",
                "patent",
                "market",
                "molecular",
                "regulatory"
            ]
        }
    }


@app.get("/", response_model=Dict[str, Any])
async def root():
    """
    API information and documentation.
    
    Returns:
        API overview and available endpoints
    """
    return {
        "name": "Drug Repurposing Assistant API",
        "version": "1.0.0",
        "description": "Multi-agent system for analyzing drug repurposing opportunities",
        "endpoints": {
            "health": {
                "method": "GET",
                "path": "/health",
                "description": "Health check"
            },
            "analyze": {
                "method": "POST",
                "path": "/analyze",
                "description": "Analyze a single drug-indication pair"
            },
            "batch_analyze": {
                "method": "POST",
                "path": "/batch",
                "description": "Analyze multiple drug-indication pairs"
            },
            "get_job_status": {
                "method": "GET",
                "path": "/job/{job_id}",
                "description": "Get results for a specific job"
            },
            "list_jobs": {
                "method": "GET",
                "path": "/jobs",
                "description": "List all processed jobs"
            },
            "agents_info": {
                "method": "GET",
                "path": "/agents",
                "description": "Get information about available agents"
            },
            "docs": {
                "method": "GET",
                "path": "/docs",
                "description": "Interactive API documentation (Swagger UI)"
            },
            "redoc": {
                "method": "GET",
                "path": "/redoc",
                "description": "ReDoc API documentation"
            }
        },
        "quick_start": {
            "step1": "Send POST request to /analyze with drug_name and indication",
            "step2": "Receive job_id in response",
            "step3": "Use job_id to fetch results from /job/{job_id}",
            "example_curl": 'curl -X POST "http://localhost:8000/analyze" -H "Content-Type: application/json" -d \'{"drug_name":"metformin","indication":"cardiovascular disease"}\''
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Drug Repurposing Assistant API...")
    logger.info("API Documentation available at: http://localhost:8000/docs")
    
    # Get port from environment variable (for Render deployment) or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
