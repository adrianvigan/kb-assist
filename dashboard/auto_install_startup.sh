#!/bin/bash

echo "🔍 Checking if packages are installed..."

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "📦 Streamlit not found. Installing packages from requirements.txt..."
    pip install -r /home/site/wwwroot/requirements.txt --no-cache-dir
    echo "✅ Packages installed!"
else
    echo "✅ Streamlit already installed, skipping..."
fi

# Start Streamlit
echo "🚀 Starting Streamlit dashboard..."
streamlit run Home.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true
