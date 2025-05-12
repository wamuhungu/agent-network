#!/usr/bin/env python3
"""
Dashboard Runner

A simple script to run the agent monitoring dashboard.
"""
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(os.path.abspath(os.path.dirname(__file__))).parent
sys.path.insert(0, str(project_root))

from src.dashboard.app import app

if __name__ == "__main__":
    print("Starting Agent Network Dashboard...")
    print("Dashboard will be available at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)