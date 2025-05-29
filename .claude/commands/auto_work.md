# Auto Work Command

Continuously check for new tasks with user control and countdown timer.

## Purpose
Provides automatic task monitoring with 30-second intervals, user prompts, and countdown display. Allows users to continue checking or stop the loop at any time.

## Usage
```bash
# Start continuous work checking
project:auto_work
```

## Implementation

```bash
#!/bin/bash

echo "🔄 AUTO WORK MODE ACTIVATED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checking for new tasks every 30 seconds..."
echo "Press Enter to continue or type 'stop' to halt"
echo ""

CONTINUE_CHECKING=true
CYCLE_COUNT=0

while [ "$CONTINUE_CHECKING" = true ]; do
    CYCLE_COUNT=$((CYCLE_COUNT + 1))
    
    echo "🔍 WORK CHECK CYCLE #$CYCLE_COUNT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Run developer work check
    bash -c "$(cat .claude/commands/developer_work.md | sed -n '/```bash/,/```/p' | sed '1d;$d')"
    
    # Check if a task was picked up by looking for "New task started" in status
    TASK_PICKED_UP=$(python3 -c "
import json
try:
    with open('.agents/developer/status.json', 'r') as f:
        status = json.load(f)
    current_tasks = status.get('current_tasks', [])
    if current_tasks:
        print('true')
    else:
        print('false')
except:
    print('false')
" 2>/dev/null)
    
    if [ "$TASK_PICKED_UP" = "true" ]; then
        echo ""
        echo "✅ TASK PICKED UP - STOPPING AUTO CHECK"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "A task has been assigned. Work on the task then run /auto_work again."
        break
    fi
    
    echo ""
    echo "⏰ NEXT CHECK IN 30 SECONDS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Countdown with user input check
    for i in $(seq 30 -1 1); do
        printf "\rChecking for new work... (Press Enter to continue or type 'stop' to halt) Next check in %2d seconds" $i
        
        # Check for user input with timeout
        if read -t 1 -r USER_INPUT; then
            if [ "$USER_INPUT" = "stop" ]; then
                echo ""
                echo ""
                echo "🛑 AUTO WORK STOPPED BY USER"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo "Auto checking halted. Run /auto_work to restart or /developer_work for single check."
                CONTINUE_CHECKING=false
                break
            elif [ -z "$USER_INPUT" ]; then
                echo ""
                echo ""
                echo "⏩ USER REQUESTED IMMEDIATE CHECK"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                break
            fi
        fi
    done
    
    if [ "$CONTINUE_CHECKING" = false ]; then
        break
    fi
    
    echo ""
    echo ""
done

echo ""
echo "🏁 AUTO WORK SESSION ENDED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total cycles completed: $CYCLE_COUNT"
echo ""
echo "💡 NEXT STEPS:"
echo "  • Run /developer_work for single task check"
echo "  • Run /auto_work to restart continuous checking"
echo "  • Run /complete_task \"TASK_ID\" when current task is finished"
```

## Features
1. **Continuous Monitoring**: Checks for tasks every 30 seconds automatically
2. **User Control**: Allows immediate checking (Enter) or stopping (type 'stop')
3. **Countdown Timer**: Shows remaining seconds until next check
4. **Auto Stop**: Stops when a task is picked up to prevent conflicts
5. **Cycle Tracking**: Shows cycle count for monitoring frequency
6. **Real-time Input**: Responds to user input during countdown

## User Interactions
- **Press Enter**: Immediately check for new tasks (skip countdown)
- **Type 'stop'**: Halt the auto checking loop
- **Task Assignment**: Automatically stops when work is found

## Auto Stop Conditions
- User types 'stop' during countdown
- A task is picked up and developer status changes to 'working'
- User interrupts with Ctrl+C

## Usage Scenarios
- **Background Monitoring**: Run when waiting for manager to assign tasks
- **Active Development**: Monitor while working on other tasks
- **Session Management**: Continuous operation during development sessions

## Output Information
- Work cycle number and timestamp
- Full developer work output for each check
- Countdown timer with user prompt
- Clear stop/continue messages
- Session summary at completion

## Integration
- Runs the full `/developer_work` command internally
- Respects all existing work states and logic
- Logs activities through standard developer work logging
- Updates status files through normal work cycle process

## Example Session
```
🔄 AUTO WORK MODE ACTIVATED
Checking for new tasks every 30 seconds...
Press Enter to continue or type 'stop' to halt

🔍 WORK CHECK CYCLE #1
[Full developer work output]

⏰ NEXT CHECK IN 30 SECONDS
Checking for new work... (Press Enter to continue or type 'stop' to halt) Next check in 15 seconds

[User presses Enter]

⏩ USER REQUESTED IMMEDIATE CHECK
🔍 WORK CHECK CYCLE #2
[Full developer work output]

✅ TASK PICKED UP - STOPPING AUTO CHECK
A task has been assigned. Work on the task then run /auto_work again.
```