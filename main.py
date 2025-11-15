"""
Lab Intelligence Chatbot - FastAPI Backend
Main API server for handling natural language queries and SQL generation.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import asyncio
from contextlib import asynccontextmanager

from app.database import get_db_connection, validate_sql_query
from app.llm_service import LLMService
from app.query_executor import QueryExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
llm_service = None
query_executor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global llm_service, query_executor
    
    # Startup
    logger.info("Initializing Lab Intelligence Chatbot services...")
    llm_service = LLMService()
    query_executor = QueryExecutor()
    logger.info("Services initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down services...")


app = FastAPI(
    title="Lab Intelligence Chatbot API",
    description="Natural language to SQL API for lab data queries",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class QueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sql_query: str
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    success: bool


class SchemaResponse(BaseModel):
    schema: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Returns database schema for LLM reference"""
    schema = {
        "tables": {
            "org": {
                "columns": ["ng_org_id", "org_name", "org_ng_id"],
                "description": "Organization master data"
            },
            "lab_center": {
                "columns": ["ng_lab_center_id", "ng_org_id", "lab_id", "lab_center_name", "lab_no"],
                "description": "Centers within an organization",
                "foreign_keys": {"ng_org_id": "org.ng_org_id"}
            },
            "report_details": {
                "columns": ["ng_report_id", "ng_org_id", "ng_lab_center_id", "age_years", "gender", 
                          "bill_date", "bill_id", "package_name", "generation_in_epoch"],
                "description": "Report metadata",
                "foreign_keys": {
                    "ng_org_id": "org.ng_org_id",
                    "ng_lab_center_id": "lab_center.ng_lab_center_id"
                }
            },
            "test": {
                "columns": ["ng_test_id", "ng_org_id", "ng_lab_center_id", "ng_report_id", 
                          "test_name", "total_parameter_count", "normal_parameter_count", 
                          "abnormal_parameter_count", "is_abnormal"],
                "description": "Test-level details",
                "foreign_keys": {
                    "ng_org_id": "org.ng_org_id",
                    "ng_lab_center_id": "lab_center.ng_lab_center_id",
                    "ng_report_id": "report_details.ng_report_id"
                }
            },
            "parameters": {
                "columns": ["ng_parameters_id", "ng_test_id", "ng_report_id", "ng_org_id", 
                          "ng_lab_center_id", "parameter_name", "parameter_value", "min_value", 
                          "max_value", "test_range", "impression", "is_abnormal", "unit"],
                "description": "Parameter-level details",
                "foreign_keys": {
                    "ng_test_id": "test.ng_test_id",
                    "ng_report_id": "report_details.ng_report_id",
                    "ng_org_id": "org.ng_org_id",
                    "ng_lab_center_id": "lab_center.ng_lab_center_id"
                }
            }
        },
        "relationships": [
            "org -> lab_center (1:N)",
            "org -> report_details (1:N)",
            "lab_center -> report_details (1:N)",
            "report_details -> test (1:N)",
            "test -> parameters (1:N)"
        ]
    }
    return SchemaResponse(schema=schema)


@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """
    Main endpoint for natural language queries.
    Converts natural language to SQL, validates, executes, and returns results.
    """
    try:
        logger.info(f"Received question: {request.question[:100]}...")
        
        # Step 1: Generate SQL from natural language (sync operation)
        sql_query = await asyncio.to_thread(llm_service.generate_sql, request.question)
        
        if not sql_query:
            raise HTTPException(
                status_code=400,
                detail="Unable to generate SQL query. Please rephrase your question."
            )
        
        logger.info(f"Generated SQL: {sql_query}")
        
        # Step 2: Validate SQL query (read-only, safe)
        validation_result = validate_sql_query(sql_query)
        if not validation_result["is_valid"]:
            logger.warning(f"SQL validation failed: {validation_result['error']}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid SQL query: {validation_result['error']}"
            )
        
        # Step 3: Execute query (sync operation, FastAPI will handle it)
        execution_result = await asyncio.to_thread(query_executor.execute_query, sql_query)
        
        if not execution_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Query execution failed: {execution_result.get('error', 'Unknown error')}"
            )
        
        # Step 4: Format response
        data = execution_result["data"]
        row_count = len(data)
        
        # Generate natural language answer
        answer = llm_service.format_answer(request.question, sql_query, data, row_count)
        
        response = QueryResponse(
            answer=answer,
            sql_query=sql_query,
            data=data,
            row_count=row_count,
            execution_time_ms=execution_result.get("execution_time_ms", 0),
            success=True
        )
        
        logger.info(f"Query completed successfully. Rows returned: {row_count}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

