"""
Database connection and SQL validation utilities
"""

import os
import psycopg
from psycopg_pool import ConnectionPool
from typing import Dict, Any, Optional
import logging
import re

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Database connection pool
db_pool: Optional[ConnectionPool] = None


def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment variables"""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "database": os.getenv("DB_NAME", "lab_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


def init_db_pool(min_conn: int = 1, max_conn: int = 10):
    """Initialize database connection pool"""
    global db_pool
    
    if db_pool is None:
        config = get_db_config()
        try:
            # Build connection string for psycopg3
            conninfo = f"host={config['host']} port={config['port']} dbname={config['database']} user={config['user']} password={config['password']}"
            db_pool = ConnectionPool(
                conninfo,
                min_size=min_conn,
                max_size=max_conn
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {str(e)}")
            raise
    return db_pool


def get_db_connection():
    """Get a database connection from the pool"""
    if db_pool is None:
        init_db_pool()
    return db_pool.getconn()


def return_db_connection(conn):
    """Return a connection to the pool"""
    if conn:
        conn.close()


def validate_sql_query(sql_query: str) -> Dict[str, Any]:
    """
    Validate SQL query to ensure it's read-only and safe to execute.
    
    Returns:
        dict: {
            "is_valid": bool,
            "error": str (if invalid)
        }
    """
    if not sql_query or not sql_query.strip():
        return {"is_valid": False, "error": "Empty SQL query"}
    
    # Normalize query (remove extra whitespace, convert to uppercase for checking)
    query_upper = sql_query.upper().strip()
    
    # Block dangerous operations
    dangerous_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
        "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE"
    ]
    
    for keyword in dangerous_keywords:
        # Use word boundaries to avoid matching substrings
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, query_upper):
            return {
                "is_valid": False,
                "error": f"Query contains forbidden operation: {keyword}"
            }
    
    # Ensure it starts with SELECT
    if not query_upper.startswith("SELECT"):
        return {
            "is_valid": False,
            "error": "Query must be a SELECT statement only"
        }
    
    # Block multiple statements (prevent SQL injection via ;)
    if sql_query.count(';') > 1 or (sql_query.count(';') == 1 and not sql_query.strip().endswith(';')):
        return {
            "is_valid": False,
            "error": "Multiple statements not allowed"
        }
    
    # Block comments that might hide malicious code
    if '--' in sql_query or '/*' in sql_query:
        return {
            "is_valid": False,
            "error": "SQL comments not allowed"
        }
    
    # Additional safety: Check for function calls that modify data
    dangerous_functions = [
        "PG_", "COPY_", "IMPORT", "EXPORT"
    ]
    
    for func in dangerous_functions:
        if func in query_upper:
            return {
                "is_valid": False,
                "error": f"Dangerous function call detected"
            }
    
    return {"is_valid": True}


def test_connection() -> bool:
    """Test database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        return_db_connection(conn)
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

