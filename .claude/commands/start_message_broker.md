# Start Message Broker Command

Start a local RabbitMQ message broker using Docker for agent communication.

## Purpose
Sets up and starts a RabbitMQ message broker instance using Docker, configures queues for agent communication, and provides status monitoring capabilities.

## Usage
```bash
# Start RabbitMQ message broker
project:start_message_broker
```

## Implementation

```bash
#!/bin/bash

echo "🐰 STARTING RABBITMQ MESSAGE BROKER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    echo "💡 Please install Docker Desktop from: https://docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo "💡 Please start Docker Desktop and try again"
    exit 1
fi

echo "✅ Docker is available and running"

# Configuration variables
RABBITMQ_CONTAINER_NAME="agent-network-rabbitmq"
RABBITMQ_PORT=5672
RABBITMQ_MANAGEMENT_PORT=15672
RABBITMQ_USER="agent"
RABBITMQ_PASS="network"

# Check if RabbitMQ container already exists
if docker ps -a --format "table {{.Names}}" | grep -q "^${RABBITMQ_CONTAINER_NAME}$"; then
    echo "📦 RabbitMQ container already exists"
    
    # Check if it's running
    if docker ps --format "table {{.Names}}" | grep -q "^${RABBITMQ_CONTAINER_NAME}$"; then
        echo "✅ RabbitMQ is already running"
        RABBITMQ_RUNNING=true
    else
        echo "🔄 Starting existing RabbitMQ container..."
        docker start $RABBITMQ_CONTAINER_NAME
        if [ $? -eq 0 ]; then
            echo "✅ RabbitMQ container started successfully"
            RABBITMQ_RUNNING=true
        else
            echo "❌ Failed to start existing RabbitMQ container"
            echo "💡 Try removing it: docker rm $RABBITMQ_CONTAINER_NAME"
            exit 1
        fi
    fi
else
    echo "🚀 Creating new RabbitMQ container..."
    
    # Pull RabbitMQ image with management interface
    echo "📥 Pulling RabbitMQ image..."
    docker pull rabbitmq:3-management
    
    # Create and start RabbitMQ container
    docker run -d \
        --name $RABBITMQ_CONTAINER_NAME \
        --hostname rabbitmq-agent-network \
        -p $RABBITMQ_PORT:5672 \
        -p $RABBITMQ_MANAGEMENT_PORT:15672 \
        -e RABBITMQ_DEFAULT_USER=$RABBITMQ_USER \
        -e RABBITMQ_DEFAULT_PASS=$RABBITMQ_PASS \
        --restart unless-stopped \
        rabbitmq:3-management
    
    if [ $? -eq 0 ]; then
        echo "✅ RabbitMQ container created and started successfully"
        RABBITMQ_RUNNING=true
    else
        echo "❌ Failed to create RabbitMQ container"
        exit 1
    fi
fi

# Wait for RabbitMQ to be ready
if [ "$RABBITMQ_RUNNING" = true ]; then
    echo "⏳ Waiting for RabbitMQ to be ready..."
    
    # Wait up to 60 seconds for RabbitMQ to start
    for i in {1..60}; do
        if docker exec $RABBITMQ_CONTAINER_NAME rabbitmqctl status &> /dev/null; then
            echo "✅ RabbitMQ is ready!"
            break
        fi
        
        if [ $i -eq 60 ]; then
            echo "❌ RabbitMQ failed to start within 60 seconds"
            echo "🔍 Container logs:"
            docker logs $RABBITMQ_CONTAINER_NAME --tail 20
            exit 1
        fi
        
        printf "."
        sleep 1
    done
    echo ""
fi

# Initialize queues and verify connection
echo "🔧 Initializing agent queues..."

# Test connection and setup queues using Python
python3 -c "
import sys
import time
sys.path.append('tools')

try:
    from message_broker import MessageBroker, BrokerConfig
    
    # Configure connection for Docker setup
    config = BrokerConfig(
        host='localhost',
        port=$RABBITMQ_PORT,
        username='$RABBITMQ_USER',
        password='$RABBITMQ_PASS'
    )
    
    # Retry connection a few times
    broker = None
    for attempt in range(5):
        try:
            broker = MessageBroker(config)
            if broker.connect():
                print('✅ Connected to RabbitMQ successfully')
                break
        except Exception as e:
            if attempt < 4:
                print(f'⏳ Connection attempt {attempt + 1} failed, retrying...')
                time.sleep(2)
            else:
                raise e
    
    if not broker or not broker.is_connected:
        print('❌ Failed to connect to RabbitMQ after 5 attempts')
        sys.exit(1)
    
    # Get broker status
    status = broker.get_broker_status()
    print(f'📊 Broker status: Connected = {status[\"connected\"]}')
    
    # Display queue information
    for queue_name in [broker.MANAGER_QUEUE, broker.DEVELOPER_QUEUE]:
        queue_info = broker.get_queue_info(queue_name)
        if queue_info:
            print(f'📬 Queue {queue_name}: {queue_info[\"messages\"]} messages, {queue_info[\"consumers\"]} consumers')
        else:
            print(f'⚠️  Queue {queue_name}: Could not get info')
    
    broker.disconnect()
    print('✅ Queue initialization completed')
    
except ImportError as e:
    print('❌ Message broker module not available')
    print(f'Error: {e}')
    print('💡 Install pika: pip install pika')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error setting up queues: {e}')
    sys.exit(1)
"

# Check if queue setup was successful
if [ $? -eq 0 ]; then
    QUEUES_READY=true
else
    QUEUES_READY=false
    echo "❌ QUEUE SETUP FAILED"
    exit 1
fi

# Display connection information
echo ""
echo "🎉 RABBITMQ MESSAGE BROKER READY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 CONNECTION INFO:"
echo "  • Host: localhost"
echo "  • AMQP Port: $RABBITMQ_PORT"
echo "  • Management UI: http://localhost:$RABBITMQ_MANAGEMENT_PORT"
echo "  • Username: $RABBITMQ_USER"
echo "  • Password: $RABBITMQ_PASS"
echo ""
echo "📬 AGENT QUEUES:"
echo "  • manager-queue: Ready for task completion messages"
echo "  • developer-queue: Ready for task assignment messages"
echo ""
echo "🔧 MANAGEMENT COMMANDS:"
echo "  • View logs: docker logs $RABBITMQ_CONTAINER_NAME"
echo "  • Stop broker: docker stop $RABBITMQ_CONTAINER_NAME"
echo "  • Remove broker: docker rm $RABBITMQ_CONTAINER_NAME"
echo ""
echo "🚀 NEXT STEPS:"
echo "  • Initialize manager: project:become_manager"
echo "  • Initialize developer: project:become_developer"
echo "  • Create tasks: project:create_task \"description\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Log broker startup
mkdir -p .logs
echo "$(date -Iseconds) [BROKER] RabbitMQ message broker started successfully" >> .logs/message_broker.log
echo "$(date -Iseconds) [INFO] Container: $RABBITMQ_CONTAINER_NAME, Ports: $RABBITMQ_PORT, $RABBITMQ_MANAGEMENT_PORT" >> .logs/message_broker.log
echo "$(date -Iseconds) [INFO] Queues initialized: manager-queue, developer-queue" >> .logs/message_broker.log
```

