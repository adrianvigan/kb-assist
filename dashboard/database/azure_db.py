"""
Database Connection Module (PostgreSQL via Neon.tech)
Handles all database connections and operations for KB Assist
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """
    Get DATABASE_URL from secrets or environment variables
    Reads fresh on each call to ensure secrets are available
    """
    # Try to import streamlit for secrets (Streamlit Cloud)
    try:
        import streamlit as st
        # Check if we're actually running in Streamlit Cloud (secrets available)
        if hasattr(st, 'secrets') and len(st.secrets) > 0:
            return st.secrets.get('DATABASE_URL', os.getenv('DATABASE_URL'))
        else:
            # Streamlit imported but no secrets - use environment variables
            return os.getenv('DATABASE_URL')
    except (ImportError, Exception):
        # Fall back to environment variables (local development)
        return os.getenv('DATABASE_URL')

def get_connection():
    """
    Get a connection to PostgreSQL Database (Neon.tech)
    Returns: psycopg2.Connection object
    """
    try:
        DATABASE_URL = get_database_url()
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not found in secrets or environment variables")
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL Database: {e}")
        raise

def get_connection_context():
    """
    Context manager for database connections
    Automatically commits and closes connection
    """
    from contextlib import contextmanager

    @contextmanager
    def _context():
        conn = get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    return _context()

def test_connection():
    """
    Test the database connection
    Returns: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print("Connected to PostgreSQL Database successfully!")
        print(f"Version: {version[0][:80]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to connect to PostgreSQL Database: {e}")
        return False

if __name__ == '__main__':
    # Test connection when run directly
    print("Testing PostgreSQL Database connection...")
    test_connection()
