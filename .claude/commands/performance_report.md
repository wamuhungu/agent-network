# Performance Report Command

Generate detailed performance analytics and identify bottlenecks in the agent network.

## Purpose
Analyzes system performance to provide:
- Agent productivity metrics
- Task completion rates and trends
- Processing time analysis
- Bottleneck identification
- Efficiency recommendations

## Usage
```bash
# Generate performance report for the last 7 days (default)
project:performance_report

# Generate report for specific time period
project:performance_report --days 30
```

## Implementation

```bash
#!/bin/bash

# Parse command line arguments
DAYS=7
if [ "$1" = "--days" ] && [ -n "$2" ]; then
    DAYS=$2
fi

echo "📊 AGENT NETWORK PERFORMANCE REPORT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Report Period: Last $DAYS days"
echo "Generated: $(date +'%Y-%m-%d %H:%M:%S')"
echo ""

# Generate comprehensive performance analysis
python3 -c "
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict
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
    start_date = now - timedelta(days=$DAYS)
    
    # ================== EXECUTIVE SUMMARY ==================
    print('📋 EXECUTIVE SUMMARY')
    print('─────────────────────────────────────────────────')
    
    # Get key metrics
    total_tasks = sm.db.tasks.count_documents({
        'created_at': {'\$gte': start_date}
    })
    
    completed_tasks = sm.db.tasks.count_documents({
        'status': 'completed',
        'metadata.completed_at': {'\$gte': start_date.isoformat()}
    })
    
    failed_tasks = sm.db.tasks.count_documents({
        'status': 'failed',
        'updated_at': {'\$gte': start_date}
    })
    
    in_progress = sm.db.tasks.count_documents({
        'status': {'\$in': ['assigned', 'in_progress']}
    })
    
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    print(f'Total Tasks Created:    {total_tasks}')
    print(f'Tasks Completed:        {completed_tasks}')
    print(f'Tasks Failed:           {failed_tasks}')
    print(f'Currently In Progress:  {in_progress}')
    print(f'Completion Rate:        {completion_rate:.1f}%')
    
    print()
    
    # ================== AGENT PERFORMANCE ==================
    print('👥 AGENT PERFORMANCE METRICS')
    print('─────────────────────────────────────────────────')
    
    agents = ['manager', 'developer']
    
    for agent_id in agents:
        print(f'\\n{agent_id.upper()}:')
        
        # Get agent-specific metrics
        agent_activities = sm.db.activity_logs.count_documents({
            'agent_id': agent_id,
            'timestamp': {'\$gte': start_date}
        })
        
        # Task metrics for the agent
        if agent_id == 'manager':
            tasks_created = sm.db.tasks.count_documents({
                'created_by': agent_id,
                'created_at': {'\$gte': start_date}
            })
            tasks_assigned = sm.db.activity_logs.count_documents({
                'agent_id': agent_id,
                'activity_type': 'task_assigned',
                'timestamp': {'\$gte': start_date}
            })
            print(f'  • Tasks Created:     {tasks_created}')
            print(f'  • Tasks Assigned:    {tasks_assigned}')
            
        elif agent_id == 'developer':
            tasks_completed = sm.db.tasks.count_documents({
                'metadata.completed_by': agent_id,
                'metadata.completed_at': {'\$gte': start_date.isoformat()}
            })
            
            # Calculate average completion time
            completed_with_duration = list(sm.db.tasks.find({
                'metadata.completed_by': agent_id,
                'metadata.duration_seconds': {'\$exists': True},
                'metadata.completed_at': {'\$gte': start_date.isoformat()}
            }))
            
            if completed_with_duration:
                durations = [t['metadata']['duration_seconds'] for t in completed_with_duration]
                avg_duration = statistics.mean(durations)
                median_duration = statistics.median(durations)
                
                avg_hours = int(avg_duration // 3600)
                avg_mins = int((avg_duration % 3600) // 60)
                
                median_hours = int(median_duration // 3600)
                median_mins = int((median_duration % 3600) // 60)
                
                print(f'  • Tasks Completed:   {tasks_completed}')
                print(f'  • Avg Duration:      {avg_hours}h {avg_mins}m')
                print(f'  • Median Duration:   {median_hours}h {median_mins}m')
            else:
                print(f'  • Tasks Completed:   {tasks_completed}')
                print(f'  • Avg Duration:      N/A')
        
        print(f'  • Total Activities:  {agent_activities}')
        
        # Calculate uptime
        agent_state = sm.get_agent_state(agent_id)
        if agent_state and agent_state.get('start_time'):
            try:
                start_time = datetime.fromisoformat(agent_state['start_time'].replace('Z', '+00:00'))
                if start_time >= start_date:
                    uptime = now - start_time
                else:
                    uptime = now - start_date
                uptime_percent = (uptime.total_seconds() / (now - start_date).total_seconds()) * 100
                print(f'  • Uptime:            {uptime_percent:.1f}%')
            except:
                print(f'  • Uptime:            N/A')
    
    print()
    
    # ================== TASK PROCESSING ANALYSIS ==================
    print('⏱️  TASK PROCESSING ANALYSIS')
    print('─────────────────────────────────────────────────')
    
    # Get all completed tasks with durations
    pipeline = [
        {
            '\$match': {
                'status': 'completed',
                'metadata.duration_seconds': {'\$exists': True},
                'metadata.completed_at': {'\$gte': start_date.isoformat()}
            }
        },
        {
            '\$group': {
                '_id': '\$priority',
                'count': {'\$sum': 1},
                'avg_duration': {'\$avg': '\$metadata.duration_seconds'},
                'min_duration': {'\$min': '\$metadata.duration_seconds'},
                'max_duration': {'\$max': '\$metadata.duration_seconds'}
            }
        }
    ]
    
    priority_stats = list(sm.db.tasks.aggregate(pipeline))
    
    if priority_stats:
        print('\\nBy Priority:')
        for stat in sorted(priority_stats, key=lambda x: x['_id'] or 'normal'):
            priority = stat['_id'] or 'normal'
            count = stat['count']
            avg_dur = stat['avg_duration']
            min_dur = stat['min_duration']
            max_dur = stat['max_duration']
            
            avg_str = f'{int(avg_dur//3600)}h {int((avg_dur%3600)//60)}m' if avg_dur else 'N/A'
            min_str = f'{int(min_dur//3600)}h {int((min_dur%3600)//60)}m' if min_dur else 'N/A'
            max_str = f'{int(max_dur//3600)}h {int((max_dur%3600)//60)}m' if max_dur else 'N/A'
            
            print(f'  {priority:8} - Count: {count:3d}, Avg: {avg_str:8}, Range: {min_str} - {max_str}')
    
    # Daily completion trends
    print('\\nDaily Completion Trend:')
    
    daily_pipeline = [
        {
            '\$match': {
                'status': 'completed',
                'metadata.completed_at': {'\$gte': start_date.isoformat()}
            }
        },
        {
            '\$project': {
                'date': {
                    '\$dateToString': {
                        'format': '%Y-%m-%d',
                        'date': {'\$dateFromString': {'dateString': '\$metadata.completed_at'}}
                    }
                }
            }
        },
        {
            '\$group': {
                '_id': '\$date',
                'count': {'\$sum': 1}
            }
        },
        {
            '\$sort': {'_id': 1}
        }
    ]
    
    daily_completions = list(sm.db.tasks.aggregate(daily_pipeline))
    
    if daily_completions:
        max_daily = max(d['count'] for d in daily_completions)
        
        for day_stat in daily_completions[-7:]:  # Show last 7 days
            date = day_stat['_id']
            count = day_stat['count']
            bar_length = int((count / max_daily) * 30) if max_daily > 0 else 0
            bar = '█' * bar_length + '░' * (30 - bar_length)
            print(f'  {date} [{bar}] {count}')
    
    print()
    
    # ================== BOTTLENECK ANALYSIS ==================
    print('🚧 BOTTLENECK ANALYSIS')
    print('─────────────────────────────────────────────────')
    
    bottlenecks = []
    
    # Check task queue buildup
    created_tasks = sm.db.tasks.count_documents({'status': 'created'})
    if created_tasks > 5:
        bottlenecks.append({
            'severity': 'HIGH',
            'issue': f'{created_tasks} tasks waiting to be assigned',
            'impact': 'Task processing delay',
            'recommendation': 'Check manager agent availability'
        })
    
    # Check assigned but not started
    assigned_tasks = sm.db.tasks.count_documents({'status': 'assigned'})
    if assigned_tasks > 10:
        bottlenecks.append({
            'severity': 'MEDIUM',
            'issue': f'{assigned_tasks} tasks assigned but not started',
            'impact': 'Developer capacity issue',
            'recommendation': 'Scale developer agents or review task complexity'
        })
    
    # Check failed tasks
    if failed_tasks > 0:
        failed_recent = sm.db.tasks.find({
            'status': 'failed',
            'updated_at': {'\$gte': (now - timedelta(days=1))}
        }).limit(5)
        
        failure_reasons = defaultdict(int)
        for task in failed_recent:
            reason = task.get('metadata', {}).get('failure_reason', 'Unknown')
            failure_reasons[reason] += 1
        
        bottlenecks.append({
            'severity': 'HIGH',
            'issue': f'{failed_tasks} failed tasks',
            'impact': 'Reduced completion rate',
            'recommendation': f'Review failure reasons: {dict(failure_reasons)}'
        })
    
    # Check long-running tasks
    long_running = sm.db.tasks.count_documents({
        'status': 'in_progress',
        'metadata.started_at': {'\$lte': (now - timedelta(hours=24)).isoformat()}
    })
    
    if long_running > 0:
        bottlenecks.append({
            'severity': 'MEDIUM',
            'issue': f'{long_running} tasks running over 24 hours',
            'impact': 'Resource blocking',
            'recommendation': 'Review task complexity or add timeout handling'
        })
    
    # Display bottlenecks
    if bottlenecks:
        for bottleneck in sorted(bottlenecks, key=lambda x: x['severity'], reverse=True):
            severity = bottleneck['severity']
            emoji = '🔴' if severity == 'HIGH' else '🟡'
            
            print(f'\\n{emoji} {severity} PRIORITY')
            print(f'Issue: {bottleneck[\"issue\"]}')
            print(f'Impact: {bottleneck[\"impact\"]}')
            print(f'Recommendation: {bottleneck[\"recommendation\"]}')
    else:
        print('✅ No significant bottlenecks detected')
    
    print()
    
    # ================== EFFICIENCY RECOMMENDATIONS ==================
    print('💡 EFFICIENCY RECOMMENDATIONS')
    print('─────────────────────────────────────────────────')
    
    recommendations = []
    
    # Check completion rate
    if completion_rate < 80:
        recommendations.append({
            'area': 'Task Completion',
            'finding': f'Completion rate is {completion_rate:.1f}%',
            'action': 'Review task assignment logic and agent availability'
        })
    
    # Check agent balance
    if completed_tasks > 0:
        developer_completions = sm.db.tasks.count_documents({
            'metadata.completed_by': 'developer',
            'metadata.completed_at': {'\$gte': start_date.isoformat()}
        })
        
        if total_tasks > 20 and developer_completions == 0:
            recommendations.append({
                'area': 'Agent Utilization',
                'finding': 'Developer agent has no completions',
                'action': 'Check developer agent status and task routing'
            })
    
    # Check activity patterns
    hour_pipeline = [
        {
            '\$match': {
                'timestamp': {'\$gte': start_date}
            }
        },
        {
            '\$project': {
                'hour': {'\$hour': '\$timestamp'}
            }
        },
        {
            '\$group': {
                '_id': '\$hour',
                'count': {'\$sum': 1}
            }
        },
        {
            '\$sort': {'count': -1}
        }
    ]
    
    hourly_activity = list(sm.db.activity_logs.aggregate(hour_pipeline))
    
    if hourly_activity:
        peak_hour = hourly_activity[0]['_id']
        peak_count = hourly_activity[0]['count']
        
        quiet_hours = [h for h in hourly_activity if h['count'] < peak_count * 0.1]
        if len(quiet_hours) > 12:
            recommendations.append({
                'area': 'Utilization',
                'finding': f'{len(quiet_hours)} hours with minimal activity',
                'action': 'Consider 24/7 agent scheduling or batch processing'
            })
    
    # Display recommendations
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f'\\n{i}. {rec[\"area\"]}')
            print(f'   Finding: {rec[\"finding\"]}')
            print(f'   Action: {rec[\"action\"]}')
    else:
        print('✅ System is operating efficiently')
    
    # ================== TREND ANALYSIS ==================
    print()
    print('📈 TREND ANALYSIS')
    print('─────────────────────────────────────────────────')
    
    # Compare with previous period
    prev_start = start_date - timedelta(days=$DAYS)
    prev_end = start_date
    
    prev_completed = sm.db.tasks.count_documents({
        'status': 'completed',
        'metadata.completed_at': {
            '\$gte': prev_start.isoformat(),
            '\$lt': prev_end.isoformat()
        }
    })
    
    current_completed = completed_tasks
    
    if prev_completed > 0:
        trend = ((current_completed - prev_completed) / prev_completed) * 100
        trend_emoji = '📈' if trend > 0 else '📉' if trend < 0 else '➡️'
        print(f'\\nCompletion Trend: {trend_emoji} {trend:+.1f}% vs previous period')
    
    # Task complexity trend (using duration as proxy)
    current_durations = list(sm.db.tasks.find({
        'status': 'completed',
        'metadata.duration_seconds': {'\$exists': True},
        'metadata.completed_at': {'\$gte': start_date.isoformat()}
    }, {'metadata.duration_seconds': 1}))
    
    if current_durations:
        current_avg = statistics.mean([t['metadata']['duration_seconds'] for t in current_durations])
        
        prev_durations = list(sm.db.tasks.find({
            'status': 'completed',
            'metadata.duration_seconds': {'\$exists': True},
            'metadata.completed_at': {
                '\$gte': prev_start.isoformat(),
                '\$lt': prev_end.isoformat()
            }
        }, {'metadata.duration_seconds': 1}))
        
        if prev_durations:
            prev_avg = statistics.mean([t['metadata']['duration_seconds'] for t in prev_durations])
            complexity_trend = ((current_avg - prev_avg) / prev_avg) * 100
            
            trend_emoji = '📈' if complexity_trend > 10 else '📉' if complexity_trend < -10 else '➡️'
            print(f'Task Complexity: {trend_emoji} {complexity_trend:+.1f}% change in avg duration')
    
    sm.disconnect()
    
except ImportError as e:
    print(f'❌ Required module not available: {e}')
except Exception as e:
    print(f'❌ Error generating report: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 End of Performance Report"
echo "💾 To export: project:performance_report > report.txt"
```

