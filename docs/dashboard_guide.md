# Agent Monitoring Dashboard Guide

This document provides an overview of the Agent Monitoring Dashboard, including how to run it, use it, and extend it.

## Overview

The Agent Monitoring Dashboard is a web-based tool that provides visibility into the agent network system, including:

- Current status of all agents
- Resource usage statistics and visualizations
- Active and completed task tracking
- Recent activity logs

The dashboard automatically refreshes every 30 seconds to provide up-to-date information.

## Running the Dashboard

### Prerequisites

- Python 3.7 or higher
- Flask and other dependencies installed (`pip install -r requirements.txt`)

### Starting the Dashboard

From the project root directory, run:

```bash
python tools/run_dashboard.py
```

The dashboard will be available at [http://localhost:5000](http://localhost:5000).

## Dashboard Features

### Status Overview

The top section of the dashboard displays key metrics:

- Total number of agents in the network
- Number of active tasks
- Number of completed tasks
- Total tokens used and estimated cost

### Agent Status Panel

This panel shows detailed information about each agent:

- Active/inactive status
- Last activity timestamp
- Current task (if any)
- Recent activities with timestamps

Agents are considered "active" if they have logged activity within the last hour.

### Resource Usage Charts

The dashboard includes two visualizations:

1. **Token Usage Chart**: Bar chart showing token consumption by each agent
2. **Task Completion Rate Chart**: Doughnut chart showing the ratio of completed to in-progress tasks

### Tasks Panels

Two tabs display information about tasks:

1. **Active Tasks**: Currently in-progress tasks with their assigned agents and start times
2. **Completed Tasks**: Successfully completed tasks with their completion times

### Recent Activity Logs

The bottom panel shows the most recent log entries from all agents, including:

- Timestamp
- Agent ID
- Activity type (color-coded)
- Brief details about the activity

## API Endpoints

The dashboard provides several API endpoints for accessing data:

- `/api/agents/status`: Current status of all agents
- `/api/agents/report`: Comprehensive report of agent activities and resource usage
- `/api/tasks/active`: List of currently active tasks
- `/api/tasks/completed`: List of completed tasks
- `/api/logs/recent`: Most recent log entries

These endpoints return JSON data and can be used for integration with other tools.

## Extending the Dashboard

### Adding New Visualizations

To add new charts:

1. Add a new canvas element in the HTML template (`templates/index.html`)
2. Create and initialize the chart in `initializeCharts()` in `static/js/dashboard.js`
3. Add a function to update the chart with new data
4. Call this function from `refreshAllData()`

### Adding New API Endpoints

To add new API endpoints:

1. Add a new route function in `app.py`
2. Implement the data retrieval logic
3. Return the data as JSON using `jsonify()`
4. Add a corresponding fetch function in `dashboard.js`

## Troubleshooting

### Dashboard Not Loading

Check that:

- The Flask server is running
- You're accessing the correct URL
- There are no errors in the browser console
- The API endpoints are returning valid data

### No Agent Data Showing

If no agent data appears:

- Verify that the `.logs` directory exists and has log files
- Ensure agents are properly logging their activities
- Check for any errors in the server logs