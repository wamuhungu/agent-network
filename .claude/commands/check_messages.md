Check for new messages directed to this agent.

Usage: /check_messages

This will scan the .comms directory for unprocessed messages intended for this agent.

Follow these steps:
1. Look through all JSON files in the .comms directory
2. Filter for messages where to_agent matches your agent name
3. Sort by priority and then timestamp
4. List all unprocessed messages with brief summaries
5. For each message, offer actions to:
   - View full message details
   - Mark as in progress
   - Respond to message
   - Archive message