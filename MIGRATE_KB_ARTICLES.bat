@echo off
echo ================================================================================
echo KB ARTICLES MIGRATION - SQLite to PostgreSQL
echo ================================================================================
echo.

echo [1/3] Installing required package...
pip install psycopg2-binary python-dotenv

echo.
echo [2/3] Creating kb_articles table in PostgreSQL...
python create_kb_articles_table.py

echo.
echo [3/3] Migrating data from SQLite to PostgreSQL...
python migrate_kb_articles.py

echo.
echo ================================================================================
echo DONE!
echo ================================================================================
pause
