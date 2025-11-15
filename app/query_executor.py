"""
Query executor for safely executing SQL queries and returning results
"""

import time
from typing import Dict, Any, List
import logging

from app.database import get_db_connection, return_db_connection

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Service for executing SQL queries safely"""
    
    def __init__(self, max_execution_time: int = 60):
        """
        Initialize query executor
        
        Args:
            max_execution_time: Maximum query execution time in seconds
        """
        self.max_execution_time = max_execution_time
        logger.info(f"QueryExecutor initialized with max execution time: {max_execution_time}s")
    
    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute SQL query and return results
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            dict: {
                "success": bool,
                "data": List[Dict[str, Any]],
                "execution_time_ms": float,
                "error": str (if failed)
            }
        """
        conn = None
        start_time = time.time()
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Set statement timeout
            cursor.execute(f"SET statement_timeout = {self.max_execution_time * 1000};")
            
            # Execute query
            cursor.execute(sql_query)
            
            # Get column names
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
            else:
                columns = []
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            data = [dict(zip(columns, row)) for row in rows]
            
            cursor.close()
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return_db_connection(conn)
            
            logger.info(f"Query executed successfully in {execution_time:.2f}ms. Rows: {len(data)}")
            
            return {
                "success": True,
                "data": data,
                "execution_time_ms": execution_time,
                "error": None
            }
            
        except Exception as e:
            if conn:
                return_db_connection(conn)
            
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"Query execution failed after {execution_time:.2f}ms: {error_msg}")
            
            return {
                "success": False,
                "data": [],
                "execution_time_ms": execution_time,
                "error": error_msg
            }

