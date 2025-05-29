"""
Simple HTTP Web Server Implementation

A lightweight web server that handles HTTP requests, serves static files,
and provides basic routing capabilities using Python's built-in libraries.
"""

import http.server
import socketserver
import urllib.parse
import os
import mimetypes
import json
import logging
import re
from pathlib import Path
from typing import Dict, Callable, Optional, Tuple, Any, List
from datetime import datetime


class WebServerHandler(http.server.BaseHTTPRequestHandler):
    """
    Custom HTTP request handler for the web server.
    
    Handles HTTP GET and POST requests, provides routing functionality,
    and serves static files with proper error handling.
    """
    
    # Class-level routing table and configuration
    routes: Dict[str, Callable] = {}
    route_patterns: List[Tuple[re.Pattern, Callable]] = []
    static_dir: str = "static"
    request_count: int = 0
    
    def __init__(self, *args, **kwargs):
        """Initialize the handler with logging configuration."""
        super().__init__(*args, **kwargs)
    
    def log_message(self, format: str, *args: Any) -> None:
        """
        Override default logging to use proper logging module.
        
        Args:
            format: Log message format string
            *args: Arguments for the format string
        """
        # Increment request counter
        WebServerHandler.request_count += 1
        
        # Enhanced logging with request count and timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        client_ip = self.address_string()
        log_message = f"[{timestamp}] Request #{self.request_count} from {client_ip} - {format % args}"
        logging.info(log_message)
    
    def do_GET(self) -> None:
        """
        Handle HTTP GET requests.
        
        Checks for registered routes first, then falls back to static file serving.
        """
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            
            # Check for exact path routes first
            if path in self.routes:
                response = self.routes[path](self, 'GET', {})
                if response:
                    self._send_response(*response)
                return
            
            # Check for pattern-based routes
            for pattern, handler in self.route_patterns:
                match = pattern.match(path)
                if match:
                    response = handler(self, 'GET', match.groupdict())
                    if response:
                        self._send_response(*response)
                    return
            
            # Serve static files
            self._serve_static_file(path)
            
        except Exception as e:
            logging.error(f"Error handling GET request: {e}")
            self._send_error(500, "Internal Server Error")
    
    def do_POST(self) -> None:
        """
        Handle HTTP POST requests.
        
        Processes POST data and routes to appropriate handlers.
        """
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            
            # Get POST data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse POST data based on content type
            content_type = self.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                try:
                    self.post_data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError:
                    self._send_error(400, "Invalid JSON data")
                    return
            else:
                self.post_data = urllib.parse.parse_qs(
                    post_data.decode('utf-8')
                )
            
            # Check for exact path routes first
            if path in self.routes:
                response = self.routes[path](self, 'POST', {})
                if response:
                    self._send_response(*response)
                return
            
            # Check for pattern-based routes
            for pattern, handler in self.route_patterns:
                match = pattern.match(path)
                if match:
                    response = handler(self, 'POST', match.groupdict())
                    if response:
                        self._send_response(*response)
                    return
            
            # No route found
            self._send_error(404, "Not Found")
            
        except Exception as e:
            logging.error(f"Error handling POST request: {e}")
            self._send_error(500, "Internal Server Error")
    
    def _serve_static_file(self, path: str) -> None:
        """
        Serve static files from the static directory.
        
        Args:
            path: The requested file path
        """
        # Remove leading slash and prevent directory traversal
        if path.startswith('/'):
            path = path[1:]
        
        if not path:
            path = "index.html"
        
        # Prevent directory traversal attacks
        if '..' in path or path.startswith('/'):
            self._send_error(403, "Forbidden")
            return
        
        file_path = Path(self.static_dir) / path
        
        # Check if file exists and is within static directory
        try:
            resolved_path = file_path.resolve()
            static_resolved = Path(self.static_dir).resolve()
            
            if not str(resolved_path).startswith(str(static_resolved)):
                self._send_error(403, "Forbidden")
                return
                
            if not resolved_path.exists() or not resolved_path.is_file():
                self._send_error(404, "File Not Found")
                return
            
            # Read and serve the file
            with open(resolved_path, 'rb') as f:
                content = f.read()
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(str(resolved_path))
            if content_type is None:
                content_type = 'application/octet-stream'
            
            self._send_response(200, content, content_type)
            
        except Exception as e:
            logging.error(f"Error serving static file {path}: {e}")
            self._send_error(500, "Internal Server Error")
    
    def _send_response(self, status_code: int, content: bytes, 
                      content_type: str = 'text/html') -> None:
        """
        Send HTTP response with proper headers.
        
        Args:
            status_code: HTTP status code
            content: Response content as bytes
            content_type: MIME type of the content
        """
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Server', 'SimpleWebServer/1.0')
        self.end_headers()
        self.wfile.write(content)
    
    def _send_error(self, status_code: int, message: str) -> None:
        """
        Send HTTP error response.
        
        Args:
            status_code: HTTP status code
            message: Error message
        """
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error {status_code}</title>
        </head>
        <body>
            <h1>Error {status_code}</h1>
            <p>{message}</p>
            <hr>
            <small>SimpleWebServer/1.0</small>
        </body>
        </html>
        """
        self._send_response(status_code, error_html.encode('utf-8'))


class SimpleWebServer:
    """
    Main web server class that coordinates HTTP handling and routing.
    
    Provides methods to start the server, register routes, and configure
    static file serving.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 8000, 
                 static_dir: str = 'static'):
        """
        Initialize the web server.
        
        Args:
            host: Server host address
            port: Server port number
            static_dir: Directory for static files
        """
        self.host = host
        self.port = port
        self.static_dir = static_dir
        self.routes: Dict[str, Callable] = {}
        self.route_patterns: List[Tuple[re.Pattern, Callable]] = []
        
        # Configure logging with file and console output
        self._setup_logging()
        
        # Set static directory in handler
        WebServerHandler.static_dir = static_dir
        WebServerHandler.routes = self.routes
        WebServerHandler.route_patterns = self.route_patterns
    
    def _setup_logging(self) -> None:
        """Configure logging for both file and console output."""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/webserver.log'),
                logging.StreamHandler()
            ]
        )
    
    def add_route(self, path: str, handler: Callable) -> None:
        """
        Register a route handler for exact path matching.
        
        Args:
            path: URL path to handle (exact match)
            handler: Function to handle requests to this path
        """
        self.routes[path] = handler
        WebServerHandler.routes[path] = handler
        logging.info(f"Route registered: {path}")
    
    def add_route_pattern(self, pattern: str, handler: Callable) -> None:
        """
        Register a route handler for pattern-based matching.
        
        Args:
            pattern: Regex pattern to match paths (e.g., r'/user/(?P<id>\d+)')
            handler: Function to handle requests matching this pattern
        """
        compiled_pattern = re.compile(pattern)
        self.route_patterns.append((compiled_pattern, handler))
        WebServerHandler.route_patterns = self.route_patterns
        logging.info(f"Route pattern registered: {pattern}")
    
    def start(self) -> None:
        """
        Start the web server.
        
        Creates the HTTP server and begins listening for requests.
        """
        try:
            # Create static directory if it doesn't exist
            os.makedirs(self.static_dir, exist_ok=True)
            
            # Create the server
            with socketserver.TCPServer((self.host, self.port), 
                                      WebServerHandler) as httpd:
                logging.info(f"Server starting on {self.host}:{self.port}")
                logging.info(f"Static files served from: {self.static_dir}")
                logging.info("Press Ctrl+C to stop the server")
                
                httpd.serve_forever()
                
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
        except Exception as e:
            logging.error(f"Server error: {e}")
            raise


