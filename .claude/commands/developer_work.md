# Developer Work Command

Check for available tasks and process work for the developer agent using database state.

## Purpose
Performs a single work cycle to check current task status from the database, pick up new task assignments if available, and provide guidance on task completion and next steps.

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

# Check current developer status from database
echo "📊 Checking current status from database..."

DEVELOPER_STATUS=$(python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager

try:
    sm = StateManager()
    if sm.is_connected():
        # Get developer state
        state = sm.get_agent_state('developer')
        if state:
            status = state.get('status', 'unknown')
            
            # Get current tasks
            current_tasks = sm.get_agent_tasks('developer', ['assigned', 'in_progress'])
            
            # Update heartbeat
            sm.update_agent_state('developer', metadata={
                'last_work_check': '$TIMESTAMP'
            })
            
            if current_tasks:
                task = current_tasks[0]  # Get most recent task
                print(f\"{status}:{task['task_id']}:{task.get('title', 'Untitled')}\")
            else:
                print(f\"{status}::\")
                
            # Log work check
            sm.log_activity('developer', 'work_check', {
                'status': status,
                'active_tasks': len(current_tasks)
            })
            
            sm.disconnect()
        else:
            print('uninitialized::')
    else:
        print('db_error::')
except Exception as e:
    print(f'error::{e}')
" 2>/dev/null)

# Parse the status response
IFS=':' read -r WORK_STATUS CURRENT_TASK_ID TASK_TITLE <<< "$DEVELOPER_STATUS"

if [ "$WORK_STATUS" == "db_error" ]; then
    echo "  ❌ Database connection failed"
    echo "  💡 Make sure MongoDB is running: brew services start mongodb/brew/mongodb-community@7.0"
    exit 1
fi

echo "  Current status: $WORK_STATUS"
if [ -n "$CURRENT_TASK_ID" ]; then
    echo "  Current task: $CURRENT_TASK_ID"
    [ -n "$TASK_TITLE" ] && echo "  Task title: $TASK_TITLE"
fi

echo ""

# Handle different work states
case "$WORK_STATUS" in
    "working"|"active")
        echo "🔄 CURRENTLY WORKING"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ -n "$CURRENT_TASK_ID" ]; then
            # Get full task details from database
            python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager

sm = StateManager()
if sm.is_connected():
    task = sm.get_task_by_id('$CURRENT_TASK_ID')
    if task:
        print(f\"Task: {task['task_id']}\")
        print(f\"Title: {task.get('title', 'Untitled')}\")
        print(f\"Status: {task.get('status', 'unknown')}\")
        print(f\"Priority: {task.get('priority', 'normal')}\")
        desc = task.get('description', 'No description')
        print(f\"Description: {desc[:200]}{'...' if len(desc) > 200 else ''}\")
        
        # Show requirements
        reqs = task.get('requirements', [])
        if reqs:
            print(f\"\nRequirements ({len(reqs)}):\")
            for i, req in enumerate(reqs[:5], 1):
                print(f\"  {i}. {req}\")
            if len(reqs) > 5:
                print(f\"  ... and {len(reqs) - 5} more\")
    sm.disconnect()
"
            
            echo ""
            echo "🎯 NEXT STEPS:"
            echo "  1. Continue implementing the task requirements"
            echo "  2. Ensure all deliverables are completed:"
            echo "     • Working implementation"
            echo "     • Comprehensive tests"
            echo "     • Documentation updates"
            echo "     • Code quality checks"
            echo "  3. When finished, run: project:complete_task \"$CURRENT_TASK_ID\""
            
            # Log work status
            echo "$(date -Iseconds) [WORK] Developer working on task $CURRENT_TASK_ID" >> .logs/developer.log
        else:
            echo "⚠️  Status shows working but no active task found"
            echo "💡 Checking for new assignments..."
            WORK_STATUS="ready"
        fi
        ;;
        
    "ready"|"listening"|"idle")
        echo "✅ READY FOR WORK"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Checking for new task assignments..."
        echo ""
        
        # Check for pending tasks in database
        PENDING_TASKS=$(python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager

sm = StateManager()
if sm.is_connected():
    # Get unassigned or pending tasks
    pending = sm.get_tasks_by_status('pending')
    assigned = sm.get_agent_tasks('developer', ['assigned'])
    
    # Combine and show available tasks
    available = pending + assigned
    
    if available:
        print(f'FOUND:{len(available)}')
        for task in available[:3]:
            print(f\"TASK:{task['task_id']}:{task.get('title', 'Untitled')}:{task.get('priority', 'normal')}\")
    else:
        print('NONE')
        
    sm.disconnect()
" 2>/dev/null)
        
        if [[ "$PENDING_TASKS" == "FOUND:"* ]]; then
            TASK_COUNT=$(echo "$PENDING_TASKS" | head -1 | cut -d':' -f2)
            echo "📋 Found $TASK_COUNT available task(s):"
            
            # Display available tasks
            echo "$PENDING_TASKS" | grep "^TASK:" | while IFS=':' read -r _ TASK_ID TITLE PRIORITY; do
                echo "  • $TASK_ID - $TITLE (Priority: $PRIORITY)"
            done
            
            # Pick up the first available task
            FIRST_TASK=$(echo "$PENDING_TASKS" | grep "^TASK:" | head -1 | cut -d':' -f2)
            
            if [ -n "$FIRST_TASK" ]; then
                echo ""
                echo "🎯 PICKING UP TASK: $FIRST_TASK"
                
                # Update task assignment in database
                python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager

sm = StateManager()
if sm.is_connected():
    # Assign task to developer
    if sm.assign_task_to_agent('$FIRST_TASK', 'developer'):
        print('✅ Task assigned successfully')
        
        # Update developer status
        sm.update_agent_state('developer', 'working', {
            'current_task_id': '$FIRST_TASK',
            'task_started': '$TIMESTAMP'
        })
        
        # Log activity
        sm.log_activity('developer', 'task_pickup', {
            'task_id': '$FIRST_TASK',
            'method': 'developer_work_command'
        })
    else:
        print('❌ Failed to assign task')
        
    sm.disconnect()
"
                
                TASK_PICKED_UP=true
                echo ""
                echo "📋 Use project:developer_work again to see task details"
            fi
        else
            echo "📭 No pending tasks found"
            echo ""
            echo "💡 NEXT OPTIONS:"
            echo "  • Wait for task assignments from the manager"
            echo "  • Run project:request_work to request new tasks"
            echo "  • Check back later with project:developer_work"
        fi
        ;;
        
    "uninitialized")
        echo "⚠️  DEVELOPER NOT INITIALIZED"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "The developer agent has not been initialized."
        echo ""
        echo "💡 TO GET STARTED:"
        echo "  1. Run: project:become_developer"
        echo "  2. This will initialize the developer agent in the database"
        echo "  3. Then run this command again to check for work"
        ;;
        
    "error")
        echo "❌ ERROR CHECKING STATUS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "There was an error checking the developer status."
        echo "Error: $TASK_TITLE"
        echo ""
        echo "💡 TROUBLESHOOTING:"
        echo "  • Check MongoDB is running"
        echo "  • Verify database connection"
        echo "  • Check logs at .logs/developer.log"
        ;;
        
    *)
        echo "❓ UNKNOWN STATUS: $WORK_STATUS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "The developer is in an unknown state."
        echo ""
        echo "💡 Try running: project:become_developer"
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show summary
if [ "$TASK_PICKED_UP" = true ]; then
    echo "✅ Work cycle complete - New task assigned"
else
    echo "✅ Work cycle complete"
fi

# Update last work check in database
python3 -c "
import sys
sys.path.append('tools')
from state_manager import StateManager

sm = StateManager()
if sm.is_connected():
    sm.update_agent_state('developer', metadata={
        'last_work_cycle': '$TIMESTAMP',
        'work_cycle_result': '$WORK_STATUS'
    })
    sm.disconnect()
" 2>/dev/null
```

## Features
- Checks developer status from MongoDB database
- Updates heartbeat timestamp on each check
- Queries for available tasks from database
- Assigns tasks using database operations
- Logs all activities to database
- Provides clear guidance based on current state

## Work States
- **working/active**: Currently working on a task
- **ready/listening/idle**: Available for new tasks
- **uninitialized**: Developer agent not set up
- **error**: Database connection or other errors

## Database Integration
This command now:
- Reads agent state from `agent_states` collection
- Queries tasks from `tasks` collection
- Updates task assignments in real-time
- Logs activities to `activity_logs` collection
- Maintains heartbeat for availability monitoring