Monitor agent activity and resource usage across the agent network.

Usage: /monitor [action]

Available actions:
- status: Show current status of all agents
- report: Generate a comprehensive activity report
- log [message]: Log a custom activity message
- track [tokens] [time]: Track resource usage

This command uses the AgentMonitor class in tools/monitor.py to track and report on agent activities.