"""
Combined app that runs both Flask API and Streamlit Dashboard
Flask serves API endpoints and proxies dashboard requests to Streamlit
"""
import subprocess
import time
import requests
from flask import Flask, request, jsonify, Response
import sys
import os

# Import the existing API server
from api_server import app as flask_app, submit_report

# Start Streamlit in background
print("Starting Streamlit dashboard...")
streamlit_process = subprocess.Popen([
    'streamlit', 'run', 'Home.py',
    '--server.port=8501',
    '--server.address=127.0.0.1',
    '--server.headless=true'
])

# Wait for Streamlit to start
time.sleep(5)

# Add proxy route for dashboard
@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>')
def proxy_dashboard(path):
    """Proxy requests to Streamlit dashboard"""
    # Skip API routes
    if path in ['submit', 'health']:
        return Response("Not found", status=404)

    # Proxy to Streamlit
    url = f'http://127.0.0.1:8501/{path}'
    try:
        resp = requests.get(
            url,
            headers={k: v for k, v in request.headers if k.lower() != 'host'},
            params=request.args,
            stream=True
        )

        # Forward response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return Response(f"Dashboard error: {str(e)}", status=500)

# Keep Flask app variable for gunicorn
app = flask_app

if __name__ == '__main__':
    flask_app.run(host='0.0.0.0', port=8000)
