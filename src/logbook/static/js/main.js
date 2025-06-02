/**
 * Personal Logbook - Main JavaScript functionality
 * Handles UI interactions, real-time updates, and utility functions
 */

// Global variables
let lastUpdateCheck = Date.now();
let notificationPermission = 'default';

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // Request notification permission
    requestNotificationPermission();
    
    // Add fade-in animation to cards
    animateCards();
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        initializeTooltips();
    }
    
    // Auto-save functionality for forms
    initializeAutoSave();
    
    // Keyboard shortcuts
    initializeKeyboardShortcuts();
    
    console.log('Personal Logbook initialized successfully');
}

/**
 * Update the current time display
 */
function updateCurrentTime() {
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const now = new Date();
        timeElement.textContent = now.toLocaleString();
    }
}

/**
 * Request notification permission for browser notifications
 */
function requestNotificationPermission() {
    if ('Notification' in window) {
        Notification.requestPermission().then(function(permission) {
            notificationPermission = permission;
            if (permission === 'granted') {
                console.log('Notification permission granted');
            }
        });
    }
}

/**
 * Show a browser notification
 */
function showNotification(title, message, icon = '/static/favicon.ico') {
    if (notificationPermission === 'granted') {
        new Notification(title, {
            body: message,
            icon: icon,
            timeout: 4000
        });
    }
}

/**
 * Add fade-in animation to cards
 */
function animateCards() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, index * 100);
    });
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Auto-save form data to localStorage
 */
function initializeAutoSave() {
    const forms = document.querySelectorAll('form[data-autosave]');
    forms.forEach(form => {
        const formId = form.id || 'default-form';
        
        // Load saved data
        loadFormData(form, formId);
        
        // Save on input
        form.addEventListener('input', debounce(() => {
            saveFormData(form, formId);
        }, 1000));
        
        // Clear on successful submit
        form.addEventListener('submit', () => {
            clearFormData(formId);
        });
    });
}

/**
 * Save form data to localStorage
 */
function saveFormData(form, formId) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    localStorage.setItem(`logbook_form_${formId}`, JSON.stringify(data));
    console.log(`Form data saved for ${formId}`);
}

/**
 * Load form data from localStorage
 */
function loadFormData(form, formId) {
    const savedData = localStorage.getItem(`logbook_form_${formId}`);
    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            
            Object.keys(data).forEach(key => {
                const field = form.querySelector(`[name="${key}"]`);
                if (field && data[key]) {
                    field.value = data[key];
                }
            });
            
            console.log(`Form data loaded for ${formId}`);
        } catch (error) {
            console.error('Error loading form data:', error);
        }
    }
}

/**
 * Clear saved form data
 */
function clearFormData(formId) {
    localStorage.removeItem(`logbook_form_${formId}`);
    console.log(`Form data cleared for ${formId}`);
}

/**
 * Initialize keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl+N or Cmd+N: New entry
        if ((event.ctrlKey || event.metaKey) && event.key === 'n' && !event.shiftKey) {
            event.preventDefault();
            window.location.href = '/add';
        }
        
        // Ctrl+H or Cmd+H: Home
        if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
            event.preventDefault();
            window.location.href = '/';
        }
        
        // Escape: Close modals or go back
        if (event.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            if (modals.length === 0 && window.history.length > 1) {
                window.history.back();
            }
        }
    });
}

/**
 * Debounce function to limit function calls
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(timestamp) {
    const now = new Date();
    const time = new Date(timestamp);
    const diffInSeconds = Math.floor((now - time) / 1000);
    
    if (diffInSeconds < 60) {
        return 'just now';
    } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 2592000) {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days} day${days > 1 ? 's' : ''} ago`;
    } else {
        return time.toLocaleDateString();
    }
}

/**
 * Update all relative timestamps on the page
 */
function updateRelativeTimestamps() {
    const timestamps = document.querySelectorAll('[data-timestamp]');
    timestamps.forEach(element => {
        const timestamp = element.getAttribute('data-timestamp');
        element.textContent = formatRelativeTime(timestamp);
    });
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showToast('Copied to clipboard!', 'success');
        } catch (fallbackError) {
            showToast('Failed to copy to clipboard', 'error');
        }
        document.body.removeChild(textArea);
    }
}

/**
 * Show a toast notification
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, duration);
}

/**
 * Validate audio file before processing
 */
function validateAudioFile(file) {
    const validTypes = ['audio/wav', 'audio/mp3', 'audio/webm', 'audio/ogg'];
    const maxSize = 50 * 1024 * 1024; // 50MB
    
    if (!validTypes.includes(file.type)) {
        showToast('Please select a valid audio file (WAV, MP3, WebM, or OGG)', 'error');
        return false;
    }
    
    if (file.size > maxSize) {
        showToast('Audio file is too large. Maximum size is 50MB.', 'error');
        return false;
    }
    
    return true;
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Search entries (client-side filtering)
 */
function searchEntries(query) {
    const entries = document.querySelectorAll('.logbook-entry');
    const searchTerm = query.toLowerCase().trim();
    
    entries.forEach(entry => {
        const title = entry.querySelector('.card-header h6').textContent.toLowerCase();
        const content = entry.querySelector('.card-text')?.textContent.toLowerCase() || '';
        
        if (title.includes(searchTerm) || content.includes(searchTerm)) {
            entry.style.display = 'block';
            entry.classList.add('fade-in');
        } else {
            entry.style.display = 'none';
            entry.classList.remove('fade-in');
        }
    });
}

/**
 * Export entries as JSON
 */
async function exportEntries() {
    try {
        const response = await fetch('/api/entries');
        const data = await response.json();
        
        const exportData = {
            export_date: new Date().toISOString(),
            total_entries: data.entries.length,
            entries: data.entries
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `logbook_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
        showToast('Entries exported successfully!', 'success');
    } catch (error) {
        console.error('Export failed:', error);
        showToast('Failed to export entries', 'error');
    }
}

/**
 * Check for updates periodically
 */
function checkForUpdates() {
    // This could be expanded to check for new entries from other sources
    // For now, just update relative timestamps
    updateRelativeTimestamps();
}

// Start periodic updates
setInterval(checkForUpdates, 30000); // Every 30 seconds

// Utility functions for external use
window.LogbookUtils = {
    showToast,
    copyToClipboard,
    formatRelativeTime,
    exportEntries,
    searchEntries,
    validateAudioFile,
    formatFileSize
};