#!/bin/bash

# Start Flask API on port 5000 in background
echo "Starting Flask API on port 5000..."
gunicorn --bind 127.0.0.1:5000 --timeout 600 api_server:app &

# Wait for API to start
sleep 3

# Start Streamlit Dashboard on port 8501 in background
echo "Starting Streamlit Dashboard on port 8501..."
streamlit run Home.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true &

# Wait for Streamlit to start
sleep 3

# Start nginx as main process (keeps container running)
echo "Starting nginx reverse proxy on port 8000..."
nginx -c /home/site/wwwroot/nginx.conf -g 'daemon off;'
