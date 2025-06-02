# Activity Analysis Command

Analyze historical activity patterns and generate insights from agent behaviors.

## Purpose
Provides deep analysis of system activities including:
- Activity pattern recognition
- Peak usage identification
- Agent behavior analysis
- Communication flow visualization
- Anomaly detection

## Usage
```bash
# Analyze activities from the last 24 hours (default)
project:activity_analysis

# Analyze specific time period
project:activity_analysis --hours 48

# Filter by agent
project:activity_analysis --agent developer

# Filter by activity type
project:activity_analysis --type task_completed
```

## Implementation

```bash
#!/bin/bash

# Parse command line arguments
HOURS=24
AGENT_FILTER=""
TYPE_FILTER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --hours)
            HOURS="$2"
            shift 2
            ;;
        --agent)
            AGENT_FILTER="$2"
            shift 2
            ;;
        --type)
            TYPE_FILTER="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "🔍 AGENT NETWORK ACTIVITY ANALYSIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Analysis Period: Last $HOURS hours"
if [ -n "$AGENT_FILTER" ]; then
    echo "Agent Filter: $AGENT_FILTER"
fi
if [ -n "$TYPE_FILTER" ]; then
    echo "Type Filter: $TYPE_FILTER"
fi
echo "Generated: $(date +'%Y-%m-%d %H:%M:%S')"
echo ""

# Perform comprehensive activity analysis
python3 -c "
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

# Add tools directory to Python path
sys.path.append('tools')

try:
    from state_manager import StateManager
    
    # Initialize database connection
    sm = StateManager()
    if not sm.is_connected():
        print('❌ Database connection failed')
        sys.exit(1)
    
    # Calculate time boundaries
    now = datetime.utcnow()
    start_time = now - timedelta(hours=$HOURS)
    
    # Build query filters
    query = {'timestamp': {'\$gte': start_time}}
    if '$AGENT_FILTER':
        query['agent_id'] = '$AGENT_FILTER'
    if '$TYPE_FILTER':
        query['activity_type'] = '$TYPE_FILTER'
    
    # ================== ACTIVITY OVERVIEW ==================
    print('📊 ACTIVITY OVERVIEW')
    print('─────────────────────────────────────────────────')
    
    # Get total activities
    total_activities = sm.db.activity_logs.count_documents(query)
    
    if total_activities == 0:
        print('No activities found for the specified criteria')
        sm.disconnect()
        sys.exit(0)
    
    print(f'Total Activities: {total_activities}')
    
    # Calculate activity rate
    hours_elapsed = (now - start_time).total_seconds() / 3600
    activity_rate = total_activities / hours_elapsed
    print(f'Activity Rate: {activity_rate:.1f} per hour')
    
    # Get unique agents
    unique_agents = sm.db.activity_logs.distinct('agent_id', query)
    print(f'Active Agents: {len(unique_agents)} ({", ".join(unique_agents)})')
    
    print()
    
    # ================== ACTIVITY TYPE BREAKDOWN ==================
    print('📋 ACTIVITY TYPE BREAKDOWN')
    print('─────────────────────────────────────────────────')
    
    # Get activity type distribution
    type_pipeline = [
        {'\$match': query},
        {
            '\$group': {
                '_id': '\$activity_type',
                'count': {'\$sum': 1}
            }
        },
        {'\$sort': {'count': -1}}
    ]
    
    activity_types = list(sm.db.activity_logs.aggregate(type_pipeline))
    
    if activity_types:
        max_count = activity_types[0]['count']
        
        for activity in activity_types[:10]:  # Top 10 types
            activity_type = activity['_id']
            count = activity['count']
            percentage = (count / total_activities) * 100
            
            # Visual bar
            bar_length = int((count / max_count) * 30)
            bar = '█' * bar_length + '░' * (30 - bar_length)
            
            # Activity emoji
            emoji = {
                'initialization': '🚀',
                'task_created': '📝',
                'task_assigned': '📋',
                'task_completed': '✅',
                'task_failed': '❌',
                'work_request': '📨',
                'status_update': '📊',
                'error': '⚠️'
            }.get(activity_type, '•')
            
            print(f'{emoji} {activity_type:20} [{bar}] {count:4d} ({percentage:5.1f}%)')
    
    print()
    
    # ================== TEMPORAL PATTERNS ==================
    print('⏰ TEMPORAL PATTERNS')
    print('─────────────────────────────────────────────────')
    
    # Hourly distribution
    hourly_pipeline = [
        {'\$match': query},
        {
            '\$project': {
                'hour': {'\$hour': '\$timestamp'},
                'day_hour': {
                    '\$dateToString': {
                        'format': '%Y-%m-%d %H:00',
                        'date': '\$timestamp'
                    }
                }
            }
        },
        {
            '\$group': {
                '_id': '\$day_hour',
                'count': {'\$sum': 1}
            }
        },
        {'\$sort': {'_id': 1}}
    ]
    
    hourly_activities = list(sm.db.activity_logs.aggregate(hourly_pipeline))
    
    if hourly_activities:
        # Show recent hours
        recent_hours = hourly_activities[-24:] if len(hourly_activities) > 24 else hourly_activities
        
        if recent_hours:
            max_hourly = max(h['count'] for h in recent_hours)
            
            print('\\nHourly Activity (Recent 24h):')
            for i in range(0, len(recent_hours), 6):  # Show every 6 hours
                hour_data = recent_hours[i]
                hour_str = hour_data['_id'].split()[1]
                count = hour_data['count']
                
                bar_length = int((count / max_hourly) * 20) if max_hourly > 0 else 0
                bar = '█' * bar_length + '░' * (20 - bar_length)
                
                print(f'  {hour_str} [{bar}] {count}')
    
    # Peak activity analysis
    hour_counts = defaultdict(int)
    all_activities = sm.db.activity_logs.find(query, {'timestamp': 1})
    
    for activity in all_activities:
        hour = activity['timestamp'].hour
        hour_counts[hour] += 1
    
    if hour_counts:
        peak_hour = max(hour_counts, key=hour_counts.get)
        peak_count = hour_counts[peak_hour]
        avg_hourly = sum(hour_counts.values()) / 24
        
        print(f'\\nPeak Activity Hour: {peak_hour:02d}:00 ({peak_count} activities)')
        print(f'Average Per Hour: {avg_hourly:.1f}')
        
        # Identify quiet periods
        quiet_hours = [h for h in range(24) if hour_counts[h] < avg_hourly * 0.5]
        if quiet_hours:
            quiet_ranges = []
            start = quiet_hours[0]
            
            for i in range(1, len(quiet_hours)):
                if quiet_hours[i] != quiet_hours[i-1] + 1:
                    quiet_ranges.append(f'{start:02d}:00-{quiet_hours[i-1]:02d}:59')
                    start = quiet_hours[i]
            quiet_ranges.append(f'{start:02d}:00-{quiet_hours[-1]:02d}:59')
            
            print(f'Quiet Periods: {", ".join(quiet_ranges)}')
    
    print()
    
    # ================== AGENT BEHAVIOR ANALYSIS ==================
    print('🤖 AGENT BEHAVIOR ANALYSIS')
    print('─────────────────────────────────────────────────')
    
    # Agent activity breakdown
    agent_pipeline = [
        {'\$match': query},
        {
            '\$group': {
                '_id': {
                    'agent': '\$agent_id',
                    'type': '\$activity_type'
                },
                'count': {'\$sum': 1}
            }
        },
        {'\$sort': {'_id.agent': 1, 'count': -1}}
    ]
    
    agent_activities = list(sm.db.activity_logs.aggregate(agent_pipeline))
    
    # Group by agent
    agent_summary = defaultdict(lambda: defaultdict(int))
    for activity in agent_activities:
        agent = activity['_id']['agent']
        activity_type = activity['_id']['type']
        count = activity['count']
        agent_summary[agent][activity_type] = count
    
    for agent, activities in sorted(agent_summary.items()):
        total = sum(activities.values())
        print(f'\\n{agent.upper()} ({total} activities):')
        
        # Top 5 activities for this agent
        top_activities = sorted(activities.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for activity_type, count in top_activities:
            percentage = (count / total) * 100
            print(f'  • {activity_type:20} {count:4d} ({percentage:5.1f}%)')
        
        # Agent-specific metrics
        if agent == 'developer':
            completions = activities.get('task_completed', 0)
            assignments = activities.get('task_assigned', 0)
            if assignments > 0:
                completion_ratio = (completions / assignments) * 100
                print(f'  → Completion Ratio: {completion_ratio:.1f}%')
        
        elif agent == 'manager':
            created = activities.get('task_created', 0)
            assigned = activities.get('task_assigned', 0)
            if created > 0:
                assignment_ratio = (assigned / created) * 100
                print(f'  → Assignment Ratio: {assignment_ratio:.1f}%')
    
    print()
    
    # ================== COMMUNICATION FLOW ==================
    print('📡 COMMUNICATION FLOW')
    print('─────────────────────────────────────────────────')
    
    # Analyze task assignments and completions
    task_flow = {
        'manager_to_developer': 0,
        'developer_to_manager': 0
    }
    
    # Count task assignments (manager to developer)
    assignments = sm.db.activity_logs.count_documents({
        **query,
        'agent_id': 'manager',
        'activity_type': 'task_assigned'
    })
    task_flow['manager_to_developer'] = assignments
    
    # Count task completions (developer to manager)
    completions = sm.db.activity_logs.count_documents({
        **query,
        'agent_id': 'developer',
        'activity_type': 'completion_sent'
    })
    task_flow['developer_to_manager'] = completions
    
    print('Message Flow:')
    print(f'  Manager → Developer: {task_flow["manager_to_developer"]} task assignments')
    print(f'  Developer → Manager: {task_flow["developer_to_manager"]} completion notifications')
    
    if assignments > 0 and completions > 0:
        response_rate = (completions / assignments) * 100
        print(f'  Response Rate: {response_rate:.1f}%')
    
    print()
    
    # ================== ANOMALY DETECTION ==================
    print('🚨 ANOMALY DETECTION')
    print('─────────────────────────────────────────────────')
    
    anomalies = []
    
    # Check for error spikes
    error_activities = sm.db.activity_logs.count_documents({
        **query,
        'activity_type': {'\$in': ['error', 'task_failed']}
    })
    
    error_rate = (error_activities / total_activities) * 100 if total_activities > 0 else 0
    if error_rate > 5:
        anomalies.append({
            'type': 'High Error Rate',
            'severity': 'HIGH',
            'details': f'{error_rate:.1f}% of activities are errors',
            'recommendation': 'Review error logs and system health'
        })
    
    # Check for activity gaps
    activity_times = list(sm.db.activity_logs.find(
        query,
        {'timestamp': 1}
    ).sort('timestamp', 1))
    
    if len(activity_times) > 1:
        gaps = []
        for i in range(1, len(activity_times)):
            gap = (activity_times[i]['timestamp'] - activity_times[i-1]['timestamp']).total_seconds() / 60
            if gap > 60:  # Gap larger than 60 minutes
                gaps.append({
                    'start': activity_times[i-1]['timestamp'],
                    'end': activity_times[i]['timestamp'],
                    'duration': gap
                })
        
        if gaps:
            longest_gap = max(gaps, key=lambda x: x['duration'])
            anomalies.append({
                'type': 'Activity Gap',
                'severity': 'MEDIUM',
                'details': f'{longest_gap["duration"]:.0f} minute gap at {longest_gap["start"].strftime("%Y-%m-%d %H:%M")}',
                'recommendation': 'Check agent availability during this period'
            })
    
    # Check for unusual patterns
    if total_activities > 100:
        # Calculate standard deviation of hourly activities
        hourly_counts = list(hour_counts.values())
        if hourly_counts:
            mean_hourly = statistics.mean(hourly_counts)
            stdev_hourly = statistics.stdev(hourly_counts) if len(hourly_counts) > 1 else 0
            
            # Check for hours with activity > 2 standard deviations from mean
            unusual_hours = [h for h, count in hour_counts.items() 
                           if count > mean_hourly + 2 * stdev_hourly]
            
            if unusual_hours:
                anomalies.append({
                    'type': 'Unusual Activity Spike',
                    'severity': 'LOW',
                    'details': f'Abnormal activity at hours: {", ".join(f"{h:02d}:00" for h in unusual_hours)}',
                    'recommendation': 'Verify if this was expected behavior'
                })
    
    # Display anomalies
    if anomalies:
        for anomaly in sorted(anomalies, key=lambda x: {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}[x['severity']], reverse=True):
            severity = anomaly['severity']
            emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[severity]
            
            print(f'{emoji} {severity}: {anomaly["type"]}')
            print(f'   Details: {anomaly["details"]}')
            print(f'   Action: {anomaly["recommendation"]}')
            print()
    else:
        print('✅ No anomalies detected')
    
    # ================== TASK LIFECYCLE ANALYSIS ==================
    if not '$TYPE_FILTER':  # Only show if not filtering by type
        print()
        print('🔄 TASK LIFECYCLE ANALYSIS')
        print('─────────────────────────────────────────────────')
        
        # Track task lifecycle events
        lifecycle_events = sm.db.activity_logs.find({
            **query,
            'activity_type': {'\$in': ['task_created', 'task_assigned', 'task_completed']},
            'details.task_id': {'\$exists': True}
        }).sort('timestamp', 1)
        
        task_timelines = defaultdict(list)
        for event in lifecycle_events:
            task_id = event['details'].get('task_id')
            if task_id:
                task_timelines[task_id].append({
                    'type': event['activity_type'],
                    'time': event['timestamp']
                })
        
        # Calculate lifecycle metrics
        creation_to_assignment = []
        assignment_to_completion = []
        
        for task_id, events in task_timelines.items():
            event_dict = {e['type']: e['time'] for e in events}
            
            if 'task_created' in event_dict and 'task_assigned' in event_dict:
                delta = (event_dict['task_assigned'] - event_dict['task_created']).total_seconds() / 60
                creation_to_assignment.append(delta)
            
            if 'task_assigned' in event_dict and 'task_completed' in event_dict:
                delta = (event_dict['task_completed'] - event_dict['task_assigned']).total_seconds() / 60
                assignment_to_completion.append(delta)
        
        if creation_to_assignment:
            avg_c2a = statistics.mean(creation_to_assignment)
            median_c2a = statistics.median(creation_to_assignment)
            print(f'Creation → Assignment:')
            print(f'  Average: {avg_c2a:.1f} minutes')
            print(f'  Median: {median_c2a:.1f} minutes')
        
        if assignment_to_completion:
            avg_a2c = statistics.mean(assignment_to_completion)
            median_a2c = statistics.median(assignment_to_completion)
            print(f'\\nAssignment → Completion:')
            print(f'  Average: {avg_a2c/60:.1f} hours')
            print(f'  Median: {median_a2c/60:.1f} hours')
    
    sm.disconnect()
    
except ImportError as e:
    print(f'❌ Required module not available: {e}')
except Exception as e:
    print(f'❌ Error analyzing activities: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 End of Activity Analysis"
echo "💡 Use filters to drill down: --agent, --type, --hours"
```

