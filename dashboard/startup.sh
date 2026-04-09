#!/bin/bash
# Azure App Service startup script
gunicorn --bind=0.0.0.0:8000 --timeout 600 api_server:app
