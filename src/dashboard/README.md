# Agent Monitoring Dashboard

This component provides a web-based dashboard for monitoring the agent network system.

## Directory Structure

- `app.py`: Main Flask application with routes and API endpoints
- `templates/`: HTML templates
  - `index.html`: Main dashboard page template
- `static/`: Static assets
  - `css/`: CSS stylesheets
    - `style.css`: Custom styling for the dashboard
  - `js/`: JavaScript files
    - `dashboard.js`: Dashboard functionality including data fetching and UI updates

## Features

- Real-time monitoring of agent status
- Visualization of resource usage
- Tracking of active and completed tasks
- Activity log display
- Automatic data refresh every 30 seconds

## Integration with AgentMonitor

The dashboard integrates with the `AgentMonitor` class in `tools/monitor.py` to retrieve data about:

- Agent status
- Resource usage (tokens, compute time)
- Task completion metrics
- Activity logs

## API Endpoints

The dashboard provides several REST API endpoints:

- `/api/agents/status`: Get the current status of all agents
- `/api/agents/report`: Get a comprehensive report of agent activities
- `/api/tasks/active`: Get all active tasks
- `/api/tasks/completed`: Get all completed tasks
- `/api/logs/recent`: Get recent log entries

## Running the Dashboard

See the documentation in `docs/dashboard_guide.md` for detailed instructions on running and using the dashboard.