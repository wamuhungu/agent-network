# System Dashboard Command

Real-time monitoring dashboard for agent status and task metrics.

## Purpose
Provides a comprehensive view of the agent network including:
- Current agent statuses and availability
- Active task distribution and progress
- Recent activities and completions
- System health metrics
- Message queue status

## Usage
```bash
# Display real-time system dashboard
project:system_dashboard
```

## Implementation

```bash
#!/bin/bash

echo "🎯 AGENT NETWORK SYSTEM DASHBOARD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Last Updated: $(date +'%Y-%m-%d %H:%M:%S')"
echo ""

# Get comprehensive system status from database
python3 -c "
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict

# Add tools directory to Python path
sys.path.append('tools')

try:
    from state_manager import StateManager
    from message_broker import MessageBroker
    
    # Initialize connections
    sm = StateManager()
    if not sm.is_connected():
        print('❌ Database connection failed')
        sys.exit(1)
    
    # Get current time for calculations
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # ================== AGENT STATUS SECTION ==================
    print('👥 AGENT STATUS')
    print('─────────────────────────────────────────────────')
    
    agents = ['manager', 'developer']
    for agent_id in agents:
        state = sm.get_agent_state(agent_id)
        if state:
            status = state.get('status', 'unknown')
            session_id = state.get('session_id', 'N/A')
            
            # Calculate uptime
            start_time = state.get('start_time')
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    uptime = now - start_dt
                    uptime_str = f'{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m'
                except:
                    uptime_str = 'N/A'
            else:
                uptime_str = 'N/A'
            
            # Check heartbeat
            last_heartbeat = state.get('last_heartbeat')
            if last_heartbeat:
                try:
                    heartbeat_dt = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                    heartbeat_age = (now - heartbeat_dt).total_seconds()
                    if heartbeat_age < 60:
                        heartbeat_status = '💚'
                    elif heartbeat_age < 300:
                        heartbeat_status = '💛'
                    else:
                        heartbeat_status = '💔'
                except:
                    heartbeat_status = '❓'
            else:
                heartbeat_status = '❓'
            
            # Status emoji
            status_emoji = {
                'active': '🟢',
                'working': '🔵',
                'listening': '👂',
                'ready': '✅',
                'error': '🔴',
                'stopped': '⚫'
            }.get(status, '❓')
            
            print(f'{agent_id.upper():12} {status_emoji} {status:10} {heartbeat_status} Uptime: {uptime_str}')
            
            # Show current task for developer
            if agent_id == 'developer' and status == 'working':
                current_task_id = state.get('current_task_id')
                if current_task_id:
                    print(f'             └─ Working on: {current_task_id}')
        else:
            print(f'{agent_id.upper():12} ⚫ offline')
    
    print()
    
    # ================== TASK METRICS SECTION ==================
    print('📊 TASK METRICS')
    print('─────────────────────────────────────────────────')
    
    # Get task statistics
    task_stats = sm.db.tasks.aggregate([
        {
            '\$group': {
                '_id': '\$status',
                'count': {'\$sum': 1}
            }
        }
    ])
    
    stats_dict = {stat['_id']: stat['count'] for stat in task_stats}
    total_tasks = sum(stats_dict.values())
    
    print(f'Total Tasks: {total_tasks}')
    print()
    
    # Display task distribution
    statuses = ['created', 'assigned', 'in_progress', 'completed', 'failed']
    for status in statuses:
        count = stats_dict.get(status, 0)
        if total_tasks > 0:
            percentage = (count / total_tasks) * 100
            bar_length = int(percentage / 5)  # Scale to 20 chars max
            bar = '█' * bar_length + '░' * (20 - bar_length)
            print(f'{status:12} [{bar}] {count:3d} ({percentage:5.1f}%)')
        else:
            print(f'{status:12} [░░░░░░░░░░░░░░░░░░░░] {count:3d} (  0.0%)')
    
    print()
    
    # ================== RECENT ACTIVITIES SECTION ==================
    print('🔄 RECENT ACTIVITIES (Last Hour)')
    print('─────────────────────────────────────────────────')
    
    # Get recent activities
    recent_activities = sm.db.activity_logs.find({
        'timestamp': {'\$gte': one_hour_ago}
    }).sort('timestamp', -1).limit(10)
    
    activity_count = 0
    for activity in recent_activities:
        activity_count += 1
        agent = activity.get('agent_id', 'unknown')
        activity_type = activity.get('activity_type', 'unknown')
        timestamp = activity.get('timestamp', now)
        
        # Calculate time ago
        time_diff = now - timestamp
        if time_diff.total_seconds() < 60:
            time_ago = f'{int(time_diff.total_seconds())}s ago'
        elif time_diff.total_seconds() < 3600:
            time_ago = f'{int(time_diff.total_seconds() / 60)}m ago'
        else:
            time_ago = f'{int(time_diff.total_seconds() / 3600)}h ago'
        
        # Activity emoji
        activity_emoji = {
            'task_created': '📝',
            'task_assigned': '📋',
            'task_completed': '✅',
            'task_failed': '❌',
            'initialization': '🚀',
            'error': '⚠️'
        }.get(activity_type, '•')
        
        # Get details
        details = activity.get('details', {})
        task_id = details.get('task_id', '')
        
        if task_id:
            print(f'{time_ago:>10} {activity_emoji} {agent:10} {activity_type:20} [{task_id}]')
        else:
            print(f'{time_ago:>10} {activity_emoji} {agent:10} {activity_type:20}')
    
    if activity_count == 0:
        print('No recent activities')
    
    print()
    
    # ================== MESSAGE QUEUE STATUS ==================
    print('📬 MESSAGE QUEUE STATUS')
    print('─────────────────────────────────────────────────')
    
    try:
        broker = MessageBroker()
        if broker.connect():
            queues = ['manager-queue', 'developer-queue', 'work-request-queue']
            
            for queue_name in queues:
                queue_info = broker.get_queue_info(queue_name)
                if queue_info:
                    messages = queue_info['messages']
                    consumers = queue_info['consumers']
                    
                    # Queue health indicator
                    if messages == 0:
                        health = '✅'
                    elif messages < 10:
                        health = '💛'
                    else:
                        health = '🔴'
                    
                    print(f'{queue_name:20} {health} Messages: {messages:3d}  Consumers: {consumers}')
                else:
                    print(f'{queue_name:20} ❓ Status unknown')
            
            broker.disconnect()
        else:
            print('❌ RabbitMQ connection failed')
    except Exception as e:
        print(f'❌ Error checking message queues: {e}')
    
    print()
    
    # ================== SYSTEM HEALTH ==================
    print('🏥 SYSTEM HEALTH')
    print('─────────────────────────────────────────────────')
    
    # Calculate health metrics
    health_issues = []
    
    # Check agent availability
    active_agents = sum(1 for agent in agents if sm.get_agent_state(agent) and 
                       sm.get_agent_state(agent).get('status') in ['active', 'working', 'listening', 'ready'])
    
    if active_agents < len(agents):
        health_issues.append(f'{len(agents) - active_agents} agent(s) offline')
    
    # Check task backlog
    pending_tasks = stats_dict.get('created', 0) + stats_dict.get('assigned', 0)
    if pending_tasks > 10:
        health_issues.append(f'{pending_tasks} tasks pending')
    
    # Check failed tasks
    failed_tasks = stats_dict.get('failed', 0)
    if failed_tasks > 0:
        health_issues.append(f'{failed_tasks} failed tasks')
    
    # Display health status
    if not health_issues:
        print('✅ All systems operational')
    else:
        print('⚠️  Issues detected:')
        for issue in health_issues:
            print(f'   • {issue}')
    
    # ================== PERFORMANCE SUMMARY ==================
    print()
    print('📈 PERFORMANCE SUMMARY (Last 24 Hours)')
    print('─────────────────────────────────────────────────')
    
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # Tasks completed in last 24 hours
    completed_24h = sm.db.tasks.count_documents({
        'status': 'completed',
        'metadata.completed_at': {'\$gte': twenty_four_hours_ago.isoformat()}
    })
    
    # Average task duration
    completed_tasks = sm.db.tasks.find({
        'status': 'completed',
        'metadata.duration_seconds': {'\$exists': True}
    })
    
    durations = []
    for task in completed_tasks:
        duration = task.get('metadata', {}).get('duration_seconds')
        if duration:
            durations.append(duration)
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        avg_duration_str = f'{int(avg_duration // 3600)}h {int((avg_duration % 3600) // 60)}m'
    else:
        avg_duration_str = 'N/A'
    
    print(f'Tasks Completed: {completed_24h}')
    print(f'Average Duration: {avg_duration_str}')
    print(f'Success Rate: {(completed_24h / (completed_24h + failed_tasks) * 100) if (completed_24h + failed_tasks) > 0 else 0:.1f}%')
    
    sm.disconnect()
    
except ImportError as e:
    print(f'❌ Required module not available: {e}')
except Exception as e:
    print(f'❌ Error generating dashboard: {e}')
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Press Ctrl+C to exit | Updates every 30 seconds"
echo "📊 For detailed reports use: project:performance_report"
```