# Example route handlers
def hello_handler(request_handler: WebServerHandler, method: str, 
                 url_params: Dict[str, str]) -> Tuple[int, bytes, str]:
    """
    Example route handler for /hello endpoint.
    
    Args:
        request_handler: The HTTP request handler instance
        method: HTTP method (GET or POST)
        url_params: URL parameters from pattern matching
        
    Returns:
        Tuple of (status_code, content, content_type)
    """
    if method == 'GET':
        response = {
            "message": "Hello from SimpleWebServer!",
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url_params": url_params,
            "request_count": WebServerHandler.request_count
        }
        content = json.dumps(response, indent=2).encode('utf-8')
        return (200, content, 'application/json')
    
    elif method == 'POST':
        post_data = getattr(request_handler, 'post_data', {})
        response = {
            "message": "POST request received",
            "data": post_data,
            "timestamp": datetime.now().isoformat(),
            "url_params": url_params
        }
        content = json.dumps(response, indent=2).encode('utf-8')
        return (200, content, 'application/json')


def status_handler(request_handler: WebServerHandler, method: str,
                  url_params: Dict[str, str]) -> Tuple[int, bytes, str]:
    """
    Server status endpoint.
    
    Args:
        request_handler: The HTTP request handler instance
        method: HTTP method
        url_params: URL parameters from pattern matching
        
    Returns:
        Tuple of (status_code, content, content_type)
    """
    status = {
        "server": "SimpleWebServer/1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "client_ip": request_handler.client_address[0],
        "request_count": WebServerHandler.request_count,
        "url_params": url_params
    }
    content = json.dumps(status, indent=2).encode('utf-8')
    return (200, content, 'application/json')


