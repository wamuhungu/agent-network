"""
Tests for the Agent Monitoring Dashboard

These tests verify that the dashboard functions correctly,
including API endpoints and rendering.
"""
import sys
import os
import json
import pytest
from pathlib import Path

# Add the project root to the path
project_root = Path(os.path.abspath(os.path.dirname(__file__))).parent
sys.path.insert(0, str(project_root))

from src.dashboard.app import app

@pytest.fixture
def client():
    """Create a test client for the dashboard app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    """Test that the index route returns the dashboard page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Agent Network Dashboard' in response.data


def test_agent_status_api(client):
    """Test the agent status API endpoint."""
    response = client.get('/api/agents/status')
    assert response.status_code == 200
    # Response should be valid JSON
    data = json.loads(response.data)
    assert isinstance(data, dict)


def test_agent_report_api(client):
    """Test the agent report API endpoint."""
    response = client.get('/api/agents/report')
    assert response.status_code == 200
    # Response should be valid JSON
    data = json.loads(response.data)
    assert isinstance(data, dict)
    assert 'report_time' in data
    assert 'agent_stats' in data


def test_tasks_api(client):
    """Test the tasks API endpoints."""
    # Test active tasks
    response = client.get('/api/tasks/active')
    assert response.status_code == 200
    active_tasks = json.loads(response.data)
    assert isinstance(active_tasks, list)
    
    # Test completed tasks
    response = client.get('/api/tasks/completed')
    assert response.status_code == 200
    completed_tasks = json.loads(response.data)
    assert isinstance(completed_tasks, list)


def test_logs_api(client):
    """Test the logs API endpoint."""
    response = client.get('/api/logs/recent')
    assert response.status_code == 200
    logs = json.loads(response.data)
    assert isinstance(logs, list)