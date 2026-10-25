"""
CloudShare application entry point.
Run with: python run.py   (development)
Or:        flask run       (with FLASK_APP=run.py)
"""

import os
import sys

# Ensure the cloudshare package root is in the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Development server – never use debug=True in production
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_ENV", "development") == "development",
    )