## Features

### Container Management
- **Automatic Detection**: Checks if RabbitMQ container already exists
- **Restart Capability**: Starts existing stopped containers
- **Health Monitoring**: Waits for RabbitMQ to be fully ready
- **Error Handling**: Provides clear error messages and solutions

### Queue Configuration
- **Agent Queues**: Creates dedicated queues for manager and developer
- **Connection Testing**: Verifies broker connectivity
- **Status Monitoring**: Shows queue statistics and broker status

### Management Interface
- **Web UI**: Accessible at http://localhost:15672
- **User Credentials**: Custom agent/network credentials
- **Queue Monitoring**: Visual queue management and statistics
- **Message Inspection**: Debug and monitor message flow

## Prerequisites

### Docker Installation
```bash
# macOS
brew install --cask docker

# Or download Docker Desktop from https://docker.com/products/docker-desktop
```

### Python Dependencies
```bash
# Install RabbitMQ Python client
pip install pika
```

## Docker Configuration

### Container Settings
- **Name**: `agent-network-rabbitmq`
- **Image**: `rabbitmq:3-management`
- **Ports**: 5672 (AMQP), 15672 (Management)
- **Restart Policy**: `unless-stopped`
- **Hostname**: `rabbitmq-agent-network`

### Environment Variables
- **Username**: `agent`
- **Password**: `network`
- **Virtual Host**: `/` (default)

