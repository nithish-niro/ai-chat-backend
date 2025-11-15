"""
LLM Service for Natural Language to SQL conversion
Uses LangChain and OpenAI GPT models
"""

import os
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import logging

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class LLMService:
    """Service for handling LLM interactions and SQL generation"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize LLM service
        
        Args:
            model_name: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,  # Lower temperature for more deterministic SQL
            api_key=api_key
        )
        self.model_name = model_name
        
        # Database schema for context
        self.schema_context = self._build_schema_context()
        
        logger.info(f"LLMService initialized with model: {model_name}")
    
    def _build_schema_context(self) -> str:
        """Build schema context string for prompt"""
        schema = """
PostgreSQL Database Schema for Lab Intelligence System:

Table: org
  - ng_org_id (int, PK): Organization ID
  - org_name (varchar): Organization name
  - org_ng_id (varchar, unique): Organization NG ID

Table: lab_center
  - ng_lab_center_id (int, PK): Lab center ID
  - ng_org_id (int, FK -> org.ng_org_id): Organization ID
  - lab_id (varchar, unique): Lab identifier
  - lab_center_name (varchar): Lab center name
  - lab_no (varchar): Lab number

Table: report_details
  - ng_report_id (int, PK): Report ID
  - ng_org_id (int, FK -> org.ng_org_id): Organization ID
  - ng_lab_center_id (int, FK -> lab_center.ng_lab_center_id): Lab center ID
  - age_years (int): Patient age in years
  - gender (varchar): Patient gender
  - bill_date (timestamp): Bill date
  - bill_id (varchar, unique): Bill identifier
  - package_name (varchar): Package name
  - generation_in_epoch (bigint): Generation timestamp in epoch

Table: test
  - ng_test_id (int, PK): Test ID
  - ng_org_id (int, FK -> org.ng_org_id): Organization ID
  - ng_lab_center_id (int, FK -> lab_center.ng_lab_center_id): Lab center ID
  - ng_report_id (int, FK -> report_details.ng_report_id): Report ID
  - test_name (varchar): Name of the test
  - total_parameter_count (int): Total parameters in test
  - normal_parameter_count (int): Normal parameter count
  - abnormal_parameter_count (int): Abnormal parameter count
  - is_abnormal (boolean): Whether test has abnormal results

Table: parameters
  - ng_parameters_id (int, PK): Parameter ID
  - ng_test_id (int, FK -> test.ng_test_id): Test ID
  - ng_report_id (int, FK -> report_details.ng_report_id): Report ID
  - ng_org_id (int, FK -> org.ng_org_id): Organization ID
  - ng_lab_center_id (int, FK -> lab_center.ng_lab_center_id): Lab center ID
  - parameter_name (varchar): Parameter name
  - parameter_value (varchar): Parameter value
  - min_value (varchar): Minimum reference value
  - max_value (varchar): Maximum reference value
  - test_range (varchar): Test range
  - impression (varchar): Impression/interpretation
  - is_abnormal (boolean): Whether parameter is abnormal
  - unit (varchar): Parameter unit

Important Notes:
- All dates are stored as timestamps in bill_date
- Use DATE() function to extract date from timestamp
- Lab numbers are stored in lab_center.lab_no (varchar, not int)
- Use JOINs to connect related tables
- Always use proper WHERE clauses for filtering
- Use is_abnormal = TRUE for abnormal tests/parameters
"""
        return schema
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for SQL generation"""
        return f"""You are an expert SQL analyst for a pathology laboratory information system.

Your task is to convert natural language questions into safe, read-only PostgreSQL SELECT queries.

{self.schema_context}

Rules:
1. Generate ONLY SELECT queries - never INSERT, UPDATE, DELETE, DROP, or any data modification commands
2. Use proper JOINs to connect related tables
3. Use DATE() function when comparing dates
4. Be precise with column names and table names (use exact names from schema)
5. Use appropriate WHERE clauses for filtering
6. For date comparisons, use DATE(bill_date) or DATE comparisons
7. Return ONLY the SQL query, nothing else - no explanations, no markdown, just pure SQL
8. Use proper SQL syntax with semicolon at the end
9. If the question asks for "yesterday", use CURRENT_DATE - INTERVAL '1 day' or DATE(bill_date) = CURRENT_DATE - 1
10. If the question asks for specific labs, join with lab_center table and filter by lab_no or lab_center_name

Examples:
- "Show all abnormal tests for Lab 12 yesterday" → 
  SELECT t.test_name, r.bill_date, l.lab_center_name, l.lab_no
  FROM test t
  JOIN report_details r ON t.ng_report_id = r.ng_report_id
  JOIN lab_center l ON l.ng_lab_center_id = t.ng_lab_center_id
  WHERE t.is_abnormal = TRUE
    AND l.lab_no = '12'
    AND DATE(r.bill_date) = CURRENT_DATE - 1;

- "How many reports were generated this month?" →
  SELECT COUNT(*) as report_count
  FROM report_details
  WHERE DATE_TRUNC('month', bill_date) = DATE_TRUNC('month', CURRENT_DATE);

- "List abnormal parameters for male patients" →
  SELECT p.parameter_name, p.parameter_value, p.is_abnormal, r.gender, r.age_years
  FROM parameters p
  JOIN report_details r ON p.ng_report_id = r.ng_report_id
  WHERE p.is_abnormal = TRUE
    AND r.gender = 'Male';
"""
    
    def generate_sql(self, question: str) -> Optional[str]:
        """
        Generate SQL query from natural language question
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string or None if generation fails
        """
        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=f"Question: {question}\n\nGenerate the SQL query:")
            ]
            
            response = self.llm.invoke(messages)
            
            # Extract SQL from response
            sql_query = response.content.strip()
            
            # Remove markdown code blocks if present
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            elif sql_query.startswith("```"):
                sql_query = sql_query[3:]
            
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            sql_query = sql_query.strip()
            
            # Ensure it ends with semicolon
            if not sql_query.endswith(';'):
                sql_query += ';'
            
            logger.info(f"Generated SQL: {sql_query[:200]}...")
            return sql_query
            
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}", exc_info=True)
            return None
    
    def format_answer(self, question: str, sql_query: str, data: List[Dict[str, Any]], row_count: int) -> str:
        """
        Format the query results into a natural language answer
        
        Args:
            question: Original question
            sql_query: SQL query that was executed
            data: Query results
            row_count: Number of rows returned
            
        Returns:
            Formatted answer string
        """
        try:
            # If no data, return simple message
            if row_count == 0:
                return f"I found no results matching your query: '{question}'."
            
            # For small datasets, provide summary
            if row_count <= 10:
                summary = f"I found {row_count} result(s) for your query. "
                
                # Add some key insights if available
                if data and len(data) > 0:
                    first_row = data[0]
                    keys = list(first_row.keys())
                    if keys:
                        summary += f"The data includes columns like: {', '.join(keys[:5])}. "
                
                return summary + "See the table below for details."
            else:
                return f"I found {row_count} results matching your query. The data is displayed in the table below."
                
        except Exception as e:
            logger.error(f"Error formatting answer: {str(e)}")
            return f"Query executed successfully. Found {row_count} result(s)."

