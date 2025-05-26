# Manager Monitor Command

Monitor system status and process incoming messages for the manager agent.

## Purpose
Performs a single monitoring cycle to check for completion messages, process completed tasks, handle new requirements, and provide status updates with next action guidance.

## Usage
```bash
# Run a single monitoring cycle
project:manager_monitor
```

## Implementation

```bash
#!/bin/bash

TIMESTAMP=$(date -Iseconds)
PROCESSED_COUNT=0
COMPLETION_COUNT=0
REQUIREMENT_COUNT=0
NEXT_ACTIONS=()

echo "🔍 MANAGER MONITORING CYCLE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Timestamp: $TIMESTAMP"
echo ""

# Ensure directories exist
mkdir -p .comms/completed .comms/processed .logs

# Check for completion messages from developer
echo "📋 Checking for completion messages..."
COMPLETION_FILES=$(find .comms -name "completion_*.json" -type f 2>/dev/null || true)

if [ -n "$COMPLETION_FILES" ]; then
    for completion_file in $COMPLETION_FILES; do
        if [ -f "$completion_file" ]; then
            echo "  ✅ Processing: $(basename $completion_file)"
            
            # Extract task ID from completion message
            TASK_ID=$(python3 -c "
import json
try:
    with open('$completion_file', 'r') as f:
        data = json.load(f)
    print(data.get('task_id', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)
            
            # Log completion processing
            echo "$TIMESTAMP [MONITOR] Processing completion for task: $TASK_ID" >> .logs/manager.log
            
            # Move completion message to processed
            mv "$completion_file" ".comms/processed/"
            
            COMPLETION_COUNT=$((COMPLETION_COUNT + 1))
            PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
        fi
    done
else
    echo "  ℹ️  No completion messages found"
fi

echo ""

# Check for new requirements
echo "📥 Checking for new requirements..."
REQUIREMENT_FILES=$(find .comms -name "requirement_*.json" -type f 2>/dev/null || true)

if [ -n "$REQUIREMENT_FILES" ]; then
    for requirement_file in $REQUIREMENT_FILES; do
        if [ -f "$requirement_file" ]; then
            echo "  📝 New requirement: $(basename $requirement_file)"
            
            # Extract requirement summary
            REQ_SUMMARY=$(python3 -c "
import json
try:
    with open('$requirement_file', 'r') as f:
        data = json.load(f)
    print(data.get('description', 'No description available')[:80] + '...')
except:
    print('Unable to parse requirement')
" 2>/dev/null)
            
            echo "     Summary: $REQ_SUMMARY"
            
            # Log requirement detection
            echo "$TIMESTAMP [MONITOR] New requirement detected: $(basename $requirement_file)" >> .logs/manager.log
            
            REQUIREMENT_COUNT=$((REQUIREMENT_COUNT + 1))
            PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
            
            NEXT_ACTIONS+=("Create task from requirement: $(basename $requirement_file)")
        fi
    done
else
    echo "  ℹ️  No new requirements found"
fi

echo ""

# Check pending tasks
echo "📊 Checking system status..."
PENDING_TASKS=$(find .comms -name "task_*.json" -type f 2>/dev/null | wc -l | tr -d ' ')
ARCHIVED_TASKS=$(find .comms/completed -name "task_*.json" -type f 2>/dev/null | wc -l | tr -d ' ')

echo "  📋 Pending tasks: $PENDING_TASKS"
echo "  ✅ Completed tasks: $ARCHIVED_TASKS"

# Check developer status
if [ -f .agents/developer/status.json ]; then
    DEV_STATUS=$(python3 -c "
import json
try:
    with open('.agents/developer/status.json', 'r') as f:
        data = json.load(f)
    print(data.get('status', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)
    echo "  👨‍💻 Developer status: $DEV_STATUS"
    
    if [ "$DEV_STATUS" = "ready" ] && [ "$PENDING_TASKS" -gt 0 ]; then
        NEXT_ACTIONS+=("Developer ready - tasks available for assignment")
    fi
else
    echo "  ⚠️  Developer status file not found"
    NEXT_ACTIONS+=("Initialize developer agent")
fi

echo ""

# Update manager status
if [ -f .agents/manager/status.json ]; then
    python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('.agents/manager/status.json', 'r') as f:
        status = json.load(f)
    
    status['last_activity'] = '$TIMESTAMP'
    status['monitoring'] = {
        'last_check': '$TIMESTAMP',
        'completions_processed': $COMPLETION_COUNT,
        'requirements_found': $REQUIREMENT_COUNT,
        'pending_tasks': $PENDING_TASKS,
        'completed_tasks': $ARCHIVED_TASKS
    }
    
    with open('.agents/manager/status.json', 'w') as f:
        json.dump(status, f, indent=2)
        
except Exception as e:
    print(f'Warning: Could not update manager status: {e}', file=sys.stderr)
"
    echo "✅ Manager status updated"
else
    echo "⚠️  Manager status file not found"
    NEXT_ACTIONS+=("Initialize manager agent with 'project:become_manager'")
fi

# Log monitoring cycle
echo "$TIMESTAMP [MONITOR] Monitoring cycle completed - Processed: $PROCESSED_COUNT items" >> .logs/manager.log

echo ""

# Display summary
echo "📈 MONITORING SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Items processed: $PROCESSED_COUNT"
echo "  • Completions: $COMPLETION_COUNT"
echo "  • Requirements: $REQUIREMENT_COUNT"
echo "System status: $PENDING_TASKS pending, $ARCHIVED_TASKS completed"
echo ""

# Provide next actions guidance
if [ ${#NEXT_ACTIONS[@]} -gt 0 ]; then
    echo "🎯 RECOMMENDED NEXT ACTIONS:"
    for i in "${!NEXT_ACTIONS[@]}"; do
        echo "  $((i+1)). ${NEXT_ACTIONS[i]}"
    done
    echo ""
    echo "💡 SUGGESTED COMMANDS:"
    
    if [ "$REQUIREMENT_COUNT" -gt 0 ]; then
        echo "  • project:create_task \"[description from requirement]\""
    fi
    
    if [ "$DEV_STATUS" = "ready" ] && [ "$PENDING_TASKS" -gt 0 ]; then
        echo "  • Developer can run: project:developer_work"
    fi
    
    if [ "$PENDING_TASKS" -eq 0 ] && [ "$REQUIREMENT_COUNT" -eq 0 ]; then
        echo "  • System idle - waiting for new requirements"
        echo "  • Consider running this monitor again in a few minutes"
    fi
else
    echo "✅ SYSTEM STATUS: All up to date"
    echo "💡 Run this monitor again periodically to check for new activity"
fi

echo ""
echo "🔄 To continue monitoring, run: project:manager_monitor"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Monitoring Functions
1. **Completion Processing**: Finds and processes completion messages from developer
2. **Requirement Detection**: Identifies new requirement files for task creation
3. **Status Updates**: Updates manager status with current timestamp and metrics
4. **System Overview**: Shows pending/completed task counts and agent status
5. **Next Actions**: Provides specific guidance on what to do next

## Output Information
- Timestamp and processing summary
- Count of processed completions and requirements
- System status (pending/completed tasks, developer status)
- Recommended next actions with specific commands
- Guidance for continued monitoring

## Files Updated
- Moves completion messages to `.comms/processed/`
- Updates `.agents/manager/status.json` with monitoring data
- Logs activities to `.logs/manager.log`

## Usage Pattern
Run this command periodically (every few minutes) to:
- Process completed work
- Identify new requirements
- Get guidance on next management actions
- Maintain system awareness

## Example Output
```
🔍 MANAGER MONITORING CYCLE
Timestamp: 2024-11-26T14:30:22-08:00

📋 Checking for completion messages...
  ✅ Processing: completion_20241126_143022_B8G4Ly.json

📥 Checking for new requirements...
  ℹ️  No new requirements found

📊 Checking system status...
  📋 Pending tasks: 2
  ✅ Completed tasks: 1
  👨‍💻 Developer status: ready

🎯 RECOMMENDED NEXT ACTIONS:
  1. Developer ready - tasks available for assignment

💡 SUGGESTED COMMANDS:
  • Developer can run: project:developer_work
```