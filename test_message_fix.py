#!/usr/bin/env python3
"""
Simple test to verify the message format fix is working.
"""

import sys
sys.path.append('tools')
from task_notifier import send_task_completion_notification

# Send a test notification
print("🧪 Testing message format fix...")
print("-" * 50)

success = send_task_completion_notification(
    task_id='test_fix_verification',
    completed_by='developer',
    deliverables=['hello_primes.py', 'test_hello_primes.py', 'README_primes.md'],
    summary='Testing that manager receives properly formatted messages',
    target_queue='manager-queue'
)

if success:
    print("\n✅ Message sent successfully!")
    print("\nThe manager's message listener should now show:")
    print("- message_type: task_completion")
    print("- from_agent: developer")
    print("- task_id: test_fix_verification")
else:
    print("\n❌ Failed to send message")

print("\nCheck the manager's message listener output to verify!")
print("-" * 50)