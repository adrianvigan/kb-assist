"""
Azure SQL Database Connection Module
Handles all database connections and operations for KB Assist
"""
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure SQL connection details
SERVER = os.getenv('AZURE_SQL_SERVER')
DATABASE = os.getenv('AZURE_SQL_DATABASE')
USERNAME = os.getenv('AZURE_SQL_USERNAME')
PASSWORD = os.getenv('AZURE_SQL_PASSWORD')
DRIVER = os.getenv('AZURE_SQL_DRIVER', 'ODBC Driver 18 for SQL Server')

def get_connection():
    """
    Get a connection to Azure SQL Database
    Returns: pyodbc.Connection object
    """
    connection_string = (
        f'DRIVER={{{DRIVER}}};\
        SERVER={SERVER};\
        DATABASE={DATABASE};\
        UID={USERNAME};\
        PWD={PASSWORD};\
        Encrypt=yes;\
        TrustServerCertificate=no;\
        Connection Timeout=30;'
    )

    try:
        conn = pyodbc.connect(connection_string)
        return conn
    except pyodbc.Error as e:
        print(f"Error connecting to Azure SQL Database: {e}")
        raise

def execute_query(query, params=None, fetch=True):
    """
    Execute a SQL query
    Args:
        query: SQL query string
        params: Query parameters (tuple or list)
        fetch: Whether to fetch results (True for SELECT, False for INSERT/UPDATE/DELETE)
    Returns:
        For SELECT: list of rows
        For INSERT/UPDATE/DELETE: number of affected rows
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetch:
            # Fetch all rows for SELECT queries
            rows = cursor.fetchall()
            return rows
        else:
            # Commit changes for INSERT/UPDATE/DELETE
            conn.commit()
            return cursor.rowcount

    except pyodbc.Error as e:
        conn.rollback()
        print(f"Error executing query: {e}")
        raise

    finally:
        cursor.close()
        conn.close()

def execute_many(query, params_list):
    """
    Execute a query with multiple parameter sets (batch insert)
    Args:
        query: SQL query string
        params_list: List of parameter tuples
    Returns:
        Number of affected rows
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount

    except pyodbc.Error as e:
        conn.rollback()
        print(f"Error executing batch query: {e}")
        raise

    finally:
        cursor.close()
        conn.close()

def get_connection_context():
    """
    Get a connection as a context manager
    Usage:
        with get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    class ConnectionContext:
        def __enter__(self):
            self.conn = get_connection()
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close()

    return ConnectionContext()

def test_connection():
    """
    Test the database connection
    Returns: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()
        print(f"✅ Connected to Azure SQL Database successfully!")
        print(f"Version: {version[0][:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Azure SQL Database: {e}")
        return False

if __name__ == '__main__':
    # Test connection when run directly
    print("Testing Azure SQL Database connection...")
    test_connection()