## Report Sections

### Executive Summary
- Total tasks created in period
- Completion and failure counts
- Current in-progress tasks
- Overall completion rate

### Agent Performance Metrics
**Manager Agent:**
- Tasks created and assigned
- Total activities logged
- Uptime percentage

**Developer Agent:**
- Tasks completed
- Average and median duration
- Total activities logged
- Uptime percentage

### Task Processing Analysis
**By Priority:**
- Task count per priority level
- Average processing time
- Min/max duration range

**Daily Trends:**
- Visual bar chart of daily completions
- Last 7 days displayed
- Trend identification

### Bottleneck Analysis
Automatic detection of:
- Task queue buildup
- Unstarted assigned tasks
- Failed task patterns
- Long-running tasks (>24h)

Each bottleneck includes:
- Severity level (HIGH/MEDIUM)
- Issue description
- Business impact
- Specific recommendations

### Efficiency Recommendations
Analyzes and suggests improvements for:
- Low completion rates
- Agent utilization imbalances
- Activity pattern gaps
- Resource optimization

### Trend Analysis
- Period-over-period comparison
- Completion rate trends
- Task complexity changes
- Performance trajectory

## Usage Examples

```bash
# Default 7-day report
project:performance_report

# 30-day comprehensive report
project:performance_report --days 30

# Export to file
project:performance_report --days 14 > performance_report_2weeks.txt

# Monthly report
project:performance_report --days 30 > monthly_report_$(date +%Y%m).txt
```

