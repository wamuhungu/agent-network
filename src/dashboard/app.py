"""
Agent Monitoring Dashboard

A web application that provides visibility into agent status, resource usage,
and task completion metrics for the agent network.
"""
import os
import sys
import json
from datetime import datetime
from flask import Flask, render_template, jsonify

# Add the project root to the path so we can import the monitor module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.monitor import AgentMonitor

app = Flask(__name__)
monitor = AgentMonitor(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')


@app.route('/api/agents/status')
def get_agent_status():
    """Get the current status of all agents."""
    return jsonify(monitor.get_agent_status())


@app.route('/api/agents/report')
def get_agent_report():
    """Get a comprehensive report of agent activities."""
    return jsonify(monitor.generate_report())


@app.route('/api/logs/recent')
def get_recent_logs():
    """Get the most recent log entries from the unified log."""
    try:
        log_path = os.path.join(monitor.log_dir, 'unified.jsonl')
        if not os.path.exists(log_path):
            return jsonify([])
            
        with open(log_path, 'r') as f:
            # Get the last 50 entries or all if less than 50
            lines = f.readlines()
            recent_logs = [json.loads(line) for line in lines[-50:] if line.strip()]
            
        return jsonify(recent_logs)
    except Exception as e:
        app.logger.error(f"Error getting recent logs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/active')
def get_active_tasks():
    """Get all active tasks in the system."""
    try:
        tasks = {}
        
        # Get all the logs
        for log_file in monitor.log_dir.glob("*.jsonl"):
            if log_file.name == "unified.jsonl":
                continue
                
            with open(log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                        
                    entry = json.loads(line)
                    if entry['activity_type'] == 'task_start':
                        task_id = entry['details'].get('task_id')
                        if task_id:
                            tasks[task_id] = {
                                'id': task_id,
                                'title': entry['details'].get('title', 'Unknown'),
                                'start_time': entry['timestamp'],
                                'agent': entry['agent_id'],
                                'status': 'in_progress'
                            }
                    elif entry['activity_type'] == 'task_complete':
                        task_id = entry['details'].get('task_id')
                        if task_id and task_id in tasks:
                            tasks[task_id]['status'] = 'completed'
                            tasks[task_id]['completion_time'] = entry['timestamp']
        
        # Filter to just active tasks
        active_tasks = [task for task in tasks.values() if task['status'] == 'in_progress']
        return jsonify(active_tasks)
    except Exception as e:
        app.logger.error(f"Error getting active tasks: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/completed')
def get_completed_tasks():
    """Get all completed tasks in the system."""
    try:
        tasks = {}
        
        # Get all the logs
        for log_file in monitor.log_dir.glob("*.jsonl"):
            if log_file.name == "unified.jsonl":
                continue
                
            with open(log_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                        
                    entry = json.loads(line)
                    if entry['activity_type'] == 'task_start':
                        task_id = entry['details'].get('task_id')
                        if task_id:
                            tasks[task_id] = {
                                'id': task_id,
                                'title': entry['details'].get('title', 'Unknown'),
                                'start_time': entry['timestamp'],
                                'agent': entry['agent_id'],
                                'status': 'in_progress'
                            }
                    elif entry['activity_type'] == 'task_complete':
                        task_id = entry['details'].get('task_id')
                        if task_id:
                            if task_id in tasks:
                                tasks[task_id]['status'] = 'completed'
                                tasks[task_id]['completion_time'] = entry['timestamp']
                            else:
                                # Handle case where we have completion but no start
                                tasks[task_id] = {
                                    'id': task_id,
                                    'title': entry['details'].get('title', 'Unknown'),
                                    'completion_time': entry['timestamp'],
                                    'agent': entry['agent_id'],
                                    'status': 'completed'
                                }
        
        # Filter to just completed tasks
        completed_tasks = [task for task in tasks.values() if task['status'] == 'completed']
        
        # Sort by completion time, newest first
        completed_tasks.sort(key=lambda x: x.get('completion_time', ''), reverse=True)
        
        return jsonify(completed_tasks)
    except Exception as e:
        app.logger.error(f"Error getting completed tasks: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)