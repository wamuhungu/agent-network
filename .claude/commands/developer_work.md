# Developer Work Command

Check for available tasks and process work for the developer agent.

## Purpose
Performs a single work cycle to check current task status, pick up new task assignments if available, and provide guidance on task completion and next steps.

## Usage
```bash
# Run a single work cycle
project:developer_work
```

## Implementation

```bash
#!/bin/bash

TIMESTAMP=$(date -Iseconds)
CURRENT_TASK_ID=""
TASK_PICKED_UP=false
WORK_STATUS="idle"

echo "👨‍💻 DEVELOPER WORK CYCLE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Timestamp: $TIMESTAMP"
echo ""

# Ensure directories exist
mkdir -p .comms .logs .agents/developer

# Check current developer status
echo "📊 Checking current status..."
if [ -f .agents/developer/status.json ]; then
    CURRENT_STATUS=$(python3 -c "
import json
try:
    with open('.agents/developer/status.json', 'r') as f:
        data = json.load(f)
    status = data.get('status', 'unknown')
    current_tasks = data.get('current_tasks', [])
    if current_tasks:
        print(f\"{status}:{current_tasks[0].get('task_id', '')}\")
    else:
        print(status)
except:
    print('unknown')
" 2>/dev/null)
    
    if [[ "$CURRENT_STATUS" == *":"* ]]; then
        WORK_STATUS=$(echo "$CURRENT_STATUS" | cut -d':' -f1)
        CURRENT_TASK_ID=$(echo "$CURRENT_STATUS" | cut -d':' -f2)
    else
        WORK_STATUS="$CURRENT_STATUS"
    fi
    
    echo "  Current status: $WORK_STATUS"
    if [ -n "$CURRENT_TASK_ID" ]; then
        echo "  Current task: $CURRENT_TASK_ID"
    fi
else
    echo "  ⚠️  Developer status file not found"
    WORK_STATUS="uninitialized"
fi

echo ""

# Handle different work states
case "$WORK_STATUS" in
    "working")
        echo "🔄 CURRENTLY WORKING"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ -n "$CURRENT_TASK_ID" ]; then
            # Check if task file still exists (not completed yet)
            if [ -f ".comms/${CURRENT_TASK_ID}.json" ]; then
                # Get task description
                TASK_DESC=$(python3 -c "
import json
try:
    with open('.comms/${CURRENT_TASK_ID}.json', 'r') as f:
        data = json.load(f)
    print(data.get('task', {}).get('description', 'No description available')[:100] + '...')
except:
    print('Unable to get task description')
" 2>/dev/null)
                
                echo "Task: $CURRENT_TASK_ID"
                echo "Description: $TASK_DESC"
                echo ""
                echo "🎯 NEXT STEPS:"
                echo "  1. Continue implementing the task requirements"
                echo "  2. Ensure all deliverables are completed:"
                echo "     • Working implementation"
                echo "     • Comprehensive tests"
                echo "     • Documentation updates"
                echo "     • Code quality checks"
                echo "  3. When finished, run: project:complete_task \"$CURRENT_TASK_ID\""
                
                # Log work check
                echo "$TIMESTAMP [WORK] Checked current task: $CURRENT_TASK_ID" >> .logs/developer.log
            else
                echo "⚠️  Task file missing - task may have been completed externally"
                echo "Updating status to ready..."
                
                # Update status to ready
                python3 -c "
import json
try:
    with open('.agents/developer/status.json', 'r') as f:
        status = json.load(f)
    status['status'] = 'ready'
    status['current_tasks'] = []
    status['last_activity'] = '$TIMESTAMP'
    with open('.agents/developer/status.json', 'w') as f:
        json.dump(status, f, indent=2)
except:
    pass
"
                WORK_STATUS="ready"
            fi
        else
            echo "⚠️  No current task ID found despite working status"
            echo "Updating status to ready..."
            WORK_STATUS="ready"
        fi
        ;;
        
    "ready"|"idle")
        echo "🔍 LOOKING FOR NEW TASKS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Look for available task assignments
        AVAILABLE_TASKS=$(find .comms -name "task_*.json" -type f 2>/dev/null | head -1)
        
        if [ -n "$AVAILABLE_TASKS" ]; then
            NEXT_TASK_FILE="$AVAILABLE_TASKS"
            NEXT_TASK_ID=$(basename "$NEXT_TASK_FILE" .json)
            
            # Get task details
            TASK_INFO=$(python3 -c "
import json
try:
    with open('$NEXT_TASK_FILE', 'r') as f:
        data = json.load(f)
    task = data.get('task', {})
    print(f\"{task.get('description', 'No description')}|{data.get('priority', 'normal')}|{data.get('timestamp', 'unknown')}\")
except:
    print('Unable to parse task|unknown|unknown')
" 2>/dev/null)
            
            IFS='|' read -r TASK_DESC TASK_PRIORITY TASK_TIMESTAMP <<< "$TASK_INFO"
            
            echo "✅ Found available task: $NEXT_TASK_ID"
            echo "Description: $TASK_DESC"
            echo "Priority: $TASK_PRIORITY"
            echo "Created: $TASK_TIMESTAMP"
            echo ""
            echo "🚀 STARTING WORK..."
            
            # Update developer status to working
            python3 -c "
import json
from datetime import datetime

try:
    if os.path.exists('.agents/developer/status.json'):
        with open('.agents/developer/status.json', 'r') as f:
            status = json.load(f)
    else:
        status = {'agent_id': 'developer', 'agent_type': 'developer'}
    
    status['status'] = 'working'
    status['last_activity'] = '$TIMESTAMP'
    status['current_tasks'] = [{
        'task_id': '$NEXT_TASK_ID',
        'started_at': '$TIMESTAMP',
        'description': '$TASK_DESC'
    }]
    
    with open('.agents/developer/status.json', 'w') as f:
        json.dump(status, f, indent=2)
        
except Exception as e:
    import sys
    print(f'Error updating status: {e}', file=sys.stderr)
" 2>/dev/null
            
            # Log task pickup
            echo "$TIMESTAMP [WORK] Picked up task: $NEXT_TASK_ID" >> .logs/developer.log
            
            CURRENT_TASK_ID="$NEXT_TASK_ID"
            TASK_PICKED_UP=true
            WORK_STATUS="working"
            
            echo "Status updated to: working"
            echo ""
            echo "🎯 TASK REQUIREMENTS:"
            echo "  • Implement the requested functionality"
            echo "  • Write comprehensive tests"
            echo "  • Create or update documentation"
            echo "  • Follow coding standards in docs/standards/"
            echo "  • Ensure code quality and maintainability"
            echo ""
            echo "📁 IMPORTANT DIRECTORIES:"
            echo "  • Source code: src/"
            echo "  • Tests: tests/"
            echo "  • Documentation: docs/"
            echo "  • Standards: docs/standards/coding_standards.md"
            
        else
            echo "ℹ️  No tasks available in queue"
            echo ""
            echo "🎯 NEXT STEPS:"
            echo "  • Wait for manager to assign new tasks"
            echo "  • Run this command again in a few minutes"
            echo "  • Check .comms/ directory for new task_*.json files"
            echo ""
            echo "💡 Waiting for new tasks... Run /developer_work again to check, or use /auto_work to enable continuous checking"
            
            # Log no tasks available
            echo "$TIMESTAMP [WORK] No tasks available" >> .logs/developer.log
        fi
        ;;
        
    "uninitialized")
        echo "⚠️  DEVELOPER NOT INITIALIZED"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🎯 NEXT STEPS:"
        echo "  1. Initialize developer agent with: project:become_developer"
        echo "  2. Then run this command again: project:developer_work"
        ;;
        
    *)
        echo "❓ UNKNOWN STATUS: $WORK_STATUS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🎯 NEXT STEPS:"
        echo "  • Check .agents/developer/status.json file"
        echo "  • Consider reinitializing with: project:become_developer"
        ;;
esac

echo ""

# Display work summary
echo "📈 WORK CYCLE SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Status: $WORK_STATUS"

if [ -n "$CURRENT_TASK_ID" ]; then
    echo "Current task: $CURRENT_TASK_ID"
fi

if [ "$TASK_PICKED_UP" = true ]; then
    echo "Action: New task started"
    echo ""
    echo "💡 IMPLEMENTATION GUIDANCE:"
    echo "  • Start by reading the task requirements carefully"
    echo "  • Plan your implementation approach"
    echo "  • Follow the project's coding standards"
    echo "  • Test your implementation thoroughly"
    echo "  • Update documentation as needed"
    echo "  • When complete, run: project:complete_task \"$CURRENT_TASK_ID\""
fi

echo ""

# Provide next action guidance
case "$WORK_STATUS" in
    "working")
        echo "🔄 Continue working on current task, then run: project:complete_task \"$CURRENT_TASK_ID\""
        ;;
    "ready")
        if [ "$TASK_PICKED_UP" = true ]; then
            echo "🚀 Start implementing the picked up task"
        else
            echo "⏳ Run this command again in a few minutes to check for new tasks"
        fi
        ;;
    "uninitialized")
        echo "🏗️  Run: project:become_developer"
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Work Functions
1. **Status Check**: Reads current developer status and task assignments
2. **Task Pickup**: Automatically picks up available tasks when ready
3. **Work Guidance**: Provides specific next steps based on current state
4. **Status Updates**: Updates developer status when starting new tasks
5. **Implementation Guidance**: Shows requirements and directory structure

## Work States Handled
- **Working**: Currently has an active task - provides completion guidance
- **Ready/Idle**: Available for work - automatically picks up next task
- **Uninitialized**: Developer agent not set up - provides setup guidance
- **Unknown**: Handles edge cases and status file issues

## Output Information
- Current work status and task details
- Available task pickup with automatic assignment
- Implementation requirements and guidance
- Directory structure and coding standards
- Specific next steps and commands

## Files Updated
- Updates `.agents/developer/status.json` when picking up tasks
- Logs activities to `.logs/developer.log`
- Changes status from "ready" to "working" automatically

## Usage Pattern
Run this command:
- When starting a work session
- Periodically to check for new tasks (every few minutes)
- After completing setup tasks
- When unsure of current work status

## Example Output
```
👨‍💻 DEVELOPER WORK CYCLE
Timestamp: 2024-11-26T14:30:22-08:00

📊 Checking current status...
  Current status: ready

🔍 LOOKING FOR NEW TASKS
✅ Found available task: task_20241126_143022_A7F3Kx
Description: Add user authentication to the dashboard
Priority: normal
Created: 2024-11-26T14:30:22-08:00

🚀 STARTING WORK...
Status updated to: working

🎯 TASK REQUIREMENTS:
  • Implement the requested functionality
  • Write comprehensive tests
  • Create or update documentation
  • Follow coding standards in docs/standards/
  • Ensure code quality and maintainability

💡 IMPLEMENTATION GUIDANCE:
  • Start by reading the task requirements carefully
  • Plan your implementation approach
  • Follow the project's coding standards
  • Test your implementation thoroughly
  • When complete, run: project:complete_task "task_20241126_143022_A7F3Kx"
```