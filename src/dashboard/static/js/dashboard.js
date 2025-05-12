/**
 * Agent Network Dashboard
 * 
 * JavaScript functionality for the dashboard, including data fetching,
 * UI updates, and data visualization.
 */

// Charts and data storage
let tokenUsageChart = null;
let completionRateChart = null;
let dashboardData = {
    agents: {},
    report: {},
    activeTasks: [],
    completedTasks: [],
    recentLogs: []
};

// Refresh interval in milliseconds (30 seconds)
const REFRESH_INTERVAL = 30000;
let refreshTimer = null;

// Initialize the dashboard when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    document.getElementById('refresh-button').addEventListener('click', refreshAllData);
    
    // Initialize charts with empty data
    initializeCharts();
    
    // Load initial data
    refreshAllData();
    
    // Set up auto-refresh
    startAutoRefresh();
});

/**
 * Starts the auto-refresh timer to update data periodically
 */
function startAutoRefresh() {
    refreshTimer = setInterval(refreshAllData, REFRESH_INTERVAL);
}

/**
 * Refreshes all dashboard data from the API
 */
function refreshAllData() {
    // Show refresh animation
    const refreshButton = document.getElementById('refresh-button');
    const refreshIcon = refreshButton.querySelector('i');
    refreshIcon.classList.add('refreshing');
    
    // Update last updated time
    updateLastUpdatedTime();
    
    // Fetch all data concurrently
    Promise.all([
        fetchAgentStatus(),
        fetchAgentReport(),
        fetchActiveTasks(),
        fetchCompletedTasks(),
        fetchRecentLogs()
    ])
    .then(() => {
        // Update all UI components with new data
        updateStatusCards();
        updateAgentStatusPanel();
        updateResourceCharts();
        updateTaskLists();
        updateRecentLogs();
        
        // Stop refresh animation
        refreshIcon.classList.remove('refreshing');
    })
    .catch(error => {
        console.error('Error refreshing dashboard data:', error);
        refreshIcon.classList.remove('refreshing');
        alert('Error refreshing dashboard data. See console for details.');
    });
}

/**
 * Updates the "last updated" timestamp
 */
function updateLastUpdatedTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    document.querySelector('#last-updated-time span').textContent = timeString;
}

/**
 * Fetches the current status of all agents
 */
async function fetchAgentStatus() {
    const response = await fetch('/api/agents/status');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    dashboardData.agents = await response.json();
}

/**
 * Fetches the comprehensive agent activity report
 */
async function fetchAgentReport() {
    const response = await fetch('/api/agents/report');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    dashboardData.report = await response.json();
}

/**
 * Fetches active tasks in the system
 */
async function fetchActiveTasks() {
    const response = await fetch('/api/tasks/active');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    dashboardData.activeTasks = await response.json();
}

/**
 * Fetches completed tasks in the system
 */
async function fetchCompletedTasks() {
    const response = await fetch('/api/tasks/completed');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    dashboardData.completedTasks = await response.json();
}

/**
 * Fetches recent log entries
 */
async function fetchRecentLogs() {
    const response = await fetch('/api/logs/recent');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    dashboardData.recentLogs = await response.json();
}

/**
 * Updates the overview status cards with current data
 */
function updateStatusCards() {
    // Update total agents count
    const agentCount = Object.keys(dashboardData.agents).length;
    document.getElementById('total-agents').textContent = agentCount;
    
    // Update task counts
    document.getElementById('active-tasks').textContent = dashboardData.activeTasks.length;
    document.getElementById('completed-tasks').textContent = dashboardData.completedTasks.length;
    
    // Update token usage and cost
    if (dashboardData.report.total_tokens_used !== undefined) {
        document.getElementById('total-tokens').textContent = dashboardData.report.total_tokens_used.toLocaleString();
        document.getElementById('estimated-cost').textContent = 
            `Estimated cost: $${dashboardData.report.estimated_cost.toFixed(4)}`;
    }
}

/**
 * Updates the agent status panel with current data
 */
