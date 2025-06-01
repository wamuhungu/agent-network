"""
RabbitMQ Message Broker for Agent Network Communication

This module provides a robust RabbitMQ-based messaging system to replace
file-based communication between agents. It offers immediate delivery,
transient messaging, and dedicated queues for each agent type.

Features:
- Connection management with automatic reconnection
- Dedicated queues for manager and developer agents
- Message publishing with delivery confirmation
- Message consuming with callback functions
- Error handling and logging
- Queue statistics and monitoring
"""

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager

try:
    import pika
    import pika.exceptions
except ImportError:
    print("ERROR: pika library not installed. Install with: pip install pika")
    raise


@dataclass
class BrokerConfig:
    """Configuration for RabbitMQ broker connection."""
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    virtual_host: str = '/'
    connection_timeout: int = 30
    heartbeat: int = 600
    retry_delay: int = 5
    max_retries: int = 3


class MessageBroker:
    """
    RabbitMQ message broker for agent communication.
    
    Provides reliable messaging between agents with automatic reconnection,
    error handling, and message persistence until consumed.
    """
    
    # Queue names for different agent types
    MANAGER_QUEUE = 'manager-queue'
    DEVELOPER_QUEUE = 'developer-queue'
    MANAGER_REQUIREMENTS_QUEUE = 'manager-requirements-queue'
    WORK_REQUEST_QUEUE = 'work-request-queue'
    
    # Exchange name for direct messaging
    EXCHANGE_NAME = 'agent-exchange'
    
    def __init__(self, config: Optional[BrokerConfig] = None):
        """
        Initialize the message broker.
        
        Args:
            config: Broker configuration. Uses defaults if None.
        """
        self.config = config or BrokerConfig()
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self.is_connected = False
        self.consumers: Dict[str, threading.Thread] = {}
        self.callback_handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/message_broker.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def connect(self) -> bool:
        """
        Establish connection to RabbitMQ server.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # Connection parameters
            credentials = pika.PlainCredentials(
                self.config.username, 
                self.config.password
            )
            
            parameters = pika.ConnectionParameters(
                host=self.config.host,
                port=self.config.port,
                virtual_host=self.config.virtual_host,
                credentials=credentials,
                connection_attempts=self.config.max_retries,
                retry_delay=self.config.retry_delay,
                socket_timeout=self.config.connection_timeout,
                heartbeat=self.config.heartbeat
            )
            
            # Establish connection
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.is_connected = True
            
            # Setup exchange and queues
            self._setup_infrastructure()
            
            self.logger.info(f"Connected to RabbitMQ at {self.config.host}:{self.config.port}")
            return True
            
        except (pika.exceptions.AMQPConnectionError, 
                pika.exceptions.AMQPChannelError) as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Safely disconnect from RabbitMQ server."""
        try:
            # Stop all consumers
            for queue_name, thread in self.consumers.items():
                self.logger.info(f"Stopping consumer for {queue_name}")
                if thread.is_alive():
                    thread.join(timeout=5)
            
            self.consumers.clear()
            self.callback_handlers.clear()
            
            # Close connection
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            
            self.is_connected = False
            self.logger.info("Disconnected from RabbitMQ")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
    
    def _setup_infrastructure(self):
        """Setup RabbitMQ exchange and queues."""
        if not self.channel:
            raise RuntimeError("No channel available")
        
        # Declare exchange
        self.channel.exchange_declare(
            exchange=self.EXCHANGE_NAME,
            exchange_type='direct',
            durable=False
        )
        
        # Declare queues with specific properties
        queues = [self.MANAGER_QUEUE, self.DEVELOPER_QUEUE, 
                 self.MANAGER_REQUIREMENTS_QUEUE, self.WORK_REQUEST_QUEUE]
        
        for queue_name in queues:
            self.channel.queue_declare(
                queue=queue_name,
                durable=False,      # Transient - queue disappears on restart
                exclusive=False,    # Allow multiple connections
                auto_delete=False   # Don't auto-delete when no consumers
            )
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.EXCHANGE_NAME,
                queue=queue_name,
                routing_key=queue_name
            )
        
        self.logger.info("RabbitMQ infrastructure setup complete")
    
    def publish_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to the specified queue.
        
        Args:
            queue_name: Target queue name
            message: Message dictionary to send
            
        Returns:
            True if message published successfully, False otherwise.
        """
        if not self.is_connected:
            self.logger.error("Not connected to RabbitMQ")
            return False
        
        try:
            # Add metadata to message
            enhanced_message = {
                **message,
                'broker_metadata': {
                    'published_at': datetime.now().isoformat(),
                    'message_id': str(uuid.uuid4()),
                    'queue': queue_name
                }
            }
            
            # Serialize message
            message_body = json.dumps(enhanced_message, indent=2)
            
            # Publish with delivery confirmation
            if self.channel:
                self.channel.confirm_delivery()
                
                success = self.channel.basic_publish(
                    exchange=self.EXCHANGE_NAME,
                    routing_key=queue_name,
                    body=message_body,
                    properties=pika.BasicProperties(
                        delivery_mode=1,  # Transient message
                        content_type='application/json',
                        timestamp=int(time.time())
                    )
                )
                
                if success:
                    self.logger.info(f"Published message to {queue_name}: {enhanced_message.get('message_type', 'unknown')}")
                    return True
                else:
                    self.logger.error(f"Failed to confirm delivery to {queue_name}")
                    return False
            
        except pika.exceptions.UnroutableError:
            self.logger.error(f"Message unroutable to queue {queue_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error publishing message to {queue_name}: {e}")
            return False
        
        return False
    
    def send_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        Alias for publish_message for backward compatibility.
        
        Args:
            queue_name: Target queue name
            message: Message dictionary to send
            
        Returns:
            True if message sent successfully, False otherwise.
        """
        return self.publish_message(queue_name, message)
    
    def start_consuming(self, queue_name: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Start consuming messages from a queue with a callback function.
        
        Args:
            queue_name: Queue to consume from
            callback: Function to call when message received
        """
        if not self.is_connected:
            self.logger.error("Not connected to RabbitMQ")
            return
        
        if queue_name in self.consumers:
            self.logger.warning(f"Consumer already running for {queue_name}")
            return
        
        # Store callback
        self.callback_handlers[queue_name] = callback
        
        # Create consumer thread
        consumer_thread = threading.Thread(
            target=self._consume_messages,
            args=(queue_name,),
            daemon=True,
            name=f"Consumer-{queue_name}"
        )
        
        self.consumers[queue_name] = consumer_thread
        consumer_thread.start()
        
        self.logger.info(f"Started consuming from {queue_name}")
    
    def _consume_messages(self, queue_name: str):
        """
        Internal method to consume messages from a queue.
        
        Args:
            queue_name: Queue to consume from
        """
        try:
            # Create new connection for this consumer
            consumer_connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.config.host,
                    port=self.config.port,
                    virtual_host=self.config.virtual_host,
                    credentials=pika.PlainCredentials(
                        self.config.username, 
                        self.config.password
                    )
                )
            )
            consumer_channel = consumer_connection.channel()
            
            def message_callback(ch, method, properties, body):
                """Handle incoming message."""
                try:
                    # Parse message
                    message = json.loads(body.decode('utf-8'))
                    
                    self.logger.info(f"Received message from {queue_name}: {message.get('message_type', 'unknown')}")
                    
                    # Call user callback
                    if queue_name in self.callback_handlers:
                        self.callback_handlers[queue_name](message)
                    
                    # Acknowledge message (removes from queue)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON in message from {queue_name}: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    self.logger.error(f"Error processing message from {queue_name}: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            # Setup consumer
            consumer_channel.basic_consume(
                queue=queue_name,
                on_message_callback=message_callback
            )
            
            self.logger.info(f"Consumer for {queue_name} ready")
            
            # Start consuming
            consumer_channel.start_consuming()
            
        except Exception as e:
            self.logger.error(f"Consumer error for {queue_name}: {e}")
        finally:
            try:
                if 'consumer_connection' in locals():
                    consumer_connection.close()
            except:
                pass
    
    def stop_consuming(self, queue_name: str):
        """
        Stop consuming from a specific queue.
        
        Args:
            queue_name: Queue to stop consuming from
        """
        if queue_name in self.consumers:
            thread = self.consumers[queue_name]
            if thread.is_alive():
                thread.join(timeout=5)
            del self.consumers[queue_name]
            
        if queue_name in self.callback_handlers:
            del self.callback_handlers[queue_name]
        
        self.logger.info(f"Stopped consuming from {queue_name}")
    
    def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a queue.
        
        Args:
            queue_name: Queue to inspect
            
        Returns:
            Dictionary with queue information or None if error.
        """
        if not self.is_connected or not self.channel:
            return None
        
        try:
            method = self.channel.queue_declare(queue=queue_name, passive=True)
            return {
                'queue': queue_name,
                'messages': method.method.message_count,
                'consumers': method.method.consumer_count
            }
        except Exception as e:
            self.logger.error(f"Error getting queue info for {queue_name}: {e}")
            return None
    
    def purge_queue(self, queue_name: str) -> bool:
        """
        Remove all messages from a queue.
        
        Args:
            queue_name: Queue to purge
            
        Returns:
            True if successful, False otherwise.
        """
        if not self.is_connected or not self.channel:
            return False
        
        try:
            self.channel.queue_purge(queue=queue_name)
            self.logger.info(f"Purged queue {queue_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error purging queue {queue_name}: {e}")
            return False
    
    def get_broker_status(self) -> Dict[str, Any]:
        """
        Get overall broker status and statistics.
        
        Returns:
            Dictionary with broker status information.
        """
        status = {
            'connected': self.is_connected,
            'connection_info': {
                'host': self.config.host,
                'port': self.config.port,
                'virtual_host': self.config.virtual_host
            },
            'active_consumers': list(self.consumers.keys()),
            'queues': {}
        }
        
        # Get queue information
        for queue_name in [self.MANAGER_QUEUE, self.DEVELOPER_QUEUE, 
                          self.MANAGER_REQUIREMENTS_QUEUE, self.WORK_REQUEST_QUEUE]:
            queue_info = self.get_queue_info(queue_name)
            if queue_info:
                status['queues'][queue_name] = queue_info
        
        return status


# Convenience functions for common operations

def create_broker(config: Optional[BrokerConfig] = None) -> MessageBroker:
    """
    Create and connect to message broker.
    
    Args:
        config: Optional broker configuration
        
    Returns:
        Connected MessageBroker instance
        
    Raises:
        RuntimeError: If connection fails
    """
    broker = MessageBroker(config)
    if not broker.connect():
        raise RuntimeError("Failed to connect to RabbitMQ broker")
    return broker


def send_task_to_developer(message: Dict[str, Any], 
                          broker: Optional[MessageBroker] = None) -> bool:
    """
    Send a task assignment message to the developer queue.
    
    Args:
        message: Task assignment message
        broker: Optional broker instance (creates new if None)
        
    Returns:
        True if message sent successfully
    """
    if broker is None:
        broker = create_broker()
        should_disconnect = True
    else:
        should_disconnect = False
    
    try:
        success = broker.publish_message(MessageBroker.DEVELOPER_QUEUE, message)
        return success
    finally:
        if should_disconnect:
            broker.disconnect()


def send_completion_to_manager(message: Dict[str, Any], 
                             broker: Optional[MessageBroker] = None) -> bool:
    """
    Send a task completion message to the manager queue.
    
    Args:
        message: Task completion message
        broker: Optional broker instance (creates new if None)
        
    Returns:
        True if message sent successfully
    """
    if broker is None:
        broker = create_broker()
        should_disconnect = True
    else:
        should_disconnect = False
    
    try:
        success = broker.publish_message(MessageBroker.MANAGER_QUEUE, message)
        return success
    finally:
        if should_disconnect:
            broker.disconnect()


@contextmanager
def broker_connection(config: Optional[BrokerConfig] = None):
    """
    Context manager for broker connections.
    
    Args:
        config: Optional broker configuration
        
    Yields:
        Connected MessageBroker instance
    """
    broker = create_broker(config)
    try:
        yield broker
    finally:
        broker.disconnect()


if __name__ == '__main__':
    # Basic test/demo
    import sys
    
    def test_broker():
        """Test broker functionality."""
        print("Testing RabbitMQ Message Broker...")
        
        try:
            # Create broker
            broker = create_broker()
            print("✓ Connected to RabbitMQ")
            
            # Get status
            status = broker.get_broker_status()
            print(f"✓ Broker status: {status}")
            
            # Test message
            test_message = {
                "message_type": "test",
                "from_agent": "test",
                "to_agent": "test", 
                "timestamp": datetime.now().isoformat(),
                "content": "Test message"
            }
            
            # Send to developer queue
            success = broker.publish_message(MessageBroker.DEVELOPER_QUEUE, test_message)
            if success:
                print("✓ Test message sent to developer queue")
            else:
                print("✗ Failed to send test message")
            
            # Check queue status
            queue_info = broker.get_queue_info(MessageBroker.DEVELOPER_QUEUE)
            print(f"✓ Developer queue info: {queue_info}")
            
            broker.disconnect()
            print("✓ Disconnected successfully")
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            sys.exit(1)
    
    test_broker()