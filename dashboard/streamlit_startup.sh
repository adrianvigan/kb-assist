#!/bin/bash
# Azure App Service startup script for Streamlit
streamlit run Home.py --server.port=8000 --server.address=0.0.0.0 --server.headless=true
