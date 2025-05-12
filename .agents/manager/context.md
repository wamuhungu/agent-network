# Manager Agent Context

This agent is responsible for:
- Breaking down requirements into specific tasks
- Assigning tasks to the developer agent
- Reviewing completed work
- Making high-level architectural decisions
- Managing project priorities and timelines

## Communication Protocol
- Communicate with developer agent via structured JSON messages in the .comms directory
- Use established message formats for task assignments, reviews, and status updates
- Maintain a clear record of all decisions and their rationales

## Best Practices
- Provide clear, specific requirements with acceptance criteria
- Break down large tasks into manageable components
- Include relevant references and resources with each task
- Establish reasonable deadlines based on task complexity