## Analysis Components

### Activity Overview
- Total activity count
- Activity rate per hour
- List of active agents
- Time period coverage

### Activity Type Breakdown
- Distribution of activity types
- Visual bar charts
- Percentage breakdown
- Top 10 activity types
- Activity-specific emojis

### Temporal Patterns
- Hourly activity distribution
- Peak activity identification
- Average activity per hour
- Quiet period detection
- Activity trend visualization

### Agent Behavior Analysis
- Per-agent activity breakdown
- Top activities by agent
- Agent-specific metrics:
  - Developer: Completion ratio
  - Manager: Assignment ratio
- Behavioral pattern recognition

### Communication Flow
- Message flow between agents
- Task assignment tracking
- Completion notification tracking
- Response rate calculation
- Communication efficiency

### Anomaly Detection
Automatic detection of:
- High error rates (>5%)
- Activity gaps (>60 minutes)
- Unusual activity spikes
- Pattern deviations

Each anomaly includes:
- Type and severity
- Specific details
- Recommended actions

### Task Lifecycle Analysis
- Creation to assignment time
- Assignment to completion time
- Average and median durations
- Lifecycle bottleneck identification

## Usage Examples

```bash
# Default 24-hour analysis
project:activity_analysis

# Analyze last 48 hours
project:activity_analysis --hours 48

# Focus on developer agent
project:activity_analysis --agent developer

# Analyze only task completions
project:activity_analysis --type task_completed

# Combined filters
project:activity_analysis --hours 72 --agent manager --type task_created
```