## Sample Output
```
📊 AGENT NETWORK PERFORMANCE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report Period: Last 7 days
Generated: 2024-11-26 15:00:00

📋 EXECUTIVE SUMMARY
─────────────────────────────────────────────────
Total Tasks Created:    156
Tasks Completed:        142
Tasks Failed:           3
Currently In Progress:  11
Completion Rate:        91.0%

👥 AGENT PERFORMANCE METRICS
─────────────────────────────────────────────────

MANAGER:
  • Tasks Created:     156
  • Tasks Assigned:    153
  • Total Activities:  487
  • Uptime:            98.5%

DEVELOPER:
  • Tasks Completed:   142
  • Avg Duration:      2h 15m
  • Median Duration:   1h 45m
  • Total Activities:  892
  • Uptime:            97.2%

⏱️  TASK PROCESSING ANALYSIS
─────────────────────────────────────────────────

By Priority:
  high     - Count:  45, Avg: 3h 20m  , Range: 1h 15m - 8h 30m
  normal   - Count:  85, Avg: 1h 45m  , Range: 0h 30m - 4h 15m
  low      - Count:  12, Avg: 0h 55m  , Range: 0h 20m - 2h 10m

Daily Completion Trend:
  2024-11-20 [██████████████████░░░░░░░░░░░░] 18
  2024-11-21 [████████████████████████░░░░░░] 24
  2024-11-22 [███████████████████████████░░░] 26
  2024-11-23 [██████████████░░░░░░░░░░░░░░░░] 14
  2024-11-24 [████████████░░░░░░░░░░░░░░░░░░] 12
  2024-11-25 [██████████████████████████████] 28
  2024-11-26 [████████████████████░░░░░░░░░░] 20

🚧 BOTTLENECK ANALYSIS
─────────────────────────────────────────────────

🔴 HIGH PRIORITY
Issue: 3 failed tasks
Impact: Reduced completion rate
Recommendation: Review failure reasons: {'Timeout': 2, 'Error': 1}

💡 EFFICIENCY RECOMMENDATIONS
─────────────────────────────────────────────────
✅ System is operating efficiently

📈 TREND ANALYSIS
─────────────────────────────────────────────────

Completion Trend: 📈 +15.4% vs previous period
Task Complexity: ➡️ +2.3% change in avg duration
```

## Key Metrics Explained

**Completion Rate**: Percentage of created tasks that were completed
**Uptime**: Percentage of time agent was available during period
**Average Duration**: Mean time to complete tasks
**Median Duration**: Middle value of completion times
**Daily Trend**: Visual representation of productivity patterns

## Automated Reporting

Create a cron job for regular reports:
```bash
# Weekly report every Monday
0 9 * * 1 cd /path/to/project && project:performance_report --days 7 > reports/weekly_$(date +\%Y\%m\%d).txt

# Monthly report on the 1st
0 9 1 * * cd /path/to/project && project:performance_report --days 30 > reports/monthly_$(date +\%Y\%m).txt
```