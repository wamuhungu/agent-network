# Work Once Command

Run a single developer work check without prompting for continuation.

## Purpose
Performs exactly one work cycle to check task status and pick up work if available, then exits cleanly without any continuous checking or user prompts.

## Usage
```bash
# Run single work check
project:work_once
```

## Implementation

```bash
#!/bin/bash

echo "🔍 SINGLE WORK CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Performing one-time task check..."
echo ""

# Run the developer work cycle once
bash -c "$(cat .claude/commands/developer_work.md | sed -n '/```bash/,/```/p' | sed '1d;$d')"

echo ""
echo "✅ SINGLE CHECK COMPLETED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check final status from MongoDB
FINAL_STATUS=$(python3 -c "
import sys
sys.path.append('/Users/abdelr/Projects/claudecode/agent-network')
from src.services.database import DatabaseService
import asyncio

async def check_developer_status():
    db = DatabaseService()
    
    # Get developer state from MongoDB
    dev_state = await db.agent_states.find_one({'agent_name': 'developer'})
    if not dev_state:
        print('uninitialized')
        return
        
    status = dev_state.get('status', 'unknown')
    
    # Check for active tasks
    active_tasks = await db.tasks.count_documents({
        'assigned_to': 'developer',
        'status': 'in_progress'
    })
    
    if active_tasks > 0 and status == 'working':
        print('working')
    elif status in ['ready', 'idle', 'active']:
        print('ready')
    else:
        print(status)

asyncio.run(check_developer_status())
" 2>/dev/null)

case "$FINAL_STATUS" in
    "working")
        echo "🚀 TASK ASSIGNED - Ready to implement"
        echo ""
        echo "💡 NEXT STEPS:"
        echo "  • Start implementing the assigned task"
        echo "  • Use /work_once to check again after completion"
        echo "  • Use /auto_work for continuous monitoring"
        ;;
    "ready")
        echo "⏳ NO TASKS AVAILABLE - Standing by"
        echo ""
        echo "💡 NEXT STEPS:"
        echo "  • Use /work_once to check again later"
        echo "  • Use /auto_work for continuous monitoring"
        echo "  • Wait for manager to assign new tasks"
        ;;
    "uninitialized")
        echo "⚠️  DEVELOPER NOT INITIALIZED"
        echo ""
        echo "💡 NEXT STEPS:"
        echo "  • Run /become_developer to initialize"
        echo "  • Then use /work_once to check for tasks"
        ;;
    *)
        echo "❓ UNKNOWN STATUS: $FINAL_STATUS"
        echo ""
        echo "💡 NEXT STEPS:"
        echo "  • Check MongoDB agent_states collection"
        echo "  • Consider running /become_developer"
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## Features
1. **Single Execution**: Runs once and exits cleanly
2. **No Prompts**: No user interaction or continuation prompts
3. **Status Summary**: Provides clear status and next steps
4. **Quick Check**: Fast way to check current work state
5. **Clean Output**: Concise summary after work cycle

## Use Cases
- **Quick Status Check**: See current work state without continuous monitoring
- **Script Integration**: Can be called from other scripts or automation
- **Manual Control**: Preferred when you want explicit control over checking frequency
- **Testing**: Verify work cycle functionality without loops

## Comparison with Other Commands

| Command | Purpose | Execution | User Interaction |
|---------|---------|-----------|------------------|
| `/developer_work` | Full work cycle | Once | Provides guidance for next check |
| `/work_once` | Quick check | Once | Clean exit with status summary |
| `/auto_work` | Continuous monitoring | Loop | Interactive prompts and countdown |

## Output Format
- Standard developer work cycle output
- Clear completion message
- Status-based next step guidance
- Clean termination

## Integration
- Uses the same core logic as `/developer_work`
- Checks MongoDB for developer status and active tasks
- Respects all work states and task assignment logic
- Logs activities through standard developer work logging

## Example Output
```
🔍 SINGLE WORK CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Performing one-time task check...

👨‍💻 DEVELOPER WORK CYCLE
[Standard developer work output]

✅ SINGLE CHECK COMPLETED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ NO TASKS AVAILABLE - Standing by

💡 NEXT STEPS:
  • Use /work_once to check again later
  • Use /auto_work for continuous monitoring
  • Wait for manager to assign new tasks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Best Practices
- Use when you want manual control over work checking frequency
- Ideal for integration with external scheduling systems
- Good for testing and debugging work cycle logic
- Preferred when working intermittently rather than continuously