## Features

### Agent Status Display
- Real-time agent status with visual indicators
- Heartbeat monitoring (💚 < 1min, 💛 < 5min, 💔 > 5min)
- Uptime tracking for each agent
- Current task display for working agents

### Task Metrics
- Total task count and distribution
- Visual progress bars for each status
- Percentage breakdown by status
- Support for: created, assigned, in_progress, completed, failed

### Recent Activities
- Last hour of system activities
- Time-relative display (seconds/minutes/hours ago)
- Activity type icons for quick recognition
- Task ID association where applicable

### Message Queue Status
- Real-time queue message counts
- Consumer connection monitoring
- Health indicators (✅ empty, 💛 < 10 messages, 🔴 > 10 messages)
- All major queues monitored

### System Health
- Automatic issue detection
- Agent availability checking
- Task backlog monitoring
- Failed task alerts

### Performance Summary
- 24-hour completion metrics
- Average task duration calculation
- Success rate percentage
- Historical performance tracking

## Display Elements

### Status Emojis
- 🟢 Active
- 🔵 Working
- 👂 Listening
- ✅ Ready
- 🔴 Error
- ⚫ Stopped/Offline

### Activity Icons
- 📝 Task Created
- 📋 Task Assigned
- ✅ Task Completed
- ❌ Task Failed
- 🚀 Initialization
- ⚠️ Error

