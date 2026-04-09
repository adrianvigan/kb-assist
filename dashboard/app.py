"""
Azure App Service entry point
Imports the Flask app from api_server
"""
from api_server import app

if __name__ == '__main__':
    app.run()
