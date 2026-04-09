"""
Azure SQL Database Connection Module (using pymssql - no ODBC required)
Handles all database connections and operations for KB Assist
"""
import pymssql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import streamlit for secrets (Streamlit Cloud)
try:
    import streamlit as st
    # Use Streamlit secrets if available (Streamlit Cloud)
    SERVER = st.secrets.get('AZURE_SQL_SERVER', os.getenv('AZURE_SQL_SERVER'))
    DATABASE = st.secrets.get('AZURE_SQL_DATABASE', os.getenv('AZURE_SQL_DATABASE'))
    USERNAME = st.secrets.get('AZURE_SQL_USERNAME', os.getenv('AZURE_SQL_USERNAME'))
    PASSWORD = st.secrets.get('AZURE_SQL_PASSWORD', os.getenv('AZURE_SQL_PASSWORD'))
except ImportError:
    # Fall back to environment variables (local development)
    SERVER = os.getenv('AZURE_SQL_SERVER')
    DATABASE = os.getenv('AZURE_SQL_DATABASE')
    USERNAME = os.getenv('AZURE_SQL_USERNAME')
    PASSWORD = os.getenv('AZURE_SQL_PASSWORD')

def get_connection():
    """
    Get a connection to Azure SQL Database using pymssql
    Returns: pymssql.Connection object
    """
    try:
        conn = pymssql.connect(
            server=SERVER,
            user=USERNAME,
            password=PASSWORD,
            database=DATABASE,
            as_dict=False
        )
        return conn
    except pymssql.Error as e:
        print(f"Error connecting to Azure SQL Database: {e}")
        raise

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
