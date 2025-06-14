Check for new messages directed to this agent.

Usage: /check_messages

This will query MongoDB for unprocessed messages intended for this agent.

Follow these steps:
1. Query MongoDB for messages directed to this agent:
   ```python
   import sys
   sys.path.append('/Users/abdelr/Projects/claudecode/agent-network')
   from src.services.database import DatabaseService
   import asyncio
   from datetime import datetime
   
   async def check_messages():
       db = DatabaseService()
       
       # Get agent name from environment or default
       agent_name = "developer"  # or "manager"
       
       # Query for unprocessed messages
       messages = await db.messages.find({
           "to": agent_name,
           "status": {"$in": ["pending", "unread"]}
       }).sort([("priority", -1), ("created_at", 1)]).to_list(None)
       
       if not messages:
           print("No new messages")
           return
           
       print(f"Found {len(messages)} unprocessed messages:")
       for msg in messages:
           print(f"\n- ID: {msg['_id']}")
           print(f"  From: {msg.get('from', 'unknown')}")
           print(f"  Type: {msg.get('type', 'unknown')}")
           print(f"  Priority: {msg.get('priority', 'normal')}")
           print(f"  Created: {msg.get('created_at', 'unknown')}")
           print(f"  Summary: {msg.get('description', msg.get('content', 'No description'))[:100]}...")
   
   asyncio.run(check_messages())
   ```
2. Filter for messages where to_agent matches your agent name
3. Sort by priority and then timestamp
4. List all unprocessed messages with brief summaries
5. For each message, offer actions to:
   - View full message details
   - Mark as in progress
   - Respond to message
   - Archive message