## Example Output
```
🎯 AGENT NETWORK SYSTEM DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Last Updated: 2024-11-26 14:30:00

👥 AGENT STATUS
─────────────────────────────────────────────────
MANAGER      🟢 active      💚 Uptime: 2d 3h 45m
DEVELOPER    🔵 working     💚 Uptime: 2d 3h 42m
             └─ Working on: task_20241126_143022_A7F3Kx

📊 TASK METRICS
─────────────────────────────────────────────────
Total Tasks: 47

created      [░░░░░░░░░░░░░░░░░░░░]   2 ( 4.3%)
assigned     [██░░░░░░░░░░░░░░░░░░]   5 (10.6%)
in_progress  [████░░░░░░░░░░░░░░░░]   8 (17.0%)
completed    [████████████████░░░░]  32 (68.1%)
failed       [░░░░░░░░░░░░░░░░░░░░]   0 ( 0.0%)

🔄 RECENT ACTIVITIES (Last Hour)
─────────────────────────────────────────────────
      5m ago 📋 manager    task_assigned        [task_20241126_144500_XY7Z9]
     12m ago ✅ developer  task_completed       [task_20241126_143022_A7F3Kx]
     25m ago 📝 manager    task_created         [task_20241126_142500_B8K2P]
     45m ago 🚀 developer  initialization       

📬 MESSAGE QUEUE STATUS
─────────────────────────────────────────────────
manager-queue        ✅ Messages:   0  Consumers: 1
developer-queue      💛 Messages:   3  Consumers: 1
work-request-queue   ✅ Messages:   0  Consumers: 0

🏥 SYSTEM HEALTH
─────────────────────────────────────────────────
✅ All systems operational

📈 PERFORMANCE SUMMARY (Last 24 Hours)
─────────────────────────────────────────────────
Tasks Completed: 28
Average Duration: 1h 45m
Success Rate: 100.0%
```

## Auto-Refresh Version

For continuous monitoring, create a wrapper script:
```bash
# Watch mode - auto-refresh every 30 seconds
while true; do
    clear
    project:system_dashboard
    sleep 30
done
```