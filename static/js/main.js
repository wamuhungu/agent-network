/**
 * Main JavaScript file for SimpleWebServer demo page
 * Provides interactive API testing functionality
 */

// API testing functions
async function testEndpoint(path, method = 'GET') {
    const outputElement = document.getElementById('response-output');
    const button = event.target;
    
    // Show loading state
    button.classList.add('loading');
    outputElement.textContent = 'Loading...';
    
    try {
        const response = await fetch(path, {
            method: method,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.text();
        
        // Format the response
        let formattedResponse = `HTTP ${response.status} ${response.statusText}\n`;
        formattedResponse += `Content-Type: ${response.headers.get('Content-Type')}\n\n`;
        
        // Try to pretty-print JSON
        try {
            const jsonData = JSON.parse(data);
            formattedResponse += JSON.stringify(jsonData, null, 2);
        } catch (e) {
            formattedResponse += data;
        }
        
        outputElement.textContent = formattedResponse;
        
    } catch (error) {
        outputElement.textContent = `Error: ${error.message}`;
    } finally {
        // Remove loading state
        button.classList.remove('loading');
    }
}

async function testPostEndpoint() {
    const outputElement = document.getElementById('response-output');
    const button = event.target;
    
    // Sample POST data
    const postData = {
        name: "Test User",
        message: "Hello from the web interface!",
        timestamp: new Date().toISOString()
    };
    
    // Show loading state
    button.classList.add('loading');
    outputElement.textContent = 'Loading...';
    
    try {
        const response = await fetch('/hello', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(postData)
        });
        
        const data = await response.text();
        
        // Format the response
        let formattedResponse = `HTTP ${response.status} ${response.statusText}\n`;
        formattedResponse += `Content-Type: ${response.headers.get('Content-Type')}\n\n`;
        formattedResponse += `Request Data:\n${JSON.stringify(postData, null, 2)}\n\n`;
        formattedResponse += `Response:\n`;
        
        // Try to pretty-print JSON response
        try {
            const jsonData = JSON.parse(data);
            formattedResponse += JSON.stringify(jsonData, null, 2);
        } catch (e) {
            formattedResponse += data;
        }
        
        outputElement.textContent = formattedResponse;
        
    } catch (error) {
        outputElement.textContent = `Error: ${error.message}`;
    } finally {
        // Remove loading state
        button.classList.remove('loading');
    }
}

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    console.log('SimpleWebServer demo page loaded');
    
    // Add some helpful information to the console
    console.log('Available API endpoints:');
    console.log('- GET /hello - Returns a greeting message');
    console.log('- POST /hello - Accepts JSON data and returns response');
    console.log('- GET /status - Returns server status');
    
    // Display current time
    const now = new Date();
    console.log(`Page loaded at: ${now.toISOString()}`);
});

// Global error handler for fetch requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    const outputElement = document.getElementById('response-output');
    if (outputElement && outputElement.textContent === 'Loading...') {
        outputElement.textContent = `Network Error: ${event.reason.message || 'Unknown error occurred'}`;
    }
});

// Helper function to format timestamps
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Helper function to copy response to clipboard
function copyResponse() {
    const outputElement = document.getElementById('response-output');
    const text = outputElement.textContent;
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            console.log('Response copied to clipboard');
        });
    }
}