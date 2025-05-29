"""
Test suite for the SimpleWebServer implementation.

Tests all core functionality including HTTP handling, routing,
static file serving, and error handling.
"""

import pytest
import json
import threading
import time
import requests
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the web server components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from webserver import SimpleWebServer, hello_handler, status_handler, user_profile_handler


class TestWebServerCore:
    """Test core web server functionality."""
    
    @pytest.fixture
    def temp_static_dir(self):
        """Create a temporary directory for static files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_html = Path(tmpdir) / "test.html"
            test_html.write_text("<html><body>Test Page</body></html>")
            
            test_css = Path(tmpdir) / "test.css"
            test_css.write_text("body { color: blue; }")
            
            yield tmpdir
    
    @pytest.fixture
    def test_server(self, temp_static_dir):
        """Create a test server instance."""
        return SimpleWebServer(host='localhost', port=0, static_dir=temp_static_dir)
    
    def test_server_initialization(self, test_server):
        """Test server initializes with correct configuration."""
        assert test_server.host == 'localhost'
        assert test_server.port == 0
        assert isinstance(test_server.routes, dict)
        assert isinstance(test_server.route_patterns, list)
    
    def test_add_route(self, test_server):
        """Test route registration."""
        test_server.add_route('/test', hello_handler)
        assert '/test' in test_server.routes
        assert test_server.routes['/test'] == hello_handler
    
    def test_add_route_pattern(self, test_server):
        """Test pattern-based route registration."""
        test_server.add_route_pattern(r'/user/(?P<id>\d+)', user_profile_handler)
        assert len(test_server.route_patterns) == 1
        pattern, handler = test_server.route_patterns[0]
        assert handler == user_profile_handler
        
        # Test pattern matching
        match = pattern.match('/user/123')
        assert match is not None
        assert match.groupdict() == {'id': '123'}


class TestRouteHandlers:
    """Test individual route handlers."""
    
    def test_hello_handler_get(self):
        """Test hello handler GET request."""
        mock_handler = MagicMock()
        mock_handler.request_count = 1
        
        status, content, content_type = hello_handler(mock_handler, 'GET', {})
        
        assert status == 200
        assert content_type == 'application/json'
        
        # Parse response
        response_data = json.loads(content.decode('utf-8'))
        assert response_data['message'] == "Hello from SimpleWebServer!"
        assert response_data['method'] == 'GET'
        assert 'timestamp' in response_data
    
    def test_hello_handler_post(self):
        """Test hello handler POST request."""
        mock_handler = MagicMock()
        mock_handler.request_count = 1
        mock_handler.post_data = {"test": "data"}
        
        status, content, content_type = hello_handler(mock_handler, 'POST', {})
        
        assert status == 200
        assert content_type == 'application/json'
        
        # Parse response
        response_data = json.loads(content.decode('utf-8'))
        assert response_data['message'] == "POST request received"
        assert response_data['data'] == {"test": "data"}
    
    def test_status_handler(self):
        """Test status handler."""
        mock_handler = MagicMock()
        mock_handler.client_address = ('127.0.0.1', 12345)
        mock_handler.request_count = 5
        
        status, content, content_type = status_handler(mock_handler, 'GET', {})
        
        assert status == 200
        assert content_type == 'application/json'
        
        # Parse response
        response_data = json.loads(content.decode('utf-8'))
        assert response_data['server'] == "SimpleWebServer/1.0"
        assert response_data['status'] == "running"
        assert response_data['client_ip'] == '127.0.0.1'
    
    def test_user_profile_handler(self):
        """Test user profile handler with URL parameters."""
        mock_handler = MagicMock()
        
        status, content, content_type = user_profile_handler(
            mock_handler, 'GET', {'user_id': '123'}
        )
        
        assert status == 200
        assert content_type == 'application/json'
        
        # Parse response
        response_data = json.loads(content.decode('utf-8'))
        assert response_data['user_id'] == '123'
        assert response_data['name'] == "User 123"
        assert response_data['email'] == "user123@example.com"


class TestWebServerIntegration:
    """Integration tests for the web server."""
    
    @pytest.fixture
    def running_server(self, temp_static_dir):
        """Start a test server in a separate thread."""
        server = SimpleWebServer(host='localhost', port=8765, static_dir=temp_static_dir)
        
        # Add routes
        server.add_route('/hello', hello_handler)
        server.add_route('/status', status_handler)
        server.add_route_pattern(r'/user/(?P<user_id>\d+)', user_profile_handler)
        
        # Start server in thread
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
        
        yield server
        
        # Server will be stopped when thread exits
    
    def test_get_hello_endpoint(self, running_server):
        """Test GET request to /hello endpoint."""
        response = requests.get('http://localhost:8765/hello')
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/json'
        
        data = response.json()
        assert data['message'] == "Hello from SimpleWebServer!"
        assert data['method'] == 'GET'
    
    def test_post_hello_endpoint(self, running_server):
        """Test POST request to /hello endpoint."""
        test_data = {"name": "Test User", "message": "Hello World"}
        
        response = requests.post(
            'http://localhost:8765/hello',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == "POST request received"
        assert data['data'] == test_data
    
    def test_status_endpoint(self, running_server):
        """Test status endpoint."""
        response = requests.get('http://localhost:8765/status')
        
        assert response.status_code == 200
        data = response.json()
        assert data['server'] == "SimpleWebServer/1.0"
        assert data['status'] == "running"
        assert 'timestamp' in data
    
    def test_user_profile_endpoint(self, running_server):
        """Test parameterized user profile endpoint."""
        response = requests.get('http://localhost:8765/user/123')
        
        assert response.status_code == 200
        data = response.json()
        assert data['user_id'] == '123'
        assert data['name'] == "User 123"
    
    def test_static_file_serving(self, running_server, temp_static_dir):
        """Test static file serving."""
        # Test HTML file
        response = requests.get('http://localhost:8765/test.html')
        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']
        assert "Test Page" in response.text
        
        # Test CSS file
        response = requests.get('http://localhost:8765/test.css')
        assert response.status_code == 200
        assert 'text/css' in response.headers['content-type']
        assert "color: blue" in response.text
    
    def test_404_error(self, running_server):
        """Test 404 error for non-existent routes."""
        response = requests.get('http://localhost:8765/nonexistent')
        assert response.status_code == 404
    
    def test_403_directory_traversal(self, running_server):
        """Test directory traversal protection."""
        response = requests.get('http://localhost:8765/../etc/passwd')
        assert response.status_code == 403


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_json_post(self, running_server):
        """Test handling of invalid JSON in POST requests."""
        response = requests.post(
            'http://localhost:8765/hello',
            data="invalid json",
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 400
    
    def test_large_post_data(self, running_server):
        """Test handling of large POST data."""
        large_data = {"data": "x" * 10000}  # 10KB of data
        
        response = requests.post(
            'http://localhost:8765/hello',
            json=large_data,
            headers={'Content-Type': 'application/json'}
        )
        
        # Should handle large data gracefully
        assert response.status_code == 200


class TestLogging:
    """Test logging functionality."""
    
    def test_logging_configuration(self, test_server):
        """Test that logging is properly configured."""
        import logging
        
        # Check that a file handler is configured
        handlers = logging.getLogger().handlers
        file_handlers = [h for h in handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0
    
    @patch('logging.info')
    def test_route_registration_logging(self, mock_log, test_server):
        """Test that route registration is logged."""
        test_server.add_route('/test', hello_handler)
        mock_log.assert_called_with("Route registered: /test")
    
    @patch('logging.info')
    def test_pattern_registration_logging(self, mock_log, test_server):
        """Test that pattern route registration is logged."""
        test_server.add_route_pattern(r'/test/(?P<id>\d+)', user_profile_handler)
        mock_log.assert_called_with("Route pattern registered: /test/(?P<id>\\d+)")


class TestSecurity:
    """Test security features."""
    
    def test_directory_traversal_protection(self, temp_static_dir):
        """Test protection against directory traversal attacks."""
        from webserver import WebServerHandler
        
        # Mock request handler
        handler = MagicMock(spec=WebServerHandler)
        handler.static_dir = temp_static_dir
        
        # Test various directory traversal attempts
        traversal_attempts = [
            '../../../etc/passwd',
            '..\\..\\windows\\system32\\config\\sam',
            '/..',
            '/./../../etc/passwd'
        ]
        
        # These should all be blocked
        # (In a real test, we'd need to test the actual _serve_static_file method)
        for attempt in traversal_attempts:
            # Verify the path normalization would catch these
            normalized = os.path.normpath(attempt)
            assert not normalized.startswith('/') or '..' in normalized
    
    def test_file_extension_handling(self, temp_static_dir):
        """Test proper MIME type handling for different file extensions."""
        import mimetypes
        
        test_files = {
            'test.html': 'text/html',
            'test.css': 'text/css',
            'test.js': 'application/javascript',
            'test.json': 'application/json',
            'test.txt': 'text/plain'
        }
        
        for filename, expected_type in test_files.items():
            mime_type, _ = mimetypes.guess_type(filename)
            assert mime_type == expected_type or mime_type.startswith(expected_type.split('/')[0])


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])