function updateAgentStatusPanel() {
    const container = document.getElementById('agent-status-container');
    
    if (Object.keys(dashboardData.agents).length === 0) {
        container.innerHTML = '<p class="text-center">No agent data available</p>';
        return;
    }
    
    let html = '';
    
    // Loop through each agent and create a status card
    for (const [agentId, agentData] of Object.entries(dashboardData.agents)) {
        const isActive = agentData.last_activity && 
            (new Date() - new Date(agentData.last_activity)) < 3600000; // 1 hour
        
        html += `
            <div class="card agent-card ${isActive ? 'active' : 'inactive'} mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <h5 class="card-title">${agentId}</h5>
                        <span class="badge ${isActive ? 'bg-success' : 'bg-danger'} agent-status-badge">
                            ${isActive ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="agent-details">
                        <p>Last Activity: ${agentData.last_activity ? new Date(agentData.last_activity).toLocaleString() : 'Never'}</p>
                        ${agentData.current_task ? `<p>Current Task: ${agentData.current_task}</p>` : ''}
                        <p>Recent Activities:</p>
                        <ul>
                            ${agentData.recent_activities ? agentData.recent_activities.map(activity => 
                                `<li>${activity.type} - ${new Date(activity.time).toLocaleTimeString()}</li>`).join('') : ''}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

/**
 * Updates resource usage charts with current data
 */
function updateResourceCharts() {
    updateTokenUsageChart();
    updateCompletionRateChart();
}

/**
 * Initialize empty charts
 */
function initializeCharts() {
    const tokenCtx = document.getElementById('token-usage-chart').getContext('2d');
    tokenUsageChart = new Chart(tokenCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Tokens Used',
                data: [],
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    const rateCtx = document.getElementById('completion-rate-chart').getContext('2d');
    completionRateChart = new Chart(rateCtx, {
        type: 'doughnut',
        data: {
            labels: ['Completed', 'In Progress'],
            datasets: [{
                data: [0, 0],
                backgroundColor: [
                    'rgba(40, 167, 69, 0.7)',
                    'rgba(255, 193, 7, 0.7)'
                ],
                borderColor: [
                    'rgba(40, 167, 69, 1)',
                    'rgba(255, 193, 7, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * Updates the token usage chart with current data
 */
function updateTokenUsageChart() {
    if (!dashboardData.report.agent_stats) return;
    
    const agentStats = dashboardData.report.agent_stats;
    const agents = Object.keys(agentStats);
    const tokenData = agents.map(agent => agentStats[agent].tokens_used || 0);
    
    tokenUsageChart.data.labels = agents;
    tokenUsageChart.data.datasets[0].data = tokenData;
    tokenUsageChart.update();
}

/**
 * Updates the task completion rate chart with current data
 */
function updateCompletionRateChart() {
    if (!dashboardData.report.completed_tasks && !dashboardData.report.total_tasks) return;
    
    const completed = dashboardData.report.completed_tasks || 0;
    const inProgress = (dashboardData.report.total_tasks || 0) - completed;
    
    completionRateChart.data.datasets[0].data = [completed, inProgress];
    completionRateChart.update();
}

/**
 * Updates the active and completed task lists
 */
function updateTaskLists() {
    // Update active tasks list
    const activeContainer = document.getElementById('active-tasks-list');
    if (dashboardData.activeTasks.length === 0) {
        activeContainer.innerHTML = '<p class="text-center">No active tasks</p>';
    } else {
        let html = '';
        dashboardData.activeTasks.forEach(task => {
            html += `
                <div class="task-item">
                    <div class="task-title">${task.title || task.id}</div>
                    <div class="task-agent">Assigned to: ${task.agent}</div>
                    <div class="task-time">Started: ${new Date(task.start_time).toLocaleString()}</div>
                </div>
            `;
        });
        activeContainer.innerHTML = html;
    }
    
    // Update completed tasks list
    const completedContainer = document.getElementById('completed-tasks-list');
    if (dashboardData.completedTasks.length === 0) {
        completedContainer.innerHTML = '<p class="text-center">No completed tasks</p>';
    } else {
        let html = '';
        dashboardData.completedTasks.forEach(task => {
            html += `
                <div class="task-item">
                    <div class="task-title">${task.title || task.id}</div>
                    <div class="task-agent">Completed by: ${task.agent}</div>
                    <div class="task-time">
                        ${task.start_time ? `Started: ${new Date(task.start_time).toLocaleString()}<br>` : ''}
                        Completed: ${new Date(task.completion_time).toLocaleString()}
                    </div>
                </div>
            `;
        });
        completedContainer.innerHTML = html;
    }
}

/**
 * Updates the recent logs panel
 */
function updateRecentLogs() {
    const container = document.getElementById('recent-logs-container');
    
    if (dashboardData.recentLogs.length === 0) {
        container.innerHTML = '<p class="text-center">No logs available</p>';
        return;
    }
    
    // Most recent logs first
    const logs = [...dashboardData.recentLogs].reverse();
    
    let html = '';
    logs.forEach(log => {
        html += `
            <div class="log-entry">
                <span class="log-time">${new Date(log.timestamp).toLocaleString()}</span>
                <span class="log-agent">${log.agent_id}</span>
                <span class="log-type ${log.activity_type}">${log.activity_type}</span>
                <span class="log-details">${formatLogDetails(log.details)}</span>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

/**
 * Formats log details for display
 */
function formatLogDetails(details) {
    if (!details) return '';
    
    if (details.task_id) {
        return `Task: ${details.task_id} - ${details.title || ''}`;
    } else if (details.tokens_used) {
        return `Tokens: ${details.tokens_used}, Time: ${details.compute_time}ms`;
    } else {
        return JSON.stringify(details).substring(0, 100);
    }
}