# Agent Network System - Comprehensive User Guide

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture & Components](#architecture--components)
3. [Quick Start Guide](#quick-start-guide)
4. [Agent System](#agent-system)
5. [Applications](#applications)
6. [Communication System](#communication-system)
7. [Monitoring & Management](#monitoring--management)
8. [Development Workflow](#development-workflow)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)
11. [API Reference](#api-reference)
12. [Configuration](#configuration)

---

## System Overview

The Agent Network System is a sophisticated multi-agent collaborative framework built with Claude Code. It enables specialized AI agents to work together on complex projects through structured communication, task delegation, and coordinated development workflows.

### Key Features

- **Multi-Agent Collaboration**: Manager and Developer agents with specialized roles
- **Structured Communication**: JSON-based message passing with standardized schemas
- **Real-time Monitoring**: Web-based dashboard for system oversight
- **Application Suite**: Built-in tools including logbook, dashboard, and web server
- **Message Broker**: RabbitMQ-based messaging for reliable communication
- **State Management**: Persistent state tracking and recovery capabilities
- **Modular Architecture**: Extensible design for adding new agents and features

### Use Cases

- **Software Development**: Coordinated coding projects with automated task distribution
- **Project Management**: Multi-phase projects with oversight and quality control
- **Rapid Prototyping**: Quick development cycles with integrated testing
- **System Administration**: Automated monitoring and maintenance tasks
- **Documentation**: Collaborative documentation and knowledge management

---

## Architecture & Components

### Core Components

```
agent-network/
├── .agents/                    # Agent configurations and state
│   ├── manager/               # Manager agent files
│   └── developer/             # Developer agent files
├── .claude/                   # Claude Code configurations
│   └── commands/              # Custom Claude commands
├── .comms/                    # Inter-agent communication
├── src/                       # Source code applications
│   ├── dashboard/             # Monitoring dashboard
│   ├── logbook/              # Personal note-taking app
│   ├── webserver.py          # HTTP server implementation
│   └── webserver_config.py   # Server configuration
├── tools/                     # System utilities
├── docs/                      # Documentation
├── tests/                     # Test suites
└── logs/                      # System logs
```

### Agent Types

#### Manager Agent
- **Role**: Project coordinator and task orchestrator
- **Responsibilities**:
  - Requirements analysis and breakdown
  - Task assignment and prioritization
  - Progress monitoring and quality control
  - Resource allocation and conflict resolution
  - Strategic planning and decision making

#### Developer Agent
- **Role**: Code implementation and technical execution
- **Responsibilities**:
  - Feature implementation and bug fixing
  - Test writing and quality assurance
  - Technical documentation creation
  - Code review and optimization
  - System integration and deployment

### Communication Architecture

The system uses multiple communication channels:

1. **File-based Communication** (`.comms/` directory)
   - Persistent message storage
   - Audit trail maintenance
   - Offline message queuing

2. **RabbitMQ Message Broker** (`tools/message_broker.py`)
   - Real-time message delivery
   - Dedicated agent queues
   - Reliable message routing

3. **State Management** (`tools/state_manager.py`)
   - Agent state persistence
   - Transaction management
   - Recovery capabilities

---

## Quick Start Guide

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment support
- Optional: RabbitMQ for enhanced messaging

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd agent-network
   ```

2. **Set up virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the system**:
   ```bash
   python tools/database_init.py
   ```

### First Run

1. **Start the dashboard**:
   ```bash
   python tools/run_dashboard.py
   ```

2. **Access the dashboard**:
   Open `http://localhost:5000` in your browser

3. **Initialize agents** (using Claude Code):
   ```bash
   # In Claude Code terminal
   project:become_manager    # Initialize as manager
   # or
   project:become_developer  # Initialize as developer
   ```

### Basic Usage Example

1. **Create a simple task** (as Manager):
   ```json
   {
     "message_type": "task_assignment",
     "from_agent": "manager",
     "to_agent": "developer",
     "content": {
       "task_id": "simple-demo",
       "description": "Create a simple Hello World script",
       "priority": "medium",
       "requirements": ["Python script", "Unit test", "Documentation"]
     }
   }
   ```

2. **Monitor progress** via dashboard at `http://localhost:5000`

3. **Review completion** when developer responds with implementation

---

## Agent System

### Agent Lifecycle

#### Initialization
1. **Agent Setup**: Configure agent identity and capabilities
2. **State Registration**: Register with state management system
3. **Communication Setup**: Connect to message queues
4. **Health Check**: Verify system readiness

#### Operation Cycle
1. **Message Processing**: Handle incoming communications
2. **Task Execution**: Perform assigned work
3. **Status Updates**: Report progress and status
4. **Error Handling**: Manage and recover from failures

#### Shutdown
1. **Graceful Termination**: Complete current tasks
2. **State Persistence**: Save current state
3. **Cleanup**: Release resources and connections

### Agent Commands

#### Manager Commands
- `project:become_manager` - Initialize as manager agent
- `project:assign_task` - Create and assign new tasks
- `project:review_work` - Review completed work
- `project:status_report` - Generate status reports

#### Developer Commands
- `project:become_developer` - Initialize as developer agent
- `project:developer_work` - Check for and process tasks
- `project:complete_task` - Mark tasks as completed
- `project:auto_work` - Enable continuous task monitoring

### Agent Configuration

Agents are configured through JSON files in `.agents/`:

```json
{
  "agent_id": "developer",
  "agent_type": "developer",
  "status": "active",
  "capabilities": [
    "code_implementation",
    "testing_and_debugging",
    "technical_documentation"
  ],
  "communication_channels": ["file-based", "rabbitmq"],
  "development_tools": ["python", "javascript", "html_css", "flask", "git"]
}
```

---

## Applications

### 1. Monitoring Dashboard

**Location**: `src/dashboard/`

#### Features
- Real-time agent status monitoring
- Resource usage visualization
- Task tracking and metrics
- Activity log display
- Auto-refresh capabilities

#### Usage
```bash
python tools/run_dashboard.py
# Access at http://localhost:5000
```

#### API Endpoints
- `GET /api/agents/status` - Agent status information
- `GET /api/agents/report` - Comprehensive agent reports
- `GET /api/tasks/active` - Currently active tasks
- `GET /api/tasks/completed` - Completed task history
- `GET /api/logs/recent` - Recent system logs

### 2. Personal Logbook

**Location**: `src/logbook/`

#### Features
- Timestamped text note creation
- Voice recording capabilities
- Chronological entry display
- Search and filtering
- Export/import functionality
- REST API access

#### Usage
```bash
cd src/logbook
pip install -r requirements.txt
python app.py
# Access at http://localhost:5001
```

#### Key Features
- **Text Entries**: Rich text notes with timestamps
- **Voice Recordings**: Browser-based audio recording
- **Data Management**: SQLite database with full CRUD operations
- **Web Interface**: Responsive Bootstrap-based UI
- **API Integration**: RESTful endpoints for automation

### 3. Simple Web Server

**Location**: `src/webserver.py`

#### Features
- HTTP request handling (GET/POST)
- Static file serving
- Flexible routing system
- Error handling and logging
- Configuration management
- Security features

#### Usage
```bash
python src/webserver.py
# Access at http://localhost:8000
```

#### Configuration
Edit `src/webserver_config.py` or use environment variables:
```bash
export WEBSERVER_HOST=0.0.0.0
export WEBSERVER_PORT=8080
export WEBSERVER_LOG_LEVEL=INFO
```

---

## Communication System

### Message Schema

All inter-agent messages follow a standardized JSON schema:

```json
{
  "message_id": "unique-identifier",
  "from_agent": "sender-agent-id",
  "to_agent": "recipient-agent-id",
  "message_type": "task_assignment|status_update|question|review|approval|rejection",
  "priority": "low|medium|high|urgent",
  "timestamp": "2024-01-01T12:00:00Z",
  "content": {
    // Message-specific content
  }
}
```

### Message Types

#### Task Assignment
```json
{
  "message_type": "task_assignment",
  "content": {
    "task_id": "unique-task-id",
    "description": "Task description",
    "requirements": ["requirement1", "requirement2"],
    "priority": "medium",
    "deadline": "2024-01-01T18:00:00Z",
    "context": "Additional context information"
  }
}
```

#### Status Update
```json
{
  "message_type": "status_update",
  "content": {
    "task_id": "task-id",
    "status": "in_progress|completed|blocked",
    "progress_percentage": 75,
    "description": "Current status description",
    "blockers": ["blocker1", "blocker2"],
    "estimated_completion": "2024-01-01T16:00:00Z"
  }
}
```

#### Task Completion
```json
{
  "message_type": "task_completion",
  "content": {
    "task_id": "task-id",
    "status": "completed",
    "deliverables": {
      "files_created": ["file1.py", "file2.py"],
      "tests_written": ["test1.py"],
      "documentation": ["README.md"]
    },
    "summary": "Task completion summary",
    "next_steps": ["Step 1", "Step 2"]
  }
}
```

### Communication Channels

#### File-based Communication
- **Location**: `.comms/` directory
- **Format**: JSON files with message content
- **Naming**: `{message_type}_{timestamp}_{id}.json`
- **Processing**: Agents monitor directory for new files

#### RabbitMQ Broker
- **Setup**: `tools/message_broker.py`
- **Queues**: Dedicated queues per agent type
- **Features**: Real-time delivery, acknowledgments, routing
- **Configuration**: Host, port, credentials in broker config

---

## Monitoring & Management

### System Health Monitoring

#### Health Monitor (`tools/health_monitor.py`)
```bash
python tools/health_monitor.py
```

**Features**:
- Agent connectivity checks
- Resource usage monitoring
- Database integrity verification
- Log analysis and alerting
- Performance metrics collection

#### State Management (`tools/state_manager.py`)
```bash
python tools/state_manager.py --action backup
python tools/state_manager.py --action restore --backup-id backup_20240101_120000
```

**Features**:
- Automatic state persistence
- Point-in-time recovery
- Transaction management
- State synchronization
- Consistency checking

### Logging System

#### Log Locations
- **System Logs**: `logs/`
- **Agent Logs**: `.agents/{agent_id}/logs/`
- **Application Logs**: `src/{app}/logs/`

#### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information messages
- **WARNING**: Warning conditions
- **ERROR**: Error conditions
- **CRITICAL**: Critical error conditions

#### Log Analysis
```bash
# View recent system logs
tail -f logs/system.log

# Search for errors
grep ERROR logs/*.log

# Agent-specific logs
tail -f .agents/developer/logs/activity.log
```

### Performance Monitoring

#### Metrics Tracked
- **Task Completion Times**: Average and distribution
- **Token Usage**: Per agent and per task
- **Memory Usage**: System and application memory
- **Message Latency**: Communication delays
- **Error Rates**: Failure frequency and types

#### Monitoring Dashboard
Access comprehensive metrics at: `http://localhost:5000/metrics`

---

## Development Workflow

### Standard Development Process

#### 1. Project Initialization
```bash
# Initialize new project structure
python tools/database_init.py

# Start monitoring dashboard
python tools/run_dashboard.py

# Initialize manager agent (in Claude Code)
project:become_manager
```

#### 2. Requirements Phase
- Manager analyzes requirements
- Creates task breakdown structure
- Defines acceptance criteria
- Estimates effort and timeline

#### 3. Implementation Phase
```bash
# Initialize developer agent (in Claude Code)
project:become_developer

# Start auto-work mode for continuous task processing
project:auto_work
```

#### 4. Quality Assurance
- Automated testing execution
- Code review processes
- Documentation validation
- Performance benchmarking

#### 5. Deployment
- Staging deployment
- Integration testing
- Production deployment
- Post-deployment monitoring

### Collaborative Workflows

#### Feature Development
1. **Manager**: Creates feature specification
2. **Developer**: Implements core functionality
3. **Manager**: Reviews implementation
4. **Developer**: Addresses feedback
5. **Manager**: Approves for deployment

#### Bug Fixing
1. **Issue Identification**: Through monitoring or reports
2. **Triage**: Manager assesses priority and assigns
3. **Investigation**: Developer diagnoses root cause
4. **Fix Implementation**: Developer creates solution
5. **Verification**: Manager validates fix

#### Documentation
1. **Technical Documentation**: Developer creates
2. **User Documentation**: Manager reviews and enhances
3. **API Documentation**: Automatically generated
4. **Maintenance**: Ongoing updates by both agents

### Best Practices

#### For Manager Agents
- Provide clear, actionable task descriptions
- Include acceptance criteria and context
- Set realistic deadlines and priorities
- Monitor progress regularly
- Give constructive feedback

#### For Developer Agents
- Break down complex tasks into smaller components
- Write comprehensive tests
- Document code and decisions
- Communicate blockers early
- Follow coding standards

---

## Troubleshooting

### Common Issues

#### Agent Communication Problems

**Symptom**: Agents not receiving messages
**Solutions**:
1. Check message broker status:
   ```bash
   python tools/message_broker.py --status
   ```
2. Verify queue configurations
3. Restart message broker service
4. Check network connectivity

#### Application Startup Failures

**Symptom**: Applications fail to start
**Solutions**:
1. Check Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Verify database connectivity
3. Check port availability
4. Review application logs

#### Performance Issues

**Symptom**: Slow response times
**Solutions**:
1. Monitor system resources:
   ```bash
   python tools/health_monitor.py --detailed
   ```
2. Check database performance
3. Analyze message queue backlog
4. Review log files for bottlenecks

### Diagnostic Tools

#### System Status Check
```bash
python tools/consistency_checker.py
```

#### State Recovery
```bash
python tools/recovery_manager.py --diagnose
python tools/recovery_manager.py --repair
```

#### Log Analysis
```bash
python tools/monitor.py --analyze-logs --period 24h
```

### Error Recovery

#### Agent Recovery
1. **Identify Failed Agent**: Check dashboard status
2. **Review Error Logs**: Examine agent-specific logs
3. **Restart Agent**: Reinitialize agent process
4. **Verify Recovery**: Monitor status and functionality

#### State Recovery
1. **Backup Current State**: Before any recovery attempts
2. **Identify Last Good State**: Review state history
3. **Restore from Backup**: Use state manager tools
4. **Verify Integrity**: Run consistency checks

---

## Advanced Usage

### Custom Agent Development

#### Creating New Agent Types

1. **Define Agent Role**:
   ```json
   {
     "agent_id": "custom_agent",
     "agent_type": "specialist",
     "capabilities": ["custom_capability_1", "custom_capability_2"],
     "specialization": "Custom domain expertise"
   }
   ```

2. **Implement Agent Logic**:
   ```python
   class CustomAgent:
       def __init__(self, config):
           self.config = config
           self.capabilities = config['capabilities']
       
       def process_message(self, message):
           # Custom message processing logic
           pass
       
       def execute_task(self, task):
           # Custom task execution logic
           pass
   ```

3. **Register Agent**:
   ```bash
   python tools/agent_registry.py --register custom_agent
   ```

### Workflow Automation

#### Automated Task Pipelines

```python
# Define workflow pipeline
pipeline = WorkflowPipeline([
    TaskStage("requirements_analysis", agent="manager"),
    TaskStage("implementation", agent="developer"),
    TaskStage("testing", agent="developer"),
    TaskStage("review", agent="manager"),
    TaskStage("deployment", agent="devops")
])

# Execute pipeline
pipeline.execute(initial_task)
```

#### Scheduled Operations

```bash
# Set up cron job for regular health checks
0 */6 * * * python tools/health_monitor.py --automated
0 2 * * * python tools/state_manager.py --backup
```

### Integration APIs

#### External System Integration

```python
# Webhook integration
@app.route('/webhook/external-system', methods=['POST'])
def handle_external_webhook():
    data = request.json
    
    # Convert to agent message
    message = {
        "message_type": "external_task",
        "from_agent": "external_system",
        "to_agent": "manager",
        "content": data
    }
    
    # Send to message broker
    broker.publish_message("manager-queue", message)
    return jsonify({"status": "accepted"})
```

#### REST API Integration

```python
# RESTful agent control API
@app.route('/api/agents/<agent_id>/tasks', methods=['POST'])
def assign_task(agent_id):
    task_data = request.json
    
    # Validate and format task
    task = TaskAssignment(
        agent_id=agent_id,
        description=task_data['description'],
        requirements=task_data['requirements']
    )
    
    # Send to agent
    result = agent_manager.assign_task(task)
    return jsonify(result)
```

---

## API Reference

### Dashboard API

#### Agent Management
```http
GET /api/agents/status
GET /api/agents/{agent_id}/status
POST /api/agents/{agent_id}/command
DELETE /api/agents/{agent_id}/shutdown
```

#### Task Management
```http
GET /api/tasks
POST /api/tasks
GET /api/tasks/{task_id}
PUT /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
```

#### System Operations
```http
GET /api/system/health
GET /api/system/metrics
POST /api/system/backup
POST /api/system/restore
```

### Logbook API

#### Entry Management
```http
GET /api/entries
POST /api/entries
GET /api/entries/{entry_id}
PUT /api/entries/{entry_id}
DELETE /api/entries/{entry_id}
```

#### Voice Operations
```http
POST /api/entries/{entry_id}/voice
GET /api/entries/{entry_id}/voice
DELETE /api/entries/{entry_id}/voice
```

### Web Server API

#### Content Management
```http
GET /
GET /status
GET /api
GET /user/{user_id}
```

#### Configuration
```http
GET /config
POST /config
PUT /config
```

---

## Configuration

### System Configuration

#### Environment Variables
```bash
# Agent Network Configuration
AGENT_NETWORK_ENV=production
AGENT_NETWORK_LOG_LEVEL=INFO
AGENT_NETWORK_DATA_DIR=/var/lib/agent-network

# Message Broker Configuration
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=agent_user
RABBITMQ_PASSWORD=secure_password

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/agent_network
REDIS_URL=redis://localhost:6379/0

# Application Configuration
DASHBOARD_PORT=5000
LOGBOOK_PORT=5001
WEBSERVER_PORT=8000
```

#### Configuration Files

**Main Configuration** (`config/system.json`):
```json
{
  "system": {
    "name": "agent-network",
    "version": "1.0.0",
    "environment": "production"
  },
  "agents": {
    "max_concurrent": 10,
    "heartbeat_interval": 30,
    "timeout": 300
  },
  "communication": {
    "default_channel": "rabbitmq",
    "fallback_channel": "file",
    "message_retention": "7d"
  },
  "monitoring": {
    "enabled": true,
    "metrics_interval": 60,
    "log_rotation": "daily"
  }
}
```

**Agent Configuration** (`.agents/{agent_id}/config.json`):
```json
{
  "agent_id": "developer",
  "agent_type": "developer",
  "capabilities": [
    "python_development",
    "web_development",
    "testing",
    "documentation"
  ],
  "resource_limits": {
    "max_memory": "2GB",
    "max_cpu": "80%",
    "max_tasks": 5
  },
  "communication": {
    "preferred_channels": ["rabbitmq", "file"],
    "response_timeout": 60
  }
}
```

### Security Configuration

#### Authentication & Authorization
```json
{
  "security": {
    "authentication": {
      "method": "token",
      "token_expiry": "24h"
    },
    "authorization": {
      "rbac_enabled": true,
      "default_role": "agent"
    },
    "encryption": {
      "messages": true,
      "storage": true,
      "algorithm": "AES-256"
    }
  }
}
```

#### Network Security
```json
{
  "network": {
    "allowed_hosts": ["localhost", "127.0.0.1"],
    "tls_enabled": true,
    "certificate_path": "/etc/ssl/certs/agent-network.crt",
    "private_key_path": "/etc/ssl/private/agent-network.key"
  }
}
```

### Performance Tuning

#### Resource Optimization
```json
{
  "performance": {
    "thread_pool_size": 10,
    "connection_pool_size": 20,
    "cache_size": "100MB",
    "garbage_collection": {
      "enabled": true,
      "interval": "1h"
    }
  }
}
```

#### Monitoring Thresholds
```json
{
  "monitoring": {
    "thresholds": {
      "cpu_warning": 70,
      "cpu_critical": 90,
      "memory_warning": 80,
      "memory_critical": 95,
      "disk_warning": 85,
      "disk_critical": 95
    }
  }
}
```

---

## Conclusion

The Agent Network System provides a comprehensive framework for multi-agent collaboration, offering robust communication, monitoring, and management capabilities. This guide covers the essential aspects of using and managing the system effectively.

For additional support:
- Check the `docs/` directory for specialized guides
- Review component-specific README files
- Monitor system logs for troubleshooting
- Use the dashboard for real-time system insights

The system is designed to be extensible and adaptable to various use cases, from software development to project management and beyond.

---

**Last Updated**: June 2025  
**Version**: 1.0.0  
**Authors**: Agent Network Development Team