def user_profile_handler(request_handler: WebServerHandler, method: str,
                        url_params: Dict[str, str]) -> Tuple[int, bytes, str]:
    """
    Example handler for user profile endpoints with URL parameters.
    
    Handles paths like /user/123 where 123 is the user ID.
    
    Args:
        request_handler: The HTTP request handler instance
        method: HTTP method
        url_params: URL parameters (contains 'user_id')
        
    Returns:
        Tuple of (status_code, content, content_type)
    """
    user_id = url_params.get('user_id', 'unknown')
    
    # Mock user data
    user_data = {
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "created_at": "2025-01-01T00:00:00Z",
        "last_active": datetime.now().isoformat(),
        "method": method
    }
    
    content = json.dumps(user_data, indent=2).encode('utf-8')
    return (200, content, 'application/json')


def api_info_handler(request_handler: WebServerHandler, method: str,
                    url_params: Dict[str, str]) -> Tuple[int, bytes, str]:
    """
    API information and available endpoints.
    
    Args:
        request_handler: The HTTP request handler instance
        method: HTTP method
        url_params: URL parameters from pattern matching
        
    Returns:
        Tuple of (status_code, content, content_type)
    """
    api_info = {
        "api_name": "SimpleWebServer API",
        "version": "1.0.0",
        "endpoints": {
            "/hello": {
                "methods": ["GET", "POST"],
                "description": "Greeting endpoint with request echo"
            },
            "/status": {
                "methods": ["GET"],
                "description": "Server status and statistics"
            },
            "/user/{user_id}": {
                "methods": ["GET"],
                "description": "User profile information",
                "parameters": ["user_id (integer)"]
            },
            "/api": {
                "methods": ["GET"],
                "description": "This API information endpoint"
            }
        },
        "timestamp": datetime.now().isoformat(),
        "request_count": WebServerHandler.request_count
    }
    
    content = json.dumps(api_info, indent=2).encode('utf-8')
    return (200, content, 'application/json')


if __name__ == "__main__":
    # Create and configure the server
    server = SimpleWebServer(host='localhost', port=8000)
    
    # Register exact path routes
    server.add_route('/hello', hello_handler)
    server.add_route('/status', status_handler)
    server.add_route('/api', api_info_handler)
    
    # Register pattern-based routes
    server.add_route_pattern(r'/user/(?P<user_id>\d+)', user_profile_handler)
    
    # Start the server
    server.start()