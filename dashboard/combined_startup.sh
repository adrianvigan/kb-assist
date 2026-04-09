#!/bin/bash

# Combined startup script for both API and Dashboard

# Start Flask API on port 5000 in background
echo "🚀 Starting Flask API on port 5000..."
gunicorn --bind 127.0.0.1:5000 --timeout 600 app:app --daemon

# Give API time to start
sleep 5

# Start Streamlit on port 8000 (Azure's expected port)
echo "📊 Starting Streamlit Dashboard on port 8000..."
streamlit run Home.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true