## Management Commands

### Container Operations
```bash
# View container status
docker ps | grep agent-network-rabbitmq

# View container logs
docker logs agent-network-rabbitmq

# Stop the broker
docker stop agent-network-rabbitmq

# Start the broker
docker start agent-network-rabbitmq

# Remove the broker (will lose data)
docker rm agent-network-rabbitmq
```

### Queue Management
```bash
# Test broker connection
python3 -c "
import sys; sys.path.append('tools')
from message_broker import MessageBroker
broker = MessageBroker()
if broker.connect():
    print('✅ Connected')
    print(broker.get_broker_status())
    broker.disconnect()
else:
    print('❌ Connection failed')
"
```

## Troubleshooting

### Common Issues

**Docker not found**
```bash
# Install Docker Desktop
brew install --cask docker
# Or visit https://docker.com/products/docker-desktop
```

**Port already in use**
```bash
# Check what's using the port
lsof -i :5672
lsof -i :15672

# Stop conflicting services or change ports in the script
```

**Connection refused**
```bash
# Check if container is running
docker ps | grep rabbitmq

# Check container logs
docker logs agent-network-rabbitmq

# Restart container
docker restart agent-network-rabbitmq
```

**Python pika not found**
```bash
# Install pika library
pip install pika

# Or with conda
conda install -c conda-forge pika
```

## Integration

### Agent Initialization
After starting the broker:

1. **Initialize Manager**:
   ```bash
   project:become_manager
   python3 .agents/manager/message_listener.py &
   ```

2. **Initialize Developer**:
   ```bash
   project:become_developer
   python3 .agents/developer/message_listener.py &
   ```

3. **Create Tasks**:
   ```bash
   project:create_task "Implement new feature"
   ```

### Message Flow
1. Manager sends task → developer-queue
2. Developer receives task immediately
3. Developer sends completion → manager-queue
4. Manager receives completion immediately

## Monitoring

### Management UI
- **URL**: http://localhost:15672
- **Login**: agent / network
- **Features**: Queue stats, message inspection, connection monitoring

### Queue Statistics
```bash
# Check queue status
python3 -c "
import sys; sys.path.append('tools')
from message_broker import MessageBroker
broker = MessageBroker()
broker.connect()
print('Manager queue:', broker.get_queue_info('manager-queue'))
print('Developer queue:', broker.get_queue_info('developer-queue'))
broker.disconnect()
"
```

### Log Files
- **Broker Log**: `.logs/message_broker.log`
- **Manager Log**: `.logs/manager.log`
- **Developer Log**: `.logs/developer.log`

## Example Usage

```bash
# Start the message broker
project:start_message_broker

# In terminal 1 - Start manager
project:become_manager
python3 .agents/manager/message_listener.py

# In terminal 2 - Start developer  
project:become_developer
python3 .agents/developer/message_listener.py

# In terminal 3 - Create tasks
project:create_task "Add user authentication"
project:create_task "Implement dashboard widgets"

# Complete tasks (from developer terminal)
project:complete_task "task_20241126_143022_A7F3Kx"
```