## Sample Output
```
🔍 AGENT NETWORK ACTIVITY ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analysis Period: Last 24 hours
Generated: 2024-11-26 16:00:00

📊 ACTIVITY OVERVIEW
─────────────────────────────────────────────────
Total Activities: 847
Activity Rate: 35.3 per hour
Active Agents: 2 (manager, developer)

📋 ACTIVITY TYPE BREAKDOWN
─────────────────────────────────────────────────
✅ task_completed        [██████████████████████████████] 156 ( 18.4%)
📋 task_assigned         [████████████████████████░░░░░░] 120 ( 14.2%)
📝 task_created          [████████████████████████░░░░░░] 118 ( 13.9%)
📊 status_update         [████████████████░░░░░░░░░░░░░░]  89 ( 10.5%)
🚀 initialization        [████░░░░░░░░░░░░░░░░░░░░░░░░░░]  24 (  2.8%)

⏰ TEMPORAL PATTERNS
─────────────────────────────────────────────────

Hourly Activity (Recent 24h):
  00:00 [████░░░░░░░░░░░░░░░░]  12
  06:00 [████████░░░░░░░░░░░░]  24
  12:00 [████████████████████]  58
  18:00 [████████████░░░░░░░░]  36

Peak Activity Hour: 14:00 (67 activities)
Average Per Hour: 35.3
Quiet Periods: 01:00-05:59, 22:00-23:59

🤖 AGENT BEHAVIOR ANALYSIS
─────────────────────────────────────────────────

MANAGER (423 activities):
  • task_created           118 ( 27.9%)
  • task_assigned          120 ( 28.4%)
  • status_update           45 ( 10.6%)
  • initialization          12 (  2.8%)
  → Assignment Ratio: 101.7%

DEVELOPER (424 activities):
  • task_completed         156 ( 36.8%)
  • status_update           44 ( 10.4%)
  • task_assigned          120 ( 28.3%)
  • initialization          12 (  2.8%)
  → Completion Ratio: 130.0%

📡 COMMUNICATION FLOW
─────────────────────────────────────────────────
Message Flow:
  Manager → Developer: 120 task assignments
  Developer → Manager: 156 completion notifications
  Response Rate: 130.0%

🚨 ANOMALY DETECTION
─────────────────────────────────────────────────
✅ No anomalies detected

🔄 TASK LIFECYCLE ANALYSIS
─────────────────────────────────────────────────
Creation → Assignment:
  Average: 5.2 minutes
  Median: 3.8 minutes

Assignment → Completion:
  Average: 2.4 hours
  Median: 1.9 hours
```

## Activity Types Reference

Common activity types tracked:
- `initialization` - Agent startup
- `task_created` - New task creation
- `task_assigned` - Task assignment
- `task_completed` - Task completion
- `task_failed` - Task failure
- `status_update` - Status changes
- `work_request` - Work requests
- `error` - Error events

## Insights Provided

1. **Workload Distribution** - How work is spread across time
2. **Agent Efficiency** - Individual agent performance metrics
3. **Communication Health** - Inter-agent message flow
4. **System Reliability** - Error rates and anomalies
5. **Process Efficiency** - Task lifecycle timing
6. **Capacity Planning** - Peak usage and quiet periods