import json
import os
import time
from datetime import datetime
from pathlib import Path
import uuid

class AgentMonitor:
    def __init__(self, project_dir='.'):
        self.project_dir = Path(project_dir)
        self.log_dir = self.project_dir / '.logs'
        self.log_dir.mkdir(exist_ok=True)
        
    def log_activity(self, agent_id, activity_type, details):
        """Log an agent activity"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': timestamp,
            'agent_id': agent_id,
            'activity_type': activity_type,
            'details': details
        }
        
        # Write to agent-specific log
        agent_log = self.log_dir / f"{agent_id}.jsonl"
        with open(agent_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
        # Write to unified log
        unified_log = self.log_dir / "unified.jsonl"
        with open(unified_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return log_entry['id']
    
    def track_resources(self, agent_id, tokens_used, compute_time):
        """Track resource usage"""
        return self.log_activity(
            agent_id, 
            'resource_usage',
            {
                'tokens_used': tokens_used,
                'compute_time': compute_time,
                'estimated_cost': tokens_used * 0.00002  # Example rate
            }
        )
    
    def get_agent_status(self):
        """Get current status of all agents"""
        agents = {}
        for log_file in self.log_dir.glob("*.jsonl"):
            if log_file.name == "unified.jsonl":
                continue
                
            agent_id = log_file.stem
            
            try:
                with open(log_file) as f:
                    # Get last 10 log entries
                    lines = f.readlines()
                    logs = [json.loads(line) for line in lines[-10:] if line.strip()]
                    
                agents[agent_id] = {
                    'last_activity': logs[-1]['timestamp'] if logs else None,
                    'current_task': next((log['details'].get('task_id') for log in reversed(logs) 
                                        if log['activity_type'] == 'task_start'), None),
                    'recent_activities': [{'type': log['activity_type'], 'time': log['timestamp']} 
                                        for log in logs[-5:]]
                }
            except Exception as e:
                agents[agent_id] = {'error': str(e)}
        
        return agents
    
    def generate_report(self):
        """Generate a summary report of agent activities"""
        all_agents = {}
        total_tokens = 0
        total_tasks = 0
        completed_tasks = 0
        
        # Process all agent logs
        for log_file in self.log_dir.glob("*.jsonl"):
            if log_file.name == "unified.jsonl":
                continue
                
            agent_id = log_file.stem
            agent_tokens = 0
            agent_tasks = 0
            agent_completed = 0
            
            try:
                with open(log_file) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        entry = json.loads(line)
                        
                        if entry['activity_type'] == 'resource_usage':
                            agent_tokens += entry['details'].get('tokens_used', 0)
                        elif entry['activity_type'] == 'task_start':
                            agent_tasks += 1
                        elif entry['activity_type'] == 'task_complete':
                            agent_completed += 1
                
                all_agents[agent_id] = {
                    'tokens_used': agent_tokens,
                    'tasks_started': agent_tasks,
                    'tasks_completed': agent_completed,
                    'completion_rate': agent_completed/agent_tasks if agent_tasks > 0 else 0
                }
                
                total_tokens += agent_tokens
                total_tasks += agent_tasks
                completed_tasks += agent_completed
                
            except Exception as e:
                all_agents[agent_id] = {'error': str(e)}
        
        return {
            'report_time': datetime.now().isoformat(),
            'agent_stats': all_agents,
            'total_tokens_used': total_tokens,
            'estimated_cost': total_tokens * 0.00002,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overall_completion_rate': completed_tasks/total_tasks if total_tasks > 0 else 0
        }

# Sample usage
if __name__ == "__main__":
    monitor = AgentMonitor()
    print(json.dumps(monitor.get_agent_status(), indent=2))
    print(json.dumps(monitor.generate_report(), indent=2))