# SimpleWebServer Documentation

## Overview

SimpleWebServer is a lightweight HTTP server implementation built with Python's built-in libraries. It provides basic web server functionality including HTTP request handling, static file serving, routing, and error handling.

## Features

- **HTTP/1.1 Support**: Handles GET and POST requests
- **Static File Serving**: Serves HTML, CSS, JavaScript, images, and other static files
- **Flexible Routing**: Both exact path matching and regex pattern-based routing
- **Error Handling**: Comprehensive error pages and logging
- **Security**: Protection against directory traversal attacks
- **Configuration Management**: JSON-based configuration with environment variable overrides
- **Logging**: File and console logging with configurable levels
- **Testing**: Comprehensive test suite with pytest

## Quick Start

### Basic Usage

```python
from src.webserver import SimpleWebServer

# Create server instance
server = SimpleWebServer(host='localhost', port=8000, static_dir='static')

# Start the server
server.start()
```

### Adding Routes

```python
from src.webserver import SimpleWebServer

def my_handler(request_handler, method, url_params):
    response = {"message": "Hello World!"}
    content = json.dumps(response).encode('utf-8')
    return (200, content, 'application/json')

server = SimpleWebServer()

# Add exact path route
server.add_route('/api/hello', my_handler)

# Add pattern-based route
server.add_route_pattern(r'/user/(?P<user_id>\d+)', user_profile_handler)

server.start()
```

## Installation and Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd agent-network
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server**:
   ```bash
   python src/webserver.py
   ```

5. **Access the server**:
   Open your browser to `http://localhost:8000`

## Configuration

### Configuration File

Create a configuration file at `config/webserver.json`:

```json
{
  "host": "0.0.0.0",
  "port": 8080,
  "static_dir": "static",
  "log_level": "INFO",
  "log_file": "logs/webserver.log",
  "max_request_size": 2097152,
  "request_timeout": 60,
  "enable_cors": true,
  "cors_origins": ["http://localhost:3000", "https://myapp.com"],
  "debug_mode": false
}
```

### Environment Variables

Override configuration with environment variables:

```bash
export WEBSERVER_HOST=0.0.0.0
export WEBSERVER_PORT=8080
export WEBSERVER_STATIC_DIR=public
export WEBSERVER_LOG_LEVEL=DEBUG
export WEBSERVER_DEBUG_MODE=true
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | string | `localhost` | Server host address |
| `port` | integer | `8000` | Server port number |
| `static_dir` | string | `static` | Directory for static files |
| `log_level` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `log_file` | string | `logs/webserver.log` | Log file path |
| `max_request_size` | integer | `1048576` | Maximum request size in bytes |
| `request_timeout` | integer | `30` | Request timeout in seconds |
| `enable_cors` | boolean | `false` | Enable CORS headers |
| `cors_origins` | array | `["*"]` | Allowed CORS origins |
| `debug_mode` | boolean | `false` | Enable debug mode |

## API Reference

### SimpleWebServer Class

#### Constructor

```python
SimpleWebServer(host='localhost', port=8000, static_dir='static')
```

#### Methods

- **`add_route(path, handler)`**: Register exact path route
- **`add_route_pattern(pattern, handler)`**: Register regex pattern route
- **`start()`**: Start the server (blocking)

### Route Handlers

Route handlers must have this signature:

```python
def handler(request_handler, method, url_params):
    """
    Args:
        request_handler: HTTP request handler instance
        method: HTTP method ('GET' or 'POST')
        url_params: Dictionary of URL parameters from pattern matching
    
    Returns:
        Tuple of (status_code, content_bytes, content_type)
    """
    pass
