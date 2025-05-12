Send a message to another agent in the system.

Usage: /send_message [agent_name] [message_type] [content]

This will create a properly formatted message in the .comms directory for the specified agent to process.

Follow these steps:
1. Generate a unique message ID
2. Create a JSON message with the required fields:
   - message_id
   - from_agent (your agent name)
   - to_agent (recipient agent name)
   - message_type
   - content (structured based on message type)
   - priority (default: medium)
   - timestamp
3. Save the message to .comms/[message_id].json
4. Log the activity to the agent monitoring system