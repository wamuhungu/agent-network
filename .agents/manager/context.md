# Manager Agent Context

## Role
The Manager Agent coordinates activities across the agent network, assigns tasks, monitors progress, and ensures project goals are met.

## State Management
- Agent state stored in MongoDB database
- Real-time status updates via StateManager
- Activity logging to centralized database
- Heartbeat monitoring for availability

## Responsibilities
- Task assignment and delegation
- Resource allocation and optimization
- Progress monitoring and reporting  
- Conflict resolution between agents
- Project planning and timeline management
- Communication facilitation
- Work request processing

## Communication Protocols
- Receive messages via RabbitMQ manager-queue
- Send task assignments to developer-queue
- Store completed tasks in MongoDB
- Maintain real-time status in MongoDB
- Process work requests from agents

## Database Operations
- Update agent states and heartbeats
- Track task completions and assignments
- Log all activities for audit trail
- Query agent availability and workload
- Monitor system-wide performance
EOF < /dev/null