```

### Request Handler Attributes

- `request_handler.path`: Request path
- `request_handler.headers`: Request headers
- `request_handler.client_address`: Client IP and port
- `request_handler.post_data`: POST data (for POST requests)

## Built-in Endpoints

The server includes several example endpoints:

### GET /hello
Returns a JSON greeting message.

**Response:**
```json
{
  "message": "Hello from SimpleWebServer!",
  "timestamp": "2025-05-26T23:30:00",
  "method": "GET",
  "request_count": 1
}
```

### POST /hello
Accepts JSON data and echoes it back.

**Request:**
```json
{
  "name": "User",
  "message": "Hello World"
}
```

**Response:**
```json
{
  "message": "POST request received",
  "data": {
    "name": "User",
    "message": "Hello World"
  },
  "timestamp": "2025-05-26T23:30:00"
}
```

### GET /status
Returns server status information.

**Response:**
```json
{
  "server": "SimpleWebServer/1.0",
  "status": "running",
  "timestamp": "2025-05-26T23:30:00",
  "client_ip": "127.0.0.1",
  "request_count": 5
}
```

### GET /user/{user_id}
Returns user profile information (example pattern route).

**Response:**
```json
{
  "user_id": "123",
  "name": "User 123",
  "email": "user123@example.com",
  "created_at": "2025-01-01T00:00:00Z",
  "last_active": "2025-05-26T23:30:00"
}
```

### GET /api
Returns API information and available endpoints.

## Static File Serving

The server automatically serves static files from the configured static directory:

- **HTML files**: `text/html` content type
- **CSS files**: `text/css` content type
- **JavaScript files**: `application/javascript` content type
- **Images**: Appropriate image MIME types
- **Other files**: `application/octet-stream` content type

### Default Files

- Requesting `/` serves `static/index.html` if it exists
- Directory traversal protection prevents access to files outside the static directory

## Error Handling

The server provides comprehensive error handling:

### HTTP Status Codes

- **200 OK**: Successful requests
- **400 Bad Request**: Invalid JSON or malformed requests
- **403 Forbidden**: Directory traversal attempts or access denied
- **404 Not Found**: Missing routes or files
- **500 Internal Server Error**: Server-side errors

### Error Pages

Custom error pages are returned for all error conditions:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Error 404</title>
</head>
<body>
    <h1>Error 404</h1>
    <p>File Not Found</p>
    <hr>
    <small>SimpleWebServer/1.0</small>
</body>
</html>
```

## Security Features

### Directory Traversal Protection

The server prevents directory traversal attacks by:
- Resolving file paths and checking they remain within the static directory
- Rejecting requests containing `..` path components
- Validating file existence and type

### Input Validation

- JSON parsing with error handling
- Request size limits
- Timeout protection

### Headers

- `Server` header identifies the server
- `Content-Type` headers are properly set
- `Content-Length` headers for accurate content size

## Logging

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical error messages

### Log Format

```
2025-05-26 23:30:00,123 - INFO - [2025-05-26 23:30:00] Request #1 from 127.0.0.1 - "GET /hello HTTP/1.1" 200 -
```

### Log Files

- Default log file: `logs/webserver.log`
- Automatic log directory creation
- Both file and console logging

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest requests

# Run all tests
pytest tests/test_webserver.py -v

# Run specific test class
pytest tests/test_webserver.py::TestWebServerCore -v

# Run with coverage
pip install pytest-cov
pytest tests/test_webserver.py --cov=src/webserver --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Full server testing with HTTP requests
- **Security Tests**: Directory traversal and input validation
- **Error Handling Tests**: Error condition testing

## Deployment

### Production Deployment

1. **Set production configuration**:
   ```bash
   export WEBSERVER_HOST=0.0.0.0
   export WEBSERVER_PORT=80
   export WEBSERVER_LOG_LEVEL=WARNING
   export WEBSERVER_DEBUG_MODE=false
   ```

2. **Use a process manager** (e.g., systemd, supervisor):
   ```ini
   # systemd service file
   [Unit]
   Description=SimpleWebServer
   After=network.target
   
   [Service]
   Type=simple
   User=webserver
   WorkingDirectory=/opt/webserver
   ExecStart=/opt/webserver/venv/bin/python src/webserver.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Use a reverse proxy** (nginx, Apache) for production traffic

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY static/ static/
COPY config/ config/

EXPOSE 8000

CMD ["python", "src/webserver.py"]
```

## Troubleshooting

### Common Issues

1. **Port already in use**:
   - Change the port in configuration
   - Kill existing processes on the port

2. **Permission denied on port 80/443**:
   - Run as root (not recommended) or use a higher port
   - Use a reverse proxy

3. **Static files not loading**:
   - Check static directory path
   - Verify file permissions
   - Check browser developer tools for errors

4. **CORS issues**:
   - Enable CORS in configuration
   - Add appropriate origins to `cors_origins`

### Debug Mode

Enable debug mode for additional logging:

```bash
export WEBSERVER_DEBUG_MODE=true
export WEBSERVER_LOG_LEVEL=DEBUG
```

### Log Analysis

Monitor the log file for issues:

```bash
# Follow log in real-time
tail -f logs/webserver.log

# Search for errors
grep ERROR logs/webserver.log

# Monitor access patterns
grep "GET\|POST" logs/webserver.log
```

## Contributing

1. Follow the coding standards in `docs/standards/coding_standards.md`
2. Add tests for new functionality
3. Update documentation for new features
4. Ensure all tests pass before submitting

## License

This project is part of the Agent Network system and follows the project's licensing terms.