"""
Configuration management for SimpleWebServer.

Provides configuration loading from files and environment variables,
with sensible defaults and validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ServerConfig:
    """
    Server configuration settings.
    
    Attributes:
        host: Server host address
        port: Server port number
        static_dir: Directory for static files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Log file path (None for console only)
        max_request_size: Maximum request size in bytes
        request_timeout: Request timeout in seconds
        enable_cors: Enable CORS headers
        cors_origins: Allowed CORS origins (list of strings)
        debug_mode: Enable debug mode
    """
    host: str = 'localhost'
    port: int = 8000
    static_dir: str = 'static'
    log_level: str = 'INFO'
    log_file: Optional[str] = 'logs/webserver.log'
    max_request_size: int = 1048576  # 1MB
    request_timeout: int = 30
    enable_cors: bool = False
    cors_origins: list = None
    debug_mode: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.cors_origins is None:
            self.cors_origins = ['*']
        
        # Validate port range
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port number: {self.port}")
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.log_level}")
        
        # Ensure static directory exists
        os.makedirs(self.static_dir, exist_ok=True)
        
        # Ensure log directory exists if log file is specified
        if self.log_file:
            log_dir = os.path.dirname(self.log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)


class ConfigManager:
    """
    Configuration manager for the web server.
    
    Loads configuration from multiple sources in order of priority:
    1. Environment variables
    2. Configuration file
    3. Default values
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (JSON format)
        """
        self.config_file = config_file or 'config/webserver.json'
        self._config = None
    
    def load_config(self) -> ServerConfig:
        """
        Load configuration from all sources.
        
        Returns:
            ServerConfig instance with loaded configuration
        """
        # Start with default config
        config_dict = asdict(ServerConfig())
        
        # Load from file if it exists
        file_config = self._load_from_file()
        if file_config:
            config_dict.update(file_config)
        
        # Override with environment variables
        env_config = self._load_from_env()
        config_dict.update(env_config)
        
        # Create and validate configuration
        self._config = ServerConfig(**config_dict)
        
        logging.info(f"Configuration loaded from {self.config_file}")
        logging.debug(f"Configuration: {asdict(self._config)}")
        
        return self._config
    
    def _load_from_file(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from JSON file.
        
        Returns:
            Dictionary with configuration values or None if file doesn't exist
        """
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            logging.info(f"Configuration file {self.config_file} not found, using defaults")
            return None
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logging.info(f"Configuration loaded from {self.config_file}")
            return config
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in configuration file {self.config_file}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error reading configuration file {self.config_file}: {e}")
            return None
    
    def _load_from_env(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Environment variables should be prefixed with WEBSERVER_
        (e.g., WEBSERVER_HOST, WEBSERVER_PORT).
        
        Returns:
            Dictionary with configuration values from environment
        """
        env_config = {}
        
        # Define environment variable mappings
        env_mappings = {
            'WEBSERVER_HOST': ('host', str),
            'WEBSERVER_PORT': ('port', int),
            'WEBSERVER_STATIC_DIR': ('static_dir', str),
            'WEBSERVER_LOG_LEVEL': ('log_level', str),
            'WEBSERVER_LOG_FILE': ('log_file', str),
            'WEBSERVER_MAX_REQUEST_SIZE': ('max_request_size', int),
            'WEBSERVER_REQUEST_TIMEOUT': ('request_timeout', int),
            'WEBSERVER_ENABLE_CORS': ('enable_cors', bool),
            'WEBSERVER_CORS_ORIGINS': ('cors_origins', list),
            'WEBSERVER_DEBUG_MODE': ('debug_mode', bool),
        }
        
        for env_var, (config_key, value_type) in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    if value_type == bool:
                        env_config[config_key] = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        env_config[config_key] = int(env_value)
                    elif value_type == list:
                        # Parse comma-separated list
                        env_config[config_key] = [s.strip() for s in env_value.split(',')]
                    else:
                        env_config[config_key] = env_value
                    
                    logging.debug(f"Environment override: {config_key} = {env_config[config_key]}")
                    
                except ValueError as e:
                    logging.warning(f"Invalid value for {env_var}: {env_value} ({e})")
        
        return env_config
    
    def save_config(self, config: ServerConfig) -> None:
        """
        Save configuration to file.
        
        Args:
            config: ServerConfig instance to save
        """
        # Create config directory if it doesn't exist
        config_dir = os.path.dirname(self.config_file)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(asdict(config), f, indent=2)
            logging.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logging.error(f"Error saving configuration to {self.config_file}: {e}")
    
    def get_config(self) -> Optional[ServerConfig]:
        """
        Get the current configuration.
        
        Returns:
            Current ServerConfig instance or None if not loaded
        """
        return self._config


# Example configuration file content
EXAMPLE_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "static_dir": "static",
    "log_level": "INFO",
    "log_file": "logs/webserver.log",
    "max_request_size": 2097152,  # 2MB
    "request_timeout": 60,
    "enable_cors": True,
    "cors_origins": ["http://localhost:3000", "https://myapp.com"],
    "debug_mode": false
}


def create_example_config(filename: str = 'config/webserver.json') -> None:
    """
    Create an example configuration file.
    
    Args:
        filename: Path where to create the example configuration
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(EXAMPLE_CONFIG, f, indent=2)
    
    print(f"Example configuration created at {filename}")


if __name__ == "__main__":
    # Create example configuration
    create_example_config()
    
    # Test configuration loading
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    print("Loaded configuration:")
    for key, value in asdict(config).items():
        print(f"  {key}: {value}")