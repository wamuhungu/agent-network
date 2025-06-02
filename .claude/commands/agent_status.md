# Agent Status Command

Check the status of all agents in the system using the MongoDB database.

## Purpose
Displays real-time status information for all agents, including their current state, capabilities, active tasks, and recent activities.

## Usage
```bash
# Check status of all agents
project:agent_status

# Check status of specific agent
project:agent_status developer
project:agent_status manager
```

## Implementation

```bash
#!/bin/bash

# Get agent parameter if provided
AGENT_FILTER="${1:-all}"

echo "🤖 AGENT NETWORK STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Timestamp: $(date -Iseconds)"
echo "Database: MongoDB (agent_network)"
echo ""

# Check database connection
DB_CHECK=$(python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager

try:
    sm = StateManager()
    if sm.is_connected():
        print('connected')
        sm.disconnect()
    else:
        print('disconnected')
except:
    print('error')
" 2>/dev/null)

if [ "$DB_CHECK" != "connected" ]; then
    echo "❌ Database connection failed"
    echo "💡 Make sure MongoDB is running: brew services start mongodb/brew/mongodb-community@7.0"
    exit 1
fi

# Get and display agent status
python3 -c "
import sys
import json
from datetime import datetime, timezone
sys.path.append('tools')
from state_manager import StateManager

def format_time_ago(timestamp):
    '''Format timestamp as time ago'''
    if not timestamp:
        return 'Never'
    
    try:
        if isinstance(timestamp, str):
            # Try parsing ISO format
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        else:
            dt = timestamp
            
        # Make timezone aware if needed
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        diff = now - dt
        
        if diff.total_seconds() < 60:
            return f'{int(diff.total_seconds())}s ago'
        elif diff.total_seconds() < 3600:
            return f'{int(diff.total_seconds() / 60)}m ago'
        elif diff.total_seconds() < 86400:
            return f'{int(diff.total_seconds() / 3600)}h ago'
        else:
            return f'{int(diff.total_seconds() / 86400)}d ago'
    except:
        return 'Unknown'

def display_agent_status(agent_data, sm):
    '''Display status for a single agent'''
    agent_id = agent_data.get('agent_id', 'Unknown')
    print(f\"📊 {agent_id.upper()} AGENT\")
    print('─' * 50)
    
    # Basic info
    print(f\"Status: {agent_data.get('status', 'unknown')}\")
    print(f\"Session: {agent_data.get('session_id', 'N/A')}\")
    print(f\"Last Activity: {format_time_ago(agent_data.get('last_activity'))}\")
    
    # Heartbeat
    last_heartbeat = agent_data.get('last_heartbeat')
    if last_heartbeat:
        print(f\"Last Heartbeat: {format_time_ago(last_heartbeat)}\")
    
    # Capabilities
    capabilities = agent_data.get('capabilities', [])
    if capabilities:
        print(f\"Capabilities: {len(capabilities)} registered\")
        for cap in capabilities[:3]:
            print(f\"  • {cap}\")
        if len(capabilities) > 3:
            print(f\"  ... and {len(capabilities) - 3} more\")
    
    # Current tasks
    tasks = sm.get_agent_tasks(agent_id, ['assigned', 'in_progress'])
    if tasks:
        print(f\"\\nActive Tasks: {len(tasks)}\")
        for task in tasks[:2]:
            print(f\"  • {task['task_id']} - {task.get('title', 'Untitled')}\")
            print(f\"    Status: {task.get('status', 'unknown')}, Priority: {task.get('priority', 'normal')}\")
        if len(tasks) > 2:
            print(f\"  ... and {len(tasks) - 2} more\")
    else:
        print(\"\\nActive Tasks: None\")
    
    # Recent activities
    activities = sm.get_activity_history(agent_id, limit=3)
    if activities:
        print(f\"\\nRecent Activities:\")
        for activity in activities:
            activity_type = activity.get('activity_type', 'unknown')
            timestamp = format_time_ago(activity.get('timestamp'))
            print(f\"  • {activity_type} - {timestamp}\")
    
    # Development tools (for developer)
    if agent_id == 'developer' and 'development_tools' in agent_data:
        tools = agent_data.get('development_tools', [])
        print(f\"\\nDevelopment Tools: {len(tools)} available\")

try:
    sm = StateManager()
    if sm.is_connected():
        filter_agent = '$AGENT_FILTER'
        
        if filter_agent == 'all':
            # Get all agents
            agents = sm.get_all_agent_states()
            
            if not agents:
                print('No agents found in database')
                print('\\n💡 Initialize agents with:')
                print('  • project:become_manager')
                print('  • project:become_developer')
            else:
                for i, agent in enumerate(agents):
                    if i > 0:
                        print('\\n')
                    display_agent_status(agent, sm)
        else:
            # Get specific agent
            agent = sm.get_agent_state(filter_agent)
            if agent:
                display_agent_status(agent, sm)
            else:
                print(f'❌ Agent \"{filter_agent}\" not found in database')
                print('\\n💡 Available agents:')
                all_agents = sm.get_all_agent_states()
                for a in all_agents:
                    print(f\"  • {a.get('agent_id')}\")
        
        # Show database statistics
        print('\\n' + '='*50)
        print('📊 DATABASE STATISTICS')
        print('─' * 50)
        
        stats = sm.get_database_stats()
        if stats.get('connected'):
            # Tasks
            tasks = stats['collections']['tasks']
            print(f\"Tasks: {tasks['count']} total\")
            print(f\"  • Pending: {tasks['pending']}\")
            print(f\"  • In Progress: {tasks['in_progress']}\")
            print(f\"  • Completed: {tasks['completed']}\")
            
            # Activities
            print(f\"\\nActivity Logs: {stats['collections']['activity_logs']['count']} entries\")
            
            # Work Requests
            requests = stats['collections']['work_requests']
            print(f\"\\nWork Requests: {requests['count']} total\")
            print(f\"  • Pending: {requests['pending']}\")
        
        sm.disconnect()
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"
```

## Features
- Real-time agent status from MongoDB
- Shows current tasks and workload
- Displays recent activities
- Shows agent capabilities and tools
- Database statistics summary
- Time-based activity tracking

## Status Information
For each agent, displays:
- Current status (active, working, idle, etc.)
- Session information
- Last activity and heartbeat
- Capabilities and tools
- Active tasks with priority
- Recent activity history

## Database Collections Used
- `agent_states` - Current agent status
- `tasks` - Task assignments and progress
- `activity_logs` - Agent activity history
- `work_requests` - Pending work requests

## Examples
```bash
# Check all agents
project:agent_status

# Check specific agent
project:agent_status developer
project:agent_status manager
```