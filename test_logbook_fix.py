#!/usr/bin/env python3
"""
Test script to verify logbook application fixes
"""

import sys
import os
sys.path.append('src/logbook')

try:
    from app import LogbookEntry, LogbookDatabase, app
    from datetime import datetime
    
    print("✅ Import successful")
    
    # Test LogbookEntry with id property
    entry = LogbookEntry(entry_id=1, title="Test", content="Test content")
    print(f"✅ LogbookEntry.id property: {entry.id}")
    print(f"✅ LogbookEntry.formatted_date: {entry.formatted_date}")
    
    # Test nl2br filter
    with app.app_context():
        test_text = "Line 1\nLine 2\nLine 3"
        filtered = app.jinja_env.filters['nl2br'](test_text)
        print(f"✅ nl2br filter working: {filtered}")
    
    # Test database creation and basic operations
    os.makedirs('src/logbook/data', exist_ok=True)
    db = LogbookDatabase('src/logbook/data/test_logbook.db')
    print("✅ Database creation successful")
    
    # Test entry creation
    test_entry = LogbookEntry(title="Test Entry", content="This is a test entry")
    entry_id = db.add_entry(test_entry)
    print(f"✅ Entry creation successful (ID: {entry_id})")
    
    # Test entry retrieval
    entries = db.get_all_entries()
    if entries:
        print(f"✅ Entry retrieval successful: {entries[0].id}, {entries[0].title}")
        print(f"✅ Formatted date works: {entries[0].formatted_date}")
    
    print("\n🎉 All fixes verified! The logbook application should work now.")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()